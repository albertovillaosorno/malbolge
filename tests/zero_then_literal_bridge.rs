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
//   - Exact distinct zero-then-printable byte effects in a real guest VM.
// - Must-Not:
//   - Simulate guest computation, infer unrelated byte pairs or skip wire checks.
// - Allows:
//   - Inputs: canonical bounded two-constant ternary effect traces.
//   - Outputs: exact source, output and termination evidence or rejection.
//   - Side effects: none outside isolated normative VM state.
// - Split-When:
//   - A general multi-byte constant encoder replaces this bounded witness.
// - Merge-When:
//   - A complete verifier checks all constant SSA transitions.
// - Summary:
//   - The guest really outputs NUL and then a distinct printable byte.
// - Description:
//   - Each witness uses one relocated crazy operation with exact layout.
// - Usage:
//   - cargo test --locked --test zero_then_literal_bridge
// - Defaults:
//   - Other bytes, effect orders and profiles fail closed.

//! Independent normative VM proof for a source-proven zero then printable byte.

#[path = "../src/compiler/byte-echo-bridge/composition/lib.rs"]
pub mod bridge;

use bridge::ternary::{
    InputBlock, InputFunction, InputInstruction, InputScalarType, InputSourcePosition,
    InputSourceSpan, InputTerminator, TypedIrInput, canonical_ternary_bytes,
    canonical_ternary_program, lower_typed_ir,
};
use bridge::{ByteEchoBridgeError, encode_zero_then_literal};
use malbolge::{ProfileMachine, RunOutcome, current_profile, historical_profile};

const fn pos(byte: u32) -> InputSourcePosition {
    InputSourcePosition {
        byte,
        column: byte + 1,
        line: 1,
    }
}

const fn span(begin: u32, end: u32) -> InputSourceSpan {
    InputSourceSpan {
        begin: pos(begin),
        end: pos(end),
    }
}

fn source(first: u8, last: u8, stale: bool) -> Result<bridge::ternary::TernaryProgram, String> {
    let instructions = vec![
        InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: vec![first],
            result: 0,
            span: span(0, 1),
            type_kind: InputScalarType::U8,
        },
        InputInstruction::ByteOutput {
            span: span(1, 2),
            value: 0,
        },
        InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: vec![last],
            result: 1,
            span: span(2, 3),
            type_kind: InputScalarType::U8,
        },
        InputInstruction::ByteOutput {
            span: span(3, 4),
            value: if stale { 0 } else { 1 },
        },
    ];
    let typed = TypedIrInput {
        abi_id: String::from("malbolge-c32-v1"),
        functions: vec![InputFunction {
            blocks: vec![InputBlock {
                id: 0,
                instructions,
                phi_count: 0,
                terminator: InputTerminator::Return {
                    span: span(4, 5),
                    value: None,
                },
            }],
            entry: 0,
            id: 0,
            name: String::from("mixed_constant"),
            parameter_count: 0,
            return_kind: InputScalarType::Void,
            span: span(0, 5),
        }],
        global_count: 0,
        input_format_version: 1,
        proof_obligation_count: 0,
        source_id: String::from("fixtures/mixed-constant.c"),
        source_sha256: [0x73; 32],
        target_profile: String::from("malbolge-2026"),
    };
    let lowered = lower_typed_ir(&typed).map_err(|e| format!("lower: {e:?}"))?;
    let bytes = canonical_ternary_bytes(&lowered).map_err(|e| format!("wire: {e:?}"))?;
    let admitted = canonical_ternary_program(&bytes).map_err(|e| format!("read: {e:?}"))?;
    if lowered != admitted {
        return Err(String::from("ternary wire round trip changed effect trace"));
    }
    Ok(admitted)
}

#[test]
fn zero_then_four_printable_literals_are_real_guest_output() -> Result<(), String> {
    for (last, padding) in [(b'Z', 0), (b'P', 2), (b'T', 6), (b'S', 17)] {
        let program = source(0, last, false)?;
        let layout = encode_zero_then_literal(&program, current_profile())
            .map_err(|e| format!("byte {last} failed: {e:?}"))?;
        assert_eq!(layout.source().len(), padding + 5);
        assert_eq!(layout.executed_code_positions().len(), padding + 5);
        for input in [vec![], vec![255, 128, 0]] {
            let mut vm = ProfileMachine::from_source(current_profile(), layout.source(), input)
                .map_err(|e| format!("vm load: {e:?}"))?;
            assert!(matches!(vm.run(padding + 5),
                Ok(RunOutcome::Terminated { steps, .. }) if steps == padding + 5));
            assert_eq!(vm.input_consumed(), 0);
            assert_eq!(vm.output(), [0, last]);
        }
    }
    Ok(())
}

#[test]
fn zero_then_literal_refuses_unproved_transitions() -> Result<(), String> {
    for (first, last, stale) in [
        (1, b'Z', false),
        (0, b'A', false),
        (0, b'Z', true),
        (0, 0, false),
    ] {
        let program = source(first, last, stale)?;
        assert!(matches!(
            encode_zero_then_literal(&program, current_profile()),
            Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        ));
    }
    let program = source(0, b'Z', false)?;
    assert!(matches!(
        encode_zero_then_literal(&program, historical_profile()),
        Err(ByteEchoBridgeError::ProfileMismatch)
    ));
    Ok(())
}
