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
    InputFunction, InputInstruction, InputScalarType, InputSourceSpan,
    InputTerminator, TypedIrInput,
};
use super::lower::{projected_instruction_span, validate_projection_spans};
use super::model::{TernaryFunction, TernaryOperation, TernaryProgram, TernarySourceSpan};
use super::program_codec::{TERNARY_PROGRAM_CODEC_ID, operation_span};
use super::stage::{TernaryStageError, TernaryStageInput, enter_ternary_stage};

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
                projected_instruction_span(current_op).is_some_and(
                    |span| matches_source_span(span, operation_span(*saved_op)),
                )
            },
        )
        && matches_source_span(return_span, operation_span(*saved_return))
}

// This comparison is deliberately structural rather than a fresh lowering:
// resuming a large job must not re-run the work stored in its checkpoint.
// It binds function identity and exact source spans in addition to module
// provenance, while the upstream source digest remains caller-authenticated.
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
/// module and function provenance; it does not authenticate the source digest,
/// compare operation semantics, or substitute for toolchain/revision policy.
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
