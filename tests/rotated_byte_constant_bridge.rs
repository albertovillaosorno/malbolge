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
//   - Exact finite guest-computed u8 constant emission and VM evidence.
// - Must-Not:
//   - Substitute host writes for guest rotate or imply general C arithmetic.
// - Allows:
//   - Inputs: canonical ternary MCTR literals and target profile identity.
//   - Outputs: bounded re-admitted source and independent true guest byte.
//   - Side effects: bounded normative VM execution only.
// - Split-When:
//   - General byte-constant synthesis owns a larger safe profile domain.
// - Merge-When:
//   - A full target backend admits this exact proof without specialized code.
// - Summary:
//   - Proves nonzero values come from real relocated guest data rotation.
// - Description:
//   - Verifies 14 admitted bytes and rejects unproved literals and profiles.
// - Usage:
//   - cargo test --locked --test rotated_byte_constant_bridge.
// - Defaults:
//   - Out-of-domain byte constants fail closed without source emission.

//! Genuine guest nonzero literal output via a seed-dependent data rotation.

#[path = "../src/compiler/byte-echo-bridge/composition/lib.rs"]
pub mod bridge;

use bridge::ternary::{
    InputBlock, InputFunction, InputInstruction, InputScalarType, InputSourcePosition,
    InputSourceSpan, InputTerminator, TernaryProgram, TypedIrInput, canonical_ternary_bytes,
    canonical_ternary_program, lower_typed_ir,
};
use bridge::{
    ByteEchoBridgeError, encode_initial_zero_outputs, encode_rotated_byte_literal,
    encode_successful_latest_byte_trace,
};
use malbolge::{ProfileMachine, RunOutcome, current_profile, historical_profile};

const fn pos(byte: u32) -> InputSourcePosition {
    InputSourcePosition {
        byte,
        column: byte.saturating_add(1),
        line: 1,
    }
}

const fn span(begin: u32, end: u32) -> InputSourceSpan {
    InputSourceSpan {
        begin: pos(begin),
        end: pos(end),
    }
}

fn source(value: u8, duplicate_output: bool) -> Result<TernaryProgram, String> {
    let mut instructions = vec![
        InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: vec![value],
            result: 0,
            span: span(0, 1),
            type_kind: InputScalarType::U8,
        },
        InputInstruction::ByteOutput {
            span: span(1, 2),
            value: 0,
        },
    ];
    if duplicate_output {
        instructions.push(InputInstruction::ByteOutput {
            span: span(2, 3),
            value: 0,
        });
    }
    let end: u32 = if duplicate_output { 4 } else { 3 };
    let typed = TypedIrInput {
        abi_id: String::from("malbolge-c32-v1"),
        functions: vec![InputFunction {
            blocks: vec![InputBlock {
                id: 0,
                instructions,
                phi_count: 0,
                terminator: InputTerminator::Return {
                    span: span(end.saturating_sub(1), end),
                    value: None,
                },
            }],
            entry: 0,
            id: 0,
            name: String::from("one_literal_output"),
            parameter_count: 0,
            return_kind: InputScalarType::Void,
            span: span(0, end),
        }],
        global_count: 0,
        input_format_version: 1,
        proof_obligation_count: 0,
        source_id: String::from("fixtures/rotated-constant.c"),
        source_sha256: [0x73; 32],
        target_profile: String::from("malbolge-2026"),
    };
    let lowered =
        lower_typed_ir(&typed).map_err(|error| format!("literal ternary lowering: {error:?}"))?;
    let canonical = canonical_ternary_bytes(&lowered)
        .map_err(|error| format!("literal canonical MCTR encode: {error:?}"))?;
    let admitted = canonical_ternary_program(&canonical)
        .map_err(|error| format!("literal canonical MCTR decode: {error:?}"))?;
    if admitted != lowered {
        return Err(String::from(
            "literal ternary byte-for-byte roundtrip drift",
        ));
    }
    Ok(admitted)
}

#[test]
fn all_seeded_nonzero_literals_execute_real_guest_rotate_output() -> Result<(), String> {
    for (byte, noops) in [
        (4, 23),
        (5, 20),
        (6, 16),
        (9, 7),
        (10, 4),
        (11, 1),
        (18, 24),
        (19, 21),
        (20, 18),
        (21, 6),
        (22, 3),
        (23, 0),
        (251, 22),
        (253, 19),
    ] {
        let program = source(byte, false)?;
        let layout = encode_rotated_byte_literal(&program, current_profile())
            .map_err(|error| format!("seeded {byte} target rejected: {error:?}"))?;
        if layout.source().len() != noops + 4
            || layout.executed_code_positions().len() != noops + 4
            || layout
                .data_write_positions()
                .iter()
                .filter(|x| x.is_some())
                .count()
                != 1
        {
            return Err(format!("seeded literal {byte} geometry drift"));
        }
        // Each bridge admission already checks one actual VM output.
        // Repeat under nonempty stdin for representative short/high seeds.
        if [4, 23, 253].contains(&byte) {
            let mut vm =
                ProfileMachine::from_source(current_profile(), layout.source(), vec![255, 0, 128])
                    .map_err(|error| format!("guest seeded {byte} load: {error:?}"))?;
            if !matches!(vm.run(noops + 4),
                Ok(RunOutcome::Terminated { steps, .. }) if steps == noops + 4)
                || vm.output() != [byte]
                || vm.input_consumed() != 0
            {
                return Err(format!("guest seeded {byte} output diverged"));
            }
        }
        if encode_initial_zero_outputs(&program, current_profile()).is_ok()
            || encode_successful_latest_byte_trace(&program, current_profile()).is_ok()
        {
            return Err(format!("old byte trace mode admitted nonzero {byte}"));
        }
    }
    Ok(())
}

#[test]
fn seeded_literals_refuse_unsupported_values_and_extra_effects() -> Result<(), String> {
    const WITNESSED: &[u8] = &[4, 5, 6, 9, 10, 11, 18, 19, 20, 21, 22, 23, 251, 253];
    for byte in u8::MIN..=u8::MAX {
        if WITNESSED.contains(&byte) {
            continue;
        }
        let program = source(byte, false)?;
        if encode_rotated_byte_literal(&program, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unverified u8 literal {byte} admitted"));
        }
    }
    let valid = source(23, false)?;
    if encode_rotated_byte_literal(&valid, historical_profile())
        != Err(ByteEchoBridgeError::ProfileMismatch)
        || encode_rotated_byte_literal(&source(23, true)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
    {
        return Err(String::from(
            "profile drift or extra literal output admitted",
        ));
    }
    Ok(())
}
