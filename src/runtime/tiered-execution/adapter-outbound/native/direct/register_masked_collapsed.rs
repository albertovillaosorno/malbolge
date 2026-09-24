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
//   - Proves the first two-step no-operation/halt collapsed semantic shape.
// - Description:
//   - Rechecks masks, both live-ins, continuity, encryption, successors, and
//     terminal completion before publishing any collapsed-shape authority.
// - Usage:
//   - Consumed before a future byte-canonical native object emitter.
// - Defaults:
//   - Any profile, mask, effect, live-in, continuity, or outcome drift rejects.
//

//! Reviewed semantic admission for collapsed register-masked v6 regions.

use malbolge::{
    EFFECT_IR_REGISTER_MASK_VERSION, MemoryLiveIn, ProfileMemoryDelta,
    ProfileMemoryWrite, ProfileRegisterSet, ProfileRegisters,
    RegisterMaskedRegionEffectProgram, RunOutcome, RuntimeCapability,
    Termination, decode_profile_instruction, encrypt_profile_cell,
    preflight_portable_profile_requirement,
    profile_cell_decodes_to_no_operation, profile_pointer_successor,
};

use super::{RegionEffectIdentity, RegisterMaskedDirectAdmissionError};

/// Proved net effect for one collapsed no-operation followed by halt.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedRegisterMaskedNoOperationHaltAdmission {
    encrypted_address: u32,
    encrypted_value: u32,
    entry_code_pointer: u32,
    entry_data_pointer: u32,
    halt_live_in: MemoryLiveIn,
    identity: RegionEffectIdentity,
    next_code_pointer: u32,
    next_data_pointer: u32,
}

impl VerifiedRegisterMaskedNoOperationHaltAdmission {
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

fn validate_no_operation_halt(
    program: &RegisterMaskedRegionEffectProgram,
    identity: RegionEffectIdentity,
) -> Option<VerifiedRegisterMaskedNoOperationHaltAdmission> {
    if !collapsed_header_supported(program) {
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
    if !first_effect_matches(
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
        encrypted_address: entry_code_pointer,
        encrypted_value,
        entry_code_pointer,
        entry_data_pointer,
        halt_live_in,
        identity,
        next_code_pointer,
        next_data_pointer,
    })
}

fn collapsed_header_supported(
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

fn first_effect_matches(
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
