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
