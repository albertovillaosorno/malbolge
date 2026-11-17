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

use std::collections::{BTreeMap, BTreeSet};

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
type SourceCoordinatesByByte = BTreeMap<u32, (u32, u32)>;
// Local proof records, not runtime guest state.
type ProvenWord = (u32, InputScalarType, u32);
type ProvenWordTable = BTreeMap<u32, (InputScalarType, u32)>;
type LiteralCastIdentity = (u32, u32, InputScalarType, LiteralCastKind);

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

// This proof-local shape is not an executable cast or target operation.
#[derive(Clone, Copy)]
enum LiteralCastKind {
    Bitcast,
    SignExtend,
    Truncate,
    ZeroExtend,
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

const fn valid_projection_span(span: InputSourceSpan) -> bool {
    let begin = span.begin;
    let end = span.end;
    if begin.line == 0
        || begin.column == 0
        || end.line == 0
        || end.column == 0
        || begin.byte > end.byte
    {
        return false;
    }
    if begin.byte == end.byte {
        return begin.line == end.line && begin.column == end.column;
    }
    begin.line < end.line
        || (begin.line == end.line && begin.column <= end.column)
}

const fn projection_position_precedes(
    before: super::input::InputSourcePosition,
    after: super::input::InputSourcePosition,
) -> bool {
    if before.byte > after.byte {
        return false;
    }
    // One byte offset has exactly one normalized source coordinate.
    if before.byte == after.byte {
        return before.line == after.line && before.column == after.column;
    }
    before.line < after.line
        || (before.line == after.line && before.column <= after.column)
}

const fn projection_span_contains(
    parent: InputSourceSpan,
    child: InputSourceSpan,
) -> bool {
    projection_position_precedes(parent.begin, child.begin)
        && projection_position_precedes(child.end, parent.end)
}

pub(super) const fn projected_instruction_span(
    instruction: &InputInstruction,
) -> Option<InputSourceSpan> {
    match instruction {
        InputInstruction::BinaryAdd { span, .. }
        | InputInstruction::BinaryAnd { span, .. }
        | InputInstruction::BinaryDivideSigned { span, .. }
        | InputInstruction::BinaryDivideUnsigned { span, .. }
        | InputInstruction::BinaryMultiply { span, .. }
        | InputInstruction::BinaryOr { span, .. }
        | InputInstruction::BinaryRemainderSigned { span, .. }
        | InputInstruction::BinaryRemainderUnsigned { span, .. }
        | InputInstruction::BinaryShiftLeft { span, .. }
        | InputInstruction::BinaryShiftRightArithmetic { span, .. }
        | InputInstruction::BinaryShiftRightLogical { span, .. }
        | InputInstruction::BinarySubtract { span, .. }
        | InputInstruction::BinaryXor { span, .. }
        | InputInstruction::BoolToSigned { span, .. }
        | InputInstruction::ByteInput { span, .. }
        | InputInstruction::Getchar { span, .. }
        | InputInstruction::ByteOutput { span, .. }
        | InputInstruction::CompareEqual { span, .. }
        | InputInstruction::CompareNotEqual { span, .. }
        | InputInstruction::CompareOrdered { span, .. }
        | InputInstruction::ConstantInteger { span, .. }
        | InputInstruction::IntegerBitcast { span, .. }
        | InputInstruction::IntegerToBool { span, .. }
        | InputInstruction::SignExtendI8ToI32 { span, .. }
        | InputInstruction::TruncateInteger { span, .. }
        | InputInstruction::ZeroExtendInteger { span, .. } => Some(*span),
        InputInstruction::Unsupported => None,
    }
}

fn register_projection_span(
    observed: &mut SourceCoordinatesByByte,
    span: InputSourceSpan,
) -> bool {
    for point in [span.begin, span.end] {
        let coordinate = (point.line, point.column);
        if let Some(previous) = observed.insert(point.byte, coordinate)
            && previous != coordinate
        {
            return false;
        }
    }
    true
}

pub(super) fn validate_projection_spans(
    function: &InputFunction,
) -> Result<(), TernaryLoweringError> {
    let mut observed = BTreeMap::new();
    validate_projection_spans_into(function, &mut observed)
}

fn validate_projection_spans_into(
    function: &InputFunction,
    observed: &mut SourceCoordinatesByByte,
) -> Result<(), TernaryLoweringError> {
    if !valid_projection_span(function.span)
        || !register_projection_span(observed, function.span)
    {
        return Err(TernaryLoweringError::InvalidProjection);
    }
    if function.blocks.is_empty() {
        return Err(TernaryLoweringError::UnsupportedFunction);
    }
    for block in &function.blocks {
        let term_span = match block.terminator {
            InputTerminator::Return { span, .. }
            | InputTerminator::Jump { span, .. }
            | InputTerminator::Branch { span, .. } => Some(span),
            InputTerminator::Unsupported => None,
        };
        if let Some(span) = term_span
            && (!valid_projection_span(span)
                || !projection_span_contains(function.span, span)
                || !register_projection_span(observed, span))
        {
            return Err(TernaryLoweringError::InvalidProjection);
        }
        for instruction in &block.instructions {
            if let Some(span) = projected_instruction_span(instruction)
                && (!valid_projection_span(span)
                    || !projection_span_contains(function.span, span)
                    || !register_projection_span(observed, span))
            {
                return Err(TernaryLoweringError::InvalidProjection);
            }
        }
    }
    Ok(())
}

// Validate the whole projected CFG before selecting a path. Even an untaken
// arm must be structurally valid: no orphan, malformed edge, phi merge, or
// cycle may hide behind a compile-time Boolean. Runtime-dependent choices
// have no lowering in the current target operation model.
fn validate_static_cfg(
    function: &InputFunction,
) -> Result<(), TernaryLoweringError> {
    let count = function.blocks.len();
    if function.parameter_count != 0 || count == 0 {
        return Err(TernaryLoweringError::UnsupportedFunction);
    }
    let mut incoming = vec![0usize; count];
    let mut reachable = BTreeSet::new();
    let mut pending = vec![function.entry];
    while let Some(id) = pending.pop() {
        let index = usize::try_from(id)
            .map_err(|_error| TernaryLoweringError::UnsupportedFunction)?;
        let block = function
            .blocks
            .get(index)
            .ok_or(TernaryLoweringError::UnsupportedFunction)?;
        if block.id != id || block.phi_count != 0 {
            return Err(TernaryLoweringError::UnsupportedFunction);
        }
        if !reachable.insert(id) {
            continue;
        }
        let targets = match block.terminator {
            InputTerminator::Jump { target, .. } => vec![target],
            InputTerminator::Branch {
                false_target,
                true_target,
                ..
            } => {
                if false_target == true_target {
                    vec![true_target]
                } else {
                    vec![false_target, true_target]
                }
            },
            InputTerminator::Return { .. } => Vec::new(),
            InputTerminator::Unsupported => {
                return Err(TernaryLoweringError::UnsupportedTerminator);
            },
        };
        for target in targets {
            let target_index = usize::try_from(target)
                .map_err(|_error| TernaryLoweringError::UnsupportedFunction)?;
            let degree = incoming
                .get_mut(target_index)
                .ok_or(TernaryLoweringError::UnsupportedFunction)?;
            *degree = degree
                .checked_add(1)
                .ok_or(TernaryLoweringError::UnsupportedFunction)?;
            pending.push(target);
        }
    }
    if reachable.len() != count {
        return Err(TernaryLoweringError::UnsupportedFunction);
    }
    let mut zero_degree = incoming
        .iter()
        .enumerate()
        .filter_map(|(index, degree)| (*degree == 0).then_some(index))
        .collect::<Vec<_>>();
    let mut consumed = 0usize;
    while let Some(index) = zero_degree.pop() {
        consumed += 1;
        let targets = match function.blocks[index].terminator {
            InputTerminator::Jump { target, .. } => vec![target],
            InputTerminator::Branch {
                false_target,
                true_target,
                ..
            } => {
                if false_target == true_target {
                    vec![true_target]
                } else {
                    vec![false_target, true_target]
                }
            },
            _ => Vec::new(),
        };
        for target in targets {
            let index = usize::try_from(target)
                .map_err(|_error| TernaryLoweringError::UnsupportedFunction)?;
            let degree = &mut incoming[index];
            *degree -= 1;
            if *degree == 0 {
                zero_degree.push(index);
            }
        }
    }
    if consumed != count {
        return Err(TernaryLoweringError::UnsupportedFunction);
    }
    Ok(())
}

// A branch with coincident successors needs no Boolean evaluation to choose
// control flow, but its operand must still be a defined Boolean SSA value.
// Later lowering validates its defining instruction and emits any guest work.
const fn projected_boolean_definition(
    instruction: &InputInstruction,
) -> Option<u32> {
    match instruction {
        InputInstruction::ConstantInteger {
            bit_width: 1,
            result,
            type_kind: InputScalarType::Bool,
            ..
        }
        | InputInstruction::CompareEqual {
            result,
            type_kind: InputScalarType::Bool,
            ..
        }
        | InputInstruction::CompareNotEqual {
            result,
            type_kind: InputScalarType::Bool,
            ..
        }
        | InputInstruction::CompareOrdered {
            result,
            type_kind: InputScalarType::Bool,
            ..
        }
        | InputInstruction::IntegerToBool {
            result,
            type_kind: InputScalarType::Bool,
            ..
        } => Some(*result),
        _ => None,
    }
}

// Only typed exact literals can settle comparison-driven CFG choices. Keep
// their complete bit patterns; input-derived SSA and arithmetic are never
// evaluated by this static selector. The ordinary lowerer still validates and
// emits every selected comparison as a guest target operation.
fn proven_literal_integer(
    instruction: &InputInstruction,
) -> Option<(u32, InputScalarType, u32)> {
    let InputInstruction::ConstantInteger {
        bit_width,
        little_endian,
        result,
        type_kind,
        ..
    } = instruction
    else {
        return None;
    };
    let bits = match (*bit_width, *type_kind, little_endian.as_slice()) {
        (8, InputScalarType::I8 | InputScalarType::U8, &[byte]) => {
            u32::from(byte)
        },
        (16, InputScalarType::I16 | InputScalarType::U16, &[lo, hi]) => {
            u32::from(u16::from_le_bytes([lo, hi]))
        },
        (
            32,
            InputScalarType::I32 | InputScalarType::U32,
            &[first, second, third, fourth],
        ) => u32::from_le_bytes([first, second, third, fourth]),
        _ => return None,
    };
    Some((*result, *type_kind, bits))
}

// Integer comparison is reflexive for one *identical SSA word*, even if
// that word comes from a live guest input. This is not a proof that two
// separately read bytes coincide, nor a reason to erase the guest comparison.
// The ordinary lowerer subsequently validates its operand's definition and
// exact signed/unsigned type before publishing the selected target stream.
const fn proven_reflexive_comparison(
    instruction: &InputInstruction,
) -> Option<(u32, bool)> {
    let (left, right, result, chosen) = match instruction {
        InputInstruction::CompareEqual {
            left,
            right,
            result,
            type_kind: InputScalarType::Bool,
            ..
        } => (left, right, result, true),
        InputInstruction::CompareNotEqual {
            left,
            right,
            result,
            type_kind: InputScalarType::Bool,
            ..
        } => (left, right, result, false),
        InputInstruction::CompareOrdered {
            left,
            right,
            result,
            type_kind: InputScalarType::Bool,
            operation,
            ..
        } => (
            left,
            right,
            result,
            matches!(
                operation,
                InputOrderedComparison::SignedEqual
                    | InputOrderedComparison::UnsignedEqual
            ),
        ),
        _ => return None,
    };
    if *left == *right {
        Some((*result, chosen))
    } else {
        None
    }
}

fn proven_literal_comparison(
    instruction: &InputInstruction,
    words: &BTreeMap<u32, (InputScalarType, u32)>,
) -> Option<(u32, bool)> {
    let (left, right, result, ordered) = match instruction {
        InputInstruction::CompareEqual {
            left,
            result,
            right,
            type_kind: InputScalarType::Bool,
            ..
        } => (*left, *right, *result, None),
        InputInstruction::CompareNotEqual {
            left,
            result,
            right,
            type_kind: InputScalarType::Bool,
            ..
        } => (*left, *right, *result, Some(None)),
        InputInstruction::CompareOrdered {
            left,
            operation,
            result,
            right,
            type_kind: InputScalarType::Bool,
            ..
        } => (*left, *right, *result, Some(Some(*operation))),
        _ => return None,
    };
    let &(left_kind, left_bits) = words.get(&left)?;
    let &(right_kind, right_bits) = words.get(&right)?;
    if left_kind != right_kind
        || !matches!(left_kind, InputScalarType::I32 | InputScalarType::U32)
    {
        return None;
    }
    let chosen = match ordered {
        None => left_bits == right_bits,
        Some(None) => left_bits != right_bits,
        Some(Some(InputOrderedComparison::Signed))
            if left_kind == InputScalarType::I32 =>
        {
            (left_bits as i32) < (right_bits as i32)
        },
        Some(Some(InputOrderedComparison::SignedEqual))
            if left_kind == InputScalarType::I32 =>
        {
            (left_bits as i32) <= (right_bits as i32)
        },
        Some(Some(InputOrderedComparison::Unsigned))
            if left_kind == InputScalarType::U32 =>
        {
            left_bits < right_bits
        },
        Some(Some(InputOrderedComparison::UnsignedEqual))
            if left_kind == InputScalarType::U32 =>
        {
            left_bits <= right_bits
        },
        _ => return None,
    };
    Some((result, chosen))
}

// Preserve exact 32-bit literal arithmetic chains for static CFG selection.
// Signed overflow and zero divisors cannot prove a successor; unsigned
// addition/multiplication wrap, while shift counts must be below 32.
// This is control selection only: the selected path still emits each target
// ALU instruction, and no guest-derived operand is inspected on the host.
fn proven_literal_word_alu(
    instruction: &InputInstruction,
    words: &BTreeMap<u32, (InputScalarType, u32)>,
) -> Option<(u32, InputScalarType, u32)> {
    let (left, right, result, kind) = match instruction {
        InputInstruction::BinaryAnd {
            left,
            right,
            result,
            type_kind,
            ..
        }
        | InputInstruction::BinaryOr {
            left,
            right,
            result,
            type_kind,
            ..
        }
        | InputInstruction::BinaryXor {
            left,
            right,
            result,
            type_kind,
            ..
        }
        | InputInstruction::BinaryAdd {
            left,
            right,
            result,
            type_kind,
            ..
        }
        | InputInstruction::BinarySubtract {
            left,
            right,
            result,
            type_kind,
            ..
        }
        | InputInstruction::BinaryMultiply {
            left,
            right,
            result,
            type_kind,
            ..
        }
        | InputInstruction::BinaryDivideSigned {
            left,
            right,
            result,
            type_kind,
            ..
        }
        | InputInstruction::BinaryRemainderSigned {
            left,
            right,
            result,
            type_kind,
            ..
        }
        | InputInstruction::BinaryDivideUnsigned {
            left,
            right,
            result,
            type_kind,
            ..
        }
        | InputInstruction::BinaryRemainderUnsigned {
            left,
            right,
            result,
            type_kind,
            ..
        }
        | InputInstruction::BinaryShiftLeft {
            left,
            right,
            result,
            type_kind,
            ..
        }
        | InputInstruction::BinaryShiftRightLogical {
            left,
            right,
            result,
            type_kind,
            ..
        }
        | InputInstruction::BinaryShiftRightArithmetic {
            left,
            right,
            result,
            type_kind,
            ..
        } => (*left, *right, *result, *type_kind),
        _ => return None,
    };
    if !matches!(kind, InputScalarType::I32 | InputScalarType::U32) {
        return None;
    }
    let &(left_kind, left_bits) = words.get(&left)?;
    let &(right_kind, right_bits) = words.get(&right)?;
    if left_kind != kind || right_kind != kind {
        return None;
    }
    let signed_left = i32::from_le_bytes(left_bits.to_le_bytes());
    let signed_right = i32::from_le_bytes(right_bits.to_le_bytes());
    let bits = match (kind, instruction) {
        (_, InputInstruction::BinaryAnd { .. }) => left_bits & right_bits,
        (_, InputInstruction::BinaryOr { .. }) => left_bits | right_bits,
        (_, InputInstruction::BinaryXor { .. }) => left_bits ^ right_bits,
        (InputScalarType::U32, InputInstruction::BinaryAdd { .. }) => {
            left_bits.wrapping_add(right_bits)
        },
        (InputScalarType::U32, InputInstruction::BinarySubtract { .. }) => {
            left_bits.wrapping_sub(right_bits)
        },
        (InputScalarType::U32, InputInstruction::BinaryMultiply { .. }) => {
            left_bits.wrapping_mul(right_bits)
        },
        (InputScalarType::I32, InputInstruction::BinaryAdd { .. }) => {
            u32::from_le_bytes(
                signed_left.checked_add(signed_right)?.to_le_bytes(),
            )
        },
        (InputScalarType::I32, InputInstruction::BinarySubtract { .. }) => {
            u32::from_le_bytes(
                signed_left.checked_sub(signed_right)?.to_le_bytes(),
            )
        },
        (InputScalarType::I32, InputInstruction::BinaryMultiply { .. }) => {
            u32::from_le_bytes(
                signed_left.checked_mul(signed_right)?.to_le_bytes(),
            )
        },
        (InputScalarType::I32, InputInstruction::BinaryDivideSigned { .. }) => {
            u32::from_le_bytes(
                signed_left.checked_div(signed_right)?.to_le_bytes(),
            )
        },
        (
            InputScalarType::I32,
            InputInstruction::BinaryRemainderSigned { .. },
        ) => u32::from_le_bytes(
            signed_left.checked_rem(signed_right)?.to_le_bytes(),
        ),
        (
            InputScalarType::U32,
            InputInstruction::BinaryDivideUnsigned { .. },
        ) => left_bits.checked_div(right_bits)?,
        (
            InputScalarType::U32,
            InputInstruction::BinaryRemainderUnsigned { .. },
        ) => left_bits.checked_rem(right_bits)?,
        (InputScalarType::I32, InputInstruction::BinaryShiftLeft { .. })
            if signed_left >= 0i32 && right_bits < 32u32 =>
        {
            // Shifting a nonnegative signed C integer is defined only when
            // its mathematical result remains representable as signed i32.
            let shifted = i64::from(signed_left) << right_bits;
            u32::from_le_bytes(i32::try_from(shifted).ok()?.to_le_bytes())
        },
        (
            InputScalarType::I32,
            InputInstruction::BinaryShiftRightArithmetic { .. },
        ) if signed_left >= 0i32 => {
            // Negative signed right shifts are implementation-defined in C.
            u32::from_le_bytes(
                signed_left.checked_shr(right_bits)?.to_le_bytes(),
            )
        },
        (InputScalarType::U32, InputInstruction::BinaryShiftLeft { .. }) => {
            left_bits.checked_shl(right_bits)?
        },
        (
            InputScalarType::U32,
            InputInstruction::BinaryShiftRightLogical { .. },
        ) => left_bits.checked_shr(right_bits)?,
        _ => return None,
    };
    Some((result, kind, bits))
}

const fn literal_integer_width(kind: InputScalarType) -> Option<u32> {
    match kind {
        InputScalarType::I8 | InputScalarType::U8 => Some(8u32),
        InputScalarType::I16 | InputScalarType::U16 => Some(16u32),
        InputScalarType::I32 | InputScalarType::U32 => Some(32u32),
        InputScalarType::Bool
        | InputScalarType::Other
        | InputScalarType::Void => None,
    }
}

const fn literal_cast_identity(
    instruction: &InputInstruction,
) -> Option<LiteralCastIdentity> {
    let (value, result, kind, cast) =
        if let InputInstruction::IntegerBitcast {
            value,
            result,
            type_kind,
            ..
        } = instruction
        {
            (value, result, type_kind, LiteralCastKind::Bitcast)
        } else if let InputInstruction::SignExtendI8ToI32 {
            value,
            result,
            type_kind,
            ..
        } = instruction
        {
            (value, result, type_kind, LiteralCastKind::SignExtend)
        } else if let InputInstruction::ZeroExtendInteger {
            value,
            result,
            type_kind,
            ..
        } = instruction
        {
            (value, result, type_kind, LiteralCastKind::ZeroExtend)
        } else if let InputInstruction::TruncateInteger {
            value,
            result,
            type_kind,
            ..
        } = instruction
        {
            (value, result, type_kind, LiteralCastKind::Truncate)
        } else {
            return None;
        };
    Some((*value, *result, *kind, cast))
}

// Only exact, typed constant integral casts may propagate a known bit
// pattern into static CFG selection. Preserve C integer widths and bitcasts;
// narrowing drops high bits, while signed extension copies the sign bit.
// The target operation remains in the guest stream and invalid casts are
// refused by the normal lowerer rather than silently proven here.
fn proven_literal_integer_cast(
    instruction: &InputInstruction,
    words: &ProvenWordTable,
) -> Option<ProvenWord> {
    let (value, result, kind, cast) = literal_cast_identity(instruction)?;
    let &(source_kind, source_bits) = words.get(&value)?;
    let source_width = literal_integer_width(source_kind)?;
    let target_width = literal_integer_width(kind)?;
    let valid = match cast {
        LiteralCastKind::Bitcast => source_width == target_width,
        LiteralCastKind::SignExtend => matches!(
            (source_kind, kind),
            (
                InputScalarType::I8,
                InputScalarType::I16 | InputScalarType::I32
            ) | (InputScalarType::I16, InputScalarType::I32)
        ),
        LiteralCastKind::ZeroExtend => matches!(
            (source_kind, kind),
            (
                InputScalarType::U8,
                InputScalarType::U16 | InputScalarType::U32
            ) | (InputScalarType::U16, InputScalarType::U32)
        ),
        LiteralCastKind::Truncate => source_width > target_width,
    };
    if !valid {
        return None;
    }
    let result_bits = if matches!(cast, LiteralCastKind::SignExtend) {
        let [lo, hi, _, _] = source_bits.to_le_bytes();
        let signed = if source_width == 8u32 {
            i32::from(i8::from_le_bytes([lo]))
        } else {
            i32::from(i16::from_le_bytes([lo, hi]))
        };
        u32::from_le_bytes(signed.to_le_bytes())
    } else {
        match target_width {
            8 => source_bits & 0xffu32,
            16 => source_bits & 0xffffu32,
            32 => source_bits,
            _ => return None,
        }
    };
    Some((result, kind, result_bits))
}

// A cast from an exact, previously defined integer literal has a known
// truth value. This only selects control flow: the symbolic cast is still
// lowered into a target operation, and guest-derived words remain unknown.
fn proven_literal_word_truth(
    instruction: &InputInstruction,
    words: &BTreeMap<u32, (InputScalarType, u32)>,
) -> Option<(u32, bool)> {
    let InputInstruction::IntegerToBool {
        result,
        type_kind: InputScalarType::Bool,
        value,
        ..
    } = instruction
    else {
        return None;
    };
    let &(kind, bits) = words.get(value)?;
    matches!(
        kind,
        InputScalarType::I8
            | InputScalarType::U8
            | InputScalarType::I16
            | InputScalarType::U16
            | InputScalarType::I32
            | InputScalarType::U32
    )
    .then_some((*result, bits != 0))
}

// A Boolean known from exact literals or their proven integer comparisons
// converts to exactly zero or one at any admitted signed width. Keep the
// conversion symbolic in the emitted target operations; no guest Boolean can
// enter this proof table without an earlier source-constant derivation.
fn proven_literal_boolean_to_signed(
    instruction: &InputInstruction,
    constants: &BTreeMap<u32, bool>,
) -> Option<ProvenWord> {
    let InputInstruction::BoolToSigned {
        result, type_kind, value, ..
    } = instruction
    else {
        return None;
    };
    if !matches!(
        type_kind,
        InputScalarType::I8 | InputScalarType::I16 | InputScalarType::I32
    ) {
        return None;
    }
    let known = *constants.get(value)?;
    Some((*result, *type_kind, u32::from(known)))
}

// Follow all instruction-free control paths until their first observable
// instruction or return. A nested branch is safe to erase only if its Boolean
// has already been defined on the common prefix and every path reaches the
// exact same continuation. Reject even pure-looking skipped instructions:
// a computation may trap, define SSA, or carry guest effects. The whole CFG
// has already passed acyclicity, reachability, and phi checks.
fn empty_control_frontier(
    function: &InputFunction,
    start: u32,
    available_bools: &BTreeSet<u32>,
) -> Option<u32> {
    let mut pending = vec![start];
    let mut visited = BTreeSet::new();
    let mut continuation = None;
    while let Some(current) = pending.pop() {
        if !visited.insert(current) {
            continue;
        }
        let block = function.blocks.get(usize::try_from(current).ok()?)?;
        if !block.instructions.is_empty()
            || matches!(block.terminator, InputTerminator::Return { .. })
        {
            if continuation.is_some_and(|existing| existing != current) {
                return None;
            }
            continuation = Some(current);
            continue;
        }
        match block.terminator {
            InputTerminator::Jump { target, .. } => pending.push(target),
            InputTerminator::Branch {
                condition,
                false_target,
                true_target,
                ..
            } if available_bools.contains(&condition) => {
                pending.push(false_target);
                pending.push(true_target);
            },
            _ => return None,
        }
    }
    continuation
}

// Runtime-dependent paths are equivalent only when *all* their leaves share
// the same first effectful or returning block. The input-dependent control
// choices themselves then need no guest branch instruction.
fn empty_diamond_join(
    function: &InputFunction,
    false_target: u32,
    true_target: u32,
    available_bools: &BTreeSet<u32>,
) -> Option<u32> {
    if false_target == true_target {
        return None;
    }
    let false_join =
        empty_control_frontier(function, false_target, available_bools)?;
    let true_join =
        empty_control_frontier(function, true_target, available_bools)?;
    (false_join == true_join).then_some(false_join)
}

// Literal Boolean SSA can select a successor; a nonliteral Boolean may only
// skip proven empty equivalent arms. Never evaluate guest values on the host.
pub(super) fn selected_function_blocks(
    function: &InputFunction,
) -> Result<Vec<&super::input::InputBlock>, TernaryLoweringError> {
    validate_static_cfg(function)?;
    let mut blocks = Vec::new();
    let mut constants = BTreeMap::new();
    let mut literal_words = BTreeMap::new();
    let mut defined_bools = BTreeSet::new();
    let mut next = function.entry;
    loop {
        let index = usize::try_from(next)
            .map_err(|_error| TernaryLoweringError::UnsupportedFunction)?;
        let block = &function.blocks[index];
        blocks.push(block);
        for instruction in &block.instructions {
            if let Some(result) = projected_boolean_definition(instruction) {
                _ = defined_bools.insert(result);
            }
            if let InputInstruction::ConstantInteger {
                bit_width: 1,
                little_endian,
                result,
                type_kind: InputScalarType::Bool,
                ..
            } = instruction
                && let &[value @ 0..=1] = little_endian.as_slice()
            {
                _ = constants.insert(*result, value == 1);
            }
            if let Some((result, kind, bits)) =
                proven_literal_integer(instruction)
            {
                _ = literal_words.insert(result, (kind, bits));
            }
            if let Some((result, kind, bits)) =
                proven_literal_word_alu(instruction, &literal_words)
            {
                _ = literal_words.insert(result, (kind, bits));
            }
            if let Some((result, kind, bits)) =
                proven_literal_integer_cast(instruction, &literal_words)
            {
                _ = literal_words.insert(result, (kind, bits));
            }
            if let Some((result, value)) =
                proven_reflexive_comparison(instruction).or_else(|| {
                    proven_literal_comparison(instruction, &literal_words)
                })
            {
                _ = constants.insert(result, value);
            }
            if let Some((result, value)) =
                proven_literal_word_truth(instruction, &literal_words)
            {
                _ = constants.insert(result, value);
            }
            if let Some((result, kind, bits)) =
                proven_literal_boolean_to_signed(instruction, &constants)
            {
                _ = literal_words.insert(result, (kind, bits));
            }
        }
        match block.terminator {
            InputTerminator::Jump { target, .. } => next = target,
            InputTerminator::Branch {
                condition,
                false_target,
                true_target,
                ..
            } => {
                if !defined_bools.contains(&condition) {
                    return Err(TernaryLoweringError::UnsupportedTerminator);
                }
                next = match (
                    true_target == false_target,
                    constants.get(&condition),
                ) {
                    (true, _) | (false, Some(true)) => true_target,
                    (false, Some(false)) => false_target,
                    (false, None) => empty_diamond_join(
                        function,
                        false_target,
                        true_target,
                        &defined_bools,
                    )
                    .ok_or(TernaryLoweringError::UnsupportedTerminator)?,
                };
            },
            InputTerminator::Return { .. } => return Ok(blocks),
            InputTerminator::Unsupported => {
                return Err(TernaryLoweringError::UnsupportedTerminator);
            },
        }
    }
}

fn lower_function(
    function: &InputFunction,
) -> Result<TernaryFunction, TernaryLoweringError> {
    validate_projection_spans(function)?;
    let selected = selected_function_blocks(function)?;
    let mut state = LoweringState::default();
    let mut operations = Vec::new();
    for block in &selected {
        for instruction in &block.instructions {
            operations.push(lower_instruction(instruction, &mut state)?);
        }
    }
    let Some(InputTerminator::Return { span, value }) =
        selected.last().map(|block| block.terminator)
    else {
        return Err(TernaryLoweringError::UnsupportedTerminator);
    };
    let return_operation =
        if function.return_kind == InputScalarType::Void && value.is_none() {
            TernaryOperation::ReturnVoid { span: copy_span(span) }
        } else {
            lower_return_operation(
                function.return_kind,
                &state,
                value.ok_or(TernaryLoweringError::UnsupportedTerminator)?,
                copy_span(span),
            )?
        };
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
        | InputInstruction::Getchar { .. }
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
        InputInstruction::Getchar { result, span, type_kind } => {
            if *type_kind != InputScalarType::I32 {
                return Err(TernaryLoweringError::UnsupportedInstruction);
            }
            ensure_new_value(state, *result)?;
            let inserted = state.signed.insert(*result);
            debug_assert!(
                inserted,
                "new signed getchar SSA already preflighted"
            );
            Ok(TernaryOperation::GetcharI32 {
                result: *result,
                span: copy_span(*span),
            })
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
    // The canonical MCTR validator requires dense, per-function SSA results.
    // Reject forged projections here, before returning an unencodable program.
    let next = [
        state.bools.len(),
        state.bytes.len(),
        state.signed_bytes.len(),
        state.signed_halves.len(),
        state.unsigned_halves.len(),
        state.signed.len(),
        state.unsigned.len(),
    ]
    .into_iter()
    .try_fold(0usize, usize::checked_add)
    .and_then(|count| u32::try_from(count).ok())
    .ok_or(TernaryLoweringError::InvalidProjection)?;
    if value != next {
        return Err(TernaryLoweringError::InvalidProjection);
    }
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

fn valid_projection_source_id(source_id: &str) -> bool {
    !source_id.is_empty()
        && !source_id.starts_with('/')
        && !source_id.contains('\\')
        && !source_id.contains(':')
        && !source_id.contains('\0')
        && !source_id
            .split('/')
            .any(|part| part.is_empty() || part == "." || part == "..")
}

fn validate_projection_function_identities(
    input: &TypedIrInput,
) -> Result<(), TernaryLoweringError> {
    let mut names = BTreeSet::new();
    for (index, function) in input.functions.iter().enumerate() {
        let expected = u32::try_from(index)
            .map_err(|_error| TernaryLoweringError::InvalidProjection)?;
        if function.id != expected
            || function.name.is_empty()
            || function.name.contains('\0')
            || !names.insert(function.name.as_str())
        {
            return Err(TernaryLoweringError::InvalidProjection);
        }
    }
    Ok(())
}

fn validate_projection(
    input: &TypedIrInput,
) -> Result<(), TernaryLoweringError> {
    if input.abi_id != ABI_ID
        || input.input_format_version != TYPED_IR_VERSION
        || !valid_projection_source_id(&input.source_id)
        || input.target_profile != TARGET_PROFILE
    {
        return Err(TernaryLoweringError::InvalidProjection);
    }
    validate_projection_function_identities(input)
}

fn validate_projection_source_positions(
    input: &TypedIrInput,
) -> Result<(), TernaryLoweringError> {
    let mut observed = BTreeMap::new();
    for function in &input.functions {
        validate_projection_spans_into(function, &mut observed)?;
    }
    let mut previous: Option<(u32, u32)> = None;
    for coordinates in observed.values() {
        if previous.is_some_and(|point| {
            point.0 > coordinates.0
                || (point.0 == coordinates.0 && point.1 > coordinates.1)
        }) {
            return Err(TernaryLoweringError::InvalidProjection);
        }
        previous = Some(*coordinates);
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
    validate_projection_source_positions(input)?;
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
