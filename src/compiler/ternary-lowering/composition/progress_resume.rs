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
//   - Product selection between fresh ternary lowering and progress resume.
// - Must-Not:
//   - Parse sidecar JSON, duplicate checkpoint validation, or choose tool
//     paths.
// - Allows:
//   - Inputs: explicit interpreter, inspector, and progress-sidecar paths.
//   - Outputs: one admitted ternary program or stable bridge failure.
//   - Side effects: one bounded child process selected by compiler composition.
// - Split-When:
//   - Another durable compiler-state codec needs an independent adapter.
// - Merge-When:
//   - Ternary composition directly owns the progress-sidecar wire contract.
// - Summary:
//   - Selects fresh projection lowering or verified ternary progress state.
// - Description:
//   - Delegates durable-state validation and re-admits extracted ternary bytes.
// - Usage:
//   - Compiler composition supplies the explicit progress-inspector command.
// - Defaults:
//   - Launch failure, diagnostics, or invalid ternary state fail closed.
//

//! Verified progress-sidecar composition for pre-layout ternary resume.

#[path = "ternary_inspector.rs"]
mod inspector_transport;

use std::path::Path;

use inspector_transport::{TransportError, extract_ternary_checkpoint};

use super::input::{
    InputFunction, InputInstruction, InputOrderedComparison, InputScalarType, InputSourceSpan,
    InputTerminator, TypedIrInput,
};
use super::lower::{projected_instruction_span, validate_projection_spans};
use super::model::{TernaryFunction, TernaryOperation, TernaryProgram, TernarySourceSpan};
use super::program_codec::{TERNARY_PROGRAM_CODEC_ID, operation_span};
use super::stage::{TernaryStageError, TernaryStageInput, enter_ternary_stage};

type BinaryValues = (u32, u32, u32);

/// Product compiler selection for entering the ternary-lowering stage.
#[derive(Clone, Copy, Debug)]
pub enum TernaryCompilerStageInput<'input> {
    /// Lower fresh admitted typed-IR projection.
    Fresh(&'input TypedIrInput),
    /// Restore verified ternary state from one durable progress sidecar.
    ///
    /// This legacy route does not bind the restored source to a caller's
    /// expected compilation. Prefer `ProgressForSource` when available.
    Progress {
        /// Explicit interpreter used to run the trusted inspector.
        interpreter: &'input Path,
        /// Explicit trusted progress-sidecar inspector.
        inspector: &'input Path,
        /// Durable progress sidecar selecting the committed checkpoint.
        progress: &'input Path,
    },
    /// Restore state only when module and function provenance match the
    /// expected already-admitted typed-IR projection.
    ProgressForSource {
        /// Source of the expected compilation identity (not executable state).
        expected: &'input TypedIrInput,
        /// Explicit interpreter used to run the trusted inspector.
        interpreter: &'input Path,
        /// Explicit trusted progress-sidecar inspector.
        inspector: &'input Path,
        /// Durable progress sidecar selecting the committed checkpoint.
        progress: &'input Path,
    },
}

/// Stable product compiler failure while selecting ternary stage state.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TernaryCompilerStageError {
    /// Fresh typed-IR projection lowering failed.
    Fresh(TernaryStageError),
    /// Durable progress extraction or ternary checkpoint admission failed.
    Progress(TernaryProgressCheckpointError),
}

/// Stable failures for progress-sidecar ternary-stage resume.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TernaryProgressCheckpointError {
    /// Restored module/function provenance differs from the expected source.
    IdentityMismatch,
    /// The configured progress inspector could not be launched.
    InspectorLaunch,
    /// The inspector rejected durable state or emitted diagnostics.
    InspectorRejected,
    /// Extracted bytes failed ternary-stage checkpoint admission.
    Stage(TernaryStageError),
}

impl From<TernaryStageError> for TernaryProgressCheckpointError {
    fn from(error: TernaryStageError) -> Self {
        Self::Stage(error)
    }
}

/// Restores pre-layout ternary state from one durable progress sidecar.
///
/// # Errors
///
/// Returns `TernaryProgressCheckpointError` when the inspector cannot launch,
/// rejects the generation, emits diagnostics, or returns bytes that fail
/// complete ternary-stage checkpoint admission.
pub fn resume_ternary_from_progress(
    interpreter: &Path,
    inspector: &Path,
    progress: &Path,
) -> Result<TernaryProgram, TernaryProgressCheckpointError> {
    let bytes = extract_ternary_checkpoint(
        interpreter,
        inspector,
        TERNARY_PROGRAM_CODEC_ID,
        progress,
    )
    .map_err(|error| match error {
        TransportError::Launch => {
            TernaryProgressCheckpointError::InspectorLaunch
        },
        TransportError::Rejected => {
            TernaryProgressCheckpointError::InspectorRejected
        },
    })?;
    enter_ternary_stage(TernaryStageInput::Checkpoint(&bytes))
        .map_err(Into::into)
}

// The target model encodes return category and source SSA operand in its
// final operation. Bind both to the caller projection: a different already-
// defined return value is independently valid but is not the same function.
fn matches_expected_return(
    expected: InputScalarType,
    expected_value: Option<u32>,
    last: Option<&TernaryOperation>,
) -> bool {
    let observed_value = match (expected, last) {
        (InputScalarType::Bool, Some(TernaryOperation::ReturnBool { value, .. }))
        | (InputScalarType::I8, Some(TernaryOperation::ReturnI8 { value, .. }))
        | (InputScalarType::I16, Some(TernaryOperation::ReturnI16 { value, .. }))
        | (InputScalarType::I32, Some(TernaryOperation::Return { value, .. }))
        | (InputScalarType::U8, Some(TernaryOperation::ReturnU8 { value, .. }))
        | (InputScalarType::U16, Some(TernaryOperation::ReturnU16 { value, .. }))
        | (InputScalarType::U32, Some(TernaryOperation::ReturnU32 { value, .. })) => {
            Some(*value)
        },
        (InputScalarType::Void, Some(TernaryOperation::ReturnVoid { .. })) => {
            None
        },
        _ => return false,
    };
    observed_value == expected_value
}

// Source-bound resume must not accept an expected function shape that fresh
// lowering cannot represent. Fresh lowering emits one operation per projected
// instruction plus a return; this count and control-flow envelope do not redo
// typed instruction lowering stored in the checkpoint. The explicit upstream
// Unsupported sentinel is not an executable projected instruction.
fn matches_supported_function_shape(
    function: &InputFunction,
    saved_operation_count: usize,
) -> bool {
    let [block] = function.blocks.as_slice() else {
        return false;
    };
    let Some(saved_instruction_count) = saved_operation_count.checked_sub(1)
    else {
        return false;
    };
    if function.parameter_count != 0
        || block.id != function.entry
        || block.phi_count != 0
        || saved_instruction_count != block.instructions.len()
        || block.instructions.iter().any(
            |instruction| matches!(instruction, InputInstruction::Unsupported)
        )
    {
        return false;
    }
    match (function.return_kind, block.terminator) {
        (InputScalarType::Void, InputTerminator::Return { value: None, .. }) => {
            true
        },
        (InputScalarType::Void, _) => false,
        (_, InputTerminator::Return { value: Some(_), .. }) => true,
        _ => false,
    }
}

// The source map is part of source-bound checkpoint identity, even when the
// saved program is independently valid and its function span still matches.
const fn matches_source_span(
    expected: InputSourceSpan,
    observed: Option<TernarySourceSpan>,
) -> bool {
    let Some(saved) = observed else {
        return false;
    };
    expected.begin.byte == saved.begin.byte
        && expected.begin.line == saved.begin.line
        && expected.begin.column == saved.begin.column
        && expected.end.byte == saved.end.byte
        && expected.end.line == saved.end.line
        && expected.end.column == saved.end.column
}

// Scalar constants are copied unchanged by the fresh lowerer. Match their
// exact bits, signedness and upstream SSA identity without reconstructing
// operations or walking a second SSA lowering state.
fn matches_expected_constant(
    instruction: &InputInstruction,
    saved: &TernaryOperation,
) -> bool {
    let InputInstruction::ConstantInteger {
        bit_width, little_endian, result, type_kind, ..
    } = instruction else {
        return true;
    };
    match (*bit_width, *type_kind, saved) {
        (1, InputScalarType::Bool,
            TernaryOperation::MaterializeBool {
                result: observed, value, ..
            }) => *observed == *result
                && little_endian.as_slice() == [u8::from(*value)],
        (8, InputScalarType::I8,
            TernaryOperation::MaterializeI8 {
                result: observed, scalar, ..
            })
        | (8, InputScalarType::U8,
            TernaryOperation::MaterializeU8 {
                result: observed, scalar, ..
            }) => *observed == *result
                && little_endian.as_slice() == [scalar.bits()],
        (16, InputScalarType::I16,
            TernaryOperation::MaterializeI16 {
                result: observed, scalar, ..
            })
        | (16, InputScalarType::U16,
            TernaryOperation::MaterializeU16 {
                result: observed, scalar, ..
            }) => *observed == *result
                && little_endian.as_slice() == scalar.bits().to_le_bytes(),
        (32, InputScalarType::I32,
            TernaryOperation::MaterializeI32 {
                result: observed, scalar, ..
            })
        | (32, InputScalarType::U32,
            TernaryOperation::MaterializeU32 {
                result: observed, scalar, ..
            }) => *observed == *result
                && little_endian.as_slice() == scalar.bits().to_le_bytes(),
        _ => false,
    }
}

// Bind projected binary semantics without re-running SSA lowering. The
// independently admitted checkpoint already proves each operand is defined;
// exact operation kind, signedness, and SSA identities remain source-bound.
const fn expected_binary_values(instruction: &InputInstruction) -> Option<BinaryValues> {
    let (
        InputInstruction::BinaryAdd { left, result, right, .. }
        | InputInstruction::BinaryAnd { left, result, right, .. }
        | InputInstruction::BinaryDivideSigned { left, result, right, .. }
        | InputInstruction::BinaryDivideUnsigned { left, result, right, .. }
        | InputInstruction::BinaryMultiply { left, result, right, .. }
        | InputInstruction::BinaryOr { left, result, right, .. }
        | InputInstruction::BinaryRemainderSigned { left, result, right, .. }
        | InputInstruction::BinaryRemainderUnsigned { left, result, right, .. }
        | InputInstruction::BinaryShiftLeft { left, result, right, .. }
        | InputInstruction::BinaryShiftRightArithmetic { left, result, right, .. }
        | InputInstruction::BinaryShiftRightLogical { left, result, right, .. }
        | InputInstruction::BinarySubtract { left, result, right, .. }
        | InputInstruction::BinaryXor { left, result, right, .. }) = instruction else {
        return None;
    };
    Some((*left, *result, *right))
}

const fn saved_binary_values(operation: &TernaryOperation) -> Option<BinaryValues> {
    let (
        TernaryOperation::AddI32 { left, result, right, .. }
        | TernaryOperation::AddU32 { left, result, right, .. }
        | TernaryOperation::AndI32 { left, result, right, .. }
        | TernaryOperation::AndU32 { left, result, right, .. }
        | TernaryOperation::DivideI32 { left, result, right, .. }
        | TernaryOperation::DivideU32 { left, result, right, .. }
        | TernaryOperation::MultiplyI32 { left, result, right, .. }
        | TernaryOperation::MultiplyU32 { left, result, right, .. }
        | TernaryOperation::OrI32 { left, result, right, .. }
        | TernaryOperation::OrU32 { left, result, right, .. }
        | TernaryOperation::RemainderI32 { left, result, right, .. }
        | TernaryOperation::RemainderU32 { left, result, right, .. }
        | TernaryOperation::ShiftLeftI32 { left, result, right, .. }
        | TernaryOperation::ShiftLeftU32 { left, result, right, .. }
        | TernaryOperation::ShiftRightArithmeticI32 { left, result, right, .. }
        | TernaryOperation::ShiftRightLogicalU32 { left, result, right, .. }
        | TernaryOperation::SubtractI32 { left, result, right, .. }
        | TernaryOperation::SubtractU32 { left, result, right, .. }
        | TernaryOperation::XorI32 { left, result, right, .. }
        | TernaryOperation::XorU32 { left, result, right, .. }) = operation else {
        return None;
    };
    Some((*left, *result, *right))
}

fn matches_expected_binary(
    instruction: &InputInstruction,
    saved: &TernaryOperation,
) -> bool {
    let Some(expected) = expected_binary_values(instruction) else {
        return true;
    };
    matches!((instruction, saved),
        (InputInstruction::BinaryAdd { type_kind: InputScalarType::I32, .. },
            TernaryOperation::AddI32 { .. })
        | (InputInstruction::BinaryAdd { type_kind: InputScalarType::U32, .. },
            TernaryOperation::AddU32 { .. })
        | (InputInstruction::BinaryAnd { type_kind: InputScalarType::I32, .. },
            TernaryOperation::AndI32 { .. })
        | (InputInstruction::BinaryAnd { type_kind: InputScalarType::U32, .. },
            TernaryOperation::AndU32 { .. })
        | (InputInstruction::BinaryDivideSigned { type_kind: InputScalarType::I32, .. },
            TernaryOperation::DivideI32 { .. })
        | (InputInstruction::BinaryDivideUnsigned { type_kind: InputScalarType::U32, .. },
            TernaryOperation::DivideU32 { .. })
        | (InputInstruction::BinaryMultiply { type_kind: InputScalarType::I32, .. },
            TernaryOperation::MultiplyI32 { .. })
        | (InputInstruction::BinaryMultiply { type_kind: InputScalarType::U32, .. },
            TernaryOperation::MultiplyU32 { .. })
        | (InputInstruction::BinaryOr { type_kind: InputScalarType::I32, .. },
            TernaryOperation::OrI32 { .. })
        | (InputInstruction::BinaryOr { type_kind: InputScalarType::U32, .. },
            TernaryOperation::OrU32 { .. })
        | (InputInstruction::BinaryRemainderSigned { type_kind: InputScalarType::I32, .. },
            TernaryOperation::RemainderI32 { .. })
        | (InputInstruction::BinaryRemainderUnsigned { type_kind: InputScalarType::U32, .. },
            TernaryOperation::RemainderU32 { .. })
        | (InputInstruction::BinaryShiftLeft { type_kind: InputScalarType::I32, .. },
            TernaryOperation::ShiftLeftI32 { .. })
        | (InputInstruction::BinaryShiftLeft { type_kind: InputScalarType::U32, .. },
            TernaryOperation::ShiftLeftU32 { .. })
        | (InputInstruction::BinaryShiftRightArithmetic { type_kind: InputScalarType::I32, .. },
            TernaryOperation::ShiftRightArithmeticI32 { .. })
        | (InputInstruction::BinaryShiftRightLogical { type_kind: InputScalarType::U32, .. },
            TernaryOperation::ShiftRightLogicalU32 { .. })
        | (InputInstruction::BinarySubtract { type_kind: InputScalarType::I32, .. },
            TernaryOperation::SubtractI32 { .. })
        | (InputInstruction::BinarySubtract { type_kind: InputScalarType::U32, .. },
            TernaryOperation::SubtractU32 { .. })
        | (InputInstruction::BinaryXor { type_kind: InputScalarType::I32, .. },
            TernaryOperation::XorI32 { .. })
        | (InputInstruction::BinaryXor { type_kind: InputScalarType::U32, .. },
            TernaryOperation::XorU32 { .. })
    ) && saved_binary_values(saved) == Some(expected)
}

// Guest byte effects cannot be exchanged for scalar materializations or
// each other solely because their spans and function identity still match.
// Retain the exact declared successful u8 input result or output operand.
const fn matches_expected_byte_effect(
    instruction: &InputInstruction,
    saved: &TernaryOperation,
) -> bool {
    if let InputInstruction::ByteInput {
        result, type_kind, ..
    } = instruction {
        matches!(type_kind, InputScalarType::U8)
            && matches!(saved, TernaryOperation::ByteInput {
                result: observed, ..
            } if *observed == *result)
    } else if let InputInstruction::ByteOutput { value, .. } = instruction {
        matches!(saved, TernaryOperation::ByteOutput {
            value: observed, ..
        } if *observed == *value)
    } else {
        true
    }
}

// Compare exact predicate and both operand/result SSA identities. For
// equality, the projection's Bool result does not itself encode operand
// signedness; earlier source-matched definitions constrain their categories.
const fn expected_comparison_values(
    instruction: &InputInstruction,
) -> Option<BinaryValues> {
    let (InputInstruction::CompareEqual { left, result, right, .. }
        | InputInstruction::CompareNotEqual { left, result, right, .. }
        | InputInstruction::CompareOrdered { left, result, right, .. }) = instruction
    else {
        return None;
    };
    Some((*left, *result, *right))
}

const fn saved_comparison_values(
    saved: &TernaryOperation,
) -> Option<BinaryValues> {
    let (TernaryOperation::EqualI32 { left, result, right, .. }
        | TernaryOperation::EqualU32 { left, result, right, .. }
        | TernaryOperation::NotEqualI32 { left, result, right, .. }
        | TernaryOperation::NotEqualU32 { left, result, right, .. }
        | TernaryOperation::LessSignedI32 { left, result, right, .. }
        | TernaryOperation::LessSignedEqualI32 { left, result, right, .. }
        | TernaryOperation::LessUnsignedU32 { left, result, right, .. }
        | TernaryOperation::LessUnsignedEqualU32 { left, result, right, .. }) = saved
    else {
        return None;
    };
    Some((*left, *result, *right))
}

fn matches_expected_comparison(
    instruction: &InputInstruction,
    saved: &TernaryOperation,
) -> bool {
    let Some(expected) = expected_comparison_values(instruction) else {
        return true;
    };
    matches!((instruction, saved),
        (InputInstruction::CompareEqual { type_kind: InputScalarType::Bool, .. },
            TernaryOperation::EqualI32 { .. } | TernaryOperation::EqualU32 { .. })
        | (InputInstruction::CompareNotEqual { type_kind: InputScalarType::Bool, .. },
            TernaryOperation::NotEqualI32 { .. } | TernaryOperation::NotEqualU32 { .. })
        | (InputInstruction::CompareOrdered {
                operation: InputOrderedComparison::Signed,
                type_kind: InputScalarType::Bool, ..
            }, TernaryOperation::LessSignedI32 { .. })
        | (InputInstruction::CompareOrdered {
                operation: InputOrderedComparison::SignedEqual,
                type_kind: InputScalarType::Bool, ..
            }, TernaryOperation::LessSignedEqualI32 { .. })
        | (InputInstruction::CompareOrdered {
                operation: InputOrderedComparison::Unsigned,
                type_kind: InputScalarType::Bool, ..
            }, TernaryOperation::LessUnsignedU32 { .. })
        | (InputInstruction::CompareOrdered {
                operation: InputOrderedComparison::UnsignedEqual,
                type_kind: InputScalarType::Bool, ..
            }, TernaryOperation::LessUnsignedEqualU32 { .. })
    ) && saved_comparison_values(saved) == Some(expected)
}

// Each cast retains both the upstream result and source SSA identity. The
// independently validated saved program establishes operand types, so
// matching the projected destination kind and exact operation family does
// not require rebuilding the lowerer's SSA type state.
const fn expected_cast_values(instruction: &InputInstruction) -> Option<(u32, u32)> {
    let (InputInstruction::BoolToSigned { result, value, .. }
        | InputInstruction::IntegerBitcast { result, value, .. }
        | InputInstruction::IntegerToBool { result, value, .. }
        | InputInstruction::SignExtendI8ToI32 { result, value, .. }
        | InputInstruction::TruncateInteger { result, value, .. }
        | InputInstruction::ZeroExtendInteger { result, value, .. }) = instruction else {
        return None;
    };
    Some((*result, *value))
}

const fn saved_cast_values(operation: &TernaryOperation) -> Option<(u32, u32)> {
    let (TernaryOperation::BoolToI8 { result, value, .. }
        | TernaryOperation::BoolToI16 { result, value, .. }
        | TernaryOperation::BoolToI32 { result, value, .. }
        | TernaryOperation::BitcastI8ToI8 { result, value, .. }
        | TernaryOperation::BitcastI8ToU8 { result, value, .. }
        | TernaryOperation::BitcastU8ToI8 { result, value, .. }
        | TernaryOperation::BitcastU8ToU8 { result, value, .. }
        | TernaryOperation::BitcastI16ToI16 { result, value, .. }
        | TernaryOperation::BitcastI16ToU16 { result, value, .. }
        | TernaryOperation::BitcastU16ToI16 { result, value, .. }
        | TernaryOperation::BitcastU16ToU16 { result, value, .. }
        | TernaryOperation::BitcastI32ToI32 { result, value, .. }
        | TernaryOperation::BitcastI32ToU32 { result, value, .. }
        | TernaryOperation::BitcastU32ToI32 { result, value, .. }
        | TernaryOperation::BitcastU32ToU32 { result, value, .. }
        | TernaryOperation::I8ToBool { result, value, .. }
        | TernaryOperation::U8ToBool { result, value, .. }
        | TernaryOperation::I16ToBool { result, value, .. }
        | TernaryOperation::U16ToBool { result, value, .. }
        | TernaryOperation::I32ToBool { result, value, .. }
        | TernaryOperation::U32ToBool { result, value, .. }
        | TernaryOperation::SignExtendI8ToI16 { result, value, .. }
        | TernaryOperation::SignExtendI8ToI32 { result, value, .. }
        | TernaryOperation::SignExtendI16ToI32 { result, value, .. }
        | TernaryOperation::TruncateI16ToI8 { result, value, .. }
        | TernaryOperation::TruncateI16ToU8 { result, value, .. }
        | TernaryOperation::TruncateI32ToI8 { result, value, .. }
        | TernaryOperation::TruncateI32ToU8 { result, value, .. }
        | TernaryOperation::TruncateU16ToI8 { result, value, .. }
        | TernaryOperation::TruncateU16ToU8 { result, value, .. }
        | TernaryOperation::TruncateU32ToI8 { result, value, .. }
        | TernaryOperation::TruncateU32ToU8 { result, value, .. }
        | TernaryOperation::TruncateI32ToI16 { result, value, .. }
        | TernaryOperation::TruncateI32ToU16 { result, value, .. }
        | TernaryOperation::TruncateU32ToI16 { result, value, .. }
        | TernaryOperation::TruncateU32ToU16 { result, value, .. }
        | TernaryOperation::ZeroExtendU8ToU16 { result, value, .. }
        | TernaryOperation::ZeroExtendU8ToU32 { result, value, .. }
        | TernaryOperation::ZeroExtendU16ToU32 { result, value, .. }) = operation else {
        return None;
    };
    Some((*result, *value))
}

fn matches_expected_cast(
    instruction: &InputInstruction,
    saved: &TernaryOperation,
) -> bool {
    let Some(expected) = expected_cast_values(instruction) else {
        return true;
    };
    matches!((instruction, saved),
        (InputInstruction::BoolToSigned { type_kind: InputScalarType::I8, .. },
            TernaryOperation::BoolToI8 { .. })
        | (InputInstruction::BoolToSigned { type_kind: InputScalarType::I16, .. },
            TernaryOperation::BoolToI16 { .. })
        | (InputInstruction::BoolToSigned { type_kind: InputScalarType::I32, .. },
            TernaryOperation::BoolToI32 { .. })
        | (InputInstruction::IntegerBitcast { type_kind: InputScalarType::I8, .. },
            TernaryOperation::BitcastI8ToI8 { .. } | TernaryOperation::BitcastU8ToI8 { .. })
        | (InputInstruction::IntegerBitcast { type_kind: InputScalarType::U8, .. },
            TernaryOperation::BitcastI8ToU8 { .. } | TernaryOperation::BitcastU8ToU8 { .. })
        | (InputInstruction::IntegerBitcast { type_kind: InputScalarType::I16, .. },
            TernaryOperation::BitcastI16ToI16 { .. } | TernaryOperation::BitcastU16ToI16 { .. })
        | (InputInstruction::IntegerBitcast { type_kind: InputScalarType::U16, .. },
            TernaryOperation::BitcastI16ToU16 { .. } | TernaryOperation::BitcastU16ToU16 { .. })
        | (InputInstruction::IntegerBitcast { type_kind: InputScalarType::I32, .. },
            TernaryOperation::BitcastI32ToI32 { .. } | TernaryOperation::BitcastU32ToI32 { .. })
        | (InputInstruction::IntegerBitcast { type_kind: InputScalarType::U32, .. },
            TernaryOperation::BitcastI32ToU32 { .. } | TernaryOperation::BitcastU32ToU32 { .. })
        | (InputInstruction::IntegerToBool { type_kind: InputScalarType::Bool, .. },
            TernaryOperation::I8ToBool { .. } | TernaryOperation::U8ToBool { .. } | TernaryOperation::I16ToBool { .. } | TernaryOperation::U16ToBool { .. } | TernaryOperation::I32ToBool { .. } | TernaryOperation::U32ToBool { .. })
        | (InputInstruction::SignExtendI8ToI32 { type_kind: InputScalarType::I16, .. },
            TernaryOperation::SignExtendI8ToI16 { .. })
        | (InputInstruction::SignExtendI8ToI32 { type_kind: InputScalarType::I32, .. },
            TernaryOperation::SignExtendI8ToI32 { .. } | TernaryOperation::SignExtendI16ToI32 { .. })
        | (InputInstruction::TruncateInteger { type_kind: InputScalarType::I8, .. },
            TernaryOperation::TruncateI16ToI8 { .. } | TernaryOperation::TruncateI32ToI8 { .. } | TernaryOperation::TruncateU16ToI8 { .. } | TernaryOperation::TruncateU32ToI8 { .. })
        | (InputInstruction::TruncateInteger { type_kind: InputScalarType::U8, .. },
            TernaryOperation::TruncateI16ToU8 { .. } | TernaryOperation::TruncateI32ToU8 { .. } | TernaryOperation::TruncateU16ToU8 { .. } | TernaryOperation::TruncateU32ToU8 { .. })
        | (InputInstruction::TruncateInteger { type_kind: InputScalarType::I16, .. },
            TernaryOperation::TruncateI32ToI16 { .. } | TernaryOperation::TruncateU32ToI16 { .. })
        | (InputInstruction::TruncateInteger { type_kind: InputScalarType::U16, .. },
            TernaryOperation::TruncateI32ToU16 { .. } | TernaryOperation::TruncateU32ToU16 { .. })
        | (InputInstruction::ZeroExtendInteger { type_kind: InputScalarType::U16, .. },
            TernaryOperation::ZeroExtendU8ToU16 { .. })
        | (InputInstruction::ZeroExtendInteger { type_kind: InputScalarType::U32, .. },
            TernaryOperation::ZeroExtendU8ToU32 { .. } | TernaryOperation::ZeroExtendU16ToU32 { .. })
    ) && saved_cast_values(saved) == Some(expected)
}

fn matches_expected_operation_spans(
    current: &InputFunction,
    saved: &TernaryFunction,
) -> bool {
    let [block] = current.blocks.as_slice() else {
        return false;
    };
    let Some((saved_return, saved_instructions)) = saved.operations.split_last()
    else {
        return false;
    };
    let InputTerminator::Return { span: return_span, .. } = block.terminator
    else {
        return false;
    };
    saved_instructions.len() == block.instructions.len()
        && saved_instructions.iter().zip(&block.instructions).all(
            |(saved_op, current_op)| {
                matches_expected_constant(current_op, saved_op)
                    && matches_expected_binary(current_op, saved_op)
                    && matches_expected_byte_effect(current_op, saved_op)
                    && matches_expected_comparison(current_op, saved_op)
                    && matches_expected_cast(current_op, saved_op)
                    && projected_instruction_span(current_op).is_some_and(
                        |span| matches_source_span(span, operation_span(*saved_op)),
                    )
            },
        )
        && matches_source_span(return_span, operation_span(*saved_return))
}

// Bind all admitted scalar, binary, byte, comparison and cast operations
// without re-lowering the saved work. The upstream source digest remains
// caller-authenticated; this is not toolchain or revision verification.
fn matches_expected_functions(
    program: &TernaryProgram,
    expected: &TypedIrInput,
) -> bool {
    program.functions.len() == expected.functions.len()
        && program.functions.iter().zip(&expected.functions).all(
            |(saved, current)| {
                matches_supported_function_shape(current, saved.operations.len())
                    && validate_projection_spans(current).is_ok()
                    && saved.id == current.id
                    && saved.name == current.name
                    && saved.span.begin.byte == current.span.begin.byte
                    && saved.span.begin.column == current.span.begin.column
                    && saved.span.begin.line == current.span.begin.line
                    && saved.span.end.byte == current.span.end.byte
                    && saved.span.end.column == current.span.end.column
                    && saved.span.end.line == current.span.end.line
                    && current.blocks.first().is_some_and(|block| {
                        match block.terminator {
                            InputTerminator::Return { value, .. } => {
                                matches_expected_return(
                                    current.return_kind,
                                    value,
                                    saved.operations.last(),
                                )
                            },
                            InputTerminator::Unsupported => false,
                        }
                    })
                    && matches_expected_operation_spans(current, saved)
            },
        )
}

/// Restores a checkpoint only for the caller's expected compiler source.
///
/// The progress inspector still verifies checkpoint-envelope compatibility,
/// and canonical stage admission validates the extracted ternary program.
/// This additional check binds that program to separately supplied expected
/// module, function and supported operation identity; it does not authenticate
/// the source digest, prove source-language equivalence, or replace toolchain
/// policy.
///
/// # Errors
///
/// Preserves inspector and canonical-stage errors, or returns
/// `IdentityMismatch` when the validated program differs from the caller's
/// current source identity.
pub fn resume_ternary_from_progress_for_source(
    interpreter: &Path,
    inspector: &Path,
    progress: &Path,
    expected: &TypedIrInput,
) -> Result<TernaryProgram, TernaryProgressCheckpointError> {
    let program =
        resume_ternary_from_progress(interpreter, inspector, progress)?;
    if expected.global_count != 0
        || expected.proof_obligation_count != 0
        || program.abi_id != expected.abi_id
        || program.input_format_version != expected.input_format_version
        || program.source_id != expected.source_id
        || program.source_sha256 != expected.source_sha256
        || program.target_profile != expected.target_profile
        || !matches_expected_functions(&program, expected)
    {
        return Err(TernaryProgressCheckpointError::IdentityMismatch);
    }
    Ok(program)
}

/// Enters ternary lowering from fresh projection or durable progress.
///
/// # Errors
///
/// Preserves whether fresh lowering or durable progress resume failed.
pub fn enter_ternary_compiler_stage(
    input: TernaryCompilerStageInput<'_>,
) -> Result<TernaryProgram, TernaryCompilerStageError> {
    match input {
        TernaryCompilerStageInput::Fresh(projection) => {
            enter_ternary_stage(TernaryStageInput::Projection(projection))
                .map_err(TernaryCompilerStageError::Fresh)
        },
        TernaryCompilerStageInput::Progress {
            inspector,
            interpreter,
            progress,
        } => resume_ternary_from_progress(interpreter, inspector, progress)
            .map_err(TernaryCompilerStageError::Progress),
        TernaryCompilerStageInput::ProgressForSource {
            expected,
            inspector,
            interpreter,
            progress,
        } => resume_ternary_from_progress_for_source(
            interpreter, inspector, progress, expected,
        )
        .map_err(TernaryCompilerStageError::Progress),
    }
}
