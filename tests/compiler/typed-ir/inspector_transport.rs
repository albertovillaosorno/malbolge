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
#[cfg(target_os = "linux")]
use std::fs::{create_dir_all, remove_dir_all};
use std::fs::{remove_file, write};
use std::path::{Path, PathBuf};
#[cfg(target_os = "linux")]
use std::process::Command;
use std::process::id;
use std::sync::atomic::{AtomicUsize, Ordering};
#[cfg(unix)]
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use super::{
    ExtractRequest, InspectorFailure, InspectorLimits, InspectorPipePermit,
    drain_pipe, extract_with_limits, extract_with_limits_and_capacity,
};

static NEXT_FIXTURE: AtomicUsize = AtomicUsize::new(0);

// This test file is included by several compiler roots. Their independent
// counters can collide inside one process, so also bind the test thread.
#[cfg(target_os = "linux")]
fn fixture_namespace() -> String {
    format!("{}-{:?}", id(), thread::current().id())
}

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

#[cfg(target_os = "linux")]
#[test]
fn isolated_python_ignores_poisoned_startup_modules() -> Result<(), String> {
    let index = NEXT_FIXTURE.fetch_add(1, Ordering::Relaxed);
    let directory = temp_dir()
        .join(format!("malbolge-typed-inspector-poison-{}-{index}", id()));
    create_dir_all(&directory)
        .map_err(|error| format!("create poison fixture: {error}"))?;
    let marker = directory.join("injected");
    let hostile = directory.join("sitecustomize.py");
    let script = directory.join("trusted.py");
    let wrapper = directory.join("interpreter");
    let injected = format!(
        "from pathlib import Path\nPath({:?}).touch()\n",
        marker.display().to_string(),
    );
    write(&hostile, injected)
        .map_err(|error| format!("write sitecustomize: {error}"))?;
    write(&script, "import sys\nsys.stdout.buffer.write(b'trusted')\n")
        .map_err(|error| format!("write trusted script: {error}"))?;
    let launch = format!(
        "#!/bin/sh\nPYTHONPATH='{}' PYTHONHOME='{}' exec '{}' \"$@\"\n",
        directory.display(),
        directory.join("bad-python-home").display(),
        repository_python().display(),
    );
    // The parent must not hold the executable inode open for writing:
    // concurrent test forks can inherit that descriptor and cause ETXTBSY.
    let source = directory.join("interpreter-source");
    write(&source, launch)
        .map_err(|error| format!("write poisoned wrapper source: {error}"))?;
    let installed = Command::new("/usr/bin/install")
        .args(["-m", "700"])
        .arg(&source)
        .arg(&wrapper)
        .status()
        .map_err(|error| format!("publish poisoned wrapper: {error}"))?;
    if !installed.success() {
        return Err(format!("publish poisoned wrapper exited: {installed}"));
    }
    let observed = extract_with_limits(
        ExtractRequest {
            codec: "compiler.test-state-v1",
            inspector: &script,
            interpreter: &wrapper,
            progress: Path::new("not-consumed.json"),
        },
        limits(1024, 1024, Duration::from_secs(5)),
    );
    let injection_ran = marker.exists();
    remove_dir_all(&directory)
        .map_err(|error| format!("cleanup poisoned fixture: {error}"))?;
    if injection_ran || observed != Ok(b"trusted".to_vec()) {
        return Err(format!(
            "Python startup injection: {observed:?}, marker={injection_ran}"
        ));
    }
    Ok(())
}

#[test]
fn requires_isolated_python_inspector_runtime() {
    let observed = run_fixture(
        concat!(
            "import sys\n",
            "sys.stdout.buffer.write(str(sys.flags.isolated).encode())\n"
        ),
        limits(1024, 1024, Duration::from_secs(5)),
    );
    assert_eq!(observed, Ok(b"1".to_vec()));
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
fn success_kills_redirected_stdio_descendant() -> Result<(), String> {
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|error| format!("fixture clock failed: {error}"))?
        .as_nanos();
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join(".temp");
    let marker =
        root.join(format!("inspector-success-orphan-{}-{nonce}.txt", id()));
    let ready =
        root.join(format!("inspector-success-launched-{}-{nonce}.txt", id()));
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
            "subprocess.Popen([sys.executable,'-I','-c',{:?}],",
            "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,",
            "stderr=subprocess.DEVNULL)\n",
            "pathlib.Path({:?}).write_text('ready')\n",
            "sys.stdout.buffer.write(b'verified-state')\n",
        ),
        child_code,
        ready.to_string_lossy(),
    );
    let observed =
        run_fixture(&script, limits(1024, 1024, Duration::from_secs(5)));
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
    if observed != Ok(b"verified-state".to_vec()) || !launched || escaped {
        return Err(format!(
            concat!(
                "successful inspector leaked same-group descendant: ",
                "{:?}, launched={}, escaped={}",
            ),
            observed, launched, escaped,
        ));
    }
    Ok(())
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
fn interpreter_option_cannot_replace_trusted_inspector() {
    for path in ["-V", "-"] {
        let observed = extract_with_limits(
            ExtractRequest {
                codec: "compiler.test-state-v1",
                inspector: Path::new(path),
                interpreter: &repository_python(),
                progress: Path::new("not-used.json"),
            },
            limits(1024, 1024, Duration::from_secs(2)),
        );
        assert_eq!(observed, Err(InspectorFailure::Rejected));
    }
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

#[test]
fn inspector_drain_capacity_rejects_before_spawn() {
    static ACTIVE: AtomicUsize = AtomicUsize::new(0);
    let held = InspectorPipePermit::acquire(&ACTIVE, 1);
    assert!(held.is_ok(), "first inspector slot must be available");
    let request = ExtractRequest {
        codec: "compiler.test-state-v1",
        inspector: Path::new("unused.py"),
        interpreter: Path::new("/missing-inspector-executable-32714"),
        progress: Path::new("unused.json"),
    };
    let budget = limits(32, 32, Duration::from_secs(1));
    assert_eq!(
        extract_with_limits_and_capacity(request, budget, &ACTIVE, 1),
        Err(InspectorFailure::Rejected),
        "exhausted slots must reject before child launch",
    );
    assert_eq!(ACTIVE.load(Ordering::Acquire), 1);
    drop(held);
    assert_eq!(
        extract_with_limits_and_capacity(request, budget, &ACTIVE, 1),
        Err(InspectorFailure::Launch),
        "released slots must allow normal launch admission",
    );
    assert_eq!(ACTIVE.load(Ordering::Acquire), 0);
}

#[cfg(unix)]
#[test]
fn inspector_drain_lease_outlives_caller_until_pipe_eof() -> Result<(), String>
{
    use std::os::unix::net::UnixStream;
    use std::sync::Arc;

    static ACTIVE: AtomicUsize = AtomicUsize::new(0);
    let (reader, writer) = UnixStream::pair()
        .map_err(|error| format!("create blocking pipe: {error}"))?;
    let held = Arc::new(
        InspectorPipePermit::acquire(&ACTIVE, 1)
            .map_err(|_error| String::from("acquire reader slot"))?,
    );
    let receiver = drain_pipe(reader, 32, Arc::clone(&held))
        .map_err(|_error| String::from("spawn blocked reader"))?;
    drop(held);
    if ACTIVE.load(Ordering::Acquire) != 1
        || InspectorPipePermit::acquire(&ACTIVE, 1).is_ok()
    {
        return Err(String::from("blocked reader lost its capacity slot"));
    }
    drop(writer);
    let bytes = receiver
        .recv_timeout(Duration::from_secs(2))
        .map_err(|error| format!("reader did not close: {error}"))?
        .map_err(|error| format!("reader failed: {error}"))?;
    if !bytes.is_empty() {
        return Err(String::from("empty pipe yielded unexpected bytes"));
    }
    wait_for_drain_release(&ACTIVE, 100, "reader completion")
}

#[cfg(target_os = "linux")]
#[test]
fn escaped_inspector_descendant_keeps_slot_until_pipe_close()
-> Result<(), String> {
    static ACTIVE: AtomicUsize = AtomicUsize::new(0);
    let nonce = NEXT_FIXTURE.fetch_add(1, Ordering::Relaxed);
    let namespace = fixture_namespace();
    let script = temp_dir().join(format!(
        "malbolge-typed-escaped-slot-{namespace}-{nonce}.py"
    ));
    let marker = temp_dir().join(format!(
        "malbolge-typed-escaped-slot-{namespace}-{nonce}.ready"
    ));
    let source = format!(
        concat!(
            "import subprocess,sys\nfrom pathlib import Path\n",
            "subprocess.Popen([sys.executable, '-c', ",
            "'import time; time.sleep(1.5)'], ",
            "start_new_session=True)\n",
            "Path({:?}).touch()\n",
        ),
        marker.display().to_string(),
    );
    write(&script, source)
        .map_err(|error| format!("write inspector: {error}"))?;
    let request = ExtractRequest {
        codec: "compiler.test-state-v1",
        inspector: &script,
        interpreter: &repository_python(),
        progress: Path::new("unread-progress.json"),
    };
    let rejected = extract_with_limits_and_capacity(
        request,
        limits(1024, 1024, Duration::from_millis(700)),
        &ACTIVE,
        1,
    );
    let launched = marker.exists();
    remove_file(&script).map_err(|error| format!("remove fixture: {error}"))?;
    if launched {
        remove_file(&marker)
            .map_err(|error| format!("remove marker: {error}"))?;
    }
    if !launched || rejected != Err(InspectorFailure::Rejected) {
        return Err(format!("escaped child not exercised: {rejected:?}"));
    }
    if ACTIVE.load(Ordering::Acquire) != 1 {
        return Err(String::from("escaped child pipe lost reserved slot"));
    }
    let unavailable = extract_with_limits_and_capacity(
        ExtractRequest {
            interpreter: Path::new("/missing-inspector-after-timeout"),
            ..request
        },
        limits(32, 32, Duration::from_secs(1)),
        &ACTIVE,
        1,
    );
    if unavailable != Err(InspectorFailure::Rejected) {
        return Err(format!("retry bypassed reserved slot: {unavailable:?}"));
    }
    wait_for_drain_release(&ACTIVE, 600, "escaped child EOF")
}

#[cfg(unix)]
fn wait_for_drain_release(
    counter: &AtomicUsize,
    attempts: usize,
    reason: &str,
) -> Result<(), String> {
    for _ in 0usize..attempts {
        if counter.load(Ordering::Acquire) == 0 {
            return Ok(());
        }
        thread::sleep(Duration::from_millis(5));
    }
    Err(format!("{reason} did not release inspector capacity"))
}
