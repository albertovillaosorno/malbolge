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
