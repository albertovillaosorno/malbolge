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
//   - Conformance evidence for interpreter authority and specification mode.
// - Must-Not:
//   - Treat specification comparison as verifier-eligible normal semantics.
// - Allows:
//   - Inputs: public execution-mode facade and discrepancy fixtures.
//   - Outputs: exact assertions over mode identity, I/O, traces, and failures.
//   - Side effects: test-process memory only.
// - Split-When:
//   - Split when another compatibility profile needs independent evidence.
// - Merge-When:
//   - Merge when execution modes become ordinary normative VM behavior.
// - Summary:
//   - Verifies explicit mode selection and bounded interpreter authority.
// - Description:
//   - Covers H-001, H-002, H-003, and H-004 without invoking historical UB.
// - Usage:
//   - Composed by `tests/vm.rs` in every build.
// - Defaults:
//   - Normal classic execution uses interpreter authority.
//

//! Interpreter-authority and specification comparison fixtures.

use malbolge::{
    ExecutionErrorKind, ExecutionMachine, ExecutionMode,
    InterpreterUndefinedBehavior, LoadError, MachineError, Memory, Registers,
    RunOutcome, StepOutcome, StepTrace, Termination, TraceInput, Word,
};

use super::{TestResult, check_equal, normalize_result};

const IO_ROUNDTRIP: &[u8] =
    include_bytes!("../compatibility/specification/spec-io-roundtrip.malbolge");

fn interpreter_machine_for_invalid_jump() -> TestResult<ExecutionMachine> {
    let mut memory = Memory::filled(Word::ZERO);
    normalize_result(memory.replace(Word::ZERO, Word::from_byte(b'b')))?;
    normalize_result(memory.replace(Word::from_byte(1), Word::from_byte(2)))?;
    let registers = Registers {
        accumulator: Word::from_byte(7),
        code_pointer: Word::ZERO,
        data_pointer: Word::from_byte(1),
    };
    Ok(ExecutionMachine::from_state(
        memory,
        vec![0x44],
        registers,
        ExecutionMode::Interpreter,
    ))
}

#[test]
fn interpreter_mode_models_original_io_with_mode_tagged_trace() -> TestResult {
    let mut machine = normalize_result(ExecutionMachine::from_source(
        IO_ROUNDTRIP,
        vec![0x41],
        ExecutionMode::Interpreter,
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
        "interpreter roundtrip halts after three requests",
    )?;
    check_equal(machine.output(), &[0x00], "interpreter < emits initial A")?;
    check_equal(
        &machine.input_consumed(),
        &1usize,
        "interpreter / consumes input",
    )?;
    check_equal(
        &machine.registers().accumulator,
        &Word::from_byte(0x41),
        "interpreter input leaves byte in accumulator",
    )?;
    let first = traces
        .first()
        .copied()
        .ok_or_else(|| String::from("missing first interpreter trace"))?;
    check_equal(
        &first.mode,
        &ExecutionMode::Interpreter,
        "trace mode identity",
    )?;
    check_equal(
        &first.decoded,
        &Some(b'<'),
        "interpreter trace keeps raw decode",
    )?;
    check_equal(&first.input, &None, "interpreter < performs no input")?;
    check_equal(&first.output, &Some(0x00), "interpreter < records output")?;
    let second = traces
        .get(1)
        .copied()
        .ok_or_else(|| String::from("missing second interpreter trace"))?;
    check_equal(&second.decoded, &Some(b'/'), "interpreter / raw decode")?;
    check_equal(
        &second.input,
        &Some(TraceInput::Byte(0x41)),
        "interpreter / records consumed input",
    )?;
    check_equal(&second.output, &None, "interpreter / emits no output")
}

#[test]
fn interpreter_non_graphical_cell_is_bounded_non_progress() -> TestResult {
    let registers = Registers::default();
    let mut machine = ExecutionMachine::from_state(
        Memory::filled(Word::ZERO),
        Vec::new(),
        registers,
        ExecutionMode::Interpreter,
    );
    let mut traces = Vec::<StepTrace>::new();
    let outcome = normalize_result(
        machine.run_traced(3, &mut |trace: &StepTrace| traces.push(*trace)),
    )?;
    check_equal(
        &outcome,
        &RunOutcome::BudgetExhausted { steps: 3 },
        "interpreter non-graphical state uses bounded non-progress",
    )?;
    check_equal(
        &machine.registers(),
        &registers,
        "interpreter state does not move",
    )?;
    check_equal(
        &machine.termination(),
        &None,
        "interpreter state does not terminate",
    )?;
    check_equal(&traces.len(), &3usize, "one trace per bounded request")?;
    for trace in traces {
        check_equal(&trace.mode, &ExecutionMode::Interpreter, "trace mode")?;
        check_equal(
            &trace.fetched_cell,
            &Some(Word::ZERO),
            "interpreter bad cell",
        )?;
        check_equal(&trace.decoded, &None, "bad cell remains undecoded")?;
        check_equal(
            &trace.before,
            &trace.after,
            "interpreter request makes no progress",
        )?;
        check_equal(
            &trace.result,
            &Ok(StepOutcome::Continued),
            "bounded loop step",
        )?;
    }
    Ok(())
}

#[test]
fn interpreter_source_boundary_rejects_undefined_loader_case() -> TestResult {
    let Err(error) = ExecutionMachine::from_source(
        b"D",
        Vec::new(),
        ExecutionMode::Interpreter,
    ) else {
        return Err(String::from("interpreter loader reproduced H-003"));
    };
    check_equal(
        &error.mode(),
        &ExecutionMode::Interpreter,
        "loader mode identity",
    )?;
    check_equal(
        &error.kind(),
        &ExecutionErrorKind::Load(LoadError::InsufficientRecurrenceBase),
        "interpreter loader rejects H-003 instead of invoking UB",
    )
}

#[test]
fn interpreter_unsafe_self_encryption_fails_explicitly() -> TestResult {
    let mut machine = interpreter_machine_for_invalid_jump()?;
    let mut observed = None;
    let Err(error) =
        machine.step_traced(&mut |trace: &StepTrace| observed = Some(*trace))
    else {
        return Err(String::from("interpreter H-004 unexpectedly committed"));
    };
    let behavior = InterpreterUndefinedBehavior::InvalidSelfEncryptionTarget {
        pointer: Word::from_byte(2),
        value: Word::ZERO,
    };
    check_equal(
        &error.mode(),
        &ExecutionMode::Interpreter,
        "failure mode identity",
    )?;
    check_equal(
        &error.kind(),
        &ExecutionErrorKind::Machine(
            MachineError::UnsupportedInterpreterBehavior(behavior),
        ),
        "unsafe historical behavior has explicit diagnostic",
    )?;
    let trace = observed
        .ok_or_else(|| String::from("missing interpreter rejection trace"))?;
    check_equal(
        &trace.mode,
        &ExecutionMode::Interpreter,
        "rejection trace mode",
    )?;
    check_equal(
        &trace.result,
        &Err(MachineError::UnsupportedInterpreterBehavior(behavior)),
        "trace records unsupported historical behavior",
    )?;
    check_equal(
        &trace.before,
        &trace.after,
        "interpreter rejection remains atomic",
    )
}

#[test]
fn mode_identity_is_stable_and_verifier_gated() -> TestResult {
    let specification =
        normalize_result("specification".parse::<ExecutionMode>())?;
    let interpreter = normalize_result("interpreter".parse::<ExecutionMode>())?;
    let legacy_alias = normalize_result("legacy-ben".parse::<ExecutionMode>())?;
    check_equal(
        &specification,
        &ExecutionMode::Specification,
        "parse specification mode",
    )?;
    check_equal(
        &interpreter,
        &ExecutionMode::Interpreter,
        "parse interpreter mode",
    )?;
    check_equal(
        &legacy_alias,
        &ExecutionMode::Interpreter,
        "legacy parser alias",
    )?;
    check_equal(
        &specification.stable_id(),
        &"specification",
        "specification stable identity",
    )?;
    check_equal(
        &interpreter.stable_id(),
        &"interpreter",
        "interpreter stable identity",
    )?;
    check_equal(
        &specification.is_verifier_eligible(),
        &false,
        "specification comparison is not verifier eligible",
    )?;
    check_equal(
        &interpreter.is_verifier_eligible(),
        &true,
        "interpreter mode is verifier eligible",
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
fn specification_facade_preserves_documented_roundtrip() -> TestResult {
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
        "specification comparison keeps documented halt",
    )?;
    check_equal(
        machine.output(),
        &[0x41],
        "specification facade byte output",
    )?;
    check_equal(
        &machine.verifier_eligible(),
        &false,
        "specification facade remains comparison-only",
    )?;
    for trace in traces {
        check_equal(
            &trace.mode,
            &ExecutionMode::Specification,
            "specification trace mode identity",
        )?;
    }
    Ok(())
}
