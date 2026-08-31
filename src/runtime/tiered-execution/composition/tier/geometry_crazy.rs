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
//   - Checkpoint-bound semantic admission and load-image authority for v5
//     crazy.
// - Must-Not:
//   - Map executable memory, prepare ABI buffers, invoke native code, or cache.
// - Allows:
//   - Inputs: exact v5 crazy IR, verified artifact, and opaque checkpoint.
//   - Outputs: normatively replayed crazy admission and relocation-free image.
//   - Side effects: none.
// - Split-When:
//   - Crazy invocation or reusable residency gains independent lifecycle
//     policy.
// - Merge-When:
//   - One reviewed geometry-native operation framework preserves equal proofs.
// - Summary:
//   - Admits v5 crazy only after exact checkpoint replay.
// - Description:
//   - Binds crazy artifact identity to opaque geometry and replayed exit state.
// - Usage:
//   - Construct before any future mapping or invocation boundary.
// - Defaults:
//   - Checkpoint, replay, identity, artifact, or load-image drift fails closed.
//

//! Checkpoint-bound semantic admission for explicit-geometry crazy.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{ExecutionGeometryRegionEffectProgram, ProfileMachineState};

use crate::execution_cache::{NativeArtifactKey, NativeIdentityError};
use crate::execution_native::{
    VerifiedDirectLoadError,
    VerifiedExecutionGeometryCrazyNativeObjectArtifact,
    VerifiedExecutionGeometryLoadImage,
};
use crate::geometry_interpreter_handoff::{
    ExecutionGeometryHandoffAdmissionError,
    ExecutionGeometryHandoffExecutionCause,
    ExecutionGeometryInterpreterHandoff,
};

/// Failure before one verified v5 crazy can retain checkpoint authority.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeCrazyAdmissionError {
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

/// Verified v5 crazy bound to one opaque checkpoint and normative exit.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeCrazyAdmission {
    artifact: VerifiedExecutionGeometryCrazyNativeObjectArtifact,
    checkpoint: ProfileMachineState,
    expected_state: ProfileMachineState,
    load_image: VerifiedExecutionGeometryLoadImage,
    program: ExecutionGeometryRegionEffectProgram,
}

impl Display for ExecutionGeometryNativeCrazyAdmissionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::ArtifactIdentity => {
                f.write_str("verified v5 crazy artifact identity drifted")
            },
            Self::Checkpoint(error) => Display::fmt(error, f),
            Self::Identity(_error) => {
                f.write_str("v5 crazy identity reconstruction failed")
            },
            Self::Load(error) => Display::fmt(error, f),
            Self::NormativeReplay(error) => Display::fmt(error, f),
        }
    }
}

impl ExecutionGeometryNativeCrazyAdmission {
    /// Returns the exact verified v5 crazy artifact retained by admission.
    #[must_use]
    pub const fn artifact(
        &self,
    ) -> &VerifiedExecutionGeometryCrazyNativeObjectArtifact {
        &self.artifact
    }

    /// Returns the normative entry checkpoint carrying opaque geometry
    /// authority.
    #[must_use]
    pub const fn checkpoint(&self) -> &ProfileMachineState {
        &self.checkpoint
    }

    /// Returns the exact normative state accepted by future Applied execution.
    #[must_use]
    pub const fn expected_state(&self) -> &ProfileMachineState {
        &self.expected_state
    }

    /// Returns the relocation-free load image retaining exact v5 identity.
    #[must_use]
    pub const fn load_image(&self) -> &VerifiedExecutionGeometryLoadImage {
        &self.load_image
    }

    /// Binds verified crazy evidence to a normatively replayed checkpoint.
    ///
    /// Admission first checks opaque geometry/effect continuity through the
    /// interpreter handoff. Only after exact replay succeeds does it rebuild
    /// native identity and extract a relocation-free code image.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeCrazyAdmissionError`] for checkpoint,
    /// replay, identity, artifact, or load-image disagreement.
    pub fn new(
        program: ExecutionGeometryRegionEffectProgram,
        checkpoint: ProfileMachineState,
        artifact: VerifiedExecutionGeometryCrazyNativeObjectArtifact,
    ) -> Result<Self, ExecutionGeometryNativeCrazyAdmissionError> {
        let replay = ExecutionGeometryInterpreterHandoff::new(
            program.clone(),
            checkpoint.clone(),
        )
        .map_err(ExecutionGeometryNativeCrazyAdmissionError::Checkpoint)?;
        let completion = replay.execute().map_err(|failure| {
            ExecutionGeometryNativeCrazyAdmissionError::NormativeReplay(
                failure.cause(),
            )
        })?;
        let expected_key = NativeArtifactKey::new_execution_geometry(
            &program,
            artifact.key().target().clone(),
        )
        .map_err(ExecutionGeometryNativeCrazyAdmissionError::Identity)?;
        if artifact.key() != &expected_key {
            return Err(
                ExecutionGeometryNativeCrazyAdmissionError::ArtifactIdentity,
            );
        }
        let load_image =
            VerifiedExecutionGeometryLoadImage::from_crazy(&artifact)
                .map_err(ExecutionGeometryNativeCrazyAdmissionError::Load)?;
        Ok(Self {
            artifact,
            checkpoint,
            expected_state: completion.state().clone(),
            load_image,
            program,
        })
    }

    /// Returns the exact v5 crazy IR retained by admission.
    #[must_use]
    pub const fn program(&self) -> &ExecutionGeometryRegionEffectProgram {
        &self.program
    }
}
