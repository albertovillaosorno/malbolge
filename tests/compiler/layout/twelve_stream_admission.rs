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
//   - Independent publisher re-admission of twelve guest output effects.
// - Must-Not:
//   - Equate VM byte parity with source-disjoint guest data writes.
// - Allows:
//   - Inputs: independently assembled graphical code and normative VM bytes.
//   - Outputs: acceptance of valid traces and rejection of jumps/aliasing.
//   - Side effects: none.
// - Split-When:
//   - General stream verification subsumes this mode-specific contract.
// - Merge-When:
//   - The canonical publisher owns all stream modes uniformly.
// - Summary:
//   - VM byte parity cannot authorize a forward jump in a linear stream.

use super::{
    LinearOpcode, PaddedForwardStep, ProfileMachine, RunOutcome,
    VerifiedSource, encode_auto_padded_forward_layout, encode_linear_layout,
    verify_distinct_literal_twelve,
};

fn graphical_program(decoded: &[u8]) -> Result<Vec<u8>, String> {
    decoded
        .iter()
        .enumerate()
        .map(|(position, &operation)| {
            (33u8..=126)
                .find(|&byte| {
                    malbolge::decode_profile_instruction(
                        u32::from(byte),
                        u32::try_from(position).unwrap_or(u32::MAX),
                    ) == Some(operation)
                })
                .ok_or_else(|| {
                    format!("missing graphical instruction at {position}")
                })
        })
        .collect()
}

fn actual_guest_output(
    source: &[u8],
    steps: usize,
) -> Result<[u8; 12], String> {
    let profile = malbolge::current_profile();
    let mut vm = ProfileMachine::from_source(profile, source, Vec::new())
        .map_err(|error| format!("original guest load: {error:?}"))?;
    let outcome = vm.run(steps);
    let halted = matches!(
        outcome,
        Ok(RunOutcome::Terminated { steps: used, .. }) if used == steps
    );
    if !halted {
        return Err(format!(
            "source did not halt at expected step: {outcome:?}; output {:?}",
            vm.output()
        ));
    }
    vm.output()
        .try_into()
        .map_err(|error| format!("guest output length: {error:?}"))
}

#[test]
fn forwarded_guest_jumps_must_not_be_published_as_linear_byte_stream()
-> Result<(), String> {
    let profile = malbolge::current_profile();
    // The independent forward-jump planner produces a real VM program
    // which emits twelve zeros. The compiler's byte-stream proposals
    // never contain an i jump, even when its skipped region is inert.
    let mut logical =
        vec![PaddedForwardStep::Instruction(LinearOpcode::NoOperation); 14];
    logical.push(PaddedForwardStep::Jump);
    logical
        .extend([PaddedForwardStep::Instruction(LinearOpcode::OutputByte); 12]);
    logical.push(PaddedForwardStep::Instruction(LinearOpcode::Halt));
    let forwarded = encode_auto_padded_forward_layout(profile, &logical)
        .map_err(|error| format!("independent forward layout: {error:?}"))?;
    let layout = forwarded.layout();
    let steps = layout.executed_code_positions().len();
    let source = layout.source().to_vec();
    if source.len() <= steps {
        return Err(String::from("the jump did not skip source cells"));
    }
    let expected = actual_guest_output(&source, steps)?;
    if expected != [0; 12] {
        return Err(String::from("forward-jump guest lost twelve zero bytes"));
    }
    let artifact = VerifiedSource {
        source,
        steps,
        effect_witness: None,
    };
    if verify_distinct_literal_twelve(profile, &artifact, expected).is_ok() {
        return Err(String::from(
            "VM parity admitted an unsupported guest forward jump",
        ));
    }
    Ok(())
}

#[test]
fn linear_twelve_output_guest_is_statically_admitted() -> Result<(), String> {
    let profile = malbolge::current_profile();
    let mut decoded = vec![b'o'; 14];
    decoded.push(b'j');
    for _ in 0..12 {
        decoded.extend([b'p', profile.output_instruction()]);
    }
    decoded.push(b'v');
    let source = graphical_program(&decoded)?;
    let expected = actual_guest_output(&source, decoded.len())?;
    if expected == [0; 12] {
        return Err(String::from("real relocated arithmetic was not executed"));
    }
    let artifact = VerifiedSource {
        source,
        steps: decoded.len(),
        effect_witness: None,
    };
    verify_distinct_literal_twelve(profile, &artifact, expected)
}

#[test]
fn genuine_single_relocation_source_scratch_stream_is_published()
-> Result<(), String> {
    let profile = malbolge::current_profile();
    // A real code jump skips 98 graphical source data cells. The first
    // rotated operand is source[1], and j at D=3 relocates to source[3]+1
    // without reading or rewriting the earlier rotated source[1].
    // The later rotation reads untouched source scratch after j and changes
    // the output byte. Ten no-ops keep both writes behind reached code.
    let operand = |address: u32| {
        (33u8..=90).find(|&byte| {
            matches!(
                malbolge::decode_profile_instruction(u32::from(byte), address),
                Some(b'o' | b'j' | b'i' | b'*' | b'p' | b'v' | b'<' | b'/')
            )
        })
    };
    let first = operand(1).ok_or("no loader-valid source[1]")?;
    let second = operand(3).ok_or("no loader-valid source[3]")?;
    let mut operations = vec![LinearOpcode::NoOperation; 99];
    operations[0] = LinearOpcode::JumpForward { target: 99 };
    operations[1] = LinearOpcode::SkippedDataByte { byte: u32::from(first) };
    operations[3] = LinearOpcode::SkippedDataByte { byte: u32::from(second) };
    operations.extend([
        LinearOpcode::RotateData,
        LinearOpcode::OutputByte,
        LinearOpcode::RelocateDataPointer,
    ]);
    operations.extend(std::iter::repeat_n(LinearOpcode::NoOperation, 10));
    operations.push(LinearOpcode::RotateData);
    operations.extend(std::iter::repeat_n(LinearOpcode::OutputByte, 11));
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(|error| format!("independent scratch layout: {error:?}"))?;
    let steps = layout.executed_code_positions().len();
    assert!((26..=126).contains(&steps));
    assert!(layout.source().len() > steps);
    let expected_byte =
        malbolge::profile_rotate(u32::from(first), profile.memory_words())
            as u8;
    let second_at = usize::from(second) + 11;
    let second_byte = malbolge::profile_rotate(
        u32::from(layout.source()[second_at]),
        profile.memory_words(),
    ) as u8;
    let mut expected = [second_byte; 12];
    expected[0] = expected_byte;
    assert_ne!(expected[0], expected[1]);
    assert_eq!(
        layout
            .data_write_positions()
            .iter()
            .flatten()
            .copied()
            .collect::<Vec<_>>(),
        [
            1,
            u32::try_from(second_at).map_err(|error| error.to_string())?
        ],
        "two distinct source writes must surround the disjoint relocation",
    );
    assert_eq!(
        layout
            .executed_code_positions()
            .iter()
            .filter(|&&at| {
                malbolge::decode_profile_instruction(
                    u32::from(layout.source()[at as usize]),
                    at,
                ) == Some(b'j')
            })
            .count(),
        1,
    );
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|error| format!("scratch VM load: {error:?}"))?;
        assert!(matches!(vm.run(steps),
            Ok(RunOutcome::Terminated { steps: used, .. }) if used == steps));
        assert_eq!(vm.output(), expected);
        assert_eq!(vm.input_consumed(), 0);
    }
    let artifact = VerifiedSource {
        source: layout.source().to_vec(),
        steps,
        effect_witness: None,
    };
    verify_distinct_literal_twelve(profile, &artifact, expected)
}

#[test]
fn single_relocation_without_a_guest_arithmetic_write_still_refuses()
-> Result<(), String> {
    let profile = malbolge::current_profile();
    // The same forward jump and j can replay twelve zero outputs without
    // any arithmetic. Do not let the new source-scratch path authorize this
    // distinct, unproved single-j layout merely because VM bytes agree.
    let mut operations = vec![LinearOpcode::NoOperation; 99];
    operations[0] = LinearOpcode::JumpForward { target: 99 };
    operations
        .extend([LinearOpcode::OutputByte, LinearOpcode::RelocateDataPointer]);
    operations.extend(std::iter::repeat_n(LinearOpcode::NoOperation, 11));
    operations.extend(std::iter::repeat_n(LinearOpcode::OutputByte, 11));
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(|error| format!("zero-output scratch layout: {error:?}"))?;
    let steps = layout.executed_code_positions().len();
    assert!((26..=126).contains(&steps));
    assert_eq!(actual_guest_output(layout.source(), steps)?, [0; 12]);
    let artifact = VerifiedSource {
        source: layout.source().to_vec(),
        steps,
        effect_witness: None,
    };
    assert!(
        verify_distinct_literal_twelve(profile, &artifact, [0; 12]).is_err(),
        "an unproved no-arithmetic single-j trace was published",
    );
    Ok(())
}
