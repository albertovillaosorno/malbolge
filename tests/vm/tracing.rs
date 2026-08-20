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
//   - Deterministic trace-hook evidence for the safe Rust classic VM.
// - Must-Not:
//   - Treat trace formatting as semantics or depend on private VM internals.
// - Allows:
//   - Inputs: public traced execution APIs and interpreter fixtures.
//   - Outputs: exact assertions over observed state, I/O, and rejection
//   - records.
//   - Side effects: test-process memory only.
// - Split-When:
//   - Split when serialized trace formats require independent compatibility.
// - Merge-When:
//   - Merge when trace evidence becomes ordinary instruction conformance.
// - Summary:
//   - Verifies optional observation is complete and semantically inert.
// - Description:
//   - Exercises successful, terminating, and rejected traced transitions.
// - Usage:
//   - Composed by `tests/vm.rs` into the Cargo VM integration-test target.
// - Defaults:
//   - A traced run must produce the same guest result as an untraced run.
//

//! Trace-hook conformance for the classic VM.

use malbolge::{
    InterpreterUndefinedBehavior, Machine, MachineError, Memory, Registers,
    RunOutcome, StepOutcome, StepTrace, Termination, TraceInput, Word,
};

use super::{TestResult, check_equal, normalize_result};

const IO_ROUNDTRIP: &[u8] = include_bytes!(concat!(
    "../compatibility/specification/",
    "interpreter-io-roundtrip.malbolge",
));

fn check_halt_trace(trace: &StepTrace) -> TestResult {
    check_equal(&trace.decoded, &Some(b'v'), "third trace decodes halt")?;
    check_equal(
        &trace.result,
        &Ok(StepOutcome::Terminated(Termination::HaltInstruction)),
        "halt trace records termination",
    )?;
    check_equal(
        &trace.memory_delta.changed_cells(),
        &0usize,
        "halt trace changes no memory",
    )
}

fn check_input_trace(trace: &StepTrace) -> TestResult {
    check_equal(&trace.decoded, &Some(b'/'), "first trace decodes input")?;
    check_equal(
        &trace.input,
        &Some(TraceInput::Byte(0x41)),
        "first trace records consumed byte",
    )?;
    check_equal(&trace.output, &None, "input trace emits no byte")?;
    check_equal(
        &trace.before.input_consumed,
        &0usize,
        "input trace starts before consumption",
    )?;
    check_equal(
        &trace.after.input_consumed,
        &1usize,
        "input trace ends after consumption",
    )?;
    check_equal(
        &trace.after.registers.accumulator,
        &Word::from_byte(0x41),
        "input trace records accumulator result",
    )
}

fn check_output_trace(trace: &StepTrace) -> TestResult {
    check_equal(&trace.decoded, &Some(b'<'), "second trace decodes output")?;
    check_equal(&trace.output, &Some(0x41), "second trace records output")?;
    check_equal(
        &trace.after.output_len,
        &1usize,
        "output trace records stream growth",
    )
}

#[test]
fn traced_roundtrip_records_state_and_io_without_changing_semantics()
-> TestResult {
    let mut observed_machine =
        normalize_result(Machine::from_source(IO_ROUNDTRIP, vec![0x41]))?;
    let mut records = Vec::<StepTrace>::new();
    let outcome = normalize_result(
        observed_machine
            .run_traced(8, &mut |trace: &StepTrace| records.push(*trace)),
    )?;
    check_equal(
        &outcome,
        &RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 3,
        },
        "traced fixture terminates in three steps",
    )?;
    check_equal(
        &records.len(),
        &3usize,
        "one trace is emitted per requested step",
    )?;
    check_input_trace(
        records
            .first()
            .ok_or_else(|| String::from("missing input trace"))?,
    )?;
    check_output_trace(
        records
            .get(1)
            .ok_or_else(|| String::from("missing output trace"))?,
    )?;
    check_halt_trace(
        records
            .get(2)
            .ok_or_else(|| String::from("missing halt trace"))?,
    )?;

    let mut plain =
        normalize_result(Machine::from_source(IO_ROUNDTRIP, vec![0x41]))?;
    let plain_outcome = normalize_result(plain.run(8))?;
    check_equal(&outcome, &plain_outcome, "tracing preserves run outcome")?;
    check_equal(
        observed_machine.output(),
        plain.output(),
        "tracing preserves byte output",
    )?;
    check_equal(
        &observed_machine.registers(),
        &plain.registers(),
        "tracing preserves final registers",
    )
}

#[test]
fn rejected_transition_is_traced_without_partial_effects() -> TestResult {
    let mut memory = Memory::filled(Word::ZERO);
    normalize_result(memory.replace(Word::ZERO, Word::from_byte(b'b')))?;
    normalize_result(memory.replace(Word::from_byte(1), Word::from_byte(2)))?;
    let registers = Registers {
        accumulator: Word::from_byte(7),
        code_pointer: Word::ZERO,
        data_pointer: Word::from_byte(1),
    };
    let mut machine = Machine::with_registers(memory, vec![0x44], registers);
    let mut observed = None;
    let result = machine.step_traced(&mut |trace: &StepTrace| {
        observed = Some(*trace);
    });
    let expected = Err(MachineError::UnsupportedInterpreterBehavior(
        InterpreterUndefinedBehavior::InvalidSelfEncryptionTarget {
            pointer: Word::from_byte(2),
            value: Word::ZERO,
        },
    ));
    check_equal(&result, &expected, "jump rejection returns typed error")?;
    let trace =
        observed.ok_or_else(|| String::from("missing rejection trace"))?;
    check_equal(
        &trace.decoded,
        &Some(b'i'),
        "rejection trace records decoded jump",
    )?;
    check_equal(
        &trace.result,
        &expected,
        "rejection trace records exact error",
    )?;
    check_equal(
        &trace.after,
        &trace.before,
        "rejection trace is observationally atomic",
    )?;
    check_equal(&trace.input, &None, "rejected transition consumes no input")?;
    check_equal(
        &trace.memory_delta.changed_cells(),
        &0usize,
        "rejected transition changes no memory",
    )?;
    check_equal(&trace.output, &None, "rejected transition emits no output")?;
    check_equal(
        &normalize_result(machine.memory_word(Word::from_byte(2)))?,
        &Word::ZERO,
        "rejected transition commits no target-memory write",
    )
}

#[test]
fn non_graphical_non_progress_is_traced_without_decode() -> TestResult {
    let mut machine = Machine::new(Memory::filled(Word::ZERO), Vec::new());
    let mut observed = None;
    let outcome =
        normalize_result(machine.step_traced(&mut |trace: &StepTrace| {
            observed = Some(*trace);
        }))?;
    check_equal(
        &outcome,
        &StepOutcome::Continued,
        "non-graphical fetch remains a bounded non-progress step",
    )?;
    let trace =
        observed.ok_or_else(|| String::from("missing termination trace"))?;
    check_equal(
        &trace.fetched_cell,
        &Some(Word::ZERO),
        "trace records bad cell",
    )?;
    check_equal(&trace.decoded, &None, "non-graphical cell is never decoded")?;
    check_equal(
        &trace.after.termination,
        &None,
        "trace preserves live interpreter state",
    )
}
