// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE-APACHE-2.0
//
// Boundary-Contract:
// - Owns:
//   - Fail-closed lowering of admitted typed-IR semantic projections.
// - Must-Not:
//   - Parse C, serialize a target wire format, choose layout, or encode
//     Malbolge.
// - Allows:
//   - Inputs: explicit validated typed-IR projection records.
//   - Outputs: provenance-preserving pre-layout ternary programs.
//   - Side effects: returned compiler-value allocation only.
// - Split-When:
//   - Another operation family requires independent lowering policy.
// - Merge-When:
//   - Another application module owns this exact projection-to-ternary
//     boundary.
// - Summary:
//   - Lowers initial scalar and successful byte-effect semantics to target IR.
// - Description:
//   - The implemented slice remains closed and rejects every other shape.
// - Usage:
//   - Called after upstream typed-IR admission and explicit semantic
//     projection.
// - Defaults:
//   - Unsupported valid semantics fail explicitly rather than being
//     approximated.
//

//! Fail-closed typed-IR projection to pre-layout ternary lowering.

use super::input::{
    InputFunction, InputInstruction, InputScalarType, InputSourceSpan,
    InputTerminator, TypedIrInput,
};
use super::model::{
    TernaryFunction, TernaryI32Scalar, TernaryOperation, TernaryProgram,
    TernarySourcePosition, TernarySourceSpan,
};

const ABI_ID: &str = "malbolge-c32-v1";
const TARGET_PROFILE: &str = "malbolge-2026";
const TYPED_IR_VERSION: u16 = 1;

type BinaryAndInput = (u32, u32, u32, InputSourceSpan, InputScalarType);
type ByteInput = (u32, InputSourceSpan, InputScalarType);
type ConstantI32Input<'input> =
    (u16, &'input [u8], u32, InputSourceSpan, InputScalarType);
type TruncateInput = (u32, InputSourceSpan, InputScalarType, u32);

#[derive(Default)]
struct LoweringState {
    byte_values: Vec<u32>,
    i32_values: Vec<u32>,
}

/// Stable failures for the implemented ternary lowering slice.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TernaryLoweringError {
    /// Inbound projection identity or SSA structure is malformed.
    InvalidProjection,
    /// A function shape is outside the implemented lowering slice.
    UnsupportedFunction,
    /// A typed instruction is outside the implemented lowering slice.
    UnsupportedInstruction,
    /// Module-level state is outside the implemented lowering slice.
    UnsupportedModule,
    /// The return terminator is outside the implemented lowering slice.
    UnsupportedTerminator,
}

const fn copy_span(span: InputSourceSpan) -> TernarySourceSpan {
    TernarySourceSpan {
        begin: TernarySourcePosition {
            byte: span.begin.byte,
            column: span.begin.column,
            line: span.begin.line,
        },
        end: TernarySourcePosition {
            byte: span.end.byte,
            column: span.end.column,
            line: span.end.line,
        },
    }
}

fn lower_function(
    function: &InputFunction,
) -> Result<TernaryFunction, TernaryLoweringError> {
    if function.parameter_count != 0 || function.blocks.len() != 1 {
        return Err(TernaryLoweringError::UnsupportedFunction);
    }
    let block = function
        .blocks
        .first()
        .ok_or(TernaryLoweringError::UnsupportedFunction)?;
    if block.id != function.entry || block.phi_count != 0 {
        return Err(TernaryLoweringError::UnsupportedFunction);
    }

    let mut state = LoweringState::default();
    let mut operations = Vec::new();
    for instruction in &block.instructions {
        operations.push(lower_instruction(instruction, &mut state)?);
    }

    let InputTerminator::Return { span: return_span, value } = block.terminator
    else {
        return Err(TernaryLoweringError::UnsupportedTerminator);
    };
    let Some(return_value) = value else {
        return Err(TernaryLoweringError::UnsupportedTerminator);
    };
    if !state.i32_values.contains(&return_value) {
        return Err(TernaryLoweringError::UnsupportedTerminator);
    }
    operations.push(TernaryOperation::Return {
        span: copy_span(return_span),
        value: return_value,
    });

    Ok(TernaryFunction {
        id: function.id,
        name: function.name.clone(),
        operations,
        span: copy_span(function.span),
    })
}

fn lower_instruction(
    instruction: &InputInstruction,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    match instruction {
        InputInstruction::BinaryAnd {
            left,
            result,
            right,
            span,
            type_kind,
        } => {
            lower_binary_and((*left, *result, *right, *span, *type_kind), state)
        },
        InputInstruction::ByteInput { result, span, type_kind } => {
            lower_byte_input((*result, *span, *type_kind), state)
        },
        InputInstruction::ByteOutput { span, value } => {
            lower_byte_output(*span, *value, state)
        },
        InputInstruction::ConstantInteger {
            bit_width,
            little_endian,
            result,
            span,
            type_kind,
        } => lower_constant_i32(
            (
                *bit_width,
                little_endian.as_slice(),
                *result,
                *span,
                *type_kind,
            ),
            state,
        ),
        InputInstruction::TruncateInteger {
            result,
            span,
            type_kind,
            value,
        } => lower_truncate_i32_to_u8(
            (*result, *span, *type_kind, *value),
            state,
        ),
        InputInstruction::Unsupported => {
            Err(TernaryLoweringError::UnsupportedInstruction)
        },
    }
}

fn lower_binary_and(
    input: BinaryAndInput,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (left, result, right, span, type_kind) = input;
    if type_kind != InputScalarType::I32
        || !state.i32_values.contains(&left)
        || !state.i32_values.contains(&right)
    {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    ensure_new_value(state, result)?;
    state.i32_values.push(result);
    Ok(TernaryOperation::AndI32 {
        left,
        result,
        right,
        span: copy_span(span),
    })
}

fn lower_byte_input(
    input: ByteInput,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (result, span, type_kind) = input;
    if type_kind != InputScalarType::U8 {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    ensure_new_value(state, result)?;
    state.byte_values.push(result);
    Ok(TernaryOperation::ByteInput {
        result,
        span: copy_span(span),
    })
}

fn lower_byte_output(
    span: InputSourceSpan,
    value: u32,
    state: &LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    if !state.byte_values.contains(&value) {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    Ok(TernaryOperation::ByteOutput {
        span: copy_span(span),
        value,
    })
}

fn lower_constant_i32(
    input: ConstantI32Input<'_>,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (bit_width, little_endian, result, span, type_kind) = input;
    if bit_width != 32 || type_kind != InputScalarType::I32 {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    let bytes: [u8; 4] = little_endian
        .try_into()
        .map_err(|_error| TernaryLoweringError::UnsupportedInstruction)?;
    ensure_new_value(state, result)?;
    state.i32_values.push(result);
    Ok(TernaryOperation::MaterializeI32 {
        result,
        scalar: TernaryI32Scalar::from_bits(u32::from_le_bytes(bytes)),
        span: copy_span(span),
    })
}

fn lower_truncate_i32_to_u8(
    input: TruncateInput,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (result, span, type_kind, value) = input;
    if type_kind != InputScalarType::U8 || !state.i32_values.contains(&value) {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    ensure_new_value(state, result)?;
    state.byte_values.push(result);
    Ok(TernaryOperation::TruncateI32ToU8 {
        result,
        span: copy_span(span),
        value,
    })
}

fn ensure_new_value(
    state: &LoweringState,
    value: u32,
) -> Result<(), TernaryLoweringError> {
    if state.byte_values.contains(&value) || state.i32_values.contains(&value) {
        return Err(TernaryLoweringError::InvalidProjection);
    }
    Ok(())
}

fn validate_projection(
    input: &TypedIrInput,
) -> Result<(), TernaryLoweringError> {
    if input.abi_id != ABI_ID
        || input.input_format_version != TYPED_IR_VERSION
        || input.source_id.is_empty()
        || input.target_profile != TARGET_PROFILE
    {
        return Err(TernaryLoweringError::InvalidProjection);
    }
    Ok(())
}

/// Lowers one validated typed-IR semantic projection into the initial model.
///
/// # Errors
///
/// Returns [`TernaryLoweringError`] when the projection is malformed or uses
/// semantics outside the implemented `i32` constant/AND, `i32`-to-`u8`
/// truncation, return, and successful byte-effect slice.
pub fn lower_typed_ir(
    input: &TypedIrInput,
) -> Result<TernaryProgram, TernaryLoweringError> {
    validate_projection(input)?;
    if input.global_count != 0 || input.proof_obligation_count != 0 {
        return Err(TernaryLoweringError::UnsupportedModule);
    }
    let functions = input
        .functions
        .iter()
        .map(lower_function)
        .collect::<Result<Vec<_>, _>>()?;
    Ok(TernaryProgram {
        abi_id: input.abi_id.clone(),
        functions,
        input_format_version: input.input_format_version,
        source_id: input.source_id.clone(),
        source_sha256: input.source_sha256,
        target_profile: input.target_profile.clone(),
    })
}
