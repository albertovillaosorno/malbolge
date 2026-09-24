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
//   - Semantic admission for reviewed collapsed multi-step v6 regions.
// - Must-Not:
//   - Emit host code, grant executable authority, trust research reductions, or
//     generalize beyond explicitly reviewed multi-step shapes.
// - Allows:
//   - Inputs: verifier-projected register-masked v6 IR and runtime capability.
//   - Outputs: exact canonical identity plus proved collapsed net-effect data.
//   - Side effects: profile/runtime preflight only.
// - Split-When:
//   - Additional collapsed shapes require independent semantic proofs.
// - Merge-When:
//   - Direct v6 admission natively owns reviewed multi-step templates.
// - Summary:
//   - Proves reviewed two-step no-operation collapsed semantic shapes.
// - Description:
//   - Rechecks masks, live-ins, continuity, encryption, successors, and exact
//     bounded outcomes before publishing any collapsed-shape authority.
// - Usage:
//   - Consumed by shape-specific native object pipelines only after admission.
// - Defaults:
//   - Any profile, mask, effect, live-in, continuity, or outcome drift rejects.
//

//! Reviewed semantic admission and canonical objects for collapsed v6 regions.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{
    EFFECT_IR_REGISTER_MASK_VERSION, MemoryLiveIn, ProfileMemoryDelta,
    ProfileMemoryWrite, ProfileRegisterSet, ProfileRegisters,
    RegisterMaskedRegionEffectProgram, RunOutcome, RuntimeCapability,
    Termination, decode_profile_instruction, encrypt_profile_cell,
    preflight_portable_profile_requirement,
    profile_cell_decodes_to_no_operation, profile_pointer_successor,
};

use super::coff::build_minimal_coff;
use super::{
    CoffAdmissionError, DIRECT_REGISTER_MASKED_NO_OPERATION_HALT_BACKEND_ID,
    DIRECT_REGISTER_MASKED_NO_OPERATION_HALT_BACKEND_REVISION,
    DIRECT_REGISTER_MASKED_NO_OPERATION_PAIR_BACKEND_ID,
    DIRECT_REGISTER_MASKED_NO_OPERATION_PAIR_BACKEND_REVISION,
    DirectRegisterMaskedNoOperationHaltTemplate,
    DirectRegisterMaskedNoOperationPairTemplate, HostIsa, HostOperatingSystem,
    NATIVE_REGION_ABI_REVISION, NativeArtifactKey, NativeIdentityError,
    NativeTargetIdentity, RegionEffectIdentity,
    RegisterMaskedDirectAdmissionError, RegisterMaskedDirectAdmissionErrorKind,
    StructurallyAdmittedNativeObjectArtifact, UntrustedNativeObjectArtifact,
    aarch64, structurally_admit_coff, target_triple, x86_64,
};

/// Failure while emitting or verifying the collapsed no-operation/halt object.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectRegisterMaskedNoOperationHaltError {
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

/// Failure while emitting or verifying the collapsed no-operation pair object.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectRegisterMaskedNoOperationPairError {
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

/// Byte-exact verified object for the collapsed v6 no-operation/halt shape.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedRegisterMaskedNoOperationHaltNativeObjectArtifact {
    admission: VerifiedRegisterMaskedNoOperationHaltAdmission,
    artifact: StructurallyAdmittedNativeObjectArtifact,
}

impl Display for DirectRegisterMaskedNoOperationPairError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Admission(_kind) => {
                "collapsed v6 no-operation pair semantic admission failed"
            },
            Self::ArtifactIdentity => {
                "collapsed v6 no-operation pair artifact identity drifted"
            },
            Self::Coff(_error) => {
                "collapsed v6 no-operation pair COFF structure was rejected"
            },
            Self::Identity(_error) => {
                "collapsed v6 no-operation pair native identity failed"
            },
            Self::ObjectBytes => {
                "collapsed v6 no-operation pair object bytes drifted"
            },
            Self::TargetAbi => {
                "collapsed v6 no-operation pair target ABI is unsupported"
            },
            Self::TargetBackend => {
                "collapsed v6 no-operation pair target backend is unsupported"
            },
            Self::TargetFeatures => {
                "collapsed v6 no-operation pair target features are unsupported"
            },
            Self::TargetFormat => {
                "collapsed v6 no-operation pair backend requires Windows COFF"
            },
        })
    }
}

impl From<CoffAdmissionError> for DirectRegisterMaskedNoOperationPairError {
    fn from(error: CoffAdmissionError) -> Self {
        Self::Coff(error)
    }
}

impl Display for DirectRegisterMaskedNoOperationHaltError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Admission(_kind) => {
                "collapsed v6 no-operation/halt semantic admission failed"
            },
            Self::ArtifactIdentity => {
                "collapsed v6 no-operation/halt artifact identity drifted"
            },
            Self::Coff(_error) => {
                "collapsed v6 no-operation/halt COFF structure was rejected"
            },
            Self::Identity(_error) => {
                "collapsed v6 no-operation/halt native identity failed"
            },
            Self::ObjectBytes => {
                "collapsed v6 no-operation/halt object bytes drifted"
            },
            Self::TargetAbi => {
                "collapsed v6 no-operation/halt target ABI is unsupported"
            },
            Self::TargetBackend => {
                "collapsed v6 no-operation/halt target backend is unsupported"
            },
            Self::TargetFeatures => {
                "collapsed v6 no-operation/halt target features are unsupported"
            },
            Self::TargetFormat => {
                "collapsed v6 no-operation/halt backend requires Windows COFF"
            },
        })
    }
}

impl From<CoffAdmissionError> for DirectRegisterMaskedNoOperationHaltError {
    fn from(error: CoffAdmissionError) -> Self {
        Self::Coff(error)
    }
}

impl VerifiedRegisterMaskedNoOperationHaltNativeObjectArtifact {
    /// Returns the independently reconstructed collapsed semantic admission.
    #[must_use]
    pub const fn admission(
        &self,
    ) -> &VerifiedRegisterMaskedNoOperationHaltAdmission {
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

/// Byte-exact verified object for the collapsed v6 no-operation pair.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedRegisterMaskedNoOperationPairNativeObjectArtifact {
    admission: VerifiedRegisterMaskedNoOperationPairAdmission,
    artifact: StructurallyAdmittedNativeObjectArtifact,
}

impl VerifiedRegisterMaskedNoOperationPairNativeObjectArtifact {
    /// Returns independently reconstructed pair semantic admission.
    #[must_use]
    pub const fn admission(
        &self,
    ) -> &VerifiedRegisterMaskedNoOperationPairAdmission {
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

/// Proved net effect for one collapsed no-operation followed by halt.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedRegisterMaskedNoOperationHaltAdmission {
    code_live_in: MemoryLiveIn,
    encrypted_address: u32,
    encrypted_value: u32,
    entry_code_pointer: u32,
    entry_data_pointer: u32,
    halt_live_in: MemoryLiveIn,
    identity: RegionEffectIdentity,
    next_code_pointer: u32,
    next_data_pointer: u32,
    required_memory_words: u64,
}

/// Proved net effect for two consecutive collapsed no-operations.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedRegisterMaskedNoOperationPairAdmission {
    entry_code_pointer: u32,
    entry_data_pointer: u32,
    first_encrypted_value: u32,
    first_live_in: MemoryLiveIn,
    identity: RegionEffectIdentity,
    next_code_pointer: u32,
    next_data_pointer: u32,
    required_memory_words: u64,
    second_code_pointer: u32,
    second_data_pointer: u32,
    second_encrypted_value: u32,
    second_live_in: MemoryLiveIn,
}

impl VerifiedRegisterMaskedNoOperationHaltAdmission {
    /// Returns the exact entry code-cell live-in.
    #[must_use]
    pub const fn code_live_in(&self) -> MemoryLiveIn {
        self.code_live_in
    }

    /// Returns the code cell encrypted by the first semantic step.
    #[must_use]
    pub const fn encrypted_address(&self) -> u32 {
        self.encrypted_address
    }

    /// Returns the exact encrypted value committed by the first step.
    #[must_use]
    pub const fn encrypted_value(&self) -> u32 {
        self.encrypted_value
    }

    /// Returns the required entry code pointer.
    #[must_use]
    pub const fn entry_code_pointer(&self) -> u32 {
        self.entry_code_pointer
    }

    /// Returns the required entry data pointer.
    #[must_use]
    pub const fn entry_data_pointer(&self) -> u32 {
        self.entry_data_pointer
    }

    /// Returns the exact second-step halt code-cell live-in.
    #[must_use]
    pub const fn halt_live_in(&self) -> MemoryLiveIn {
        self.halt_live_in
    }

    /// Returns complete canonical v6 identity for the two-step region.
    #[must_use]
    pub const fn identity(&self) -> &RegionEffectIdentity {
        &self.identity
    }

    /// Returns the code pointer retained after the no-operation and halt.
    #[must_use]
    pub const fn next_code_pointer(&self) -> u32 {
        self.next_code_pointer
    }

    /// Returns the data pointer retained after the no-operation and halt.
    #[must_use]
    pub const fn next_data_pointer(&self) -> u32 {
        self.next_data_pointer
    }

    /// Returns the exact declared memory capacity bound into this admission.
    #[must_use]
    pub const fn required_memory_words(&self) -> u64 {
        self.required_memory_words
    }
}

impl VerifiedRegisterMaskedNoOperationPairAdmission {
    /// Returns the required entry code pointer.
    #[must_use]
    pub const fn entry_code_pointer(&self) -> u32 {
        self.entry_code_pointer
    }

    /// Returns the required entry data pointer.
    #[must_use]
    pub const fn entry_data_pointer(&self) -> u32 {
        self.entry_data_pointer
    }

    /// Returns the first code-cell value after self-encryption.
    #[must_use]
    pub const fn first_encrypted_value(&self) -> u32 {
        self.first_encrypted_value
    }

    /// Returns the first exact code-cell live-in.
    #[must_use]
    pub const fn first_live_in(&self) -> MemoryLiveIn {
        self.first_live_in
    }

    /// Returns complete canonical v6 identity for the two-step region.
    #[must_use]
    pub const fn identity(&self) -> &RegionEffectIdentity {
        &self.identity
    }

    /// Returns the code pointer after both no-operations.
    #[must_use]
    pub const fn next_code_pointer(&self) -> u32 {
        self.next_code_pointer
    }

    /// Returns the data pointer after both no-operations.
    #[must_use]
    pub const fn next_data_pointer(&self) -> u32 {
        self.next_data_pointer
    }

    /// Returns the exact declared memory capacity bound into this admission.
    #[must_use]
    pub const fn required_memory_words(&self) -> u64 {
        self.required_memory_words
    }

    /// Returns the code pointer at the second no-operation.
    #[must_use]
    pub const fn second_code_pointer(&self) -> u32 {
        self.second_code_pointer
    }

    /// Returns the data pointer at the second no-operation.
    #[must_use]
    pub const fn second_data_pointer(&self) -> u32 {
        self.second_data_pointer
    }

    /// Returns the second code-cell value after self-encryption.
    #[must_use]
    pub const fn second_encrypted_value(&self) -> u32 {
        self.second_encrypted_value
    }

    /// Returns the second exact code-cell live-in.
    #[must_use]
    pub const fn second_live_in(&self) -> MemoryLiveIn {
        self.second_live_in
    }
}

/// Admits exactly one reviewed two-step no-operation then halt net effect.
///
/// This grants semantic collapsed-shape authority only. It does not select a
/// host target, emit bytes, load executable memory, or make the region
/// callable.
///
/// # Errors
///
/// Returns the ordinary v6 admission error when profile/identity preflight or
/// any reviewed two-step shape proof fails.
pub fn admit_register_masked_no_operation_halt<'requirement>(
    program: &'requirement RegisterMaskedRegionEffectProgram,
    runtime: &'static RuntimeCapability,
) -> Result<
    VerifiedRegisterMaskedNoOperationHaltAdmission,
    RegisterMaskedDirectAdmissionError<'requirement>,
> {
    if !program
        .profile_requirement
        .is_canonical_for(&program.profile_id)
    {
        return Err(RegisterMaskedDirectAdmissionError::profile_requirement());
    }
    preflight_portable_profile_requirement(
        &program.profile_id,
        &program.profile_requirement,
        program.required_memory_words(),
        runtime,
    )
    .map_err(RegisterMaskedDirectAdmissionError::profile)?;
    let identity = RegionEffectIdentity::new_register_masked(program)
        .map_err(RegisterMaskedDirectAdmissionError::identity)?;
    validate_no_operation_halt(program, identity)
        .ok_or_else(RegisterMaskedDirectAdmissionError::unsupported_program)
}

/// Admits exactly one reviewed two-step no-operation pair net effect.
///
/// This grants semantic collapsed-shape authority only. It does not select a
/// host target, emit bytes, load executable memory, or make the region
/// callable.
///
/// # Errors
///
/// Returns the ordinary v6 admission error when profile/identity preflight or
/// any reviewed pair-shape proof fails.
pub fn admit_register_masked_no_operation_pair<'requirement>(
    program: &'requirement RegisterMaskedRegionEffectProgram,
    runtime: &'static RuntimeCapability,
) -> Result<
    VerifiedRegisterMaskedNoOperationPairAdmission,
    RegisterMaskedDirectAdmissionError<'requirement>,
> {
    if !program
        .profile_requirement
        .is_canonical_for(&program.profile_id)
    {
        return Err(RegisterMaskedDirectAdmissionError::profile_requirement());
    }
    preflight_portable_profile_requirement(
        &program.profile_id,
        &program.profile_requirement,
        program.required_memory_words(),
        runtime,
    )
    .map_err(RegisterMaskedDirectAdmissionError::profile)?;
    let identity = RegionEffectIdentity::new_register_masked(program)
        .map_err(RegisterMaskedDirectAdmissionError::identity)?;
    validate_no_operation_pair(program, identity)
        .ok_or_else(RegisterMaskedDirectAdmissionError::unsupported_program)
}

fn validate_no_operation_halt(
    program: &RegisterMaskedRegionEffectProgram,
    identity: RegionEffectIdentity,
) -> Option<VerifiedRegisterMaskedNoOperationHaltAdmission> {
    if !no_operation_halt_header_supported(program) {
        return None;
    }
    let first = *program.effects.first()?;
    let second = *program.effects.get(1)?;
    let memory_words =
        u32::try_from(program.profile_requirement.memory_words).ok()?;
    let entry_code_pointer = first.before.registers.code_pointer;
    let entry_data_pointer = first.before.registers.data_pointer;
    let next_code_pointer =
        profile_pointer_successor(entry_code_pointer, memory_words)?;
    let next_data_pointer =
        profile_pointer_successor(entry_data_pointer, memory_words)?;
    let code_live_in = find_live_in(program, entry_code_pointer)?;
    let halt_live_in = find_live_in(program, next_code_pointer)?;
    let encrypted_value = encrypt_profile_cell(code_live_in.value)?;
    if !no_operation_effect_matches(
        first,
        code_live_in,
        encrypted_value,
        (next_code_pointer, next_data_pointer),
    ) || !second_effect_matches(second, halt_live_in)
        || first.after != second.before
    {
        return None;
    }
    Some(VerifiedRegisterMaskedNoOperationHaltAdmission {
        code_live_in,
        encrypted_address: entry_code_pointer,
        encrypted_value,
        entry_code_pointer,
        entry_data_pointer,
        halt_live_in,
        identity,
        next_code_pointer,
        next_data_pointer,
        required_memory_words: program.required_memory_words(),
    })
}

fn validate_no_operation_pair(
    program: &RegisterMaskedRegionEffectProgram,
    identity: RegionEffectIdentity,
) -> Option<VerifiedRegisterMaskedNoOperationPairAdmission> {
    if !no_operation_pair_header_supported(program) {
        return None;
    }
    let first = *program.effects.first()?;
    let second = *program.effects.get(1)?;
    let memory_words =
        u32::try_from(program.profile_requirement.memory_words).ok()?;
    let entry_code_pointer = first.before.registers.code_pointer;
    let entry_data_pointer = first.before.registers.data_pointer;
    let second_code_pointer =
        profile_pointer_successor(entry_code_pointer, memory_words)?;
    let second_data_pointer =
        profile_pointer_successor(entry_data_pointer, memory_words)?;
    let next_code_pointer =
        profile_pointer_successor(second_code_pointer, memory_words)?;
    let next_data_pointer =
        profile_pointer_successor(second_data_pointer, memory_words)?;
    let first_live_in = find_live_in(program, entry_code_pointer)?;
    let second_live_in = find_live_in(program, second_code_pointer)?;
    let first_encrypted_value = encrypt_profile_cell(first_live_in.value)?;
    let second_encrypted_value = encrypt_profile_cell(second_live_in.value)?;
    if !no_operation_effect_matches(
        first,
        first_live_in,
        first_encrypted_value,
        (second_code_pointer, second_data_pointer),
    ) || !no_operation_effect_matches(
        second,
        second_live_in,
        second_encrypted_value,
        (next_code_pointer, next_data_pointer),
    ) || first.after != second.before
    {
        return None;
    }
    Some(VerifiedRegisterMaskedNoOperationPairAdmission {
        entry_code_pointer,
        entry_data_pointer,
        first_encrypted_value,
        first_live_in,
        identity,
        next_code_pointer,
        next_data_pointer,
        required_memory_words: program.required_memory_words(),
        second_code_pointer,
        second_data_pointer,
        second_encrypted_value,
        second_live_in,
    })
}

fn no_operation_pair_header_supported(
    program: &RegisterMaskedRegionEffectProgram,
) -> bool {
    let entry_reads = ProfileRegisterSet {
        accumulator: false,
        code_pointer: true,
        data_pointer: true,
    };
    program.format_version() == EFFECT_IR_REGISTER_MASK_VERSION
        && program.step_budget == 2
        && program.effects.len() == 2
        && program.memory_live_ins.len() == 2
        && program.register_live_ins == entry_reads
        && program.register_writes.len() == 2
        && program.register_writes.first().copied() == Some(entry_reads)
        && program.register_writes.get(1).copied() == Some(entry_reads)
        && program.outcome == (RunOutcome::BudgetExhausted { steps: 2 })
        && program.fits_declared_profile_capacity()
}

fn no_operation_halt_header_supported(
    program: &RegisterMaskedRegionEffectProgram,
) -> bool {
    let entry_reads = ProfileRegisterSet {
        accumulator: false,
        code_pointer: true,
        data_pointer: true,
    };
    program.format_version() == EFFECT_IR_REGISTER_MASK_VERSION
        && program.step_budget == 2
        && program.effects.len() == 2
        && program.memory_live_ins.len() == 2
        && program.register_live_ins == entry_reads
        && program.register_writes.len() == 2
        && program.register_writes.first().copied() == Some(entry_reads)
        && program.register_writes.get(1).copied()
            == Some(ProfileRegisterSet::default())
        && program.outcome
            == (RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 2,
            })
        && program.fits_declared_profile_capacity()
}

fn find_live_in(
    program: &RegisterMaskedRegionEffectProgram,
    address: u32,
) -> Option<MemoryLiveIn> {
    program
        .memory_live_ins
        .iter()
        .copied()
        .find(|live_in| live_in.address == address)
}

fn no_operation_effect_matches(
    effect: malbolge::EffectOp,
    live_in: MemoryLiveIn,
    encrypted_value: u32,
    successors: (u32, u32),
) -> bool {
    let (next_code_pointer, next_data_pointer) = successors;
    let expected_after = malbolge::ProfileMachineObservation {
        registers: ProfileRegisters {
            accumulator: effect.before.registers.accumulator,
            code_pointer: next_code_pointer,
            data_pointer: next_data_pointer,
        },
        ..effect.before
    };
    let expected_encryption =
        (live_in.value != encrypted_value).then_some(ProfileMemoryWrite {
            address: effect.before.registers.code_pointer,
            after: encrypted_value,
            before: live_in.value,
        });
    effect.before.termination.is_none()
        && effect.after == expected_after
        && effect.input.is_none()
        && effect.output.is_none()
        && effect.memory_delta
            == (ProfileMemoryDelta {
                data: None,
                encryption: expected_encryption,
            })
        && live_in.address == effect.before.registers.code_pointer
        && profile_cell_decodes_to_no_operation(
            live_in.value,
            effect.before.registers.code_pointer,
        )
}

fn second_effect_matches(
    effect: malbolge::EffectOp,
    halt_live_in: MemoryLiveIn,
) -> bool {
    let expected_after = malbolge::ProfileMachineObservation {
        termination: Some(Termination::HaltInstruction),
        ..effect.before
    };
    effect.before.termination.is_none()
        && effect.after == expected_after
        && effect.input.is_none()
        && effect.output.is_none()
        && effect.memory_delta == ProfileMemoryDelta::default()
        && halt_live_in.address == effect.before.registers.code_pointer
        && decode_profile_instruction(
            halt_live_in.value,
            effect.before.registers.code_pointer,
        ) == Some(b'v')
}

/// Emits one untrusted canonical candidate for a collapsed no-operation pair.
///
/// # Errors
///
/// Returns a pair-object error on semantic admission, target, identity, or
/// canonical byte construction failure.
pub fn emit_direct_register_masked_no_operation_pair_coff(
    program: &RegisterMaskedRegionEffectProgram,
    runtime: &'static RuntimeCapability,
    target: NativeTargetIdentity,
) -> Result<
    UntrustedNativeObjectArtifact,
    DirectRegisterMaskedNoOperationPairError,
> {
    let admission = admit_register_masked_no_operation_pair(program, runtime)
        .map_err(|error| {
        DirectRegisterMaskedNoOperationPairError::Admission(error.kind())
    })?;
    validate_no_operation_pair_target(&target)?;
    let key = NativeArtifactKey::new_register_masked(program, target)
        .map_err(DirectRegisterMaskedNoOperationPairError::Identity)?;
    let triple = target_triple(key.target().host_isa());
    let object = canonical_no_operation_pair_coff(&key, &admission)?;
    Ok(UntrustedNativeObjectArtifact::from_emitter_output(
        key, object, triple,
    ))
}

/// Promotes only exact canonical collapsed no-operation-pair object bytes.
///
/// # Errors
///
/// Returns a pair-object error on semantic, identity, target, structural, or
/// canonical-byte mismatch.
pub fn verify_direct_register_masked_no_operation_pair(
    artifact: &UntrustedNativeObjectArtifact,
    program: &RegisterMaskedRegionEffectProgram,
    runtime: &'static RuntimeCapability,
) -> Result<
    VerifiedRegisterMaskedNoOperationPairNativeObjectArtifact,
    DirectRegisterMaskedNoOperationPairError,
> {
    let admission = admit_register_masked_no_operation_pair(program, runtime)
        .map_err(|error| {
        DirectRegisterMaskedNoOperationPairError::Admission(error.kind())
    })?;
    validate_no_operation_pair_target(artifact.key().target())?;
    let expected_key = NativeArtifactKey::new_register_masked(
        program,
        artifact.key().target().clone(),
    )
    .map_err(DirectRegisterMaskedNoOperationPairError::Identity)?;
    if artifact.key() != &expected_key
        || artifact.target_triple()
            != target_triple(expected_key.target().host_isa())
    {
        return Err(DirectRegisterMaskedNoOperationPairError::ArtifactIdentity);
    }
    let admitted = structurally_admit_coff(artifact)?;
    let expected = canonical_no_operation_pair_coff(&expected_key, &admission)?;
    if admitted.object() != expected {
        return Err(DirectRegisterMaskedNoOperationPairError::ObjectBytes);
    }
    Ok(VerifiedRegisterMaskedNoOperationPairNativeObjectArtifact {
        admission,
        artifact: admitted,
    })
}

fn validate_no_operation_pair_target(
    target: &NativeTargetIdentity,
) -> Result<(), DirectRegisterMaskedNoOperationPairError> {
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(DirectRegisterMaskedNoOperationPairError::TargetFormat);
    }
    if target.backend_id()
        != DIRECT_REGISTER_MASKED_NO_OPERATION_PAIR_BACKEND_ID
        || target.backend_revision()
            != DIRECT_REGISTER_MASKED_NO_OPERATION_PAIR_BACKEND_REVISION
    {
        return Err(DirectRegisterMaskedNoOperationPairError::TargetBackend);
    }
    if target.native_abi_revision() != NATIVE_REGION_ABI_REVISION {
        return Err(DirectRegisterMaskedNoOperationPairError::TargetAbi);
    }
    if !target.required_features().is_empty() {
        return Err(DirectRegisterMaskedNoOperationPairError::TargetFeatures);
    }
    Ok(())
}

fn canonical_no_operation_pair_coff(
    key: &NativeArtifactKey,
    admission: &VerifiedRegisterMaskedNoOperationPairAdmission,
) -> Result<Vec<u8>, DirectRegisterMaskedNoOperationPairError> {
    let first = admission.first_live_in();
    let second = admission.second_live_in();
    let template = DirectRegisterMaskedNoOperationPairTemplate {
        entry_code_pointer: admission.entry_code_pointer(),
        entry_data_pointer: admission.entry_data_pointer(),
        first_encrypted_address: first.address,
        first_encrypted_value: admission.first_encrypted_value(),
        first_live_in: first.value,
        next_code_pointer: admission.next_code_pointer(),
        next_data_pointer: admission.next_data_pointer(),
        required_memory_words: admission.required_memory_words(),
        second_code_pointer: admission.second_code_pointer(),
        second_encrypted_address: second.address,
        second_encrypted_value: admission.second_encrypted_value(),
        second_live_in: second.value,
    };
    let text = match key.target().host_isa() {
        HostIsa::AArch64 => {
            aarch64::register_masked_no_operation_pair_code(template)
        },
        HostIsa::X86_64 => {
            x86_64::register_masked_no_operation_pair_code(template)
        },
    }
    .ok_or(DirectRegisterMaskedNoOperationPairError::ObjectBytes)?;
    build_minimal_coff(key, &text)
        .ok_or(DirectRegisterMaskedNoOperationPairError::ObjectBytes)
}

/// Emits one untrusted canonical candidate for collapsed no-operation/halt.
///
/// # Errors
///
/// Returns a collapsed-object error on semantic admission, target, identity, or
/// canonical byte construction failure.
pub fn emit_direct_register_masked_no_operation_halt_coff(
    program: &RegisterMaskedRegionEffectProgram,
    runtime: &'static RuntimeCapability,
    target: NativeTargetIdentity,
) -> Result<
    UntrustedNativeObjectArtifact,
    DirectRegisterMaskedNoOperationHaltError,
> {
    let admission = admit_register_masked_no_operation_halt(program, runtime)
        .map_err(|error| {
        DirectRegisterMaskedNoOperationHaltError::Admission(error.kind())
    })?;
    validate_collapsed_target(&target)?;
    let key = NativeArtifactKey::new_register_masked(program, target)
        .map_err(DirectRegisterMaskedNoOperationHaltError::Identity)?;
    let triple = target_triple(key.target().host_isa());
    let object = canonical_collapsed_coff(&key, &admission)?;
    Ok(UntrustedNativeObjectArtifact::from_emitter_output(
        key, object, triple,
    ))
}

/// Promotes only exact canonical collapsed no-operation/halt object bytes.
///
/// The verifier independently reconstructs semantic admission, exact v6 key,
/// target contract, structural COFF admission, and canonical instruction bytes.
///
/// # Errors
///
/// Returns a collapsed-object error on any semantic, identity, target,
/// structural, or canonical-byte mismatch.
pub fn verify_direct_register_masked_no_operation_halt(
    artifact: &UntrustedNativeObjectArtifact,
    program: &RegisterMaskedRegionEffectProgram,
    runtime: &'static RuntimeCapability,
) -> Result<
    VerifiedRegisterMaskedNoOperationHaltNativeObjectArtifact,
    DirectRegisterMaskedNoOperationHaltError,
> {
    let admission = admit_register_masked_no_operation_halt(program, runtime)
        .map_err(|error| {
        DirectRegisterMaskedNoOperationHaltError::Admission(error.kind())
    })?;
    validate_collapsed_target(artifact.key().target())?;
    let expected_key = NativeArtifactKey::new_register_masked(
        program,
        artifact.key().target().clone(),
    )
    .map_err(DirectRegisterMaskedNoOperationHaltError::Identity)?;
    if artifact.key() != &expected_key
        || artifact.target_triple()
            != target_triple(expected_key.target().host_isa())
    {
        return Err(DirectRegisterMaskedNoOperationHaltError::ArtifactIdentity);
    }
    let admitted = structurally_admit_coff(artifact)?;
    let expected = canonical_collapsed_coff(&expected_key, &admission)?;
    if admitted.object() != expected {
        return Err(DirectRegisterMaskedNoOperationHaltError::ObjectBytes);
    }
    Ok(VerifiedRegisterMaskedNoOperationHaltNativeObjectArtifact {
        admission,
        artifact: admitted,
    })
}

fn validate_collapsed_target(
    target: &NativeTargetIdentity,
) -> Result<(), DirectRegisterMaskedNoOperationHaltError> {
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(DirectRegisterMaskedNoOperationHaltError::TargetFormat);
    }
    if target.backend_id()
        != DIRECT_REGISTER_MASKED_NO_OPERATION_HALT_BACKEND_ID
        || target.backend_revision()
            != DIRECT_REGISTER_MASKED_NO_OPERATION_HALT_BACKEND_REVISION
    {
        return Err(DirectRegisterMaskedNoOperationHaltError::TargetBackend);
    }
    if target.native_abi_revision() != NATIVE_REGION_ABI_REVISION {
        return Err(DirectRegisterMaskedNoOperationHaltError::TargetAbi);
    }
    if !target.required_features().is_empty() {
        return Err(DirectRegisterMaskedNoOperationHaltError::TargetFeatures);
    }
    Ok(())
}

fn canonical_collapsed_coff(
    key: &NativeArtifactKey,
    admission: &VerifiedRegisterMaskedNoOperationHaltAdmission,
) -> Result<Vec<u8>, DirectRegisterMaskedNoOperationHaltError> {
    let code_live_in = admission.code_live_in();
    let halt_live_in = admission.halt_live_in();
    let template = DirectRegisterMaskedNoOperationHaltTemplate {
        code_live_in: code_live_in.value,
        encrypted_address: admission.encrypted_address(),
        encrypted_value: admission.encrypted_value(),
        entry_code_pointer: admission.entry_code_pointer(),
        entry_data_pointer: admission.entry_data_pointer(),
        halt_live_in: halt_live_in.value,
        next_code_pointer: admission.next_code_pointer(),
        next_data_pointer: admission.next_data_pointer(),
        required_memory_words: admission.required_memory_words(),
    };
    let text = match key.target().host_isa() {
        HostIsa::AArch64 => {
            aarch64::register_masked_no_operation_halt_code(template)
        },
        HostIsa::X86_64 => {
            x86_64::register_masked_no_operation_halt_code(template)
        },
    }
    .ok_or(DirectRegisterMaskedNoOperationHaltError::ObjectBytes)?;
    build_minimal_coff(key, &text)
        .ok_or(DirectRegisterMaskedNoOperationHaltError::ObjectBytes)
}
