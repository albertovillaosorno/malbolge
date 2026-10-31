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
#[cfg(target_os = "linux")]
use std::fs::{create_dir_all, remove_dir_all};
use std::fs::{read_to_string, remove_file, write};
use std::path::{Path, PathBuf};
#[cfg(target_os = "linux")]
use std::process::Command;
use std::process::id;
use std::sync::atomic::{AtomicU64, AtomicUsize, Ordering};
#[cfg(unix)]
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use super::{
    PipeDelivery, PipeKind, RequestedInspector, TransportBudget,
    TransportError, TransportPipePermit, extract_with_budget,
    extract_with_budget_and_capacity, receive_pipe,
};

static NEXT_ID: AtomicU64 = AtomicU64::new(0);

// This file is included by multiple compiler test modules with independent
// NEXT_ID counters. A PID and counter alone can collide in parallel tests.
#[cfg(target_os = "linux")]
fn fixture_namespace() -> String {
    format!("{}-{:?}", id(), thread::current().id())
}

#[cfg(target_os = "linux")]
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "different test threads must use different fixture names"
)]
fn fixture_namespaces_distinguish_parallel_threads() -> Result<(), String> {
    let first = thread::spawn(fixture_namespace)
        .join()
        .map_err(|_error| String::from("first test thread panicked"))?;
    let second = thread::spawn(fixture_namespace)
        .join()
        .map_err(|_error| String::from("second test thread panicked"))?;
    assert_ne!(first, second);
    Ok(())
}

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

#[cfg(target_os = "linux")]
#[test]
fn isolated_python_ignores_poisoned_startup_modules() -> Result<(), String> {
    let index = NEXT_ID.fetch_add(1, Ordering::Relaxed);
    let directory = temp_dir().join(format!(
        "malbolge-ternary-inspector-poison-{}-{index}",
        fixture_namespace()
    ));
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
        interpreter().display(),
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
    let observed = extract_with_budget(
        &RequestedInspector {
            codec: "malbolge-ternary-ir-v1",
            inspector: &script,
            interpreter: &wrapper,
            sidecar: Path::new("not-consumed.json"),
        },
        budget(1024, 1024, Duration::from_secs(5)),
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
    let observed = inspect_script(
        concat!(
            "import sys\n",
            "sys.stdout.buffer.write(str(sys.flags.isolated).encode())\n"
        ),
        budget(1024, 1024, Duration::from_secs(5)),
    );
    assert_eq!(observed, Ok(b"1".to_vec()));
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

#[cfg(target_os = "linux")]
#[test]
fn admits_directory_qualified_relative_interpreter() -> Result<(), String> {
    let next = NEXT_ID.fetch_add(1, Ordering::Relaxed);
    let script = temp_dir().join(format!(
        "malbolge-ternary-qualified-{}-{next}.py",
        fixture_namespace()
    ));
    write(
        &script,
        "import sys\nsys.stdout.buffer.write(b'qualified')\n",
    )
    .map_err(|error| format!("write inspector fixture: {error}"))?;
    let observed = extract_with_budget(
        &RequestedInspector {
            codec: "malbolge-ternary-ir-v1",
            inspector: &script,
            interpreter: Path::new("./.dependencies/python/3.14.7/bin/python"),
            sidecar: Path::new("unread-progress.json"),
        },
        budget(1024, 1024, Duration::from_secs(5)),
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
    let observed = extract_with_budget(
        &RequestedInspector {
            codec: "malbolge-ternary-ir-v1",
            inspector: Path::new("ignored.py"),
            interpreter: Path::new("true"),
            sidecar: Path::new("ignored.json"),
        },
        budget(1024, 1024, Duration::from_secs(2)),
    );
    assert_eq!(observed, Err(TransportError::Launch));
}

#[test]
fn interpreter_option_cannot_replace_trusted_inspector() {
    for path in ["-V", "-"] {
        let observed = extract_with_budget(
            &RequestedInspector {
                codec: "malbolge-ternary-ir-v1",
                inspector: Path::new(path),
                interpreter: &interpreter(),
                sidecar: Path::new("not-used.json"),
            },
            budget(1024, 1024, Duration::from_secs(2)),
        );
        assert_eq!(observed, Err(TransportError::Rejected));
    }
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

#[test]
fn ternary_drain_capacity_rejects_before_spawn() {
    static ACTIVE: AtomicUsize = AtomicUsize::new(0);
    let held = TransportPipePermit::acquire(&ACTIVE, 1);
    assert!(held.is_ok(), "first inspector slot must be available");
    let request = RequestedInspector {
        codec: "malbolge-ternary-ir-v1",
        inspector: Path::new("unused.py"),
        interpreter: Path::new("/missing-ternary-inspector-32714"),
        sidecar: Path::new("unused.json"),
    };
    let bound = budget(32, 32, Duration::from_secs(1));
    assert_eq!(
        extract_with_budget_and_capacity(&request, bound, &ACTIVE, 1),
        Err(TransportError::Rejected),
        "exhausted slots must reject before child launch",
    );
    assert_eq!(ACTIVE.load(Ordering::Acquire), 1);
    drop(held);
    assert_eq!(
        extract_with_budget_and_capacity(&request, bound, &ACTIVE, 1),
        Err(TransportError::Launch),
        "released slots must allow normal launch admission",
    );
    assert_eq!(ACTIVE.load(Ordering::Acquire), 0);
}

#[cfg(unix)]
#[test]
fn ternary_drain_lease_outlives_caller_until_pipe_eof() -> Result<(), String> {
    use std::os::unix::net::UnixStream;
    use std::sync::{Arc, mpsc};

    static ACTIVE: AtomicUsize = AtomicUsize::new(0);
    let (reader, writer) = UnixStream::pair()
        .map_err(|error| format!("create blocking pipe: {error}"))?;
    let held = Arc::new(
        TransportPipePermit::acquire(&ACTIVE, 1)
            .map_err(|_error| String::from("acquire reader slot"))?,
    );
    let (sender, receiver) = mpsc::channel();
    receive_pipe(reader, PipeKind::State, 32, PipeDelivery {
        permit: Arc::clone(&held),
        sender,
    })
    .map_err(|_error| String::from("spawn blocked reader"))?;
    drop(held);
    if ACTIVE.load(Ordering::Acquire) != 1
        || TransportPipePermit::acquire(&ACTIVE, 1).is_ok()
    {
        return Err(String::from("blocked reader lost its capacity slot"));
    }
    drop(writer);
    let event = receiver
        .recv_timeout(Duration::from_secs(2))
        .map_err(|error| format!("reader did not close: {error}"))?;
    let bytes = event
        .bytes
        .map_err(|error| format!("reader failed: {error}"))?;
    if !bytes.is_empty() {
        return Err(String::from("empty pipe yielded unexpected bytes"));
    }
    wait_for_drain_release(&ACTIVE, 100, "reader completion")
}

#[cfg(target_os = "linux")]
#[test]
fn escaped_ternary_child_keeps_slot_until_eof() -> Result<(), String> {
    static ACTIVE: AtomicUsize = AtomicUsize::new(0);
    let nonce = NEXT_ID.fetch_add(1, Ordering::Relaxed);
    let namespace = fixture_namespace();
    let script = temp_dir().join(format!(
        "malbolge-ternary-escaped-slot-{namespace}-{nonce}.py"
    ));
    let marker = temp_dir().join(format!(
        "malbolge-ternary-escaped-slot-{namespace}-{nonce}.ready"
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
    let request = RequestedInspector {
        codec: "malbolge-ternary-ir-v1",
        inspector: &script,
        interpreter: &interpreter(),
        sidecar: Path::new("unread-progress.json"),
    };
    let rejected = extract_with_budget_and_capacity(
        &request,
        budget(1024, 1024, Duration::from_millis(700)),
        &ACTIVE,
        1,
    );
    let launched = marker.exists();
    remove_file(&script).map_err(|error| format!("remove fixture: {error}"))?;
    if launched {
        remove_file(&marker)
            .map_err(|error| format!("remove marker: {error}"))?;
    }
    if !launched || rejected != Err(TransportError::Rejected) {
        return Err(format!("escaped child not exercised: {rejected:?}"));
    }
    if ACTIVE.load(Ordering::Acquire) != 1 {
        return Err(String::from("escaped child pipe lost reserved slot"));
    }
    let unavailable = extract_with_budget_and_capacity(
        &RequestedInspector {
            interpreter: Path::new("/missing-ternary-after-timeout"),
            ..request
        },
        budget(32, 32, Duration::from_secs(1)),
        &ACTIVE,
        1,
    );
    if unavailable != Err(TransportError::Rejected) {
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
