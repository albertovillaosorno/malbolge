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
//   - One reusable verified fused executable mapping and repeated exact calls.
// - Must-Not:
//   - Add leases, caches, sequence authority, or broaden fused admission.
// - Allows:
//   - Inputs: one verified fused artifact, adapter, runner, and caller buffers.
//   - Outputs: one reusable owner, exact weight, outcomes, and retry cleanup.
//   - Side effects: executable load/release only through the supplied adapter.
// - Split-When:
//   - Fused lease/cache policy or multi-region ownership gains independent
//     rules.
// - Merge-When:
//   - One general direct executable store subsumes exact fused residency.
// - Summary:
//   - Reuses one exact fused mapping across independently prepared calls.
// - Description:
//   - Runner/completion failure rolls back one call without losing residency.
// - Usage:
//   - Load once, execute fresh borrowed buffers repeatedly, then release.
// - Defaults:
//   - Repeated execution performs no executable-memory adapter operations.
//

//! Reusable ownership of one exact fused direct executable mapping.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::RegionEffectProgram;

use super::direct::VerifiedDirectFusedSequenceObjectArtifact;
use super::invocation::{
    DirectFusedInvocationError, NativeRegionBuffers,
    NativeRegionInvocationOutcome, PreparedDirectFusedInvocation,
};
use super::lifecycle::ReadyDirectFusedNativeExecutable;
use super::loader::{VerifiedDirectFusedLoadImage, VerifiedDirectLoadError};
use super::platform::{
    DirectFusedNativeExecutableReleaseFailure, NativeExecutableLoadFailure,
    NativeExecutableMemoryAdapter, load_direct_fused_native_executable,
    release_direct_fused_native_executable,
};
use super::runner::{
    DirectFusedLoadedExecutionFailure, DirectFusedNativeRunner,
    execute_loaded_verified_direct_fused_native,
};
use crate::execution_cache::NativeArtifactKey;

/// Failure while loading one reusable exact fused mapping.
#[derive(Debug, Eq, PartialEq)]
pub enum DirectFusedNativeOwnerLoadFailure<MemoryError> {
    /// Verified fused object could not become one relocation-free load image.
    Image(Box<VerifiedDirectLoadError>),
    /// Platform mapping/lifecycle admission failed.
    Load(Box<NativeExecutableLoadFailure<MemoryError>>),
}

/// Failure while executing through one retained fused mapping.
#[derive(Debug, Eq, PartialEq)]
pub enum DirectFusedNativeOwnerExecutionFailure<RunnerError> {
    /// Exact bound runner or completion admission failed.
    Execution(Box<DirectFusedLoadedExecutionFailure<RunnerError>>),
    /// Caller buffers failed exact whole-region preparation.
    Preparation(DirectFusedInvocationError),
}

/// Exact synchronized mapping weight retained by one fused owner.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct DirectFusedNativeResidentWeight {
    mapped_bytes: usize,
    mappings: usize,
}

/// One verified fused artifact retained beside its exact ready mapping.
#[derive(Debug)]
pub struct DirectFusedNativeExecutableOwner {
    artifact: VerifiedDirectFusedSequenceObjectArtifact,
    executable: ReadyDirectFusedNativeExecutable,
}

/// Result of loading one reusable exact fused mapping.
pub type DirectFusedNativeOwnerLoadResult<MemoryError> = Result<
    DirectFusedNativeExecutableOwner,
    Box<DirectFusedNativeOwnerLoadFailure<MemoryError>>,
>;

/// Result of one call through a reusable fused mapping.
pub type DirectFusedNativeOwnerExecutionResult<RunnerError> = Result<
    NativeRegionInvocationOutcome,
    Box<DirectFusedNativeOwnerExecutionFailure<RunnerError>>,
>;

/// Result of explicitly releasing one reusable fused mapping.
pub type DirectFusedNativeOwnerReleaseResult<MemoryError> =
    Result<(), Box<DirectFusedNativeExecutableReleaseFailure<MemoryError>>>;

impl<MemoryError: Display> Display
    for DirectFusedNativeOwnerLoadFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Image(error) => Display::fmt(error, f),
            Self::Load(error) => {
                write!(f, "fused resident load failed: {error}")
            },
        }
    }
}

impl<RunnerError: Display> Display
    for DirectFusedNativeOwnerExecutionFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Execution(error) => Display::fmt(error, f),
            Self::Preparation(error) => {
                write!(f, "fused resident preparation failed: {error}")
            },
        }
    }
}

impl DirectFusedNativeResidentWeight {
    /// Returns exact synchronized mapped bytes retained by this owner.
    #[must_use]
    pub const fn mapped_bytes(self) -> usize {
        self.mapped_bytes
    }

    /// Returns the exact number of retained executable mappings.
    #[must_use]
    pub const fn mappings(self) -> usize {
        self.mappings
    }
}

impl DirectFusedNativeExecutableOwner {
    /// Returns the exact verified fused artifact retained beside the mapping.
    #[must_use]
    pub const fn artifact(&self) -> &VerifiedDirectFusedSequenceObjectArtifact {
        &self.artifact
    }

    /// Returns the retained synchronized fused executable mapping.
    #[must_use]
    pub const fn executable(&self) -> &ReadyDirectFusedNativeExecutable {
        &self.executable
    }

    /// Executes one newly prepared whole-region call without remapping code.
    ///
    /// # Errors
    ///
    /// Returns exact preparation, binding, runner, or completion failure while
    /// retaining this reusable mapping.
    pub fn execute<Runner>(
        &self,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> DirectFusedNativeOwnerExecutionResult<Runner::Error>
    where
        Runner: DirectFusedNativeRunner,
    {
        use DirectFusedNativeOwnerExecutionFailure as Failure;

        let prepared =
            PreparedDirectFusedInvocation::new(&self.artifact, buffers)
                .map_err(|error| Box::new(Failure::Preparation(error)))?;
        execute_loaded_verified_direct_fused_native(
            runner,
            &self.executable,
            prepared,
        )
        .map_err(|error| Box::new(Failure::Execution(error)))
    }

    /// Returns the exact complete fused native key retained by this owner.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        self.executable.key()
    }

    /// Loads one reusable synchronized mapping from a verified fused artifact.
    ///
    /// # Errors
    ///
    /// Returns image or platform load failure without publishing a partial
    /// owner.
    pub fn load<Adapter>(
        adapter: &mut Adapter,
        artifact: &VerifiedDirectFusedSequenceObjectArtifact,
    ) -> DirectFusedNativeOwnerLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        use DirectFusedNativeOwnerLoadFailure as Failure;

        let image = VerifiedDirectFusedLoadImage::new(artifact)
            .map_err(|error| Box::new(Failure::Image(Box::new(error))))?;
        let executable =
            load_direct_fused_native_executable(adapter, &image)
                .map_err(|error| Box::new(Failure::Load(Box::new(error))))?;
        Ok(Self {
            artifact: artifact.clone(),
            executable,
        })
    }

    /// Returns the exact canonical fused region retained by this owner.
    #[must_use]
    pub const fn program(&self) -> &RegionEffectProgram {
        self.artifact.admission().program()
    }

    /// Releases the exact retained ready mapping.
    ///
    /// # Errors
    ///
    /// Returns retryable ready-executable ownership when platform release
    /// fails.
    pub fn release<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> DirectFusedNativeOwnerReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        release_direct_fused_native_executable(adapter, self.executable)
            .map_err(Box::new)
    }

    /// Returns exact synchronized mapping weight reported by the adapter.
    #[must_use]
    pub const fn resident_weight(&self) -> DirectFusedNativeResidentWeight {
        DirectFusedNativeResidentWeight {
            mapped_bytes: self.executable.mapping().mapped_len(),
            mappings: 1,
        }
    }
}
