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
//   - Position-constrained loader seed synthesis and normative VM cross-checks.
// - Must-Not:
//   - Assume selected data words were rotated by guest instructions.
// - Allows:
//   - Inputs: finite fixed source lengths and exact adjacent data word goals.
//   - Outputs: loadable graphical suffixes or explicit unsatisfiability.
//   - Side effects: isolated bounded guest VM execution.
// - Split-When:
//   - General data relocation/linkage performs a real operand revisit.
// - Merge-When:
//   - Loader-seed placement is part of full verified target code generation.
// - Summary:
//   - Keeps algebraic EOF words separate from valid encoded source positions.

//! The selection search cannot bypass the actual profile loader or linker.

use malbolge::{profile_crazy, profile_rotate};

use super::*;

#[test]
fn selects_exact_source_loadable_rotated_eof_pair() -> Result<(), String> {
    let profile = current_profile();
    let required = [7_138_732, 121];
    let seed = layout::select_rotated_loader_seed(profile, 91, 95, 9, required)
        .map_err(|error| format!("rotated loader search: {error:?}"))?;
    assert_eq!(seed, *b"Iy");
    assert_eq!(
        layout::admit_c23_signed_output_word_plan(profile, required)
            .map_err(|error| format!("C23 word plan: {error:?}"))?
            .operands(),
        required,
    );

    // The same physical tail is consumed by the real forward planner.
    // No synthetic operation is attributed to either loader seed cell.
    let mut logical =
        vec![PaddedForwardStep::Instruction(LinearOpcode::NoOperation); 89];
    logical[40] =
        PaddedForwardStep::Instruction(LinearOpcode::RelocateDataPointer);
    logical[41] = PaddedForwardStep::Instruction(LinearOpcode::RotateData);
    logical[42] = PaddedForwardStep::Instruction(LinearOpcode::OutputByte);
    logical[88] = PaddedForwardStep::Instruction(LinearOpcode::Halt);
    let planned = layout::encode_auto_padded_forward_layout_with_loader_seed(
        profile, &logical, seed,
    )
    .map_err(|error| format!("physical layout: {error:?}"))?;
    assert_eq!(planned.layout().source().len(), 91);
    assert_eq!(planned.source_cell_origins()[89..], [
        PaddedCellOrigin::LoaderSeed,
        PaddedCellOrigin::LoaderSeed
    ]);
    for input in [Vec::new(), vec![0, 128, 255]] {
        let mut vm = ProfileMachine::from_source(
            profile,
            planned.layout().source(),
            input,
        )
        .map_err(|error| error.to_string())?;
        let before = vm.memory_word(95).map_err(|error| error.to_string())?;
        let untouched =
            vm.memory_word(96).map_err(|error| error.to_string())?;
        let mut after_nine = before;
        for _ in 0..9 {
            after_nine = profile_rotate(after_nine, profile.word_modulus());
        }
        assert_eq!([after_nine, untouched], required);
        verify_execution_witness(&mut vm, planned.layout())?;
        assert_eq!(
            vm.memory_word(95),
            Ok(profile_rotate(before, profile.word_modulus())),
            "the actual guest performs only one of nine proposed rotations",
        );
        assert_eq!(vm.memory_word(96), Ok(untouched));
        assert_eq!(vm.input_consumed(), 0);
    }
    Ok(())
}

#[test]
fn source_position_prevents_an_algebraic_pointer_reset() {
    let profile = current_profile();
    // With a 118-cell source, phase four begins at address 122. The next
    // word is 121, so j could restore D=122 after rotating that first word.
    // But all four printable tails that give the exact 257-case operands
    // end in 'y', which cannot load at physical source address 117.
    assert_eq!(
        layout::select_rotated_loader_seed(profile, 118, 122, 9, [
            7_138_732, 121
        ]),
        Err(layout::LoaderSeedSelectionError::NoLoadableSeed),
    );
    assert_eq!(decode_profile_instruction(121, 117), Some(b')'));
    assert_eq!(
        layout::select_rotated_loader_seed(profile, 91, 95, 8, [
            7_138_732, 121
        ]),
        Err(layout::LoaderSeedSelectionError::NoLoadableSeed),
    );
}

#[test]
fn selects_and_reloads_exact_zero_rotation_data_for_both_profiles()
-> Result<(), String> {
    for profile in [current_profile(), historical_profile()] {
        let first = (33..=126u8)
            .find(|&byte| {
                decode_profile_instruction(u32::from(byte), 0) == Some(b'o')
            })
            .ok_or("no graphical first no-op")?;
        let second = (33..=126u8)
            .find(|&byte| {
                decode_profile_instruction(u32::from(byte), 1) == Some(b'o')
            })
            .ok_or("no graphical second no-op")?;
        let first_word = profile_crazy(
            u32::from(first),
            u32::from(second),
            profile.word_trits(),
        );
        let second_word =
            profile_crazy(u32::from(second), first_word, profile.word_trits());
        let seed = layout::select_rotated_loader_seed(profile, 2, 2, 0, [
            first_word,
            second_word,
        ])
        .map_err(|error| format!("zero-rotation seed: {error:?}"))?;
        let vm = ProfileMachine::from_source(profile, &seed, vec![])
            .map_err(|error| error.to_string())?;
        assert_eq!(vm.memory_word(2), Ok(first_word));
        assert_eq!(vm.memory_word(3), Ok(second_word));
    }
    Ok(())
}

#[test]
fn source_tail_selection_rejects_unsupported_geometry_and_words() {
    let profile = current_profile();
    let select = |source_length, data_address, rotations, operands| {
        layout::select_rotated_loader_seed(
            profile,
            source_length,
            data_address,
            rotations,
            operands,
        )
    };
    let desired = [7_138_732, 121];
    for (length, address, rotations) in [
        (1, 95, 9),
        (4097, 4099, 9),
        (91, 90, 9),
        (91, profile.memory_words() - 1, 9),
        (91, u32::MAX, 9),
        (91, 95, profile.word_trits()),
    ] {
        assert_eq!(
            select(length, address, rotations, desired),
            Err(layout::LoaderSeedSelectionError::InvalidGeometry),
        );
    }
    assert_eq!(
        select(91, 95, 9, [profile.word_modulus(), 121]),
        Err(layout::LoaderSeedSelectionError::InvalidOperand),
    );
}
