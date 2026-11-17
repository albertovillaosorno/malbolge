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

use malbolge::{Termination, profile_rotate};

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
            rotated = profile_rotate(rotated, profile.word_modulus());
            assert_eq!(write.after, rotated);
            let step = &traces[reset];
            assert_eq!(step.before.registers.data_pointer, RESET_DATA);
            assert_eq!(step.decoded, Some(b'j'));
            assert_eq!(step.memory_reads.data.map(|read| read.value), Some(40));
            assert_eq!(step.after.registers.data_pointer, ROTATE_DATA);
        }
        assert_eq!(machine.memory_word(ROTATE_DATA), Ok(rotated));
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
