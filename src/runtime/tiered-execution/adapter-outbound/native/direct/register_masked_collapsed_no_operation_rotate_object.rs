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
//   - Canonical native object emission and verification for collapsed v6
//     no-operation then rotate.
// - Must-Not:
//   - Grant load, executable-memory, ABI, binding, runner, or call authority.
// - Allows:
//   - Inputs: independently admitted v6 semantics and exact native target.
//   - Outputs: untrusted COFF candidates and byte-exact verified objects.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - Executable loading or invocation gains shape-specific authority.
// - Merge-When:
//   - A shared collapsed-object verifier proves identical obligations.
// - Summary:
//   - Proves canonical x86-64/AArch64 objects for v6 no-operation then rotate.
// - Description:
//   - Reconstructs semantic admission, target/key identity, COFF structure, and
//     canonical host bytes independently before object promotion.
// - Usage:
//   - Consumed only before any future load-image or executable lifecycle.
// - Defaults:
//   - Unsupported targets, structural drift, or any byte mismatch fail closed.
//

//! Canonical object proof for collapsed v6 no-operation then rotate.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{RegisterMaskedRegionEffectProgram, RuntimeCapability};

use super::coff::build_minimal_coff;
use super::{
    CoffAdmissionError, DIRECT_REGISTER_MASKED_NO_OPERATION_ROTATE_BACKEND_ID,
    DIRECT_REGISTER_MASKED_NO_OPERATION_ROTATE_BACKEND_REVISION,
    DirectRegisterMaskedNoOperationRotateTemplate, HostIsa,
    HostOperatingSystem, NATIVE_REGION_ABI_REVISION, NativeArtifactKey,
    NativeIdentityError, NativeTargetIdentity,
    RegisterMaskedDirectAdmissionErrorKind,
    StructurallyAdmittedNativeObjectArtifact, UntrustedNativeObjectArtifact,
    VerifiedRegisterMaskedNoOperationRotateAdmission, aarch64,
    admit_register_masked_no_operation_rotate, structurally_admit_coff,
    target_triple, x86_64,
};

/// Failure while emitting or verifying the collapsed no-operation/rotate
/// object.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectRegisterMaskedNoOperationRotateError {
    /// Semantic admission rejected the source v6 region.
    Admission(RegisterMaskedDirectAdmissionErrorKind),
    /// Candidate key or target triple differs from reconstructed authority.
    ArtifactIdentity,
    /// Structural COFF admission rejected the candidate.
    Coff(CoffAdmissionError),
    /// Complete native identity could not be represented.
    Identity(NativeIdentityError),
    /// Candidate bytes differ from the canonical reviewed template.
    ObjectBytes,
    /// Target ABI differs from the reviewed native region contract.
    TargetAbi,
    /// Target backend identity or revision differs.
    TargetBackend,
    /// Target requests unsupported host-code features.
    TargetFeatures,
    /// Collapsed direct objects currently require Windows COFF.
    TargetFormat,
}

impl Display for DirectRegisterMaskedNoOperationRotateError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Admission(_kind) => {
                "collapsed v6 no-operation/rotate semantic admission failed"
            },
            Self::ArtifactIdentity => {
                "collapsed v6 no-operation/rotate artifact identity drifted"
            },
            Self::Coff(_error) => {
                "collapsed v6 no-operation/rotate COFF structure was rejected"
            },
            Self::Identity(_error) => {
                "collapsed v6 no-operation/rotate native identity failed"
            },
            Self::ObjectBytes => {
                "collapsed v6 no-operation/rotate object bytes drifted"
            },
            Self::TargetAbi => {
                "collapsed v6 no-operation/rotate target ABI is unsupported"
            },
            Self::TargetBackend => {
                "collapsed v6 no-operation/rotate target backend is unsupported"
            },
            Self::TargetFeatures => {
                "collapsed v6 no-op/rotate target features are unsupported"
            },
            Self::TargetFormat => {
                "collapsed v6 no-operation/rotate backend requires Windows COFF"
            },
        })
    }
}

impl From<CoffAdmissionError> for DirectRegisterMaskedNoOperationRotateError {
    fn from(error: CoffAdmissionError) -> Self {
        Self::Coff(error)
    }
}

/// Byte-exact verified object for collapsed v6 no-operation then rotate.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedRegisterMaskedNoOperationRotateNativeObjectArtifact {
    admission: VerifiedRegisterMaskedNoOperationRotateAdmission,
    artifact: StructurallyAdmittedNativeObjectArtifact,
}

impl VerifiedRegisterMaskedNoOperationRotateNativeObjectArtifact {
    /// Returns independently reconstructed semantic admission.
    #[must_use]
    pub const fn admission(
        &self,
    ) -> &VerifiedRegisterMaskedNoOperationRotateAdmission {
        &self.admission
    }

    /// Returns the exact complete v6 native artifact key.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        self.artifact.key()
    }

    /// Returns independently verified canonical COFF bytes.
    #[must_use]
    pub fn object(&self) -> &[u8] {
        self.artifact.object()
    }

    /// Returns the exact target triple retained by structural admission.
    #[must_use]
    pub const fn target_triple(&self) -> &'static str {
        self.artifact.target_triple()
    }
}

/// Emits one untrusted canonical candidate for collapsed no-operation/rotate.
///
/// # Errors
///
/// Returns an object error on semantic admission, target, identity, or
/// canonical byte construction failure.
pub fn emit_direct_register_masked_no_operation_rotate_coff(
    program: &RegisterMaskedRegionEffectProgram,
    runtime: &'static RuntimeCapability,
    target: NativeTargetIdentity,
) -> Result<
    UntrustedNativeObjectArtifact,
    DirectRegisterMaskedNoOperationRotateError,
> {
    let admission = admit_register_masked_no_operation_rotate(program, runtime)
        .map_err(|error| {
            DirectRegisterMaskedNoOperationRotateError::Admission(error.kind())
        })?;
    validate_target(&target)?;
    let key = NativeArtifactKey::new_register_masked(program, target)
        .map_err(DirectRegisterMaskedNoOperationRotateError::Identity)?;
    let triple = target_triple(key.target().host_isa());
    let object = canonical_coff(&key, &admission)?;
    Ok(UntrustedNativeObjectArtifact::from_emitter_output(
        key, object, triple,
    ))
}

/// Promotes only exact canonical collapsed no-operation/rotate object bytes.
///
/// # Errors
///
/// Returns an object error on semantic, identity, target, structural, or
/// canonical-byte mismatch.
pub fn verify_direct_register_masked_no_operation_rotate(
    artifact: &UntrustedNativeObjectArtifact,
    program: &RegisterMaskedRegionEffectProgram,
    runtime: &'static RuntimeCapability,
) -> Result<
    VerifiedRegisterMaskedNoOperationRotateNativeObjectArtifact,
    DirectRegisterMaskedNoOperationRotateError,
> {
    let admission = admit_register_masked_no_operation_rotate(program, runtime)
        .map_err(|error| {
            DirectRegisterMaskedNoOperationRotateError::Admission(error.kind())
        })?;
    validate_target(artifact.key().target())?;
    let expected_key = NativeArtifactKey::new_register_masked(
        program,
        artifact.key().target().clone(),
    )
    .map_err(DirectRegisterMaskedNoOperationRotateError::Identity)?;
    if artifact.key() != &expected_key
        || artifact.target_triple()
            != target_triple(expected_key.target().host_isa())
    {
        return Err(
            DirectRegisterMaskedNoOperationRotateError::ArtifactIdentity,
        );
    }
    let admitted = structurally_admit_coff(artifact)?;
    let expected = canonical_coff(&expected_key, &admission)?;
    if admitted.object() != expected {
        return Err(DirectRegisterMaskedNoOperationRotateError::ObjectBytes);
    }
    Ok(
        VerifiedRegisterMaskedNoOperationRotateNativeObjectArtifact {
            admission,
            artifact: admitted,
        },
    )
}

fn validate_target(
    target: &NativeTargetIdentity,
) -> Result<(), DirectRegisterMaskedNoOperationRotateError> {
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(DirectRegisterMaskedNoOperationRotateError::TargetFormat);
    }
    if target.backend_id()
        != DIRECT_REGISTER_MASKED_NO_OPERATION_ROTATE_BACKEND_ID
        || target.backend_revision()
            != DIRECT_REGISTER_MASKED_NO_OPERATION_ROTATE_BACKEND_REVISION
    {
        return Err(DirectRegisterMaskedNoOperationRotateError::TargetBackend);
    }
    if target.native_abi_revision() != NATIVE_REGION_ABI_REVISION {
        return Err(DirectRegisterMaskedNoOperationRotateError::TargetAbi);
    }
    if !target.required_features().is_empty() {
        return Err(DirectRegisterMaskedNoOperationRotateError::TargetFeatures);
    }
    Ok(())
}

fn canonical_coff(
    key: &NativeArtifactKey,
    admission: &VerifiedRegisterMaskedNoOperationRotateAdmission,
) -> Result<Vec<u8>, DirectRegisterMaskedNoOperationRotateError> {
    let first = admission.first_live_in();
    let rotate_code = admission.rotate_code_live_in();
    let rotate_data = admission.rotate_data_live_in();
    let template = DirectRegisterMaskedNoOperationRotateTemplate {
        entry_code_pointer: admission.entry_code_pointer(),
        entry_data_pointer: admission.entry_data_pointer(),
        first_encrypted_address: first.address,
        first_encrypted_value: admission.first_encrypted_value(),
        first_live_in: first.value,
        next_code_pointer: admission.next_code_pointer(),
        next_data_pointer: admission.next_data_pointer(),
        required_memory_words: admission.required_memory_words(),
        rotate_code_live_in: rotate_code.value,
        rotate_code_pointer: admission.second_code_pointer(),
        rotate_data_address: rotate_data.address,
        rotate_data_live_in: rotate_data.value,
        rotate_data_pointer: admission.second_data_pointer(),
        rotate_encrypted_address: rotate_code.address,
        rotate_encrypted_value: admission.rotate_encrypted_value(),
        rotated_value: admission.rotated_value(),
    };
    let text = match key.target().host_isa() {
        HostIsa::AArch64 => {
            aarch64::register_masked_no_operation_rotate_code(template)
        },
        HostIsa::X86_64 => {
            x86_64::register_masked_no_operation_rotate_code(template)
        },
    }
    .ok_or(DirectRegisterMaskedNoOperationRotateError::ObjectBytes)?;
    build_minimal_coff(key, &text)
        .ok_or(DirectRegisterMaskedNoOperationRotateError::ObjectBytes)
}
