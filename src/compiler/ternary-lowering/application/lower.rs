// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Fail-closed lowering of the first admitted typed-IR semantic projection.
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
//   - Lowers constant-return `i32` semantics to target trits.
// - Description:
//   - The initial slice is deliberately closed and rejects every other shape.
// - Usage:
//   - Called after upstream typed-IR admission and explicit semantic
//     projection.
// - Defaults:
//   - Unsupported valid semantics fail explicitly rather than being
//     approximated.
//

//! First fail-closed typed-IR projection to ternary lowering slice.

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

/// Stable failures for the initial ternary lowering slice.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TernaryLoweringError {
    /// Inbound projection identity or provenance is malformed.
    InvalidProjection,
    /// A function shape is outside the first lowering slice.
    UnsupportedFunction,
    /// A typed instruction is outside the first lowering slice.
    UnsupportedInstruction,
    /// Module-level state is outside the first lowering slice.
    UnsupportedModule,
    /// The return terminator is outside the first lowering slice.
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
    if block.id != function.entry
        || block.phi_count != 0
        || block.instructions.len() != 1
    {
        return Err(TernaryLoweringError::UnsupportedFunction);
    }
    let instruction = block
        .instructions
        .first()
        .ok_or(TernaryLoweringError::UnsupportedFunction)?;
    let InputInstruction::ConstantInteger {
        bit_width,
        little_endian,
        result,
        span,
        type_kind,
    } = instruction
    else {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    };
    if *bit_width != 32 || *type_kind != InputScalarType::I32 {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    let bytes: [u8; 4] = little_endian
        .as_slice()
        .try_into()
        .map_err(|_error| TernaryLoweringError::UnsupportedInstruction)?;
    let InputTerminator::Return { span: return_span, value } = block.terminator
    else {
        return Err(TernaryLoweringError::UnsupportedTerminator);
    };
    let Some(return_value) = value else {
        return Err(TernaryLoweringError::UnsupportedTerminator);
    };
    if return_value != *result {
        return Err(TernaryLoweringError::UnsupportedTerminator);
    }
    Ok(TernaryFunction {
        id: function.id,
        name: function.name.clone(),
        operations: vec![
            TernaryOperation::MaterializeI32 {
                result: *result,
                scalar: TernaryI32Scalar::from_bits(u32::from_le_bytes(bytes)),
                span: copy_span(*span),
            },
            TernaryOperation::Return {
                span: copy_span(return_span),
                value: return_value,
            },
        ],
        span: copy_span(function.span),
    })
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
/// semantics outside the deliberately closed constant-return `i32` slice.
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
