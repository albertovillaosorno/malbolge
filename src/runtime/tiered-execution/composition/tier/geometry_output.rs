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
//   - Checkpoint-bound semantic admission and load planning for v5 output.
// - Must-Not:
//   - Invoke native code, map executable memory, forge geometry authority, or
//   - route explicit geometry through legacy direct-native APIs.
// - Allows:
//   - Inputs: exact v5 output IR/artifact and opaque entry checkpoint.
//   - Outputs: normative exit authority and relocation-free verified load
//     image.
//   - Side effects: none.
// - Split-When:
//   - Native invocation introduces output-specific ABI or rollback policy.
// - Merge-When:
//   - A reviewed common geometry-native admission framework preserves proofs.
// - Summary:
//   - Admits only normatively replayed explicit-geometry output.
// - Description:
//   - Binds exact output artifact identity to opaque checkpoint and replay
//     exit.
// - Usage:
//   - Construct before any mapping; consume load image in a later execution
//     layer.
// - Defaults:
//   - Geometry, identity, replay, or load-image drift fails closed before
//     mapping.
//

//! Checkpoint-bound semantic admission for explicit-geometry output.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{ExecutionGeometryRegionEffectProgram, ProfileMachineState};

use crate::execution_cache::{NativeArtifactKey, NativeIdentityError};
use crate::execution_native::{
    VerifiedDirectLoadError, VerifiedExecutionGeometryLoadImage,
    VerifiedExecutionGeometryOutputNativeObjectArtifact,
};
use crate::geometry_interpreter_handoff::{
    ExecutionGeometryHandoffAdmissionError,
    ExecutionGeometryHandoffExecutionCause,
    ExecutionGeometryInterpreterHandoff,
};

/// Failure before one verified v5 output can retain checkpoint authority.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeOutputAdmissionError {
    /// Verified artifact identity differs from the exact requested v5 program.
    ArtifactIdentity,
    /// Opaque checkpoint authority disagrees with the requested v5 program.
    Checkpoint(ExecutionGeometryHandoffAdmissionError),
    /// Exact v5 native identity could not be reconstructed.
    Identity(NativeIdentityError),
    /// Verified COFF could not become one relocation-free aligned load image.
    Load(VerifiedDirectLoadError),
    /// Normative one-step replay disagreed with the supplied v5 program.
    NormativeReplay(ExecutionGeometryHandoffExecutionCause),
}

/// Verified v5 output bound to one opaque checkpoint and normative exit.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeOutputAdmission {
    artifact: VerifiedExecutionGeometryOutputNativeObjectArtifact,
    checkpoint: ProfileMachineState,
    expected_state: ProfileMachineState,
    load_image: VerifiedExecutionGeometryLoadImage,
    program: ExecutionGeometryRegionEffectProgram,
}

impl Display for ExecutionGeometryNativeOutputAdmissionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::ArtifactIdentity => {
                f.write_str("verified v5 output artifact identity drifted")
            },
            Self::Checkpoint(error) => Display::fmt(error, f),
            Self::Identity(_error) => {
                f.write_str("v5 output identity reconstruction failed")
            },
            Self::Load(error) => Display::fmt(error, f),
            Self::NormativeReplay(error) => Display::fmt(error, f),
        }
    }
}

impl ExecutionGeometryNativeOutputAdmission {
    /// Returns the exact verified v5 output artifact retained by admission.
    #[must_use]
    pub const fn artifact(
        &self,
    ) -> &VerifiedExecutionGeometryOutputNativeObjectArtifact {
        &self.artifact
    }

    /// Returns the normative entry checkpoint carrying opaque geometry
    /// authority.
    #[must_use]
    pub const fn checkpoint(&self) -> &ProfileMachineState {
        &self.checkpoint
    }

    /// Returns the exact normative state accepted for a future applied call.
    #[must_use]
    pub const fn expected_state(&self) -> &ProfileMachineState {
        &self.expected_state
    }

    /// Returns the relocation-free load image retaining exact v5 identity.
    #[must_use]
    pub const fn load_image(&self) -> &VerifiedExecutionGeometryLoadImage {
        &self.load_image
    }

    /// Binds verified output evidence to a normatively replayed checkpoint.
    ///
    /// Admission first checks opaque geometry/effect continuity through the
    /// interpreter handoff. Only after exact replay succeeds does it rebuild
    /// native identity and extract a relocation-free code image.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeOutputAdmissionError`] for checkpoint,
    /// replay, identity, artifact, or load-image disagreement.
    pub fn new(
        program: ExecutionGeometryRegionEffectProgram,
        checkpoint: ProfileMachineState,
        artifact: VerifiedExecutionGeometryOutputNativeObjectArtifact,
    ) -> Result<Self, ExecutionGeometryNativeOutputAdmissionError> {
        let replay = ExecutionGeometryInterpreterHandoff::new(
            program.clone(),
            checkpoint.clone(),
        )
        .map_err(ExecutionGeometryNativeOutputAdmissionError::Checkpoint)?;
        let completion = replay.execute().map_err(|failure| {
            ExecutionGeometryNativeOutputAdmissionError::NormativeReplay(
                failure.cause(),
            )
        })?;
        let expected_key = NativeArtifactKey::new_execution_geometry(
            &program,
            artifact.key().target().clone(),
        )
        .map_err(ExecutionGeometryNativeOutputAdmissionError::Identity)?;
        if artifact.key() != &expected_key {
            return Err(
                ExecutionGeometryNativeOutputAdmissionError::ArtifactIdentity,
            );
        }
        let load_image =
            VerifiedExecutionGeometryLoadImage::from_output(&artifact)
                .map_err(ExecutionGeometryNativeOutputAdmissionError::Load)?;
        Ok(Self {
            artifact,
            checkpoint,
            expected_state: completion.state().clone(),
            load_image,
            program,
        })
    }

    /// Returns the exact v5 output IR retained by admission.
    #[must_use]
    pub const fn program(&self) -> &ExecutionGeometryRegionEffectProgram {
        &self.program
    }
}
