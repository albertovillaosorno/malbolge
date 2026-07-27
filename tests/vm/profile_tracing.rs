// File:
//   - profile_tracing.rs
// Path:
//   - tests/vm/profile_tracing.rs
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
//   - Trace inertness, profile identity, current EOF, and rejection atomicity
//     tests.
// - Must-Not:
//   - Treat trace formatting as semantics or inject private machine state.
// - Allows:
//   - Inputs: public profile-driven traced APIs and valid source fixtures.
//   - Outputs: exact observations over state, I/O, profile, and typed
//     rejection.
//   - Side effects: test-process memory only.
// - Split-When:
//   - Split when serialized profile traces gain compatibility fixtures.
// - Merge-When:
//   - Merge when classic/profile trace evidence shares one width-safe suite.
// - Summary:
//   - Proves current-profile tracing is complete, atomic, and observational
//     only.
// - Description:
//   - Exercises current EOF/output/halt and a real recurrence jump rejection.
// - Usage:
//   - Composed by `tests/vm.rs` under the normal Cargo integration test target.
// - Defaults:
//   - Traced and plain current execution must produce identical guest state.
//
// Related documents:
// - docs/technical/runtime/vm/safe-rust-malbolge-vm.md
// - docs/technical/compatibility/scalable-malbolge-memory-model.md
//
// Large file:
//   - false

//! Profile-driven trace conformance for current scalable Malbolge.

use malbolge::{
    ProfileMachine, ProfileMachineError, ProfileStepTrace, RunOutcome,
    StepOutcome, Termination, TraceInput, current_profile,
};

use super::{TestResult, check_equal, normalize_result};

const CURRENT_EOF_LOW_BYTE: u8 = 0x78;
const IO_ROUNDTRIP: &[u8] =
    include_bytes!("../compatibility/specification/spec-io-roundtrip.malbolge");
const REJECTING_JUMP_SOURCE: &[u8] = b"b'";
const REJECTING_POINTER: u32 = 98;

fn check_halt_trace(trace: &ProfileStepTrace) -> TestResult {
    check_equal(&trace.decoded, &Some(b'v'), "profile halt decode")?;
    check_equal(
        &trace.result,
        &Ok(StepOutcome::Terminated(Termination::HaltInstruction)),
        "profile halt result",
    )?;
    check_equal(
        &trace.memory_delta.changed_cells(),
        &0usize,
        "profile halt changes no memory",
    )?;
    check_equal(
        &trace.profile.id(),
        &current_profile().id(),
        "profile halt identity",
    )
}

fn check_input_eof_trace(trace: &ProfileStepTrace) -> TestResult {
    check_equal(&trace.decoded, &Some(b'<'), "profile input decode")?;
    check_equal(
        &trace.input,
        &Some(TraceInput::EndOfInput),
        "current EOF trace effect",
    )?;
    check_equal(
        &trace.after.registers.accumulator,
        &current_profile().eof_word(),
        "current EOF accumulator",
    )?;
    check_equal(
        &trace.after.input_consumed,
        &0usize,
        "EOF consumes no input byte",
    )?;
    check_equal(
        &trace.profile.fingerprint(),
        &current_profile().fingerprint(),
        "current trace fingerprint",
    )
}

fn check_output_trace(trace: &ProfileStepTrace) -> TestResult {
    check_equal(&trace.decoded, &Some(b'/'), "profile output decode")?;
    check_equal(
        &trace.output,
        &Some(CURRENT_EOF_LOW_BYTE),
        "current EOF low-byte output",
    )?;
    check_equal(
        &trace.after.output_len,
        &1usize,
        "profile output stream growth",
    )
}

fn check_current_trace_inertness(
    traced: &ProfileMachine,
    traced_outcome: RunOutcome,
) -> TestResult {
    let mut plain = normalize_result(ProfileMachine::from_source(
        current_profile(),
        IO_ROUNDTRIP,
        Vec::new(),
    ))?;
    let plain_outcome = normalize_result(plain.run(8))?;
    check_equal(
        &traced_outcome,
        &plain_outcome,
        "profile tracing preserves run outcome",
    )?;
    check_equal(
        traced.output(),
        plain.output(),
        "profile tracing preserves output",
    )?;
    check_equal(
        &traced.registers(),
        &plain.registers(),
        "profile tracing preserves registers",
    )?;
    check_equal(
        &traced.input_consumed(),
        &plain.input_consumed(),
        "profile tracing preserves input position",
    )?;
    for address in [0u32, 1, 2, 59_049, 4_782_968] {
        check_equal(
            &normalize_result(traced.memory_word(address))?,
            &normalize_result(plain.memory_word(address))?,
            "profile tracing preserves sampled memory",
        )?;
    }
    Ok(())
}

#[test]
fn current_trace_records_profile_eof_and_is_inert() -> TestResult {
    let mut traced = normalize_result(ProfileMachine::from_source(
        current_profile(),
        IO_ROUNDTRIP,
        Vec::new(),
    ))?;
    let mut records = Vec::<ProfileStepTrace>::new();
    let traced_outcome = normalize_result(traced.run_traced(
        8,
        &mut |trace: &ProfileStepTrace| {
            records.push(*trace);
        },
    ))?;
    check_equal(
        &traced_outcome,
        &RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 3,
        },
        "current traced roundtrip halt",
    )?;
    check_equal(&records.len(), &3usize, "current trace count")?;
    check_input_eof_trace(
        records
            .first()
            .ok_or_else(|| String::from("missing current input trace"))?,
    )?;
    check_output_trace(
        records
            .get(1)
            .ok_or_else(|| String::from("missing current output trace"))?,
    )?;
    check_halt_trace(
        records
            .get(2)
            .ok_or_else(|| String::from("missing current halt trace"))?,
    )?;
    check_current_trace_inertness(&traced, traced_outcome)
}

#[test]
fn current_rejected_jump_trace_is_observationally_atomic() -> TestResult {
    let mut machine = normalize_result(ProfileMachine::from_source(
        current_profile(),
        REJECTING_JUMP_SOURCE,
        vec![0x44],
    ))?;
    let before_registers = machine.registers();
    let before_input = machine.input_consumed();
    let before_target =
        normalize_result(machine.memory_word(REJECTING_POINTER))?;
    let mut observed = None;
    let result = machine.step_traced(&mut |trace: &ProfileStepTrace| {
        observed = Some(*trace);
    });
    let expected = Err(ProfileMachineError::InvalidEncryptionTarget {
        pointer: REJECTING_POINTER,
        value: before_target,
    });
    check_equal(&result, &expected, "current jump rejection")?;
    let trace = observed
        .ok_or_else(|| String::from("missing current rejection trace"))?;
    check_equal(&trace.decoded, &Some(b'i'), "current rejection decode")?;
    check_equal(&trace.result, &expected, "current rejection result")?;
    check_equal(
        &trace.after,
        &trace.before,
        "current rejection trace atomicity",
    )?;
    check_equal(&trace.input, &None, "current rejection input")?;
    check_equal(
        &trace.memory_delta.changed_cells(),
        &0usize,
        "current rejection changes no memory",
    )?;
    check_equal(&trace.output, &None, "current rejection output")?;
    check_equal(
        &trace.profile.id(),
        &current_profile().id(),
        "current rejection profile identity",
    )?;
    check_equal(
        &machine.registers(),
        &before_registers,
        "current rejection preserves registers",
    )?;
    check_equal(
        &machine.input_consumed(),
        &before_input,
        "current rejection preserves input",
    )?;
    check_equal(
        machine.output(),
        b"".as_slice(),
        "current rejection output state",
    )?;
    check_equal(
        &normalize_result(machine.memory_word(REJECTING_POINTER))?,
        &before_target,
        "current rejection preserves jump target",
    )
}
