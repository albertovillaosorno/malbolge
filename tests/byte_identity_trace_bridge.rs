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
//   - Exact 8-bit signed/unsigned alias proof against real guest byte I/O.
// - Must-Not:
//   - Impersonate arithmetic, storage, EOF, success on failed I/O or C ABI.
// - Allows:
//   - Inputs: admitted canonical MCTR source and fixed guest byte patterns.
//   - Outputs: independently verified VM effects and fail-closed SSA checks.
//   - Side effects: bounded VM execution only.
// - Split-When:
//   - General byte dataflow requires executable guest storage.
// - Merge-When:
//   - General target compiler proves the same SSA alias sublanguage.
// - Summary:
//   - Eight-bit bitcasts have no guest opcode; real I/O does.
// - Description:
//   - Validates latest-input alias liveness and source length independently.
// - Usage:
//   - cargo test --locked --test byte_identity_trace_bridge.
// - Defaults:
//   - Unsupported operations reject before code publication.

//! Canonical bitcast SSA aliases preserve the real VM byte accumulator.

#[path = "../src/compiler/byte-echo-bridge/composition/lib.rs"]
pub mod bridge;

use bridge::ternary::{
    InputBlock, InputFunction, InputInstruction, InputScalarType, InputSourcePosition,
    InputSourceSpan, InputTerminator, TernaryProgram, TypedIrInput, canonical_ternary_bytes,
    canonical_ternary_program, lower_typed_ir,
};
use bridge::{
    ByteEchoBridgeError, encode_latest_byte_identity_trace, encode_successful_byte_echo,
    encode_successful_latest_byte_trace,
};
use malbolge::{ProfileMachine, RunOutcome, current_profile, historical_profile};
use std::iter::repeat_n;

#[derive(Clone, Copy)]
enum Effect {
    Cast {
        result: u32,
        value: u32,
        kind: InputScalarType,
    },
    Input(u32),
    Output(u32),
}

const fn pos(byte: u32) -> InputSourcePosition {
    InputSourcePosition {
        byte,
        column: byte.saturating_add(1),
        line: 1,
    }
}

const fn span(start: u32, end: u32) -> InputSourceSpan {
    InputSourceSpan {
        begin: pos(start),
        end: pos(end),
    }
}

#[expect(clippy::too_many_lines, reason = "complete canonical ternary fixture")]
fn fixture(effects: &[Effect]) -> Result<TernaryProgram, String> {
    let mut operations = Vec::with_capacity(effects.len());
    for (i, effect) in effects.iter().enumerate() {
        let start = u32::try_from(i).map_err(|error| format!("effect span: {error}"))?;
        operations.push(match effect {
            Effect::Input(result) => InputInstruction::ByteInput {
                result: *result,
                span: span(start, start.saturating_add(1)),
                type_kind: InputScalarType::U8,
            },
            Effect::Cast {
                result,
                value,
                kind,
            } => InputInstruction::IntegerBitcast {
                result: *result,
                span: span(start, start.saturating_add(1)),
                type_kind: *kind,
                value: *value,
            },
            Effect::Output(value) => InputInstruction::ByteOutput {
                span: span(start, start.saturating_add(1)),
                value: *value,
            },
        });
    }
    let end = u32::try_from(operations.len().saturating_add(1))
        .map_err(|error| format!("return span: {error}"))?;
    let source = TypedIrInput {
        abi_id: String::from("malbolge-c32-v1"),
        functions: vec![InputFunction {
            blocks: vec![InputBlock {
                id: 0,
                instructions: operations,
                phi_count: 0,
                terminator: InputTerminator::Return {
                    span: span(end.saturating_sub(1), end),
                    value: None,
                },
            }],
            entry: 0,
            id: 0,
            name: String::from("identity_byte"),
            parameter_count: 0,
            return_kind: InputScalarType::Void,
            span: span(0, end),
        }],
        global_count: 0,
        input_format_version: 1,
        proof_obligation_count: 0,
        source_id: String::from("fixtures/identity-byte.c"),
        source_sha256: [0xa9; 32],
        target_profile: String::from("malbolge-2026"),
    };
    let lowered =
        lower_typed_ir(&source).map_err(|error| format!("ternary bitcast lowering: {error:?}"))?;
    let wire = canonical_ternary_bytes(&lowered)
        .map_err(|error| format!("canonical MCTR encode: {error:?}"))?;
    let admitted = canonical_ternary_program(&wire)
        .map_err(|error| format!("canonical MCTR decode: {error:?}"))?;
    if admitted != lowered {
        return Err(String::from("canonical alias/source bytes changed"));
    }
    Ok(admitted)
}

fn simple() -> Vec<Effect> {
    vec![
        Effect::Input(0),
        Effect::Cast {
            result: 1,
            value: 0,
            kind: InputScalarType::I8,
        },
        Effect::Cast {
            result: 2,
            value: 1,
            kind: InputScalarType::I8,
        },
        Effect::Cast {
            result: 3,
            value: 2,
            kind: InputScalarType::U8,
        },
        Effect::Cast {
            result: 4,
            value: 3,
            kind: InputScalarType::U8,
        },
        Effect::Output(4),
        Effect::Output(0),
        Effect::Input(5),
        Effect::Cast {
            result: 6,
            value: 5,
            kind: InputScalarType::I8,
        },
        Effect::Cast {
            result: 7,
            value: 6,
            kind: InputScalarType::U8,
        },
        Effect::Output(7),
    ]
}

#[test]
fn all_four_byte_bitcasts_preserve_actual_guest_bytes_and_consume_only_inputs() -> Result<(), String>
{
    let admitted = fixture(&simple())?;
    let layout = encode_latest_byte_identity_trace(&admitted, current_profile())
        .map_err(|error| format!("identity trace target: {error:?}"))?;
    if layout.source().len() != 6
        || layout.profile_id() != current_profile().id()
        || layout.profile_fingerprint() != current_profile().fingerprint()
    {
        return Err(String::from("identity alias source geometry drift"));
    }
    for (first, second) in [(0, 255), (255, 0), (128, 13), (42, 65)] {
        let mut vm = ProfileMachine::from_source(
            current_profile(),
            layout.source(),
            vec![first, second, 17],
        )
        .map_err(|error| format!("alias VM load: {error:?}"))?;
        if !matches!(vm.run(6), Ok(RunOutcome::Terminated { steps: 6, .. }))
            || vm.output() != [first, first, second]
            || vm.input_consumed() != 2
        {
            return Err(format!(
                "byte bitcast guest effects drift: {first} {second}"
            ));
        }
    }
    for previous in [
        encode_successful_byte_echo(&admitted, current_profile()),
        encode_successful_latest_byte_trace(&admitted, current_profile()),
    ] {
        if previous != Err(ByteEchoBridgeError::UnsupportedEffectTrace) {
            return Err(String::from(
                "existing latest/strict API admitted cast flow",
            ));
        }
    }
    Ok(())
}

#[test]
#[expect(clippy::too_many_lines, reason = "full invalid SSA alias matrix")]
fn identity_byte_bridge_rejects_stale_aliases_and_unsupported_shapes() -> Result<(), String> {
    for (index, effects) in [
        vec![Effect::Input(0), Effect::Output(0)],
        vec![
            Effect::Input(0),
            Effect::Cast {
                result: 1,
                value: 0,
                kind: InputScalarType::I8,
            },
        ],
        vec![
            Effect::Input(0),
            Effect::Input(1),
            Effect::Cast {
                result: 2,
                value: 0,
                kind: InputScalarType::U8,
            },
            Effect::Output(2),
        ],
        vec![
            Effect::Input(0),
            Effect::Cast {
                result: 1,
                value: 0,
                kind: InputScalarType::U8,
            },
            Effect::Input(2),
            Effect::Output(1),
        ],
        vec![
            Effect::Output(0),
            Effect::Input(1),
            Effect::Cast {
                result: 2,
                value: 1,
                kind: InputScalarType::U8,
            },
        ],
    ]
    .into_iter()
    .enumerate()
    {
        let program = match fixture(&effects) {
            Ok(program) => program,
            Err(_) if index == 4 => continue,
            Err(error) => return Err(format!("valid stale-alias fixture: {error}")),
        };
        if encode_latest_byte_identity_trace(&program, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(String::from("unproved byte alias admitted"));
        }
    }
    let good = fixture(&simple())?;
    if encode_latest_byte_identity_trace(&good, historical_profile())
        != Err(ByteEchoBridgeError::ProfileMismatch)
    {
        return Err(String::from("alias trace admitted foreign profile"));
    }
    Ok(())
}

#[test]
fn bitcast_alone_does_not_consume_guest_code_capacity() -> Result<(), String> {
    let mut effects = vec![
        Effect::Input(0),
        Effect::Cast {
            result: 1,
            value: 0,
            kind: InputScalarType::U8,
        },
    ];
    effects.extend(repeat_n(Effect::Output(1), 4094));
    let program = fixture(&effects)?;
    let layout = encode_latest_byte_identity_trace(&program, current_profile())
        .map_err(|error| format!("max alias-only trace: {error:?}"))?;
    if layout.source().len() != 4096 {
        return Err(String::from("identity trace code should be 4096 cells"));
    }
    let mut vm = ProfileMachine::from_source(current_profile(), layout.source(), vec![255])
        .map_err(|error| format!("max alias guest VM load: {error:?}"))?;
    if !matches!(vm.run(4096), Ok(RunOutcome::Terminated { steps: 4096, .. }))
        || vm.input_consumed() != 1
        || vm.output().len() != 4094
        || vm.output().iter().any(|byte| *byte != 255)
    {
        return Err(String::from("max identity guest output/steps drift"));
    }
    effects.push(Effect::Output(1));
    if encode_latest_byte_identity_trace(&fixture(&effects)?, current_profile()).is_ok() {
        return Err(String::from("identity trace beyond bound admitted"));
    }
    Ok(())
}
