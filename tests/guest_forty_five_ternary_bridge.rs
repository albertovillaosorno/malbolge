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
//   - Independent exact ternary-to-layout admission for 44 binary literals.
// - Must-Not:
//   - Admit arbitrary guest output or claim source-C compilation.
// - Allows:
//   - Inputs: canonical typed projections and exact current-profile bytes.
//   - Outputs: validated guest layout and normative VM evidence.
//   - Side effects: none.
// - Split-When:
//   - General byte stream compilation replaces finite recipes.
// - Merge-When:
//   - Source-C stage admits this sequence independently.
// - Summary:
//   - Exact byte-constant SSA effects lower to the proven 45-byte guest.
// - Description:
//   - Positive wire/VM proof, foreign-profile and malformed trace refusal.
// - Usage:
//   - cargo test --locked --test guest_forty_five_ternary_bridge
// - Defaults:
//   - Other output sequences do not have this witness.

//! Exact 45-byte ternary-to-layout guest execution with fail-closed admission.

#[path = "../src/compiler/byte-echo-bridge/composition/lib.rs"]
pub mod bridge;

use std::collections::BTreeSet;

use bridge::ternary::{
    InputBlock, InputFunction, InputInstruction, InputScalarType,
    InputSourcePosition, InputSourceSpan, InputTerminator, TernaryOperation,
    TernaryProgram, TernaryU8Scalar, TypedIrInput, canonical_ternary_bytes,
    canonical_ternary_program, lower_typed_ir,
};
use bridge::{ByteEchoBridgeError, encode_distinct_literal_forty_five};
use malbolge::{
    ProfileMachine, RunOutcome, current_profile, historical_profile,
};

const EXPECTED: [u8; 45] = [
    81, 62, 53, 56, 84, 31, 78, 135, 209, 165, 153, 9, 8, 199, 198, 194,
    145, 225, 167, 172, 152, 219, 155, 160, 183, 191, 124, 181, 44, 203, 18, 180,
    248, 202, 14, 149, 45, 171, 51, 61, 57, 5, 83, 35, 27,
];

const fn position(byte: u32) -> InputSourcePosition {
    InputSourcePosition {
        byte,
        column: byte.saturating_add(1),
        line: 1,
    }
}

const fn span(begin: u32, end: u32) -> InputSourceSpan {
    InputSourceSpan {
        begin: position(begin),
        end: position(end),
    }
}

fn source(bytes: &[u8]) -> Result<TernaryProgram, String> {
    let mut instructions = Vec::new();
    for (index, &byte) in bytes.iter().enumerate() {
        let id =
            u32::try_from(index).map_err(|error| format!("ssa: {error}"))?;
        let offset = id.saturating_mul(2);
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: vec![byte],
            result: id,
            span: span(offset, offset.saturating_add(1)),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: span(offset.saturating_add(1), offset.saturating_add(2)),
            value: id,
        });
    }
    let end = u32::try_from(bytes.len().saturating_mul(2).saturating_add(1))
        .map_err(|error| format!("source span: {error}"))?;
    let input = TypedIrInput {
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
            name: String::from("forty_five_literals"),
            parameter_count: 0,
            return_kind: InputScalarType::Void,
            span: span(0, end),
        }],
        global_count: 0,
        input_format_version: 1,
        proof_obligation_count: 0,
        source_id: String::from("fixtures/forty-five-ternary.c"),
        source_sha256: [0x45; 32],
        target_profile: String::from("malbolge-2026"),
    };
    let lowered =
        lower_typed_ir(&input).map_err(|error| format!("lower: {error:?}"))?;
    let canonical = canonical_ternary_bytes(&lowered)
        .map_err(|error| format!("encode: {error:?}"))?;
    let decoded = canonical_ternary_program(&canonical)
        .map_err(|error| format!("decode: {error:?}"))?;
    assert_eq!(decoded, lowered);
    Ok(decoded)
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "independent real VM assertions verify exact effect binding"
)]
fn source_bound_ternary_literals_execute_as_real_guest_bytes()
-> Result<(), String> {
    let program = source(&EXPECTED)?;
    let layout =
        encode_distinct_literal_forty_five(&program, current_profile())
            .map_err(|error| format!("bridge: {error:?}"))?;
    assert_eq!(layout.source().len(), 105);
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    assert_eq!(writes.len(), 45);
    assert_eq!(writes.iter().copied().collect::<BTreeSet<_>>().len(), 45);
    assert!(writes.iter().all(|&address| address >= 105));
    let mut vm =
        ProfileMachine::from_source(current_profile(), layout.source(), vec![
            0, 128, 255,
        ])
        .map_err(|error| format!("load: {error:?}"))?;
    assert!(matches!(
        vm.run(105),
        Ok(RunOutcome::Terminated { steps: 105, .. })
    ));
    assert_eq!(vm.input_consumed(), 0);
    assert_eq!(vm.output(), EXPECTED);
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "negative admission assertions protect the exact byte witness"
)]
fn foreign_values_profiles_and_effects_refuse_without_publication()
-> Result<(), String> {
    let program = source(&EXPECTED)?;
    assert!(matches!(
        encode_distinct_literal_forty_five(&program, historical_profile()),
        Err(ByteEchoBridgeError::ProfileMismatch)
    ));
    for index in [0usize, 20, 44] {
        let mut wrong = EXPECTED;
        wrong[index] ^= 1;
        assert!(matches!(
            encode_distinct_literal_forty_five(
                &source(&wrong)?,
                current_profile()
            ),
            Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        ));
    }
    assert!(matches!(
        encode_distinct_literal_forty_five(
            &source(&EXPECTED[..44])?,
            current_profile()
        ),
        Err(ByteEchoBridgeError::UnsupportedEffectTrace)
    ));
    let mut wrong_ssa = program.clone();
    if let TernaryOperation::ByteOutput { value, .. } =
        &mut wrong_ssa.functions[0].operations[1]
    {
        *value = 1;
    } else {
        return Err(String::from("fixture lost first ByteOutput"));
    }
    assert!(
        encode_distinct_literal_forty_five(&wrong_ssa, current_profile())
            .is_err()
    );
    let mut changed = program;
    if let TernaryOperation::MaterializeU8 { scalar, .. } =
        &mut changed.functions[0].operations[0]
    {
        *scalar = TernaryU8Scalar::from_bits(0);
    } else {
        return Err(String::from("fixture lost first byte materialization"));
    }
    assert!(matches!(
        encode_distinct_literal_forty_five(&changed, current_profile()),
        Err(ByteEchoBridgeError::UnsupportedEffectTrace)
    ));
    Ok(())
}
