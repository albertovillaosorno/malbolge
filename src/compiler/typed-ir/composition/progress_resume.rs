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
//   - Composition from the verified progress-sidecar extractor into typed IR.
// - Must-Not:
//   - Parse sidecar JSON, duplicate portable-checkpoint validation, or select
//     repository-local tool paths implicitly.
// - Allows:
//   - Inputs: explicit interpreter, inspector, and progress-sidecar paths.
//   - Outputs: one fully admitted typed-IR module or stable bridge failure.
//   - Side effects: one bounded child process owned by the caller-selected
//     progress inspector.
// - Split-When:
//   - Another durable compiler-state codec needs an independent adapter.
// - Merge-When:
//   - Compiler composition directly owns the progress-sidecar wire contract.
// - Summary:
//   - Consumes verified typed-IR checkpoint state from one progress sidecar.
// - Description:
//   - Delegates sidecar/envelope validation to the repository inspector and
//     admits only the exact typed-IR codec bytes returned by extraction.
// - Usage:
//   - Compiler composition supplies its explicit progress-inspector command.
// - Defaults:
//   - Launch failure, inspector diagnostics, and invalid typed IR fail closed.
//

//! Verified progress-sidecar composition for typed compiler IR resume.

use std::path::Path;
use std::process::{Command, Stdio};

use super::encode::TYPED_IR_CODEC_ID;
use super::module::Module;
use super::stage::{
    TypedIrStageError, TypedIrStageInput, enter_typed_ir_stage,
};

const EXTRACT_CHECKPOINT_ARGUMENT: &str = "--extract-checkpoint";

/// Stable failure categories for progress-sidecar typed-IR resume adaptation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ProgressCheckpointError {
    /// The configured progress inspector could not be launched.
    InspectorLaunch,
    /// The inspector rejected the generation or emitted diagnostics.
    InspectorRejected,
    /// Extracted bytes failed typed-IR checkpoint admission.
    Stage(TypedIrStageError),
}

impl From<TypedIrStageError> for ProgressCheckpointError {
    fn from(error: TypedIrStageError) -> Self {
        Self::Stage(error)
    }
}

/// Restores typed IR directly from one durable progress-sidecar path.
///
/// # Errors
///
/// Returns [`ProgressCheckpointError`] when the inspector cannot launch,
/// rejects the durable generation, emits unexpected diagnostics, or returns
/// bytes that fail complete typed-IR checkpoint admission.
pub fn resume_typed_ir_from_progress(
    interpreter: &Path,
    inspector: &Path,
    progress: &Path,
) -> Result<Module, ProgressCheckpointError> {
    let output = Command::new(interpreter)
        .arg(inspector)
        .arg(EXTRACT_CHECKPOINT_ARGUMENT)
        .arg(TYPED_IR_CODEC_ID)
        .arg(progress)
        .stdin(Stdio::null())
        .output()
        .map_err(|_error| ProgressCheckpointError::InspectorLaunch)?;
    if !output.status.success() || !output.stderr.is_empty() {
        return Err(ProgressCheckpointError::InspectorRejected);
    }
    enter_typed_ir_stage(TypedIrStageInput::Checkpoint(&output.stdout))
        .map_err(Into::into)
}
