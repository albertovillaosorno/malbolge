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
//   - Composition from verified progress extraction into the ternary stage.
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
//   - Consumes verified ternary checkpoint state from one progress sidecar.
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
