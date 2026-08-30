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
//   - Admission binding one verified v5 native artifact and load image to the
//   - opaque execution geometry carried by one validated VM checkpoint.
// - Must-Not:
//   - Map executable memory, invoke machine code, forge geometry tokens, or
//   - route v5 through legacy direct-native execution APIs.
// - Allows:
//   - Inputs: verified explicit-geometry initial-halt artifact, exact v5 IR,
//   - and one complete validated profile-machine checkpoint.
//   - Outputs: an affine checkpoint-bound native admission value.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - Split when geometry-aware executable lifecycle or invocation gains
//   - independent policy.
// - Merge-When:
//   - Merge when one geometry-native owner subsumes admission and execution.
// - Summary:
//   - Makes opaque checkpoint geometry prerequisite to v5 native authority.
// - Description:
//   - Rechecks exact v5 identity beside normative checkpoint admission before
//   - retaining any load-image evidence.
// - Usage:
//   - Construct before any future geometry-aware mapping or invocation bridge.
// - Defaults:
//   - Artifact, profile, geometry, observation, capacity, or live-in drift
//   - fails closed without exposing executable authority.
//

//! Checkpoint-bound admission for explicit-geometry native artifacts.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{ExecutionGeometryRegionEffectProgram, ProfileMachineState};

use crate::execution_cache::{NativeArtifactKey, NativeIdentityError};
use crate::execution_native::{
    VerifiedDirectLoadError,
    VerifiedExecutionGeometryInitialHaltNativeObjectArtifact,
    VerifiedExecutionGeometryLoadImage,
};
use crate::geometry_interpreter_handoff::{
    ExecutionGeometryHandoffAdmissionError, ExecutionGeometryInterpreterHandoff,
};

/// Failure before one v5 native artifact can retain checkpoint-bound authority.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeInitialHaltAdmissionError {
    /// Verified artifact identity differs from the exact requested v5 program.
    ArtifactIdentity,
    /// Opaque checkpoint authority disagrees with the requested v5 program.
    Checkpoint(ExecutionGeometryHandoffAdmissionError),
    /// Exact v5 native identity could not be reconstructed.
    Identity(NativeIdentityError),
    /// Verified COFF could not become one relocation-free aligned load image.
    Load(VerifiedDirectLoadError),
}

/// Verified v5 initial-halt artifact inseparably bound to one opaque
/// checkpoint.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeInitialHaltAdmission {
    artifact: VerifiedExecutionGeometryInitialHaltNativeObjectArtifact,
    checkpoint: ProfileMachineState,
    load_image: VerifiedExecutionGeometryLoadImage,
    program: ExecutionGeometryRegionEffectProgram,
}

impl Display for ExecutionGeometryNativeInitialHaltAdmissionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::ArtifactIdentity => {
                f.write_str("v5 native artifact identity differs from program")
            },
            Self::Checkpoint(error) => Display::fmt(error, f),
            Self::Identity(_error) => {
                f.write_str("v5 native identity reconstruction failed")
            },
            Self::Load(error) => Display::fmt(error, f),
        }
    }
}

impl ExecutionGeometryNativeInitialHaltAdmission {
    /// Returns the exact verified v5 native artifact retained by admission.
    #[must_use]
    pub const fn artifact(
        &self,
    ) -> &VerifiedExecutionGeometryInitialHaltNativeObjectArtifact {
        &self.artifact
    }

    /// Returns the normative checkpoint carrying opaque geometry authority.
    #[must_use]
    pub const fn checkpoint(&self) -> &ProfileMachineState {
        &self.checkpoint
    }

    /// Returns the relocation-free load image bound to the same exact v5 key.
    #[must_use]
    pub const fn load_image(&self) -> &VerifiedExecutionGeometryLoadImage {
        &self.load_image
    }

    /// Binds verified v5 native evidence to one already validated checkpoint.
    ///
    /// The checkpoint's opaque geometry token remains the execution authority.
    /// Exact program/artifact identity is reconstructed independently before a
    /// load image is retained. No executable mapping or call is performed.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeInitialHaltAdmissionError`] when
    /// checkpoint admission, exact v5 artifact identity, or load-image
    /// extraction fails.
    pub fn new(
        program: ExecutionGeometryRegionEffectProgram,
        checkpoint: ProfileMachineState,
        artifact: VerifiedExecutionGeometryInitialHaltNativeObjectArtifact,
    ) -> Result<Self, ExecutionGeometryNativeInitialHaltAdmissionError> {
        let _checkpoint_admission = ExecutionGeometryInterpreterHandoff::new(
            program.clone(),
            checkpoint.clone(),
        )
        .map_err(
            ExecutionGeometryNativeInitialHaltAdmissionError::Checkpoint,
        )?;
        let expected_key = NativeArtifactKey::new_execution_geometry(
            &program,
            artifact.key().target().clone(),
        )
        .map_err(ExecutionGeometryNativeInitialHaltAdmissionError::Identity)?;
        if artifact.key() != &expected_key {
            use ExecutionGeometryNativeInitialHaltAdmissionError as Error;
            return Err(Error::ArtifactIdentity);
        }
        let load_image =
            VerifiedExecutionGeometryLoadImage::from_initial_halt(&artifact)
                .map_err(
                    ExecutionGeometryNativeInitialHaltAdmissionError::Load,
                )?;
        Ok(Self {
            artifact,
            checkpoint,
            load_image,
            program,
        })
    }

    /// Returns the exact v5 program whose declarative geometry was admitted.
    #[must_use]
    pub const fn program(&self) -> &ExecutionGeometryRegionEffectProgram {
        &self.program
    }
}
