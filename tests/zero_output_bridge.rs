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
//   - Normative VM execution proof for exactly initial-zero guest output.
// - Must-Not:
//   - Claim nonzero constants, generic byte dataflow, EOF or host output.
// - Allows:
//   - Inputs: independently decoded MCTR with one zero scalar and outputs.
//   - Outputs: verified source, runtime byte and no-input-consumption evidence.
//   - Side effects: bounded normative VM execution only.
// - Split-When:
//   - General constant realization requires guest registers and data layout.
// - Merge-When:
//   - A complete typed source and runtime linker proves these same outputs.
// - Summary:
//   - Exact zero initialization yields guest `<` output without host callbacks.
// - Description:
//   - Validates SSA shape, scalar bits, profile, capacity and real VM effects.
// - Usage:
//   - cargo test --locked --test zero_output_bridge.
// - Defaults:
//   - Unproven output instructions reject before layout.
//
//! Canonical zero-scalar source to real guest output and halt, no input reads.

#[path = "../src/compiler/byte-echo-bridge/composition/lib.rs"]
pub mod bridge;

use bridge::ternary::{
    InputBlock, InputFunction, InputInstruction, InputScalarType, InputSourcePosition,
    InputSourceSpan, InputTerminator, TernaryOperation, TernaryProgram, TypedIrInput,
    canonical_ternary_bytes, canonical_ternary_program, lower_typed_ir,
};
use bridge::{
    ByteEchoBridgeError, encode_initial_zero_outputs, encode_successful_byte_echo,
    encode_successful_latest_byte_trace,
};
use malbolge::{ProfileMachine, RunOutcome, current_profile, historical_profile};
use std::iter::repeat_n;

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

fn zero_projection(value: u8, outputs: usize) -> Result<TypedIrInput, String> {
    let mut instructions = Vec::with_capacity(outputs.saturating_add(1));
    instructions.push(InputInstruction::ConstantInteger {
        bit_width: 8,
        little_endian: vec![value],
        result: 0,
        span: span(0, 1),
        type_kind: InputScalarType::U8,
    });
    for index in 0..outputs {
        let offset = u32::try_from(index.saturating_add(1))
            .map_err(|error| format!("output source coordinate: {error}"))?;
        instructions.push(InputInstruction::ByteOutput {
            span: span(offset, offset.saturating_add(1)),
            value: 0,
        });
    }
    let end = u32::try_from(outputs.saturating_add(2))
        .map_err(|error| format!("return source coordinate: {error}"))?;
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
            name: String::from("zero_output"),
            parameter_count: 0,
            return_kind: InputScalarType::Void,
            span: span(0, end),
        }],
        global_count: 0,
        input_format_version: 1,
        proof_obligation_count: 0,
        source_id: String::from("fixtures/zero-output.c"),
        source_sha256: [0x61; 32],
        target_profile: String::from("malbolge-2026"),
    })
}

fn zero_program(value: u8, outputs: usize) -> Result<TernaryProgram, String> {
    let lowered = lower_typed_ir(&zero_projection(value, outputs)?)
        .map_err(|error| format!("zero-byte source lowering: {error:?}"))?;
    let bytes = canonical_ternary_bytes(&lowered)
        .map_err(|error| format!("zero-byte MCTR serialization: {error:?}"))?;
    let independently_admitted = canonical_ternary_program(&bytes)
        .map_err(|error| format!("zero-byte MCTR admission: {error:?}"))?;
    if independently_admitted != lowered {
        return Err(String::from("zero-byte canonical provenance changed"));
    }
    Ok(independently_admitted)
}

#[test]
fn canonical_zero_scalar_outputs_execute_without_reading_input() -> Result<(), String> {
    for count in [1usize, 2, 7, 64] {
        let program = zero_program(0, count)?;
        let profile = current_profile();
        let source = canonical_ternary_bytes(&program)
            .map_err(|error| format!("canonical MCTR: {error:?}"))?;
        let restored = canonical_ternary_program(&source)
            .map_err(|error| format!("canonical MCTR decode: {error:?}"))?;
        let layout = encode_initial_zero_outputs(&restored, profile)
            .map_err(|error| format!("zero output bridge: {error:?}"))?;
        if layout.source().len() != count.saturating_add(1)
            || layout.profile_id() != profile.id()
            || layout.profile_fingerprint() != profile.fingerprint()
        {
            return Err(String::from(
                "zero byte layout geometry or identity mismatch",
            ));
        }
        let mut vm = ProfileMachine::from_source(profile, layout.source(), vec![255, 128])
            .map_err(|error| format!("initial accumulator VM load: {error:?}"))?;
        if !matches!(vm.run(count.saturating_add(1)),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == count.saturating_add(1))
            || vm.input_consumed() != 0
            || vm.output() != repeat_n(0u8, count).collect::<Vec<_>>()
        {
            return Err(String::from(
                "actual zero byte output or input consumption drift",
            ));
        }
    }
    Ok(())
}

#[test]
fn zero_output_mode_rejects_nonzero_empty_and_old_echo_shapes() -> Result<(), String> {
    let one = zero_program(0, 1)?;
    if encode_successful_byte_echo(&one, current_profile())
        != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        || encode_successful_latest_byte_trace(&one, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
    {
        return Err(String::from(
            "existing echo APIs changed their admitted domain",
        ));
    }
    for (value, outputs) in [(0, 0), (1, 1), (255, 3)] {
        let invalid = zero_program(value, outputs)?;
        if encode_initial_zero_outputs(&invalid, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(String::from("unproved byte or missing output was admitted"));
        }
    }
    if encode_initial_zero_outputs(&one, historical_profile())
        != Err(ByteEchoBridgeError::ProfileMismatch)
    {
        return Err(String::from("foreign target identity accepted"));
    }
    Ok(())
}

#[test]
fn zero_output_mode_rejects_stale_ssa_or_additional_materialization() -> Result<(), String> {
    let source = zero_program(0, 2)?;
    let mut stale = source.clone();
    if let Some(TernaryOperation::ByteOutput { value, .. }) = stale
        .functions
        .first_mut()
        .and_then(|function| function.operations.get_mut(1))
    {
        *value = 7;
    } else {
        return Err(String::from("expected guest output fixture"));
    }
    if encode_initial_zero_outputs(&stale, current_profile()).is_ok() {
        return Err(String::from("undefined zero output SSA accepted"));
    }
    let mut extra = source;
    let Some(function) = extra.functions.first_mut() else {
        return Err(String::from("missing valid zero-output function"));
    };
    let Some(operation) = function.operations.get_mut(1) else {
        return Err(String::from("missing zero-output target effect"));
    };
    let TernaryOperation::ByteOutput { span, .. } = operation else {
        return Err(String::from("first effect was not a guest output"));
    };
    *operation = TernaryOperation::MaterializeU8 {
        result: 1,
        scalar: bridge::ternary::TernaryU8Scalar::from_bits(0),
        span: *span,
    };
    bridge::ternary::validate_ternary_program(&extra)
        .map_err(|error| format!("additional constant is not a valid MCTR: {error:?}"))?;
    if encode_initial_zero_outputs(&extra, current_profile())
        != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
    {
        return Err(String::from("extra valid constant was silently ignored"));
    }
    Ok(())
}

#[test]
fn exact_4096_cell_zero_output_cap_rejects_next_cell() -> Result<(), String> {
    let source = zero_program(0, 4095)?;
    let layout = encode_initial_zero_outputs(&source, current_profile())
        .map_err(|error| format!("maximum zero output source: {error:?}"))?;
    if layout.source().len() != 4096 {
        return Err(String::from("maximum zero guest code geometry drift"));
    }
    let mut vm = ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        .map_err(|error| format!("maximum zero guest VM load: {error:?}"))?;
    if !matches!(vm.run(4096), Ok(RunOutcome::Terminated { steps: 4096, .. }))
        || vm.input_consumed() != 0
        || vm.output() != repeat_n(0u8, 4095).collect::<Vec<_>>()
    {
        return Err(String::from("maximum zero output VM semantics mismatch"));
    }
    let excessive = zero_program(0, 4096)?;
    if !matches!(
        encode_initial_zero_outputs(&excessive, current_profile()),
        Err(ByteEchoBridgeError::Layout(_))
    ) {
        return Err(String::from(
            "4097 code cells were not rejected by target layout",
        ));
    }
    Ok(())
}
