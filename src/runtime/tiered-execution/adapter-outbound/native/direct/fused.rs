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
//   - Emits and verifies reviewed atomic two-step fused native objects.
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

use malbolge::RegionEffectProgram;

use super::super::fused_sequence::{
    DIRECT_FUSED_SEQUENCE_BACKEND_ID, DIRECT_FUSED_SEQUENCE_BACKEND_REVISION,
    DirectFusedSequenceAdmission, DirectFusedSequenceAdmissionError,
    admit_fused_direct_sequence,
};
use super::coff::{build_minimal_coff, direct_entry_observation};
use super::{
    CoffAdmissionError, DirectCodeWriteCommit, DirectCrazyProgram,
    DirectEntryObservation, DirectFusedCrazyNoOperationTemplate,
    DirectFusedCrazyPairTemplate, DirectFusedNoOperationCrazyTemplate,
    DirectFusedNoOperationOutputTemplate, DirectFusedNoOperationPairTemplate,
    DirectFusedNoOperationRotateTemplate, DirectFusedRotateNoOperationTemplate,
    DirectFusedRotateOutputTemplate, DirectFusedRotatePairTemplate,
    DirectNativeKind, DirectNoOperationProgram, DirectOutputProgram,
    DirectRotateProgram, HostIsa, HostOperatingSystem,
    NATIVE_REGION_ABI_REVISION, NativeArtifactKey,
    StructurallyAdmittedNativeObjectArtifact, UntrustedNativeObjectArtifact,
    aarch64, structurally_admit_coff, target_triple, validate_crazy_program,
    validate_no_operation_program, validate_output_program,
    validate_rotate_program, x86_64,
};

#[derive(Clone, Copy)]
enum FusedSelection {
    CrazyNoOperation(DirectCrazyProgram, DirectNoOperationProgram),
    CrazyOutput(DirectCrazyProgram, DirectOutputProgram),
    CrazyPair(DirectCrazyProgram, DirectCrazyProgram),
    CrazyRotate(DirectCrazyProgram, DirectRotateProgram),
    NoOperationCrazy(DirectNoOperationProgram, DirectCrazyProgram),
    NoOperationOutput(DirectNoOperationProgram, DirectOutputProgram),
    NoOperationPair(DirectNoOperationProgram, DirectNoOperationProgram),
    NoOperationRotate(DirectNoOperationProgram, DirectRotateProgram),
    RotateCrazy(DirectRotateProgram, DirectCrazyProgram),
    RotateNoOperation(DirectRotateProgram, DirectNoOperationProgram),
    RotateOutput(DirectRotateProgram, DirectOutputProgram),
    RotatePair(DirectRotateProgram, DirectRotateProgram),
}

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
    /// Source sequence is outside the reviewed fused subsets.
    ProgramShape,
    /// Fused target ABI revision is not the reviewed call-frame contract.
    TargetAbi,
    /// Fused target backend/revision is not the reviewed contract.
    TargetBackend,
    /// The reviewed fused object format is Windows COFF only.
    TargetFormat,
}

/// Semantically verified atomic reviewed fused native object.
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
                "source sequence is outside reviewed fused subsets"
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

/// Emits one untrusted candidate for a reviewed atomic fused sequence.
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
    let selection = select_fused_shape(admission)?;
    let observation = direct_entry_observation(admission.source_plan().entry())
        .ok_or(DirectFusedSequenceObjectError::ObjectBytes)?;
    let text = canonical_fused_text(admission, observation, &selection)
        .ok_or(DirectFusedSequenceObjectError::ObjectBytes)?;
    build_minimal_coff(admission.key(), &text)
        .ok_or(DirectFusedSequenceObjectError::ObjectBytes)
}

fn canonical_fused_text(
    admission: &DirectFusedSequenceAdmission,
    observation: DirectEntryObservation,
    selection: &FusedSelection,
) -> Option<Vec<u8>> {
    match *selection {
        FusedSelection::CrazyNoOperation(..)
        | FusedSelection::CrazyOutput(..)
        | FusedSelection::CrazyPair(..)
        | FusedSelection::CrazyRotate(..) => {
            fused_crazy_selection_text(admission, observation, selection)
        },
        FusedSelection::NoOperationCrazy(no_operation, crazy) => {
            fused_no_operation_crazy_text(
                admission,
                observation,
                no_operation,
                crazy,
            )
        },
        FusedSelection::NoOperationOutput(no_operation, output) => {
            fused_no_operation_output_text(
                admission,
                observation,
                no_operation,
                output,
            )
        },
        FusedSelection::NoOperationPair(first, second) => {
            fused_no_operation_pair_text(admission, observation, first, second)
        },
        FusedSelection::NoOperationRotate(no_operation, rotate) => {
            fused_no_operation_rotate_text(
                admission,
                observation,
                no_operation,
                rotate,
            )
        },
        FusedSelection::RotateCrazy(rotate, crazy) => {
            fused_rotate_crazy_text(admission, observation, rotate, crazy)
        },
        FusedSelection::RotateNoOperation(rotate, no_operation) => {
            fused_rotate_no_operation_text(
                admission,
                observation,
                rotate,
                no_operation,
            )
        },
        FusedSelection::RotatePair(first, second) => {
            fused_rotate_pair_text(admission, observation, first, second)
        },
        FusedSelection::RotateOutput(rotate, output) => {
            fused_rotate_output_text(admission, observation, rotate, output)
        },
    }
}

fn fused_crazy_selection_text(
    admission: &DirectFusedSequenceAdmission,
    observation: DirectEntryObservation,
    selection: &FusedSelection,
) -> Option<Vec<u8>> {
    match *selection {
        FusedSelection::CrazyNoOperation(crazy, no_operation) => {
            fused_crazy_no_operation_text(
                admission,
                observation,
                crazy,
                no_operation,
            )
        },
        FusedSelection::CrazyOutput(crazy, output) => {
            fused_crazy_output_text(admission, observation, crazy, output)
        },
        FusedSelection::CrazyPair(first, second) => {
            fused_crazy_pair_text(admission, observation, first, second)
        },
        FusedSelection::CrazyRotate(crazy, rotate) => {
            fused_crazy_rotate_text(admission, observation, crazy, rotate)
        },
        FusedSelection::NoOperationCrazy(..)
        | FusedSelection::NoOperationOutput(..)
        | FusedSelection::NoOperationPair(..)
        | FusedSelection::NoOperationRotate(..)
        | FusedSelection::RotateCrazy(..)
        | FusedSelection::RotateNoOperation(..)
        | FusedSelection::RotateOutput(..)
        | FusedSelection::RotatePair(..) => None,
    }
}

fn fused_crazy_output_text(
    admission: &DirectFusedSequenceAdmission,
    observation: DirectEntryObservation,
    crazy: DirectCrazyProgram,
    output: DirectOutputProgram,
) -> Option<Vec<u8>> {
    let template = super::DirectFusedCrazyOutputTemplate {
        crazy: crazy.commit,
        live_ins: &admission.program().memory_live_ins,
        observation,
        output: output.commit,
        required_memory_words: admission.key().ir().required_memory_words(),
    };
    match admission.key().target().host_isa() {
        HostIsa::AArch64 => aarch64::fused_crazy_output_code(template),
        HostIsa::X86_64 => x86_64::fused_crazy_output_code(template),
    }
}

fn fused_crazy_rotate_text(
    admission: &DirectFusedSequenceAdmission,
    observation: DirectEntryObservation,
    crazy: DirectCrazyProgram,
    rotate: DirectRotateProgram,
) -> Option<Vec<u8>> {
    let template = super::DirectFusedCrazyRotateTemplate {
        crazy: crazy.commit,
        live_ins: &admission.program().memory_live_ins,
        observation,
        required_memory_words: admission.key().ir().required_memory_words(),
        rotate: rotate.commit,
    };
    match admission.key().target().host_isa() {
        HostIsa::AArch64 => aarch64::fused_crazy_rotate_code(template),
        HostIsa::X86_64 => x86_64::fused_crazy_rotate_code(template),
    }
}

fn fused_crazy_pair_text(
    admission: &DirectFusedSequenceAdmission,
    observation: DirectEntryObservation,
    first: DirectCrazyProgram,
    second: DirectCrazyProgram,
) -> Option<Vec<u8>> {
    let template = DirectFusedCrazyPairTemplate {
        first: first.commit,
        live_ins: &admission.program().memory_live_ins,
        observation,
        required_memory_words: admission.key().ir().required_memory_words(),
        second: second.commit,
    };
    match admission.key().target().host_isa() {
        HostIsa::AArch64 => aarch64::fused_crazy_pair_code(template),
        HostIsa::X86_64 => x86_64::fused_crazy_pair_code(template),
    }
}

fn fused_crazy_no_operation_text(
    admission: &DirectFusedSequenceAdmission,
    observation: DirectEntryObservation,
    crazy: DirectCrazyProgram,
    no_operation: DirectNoOperationProgram,
) -> Option<Vec<u8>> {
    let template = DirectFusedCrazyNoOperationTemplate {
        crazy: crazy.commit,
        live_ins: &admission.program().memory_live_ins,
        no_operation: no_operation_commit(no_operation),
        observation,
        required_memory_words: admission.key().ir().required_memory_words(),
    };
    match admission.key().target().host_isa() {
        HostIsa::AArch64 => aarch64::fused_crazy_no_operation_code(template),
        HostIsa::X86_64 => x86_64::fused_crazy_no_operation_code(template),
    }
}

fn fused_no_operation_crazy_text(
    admission: &DirectFusedSequenceAdmission,
    observation: DirectEntryObservation,
    no_operation: DirectNoOperationProgram,
    crazy: DirectCrazyProgram,
) -> Option<Vec<u8>> {
    let template = DirectFusedNoOperationCrazyTemplate {
        crazy: crazy.commit,
        live_ins: &admission.program().memory_live_ins,
        no_operation: no_operation_commit(no_operation),
        observation,
        required_memory_words: admission.key().ir().required_memory_words(),
    };
    match admission.key().target().host_isa() {
        HostIsa::AArch64 => aarch64::fused_no_operation_crazy_code(template),
        HostIsa::X86_64 => x86_64::fused_no_operation_crazy_code(template),
    }
}

fn fused_no_operation_output_text(
    admission: &DirectFusedSequenceAdmission,
    observation: DirectEntryObservation,
    no_operation: DirectNoOperationProgram,
    output: DirectOutputProgram,
) -> Option<Vec<u8>> {
    let template = DirectFusedNoOperationOutputTemplate {
        live_ins: &admission.program().memory_live_ins,
        no_operation: no_operation_commit(no_operation),
        observation,
        output: output.commit,
        required_memory_words: admission.key().ir().required_memory_words(),
    };
    match admission.key().target().host_isa() {
        HostIsa::AArch64 => aarch64::fused_no_operation_output_code(template),
        HostIsa::X86_64 => x86_64::fused_no_operation_output_code(template),
    }
}

fn fused_no_operation_pair_text(
    admission: &DirectFusedSequenceAdmission,
    observation: DirectEntryObservation,
    first: DirectNoOperationProgram,
    second: DirectNoOperationProgram,
) -> Option<Vec<u8>> {
    let template = DirectFusedNoOperationPairTemplate {
        first: no_operation_commit(first),
        live_ins: &admission.program().memory_live_ins,
        observation,
        required_memory_words: admission.key().ir().required_memory_words(),
        second: no_operation_commit(second),
    };
    match admission.key().target().host_isa() {
        HostIsa::AArch64 => aarch64::fused_no_operation_pair_code(template),
        HostIsa::X86_64 => x86_64::fused_no_operation_pair_code(template),
    }
}

fn fused_no_operation_rotate_text(
    admission: &DirectFusedSequenceAdmission,
    observation: DirectEntryObservation,
    no_operation: DirectNoOperationProgram,
    rotate: DirectRotateProgram,
) -> Option<Vec<u8>> {
    let template = DirectFusedNoOperationRotateTemplate {
        live_ins: &admission.program().memory_live_ins,
        no_operation: no_operation_commit(no_operation),
        observation,
        required_memory_words: admission.key().ir().required_memory_words(),
        rotate: rotate.commit,
    };
    match admission.key().target().host_isa() {
        HostIsa::AArch64 => aarch64::fused_no_operation_rotate_code(template),
        HostIsa::X86_64 => x86_64::fused_no_operation_rotate_code(template),
    }
}

fn fused_rotate_crazy_text(
    admission: &DirectFusedSequenceAdmission,
    observation: DirectEntryObservation,
    rotate: DirectRotateProgram,
    crazy: DirectCrazyProgram,
) -> Option<Vec<u8>> {
    let template = super::DirectFusedRotateCrazyTemplate {
        crazy: crazy.commit,
        live_ins: &admission.program().memory_live_ins,
        observation,
        required_memory_words: admission.key().ir().required_memory_words(),
        rotate: rotate.commit,
    };
    match admission.key().target().host_isa() {
        HostIsa::AArch64 => aarch64::fused_rotate_crazy_code(template),
        HostIsa::X86_64 => x86_64::fused_rotate_crazy_code(template),
    }
}

fn fused_rotate_no_operation_text(
    admission: &DirectFusedSequenceAdmission,
    observation: DirectEntryObservation,
    rotate: DirectRotateProgram,
    no_operation: DirectNoOperationProgram,
) -> Option<Vec<u8>> {
    let template = DirectFusedRotateNoOperationTemplate {
        live_ins: &admission.program().memory_live_ins,
        no_operation: no_operation_commit(no_operation),
        observation,
        required_memory_words: admission.key().ir().required_memory_words(),
        rotate: rotate.commit,
    };
    match admission.key().target().host_isa() {
        HostIsa::AArch64 => aarch64::fused_rotate_no_operation_code(template),
        HostIsa::X86_64 => x86_64::fused_rotate_no_operation_code(template),
    }
}

fn fused_rotate_pair_text(
    admission: &DirectFusedSequenceAdmission,
    observation: DirectEntryObservation,
    first: DirectRotateProgram,
    second: DirectRotateProgram,
) -> Option<Vec<u8>> {
    let template = DirectFusedRotatePairTemplate {
        first: first.commit,
        live_ins: &admission.program().memory_live_ins,
        observation,
        required_memory_words: admission.key().ir().required_memory_words(),
        second: second.commit,
    };
    match admission.key().target().host_isa() {
        HostIsa::AArch64 => aarch64::fused_rotate_pair_code(template),
        HostIsa::X86_64 => x86_64::fused_rotate_pair_code(template),
    }
}

fn fused_rotate_output_text(
    admission: &DirectFusedSequenceAdmission,
    observation: DirectEntryObservation,
    rotate: DirectRotateProgram,
    output: DirectOutputProgram,
) -> Option<Vec<u8>> {
    let template = DirectFusedRotateOutputTemplate {
        live_ins: &admission.program().memory_live_ins,
        observation,
        output: output.commit,
        required_memory_words: admission.key().ir().required_memory_words(),
        rotate: rotate.commit,
    };
    match admission.key().target().host_isa() {
        HostIsa::AArch64 => aarch64::fused_rotate_output_code(template),
        HostIsa::X86_64 => x86_64::fused_rotate_output_code(template),
    }
}

fn select_fused_shape(
    admission: &DirectFusedSequenceAdmission,
) -> Result<FusedSelection, DirectFusedSequenceObjectError> {
    let [first_program, second_program] = admission.source_plan().programs()
    else {
        return Err(DirectFusedSequenceObjectError::ProgramShape);
    };
    let [first_artifact, second_artifact] = admission.source_plan().artifacts()
    else {
        return Err(DirectFusedSequenceObjectError::ProgramShape);
    };
    if let Some(selection) = select_non_output_shape(
        first_artifact.kind(),
        second_artifact.kind(),
        first_program,
        second_program,
    )? {
        return Ok(selection);
    }
    if second_artifact.kind() != DirectNativeKind::Output {
        return Err(DirectFusedSequenceObjectError::ProgramShape);
    }
    let output = validate_output_program(second_program)
        .map_err(|_error| DirectFusedSequenceObjectError::ProgramShape)?;
    match first_artifact.kind() {
        DirectNativeKind::NoOperation => {
            let no_operation = validate_no_operation_program(first_program)
                .map_err(|_error| {
                    DirectFusedSequenceObjectError::ProgramShape
                })?;
            Ok(FusedSelection::NoOperationOutput(no_operation, output))
        },
        DirectNativeKind::Rotate => {
            let rotate =
                validate_rotate_program(first_program).map_err(|_error| {
                    DirectFusedSequenceObjectError::ProgramShape
                })?;
            Ok(FusedSelection::RotateOutput(rotate, output))
        },
        DirectNativeKind::Crazy => {
            let crazy =
                validate_crazy_program(first_program).map_err(|_error| {
                    DirectFusedSequenceObjectError::ProgramShape
                })?;
            Ok(FusedSelection::CrazyOutput(crazy, output))
        },
        DirectNativeKind::Deopt
        | DirectNativeKind::HaltFetch
        | DirectNativeKind::HaltRegisters
        | DirectNativeKind::InitialHalt
        | DirectNativeKind::Input
        | DirectNativeKind::JumpCode
        | DirectNativeKind::JumpData
        | DirectNativeKind::NonGraphical
        | DirectNativeKind::Output => {
            Err(DirectFusedSequenceObjectError::ProgramShape)
        },
    }
}

fn select_crazy_shape(
    first_kind: DirectNativeKind,
    second_kind: DirectNativeKind,
    first_program: &RegionEffectProgram,
    second_program: &RegionEffectProgram,
) -> Result<Option<FusedSelection>, DirectFusedSequenceObjectError> {
    if first_kind == DirectNativeKind::Crazy {
        let crazy = validate_crazy_program(first_program)
            .map_err(|_error| DirectFusedSequenceObjectError::ProgramShape)?;
        return match second_kind {
            DirectNativeKind::Crazy => {
                let second = validate_crazy_program(second_program).map_err(
                    |_error| DirectFusedSequenceObjectError::ProgramShape,
                )?;
                Ok(Some(FusedSelection::CrazyPair(crazy, second)))
            },
            DirectNativeKind::NoOperation => {
                let no_operation =
                    validate_no_operation_program(second_program).map_err(
                        |_error| DirectFusedSequenceObjectError::ProgramShape,
                    )?;
                Ok(Some(FusedSelection::CrazyNoOperation(crazy, no_operation)))
            },
            DirectNativeKind::Rotate => {
                let rotate = validate_rotate_program(second_program).map_err(
                    |_error| DirectFusedSequenceObjectError::ProgramShape,
                )?;
                Ok(Some(FusedSelection::CrazyRotate(crazy, rotate)))
            },
            DirectNativeKind::Deopt
            | DirectNativeKind::HaltFetch
            | DirectNativeKind::HaltRegisters
            | DirectNativeKind::InitialHalt
            | DirectNativeKind::Input
            | DirectNativeKind::JumpCode
            | DirectNativeKind::JumpData
            | DirectNativeKind::NonGraphical
            | DirectNativeKind::Output => Ok(None),
        };
    }
    if first_kind == DirectNativeKind::NoOperation
        && second_kind == DirectNativeKind::Crazy
    {
        let no_operation = validate_no_operation_program(first_program)
            .map_err(|_error| DirectFusedSequenceObjectError::ProgramShape)?;
        let crazy = validate_crazy_program(second_program)
            .map_err(|_error| DirectFusedSequenceObjectError::ProgramShape)?;
        return Ok(Some(FusedSelection::NoOperationCrazy(no_operation, crazy)));
    }
    Ok(None)
}

fn select_non_output_shape(
    first_kind: DirectNativeKind,
    second_kind: DirectNativeKind,
    first_program: &RegionEffectProgram,
    second_program: &RegionEffectProgram,
) -> Result<Option<FusedSelection>, DirectFusedSequenceObjectError> {
    if let Some(selection) = select_crazy_shape(
        first_kind,
        second_kind,
        first_program,
        second_program,
    )? {
        return Ok(Some(selection));
    }
    if first_kind == DirectNativeKind::NoOperation
        && second_kind == DirectNativeKind::NoOperation
    {
        let first = validate_no_operation_program(first_program)
            .map_err(|_error| DirectFusedSequenceObjectError::ProgramShape)?;
        let second = validate_no_operation_program(second_program)
            .map_err(|_error| DirectFusedSequenceObjectError::ProgramShape)?;
        return Ok(Some(FusedSelection::NoOperationPair(first, second)));
    }
    if first_kind == DirectNativeKind::NoOperation
        && second_kind == DirectNativeKind::Rotate
    {
        let no_operation = validate_no_operation_program(first_program)
            .map_err(|_error| DirectFusedSequenceObjectError::ProgramShape)?;
        let rotate = validate_rotate_program(second_program)
            .map_err(|_error| DirectFusedSequenceObjectError::ProgramShape)?;
        return Ok(Some(FusedSelection::NoOperationRotate(
            no_operation,
            rotate,
        )));
    }
    select_rotate_shape(first_kind, second_kind, first_program, second_program)
}

fn select_rotate_shape(
    first_kind: DirectNativeKind,
    second_kind: DirectNativeKind,
    first_program: &RegionEffectProgram,
    second_program: &RegionEffectProgram,
) -> Result<Option<FusedSelection>, DirectFusedSequenceObjectError> {
    if first_kind != DirectNativeKind::Rotate {
        return Ok(None);
    }
    let rotate = validate_rotate_program(first_program)
        .map_err(|_error| DirectFusedSequenceObjectError::ProgramShape)?;
    match second_kind {
        DirectNativeKind::Crazy => {
            let crazy =
                validate_crazy_program(second_program).map_err(|_error| {
                    DirectFusedSequenceObjectError::ProgramShape
                })?;
            Ok(Some(FusedSelection::RotateCrazy(rotate, crazy)))
        },
        DirectNativeKind::NoOperation => {
            let no_operation = validate_no_operation_program(second_program)
                .map_err(|_error| {
                    DirectFusedSequenceObjectError::ProgramShape
                })?;
            Ok(Some(FusedSelection::RotateNoOperation(
                rotate,
                no_operation,
            )))
        },
        DirectNativeKind::Rotate => {
            let second =
                validate_rotate_program(second_program).map_err(|_error| {
                    DirectFusedSequenceObjectError::ProgramShape
                })?;
            Ok(Some(FusedSelection::RotatePair(rotate, second)))
        },
        DirectNativeKind::Deopt
        | DirectNativeKind::HaltFetch
        | DirectNativeKind::HaltRegisters
        | DirectNativeKind::InitialHalt
        | DirectNativeKind::Input
        | DirectNativeKind::JumpCode
        | DirectNativeKind::JumpData
        | DirectNativeKind::NonGraphical
        | DirectNativeKind::Output => Ok(None),
    }
}

const fn no_operation_commit(
    program: DirectNoOperationProgram,
) -> DirectCodeWriteCommit {
    DirectCodeWriteCommit {
        encrypted_address: program.live_in.address,
        encrypted_value: program.encrypted_value,
        next_code_pointer: program.next_code_pointer,
        next_data_pointer: program.next_data_pointer,
    }
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
