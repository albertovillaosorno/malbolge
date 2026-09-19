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
//   - Reusable v6 executable ownership and exact terminal resident lease slots.
// - Must-Not:
//   - Project v6 authority into legacy/v5 types or release live leased
//     mappings.
// - Allows:
//   - Inputs: verified register-masked artifacts, exact programs, adapters,
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
//   - Reusable owners retain exact mappings; single-resident Arc leases are
//     immutable and block release while held.
// - Usage:
//   - Load reviewed owners directly or acquire their resident leases.
// - Defaults:
//   - Hits and lease clone/drop perform no executable-memory adapter
//     operations.
//

//! Reusable register-masked v6 executable ownership and exact lease reuse.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::sync::Arc;

use malbolge::{ProfileMachineObservation, RegisterMaskedRegionEffectProgram};

use super::direct::{
    VerifiedRegisterMaskedHaltFetchNativeObjectArtifact,
    VerifiedRegisterMaskedNoOperationNativeObjectArtifact,
    VerifiedRegisterMaskedNonGraphicalNativeObjectArtifact,
    VerifiedRegisterMaskedRotateNativeObjectArtifact,
};
use super::invocation::{
    NativeRegionBuffers, NativeRegionInvocationOutcome,
    PreparedRegisterMaskedHaltFetchInvocation,
    PreparedRegisterMaskedNoOperationInvocation,
    PreparedRegisterMaskedNonGraphicalInvocation,
    PreparedRegisterMaskedRotateInvocation,
    VerifiedRegisterMaskedInvocationError,
};
use super::lifecycle::{
    ReadyRegisterMaskedNativeExecutable,
    ReadyRegisterMaskedNoOperationNativeExecutable,
    ReadyRegisterMaskedNonGraphicalNativeExecutable,
    ReadyRegisterMaskedRotateNativeExecutable,
};
use super::loader::{
    VerifiedDirectLoadError, VerifiedRegisterMaskedLoadImage,
    VerifiedRegisterMaskedNoOperationLoadImage,
    VerifiedRegisterMaskedNonGraphicalLoadImage,
    VerifiedRegisterMaskedRotateLoadImage,
};
use super::platform::{
    NativeExecutableLoadFailure, NativeExecutableMemoryAdapter,
    RegisterMaskedNativeExecutableReleaseFailure,
    RegisterMaskedNoOperationNativeExecutableReleaseFailure,
    RegisterMaskedNonGraphicalNativeExecutableReleaseFailure,
    RegisterMaskedRotateNativeExecutableReleaseFailure,
    load_register_masked_native_executable,
    load_register_masked_no_operation_native_executable,
    load_register_masked_non_graphical_native_executable,
    load_register_masked_rotate_native_executable,
    release_register_masked_native_executable,
    release_register_masked_no_operation_native_executable,
    release_register_masked_non_graphical_native_executable,
    release_register_masked_rotate_native_executable,
};
use super::runner::{
    RegisterMaskedLoadedExecutionFailure, RegisterMaskedNativeRunner,
    RegisterMaskedNoOperationLoadedExecutionFailure,
    RegisterMaskedNoOperationNativeRunner,
    RegisterMaskedNonGraphicalLoadedExecutionFailure,
    RegisterMaskedNonGraphicalNativeRunner,
    RegisterMaskedRotateLoadedExecutionFailure,
    RegisterMaskedRotateNativeRunner,
    execute_loaded_verified_register_masked_native,
    execute_loaded_verified_register_masked_no_operation_native,
    execute_loaded_verified_register_masked_non_graphical_native,
    execute_loaded_verified_register_masked_rotate_native,
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

/// Failure while loading one reusable v6 no-operation mapping.
#[derive(Debug, Eq, PartialEq)]
pub enum RegisterMaskedNoOperationNativeOwnerLoadFailure<MemoryError> {
    /// Verified artifact identity differs from the requested v6 program.
    ArtifactIdentity,
    /// Exact v6 native identity could not be reconstructed.
    Identity(Box<NativeIdentityError>),
    /// Verified object could not become one relocation-free load image.
    Image(Box<VerifiedDirectLoadError>),
    /// Platform mapping/lifecycle admission failed.
    Load(Box<NativeExecutableLoadFailure<MemoryError>>),
}

/// Failure while executing through one retained v6 no-operation mapping.
#[derive(Debug, Eq, PartialEq)]
pub enum RegisterMaskedNoOperationNativeOwnerExecutionFailure<RunnerError> {
    /// Bound runner or completion admission failed.
    Execution(
        Box<RegisterMaskedNoOperationLoadedExecutionFailure<RunnerError>>,
    ),
    /// Rebased caller state failed exact v6 invocation preparation.
    Preparation(VerifiedRegisterMaskedInvocationError),
}

/// Failure while loading one reusable v6 rotate mapping.
#[derive(Debug, Eq, PartialEq)]
pub enum RegisterMaskedRotateNativeOwnerLoadFailure<MemoryError> {
    /// Verified artifact identity differs from the requested v6 program.
    ArtifactIdentity,
    /// Exact v6 native identity could not be reconstructed.
    Identity(Box<NativeIdentityError>),
    /// Verified object could not become one relocation-free load image.
    Image(Box<VerifiedDirectLoadError>),
    /// Platform mapping/lifecycle admission failed.
    Load(Box<NativeExecutableLoadFailure<MemoryError>>),
}

/// Failure while executing through one retained v6 rotate mapping.
#[derive(Debug, Eq, PartialEq)]
pub enum RegisterMaskedRotateNativeOwnerExecutionFailure<RunnerError> {
    /// Bound runner or completion admission failed.
    Execution(Box<RegisterMaskedRotateLoadedExecutionFailure<RunnerError>>),
    /// Rebased caller state failed exact v6 invocation preparation.
    Preparation(VerifiedRegisterMaskedInvocationError),
}

/// Failure while loading one reusable non-graphical v6 mapping.
#[derive(Debug, Eq, PartialEq)]
pub enum RegisterMaskedNonGraphicalNativeOwnerLoadFailure<MemoryError> {
    /// Verified artifact identity differs from the requested v6 program.
    ArtifactIdentity,
    /// Exact v6 native identity could not be reconstructed.
    Identity(Box<NativeIdentityError>),
    /// Verified object could not become one relocation-free load image.
    Image(Box<VerifiedDirectLoadError>),
    /// Platform mapping/lifecycle admission failed.
    Load(Box<NativeExecutableLoadFailure<MemoryError>>),
}

/// Failure while executing through one retained non-graphical v6 mapping.
#[derive(Debug, Eq, PartialEq)]
pub enum RegisterMaskedNonGraphicalNativeOwnerExecutionFailure<RunnerError> {
    /// Bound runner or completion admission failed.
    Execution(
        Box<RegisterMaskedNonGraphicalLoadedExecutionFailure<RunnerError>>,
    ),
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

/// One reusable verified v6 no-operation artifact beside its ready mapping.
#[derive(Debug)]
pub struct RegisterMaskedNoOperationNativeExecutableOwner {
    artifact: VerifiedRegisterMaskedNoOperationNativeObjectArtifact,
    executable: ReadyRegisterMaskedNoOperationNativeExecutable,
    program: RegisterMaskedRegionEffectProgram,
}

/// One reusable verified v6 rotate artifact beside its ready mapping.
#[derive(Debug)]
pub struct RegisterMaskedRotateNativeExecutableOwner {
    artifact: VerifiedRegisterMaskedRotateNativeObjectArtifact,
    executable: ReadyRegisterMaskedRotateNativeExecutable,
    program: RegisterMaskedRegionEffectProgram,
}

/// One reusable verified non-graphical v6 artifact beside its ready mapping.
#[derive(Debug)]
pub struct RegisterMaskedNonGraphicalNativeExecutableOwner {
    artifact: VerifiedRegisterMaskedNonGraphicalNativeObjectArtifact,
    executable: ReadyRegisterMaskedNonGraphicalNativeExecutable,
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

/// Result of loading one reusable v6 no-operation mapping.
pub type RegisterMaskedNoOperationNativeOwnerLoadResult<MemoryError> = Result<
    RegisterMaskedNoOperationNativeExecutableOwner,
    Box<RegisterMaskedNoOperationNativeOwnerLoadFailure<MemoryError>>,
>;

/// Result of one call through a reusable v6 no-operation mapping.
pub type RegisterMaskedNoOperationNativeOwnerExecutionResult<RunnerError> =
    Result<
        NativeRegionInvocationOutcome,
        Box<RegisterMaskedNoOperationNativeOwnerExecutionFailure<RunnerError>>,
    >;

/// Result of releasing one reusable v6 no-operation mapping.
pub type RegisterMaskedNoOperationNativeOwnerReleaseResult<MemoryError> =
    Result<
        (),
        Box<
            RegisterMaskedNoOperationNativeExecutableReleaseFailure<
                MemoryError,
            >,
        >,
    >;

/// Result of loading one reusable v6 rotate mapping.
pub type RegisterMaskedRotateNativeOwnerLoadResult<MemoryError> = Result<
    RegisterMaskedRotateNativeExecutableOwner,
    Box<RegisterMaskedRotateNativeOwnerLoadFailure<MemoryError>>,
>;

/// Result of one call through a reusable v6 rotate mapping.
pub type RegisterMaskedRotateNativeOwnerExecutionResult<RunnerError> = Result<
    NativeRegionInvocationOutcome,
    Box<RegisterMaskedRotateNativeOwnerExecutionFailure<RunnerError>>,
>;

/// Result of releasing one reusable v6 rotate mapping.
pub type RegisterMaskedRotateNativeOwnerReleaseResult<MemoryError> = Result<
    (),
    Box<RegisterMaskedRotateNativeExecutableReleaseFailure<MemoryError>>,
>;

/// Result of loading one reusable non-graphical v6 mapping.
pub type RegisterMaskedNonGraphicalNativeOwnerLoadResult<MemoryError> = Result<
    RegisterMaskedNonGraphicalNativeExecutableOwner,
    Box<RegisterMaskedNonGraphicalNativeOwnerLoadFailure<MemoryError>>,
>;

/// Result of one call through a reusable non-graphical v6 mapping.
pub type RegisterMaskedNonGraphicalNativeOwnerExecutionResult<RunnerError> =
    Result<
        NativeRegionInvocationOutcome,
        Box<RegisterMaskedNonGraphicalNativeOwnerExecutionFailure<RunnerError>>,
    >;

/// Result of releasing one reusable non-graphical v6 mapping.
pub type RegisterMaskedNonGraphicalNativeOwnerReleaseResult<MemoryError> =
    Result<
        (),
        Box<
            RegisterMaskedNonGraphicalNativeExecutableReleaseFailure<
                MemoryError,
            >,
        >,
    >;

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

/// Whether one no-operation lease acquisition loaded or reused the resident.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RegisterMaskedNoOperationNativeResidentCacheDisposition {
    /// The exact resident already existed and was leased without adapter work.
    Hit,
    /// The exact resident was loaded and published into the empty slot.
    Inserted,
}

/// Failure while acquiring one exact no-operation resident lease.
#[derive(Debug, Eq, PartialEq)]
pub enum RegisterMaskedNoOperationNativeResidentCacheAcquireFailure<MemoryError>
{
    /// A different exact no-operation identity already owns the slot.
    IdentityOccupied,
    /// Loading the requested resident owner failed.
    Load(Box<RegisterMaskedNoOperationNativeOwnerLoadFailure<MemoryError>>),
}

/// Explicit result of attempting to release the no-operation resident.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RegisterMaskedNoOperationNativeResidentCacheRelease {
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

/// One immutable external lease of the exact no-operation resident.
#[derive(Clone, Debug)]
pub struct RegisterMaskedNoOperationNativeResidentLease {
    resident: Arc<RegisterMaskedNoOperationNativeExecutableOwner>,
}

/// Lease plus whether the no-operation resident was inserted or reused.
#[derive(Debug)]
pub struct RegisterMaskedNoOperationNativeResidentCacheAcquisition {
    disposition: RegisterMaskedNoOperationNativeResidentCacheDisposition,
    lease: RegisterMaskedNoOperationNativeResidentLease,
}

/// Single exact resident slot for cloneable no-operation v6 leases.
#[derive(Debug, Default)]
pub struct RegisterMaskedNoOperationNativeResidentLeaseCache {
    resident: Option<Arc<RegisterMaskedNoOperationNativeExecutableOwner>>,
}

/// Result of acquiring one exact no-operation resident lease.
pub type RegisterMaskedNoOperationNativeResidentAcquireResult<MemoryError> =
    Result<
        RegisterMaskedNoOperationNativeResidentCacheAcquisition,
        Box<
            RegisterMaskedNoOperationNativeResidentCacheAcquireFailure<
                MemoryError,
            >,
        >,
    >;

/// Result of releasing the no-operation resident after leases are gone.
pub type RegisterMaskedNoOperationNativeResidentReleaseResult<MemoryError> =
    Result<
        RegisterMaskedNoOperationNativeResidentCacheRelease,
        Box<
            RegisterMaskedNoOperationNativeExecutableReleaseFailure<
                MemoryError,
            >,
        >,
    >;

/// Whether one non-graphical lease acquisition loaded or reused the resident.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RegisterMaskedNonGraphicalNativeResidentCacheDisposition {
    /// The exact resident already existed and was leased without adapter work.
    Hit,
    /// The exact resident was loaded and published into the empty slot.
    Inserted,
}

/// Failure while acquiring one exact non-graphical resident lease.
#[derive(Debug, Eq, PartialEq)]
pub enum RegisterMaskedNonGraphicalNativeResidentCacheAcquireFailure<
    MemoryError,
> {
    /// A different exact non-graphical identity already owns the slot.
    IdentityOccupied,
    /// Loading the requested resident owner failed.
    Load(Box<RegisterMaskedNonGraphicalNativeOwnerLoadFailure<MemoryError>>),
}

/// Explicit result of attempting to release the non-graphical resident.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RegisterMaskedNonGraphicalNativeResidentCacheRelease {
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

/// One immutable external lease of the exact non-graphical resident.
#[derive(Clone, Debug)]
pub struct RegisterMaskedNonGraphicalNativeResidentLease {
    resident: Arc<RegisterMaskedNonGraphicalNativeExecutableOwner>,
}

/// Lease plus whether the non-graphical resident was inserted or reused.
#[derive(Debug)]
pub struct RegisterMaskedNonGraphicalNativeResidentCacheAcquisition {
    disposition: RegisterMaskedNonGraphicalNativeResidentCacheDisposition,
    lease: RegisterMaskedNonGraphicalNativeResidentLease,
}

/// Single exact resident slot for cloneable non-graphical v6 leases.
#[derive(Debug, Default)]
pub struct RegisterMaskedNonGraphicalNativeResidentLeaseCache {
    resident: Option<Arc<RegisterMaskedNonGraphicalNativeExecutableOwner>>,
}

/// Result of acquiring one exact non-graphical resident lease.
pub type RegisterMaskedNonGraphicalNativeResidentCacheAcquireResult<
    MemoryError,
> = Result<
    RegisterMaskedNonGraphicalNativeResidentCacheAcquisition,
    Box<
        RegisterMaskedNonGraphicalNativeResidentCacheAcquireFailure<
            MemoryError,
        >,
    >,
>;

/// Result of releasing the non-graphical resident after leases are gone.
pub type RegisterMaskedNonGraphicalNativeResidentCacheReleaseResult<
    MemoryError,
> = Result<
    RegisterMaskedNonGraphicalNativeResidentCacheRelease,
    Box<RegisterMaskedNonGraphicalNativeExecutableReleaseFailure<MemoryError>>,
>;

type NoOperationCacheAcquireFailure<MemoryError> =
    RegisterMaskedNoOperationNativeResidentCacheAcquireFailure<MemoryError>;
type NoOperationCacheDisposition =
    RegisterMaskedNoOperationNativeResidentCacheDisposition;
type NonGraphicalCacheAcquireFailure<MemoryError> =
    RegisterMaskedNonGraphicalNativeResidentCacheAcquireFailure<MemoryError>;
type NonGraphicalCacheDisposition =
    RegisterMaskedNonGraphicalNativeResidentCacheDisposition;

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
    for RegisterMaskedNoOperationNativeOwnerLoadFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::ArtifactIdentity => f.write_str(
                "v6 no-operation resident artifact identity differs",
            ),
            Self::Identity(_error) => f.write_str(
                "v6 no-operation resident identity reconstruction failed",
            ),
            Self::Image(error) => Display::fmt(error, f),
            Self::Load(error) => {
                write!(f, "v6 no-operation resident load failed: {error}")
            },
        }
    }
}

impl<RunnerError: Display> Display
    for RegisterMaskedNoOperationNativeOwnerExecutionFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Preparation(error) => {
                write!(
                    f,
                    "v6 no-operation resident preparation failed: {error}"
                )
            },
            Self::Execution(error) => Display::fmt(error, f),
        }
    }
}

impl<MemoryError: Display> Display
    for RegisterMaskedRotateNativeOwnerLoadFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::ArtifactIdentity => {
                f.write_str("v6 rotate resident artifact identity differs")
            },
            Self::Identity(_error) => {
                f.write_str("v6 rotate resident identity reconstruction failed")
            },
            Self::Image(error) => Display::fmt(error, f),
            Self::Load(error) => {
                write!(f, "v6 rotate resident load failed: {error}")
            },
        }
    }
}

impl<RunnerError: Display> Display
    for RegisterMaskedRotateNativeOwnerExecutionFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Preparation(error) => {
                write!(f, "v6 rotate resident preparation failed: {error}")
            },
            Self::Execution(error) => Display::fmt(error, f),
        }
    }
}

impl<MemoryError: Display> Display
    for RegisterMaskedNonGraphicalNativeOwnerLoadFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::ArtifactIdentity => f.write_str(
                "non-graphical v6 resident artifact identity differs",
            ),
            Self::Identity(_error) => f.write_str(
                "non-graphical v6 resident identity reconstruction failed",
            ),
            Self::Image(error) => Display::fmt(error, f),
            Self::Load(error) => {
                write!(f, "non-graphical v6 resident load failed: {error}")
            },
        }
    }
}

impl<RunnerError> Display
    for RegisterMaskedNonGraphicalNativeOwnerExecutionFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Preparation(error) => {
                write!(
                    f,
                    "non-graphical v6 resident preparation failed: {error}"
                )
            },
            Self::Execution(_error) => {
                f.write_str("non-graphical v6 resident execution failed")
            },
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

impl<MemoryError: Display> Display
    for RegisterMaskedNoOperationNativeResidentCacheAcquireFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::IdentityOccupied => f.write_str(
                "different no-operation v6 identity already resident",
            ),
            Self::Load(error) => Display::fmt(error, f),
        }
    }
}

impl<MemoryError: Display> Display
    for RegisterMaskedNonGraphicalNativeResidentCacheAcquireFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::IdentityOccupied => f.write_str(
                "different non-graphical v6 identity already resident",
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

impl RegisterMaskedNoOperationNativeExecutableOwner {
    /// Returns the exact verified v6 no-operation artifact retained beside the
    /// mapping.
    #[must_use]
    pub const fn artifact(
        &self,
    ) -> &VerifiedRegisterMaskedNoOperationNativeObjectArtifact {
        &self.artifact
    }

    /// Returns the retained synchronized v6 no-operation executable mapping.
    #[must_use]
    pub const fn executable(
        &self,
    ) -> &ReadyRegisterMaskedNoOperationNativeExecutable {
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
    ) -> RegisterMaskedNoOperationNativeOwnerExecutionResult<Runner::Error>
    where
        Runner: RegisterMaskedNoOperationNativeRunner,
    {
        use RegisterMaskedNoOperationNativeOwnerExecutionFailure as Failure;

        let prepared = PreparedRegisterMaskedNoOperationInvocation::new(
            &self.artifact,
            &self.program,
            entry,
            buffers,
        )
        .map_err(|error| Box::new(Failure::Preparation(error)))?;
        execute_loaded_verified_register_masked_no_operation_native(
            runner,
            &self.executable,
            prepared,
        )
        .map_err(|error| Box::new(Failure::Execution(error)))
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
        artifact: &VerifiedRegisterMaskedNoOperationNativeObjectArtifact,
    ) -> RegisterMaskedNoOperationNativeOwnerLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        use RegisterMaskedNoOperationNativeOwnerLoadFailure as Failure;

        let expected_key = NativeArtifactKey::new_register_masked(
            program,
            artifact.key().target().clone(),
        )
        .map_err(|error| Box::new(Failure::Identity(Box::new(error))))?;
        if artifact.key() != &expected_key {
            return Err(Box::new(Failure::ArtifactIdentity));
        }
        let image =
            VerifiedRegisterMaskedNoOperationLoadImage::new(artifact)
                .map_err(|error| Box::new(Failure::Image(Box::new(error))))?;
        let executable = load_register_masked_no_operation_native_executable(
            adapter, &image,
        )
        .map_err(|error| Box::new(Failure::Load(Box::new(error))))?;
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
    ) -> RegisterMaskedNoOperationNativeOwnerReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        release_register_masked_no_operation_native_executable(
            adapter,
            self.executable,
        )
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

impl RegisterMaskedRotateNativeExecutableOwner {
    /// Returns the exact verified v6 rotate artifact retained beside the
    /// mapping.
    #[must_use]
    pub const fn artifact(
        &self,
    ) -> &VerifiedRegisterMaskedRotateNativeObjectArtifact {
        &self.artifact
    }

    /// Returns the retained synchronized v6 rotate executable mapping.
    #[must_use]
    pub const fn executable(
        &self,
    ) -> &ReadyRegisterMaskedRotateNativeExecutable {
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
    ) -> RegisterMaskedRotateNativeOwnerExecutionResult<Runner::Error>
    where
        Runner: RegisterMaskedRotateNativeRunner,
    {
        use RegisterMaskedRotateNativeOwnerExecutionFailure as Failure;

        let prepared = PreparedRegisterMaskedRotateInvocation::new(
            &self.artifact,
            &self.program,
            entry,
            buffers,
        )
        .map_err(|error| Box::new(Failure::Preparation(error)))?;
        execute_loaded_verified_register_masked_rotate_native(
            runner,
            &self.executable,
            prepared,
        )
        .map_err(|error| Box::new(Failure::Execution(error)))
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
        artifact: &VerifiedRegisterMaskedRotateNativeObjectArtifact,
    ) -> RegisterMaskedRotateNativeOwnerLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        use RegisterMaskedRotateNativeOwnerLoadFailure as Failure;

        let expected_key = NativeArtifactKey::new_register_masked(
            program,
            artifact.key().target().clone(),
        )
        .map_err(|error| Box::new(Failure::Identity(Box::new(error))))?;
        if artifact.key() != &expected_key {
            return Err(Box::new(Failure::ArtifactIdentity));
        }
        let image = VerifiedRegisterMaskedRotateLoadImage::new(artifact)
            .map_err(|error| Box::new(Failure::Image(Box::new(error))))?;
        let executable =
            load_register_masked_rotate_native_executable(adapter, &image)
                .map_err(|error| Box::new(Failure::Load(Box::new(error))))?;
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
    ) -> RegisterMaskedRotateNativeOwnerReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        release_register_masked_rotate_native_executable(
            adapter,
            self.executable,
        )
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

impl RegisterMaskedNonGraphicalNativeExecutableOwner {
    /// Returns the exact verified non-graphical v6 artifact retained beside the
    /// mapping.
    #[must_use]
    pub const fn artifact(
        &self,
    ) -> &VerifiedRegisterMaskedNonGraphicalNativeObjectArtifact {
        &self.artifact
    }

    /// Returns the retained synchronized non-graphical v6 executable mapping.
    #[must_use]
    pub const fn executable(
        &self,
    ) -> &ReadyRegisterMaskedNonGraphicalNativeExecutable {
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
    ) -> RegisterMaskedNonGraphicalNativeOwnerExecutionResult<Runner::Error>
    where
        Runner: RegisterMaskedNonGraphicalNativeRunner,
    {
        use RegisterMaskedNonGraphicalNativeOwnerExecutionFailure as Failure;

        let prepared = PreparedRegisterMaskedNonGraphicalInvocation::new(
            &self.artifact,
            &self.program,
            entry,
            buffers,
        )
        .map_err(|error| Box::new(Failure::Preparation(error)))?;
        execute_loaded_verified_register_masked_non_graphical_native(
            runner,
            &self.executable,
            prepared,
        )
        .map_err(|error| Box::new(Failure::Execution(error)))
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
        artifact: &VerifiedRegisterMaskedNonGraphicalNativeObjectArtifact,
    ) -> RegisterMaskedNonGraphicalNativeOwnerLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        use RegisterMaskedNonGraphicalNativeOwnerLoadFailure as Failure;

        let expected_key = NativeArtifactKey::new_register_masked(
            program,
            artifact.key().target().clone(),
        )
        .map_err(|error| Box::new(Failure::Identity(Box::new(error))))?;
        if artifact.key() != &expected_key {
            return Err(Box::new(Failure::ArtifactIdentity));
        }
        let image = VerifiedRegisterMaskedNonGraphicalLoadImage::new(artifact)
            .map_err(|error| Box::new(Failure::Image(Box::new(error))))?;
        let executable = load_register_masked_non_graphical_native_executable(
            adapter, &image,
        )
        .map_err(|error| Box::new(Failure::Load(Box::new(error))))?;
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
    ) -> RegisterMaskedNonGraphicalNativeOwnerReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        release_register_masked_non_graphical_native_executable(
            adapter,
            self.executable,
        )
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
impl RegisterMaskedNoOperationNativeResidentCacheAcquisition {
    /// Returns whether this acquisition loaded or reused the resident mapping.
    #[must_use]
    pub const fn disposition(
        &self,
    ) -> RegisterMaskedNoOperationNativeResidentCacheDisposition {
        self.disposition
    }

    /// Consumes this acquisition and returns its immutable external lease.
    #[must_use]
    pub fn into_lease(self) -> RegisterMaskedNoOperationNativeResidentLease {
        self.lease
    }

    /// Returns the immutable lease retained by this acquisition.
    #[must_use]
    pub const fn lease(&self) -> &RegisterMaskedNoOperationNativeResidentLease {
        &self.lease
    }
}

impl RegisterMaskedNoOperationNativeResidentLease {
    /// Executes through the resident no-operation mapping without adapter work.
    ///
    /// # Errors
    ///
    /// Returns exact preparation, runner, binding, or completion failure.
    pub fn execute<Runner>(
        &self,
        runner: &mut Runner,
        entry: ProfileMachineObservation,
        buffers: NativeRegionBuffers<'_>,
    ) -> RegisterMaskedNoOperationNativeOwnerExecutionResult<Runner::Error>
    where
        Runner: RegisterMaskedNoOperationNativeRunner,
    {
        self.resident.execute(runner, entry, buffers)
    }

    /// Returns the exact resident no-operation v6 native key.
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

impl RegisterMaskedNoOperationNativeResidentLeaseCache {
    /// Loads or reuses one exact no-operation v6 resident as an immutable
    /// lease.
    ///
    /// A different identity cannot replace the resident through this
    /// single-slot boundary; release the old resident explicitly first.
    ///
    /// # Errors
    ///
    /// Returns identity occupancy or exact owner-loading failure.
    pub fn ensure<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        program: &RegisterMaskedRegionEffectProgram,
        artifact: &VerifiedRegisterMaskedNoOperationNativeObjectArtifact,
    ) -> RegisterMaskedNoOperationNativeResidentAcquireResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        if let Some(resident) = &self.resident {
            if resident.program() != program || resident.artifact() != artifact
            {
                return Err(Box::new(
                    NoOperationCacheAcquireFailure::IdentityOccupied,
                ));
            }
            return Ok(
                RegisterMaskedNoOperationNativeResidentCacheAcquisition {
                    disposition: NoOperationCacheDisposition::Hit,
                    lease: RegisterMaskedNoOperationNativeResidentLease {
                        resident: Arc::clone(resident),
                    },
                },
            );
        }
        let loaded = RegisterMaskedNoOperationNativeExecutableOwner::load(
            adapter, program, artifact,
        )
        .map_err(|error| {
            Box::new(NoOperationCacheAcquireFailure::Load(error))
        })?;
        let resident = Arc::new(loaded);
        let lease = RegisterMaskedNoOperationNativeResidentLease {
            resident: Arc::clone(&resident),
        };
        self.resident = Some(resident);
        Ok(RegisterMaskedNoOperationNativeResidentCacheAcquisition {
            disposition: NoOperationCacheDisposition::Inserted,
            lease,
        })
    }

    /// Reports whether one exact no-operation mapping is currently resident.
    #[must_use]
    pub const fn has_resident(&self) -> bool {
        self.resident.is_some()
    }

    /// Constructs one empty single-resident no-operation lease cache.
    #[must_use]
    pub const fn new() -> Self {
        Self { resident: None }
    }

    /// Releases the resident only when no external lease remains.
    ///
    /// Live leases block adapter release. Cleanup failure empties the cache and
    /// transfers exact ready-executable retry ownership through the failure.
    ///
    /// # Errors
    ///
    /// Returns exact no-operation cleanup retry ownership on release failure.
    pub fn release_if_unleased<Adapter>(
        &mut self,
        adapter: &mut Adapter,
    ) -> RegisterMaskedNoOperationNativeResidentReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        use RegisterMaskedNoOperationNativeResidentCacheRelease as Release;

        let Some(resident) = self.resident.take() else {
            return Ok(Release::Missing);
        };
        let leases = Arc::strong_count(&resident).saturating_sub(1);
        if leases > 0 {
            self.resident = Some(resident);
            return Ok(Release::Leased { leases });
        }
        match Arc::try_unwrap(resident) {
            Ok(owner) => owner.release(adapter).map(|()| Release::Released),
            Err(retained) => {
                let remaining_leases =
                    Arc::strong_count(&retained).saturating_sub(1);
                self.resident = Some(retained);
                Ok(Release::Leased { leases: remaining_leases })
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

impl RegisterMaskedNonGraphicalNativeResidentCacheAcquisition {
    /// Returns whether this acquisition loaded or reused the resident mapping.
    #[must_use]
    pub const fn disposition(
        &self,
    ) -> RegisterMaskedNonGraphicalNativeResidentCacheDisposition {
        self.disposition
    }

    /// Consumes this acquisition and returns its immutable external lease.
    #[must_use]
    pub fn into_lease(self) -> RegisterMaskedNonGraphicalNativeResidentLease {
        self.lease
    }

    /// Returns the immutable lease retained by this acquisition.
    #[must_use]
    pub const fn lease(
        &self,
    ) -> &RegisterMaskedNonGraphicalNativeResidentLease {
        &self.lease
    }
}

impl RegisterMaskedNonGraphicalNativeResidentLease {
    /// Executes through the resident non-graphical mapping without adapter
    /// work.
    ///
    /// # Errors
    ///
    /// Returns exact preparation, runner, binding, or completion failure.
    pub fn execute<Runner>(
        &self,
        runner: &mut Runner,
        entry: ProfileMachineObservation,
        buffers: NativeRegionBuffers<'_>,
    ) -> RegisterMaskedNonGraphicalNativeOwnerExecutionResult<Runner::Error>
    where
        Runner: RegisterMaskedNonGraphicalNativeRunner,
    {
        self.resident.execute(runner, entry, buffers)
    }

    /// Returns the exact resident non-graphical v6 native key.
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

impl RegisterMaskedNonGraphicalNativeResidentLeaseCache {
    /// Loads or reuses one exact non-graphical v6 resident as an immutable
    /// lease.
    ///
    /// A different identity cannot replace the resident through this
    /// single-slot boundary; release the old resident explicitly first.
    ///
    /// # Errors
    ///
    /// Returns identity occupancy or exact owner-loading failure.
    pub fn ensure<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        program: &RegisterMaskedRegionEffectProgram,
        artifact: &VerifiedRegisterMaskedNonGraphicalNativeObjectArtifact,
    ) -> RegisterMaskedNonGraphicalNativeResidentCacheAcquireResult<
        Adapter::Error,
    >
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        if let Some(resident) = &self.resident {
            if resident.program() != program || resident.artifact() != artifact
            {
                return Err(Box::new(
                    NonGraphicalCacheAcquireFailure::IdentityOccupied,
                ));
            }
            return Ok(
                RegisterMaskedNonGraphicalNativeResidentCacheAcquisition {
                    disposition: NonGraphicalCacheDisposition::Hit,
                    lease: RegisterMaskedNonGraphicalNativeResidentLease {
                        resident: Arc::clone(resident),
                    },
                },
            );
        }
        let loaded = RegisterMaskedNonGraphicalNativeExecutableOwner::load(
            adapter, program, artifact,
        )
        .map_err(|error| {
            Box::new(NonGraphicalCacheAcquireFailure::Load(error))
        })?;
        let resident = Arc::new(loaded);
        let lease = RegisterMaskedNonGraphicalNativeResidentLease {
            resident: Arc::clone(&resident),
        };
        self.resident = Some(resident);
        Ok(RegisterMaskedNonGraphicalNativeResidentCacheAcquisition {
            disposition: NonGraphicalCacheDisposition::Inserted,
            lease,
        })
    }

    /// Reports whether one exact non-graphical mapping is currently resident.
    #[must_use]
    pub const fn has_resident(&self) -> bool {
        self.resident.is_some()
    }

    /// Constructs one empty single-resident non-graphical lease cache.
    #[must_use]
    pub const fn new() -> Self {
        Self { resident: None }
    }

    /// Releases the resident only when no external lease remains.
    ///
    /// Live leases block adapter release. Cleanup failure empties the cache and
    /// transfers exact ready-executable retry ownership through the failure.
    ///
    /// # Errors
    ///
    /// Returns exact non-graphical cleanup retry ownership on release failure.
    pub fn release_if_unleased<Adapter>(
        &mut self,
        adapter: &mut Adapter,
    ) -> RegisterMaskedNonGraphicalNativeResidentCacheReleaseResult<
        Adapter::Error,
    >
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        use RegisterMaskedNonGraphicalNativeResidentCacheRelease as Release;

        let Some(resident) = self.resident.take() else {
            return Ok(Release::Missing);
        };
        let leases = Arc::strong_count(&resident).saturating_sub(1);
        if leases > 0 {
            self.resident = Some(resident);
            return Ok(Release::Leased { leases });
        }
        match Arc::try_unwrap(resident) {
            Ok(owner) => owner.release(adapter).map(|()| Release::Released),
            Err(retained) => {
                let remaining_leases =
                    Arc::strong_count(&retained).saturating_sub(1);
                self.resident = Some(retained);
                Ok(Release::Leased { leases: remaining_leases })
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
