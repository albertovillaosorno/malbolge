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
//   - Canonical candidate emission and semantic promotion for reviewed fused
//   - direct sequences.
// - Must-Not:
//   - Admit arbitrary fused shapes, allocate executable memory, or invoke code.
// - Allows:
//   - Inputs: exact `DirectFusedSequenceAdmission` evidence.
//   - Outputs: untrusted COFF candidates and byte-exact verified fused objects.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - More than one fused template family requires independent ownership.
// - Merge-When:
//   - General direct emission subsumes fused templates without weakening
//     review.
// - Summary:
//   - Emits and verifies the first atomic rotate/output fused native object.
// - Description:
//   - Reconstructs admission and canonical bytes independently before
//     promotion.
// - Usage:
//   - Called only after region-wide fused identity admission.
// - Defaults:
//   - Unsupported source shapes and any byte drift fail closed.
//

//! Candidate emission and semantic verification for reviewed fused sequences.

use std::fmt::{Display, Formatter, Result as FormatResult};

use super::super::fused_sequence::{
    DIRECT_FUSED_SEQUENCE_BACKEND_ID, DIRECT_FUSED_SEQUENCE_BACKEND_REVISION,
    DirectFusedSequenceAdmission, DirectFusedSequenceAdmissionError,
    admit_fused_direct_sequence,
};
use super::coff::{build_minimal_coff, direct_entry_observation};
use super::{
    CoffAdmissionError, DirectFusedRotateOutputTemplate, DirectNativeKind,
    DirectOutputProgram, DirectRotateProgram, HostIsa, HostOperatingSystem,
    NATIVE_REGION_ABI_REVISION, NativeArtifactKey,
    StructurallyAdmittedNativeObjectArtifact, UntrustedNativeObjectArtifact,
    aarch64, structurally_admit_coff, target_triple, validate_output_program,
    validate_rotate_program, x86_64,
};

type FusedRotateOutputSelection = (DirectRotateProgram, DirectOutputProgram);

/// Failure while emitting or verifying one reviewed fused direct object.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectFusedSequenceObjectError {
    /// Region-wide admission could not be reconstructed from retained evidence.
    Admission(DirectFusedSequenceAdmissionError),
    /// Candidate or admission identity differs from reconstructed authority.
    ArtifactIdentity,
    /// Structural COFF admission rejected the candidate.
    Coff(CoffAdmissionError),
    /// Object bytes differ from the canonical fused template.
    ObjectBytes,
    /// Source sequence is outside the reviewed rotate/output fused subset.
    ProgramShape,
    /// Fused target ABI revision is not the reviewed call-frame contract.
    TargetAbi,
    /// Fused target backend/revision is not the reviewed contract.
    TargetBackend,
    /// The reviewed fused object format is Windows COFF only.
    TargetFormat,
}

/// Semantically verified atomic fused rotate/output native object.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedDirectFusedSequenceObjectArtifact {
    admission: DirectFusedSequenceAdmission,
    artifact: StructurallyAdmittedNativeObjectArtifact,
}

impl Display for DirectFusedSequenceObjectError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Admission(_error) => {
                "fused direct sequence admission reconstruction failed"
            },
            Self::ArtifactIdentity => {
                "fused direct sequence artifact identity drifted"
            },
            Self::Coff(_error) => {
                "fused direct sequence COFF structure was rejected"
            },
            Self::ObjectBytes => {
                "fused direct sequence object differs from canonical bytes"
            },
            Self::ProgramShape => {
                "source sequence is outside fused rotate/output subset"
            },
            Self::TargetAbi => {
                "fused direct sequence target uses unsupported native ABI"
            },
            Self::TargetBackend => {
                "target does not select fused direct sequence backend"
            },
            Self::TargetFormat => {
                "fused direct sequence backend requires Windows COFF"
            },
        })
    }
}

impl From<CoffAdmissionError> for DirectFusedSequenceObjectError {
    fn from(error: CoffAdmissionError) -> Self {
        Self::Coff(error)
    }
}

impl VerifiedDirectFusedSequenceObjectArtifact {
    /// Returns the exact region-wide admission independently bound to this
    /// object.
    #[must_use]
    pub const fn admission(&self) -> &DirectFusedSequenceAdmission {
        &self.admission
    }

    /// Returns the exact fused native artifact identity.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        self.artifact.key()
    }

    /// Returns the semantically verified fused COFF bytes.
    #[must_use]
    pub fn object(&self) -> &[u8] {
        self.artifact.object()
    }

    /// Returns the exact target triple associated with the fused object.
    #[must_use]
    pub const fn target_triple(&self) -> &'static str {
        self.artifact.target_triple()
    }
}

/// Emits one untrusted candidate for the reviewed atomic rotate/output fusion.
///
/// # Errors
///
/// Returns [`DirectFusedSequenceObjectError`] when retained admission drifts,
/// source shape is unsupported, target assumptions differ, or canonical object
/// bytes cannot be represented.
pub fn emit_fused_direct_sequence_coff(
    admission: &DirectFusedSequenceAdmission,
) -> Result<UntrustedNativeObjectArtifact, DirectFusedSequenceObjectError> {
    validate_admission(admission)?;
    let object = canonical_fused_coff(admission)?;
    Ok(UntrustedNativeObjectArtifact::from_emitter_output(
        admission.key().clone(),
        object,
        target_triple(admission.key().target().host_isa()),
    ))
}

/// Promotes only the exact canonical fused object for retained source evidence.
///
/// The verifier reconstructs the complete fused admission from its retained
/// verified one-step plan, performs structural COFF admission, then
/// independently reconstructs the reviewed fused bytes before granting semantic
/// authority.
///
/// # Errors
///
/// Returns [`DirectFusedSequenceObjectError`] for admission/key/target drift,
/// structural rejection, unsupported source shape, or any canonical byte drift.
pub fn verify_fused_direct_sequence(
    artifact: &UntrustedNativeObjectArtifact,
    admission: &DirectFusedSequenceAdmission,
) -> Result<
    VerifiedDirectFusedSequenceObjectArtifact,
    DirectFusedSequenceObjectError,
> {
    validate_admission(admission)?;
    if artifact.key() != admission.key()
        || artifact.target_triple()
            != target_triple(admission.key().target().host_isa())
    {
        return Err(DirectFusedSequenceObjectError::ArtifactIdentity);
    }
    let admitted = structurally_admit_coff(artifact)?;
    let expected = canonical_fused_coff(admission)?;
    if admitted.object() != expected {
        return Err(DirectFusedSequenceObjectError::ObjectBytes);
    }
    Ok(VerifiedDirectFusedSequenceObjectArtifact {
        admission: admission.clone(),
        artifact: admitted,
    })
}

fn canonical_fused_coff(
    admission: &DirectFusedSequenceAdmission,
) -> Result<Vec<u8>, DirectFusedSequenceObjectError> {
    let (rotate, output) = select_rotate_output(admission)?;
    let observation = direct_entry_observation(rotate.observation)
        .ok_or(DirectFusedSequenceObjectError::ObjectBytes)?;
    let template = DirectFusedRotateOutputTemplate {
        live_ins: &admission.program().memory_live_ins,
        observation,
        output: output.commit,
        required_memory_words: admission.key().ir().required_memory_words(),
        rotate: rotate.commit,
    };
    let text = match admission.key().target().host_isa() {
        HostIsa::AArch64 => aarch64::fused_rotate_output_code(template),
        HostIsa::X86_64 => x86_64::fused_rotate_output_code(template),
    }
    .ok_or(DirectFusedSequenceObjectError::ObjectBytes)?;
    build_minimal_coff(admission.key(), &text)
        .ok_or(DirectFusedSequenceObjectError::ObjectBytes)
}

fn select_rotate_output(
    admission: &DirectFusedSequenceAdmission,
) -> Result<FusedRotateOutputSelection, DirectFusedSequenceObjectError> {
    let [rotate_program, output_program] = admission.source_plan().programs()
    else {
        return Err(DirectFusedSequenceObjectError::ProgramShape);
    };
    let [rotate_artifact, output_artifact] =
        admission.source_plan().artifacts()
    else {
        return Err(DirectFusedSequenceObjectError::ProgramShape);
    };
    if rotate_artifact.kind() != DirectNativeKind::Rotate
        || output_artifact.kind() != DirectNativeKind::Output
    {
        return Err(DirectFusedSequenceObjectError::ProgramShape);
    }
    let rotate = validate_rotate_program(rotate_program)
        .map_err(|_error| DirectFusedSequenceObjectError::ProgramShape)?;
    let output = validate_output_program(output_program)
        .map_err(|_error| DirectFusedSequenceObjectError::ProgramShape)?;
    Ok((rotate, output))
}

fn validate_admission(
    admission: &DirectFusedSequenceAdmission,
) -> Result<(), DirectFusedSequenceObjectError> {
    let expected = admit_fused_direct_sequence(admission.source_plan())
        .map_err(DirectFusedSequenceObjectError::Admission)?;
    if &expected != admission {
        return Err(DirectFusedSequenceObjectError::ArtifactIdentity);
    }
    let target = admission.key().target();
    if target.native_abi_revision() != NATIVE_REGION_ABI_REVISION {
        return Err(DirectFusedSequenceObjectError::TargetAbi);
    }
    if target.backend_id() != DIRECT_FUSED_SEQUENCE_BACKEND_ID
        || target.backend_revision() != DIRECT_FUSED_SEQUENCE_BACKEND_REVISION
    {
        return Err(DirectFusedSequenceObjectError::TargetBackend);
    }
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(DirectFusedSequenceObjectError::TargetFormat);
    }
    Ok(())
}
