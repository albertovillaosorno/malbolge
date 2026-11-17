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
//   - Source-independent, real guest mixed signed input and constant output.
// - Must-Not:
//   - Convert EOF into a successful byte, use a host output, or skip VM replay.
// - Allows:
//   - Inputs: fresh typed-IR and binary stdin including EOF and unread suffix.
//   - Outputs: canonical ternary, actual Malbolge bytes and typed refusal.
//   - Side effects: bounded normative in-memory VM execution only.
// - Split-When:
//   - General source-C mixed I/O compiler subsumes this finite effect slice.
// - Merge-When:
//   - The mutable checksum's guest runtime implements the same semantics.
// - Summary:
//   - A real signed input precedes a guest-computed, unrelated literal byte.

use ternary::{
    InputBlock, InputFunction, InputInstruction, InputScalarType,
    InputSourcePosition, InputSourceSpan, InputTerminator, TypedIrInput,
    canonical_ternary_bytes, canonical_ternary_program, lower_typed_ir,
};

use super::*;

const OUTPUT: u8 = 11;

const fn position(byte: u32) -> InputSourcePosition {
    InputSourcePosition {
        byte,
        column: byte + 1,
        line: 1,
    }
}

const fn span(start: u32, end: u32) -> InputSourceSpan {
    InputSourceSpan {
        begin: position(start),
        end: position(end),
    }
}

fn admitted_program_with_reads(
    read_count: usize,
    output: u8,
) -> Result<TernaryProgram, String> {
    let mut instructions = Vec::new();
    for index in 0..read_count {
        let id = u32::try_from(index).map_err(|error| error.to_string())?;
        let start = id * 2 + 1;
        instructions.push(InputInstruction::Getchar {
            result: id,
            span: span(start, start + 1),
            type_kind: InputScalarType::I32,
        });
    }
    let literal_id =
        u32::try_from(read_count).map_err(|error| error.to_string())?;
    let literal_start = literal_id * 2 + 1;
    instructions.extend([
        InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: vec![output],
            result: literal_id,
            span: span(literal_start, literal_start + 1),
            type_kind: InputScalarType::U8,
        },
        InputInstruction::ByteOutput {
            span: span(literal_start + 2, literal_start + 3),
            value: literal_id,
        },
    ]);
    let input = TypedIrInput {
        abi_id: String::from("malbolge-c32-v1"),
        functions: vec![InputFunction {
            blocks: vec![InputBlock {
                id: 0,
                instructions,
                phi_count: 0,
                terminator: InputTerminator::Return {
                    span: span(literal_start + 4, literal_start + 5),
                    value: None,
                },
            }],
            entry: 0,
            id: 0,
            name: String::from("mixed_signed_input_literal"),
            parameter_count: 0,
            return_kind: InputScalarType::Void,
            span: span(0, literal_start + 6),
        }],
        global_count: 0,
        input_format_version: 1,
        proof_obligation_count: 0,
        source_id: String::from("fixtures/mixed-signed-input-literal.c"),
        source_sha256: [0x5d; 32],
        target_profile: String::from("malbolge-2026"),
    };
    lower_typed_ir(&input).map_err(|error| format!("lowering: {error:?}"))
}

fn admitted_program() -> Result<TernaryProgram, String> {
    admitted_program_with_reads(1, OUTPUT)
}

#[test]
fn signed_getchar_then_independent_guest_literal() -> Result<(), String> {
    let program = admitted_program()?;
    let encoded = canonical_ternary_bytes(&program)
        .map_err(|error| format!("canonical encoding: {error:?}"))?;
    let decoded = canonical_ternary_program(&encoded)
        .map_err(|error| format!("canonical decode: {error:?}"))?;
    if decoded != program {
        return Err(String::from(
            "canonical typed/ternary roundtrip changed operations",
        ));
    }
    let profile = current_profile();
    let layout = encode_discarded_input_literal(&decoded, profile)
        .map_err(|error| format!("mixed guest bridge: {error:?}"))?;
    if layout.profile_id() != profile.id()
        || layout.profile_fingerprint() != profile.fingerprint()
        || layout.executed_code_positions().len() != 5
    {
        return Err(String::from("unexpected guest identity or path"));
    }
    // The first instruction is actual guest input; a rotated loader word,
    // not a host literal callback, overwrites the accumulator before output.
    if malbolge::decode_profile_instruction(u32::from(layout.source()[0]), 0)
        != Some(profile.input_instruction())
    {
        return Err(String::from("guest did not begin with real input"));
    }
    for stream in [vec![], vec![0], vec![128], vec![255], vec![0, 255, 42]] {
        let mut machine = ProfileMachine::from_source(
            profile,
            layout.source(),
            stream.clone(),
        )
        .map_err(|error| format!("machine load: {error:?}"))?;
        let outcome = machine
            .run(5)
            .map_err(|error| format!("machine run: {error:?}"))?;
        if !matches!(outcome, RunOutcome::Terminated { steps: 5, .. })
            || machine.output() != [OUTPUT]
            || machine.input_consumed() != usize::from(!stream.is_empty())
        {
            return Err(format!(
                "guest differs on input={stream:?}: {outcome:?}, output={:?}",
                machine.output()
            ));
        }
    }
    Ok(())
}

#[test]
fn signed_input_literal_rejects_wrong_effect_shape() -> Result<(), String> {
    let profile = current_profile();
    let original = admitted_program()?;
    if encode_discarded_input_literal(&original, malbolge::historical_profile())
        != Err(ByteEchoBridgeError::ProfileMismatch)
    {
        return Err(String::from("accepted foreign target profile"));
    }
    let mut wrong_output = original.clone();
    let effect = wrong_output.functions[0]
        .operations
        .get_mut(2)
        .ok_or("missing byte output")?;
    let TernaryOperation::ByteOutput { value, .. } = effect else {
        return Err(String::from("wrong lowered operation"));
    };
    *value = 0;
    if encode_discarded_input_literal(&wrong_output, profile).is_ok() {
        return Err(String::from("accepted signed getchar as byte output"));
    }
    let mut reordered = original.clone();
    reordered.functions[0].operations.swap(0, 1);
    if encode_discarded_input_literal(&reordered, profile).is_ok() {
        return Err(String::from("accepted changed source effect ordering"));
    }
    let mut no_input = original.clone();
    let _removed = no_input.functions[0].operations.remove(0);
    if encode_discarded_input_literal(&no_input, profile).is_ok() {
        return Err(String::from("invented an absent guest input"));
    }
    Ok(())
}

#[test]
fn signed_two_getchars_then_independent_guest_literal() -> Result<(), String> {
    let program = admitted_program_with_reads(2, OUTPUT)?;
    let wire = canonical_ternary_bytes(&program)
        .map_err(|error| format!("canonical encoding: {error:?}"))?;
    let decoded = canonical_ternary_program(&wire)
        .map_err(|error| format!("canonical decode: {error:?}"))?;
    if decoded != program {
        return Err(String::from(
            "two reads changed during canonical roundtrip",
        ));
    }
    let profile = current_profile();
    let layout = encode_discarded_input_literal(&decoded, profile)
        .map_err(|error| format!("two-input bridge: {error:?}"))?;
    if layout.executed_code_positions().len() != 6
        || layout.source() != [117, 116, 38, 36, 95, 76]
        || layout.data_pointer_positions() != [0, 1, 2, 39, 40, 41]
    {
        return Err(String::from("unrecognized two-read guest layout"));
    }
    for index in 0..2usize {
        let source_byte = layout.source()[index];
        if malbolge::decode_profile_instruction(
            u32::from(source_byte),
            u32::try_from(index).map_err(|error| error.to_string())?,
        ) != Some(profile.input_instruction())
        {
            return Err(String::from("source skipped a guest input effect"));
        }
    }
    for stream in [vec![], vec![0], vec![255], vec![128, 255], vec![
        0, 128, 255,
    ]] {
        let mut machine = ProfileMachine::from_source(
            profile,
            layout.source(),
            stream.clone(),
        )
        .map_err(|error| format!("machine load: {error:?}"))?;
        let outcome = machine
            .run(6)
            .map_err(|error| format!("machine run: {error:?}"))?;
        if !matches!(outcome, RunOutcome::Terminated { steps: 6, .. })
            || machine.input_consumed() != stream.len().min(2)
            || machine.output() != [OUTPUT]
        {
            return Err(format!(
                "two-read guest {stream:?}: {outcome:?}; {}/{:?}",
                machine.input_consumed(),
                machine.output()
            ));
        }
    }
    Ok(())
}

#[test]
fn signed_two_getchars_refuses_unproved_output_and_third_read()
-> Result<(), String> {
    let profile = current_profile();
    let unsupported = admitted_program_with_reads(2, 223)?;
    if encode_discarded_input_literal(&unsupported, profile).is_ok() {
        return Err(String::from("published unwitnessed two-read byte 223"));
    }
    let third = admitted_program_with_reads(3, OUTPUT)?;
    if encode_discarded_input_literal(&third, profile).is_ok() {
        return Err(String::from("published unsupported third signed input"));
    }
    let mut duplicate = admitted_program_with_reads(2, OUTPUT)?;
    let TernaryOperation::GetcharI32 { result, .. } =
        &mut duplicate.functions[0].operations[1]
    else {
        return Err(String::from("missing second input"));
    };
    *result = 0;
    if encode_discarded_input_literal(&duplicate, profile).is_ok() {
        return Err(String::from("published duplicate signed input SSA"));
    }
    Ok(())
}
