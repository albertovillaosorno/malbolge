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
//   - Real-VM executable evidence for latest-successful-byte I/O traces.
// - Must-Not:
//   - Claim EOF, failed output, general SSA storage or guest ABI behavior.
// - Allows:
//   - Inputs: canonical ternary projections with byte I/O effects.
//   - Outputs: independently admitted graphical code, exact real VM traces.
//   - Side effects: in-memory normative VM execution only.
// - Split-When:
//   - General byte dataflow requires guest memory and executable helpers.
// - Merge-When:
//   - The complete compiler linker proves this exact I/O sublanguage.
// - Summary:
//   - Checks repeat-last-byte output and consumed-without-output effects.
// - Description:
//   - Verifies successful-byte traces, forged SSA, and size/profile bounds.
// - Usage:
//   - cargo test --locked --test byte_io_trace_bridge.
// - Defaults:
//   - Every read succeeds with one byte, and output always succeeds.
//
//! Bounded executable last-read I/O traces with no host guest computation.

#[path = "../src/compiler/byte-echo-bridge/composition/lib.rs"]
pub mod bridge;

use bridge::layout::LinearLayoutError;
use bridge::ternary::{
    InputBlock, InputFunction, InputInstruction, InputScalarType, InputSourcePosition,
    InputSourceSpan, InputTerminator, TernaryOperation, TernaryProgram, TypedIrInput,
    canonical_ternary_bytes, canonical_ternary_program, lower_typed_ir,
};
use bridge::{
    ByteEchoBridgeError, encode_successful_byte_echo, encode_successful_latest_byte_trace,
};
use malbolge::{ProfileMachine, RunOutcome, current_profile, historical_profile};
use std::iter::repeat_n;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Effect {
    Read(u32),
    Write(u32),
}

const fn position(byte: u32) -> InputSourcePosition {
    InputSourcePosition {
        byte,
        column: byte.saturating_add(1),
        line: 1,
    }
}

const fn span(start: u32, end: u32) -> InputSourceSpan {
    InputSourceSpan {
        begin: position(start),
        end: position(end),
    }
}

fn projection(effects: &[Effect]) -> Result<TypedIrInput, String> {
    let mut instructions = Vec::with_capacity(effects.len());
    for (index, effect) in effects.iter().enumerate() {
        let start = u32::try_from(index).map_err(|error| format!("source offset: {error}"))?;
        let source = span(start, start.saturating_add(1));
        match effect {
            Effect::Read(result) => instructions.push(InputInstruction::ByteInput {
                result: *result,
                span: source,
                type_kind: InputScalarType::U8,
            }),
            Effect::Write(value) => instructions.push(InputInstruction::ByteOutput {
                span: source,
                value: *value,
            }),
        }
    }
    let end = u32::try_from(effects.len().saturating_add(1))
        .map_err(|error| format!("return span: {error}"))?;
    Ok(TypedIrInput {
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
            name: String::from("latest_byte_trace"),
            parameter_count: 0,
            return_kind: InputScalarType::Void,
            span: span(0, end),
        }],
        global_count: 0,
        input_format_version: 1,
        proof_obligation_count: 0,
        source_id: String::from("fixtures/byte-io-trace.c"),
        source_sha256: [0xa3; 32],
        target_profile: String::from("malbolge-2026"),
    })
}

fn program(effects: &[Effect]) -> Result<TernaryProgram, String> {
    let lowered = lower_typed_ir(&projection(effects)?)
        .map_err(|error| format!("ternary lowering: {error:?}"))?;
    let bytes =
        canonical_ternary_bytes(&lowered).map_err(|error| format!("MCTR encoding: {error:?}"))?;
    let restored = canonical_ternary_program(&bytes)
        .map_err(|error| format!("independent MCTR admission: {error:?}"))?;
    if lowered != restored {
        return Err(String::from("canonical ternary round trip diverged"));
    }
    Ok(restored)
}

fn check_on_normative_vm(effects: &[Effect], input: &[u8]) -> Result<(), String> {
    let ternary = program(effects)?;
    let compiled = encode_successful_latest_byte_trace(&ternary, current_profile())
        .map_err(|error| format!("bridge admission: {error:?}"))?;
    if compiled.source().len() != effects.len().saturating_add(1) {
        return Err(String::from("unexpected code length"));
    }
    let mut expected_output = Vec::new();
    let mut consumed = 0usize;
    let mut last = None;
    for effect in effects {
        match effect {
            Effect::Read(_) => {
                last = input.get(consumed).copied();
                consumed = consumed.saturating_add(1);
            }
            Effect::Write(_) => {
                expected_output.push(last.ok_or("missing oracle byte")?);
            }
        }
    }
    let mut machine =
        ProfileMachine::from_source(current_profile(), compiled.source(), input.to_vec())
            .map_err(|error| format!("VM source admission: {error:?}"))?;
    let expected_steps = effects.len().saturating_add(1);
    if !matches!(machine.run(expected_steps),
        Ok(RunOutcome::Terminated { steps, .. }) if steps == expected_steps)
    {
        return Err(String::from("VM failed to terminate at exact trace bound"));
    }
    if machine.input_consumed() != consumed || machine.output() != expected_output {
        return Err(format!(
            "VM trace differs after {consumed} consumed byte(s)"
        ));
    }
    Ok(())
}

#[test]
fn consumed_and_repeated_successful_bytes_execute_on_real_vm() -> Result<(), String> {
    let cases = [
        vec![Effect::Read(0)],
        vec![Effect::Read(0), Effect::Read(1), Effect::Read(2)],
        vec![
            Effect::Read(0),
            Effect::Write(0),
            Effect::Write(0),
            Effect::Write(0),
        ],
        vec![
            Effect::Read(0),
            Effect::Read(1),
            Effect::Write(1),
            Effect::Write(1),
        ],
        vec![
            Effect::Read(0),
            Effect::Write(0),
            Effect::Read(1),
            Effect::Write(1),
            Effect::Write(1),
            Effect::Read(2),
            Effect::Read(3),
            Effect::Write(3),
        ],
    ];
    for case in cases {
        check_on_normative_vm(&case, &[0, 255, 128, 13, 10])?;
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "exact source code and old API guard"
)]
fn adjacent_echo_remains_byte_exact_with_existing_producer() -> Result<(), String> {
    for count in [1u32, 2, 3, 7, 64, 256] {
        let effects = (0..count)
            .flat_map(|value| [Effect::Read(value), Effect::Write(value)])
            .collect::<Vec<_>>();
        let lowered = program(&effects)?;
        let old = encode_successful_byte_echo(&lowered, current_profile())
            .map_err(|error| format!("old bridge: {error:?}"))?;
        let latest = encode_successful_latest_byte_trace(&lowered, current_profile())
            .map_err(|error| format!("latest byte bridge: {error:?}"))?;
        assert_eq!(old, latest);
        assert_eq!(old.source(), latest.source());
    }
    Ok(())
}

#[test]
fn all_256_successful_bytes_execute_with_duplicate_outputs() -> Result<(), String> {
    let effects = (0..=u8::MAX)
        .flat_map(|byte| {
            let id = u32::from(byte);
            [Effect::Read(id), Effect::Write(id), Effect::Write(id)]
        })
        .collect::<Vec<_>>();
    let bytes = (0..=u8::MAX).collect::<Vec<_>>();
    check_on_normative_vm(&effects, &bytes)?;
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "exact maximum admitted code length"
)]
fn maximum_layout_length_replays_only_last_successful_byte() -> Result<(), String> {
    let mut effects = Vec::with_capacity(4095);
    effects.push(Effect::Read(0));
    effects.extend(repeat_n(Effect::Write(0), 4094));
    check_on_normative_vm(&effects, &[255])?;
    effects.push(Effect::Write(0));
    assert_eq!(
        encode_successful_latest_byte_trace(&program(&effects)?, current_profile()),
        Err(ByteEchoBridgeError::Layout(LinearLayoutError::TooLong)),
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "unsupported SSA and profile checks"
)]
fn last_read_ssa_identity_must_match_every_output() -> Result<(), String> {
    let valid_source = [Effect::Read(0), Effect::Read(1), Effect::Write(0)];
    let lowered = program(&valid_source)?;
    assert_eq!(
        encode_successful_latest_byte_trace(&lowered, current_profile()),
        Err(ByteEchoBridgeError::UnsupportedEffectTrace),
    );
    let single_input = program(&[Effect::Read(0)])?;
    assert_eq!(
        encode_successful_latest_byte_trace(&single_input, historical_profile()),
        Err(ByteEchoBridgeError::ProfileMismatch),
    );
    assert_eq!(
        encode_successful_byte_echo(&single_input, current_profile()),
        Err(ByteEchoBridgeError::UnsupportedEffectTrace),
    );
    let doubled_output = program(&[Effect::Read(0), Effect::Write(0), Effect::Write(0)])?;
    assert_eq!(
        encode_successful_byte_echo(&doubled_output, current_profile()),
        Err(ByteEchoBridgeError::UnsupportedEffectTrace),
    );
    Ok(())
}

#[test]
#[expect(clippy::panic_in_result_fn, reason = "forged IR preflight rejection")]
fn unsupported_scalar_and_return_effects_reject_before_target_encoding() -> Result<(), String> {
    let mut scalar = projection(&[Effect::Read(0), Effect::Write(0)])?;
    let [function] = scalar.functions.as_mut_slice() else {
        return Err(String::from("missing fixture function"));
    };
    let [block] = function.blocks.as_mut_slice() else {
        return Err(String::from("missing fixture block"));
    };
    block.instructions.insert(
        1,
        InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: vec![17],
            result: 1,
            span: span(1, 2),
            type_kind: InputScalarType::U8,
        },
    );
    // Source-map coherence is deliberately re-established after inserting a
    // valid scalar, so rejection tests the unsupported effect, not bad spans.
    let output = block
        .instructions
        .get_mut(2)
        .ok_or("missing modified output")?;
    *output = InputInstruction::ByteOutput {
        span: span(2, 3),
        value: 0,
    };
    block.terminator = InputTerminator::Return {
        span: span(3, 4),
        value: None,
    };
    function.span = span(0, 4);
    let lowered =
        lower_typed_ir(&scalar).map_err(|error| format!("lower valid scalar: {error:?}"))?;
    assert_eq!(
        encode_successful_latest_byte_trace(&lowered, current_profile()),
        Err(ByteEchoBridgeError::UnsupportedEffectTrace),
    );
    let mut returning = projection(&[Effect::Read(0)])?;
    let [returning_function] = returning.functions.as_mut_slice() else {
        return Err(String::from("missing return function"));
    };
    returning_function.return_kind = InputScalarType::U8;
    let [returning_block] = returning_function.blocks.as_mut_slice() else {
        return Err(String::from("missing return block"));
    };
    returning_block.terminator = InputTerminator::Return {
        span: span(1, 2),
        value: Some(0),
    };
    let return_lowered =
        lower_typed_ir(&returning).map_err(|error| format!("lower valid return: {error:?}"))?;
    assert_eq!(
        encode_successful_latest_byte_trace(&return_lowered, current_profile()),
        Err(ByteEchoBridgeError::UnsupportedEffectTrace),
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "empty or invalid checkpoint rejection"
)]
fn no_input_empty_or_forged_canonical_state_cannot_be_emitted() -> Result<(), String> {
    let empty = program(&[])?;
    assert_eq!(
        encode_successful_latest_byte_trace(&empty, current_profile()),
        Err(ByteEchoBridgeError::UnsupportedEffectTrace),
    );
    let mut forged = program(&[Effect::Read(0), Effect::Write(0)])?;
    let [function] = forged.functions.as_mut_slice() else {
        return Err(String::from("missing program function"));
    };
    let Some(TernaryOperation::ByteOutput { value, .. }) = function.operations.get_mut(1) else {
        return Err(String::from("missing output"));
    };
    *value = 99;
    assert!(matches!(
        encode_successful_latest_byte_trace(&forged, current_profile()),
        Err(ByteEchoBridgeError::InvalidProgram(_)),
    ));
    Ok(())
}
