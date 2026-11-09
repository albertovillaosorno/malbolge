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
//   - Source-scratch proposal for an actual Fibonacci C output prefix.
// - Must-Not:
//   - Publish a host-computed byte trace without real guest VM output.
// - Allows:
//   - Inputs: independent unsigned recurrence bytes and code phases.
//   - Outputs: a verified forward-jump source and two real guest effects.
//   - Side effects: bounded normative VM replay only.
// - Split-When:
//   - General source-scratch linker work has separate ownership.
// - Merge-When:
//   - A general guest layout synthesizer proves this geometry.
// - Summary:
//   - A forward jump permits scratch writes to past code cells.

use super::super::{ProfileMachine, RunOutcome, pair_source_cells};
use super::*;

#[test]
fn fibonacci_prefix_uses_source_scratch_not_host_output() -> Result<(), String>
{
    let mut previous = 1u32;
    let mut current = 1u32;
    let mut expected = [0u8; 2];
    for byte in &mut expected {
        let next = (previous + current) & 255;
        *byte = u8::try_from(if next & 1 == 0 {
            next
        } else {
            next ^ 0x5a
        })
        .map_err(|error| error.to_string())?;
        previous = current;
        current = next;
    }
    assert_eq!(expected, [0x02, 0x59]);
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile).ok_or("missing decoder phases")?;
    let layout =
        verified_source_scratch_output_layout(profile, expected, &cells)
            .ok_or("source-scratch prefix proposal missed real C effects")?;
    assert!(layout.source().len() > 99);
    assert!(
        layout
            .data_write_positions()
            .iter()
            .flatten()
            .any(|&address| {
                usize::try_from(address)
                    .is_ok_and(|value| value < layout.source().len())
            })
    );
    for input in [Vec::new(), vec![0, 255, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|error| format!("guest load: {error:?}"))?;
        assert!(matches!(
            vm.run(layout.executed_code_positions().len()),
            Ok(RunOutcome::Terminated { .. })
        ));
        assert_eq!(vm.output(), expected);
        assert_eq!(vm.input_consumed(), 0);
    }
    Ok(())
}

#[test]
fn scratch_emits_third_byte_after_jump() -> Result<(), String> {
    let expected = [0x02, 0x59, 0x1b];
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile).ok_or("missing decoder phases")?;
    let layout =
        verified_source_scratch_output_layout(profile, expected, &cells)
            .ok_or("missing third guest effect")?;
    for input in [Vec::new(), vec![0, 255, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|error| format!("guest load: {error:?}"))?;
        assert!(matches!(
            vm.run(layout.executed_code_positions().len()),
            Ok(RunOutcome::Terminated { .. })
        ));
        assert_eq!(vm.output(), expected);
    }
    Ok(())
}

#[test]
fn variable_source_scratch_emits_masked_twelve_fibonacci_bytes()
-> Result<(), String> {
    let expected = [
        0x02, 0x19, 0x1f, 0x08, 0x17, 0x0f, 0x02, 0x0d, 0x03, 0x10, 0x13, 0x03,
    ];
    let profile = malbolge::current_profile();
    let layout = verified_variable_source_scratch_layout(profile, expected)
        .ok_or("missing twelve real masked Fibonacci effects")?;
    assert!(layout.source().len() > layout.executed_code_positions().len());
    assert!(
        layout
            .data_write_positions()
            .iter()
            .flatten()
            .any(|&write| write < layout.source().len() as u32)
    );
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|error| format!("guest load: {error:?}"))?;
        assert!(matches!(
            vm.run(layout.executed_code_positions().len()),
            Ok(RunOutcome::Terminated { .. })
        ));
        assert_eq!(vm.output(), expected);
    }
    Ok(())
}

#[test]
fn skipped_jump_and_input_codes_are_inert_guest_data() -> Result<(), String> {
    let profile = malbolge::current_profile();
    let first_jump = (33u8..=126)
        .find(|&byte| {
            malbolge::decode_profile_instruction(u32::from(byte), 0)
                == Some(b'i')
        })
        .ok_or("missing first jump")?;
    let target = u32::from(first_jump) + 1;
    for opcode in [b'i', profile.input_instruction()] {
        let operand = (33u8..=126)
            .find(|&byte| {
                malbolge::decode_profile_instruction(u32::from(byte), 1)
                    == Some(opcode)
            })
            .ok_or("missing loader-valid scratch word")?;
        let mut operations = vec![LinearOpcode::NoOperation; target as usize];
        operations[0] = LinearOpcode::JumpForward { target };
        operations[1] =
            LinearOpcode::SkippedDataByte { byte: u32::from(operand) };
        operations.extend([
            LinearOpcode::CrazyData,
            LinearOpcode::OutputByte,
            LinearOpcode::Halt,
        ]);
        let layout = super::super::encode_linear_layout(profile, &operations)
            .map_err(|error| format!("scratch layout: {error:?}"))?;
        assert_eq!(
            layout
                .data_write_positions()
                .iter()
                .flatten()
                .copied()
                .collect::<Vec<_>>(),
            [1]
        );
        let result = malbolge::profile_crazy(u32::from(operand), 0, 15) as u8;
        for input in [Vec::new(), vec![255, 0, 128]] {
            let mut vm =
                ProfileMachine::from_source(profile, layout.source(), input)
                    .map_err(|error| format!("guest load: {error:?}"))?;
            assert!(matches!(
                vm.run(layout.executed_code_positions().len()),
                Ok(RunOutcome::Terminated { .. })
            ));
            assert_eq!(vm.output(), [result]);
            assert_eq!(vm.input_consumed(), 0);
        }
    }
    Ok(())
}
