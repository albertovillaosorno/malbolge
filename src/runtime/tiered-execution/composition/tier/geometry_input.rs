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
//     input.
// - Must-Not:
//   - Map executable memory, prepare ABI buffers, invoke native code, or cache.
// - Allows:
//   - Inputs: exact v5 input IR, verified artifact, and opaque checkpoint.
//   - Outputs: normatively replayed input admission and relocation-free image.
//   - Side effects: none.
// - Split-When:
//   - Input invocation or reusable residency gains independent lifecycle
//     policy.
// - Merge-When:
//   - One reviewed geometry-native operation framework preserves equal proofs.
// - Summary:
//   - Admits v5 input only after exact checkpoint replay.
// - Description:
//   - Binds byte/EOF input artifact identity to opaque geometry and replayed
//     exit.
// - Usage:
//   - Construct before any future mapping or invocation boundary.
// - Defaults:
//   - Checkpoint, replay, identity, artifact, or load-image drift fails closed.
//

//! Checkpoint-bound semantic admission for explicit-geometry input.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{ExecutionGeometryRegionEffectProgram, ProfileMachineState};

use crate::execution_cache::{NativeArtifactKey, NativeIdentityError};
use crate::execution_native::{
    VerifiedDirectLoadError,
    VerifiedExecutionGeometryInputNativeObjectArtifact,
    VerifiedExecutionGeometryLoadImage,
};
use crate::geometry_interpreter_handoff::{
    ExecutionGeometryHandoffAdmissionError,
    ExecutionGeometryHandoffExecutionCause,
    ExecutionGeometryInterpreterHandoff,
};

/// Failure before one verified v5 input can retain checkpoint authority.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeInputAdmissionError {
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

/// Verified v5 input bound to one opaque checkpoint and normative exit.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeInputAdmission {
    artifact: VerifiedExecutionGeometryInputNativeObjectArtifact,
    checkpoint: ProfileMachineState,
    expected_state: ProfileMachineState,
    load_image: VerifiedExecutionGeometryLoadImage,
    program: ExecutionGeometryRegionEffectProgram,
}

impl Display for ExecutionGeometryNativeInputAdmissionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::ArtifactIdentity => {
                f.write_str("verified v5 input artifact identity drifted")
            },
            Self::Checkpoint(error) => Display::fmt(error, f),
            Self::Identity(_error) => {
                f.write_str("v5 input identity reconstruction failed")
            },
            Self::Load(error) => Display::fmt(error, f),
            Self::NormativeReplay(error) => Display::fmt(error, f),
        }
    }
}

impl ExecutionGeometryNativeInputAdmission {
    /// Returns the exact verified v5 input artifact retained by admission.
    #[must_use]
    pub const fn artifact(
        &self,
    ) -> &VerifiedExecutionGeometryInputNativeObjectArtifact {
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

    /// Binds verified input evidence to a normatively replayed checkpoint.
    ///
    /// Admission first checks opaque geometry/effect continuity through the
    /// interpreter handoff. Only after exact replay succeeds does it rebuild
    /// native identity and extract a relocation-free code image.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeInputAdmissionError`] for checkpoint,
    /// replay, identity, artifact, or load-image disagreement.
    pub fn new(
        program: ExecutionGeometryRegionEffectProgram,
        checkpoint: ProfileMachineState,
        artifact: VerifiedExecutionGeometryInputNativeObjectArtifact,
    ) -> Result<Self, ExecutionGeometryNativeInputAdmissionError> {
        let replay = ExecutionGeometryInterpreterHandoff::new(
            program.clone(),
            checkpoint.clone(),
        )
        .map_err(ExecutionGeometryNativeInputAdmissionError::Checkpoint)?;
        let completion = replay.execute().map_err(|failure| {
            ExecutionGeometryNativeInputAdmissionError::NormativeReplay(
                failure.cause(),
            )
        })?;
        let expected_key = NativeArtifactKey::new_execution_geometry(
            &program,
            artifact.key().target().clone(),
        )
        .map_err(ExecutionGeometryNativeInputAdmissionError::Identity)?;
        if artifact.key() != &expected_key {
            return Err(
                ExecutionGeometryNativeInputAdmissionError::ArtifactIdentity,
            );
        }
        let load_image =
            VerifiedExecutionGeometryLoadImage::from_input(&artifact)
                .map_err(ExecutionGeometryNativeInputAdmissionError::Load)?;
        Ok(Self {
            artifact,
            checkpoint,
            expected_state: completion.state().clone(),
            load_image,
            program,
        })
    }

    /// Returns the exact v5 input IR retained by admission.
    #[must_use]
    pub const fn program(&self) -> &ExecutionGeometryRegionEffectProgram {
        &self.program
    }
}
