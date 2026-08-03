// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
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
    NativeInstructionSyncReport, ReadyNativeExecutable, SealedNativeExecutable,
    StagedNativeExecutable, validate_writable_mapping,
};
use super::loader::{NativeExecutablePermission, VerifiedDirectLoadImage};

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
