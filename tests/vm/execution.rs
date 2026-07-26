// File:
//   - execution.rs
// Path:
//   - tests/vm/execution.rs
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
//   - Bounded execution and resumption evidence for the classic Rust VM.
// - Must-Not:
//   - Introduce host-time deadlines or hide unbounded execution loops.
// - Allows:
//   - Inputs: public VM execution budgets and deterministic fixture streams.
//   - Outputs: exact budget, termination, resumption, and state assertions.
//   - Side effects: test-process memory only.
// - Split-When:
//   - Split when scheduling or cycle detection needs independent ownership.
// - Merge-When:
//   - Merge when bounded execution becomes trivial instruction conformance.
// - Summary:
//   - Verifies deterministic step-budget execution and stable termination.
// - Description:
//   - Exercises `Machine::run` across budget exhaustion and resumed execution.
// - Usage:
//   - Composed by `tests/vm.rs` into the Cargo VM integration-test target.
// - Defaults:
//   - Budgets count semantic step requests, including a terminating step.
//
// Related documents:
// - docs/technical/runtime/vm/safe-rust-malbolge-vm.md
// - docs/technical/specification/malbolge-1998.md
//
// Large file:
//   - false
//

//! Bounded execution conformance for the classic VM.

use malbolge::{Machine, RunOutcome, Termination};

use super::{TestResult, check_equal, normalize_result};

const IO_ROUNDTRIP: &[u8] =
    include_bytes!("../compatibility/specification/spec-io-roundtrip.malbolge");

#[test]
fn bounded_run_exhaustion_can_resume_to_termination() -> TestResult {
    let mut machine =
        normalize_result(Machine::from_source(IO_ROUNDTRIP, vec![0x41]))?;
    let before = machine.registers();
    check_equal(
        &normalize_result(machine.run(0))?,
        &RunOutcome::BudgetExhausted { steps: 0 },
        "zero budget executes no steps",
    )?;
    check_equal(
        &machine.registers(),
        &before,
        "zero budget preserves registers",
    )?;
    check_equal(
        &normalize_result(machine.run(2))?,
        &RunOutcome::BudgetExhausted { steps: 2 },
        "two-step budget stops before halt",
    )?;
    check_equal(
        machine.output(),
        &[0x41],
        "budgeted execution preserves output effects",
    )?;
    check_equal(
        &machine.termination(),
        &None,
        "budget exhaustion is not termination",
    )?;
    check_equal(
        &normalize_result(machine.run(1))?,
        &RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 1,
        },
        "resumed execution reaches halt",
    )
}

#[test]
fn terminated_run_reports_zero_additional_steps() -> TestResult {
    let mut machine =
        normalize_result(Machine::from_source(IO_ROUNDTRIP, Vec::new()))?;
    check_equal(
        &normalize_result(machine.run(3))?,
        &RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 3,
        },
        "initial run reaches halt in three semantic steps",
    )?;
    let before = machine.registers();
    check_equal(
        &normalize_result(machine.run(100))?,
        &RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 0,
        },
        "already terminated run executes no additional steps",
    )?;
    check_equal(
        &machine.registers(),
        &before,
        "already terminated run preserves registers",
    )
}
