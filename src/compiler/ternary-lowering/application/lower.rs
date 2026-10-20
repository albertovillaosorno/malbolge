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

use std::collections::BTreeSet;

use super::input::{
    InputFunction, InputInstruction, InputScalarType, InputSourceSpan,
    InputTerminator, TypedIrInput,
};
use super::model::{
    TernaryFunction, TernaryI32Scalar, TernaryOperation, TernaryProgram,
    TernarySourcePosition, TernarySourceSpan, TernaryU8Scalar,
};

const ABI_ID: &str = "malbolge-c32-v1";
const TARGET_PROFILE: &str = "malbolge-2026";
const TYPED_IR_VERSION: u16 = 1;

type Binary32Input = (u32, u32, u32, InputSourceSpan, InputScalarType);
type ByteInput = (u32, InputSourceSpan, InputScalarType);
type ConstantI32Input<'input> =
    (u16, &'input [u8], u32, InputSourceSpan, InputScalarType);
type TruncateInput = (u32, InputSourceSpan, InputScalarType, u32);

#[derive(Clone, Copy)]
enum Bitwise32Kind {
    And,
    Or,
    Xor,
}

#[derive(Clone, Copy)]
enum Arithmetic32Kind {
    Add,
    DivideSigned,
    DivideUnsigned,
    Multiply,
    RemainderSigned,
    RemainderUnsigned,
    ShiftLeft,
    ShiftRightArithmetic,
    ShiftRightLogical,
    Subtract,
}

#[derive(Default)]
struct LoweringState {
    bytes: BTreeSet<u32>,
    signed: BTreeSet<u32>,
    unsigned: BTreeSet<u32>,
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
    let return_operation = match function.return_kind {
        InputScalarType::I32 if state.signed.contains(&return_value) => {
            TernaryOperation::Return {
                span: copy_span(return_span),
                value: return_value,
            }
        },
        InputScalarType::U32 if state.unsigned.contains(&return_value) => {
            TernaryOperation::ReturnU32 {
                span: copy_span(return_span),
                value: return_value,
            }
        },
        InputScalarType::U8 if state.bytes.contains(&return_value) => {
            TernaryOperation::ReturnU8 {
                span: copy_span(return_span),
                value: return_value,
            }
        },
        InputScalarType::I32
        | InputScalarType::Other
        | InputScalarType::U32
        | InputScalarType::U8 => {
            return Err(TernaryLoweringError::UnsupportedTerminator);
        },
    };
    operations.push(return_operation);

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
        InputInstruction::BinaryAdd { .. }
        | InputInstruction::BinaryMultiply { .. }
        | InputInstruction::BinarySubtract { .. } => {
            lower_arithmetic_instruction(instruction, state)
        },
        InputInstruction::BinaryDivideSigned { .. }
        | InputInstruction::BinaryDivideUnsigned { .. }
        | InputInstruction::BinaryRemainderSigned { .. }
        | InputInstruction::BinaryRemainderUnsigned { .. } => {
            lower_divrem_instruction(instruction, state)
        },
        InputInstruction::BinaryShiftLeft { .. }
        | InputInstruction::BinaryShiftRightArithmetic { .. }
        | InputInstruction::BinaryShiftRightLogical { .. } => {
            lower_shift_instruction(instruction, state)
        },
        InputInstruction::BinaryAnd { .. }
        | InputInstruction::BinaryOr { .. }
        | InputInstruction::BinaryXor { .. } => {
            lower_bitwise_instruction(instruction, state)
        },
        InputInstruction::ByteInput { .. }
        | InputInstruction::ByteOutput { .. }
        | InputInstruction::IntegerBitcast { .. }
        | InputInstruction::ConstantInteger { .. }
        | InputInstruction::TruncateInteger { .. }
        | InputInstruction::Unsupported
        | InputInstruction::ZeroExtendInteger { .. } => {
            lower_other_instruction(instruction, state)
        },
    }
}

fn lower_arithmetic_instruction(
    instruction: &InputInstruction,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (InputInstruction::BinaryAdd {
        left,
        result,
        right,
        span,
        type_kind,
    }
    | InputInstruction::BinarySubtract {
        left,
        result,
        right,
        span,
        type_kind,
    }
    | InputInstruction::BinaryMultiply {
        left,
        result,
        right,
        span,
        type_kind,
    }) = instruction
    else {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    };
    let kind = if matches!(instruction, InputInstruction::BinaryAdd { .. }) {
        Arithmetic32Kind::Add
    } else if matches!(instruction, InputInstruction::BinaryMultiply { .. }) {
        Arithmetic32Kind::Multiply
    } else {
        Arithmetic32Kind::Subtract
    };
    lower_arithmetic_word32(
        (*left, *result, *right, *span, *type_kind),
        kind,
        state,
    )
}

const fn divrem_kind(
    instruction: &InputInstruction,
) -> Result<Arithmetic32Kind, TernaryLoweringError> {
    if matches!(instruction, InputInstruction::BinaryDivideSigned { .. }) {
        return Ok(Arithmetic32Kind::DivideSigned);
    }
    if matches!(instruction, InputInstruction::BinaryDivideUnsigned { .. }) {
        return Ok(Arithmetic32Kind::DivideUnsigned);
    }
    if matches!(instruction, InputInstruction::BinaryRemainderSigned { .. }) {
        return Ok(Arithmetic32Kind::RemainderSigned);
    }
    if matches!(
        instruction,
        InputInstruction::BinaryRemainderUnsigned { .. }
    ) {
        return Ok(Arithmetic32Kind::RemainderUnsigned);
    }
    Err(TernaryLoweringError::UnsupportedInstruction)
}

fn lower_divrem_instruction(
    instruction: &InputInstruction,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (InputInstruction::BinaryDivideSigned {
        left,
        result,
        right,
        span,
        type_kind,
    }
    | InputInstruction::BinaryDivideUnsigned {
        left,
        result,
        right,
        span,
        type_kind,
    }
    | InputInstruction::BinaryRemainderSigned {
        left,
        result,
        right,
        span,
        type_kind,
    }
    | InputInstruction::BinaryRemainderUnsigned {
        left,
        result,
        right,
        span,
        type_kind,
    }) = instruction
    else {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    };
    let kind = divrem_kind(instruction)?;
    let expected_kind = if matches!(
        kind,
        Arithmetic32Kind::DivideSigned | Arithmetic32Kind::RemainderSigned
    ) {
        InputScalarType::I32
    } else {
        InputScalarType::U32
    };
    if *type_kind != expected_kind {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    lower_arithmetic_word32(
        (*left, *result, *right, *span, *type_kind),
        kind,
        state,
    )
}

fn lower_shift_instruction(
    instruction: &InputInstruction,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (InputInstruction::BinaryShiftLeft {
        left,
        result,
        right,
        span,
        type_kind,
    }
    | InputInstruction::BinaryShiftRightArithmetic {
        left,
        result,
        right,
        span,
        type_kind,
    }
    | InputInstruction::BinaryShiftRightLogical {
        left,
        result,
        right,
        span,
        type_kind,
    }) = instruction
    else {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    };
    let kind =
        if matches!(instruction, InputInstruction::BinaryShiftLeft { .. }) {
            Arithmetic32Kind::ShiftLeft
        } else if matches!(
            instruction,
            InputInstruction::BinaryShiftRightArithmetic { .. }
        ) {
            Arithmetic32Kind::ShiftRightArithmetic
        } else {
            Arithmetic32Kind::ShiftRightLogical
        };
    lower_arithmetic_word32(
        (*left, *result, *right, *span, *type_kind),
        kind,
        state,
    )
}

fn lower_bitwise_instruction(
    instruction: &InputInstruction,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (InputInstruction::BinaryAnd {
        left,
        result,
        right,
        span,
        type_kind,
    }
    | InputInstruction::BinaryOr {
        left,
        result,
        right,
        span,
        type_kind,
    }
    | InputInstruction::BinaryXor {
        left,
        result,
        right,
        span,
        type_kind,
    }) = instruction
    else {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    };
    let kind = if matches!(instruction, InputInstruction::BinaryAnd { .. }) {
        Bitwise32Kind::And
    } else if matches!(instruction, InputInstruction::BinaryOr { .. }) {
        Bitwise32Kind::Or
    } else {
        Bitwise32Kind::Xor
    };
    lower_binary_word32(
        (*left, *result, *right, *span, *type_kind),
        kind,
        state,
    )
}

fn lower_constant_projection(
    instruction: &InputInstruction,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
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
    lower_constant_integer(
        (
            *bit_width,
            little_endian.as_slice(),
            *result,
            *span,
            *type_kind,
        ),
        state,
    )
}

fn lower_other_instruction(
    instruction: &InputInstruction,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    match instruction {
        InputInstruction::ByteInput { result, span, type_kind } => {
            lower_byte_input((*result, *span, *type_kind), state)
        },
        InputInstruction::ByteOutput { span, value } => {
            lower_byte_output(*span, *value, state)
        },
        InputInstruction::ConstantInteger { .. } => {
            lower_constant_projection(instruction, state)
        },
        InputInstruction::TruncateInteger {
            result,
            span,
            type_kind,
            value,
        } => lower_truncate_i32_to_u8(
            (*result, *span, *type_kind, *value),
            state,
        ),
        InputInstruction::IntegerBitcast {
            result,
            span,
            type_kind,
            value,
        } => lower_integer_bitcast((*result, *span, *type_kind, *value), state),
        InputInstruction::ZeroExtendInteger {
            result,
            span,
            type_kind,
            value,
        } => lower_zero_extend_u8_to_u32(
            (*result, *span, *type_kind, *value),
            state,
        ),
        InputInstruction::Unsupported
        | InputInstruction::BinaryAnd { .. }
        | InputInstruction::BinaryOr { .. }
        | InputInstruction::BinaryXor { .. }
        | InputInstruction::BinaryAdd { .. }
        | InputInstruction::BinarySubtract { .. }
        | InputInstruction::BinaryMultiply { .. }
        | InputInstruction::BinaryDivideSigned { .. }
        | InputInstruction::BinaryDivideUnsigned { .. }
        | InputInstruction::BinaryRemainderSigned { .. }
        | InputInstruction::BinaryRemainderUnsigned { .. }
        | InputInstruction::BinaryShiftLeft { .. }
        | InputInstruction::BinaryShiftRightArithmetic { .. }
        | InputInstruction::BinaryShiftRightLogical { .. } => {
            Err(TernaryLoweringError::UnsupportedInstruction)
        },
    }
}

fn lower_arithmetic_word32(
    input: Binary32Input,
    kind: Arithmetic32Kind,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (left, result, right, span, type_kind) = input;
    let uses = match type_kind {
        InputScalarType::I32 => &state.signed,
        InputScalarType::U32 => &state.unsigned,
        InputScalarType::Other | InputScalarType::U8 => {
            return Err(TernaryLoweringError::UnsupportedInstruction);
        },
    };
    if !uses.contains(&left) || !uses.contains(&right) {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    ensure_new_value(state, result)?;
    let inserted = match type_kind {
        InputScalarType::I32 => state.signed.insert(result),
        InputScalarType::U32 => state.unsigned.insert(result),
        InputScalarType::Other | InputScalarType::U8 => false,
    };
    debug_assert!(inserted, "new SSA value was already preflighted");
    construct_arithmetic_operation(
        kind,
        type_kind,
        (left, result, right),
        copy_span(span),
    )
}

const fn construct_arithmetic_operation(
    kind: Arithmetic32Kind,
    type_kind: InputScalarType,
    operands: (u32, u32, u32),
    span: TernarySourceSpan,
) -> Result<TernaryOperation, TernaryLoweringError> {
    if matches!(
        kind,
        Arithmetic32Kind::DivideSigned
            | Arithmetic32Kind::DivideUnsigned
            | Arithmetic32Kind::RemainderSigned
            | Arithmetic32Kind::RemainderUnsigned
    ) {
        return construct_divrem_operation(kind, type_kind, operands, span);
    }
    if matches!(
        kind,
        Arithmetic32Kind::ShiftLeft
            | Arithmetic32Kind::ShiftRightArithmetic
            | Arithmetic32Kind::ShiftRightLogical
    ) {
        return construct_shift_operation(kind, type_kind, operands, span);
    }
    let (left, result, right) = operands;
    Ok(match (kind, type_kind) {
        (Arithmetic32Kind::Add, _) => {
            return construct_add_operation(type_kind, operands, span);
        },
        (Arithmetic32Kind::Multiply, InputScalarType::I32) => {
            TernaryOperation::MultiplyI32 {
                left,
                result,
                right,
                span,
            }
        },
        (Arithmetic32Kind::Multiply, InputScalarType::U32) => {
            TernaryOperation::MultiplyU32 {
                left,
                result,
                right,
                span,
            }
        },
        (Arithmetic32Kind::Subtract, _) => {
            return construct_subtract_operation(type_kind, operands, span);
        },
        (
            Arithmetic32Kind::DivideSigned
            | Arithmetic32Kind::DivideUnsigned
            | Arithmetic32Kind::RemainderSigned
            | Arithmetic32Kind::RemainderUnsigned
            | Arithmetic32Kind::ShiftLeft
            | Arithmetic32Kind::ShiftRightArithmetic
            | Arithmetic32Kind::ShiftRightLogical,
            _,
        )
        | (_, InputScalarType::Other | InputScalarType::U8) => {
            return Err(TernaryLoweringError::UnsupportedInstruction);
        },
    })
}

const fn construct_add_operation(
    type_kind: InputScalarType,
    operands: (u32, u32, u32),
    span: TernarySourceSpan,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (left, result, right) = operands;
    Ok(match type_kind {
        InputScalarType::I32 => TernaryOperation::AddI32 {
            left,
            result,
            right,
            span,
        },
        InputScalarType::U32 => TernaryOperation::AddU32 {
            left,
            result,
            right,
            span,
        },
        InputScalarType::Other | InputScalarType::U8 => {
            return Err(TernaryLoweringError::UnsupportedInstruction);
        },
    })
}

const fn construct_divrem_operation(
    kind: Arithmetic32Kind,
    type_kind: InputScalarType,
    operands: (u32, u32, u32),
    span: TernarySourceSpan,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (left, result, right) = operands;
    Ok(match (kind, type_kind) {
        (Arithmetic32Kind::DivideSigned, InputScalarType::I32) => {
            TernaryOperation::DivideI32 {
                left,
                result,
                right,
                span,
            }
        },
        (Arithmetic32Kind::DivideUnsigned, InputScalarType::U32) => {
            TernaryOperation::DivideU32 {
                left,
                result,
                right,
                span,
            }
        },
        (Arithmetic32Kind::RemainderSigned, InputScalarType::I32) => {
            TernaryOperation::RemainderI32 {
                left,
                result,
                right,
                span,
            }
        },
        (Arithmetic32Kind::RemainderUnsigned, InputScalarType::U32) => {
            TernaryOperation::RemainderU32 {
                left,
                result,
                right,
                span,
            }
        },
        (_, _) => return Err(TernaryLoweringError::UnsupportedInstruction),
    })
}

const fn construct_subtract_operation(
    type_kind: InputScalarType,
    operands: (u32, u32, u32),
    span: TernarySourceSpan,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (left, result, right) = operands;
    Ok(match type_kind {
        InputScalarType::I32 => TernaryOperation::SubtractI32 {
            left,
            result,
            right,
            span,
        },
        InputScalarType::U32 => TernaryOperation::SubtractU32 {
            left,
            result,
            right,
            span,
        },
        InputScalarType::Other | InputScalarType::U8 => {
            return Err(TernaryLoweringError::UnsupportedInstruction);
        },
    })
}

const fn construct_shift_operation(
    kind: Arithmetic32Kind,
    type_kind: InputScalarType,
    operands: (u32, u32, u32),
    span: TernarySourceSpan,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (left, result, right) = operands;
    Ok(match (kind, type_kind) {
        (Arithmetic32Kind::ShiftLeft, InputScalarType::I32) => {
            TernaryOperation::ShiftLeftI32 {
                left,
                result,
                right,
                span,
            }
        },
        (Arithmetic32Kind::ShiftLeft, InputScalarType::U32) => {
            TernaryOperation::ShiftLeftU32 {
                left,
                result,
                right,
                span,
            }
        },
        (Arithmetic32Kind::ShiftRightArithmetic, InputScalarType::I32) => {
            TernaryOperation::ShiftRightArithmeticI32 {
                left,
                result,
                right,
                span,
            }
        },
        (Arithmetic32Kind::ShiftRightLogical, InputScalarType::U32) => {
            TernaryOperation::ShiftRightLogicalU32 {
                left,
                result,
                right,
                span,
            }
        },
        (Arithmetic32Kind::ShiftRightArithmetic, InputScalarType::U32)
        | (Arithmetic32Kind::ShiftRightLogical, InputScalarType::I32) => {
            return Err(TernaryLoweringError::UnsupportedInstruction);
        },
        (_, _) => return Err(TernaryLoweringError::UnsupportedInstruction),
    })
}

fn lower_binary_word32(
    input: Binary32Input,
    kind: Bitwise32Kind,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (left, result, right, span, type_kind) = input;
    let uses = match type_kind {
        InputScalarType::I32 => &state.signed,
        InputScalarType::U32 => &state.unsigned,
        InputScalarType::Other | InputScalarType::U8 => {
            return Err(TernaryLoweringError::UnsupportedInstruction);
        },
    };
    if !uses.contains(&left) || !uses.contains(&right) {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    ensure_new_value(state, result)?;
    let inserted = match type_kind {
        InputScalarType::I32 => state.signed.insert(result),
        InputScalarType::U32 => state.unsigned.insert(result),
        InputScalarType::Other | InputScalarType::U8 => false,
    };
    debug_assert!(inserted, "new SSA value was already preflighted");
    construct_bitwise_operation(
        kind,
        type_kind,
        (left, result, right),
        copy_span(span),
    )
}

const fn construct_bitwise_operation(
    kind: Bitwise32Kind,
    type_kind: InputScalarType,
    operands: (u32, u32, u32),
    span: TernarySourceSpan,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (left, result, right) = operands;
    Ok(match (kind, type_kind) {
        (Bitwise32Kind::And, InputScalarType::I32) => {
            TernaryOperation::AndI32 {
                left,
                result,
                right,
                span,
            }
        },
        (Bitwise32Kind::And, InputScalarType::U32) => {
            TernaryOperation::AndU32 {
                left,
                result,
                right,
                span,
            }
        },
        (Bitwise32Kind::Or, InputScalarType::I32) => TernaryOperation::OrI32 {
            left,
            result,
            right,
            span,
        },
        (Bitwise32Kind::Or, InputScalarType::U32) => TernaryOperation::OrU32 {
            left,
            result,
            right,
            span,
        },
        (Bitwise32Kind::Xor, InputScalarType::I32) => {
            TernaryOperation::XorI32 {
                left,
                result,
                right,
                span,
            }
        },
        (Bitwise32Kind::Xor, InputScalarType::U32) => {
            TernaryOperation::XorU32 {
                left,
                result,
                right,
                span,
            }
        },
        (_, InputScalarType::Other | InputScalarType::U8) => {
            return Err(TernaryLoweringError::UnsupportedInstruction);
        },
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
    let inserted = state.bytes.insert(result);
    debug_assert!(inserted, "new SSA value was already preflighted");
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
    if !state.bytes.contains(&value) {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    Ok(TernaryOperation::ByteOutput {
        span: copy_span(span),
        value,
    })
}

fn lower_constant_integer(
    input: ConstantI32Input<'_>,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (bit_width, little_endian, result, span, type_kind) = input;
    if bit_width == 8 && type_kind == InputScalarType::U8 {
        let &[byte] = little_endian else {
            return Err(TernaryLoweringError::UnsupportedInstruction);
        };
        ensure_new_value(state, result)?;
        let inserted = state.bytes.insert(result);
        debug_assert!(inserted, "new SSA value was already preflighted");
        return Ok(TernaryOperation::MaterializeU8 {
            result,
            scalar: TernaryU8Scalar::from_bits(byte),
            span: copy_span(span),
        });
    }
    if bit_width != 32 {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    let bytes: [u8; 4] = little_endian
        .try_into()
        .map_err(|_error| TernaryLoweringError::UnsupportedInstruction)?;
    let scalar = TernaryI32Scalar::from_bits(u32::from_le_bytes(bytes));
    ensure_new_value(state, result)?;
    match type_kind {
        InputScalarType::I32 => {
            let inserted = state.signed.insert(result);
            debug_assert!(inserted, "new SSA value was already preflighted");
            Ok(TernaryOperation::MaterializeI32 {
                result,
                scalar,
                span: copy_span(span),
            })
        },
        InputScalarType::U32 => {
            let inserted = state.unsigned.insert(result);
            debug_assert!(inserted, "new SSA value was already preflighted");
            Ok(TernaryOperation::MaterializeU32 {
                result,
                scalar,
                span: copy_span(span),
            })
        },
        InputScalarType::Other | InputScalarType::U8 => {
            Err(TernaryLoweringError::UnsupportedInstruction)
        },
    }
}

fn lower_truncate_i32_to_u8(
    input: TruncateInput,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (result, span, type_kind, value) = input;
    if type_kind != InputScalarType::U8 {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    let source_signed = state.signed.contains(&value);
    if !source_signed && !state.unsigned.contains(&value) {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    ensure_new_value(state, result)?;
    let inserted = state.bytes.insert(result);
    debug_assert!(inserted, "new SSA value was already preflighted");
    let target_span = copy_span(span);
    if source_signed {
        Ok(TernaryOperation::TruncateI32ToU8 {
            result,
            span: target_span,
            value,
        })
    } else {
        Ok(TernaryOperation::TruncateU32ToU8 {
            result,
            span: target_span,
            value,
        })
    }
}

fn lower_zero_extend_u8_to_u32(
    input: TruncateInput,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (result, span, type_kind, value) = input;
    if type_kind != InputScalarType::U32 || !state.bytes.contains(&value) {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    ensure_new_value(state, result)?;
    let inserted = state.unsigned.insert(result);
    debug_assert!(inserted, "new SSA value was already preflighted");
    Ok(TernaryOperation::ZeroExtendU8ToU32 {
        result,
        span: copy_span(span),
        value,
    })
}

fn lower_integer_bitcast(
    input: TruncateInput,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (result, span, type_kind, value) = input;
    let signed_to_unsigned = match type_kind {
        InputScalarType::U32 if state.signed.contains(&value) => true,
        InputScalarType::I32 if state.unsigned.contains(&value) => false,
        InputScalarType::I32
        | InputScalarType::U32
        | InputScalarType::Other
        | InputScalarType::U8 => {
            return Err(TernaryLoweringError::UnsupportedInstruction);
        },
    };
    ensure_new_value(state, result)?;
    let inserted = if signed_to_unsigned {
        state.unsigned.insert(result)
    } else {
        state.signed.insert(result)
    };
    debug_assert!(inserted, "new SSA value was already preflighted");
    let target_span = copy_span(span);
    if signed_to_unsigned {
        Ok(TernaryOperation::BitcastI32ToU32 {
            result,
            span: target_span,
            value,
        })
    } else {
        Ok(TernaryOperation::BitcastU32ToI32 {
            result,
            span: target_span,
            value,
        })
    }
}

fn ensure_new_value(
    state: &LoweringState,
    value: u32,
) -> Result<(), TernaryLoweringError> {
    if state.bytes.contains(&value)
        || state.signed.contains(&value)
        || state.unsigned.contains(&value)
    {
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
/// semantics outside typed 32-bit constant/bitwise operations, `u8`
/// constants, narrowing to `u8`, return, and byte effects.
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
