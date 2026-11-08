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
//   - VM oracle and bridge proposal proof for a live second guest relocation.
// - Must-Not:
//   - Substitute host output for actual Malbolge execution.
// - Allows:
//   - Inputs: source-independent real guest arithmetic and relocation.
//   - Outputs: independently verified guest bytes and typed layout.
//   - Side effects: bounded normative VM execution only.
// - Split-When:
//   - A general relocation graph synthesizer is available.
// - Merge-When:
//   - A complete guest byte-stream linker owns this proof.
// - Summary:
//   - A second j changes the data path between real output effects.

use super::super::{
    ProfileMachine, RunOutcome, encode_linear_layout, pair_source_cells,
    proposed_output_stream,
};
use super::*;

fn original_guest() -> Vec<LinearOpcode> {
    let mut instructions = vec![LinearOpcode::NoOperation; 8];
    instructions.extend([
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::RotateData,
        LinearOpcode::OutputByte,
        LinearOpcode::Halt,
    ]);
    instructions
}

#[test]
fn second_live_relocation_proposal_matches_real_guest_output()
-> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile).ok_or("missing decoder phases")?;
    let instructions = original_guest();
    let original = encode_linear_layout(profile, &instructions)
        .map_err(|error| format!("independent original guest: {error:?}"))?;
    let mut vm = ProfileMachine::from_source(profile, original.source(), vec![
        0x7f, 0x00,
    ])
    .map_err(|error| format!("independent VM load: {error:?}"))?;
    if !matches!(vm.run(instructions.len()),
        Ok(RunOutcome::Terminated { steps, .. }) if steps == instructions.len())
    {
        return Err(String::from("original guest did not halt"));
    }
    let expected: [u8; 2] = vm
        .output()
        .try_into()
        .map_err(|error| format!("original guest output: {error:?}"))?;
    if vm.input_consumed() != 0 {
        return Err(String::from("guest consumed supplied input"));
    }
    assert_eq!(expected, [0x36, 0x08]);
    let mut forged = expected;
    forged[1] ^= 1;
    assert!(
        verified_output_stream_layout(profile, &instructions, forged, &cells,)
            .is_none()
    );
    assert_eq!(
        proposed_output_stream(&instructions, &cells),
        Some(expected)
    );
    let recovered =
        verified_two_relocation_write_layout(profile, expected, &cells)
            .ok_or("bounded two-relocation proposal missed real guest")?;
    assert_eq!(
        recovered.data_pointer_positions().len(),
        recovered.source().len(),
    );
    assert_eq!(
        recovered
            .source()
            .iter()
            .enumerate()
            .filter(|(position, byte)| {
                malbolge::decode_profile_instruction(
                    u32::from(**byte),
                    u32::try_from(*position).unwrap_or(u32::MAX),
                ) == Some(b'j')
            })
            .count(),
        2,
    );
    let mut verified =
        ProfileMachine::from_source(profile, recovered.source(), vec![0x80])
            .map_err(|error| format!("recovered VM load: {error:?}"))?;
    let recovered_steps = recovered.source().len();
    if !matches!(verified.run(recovered_steps),
        Ok(RunOutcome::Terminated { steps, .. }) if steps == recovered_steps)
        || verified.output() != expected
        || verified.input_consumed() != 0
    {
        return Err(String::from("recovered two-j guest drifted"));
    }
    Ok(())
}

#[test]
fn second_relocation_after_two_guest_outputs_is_not_count_specific()
-> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile).ok_or("missing decoder phases")?;
    let mut operations = vec![LinearOpcode::NoOperation; 8];
    operations.extend([
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::RotateData,
        LinearOpcode::OutputByte,
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::Halt,
    ]);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(|error| format!("three-output oracle source: {error:?}"))?;
    let mut vm =
        ProfileMachine::from_source(profile, layout.source(), vec![0x7f])
            .map_err(|error| format!("three-output oracle VM: {error:?}"))?;
    if !matches!(vm.run(operations.len()),
        Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
    {
        return Err(String::from("three-output oracle did not halt"));
    }
    let expected: [u8; 3] = vm
        .output()
        .try_into()
        .map_err(|error| format!("three-output oracle bytes: {error:?}"))?;
    assert_eq!(proposed_output_stream(&operations, &cells), Some(expected));
    let recovered =
        verified_two_relocation_write_layout(profile, expected, &cells)
            .ok_or("two-j grammar failed three-output guest")?;
    assert_eq!(recovered.data_write_positions().iter().flatten().count(), 3);
    let mut replay =
        ProfileMachine::from_source(profile, recovered.source(), vec![
            255, 0, 128,
        ])
        .map_err(|error| format!("three-output replay: {error:?}"))?;
    let recovered_steps = recovered.source().len();
    if !matches!(replay.run(recovered_steps),
        Ok(RunOutcome::Terminated { steps, .. }) if steps == recovered_steps)
        || replay.output() != expected
        || replay.input_consumed() != 0
    {
        return Err(String::from("three-output guest replay drifted"));
    }
    Ok(())
}

#[test]
fn third_live_relocation_has_an_independent_proposal() -> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile).ok_or("missing graphical phases")?;
    let mut operations = vec![LinearOpcode::NoOperation; 8];
    operations.extend([
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::RotateData,
        LinearOpcode::OutputByte,
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::Halt,
    ]);
    // Build the original graphical program directly from decoder phases,
    // not by asking the layout checker under test to encode the guest.
    let original = operations
        .iter()
        .enumerate()
        .map(|(position, &operation)| {
            cells
                .get(position)
                .and_then(|phase| {
                    phase.get(super::super::pair_opcode_slot(operation)?)
                })
                .copied()
        })
        .collect::<Option<Vec<_>>>()
        .ok_or("missing positional source cell")?;
    let mut vm = ProfileMachine::from_source(profile, &original, vec![255, 0])
        .map_err(|error| format!("independent three-j load: {error:?}"))?;
    if !matches!(vm.run(operations.len()),
        Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
    {
        return Err(String::from("original three-j guest did not halt"));
    }
    let expected: [u8; 3] = vm
        .output()
        .try_into()
        .map_err(|error| format!("three-j output: {error:?}"))?;
    assert_eq!(expected, [0x51, 0xa2, 0xfe]);
    if vm.input_consumed() != 0 {
        return Err(String::from("three-j guest consumed stdin"));
    }
    assert_eq!(proposed_output_stream(&operations, &cells), Some(expected));
    let recovered =
        verified_three_relocation_write_layout(profile, expected, &cells)
            .ok_or("proposer missed independent live three-j guest")?;
    assert_eq!(recovered.data_write_positions().iter().flatten().count(), 3);
    assert_eq!(recovered.source(), original);
    let step_limit = recovered.source().len();
    for input in [Vec::new(), vec![0, 255, 1]] {
        let mut replay =
            ProfileMachine::from_source(profile, recovered.source(), input)
                .map_err(|error| format!("recovered guest load: {error:?}"))?;
        if !matches!(replay.run(step_limit),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == step_limit)
            || replay.output() != expected
            || replay.input_consumed() != 0
        {
            return Err(String::from("three-j recovered guest drifted"));
        }
    }
    let mut forged = expected;
    forged[2] ^= 1;
    assert!(
        verified_output_stream_layout(profile, &operations, forged, &cells)
            .is_none()
    );
    Ok(())
}

#[test]
fn third_relocation_after_two_effects_is_not_a_fixed_split()
-> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile).ok_or("missing graphical phases")?;
    let mut operations = Vec::new();
    operations.extend([
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::RotateData,
        LinearOpcode::OutputByte,
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::RotateData,
        LinearOpcode::OutputByte,
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::Halt,
    ]);
    let raw = operations
        .iter()
        .enumerate()
        .map(|(position, &operation)| {
            cells
                .get(position)
                .and_then(|phase| {
                    phase.get(super::super::pair_opcode_slot(operation)?)
                })
                .copied()
        })
        .collect::<Option<Vec<_>>>()
        .ok_or("missing positional source byte")?;
    let mut oracle = ProfileMachine::from_source(profile, &raw, Vec::new())
        .map_err(|error| format!("original five-output VM: {error:?}"))?;
    if !matches!(oracle.run(raw.len()),
        Ok(RunOutcome::Terminated { steps, .. }) if steps == raw.len())
    {
        return Err(String::from("original five-output VM did not halt"));
    }
    let expected: [u8; 5] = oracle
        .output()
        .try_into()
        .map_err(|error| format!("five source bytes: {error:?}"))?;
    assert_eq!(expected, [0x54, 0x08, 0xa7, 0xb1, 0xbc]);
    let original =
        verified_output_stream_layout(profile, &operations, expected, &cells)
            .ok_or("five-byte source failed independent layout proof")?;
    assert_eq!(original.source(), raw);
    assert_eq!(original.data_write_positions().iter().flatten().count(), 5);
    let recovered =
        verified_three_relocation_write_layout(profile, expected, &cells)
            .ok_or("three-j grammar missed a later split")?;
    let jumps = recovered
        .source()
        .iter()
        .enumerate()
        .filter(|(position, byte)| {
            malbolge::decode_profile_instruction(
                u32::from(**byte),
                u32::try_from(*position).unwrap_or(u32::MAX),
            ) == Some(b'j')
        })
        .count();
    assert_eq!(jumps, 3);
    assert_eq!(recovered.data_write_positions().iter().flatten().count(), 5);
    let guest_steps = recovered.source().len();
    for data in [Vec::new(), vec![0, 255]] {
        let mut guest =
            ProfileMachine::from_source(profile, recovered.source(), data)
                .map_err(|error| {
                    format!("five-output replay load: {error:?}")
                })?;
        assert!(matches!(guest.run(guest_steps),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == guest_steps));
        assert_eq!(guest.output(), expected);
        assert_eq!(guest.input_consumed(), 0);
    }
    Ok(())
}

#[test]
fn fourth_live_relocation_reconstructs_independent_guest() -> Result<(), String>
{
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile).ok_or("missing graphical phases")?;
    let mut operations = Vec::new();
    for index in 0..4 {
        operations.extend([
            LinearOpcode::RelocateDataPointer,
            if index % 2 == 0 {
                LinearOpcode::CrazyData
            } else {
                LinearOpcode::RotateData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    // Encode the original guest from public decoder phases, not the search
    // algorithm whose output is under test.
    let source = operations
        .iter()
        .enumerate()
        .map(|(position, &operation)| {
            cells
                .get(position)
                .and_then(|phase| {
                    phase.get(super::super::pair_opcode_slot(operation)?)
                })
                .copied()
        })
        .collect::<Option<Vec<_>>>()
        .ok_or("missing positional fourth-j byte")?;
    let mut oracle =
        ProfileMachine::from_source(profile, &source, vec![255])
            .map_err(|error| format!("four-j guest load: {error:?}"))?;
    if !matches!(oracle.run(source.len()),
        Ok(RunOutcome::Terminated { steps, .. }) if steps == source.len())
    {
        return Err(String::from("four-j guest did not halt"));
    }
    let expected: [u8; 4] = oracle
        .output()
        .try_into()
        .map_err(|error| format!("four-j output: {error:?}"))?;
    assert_eq!(oracle.input_consumed(), 0);
    assert_eq!(expected, [0x38, 0x17, 0x2a, 0x2a]);
    let recovered =
        verified_four_relocation_write_layout(profile, expected, &cells)
            .ok_or("four-j guest missing from multi-region proposal")?;
    assert_eq!(recovered.source(), source);
    assert_eq!(recovered.data_write_positions().iter().flatten().count(), 4);
    let count = recovered
        .source()
        .iter()
        .enumerate()
        .filter(|(position, byte)| {
            malbolge::decode_profile_instruction(
                u32::from(**byte),
                u32::try_from(*position).unwrap_or(u32::MAX),
            ) == Some(b'j')
        })
        .count();
    assert_eq!(count, 4);
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut replay =
            ProfileMachine::from_source(profile, recovered.source(), input)
                .map_err(|error| format!("four-j replay load: {error:?}"))?;
        assert!(matches!(replay.run(source.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == source.len()));
        assert_eq!(replay.output(), expected);
        assert_eq!(replay.input_consumed(), 0);
    }
    let mut forged = expected;
    forged[3] ^= 1;
    assert!(
        verified_output_stream_layout(profile, &operations, forged, &cells)
            .is_none()
    );
    Ok(())
}

#[test]
fn fourth_relocation_after_multiple_outputs_is_not_a_fixed_split()
-> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile).ok_or("missing decoder phases")?;
    let mut operations = vec![LinearOpcode::RelocateDataPointer];
    for index in 0..5 {
        if matches!(index, 1 | 2 | 4) {
            operations.push(LinearOpcode::RelocateDataPointer);
        }
        operations.extend([
            if index % 2 == 0 {
                LinearOpcode::CrazyData
            } else {
                LinearOpcode::RotateData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    let raw = operations
        .iter()
        .enumerate()
        .map(|(position, &operation)| {
            cells
                .get(position)
                .and_then(|phase| {
                    phase.get(super::super::pair_opcode_slot(operation)?)
                })
                .copied()
        })
        .collect::<Option<Vec<_>>>()
        .ok_or("missing fourth-j source phase")?;
    let mut oracle = ProfileMachine::from_source(profile, &raw, Vec::new())
        .map_err(|error| format!("five-output oracle load: {error:?}"))?;
    assert!(matches!(oracle.run(raw.len()),
        Ok(RunOutcome::Terminated { steps, .. }) if steps == raw.len()));
    let expected: [u8; 5] = oracle
        .output()
        .try_into()
        .map_err(|error| format!("five-output bytes: {error:?}"))?;
    assert_eq!(expected, [0x35, 0x08, 0xdc, 0x08, 0xa3]);
    assert_eq!(proposed_output_stream(&operations, &cells), Some(expected));
    let recovered =
        verified_four_relocation_write_layout(profile, expected, &cells)
            .ok_or("four-j later-split grammar missed independent source")?;
    assert_eq!(recovered.source(), raw);
    assert_eq!(recovered.data_write_positions().iter().flatten().count(), 5);
    let jumps = recovered
        .source()
        .iter()
        .enumerate()
        .filter(|(position, byte)| {
            malbolge::decode_profile_instruction(
                u32::from(**byte),
                u32::try_from(*position).unwrap_or(u32::MAX),
            ) == Some(b'j')
        })
        .count();
    assert_eq!(jumps, 4);
    for input in [Vec::new(), vec![0, 128, 255]] {
        let mut vm =
            ProfileMachine::from_source(profile, recovered.source(), input)
                .map_err(|error| {
                    format!("five-output replay load: {error:?}")
                })?;
        assert!(matches!(vm.run(raw.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == raw.len()));
        assert_eq!(vm.output(), expected);
        assert_eq!(vm.input_consumed(), 0);
    }
    Ok(())
}

#[test]
fn split_relocation_with_nonpaired_effects_reconstructs_guest()
-> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile).ok_or("missing source cells")?;
    // An independent twelve-effect guest with two live relocations, one
    // repeated output and a no-op stride between guest data writes.
    let prefix = 8;
    let mut operations = vec![LinearOpcode::NoOperation; prefix];
    operations.extend([
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::OutputByte,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::RotateData,
        LinearOpcode::OutputByte,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::NoOperation,
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::RotateData,
        LinearOpcode::OutputByte,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::RotateData,
        LinearOpcode::OutputByte,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::NoOperation,
        LinearOpcode::Halt,
    ]);
    let mut expanded = vec![LinearOpcode::NoOperation; prefix];
    for (index, &operation) in operations[prefix..].iter().enumerate() {
        expanded.push(operation);
        if index % 3 == 0
            && matches!(
                operation,
                LinearOpcode::CrazyData
                    | LinearOpcode::RotateData
                    | LinearOpcode::OutputByte
            )
        {
            expanded.push(LinearOpcode::NoOperation);
        }
    }
    operations = expanded;
    let original_source = operations
        .iter()
        .enumerate()
        .map(|(position, &opcode)| {
            cells
                .get(position)
                .and_then(|cell| {
                    cell.get(super::super::pair_opcode_slot(opcode)?)
                })
                .copied()
        })
        .collect::<Option<Vec<_>>>()
        .ok_or("original source position decoder")?;
    let mut guest =
        ProfileMachine::from_source(profile, &original_source, vec![255, 0])
            .map_err(|error| format!("original VM loader: {error:?}"))?;
    if !matches!(guest.run(operations.len()),
        Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
    {
        return Err(String::from("independent source did not halt"));
    }
    let expected: [u8; 12] = guest
        .output()
        .try_into()
        .map_err(|error| format!("original output count: {error:?}"))?;
    if expected
        != [
            0x36, 0x36, 0x01, 0xfe, 0xa2, 0x0e, 0x28, 0xfe, 0xb1, 0x85, 0xfe,
            0xb1,
        ]
    {
        return Err(format!(
            "independent guest output changed: {expected:02x?}"
        ));
    }
    let end_to_end = verified_short_output_layout(profile, expected, &cells)
        .ok_or("public stream search did not find new guest geometry")?;
    if end_to_end.source().is_empty() {
        return Err(String::from("public search returned empty guest"));
    }
    let writes: Vec<_> = end_to_end
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() < 2
        || writes
            .iter()
            .any(|&address| address < end_to_end.source().len() as u32)
    {
        return Err(String::from("split search did not prove guest writes"));
    }
    let decoded = end_to_end
        .source()
        .iter()
        .enumerate()
        .map(|(position, &byte)| {
            [
                LinearOpcode::NoOperation,
                LinearOpcode::RelocateDataPointer,
                LinearOpcode::CrazyData,
                LinearOpcode::RotateData,
                LinearOpcode::OutputByte,
                LinearOpcode::Halt,
            ]
            .into_iter()
            .find(|&op| {
                super::super::pair_opcode_slot(op).and_then(|slot| {
                    cells
                        .get(position)
                        .and_then(|phase| phase.get(slot))
                        .copied()
                }) == Some(byte)
            })
        })
        .collect::<Option<Vec<_>>>()
        .ok_or("recovered source does not decode")?;
    if decoded
        .iter()
        .filter(|&&op| op == LinearOpcode::RelocateDataPointer)
        .count()
        != 2
    {
        return Err(String::from(
            "split search omitted the live second relocation",
        ));
    }
    let mut forged = expected;
    forged[0] ^= 1;
    if verified_output_stream_layout(profile, &decoded, forged, &cells)
        .is_some()
    {
        return Err(String::from("forged guest output admitted"));
    }
    Ok(())
}
