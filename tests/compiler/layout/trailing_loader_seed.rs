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
//   - Verified, unreachable graphical source tails that seed guest data.
// - Must-Not:
//   - Execute trailing cells or claim complete signed-EOF C conversion.
// - Allows:
//   - Inputs: exact two-cell loader suffix after a reached halt.
//   - Outputs: admitted layout and traced N15 expanded-memory rotation.
//   - Side effects: finite normative profile VM executions.
// - Split-When:
//   - Dynamic guest constants and return-to-operand layout are synthesized.
// - Merge-When:
//   - A general verified linker subsumes dead source loader-data cells.
// - Summary:
//   - Source-loaded operand words can survive an earlier real guest halt.

//! The byte operands come from the actual loader, not an injected VM state.

use malbolge::{ProfileMemoryRead, Termination, profile_crazy, profile_rotate};

use super::*;

fn halted_seed_plan() -> Vec<LinearOpcode> {
    let mut operations = vec![LinearOpcode::NoOperation; 91];
    operations[40] = LinearOpcode::RelocateDataPointer;
    operations[41] = LinearOpcode::RotateData;
    operations[42] = LinearOpcode::OutputByte;
    operations[88] = LinearOpcode::Halt;
    // The decoder admits I as o at 89 and y as input at 90, but neither
    // instruction executes. Both are loadable source data for N15 expansion.
    operations[89] = LinearOpcode::SkippedDataByte { byte: 73 };
    operations[90] = LinearOpcode::SkippedDataByte { byte: 121 };
    operations
}

#[test]
fn halted_source_tail_drives_a_real_loader_expanded_rotation()
-> Result<(), String> {
    let profile = current_profile();
    let operations = halted_seed_plan();
    let layout = encode_linear_layout(profile, &operations)
        .map_err(|error| format!("trailing seed layout: {error:?}"))?;
    let source = layout.source();
    assert_eq!(source.len(), 91);
    assert_eq!(&source[89..], b"Iy");
    // An executed j reads its own canonical cell (^ = 94), selecting
    // expanded address 95; its following * mutates precisely that word.
    assert_eq!(source[40], 94);
    assert_eq!(layout.data_pointer_positions()[41], 95);
    assert_eq!(layout.data_write_positions()[41], Some(95));
    assert_eq!(layout.executed_code_positions().last(), Some(&88));
    assert!(!layout.executed_code_positions().contains(&89));
    assert!(!layout.executed_code_positions().contains(&90));
    assert_eq!(layout.encrypted_code_positions().len(), 88);

    for input in [Vec::new(), vec![0, 128, 255]] {
        let mut machine = ProfileMachine::from_source(profile, source, input)
            .map_err(|error| error.to_string())?;
        let first =
            machine.memory_word(95).map_err(|error| error.to_string())?;
        let second =
            machine.memory_word(96).map_err(|error| error.to_string())?;
        let last_two = [u32::from(source[89]), u32::from(source[90])];
        let expanded: Vec<u32> = (0..6)
            .scan(last_two, |words, _| {
                let word = profile_crazy(words[0], words[1], 15);
                *words = [words[1], word];
                Some(word)
            })
            .collect();
        assert_eq!(first, expanded[4]);
        assert_eq!(second, expanded[5]);
        assert_eq!([first, second], [7_174_404, 121]);

        let mut traces = Vec::new();
        let outcome = machine
            .run_traced(89, &mut |trace| traces.push(*trace))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 89,
        },);
        assert_eq!(traces.len(), 89);
        assert_eq!(
            traces[41].memory_reads.data,
            Some(ProfileMemoryRead {
                address: 95,
                value: first,
            }),
        );
        assert_eq!(traces[41].decoded, Some(b'*'));
        let rotated = profile_rotate(first, profile.word_modulus());
        assert_eq!(machine.memory_word(95), Ok(rotated));
        assert_eq!(machine.memory_word(96), Ok(second));
        assert_eq!(machine.output(), [(rotated % 256) as u8]);
        assert_eq!(machine.input_consumed(), 0);
    }
    Ok(())
}

#[test]
fn only_two_loader_data_cells_may_follow_a_reached_halt() {
    let profile = current_profile();
    let valid = halted_seed_plan();
    let encoded = encode_linear_layout(profile, &valid)
        .expect("valid source tail must admit")
        .source()
        .to_vec();
    let identity = LinearProfileIdentity {
        id: profile.id(),
        fingerprint: profile.fingerprint(),
    };
    let mut forged = encoded.clone();
    forged[90] = 120;
    assert_eq!(
        admit_linear_layout(profile, &valid, &forged, identity),
        Err(LinearLayoutError::DecodeMismatch { position: 90 }),
    );
    let mut single = valid.clone();
    let _ = single.pop();
    assert!(encode_linear_layout(profile, &single).is_err());
    let mut three = valid.clone();
    three.push(LinearOpcode::SkippedDataByte { byte: 73 });
    assert!(encode_linear_layout(profile, &three).is_err());
    let mut invalid = valid.clone();
    invalid[90] = LinearOpcode::SkippedDataByte { byte: 127 };
    assert_eq!(
        encode_linear_layout(profile, &invalid),
        Err(LinearLayoutError::NoEncoding { position: 90 }),
    );
    let mut premature = valid.clone();
    premature[87] = LinearOpcode::Halt;
    assert_eq!(
        encode_linear_layout(profile, &premature),
        Err(LinearLayoutError::EarlyHalt { position: 87 }),
    );
    let mut live_skipped = valid;
    live_skipped[50] = LinearOpcode::SkippedDataByte { byte: 73 };
    assert_eq!(
        encode_linear_layout(profile, &live_skipped),
        Err(LinearLayoutError::JumpPathUnsupported),
    );
}

#[test]
fn padded_planner_keeps_loader_seeds_outside_reached_logical_steps()
-> Result<(), String> {
    let profile = current_profile();
    let manually_planned = halted_seed_plan();
    let logical: Vec<PaddedForwardStep> = manually_planned[..89]
        .iter()
        .copied()
        .map(PaddedForwardStep::Instruction)
        .collect();
    let padded = layout::encode_auto_padded_forward_layout_with_loader_seed(
        profile, &logical, *b"Iy",
    )
    .map_err(|error| format!("padded seed plan: {error:?}"))?;
    let manual = encode_linear_layout(profile, &manually_planned)
        .map_err(|error| format!("manual seed plan: {error:?}"))?;
    assert_eq!(padded.layout(), &manual);
    assert_eq!(padded.operations(), &manually_planned);
    assert_eq!(padded.logical_code_positions().len(), 89);
    assert_eq!(padded.logical_code_positions().last(), Some(&88));
    assert_eq!(&padded.source_cell_origins()[89..], &[
        PaddedCellOrigin::LoaderSeed,
        PaddedCellOrigin::LoaderSeed
    ],);
    verify_bidirectional_source_map(&padded)?;
    let mut vm =
        ProfileMachine::from_source(profile, padded.layout().source(), vec![
            255,
        ])
        .map_err(|error| error.to_string())?;
    verify_execution_witness(&mut vm, padded.layout())?;
    assert_eq!(vm.input_consumed(), 0);

    // The same fixed loader tail must be available to online relocation
    // selection, not only to a hand-placed `j` instruction.
    let mut auto = logical;
    auto[40] = PaddedForwardStep::AutoRelocate;
    let automatically_relocated =
        layout::encode_auto_padded_forward_layout_with_loader_seed(
            profile, &auto, *b"Iy",
        )
        .map_err(|error| format!("automatic seed relocation: {error:?}"))?;
    assert_eq!(automatically_relocated.layout(), &manual);
    assert_eq!(automatically_relocated.logical_code_positions().len(), 89);
    verify_bidirectional_source_map(&automatically_relocated)?;
    Ok(())
}

#[test]
fn padded_loader_seed_api_rejects_unreachable_or_invalid_logical_paths() {
    let profile = current_profile();
    let logical = [
        PaddedForwardStep::Instruction(LinearOpcode::NoOperation),
        PaddedForwardStep::Instruction(LinearOpcode::Halt),
    ];
    let graphical = |position| {
        (33..=126u8)
            .find(|&byte| {
                decode_profile_instruction(u32::from(byte), position)
                    == Some(b'o')
            })
            .expect("one loadable graphical cell at each source address")
    };
    let seed = [graphical(2), graphical(3)];
    let safe = layout::encode_auto_padded_forward_layout_with_loader_seed(
        profile, &logical, seed,
    )
    .expect("a reached halt must preserve two loadable suffix cells");
    assert_eq!(safe.layout().source().len(), 4);
    assert_eq!(safe.logical_code_positions(), [0, 1]);
    assert_eq!(safe.source_cell_origins(), [
        PaddedCellOrigin::Logical(0),
        PaddedCellOrigin::Logical(1),
        PaddedCellOrigin::LoaderSeed,
        PaddedCellOrigin::LoaderSeed
    ]);
    let mut guest =
        ProfileMachine::from_source(profile, safe.layout().source(), vec![])
            .expect(
                "the canonical loader must accept its exact graphical suffix",
            );
    assert_eq!(
        guest.run(2),
        Ok(RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 2,
        })
    );

    let bad_byte = (33..=126u8)
        .find(|&byte| {
            !matches!(
                decode_profile_instruction(u32::from(byte), 2),
                Some(b'j' | b'i' | b'*' | b'p' | b'v' | b'o' | b'<' | b'/')
            )
        })
        .expect("some graphical bytes are not loadable at address two");
    assert_eq!(
        layout::encode_auto_padded_forward_layout_with_loader_seed(
            profile,
            &logical,
            [bad_byte, seed[1]],
        ),
        Err(LinearLayoutError::NoEncoding { position: 2 }),
    );
    assert_eq!(
        encode_auto_padded_forward_layout(profile, &[
            logical[0],
            logical[1],
            PaddedForwardStep::Instruction(LinearOpcode::SkippedDataByte {
                byte: u32::from(seed[0]),
            }),
            PaddedForwardStep::Instruction(LinearOpcode::SkippedDataByte {
                byte: u32::from(seed[1]),
            }),
        ]),
        Err(LinearLayoutError::JumpPathUnsupported),
    );
    let wrong_terminal = [
        PaddedForwardStep::Instruction(LinearOpcode::Halt),
        PaddedForwardStep::Instruction(LinearOpcode::NoOperation),
    ];
    assert_eq!(
        layout::encode_auto_padded_forward_layout_with_loader_seed(
            profile,
            &wrong_terminal,
            seed,
        ),
        Err(LinearLayoutError::MissingHalt),
    );
    let early_halt = [
        PaddedForwardStep::Instruction(LinearOpcode::Halt),
        PaddedForwardStep::Instruction(LinearOpcode::NoOperation),
        PaddedForwardStep::Instruction(LinearOpcode::Halt),
    ];
    assert_eq!(
        layout::encode_auto_padded_forward_layout_with_loader_seed(
            profile,
            &early_halt,
            [graphical(3), graphical(4)],
        ),
        Err(LinearLayoutError::EarlyHalt { position: 0 }),
    );
}

// A forward-jump gap and a post-halt loader suffix are different kinds
// of unreachable source cells. Both must retain their exact provenance.
#[test]
fn loader_seed_provenance_does_not_confuse_forward_jump_gaps()
-> Result<(), String> {
    let logical = [
        PaddedForwardStep::Jump,
        PaddedForwardStep::Instruction(LinearOpcode::NoOperation),
        PaddedForwardStep::Instruction(LinearOpcode::Halt),
    ];
    let source_byte = (33..=126u32)
        .find(|&byte| decode_profile_instruction(byte, 0) == Some(b'i'))
        .ok_or("no inverse graphical first-instruction jump")?;
    let target =
        usize::try_from(source_byte + 1).map_err(|error| error.to_string())?;
    let graphical = |position: u32| {
        (33..=126u8)
            .find(|&byte| {
                decode_profile_instruction(u32::from(byte), position)
                    == Some(b'o')
            })
            .ok_or("no inverse graphical no-op")
    };
    let first_seed = graphical(
        u32::try_from(target + 2).map_err(|error| error.to_string())?,
    )?;
    let second_seed = graphical(
        u32::try_from(target + 3).map_err(|error| error.to_string())?,
    )?;
    for profile in [current_profile(), historical_profile()] {
        let padded =
            layout::encode_auto_padded_forward_layout_with_loader_seed(
                profile,
                &logical,
                [first_seed, second_seed],
            )
            .map_err(|error| format!("jumped loader seed: {error:?}"))?;
        assert_eq!(padded.operations().len(), target + 4);
        assert_eq!(padded.logical_code_positions(), [
            0,
            target as u32,
            target as u32 + 1
        ]);
        assert_eq!(
            padded.source_cell_origins()[0],
            PaddedCellOrigin::Logical(0)
        );
        assert!(
            padded.source_cell_origins()[1..target]
                .iter()
                .all(|origin| { *origin == PaddedCellOrigin::SkippedPadding })
        );
        assert_eq!(
            padded.source_cell_origins()[target],
            PaddedCellOrigin::Logical(1)
        );
        assert_eq!(
            padded.source_cell_origins()[target + 1],
            PaddedCellOrigin::Logical(2)
        );
        assert_eq!(&padded.source_cell_origins()[target + 2..], &[
            PaddedCellOrigin::LoaderSeed,
            PaddedCellOrigin::LoaderSeed
        ],);
        verify_bidirectional_source_map(&padded)?;
        let mut vm = ProfileMachine::from_source(
            profile,
            padded.layout().source(),
            vec![0, 255],
        )
        .map_err(|error| format!("jumped guest load: {error:?}"))?;
        verify_execution_witness(&mut vm, padded.layout())?;
        assert_eq!(vm.input_consumed(), 0);
        assert!(vm.output().is_empty());
    }
    Ok(())
}

#[test]
fn final_relocation_before_halt_remains_safe_with_a_loader_seed()
-> Result<(), String> {
    // A trailing seed changes physical source length, not the last reached
    // instruction: j followed immediately by halt cannot alias a later read.
    let mut operations = vec![LinearOpcode::NoOperation; 130];
    operations[126] = LinearOpcode::RelocateDataPointer;
    operations[127] = LinearOpcode::Halt;
    for position in [128usize, 129] {
        let byte = (33..=126u8)
            .find(|&byte| {
                decode_profile_instruction(u32::from(byte), position as u32)
                    == Some(b'o')
            })
            .ok_or("missing source-loadable seed")?;
        operations[position] =
            LinearOpcode::SkippedDataByte { byte: u32::from(byte) };
    }
    for profile in [current_profile(), historical_profile()] {
        let without_seed = encode_linear_layout(profile, &operations[..128])
            .map_err(|error| format!("unseeded final relocation: {error:?}"))?;
        let with_seed = encode_linear_layout(profile, &operations)
            .map_err(|error| format!("seeded final relocation: {error:?}"))?;
        assert_eq!(&with_seed.source()[..128], without_seed.source());
        let logical: Vec<PaddedForwardStep> = operations[..128]
            .iter()
            .copied()
            .map(PaddedForwardStep::Instruction)
            .collect();
        let [
            LinearOpcode::SkippedDataByte { byte: first },
            LinearOpcode::SkippedDataByte { byte: second },
        ] = operations[128..]
        else {
            return Err(String::from("missing exact two-cell seed"));
        };
        let planned =
            layout::encode_auto_padded_forward_layout_with_loader_seed(
                profile,
                &logical,
                [first as u8, second as u8],
            )
            .map_err(|error| format!("padded final relocation: {error:?}"))?;
        assert_eq!(planned.layout(), &with_seed);
        assert_eq!(planned.logical_code_positions().len(), 128);
        assert_eq!(&planned.source_cell_origins()[128..], &[
            PaddedCellOrigin::LoaderSeed,
            PaddedCellOrigin::LoaderSeed,
        ]);
        verify_bidirectional_source_map(&planned)?;
        assert_eq!(with_seed.executed_code_positions().last(), Some(&127));
        assert_eq!(with_seed.data_pointer_positions()[126], 126);
        assert!(with_seed.data_pointer_positions()[127] < 130);
        assert_eq!(
            with_seed.data_write_positions().iter().flatten().count(),
            0
        );
        for source in [without_seed.source(), with_seed.source()] {
            let mut machine =
                ProfileMachine::from_source(profile, source, vec![255])
                    .map_err(|error| format!("guest load: {error}"))?;
            assert_eq!(
                machine.run(128),
                Ok(RunOutcome::Terminated {
                    reason: Termination::HaltInstruction,
                    steps: 128,
                })
            );
            assert_eq!(machine.input_consumed(), 0);
            assert!(machine.output().is_empty());
        }
    }
    Ok(())
}
