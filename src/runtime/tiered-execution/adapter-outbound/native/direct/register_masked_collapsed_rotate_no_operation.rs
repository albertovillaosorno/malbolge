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
//   - Semantic admission for collapsed v6 rotate then no-operation.
// - Must-Not:
//   - Emit host code, grant executable authority, or admit the internal-alias
//     form where rotate rewrites the second instruction before it executes.
// - Allows:
//   - Inputs: verifier-projected register-masked v6 IR and runtime capability.
//   - Outputs: exact canonical identity plus proved collapsed net-effect data.
//   - Side effects: profile/runtime preflight only.
// - Split-When:
//   - Native object, load, ABI, or invocation authority is introduced.
// - Merge-When:
//   - A shared collapsed semantic primitive proves identical obligations.
// - Summary:
//   - Proves the reviewed non-aliasing two-step rotate then no-operation shape.
// - Description:
//   - Rechecks masks, three distinct live-ins, both encryptions, rotation,
//     continuity, pointer successors, and the exact budget-exhausted outcome.
// - Usage:
//   - May feed a future shape-specific native object pipeline after admission.
// - Defaults:
//   - Any profile, mask, effect, alias, continuity, or outcome drift rejects.
//

//! Semantic admission for non-aliasing collapsed v6 rotate/no-operation
//! regions.

use malbolge::{
    EFFECT_IR_REGISTER_MASK_VERSION, EffectOp, MemoryLiveIn,
    ProfileMachineObservation, ProfileMemoryDelta, ProfileMemoryWrite,
    ProfileRegisterSet, ProfileRegisters, RegisterMaskedRegionEffectProgram,
    RunOutcome, RuntimeCapability, decode_profile_instruction,
    encrypt_profile_cell, preflight_portable_profile_requirement,
    profile_cell_decodes_to_no_operation, profile_pointer_successor,
    profile_rotate,
};

use super::{RegionEffectIdentity, RegisterMaskedDirectAdmissionError};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct RotateEffectProof {
    code_live_in: MemoryLiveIn,
    data_live_in: MemoryLiveIn,
    encrypted_value: u32,
    next_code_pointer: u32,
    next_data_pointer: u32,
    rotated_value: u32,
}

/// Proved net effect for one collapsed rotate followed by no-operation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedRegisterMaskedRotateNoOperationAdmission {
    entry_code_pointer: u32,
    entry_data_pointer: u32,
    identity: RegionEffectIdentity,
    next_code_pointer: u32,
    next_data_pointer: u32,
    no_operation_encrypted_value: u32,
    no_operation_live_in: MemoryLiveIn,
    required_memory_words: u64,
    rotate_code_live_in: MemoryLiveIn,
    rotate_data_live_in: MemoryLiveIn,
    rotate_encrypted_value: u32,
    rotated_value: u32,
    second_code_pointer: u32,
    second_data_pointer: u32,
}

impl VerifiedRegisterMaskedRotateNoOperationAdmission {
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

    /// Returns complete canonical v6 identity for the two-step region.
    #[must_use]
    pub const fn identity(&self) -> &RegionEffectIdentity {
        &self.identity
    }

    /// Returns the code pointer after both semantic steps.
    #[must_use]
    pub const fn next_code_pointer(&self) -> u32 {
        self.next_code_pointer
    }

    /// Returns the data pointer after both semantic steps.
    #[must_use]
    pub const fn next_data_pointer(&self) -> u32 {
        self.next_data_pointer
    }

    /// Returns the second no-operation code cell after encryption.
    #[must_use]
    pub const fn no_operation_encrypted_value(&self) -> u32 {
        self.no_operation_encrypted_value
    }

    /// Returns the exact second no-operation code-cell live-in.
    #[must_use]
    pub const fn no_operation_live_in(&self) -> MemoryLiveIn {
        self.no_operation_live_in
    }

    /// Returns the declared memory capacity bound into this admission.
    #[must_use]
    pub const fn required_memory_words(&self) -> u64 {
        self.required_memory_words
    }

    /// Returns the exact first rotate code-cell live-in.
    #[must_use]
    pub const fn rotate_code_live_in(&self) -> MemoryLiveIn {
        self.rotate_code_live_in
    }

    /// Returns the exact first rotate data-cell live-in.
    #[must_use]
    pub const fn rotate_data_live_in(&self) -> MemoryLiveIn {
        self.rotate_data_live_in
    }

    /// Returns the first rotate code cell after encryption.
    #[must_use]
    pub const fn rotate_encrypted_value(&self) -> u32 {
        self.rotate_encrypted_value
    }

    /// Returns the rotated data value committed to memory and accumulator.
    #[must_use]
    pub const fn rotated_value(&self) -> u32 {
        self.rotated_value
    }

    /// Returns the code pointer at the second semantic step.
    #[must_use]
    pub const fn second_code_pointer(&self) -> u32 {
        self.second_code_pointer
    }

    /// Returns the data pointer at the second semantic step.
    #[must_use]
    pub const fn second_data_pointer(&self) -> u32 {
        self.second_data_pointer
    }
}

/// Admits exactly one reviewed non-aliasing rotate/no-operation v6 net effect.
///
/// This grants semantic collapsed-shape authority only. It does not select a
/// host target, emit bytes, load executable memory, or make the region
/// callable.
///
/// # Errors
///
/// Returns the ordinary v6 admission error when profile/identity preflight or
/// any reviewed two-step shape proof fails.
pub fn admit_register_masked_rotate_no_operation<'requirement>(
    program: &'requirement RegisterMaskedRegionEffectProgram,
    runtime: &'static RuntimeCapability,
) -> Result<
    VerifiedRegisterMaskedRotateNoOperationAdmission,
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
    validate_rotate_no_operation(program, identity)
        .ok_or_else(RegisterMaskedDirectAdmissionError::unsupported_program)
}

fn validate_rotate_no_operation(
    program: &RegisterMaskedRegionEffectProgram,
    identity: RegionEffectIdentity,
) -> Option<VerifiedRegisterMaskedRotateNoOperationAdmission> {
    if !header_supported(program) {
        return None;
    }
    let first = *program.effects.first()?;
    let second = *program.effects.get(1)?;
    let memory_words =
        u32::try_from(program.profile_requirement.memory_words).ok()?;
    let rotate = derive_rotate_effect(program, first, memory_words)?;
    if first.after != second.before {
        return None;
    }
    let no_operation_live_in = find_live_in(program, rotate.next_code_pointer)?;
    if rotate.data_live_in.address == no_operation_live_in.address
        || rotate.code_live_in.address == no_operation_live_in.address
    {
        return None;
    }
    let no_operation_encrypted_value =
        encrypt_profile_cell(no_operation_live_in.value)?;
    let next_code_pointer =
        profile_pointer_successor(rotate.next_code_pointer, memory_words)?;
    let next_data_pointer =
        profile_pointer_successor(rotate.next_data_pointer, memory_words)?;
    if !no_operation_effect_matches(
        second,
        no_operation_live_in,
        no_operation_encrypted_value,
        (next_code_pointer, next_data_pointer),
    ) {
        return None;
    }
    Some(VerifiedRegisterMaskedRotateNoOperationAdmission {
        entry_code_pointer: first.before.registers.code_pointer,
        entry_data_pointer: first.before.registers.data_pointer,
        identity,
        next_code_pointer,
        next_data_pointer,
        no_operation_encrypted_value,
        no_operation_live_in,
        required_memory_words: program.required_memory_words(),
        rotate_code_live_in: rotate.code_live_in,
        rotate_data_live_in: rotate.data_live_in,
        rotate_encrypted_value: rotate.encrypted_value,
        rotated_value: rotate.rotated_value,
        second_code_pointer: rotate.next_code_pointer,
        second_data_pointer: rotate.next_data_pointer,
    })
}

fn header_supported(program: &RegisterMaskedRegionEffectProgram) -> bool {
    let entry_reads = ProfileRegisterSet {
        accumulator: false,
        code_pointer: true,
        data_pointer: true,
    };
    let rotate_writes = ProfileRegisterSet {
        accumulator: true,
        code_pointer: true,
        data_pointer: true,
    };
    program.format_version() == EFFECT_IR_REGISTER_MASK_VERSION
        && program.step_budget == 2
        && program.effects.len() == 2
        && program.memory_live_ins.len() == 3
        && program.register_live_ins == entry_reads
        && program.register_writes.len() == 2
        && program.register_writes.first().copied() == Some(rotate_writes)
        && program.register_writes.get(1).copied() == Some(entry_reads)
        && program.outcome == (RunOutcome::BudgetExhausted { steps: 2 })
        && program.fits_declared_profile_capacity()
}

fn derive_rotate_effect(
    program: &RegisterMaskedRegionEffectProgram,
    effect: EffectOp,
    memory_words: u32,
) -> Option<RotateEffectProof> {
    let before = effect.before;
    let code_live_in = find_live_in(program, before.registers.code_pointer)?;
    let data_live_in = find_live_in(program, before.registers.data_pointer)?;
    if code_live_in.address == data_live_in.address
        || data_live_in.value >= memory_words
        || decode_profile_instruction(
            code_live_in.value,
            before.registers.code_pointer,
        ) != Some(b'*')
    {
        return None;
    }
    let encrypted_value = encrypt_profile_cell(code_live_in.value)?;
    let rotated_value = profile_rotate(data_live_in.value, memory_words);
    let next_code_pointer =
        profile_pointer_successor(before.registers.code_pointer, memory_words)?;
    let next_data_pointer =
        profile_pointer_successor(before.registers.data_pointer, memory_words)?;
    let expected_after = ProfileMachineObservation {
        registers: ProfileRegisters {
            accumulator: rotated_value,
            code_pointer: next_code_pointer,
            data_pointer: next_data_pointer,
        },
        ..before
    };
    if effect.before.termination.is_some()
        || effect.after != expected_after
        || effect.input.is_some()
        || effect.output.is_some()
        || effect.memory_delta
            != rotate_memory_delta(
                code_live_in,
                data_live_in,
                encrypted_value,
                rotated_value,
            )
    {
        return None;
    }
    Some(RotateEffectProof {
        code_live_in,
        data_live_in,
        encrypted_value,
        next_code_pointer,
        next_data_pointer,
        rotated_value,
    })
}

fn rotate_memory_delta(
    code_live_in: MemoryLiveIn,
    data_live_in: MemoryLiveIn,
    encrypted_value: u32,
    rotated_value: u32,
) -> ProfileMemoryDelta {
    let data =
        (data_live_in.value != rotated_value).then_some(ProfileMemoryWrite {
            address: data_live_in.address,
            after: rotated_value,
            before: data_live_in.value,
        });
    let encryption =
        (code_live_in.value != encrypted_value).then_some(ProfileMemoryWrite {
            address: code_live_in.address,
            after: encrypted_value,
            before: code_live_in.value,
        });
    ProfileMemoryDelta { data, encryption }
}

fn no_operation_effect_matches(
    effect: EffectOp,
    live_in: MemoryLiveIn,
    encrypted_value: u32,
    successors: (u32, u32),
) -> bool {
    let (next_code_pointer, next_data_pointer) = successors;
    let expected_after = ProfileMachineObservation {
        registers: ProfileRegisters {
            accumulator: effect.before.registers.accumulator,
            code_pointer: next_code_pointer,
            data_pointer: next_data_pointer,
        },
        ..effect.before
    };
    let encryption =
        (live_in.value != encrypted_value).then_some(ProfileMemoryWrite {
            address: live_in.address,
            after: encrypted_value,
            before: live_in.value,
        });
    effect.before.termination.is_none()
        && effect.after == expected_after
        && effect.input.is_none()
        && effect.output.is_none()
        && effect.memory_delta
            == (ProfileMemoryDelta { data: None, encryption })
        && live_in.address == effect.before.registers.code_pointer
        && profile_cell_decodes_to_no_operation(
            live_in.value,
            effect.before.registers.code_pointer,
        )
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
