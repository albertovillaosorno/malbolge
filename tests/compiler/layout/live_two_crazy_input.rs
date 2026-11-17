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
//   - Executable two-stage guest input-dependent ternary arithmetic.
// - Must-Not:
//   - Equate arbitrary guest arithmetic with C23 signed EOF conversion.
// - Allows:
//   - Inputs: one fixed graphical loader seed and binary/EOF guest input.
//   - Outputs: exact two-stage VM traces and independent trit-output oracle.
//   - Side effects: bounded isolated normative VM execution.
// - Split-When:
//   - General linker places verified signed EOF conversion operands.
// - Merge-When:
//   - Full guest C stdio uses the same two-stage arithmetic verification.
// - Summary:
//   - Nine guest rotations followed by real input and two different p writes.

//! Two consecutive guest crazy operations follow nine genuine data rotations.
//! The resulting function is not C23 `putchar(getchar())` at EOF.

use malbolge::{ProfileStepTrace, Termination};

use super::*;

macro_rules! require_eq {
    ($actual:expr, $expected:expr, $context:literal) => {{
        let actual = $actual;
        let expected = $expected;
        if actual != expected {
            return Err(format!(
                "{}: actual {actual:?}, expected {expected:?}",
                $context
            ));
        }
    }};
}

const SOURCE_CELLS: usize = 29;
const ROTATIONS: usize = 9;
const ROTATION_ADDRESS: u32 = 41;
const FIRST_CRAZY_ADDRESS: u32 = 42;
const SECOND_CRAZY_ADDRESS: u32 = 43;
const SOURCE_SEED: [u8; 2] = *b"Z(";

fn operations() -> Vec<LinearOpcode> {
    let mut code = Vec::with_capacity(SOURCE_CELLS);
    code.push(LinearOpcode::RelocateDataPointer);
    for _ in 0..ROTATIONS {
        code.extend([
            LinearOpcode::RotateData,
            LinearOpcode::RelocateDataPointer,
        ]);
    }
    code.extend([
        LinearOpcode::InputWord,
        LinearOpcode::CrazyData,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::NoOperation,
        LinearOpcode::NoOperation,
        LinearOpcode::NoOperation,
        LinearOpcode::Halt,
    ]);
    code.extend(
        SOURCE_SEED
            .into_iter()
            .map(|byte| LinearOpcode::SkippedDataByte {
                byte: u32::from(byte),
            }),
    );
    code
}

// Independent digitwise oracle, not the interpreter's ternary math helper.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "bounded fifteen-trit scalar arithmetic is the independent oracle"
)]
fn scalar_crazy(mut data: u32, mut accumulator: u32, trits: u8) -> u32 {
    let mut place = 1u32;
    let mut result = 0u32;
    for _ in 0..trits {
        let trit = match (data % 3, accumulator % 3) {
            (0 | 1, 0) | (2, 2) => 1,
            (1, 2) | (2, 0 | 1) => 2,
            _ => 0,
        };
        result += trit * place;
        place *= 3;
        data /= 3;
        accumulator /= 3;
    }
    result
}

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division,
    clippy::integer_division_remainder_used,
    reason = "bounded base-three right rotation against 15-trit word range"
)]
fn scalar_rotate(word: u32, trits: u8) -> u32 {
    word / 3 + (word % 3) * 3u32.pow(u32::from(trits - 1))
}

#[expect(
    clippy::integer_division_remainder_used,
    reason = "guest output instruction is defined modulo 256"
)]
fn guest_low_byte(word: u32) -> Result<u8, String> {
    u8::try_from(word % 256).map_err(|error| error.to_string())
}

#[expect(
    clippy::arithmetic_side_effects,
    reason = "nine fixed iterations have trace indices between one and eighteen"
)]
fn verify_rotations(
    trace: &[ProfileStepTrace],
    trits: u8,
) -> Result<(), String> {
    let mut rotated = 7_174_413;
    for index in 0..ROTATIONS {
        let write = trace
            .get(1 + index * 2)
            .ok_or("missing rotation guest step")?
            .memory_delta
            .data
            .ok_or("missing preparatory guest rotation")?;
        rotated = scalar_rotate(rotated, trits);
        require_eq!(write.address, ROTATION_ADDRESS, "rotation address");
        require_eq!(write.after, rotated, "rotated word");
        let reset = trace.get(2 + index * 2).ok_or("missing reset step")?;
        require_eq!(
            reset.after.registers.data_pointer,
            ROTATION_ADDRESS,
            "rotation pointer reset"
        );
    }
    Ok(())
}

fn verify_crazy_step(
    trace: &[ProfileStepTrace],
    step: usize,
    expected: (u32, u32, u32),
) -> Result<(), String> {
    let (address, before, after) = expected;
    let observed_step = trace.get(step).ok_or("missing crazy guest step")?;
    require_eq!(observed_step.decoded, Some(b'p'), "crazy opcode");
    let data_read = observed_step
        .memory_reads
        .data
        .ok_or("missing input-dependent crazy operand")?;
    require_eq!(
        (data_read.address, data_read.value),
        (address, before),
        "crazy data operand"
    );
    // The VM records only changed cells, not an idempotent p store.
    match observed_step.memory_delta.data {
        None if before == after => {},
        Some(write) if before != after => {
            require_eq!(
                (write.address, write.before, write.after),
                (address, before, after),
                "changed crazy memory"
            );
        },
        _ => return Err(String::from("incorrect crazy changed-cell witness")),
    }
    Ok(())
}

fn verify_initial_memory(
    machine: &ProfileMachine,
    first_operand: u32,
    second_operand: u32,
) -> Result<(), String> {
    require_eq!(
        machine.memory_word(ROTATION_ADDRESS),
        Ok(7_174_413),
        "rotation data seed"
    );
    require_eq!(
        machine.memory_word(FIRST_CRAZY_ADDRESS),
        Ok(first_operand),
        "first crazy seed"
    );
    require_eq!(
        machine.memory_word(SECOND_CRAZY_ADDRESS),
        Ok(second_operand),
        "second crazy seed"
    );
    Ok(())
}

fn verify_final_guest(
    machine: &ProfileMachine,
    first: u32,
    second: u32,
    input: &[u8],
) -> Result<(), String> {
    require_eq!(
        machine.memory_word(FIRST_CRAZY_ADDRESS),
        Ok(first),
        "final first operand"
    );
    require_eq!(
        machine.memory_word(SECOND_CRAZY_ADDRESS),
        Ok(second),
        "final second operand"
    );
    require_eq!(
        machine.output(),
        [guest_low_byte(second)?],
        "two-crazy output"
    );
    require_eq!(
        machine.input_consumed(),
        usize::from(!input.is_empty()),
        "consumed guest bytes"
    );
    Ok(())
}

fn verify_one_input(
    source: &[u8],
    input: &[u8],
    first_operand: u32,
    second_operand: u32,
) -> Result<(), String> {
    let profile = current_profile();
    let input_word = input
        .first()
        .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
    let expected_first =
        scalar_crazy(first_operand, input_word, profile.word_trits());
    let expected_second =
        scalar_crazy(second_operand, expected_first, profile.word_trits());
    let mut machine =
        ProfileMachine::from_source(profile, source, input.to_vec())
            .map_err(|error| error.to_string())?;
    verify_initial_memory(&machine, first_operand, second_operand)?;
    let mut trace = Vec::new();
    let outcome = machine
        .run_traced(27, &mut |step| trace.push(*step))
        .map_err(|error| error.to_string())?;
    require_eq!(
        outcome,
        RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 27,
        },
        "guest halt"
    );
    verify_rotations(&trace, profile.word_trits())?;
    require_eq!(
        trace.get(19).map(|step| step.decoded),
        Some(Some(profile.input_instruction())),
        "guest input opcode"
    );
    verify_crazy_step(
        &trace,
        20,
        (FIRST_CRAZY_ADDRESS, first_operand, expected_first),
    )?;
    verify_crazy_step(
        &trace,
        21,
        (SECOND_CRAZY_ADDRESS, second_operand, expected_second),
    )?;
    require_eq!(
        trace.get(22).map(|step| step.decoded),
        Some(Some(profile.output_instruction())),
        "guest output opcode"
    );
    verify_final_guest(&machine, expected_first, expected_second, input)?;
    Ok(())
}

fn verify_real_two_stage_guest(source: &[u8]) -> Result<(), String> {
    let profile = current_profile();
    let first_operand = 40u32;
    let second_operand = scalar_crazy(90, 40, profile.word_trits());
    require_eq!(second_operand, 7_174_413, "second loader operand");
    // Two correct data operations do not imply C23 signed EOF conversion.
    let eof_mapped = scalar_crazy(
        second_operand,
        scalar_crazy(first_operand, profile.eof_word(), profile.word_trits()),
        profile.word_trits(),
    );
    require_eq!(guest_low_byte(eof_mapped)?, 13, "non-C23 EOF result");
    for input in [
        Vec::new(),
        vec![0],
        vec![1],
        vec![2],
        vec![127],
        vec![128],
        vec![255],
        vec![255, 0, 128],
    ] {
        verify_one_input(source, &input, first_operand, second_operand)?;
    }
    Ok(())
}

#[test]
fn manual_guest_executes_two_distinct_input_dependent_crazy_writes()
-> Result<(), String> {
    let artifact = encode_linear_layout(current_profile(), &operations())
        .map_err(|error| format!("manual two-crazy guest: {error:?}"))?;
    require_eq!(
        artifact.source().len(),
        SOURCE_CELLS,
        "manual source length"
    );
    require_eq!(
        artifact.source().get(27..),
        Some(SOURCE_SEED.as_slice()),
        "source seed"
    );
    require_eq!(
        artifact.data_write_positions().get(20),
        Some(&Some(FIRST_CRAZY_ADDRESS)),
        "first mapped write"
    );
    require_eq!(
        artifact.data_write_positions().get(21),
        Some(&Some(SECOND_CRAZY_ADDRESS)),
        "second mapped write"
    );
    verify_real_two_stage_guest(artifact.source())
}

#[test]
fn auto_layout_matches_manual_live_two_crazy_guest() -> Result<(), String> {
    let logical: Vec<_> = operations()
        .into_iter()
        .take(27)
        .map(|operation| match operation {
            LinearOpcode::RelocateDataPointer => {
                PaddedForwardStep::AutoRelocate
            },
            kept @ (LinearOpcode::CrazyData
            | LinearOpcode::Halt
            | LinearOpcode::InputWord
            | LinearOpcode::JumpForward { .. }
            | LinearOpcode::NoOperation
            | LinearOpcode::OutputByte
            | LinearOpcode::RotateData
            | LinearOpcode::SkippedDataByte { .. }) => {
                PaddedForwardStep::Instruction(kept)
            },
        })
        .collect();
    let artifact = layout::encode_auto_padded_forward_layout_with_loader_seed(
        current_profile(),
        &logical,
        SOURCE_SEED,
    )
    .map_err(|error| format!("auto two-crazy guest: {error:?}"))?;
    let manual = encode_linear_layout(current_profile(), &operations())
        .map_err(|error| format!("manual two-crazy guest: {error:?}"))?;
    require_eq!(artifact.layout(), &manual, "auto/manual encoded layout");
    verify_bidirectional_source_map(&artifact)?;
    verify_real_two_stage_guest(artifact.layout().source())
}
