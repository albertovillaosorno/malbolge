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
//   - Bounded child transport regressions for ternary checkpoint recovery.
// - Must-Not:
//   - Parse progress JSON or confer independent checkpoint acceptance.
// - Allows:
//   - Inputs: temporary configured Python inspector fixtures.
//   - Outputs: exact successful bytes or typed fail-closed failure categories.
//   - Side effects: temporary scripts and bounded child process execution.
// - Split-When:
//   - Another stage requires an independent process policy.
// - Merge-When:
//   - An explicit governed shared inspector port owns this test boundary.
// - Summary:
//   - Proves ternary inspector resource limits under adversarial processes.
// - Description:
//   - Tests wide pipes, byte overflows, deadlines, and child status failures.
// - Usage:
//   - Included by the ternary-lowering compiler integration test root.
// - Defaults:
//   - All launched children are subject to bounded deadlines.
//

//! Ternary checkpoint process transport resource regressions.

use std::env::temp_dir;
use std::fs::{read_to_string, remove_file, write};
use std::path::{Path, PathBuf};
use std::process::id;
use std::sync::atomic::{AtomicU64, Ordering};
#[cfg(target_os = "linux")]
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use super::{
    RequestedInspector, TransportBudget, TransportError, extract_with_budget,
};

static NEXT_ID: AtomicU64 = AtomicU64::new(0);

fn interpreter() -> PathBuf {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    if cfg!(windows) {
        root.join(".dependencies/python/3.14.7/python.exe")
    } else {
        root.join(".dependencies/python/3.14.7/bin/python")
    }
}

fn budget(
    state_bytes: usize,
    diagnostic_bytes: usize,
    deadline: Duration,
) -> TransportBudget {
    TransportBudget {
        deadline,
        diagnostic_bytes,
        state_bytes,
    }
}

fn inspect_script(
    source: &str,
    limit: TransportBudget,
) -> Result<Vec<u8>, TransportError> {
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|_error| TransportError::Rejected)?
        .as_nanos();
    let next = NEXT_ID.fetch_add(1, Ordering::Relaxed);
    let script = temp_dir().join(format!(
        "malbolge-ternary-inspector-{}-{nonce}-{next}.py",
        id(),
    ));
    write(&script, source).map_err(|_error| TransportError::Rejected)?;
    let result = extract_with_budget(
        &RequestedInspector {
            codec: "malbolge-ternary-ir-v1",
            inspector: &script,
            interpreter: &interpreter(),
            sidecar: Path::new("not-consumed.json"),
        },
        limit,
    );
    remove_file(&script).map_err(|_error| TransportError::Rejected)?;
    result
}

#[test]
fn returns_complete_stdout_larger_than_one_pipe_buffer() {
    let payload = inspect_script(
        "import sys\nsys.stdout.buffer.write(b'x'*262144)\n",
        budget(262_144, 64, Duration::from_secs(5)),
    );
    let dimensions = payload
        .map(|bytes| (bytes.len(), bytes.iter().all(|byte| *byte == b'x')));
    assert_eq!(dimensions, Ok((262_144, true)));
}

#[test]
fn accepts_early_pipe_eof_while_child_still_finishing() {
    let observed = inspect_script(
        concat!(
            "import sys,time\n",
            "sys.stdout.buffer.write(b'early-state')\n",
            "sys.stdout.close()\n",
            "sys.stderr.close()\n",
            "time.sleep(0.15)\n",
        ),
        budget(1024, 1024, Duration::from_secs(3)),
    );
    assert_eq!(observed, Ok(b"early-state".to_vec()));
}

#[test]
fn rejects_one_byte_beyond_output_budget() {
    let observed = inspect_script(
        "import sys\nsys.stdout.buffer.write(b'state-overflow')\n",
        budget(13, 64, Duration::from_secs(5)),
    );
    assert_eq!(observed, Err(TransportError::Rejected));
}

#[test]
fn rejects_excessive_diagnostics() {
    let observed = inspect_script(
        "import sys\nsys.stderr.buffer.write(b'!'*100000)\n",
        budget(1024, 1024, Duration::from_secs(5)),
    );
    assert_eq!(observed, Err(TransportError::Rejected));
}

#[test]
fn rejects_nonzero_exit_with_state_bytes() {
    let observed = inspect_script(
        concat!(
            "import sys\n",
            "sys.stdout.buffer.write(b'state')\n",
            "sys.exit(7)\n",
        ),
        budget(1024, 1024, Duration::from_secs(5)),
    );
    assert_eq!(observed, Err(TransportError::Rejected));
}

#[test]
fn rejects_successful_child_with_diagnostics() {
    let observed = inspect_script(
        "import sys\nsys.stderr.write('diagnostic')\n",
        budget(1024, 1024, Duration::from_secs(5)),
    );
    assert_eq!(observed, Err(TransportError::Rejected));
}

#[cfg(target_os = "linux")]
#[test]
fn rejects_completed_diagnostics_without_waiting_for_stdout_descendant() {
    let started = Instant::now();
    let observed = inspect_script(
        concat!(
            "import subprocess,sys\n",
            "subprocess.Popen([sys.executable,'-c',",
            "'import time;time.sleep(3)'],",
            "stdout=sys.stdout,stderr=subprocess.DEVNULL)\n",
            "sys.stderr.write('invalid inspector diagnostics')\n",
        ),
        budget(1024, 1024, Duration::from_secs(5)),
    );
    assert_eq!(observed, Err(TransportError::Rejected));
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
        inspect_script(&script, budget(1024, 1024, Duration::from_secs(5)));
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
    if observed != Err(TransportError::Rejected)
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
fn terminates_child_when_deadline_expires() {
    let started = Instant::now();
    let observed = inspect_script(
        "import time\ntime.sleep(20)\n",
        budget(1024, 1024, Duration::from_millis(180)),
    );
    assert_eq!(observed, Err(TransportError::Rejected));
    assert!(started.elapsed() < Duration::from_secs(3));
}

#[cfg(unix)]
#[test]
fn rejects_inherited_pipes_before_descendant_exits() {
    let started = Instant::now();
    let observed = inspect_script(
        concat!(
            "import subprocess,sys\n",
            "subprocess.Popen([sys.executable, '-c', ",
            "'import time;time.sleep(1)'], ",
            "stdout=sys.stdout, stderr=sys.stderr)\n",
        ),
        budget(1024, 1024, Duration::from_millis(180)),
    );
    assert_eq!(observed, Err(TransportError::Rejected));
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
        inspect_script(&script, budget(1024, 1024, Duration::from_millis(500)));
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
    if observed != Err(TransportError::Rejected) {
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
fn null_stdin_completes_without_inheriting_interactive_input() {
    let observed = inspect_script(
        concat!(
            "import sys\n",
            "sys.stdout.buffer.write(b'OK'+sys.stdin.buffer.read())\n",
        ),
        budget(1024, 1024, Duration::from_secs(5)),
    );
    assert_eq!(observed, Ok(b"OK".to_vec()));
}

#[test]
fn rejects_simultaneously_full_state_and_diagnostic_pipes() {
    let started = Instant::now();
    let observed = inspect_script(
        concat!(
            "import sys\n",
            "sys.stdout.buffer.write(b'x'*300000)\n",
            "sys.stderr.buffer.write(b'!'*300000)\n",
        ),
        budget(350_000, 4096, Duration::from_secs(5)),
    );
    assert_eq!(observed, Err(TransportError::Rejected));
    assert!(started.elapsed() < Duration::from_secs(3));
}

#[test]
fn zero_deadline_rejects_before_child_spawn() {
    let observed = extract_with_budget(
        &RequestedInspector {
            codec: "malbolge-ternary-ir-v1",
            inspector: Path::new("missing.py"),
            interpreter: Path::new("/unavailable-interpreter"),
            sidecar: Path::new("missing.json"),
        },
        budget(1024, 1024, Duration::ZERO),
    );
    assert_eq!(observed, Err(TransportError::Rejected));
}

#[cfg(target_os = "linux")]
#[test]
fn reaps_direct_inspector_child_after_deadline() -> Result<(), String> {
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|error| format!("fixture clock failure: {error}"))?
        .as_nanos();
    let path = temp_dir().join(format!(
        "malbolge-ternary-inspector-pid-{}-{nonce}.txt",
        id(),
    ));
    let source = format!(
        concat!(
            "import os,time\n",
            "open({:?},'w').write(str(os.getpid()))\n",
            "time.sleep(20)\n",
        ),
        path.to_string_lossy(),
    );
    let result =
        inspect_script(&source, budget(1024, 1024, Duration::from_millis(750)));
    let pid_text = read_to_string(&path)
        .map_err(|error| format!("read child PID evidence: {error}"))?;
    remove_file(&path)
        .map_err(|error| format!("remove child PID evidence: {error}"))?;
    let pid = pid_text
        .parse::<u32>()
        .map_err(|error| format!("parse child PID evidence: {error}"))?;
    if result != Err(TransportError::Rejected) {
        return Err(String::from("expired direct child was not rejected"));
    }
    if Path::new(&format!("/proc/{pid}")).exists() {
        return Err(String::from("expired inspector child was not reaped"));
    }
    Ok(())
}

#[test]
fn preserves_interpreter_launch_failure() {
    let observed = extract_with_budget(
        &RequestedInspector {
            codec: "malbolge-ternary-ir-v1",
            inspector: Path::new("missing.py"),
            interpreter: Path::new("/unavailable-interpreter"),
            sidecar: Path::new("missing.json"),
        },
        budget(1024, 1024, Duration::from_secs(1)),
    );
    assert_eq!(observed, Err(TransportError::Launch));
}
