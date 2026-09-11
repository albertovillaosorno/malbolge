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
//   - Reusable v6 executable ownership and one exact resident lease slot.
// - Must-Not:
//   - Project v6 authority into legacy/v5 types or release live leased
//     mappings.
// - Allows:
//   - Inputs: verified register-masked halt artifacts, exact programs,
//     adapters,
//   - runners, rebased observations, and caller buffers.
//   - Outputs: reusable owners, cloneable leases, exact weight, and retryable
//   - cleanup ownership.
//   - Side effects: executable load/release only through the supplied adapter.
// - Split-When:
//   - Durable/cross-process ownership or a general v6 executable store gains
//     independent lifecycle policy.
// - Merge-When:
//   - One general mask-aware executable store subsumes single-resident reuse.
// - Summary:
//   - Reuses one exact v6 mapping without weakening mask-aware identity.
// - Description:
//   - Arc leases are immutable and prevent release while externally retained.
// - Usage:
//   - Load an owner directly or acquire one exact resident lease from the
//     cache.
// - Defaults:
//   - Hits and lease clone/drop perform no executable-memory adapter
//     operations.
//

//! Reusable register-masked v6 executable ownership and exact lease reuse.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::sync::Arc;

use malbolge::{ProfileMachineObservation, RegisterMaskedRegionEffectProgram};

use super::direct::VerifiedRegisterMaskedHaltFetchNativeObjectArtifact;
use super::invocation::{
    NativeRegionBuffers, NativeRegionInvocationOutcome,
    PreparedRegisterMaskedHaltFetchInvocation,
    VerifiedRegisterMaskedInvocationError,
};
use super::lifecycle::ReadyRegisterMaskedNativeExecutable;
use super::loader::{VerifiedDirectLoadError, VerifiedRegisterMaskedLoadImage};
use super::platform::{
    NativeExecutableLoadFailure, NativeExecutableMemoryAdapter,
    RegisterMaskedNativeExecutableReleaseFailure,
    load_register_masked_native_executable,
    release_register_masked_native_executable,
};
use super::runner::{
    RegisterMaskedLoadedExecutionFailure, RegisterMaskedNativeRunner,
    execute_loaded_verified_register_masked_native,
};
use crate::execution_cache::{NativeArtifactKey, NativeIdentityError};

/// Failure while loading one reusable exact register-masked v6 mapping.
#[derive(Debug, Eq, PartialEq)]
pub enum RegisterMaskedNativeOwnerLoadFailure<MemoryError> {
    /// Verified artifact identity differs from the requested v6 program.
    ArtifactIdentity,
    /// Exact v6 native identity could not be reconstructed.
    Identity(Box<NativeIdentityError>),
    /// Verified object could not become one relocation-free load image.
    Image(Box<VerifiedDirectLoadError>),
    /// Platform mapping/lifecycle admission failed.
    Load(Box<NativeExecutableLoadFailure<MemoryError>>),
}

/// Failure while executing through one retained register-masked mapping.
#[derive(Debug, Eq, PartialEq)]
pub enum RegisterMaskedNativeOwnerExecutionFailure<RunnerError> {
    /// Bound runner or completion admission failed.
    Execution(Box<RegisterMaskedLoadedExecutionFailure<RunnerError>>),
    /// Rebased caller state failed exact v6 invocation preparation.
    Preparation(VerifiedRegisterMaskedInvocationError),
}

/// Exact synchronized mapping weight retained by one v6 owner.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RegisterMaskedNativeResidentWeight {
    mapped_bytes: usize,
    mappings: usize,
}

/// One reusable verified register-masked artifact beside its ready mapping.
#[derive(Debug)]
pub struct RegisterMaskedNativeExecutableOwner {
    artifact: VerifiedRegisterMaskedHaltFetchNativeObjectArtifact,
    executable: ReadyRegisterMaskedNativeExecutable,
    program: RegisterMaskedRegionEffectProgram,
}

/// Result of loading one reusable exact register-masked mapping.
pub type RegisterMaskedNativeOwnerLoadResult<MemoryError> = Result<
    RegisterMaskedNativeExecutableOwner,
    Box<RegisterMaskedNativeOwnerLoadFailure<MemoryError>>,
>;

/// Result of one call through a reusable register-masked mapping.
pub type RegisterMaskedNativeOwnerExecutionResult<RunnerError> = Result<
    NativeRegionInvocationOutcome,
    Box<RegisterMaskedNativeOwnerExecutionFailure<RunnerError>>,
>;

/// Result of releasing one reusable register-masked mapping.
pub type RegisterMaskedNativeOwnerReleaseResult<MemoryError> =
    Result<(), Box<RegisterMaskedNativeExecutableReleaseFailure<MemoryError>>>;

/// Whether one lease acquisition loaded or reused the exact resident mapping.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RegisterMaskedNativeResidentCacheDisposition {
    /// The exact resident mapping already existed and was leased without I/O.
    Hit,
    /// The exact mapping was loaded and published into the empty resident slot.
    Inserted,
}

/// Failure while acquiring one exact register-masked resident lease.
#[derive(Debug, Eq, PartialEq)]
pub enum RegisterMaskedNativeResidentCacheAcquireFailure<MemoryError> {
    /// A different exact v6 identity already owns the single resident slot.
    IdentityOccupied,
    /// Loading the requested exact resident failed.
    Load(Box<RegisterMaskedNativeOwnerLoadFailure<MemoryError>>),
}

/// Explicit result of attempting to release the single v6 resident.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RegisterMaskedNativeResidentCacheRelease {
    /// External leases still retain the resident mapping.
    Leased {
        /// Number of external lease owners blocking release.
        leases: usize,
    },
    /// No resident mapping exists.
    Missing,
    /// The unleased resident mapping released successfully.
    Released,
}

/// One immutable external lease of the exact register-masked resident.
#[derive(Clone, Debug)]
pub struct RegisterMaskedNativeResidentLease {
    resident: Arc<RegisterMaskedNativeExecutableOwner>,
}

/// Lease plus whether the resident mapping was inserted or reused.
#[derive(Debug)]
pub struct RegisterMaskedNativeResidentCacheAcquisition {
    disposition: RegisterMaskedNativeResidentCacheDisposition,
    lease: RegisterMaskedNativeResidentLease,
}

/// Single exact resident slot for cloneable register-masked v6 leases.
#[derive(Debug, Default)]
pub struct RegisterMaskedNativeResidentLeaseCache {
    resident: Option<Arc<RegisterMaskedNativeExecutableOwner>>,
}

/// Result of acquiring one exact register-masked resident lease.
pub type RegisterMaskedNativeResidentCacheAcquireResult<MemoryError> = Result<
    RegisterMaskedNativeResidentCacheAcquisition,
    Box<RegisterMaskedNativeResidentCacheAcquireFailure<MemoryError>>,
>;

/// Result of releasing the resident after all external leases are gone.
pub type RegisterMaskedNativeResidentCacheReleaseResult<MemoryError> = Result<
    RegisterMaskedNativeResidentCacheRelease,
    Box<RegisterMaskedNativeExecutableReleaseFailure<MemoryError>>,
>;

impl<MemoryError: Display> Display
    for RegisterMaskedNativeOwnerLoadFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::ArtifactIdentity => f.write_str(
                "register-masked resident artifact identity differs",
            ),
            Self::Identity(_error) => f.write_str(
                "register-masked resident identity reconstruction failed",
            ),
            Self::Image(error) => Display::fmt(error, f),
            Self::Load(error) => {
                write!(f, "register-masked resident load failed: {error}")
            },
        }
    }
}

impl<RunnerError: Display> Display
    for RegisterMaskedNativeOwnerExecutionFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Preparation(error) => {
                write!(
                    f,
                    "register-masked resident preparation failed: {error}"
                )
            },
            Self::Execution(error) => Display::fmt(error, f),
        }
    }
}

impl<MemoryError: Display> Display
    for RegisterMaskedNativeResidentCacheAcquireFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::IdentityOccupied => f.write_str(
                "different register-masked identity already resident",
            ),
            Self::Load(error) => Display::fmt(error, f),
        }
    }
}

impl RegisterMaskedNativeResidentWeight {
    /// Returns exact synchronized mapped bytes retained by this owner.
    #[must_use]
    pub const fn mapped_bytes(self) -> usize {
        self.mapped_bytes
    }

    /// Returns the exact number of live executable mappings.
    #[must_use]
    pub const fn mappings(self) -> usize {
        self.mappings
    }
}

impl RegisterMaskedNativeExecutableOwner {
    /// Returns the exact verified v6 artifact retained beside the mapping.
    #[must_use]
    pub const fn artifact(
        &self,
    ) -> &VerifiedRegisterMaskedHaltFetchNativeObjectArtifact {
        &self.artifact
    }

    /// Returns the retained synchronized register-masked executable mapping.
    #[must_use]
    pub const fn executable(&self) -> &ReadyRegisterMaskedNativeExecutable {
        &self.executable
    }

    /// Executes one newly rebased caller observation without remapping code.
    ///
    /// # Errors
    ///
    /// Returns exact preparation, binding, runner, or completion failure while
    /// retaining this reusable mapping.
    pub fn execute<Runner>(
        &self,
        runner: &mut Runner,
        entry: ProfileMachineObservation,
        buffers: NativeRegionBuffers<'_>,
    ) -> RegisterMaskedNativeOwnerExecutionResult<Runner::Error>
    where
        Runner: RegisterMaskedNativeRunner,
    {
        let prepared = PreparedRegisterMaskedHaltFetchInvocation::new(
            &self.artifact,
            &self.program,
            entry,
            buffers,
        )
        .map_err(|error| {
            Box::new(RegisterMaskedNativeOwnerExecutionFailure::Preparation(
                error,
            ))
        })?;
        execute_loaded_verified_register_masked_native(
            runner,
            &self.executable,
            prepared,
        )
        .map_err(|error| {
            Box::new(RegisterMaskedNativeOwnerExecutionFailure::Execution(
                error,
            ))
        })
    }

    /// Returns the exact complete v6 native key retained by this owner.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        self.executable.key()
    }

    /// Loads one reusable synchronized mapping after exact program/key
    /// admission.
    ///
    /// # Errors
    ///
    /// Returns identity, image, or platform load failure without publishing a
    /// partial owner.
    pub fn load<Adapter>(
        adapter: &mut Adapter,
        program: &RegisterMaskedRegionEffectProgram,
        artifact: &VerifiedRegisterMaskedHaltFetchNativeObjectArtifact,
    ) -> RegisterMaskedNativeOwnerLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let expected_key = NativeArtifactKey::new_register_masked(
            program,
            artifact.key().target().clone(),
        )
        .map_err(|error| {
            Box::new(RegisterMaskedNativeOwnerLoadFailure::Identity(Box::new(
                error,
            )))
        })?;
        if artifact.key() != &expected_key {
            return Err(Box::new(
                RegisterMaskedNativeOwnerLoadFailure::ArtifactIdentity,
            ));
        }
        let image = VerifiedRegisterMaskedLoadImage::new(artifact).map_err(
            |error| {
                Box::new(RegisterMaskedNativeOwnerLoadFailure::Image(Box::new(
                    error,
                )))
            },
        )?;
        let executable = load_register_masked_native_executable(
            adapter, &image,
        )
        .map_err(|error| {
            Box::new(RegisterMaskedNativeOwnerLoadFailure::Load(Box::new(
                error,
            )))
        })?;
        Ok(Self {
            artifact: artifact.clone(),
            executable,
            program: program.clone(),
        })
    }

    /// Returns the exact register-masked program retained by this owner.
    #[must_use]
    pub const fn program(&self) -> &RegisterMaskedRegionEffectProgram {
        &self.program
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
    ) -> RegisterMaskedNativeOwnerReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        release_register_masked_native_executable(adapter, self.executable)
            .map_err(Box::new)
    }

    /// Returns exact synchronized mapping weight reported by the adapter.
    #[must_use]
    pub const fn resident_weight(&self) -> RegisterMaskedNativeResidentWeight {
        RegisterMaskedNativeResidentWeight {
            mapped_bytes: self.executable.mapping().mapped_len(),
            mappings: 1,
        }
    }
}

impl RegisterMaskedNativeResidentCacheAcquisition {
    /// Returns whether this acquisition loaded or reused the resident mapping.
    #[must_use]
    pub const fn disposition(
        &self,
    ) -> RegisterMaskedNativeResidentCacheDisposition {
        self.disposition
    }

    /// Consumes this acquisition and returns its immutable external lease.
    #[must_use]
    pub fn into_lease(self) -> RegisterMaskedNativeResidentLease {
        self.lease
    }

    /// Returns the immutable lease retained by this acquisition.
    #[must_use]
    pub const fn lease(&self) -> &RegisterMaskedNativeResidentLease {
        &self.lease
    }
}

impl RegisterMaskedNativeResidentLease {
    /// Executes through the resident exact v6 mapping without adapter work.
    ///
    /// # Errors
    ///
    /// Returns exact v6 preparation, runner, or completion failure.
    pub fn execute<Runner>(
        &self,
        runner: &mut Runner,
        entry: ProfileMachineObservation,
        buffers: NativeRegionBuffers<'_>,
    ) -> RegisterMaskedNativeOwnerExecutionResult<Runner::Error>
    where
        Runner: RegisterMaskedNativeRunner,
    {
        self.resident.execute(runner, entry, buffers)
    }

    /// Returns the exact resident v6 native key.
    #[must_use]
    pub fn key(&self) -> &NativeArtifactKey {
        self.resident.key()
    }

    /// Returns exact synchronized weight reported by the resident owner.
    #[must_use]
    pub fn resident_weight(&self) -> RegisterMaskedNativeResidentWeight {
        self.resident.resident_weight()
    }

    /// Reports whether two leases share the same resident owner allocation.
    #[must_use]
    pub fn shares_resident_with(&self, other: &Self) -> bool {
        Arc::ptr_eq(&self.resident, &other.resident)
    }

    /// Returns all strong owners, including the cache resident owner.
    #[must_use]
    pub fn strong_owner_count(&self) -> usize {
        Arc::strong_count(&self.resident)
    }
}

impl RegisterMaskedNativeResidentLeaseCache {
    /// Loads or reuses one exact v6 resident as an immutable lease.
    ///
    /// A different identity cannot replace the resident through this minimal
    /// boundary; release the old resident explicitly first.
    ///
    /// # Errors
    ///
    /// Returns identity occupancy or exact owner-loading failure.
    pub fn ensure<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        program: &RegisterMaskedRegionEffectProgram,
        artifact: &VerifiedRegisterMaskedHaltFetchNativeObjectArtifact,
    ) -> RegisterMaskedNativeResidentCacheAcquireResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        if let Some(resident) = &self.resident {
            if resident.program() != program || resident.artifact() != artifact
            {
                use RegisterMaskedNativeResidentCacheAcquireFailure as Failure;
                return Err(Box::new(Failure::IdentityOccupied));
            }
            return Ok(RegisterMaskedNativeResidentCacheAcquisition {
                disposition: RegisterMaskedNativeResidentCacheDisposition::Hit,
                lease: RegisterMaskedNativeResidentLease {
                    resident: Arc::clone(resident),
                },
            });
        }
        let loaded = RegisterMaskedNativeExecutableOwner::load(
            adapter, program, artifact,
        )
        .map_err(|error| {
            Box::new(RegisterMaskedNativeResidentCacheAcquireFailure::Load(
                error,
            ))
        })?;
        let resident = Arc::new(loaded);
        let lease = RegisterMaskedNativeResidentLease {
            resident: Arc::clone(&resident),
        };
        self.resident = Some(resident);
        Ok(RegisterMaskedNativeResidentCacheAcquisition {
            disposition: RegisterMaskedNativeResidentCacheDisposition::Inserted,
            lease,
        })
    }

    /// Reports whether one exact register-masked mapping is currently resident.
    #[must_use]
    pub const fn has_resident(&self) -> bool {
        self.resident.is_some()
    }

    /// Constructs one empty single-resident register-masked lease cache.
    #[must_use]
    pub const fn new() -> Self {
        Self { resident: None }
    }

    /// Releases the resident mapping only when no external lease remains.
    ///
    /// A live lease returns
    /// [`RegisterMaskedNativeResidentCacheRelease::Leased`] without adapter
    /// work. Cleanup failure empties the cache and transfers
    /// exact ready-executable retry ownership through the returned failure.
    ///
    /// # Errors
    ///
    /// Returns exact register-masked cleanup retry ownership on release
    /// failure.
    pub fn release_if_unleased<Adapter>(
        &mut self,
        adapter: &mut Adapter,
    ) -> RegisterMaskedNativeResidentCacheReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let Some(resident) = self.resident.take() else {
            return Ok(RegisterMaskedNativeResidentCacheRelease::Missing);
        };
        let leases = Arc::strong_count(&resident).saturating_sub(1);
        if leases > 0 {
            self.resident = Some(resident);
            return Ok(RegisterMaskedNativeResidentCacheRelease::Leased {
                leases,
            });
        }
        match Arc::try_unwrap(resident) {
            Ok(owner) => owner
                .release(adapter)
                .map(|()| RegisterMaskedNativeResidentCacheRelease::Released),
            Err(retained) => {
                let remaining_leases =
                    Arc::strong_count(&retained).saturating_sub(1);
                self.resident = Some(retained);
                Ok(RegisterMaskedNativeResidentCacheRelease::Leased {
                    leases: remaining_leases,
                })
            },
        }
    }

    /// Returns the number of external leases retaining the resident mapping.
    #[must_use]
    pub fn resident_lease_count(&self) -> usize {
        self.resident
            .as_ref()
            .map_or(0, |resident| Arc::strong_count(resident).saturating_sub(1))
    }
}
