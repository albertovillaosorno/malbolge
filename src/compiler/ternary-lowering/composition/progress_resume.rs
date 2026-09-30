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

use std::path::Path;
use std::process::{Command, Stdio};

use super::model::TernaryProgram;
use super::program_codec::TERNARY_PROGRAM_CODEC_ID;
use super::stage::{TernaryStageError, TernaryStageInput, enter_ternary_stage};

const EXTRACT_CHECKPOINT_ARGUMENT: &str = "--extract-checkpoint";

/// Product compiler selection for entering the ternary-lowering stage.
#[derive(Clone, Copy, Debug)]
pub enum TernaryCompilerStageInput<'input> {
    /// Lower fresh admitted typed-IR projection.
    Fresh(&'input super::input::TypedIrInput),
    /// Restore verified ternary state from one durable progress sidecar.
    Progress {
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
    let output = Command::new(interpreter)
        .arg(inspector)
        .arg(EXTRACT_CHECKPOINT_ARGUMENT)
        .arg(TERNARY_PROGRAM_CODEC_ID)
        .arg(progress)
        .stdin(Stdio::null())
        .output()
        .map_err(|_error| TernaryProgressCheckpointError::InspectorLaunch)?;
    if !output.status.success() || !output.stderr.is_empty() {
        return Err(TernaryProgressCheckpointError::InspectorRejected);
    }
    enter_ternary_stage(TernaryStageInput::Checkpoint(&output.stdout))
        .map_err(Into::into)
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
    }
}
