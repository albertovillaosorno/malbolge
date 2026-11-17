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
//   - Guest-executed repeated arithmetic at a loader-expanded memory cell.
// - Must-Not:
//   - Claim repeated writes provide signed EOF conversion or C loop support.
// - Allows:
//   - Inputs: one exact graphical loader tail and bounded N15 guest path.
//   - Outputs: nine independently traced rotations and pointer resets.
//   - Side effects: isolated normative profile VM runs only.
// - Split-When:
//   - A general guest data-operand revisit solver replaces fixed witnesses.
// - Merge-When:
//   - Compiler backend synthesizes verified repeated data-cell mutations.
// - Summary:
//   - Alternating actual * and j revisits one loader cell nine times.

//! An untouched loader word can reset D between nine genuine guest writes.
//! These operands do not implement C23 EOF conversion or source-C storage.

use malbolge::Termination;

use super::*;

const SOURCE_LENGTH: usize = 23;
const ROTATE_DATA: u32 = 41;
const RESET_DATA: u32 = 42;
const ROTATIONS: usize = 9;
const LOADER_SEED: [u8; 2] = [112, 40];

fn repeated_rotation_operations() -> Vec<LinearOpcode> {
    let mut operations = vec![LinearOpcode::NoOperation; SOURCE_LENGTH];
    operations[0] = LinearOpcode::RelocateDataPointer;
    for rotation in 0..ROTATIONS {
        operations[1 + 2 * rotation] = LinearOpcode::RotateData;
        operations[2 + 2 * rotation] = LinearOpcode::RelocateDataPointer;
    }
    operations[20] = LinearOpcode::Halt;
    operations[21] = LinearOpcode::SkippedDataByte {
        byte: u32::from(LOADER_SEED[0]),
    };
    operations[22] = LinearOpcode::SkippedDataByte {
        byte: u32::from(LOADER_SEED[1]),
    };
    operations
}

// Independent base-three right rotation: the VM operation is not the oracle.
fn scalar_rotate_right(word: u32, trits: u8) -> u32 {
    let high_place = 3u32.pow(u32::from(trits.saturating_sub(1)));
    word / 3 + (word % 3) * high_place
}

fn verify_nine_guest_writes(source: &[u8]) -> Result<(), String> {
    let profile = current_profile();
    for input in [Vec::new(), vec![0, 128, 255]] {
        let mut machine = ProfileMachine::from_source(profile, source, input)
            .map_err(|error| error.to_string())?;
        let initial = machine
            .memory_word(ROTATE_DATA)
            .map_err(|error| error.to_string())?;
        assert_eq!(initial, 7_174_413);
        assert_eq!(machine.memory_word(RESET_DATA), Ok(40));
        let mut traces = Vec::new();
        let result = machine
            .run_traced(21, &mut |trace| traces.push(*trace))
            .map_err(|error| error.to_string())?;
        assert_eq!(result, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 21,
        });
        let mut rotated = initial;
        for rotation in 0..ROTATIONS {
            let rotate = 1 + 2 * rotation;
            let reset = rotate + 1;
            let step = &traces[rotate];
            assert_eq!(step.before.registers.data_pointer, ROTATE_DATA);
            assert_eq!(step.decoded, Some(b'*'));
            let write = step.memory_delta.data.ok_or("missing guest write")?;
            assert_eq!(write.address, ROTATE_DATA);
            assert_eq!(write.before, rotated);
            rotated = scalar_rotate_right(rotated, profile.word_trits());
            assert_eq!(write.after, rotated);
            let step = &traces[reset];
            assert_eq!(step.before.registers.data_pointer, RESET_DATA);
            assert_eq!(step.decoded, Some(b'j'));
            assert_eq!(step.memory_reads.data.map(|read| read.value), Some(40));
            assert_eq!(step.after.registers.data_pointer, ROTATE_DATA);
        }
        assert_eq!(machine.memory_word(ROTATE_DATA), Ok(rotated));
        // This is a data-write witness only, not the two-operand C23
        // signed-getchar conversion that would require a different seed.
        assert_ne!(rotated, 7_138_732);
        assert_eq!(machine.memory_word(RESET_DATA), Ok(40));
        assert_eq!(machine.input_consumed(), 0);
        assert!(machine.output().is_empty());
    }
    Ok(())
}

#[test]
fn nine_real_rotations_revisit_one_loader_word() -> Result<(), String> {
    let profile = current_profile();
    let operations = repeated_rotation_operations();
    let layout = encode_linear_layout(profile, &operations)
        .map_err(|error| format!("nine-rotation layout: {error:?}"))?;
    assert_eq!(layout.source().len(), SOURCE_LENGTH);
    assert_eq!(&layout.source()[21..], &LOADER_SEED);
    assert_eq!(layout.data_pointer_positions()[0], 0);
    for rotation in 0..ROTATIONS {
        let rotate = 1 + 2 * rotation;
        let reset = rotate + 1;
        assert_eq!(layout.data_pointer_positions()[rotate], ROTATE_DATA);
        assert_eq!(layout.data_pointer_positions()[reset], RESET_DATA);
        assert_eq!(layout.data_write_positions()[rotate], Some(ROTATE_DATA));
        assert_eq!(layout.data_write_positions()[reset], None);
    }
    verify_nine_guest_writes(layout.source())
}

#[test]
fn auto_relocation_reuses_fixed_loader_seed_across_nine_writes()
-> Result<(), String> {
    let profile = current_profile();
    let mut logical =
        vec![PaddedForwardStep::Instruction(LinearOpcode::NoOperation); 21];
    logical[0] = PaddedForwardStep::AutoRelocate;
    for rotation in 0..ROTATIONS {
        logical[1 + 2 * rotation] =
            PaddedForwardStep::Instruction(LinearOpcode::RotateData);
        logical[2 + 2 * rotation] = PaddedForwardStep::AutoRelocate;
    }
    logical[20] = PaddedForwardStep::Instruction(LinearOpcode::Halt);
    let encoded = layout::encode_auto_padded_forward_layout_with_loader_seed(
        profile,
        &logical,
        LOADER_SEED,
    )
    .map_err(|error| format!("repeated auto relocation: {error:?}"))?;
    let manual = encode_linear_layout(profile, &repeated_rotation_operations())
        .map_err(|error| format!("manual rotations: {error:?}"))?;
    assert_eq!(encoded.layout(), &manual);
    assert_eq!(encoded.logical_code_positions().len(), 21);
    verify_bidirectional_source_map(&encoded)?;
    verify_nine_guest_writes(encoded.layout().source())
}

// A longer physical tail can preserve the same loader arithmetic operand
// while leaving room for actual, input-dependent guest I/O after nine writes.
// The resulting byte is a ternary-machine value, not C23 putchar(getchar()).
const LIVE_SOURCE_LENGTH: usize = 29;
const LIVE_LOADER_SEED: [u8; 2] = [b'Z', b'('];

fn live_arithmetic_operations() -> Vec<LinearOpcode> {
    let mut operations = vec![LinearOpcode::NoOperation; LIVE_SOURCE_LENGTH];
    operations[0] = LinearOpcode::RelocateDataPointer;
    for rotation in 0..ROTATIONS {
        operations[1 + 2 * rotation] = LinearOpcode::RotateData;
        operations[2 + 2 * rotation] = LinearOpcode::RelocateDataPointer;
    }
    operations[19] = LinearOpcode::InputWord;
    operations[20] = LinearOpcode::CrazyData;
    operations[21] = LinearOpcode::OutputByte;
    operations[26] = LinearOpcode::Halt;
    operations[27] = LinearOpcode::SkippedDataByte {
        byte: u32::from(LIVE_LOADER_SEED[0]),
    };
    operations[28] = LinearOpcode::SkippedDataByte {
        byte: u32::from(LIVE_LOADER_SEED[1]),
    };
    operations
}

// An independent per-trit crazy oracle, not the interpreter's own helper.
fn scalar_crazy_word(mut data: u32, mut accumulator: u32, trits: u8) -> u32 {
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

fn verify_live_arithmetic_after_repeated_rotations(
    source: &[u8],
    inputs: &[Vec<u8>],
) -> Result<(), String> {
    let profile = current_profile();
    for input in inputs {
        let guest_input = input
            .first()
            .map_or(profile.eof_word(), |value| u32::from(*value));
        let expected = scalar_crazy_word(40, guest_input, profile.word_trits());
        let mut machine =
            ProfileMachine::from_source(profile, source, input.clone())
                .map_err(|error| error.to_string())?;
        assert_eq!(machine.memory_word(ROTATE_DATA), Ok(7_174_413));
        assert_eq!(machine.memory_word(RESET_DATA), Ok(40));
        let mut traces = Vec::new();
        let outcome = machine
            .run_traced(27, &mut |trace| traces.push(*trace))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 27,
        });
        let mut rotation_value = 7_174_413;
        for rotation in 0..ROTATIONS {
            let write = traces[1 + 2 * rotation]
                .memory_delta
                .data
                .ok_or("missing rotation data write")?;
            rotation_value =
                scalar_rotate_right(rotation_value, profile.word_trits());
            assert_eq!(write.address, ROTATE_DATA);
            assert_eq!(write.after, rotation_value);
            assert_eq!(
                traces[2 + 2 * rotation].after.registers.data_pointer,
                ROTATE_DATA,
            );
        }
        assert_eq!(machine.memory_word(ROTATE_DATA), Ok(rotation_value));
        assert_eq!(traces[19].decoded, Some(profile.input_instruction()));
        assert_eq!(traces[20].decoded, Some(b'p'));
        assert_eq!(traces[20].before.registers.data_pointer, RESET_DATA);
        let crazy_write = traces[20]
            .memory_delta
            .data
            .ok_or("missing input-dependent crazy write")?;
        assert_eq!(crazy_write.address, RESET_DATA);
        assert_eq!(crazy_write.before, 40);
        assert_eq!(crazy_write.after, expected);
        assert_eq!(traces[20].after.registers.accumulator, expected);
        assert_eq!(traces[21].decoded, Some(profile.output_instruction()));
        assert_eq!(machine.memory_word(RESET_DATA), Ok(expected));
        assert_eq!(machine.output(), [(expected % 256) as u8]);
        assert_eq!(machine.input_consumed(), usize::from(!input.is_empty()));
    }
    Ok(())
}

#[test]
fn nine_rotations_feed_real_input_dependent_crazy_output() -> Result<(), String>
{
    let profile = current_profile();
    let layout =
        encode_linear_layout(profile, &live_arithmetic_operations())
            .map_err(|error| format!("live arithmetic layout: {error:?}"))?;
    assert_eq!(layout.source().len(), LIVE_SOURCE_LENGTH);
    assert_eq!(&layout.source()[27..], &LIVE_LOADER_SEED);
    assert_eq!(layout.data_pointer_positions()[20], RESET_DATA);
    assert_eq!(layout.data_write_positions()[20], Some(RESET_DATA));
    verify_live_arithmetic_after_repeated_rotations(layout.source(), &[
        Vec::new(),
        vec![0],
        vec![1],
        vec![2],
        vec![128],
        vec![255],
    ])
}

#[test]
fn auto_padded_nine_rotations_preserve_live_arithmetic_output()
-> Result<(), String> {
    let profile = current_profile();
    let mut logical =
        vec![PaddedForwardStep::Instruction(LinearOpcode::NoOperation); 27];
    logical[0] = PaddedForwardStep::AutoRelocate;
    for rotation in 0..ROTATIONS {
        logical[1 + 2 * rotation] =
            PaddedForwardStep::Instruction(LinearOpcode::RotateData);
        logical[2 + 2 * rotation] = PaddedForwardStep::AutoRelocate;
    }
    logical[19] = PaddedForwardStep::Instruction(LinearOpcode::InputWord);
    logical[20] = PaddedForwardStep::Instruction(LinearOpcode::CrazyData);
    logical[21] = PaddedForwardStep::Instruction(LinearOpcode::OutputByte);
    logical[26] = PaddedForwardStep::Instruction(LinearOpcode::Halt);
    let automatic = layout::encode_auto_padded_forward_layout_with_loader_seed(
        profile,
        &logical,
        LIVE_LOADER_SEED,
    )
    .map_err(|error| format!("automatic live arithmetic: {error:?}"))?;
    let manual =
        encode_linear_layout(profile, &live_arithmetic_operations())
            .map_err(|error| format!("manual live arithmetic: {error:?}"))?;
    assert_eq!(automatic.layout(), &manual);
    verify_bidirectional_source_map(&automatic)?;
    verify_live_arithmetic_after_repeated_rotations(
        automatic.layout().source(),
        &[vec![0, 128, 255]],
    )
}
