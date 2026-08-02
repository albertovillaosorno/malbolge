// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Conformance evidence for explicit specification and legacy-ben modes.
// - Must-Not:
//   - Treat historical behavior as verifier-eligible normative semantics.
// - Allows:
//   - Inputs: public execution-mode facade and discrepancy fixtures.
//   - Outputs: exact assertions over mode identity, I/O, traces, and failures.
//   - Side effects: test-process memory only.
// - Split-When:
//   - Split when another compatibility profile needs independent evidence.
// - Merge-When:
//   - Merge when execution modes become ordinary normative VM behavior.
// - Summary:
//   - Verifies explicit mode selection and bounded historical compatibility.
// - Description:
//   - Covers H-001, H-002, H-003, and H-004 without invoking historical UB.
// - Usage:
//   - Composed by `tests/vm.rs`; legacy fixtures require `legacy-ben` feature.
// - Defaults:
//   - Normal builds reject legacy-ben construction explicitly.
//

//! Execution-mode conformance and historical discrepancy fixtures.

use malbolge::{
    ExecutionErrorKind, ExecutionMachine, ExecutionMode, RunOutcome, StepTrace,
    Termination,
};
#[cfg(feature = "legacy-ben")]
use malbolge::{
    LegacyBehavior, LoadError, MachineError, Memory, Registers, StepOutcome,
    TraceInput, Word,
};

use super::{TestResult, check_equal, normalize_result};

const IO_ROUNDTRIP: &[u8] =
    include_bytes!("../compatibility/specification/spec-io-roundtrip.malbolge");

#[cfg(feature = "legacy-ben")]
fn legacy_machine_for_invalid_jump() -> TestResult<ExecutionMachine> {
    let mut memory = Memory::filled(Word::ZERO);
    normalize_result(memory.replace(Word::ZERO, Word::from_byte(b'b')))?;
    normalize_result(memory.replace(Word::from_byte(1), Word::from_byte(2)))?;
    let registers = Registers {
        accumulator: Word::from_byte(7),
        code_pointer: Word::ZERO,
        data_pointer: Word::from_byte(1),
    };
    normalize_result(ExecutionMachine::from_state(
        memory,
        vec![0x44],
        registers,
        ExecutionMode::LegacyBen,
    ))
}

#[cfg(not(feature = "legacy-ben"))]
#[test]
fn legacy_mode_is_disabled_without_feature() -> TestResult {
    let Err(error) = ExecutionMachine::from_source(
        IO_ROUNDTRIP,
        vec![0x41],
        ExecutionMode::LegacyBen,
    ) else {
        return Err(String::from("legacy-ben unexpectedly enabled"));
    };
    check_equal(
        &error.mode(),
        &ExecutionMode::LegacyBen,
        "disabled diagnostic keeps requested mode",
    )?;
    check_equal(
        &error.kind(),
        &ExecutionErrorKind::LegacyBenDisabled,
        "default build rejects legacy mode explicitly",
    )
}

#[cfg(feature = "legacy-ben")]
#[test]
fn legacy_mode_models_reversed_io_with_mode_tagged_trace() -> TestResult {
    let mut machine = normalize_result(ExecutionMachine::from_source(
        IO_ROUNDTRIP,
        vec![0x41],
        ExecutionMode::LegacyBen,
    ))?;
    let mut traces = Vec::<StepTrace>::new();
    let outcome = normalize_result(
        machine.run_traced(8, &mut |trace: &StepTrace| traces.push(*trace)),
    )?;
    check_equal(
        &outcome,
        &RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 3,
        },
        "legacy roundtrip halts after three requests",
    )?;
    check_equal(machine.output(), &[0x00], "legacy < emits initial A")?;
    check_equal(
        &machine.input_consumed(),
        &1usize,
        "legacy / consumes input",
    )?;
    check_equal(
        &machine.registers().accumulator,
        &Word::from_byte(0x41),
        "legacy input leaves byte in accumulator",
    )?;
    let first = traces
        .first()
        .copied()
        .ok_or_else(|| String::from("missing first legacy trace"))?;
    check_equal(
        &first.mode,
        &ExecutionMode::LegacyBen,
        "trace mode identity",
    )?;
    check_equal(&first.decoded, &Some(b'<'), "legacy trace keeps raw decode")?;
    check_equal(&first.input, &None, "legacy < performs no input")?;
    check_equal(&first.output, &Some(0x00), "legacy < records output")?;
    let second = traces
        .get(1)
        .copied()
        .ok_or_else(|| String::from("missing second legacy trace"))?;
    check_equal(&second.decoded, &Some(b'/'), "legacy / raw decode")?;
    check_equal(
        &second.input,
        &Some(TraceInput::Byte(0x41)),
        "legacy / records consumed input",
    )?;
    check_equal(&second.output, &None, "legacy / emits no output")
}

#[cfg(feature = "legacy-ben")]
#[test]
fn legacy_non_graphical_cell_is_bounded_non_progress() -> TestResult {
    let registers = Registers::default();
    let mut machine = normalize_result(ExecutionMachine::from_state(
        Memory::filled(Word::ZERO),
        Vec::new(),
        registers,
        ExecutionMode::LegacyBen,
    ))?;
    let mut traces = Vec::<StepTrace>::new();
    let outcome = normalize_result(
        machine.run_traced(3, &mut |trace: &StepTrace| traces.push(*trace)),
    )?;
    check_equal(
        &outcome,
        &RunOutcome::BudgetExhausted { steps: 3 },
        "legacy non-graphical state uses bounded non-progress",
    )?;
    check_equal(
        &machine.registers(),
        &registers,
        "legacy state does not move",
    )?;
    check_equal(
        &machine.termination(),
        &None,
        "legacy state does not terminate",
    )?;
    check_equal(&traces.len(), &3usize, "one trace per bounded request")?;
    for trace in traces {
        check_equal(&trace.mode, &ExecutionMode::LegacyBen, "trace mode")?;
        check_equal(&trace.fetched_cell, &Some(Word::ZERO), "legacy bad cell")?;
        check_equal(&trace.decoded, &None, "bad cell remains undecoded")?;
        check_equal(
            &trace.before,
            &trace.after,
            "legacy request makes no progress",
        )?;
        check_equal(
            &trace.result,
            &Ok(StepOutcome::Continued),
            "bounded loop step",
        )?;
    }
    Ok(())
}

#[cfg(feature = "legacy-ben")]
#[test]
fn legacy_source_boundary_rejects_undefined_loader_case() -> TestResult {
    let Err(error) = ExecutionMachine::from_source(
        b"D",
        Vec::new(),
        ExecutionMode::LegacyBen,
    ) else {
        return Err(String::from("legacy loader reproduced H-003"));
    };
    check_equal(
        &error.mode(),
        &ExecutionMode::LegacyBen,
        "loader mode identity",
    )?;
    check_equal(
        &error.kind(),
        &ExecutionErrorKind::Load(LoadError::InsufficientRecurrenceBase),
        "legacy loader rejects H-003 instead of invoking UB",
    )
}

#[cfg(feature = "legacy-ben")]
#[test]
fn legacy_unsafe_self_encryption_fails_explicitly() -> TestResult {
    let mut machine = legacy_machine_for_invalid_jump()?;
    let mut observed = None;
    let Err(error) =
        machine.step_traced(&mut |trace: &StepTrace| observed = Some(*trace))
    else {
        return Err(String::from("legacy H-004 unexpectedly committed"));
    };
    let behavior = LegacyBehavior::InvalidSelfEncryptionTarget {
        pointer: Word::from_byte(2),
        value: Word::ZERO,
    };
    check_equal(
        &error.mode(),
        &ExecutionMode::LegacyBen,
        "failure mode identity",
    )?;
    check_equal(
        &error.kind(),
        &ExecutionErrorKind::Machine(MachineError::UnsupportedLegacyBehavior(
            behavior,
        )),
        "unsafe historical behavior has explicit diagnostic",
    )?;
    let trace = observed
        .ok_or_else(|| String::from("missing legacy rejection trace"))?;
    check_equal(
        &trace.mode,
        &ExecutionMode::LegacyBen,
        "rejection trace mode",
    )?;
    check_equal(
        &trace.result,
        &Err(MachineError::UnsupportedLegacyBehavior(behavior)),
        "trace records unsupported historical behavior",
    )?;
    check_equal(
        &trace.before,
        &trace.after,
        "legacy rejection remains atomic",
    )
}

#[test]
fn mode_identity_is_stable_and_verifier_gated() -> TestResult {
    let specification =
        normalize_result("specification".parse::<ExecutionMode>())?;
    let legacy = normalize_result("legacy-ben".parse::<ExecutionMode>())?;
    check_equal(
        &specification,
        &ExecutionMode::Specification,
        "parse normative mode",
    )?;
    check_equal(&legacy, &ExecutionMode::LegacyBen, "parse legacy mode")?;
    check_equal(
        &specification.stable_id(),
        &"specification",
        "normative stable identity",
    )?;
    check_equal(&legacy.stable_id(), &"legacy-ben", "legacy stable identity")?;
    check_equal(
        &specification.is_verifier_eligible(),
        &true,
        "normative mode is verifier eligible",
    )?;
    check_equal(
        &legacy.is_verifier_eligible(),
        &false,
        "legacy mode is never verifier eligible",
    )?;
    let Err(parse_error) = "historical-auto".parse::<ExecutionMode>() else {
        return Err(String::from("unknown mode fell back implicitly"));
    };
    check_equal(
        &parse_error.requested(),
        &"historical-auto",
        "unknown mode diagnostic preserves request",
    )
}

#[test]
fn specification_facade_preserves_normative_roundtrip() -> TestResult {
    let mut machine = normalize_result(ExecutionMachine::from_source(
        IO_ROUNDTRIP,
        vec![0x41],
        ExecutionMode::Specification,
    ))?;
    let mut traces = Vec::<StepTrace>::new();
    let outcome = normalize_result(
        machine.run_traced(8, &mut |trace: &StepTrace| traces.push(*trace)),
    )?;
    check_equal(
        &outcome,
        &RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 3,
        },
        "specification facade keeps normative halt",
    )?;
    check_equal(
        machine.output(),
        &[0x41],
        "specification facade byte output",
    )?;
    check_equal(
        &machine.verifier_eligible(),
        &true,
        "specification facade remains verifier eligible",
    )?;
    for trace in traces {
        check_equal(
            &trace.mode,
            &ExecutionMode::Specification,
            "normative trace mode identity",
        )?;
    }
    Ok(())
}
