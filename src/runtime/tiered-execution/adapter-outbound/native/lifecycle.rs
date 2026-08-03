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
//   - Safe ordered admission of executable mapping lifecycle evidence.
// - Must-Not:
//   - Allocate pages, change permissions, synchronize instructions, or call
//   - machine code.
// - Allows:
//   - Inputs: verified load images and exact platform-operation reports.
//   - Outputs: staged, sealed, synchronized, and release-bound typed states.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - A concrete operating-system executable-memory adapter is introduced.
// - Merge-When:
//   - One platform owner subsumes mapping operations and lifecycle admission.
// - Summary:
//   - Makes RW-to-RX-to-synchronized ordering explicit and fail closed.
// - Description:
//   - Binds every report to one mapping, image, address range, and exact key.
// - Usage:
//   - Platform adapters report completed operations; this module admits order.
// - Defaults:
//   - Any permission, identity, byte, capacity, or range drift is rejected.
//

//! Safe typestate admission for a future executable-memory platform adapter.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::num::{NonZeroU64, NonZeroUsize};

use super::loader::{NativeExecutablePermission, VerifiedDirectLoadImage};
use crate::execution_cache::{NativeArtifactKey, NativeTargetIdentity};

/// Stable non-zero identity assigned by one platform mapping owner.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct NativeExecutableMappingId(NonZeroU64);

/// Exact observed state of one platform executable-memory mapping.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeExecutableMappingReport {
    base_address: NonZeroUsize,
    mapped_len: usize,
    mapping_id: NativeExecutableMappingId,
    permissions: NativeExecutablePermission,
}

/// Exact instruction-cache synchronization report for one mapping range.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeInstructionSyncReport {
    byte_len: usize,
    mapping_id: NativeExecutableMappingId,
    start_address: NonZeroUsize,
}

/// Exact mapping release request retained by a synchronized executable.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeExecutableReleaseRequest {
    base_address: NonZeroUsize,
    mapped_len: usize,
    mapping_id: NativeExecutableMappingId,
}

/// Failure while admitting one ordered executable mapping transition.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeExecutableLifecycleError {
    /// Address arithmetic overflowed the host address representation.
    AddressOverflow,
    /// Writable mapping bytes differ from the exact verified code image.
    CodeImage,
    /// The exact entrypoint lies outside the admitted mapping range.
    EntryRange,
    /// Mapping base address violates the target instruction alignment.
    MappingAlignment,
    /// Mapping cannot contain the complete verified code image.
    MappingCapacity,
    /// A later report refers to a different mapping identity or range.
    MappingIdentity,
    /// A lifecycle report names permissions invalid for its transition.
    Permissions,
    /// Instruction synchronization covered a different mapping byte range.
    SynchronizationRange,
}

/// Verified bytes admitted in one exact writable staging mapping.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct StagedNativeExecutable {
    image: VerifiedDirectLoadImage,
    mapping: NativeExecutableMappingReport,
}

/// Exact mapping admitted after its RW-to-RX permission transition.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SealedNativeExecutable {
    image: VerifiedDirectLoadImage,
    mapping: NativeExecutableMappingReport,
}

/// Exact RX mapping admitted after mandatory instruction synchronization.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ReadyNativeExecutable {
    entry_address: NonZeroUsize,
    image: VerifiedDirectLoadImage,
    mapping: NativeExecutableMappingReport,
}

impl NativeExecutableMappingId {
    /// Returns the underlying non-zero platform mapping identity.
    #[must_use]
    pub const fn get(self) -> u64 {
        self.0.get()
    }

    /// Constructs one mapping identity, rejecting zero.
    #[must_use]
    pub const fn new(value: u64) -> Option<Self> {
        match NonZeroU64::new(value) {
            Some(non_zero) => Some(Self(non_zero)),
            None => None,
        }
    }
}

impl NativeExecutableMappingReport {
    /// Returns the non-zero mapping base address.
    #[must_use]
    pub const fn base_address(self) -> NonZeroUsize {
        self.base_address
    }

    /// Returns the complete mapped byte capacity.
    #[must_use]
    pub const fn mapped_len(self) -> usize {
        self.mapped_len
    }

    /// Returns the exact platform mapping identity.
    #[must_use]
    pub const fn mapping_id(self) -> NativeExecutableMappingId {
        self.mapping_id
    }

    /// Constructs one exact platform mapping report.
    #[must_use]
    pub const fn new(
        mapping_id: NativeExecutableMappingId,
        base_address: NonZeroUsize,
        mapped_len: usize,
        permissions: NativeExecutablePermission,
    ) -> Self {
        Self {
            base_address,
            mapped_len,
            mapping_id,
            permissions,
        }
    }

    /// Returns the observed page permissions.
    #[must_use]
    pub const fn permissions(self) -> NativeExecutablePermission {
        self.permissions
    }
}

impl NativeInstructionSyncReport {
    /// Returns the synchronized byte length.
    #[must_use]
    pub const fn byte_len(self) -> usize {
        self.byte_len
    }

    /// Returns the exact platform mapping identity.
    #[must_use]
    pub const fn mapping_id(self) -> NativeExecutableMappingId {
        self.mapping_id
    }

    /// Constructs one exact instruction synchronization report.
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

    /// Returns the synchronized range start address.
    #[must_use]
    pub const fn start_address(self) -> NonZeroUsize {
        self.start_address
    }
}

impl NativeExecutableReleaseRequest {
    /// Returns the exact mapping base address to release.
    #[must_use]
    pub const fn base_address(self) -> NonZeroUsize {
        self.base_address
    }

    /// Returns the complete mapped byte length to release.
    #[must_use]
    pub const fn mapped_len(self) -> usize {
        self.mapped_len
    }

    /// Returns the exact mapping identity to release.
    #[must_use]
    pub const fn mapping_id(self) -> NativeExecutableMappingId {
        self.mapping_id
    }
}

impl Display for NativeExecutableLifecycleError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::AddressOverflow => "native executable address overflowed",
            Self::CodeImage => "native executable staging bytes differ",
            Self::EntryRange => "native executable entrypoint is out of range",
            Self::MappingAlignment => {
                "native executable mapping base is misaligned"
            },
            Self::MappingCapacity => {
                "native executable mapping capacity is insufficient"
            },
            Self::MappingIdentity => {
                "native executable mapping identity drifted"
            },
            Self::Permissions => "native executable permissions are invalid",
            Self::SynchronizationRange => {
                "native executable synchronization range drifted"
            },
        })
    }
}

impl StagedNativeExecutable {
    /// Admits the exact RW-to-RX transition for this same mapping.
    ///
    /// # Errors
    ///
    /// Returns [`NativeExecutableLifecycleError`] when the mapping identity,
    /// range, or final permissions differ.
    pub fn admit_read_execute(
        self,
        mapping: NativeExecutableMappingReport,
    ) -> Result<SealedNativeExecutable, NativeExecutableLifecycleError> {
        if !same_mapping(self.mapping, mapping) {
            return Err(NativeExecutableLifecycleError::MappingIdentity);
        }
        if mapping.permissions() != self.image.policy().final_permissions() {
            return Err(NativeExecutableLifecycleError::Permissions);
        }
        Ok(SealedNativeExecutable {
            image: self.image,
            mapping,
        })
    }

    /// Returns the exact verified load image retained by this state.
    #[must_use]
    pub const fn image(&self) -> &VerifiedDirectLoadImage {
        &self.image
    }

    /// Returns the exact writable mapping report retained by this state.
    #[must_use]
    pub const fn mapping(&self) -> NativeExecutableMappingReport {
        self.mapping
    }

    /// Admits exact copied code in one writable platform mapping.
    ///
    /// # Errors
    ///
    /// Returns [`NativeExecutableLifecycleError`] when permissions, bytes,
    /// alignment, capacity, address arithmetic, or entry range disagree.
    pub fn stage(
        image: &VerifiedDirectLoadImage,
        mapping: NativeExecutableMappingReport,
        copied_code: &[u8],
    ) -> Result<Self, NativeExecutableLifecycleError> {
        if mapping.permissions() != image.policy().initial_permissions() {
            return Err(NativeExecutableLifecycleError::Permissions);
        }
        if copied_code != image.code() {
            return Err(NativeExecutableLifecycleError::CodeImage);
        }
        if mapping.mapped_len() < image.allocation_len() {
            return Err(NativeExecutableLifecycleError::MappingCapacity);
        }
        if !is_aligned(
            mapping.base_address().get(),
            image.minimum_instruction_alignment(),
        ) {
            return Err(NativeExecutableLifecycleError::MappingAlignment);
        }
        validate_mapping_ranges(image, mapping)?;
        Ok(Self {
            image: image.clone(),
            mapping,
        })
    }
}

impl SealedNativeExecutable {
    /// Admits exact instruction synchronization for the complete code range.
    ///
    /// # Errors
    ///
    /// Returns [`NativeExecutableLifecycleError`] when identity or synchronized
    /// range differs from the exact executable image.
    pub fn admit_instruction_sync(
        self,
        report: NativeInstructionSyncReport,
    ) -> Result<ReadyNativeExecutable, NativeExecutableLifecycleError> {
        if report.mapping_id() != self.mapping.mapping_id() {
            return Err(NativeExecutableLifecycleError::MappingIdentity);
        }
        if report.start_address() != self.mapping.base_address()
            || report.byte_len() != self.image.allocation_len()
        {
            return Err(NativeExecutableLifecycleError::SynchronizationRange);
        }
        let entry_address = entry_address(&self.image, self.mapping)?;
        Ok(ReadyNativeExecutable {
            entry_address,
            image: self.image,
            mapping: self.mapping,
        })
    }

    /// Returns the exact verified load image retained by this state.
    #[must_use]
    pub const fn image(&self) -> &VerifiedDirectLoadImage {
        &self.image
    }

    /// Returns the exact read-execute mapping report retained by this state.
    #[must_use]
    pub const fn mapping(&self) -> NativeExecutableMappingReport {
        self.mapping
    }
}

impl ReadyNativeExecutable {
    /// Returns the non-zero native entrypoint address.
    #[must_use]
    pub const fn entry_address(&self) -> NonZeroUsize {
        self.entry_address
    }

    /// Returns the exact verified load image retained by this executable.
    #[must_use]
    pub const fn image(&self) -> &VerifiedDirectLoadImage {
        &self.image
    }

    /// Returns the complete retained artifact identity.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        self.image.key()
    }

    /// Returns the exact synchronized mapping report.
    #[must_use]
    pub const fn mapping(&self) -> NativeExecutableMappingReport {
        self.mapping
    }

    /// Returns an exact future cleanup request for the complete mapping.
    #[must_use]
    pub const fn release_request(&self) -> NativeExecutableReleaseRequest {
        NativeExecutableReleaseRequest {
            base_address: self.mapping.base_address(),
            mapped_len: self.mapping.mapped_len(),
            mapping_id: self.mapping.mapping_id(),
        }
    }

    /// Returns the exact target assumptions retained by this executable.
    #[must_use]
    pub const fn target(&self) -> &NativeTargetIdentity {
        self.image.target()
    }

    /// Returns the exact selected Windows target triple.
    #[must_use]
    pub const fn target_triple(&self) -> &'static str {
        self.image.target_triple()
    }
}

fn entry_address(
    image: &VerifiedDirectLoadImage,
    mapping: NativeExecutableMappingReport,
) -> Result<NonZeroUsize, NativeExecutableLifecycleError> {
    let value = mapping
        .base_address()
        .get()
        .checked_add(image.entry_offset())
        .ok_or(NativeExecutableLifecycleError::AddressOverflow)?;
    let code_end = mapping
        .base_address()
        .get()
        .checked_add(image.allocation_len())
        .ok_or(NativeExecutableLifecycleError::AddressOverflow)?;
    if value >= code_end {
        return Err(NativeExecutableLifecycleError::EntryRange);
    }
    NonZeroUsize::new(value).ok_or(NativeExecutableLifecycleError::EntryRange)
}

const fn is_aligned(value: usize, alignment: usize) -> bool {
    match alignment.checked_sub(1) {
        Some(mask) => value & mask == 0,
        None => false,
    }
}

const fn same_mapping(
    left: NativeExecutableMappingReport,
    right: NativeExecutableMappingReport,
) -> bool {
    left.base_address().get() == right.base_address().get()
        && left.mapped_len() == right.mapped_len()
        && left.mapping_id().get() == right.mapping_id().get()
}

fn validate_mapping_ranges(
    image: &VerifiedDirectLoadImage,
    mapping: NativeExecutableMappingReport,
) -> Result<(), NativeExecutableLifecycleError> {
    let mapping_end = mapping
        .base_address()
        .get()
        .checked_add(mapping.mapped_len())
        .ok_or(NativeExecutableLifecycleError::AddressOverflow)?;
    let code_end = mapping
        .base_address()
        .get()
        .checked_add(image.allocation_len())
        .ok_or(NativeExecutableLifecycleError::AddressOverflow)?;
    if code_end > mapping_end {
        return Err(NativeExecutableLifecycleError::MappingCapacity);
    }
    let _entry = entry_address(image, mapping)?;
    Ok(())
}
