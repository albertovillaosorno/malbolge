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
    InputFunction, InputInstruction, InputOrderedComparison, InputScalarType,
    InputSourceSpan, InputTerminator, TypedIrInput,
};
use super::model::{
    TernaryFunction, TernaryI32Scalar, TernaryOperation, TernaryProgram,
    TernarySourcePosition, TernarySourceSpan, TernaryU8Scalar,
    TernaryU16Scalar,
};

const ABI_ID: &str = "malbolge-c32-v1";
const TARGET_PROFILE: &str = "malbolge-2026";
const TYPED_IR_VERSION: u16 = 1;

type Binary32Input = (u32, u32, u32, InputSourceSpan, InputScalarType);
type ByteInput = (u32, InputSourceSpan, InputScalarType);
type NarrowConstantInput<'input> =
    (&'input [u8], u32, InputSourceSpan, InputScalarType);
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
    bools: BTreeSet<u32>,
    bytes: BTreeSet<u32>,
    signed: BTreeSet<u32>,
    signed_bytes: BTreeSet<u32>,
    signed_halves: BTreeSet<u32>,
    unsigned: BTreeSet<u32>,
    unsigned_halves: BTreeSet<u32>,
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
    if function.return_kind == InputScalarType::Void && value.is_none() {
        operations.push(TernaryOperation::ReturnVoid {
            span: copy_span(return_span),
        });
        return Ok(TernaryFunction {
            id: function.id,
            name: function.name.clone(),
            operations,
            span: copy_span(function.span),
        });
    }
    let Some(return_value) = value else {
        return Err(TernaryLoweringError::UnsupportedTerminator);
    };
    let return_operation = lower_return_operation(
        function.return_kind,
        &state,
        return_value,
        copy_span(return_span),
    )?;
    operations.push(return_operation);

    Ok(TernaryFunction {
        id: function.id,
        name: function.name.clone(),
        operations,
        span: copy_span(function.span),
    })
}

fn lower_return_operation(
    return_kind: InputScalarType,
    state: &LoweringState,
    return_value: u32,
    span: TernarySourceSpan,
) -> Result<TernaryOperation, TernaryLoweringError> {
    Ok(match return_kind {
        InputScalarType::Bool if state.bools.contains(&return_value) => {
            TernaryOperation::ReturnBool {
                span,
                value: return_value,
            }
        },
        InputScalarType::I16 if state.signed_halves.contains(&return_value) => {
            TernaryOperation::ReturnI16 {
                span,
                value: return_value,
            }
        },
        InputScalarType::I8 if state.signed_bytes.contains(&return_value) => {
            TernaryOperation::ReturnI8 {
                span,
                value: return_value,
            }
        },
        InputScalarType::I32 if state.signed.contains(&return_value) => {
            TernaryOperation::Return {
                span,
                value: return_value,
            }
        },
        InputScalarType::U16
            if state.unsigned_halves.contains(&return_value) =>
        {
            TernaryOperation::ReturnU16 {
                span,
                value: return_value,
            }
        },
        InputScalarType::U32 if state.unsigned.contains(&return_value) => {
            TernaryOperation::ReturnU32 {
                span,
                value: return_value,
            }
        },
        InputScalarType::U8 if state.bytes.contains(&return_value) => {
            TernaryOperation::ReturnU8 {
                span,
                value: return_value,
            }
        },
        InputScalarType::Bool
        | InputScalarType::I16
        | InputScalarType::I32
        | InputScalarType::I8
        | InputScalarType::Other
        | InputScalarType::U16
        | InputScalarType::U32
        | InputScalarType::U8
        | InputScalarType::Void => {
            return Err(TernaryLoweringError::UnsupportedTerminator);
        },
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
        InputInstruction::CompareEqual { .. }
        | InputInstruction::CompareNotEqual { .. } => {
            lower_comparison_instruction(instruction, state)
        },
        InputInstruction::CompareOrdered { .. } => {
            lower_ordered_comparison_instruction(instruction, state)
        },
        InputInstruction::BoolToSigned { .. }
        | InputInstruction::ByteInput { .. }
        | InputInstruction::ByteOutput { .. }
        | InputInstruction::IntegerBitcast { .. }
        | InputInstruction::IntegerToBool { .. }
        | InputInstruction::ConstantInteger { .. }
        | InputInstruction::TruncateInteger { .. }
        | InputInstruction::SignExtendI8ToI32 { .. }
        | InputInstruction::Unsupported
        | InputInstruction::ZeroExtendInteger { .. } => {
            lower_other_instruction(instruction, state)
        },
    }
}

fn lower_comparison_instruction(
    instruction: &InputInstruction,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (InputInstruction::CompareEqual {
        left,
        result,
        right,
        span,
        type_kind,
    }
    | InputInstruction::CompareNotEqual {
        left,
        result,
        right,
        span,
        type_kind,
    }) = instruction
    else {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    };
    if *type_kind != InputScalarType::Bool {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    let signed = state.signed.contains(left) && state.signed.contains(right);
    let unsigned =
        state.unsigned.contains(left) && state.unsigned.contains(right);
    if !signed && !unsigned {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    ensure_new_value(state, *result)?;
    let inserted = state.bools.insert(*result);
    debug_assert!(inserted, "new SSA value was already preflighted");
    construct_comparison_operation(
        signed,
        instruction,
        (*left, *result, *right),
        copy_span(*span),
    )
}

const fn construct_comparison_operation(
    signed: bool,
    instruction: &InputInstruction,
    operands: (u32, u32, u32),
    span: TernarySourceSpan,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (left, result, right) = operands;
    Ok(match (signed, instruction) {
        (true, InputInstruction::CompareEqual { .. }) => {
            TernaryOperation::EqualI32 {
                left,
                result,
                right,
                span,
            }
        },
        (false, InputInstruction::CompareEqual { .. }) => {
            TernaryOperation::EqualU32 {
                left,
                result,
                right,
                span,
            }
        },
        (true, InputInstruction::CompareNotEqual { .. }) => {
            TernaryOperation::NotEqualI32 {
                left,
                result,
                right,
                span,
            }
        },
        (false, InputInstruction::CompareNotEqual { .. }) => {
            TernaryOperation::NotEqualU32 {
                left,
                result,
                right,
                span,
            }
        },
        (_, _) => return Err(TernaryLoweringError::UnsupportedInstruction),
    })
}

fn lower_ordered_comparison_instruction(
    instruction: &InputInstruction,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let InputInstruction::CompareOrdered {
        left,
        operation,
        result,
        right,
        span,
        type_kind,
    } = instruction
    else {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    };
    if *type_kind != InputScalarType::Bool {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    let uses = match operation {
        InputOrderedComparison::Signed
        | InputOrderedComparison::SignedEqual => &state.signed,
        InputOrderedComparison::Unsigned
        | InputOrderedComparison::UnsignedEqual => &state.unsigned,
    };
    if !uses.contains(left) || !uses.contains(right) {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    ensure_new_value(state, *result)?;
    let inserted = state.bools.insert(*result);
    debug_assert!(inserted, "new SSA value was already preflighted");
    Ok(construct_ordered_comparison(
        *operation,
        (*left, *result, *right),
        copy_span(*span),
    ))
}

const fn construct_ordered_comparison(
    operation: InputOrderedComparison,
    operands: (u32, u32, u32),
    span: TernarySourceSpan,
) -> TernaryOperation {
    let (left, result, right) = operands;
    match operation {
        InputOrderedComparison::Signed => TernaryOperation::LessSignedI32 {
            left,
            result,
            right,
            span,
        },
        InputOrderedComparison::SignedEqual => {
            TernaryOperation::LessSignedEqualI32 {
                left,
                result,
                right,
                span,
            }
        },
        InputOrderedComparison::Unsigned => TernaryOperation::LessUnsignedU32 {
            left,
            result,
            right,
            span,
        },
        InputOrderedComparison::UnsignedEqual => {
            TernaryOperation::LessUnsignedEqualU32 {
                left,
                result,
                right,
                span,
            }
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

fn lower_boolean_cast(
    instruction: &InputInstruction,
    state: &mut LoweringState,
) -> Option<Result<TernaryOperation, TernaryLoweringError>> {
    if let InputInstruction::BoolToSigned {
        result,
        span,
        type_kind,
        value,
    } = instruction
    {
        return Some(lower_bool_to_signed(
            (*result, *span, *type_kind, *value),
            state,
        ));
    }
    if let InputInstruction::IntegerToBool {
        result,
        span,
        type_kind,
        value,
    } = instruction
    {
        return Some(lower_integer_to_bool(
            (*result, *span, *type_kind, *value),
            state,
        ));
    }
    if let InputInstruction::SignExtendI8ToI32 {
        result,
        span,
        type_kind,
        value,
    } = instruction
    {
        return Some(lower_sign_extend_i8_to_i32(
            (*result, *span, *type_kind, *value),
            state,
        ));
    }
    None
}

fn lower_other_instruction(
    instruction: &InputInstruction,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    if let Some(result) = lower_boolean_cast(instruction, state) {
        return result;
    }
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
        } => lower_truncate_word_to_byte(
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
        InputInstruction::SignExtendI8ToI32 { .. }
        | InputInstruction::BoolToSigned { .. }
        | InputInstruction::IntegerToBool { .. }
        | InputInstruction::Unsupported
        | InputInstruction::CompareEqual { .. }
        | InputInstruction::CompareNotEqual { .. }
        | InputInstruction::CompareOrdered { .. }
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
        InputScalarType::Bool
        | InputScalarType::Other
        | InputScalarType::U8
        | InputScalarType::I8
        | InputScalarType::I16
        | InputScalarType::U16
        | InputScalarType::Void => {
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
        InputScalarType::Bool
        | InputScalarType::Other
        | InputScalarType::U8
        | InputScalarType::I8
        | InputScalarType::I16
        | InputScalarType::U16
        | InputScalarType::Void => false,
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
        _ => return Err(TernaryLoweringError::UnsupportedInstruction),
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
        InputScalarType::Bool
        | InputScalarType::Other
        | InputScalarType::U8
        | InputScalarType::I8
        | InputScalarType::I16
        | InputScalarType::U16
        | InputScalarType::Void => {
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
        InputScalarType::Bool
        | InputScalarType::Other
        | InputScalarType::U8
        | InputScalarType::I8
        | InputScalarType::I16
        | InputScalarType::U16
        | InputScalarType::Void => {
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
        InputScalarType::Bool
        | InputScalarType::Other
        | InputScalarType::U8
        | InputScalarType::I8
        | InputScalarType::I16
        | InputScalarType::U16
        | InputScalarType::Void => {
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
        InputScalarType::Bool
        | InputScalarType::Other
        | InputScalarType::U8
        | InputScalarType::I8
        | InputScalarType::I16
        | InputScalarType::U16
        | InputScalarType::Void => false,
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
        (
            _,
            InputScalarType::Bool
            | InputScalarType::Other
            | InputScalarType::U8
            | InputScalarType::I8
            | InputScalarType::I16
            | InputScalarType::U16
            | InputScalarType::Void,
        ) => {
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

fn lower_boolean_constant(
    little_endian: &[u8],
    result: u32,
    span: InputSourceSpan,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let &[bit @ 0..=1] = little_endian else {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    };
    ensure_new_value(state, result)?;
    let inserted = state.bools.insert(result);
    debug_assert!(inserted, "new SSA value was already preflighted");
    Ok(TernaryOperation::MaterializeBool {
        result,
        value: bit == 1,
        span: copy_span(span),
    })
}

fn lower_signed_byte_constant(
    little_endian: &[u8],
    result: u32,
    span: InputSourceSpan,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let &[byte] = little_endian else {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    };
    ensure_new_value(state, result)?;
    let inserted = state.signed_bytes.insert(result);
    debug_assert!(inserted, "new SSA value was already preflighted");
    Ok(TernaryOperation::MaterializeI8 {
        result,
        scalar: TernaryU8Scalar::from_bits(byte),
        span: copy_span(span),
    })
}

fn lower_halfword_constant(
    input: NarrowConstantInput<'_>,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (little_endian, result, span, kind) = input;
    let bytes: [u8; 2] = little_endian
        .try_into()
        .map_err(|_error| TernaryLoweringError::UnsupportedInstruction)?;
    if !matches!(kind, InputScalarType::I16 | InputScalarType::U16) {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    ensure_new_value(state, result)?;
    let scalar = TernaryU16Scalar::from_bits(u16::from_le_bytes(bytes));
    let converted_span = copy_span(span);
    Ok(if kind == InputScalarType::I16 {
        let inserted = state.signed_halves.insert(result);
        debug_assert!(inserted, "new SSA value was already preflighted");
        TernaryOperation::MaterializeI16 {
            result,
            scalar,
            span: converted_span,
        }
    } else {
        let inserted = state.unsigned_halves.insert(result);
        debug_assert!(inserted, "new SSA value was already preflighted");
        TernaryOperation::MaterializeU16 {
            result,
            scalar,
            span: converted_span,
        }
    })
}

fn lower_constant_integer(
    input: ConstantI32Input<'_>,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (bit_width, little_endian, result, span, type_kind) = input;
    if bit_width == 1 && type_kind == InputScalarType::Bool {
        return lower_boolean_constant(little_endian, result, span, state);
    }
    if bit_width == 16 {
        return lower_halfword_constant(
            (little_endian, result, span, type_kind),
            state,
        );
    }
    if bit_width == 8 && type_kind == InputScalarType::I8 {
        return lower_signed_byte_constant(little_endian, result, span, state);
    }
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
    lower_word_constant((little_endian, result, span, type_kind), state)
}

fn lower_word_constant(
    input: NarrowConstantInput<'_>,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (little_endian, result, span, type_kind) = input;
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
        InputScalarType::Bool
        | InputScalarType::Other
        | InputScalarType::U8
        | InputScalarType::I8
        | InputScalarType::I16
        | InputScalarType::U16
        | InputScalarType::Void => {
            Err(TernaryLoweringError::UnsupportedInstruction)
        },
    }
}

fn lower_truncate_halfword_to_byte(
    input: TruncateInput,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (result, span, kind, value) = input;
    if !matches!(kind, InputScalarType::I8 | InputScalarType::U8) {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    let signed_source = state.signed_halves.contains(&value);
    if !signed_source && !state.unsigned_halves.contains(&value) {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    ensure_new_value(state, result)?;
    let inserted = if kind == InputScalarType::I8 {
        state.signed_bytes.insert(result)
    } else {
        state.bytes.insert(result)
    };
    debug_assert!(inserted, "new byte SSA was already preflighted");
    let converted_span = copy_span(span);
    Ok(match (signed_source, kind) {
        (true, InputScalarType::I8) => TernaryOperation::TruncateI16ToI8 {
            result,
            span: converted_span,
            value,
        },
        (true, InputScalarType::U8) => TernaryOperation::TruncateI16ToU8 {
            result,
            span: converted_span,
            value,
        },
        (false, InputScalarType::I8) => TernaryOperation::TruncateU16ToI8 {
            result,
            span: converted_span,
            value,
        },
        (false, InputScalarType::U8) => TernaryOperation::TruncateU16ToU8 {
            result,
            span: converted_span,
            value,
        },
        (_, _) => return Err(TernaryLoweringError::UnsupportedInstruction),
    })
}

fn lower_truncate_word_to_halfword(
    input: TruncateInput,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (result, span, kind, value) = input;
    if !matches!(kind, InputScalarType::I16 | InputScalarType::U16) {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    let signed_source = state.signed.contains(&value);
    if !signed_source && !state.unsigned.contains(&value) {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    ensure_new_value(state, result)?;
    let inserted = if kind == InputScalarType::I16 {
        state.signed_halves.insert(result)
    } else {
        state.unsigned_halves.insert(result)
    };
    debug_assert!(inserted, "new halfword SSA was already preflighted");
    let converted_span = copy_span(span);
    Ok(match (signed_source, kind) {
        (true, InputScalarType::I16) => TernaryOperation::TruncateI32ToI16 {
            result,
            span: converted_span,
            value,
        },
        (true, InputScalarType::U16) => TernaryOperation::TruncateI32ToU16 {
            result,
            span: converted_span,
            value,
        },
        (false, InputScalarType::I16) => TernaryOperation::TruncateU32ToI16 {
            result,
            span: converted_span,
            value,
        },
        (false, InputScalarType::U16) => TernaryOperation::TruncateU32ToU16 {
            result,
            span: converted_span,
            value,
        },
        (_, _) => return Err(TernaryLoweringError::UnsupportedInstruction),
    })
}

fn lower_truncate_word_to_byte(
    input: TruncateInput,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (result, span, type_kind, value) = input;
    if matches!(type_kind, InputScalarType::I16 | InputScalarType::U16) {
        return lower_truncate_word_to_halfword(input, state);
    }
    if state.signed_halves.contains(&value)
        || state.unsigned_halves.contains(&value)
    {
        return lower_truncate_halfword_to_byte(input, state);
    }
    if !matches!(type_kind, InputScalarType::U8 | InputScalarType::I8) {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    let source_signed = state.signed.contains(&value);
    if !source_signed && !state.unsigned.contains(&value) {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    ensure_new_value(state, result)?;
    let inserted = if type_kind == InputScalarType::I8 {
        state.signed_bytes.insert(result)
    } else {
        state.bytes.insert(result)
    };
    debug_assert!(inserted, "new SSA value was already preflighted");
    let target_span = copy_span(span);
    Ok(match (source_signed, type_kind) {
        (true, InputScalarType::I8) => TernaryOperation::TruncateI32ToI8 {
            result,
            span: target_span,
            value,
        },
        (true, InputScalarType::U8) => TernaryOperation::TruncateI32ToU8 {
            result,
            span: target_span,
            value,
        },
        (false, InputScalarType::I8) => TernaryOperation::TruncateU32ToI8 {
            result,
            span: target_span,
            value,
        },
        (false, InputScalarType::U8) => TernaryOperation::TruncateU32ToU8 {
            result,
            span: target_span,
            value,
        },
        (_, _) => return Err(TernaryLoweringError::UnsupportedInstruction),
    })
}

fn lower_halfword_to_bool(
    input: TruncateInput,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (result, span, type_kind, value) = input;
    if type_kind != InputScalarType::Bool {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    let signed = state.signed_halves.contains(&value);
    let unsigned = state.unsigned_halves.contains(&value);
    if !signed && !unsigned {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    ensure_new_value(state, result)?;
    let inserted = state.bools.insert(result);
    debug_assert!(inserted, "new SSA value was already preflighted");
    let converted_span = copy_span(span);
    Ok(if signed {
        TernaryOperation::I16ToBool {
            result,
            span: converted_span,
            value,
        }
    } else {
        TernaryOperation::U16ToBool {
            result,
            span: converted_span,
            value,
        }
    })
}

fn lower_integer_to_bool(
    input: TruncateInput,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (result, span, type_kind, value) = input;
    if state.signed_halves.contains(&value)
        || state.unsigned_halves.contains(&value)
    {
        return lower_halfword_to_bool(input, state);
    }
    if type_kind != InputScalarType::Bool {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    let signed = state.signed.contains(&value);
    let unsigned = state.unsigned.contains(&value);
    let byte = state.bytes.contains(&value);
    let signed_byte = state.signed_bytes.contains(&value);
    if !signed && !unsigned && !byte && !signed_byte {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    ensure_new_value(state, result)?;
    let inserted = state.bools.insert(result);
    debug_assert!(inserted, "new SSA value was already preflighted");
    let source_span = copy_span(span);
    Ok(if signed {
        TernaryOperation::I32ToBool {
            result,
            span: source_span,
            value,
        }
    } else if unsigned {
        TernaryOperation::U32ToBool {
            result,
            span: source_span,
            value,
        }
    } else if byte {
        TernaryOperation::U8ToBool {
            result,
            span: source_span,
            value,
        }
    } else {
        TernaryOperation::I8ToBool {
            result,
            span: source_span,
            value,
        }
    })
}

fn lower_bool_to_halfword(
    input: TruncateInput,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (result, span, kind, value) = input;
    if kind != InputScalarType::I16 || !state.bools.contains(&value) {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    ensure_new_value(state, result)?;
    let inserted = state.signed_halves.insert(result);
    debug_assert!(inserted, "new SSA value was already preflighted");
    Ok(TernaryOperation::BoolToI16 {
        result,
        span: copy_span(span),
        value,
    })
}

fn lower_bool_to_signed(
    input: TruncateInput,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (result, span, type_kind, value) = input;
    if type_kind == InputScalarType::I16 {
        return lower_bool_to_halfword(input, state);
    }
    if !matches!(type_kind, InputScalarType::I32 | InputScalarType::I8)
        || !state.bools.contains(&value)
    {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    ensure_new_value(state, result)?;
    let inserted = if type_kind == InputScalarType::I8 {
        state.signed_bytes.insert(result)
    } else {
        state.signed.insert(result)
    };
    debug_assert!(inserted, "new SSA value was already preflighted");
    let converted_span = copy_span(span);
    Ok(if type_kind == InputScalarType::I8 {
        TernaryOperation::BoolToI8 {
            result,
            span: converted_span,
            value,
        }
    } else {
        TernaryOperation::BoolToI32 {
            result,
            span: converted_span,
            value,
        }
    })
}

fn lower_sign_extend_i16_to_i32(
    input: TruncateInput,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (result, span, kind, value) = input;
    if kind != InputScalarType::I32 || !state.signed_halves.contains(&value) {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    ensure_new_value(state, result)?;
    let inserted = state.signed.insert(result);
    debug_assert!(inserted, "new SSA was already preflighted");
    Ok(TernaryOperation::SignExtendI16ToI32 {
        result,
        span: copy_span(span),
        value,
    })
}

fn lower_sign_extend_i8_to_i16(
    input: TruncateInput,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (result, span, kind, value) = input;
    if kind != InputScalarType::I16 || !state.signed_bytes.contains(&value) {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    ensure_new_value(state, result)?;
    let inserted = state.signed_halves.insert(result);
    debug_assert!(inserted, "new SSA was already preflighted");
    Ok(TernaryOperation::SignExtendI8ToI16 {
        result,
        span: copy_span(span),
        value,
    })
}

fn lower_sign_extend_i8_to_i32(
    input: TruncateInput,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (result, span, type_kind, value) = input;
    if state.signed_halves.contains(&value) {
        return lower_sign_extend_i16_to_i32(input, state);
    }
    if type_kind == InputScalarType::I16 {
        return lower_sign_extend_i8_to_i16(input, state);
    }
    if type_kind != InputScalarType::I32 || !state.signed_bytes.contains(&value)
    {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    ensure_new_value(state, result)?;
    let inserted = state.signed.insert(result);
    debug_assert!(inserted, "new SSA value was already preflighted");
    Ok(TernaryOperation::SignExtendI8ToI32 {
        result,
        span: copy_span(span),
        value,
    })
}

fn lower_zero_extend_u16_to_u32(
    input: TruncateInput,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (result, span, kind, value) = input;
    if kind != InputScalarType::U32 || !state.unsigned_halves.contains(&value) {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    ensure_new_value(state, result)?;
    let inserted = state.unsigned.insert(result);
    debug_assert!(inserted, "new SSA was already preflighted");
    Ok(TernaryOperation::ZeroExtendU16ToU32 {
        result,
        span: copy_span(span),
        value,
    })
}

fn lower_zero_extend_u8_to_u16(
    input: TruncateInput,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (result, span, kind, value) = input;
    if kind != InputScalarType::U16 || !state.bytes.contains(&value) {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    ensure_new_value(state, result)?;
    let inserted = state.unsigned_halves.insert(result);
    debug_assert!(inserted, "new SSA was already preflighted");
    Ok(TernaryOperation::ZeroExtendU8ToU16 {
        result,
        span: copy_span(span),
        value,
    })
}

fn lower_zero_extend_u8_to_u32(
    input: TruncateInput,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (result, span, type_kind, value) = input;
    if state.unsigned_halves.contains(&value) {
        return lower_zero_extend_u16_to_u32(input, state);
    }
    if type_kind == InputScalarType::U16 {
        return lower_zero_extend_u8_to_u16(input, state);
    }
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

fn lower_halfword_bitcast(
    input: TruncateInput,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (result, span, type_kind, value) = input;
    let signed_source = state.signed_halves.contains(&value);
    let unsigned_source = state.unsigned_halves.contains(&value);
    if !(signed_source || unsigned_source)
        || !matches!(type_kind, InputScalarType::I16 | InputScalarType::U16)
    {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    ensure_new_value(state, result)?;
    let inserted = if type_kind == InputScalarType::I16 {
        state.signed_halves.insert(result)
    } else {
        state.unsigned_halves.insert(result)
    };
    debug_assert!(inserted, "new halfword SSA was already preflighted");
    let converted_span = copy_span(span);
    Ok(match (signed_source, type_kind) {
        (true, InputScalarType::I16) => TernaryOperation::BitcastI16ToI16 {
            result,
            span: converted_span,
            value,
        },
        (true, InputScalarType::U16) => TernaryOperation::BitcastI16ToU16 {
            result,
            span: converted_span,
            value,
        },
        (false, InputScalarType::I16) => TernaryOperation::BitcastU16ToI16 {
            result,
            span: converted_span,
            value,
        },
        (false, InputScalarType::U16) => TernaryOperation::BitcastU16ToU16 {
            result,
            span: converted_span,
            value,
        },
        (_, _) => return Err(TernaryLoweringError::UnsupportedInstruction),
    })
}

fn lower_byte_bitcast(
    input: TruncateInput,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (result, span, type_kind, value) = input;
    let signed_source = state.signed_bytes.contains(&value);
    let unsigned_source = state.bytes.contains(&value);
    if !(signed_source || unsigned_source)
        || !matches!(type_kind, InputScalarType::I8 | InputScalarType::U8)
    {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    ensure_new_value(state, result)?;
    let inserted = if type_kind == InputScalarType::I8 {
        state.signed_bytes.insert(result)
    } else {
        state.bytes.insert(result)
    };
    debug_assert!(inserted, "new SSA value was already preflighted");
    let converted_span = copy_span(span);
    Ok(match (signed_source, type_kind) {
        (true, InputScalarType::I8) => TernaryOperation::BitcastI8ToI8 {
            result,
            span: converted_span,
            value,
        },
        (true, InputScalarType::U8) => TernaryOperation::BitcastI8ToU8 {
            result,
            span: converted_span,
            value,
        },
        (false, InputScalarType::I8) => TernaryOperation::BitcastU8ToI8 {
            result,
            span: converted_span,
            value,
        },
        (false, InputScalarType::U8) => TernaryOperation::BitcastU8ToU8 {
            result,
            span: converted_span,
            value,
        },
        (_, _) => return Err(TernaryLoweringError::UnsupportedInstruction),
    })
}

fn lower_integer_bitcast(
    input: TruncateInput,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (_, _, _, value) = input;
    if state.signed_halves.contains(&value)
        || state.unsigned_halves.contains(&value)
    {
        return lower_halfword_bitcast(input, state);
    }
    if state.signed_bytes.contains(&value) || state.bytes.contains(&value) {
        return lower_byte_bitcast(input, state);
    }
    lower_word_bitcast(input, state)
}

fn lower_word_bitcast(
    input: TruncateInput,
    state: &mut LoweringState,
) -> Result<TernaryOperation, TernaryLoweringError> {
    let (result, span, type_kind, value) = input;
    let source_kind = if state.signed.contains(&value) {
        InputScalarType::I32
    } else if state.unsigned.contains(&value) {
        InputScalarType::U32
    } else {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    };
    if !matches!(type_kind, InputScalarType::I32 | InputScalarType::U32) {
        return Err(TernaryLoweringError::UnsupportedInstruction);
    }
    ensure_new_value(state, result)?;
    let inserted = match type_kind {
        InputScalarType::I32 => state.signed.insert(result),
        InputScalarType::U32 => state.unsigned.insert(result),
        InputScalarType::Bool
        | InputScalarType::Other
        | InputScalarType::U8
        | InputScalarType::I8
        | InputScalarType::I16
        | InputScalarType::U16
        | InputScalarType::Void => false,
    };
    debug_assert!(inserted, "new SSA value was already preflighted");
    let target_span = copy_span(span);
    Ok(match (source_kind, type_kind) {
        (InputScalarType::I32, InputScalarType::I32) => {
            TernaryOperation::BitcastI32ToI32 {
                result,
                span: target_span,
                value,
            }
        },
        (InputScalarType::I32, InputScalarType::U32) => {
            TernaryOperation::BitcastI32ToU32 {
                result,
                span: target_span,
                value,
            }
        },
        (InputScalarType::U32, InputScalarType::I32) => {
            TernaryOperation::BitcastU32ToI32 {
                result,
                span: target_span,
                value,
            }
        },
        (InputScalarType::U32, InputScalarType::U32) => {
            TernaryOperation::BitcastU32ToU32 {
                result,
                span: target_span,
                value,
            }
        },
        (_, _) => return Err(TernaryLoweringError::UnsupportedInstruction),
    })
}

fn ensure_new_value(
    state: &LoweringState,
    value: u32,
) -> Result<(), TernaryLoweringError> {
    if state.bools.contains(&value)
        || state.bytes.contains(&value)
        || state.signed_bytes.contains(&value)
        || state.signed_halves.contains(&value)
        || state.unsigned_halves.contains(&value)
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
