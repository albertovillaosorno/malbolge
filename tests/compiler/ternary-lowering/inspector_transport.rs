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
use std::fs::{remove_file, write};
use std::path::{Path, PathBuf};
use std::process::id;
use std::sync::atomic::{AtomicU64, Ordering};
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
