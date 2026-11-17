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
//   - Exact profiled-VM execution of both admitted signed EOF conversion words.
// - Must-Not:
//   - Claim that injected data cells form a loadable compiler artifact.
// - Allows:
//   - Inputs: bounded successful-byte and EOF C23 getchar cases.
//   - Outputs: trace-proven data writes and C23 putchar byte parity.
//   - Side effects: test-owned, validated N15 machine state only.
// - Split-When:
//   - The compiler lays out both operand words in a published guest artifact.
// - Merge-When:
//   - Complete signed C23 getchar-to-putchar guest lowering is verified.
// - Summary:
//   - Two crazy opcodes execute correctly with separate real data cells.
// - Description:
//   - Replays 13 input/EOF cases and one operand mutation in five VM steps.
// - Usage:
//   - `cargo test --test profile_signed_eof_byte_conversion`.
// - Defaults:
//   - The current N15 target and frozen two-word conversion are required.

//! Guest instruction-level pre-layout proof, not a C-to-Malbolge compilation.

use malbolge::{
    ProfileMachine, ProfileMemoryRead, ProfileRegisters, ProfileStepTrace,
    RunOutcome, StepOutcome, Termination, TraceInput, current_profile,
    decode_profile_instruction, profile_crazy,
};

// The layout module admits this pair only after its separate, exhaustive
// 257-case scalar oracle. Keep the bytes literal to make the VM replay an
// independent witness, without importing the entire layout implementation.
const C23_SIGNED_OUTPUT_WORDS: [u32; 2] = [87_844, 2_551];
const FIRST_DATA_ADDRESS: u32 = 65;
const INITIAL_DATA_POINTER: u32 = 64;
const SECOND_DATA_ADDRESS: u32 = 66;
const SUCCESSFUL_BYTES: [u8; 12] =
    [0, 1, 2, 3, 31, 32, 65, 106, 127, 128, 254, 255];

fn encoded_code() -> Result<Vec<u8>, String> {
    let profile = current_profile();
    let opcodes = [
        profile.input_instruction(),
        b'p',
        b'p',
        profile.output_instruction(),
        b'v',
    ];
    opcodes
        .into_iter()
        .enumerate()
        .map(|(position, opcode)| {
            (33u8..=126)
                .find(|cell| {
                    decode_profile_instruction(
                        u32::from(*cell),
                        u32::try_from(position).unwrap_or(u32::MAX),
                    ) == Some(opcode)
                })
                .ok_or_else(|| {
                    format!("cannot encode {opcode} at C={position}")
                })
        })
        .collect()
}

fn guest_machine(
    base_memory: &[u32],
    operands: [u32; 2],
    input: Option<u8>,
) -> Result<ProfileMachine, String> {
    let mut memory = base_memory.to_vec();
    for (address, value) in [
        (FIRST_DATA_ADDRESS, operands[0]),
        (SECOND_DATA_ADDRESS, operands[1]),
    ] {
        let index =
            usize::try_from(address).map_err(|error| error.to_string())?;
        let cell = memory
            .get_mut(index)
            .ok_or_else(|| format!("missing data cell {address}"))?;
        *cell = value;
    }
    ProfileMachine::from_state(
        current_profile(),
        memory,
        input.into_iter().collect(),
        ProfileRegisters {
            accumulator: 0,
            code_pointer: 0,
            data_pointer: INITIAL_DATA_POINTER,
        },
    )
    .map_err(|error| error.to_string())
}

fn run_case(
    base_memory: &[u32],
    operands: [u32; 2],
    input: Option<u8>,
) -> Result<u8, String> {
    let mut machine = guest_machine(base_memory, operands, input)?;
    let mut traces: Vec<ProfileStepTrace> = Vec::new();
    let outcome = machine
        .run_traced(5, &mut |trace| traces.push(*trace))
        .map_err(|error| error.to_string())?;
    if outcome
        != (RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 5,
        })
    {
        return Err(format!("unexpected guest run outcome: {outcome:?}"));
    }
    let [read, first, second, output, halt] = traces.as_slice() else {
        return Err(format!("expected five steps, got {}", traces.len()));
    };
    let expected_input =
        input.map_or_else(|| current_profile().eof_word(), u32::from);
    let expected_event = input.map_or(TraceInput::EndOfInput, TraceInput::Byte);
    if read.input != Some(expected_event)
        || read.after.registers.accumulator != expected_input
        || read.result != Ok(StepOutcome::Continued)
    {
        return Err(format!("incorrect genuine input step: {read:?}"));
    }
    let intermediate = validate_crazy(
        &machine,
        first,
        (FIRST_DATA_ADDRESS, operands[0]),
        expected_input,
    )?;
    let _final_word = validate_crazy(
        &machine,
        second,
        (SECOND_DATA_ADDRESS, operands[1]),
        intermediate,
    )?;
    let [actual] = machine.output() else {
        return Err(format!("expected one guest byte: {:?}", machine.output()));
    };
    if output.output != Some(*actual)
        || output.result != Ok(StepOutcome::Continued)
        || halt.result
            != Ok(StepOutcome::Terminated(Termination::HaltInstruction))
        || machine.input_consumed() != usize::from(input.is_some())
    {
        return Err(format!(
            "incorrect output/EOF trace: {output:?}, {halt:?}"
        ));
    }
    Ok(*actual)
}

fn validate_crazy(
    machine: &ProfileMachine,
    trace: &ProfileStepTrace,
    data: (u32, u32),
    accumulator: u32,
) -> Result<u32, String> {
    let (address, operand) = data;
    let expected = profile_crazy(operand, accumulator, 15);
    if trace.decoded != Some(b'p')
        || trace.memory_reads.data
            != Some(ProfileMemoryRead { address, value: operand })
        || trace.after.registers.accumulator != expected
        || trace.result != Ok(StepOutcome::Continued)
        || machine
            .memory_word(address)
            .map_err(|error| error.to_string())?
            != expected
    {
        return Err(format!(
            "incorrect guest crazy step at D={address}: {trace:?}"
        ));
    }
    Ok(expected)
}

#[test]
fn placed_c23_conversion_runs_two_real_guest_crazy_steps() -> Result<(), String>
{
    let source = encoded_code()?;
    let base = ProfileMachine::from_source(current_profile(), &source, vec![])
        .map_err(|error| error.to_string())?;
    // These two non-ASCII operand cells are injected into a verified N15
    // initial state. The compiler must still produce them via source/layout.
    for input in SUCCESSFUL_BYTES.into_iter().map(Some).chain([None]) {
        let actual = run_case(base.memory(), C23_SIGNED_OUTPUT_WORDS, input)?;
        let expected = input.unwrap_or(255);
        if actual != expected {
            return Err(format!(
                "C23 putchar mismatch for {input:?}: {actual}"
            ));
        }
    }
    // A one-trit data-cell mutation must change the *real* guest EOF byte.
    let mut mutated = C23_SIGNED_OUTPUT_WORDS;
    mutated[1] += 1;
    let changed = run_case(base.memory(), mutated, None)?;
    if changed != 254 {
        return Err(format!("mutated guest EOF expected 254, got {changed}"));
    }
    Ok(())
}
