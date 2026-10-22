// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Integration regressions for the bounded typed-IR inspector transport.
// - Must-Not:
//   - Own compiler state or change the product inspector trust boundary.
// - Allows:
//   - Inputs: caller-chosen bounded Python inspector fixtures.
//   - Outputs: deterministic byte and process-failure assertions.
//   - Side effects: short-lived temporary scripts and bounded child processes.
// - Split-When:
//   - Another compiler function owns an independent transport protocol.
// - Merge-When:
//   - Source-level process transport tests move to a shared test harness.
// - Summary:
//   - Locks the bounded stage-inspector child resource and failure behavior.
// - Description:
//   - Exercises limits, diagnostics, lifecycle and wide pipe output.
// - Usage:
//   - Compiled by the typed-IR integration test root.
// - Defaults:
//   - No test fixture may escape its byte or time budget.
//

//! Bounded compiler inspector transport regressions.

use std::env::temp_dir;
use std::fs::{remove_file, write};
use std::path::{Path, PathBuf};
use std::process::id;
use std::sync::atomic::{AtomicUsize, Ordering};
#[cfg(target_os = "linux")]
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use super::{
    ExtractRequest, InspectorFailure, InspectorLimits, extract_with_limits,
};

static NEXT_FIXTURE: AtomicUsize = AtomicUsize::new(0);

fn repository_python() -> PathBuf {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    if cfg!(windows) {
        root.join(".dependencies/python/3.14.7/python.exe")
    } else {
        root.join(".dependencies/python/3.14.7/bin/python")
    }
}

fn run_fixture(
    script: &str,
    limits: InspectorLimits,
) -> Result<Vec<u8>, InspectorFailure> {
    let sequence = NEXT_FIXTURE.fetch_add(1, Ordering::Relaxed);
    let unique = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|_error| InspectorFailure::Rejected)?
        .as_nanos();
    let path = temp_dir().join(format!(
        "malbolge-inspector-{}-{unique}-{sequence}.py",
        id(),
    ));
    write(&path, script).map_err(|_error| InspectorFailure::Rejected)?;
    let result = extract_with_limits(
        ExtractRequest {
            codec: "compiler.test-state-v1",
            inspector: &path,
            interpreter: &repository_python(),
            progress: Path::new("unread-progress.json"),
        },
        limits,
    );
    remove_file(&path).map_err(|_error| InspectorFailure::Rejected)?;
    result
}

fn limits(stdout: usize, stderr: usize, timeout: Duration) -> InspectorLimits {
    InspectorLimits { stderr, stdout, timeout }
}

#[test]
fn accepts_concurrent_large_stdout_drain() {
    let observed = run_fixture(
        "import sys\nsys.stdout.buffer.write(b'x' * 262144)\n",
        limits(300_000, 1024, Duration::from_secs(5)),
    );
    let admitted = observed
        .map(|bytes| (bytes.len(), bytes.iter().all(|value| *value == b'x')));
    assert_eq!(admitted, Ok((262_144, true)));
}

#[test]
fn rejects_stdout_exceeding_declared_byte_limit() {
    let started = Instant::now();
    let observed = run_fixture(
        "import sys\nsys.stdout.buffer.write(b'x' * 1000000)\n",
        limits(1024, 1024, Duration::from_secs(5)),
    );
    assert_eq!(observed, Err(InspectorFailure::Rejected));
    assert!(started.elapsed() < Duration::from_secs(3));
}

#[test]
fn rejects_stderr_exceeding_diagnostic_limit() {
    let observed = run_fixture(
        "import sys\nsys.stderr.buffer.write(b'!' * 50000)\n",
        limits(1024, 512, Duration::from_secs(5)),
    );
    assert_eq!(observed, Err(InspectorFailure::Rejected));
}

#[test]
fn rejects_child_diagnostics_even_on_zero_exit_status() {
    let observed = run_fixture(
        concat!(
            "import sys\n",
            "sys.stdout.buffer.write(b'good')\n",
            "sys.stderr.write('oops')\n",
        ),
        limits(1024, 1024, Duration::from_secs(5)),
    );
    assert_eq!(observed, Err(InspectorFailure::Rejected));
}

#[cfg(target_os = "linux")]
#[test]
fn rejects_failed_inspector_before_inherited_pipe_holder_finishes() {
    let started = Instant::now();
    let observed = run_fixture(
        concat!(
            "import subprocess,sys\n",
            "subprocess.Popen([sys.executable,'-c',",
            "'import time;time.sleep(3)'],",
            "stdout=sys.stdout,stderr=sys.stderr)\n",
            "sys.stderr.write('failed')\n",
            "sys.exit(7)\n",
        ),
        limits(1024, 1024, Duration::from_secs(5)),
    );
    assert_eq!(observed, Err(InspectorFailure::Rejected));
    assert!(
        started.elapsed() < Duration::from_secs(2),
        "a failed inspector waited for an unrelated pipe holder"
    );
}

#[cfg(target_os = "linux")]
#[test]
fn rejects_completed_diagnostics_without_waiting_for_stdout_descendant() {
    let started = Instant::now();
    let observed = run_fixture(
        concat!(
            "import subprocess,sys\n",
            "subprocess.Popen([sys.executable,'-c',",
            "'import time;time.sleep(3)'],",
            "stdout=sys.stdout,stderr=subprocess.DEVNULL)\n",
            "sys.stderr.write('invalid inspector diagnostics')\n",
        ),
        limits(1024, 1024, Duration::from_secs(5)),
    );
    assert_eq!(observed, Err(InspectorFailure::Rejected));
    assert!(
        started.elapsed() < Duration::from_secs(2),
        "completed inspector diagnostics waited for a stdout pipe holder"
    );
}

#[cfg(target_os = "linux")]
#[test]
fn kills_inherited_stdout_holder_after_rejected_diagnostics()
-> Result<(), String> {
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|error| format!("fixture clock failed: {error}"))?
        .as_nanos();
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join(".temp");
    let marker = root.join(format!(
        "inspector-diagnostic-descendant-{}-{nonce}.txt",
        id()
    ));
    let ready = root.join(format!(
        "inspector-diagnostic-launched-{}-{nonce}.txt",
        id()
    ));
    let child_code = format!(
        concat!(
            "import time,pathlib;time.sleep(1);",
            "pathlib.Path({:?}).write_text('orphan');time.sleep(2)",
        ),
        marker.to_string_lossy(),
    );
    let script = format!(
        concat!(
            "import subprocess,sys,pathlib\n",
            "subprocess.Popen([sys.executable,'-c',{:?}],",
            "stdout=sys.stdout,stderr=subprocess.DEVNULL)\n",
            "pathlib.Path({:?}).write_text('ready')\n",
            "sys.stderr.write('diagnostic')\n",
        ),
        child_code,
        ready.to_string_lossy(),
    );
    let started = Instant::now();
    let observed =
        run_fixture(&script, limits(1024, 1024, Duration::from_secs(5)));
    let elapsed = started.elapsed();
    let launched = ready.exists();
    if launched {
        remove_file(&ready)
            .map_err(|error| format!("remove launch marker: {error}"))?;
    }
    thread::sleep(Duration::from_millis(1200));
    let escaped = marker.exists();
    if escaped {
        remove_file(&marker)
            .map_err(|error| format!("remove escaped marker: {error}"))?;
    }
    if observed != Err(InspectorFailure::Rejected)
        || !launched
        || escaped
        || elapsed >= Duration::from_secs(2)
    {
        return Err(format!(
            "diagnostic group cleanup: {observed:?}, {elapsed:?}"
        ));
    }
    Ok(())
}

#[test]
fn terminates_stalled_child_at_inspection_deadline() {
    let started = Instant::now();
    let observed = run_fixture(
        "import time\ntime.sleep(20)\n",
        limits(1024, 1024, Duration::from_millis(150)),
    );
    assert_eq!(observed, Err(InspectorFailure::Rejected));
    assert!(started.elapsed() < Duration::from_secs(3));
}

#[cfg(target_os = "linux")]
#[test]
fn kills_inherited_pipe_descendant_after_deadline() -> Result<(), String> {
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|error| format!("fixture clock failed: {error}"))?
        .as_nanos();
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join(".temp");
    let marker =
        root.join(format!("inspector-descendant-{}-{nonce}.txt", id()));
    let ready = root.join(format!("inspector-launched-{}-{nonce}.txt", id()));
    let child_code = format!(
        concat!(
            "import time,pathlib;time.sleep(1);",
            "pathlib.Path({:?}).write_text('orphan')",
        ),
        marker.to_string_lossy(),
    );
    let script = format!(
        concat!(
            "import subprocess,sys,pathlib\n",
            "subprocess.Popen([sys.executable,'-c',{:?}],",
            "stdout=sys.stdout,stderr=sys.stderr)\n",
            "pathlib.Path({:?}).write_text('ready')\n",
        ),
        child_code,
        ready.to_string_lossy(),
    );
    let observed =
        run_fixture(&script, limits(1024, 1024, Duration::from_millis(500)));
    let launched = ready.exists();
    if launched {
        remove_file(&ready)
            .map_err(|error| format!("cleanup launch evidence: {error}"))?;
    }
    thread::sleep(Duration::from_millis(1200));
    let escaped = marker.exists();
    if escaped {
        remove_file(&marker)
            .map_err(|error| format!("cleanup escaped marker: {error}"))?;
    }
    if !launched {
        return Err(String::from(
            "test inspector never launched its descendant",
        ));
    }
    if observed != Err(InspectorFailure::Rejected) {
        return Err(format!(
            "expired inspector was not rejected: {observed:?}"
        ));
    }
    if escaped {
        return Err(String::from(
            "inherited-pipe descendant survived deadline",
        ));
    }
    Ok(())
}

#[test]
fn zero_deadline_rejects_without_child_creation() {
    let observed = run_fixture(
        "raise AssertionError('should not start')\n",
        limits(1024, 1024, Duration::ZERO),
    );
    assert_eq!(observed, Err(InspectorFailure::Rejected));
}

#[cfg(target_os = "linux")]
#[test]
fn admits_directory_qualified_relative_interpreter() -> Result<(), String> {
    let next = NEXT_FIXTURE.fetch_add(1, Ordering::Relaxed);
    let script =
        temp_dir().join(format!("malbolge-typed-qualified-{}-{next}.py", id()));
    write(
        &script,
        "import sys\nsys.stdout.buffer.write(b'qualified')\n",
    )
    .map_err(|error| format!("write inspector fixture: {error}"))?;
    let observed = extract_with_limits(
        ExtractRequest {
            codec: "compiler.test-state-v1",
            inspector: &script,
            interpreter: Path::new("./.dependencies/python/3.14.7/bin/python"),
            progress: Path::new("unread-progress.json"),
        },
        limits(1024, 1024, Duration::from_secs(5)),
    );
    remove_file(&script)
        .map_err(|error| format!("clean inspector fixture: {error}"))?;
    if observed == Ok(b"qualified".to_vec()) {
        Ok(())
    } else {
        Err(format!("relative interpreter was rejected: {observed:?}"))
    }
}

#[cfg(target_os = "linux")]
#[test]
fn rejects_bare_interpreter_before_host_path_lookup() {
    let observed = extract_with_limits(
        ExtractRequest {
            codec: "compiler.test-state-v1",
            inspector: Path::new("ignored.py"),
            interpreter: Path::new("true"),
            progress: Path::new("ignored.json"),
        },
        limits(1024, 1024, Duration::from_secs(2)),
    );
    assert_eq!(observed, Err(InspectorFailure::Launch));
}

#[test]
fn preserves_spawn_failure_category() {
    let observed = extract_with_limits(
        ExtractRequest {
            codec: "compiler.test-state-v1",
            inspector: Path::new("missing-inspector.py"),
            interpreter: Path::new("/missing-inspector-interpreter"),
            progress: Path::new("missing-progress.json"),
        },
        limits(1024, 1024, Duration::from_secs(1)),
    );
    assert_eq!(observed, Err(InspectorFailure::Launch));
}

#[cfg(unix)]
#[test]
fn rejects_descendant_inherited_pipe_after_inspector_exit() {
    let started = Instant::now();
    let observed = run_fixture(
        concat!(
            "import subprocess,sys\n",
            "subprocess.Popen([sys.executable, '-c', ",
            "'import time;time.sleep(1)'], ",
            "stdout=sys.stdout, stderr=sys.stderr)\n",
        ),
        limits(1024, 1024, Duration::from_millis(180)),
    );
    assert_eq!(observed, Err(InspectorFailure::Rejected));
    assert!(started.elapsed() < Duration::from_secs(3));
}
