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
    VerifiedSource, encode_auto_padded_forward_layout,
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
