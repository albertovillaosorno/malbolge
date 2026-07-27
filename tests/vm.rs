// File:
//   - vm.rs
// Path:
//   - tests/vm.rs
//
// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE
// Path-Rule:
//   - All paths in this header are repository-root relative.
//
// Boundary-Contract:
// - Owns:
//   - Cargo composition for VM integration-test modules.
// - Must-Not:
//   - Contain VM behavior assertions or duplicate conformance fixtures.
// - Allows:
//   - Inputs: package-local VM test modules.
//   - Outputs: one Cargo-discoverable VM integration-test target.
//   - Side effects: test module composition only.
// - Split-When:
//   - Split when another test responsibility requires its own Cargo target.
// - Merge-When:
//   - Merge when VM conformance no longer needs nested test organization.
// - Summary:
//   - Thin Cargo composition root for VM integration tests.
// - Description:
//   - Keeps Cargo target discovery separate from responsibility-oriented tests.
// - Usage:
//   - Auto-discovered by Cargo and delegates executable tests to `tests/vm/`.
// - Defaults:
//   - Contains no executable test logic of its own.
//
// Related documents:
// - docs/technical/runtime/vm/safe-rust-malbolge-vm.md
// - tests/README.md
//
// Large file:
//   - false
//

//! Cargo composition root for VM integration tests.

#[path = "vm/batch.rs"]
mod batch;
#[path = "vm/capsule.rs"]
mod capsule;
#[path = "vm/conformance.rs"]
mod conformance;
#[path = "vm/differential.rs"]
mod differential;
#[path = "vm/execution.rs"]
mod execution;
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

use std::fmt::{Debug, Display};

type TestResult<Value = ()> = Result<Value, String>;

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
