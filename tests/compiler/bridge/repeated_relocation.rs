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

#[test]
fn third_live_relocation_between_nonpaired_byte_effects() -> Result<(), String>
{
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile).ok_or("missing source cells")?;
    // Source-independent guest: repeated outputs and no-op data strides
    // occur inside three separate live relocation regions.
    let mut operations = vec![LinearOpcode::NoOperation; 8];
    operations.extend([
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::OutputByte,
        LinearOpcode::RotateData,
        LinearOpcode::OutputByte,
        LinearOpcode::NoOperation,
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::OutputByte,
        LinearOpcode::NoOperation,
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::RotateData,
        LinearOpcode::OutputByte,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::NoOperation,
        LinearOpcode::Halt,
    ]);
    let source = operations
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
        .ok_or("guest source decoder")?;
    let mut guest = ProfileMachine::from_source(profile, &source, vec![255, 0])
        .map_err(|error| format!("original guest load: {error:?}"))?;
    if !matches!(guest.run(operations.len()),
        Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
    {
        return Err(String::from("original guest did not halt"));
    }
    let expected: [u8; 9] = guest
        .output()
        .try_into()
        .map_err(|error| format!("original output count: {error:?}"))?;
    assert_eq!(expected, [
        0x41, 0x41, 0x11, 0x30, 0x17, 0x17, 0x2c, 0x18, 0x35
    ]);
    if guest.input_consumed() != 0 {
        return Err(String::from("original guest consumed supplied input"));
    }
    let recovered = verified_three_split_relocation_output_layout(
        profile, expected, &cells,
    )
    .ok_or("bounded three-region fallback did not recover guest")?;
    let relocations = recovered
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
    if relocations < 3 {
        return Err(format!(
            "expected three live relocations, recovered {relocations}"
        ));
    }
    let mut forged = expected;
    forged[0] ^= 1;
    if verified_output_stream_layout(profile, &operations, forged, &cells)
        .is_some()
    {
        return Err(String::from("forged output passed independent verifier"));
    }
    Ok(())
}

#[test]
fn three_region_search_recovers_uneven_noop_strides() -> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile).ok_or("missing source decoder")?;
    // A complete nine-effect guest with no-op strides concentrated before
    // the first split, rather than the balanced fallback's fixed regions.
    let mut operations = vec![LinearOpcode::NoOperation; 8];
    operations.extend([
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::OutputByte,
        LinearOpcode::RotateData,
        LinearOpcode::OutputByte,
        LinearOpcode::NoOperation,
        LinearOpcode::NoOperation,
        LinearOpcode::NoOperation,
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::OutputByte,
        LinearOpcode::NoOperation,
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::RotateData,
        LinearOpcode::OutputByte,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::NoOperation,
        LinearOpcode::Halt,
    ]);
    assert_eq!(operations.len(), 33);
    let source = operations
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
        .ok_or("independent graphical source")?;
    let mut oracle =
        ProfileMachine::from_source(profile, &source, vec![255, 0])
            .map_err(|error| format!("original guest load: {error:?}"))?;
    assert!(matches!(oracle.run(source.len()),
        Ok(RunOutcome::Terminated { steps, .. }) if steps == source.len()));
    let expected: [u8; 9] = oracle
        .output()
        .try_into()
        .map_err(|error| format!("guest output: {error:?}"))?;
    assert_eq!(expected, [
        0x35, 0x35, 0x86, 0xaf, 0x8f, 0x8f, 0xb5, 0x83, 0xc4
    ]);
    assert_eq!(oracle.input_consumed(), 0);
    let original =
        verified_output_stream_layout(profile, &operations, expected, &cells)
            .ok_or("independent positional guest proof failed")?;
    assert_eq!(original.source(), source);
    let recovered = verified_three_split_relocation_output_layout(
        profile, expected, &cells,
    )
    .ok_or_else(|| {
        format!("missed uneven three-region guest {expected:02x?}")
    })?;
    assert_eq!(recovered.source().len(), 33);
    let relocations = recovered
        .source()
        .iter()
        .enumerate()
        .filter(|(pos, byte)| {
            malbolge::decode_profile_instruction(
                u32::from(**byte),
                u32::try_from(*pos).unwrap_or(u32::MAX),
            ) == Some(b'j')
        })
        .count();
    assert_eq!(relocations, 3);
    for supplied in [Vec::new(), vec![0, 255, 1]] {
        let mut vm =
            ProfileMachine::from_source(profile, recovered.source(), supplied)
                .map_err(|error| format!("recovered VM load: {error:?}"))?;
        let limit = recovered.source().len();
        assert!(matches!(vm.run(limit),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == limit));
        assert_eq!(vm.output(), expected);
        assert_eq!(vm.input_consumed(), 0);
    }
    let mut forged = expected;
    forged[0] ^= 1;
    assert!(
        verified_output_stream_layout(profile, &operations, forged, &cells)
            .is_none()
    );
    Ok(())
}

#[test]
fn three_regions_recover_zero_output_before_first_relocation()
-> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells =
        pair_source_cells(profile).ok_or("missing positional decoder")?;
    // A full guest emits zero while A is still zero, then uses three live
    // data regions. Source bytes are derived from decoder phases, not search.
    let mut operations = vec![LinearOpcode::OutputByte];
    operations.extend([LinearOpcode::NoOperation; 7]);
    operations.extend([
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::OutputByte,
        LinearOpcode::RotateData,
        LinearOpcode::OutputByte,
        LinearOpcode::NoOperation,
        LinearOpcode::NoOperation,
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::OutputByte,
        LinearOpcode::NoOperation,
        LinearOpcode::NoOperation,
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::RotateData,
        LinearOpcode::OutputByte,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::NoOperation,
        LinearOpcode::NoOperation,
        LinearOpcode::Halt,
    ]);
    assert_eq!(operations.len(), 34);
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
        .ok_or("missing independent source bytes")?;
    let mut oracle =
        ProfileMachine::from_source(profile, &original, vec![1, 255])
            .map_err(|error| format!("independent guest VM: {error:?}"))?;
    assert!(matches!(oracle.run(operations.len()),
        Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len()));
    let expected: [u8; 10] = oracle
        .output()
        .try_into()
        .map_err(|error| format!("independent output: {error:?}"))?;
    assert_eq!(expected, [
        0, 0x3e, 0x3e, 0x2e, 0x0a, 0x3d, 0x3d, 0x10, 0x40, 0x19
    ]);
    assert_eq!(oracle.input_consumed(), 0);
    assert!(
        verified_output_stream_layout(profile, &operations, expected, &cells)
            .is_some(),
        "independent guest layout refused"
    );
    let recovered = verified_three_split_relocation_output_layout(
        profile, expected, &cells,
    )
    .ok_or_else(|| {
        format!("missed source-proven zero prefix {expected:02x?}")
    })?;
    assert_eq!(
        recovered.source().first(),
        original.first(),
        "initial guest zero-output instruction not reconstructed"
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
        3,
    );
    let source_length = u32::try_from(recovered.source().len())
        .map_err(|error| format!("source length conversion: {error:?}"))?;
    assert!(
        recovered
            .data_write_positions()
            .iter()
            .flatten()
            .all(|&address| address >= source_length)
    );
    for supplied in [Vec::new(), vec![0, 255, 1]] {
        let mut replay =
            ProfileMachine::from_source(profile, recovered.source(), supplied)
                .map_err(|error| format!("recovered guest load: {error:?}"))?;
        let step_limit = recovered.source().len();
        assert!(matches!(replay.run(step_limit),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == step_limit));
        assert_eq!(replay.output(), expected);
        assert_eq!(replay.input_consumed(), 0);
    }
    let mut forged = expected;
    forged[0] ^= 1;
    assert!(
        verified_output_stream_layout(profile, &operations, forged, &cells)
            .is_none()
    );
    Ok(())
}

#[test]
fn two_regions_recover_compact_guest_with_early_zero_output()
-> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile).ok_or("missing source decoder")?;
    // Independently encode a short real guest: zero output occurs before
    // any relocation, followed by repeated and distinct data-region bytes.
    let mut operations = vec![LinearOpcode::OutputByte];
    operations.extend([LinearOpcode::NoOperation; 7]);
    operations.extend([
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::OutputByte,
        LinearOpcode::RotateData,
        LinearOpcode::OutputByte,
        LinearOpcode::NoOperation,
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::NoOperation,
        LinearOpcode::Halt,
    ]);
    assert_eq!(operations.len(), 22);
    let raw = operations
        .iter()
        .enumerate()
        .map(|(position, &opcode)| {
            cells
                .get(position)
                .and_then(|phase| {
                    phase.get(super::super::pair_opcode_slot(opcode)?)
                })
                .copied()
        })
        .collect::<Option<Vec<_>>>()
        .ok_or("missing independent decoder cell")?;
    let mut oracle = ProfileMachine::from_source(profile, &raw, vec![255])
        .map_err(|error| format!("source guest VM load: {error:?}"))?;
    assert!(matches!(oracle.run(raw.len()),
        Ok(RunOutcome::Terminated { steps, .. }) if steps == raw.len()));
    let expected: [u8; 6] = oracle
        .output()
        .try_into()
        .map_err(|error| format!("source guest output: {error:?}"))?;
    assert_eq!(expected, [0, 0x53, 0x53, 0x42, 0x39, 0x38]);
    assert_eq!(oracle.input_consumed(), 0);
    assert!(
        verified_output_stream_layout(profile, &operations, expected, &cells)
            .is_some()
    );
    let recovered =
        verified_split_relocation_output_layout(profile, expected, &cells)
            .ok_or_else(|| {
                format!("two-region search missed guest: {expected:02x?}")
            })?;
    assert_eq!(recovered.source().first(), raw.first());
    assert!(recovered.source().len() <= raw.len());
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
    let length = u32::try_from(recovered.source().len())
        .map_err(|error| format!("source length conversion: {error:?}"))?;
    assert!(
        recovered
            .data_write_positions()
            .iter()
            .flatten()
            .all(|&address| address >= length)
    );
    let mut forged = expected;
    forged[0] ^= 1;
    assert!(
        verified_output_stream_layout(profile, &operations, forged, &cells)
            .is_none()
    );
    for input in [Vec::new(), vec![0, 128, 255]] {
        let mut guest =
            ProfileMachine::from_source(profile, recovered.source(), input)
                .map_err(|error| format!("recovered VM load: {error:?}"))?;
        let steps = recovered.source().len();
        assert!(matches!(
            guest.run(steps),
            Ok(RunOutcome::Terminated { steps: actual, .. }) if actual == steps
        ));
        assert_eq!(guest.output(), expected);
        assert_eq!(guest.input_consumed(), 0);
    }
    Ok(())
}

#[test]
fn three_regions_recover_short_repeated_output_guest() -> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile).ok_or("missing source phases")?;
    // Build a source-independent 27-cell guest with three live j moves.
    // An initial zero and repeated outputs remove required arithmetic writes.
    let mut operations = vec![LinearOpcode::OutputByte];
    operations.extend([LinearOpcode::NoOperation; 7]);
    operations.extend([
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::OutputByte,
        LinearOpcode::RotateData,
        LinearOpcode::OutputByte,
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::OutputByte,
        LinearOpcode::RotateData,
        LinearOpcode::OutputByte,
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::RotateData,
        LinearOpcode::OutputByte,
        LinearOpcode::NoOperation,
        LinearOpcode::Halt,
    ]);
    assert_eq!(operations.len(), 27);
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
        .ok_or("missing independent source encoding")?;
    let mut oracle = ProfileMachine::from_source(profile, &raw, vec![255])
        .map_err(|error| format!("guest VM load: {error:?}"))?;
    assert!(matches!(oracle.run(raw.len()),
        Ok(RunOutcome::Terminated { steps, .. }) if steps == raw.len()));
    let expected: [u8; 9] = oracle
        .output()
        .try_into()
        .map_err(|error| format!("independent guest bytes: {error:?}"))?;
    assert_eq!(expected, [
        0, 0x38, 0x38, 0x82, 0xce, 0xce, 0xc6, 0x7b, 0x8b
    ]);
    assert_eq!(oracle.input_consumed(), 0);
    assert!(
        verified_output_stream_layout(profile, &operations, expected, &cells)
            .is_some(),
        "real guest failed independent positional/source-disjoint admission"
    );
    let recovered = verified_three_split_relocation_output_layout(
        profile, expected, &cells,
    )
    .ok_or_else(|| format!("missed short 3-region guest {expected:02x?}"))?;
    assert!(
        recovered.source().len() <= raw.len(),
        "short valid geometry was not considered"
    );
    assert_eq!(recovered.source().first(), raw.first());
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
        3,
    );
    let length = u32::try_from(recovered.source().len())
        .map_err(|error| format!("guest length: {error:?}"))?;
    assert!(
        recovered
            .data_write_positions()
            .iter()
            .flatten()
            .all(|&address| address >= length)
    );
    for input in [Vec::new(), vec![0, 255, 128]] {
        let mut replay =
            ProfileMachine::from_source(profile, recovered.source(), input)
                .map_err(|error| format!("recovered VM load: {error:?}"))?;
        let step_limit = recovered.source().len();
        assert!(matches!(replay.run(step_limit),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == step_limit));
        assert_eq!(replay.output(), expected);
        assert_eq!(replay.input_consumed(), 0);
    }
    let mut forged = expected;
    forged[1] ^= 1;
    assert!(
        verified_output_stream_layout(profile, &operations, forged, &cells)
            .is_none()
    );
    Ok(())
}

// A compact source-independent guest with three unequal relocation regions.
// Keep its construction separate from the proposal under test.
fn unbalanced_three_region_source() -> Vec<LinearOpcode> {
    let mut operations = vec![LinearOpcode::OutputByte];
    operations.extend([LinearOpcode::NoOperation; 7]);
    operations.extend([
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::OutputByte,
        LinearOpcode::RotateData,
        LinearOpcode::OutputByte,
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::NoOperation,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::OutputByte,
        LinearOpcode::RotateData,
        LinearOpcode::OutputByte,
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::RotateData,
        LinearOpcode::OutputByte,
        LinearOpcode::NoOperation,
        LinearOpcode::Halt,
    ]);
    operations
}

type UnbalancedGuestEvidence = ([u8; 9], Vec<u8>);

fn unbalanced_guest_oracle(
    profile: &'static ProfileDescriptor,
    operations: &[LinearOpcode],
    cells: &[[u8; 6]],
) -> Result<UnbalancedGuestEvidence, String> {
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
        .ok_or("missing independently encoded source")?;
    let mut oracle = ProfileMachine::from_source(profile, &raw, vec![255])
        .map_err(|error| format!("guest VM load: {error:?}"))?;
    if !matches!(oracle.run(raw.len()),
        Ok(RunOutcome::Terminated { steps, .. }) if steps == raw.len())
    {
        return Err(String::from("independent guest did not halt"));
    }
    let expected: [u8; 9] = oracle
        .output()
        .try_into()
        .map_err(|error| format!("independent output: {error:?}"))?;
    if oracle.input_consumed() != 0 {
        return Err(String::from("independent guest consumed stdin"));
    }
    Ok((expected, raw))
}

fn verify_unbalanced_recovery(
    profile: &'static ProfileDescriptor,
    expected: [u8; 9],
    raw: &[u8],
    cells: &[[u8; 6]],
) -> Result<(), String> {
    let recovered =
        verified_three_split_relocation_output_layout(profile, expected, cells)
            .ok_or_else(|| {
                format!("missed unequal-split guest {expected:02x?}")
            })?;
    if recovered.source().len() > raw.len()
        || recovered.source().first() != raw.first()
    {
        return Err(String::from("compact zero-output source not recovered"));
    }
    let source_length = u32::try_from(recovered.source().len())
        .map_err(|error| format!("guest source length: {error:?}"))?;
    let relocations = recovered
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
    if relocations != 3
        || recovered
            .data_write_positions()
            .iter()
            .flatten()
            .any(|&address| address < source_length)
    {
        return Err(String::from("relocation or guest data overlap"));
    }
    for input in [Vec::new(), vec![0, 255, 128]] {
        let mut replay =
            ProfileMachine::from_source(profile, recovered.source(), input)
                .map_err(|error| format!("recovered VM load: {error:?}"))?;
        let step_limit = recovered.source().len();
        if !matches!(replay.run(step_limit),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == step_limit)
            || replay.output() != expected
            || replay.input_consumed() != 0
        {
            return Err(String::from("normative guest replay mismatch"));
        }
    }
    Ok(())
}

fn validate_unbalanced_guest() -> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile).ok_or("missing source phases")?;
    // j at positions 8, 14 and 21; extra no-op before the second write.
    let operations = unbalanced_three_region_source();
    if operations.len() != 28 {
        return Err(String::from("unexpected independent source length"));
    }
    let (expected, raw) =
        unbalanced_guest_oracle(profile, &operations, &cells)?;
    if expected != [0, 0x50, 0x50, 0x3f, 0x36, 0x36, 0x3f, 0, 0x12]
        || proposed_output_stream(&operations, &cells) != Some(expected)
        || verified_output_stream_layout(profile, &operations, expected, &cells)
            .is_none()
    {
        return Err(String::from("source-independent byte proof failed"));
    }
    let mut forged = expected;
    forged[4] ^= 1;
    if verified_output_stream_layout(profile, &operations, forged, &cells)
        .is_some()
    {
        return Err(String::from("forged guest transcript admitted"));
    }
    verify_unbalanced_recovery(profile, expected, &raw, &cells)
}

#[test]
fn three_regions_recover_unbalanced_source_geometry() {
    assert_eq!(validate_unbalanced_guest(), Ok(()));
}

#[test]
fn four_regions_recover_nonpaired_guest_outputs() -> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile).ok_or("missing source phases")?;
    // The fourth live j separates two real arithmetic/output regions;
    // several outputs reuse A instead of requiring paired arithmetic.
    let mut operations = unbalanced_three_region_source();
    operations.insert(19, LinearOpcode::RelocateDataPointer);
    assert_eq!(operations.len(), 29);
    let original = encode_linear_layout(profile, &operations)
        .map_err(|error| format!("independent four-j layout: {error:?}"))?;
    let mut vm = ProfileMachine::from_source(profile, original.source(), vec![
        255, 0, 128,
    ])
    .map_err(|error| format!("independent guest load: {error:?}"))?;
    assert!(matches!(vm.run(operations.len()),
        Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len()));
    assert_eq!(vm.input_consumed(), 0);
    let expected: [u8; 9] = vm
        .output()
        .try_into()
        .map_err(|error| format!("independent guest outputs: {error:?}"))?;
    assert_eq!(proposed_output_stream(&operations, &cells), Some(expected));
    assert!(
        verified_output_stream_layout(profile, &operations, expected, &cells)
            .is_some(),
        "four-region original failed independent guest verification"
    );
    let geometry = SearchGeometry {
        memory: &[],
        prefix: 8,
        prefix_outputs: 1,
        source_length: 29,
    };
    let splits = [14, 19, 22];
    let spec = SplitSearchSpec {
        geometry: &geometry,
        additional_relocations: &splits,
        terminal: TerminalSuffix::Noop,
        step_budget: 32_768,
    };
    let recovered =
        proposed_split_geometry_with_budget(profile, &cells, spec, expected)
            .ok_or_else(|| {
                format!(
                    "missed independently valid four-j stream {expected:02x?}"
                )
            })?;
    let verified = verified_output_stream_layout(
        profile, &recovered, expected, &cells,
    )
    .ok_or("four-j proposal failed independent output and layout admission")?;
    assert_eq!(
        recovered
            .iter()
            .filter(|&&op| op == LinearOpcode::RelocateDataPointer)
            .count(),
        4
    );
    for input in [Vec::new(), vec![0, 255, 128]] {
        let mut replay =
            ProfileMachine::from_source(profile, verified.source(), input)
                .map_err(|error| format!("recovered VM load: {error:?}"))?;
        assert!(matches!(
            replay.run(recovered.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == recovered.len()
        ));
        assert_eq!(replay.output(), expected);
        assert_eq!(replay.input_consumed(), 0);
    }
    let published =
        verified_four_split_relocation_output_layout(profile, expected, &cells)
            .ok_or("production four-region fallback missed verified guest")?;
    assert_eq!(
        published
            .source()
            .iter()
            .enumerate()
            .filter(|(index, byte)| {
                malbolge::decode_profile_instruction(
                    u32::from(**byte),
                    u32::try_from(*index).unwrap_or(u32::MAX),
                ) == Some(b'j')
            })
            .count(),
        4
    );
    let mut forged = expected;
    forged[4] ^= 1;
    assert!(
        verified_output_stream_layout(profile, &operations, forged, &cells)
            .is_none()
    );
    Ok(())
}

#[test]
fn four_regions_recover_nonzero_first_reused_outputs() -> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile).ok_or("missing source phases")?;
    // Move the initial zero output into an existing read-only data stride.
    // This preserves nine real guest outputs and four live j instructions,
    // but the first observable byte now comes from a relocated data write.
    let mut operations = unbalanced_three_region_source();
    operations.insert(19, LinearOpcode::RelocateDataPointer);
    assert_eq!(operations.len(), 29);
    assert_eq!(operations[0], LinearOpcode::OutputByte);
    assert_eq!(operations[15], LinearOpcode::NoOperation);
    operations[0] = LinearOpcode::NoOperation;
    operations[15] = LinearOpcode::OutputByte;
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
        .ok_or("missing positional guest source")?;
    let mut original =
        ProfileMachine::from_source(profile, &raw, Vec::new())
            .map_err(|error| format!("original VM load: {error:?}"))?;
    assert!(matches!(original.run(raw.len()),
        Ok(RunOutcome::Terminated { steps, .. }) if steps == raw.len()));
    let expected: [u8; 9] = original
        .output()
        .try_into()
        .map_err(|error| format!("original VM output: {error:?}"))?;
    assert_eq!(expected, [
        0x42, 0x42, 0x03, 0x03, 0xb7, 0xb7, 0xff, 0xb9, 0xa9
    ]);
    assert_eq!(original.input_consumed(), 0);
    assert_eq!(proposed_output_stream(&operations, &cells), Some(expected));
    assert!(
        verified_output_stream_layout(profile, &operations, expected, &cells)
            .is_some(),
        "independent four-region source rejected"
    );
    let layout =
        verified_four_split_relocation_output_layout(profile, expected, &cells)
            .ok_or("nonzero-first four-region search missed real guest")?;
    assert_eq!(layout.source().len(), 29);
    let decoded = layout
        .source()
        .iter()
        .enumerate()
        .map(|(index, &byte)| {
            malbolge::decode_profile_instruction(
                u32::from(byte),
                u32::try_from(index).unwrap_or(u32::MAX),
            )
        })
        .collect::<Vec<_>>();
    assert_eq!(decoded.iter().filter(|&&op| op == Some(b'j')).count(), 4);
    assert!(
        layout
            .data_write_positions()
            .iter()
            .flatten()
            .all(|&address| {
                usize::try_from(address).is_ok_and(|value| value >= raw.len())
            })
    );
    for supplied in [Vec::new(), vec![255, 0, 128]] {
        let mut replay =
            ProfileMachine::from_source(profile, layout.source(), supplied)
                .map_err(|error| format!("recovered VM load: {error:?}"))?;
        let step_limit = layout.source().len();
        assert!(matches!(replay.run(step_limit),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == step_limit));
        assert_eq!(replay.output(), expected);
        assert_eq!(replay.input_consumed(), 0);
    }
    let mut forged = expected;
    forged[2] ^= 1;
    assert!(
        verified_output_stream_layout(profile, &operations, forged, &cells,)
            .is_none()
    );
    Ok(())
}

#[test]
fn four_regions_recover_uneven_split_with_extra_early_stride()
-> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile).ok_or("missing source phases")?;
    // A source-independent extra no-op after the first j shifts both later
    // data relocations. The existing 3*N+2 fixed geometry cannot express it.
    let mut operations = unbalanced_three_region_source();
    operations.insert(19, LinearOpcode::RelocateDataPointer);
    operations.insert(9, LinearOpcode::NoOperation);
    assert_eq!(operations.len(), 30);
    let (expected, raw) =
        unbalanced_guest_oracle(profile, &operations, &cells)?;
    assert_eq!(expected, [
        0, 0x41, 0x41, 0x8a, 0xc4, 0xc4, 0x8a, 0xc6, 0x86
    ]);
    assert_eq!(proposed_output_stream(&operations, &cells), Some(expected));
    assert!(
        verified_output_stream_layout(profile, &operations, expected, &cells)
            .is_some(),
        "the independent publisher rejected the source guest"
    );
    let recovered =
        verified_four_split_relocation_output_layout(profile, expected, &cells)
            .ok_or("four-region search missed uneven live relocations")?;
    assert_eq!(recovered.source().len(), raw.len());
    let relocated = recovered
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
    assert_eq!(relocated, 4);
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, recovered.source(), input)
                .map_err(|error| {
                    format!("recovered guest VM load: {error:?}")
                })?;
        assert!(matches!(vm.run(recovered.source().len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == raw.len()));
        assert_eq!(vm.output(), expected);
        assert_eq!(vm.input_consumed(), 0);
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
fn four_regions_recover_output_at_terminal_source_cell() -> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile).ok_or("missing source phases")?;
    // Move one repeated output to the final source cell before halt. This
    // changes the loader tail seed, so the guest is independently re-run.
    let mut operations = unbalanced_three_region_source();
    operations.insert(19, LinearOpcode::RelocateDataPointer);
    operations.insert(9, LinearOpcode::NoOperation);
    if operations.len() != 30
        || operations.get(12) != Some(&LinearOpcode::OutputByte)
        || operations.get(28) != Some(&LinearOpcode::NoOperation)
    {
        return Err(String::from("unexpected independent source geometry"));
    }
    *operations.get_mut(12).ok_or("missing repeated output")? =
        LinearOpcode::NoOperation;
    *operations.get_mut(28).ok_or("missing terminal output")? =
        LinearOpcode::OutputByte;
    let (expected, raw) =
        unbalanced_guest_oracle(profile, &operations, &cells)?;
    assert_eq!(expected, [
        0x00, 0x41, 0x8a, 0xce, 0xce, 0x0b, 0xbb, 0x09, 0x09
    ]);
    assert_eq!(proposed_output_stream(&operations, &cells), Some(expected));
    assert!(
        verified_output_stream_layout(profile, &operations, expected, &cells)
            .is_some(),
        "the independent verifier rejected terminal-output source"
    );
    let recovered =
        verified_four_split_relocation_output_layout(profile, expected, &cells)
            .ok_or("four-region proposal omitted a terminal output seed")?;
    assert_eq!(recovered.source().len(), raw.len());
    let decoded = recovered
        .source()
        .iter()
        .enumerate()
        .map(|(index, byte)| {
            malbolge::decode_profile_instruction(
                u32::from(*byte),
                u32::try_from(index).unwrap_or(u32::MAX),
            )
        })
        .collect::<Vec<_>>();
    assert_eq!(decoded.iter().filter(|&&op| op == Some(b'j')).count(), 4);
    assert_eq!(decoded.get(raw.len() - 2), Some(&Some(b'<')));
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, recovered.source(), input)
                .map_err(|error| format!("recovered VM load: {error:?}"))?;
        assert!(matches!(vm.run(raw.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == raw.len()));
        assert_eq!(vm.output(), expected);
        assert_eq!(vm.input_consumed(), 0);
    }
    let mut forged = expected;
    forged[4] ^= 1;
    assert!(
        verified_output_stream_layout(profile, &operations, forged, &cells)
            .is_none()
    );
    Ok(())
}

// Both independent source shapes must pass the same publisher and VM checks.
fn verify_arithmetic_terminal_replay(
    profile: &'static ProfileDescriptor,
    layout: &LinearLayout,
    expected: [u8; 9],
    terminal: u8,
) -> Result<(), String> {
    let source_length = layout.source().len();
    let decoded = layout
        .source()
        .iter()
        .enumerate()
        .map(|(index, &byte)| {
            malbolge::decode_profile_instruction(
                u32::from(byte),
                u32::try_from(index).unwrap_or(u32::MAX),
            )
        })
        .collect::<Vec<_>>();
    if decoded.iter().filter(|&&op| op == Some(b'j')).count() != 4
        || decoded.get(source_length.saturating_sub(2)) != Some(&Some(terminal))
    {
        return Err(String::from(
            "recovered four-region opcode identity drifted",
        ));
    }
    if layout
        .data_write_positions()
        .iter()
        .flatten()
        .any(|&address| {
            !usize::try_from(address).is_ok_and(|index| index >= source_length)
        })
    {
        return Err(String::from("recovered guest wrote into its source"));
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|error| format!("recovered VM load: {error:?}"))?;
        if !matches!(vm.run(source_length),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == source_length)
            || vm.output() != expected
            || vm.input_consumed() != 0
        {
            return Err(String::from(
                "arithmetic-terminal guest replay drifted",
            ));
        }
    }
    Ok(())
}

fn verify_arithmetic_terminal_source(
    profile: &'static ProfileDescriptor,
    operations: &[LinearOpcode],
    cells: &[[u8; 6]],
    witness: ([u8; 9], u8),
) -> Result<(), String> {
    let (expected, terminal) = witness;
    let (observed, raw) = unbalanced_guest_oracle(profile, operations, cells)?;
    if observed != expected
        || proposed_output_stream(operations, cells) != Some(expected)
    {
        return Err(String::from("independent source oracle mismatch"));
    }
    if verified_output_stream_layout(profile, operations, expected, cells)
        .is_none()
    {
        return Err(String::from("independent publisher rejected source"));
    }
    let recovered =
        verified_four_split_relocation_output_layout(profile, expected, cells)
            .ok_or("four-region arithmetic-terminal search missed source")?;
    if recovered.source().len() != raw.len() {
        return Err(String::from("recovered source length drifted"));
    }
    verify_arithmetic_terminal_replay(profile, &recovered, expected, terminal)?;
    let mut forged = expected;
    *forged.get_mut(3).ok_or("missing forged output")? ^= 1;
    if verified_output_stream_layout(profile, operations, forged, cells)
        .is_some()
    {
        return Err(String::from("forged output unexpectedly accepted"));
    }
    Ok(())
}

#[test]
fn four_regions_recover_arithmetic_terminal_seeds() -> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile).ok_or("missing source phases")?;
    // Both terminal writes change the loader seed of the earlier guest data.
    for (terminal, expected, decoded) in [
        (
            LinearOpcode::CrazyData,
            [0x00, 0x38, 0x38, 0x8a, 0xb5, 0xb5, 0xb1, 0x88, 0xb0],
            b'p',
        ),
        (
            LinearOpcode::RotateData,
            [0x00, 0x41, 0x41, 0x8a, 0xb5, 0xb5, 0x8a, 0xc6, 0x8a],
            b'*',
        ),
    ] {
        let mut operations = unbalanced_three_region_source();
        operations.insert(19, LinearOpcode::RelocateDataPointer);
        operations.insert(9, LinearOpcode::NoOperation);
        if operations.len() != 30 {
            return Err(String::from("unexpected shifted split geometry"));
        }
        *operations
            .get_mut(28)
            .ok_or("missing terminal source cell")? = terminal;
        verify_arithmetic_terminal_source(
            profile,
            &operations,
            &cells,
            (expected, decoded),
        )?;
    }
    Ok(())
}

#[test]
fn four_regions_recover_compact_arithmetic_terminal_seed() -> Result<(), String>
{
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile).ok_or("missing source phases")?;
    // The compact split has no extra stride; a terminal rotate changes
    // the expansion seed without changing the nine output instructions.
    let mut operations = unbalanced_three_region_source();
    operations.insert(19, LinearOpcode::RelocateDataPointer);
    if operations.len() != 29 {
        return Err(String::from("unexpected compact split geometry"));
    }
    *operations
        .get_mut(27)
        .ok_or("missing terminal source cell")? = LinearOpcode::RotateData;
    verify_arithmetic_terminal_source(
        profile,
        &operations,
        &cells,
        ([0x00, 0x42, 0x42, 0x03, 0xc6, 0xc6, 0xa5, 0x18, 0xff], b'*'),
    )
}

#[test]
fn five_relocations_recover_twelve_guest_outputs() -> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile).ok_or("missing source phases")?;
    // Twelve genuine outputs span five data regions; this source is built
    // from positional decoder cells, not from the proposed search grammar.
    let mut operations = Vec::new();
    for index in 0..12 {
        if index < 5 {
            operations.push(LinearOpcode::RelocateDataPointer);
        }
        operations.extend([LinearOpcode::CrazyData, LinearOpcode::OutputByte]);
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
        .ok_or("missing positional source byte")?;
    let mut vm = ProfileMachine::from_source(profile, &raw, Vec::new())
        .map_err(|error| format!("independent five-region load: {error:?}"))?;
    assert!(matches!(vm.run(raw.len()),
        Ok(RunOutcome::Terminated { steps, .. }) if steps == raw.len()));
    assert_eq!(vm.input_consumed(), 0);
    let expected: [u8; 12] = vm
        .output()
        .try_into()
        .map_err(|error| format!("twelve guest outputs: {error:?}"))?;
    assert_eq!(expected, [
        0x41, 0x47, 0x5a, 0x25, 0x25, 0x4d, 0x32, 0x18, 0x5a, 0x25, 0x25, 0x4d
    ]);
    let original =
        verified_output_stream_layout(profile, &operations, expected, &cells)
            .ok_or("independent publisher refused twelve-byte guest")?;
    assert_eq!(original.source(), raw);
    assert_eq!(original.data_write_positions().iter().flatten().count(), 12);
    assert_eq!(
        operations
            .iter()
            .filter(|&&operation| {
                operation == LinearOpcode::RelocateDataPointer
            })
            .count(),
        5
    );
    let recovered =
        verified_relocated_write_layout(profile, expected, &cells, 5)
            .ok_or("five-region proposer missed independent guest")?;
    assert_eq!(recovered.source(), raw);
    assert_eq!(
        recovered.data_write_positions().iter().flatten().count(),
        12
    );
    let published = verified_short_output_layout(profile, expected, &cells)
        .ok_or("production twelve-byte bridge missed a verified guest")?;
    // A different verified source can emit the same bytes; exact source
    // identity is not part of the public byte-stream compiler contract.
    assert!(published.data_write_positions().iter().flatten().count() > 0);
    for supplied in [Vec::new(), vec![0, 255, 128]] {
        let mut replay =
            ProfileMachine::from_source(profile, recovered.source(), supplied)
                .map_err(|error| {
                    format!("recovered five-region load: {error:?}")
                })?;
        assert!(matches!(replay.run(raw.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == raw.len()));
        assert_eq!(replay.output(), expected);
        assert_eq!(replay.input_consumed(), 0);
    }
    let mut forged = expected;
    forged[5] ^= 1;
    assert!(
        verified_output_stream_layout(profile, &operations, forged, &cells,)
            .is_none()
    );
    Ok(())
}
