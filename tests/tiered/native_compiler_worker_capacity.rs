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
//   - Native compiler worker-group quota and escaped reader regression tests.
// - Must-Not:
//   - Replace production compiler admission or mock process group semantics.
// - Allows:
//   - Inputs: bounded worker permits, child stdio pipes, and deadline budgets.
//   - Outputs: rejection, deadline, and retained-capacity test outcomes.
//   - Side effects: one short-lived escaped child in the Linux host test.
// - Split-When:
//   - Compiler resource management has independent platform implementations.
// - Merge-When:
//   - Shared native process session tests adopt the compiler worker boundary.
// - Summary:
//   - Guards process-wide compiler worker capacity across detached readers.
// - Description:
//   - Covers saturation, retained ownership, and eventual quota recovery.
// - Usage:
//   - Included by the native compiler adapter for Rust test builds only.
// - Defaults:
//   - Does not compile in production.
//

//! Compiler worker-group quota and detached pipe reader regression tests.

use std::process::{Command, Stdio};
use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::thread;
use std::time::{Duration, Instant};

use super::{
    BootstrapCompilerError, CompilerWorkerPermit,
    MAX_BOOTSTRAP_COMPILER_WORKER_GROUPS, collect_compiler_output,
};

#[test]
fn compiler_worker_permits_reject_over_capacity_and_release_once()
-> Result<(), String> {
    let counter = AtomicUsize::new(0);
    let mut permits = Vec::new();
    for _ in 0..MAX_BOOTSTRAP_COMPILER_WORKER_GROUPS {
        permits.push(
            CompilerWorkerPermit::acquire(
                &counter,
                MAX_BOOTSTRAP_COMPILER_WORKER_GROUPS,
            )
            .map_err(|error| error.to_string())?,
        );
    }
    let exhausted = CompilerWorkerPermit::acquire(
        &counter,
        MAX_BOOTSTRAP_COMPILER_WORKER_GROUPS,
    )
    .err();
    if exhausted
        != Some(BootstrapCompilerError::WorkerCapacityExceeded {
            maximum: MAX_BOOTSTRAP_COMPILER_WORKER_GROUPS,
        })
    {
        return Err(format!("worker exhaustion drifted: {exhausted:?}"));
    }
    if counter.load(Ordering::Acquire) != MAX_BOOTSTRAP_COMPILER_WORKER_GROUPS {
        return Err(String::from("worker limit was oversubscribed"));
    }
    drop(permits);
    if counter.load(Ordering::Acquire) != 0 {
        return Err(String::from("released workers retained capacity"));
    }
    let _reused = CompilerWorkerPermit::acquire(&counter, 1)
        .map_err(|error| error.to_string())?;
    Ok(())
}

#[test]
fn compiler_worker_permit_remains_owned_by_last_detached_reader()
-> Result<(), String> {
    let counter = AtomicUsize::new(0);
    let permit = Arc::new(
        CompilerWorkerPermit::acquire(&counter, 1)
            .map_err(|error| error.to_string())?,
    );
    let input = Arc::clone(&permit);
    let output = Arc::clone(&permit);
    let diagnostic = Arc::clone(&permit);
    drop(permit);
    drop(input);
    drop(output);
    if CompilerWorkerPermit::acquire(&counter, 1).err()
        != Some(BootstrapCompilerError::WorkerCapacityExceeded { maximum: 1 })
    {
        return Err(String::from("last detached reader lost its permit"));
    }
    drop(diagnostic);
    if counter.load(Ordering::Acquire) != 0 {
        return Err(String::from("last reader did not restore capacity"));
    }
    let _reacquired = CompilerWorkerPermit::acquire(&counter, 1)
        .map_err(|error| error.to_string())?;
    Ok(())
}

#[cfg(target_os = "linux")]
#[test]
fn escaped_compiler_pipe_reader_retains_capacity_after_deadline()
-> Result<(), String> {
    use std::os::unix::process::CommandExt as _;

    static COUNTER: AtomicUsize = AtomicUsize::new(0);
    let permit = Arc::new(
        CompilerWorkerPermit::acquire(&COUNTER, 1)
            .map_err(|error| error.to_string())?,
    );
    let mut command = Command::new("/bin/sh");
    let _configured = command
        .args(["-c", "/usr/bin/setsid /usr/bin/sleep 2 & exit 0"])
        .process_group(0)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    let child = command.spawn().map_err(|error| error.to_string())?;
    let result =
        collect_compiler_output(child, "", Duration::from_millis(80), permit);
    if !matches!(result, Err(BootstrapCompilerError::DeadlineExceeded { .. })) {
        return Err(format!("escaped compiler bypassed deadline: {result:?}"));
    }
    if CompilerWorkerPermit::acquire(&COUNTER, 1).err()
        != Some(BootstrapCompilerError::WorkerCapacityExceeded { maximum: 1 })
    {
        return Err(String::from("escaped reader lost its worker permit"));
    }
    let started = Instant::now();
    while COUNTER.load(Ordering::Acquire) != 0
        && started.elapsed() < Duration::from_secs(5)
    {
        thread::sleep(Duration::from_millis(10));
    }
    if COUNTER.load(Ordering::Acquire) != 0 {
        return Err(String::from("escaped reader never released capacity"));
    }
    let _reacquired = CompilerWorkerPermit::acquire(&COUNTER, 1)
        .map_err(|error| error.to_string())?;
    Ok(())
}
