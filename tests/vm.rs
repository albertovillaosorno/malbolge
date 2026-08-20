// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Cargo composition and shared resource guards for VM integration tests.
// - Must-Not:
//   - Contain VM behavior assertions or duplicate conformance fixtures.
// - Allows:
//   - Inputs: package-local VM test modules.
//   - Outputs: one Cargo-discoverable VM integration-test target.
//   - Side effects: module composition and process-local test synchronization.
// - Split-When:
//   - Split when another test responsibility requires its own Cargo target.
// - Merge-When:
//   - Merge when VM conformance no longer needs nested test organization.
// - Summary:
//   - Cargo composition root plus shared test-resource synchronization.
// - Description:
//   - Keeps Cargo discovery and cross-module resource guards outside VM
//     behavior.
// - Usage:
//   - Auto-discovered by Cargo and delegates executable tests to `tests/vm/`.
// - Defaults:
//   - Contains no VM behavior assertions; CUDA tests share one process mutex.
//

//! Cargo composition root for VM integration tests.

#[path = "vm/annotated.rs"]
mod annotated;
#[path = "vm/batch.rs"]
mod batch;
#[path = "vm/batch_backend.rs"]
mod batch_backend;
#[path = "vm/capsule.rs"]
mod capsule;
#[path = "vm/conformance.rs"]
mod conformance;
#[path = "vm/cuda_profile_run.rs"]
mod cuda_profile_run;
#[path = "vm/cuda_run.rs"]
mod cuda_run;
#[path = "vm/cuda_step.rs"]
mod cuda_step;
#[path = "vm/cycle_detection.rs"]
mod cycle_detection;
#[path = "vm/differential.rs"]
mod differential;
#[path = "vm/execution.rs"]
mod execution;
#[path = "vm/host_capability.rs"]
mod host_capability;
#[path = "vm/host_capability_dispatch.rs"]
mod host_capability_dispatch;
#[path = "vm/host_capability_mouse.rs"]
mod host_capability_mouse;
#[path = "vm/host_capability_telemetry.rs"]
mod host_capability_telemetry;
#[path = "vm/host_capability_time.rs"]
mod host_capability_time;
#[path = "vm/host_capability_time_transport.rs"]
mod host_capability_time_transport;
#[path = "vm/instructions.rs"]
mod instructions;
#[path = "vm/logical.rs"]
mod logical;
#[path = "vm/modes.rs"]
mod modes;
#[path = "vm/profile_batch.rs"]
mod profile_batch;
#[path = "vm/profile_logical.rs"]
mod profile_logical;
#[path = "vm/profile_machine.rs"]
mod profile_machine;
#[path = "vm/profile_reads.rs"]
mod profile_reads;
#[path = "vm/profile_requirements.rs"]
mod profile_requirements;
#[path = "vm/profile_state.rs"]
mod profile_state;
#[path = "vm/profile_tracing.rs"]
mod profile_tracing;
#[path = "vm/tables.rs"]
mod tables;
#[path = "vm/tracing.rs"]
mod tracing;

use std::env::join_paths;
use std::ffi::OsString;
use std::fmt::{Debug, Display};
use std::path::{Path, PathBuf};
use std::sync::{Mutex, MutexGuard};

static CUDA_TEST_MUTEX: Mutex<()> = Mutex::new(());

type TestResult<Value = ()> = Result<Value, String>;

fn cuda_test_guard() -> TestResult<MutexGuard<'static, ()>> {
    CUDA_TEST_MUTEX
        .lock()
        .map_err(|error| format!("CUDA test serialization poisoned: {error}"))
}

fn validation_python(root: &Path) -> PathBuf {
    if cfg!(windows) {
        root.join(".dependencies/python/3.14.6/Scripts/python-jig.cmd")
    } else {
        root.join(".dependencies/python/3.14.6/bin/python-jig")
    }
}

fn accelerator_python_path(root: &Path) -> TestResult<OsString> {
    join_paths([
        root.join("src/optimization/accelerator/application"),
        root.join("src/optimization/accelerator/adapter-outbound"),
    ])
    .map_err(|error| format!("accelerator PYTHONPATH construction: {error}"))
}

fn check_equal<Value>(
    actual: &Value,
    expected: &Value,
    context: &str,
) -> TestResult
where
    Value: Debug + PartialEq + ?Sized,
{
    if actual == expected {
        Ok(())
    } else {
        Err(format!(
            "{context}: expected {expected:?}, observed {actual:?}"
        ))
    }
}

fn normalize_result<Value, Failure>(
    result: Result<Value, Failure>,
) -> TestResult<Value>
where
    Failure: Display,
{
    result.map_err(|failure| format!("{failure}"))
}
