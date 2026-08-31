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
//   - Relocation-free executable-image planning for verified direct objects.
// - Must-Not:
//   - Allocate executable memory, invoke code, or permit writable-executable
//   - pages.
// - Allows:
//   - Inputs: semantically verified direct COFF artifacts.
//   - Outputs: immutable code bytes, entry offset, and strict W^X policy.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - OS allocation, permission transitions, or instruction-cache operations
//   - gain concrete platform ownership.
// - Merge-When:
//   - One executable owner subsumes image extraction and lifetime policy.
// - Summary:
//   - Converts verified direct COFF into an immutable loader-ready code image.
// - Description:
//   - Revalidates closure, rejects relocations, and retains exact key identity.
// - Usage:
//   - Prepared before a future platform loader receives an exact call binding.
// - Defaults:
//   - Copy under RW, transition to RX, synchronize instructions, then execute.
//

//! Relocation-free load-image planning for verified direct native artifacts.

use std::fmt::{Display, Formatter, Result as FormatResult};

use super::coff::{
    CoffAdmissionError, CoffExecutableTextError,
    extract_relocation_free_executable_text,
};
use super::direct::{
    VerifiedDirectNativeArtifact,
    VerifiedExecutionGeometryCrazyNativeObjectArtifact,
    VerifiedExecutionGeometryInitialHaltNativeObjectArtifact,
    VerifiedExecutionGeometryInitialJumpDataNativeObjectArtifact,
    VerifiedExecutionGeometryInputNativeObjectArtifact,
    VerifiedExecutionGeometryNoOperationNativeObjectArtifact,
    VerifiedExecutionGeometryOutputNativeObjectArtifact,
    VerifiedExecutionGeometryRotateNativeObjectArtifact,
};
use crate::execution_cache::{
    HostIsa, NativeArtifactKey, NativeTargetIdentity,
};

/// Page permissions used by the strict native load transition.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeExecutablePermission {
    /// Immutable executable pages used only after the code copy completes.
    ReadExecute,
    /// Writable staging pages used only while copying admitted code.
    ReadWrite,
}

/// Fixed permission and synchronization policy for a future executable owner.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeExecutableLoadPolicy {
    final_permissions: NativeExecutablePermission,
    initial_permissions: NativeExecutablePermission,
    synchronize_instructions: bool,
}

/// Failure while deriving a loader-ready image from a verified direct object.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum VerifiedDirectLoadError {
    /// The entrypoint or instruction stream violates ISA alignment.
    InstructionAlignment,
    /// The verified object no longer has one structurally closed image.
    Object(CoffAdmissionError),
    /// The object requires relocation processing not owned by this loader.
    Relocations,
}

/// Relocation-free image for one verified explicit-geometry native artifact.
///
/// This value has no lifecycle or invocation implementation. It only proves
/// that admitted v5 COFF contains one relocation-free, ISA-aligned code image.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedExecutionGeometryLoadImage {
    code: Box<[u8]>,
    entry_offset: usize,
    key: NativeArtifactKey,
    policy: NativeExecutableLoadPolicy,
    target_triple: &'static str,
}

/// Immutable relocation-free code image retaining complete artifact identity.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedDirectLoadImage {
    code: Box<[u8]>,
    entry_offset: usize,
    key: NativeArtifactKey,
    policy: NativeExecutableLoadPolicy,
    target_triple: &'static str,
}

impl NativeExecutableLoadPolicy {
    /// Returns permissions required after copying and before execution.
    #[must_use]
    pub const fn final_permissions(self) -> NativeExecutablePermission {
        self.final_permissions
    }

    /// Returns permissions required while copying admitted bytes.
    #[must_use]
    pub const fn initial_permissions(self) -> NativeExecutablePermission {
        self.initial_permissions
    }

    /// Reports whether instruction visibility must be synchronized after RX.
    #[must_use]
    pub const fn requires_instruction_sync(self) -> bool {
        self.synchronize_instructions
    }

    /// Returns the only admitted load transition: RW staging to RX execution.
    #[must_use]
    pub const fn strict_wx() -> Self {
        Self {
            final_permissions: NativeExecutablePermission::ReadExecute,
            initial_permissions: NativeExecutablePermission::ReadWrite,
            synchronize_instructions: true,
        }
    }
}

impl Display for VerifiedDirectLoadError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::InstructionAlignment => {
                "verified direct code violates ISA instruction alignment"
            },
            Self::Object(_) => "verified direct object is not loader-ready",
            Self::Relocations => "verified direct object requires relocations",
        })
    }
}

impl VerifiedExecutionGeometryLoadImage {
    /// Returns the exact number of admitted code bytes.
    #[must_use]
    pub const fn allocation_len(&self) -> usize {
        self.code.len()
    }

    /// Returns the complete relocation-free instruction stream.
    #[must_use]
    pub const fn code(&self) -> &[u8] {
        &self.code
    }

    /// Returns code beginning at the required native entrypoint.
    #[must_use]
    pub fn entry_code(&self) -> &[u8] {
        self.code.get(self.entry_offset..).unwrap_or_default()
    }

    /// Returns the entrypoint byte offset inside [`Self::code`].
    #[must_use]
    pub const fn entry_offset(&self) -> usize {
        self.entry_offset
    }

    /// Derives a relocation-free image from verified v5 crazy bytes.
    ///
    /// # Errors
    ///
    /// Returns [`VerifiedDirectLoadError`] when COFF extraction, relocation, or
    /// target instruction alignment is invalid.
    pub fn from_crazy(
        artifact: &VerifiedExecutionGeometryCrazyNativeObjectArtifact,
    ) -> Result<Self, VerifiedDirectLoadError> {
        Self::from_verified_parts(
            artifact.key(),
            artifact.object(),
            artifact.target_triple(),
        )
    }

    /// Derives a relocation-free image from verified v5 initial-halt bytes.
    ///
    /// # Errors
    ///
    /// Returns [`VerifiedDirectLoadError`] when COFF extraction, relocation, or
    /// target instruction alignment is invalid.
    pub fn from_initial_halt(
        artifact: &VerifiedExecutionGeometryInitialHaltNativeObjectArtifact,
    ) -> Result<Self, VerifiedDirectLoadError> {
        Self::from_verified_parts(
            artifact.key(),
            artifact.object(),
            artifact.target_triple(),
        )
    }

    /// Derives a relocation-free image from verified v5 initial-jump bytes.
    ///
    /// # Errors
    ///
    /// Returns [`VerifiedDirectLoadError`] when COFF extraction, relocation, or
    /// target instruction alignment is invalid.
    pub fn from_initial_jump_data(
        artifact: &VerifiedExecutionGeometryInitialJumpDataNativeObjectArtifact,
    ) -> Result<Self, VerifiedDirectLoadError> {
        Self::from_verified_parts(
            artifact.key(),
            artifact.object(),
            artifact.target_triple(),
        )
    }

    /// Derives a relocation-free image from verified v5 input bytes.
    ///
    /// # Errors
    ///
    /// Returns [`VerifiedDirectLoadError`] when COFF extraction, relocation, or
    /// target instruction alignment is invalid.
    pub fn from_input(
        artifact: &VerifiedExecutionGeometryInputNativeObjectArtifact,
    ) -> Result<Self, VerifiedDirectLoadError> {
        Self::from_verified_parts(
            artifact.key(),
            artifact.object(),
            artifact.target_triple(),
        )
    }

    /// Derives a relocation-free image from verified v5 no-operation bytes.
    ///
    /// # Errors
    ///
    /// Returns [`VerifiedDirectLoadError`] when COFF extraction, relocation, or
    /// target instruction alignment is invalid.
    pub fn from_no_operation(
        artifact: &VerifiedExecutionGeometryNoOperationNativeObjectArtifact,
    ) -> Result<Self, VerifiedDirectLoadError> {
        Self::from_verified_parts(
            artifact.key(),
            artifact.object(),
            artifact.target_triple(),
        )
    }

    /// Derives a relocation-free image from verified v5 output bytes.
    ///
    /// # Errors
    ///
    /// Returns [`VerifiedDirectLoadError`] when COFF extraction, relocation, or
    /// target instruction alignment is invalid.
    pub fn from_output(
        artifact: &VerifiedExecutionGeometryOutputNativeObjectArtifact,
    ) -> Result<Self, VerifiedDirectLoadError> {
        Self::from_verified_parts(
            artifact.key(),
            artifact.object(),
            artifact.target_triple(),
        )
    }

    /// Derives a relocation-free image from verified v5 rotate bytes.
    ///
    /// # Errors
    ///
    /// Returns [`VerifiedDirectLoadError`] when COFF extraction, relocation, or
    /// target instruction alignment is invalid.
    pub fn from_rotate(
        artifact: &VerifiedExecutionGeometryRotateNativeObjectArtifact,
    ) -> Result<Self, VerifiedDirectLoadError> {
        Self::from_verified_parts(
            artifact.key(),
            artifact.object(),
            artifact.target_triple(),
        )
    }

    fn from_verified_parts(
        key: &NativeArtifactKey,
        object: &[u8],
        target_triple: &'static str,
    ) -> Result<Self, VerifiedDirectLoadError> {
        let parts = verified_load_image_parts(key, object, target_triple)?;
        Ok(Self {
            code: parts.code,
            entry_offset: parts.entry_offset,
            key: parts.key,
            policy: parts.policy,
            target_triple: parts.target_triple,
        })
    }

    /// Returns the exact ISA retained by the v5 artifact identity.
    #[must_use]
    pub const fn host_isa(&self) -> HostIsa {
        self.key.target().host_isa()
    }

    /// Returns the complete retained v5 artifact identity.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        &self.key
    }

    /// Returns minimum instruction alignment required by the target ISA.
    #[must_use]
    pub const fn minimum_instruction_alignment(&self) -> usize {
        minimum_instruction_alignment(self.host_isa())
    }

    /// Returns the mandatory W^X and instruction-sync policy.
    #[must_use]
    pub const fn policy(&self) -> NativeExecutableLoadPolicy {
        self.policy
    }

    /// Returns exact target assumptions retained by this v5 load image.
    #[must_use]
    pub const fn target(&self) -> &NativeTargetIdentity {
        self.key.target()
    }

    /// Returns the exact selected Windows target triple.
    #[must_use]
    pub const fn target_triple(&self) -> &'static str {
        self.target_triple
    }
}

impl VerifiedDirectLoadImage {
    /// Returns the exact number of admitted code bytes to allocate and copy.
    #[must_use]
    pub const fn allocation_len(&self) -> usize {
        self.code.len()
    }

    /// Returns the complete relocation-free instruction stream.
    #[must_use]
    pub const fn code(&self) -> &[u8] {
        &self.code
    }

    /// Returns code beginning at the required native entrypoint.
    #[must_use]
    pub fn entry_code(&self) -> &[u8] {
        self.code.get(self.entry_offset..).unwrap_or_default()
    }

    /// Returns the entrypoint byte offset inside [`Self::code`].
    #[must_use]
    pub const fn entry_offset(&self) -> usize {
        self.entry_offset
    }

    /// Extracts the canonical object carried by one verified artifact for
    /// tests.
    #[cfg(test)]
    #[doc(hidden)]
    pub fn from_artifact_for_test(
        artifact: &VerifiedDirectNativeArtifact,
    ) -> Result<Self, VerifiedDirectLoadError> {
        Self::new(artifact)
    }

    fn from_object(
        artifact: &VerifiedDirectNativeArtifact,
        object: &[u8],
    ) -> Result<Self, VerifiedDirectLoadError> {
        let parts = verified_load_image_parts(
            artifact.key(),
            object,
            artifact.target_triple(),
        )?;
        Ok(Self {
            code: parts.code,
            entry_offset: parts.entry_offset,
            key: parts.key,
            policy: parts.policy,
            target_triple: parts.target_triple,
        })
    }

    /// Extracts a supplied object under one verified identity for tests.
    #[cfg(test)]
    #[doc(hidden)]
    pub fn from_object_for_test(
        artifact: &VerifiedDirectNativeArtifact,
        object: &[u8],
    ) -> Result<Self, VerifiedDirectLoadError> {
        Self::from_object(artifact, object)
    }

    /// Returns the exact ISA selected by the retained artifact identity.
    #[must_use]
    pub const fn host_isa(&self) -> HostIsa {
        self.key.target().host_isa()
    }

    /// Returns the complete retained artifact identity.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        &self.key
    }

    /// Returns minimum instruction alignment required by the target ISA.
    #[must_use]
    pub const fn minimum_instruction_alignment(&self) -> usize {
        minimum_instruction_alignment(self.host_isa())
    }

    /// Extracts one immutable relocation-free image from a verified artifact.
    pub(super) fn new(
        artifact: &VerifiedDirectNativeArtifact,
    ) -> Result<Self, VerifiedDirectLoadError> {
        Self::from_object(artifact, artifact.object())
    }

    /// Returns the mandatory W^X and instruction-sync policy.
    #[must_use]
    pub const fn policy(&self) -> NativeExecutableLoadPolicy {
        self.policy
    }

    /// Returns the exact target assumptions retained by this image.
    #[must_use]
    pub const fn target(&self) -> &NativeTargetIdentity {
        self.key.target()
    }

    /// Returns the exact selected Windows target triple.
    #[must_use]
    pub const fn target_triple(&self) -> &'static str {
        self.target_triple
    }
}

struct VerifiedLoadImageParts {
    code: Box<[u8]>,
    entry_offset: usize,
    key: NativeArtifactKey,
    policy: NativeExecutableLoadPolicy,
    target_triple: &'static str,
}

fn verified_load_image_parts(
    key: &NativeArtifactKey,
    object: &[u8],
    target_triple: &'static str,
) -> Result<VerifiedLoadImageParts, VerifiedDirectLoadError> {
    let isa = key.target().host_isa();
    let executable = extract_relocation_free_executable_text(object, isa)
        .map_err(map_executable_text_error)?;
    let alignment = minimum_instruction_alignment(isa);
    if !is_aligned(executable.entry_offset, alignment)
        || (isa == HostIsa::AArch64
            && !is_aligned(executable.code.len(), alignment))
    {
        return Err(VerifiedDirectLoadError::InstructionAlignment);
    }
    Ok(VerifiedLoadImageParts {
        code: executable.code,
        entry_offset: executable.entry_offset,
        key: key.clone(),
        policy: NativeExecutableLoadPolicy::strict_wx(),
        target_triple,
    })
}

const fn is_aligned(value: usize, alignment: usize) -> bool {
    match alignment.checked_sub(1) {
        Some(mask) => value & mask == 0,
        None => false,
    }
}

const fn map_executable_text_error(
    error: CoffExecutableTextError,
) -> VerifiedDirectLoadError {
    match error {
        CoffExecutableTextError::Admission(admission) => {
            VerifiedDirectLoadError::Object(admission)
        },
        CoffExecutableTextError::Relocations => {
            VerifiedDirectLoadError::Relocations
        },
    }
}

const fn minimum_instruction_alignment(isa: HostIsa) -> usize {
    match isa {
        HostIsa::AArch64 => 4,
        HostIsa::X86_64 => 1,
    }
}
