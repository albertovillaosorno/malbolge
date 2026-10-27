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

use super::input::TypedIrInput;
use super::model::TernaryProgram;
use super::program_codec::TERNARY_PROGRAM_CODEC_ID;
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
    /// Restore state only when its source/ABI/profile matches the expected
    /// already-admitted typed-IR projection.
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
    /// Restored provenance is not the caller's expected source/ABI/profile.
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

/// Restores a checkpoint only for the caller's expected compiler source.
///
/// The progress inspector still verifies checkpoint-envelope compatibility,
/// and canonical stage admission validates the extracted ternary program.
/// This additional check binds that program to separately supplied expected
/// source/ABI/profile provenance; it does not authenticate the source digest
/// or substitute for the caller's toolchain/revision compatibility policy.
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
    if program.abi_id != expected.abi_id
        || program.input_format_version != expected.input_format_version
        || program.source_id != expected.source_id
        || program.source_sha256 != expected.source_sha256
        || program.target_profile != expected.target_profile
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
