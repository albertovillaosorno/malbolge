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
//   - Canonical native object emission and verification for non-aliasing
//     collapsed v6 rotate then no-operation.
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
//   - Proves canonical x86-64/AArch64 objects for v6 rotate then no-operation.
// - Description:
//   - Reconstructs semantic admission, target/key identity, COFF structure, and
//     canonical host bytes independently before object promotion.
// - Usage:
//   - Consumed only before any future load-image or executable lifecycle.
// - Defaults:
//   - Unsupported targets, structural drift, or any byte mismatch fail closed.
//

//! Canonical object proof for non-aliasing collapsed v6 rotate/no-operation.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{RegisterMaskedRegionEffectProgram, RuntimeCapability};

use super::coff::build_minimal_coff;
use super::{
    CoffAdmissionError, DIRECT_REGISTER_MASKED_ROTATE_NO_OPERATION_BACKEND_ID,
    DIRECT_REGISTER_MASKED_ROTATE_NO_OPERATION_BACKEND_REVISION,
    DirectRegisterMaskedRotateNoOperationTemplate, HostIsa,
    HostOperatingSystem, NATIVE_REGION_ABI_REVISION, NativeArtifactKey,
    NativeIdentityError, NativeTargetIdentity,
    RegisterMaskedDirectAdmissionErrorKind,
    StructurallyAdmittedNativeObjectArtifact, UntrustedNativeObjectArtifact,
    VerifiedRegisterMaskedRotateNoOperationAdmission, aarch64,
    admit_register_masked_rotate_no_operation, structurally_admit_coff,
    target_triple, x86_64,
};

/// Failure while emitting or verifying the collapsed rotate/no-operation
/// object.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectRegisterMaskedRotateNoOperationError {
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

impl Display for DirectRegisterMaskedRotateNoOperationError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Admission(_kind) => {
                "collapsed v6 rotate/no-operation semantic admission failed"
            },
            Self::ArtifactIdentity => {
                "collapsed v6 rotate/no-operation artifact identity drifted"
            },
            Self::Coff(_error) => {
                "collapsed v6 rotate/no-operation COFF structure was rejected"
            },
            Self::Identity(_error) => {
                "collapsed v6 rotate/no-operation native identity failed"
            },
            Self::ObjectBytes => {
                "collapsed v6 rotate/no-operation object bytes drifted"
            },
            Self::TargetAbi => {
                "collapsed v6 rotate/no-operation target ABI is unsupported"
            },
            Self::TargetBackend => {
                "collapsed v6 rotate/no-operation target backend is unsupported"
            },
            Self::TargetFeatures => {
                "collapsed v6 rotate/no-op target features are unsupported"
            },
            Self::TargetFormat => {
                "collapsed v6 rotate/no-operation backend requires Windows COFF"
            },
        })
    }
}

impl From<CoffAdmissionError> for DirectRegisterMaskedRotateNoOperationError {
    fn from(error: CoffAdmissionError) -> Self {
        Self::Coff(error)
    }
}

/// Byte-exact verified object for collapsed v6 rotate then no-operation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedRegisterMaskedRotateNoOperationNativeObjectArtifact {
    admission: VerifiedRegisterMaskedRotateNoOperationAdmission,
    artifact: StructurallyAdmittedNativeObjectArtifact,
}

impl VerifiedRegisterMaskedRotateNoOperationNativeObjectArtifact {
    /// Returns independently reconstructed semantic admission.
    #[must_use]
    pub const fn admission(
        &self,
    ) -> &VerifiedRegisterMaskedRotateNoOperationAdmission {
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

/// Emits one untrusted canonical candidate for collapsed rotate/no-operation.
///
/// # Errors
///
/// Returns an object error on semantic admission, target, identity, or
/// canonical byte construction failure.
pub fn emit_direct_register_masked_rotate_no_operation_coff(
    program: &RegisterMaskedRegionEffectProgram,
    runtime: &'static RuntimeCapability,
    target: NativeTargetIdentity,
) -> Result<
    UntrustedNativeObjectArtifact,
    DirectRegisterMaskedRotateNoOperationError,
> {
    let admission = admit_register_masked_rotate_no_operation(program, runtime)
        .map_err(|error| {
            DirectRegisterMaskedRotateNoOperationError::Admission(error.kind())
        })?;
    validate_target(&target)?;
    let key = NativeArtifactKey::new_register_masked(program, target)
        .map_err(DirectRegisterMaskedRotateNoOperationError::Identity)?;
    let triple = target_triple(key.target().host_isa());
    let object = canonical_coff(&key, &admission)?;
    Ok(UntrustedNativeObjectArtifact::from_emitter_output(
        key, object, triple,
    ))
}

/// Promotes only exact canonical collapsed rotate/no-operation object bytes.
///
/// # Errors
///
/// Returns an object error on semantic, identity, target, structural, or
/// canonical-byte mismatch.
pub fn verify_direct_register_masked_rotate_no_operation(
    artifact: &UntrustedNativeObjectArtifact,
    program: &RegisterMaskedRegionEffectProgram,
    runtime: &'static RuntimeCapability,
) -> Result<
    VerifiedRegisterMaskedRotateNoOperationNativeObjectArtifact,
    DirectRegisterMaskedRotateNoOperationError,
> {
    let admission = admit_register_masked_rotate_no_operation(program, runtime)
        .map_err(|error| {
            DirectRegisterMaskedRotateNoOperationError::Admission(error.kind())
        })?;
    validate_target(artifact.key().target())?;
    let expected_key = NativeArtifactKey::new_register_masked(
        program,
        artifact.key().target().clone(),
    )
    .map_err(DirectRegisterMaskedRotateNoOperationError::Identity)?;
    if artifact.key() != &expected_key
        || artifact.target_triple()
            != target_triple(expected_key.target().host_isa())
    {
        return Err(
            DirectRegisterMaskedRotateNoOperationError::ArtifactIdentity,
        );
    }
    let admitted = structurally_admit_coff(artifact)?;
    let expected = canonical_coff(&expected_key, &admission)?;
    if admitted.object() != expected {
        return Err(DirectRegisterMaskedRotateNoOperationError::ObjectBytes);
    }
    Ok(
        VerifiedRegisterMaskedRotateNoOperationNativeObjectArtifact {
            admission,
            artifact: admitted,
        },
    )
}

fn validate_target(
    target: &NativeTargetIdentity,
) -> Result<(), DirectRegisterMaskedRotateNoOperationError> {
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(DirectRegisterMaskedRotateNoOperationError::TargetFormat);
    }
    if target.backend_id()
        != DIRECT_REGISTER_MASKED_ROTATE_NO_OPERATION_BACKEND_ID
        || target.backend_revision()
            != DIRECT_REGISTER_MASKED_ROTATE_NO_OPERATION_BACKEND_REVISION
    {
        return Err(DirectRegisterMaskedRotateNoOperationError::TargetBackend);
    }
    if target.native_abi_revision() != NATIVE_REGION_ABI_REVISION {
        return Err(DirectRegisterMaskedRotateNoOperationError::TargetAbi);
    }
    if !target.required_features().is_empty() {
        return Err(DirectRegisterMaskedRotateNoOperationError::TargetFeatures);
    }
    Ok(())
}

fn canonical_coff(
    key: &NativeArtifactKey,
    admission: &VerifiedRegisterMaskedRotateNoOperationAdmission,
) -> Result<Vec<u8>, DirectRegisterMaskedRotateNoOperationError> {
    let rotate_code = admission.rotate_code_live_in();
    let rotate_data = admission.rotate_data_live_in();
    let no_operation = admission.no_operation_live_in();
    let template = DirectRegisterMaskedRotateNoOperationTemplate {
        entry_code_pointer: admission.entry_code_pointer(),
        entry_data_pointer: admission.entry_data_pointer(),
        next_code_pointer: admission.next_code_pointer(),
        next_data_pointer: admission.next_data_pointer(),
        no_operation_code_pointer: admission.second_code_pointer(),
        no_operation_encrypted_address: no_operation.address,
        no_operation_encrypted_value: admission.no_operation_encrypted_value(),
        no_operation_live_in: no_operation.value,
        required_memory_words: admission.required_memory_words(),
        rotate_code_live_in: rotate_code.value,
        rotate_data_address: rotate_data.address,
        rotate_data_live_in: rotate_data.value,
        rotate_encrypted_address: rotate_code.address,
        rotate_encrypted_value: admission.rotate_encrypted_value(),
        rotated_value: admission.rotated_value(),
    };
    let text = match key.target().host_isa() {
        HostIsa::AArch64 => {
            aarch64::register_masked_rotate_no_operation_code(template)
        },
        HostIsa::X86_64 => {
            x86_64::register_masked_rotate_no_operation_code(template)
        },
    }
    .ok_or(DirectRegisterMaskedRotateNoOperationError::ObjectBytes)?;
    build_minimal_coff(key, &text)
        .ok_or(DirectRegisterMaskedRotateNoOperationError::ObjectBytes)
}
