// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - LicenseRef-Proprietary
// Confidential:
//   - true
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Source-scratch data writes safely behind forward-only guest code.
// - Must-Not:
//   - Permit writes to pending instructions or falsify output/VM state.
// - Allows:
//   - Inputs: encoded graphical cells and a forward-jump machine trace.
//   - Outputs: exact in-source write positions and actual guest bytes.
//   - Side effects: bounded normative VM replays only.
// - Split-When:
//   - General self-modifying code placement has its own verifier.
// - Merge-When:
//   - A general layout verifier models source/data aliasing completely.
// - Summary:
//   - Writes to skipped, past source cells do not corrupt future code.

use super::*;

fn scratch_guest() -> Result<Vec<LinearOpcode>, String> {
    let target =
        usize::try_from(jump_target(0)?).map_err(|error| error.to_string())?;
    if target <= 5 {
        return Err(String::from("forward jump leaves insufficient scratch"));
    }
    let mut operations = vec![LinearOpcode::NoOperation; target + 5];
    operations[0] = LinearOpcode::JumpForward {
        target: u32::try_from(target).map_err(|error| error.to_string())?,
    };
    operations[target] = LinearOpcode::CrazyData;
    operations[target + 1] = LinearOpcode::OutputByte;
    operations[target + 2] = LinearOpcode::RotateData;
    operations[target + 3] = LinearOpcode::OutputByte;
    operations[target + 4] = LinearOpcode::Halt;
    Ok(operations)
}

#[test]
fn forward_jump_allows_source_scratch_arithmetic_behind_code()
-> Result<(), String> {
    let operations = scratch_guest()?;
    for profile in [current_profile(), historical_profile()] {
        let layout = encode_linear_layout(profile, &operations)
            .map_err(|error| format!("source-scratch layout: {error:?}"))?;
        assert_eq!(layout.data_write_positions()[1], Some(1));
        assert_eq!(layout.data_write_positions()[3], Some(3));
        assert_eq!(layout.executed_code_positions().len(), 6);
        let source = layout.source().to_vec();
        let first = malbolge::profile_crazy(
            u32::from(source[1]),
            0,
            profile.word_trits(),
        );
        let third = u32::from(source[3]);
        let rotated = third / 3
            + (third % 3) * (3u32.pow(u32::from(profile.word_trits()) - 1));
        let expected = [first as u8, rotated as u8];
        for input in [Vec::new(), vec![0, 255, 42]] {
            let mut vm = ProfileMachine::from_source(profile, &source, input)
                .map_err(|error| {
                format!("source-scratch VM load: {error:?}")
            })?;
            assert!(matches!(
                vm.run(6),
                Ok(RunOutcome::Terminated { steps: 6, .. })
            ));
            assert_eq!(vm.output(), expected);
            assert_eq!(vm.input_consumed(), 0);
            assert_ne!(
                vm.memory_word(1)
                    .map_err(|error| format!("scratch write: {error:?}"))?,
                u32::from(source[1])
            );
        }
        let mut forged = source.clone();
        forged[1] ^= 1;
        assert!(matches!(
            admit_linear_layout(
                profile,
                &operations,
                &forged,
                LinearProfileIdentity {
                    id: profile.id(),
                    fingerprint: profile.fingerprint(),
                },
            ),
            Err(LinearLayoutError::DecodeMismatch { position: 1 })
        ));
    }
    Ok(())
}

#[test]
fn source_scratch_refuses_writes_at_pending_code() {
    let profile = current_profile();
    let operations = [
        LinearOpcode::NoOperation,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::Halt,
    ];
    assert_eq!(
        encode_linear_layout(profile, &operations),
        Err(LinearLayoutError::UnsafeDataPlacement)
    );
}

#[test]
fn jump_encrypted_skip_cell_is_a_real_guest_operand() -> Result<(), String> {
    let profile = current_profile();
    let target =
        usize::try_from(jump_target(0)?).map_err(|error| error.to_string())?;
    let mut operations = vec![LinearOpcode::NoOperation; target + target + 1];
    operations[0] = LinearOpcode::JumpForward {
        target: u32::try_from(target).map_err(|error| error.to_string())?,
    };
    operations[target + target - 2] = LinearOpcode::RotateData;
    operations[target + target - 1] = LinearOpcode::OutputByte;
    operations[target + target] = LinearOpcode::Halt;
    let layout = encode_linear_layout(profile, &operations)
        .map_err(|error| format!("encrypted scratch layout: {error:?}"))?;
    let cell = u32::from(layout.source()[target - 1]);
    let encrypted =
        encrypt_profile_cell(cell).ok_or("missing jump encryption")?;
    let expected = malbolge::profile_rotate(encrypted, profile.memory_words());
    assert_eq!(
        layout.data_write_positions().iter().flatten().last(),
        Some(&(target as u32 - 1))
    );
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|error| format!("guest load: {error:?}"))?;
        assert!(matches!(
            vm.run(layout.executed_code_positions().len()),
            Ok(RunOutcome::Terminated { .. })
        ));
        assert_eq!(vm.output(), [expected as u8]);
        assert_eq!(
            vm.memory_word(target as u32 - 1)
                .map_err(|error| format!("guest scratch: {error:?}"))?,
            expected
        );
    }
    Ok(())
}

#[test]
fn skipped_graphical_data_requires_valid_loader_opcode_and_unreachable_cell()
-> Result<(), String> {
    let profile = current_profile();
    let target =
        usize::try_from(jump_target(0)?).map_err(|error| error.to_string())?;
    let mut operations = vec![LinearOpcode::NoOperation; target + 2];
    operations[0] = LinearOpcode::JumpForward {
        target: u32::try_from(target).map_err(|error| error.to_string())?,
    };
    operations[target] = LinearOpcode::OutputByte;
    operations[target + 1] = LinearOpcode::Halt;
    // ASCII '2' is graphical at address one but does not decode to a
    // legal source instruction. Never publish a guest the VM cannot load.
    operations[1] = LinearOpcode::SkippedDataByte { byte: 50 };
    assert_eq!(
        encode_linear_layout(profile, &operations),
        Err(LinearLayoutError::NoEncoding { position: 1 })
    );
    // Position one is not unreachable when no forward jump skips over it.
    let reachable = [
        LinearOpcode::NoOperation,
        LinearOpcode::SkippedDataByte { byte: 50 },
        LinearOpcode::Halt,
    ];
    assert_eq!(
        encode_linear_layout(profile, &reachable),
        Err(LinearLayoutError::JumpPathUnsupported)
    );
    Ok(())
}
