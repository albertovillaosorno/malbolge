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
//   - Safe orchestration of caller-owned executable-memory platform adapters.
// - Must-Not:
//   - Implement operating-system memory calls or invoke machine code.
// - Allows:
//   - Inputs: verified load images and one explicit platform adapter.
//   - Outputs: ready executables or phase-tagged failures with cleanup
//     evidence.
//   - Side effects: only those explicitly performed by the supplied adapter.
// - Split-When:
//   - Concrete Windows or POSIX executable-memory implementations are added.
// - Merge-When:
//   - One platform adapter owns both operations and safe orchestration.
// - Summary:
//   - Runs allocate, copy, protect, synchronize, and release transactionally.
// - Description:
//   - Attempts exact release after every post-allocation failure.
// - Usage:
//   - Implement the port outside this safe core, then load one verified image.
// - Defaults:
//   - Primary failure is retained together with any cleanup failure.
//

//! Safe executable-memory adapter port and transactional loader orchestration.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::num::NonZeroUsize;

use super::lifecycle::{
    NativeExecutableLifecycleError, NativeExecutableMappingId,
    NativeExecutableMappingReport, NativeExecutableReleaseRequest,
    NativeInstructionSyncReport, ReadyDirectFusedNativeExecutable,
    ReadyExecutionGeometryNativeExecutable, ReadyNativeExecutable,
    ReadyRegisterMaskedCrazyNativeExecutable,
    ReadyRegisterMaskedNativeExecutable,
    ReadyRegisterMaskedNoOperationHaltNativeExecutable,
    ReadyRegisterMaskedNoOperationNativeExecutable,
    ReadyRegisterMaskedNoOperationPairNativeExecutable,
    ReadyRegisterMaskedNonGraphicalNativeExecutable,
    ReadyRegisterMaskedOutputNativeExecutable,
    ReadyRegisterMaskedRotateNativeExecutable,
    SealedDirectFusedNativeExecutable, SealedExecutionGeometryNativeExecutable,
    SealedNativeExecutable, SealedRegisterMaskedCrazyNativeExecutable,
    SealedRegisterMaskedNativeExecutable,
    SealedRegisterMaskedNoOperationHaltNativeExecutable,
    SealedRegisterMaskedNoOperationNativeExecutable,
    SealedRegisterMaskedNoOperationPairNativeExecutable,
    SealedRegisterMaskedNonGraphicalNativeExecutable,
    SealedRegisterMaskedOutputNativeExecutable,
    SealedRegisterMaskedRotateNativeExecutable,
    StagedDirectFusedNativeExecutable, StagedExecutionGeometryNativeExecutable,
    StagedNativeExecutable, StagedRegisterMaskedCrazyNativeExecutable,
    StagedRegisterMaskedNativeExecutable,
    StagedRegisterMaskedNoOperationHaltNativeExecutable,
    StagedRegisterMaskedNoOperationNativeExecutable,
    StagedRegisterMaskedNoOperationPairNativeExecutable,
    StagedRegisterMaskedNonGraphicalNativeExecutable,
    StagedRegisterMaskedOutputNativeExecutable,
    StagedRegisterMaskedRotateNativeExecutable,
    validate_direct_fused_writable_mapping,
    validate_execution_geometry_writable_mapping,
    validate_register_masked_crazy_writable_mapping,
    validate_register_masked_no_operation_halt_writable_mapping,
    validate_register_masked_no_operation_pair_writable_mapping,
    validate_register_masked_no_operation_writable_mapping,
    validate_register_masked_non_graphical_writable_mapping,
    validate_register_masked_output_writable_mapping,
    validate_register_masked_rotate_writable_mapping,
    validate_register_masked_writable_mapping, validate_writable_mapping,
};
use super::loader::{
    NativeExecutablePermission, VerifiedDirectFusedLoadImage,
    VerifiedDirectLoadImage, VerifiedExecutionGeometryLoadImage,
    VerifiedRegisterMaskedCrazyLoadImage, VerifiedRegisterMaskedLoadImage,
    VerifiedRegisterMaskedNoOperationHaltLoadImage,
    VerifiedRegisterMaskedNoOperationLoadImage,
    VerifiedRegisterMaskedNoOperationPairLoadImage,
    VerifiedRegisterMaskedNonGraphicalLoadImage,
    VerifiedRegisterMaskedOutputLoadImage,
    VerifiedRegisterMaskedRotateLoadImage,
};

/// Exact writable allocation request derived from one verified load image.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeExecutableAllocationRequest {
    alignment: usize,
    byte_len: usize,
    permissions: NativeExecutablePermission,
}

/// Exact copy evidence returned after writing one verified code image.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeExecutableCodeCopyReport {
    copied_code: Box<[u8]>,
    mapping_id: NativeExecutableMappingId,
    start_address: NonZeroUsize,
}

/// Exact synchronization request for one sealed executable code range.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeInstructionSyncRequest {
    byte_len: usize,
    mapping_id: NativeExecutableMappingId,
    start_address: NonZeroUsize,
}

/// Ordered platform operation whose execution or admission failed.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeExecutableLoadPhase {
    /// Writable mapping allocation and report admission.
    Allocate,
    /// Exact verified code copy and staging admission.
    Copy,
    /// Same-mapping transition from RW to RX.
    Protect,
    /// Full-code instruction synchronization and ready admission.
    Synchronize,
}

/// Drift in platform operation evidence not represented by lifecycle reports.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeExecutableOperationEvidenceError {
    /// Copy evidence names a different mapping identity.
    CopyMappingIdentity,
    /// Copy evidence starts at a different mapping address.
    CopyStartAddress,
}

#[derive(Debug, Eq, PartialEq)]
enum NativeExecutableLoadFailureCause<Error> {
    Adapter(Box<Error>),
    Evidence(Box<NativeExecutableOperationEvidenceError>),
    Lifecycle(Box<NativeExecutableLifecycleError>),
}

/// Phase-tagged load failure retaining exact cleanup evidence.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeExecutableLoadFailure<Error> {
    cause: NativeExecutableLoadFailureCause<Error>,
    phase: NativeExecutableLoadPhase,
    release_error: Option<Box<Error>>,
    release_request: Option<NativeExecutableReleaseRequest>,
}

/// Failed explicit release retaining the executable for exact retry.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeExecutableReleaseFailure<Error> {
    error: Box<Error>,
    executable: Box<ReadyNativeExecutable>,
}

/// Failed fused release retaining the exact executable for retry.
#[derive(Debug, Eq, PartialEq)]
pub struct DirectFusedNativeExecutableReleaseFailure<Error> {
    error: Box<Error>,
    executable: Box<ReadyDirectFusedNativeExecutable>,
}

/// Failed v5 release retaining the exact executable for retry.
#[derive(Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeExecutableReleaseFailure<Error> {
    error: Box<Error>,
    executable: Box<ReadyExecutionGeometryNativeExecutable>,
}

/// Failed register-masked v6 release retaining exact executable identity.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedNativeExecutableReleaseFailure<Error> {
    error: Box<Error>,
    executable: Box<ReadyRegisterMaskedNativeExecutable>,
}

/// Failed v6 Crazy release retaining exact executable identity.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedCrazyNativeExecutableReleaseFailure<Error> {
    error: Box<Error>,
    executable: Box<ReadyRegisterMaskedCrazyNativeExecutable>,
}

/// Failed v6 output release retaining exact executable identity.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedOutputNativeExecutableReleaseFailure<Error> {
    error: Box<Error>,
    executable: Box<ReadyRegisterMaskedOutputNativeExecutable>,
}

/// Failed v6 no-operation release retaining exact executable identity.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedNoOperationNativeExecutableReleaseFailure<Error> {
    error: Box<Error>,
    executable: Box<ReadyRegisterMaskedNoOperationNativeExecutable>,
}

/// Failed collapsed v6 no-op/halt release retaining exact executable identity.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedNoOperationHaltNativeExecutableReleaseFailure<Error> {
    error: Box<Error>,
    executable: Box<ReadyRegisterMaskedNoOperationHaltNativeExecutable>,
}

/// Failed collapsed v6 no-operation-pair release retaining exact executable
/// identity.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedNoOperationPairNativeExecutableReleaseFailure<Error> {
    error: Box<Error>,
    executable: Box<ReadyRegisterMaskedNoOperationPairNativeExecutable>,
}

/// Failed v6 rotate release retaining exact executable identity.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedRotateNativeExecutableReleaseFailure<Error> {
    error: Box<Error>,
    executable: Box<ReadyRegisterMaskedRotateNativeExecutable>,
}

/// Failed non-graphical v6 release retaining exact executable identity.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedNonGraphicalNativeExecutableReleaseFailure<Error> {
    error: Box<Error>,
    executable: Box<ReadyRegisterMaskedNonGraphicalNativeExecutable>,
}

/// Result of loading one exact fused native executable.
pub type DirectFusedNativeExecutableLoadResult<Error> = Result<
    ReadyDirectFusedNativeExecutable,
    NativeExecutableLoadFailure<Error>,
>;

/// Result of explicitly releasing one ready fused executable.
pub type DirectFusedNativeExecutableReleaseResult<Error> =
    Result<(), DirectFusedNativeExecutableReleaseFailure<Error>>;

/// Result of loading one exact explicit-geometry native executable.
pub type ExecutionGeometryNativeExecutableLoadResult<Error> = Result<
    ReadyExecutionGeometryNativeExecutable,
    NativeExecutableLoadFailure<Error>,
>;

/// Result of explicitly releasing one ready explicit-geometry executable.
pub type ExecutionGeometryNativeExecutableReleaseResult<Error> =
    Result<(), ExecutionGeometryNativeExecutableReleaseFailure<Error>>;

/// Result of loading one exact register-masked v6 native executable.
pub type RegisterMaskedNativeExecutableLoadResult<Error> = Result<
    ReadyRegisterMaskedNativeExecutable,
    NativeExecutableLoadFailure<Error>,
>;

/// Result of explicitly releasing one ready register-masked v6 executable.
pub type RegisterMaskedNativeExecutableReleaseResult<Error> =
    Result<(), RegisterMaskedNativeExecutableReleaseFailure<Error>>;

/// Result of loading one v6 Crazy native executable.
pub type RegisterMaskedCrazyNativeExecutableLoadResult<Error> = Result<
    ReadyRegisterMaskedCrazyNativeExecutable,
    NativeExecutableLoadFailure<Error>,
>;

/// Result of explicitly releasing one ready v6 Crazy executable.
pub type RegisterMaskedCrazyNativeExecutableReleaseResult<Error> =
    Result<(), RegisterMaskedCrazyNativeExecutableReleaseFailure<Error>>;

/// Result of loading one v6 output native executable.
pub type RegisterMaskedOutputNativeExecutableLoadResult<Error> = Result<
    ReadyRegisterMaskedOutputNativeExecutable,
    NativeExecutableLoadFailure<Error>,
>;

/// Result of explicitly releasing one ready v6 output executable.
pub type RegisterMaskedOutputNativeExecutableReleaseResult<Error> =
    Result<(), RegisterMaskedOutputNativeExecutableReleaseFailure<Error>>;

/// Result of loading one v6 no-operation native executable.
pub type RegisterMaskedNoOperationNativeExecutableLoadResult<Error> = Result<
    ReadyRegisterMaskedNoOperationNativeExecutable,
    NativeExecutableLoadFailure<Error>,
>;

/// Result of explicitly releasing one ready v6 no-operation executable.
pub type RegisterMaskedNoOperationNativeExecutableReleaseResult<Error> =
    Result<(), RegisterMaskedNoOperationNativeExecutableReleaseFailure<Error>>;

/// Result of loading one collapsed v6 no-op/halt native executable.
pub type RegisterMaskedNoOperationHaltNativeExecutableLoadResult<Error> =
    Result<
        ReadyRegisterMaskedNoOperationHaltNativeExecutable,
        NativeExecutableLoadFailure<Error>,
    >;

/// Result of explicitly releasing one collapsed v6 no-op/halt executable.
pub type RegisterMaskedNoOperationHaltNativeExecutableReleaseResult<Error> =
    Result<
        (),
        RegisterMaskedNoOperationHaltNativeExecutableReleaseFailure<Error>,
    >;

/// Result of loading one collapsed v6 no-operation pair native executable.
pub type RegisterMaskedNoOperationPairNativeExecutableLoadResult<Error> =
    Result<
        ReadyRegisterMaskedNoOperationPairNativeExecutable,
        NativeExecutableLoadFailure<Error>,
    >;

/// Result of explicitly releasing one collapsed v6 no-operation pair
/// executable.
pub type RegisterMaskedNoOperationPairNativeExecutableReleaseResult<Error> =
    Result<
        (),
        RegisterMaskedNoOperationPairNativeExecutableReleaseFailure<Error>,
    >;

/// Result of loading one v6 rotate native executable.
pub type RegisterMaskedRotateNativeExecutableLoadResult<Error> = Result<
    ReadyRegisterMaskedRotateNativeExecutable,
    NativeExecutableLoadFailure<Error>,
>;

/// Result of explicitly releasing one ready v6 rotate executable.
pub type RegisterMaskedRotateNativeExecutableReleaseResult<Error> =
    Result<(), RegisterMaskedRotateNativeExecutableReleaseFailure<Error>>;

/// Result of loading one non-graphical register-masked v6 executable.
pub type RegisterMaskedNonGraphicalNativeExecutableLoadResult<Error> = Result<
    ReadyRegisterMaskedNonGraphicalNativeExecutable,
    NativeExecutableLoadFailure<Error>,
>;

/// Result of explicitly releasing one non-graphical v6 executable.
pub type RegisterMaskedNonGraphicalNativeExecutableReleaseResult<Error> =
    Result<(), RegisterMaskedNonGraphicalNativeExecutableReleaseFailure<Error>>;

/// Result of loading one exact verified native executable.
pub type NativeExecutableLoadResult<Error> =
    Result<ReadyNativeExecutable, NativeExecutableLoadFailure<Error>>;

/// Result of explicitly releasing one ready native executable.
pub type NativeExecutableReleaseResult<Error> =
    Result<(), NativeExecutableReleaseFailure<Error>>;

type NativeExecutableLoadStepResult<Value, Error> =
    Result<Value, NativeExecutableLoadFailure<Error>>;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct AllocatedNativeMapping {
    mapping: NativeExecutableMappingReport,
    release_request: NativeExecutableReleaseRequest,
}

/// Caller-owned platform operations required by the safe native loader.
pub trait NativeExecutableMemoryAdapter {
    /// Stable platform-specific operation failure.
    type Error;

    /// Allocates one writable, non-executable mapping.
    ///
    /// Every successful allocation must retain a unique mapping identity and a
    /// non-overlapping address range until its matching release succeeds.
    ///
    /// # Errors
    ///
    /// Returns the adapter's stable allocation failure.
    fn allocate_writable(
        &mut self,
        request: NativeExecutableAllocationRequest,
    ) -> Result<NativeExecutableMappingReport, Self::Error>;

    /// Copies exact code into the supplied writable mapping.
    ///
    /// # Errors
    ///
    /// Returns the adapter's stable copy failure.
    fn copy_code(
        &mut self,
        mapping: NativeExecutableMappingReport,
        code: &[u8],
    ) -> Result<NativeExecutableCodeCopyReport, Self::Error>;

    /// Transitions the same mapping to read-execute permissions.
    ///
    /// # Errors
    ///
    /// Returns the adapter's stable protection failure.
    fn protect_read_execute(
        &mut self,
        mapping: NativeExecutableMappingReport,
    ) -> Result<NativeExecutableMappingReport, Self::Error>;

    /// Releases one exact mapping range.
    ///
    /// # Errors
    ///
    /// Returns the adapter's stable release failure.
    fn release(
        &mut self,
        request: NativeExecutableReleaseRequest,
    ) -> Result<(), Self::Error>;

    /// Synchronizes one exact executable instruction range.
    ///
    /// # Errors
    ///
    /// Returns the adapter's stable instruction-sync failure.
    fn synchronize_instructions(
        &mut self,
        request: NativeInstructionSyncRequest,
    ) -> Result<NativeInstructionSyncReport, Self::Error>;
}

impl NativeExecutableAllocationRequest {
    /// Returns the minimum accepted mapping alignment.
    #[must_use]
    pub const fn alignment(self) -> usize {
        self.alignment
    }

    /// Returns the exact verified code length to allocate.
    #[must_use]
    pub const fn byte_len(self) -> usize {
        self.byte_len
    }

    /// Constructs one exact writable allocation request.
    #[must_use]
    pub const fn new(
        byte_len: usize,
        alignment: usize,
        permissions: NativeExecutablePermission,
    ) -> Self {
        Self {
            alignment,
            byte_len,
            permissions,
        }
    }

    /// Returns the required initial mapping permissions.
    #[must_use]
    pub const fn permissions(self) -> NativeExecutablePermission {
        self.permissions
    }
}

impl NativeExecutableCodeCopyReport {
    /// Returns the exact observed copied bytes.
    #[must_use]
    pub const fn copied_code(&self) -> &[u8] {
        &self.copied_code
    }

    /// Returns the mapping identity that received the copy.
    #[must_use]
    pub const fn mapping_id(&self) -> NativeExecutableMappingId {
        self.mapping_id
    }

    /// Constructs exact copy evidence for one mapping range.
    #[must_use]
    pub fn new<Code>(
        mapping_id: NativeExecutableMappingId,
        start_address: NonZeroUsize,
        copied_code: Code,
    ) -> Self
    where
        Code: Into<Box<[u8]>>,
    {
        Self {
            copied_code: copied_code.into(),
            mapping_id,
            start_address,
        }
    }

    /// Returns the address at which the copy began.
    #[must_use]
    pub const fn start_address(&self) -> NonZeroUsize {
        self.start_address
    }
}

impl NativeInstructionSyncRequest {
    /// Returns the exact byte length requiring synchronization.
    #[must_use]
    pub const fn byte_len(self) -> usize {
        self.byte_len
    }

    /// Returns the exact mapping identity requiring synchronization.
    #[must_use]
    pub const fn mapping_id(self) -> NativeExecutableMappingId {
        self.mapping_id
    }

    /// Constructs one exact instruction synchronization request.
    #[must_use]
    pub const fn new(
        mapping_id: NativeExecutableMappingId,
        start_address: NonZeroUsize,
        byte_len: usize,
    ) -> Self {
        Self {
            byte_len,
            mapping_id,
            start_address,
        }
    }

    /// Returns the first address requiring synchronization.
    #[must_use]
    pub const fn start_address(self) -> NonZeroUsize {
        self.start_address
    }
}

impl<Error> NativeExecutableLoadFailure<Error> {
    /// Returns the primary adapter error, when platform execution failed.
    #[must_use]
    pub const fn adapter_error(&self) -> Option<&Error> {
        match &self.cause {
            NativeExecutableLoadFailureCause::Adapter(error) => Some(error),
            NativeExecutableLoadFailureCause::Evidence(_)
            | NativeExecutableLoadFailureCause::Lifecycle(_) => None,
        }
    }

    /// Reports whether rollback after the primary load failure still failed.
    #[must_use]
    pub const fn cleanup_pending(&self) -> bool {
        self.release_error.is_some()
    }

    /// Returns operation-evidence drift, when report identity disagreed.
    #[must_use]
    pub const fn evidence_error(
        &self,
    ) -> Option<NativeExecutableOperationEvidenceError> {
        match &self.cause {
            NativeExecutableLoadFailureCause::Evidence(error) => Some(**error),
            NativeExecutableLoadFailureCause::Adapter(_)
            | NativeExecutableLoadFailureCause::Lifecycle(_) => None,
        }
    }

    /// Returns lifecycle admission failure, when a report failed closed.
    #[must_use]
    pub const fn lifecycle_error(
        &self,
    ) -> Option<NativeExecutableLifecycleError> {
        match &self.cause {
            NativeExecutableLoadFailureCause::Lifecycle(error) => Some(**error),
            NativeExecutableLoadFailureCause::Adapter(_)
            | NativeExecutableLoadFailureCause::Evidence(_) => None,
        }
    }

    /// Returns the exact operation phase that failed.
    #[must_use]
    pub const fn phase(&self) -> NativeExecutableLoadPhase {
        self.phase
    }

    /// Returns cleanup failure without replacing the primary cause.
    #[must_use]
    pub const fn release_error(&self) -> Option<&Error> {
        match &self.release_error {
            Some(error) => Some(error),
            None => None,
        }
    }

    /// Returns the exact cleanup request attempted after allocation.
    #[must_use]
    pub const fn release_request(
        &self,
    ) -> Option<NativeExecutableReleaseRequest> {
        self.release_request
    }

    /// Retries failed rollback while preserving the primary load failure.
    ///
    /// The original phase and primary cause remain unchanged. A successful
    /// release clears only the secondary cleanup error; another adapter failure
    /// replaces it while retaining the same release request for later retry.
    #[must_use]
    pub fn retry_cleanup<Adapter>(mut self, adapter: &mut Adapter) -> Self
    where
        Adapter: NativeExecutableMemoryAdapter<Error = Error>,
    {
        if self.release_error.is_some()
            && let Some(request) = self.release_request
        {
            self.release_error = adapter.release(request).err().map(Box::new);
        }
        self
    }
}

impl Display for NativeExecutableLoadPhase {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Allocate => "allocate",
            Self::Copy => "copy",
            Self::Protect => "protect",
            Self::Synchronize => "synchronize",
        })
    }
}

impl Display for NativeExecutableOperationEvidenceError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::CopyMappingIdentity => "copy mapping identity drifted",
            Self::CopyStartAddress => "copy start address drifted",
        })
    }
}

impl<Error: Display> Display for NativeExecutableLoadFailure<Error> {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "native executable load failed during {}: ", self.phase)?;
        match &self.cause {
            NativeExecutableLoadFailureCause::Adapter(error) => {
                write!(f, "adapter error: {error}")?;
            },
            NativeExecutableLoadFailureCause::Evidence(error) => {
                write!(f, "operation evidence drift: {error}")?;
            },
            NativeExecutableLoadFailureCause::Lifecycle(error) => {
                write!(f, "lifecycle admission: {error}")?;
            },
        }
        if let Some(release_error) = &self.release_error {
            write!(f, "; release failed: {release_error}")?;
        }
        Ok(())
    }
}

impl<Error> DirectFusedNativeExecutableReleaseFailure<Error> {
    /// Returns the platform release error.
    #[must_use]
    pub const fn error(&self) -> &Error {
        &self.error
    }

    /// Returns the exact fused ready executable retained for retry.
    #[must_use]
    pub fn executable(&self) -> &ReadyDirectFusedNativeExecutable {
        self.executable.as_ref()
    }

    /// Retries release without losing fused executable identity after failure.
    ///
    /// # Errors
    ///
    /// Returns a refreshed failure retaining the same executable when release
    /// fails again.
    pub fn retry<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> DirectFusedNativeExecutableReleaseResult<Error>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = Error>,
    {
        let request = self.executable.release_request();
        match adapter.release(request) {
            Ok(()) => Ok(()),
            Err(error) => Err(Self {
                error: Box::new(error),
                executable: self.executable,
            }),
        }
    }
}

impl<Error: Display> Display
    for DirectFusedNativeExecutableReleaseFailure<Error>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "fused native executable release failed: {}", self.error)
    }
}

impl<Error> ExecutionGeometryNativeExecutableReleaseFailure<Error> {
    /// Returns the platform release error.
    #[must_use]
    pub const fn error(&self) -> &Error {
        &self.error
    }

    /// Returns the exact v5 ready executable retained for retry.
    #[must_use]
    pub fn executable(&self) -> &ReadyExecutionGeometryNativeExecutable {
        self.executable.as_ref()
    }

    /// Retries release without losing v5 executable identity after failure.
    ///
    /// # Errors
    ///
    /// Returns a refreshed failure retaining the same executable when release
    /// fails again.
    pub fn retry<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> ExecutionGeometryNativeExecutableReleaseResult<Error>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = Error>,
    {
        let request = self.executable.release_request();
        match adapter.release(request) {
            Ok(()) => Ok(()),
            Err(error) => Err(Self {
                error: Box::new(error),
                executable: self.executable,
            }),
        }
    }
}

impl<Error: Display> Display
    for ExecutionGeometryNativeExecutableReleaseFailure<Error>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "v5 native executable release failed: {}", self.error)
    }
}

impl<Error> RegisterMaskedNativeExecutableReleaseFailure<Error> {
    /// Returns the platform release error.
    #[must_use]
    pub const fn error(&self) -> &Error {
        &self.error
    }

    /// Returns the exact v6 ready executable retained for retry.
    #[must_use]
    pub fn executable(&self) -> &ReadyRegisterMaskedNativeExecutable {
        self.executable.as_ref()
    }

    /// Retries release without losing v6 executable identity after failure.
    ///
    /// # Errors
    ///
    /// Returns a refreshed failure retaining the same executable when release
    /// fails again.
    pub fn retry<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> RegisterMaskedNativeExecutableReleaseResult<Error>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = Error>,
    {
        let request = self.executable.release_request();
        match adapter.release(request) {
            Ok(()) => Ok(()),
            Err(error) => Err(Self {
                error: Box::new(error),
                executable: self.executable,
            }),
        }
    }
}

impl<Error: Display> Display
    for RegisterMaskedNativeExecutableReleaseFailure<Error>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "v6 native executable release failed: {}", self.error)
    }
}

impl<Error> RegisterMaskedCrazyNativeExecutableReleaseFailure<Error> {
    /// Returns the platform release error.
    #[must_use]
    pub const fn error(&self) -> &Error {
        &self.error
    }

    /// Returns the exact v6 Crazy executable retained for retry.
    #[must_use]
    pub fn executable(&self) -> &ReadyRegisterMaskedCrazyNativeExecutable {
        self.executable.as_ref()
    }

    /// Retries release without losing v6 Crazy identity after failure.
    ///
    /// # Errors
    ///
    /// Returns a refreshed failure retaining the same executable on failure.
    pub fn retry<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> RegisterMaskedCrazyNativeExecutableReleaseResult<Error>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = Error>,
    {
        let request = self.executable.release_request();
        match adapter.release(request) {
            Ok(()) => Ok(()),
            Err(error) => Err(Self {
                error: Box::new(error),
                executable: self.executable,
            }),
        }
    }
}

impl<Error: Display> Display
    for RegisterMaskedCrazyNativeExecutableReleaseFailure<Error>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "v6 Crazy native release failed: {}", self.error)
    }
}

impl<Error> RegisterMaskedOutputNativeExecutableReleaseFailure<Error> {
    /// Returns the platform release error.
    #[must_use]
    pub const fn error(&self) -> &Error {
        &self.error
    }

    /// Returns the exact v6 output executable retained for retry.
    #[must_use]
    pub fn executable(&self) -> &ReadyRegisterMaskedOutputNativeExecutable {
        self.executable.as_ref()
    }

    /// Retries release without losing v6 output identity after failure.
    ///
    /// # Errors
    ///
    /// Returns a refreshed failure retaining the same executable on failure.
    pub fn retry<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> RegisterMaskedOutputNativeExecutableReleaseResult<Error>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = Error>,
    {
        let request = self.executable.release_request();
        match adapter.release(request) {
            Ok(()) => Ok(()),
            Err(error) => Err(Self {
                error: Box::new(error),
                executable: self.executable,
            }),
        }
    }
}

impl<Error: Display> Display
    for RegisterMaskedOutputNativeExecutableReleaseFailure<Error>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "v6 output native release failed: {}", self.error)
    }
}

impl<Error> RegisterMaskedNoOperationNativeExecutableReleaseFailure<Error> {
    /// Returns the platform release error.
    #[must_use]
    pub const fn error(&self) -> &Error {
        &self.error
    }

    /// Returns the exact v6 no-operation executable retained for retry.
    #[must_use]
    pub fn executable(
        &self,
    ) -> &ReadyRegisterMaskedNoOperationNativeExecutable {
        self.executable.as_ref()
    }

    /// Retries release without losing v6 no-operation identity after failure.
    ///
    /// # Errors
    ///
    /// Returns a refreshed failure retaining the same executable on failure.
    pub fn retry<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> RegisterMaskedNoOperationNativeExecutableReleaseResult<Error>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = Error>,
    {
        let request = self.executable.release_request();
        match adapter.release(request) {
            Ok(()) => Ok(()),
            Err(error) => Err(Self {
                error: Box::new(error),
                executable: self.executable,
            }),
        }
    }
}

impl<Error: Display> Display
    for RegisterMaskedNoOperationNativeExecutableReleaseFailure<Error>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "v6 no-operation native release failed: {}", self.error)
    }
}

impl<Error> RegisterMaskedNoOperationHaltNativeExecutableReleaseFailure<Error> {
    /// Returns the platform release error.
    #[must_use]
    pub const fn error(&self) -> &Error {
        &self.error
    }

    /// Returns the exact collapsed v6 executable retained for retry.
    #[must_use]
    pub fn executable(
        &self,
    ) -> &ReadyRegisterMaskedNoOperationHaltNativeExecutable {
        self.executable.as_ref()
    }

    /// Retries release without losing collapsed v6 identity after failure.
    ///
    /// # Errors
    ///
    /// Returns a refreshed failure retaining the same executable on failure.
    pub fn retry<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> RegisterMaskedNoOperationHaltNativeExecutableReleaseResult<Error>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = Error>,
    {
        let request = self.executable.release_request();
        match adapter.release(request) {
            Ok(()) => Ok(()),
            Err(error) => Err(Self {
                error: Box::new(error),
                executable: self.executable,
            }),
        }
    }
}

impl<Error: Display> Display
    for RegisterMaskedNoOperationHaltNativeExecutableReleaseFailure<Error>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "collapsed v6 no-op/halt native release failed: {}",
            self.error
        )
    }
}

impl<Error> RegisterMaskedNoOperationPairNativeExecutableReleaseFailure<Error> {
    /// Returns the platform release error.
    #[must_use]
    pub const fn error(&self) -> &Error {
        &self.error
    }

    /// Returns the exact collapsed v6 executable retained for retry.
    #[must_use]
    pub fn executable(
        &self,
    ) -> &ReadyRegisterMaskedNoOperationPairNativeExecutable {
        self.executable.as_ref()
    }

    /// Retries release without losing collapsed pair v6 identity after failure.
    ///
    /// # Errors
    ///
    /// Returns a refreshed failure retaining the same executable on failure.
    pub fn retry<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> RegisterMaskedNoOperationPairNativeExecutableReleaseResult<Error>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = Error>,
    {
        let request = self.executable.release_request();
        match adapter.release(request) {
            Ok(()) => Ok(()),
            Err(error) => Err(Self {
                error: Box::new(error),
                executable: self.executable,
            }),
        }
    }
}

impl<Error: Display> Display
    for RegisterMaskedNoOperationPairNativeExecutableReleaseFailure<Error>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "collapsed v6 no-operation pair native release failed: {}",
            self.error
        )
    }
}

impl<Error> RegisterMaskedRotateNativeExecutableReleaseFailure<Error> {
    /// Returns the platform release error.
    #[must_use]
    pub const fn error(&self) -> &Error {
        &self.error
    }

    /// Returns the exact v6 rotate executable retained for retry.
    #[must_use]
    pub fn executable(&self) -> &ReadyRegisterMaskedRotateNativeExecutable {
        self.executable.as_ref()
    }

    /// Retries release without losing v6 rotate identity after failure.
    ///
    /// # Errors
    ///
    /// Returns a refreshed failure retaining the same executable on failure.
    pub fn retry<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> RegisterMaskedRotateNativeExecutableReleaseResult<Error>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = Error>,
    {
        let request = self.executable.release_request();
        match adapter.release(request) {
            Ok(()) => Ok(()),
            Err(error) => Err(Self {
                error: Box::new(error),
                executable: self.executable,
            }),
        }
    }
}

impl<Error: Display> Display
    for RegisterMaskedRotateNativeExecutableReleaseFailure<Error>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "v6 rotate native release failed: {}", self.error)
    }
}

impl<Error> RegisterMaskedNonGraphicalNativeExecutableReleaseFailure<Error> {
    /// Returns the platform release error.
    #[must_use]
    pub const fn error(&self) -> &Error {
        &self.error
    }

    /// Returns the exact non-graphical v6 executable retained for retry.
    #[must_use]
    pub fn executable(
        &self,
    ) -> &ReadyRegisterMaskedNonGraphicalNativeExecutable {
        self.executable.as_ref()
    }

    /// Retries release without losing non-graphical v6 executable identity.
    ///
    /// # Errors
    ///
    /// Returns a refreshed failure retaining the same executable on failure.
    pub fn retry<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> RegisterMaskedNonGraphicalNativeExecutableReleaseResult<Error>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = Error>,
    {
        let request = self.executable.release_request();
        match adapter.release(request) {
            Ok(()) => Ok(()),
            Err(error) => Err(Self {
                error: Box::new(error),
                executable: self.executable,
            }),
        }
    }
}

impl<Error: Display> Display
    for RegisterMaskedNonGraphicalNativeExecutableReleaseFailure<Error>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "non-graphical v6 native executable release failed: {}",
            self.error
        )
    }
}

impl<Error> NativeExecutableReleaseFailure<Error> {
    /// Returns the platform release error.
    #[must_use]
    pub const fn error(&self) -> &Error {
        &self.error
    }

    /// Returns the ready executable retained for an exact retry.
    #[must_use]
    pub fn executable(&self) -> &ReadyNativeExecutable {
        self.executable.as_ref()
    }

    /// Retries release without losing the ready executable after another
    /// failure.
    ///
    /// # Errors
    ///
    /// Returns a refreshed failure retaining the same executable when release
    /// fails again.
    pub fn retry<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> NativeExecutableReleaseResult<Error>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = Error>,
    {
        let request = self.executable.release_request();
        match adapter.release(request) {
            Ok(()) => Ok(()),
            Err(error) => Err(Self {
                error: Box::new(error),
                executable: self.executable,
            }),
        }
    }
}

impl<Error: Display> Display for NativeExecutableReleaseFailure<Error> {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "native executable release failed: {}", self.error)
    }
}

/// Loads one verified fused image through the platform adapter.
///
/// Every post-allocation failure attempts exact release before returning. The
/// resulting ready executable remains fused-specific with no invocation or
/// runner authority.
///
/// # Errors
///
/// Returns [`NativeExecutableLoadFailure`] when an adapter operation or fused
/// lifecycle admission fails.
pub fn load_direct_fused_native_executable<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedDirectFusedLoadImage,
) -> DirectFusedNativeExecutableLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let allocated = allocate_direct_fused_image(adapter, image)?;
    let staged = copy_direct_fused_image(adapter, image, allocated)?;
    let sealed = protect_direct_fused_image(adapter, staged, allocated)?;
    synchronize_direct_fused_image(adapter, sealed, allocated)
}

/// Releases one ready fused executable while preserving retry ownership.
///
/// # Errors
///
/// Returns [`DirectFusedNativeExecutableReleaseFailure`] with the exact ready
/// executable when the adapter rejects release.
pub fn release_direct_fused_native_executable<Adapter>(
    adapter: &mut Adapter,
    executable: ReadyDirectFusedNativeExecutable,
) -> DirectFusedNativeExecutableReleaseResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = executable.release_request();
    match adapter.release(request) {
        Ok(()) => Ok(()),
        Err(error) => Err(DirectFusedNativeExecutableReleaseFailure {
            error: Box::new(error),
            executable: Box::new(executable),
        }),
    }
}

/// Loads one verified explicit-geometry image through the platform adapter.
///
/// Every post-allocation failure attempts exact release before returning. The
/// resulting ready executable remains a v5-specific type with no runner path.
///
/// # Errors
///
/// Returns [`NativeExecutableLoadFailure`] when any adapter operation or v5
/// lifecycle admission fails.
pub fn load_execution_geometry_native_executable<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedExecutionGeometryLoadImage,
) -> ExecutionGeometryNativeExecutableLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let allocated = allocate_execution_geometry_image(adapter, image)?;
    let staged = copy_execution_geometry_image(adapter, image, allocated)?;
    let sealed = protect_execution_geometry_image(adapter, staged, allocated)?;
    synchronize_execution_geometry_image(adapter, sealed, allocated)
}

/// Releases one ready v5 executable while preserving it for retry on failure.
///
/// # Errors
///
/// Returns [`ExecutionGeometryNativeExecutableReleaseFailure`] with the exact
/// ready executable when the adapter rejects release.
pub fn release_execution_geometry_native_executable<Adapter>(
    adapter: &mut Adapter,
    executable: ReadyExecutionGeometryNativeExecutable,
) -> ExecutionGeometryNativeExecutableReleaseResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = executable.release_request();
    match adapter.release(request) {
        Ok(()) => Ok(()),
        Err(error) => Err(ExecutionGeometryNativeExecutableReleaseFailure {
            error: Box::new(error),
            executable: Box::new(executable),
        }),
    }
}

/// Loads one verified register-masked v6 image through the platform adapter.
///
/// Every post-allocation failure attempts exact release before returning. The
/// resulting ready executable remains a v6-specific type.
///
/// # Errors
///
/// Returns [`NativeExecutableLoadFailure`] when any adapter operation or v6
/// lifecycle admission fails.
pub fn load_register_masked_native_executable<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedRegisterMaskedLoadImage,
) -> RegisterMaskedNativeExecutableLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let allocated = allocate_register_masked_image(adapter, image)?;
    let staged = copy_register_masked_image(adapter, image, allocated)?;
    let sealed = protect_register_masked_image(adapter, staged, allocated)?;
    synchronize_register_masked_image(adapter, sealed, allocated)
}

/// Releases one ready v6 executable while preserving it for retry on failure.
///
/// # Errors
///
/// Returns [`RegisterMaskedNativeExecutableReleaseFailure`] with the exact
/// ready executable when the adapter rejects release.
pub fn release_register_masked_native_executable<Adapter>(
    adapter: &mut Adapter,
    executable: ReadyRegisterMaskedNativeExecutable,
) -> RegisterMaskedNativeExecutableReleaseResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = executable.release_request();
    match adapter.release(request) {
        Ok(()) => Ok(()),
        Err(error) => Err(RegisterMaskedNativeExecutableReleaseFailure {
            error: Box::new(error),
            executable: Box::new(executable),
        }),
    }
}

/// Loads one verified v6 Crazy image through the platform adapter.
///
/// Every post-allocation failure attempts exact release before returning. The
/// result remains Crazy-specific with no binding or runner authority.
///
/// # Errors
///
/// Returns [`NativeExecutableLoadFailure`] when an adapter operation or
/// lifecycle admission fails.
pub fn load_register_masked_crazy_native_executable<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedRegisterMaskedCrazyLoadImage,
) -> RegisterMaskedCrazyNativeExecutableLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let allocated = allocate_register_masked_crazy_image(adapter, image)?;
    let staged = copy_register_masked_crazy_image(adapter, image, allocated)?;
    let sealed =
        protect_register_masked_crazy_image(adapter, staged, allocated)?;
    synchronize_register_masked_crazy_image(adapter, sealed, allocated)
}

/// Releases one ready v6 Crazy executable with retry ownership.
///
/// # Errors
///
/// Returns [`RegisterMaskedCrazyNativeExecutableReleaseFailure`] with the
/// exact ready executable when the adapter rejects release.
pub fn release_register_masked_crazy_native_executable<Adapter>(
    adapter: &mut Adapter,
    executable: ReadyRegisterMaskedCrazyNativeExecutable,
) -> RegisterMaskedCrazyNativeExecutableReleaseResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = executable.release_request();
    match adapter.release(request) {
        Ok(()) => Ok(()),
        Err(error) => Err(RegisterMaskedCrazyNativeExecutableReleaseFailure {
            error: Box::new(error),
            executable: Box::new(executable),
        }),
    }
}

/// Loads one verified v6 output image through the platform adapter.
///
/// Every post-allocation failure attempts exact release before returning. The
/// result remains output-specific with no binding or runner authority.
///
/// # Errors
///
/// Returns [`NativeExecutableLoadFailure`] when an adapter operation or
/// lifecycle admission fails.
pub fn load_register_masked_output_native_executable<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedRegisterMaskedOutputLoadImage,
) -> RegisterMaskedOutputNativeExecutableLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let allocated = allocate_register_masked_output_image(adapter, image)?;
    let staged = copy_register_masked_output_image(adapter, image, allocated)?;
    let sealed =
        protect_register_masked_output_image(adapter, staged, allocated)?;
    synchronize_register_masked_output_image(adapter, sealed, allocated)
}

/// Releases one ready v6 output executable with retry ownership.
///
/// # Errors
///
/// Returns [`RegisterMaskedOutputNativeExecutableReleaseFailure`] with the
/// exact ready executable when the adapter rejects release.
pub fn release_register_masked_output_native_executable<Adapter>(
    adapter: &mut Adapter,
    executable: ReadyRegisterMaskedOutputNativeExecutable,
) -> RegisterMaskedOutputNativeExecutableReleaseResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = executable.release_request();
    match adapter.release(request) {
        Ok(()) => Ok(()),
        Err(error) => Err(RegisterMaskedOutputNativeExecutableReleaseFailure {
            error: Box::new(error),
            executable: Box::new(executable),
        }),
    }
}

/// Loads one verified v6 no-operation image through the platform adapter.
///
/// Every post-allocation failure attempts exact release before returning. The
/// result remains no-operation-specific with no binding or runner authority.
///
/// # Errors
///
/// Returns [`NativeExecutableLoadFailure`] when an adapter operation or
/// lifecycle admission fails.
pub fn load_register_masked_no_operation_native_executable<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedRegisterMaskedNoOperationLoadImage,
) -> RegisterMaskedNoOperationNativeExecutableLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let allocated =
        allocate_register_masked_no_operation_image(adapter, image)?;
    let staged =
        copy_register_masked_no_operation_image(adapter, image, allocated)?;
    let sealed =
        protect_register_masked_no_operation_image(adapter, staged, allocated)?;
    synchronize_register_masked_no_operation_image(adapter, sealed, allocated)
}

/// Releases one ready v6 no-operation executable with retry ownership.
///
/// # Errors
///
/// Returns [`RegisterMaskedNoOperationNativeExecutableReleaseFailure`] with the
/// exact ready executable when the adapter rejects release.
pub fn release_register_masked_no_operation_native_executable<Adapter>(
    adapter: &mut Adapter,
    executable: ReadyRegisterMaskedNoOperationNativeExecutable,
) -> RegisterMaskedNoOperationNativeExecutableReleaseResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = executable.release_request();
    match adapter.release(request) {
        Ok(()) => Ok(()),
        Err(error) => {
            Err(RegisterMaskedNoOperationNativeExecutableReleaseFailure {
                error: Box::new(error),
                executable: Box::new(executable),
            })
        },
    }
}

/// Loads one verified collapsed v6 no-op/halt image through the adapter.
///
/// Every post-allocation failure attempts exact release before returning. The
/// result remains collapsed-shape-specific with no binding or runner authority.
///
/// # Errors
///
/// Returns [`NativeExecutableLoadFailure`] when an adapter operation or
/// lifecycle admission fails.
pub fn load_register_masked_no_operation_halt_native_executable<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedRegisterMaskedNoOperationHaltLoadImage,
) -> RegisterMaskedNoOperationHaltNativeExecutableLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let allocated =
        allocate_register_masked_no_operation_halt_image(adapter, image)?;
    let staged = copy_register_masked_no_operation_halt_image(
        adapter, image, allocated,
    )?;
    let sealed = protect_register_masked_no_operation_halt_image(
        adapter, staged, allocated,
    )?;
    synchronize_register_masked_no_operation_halt_image(
        adapter, sealed, allocated,
    )
}

/// Releases one ready collapsed v6 no-op/halt executable with retry ownership.
///
/// # Errors
///
/// Returns [`RegisterMaskedNoOperationHaltNativeExecutableReleaseFailure`] with
/// the exact ready executable when the adapter rejects release.
pub fn release_register_masked_no_operation_halt_native_executable<Adapter>(
    adapter: &mut Adapter,
    executable: ReadyRegisterMaskedNoOperationHaltNativeExecutable,
) -> RegisterMaskedNoOperationHaltNativeExecutableReleaseResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = executable.release_request();
    match adapter.release(request) {
        Ok(()) => Ok(()),
        Err(error) => Err(
            RegisterMaskedNoOperationHaltNativeExecutableReleaseFailure {
                error: Box::new(error),
                executable: Box::new(executable),
            },
        ),
    }
}

/// Loads one verified collapsed v6 no-operation pair image through the adapter.
///
/// Every post-allocation failure attempts exact release before returning. The
/// result remains collapsed-pair-specific with no binding or runner authority.
///
/// # Errors
///
/// Returns [`NativeExecutableLoadFailure`] when an adapter operation or
/// lifecycle admission fails.
pub fn load_register_masked_no_operation_pair_native_executable<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedRegisterMaskedNoOperationPairLoadImage,
) -> RegisterMaskedNoOperationPairNativeExecutableLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let allocated =
        allocate_register_masked_no_operation_pair_image(adapter, image)?;
    let staged = copy_register_masked_no_operation_pair_image(
        adapter, image, allocated,
    )?;
    let sealed = protect_register_masked_no_operation_pair_image(
        adapter, staged, allocated,
    )?;
    synchronize_register_masked_no_operation_pair_image(
        adapter, sealed, allocated,
    )
}

/// Releases one ready collapsed v6 no-operation pair executable with retry
/// ownership.
///
/// # Errors
///
/// Returns [`RegisterMaskedNoOperationPairNativeExecutableReleaseFailure`] with
/// the exact ready executable when the adapter rejects release.
pub fn release_register_masked_no_operation_pair_native_executable<Adapter>(
    adapter: &mut Adapter,
    executable: ReadyRegisterMaskedNoOperationPairNativeExecutable,
) -> RegisterMaskedNoOperationPairNativeExecutableReleaseResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = executable.release_request();
    match adapter.release(request) {
        Ok(()) => Ok(()),
        Err(error) => Err(
            RegisterMaskedNoOperationPairNativeExecutableReleaseFailure {
                error: Box::new(error),
                executable: Box::new(executable),
            },
        ),
    }
}

/// Loads one verified v6 rotate image through the platform adapter.
///
/// Every post-allocation failure attempts exact release before returning. The
/// result remains rotate-specific with no binding or runner authority.
///
/// # Errors
///
/// Returns [`NativeExecutableLoadFailure`] when an adapter operation or
/// lifecycle admission fails.
pub fn load_register_masked_rotate_native_executable<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedRegisterMaskedRotateLoadImage,
) -> RegisterMaskedRotateNativeExecutableLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let allocated = allocate_register_masked_rotate_image(adapter, image)?;
    let staged = copy_register_masked_rotate_image(adapter, image, allocated)?;
    let sealed =
        protect_register_masked_rotate_image(adapter, staged, allocated)?;
    synchronize_register_masked_rotate_image(adapter, sealed, allocated)
}

/// Releases one ready v6 rotate executable with retry ownership.
///
/// # Errors
///
/// Returns [`RegisterMaskedRotateNativeExecutableReleaseFailure`] with the
/// exact ready executable when the adapter rejects release.
pub fn release_register_masked_rotate_native_executable<Adapter>(
    adapter: &mut Adapter,
    executable: ReadyRegisterMaskedRotateNativeExecutable,
) -> RegisterMaskedRotateNativeExecutableReleaseResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = executable.release_request();
    match adapter.release(request) {
        Ok(()) => Ok(()),
        Err(error) => Err(RegisterMaskedRotateNativeExecutableReleaseFailure {
            error: Box::new(error),
            executable: Box::new(executable),
        }),
    }
}

/// Loads one verified non-graphical v6 image through the platform adapter.
///
/// Every post-allocation failure attempts exact release before returning. The
/// result remains a non-graphical-specific ready type with no invocation
/// binding or runner authority.
///
/// # Errors
///
/// Returns [`NativeExecutableLoadFailure`] when an adapter operation or
/// non-graphical lifecycle admission fails.
pub fn load_register_masked_non_graphical_native_executable<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedRegisterMaskedNonGraphicalLoadImage,
) -> RegisterMaskedNonGraphicalNativeExecutableLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let allocated =
        allocate_register_masked_non_graphical_image(adapter, image)?;
    let staged =
        copy_register_masked_non_graphical_image(adapter, image, allocated)?;
    let sealed = protect_register_masked_non_graphical_image(
        adapter, staged, allocated,
    )?;
    synchronize_register_masked_non_graphical_image(adapter, sealed, allocated)
}

/// Releases one ready non-graphical v6 executable with retry ownership.
///
/// # Errors
///
/// Returns [`RegisterMaskedNonGraphicalNativeExecutableReleaseFailure`] with
/// the exact ready executable when the adapter rejects release.
pub fn release_register_masked_non_graphical_native_executable<Adapter>(
    adapter: &mut Adapter,
    executable: ReadyRegisterMaskedNonGraphicalNativeExecutable,
) -> RegisterMaskedNonGraphicalNativeExecutableReleaseResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = executable.release_request();
    match adapter.release(request) {
        Ok(()) => Ok(()),
        Err(error) => {
            Err(RegisterMaskedNonGraphicalNativeExecutableReleaseFailure {
                error: Box::new(error),
                executable: Box::new(executable),
            })
        },
    }
}

/// Loads one verified image through an explicit caller-owned platform adapter.
///
/// Every post-allocation failure attempts the exact release request before
/// returning. A cleanup failure is retained without replacing the primary
/// cause.
///
/// # Errors
///
/// Returns [`NativeExecutableLoadFailure`] when any adapter operation or
/// lifecycle admission fails.
pub fn load_native_executable<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedDirectLoadImage,
) -> NativeExecutableLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let allocated = allocate_image(adapter, image)?;
    let staged = copy_image(adapter, image, allocated)?;
    let sealed = protect_image(adapter, staged, allocated)?;
    synchronize_image(adapter, sealed, allocated)
}

/// Releases one ready executable while preserving it for retry on failure.
///
/// # Errors
///
/// Returns [`NativeExecutableReleaseFailure`] with the original ready
/// executable when the adapter rejects the exact release request.
pub fn release_native_executable<Adapter>(
    adapter: &mut Adapter,
    executable: ReadyNativeExecutable,
) -> NativeExecutableReleaseResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = executable.release_request();
    match adapter.release(request) {
        Ok(()) => Ok(()),
        Err(error) => Err(NativeExecutableReleaseFailure {
            error: Box::new(error),
            executable: Box::new(executable),
        }),
    }
}

fn allocate_direct_fused_image<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedDirectFusedLoadImage,
) -> NativeExecutableLoadStepResult<AllocatedNativeMapping, Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = NativeExecutableAllocationRequest::new(
        image.allocation_len(),
        image.minimum_instruction_alignment(),
        image.policy().initial_permissions(),
    );
    let mapping = match adapter.allocate_writable(request) {
        Ok(mapping) => mapping,
        Err(error) => {
            return Err(NativeExecutableLoadFailure {
                cause: NativeExecutableLoadFailureCause::Adapter(Box::new(
                    error,
                )),
                phase: NativeExecutableLoadPhase::Allocate,
                release_error: None,
                release_request: None,
            });
        },
    };
    let release_request = NativeExecutableReleaseRequest::from_mapping(mapping);
    if let Err(error) = validate_direct_fused_writable_mapping(image, mapping) {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Allocate,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            release_request,
        ));
    }
    Ok(AllocatedNativeMapping { mapping, release_request })
}

fn allocate_execution_geometry_image<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedExecutionGeometryLoadImage,
) -> NativeExecutableLoadStepResult<AllocatedNativeMapping, Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = NativeExecutableAllocationRequest::new(
        image.allocation_len(),
        image.minimum_instruction_alignment(),
        image.policy().initial_permissions(),
    );
    let mapping = match adapter.allocate_writable(request) {
        Ok(mapping) => mapping,
        Err(error) => {
            return Err(NativeExecutableLoadFailure {
                cause: NativeExecutableLoadFailureCause::Adapter(Box::new(
                    error,
                )),
                phase: NativeExecutableLoadPhase::Allocate,
                release_error: None,
                release_request: None,
            });
        },
    };
    let release_request = NativeExecutableReleaseRequest::from_mapping(mapping);
    if let Err(error) =
        validate_execution_geometry_writable_mapping(image, mapping)
    {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Allocate,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            release_request,
        ));
    }
    Ok(AllocatedNativeMapping { mapping, release_request })
}

fn allocate_register_masked_image<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedRegisterMaskedLoadImage,
) -> NativeExecutableLoadStepResult<AllocatedNativeMapping, Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = NativeExecutableAllocationRequest::new(
        image.allocation_len(),
        image.minimum_instruction_alignment(),
        image.policy().initial_permissions(),
    );
    let mapping = match adapter.allocate_writable(request) {
        Ok(mapping) => mapping,
        Err(error) => {
            return Err(NativeExecutableLoadFailure {
                cause: NativeExecutableLoadFailureCause::Adapter(Box::new(
                    error,
                )),
                phase: NativeExecutableLoadPhase::Allocate,
                release_error: None,
                release_request: None,
            });
        },
    };
    let release_request = NativeExecutableReleaseRequest::from_mapping(mapping);
    if let Err(error) =
        validate_register_masked_writable_mapping(image, mapping)
    {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Allocate,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            release_request,
        ));
    }
    Ok(AllocatedNativeMapping { mapping, release_request })
}

fn allocate_register_masked_crazy_image<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedRegisterMaskedCrazyLoadImage,
) -> NativeExecutableLoadStepResult<AllocatedNativeMapping, Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = NativeExecutableAllocationRequest::new(
        image.allocation_len(),
        image.minimum_instruction_alignment(),
        image.policy().initial_permissions(),
    );
    let mapping = match adapter.allocate_writable(request) {
        Ok(mapping) => mapping,
        Err(error) => {
            return Err(NativeExecutableLoadFailure {
                cause: NativeExecutableLoadFailureCause::Adapter(Box::new(
                    error,
                )),
                phase: NativeExecutableLoadPhase::Allocate,
                release_error: None,
                release_request: None,
            });
        },
    };
    let release_request = NativeExecutableReleaseRequest::from_mapping(mapping);
    if let Err(error) =
        validate_register_masked_crazy_writable_mapping(image, mapping)
    {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Allocate,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            release_request,
        ));
    }
    Ok(AllocatedNativeMapping { mapping, release_request })
}

fn allocate_register_masked_output_image<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedRegisterMaskedOutputLoadImage,
) -> NativeExecutableLoadStepResult<AllocatedNativeMapping, Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = NativeExecutableAllocationRequest::new(
        image.allocation_len(),
        image.minimum_instruction_alignment(),
        image.policy().initial_permissions(),
    );
    let mapping = match adapter.allocate_writable(request) {
        Ok(mapping) => mapping,
        Err(error) => {
            return Err(NativeExecutableLoadFailure {
                cause: NativeExecutableLoadFailureCause::Adapter(Box::new(
                    error,
                )),
                phase: NativeExecutableLoadPhase::Allocate,
                release_error: None,
                release_request: None,
            });
        },
    };
    let release_request = NativeExecutableReleaseRequest::from_mapping(mapping);
    if let Err(error) =
        validate_register_masked_output_writable_mapping(image, mapping)
    {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Allocate,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            release_request,
        ));
    }
    Ok(AllocatedNativeMapping { mapping, release_request })
}

fn allocate_register_masked_no_operation_image<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedRegisterMaskedNoOperationLoadImage,
) -> NativeExecutableLoadStepResult<AllocatedNativeMapping, Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = NativeExecutableAllocationRequest::new(
        image.allocation_len(),
        image.minimum_instruction_alignment(),
        image.policy().initial_permissions(),
    );
    let mapping = match adapter.allocate_writable(request) {
        Ok(mapping) => mapping,
        Err(error) => {
            return Err(NativeExecutableLoadFailure {
                cause: NativeExecutableLoadFailureCause::Adapter(Box::new(
                    error,
                )),
                phase: NativeExecutableLoadPhase::Allocate,
                release_error: None,
                release_request: None,
            });
        },
    };
    let release_request = NativeExecutableReleaseRequest::from_mapping(mapping);
    if let Err(error) =
        validate_register_masked_no_operation_writable_mapping(image, mapping)
    {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Allocate,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            release_request,
        ));
    }
    Ok(AllocatedNativeMapping { mapping, release_request })
}

fn allocate_register_masked_no_operation_halt_image<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedRegisterMaskedNoOperationHaltLoadImage,
) -> NativeExecutableLoadStepResult<AllocatedNativeMapping, Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = NativeExecutableAllocationRequest::new(
        image.allocation_len(),
        image.minimum_instruction_alignment(),
        image.policy().initial_permissions(),
    );
    let mapping = match adapter.allocate_writable(request) {
        Ok(mapping) => mapping,
        Err(error) => {
            return Err(NativeExecutableLoadFailure {
                cause: NativeExecutableLoadFailureCause::Adapter(Box::new(
                    error,
                )),
                phase: NativeExecutableLoadPhase::Allocate,
                release_error: None,
                release_request: None,
            });
        },
    };
    let release_request = NativeExecutableReleaseRequest::from_mapping(mapping);
    if let Err(error) =
        validate_register_masked_no_operation_halt_writable_mapping(
            image, mapping,
        )
    {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Allocate,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            release_request,
        ));
    }
    Ok(AllocatedNativeMapping { mapping, release_request })
}

fn allocate_register_masked_no_operation_pair_image<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedRegisterMaskedNoOperationPairLoadImage,
) -> NativeExecutableLoadStepResult<AllocatedNativeMapping, Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = NativeExecutableAllocationRequest::new(
        image.allocation_len(),
        image.minimum_instruction_alignment(),
        image.policy().initial_permissions(),
    );
    let mapping = match adapter.allocate_writable(request) {
        Ok(mapping) => mapping,
        Err(error) => {
            return Err(NativeExecutableLoadFailure {
                cause: NativeExecutableLoadFailureCause::Adapter(Box::new(
                    error,
                )),
                phase: NativeExecutableLoadPhase::Allocate,
                release_error: None,
                release_request: None,
            });
        },
    };
    let release_request = NativeExecutableReleaseRequest::from_mapping(mapping);
    if let Err(error) =
        validate_register_masked_no_operation_pair_writable_mapping(
            image, mapping,
        )
    {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Allocate,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            release_request,
        ));
    }
    Ok(AllocatedNativeMapping { mapping, release_request })
}

fn allocate_register_masked_rotate_image<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedRegisterMaskedRotateLoadImage,
) -> NativeExecutableLoadStepResult<AllocatedNativeMapping, Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = NativeExecutableAllocationRequest::new(
        image.allocation_len(),
        image.minimum_instruction_alignment(),
        image.policy().initial_permissions(),
    );
    let mapping = match adapter.allocate_writable(request) {
        Ok(mapping) => mapping,
        Err(error) => {
            return Err(NativeExecutableLoadFailure {
                cause: NativeExecutableLoadFailureCause::Adapter(Box::new(
                    error,
                )),
                phase: NativeExecutableLoadPhase::Allocate,
                release_error: None,
                release_request: None,
            });
        },
    };
    let release_request = NativeExecutableReleaseRequest::from_mapping(mapping);
    if let Err(error) =
        validate_register_masked_rotate_writable_mapping(image, mapping)
    {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Allocate,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            release_request,
        ));
    }
    Ok(AllocatedNativeMapping { mapping, release_request })
}

fn allocate_register_masked_non_graphical_image<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedRegisterMaskedNonGraphicalLoadImage,
) -> NativeExecutableLoadStepResult<AllocatedNativeMapping, Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = NativeExecutableAllocationRequest::new(
        image.allocation_len(),
        image.minimum_instruction_alignment(),
        image.policy().initial_permissions(),
    );
    let mapping = match adapter.allocate_writable(request) {
        Ok(mapping) => mapping,
        Err(error) => {
            return Err(NativeExecutableLoadFailure {
                cause: NativeExecutableLoadFailureCause::Adapter(Box::new(
                    error,
                )),
                phase: NativeExecutableLoadPhase::Allocate,
                release_error: None,
                release_request: None,
            });
        },
    };
    let release_request = NativeExecutableReleaseRequest::from_mapping(mapping);
    if let Err(error) =
        validate_register_masked_non_graphical_writable_mapping(image, mapping)
    {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Allocate,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            release_request,
        ));
    }
    Ok(AllocatedNativeMapping { mapping, release_request })
}

fn allocate_image<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedDirectLoadImage,
) -> NativeExecutableLoadStepResult<AllocatedNativeMapping, Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = NativeExecutableAllocationRequest::new(
        image.allocation_len(),
        image.minimum_instruction_alignment(),
        image.policy().initial_permissions(),
    );
    let mapping = match adapter.allocate_writable(request) {
        Ok(mapping) => mapping,
        Err(error) => {
            return Err(NativeExecutableLoadFailure {
                cause: NativeExecutableLoadFailureCause::Adapter(Box::new(
                    error,
                )),
                phase: NativeExecutableLoadPhase::Allocate,
                release_error: None,
                release_request: None,
            });
        },
    };
    let release_request = NativeExecutableReleaseRequest::from_mapping(mapping);
    if let Err(error) = validate_writable_mapping(image, mapping) {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Allocate,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            release_request,
        ));
    }
    Ok(AllocatedNativeMapping { mapping, release_request })
}

fn copy_direct_fused_image<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedDirectFusedLoadImage,
    allocated: AllocatedNativeMapping,
) -> NativeExecutableLoadStepResult<
    StagedDirectFusedNativeExecutable,
    Adapter::Error,
>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let copied = match adapter.copy_code(allocated.mapping, image.code()) {
        Ok(copied) => copied,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Copy,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    if copied.mapping_id() != allocated.mapping.mapping_id() {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Evidence(Box::new(
                NativeExecutableOperationEvidenceError::CopyMappingIdentity,
            )),
            allocated.release_request,
        ));
    }
    if copied.start_address() != allocated.mapping.base_address() {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Evidence(Box::new(
                NativeExecutableOperationEvidenceError::CopyStartAddress,
            )),
            allocated.release_request,
        ));
    }
    StagedDirectFusedNativeExecutable::stage(
        image,
        allocated.mapping,
        copied.copied_code(),
    )
    .map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}

fn copy_execution_geometry_image<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedExecutionGeometryLoadImage,
    allocated: AllocatedNativeMapping,
) -> NativeExecutableLoadStepResult<
    StagedExecutionGeometryNativeExecutable,
    Adapter::Error,
>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let copied = match adapter.copy_code(allocated.mapping, image.code()) {
        Ok(copied) => copied,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Copy,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    if copied.mapping_id() != allocated.mapping.mapping_id() {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Evidence(Box::new(
                NativeExecutableOperationEvidenceError::CopyMappingIdentity,
            )),
            allocated.release_request,
        ));
    }
    if copied.start_address() != allocated.mapping.base_address() {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Evidence(Box::new(
                NativeExecutableOperationEvidenceError::CopyStartAddress,
            )),
            allocated.release_request,
        ));
    }
    StagedExecutionGeometryNativeExecutable::stage(
        image,
        allocated.mapping,
        copied.copied_code(),
    )
    .map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}

fn copy_register_masked_image<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedRegisterMaskedLoadImage,
    allocated: AllocatedNativeMapping,
) -> NativeExecutableLoadStepResult<
    StagedRegisterMaskedNativeExecutable,
    Adapter::Error,
>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let copied = match adapter.copy_code(allocated.mapping, image.code()) {
        Ok(copied) => copied,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Copy,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    if copied.mapping_id() != allocated.mapping.mapping_id() {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Evidence(Box::new(
                NativeExecutableOperationEvidenceError::CopyMappingIdentity,
            )),
            allocated.release_request,
        ));
    }
    if copied.start_address() != allocated.mapping.base_address() {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Evidence(Box::new(
                NativeExecutableOperationEvidenceError::CopyStartAddress,
            )),
            allocated.release_request,
        ));
    }
    StagedRegisterMaskedNativeExecutable::stage(
        image,
        allocated.mapping,
        copied.copied_code(),
    )
    .map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}

fn copy_register_masked_crazy_image<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedRegisterMaskedCrazyLoadImage,
    allocated: AllocatedNativeMapping,
) -> NativeExecutableLoadStepResult<
    StagedRegisterMaskedCrazyNativeExecutable,
    Adapter::Error,
>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let copied = match adapter.copy_code(allocated.mapping, image.code()) {
        Ok(copied) => copied,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Copy,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    if copied.mapping_id() != allocated.mapping.mapping_id() {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Evidence(Box::new(
                NativeExecutableOperationEvidenceError::CopyMappingIdentity,
            )),
            allocated.release_request,
        ));
    }
    if copied.start_address() != allocated.mapping.base_address() {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Evidence(Box::new(
                NativeExecutableOperationEvidenceError::CopyStartAddress,
            )),
            allocated.release_request,
        ));
    }
    StagedRegisterMaskedCrazyNativeExecutable::stage(
        image,
        allocated.mapping,
        copied.copied_code(),
    )
    .map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}

fn copy_register_masked_output_image<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedRegisterMaskedOutputLoadImage,
    allocated: AllocatedNativeMapping,
) -> NativeExecutableLoadStepResult<
    StagedRegisterMaskedOutputNativeExecutable,
    Adapter::Error,
>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let copied = match adapter.copy_code(allocated.mapping, image.code()) {
        Ok(copied) => copied,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Copy,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    if copied.mapping_id() != allocated.mapping.mapping_id() {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Evidence(Box::new(
                NativeExecutableOperationEvidenceError::CopyMappingIdentity,
            )),
            allocated.release_request,
        ));
    }
    if copied.start_address() != allocated.mapping.base_address() {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Evidence(Box::new(
                NativeExecutableOperationEvidenceError::CopyStartAddress,
            )),
            allocated.release_request,
        ));
    }
    StagedRegisterMaskedOutputNativeExecutable::stage(
        image,
        allocated.mapping,
        copied.copied_code(),
    )
    .map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}

fn copy_register_masked_no_operation_image<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedRegisterMaskedNoOperationLoadImage,
    allocated: AllocatedNativeMapping,
) -> NativeExecutableLoadStepResult<
    StagedRegisterMaskedNoOperationNativeExecutable,
    Adapter::Error,
>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let copied = match adapter.copy_code(allocated.mapping, image.code()) {
        Ok(copied) => copied,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Copy,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    if copied.mapping_id() != allocated.mapping.mapping_id() {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Evidence(Box::new(
                NativeExecutableOperationEvidenceError::CopyMappingIdentity,
            )),
            allocated.release_request,
        ));
    }
    if copied.start_address() != allocated.mapping.base_address() {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Evidence(Box::new(
                NativeExecutableOperationEvidenceError::CopyStartAddress,
            )),
            allocated.release_request,
        ));
    }
    StagedRegisterMaskedNoOperationNativeExecutable::stage(
        image,
        allocated.mapping,
        copied.copied_code(),
    )
    .map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}

fn copy_register_masked_no_operation_halt_image<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedRegisterMaskedNoOperationHaltLoadImage,
    allocated: AllocatedNativeMapping,
) -> NativeExecutableLoadStepResult<
    StagedRegisterMaskedNoOperationHaltNativeExecutable,
    Adapter::Error,
>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let copied = match adapter.copy_code(allocated.mapping, image.code()) {
        Ok(copied) => copied,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Copy,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    if copied.mapping_id() != allocated.mapping.mapping_id() {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Evidence(Box::new(
                NativeExecutableOperationEvidenceError::CopyMappingIdentity,
            )),
            allocated.release_request,
        ));
    }
    if copied.start_address() != allocated.mapping.base_address() {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Evidence(Box::new(
                NativeExecutableOperationEvidenceError::CopyStartAddress,
            )),
            allocated.release_request,
        ));
    }
    StagedRegisterMaskedNoOperationHaltNativeExecutable::stage(
        image,
        allocated.mapping,
        copied.copied_code(),
    )
    .map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}

fn copy_register_masked_no_operation_pair_image<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedRegisterMaskedNoOperationPairLoadImage,
    allocated: AllocatedNativeMapping,
) -> NativeExecutableLoadStepResult<
    StagedRegisterMaskedNoOperationPairNativeExecutable,
    Adapter::Error,
>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let copied = match adapter.copy_code(allocated.mapping, image.code()) {
        Ok(copied) => copied,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Copy,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    if copied.mapping_id() != allocated.mapping.mapping_id() {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Evidence(Box::new(
                NativeExecutableOperationEvidenceError::CopyMappingIdentity,
            )),
            allocated.release_request,
        ));
    }
    if copied.start_address() != allocated.mapping.base_address() {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Evidence(Box::new(
                NativeExecutableOperationEvidenceError::CopyStartAddress,
            )),
            allocated.release_request,
        ));
    }
    StagedRegisterMaskedNoOperationPairNativeExecutable::stage(
        image,
        allocated.mapping,
        copied.copied_code(),
    )
    .map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}

fn copy_register_masked_rotate_image<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedRegisterMaskedRotateLoadImage,
    allocated: AllocatedNativeMapping,
) -> NativeExecutableLoadStepResult<
    StagedRegisterMaskedRotateNativeExecutable,
    Adapter::Error,
>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let copied = match adapter.copy_code(allocated.mapping, image.code()) {
        Ok(copied) => copied,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Copy,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    if copied.mapping_id() != allocated.mapping.mapping_id() {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Evidence(Box::new(
                NativeExecutableOperationEvidenceError::CopyMappingIdentity,
            )),
            allocated.release_request,
        ));
    }
    if copied.start_address() != allocated.mapping.base_address() {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Evidence(Box::new(
                NativeExecutableOperationEvidenceError::CopyStartAddress,
            )),
            allocated.release_request,
        ));
    }
    StagedRegisterMaskedRotateNativeExecutable::stage(
        image,
        allocated.mapping,
        copied.copied_code(),
    )
    .map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}

fn copy_register_masked_non_graphical_image<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedRegisterMaskedNonGraphicalLoadImage,
    allocated: AllocatedNativeMapping,
) -> NativeExecutableLoadStepResult<
    StagedRegisterMaskedNonGraphicalNativeExecutable,
    Adapter::Error,
>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let copied = match adapter.copy_code(allocated.mapping, image.code()) {
        Ok(copied) => copied,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Copy,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    if copied.mapping_id() != allocated.mapping.mapping_id() {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Evidence(Box::new(
                NativeExecutableOperationEvidenceError::CopyMappingIdentity,
            )),
            allocated.release_request,
        ));
    }
    if copied.start_address() != allocated.mapping.base_address() {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Evidence(Box::new(
                NativeExecutableOperationEvidenceError::CopyStartAddress,
            )),
            allocated.release_request,
        ));
    }
    StagedRegisterMaskedNonGraphicalNativeExecutable::stage(
        image,
        allocated.mapping,
        copied.copied_code(),
    )
    .map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}

fn copy_image<Adapter>(
    adapter: &mut Adapter,
    image: &VerifiedDirectLoadImage,
    allocated: AllocatedNativeMapping,
) -> NativeExecutableLoadStepResult<StagedNativeExecutable, Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let copied = match adapter.copy_code(allocated.mapping, image.code()) {
        Ok(copied) => copied,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Copy,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    if copied.mapping_id() != allocated.mapping.mapping_id() {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Evidence(Box::new(
                NativeExecutableOperationEvidenceError::CopyMappingIdentity,
            )),
            allocated.release_request,
        ));
    }
    if copied.start_address() != allocated.mapping.base_address() {
        return Err(fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Evidence(Box::new(
                NativeExecutableOperationEvidenceError::CopyStartAddress,
            )),
            allocated.release_request,
        ));
    }
    StagedNativeExecutable::stage(
        image,
        allocated.mapping,
        copied.copied_code(),
    )
    .map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}

fn fail_with_release<Adapter>(
    adapter: &mut Adapter,
    phase: NativeExecutableLoadPhase,
    cause: NativeExecutableLoadFailureCause<Adapter::Error>,
    release_request: NativeExecutableReleaseRequest,
) -> NativeExecutableLoadFailure<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    NativeExecutableLoadFailure {
        cause,
        phase,
        release_error: adapter.release(release_request).err().map(Box::new),
        release_request: Some(release_request),
    }
}

fn protect_direct_fused_image<Adapter>(
    adapter: &mut Adapter,
    staged: StagedDirectFusedNativeExecutable,
    allocated: AllocatedNativeMapping,
) -> NativeExecutableLoadStepResult<
    SealedDirectFusedNativeExecutable,
    Adapter::Error,
>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let report = match adapter.protect_read_execute(allocated.mapping) {
        Ok(report) => report,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Protect,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    staged.admit_read_execute(report).map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Protect,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}

fn protect_execution_geometry_image<Adapter>(
    adapter: &mut Adapter,
    staged: StagedExecutionGeometryNativeExecutable,
    allocated: AllocatedNativeMapping,
) -> NativeExecutableLoadStepResult<
    SealedExecutionGeometryNativeExecutable,
    Adapter::Error,
>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let report = match adapter.protect_read_execute(allocated.mapping) {
        Ok(report) => report,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Protect,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    staged.admit_read_execute(report).map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Protect,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}

fn protect_register_masked_image<Adapter>(
    adapter: &mut Adapter,
    staged: StagedRegisterMaskedNativeExecutable,
    allocated: AllocatedNativeMapping,
) -> NativeExecutableLoadStepResult<
    SealedRegisterMaskedNativeExecutable,
    Adapter::Error,
>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let report = match adapter.protect_read_execute(allocated.mapping) {
        Ok(report) => report,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Protect,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    staged.admit_read_execute(report).map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Protect,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}

fn protect_register_masked_crazy_image<Adapter>(
    adapter: &mut Adapter,
    staged: StagedRegisterMaskedCrazyNativeExecutable,
    allocated: AllocatedNativeMapping,
) -> NativeExecutableLoadStepResult<
    SealedRegisterMaskedCrazyNativeExecutable,
    Adapter::Error,
>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let report = match adapter.protect_read_execute(allocated.mapping) {
        Ok(report) => report,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Protect,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    staged.admit_read_execute(report).map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Protect,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}

fn protect_register_masked_output_image<Adapter>(
    adapter: &mut Adapter,
    staged: StagedRegisterMaskedOutputNativeExecutable,
    allocated: AllocatedNativeMapping,
) -> NativeExecutableLoadStepResult<
    SealedRegisterMaskedOutputNativeExecutable,
    Adapter::Error,
>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let report = match adapter.protect_read_execute(allocated.mapping) {
        Ok(report) => report,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Protect,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    staged.admit_read_execute(report).map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Protect,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}

fn protect_register_masked_no_operation_image<Adapter>(
    adapter: &mut Adapter,
    staged: StagedRegisterMaskedNoOperationNativeExecutable,
    allocated: AllocatedNativeMapping,
) -> NativeExecutableLoadStepResult<
    SealedRegisterMaskedNoOperationNativeExecutable,
    Adapter::Error,
>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let report = match adapter.protect_read_execute(allocated.mapping) {
        Ok(report) => report,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Protect,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    staged.admit_read_execute(report).map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Protect,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}

fn protect_register_masked_no_operation_halt_image<Adapter>(
    adapter: &mut Adapter,
    staged: StagedRegisterMaskedNoOperationHaltNativeExecutable,
    allocated: AllocatedNativeMapping,
) -> NativeExecutableLoadStepResult<
    SealedRegisterMaskedNoOperationHaltNativeExecutable,
    Adapter::Error,
>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let report = match adapter.protect_read_execute(allocated.mapping) {
        Ok(report) => report,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Protect,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    staged.admit_read_execute(report).map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Protect,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}

fn protect_register_masked_no_operation_pair_image<Adapter>(
    adapter: &mut Adapter,
    staged: StagedRegisterMaskedNoOperationPairNativeExecutable,
    allocated: AllocatedNativeMapping,
) -> NativeExecutableLoadStepResult<
    SealedRegisterMaskedNoOperationPairNativeExecutable,
    Adapter::Error,
>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let report = match adapter.protect_read_execute(allocated.mapping) {
        Ok(report) => report,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Protect,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    staged.admit_read_execute(report).map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Protect,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}

fn protect_register_masked_rotate_image<Adapter>(
    adapter: &mut Adapter,
    staged: StagedRegisterMaskedRotateNativeExecutable,
    allocated: AllocatedNativeMapping,
) -> NativeExecutableLoadStepResult<
    SealedRegisterMaskedRotateNativeExecutable,
    Adapter::Error,
>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let report = match adapter.protect_read_execute(allocated.mapping) {
        Ok(report) => report,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Protect,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    staged.admit_read_execute(report).map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Protect,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}

fn protect_register_masked_non_graphical_image<Adapter>(
    adapter: &mut Adapter,
    staged: StagedRegisterMaskedNonGraphicalNativeExecutable,
    allocated: AllocatedNativeMapping,
) -> NativeExecutableLoadStepResult<
    SealedRegisterMaskedNonGraphicalNativeExecutable,
    Adapter::Error,
>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let report = match adapter.protect_read_execute(allocated.mapping) {
        Ok(report) => report,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Protect,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    staged.admit_read_execute(report).map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Protect,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}

fn protect_image<Adapter>(
    adapter: &mut Adapter,
    staged: StagedNativeExecutable,
    allocated: AllocatedNativeMapping,
) -> NativeExecutableLoadStepResult<SealedNativeExecutable, Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let report = match adapter.protect_read_execute(allocated.mapping) {
        Ok(report) => report,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Protect,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    staged.admit_read_execute(report).map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Protect,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}

fn synchronize_direct_fused_image<Adapter>(
    adapter: &mut Adapter,
    sealed: SealedDirectFusedNativeExecutable,
    allocated: AllocatedNativeMapping,
) -> DirectFusedNativeExecutableLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = NativeInstructionSyncRequest::new(
        sealed.mapping().mapping_id(),
        sealed.mapping().base_address(),
        sealed.image().allocation_len(),
    );
    let report = match adapter.synchronize_instructions(request) {
        Ok(report) => report,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Synchronize,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    sealed.admit_instruction_sync(report).map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Synchronize,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}

fn synchronize_execution_geometry_image<Adapter>(
    adapter: &mut Adapter,
    sealed: SealedExecutionGeometryNativeExecutable,
    allocated: AllocatedNativeMapping,
) -> ExecutionGeometryNativeExecutableLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = NativeInstructionSyncRequest::new(
        sealed.mapping().mapping_id(),
        sealed.mapping().base_address(),
        sealed.image().allocation_len(),
    );
    let report = match adapter.synchronize_instructions(request) {
        Ok(report) => report,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Synchronize,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    sealed.admit_instruction_sync(report).map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Synchronize,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}

fn synchronize_register_masked_image<Adapter>(
    adapter: &mut Adapter,
    sealed: SealedRegisterMaskedNativeExecutable,
    allocated: AllocatedNativeMapping,
) -> RegisterMaskedNativeExecutableLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = NativeInstructionSyncRequest::new(
        sealed.mapping().mapping_id(),
        sealed.mapping().base_address(),
        sealed.image().allocation_len(),
    );
    let report = match adapter.synchronize_instructions(request) {
        Ok(report) => report,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Synchronize,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    sealed.admit_instruction_sync(report).map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Synchronize,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}

fn synchronize_register_masked_crazy_image<Adapter>(
    adapter: &mut Adapter,
    sealed: SealedRegisterMaskedCrazyNativeExecutable,
    allocated: AllocatedNativeMapping,
) -> RegisterMaskedCrazyNativeExecutableLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = NativeInstructionSyncRequest::new(
        sealed.mapping().mapping_id(),
        sealed.mapping().base_address(),
        sealed.image().allocation_len(),
    );
    let report = match adapter.synchronize_instructions(request) {
        Ok(report) => report,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Synchronize,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    sealed.admit_instruction_sync(report).map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Synchronize,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}

fn synchronize_register_masked_output_image<Adapter>(
    adapter: &mut Adapter,
    sealed: SealedRegisterMaskedOutputNativeExecutable,
    allocated: AllocatedNativeMapping,
) -> RegisterMaskedOutputNativeExecutableLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = NativeInstructionSyncRequest::new(
        sealed.mapping().mapping_id(),
        sealed.mapping().base_address(),
        sealed.image().allocation_len(),
    );
    let report = match adapter.synchronize_instructions(request) {
        Ok(report) => report,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Synchronize,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    sealed.admit_instruction_sync(report).map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Synchronize,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}

fn synchronize_register_masked_no_operation_image<Adapter>(
    adapter: &mut Adapter,
    sealed: SealedRegisterMaskedNoOperationNativeExecutable,
    allocated: AllocatedNativeMapping,
) -> RegisterMaskedNoOperationNativeExecutableLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = NativeInstructionSyncRequest::new(
        sealed.mapping().mapping_id(),
        sealed.mapping().base_address(),
        sealed.image().allocation_len(),
    );
    let report = match adapter.synchronize_instructions(request) {
        Ok(report) => report,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Synchronize,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    sealed.admit_instruction_sync(report).map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Synchronize,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}

fn synchronize_register_masked_no_operation_halt_image<Adapter>(
    adapter: &mut Adapter,
    sealed: SealedRegisterMaskedNoOperationHaltNativeExecutable,
    allocated: AllocatedNativeMapping,
) -> RegisterMaskedNoOperationHaltNativeExecutableLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = NativeInstructionSyncRequest::new(
        sealed.mapping().mapping_id(),
        sealed.mapping().base_address(),
        sealed.image().allocation_len(),
    );
    let report = match adapter.synchronize_instructions(request) {
        Ok(report) => report,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Synchronize,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    sealed.admit_instruction_sync(report).map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Synchronize,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}

fn synchronize_register_masked_no_operation_pair_image<Adapter>(
    adapter: &mut Adapter,
    sealed: SealedRegisterMaskedNoOperationPairNativeExecutable,
    allocated: AllocatedNativeMapping,
) -> RegisterMaskedNoOperationPairNativeExecutableLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = NativeInstructionSyncRequest::new(
        sealed.mapping().mapping_id(),
        sealed.mapping().base_address(),
        sealed.image().allocation_len(),
    );
    let report = match adapter.synchronize_instructions(request) {
        Ok(report) => report,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Synchronize,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    sealed.admit_instruction_sync(report).map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Synchronize,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}

fn synchronize_register_masked_rotate_image<Adapter>(
    adapter: &mut Adapter,
    sealed: SealedRegisterMaskedRotateNativeExecutable,
    allocated: AllocatedNativeMapping,
) -> RegisterMaskedRotateNativeExecutableLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = NativeInstructionSyncRequest::new(
        sealed.mapping().mapping_id(),
        sealed.mapping().base_address(),
        sealed.image().allocation_len(),
    );
    let report = match adapter.synchronize_instructions(request) {
        Ok(report) => report,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Synchronize,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    sealed.admit_instruction_sync(report).map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Synchronize,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}

fn synchronize_register_masked_non_graphical_image<Adapter>(
    adapter: &mut Adapter,
    sealed: SealedRegisterMaskedNonGraphicalNativeExecutable,
    allocated: AllocatedNativeMapping,
) -> RegisterMaskedNonGraphicalNativeExecutableLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = NativeInstructionSyncRequest::new(
        sealed.mapping().mapping_id(),
        sealed.mapping().base_address(),
        sealed.image().allocation_len(),
    );
    let report = match adapter.synchronize_instructions(request) {
        Ok(report) => report,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Synchronize,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    sealed.admit_instruction_sync(report).map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Synchronize,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}

fn synchronize_image<Adapter>(
    adapter: &mut Adapter,
    sealed: SealedNativeExecutable,
    allocated: AllocatedNativeMapping,
) -> NativeExecutableLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request = NativeInstructionSyncRequest::new(
        sealed.mapping().mapping_id(),
        sealed.mapping().base_address(),
        sealed.image().allocation_len(),
    );
    let report = match adapter.synchronize_instructions(request) {
        Ok(report) => report,
        Err(error) => {
            return Err(fail_with_release(
                adapter,
                NativeExecutableLoadPhase::Synchronize,
                NativeExecutableLoadFailureCause::Adapter(Box::new(error)),
                allocated.release_request,
            ));
        },
    };
    sealed.admit_instruction_sync(report).map_err(|error| {
        fail_with_release(
            adapter,
            NativeExecutableLoadPhase::Synchronize,
            NativeExecutableLoadFailureCause::Lifecycle(Box::new(error)),
            allocated.release_request,
        )
    })
}
