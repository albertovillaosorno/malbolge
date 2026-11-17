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
//   - Real guest input/EOF distinction through an exact VM checkpoint.
// - Must-Not:
//   - Claim C getchar lowering or replace the guest with host-side output.
// - Allows:
//   - Inputs: two frozen byte streams and both canonical profile geometries.
//   - Outputs: exact committed input traces, accumulator and guest stdout.
//   - Side effects: bounded in-memory normative guest execution only.
// - Split-When:
//   - Generated compiler programs need their own translation witnesses.
// - Merge-When:
//   - The P2 compiled EOF checksum independently proves checkpoint parity.
// - Summary:
//   - Real VM EOF is not a byte, even when output residues collide.
// - Description:
//   - Confirms repeated EOF and unchanged cursor after snapshot restoration.
// - Usage:
//   - `cargo test --test profile_eof_continuation`.
// - Defaults:
//   - Fixed six-step programs and no unbounded execution.
//
//! A pinned guest-level EOF/checkpoint boundary for later C input lowering.

use std::fmt::Debug;

use malbolge::{
    ProfileDescriptor, ProfileMachine, ProfileStepTrace, StepOutcome,
    Termination, TraceInput, current_profile, decode_profile_instruction,
    historical_profile,
};

fn check_equal<Value>(
    actual: &Value,
    expected: &Value,
    context: &str,
) -> Result<(), String>
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

fn instruction_source(profile: &ProfileDescriptor) -> Result<Vec<u8>, String> {
    let decoded = [
        profile.input_instruction(),
        profile.input_instruction(),
        profile.input_instruction(),
        profile.input_instruction(),
        profile.output_instruction(),
        b'v',
    ];
    decoded
        .into_iter()
        .enumerate()
        .map(|(position, opcode)| {
            (33u8..=126)
                .find(|byte| {
                    decode_profile_instruction(
                        u32::from(*byte),
                        u32::try_from(position).unwrap_or(u32::MAX),
                    ) == Some(opcode)
                })
                .ok_or_else(|| format!("cannot encode {opcode} at {position}"))
        })
        .collect()
}

fn check_input(
    machine: &mut ProfileMachine,
    profile: &ProfileDescriptor,
    input: &[u8],
    index: usize,
) -> Result<(), String> {
    let expected = input
        .get(index)
        .copied()
        .map_or(TraceInput::EndOfInput, TraceInput::Byte);
    let expected_accumulator = input
        .get(index)
        .copied()
        .map_or_else(|| profile.eof_word(), u32::from);
    let mut records: Vec<ProfileStepTrace> = Vec::new();
    let outcome = machine
        .step_traced(&mut |trace| records.push(*trace))
        .map_err(|error| error.to_string())?;
    check_equal(&outcome, &StepOutcome::Continued, "input transition")?;
    let [record] = records.as_slice() else {
        return Err(format!(
            "expected exactly one input trace at step {index}"
        ));
    };
    check_equal(
        &record.decoded,
        &Some(profile.input_instruction()),
        "decode",
    )?;
    check_equal(&record.input, &Some(expected), "input event")?;
    check_equal(&record.output, &None, "input must not write")?;
    check_equal(
        &record.before.input_consumed,
        &input.len().min(index),
        "prior cursor",
    )?;
    check_equal(
        &record.after.input_consumed,
        &input.len().min(index.saturating_add(1)),
        "next cursor",
    )?;
    check_equal(
        &record.after.registers.accumulator,
        &expected_accumulator,
        "full-width input or EOF accumulator",
    )?;
    check_equal(
        &record.after.registers,
        &machine.registers(),
        "trace and machine registers",
    )
}

fn run_case(
    profile: &'static ProfileDescriptor,
    code: &[u8],
    input: &[u8],
) -> Result<(), String> {
    let mut machine =
        ProfileMachine::from_source(profile, code, input.to_vec()).map_err(
            |error| format!("cannot load {} guest: {error}", profile.id()),
        )?;
    for index in 0..2 {
        check_input(&mut machine, profile, input, index)?;
    }
    let checkpoint = machine.snapshot_state();
    check_equal(checkpoint.io().input(), input, "checkpoint input")?;
    check_equal(
        &checkpoint.io().input_consumed(),
        &input.len().min(2),
        "checkpoint cursor",
    )?;
    let mut restored = ProfileMachine::from_snapshot(checkpoint);
    check_equal(&restored.registers(), &machine.registers(), "restore regs")?;
    check_equal(
        &restored.input_consumed(),
        &machine.input_consumed(),
        "restore cursor",
    )?;
    check_equal(restored.output(), machine.output(), "restore output")?;

    for index in 2..4 {
        check_input(&mut machine, profile, input, index)?;
        check_equal(
            &restored.step(),
            &Ok(StepOutcome::Continued),
            "restored input",
        )?;
        check_equal(&restored.registers(), &machine.registers(), "input regs")?;
        check_equal(
            &restored.input_consumed(),
            &machine.input_consumed(),
            "input cursor",
        )?;
    }
    let eof_byte = profile.eof_word().to_le_bytes()[0];
    // EOF never advances the cursor, including when a prior input byte has
    // the same low byte as this profile's full-width EOF sentinel.
    check_equal(&machine.input_consumed(), &input.len(), "final cursor")?;
    check_equal(
        &machine.registers().accumulator,
        &profile.eof_word(),
        "full-width EOF",
    )?;
    check_equal(&machine.step(), &Ok(StepOutcome::Continued), "output")?;
    check_equal(
        &restored.step(),
        &Ok(StepOutcome::Continued),
        "restored output",
    )?;
    check_equal(machine.output(), [eof_byte].as_slice(), "guest EOF stdout")?;
    check_equal(machine.output(), restored.output(), "restored stdout")?;
    let halted = Ok(StepOutcome::Terminated(Termination::HaltInstruction));
    check_equal(&machine.step(), &halted, "halt")?;
    check_equal(&restored.step(), &halted, "restored halt")?;
    check_equal(
        &machine.snapshot_state(),
        &restored.snapshot_state(),
        "full VM state after checkpoint continuation",
    )
}

#[test]
fn guest_eof_remains_distinct_from_identical_low_byte_across_checkpoints()
-> Result<(), String> {
    for profile in [current_profile(), historical_profile()] {
        let code = instruction_source(profile)?;
        let eof_byte = profile.eof_word().to_le_bytes()[0];
        // A *successful* byte with the same low 8 bits as EOF precedes two
        // genuine EOF reads. Neither decision comes from a host-side oracle.
        for input in [Vec::new(), vec![eof_byte, 0xff]] {
            run_case(profile, &code, &input)?;
        }
    }
    Ok(())
}
