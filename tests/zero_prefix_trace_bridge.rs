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
//   - Canonical MCTR mixed zero-prefix/latest-input trace execution evidence.
// - Must-Not:
//   - Claim arbitrary constant materialization, source C or guest ABI.
// - Allows:
//   - Inputs: verified zero scalar and successful-byte effect projections.
//   - Outputs: exact normative VM source/SSA/output/consumption witnesses.
//   - Side effects: bounded real VM execution only.
// - Split-When:
//   - General byte SSA memory requires executable guest storage.
// - Merge-When:
//   - General verified ternary compiler admits the exact same subset.
// - Summary:
//   - Real guest A starts at zero, then each read overwrites A for outputs.
// - Description:
//   - Proves mixed output and read order with fail-closed stale SSA.
// - Usage:
//   - cargo test --locked --test zero_prefix_trace_bridge.
// - Defaults:
//   - Never emulate guest I/O with host byte output.

#![doc = "Canonical zero-prefixed successful-byte output guest VM proof."]

#[path = "../src/compiler/byte-echo-bridge/composition/lib.rs"]
pub mod bridge;

use bridge::ternary::{
    InputBlock, InputFunction, InputInstruction, InputScalarType, InputSourcePosition,
    InputSourceSpan, InputTerminator, TernaryOperation, TernaryProgram, TypedIrInput,
    canonical_ternary_bytes, canonical_ternary_program, lower_typed_ir,
};
use bridge::{
    ByteEchoBridgeError, encode_initial_zero_outputs, encode_successful_byte_echo,
    encode_successful_latest_byte_trace, encode_zero_prefixed_latest_byte_trace,
};
use malbolge::{ProfileMachine, RunOutcome, current_profile, historical_profile};
use std::iter::repeat_n;

#[derive(Clone, Copy)]
enum Effect {
    Input(u32),
    Output(u32),
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

#[expect(
    clippy::too_many_lines,
    reason = "fully specified canonical IR fixture"
)]
fn lowered_program(zero: u8, effects: &[Effect]) -> Result<TernaryProgram, String> {
    let mut instructions = Vec::with_capacity(effects.len().saturating_add(1));
    instructions.push(InputInstruction::ConstantInteger {
        bit_width: 8,
        little_endian: vec![zero],
        result: 0,
        span: span(0, 1),
        type_kind: InputScalarType::U8,
    });
    for (index, effect) in effects.iter().enumerate() {
        let start = u32::try_from(index.saturating_add(1))
            .map_err(|error| format!("source location: {error}"))?;
        instructions.push(match effect {
            Effect::Input(result) => InputInstruction::ByteInput {
                result: *result,
                span: span(start, start.saturating_add(1)),
                type_kind: InputScalarType::U8,
            },
            Effect::Output(value) => InputInstruction::ByteOutput {
                span: span(start, start.saturating_add(1)),
                value: *value,
            },
        });
    }
    let end = u32::try_from(instructions.len().saturating_add(1))
        .map_err(|error| format!("terminal coordinate: {error}"))?;
    let source = TypedIrInput {
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
            name: String::from("zero_prefixed_trace"),
            parameter_count: 0,
            return_kind: InputScalarType::Void,
            span: span(0, end),
        }],
        global_count: 0,
        input_format_version: 1,
        proof_obligation_count: 0,
        source_id: String::from("fixtures/zero-prefixed-trace.c"),
        source_sha256: [0x73; 32],
        target_profile: String::from("malbolge-2026"),
    };
    let lowered =
        lower_typed_ir(&source).map_err(|error| format!("ternary source lowering: {error:?}"))?;
    let bytes = canonical_ternary_bytes(&lowered)
        .map_err(|error| format!("serialize canonical MCTR: {error:?}"))?;
    let admitted = canonical_ternary_program(&bytes)
        .map_err(|error| format!("independent MCTR decoder: {error:?}"))?;
    if admitted != lowered {
        return Err(String::from("MCTR source provenance not retained"));
    }
    Ok(admitted)
}

#[test]
fn zero_prefix_then_two_successful_reads_execute_exact_guest_bytes() -> Result<(), String> {
    let source = lowered_program(
        0,
        &[
            Effect::Output(0),
            Effect::Output(0),
            Effect::Input(1),
            Effect::Output(1),
            Effect::Output(1),
            Effect::Input(2),
            Effect::Output(2),
        ],
    )?;
    let layout = encode_zero_prefixed_latest_byte_trace(&source, current_profile())
        .map_err(|error| format!("mixed ternary bridge: {error:?}"))?;
    if layout.source().len() != 8
        || layout.profile_id() != current_profile().id()
        || layout.profile_fingerprint() != current_profile().fingerprint()
    {
        return Err(String::from("mixed ternary output geometry/profile drift"));
    }
    for (first, second) in [(0, 255), (255, 0), (128, 13), (42, 65)] {
        let mut vm = ProfileMachine::from_source(
            current_profile(),
            layout.source(),
            vec![first, second, 170],
        )
        .map_err(|error| format!("mixed real VM load: {error:?}"))?;
        if !matches!(vm.run(8), Ok(RunOutcome::Terminated { steps: 8, .. }))
            || vm.output() != [0, 0, first, first, second]
            || vm.input_consumed() != 2
        {
            return Err(format!(
                "real guest mixed trace mismatch: ({first}, {second})"
            ));
        }
    }
    Ok(())
}

#[test]
fn zero_prefix_mode_rejects_nonzero_stale_and_unselected_domains() -> Result<(), String> {
    let valid = lowered_program(0, &[Effect::Output(0), Effect::Input(1), Effect::Output(1)])?;
    for old in [
        encode_initial_zero_outputs(&valid, current_profile()),
        encode_successful_byte_echo(&valid, current_profile()),
        encode_successful_latest_byte_trace(&valid, current_profile()),
    ] {
        if old != Err(ByteEchoBridgeError::UnsupportedEffectTrace) {
            return Err(String::from("old bridge API unexpectedly broadened"));
        }
    }
    if encode_zero_prefixed_latest_byte_trace(&valid, historical_profile())
        != Err(ByteEchoBridgeError::ProfileMismatch)
    {
        return Err(String::from("mixed bridge accepted wrong profile"));
    }
    for (zero, effects) in [
        (
            1,
            vec![Effect::Output(0), Effect::Input(1), Effect::Output(1)],
        ),
        (0, vec![Effect::Input(1), Effect::Output(1)]),
        (0, vec![Effect::Output(0), Effect::Input(1)]),
        (
            0,
            vec![Effect::Output(0), Effect::Input(1), Effect::Output(0)],
        ),
        (
            0,
            vec![
                Effect::Output(0),
                Effect::Input(1),
                Effect::Input(2),
                Effect::Output(1),
            ],
        ),
    ] {
        let candidate = lowered_program(zero, &effects)?;
        if encode_zero_prefixed_latest_byte_trace(&candidate, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(String::from("unproved mixed byte SSA trace admitted"));
        }
    }
    Ok(())
}

#[test]
fn zero_prefix_mode_refuses_extra_valid_materialization() -> Result<(), String> {
    let mut program =
        lowered_program(0, &[Effect::Output(0), Effect::Input(1), Effect::Output(1)])?;
    let operation = program
        .functions
        .first_mut()
        .and_then(|function| function.operations.get_mut(1))
        .ok_or("first zero output effect missing")?;
    let TernaryOperation::ByteOutput { span, .. } = operation else {
        return Err(String::from("expected first output"));
    };
    *operation = TernaryOperation::MaterializeU8 {
        result: 1,
        scalar: bridge::ternary::TernaryU8Scalar::from_bits(0),
        span: *span,
    };
    let Some(function) = program.functions.first_mut() else {
        return Err(String::from("missing scalar function"));
    };
    if let Some(TernaryOperation::ByteInput { result, .. }) = function.operations.get_mut(2) {
        *result = 2;
    } else {
        return Err(String::from("missing byte read"));
    }
    if let Some(TernaryOperation::ByteOutput { value, .. }) = function.operations.get_mut(3) {
        *value = 2;
    } else {
        return Err(String::from("missing byte output"));
    }
    bridge::ternary::validate_ternary_program(&program)
        .map_err(|error| format!("extra scalar is valid MCTR: {error:?}"))?;
    if encode_zero_prefixed_latest_byte_trace(&program, current_profile())
        != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
    {
        return Err(String::from("extra valid materialization silently ignored"));
    }
    Ok(())
}

#[test]
fn zero_prefix_mode_exact_source_capacity_rejects_one_more_cell() -> Result<(), String> {
    let mut effects = vec![Effect::Output(0), Effect::Input(1)];
    effects.extend(repeat_n(Effect::Output(1), 4093));
    let source = lowered_program(0, &effects)?;
    let layout = encode_zero_prefixed_latest_byte_trace(&source, current_profile())
        .map_err(|error| format!("maximum mixed guest source: {error:?}"))?;
    if layout.source().len() != 4096 {
        return Err(String::from("maximum mixed layout is not 4096 cells"));
    }
    let mut vm = ProfileMachine::from_source(current_profile(), layout.source(), vec![255])
        .map_err(|error| format!("maximum mixed guest VM load: {error:?}"))?;
    if !matches!(vm.run(4096), Ok(RunOutcome::Terminated { steps: 4096, .. }))
        || vm.input_consumed() != 1
        || vm.output().len() != 4094
        || vm.output().first() != Some(&0)
        || vm
            .output()
            .get(1..)
            .is_none_or(|bytes| bytes.iter().any(|byte| *byte != 255))
    {
        return Err(String::from("maximum mixed trace changed real VM effects"));
    }
    effects.push(Effect::Output(1));
    let excessive = lowered_program(0, &effects)?;
    if !matches!(
        encode_zero_prefixed_latest_byte_trace(&excessive, current_profile()),
        Err(ByteEchoBridgeError::Layout(_))
    ) {
        return Err(String::from("mixed 4097-cell trace was not rejected"));
    }
    Ok(())
}
