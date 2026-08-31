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
//   - Exact portable-IR shape and target admission predicates.
// - Must-Not:
//   - Bypass canonical object identity or semantic admission.
// - Allows:
//   - Inputs: reviewed direct-native planning and artifact values.
//   - Outputs: deterministic values owned by this direct-native slice.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - The slice exceeds one independently reviewable responsibility.
// - Merge-When:
//   - Another module owns the exact same direct-native authority.
// - Summary:
//   - Direct-native shape admission.
// - Description:
//   - Isolates one direct-native responsibility from the facade.
// - Usage:
//   - Used only through the parent direct-native module.
// - Defaults:
//   - Unsupported values fail closed.
//

//! Exact IR and target admission for direct-native templates.

use super::*;

type ExecutionGeometryCrazyShapeResult =
    Result<DirectCrazyProgram, DirectExecutionGeometryCrazyError>;
type ExecutionGeometryInitialHaltShapeResult = Result<
    DirectFetchedTerminalProgram,
    DirectExecutionGeometryInitialHaltError,
>;
type ExecutionGeometryInitialJumpDataShapeResult = Result<
    DirectInitialJumpDataProgram,
    DirectExecutionGeometryInitialJumpDataError,
>;
type ExecutionGeometryInputShapeResult =
    Result<DirectInputProgram, DirectExecutionGeometryInputError>;
type ExecutionGeometryJumpCodeShapeResult =
    Result<DirectJumpCodeProgram, DirectExecutionGeometryJumpCodeError>;
type ExecutionGeometryJumpDataShapeResult =
    Result<DirectJumpDataProgram, DirectExecutionGeometryJumpDataError>;
type ExecutionGeometryNoOperationShapeResult =
    Result<DirectNoOperationProgram, DirectExecutionGeometryNoOperationError>;
type ExecutionGeometryOutputShapeResult =
    Result<DirectOutputProgram, DirectExecutionGeometryOutputError>;
type ExecutionGeometryRotateShapeResult =
    Result<DirectRotateProgram, DirectExecutionGeometryRotateError>;

#[derive(Clone, Copy)]
struct DirectInputSemantics {
    eof_word: u32,
    input_instruction: u8,
    memory_words: u32,
}

fn direct_program_header_supported(program: &RegionEffectProgram) -> bool {
    is_canonical_effect_ir_version(program.format_version)
        && u32::try_from(program.profile_requirement.memory_words).is_ok()
}

fn direct_memory_words(program: &RegionEffectProgram) -> Option<u32> {
    direct_program_header_supported(program)
        .then(|| u32::try_from(program.profile_requirement.memory_words).ok())
        .flatten()
}

pub(super) fn fetched_terminal_program(
    program: &RegionEffectProgram,
    reason: Termination,
) -> Option<DirectFetchedTerminalProgram> {
    if !direct_program_header_supported(program)
        || !program.fits_declared_profile_capacity()
        || program.step_budget != 1
        || program.memory_live_ins.len() != 1
        || program.effects.len() != 1
        || program.outcome != (RunOutcome::Terminated { reason, steps: 1 })
    {
        return None;
    }
    let effect = program.effects.first()?;
    let live_in = program.memory_live_ins.first().copied()?;
    let expected_after = ProfileMachineObservation {
        termination: Some(reason),
        ..effect.before
    };
    if effect.before.termination.is_some()
        || effect.after != expected_after
        || effect.input.is_some()
        || effect.output.is_some()
        || effect.memory_delta != ProfileMemoryDelta::default()
        || live_in.address != effect.before.registers.code_pointer
    {
        return None;
    }
    Some(DirectFetchedTerminalProgram {
        live_in,
        observation: effect.before,
    })
}

pub(super) fn validate_execution_geometry_crazy_program(
    program: &ExecutionGeometryRegionEffectProgram,
) -> ExecutionGeometryCrazyShapeResult {
    if program.format_version() != EFFECT_IR_EXECUTION_GEOMETRY_VERSION
        || !program.fits_execution_geometry_capacity()
        || !program.fits_profile_capacity()
        || program.step_budget() != 1
        || program.memory_live_ins().len() != 2
        || program.effects().len() != 1
        || program.outcome() != (RunOutcome::BudgetExhausted { steps: 1 })
    {
        return Err(DirectExecutionGeometryCrazyError::ProgramShape);
    }
    let effect = program
        .effects()
        .first()
        .copied()
        .ok_or(DirectExecutionGeometryCrazyError::ProgramShape)?;
    derive_execution_geometry_crazy_program(program, effect)
        .ok_or(DirectExecutionGeometryCrazyError::ProgramShape)
}

fn derive_execution_geometry_crazy_program(
    program: &ExecutionGeometryRegionEffectProgram,
    effect: EffectOp,
) -> Option<DirectCrazyProgram> {
    let before = effect.before;
    let code_pointer = before.registers.code_pointer;
    let data_pointer = before.registers.data_pointer;
    if code_pointer == data_pointer || before.termination.is_some() {
        return None;
    }
    let code_live_in = program
        .memory_live_ins()
        .iter()
        .copied()
        .find(|live_in| live_in.address == code_pointer)?;
    let data_live_in = program
        .memory_live_ins()
        .iter()
        .copied()
        .find(|live_in| live_in.address == data_pointer)?;
    let commit = execution_geometry_crazy_commit(
        program,
        before,
        code_live_in,
        data_live_in,
    )?;
    let expected_after = ProfileMachineObservation {
        registers: ProfileRegisters {
            accumulator: commit.accumulator,
            code_pointer: commit.next_code_pointer,
            data_pointer: commit.next_data_pointer,
        },
        ..before
    };
    if effect.after != expected_after
        || effect.input.is_some()
        || effect.output.is_some()
        || effect.memory_delta
            != rotate_memory_delta(code_live_in, data_live_in, commit)
    {
        return None;
    }
    Some(DirectCrazyProgram {
        code_live_in,
        commit,
        data_live_in,
        observation: before,
    })
}

fn execution_geometry_crazy_commit(
    program: &ExecutionGeometryRegionEffectProgram,
    before: ProfileMachineObservation,
    code_live_in: MemoryLiveIn,
    data_live_in: MemoryLiveIn,
) -> Option<DirectCrazyCommit> {
    let code_pointer = before.registers.code_pointer;
    let data_pointer = before.registers.data_pointer;
    let geometry = program.execution_geometry();
    let memory_words = geometry.memory_words();
    if decode_profile_instruction(code_live_in.value, code_pointer)
        != Some(b'p')
        || data_live_in.value >= memory_words
        || before.registers.accumulator >= memory_words
    {
        return None;
    }
    let value = profile_crazy(
        data_live_in.value,
        before.registers.accumulator,
        geometry.word_trits(),
    );
    Some(DirectCrazyCommit {
        accumulator: value,
        data_address: data_pointer,
        data_value: value,
        encrypted_address: code_pointer,
        encrypted_value: encrypt_profile_cell(code_live_in.value)?,
        next_code_pointer: profile_pointer_successor(
            code_pointer,
            memory_words,
        )?,
        next_data_pointer: profile_pointer_successor(
            data_pointer,
            memory_words,
        )?,
    })
}

pub(super) fn validate_execution_geometry_crazy_target(
    target: &NativeTargetIdentity,
) -> Result<(), DirectExecutionGeometryCrazyError> {
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(DirectExecutionGeometryCrazyError::TargetFormat);
    }
    if target.backend_id() != DIRECT_EXECUTION_GEOMETRY_CRAZY_BACKEND_ID
        || target.backend_revision()
            != DIRECT_EXECUTION_GEOMETRY_CRAZY_BACKEND_REVISION
        || target.native_abi_revision() != NATIVE_REGION_ABI_REVISION
    {
        return Err(DirectExecutionGeometryCrazyError::TargetBackend);
    }
    if !target.required_features().is_empty() {
        return Err(DirectExecutionGeometryCrazyError::TargetFeatures);
    }
    Ok(())
}

pub(super) fn validate_execution_geometry_initial_halt_program(
    program: &ExecutionGeometryRegionEffectProgram,
) -> ExecutionGeometryInitialHaltShapeResult {
    if program.format_version() != EFFECT_IR_EXECUTION_GEOMETRY_VERSION
        || !program.fits_execution_geometry_capacity()
        || !program.fits_profile_capacity()
        || program.step_budget() != 1
        || program.memory_live_ins().len() != 1
        || program.effects().len() != 1
        || program.outcome()
            != (RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 1,
            })
    {
        return Err(DirectExecutionGeometryInitialHaltError::ProgramShape);
    }
    let effect = program
        .effects()
        .first()
        .ok_or(DirectExecutionGeometryInitialHaltError::ProgramShape)?;
    let live_in = program
        .memory_live_ins()
        .first()
        .copied()
        .ok_or(DirectExecutionGeometryInitialHaltError::ProgramShape)?;
    let expected_after = ProfileMachineObservation {
        termination: Some(Termination::HaltInstruction),
        ..effect.before
    };
    if effect.before.termination.is_some()
        || effect.after != expected_after
        || effect.input.is_some()
        || effect.output.is_some()
        || effect.memory_delta != ProfileMemoryDelta::default()
        || live_in.address != effect.before.registers.code_pointer
        || decode_profile_instruction(
            live_in.value,
            effect.before.registers.code_pointer,
        ) != Some(b'v')
    {
        return Err(DirectExecutionGeometryInitialHaltError::ProgramShape);
    }
    Ok(DirectFetchedTerminalProgram {
        live_in,
        observation: effect.before,
    })
}

pub(super) fn validate_execution_geometry_initial_halt_target(
    target: &NativeTargetIdentity,
) -> Result<(), DirectExecutionGeometryInitialHaltError> {
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(DirectExecutionGeometryInitialHaltError::TargetFormat);
    }
    if target.backend_id() != DIRECT_EXECUTION_GEOMETRY_INITIAL_HALT_BACKEND_ID
        || target.backend_revision()
            != DIRECT_EXECUTION_GEOMETRY_INITIAL_HALT_BACKEND_REVISION
        || target.native_abi_revision() != NATIVE_REGION_ABI_REVISION
    {
        return Err(DirectExecutionGeometryInitialHaltError::TargetBackend);
    }
    if !target.required_features().is_empty() {
        return Err(DirectExecutionGeometryInitialHaltError::TargetFeatures);
    }
    Ok(())
}

pub(super) fn validate_execution_geometry_initial_jump_data_program(
    program: &ExecutionGeometryRegionEffectProgram,
) -> ExecutionGeometryInitialJumpDataShapeResult {
    if program.format_version() != EFFECT_IR_EXECUTION_GEOMETRY_VERSION
        || !program.fits_execution_geometry_capacity()
        || !program.fits_profile_capacity()
        || program.step_budget() != 1
        || program.memory_live_ins().len() != 1
        || program.effects().len() != 1
        || program.outcome() != (RunOutcome::BudgetExhausted { steps: 1 })
    {
        return Err(DirectExecutionGeometryInitialJumpDataError::ProgramShape);
    }
    let effect = program
        .effects()
        .first()
        .copied()
        .ok_or(DirectExecutionGeometryInitialJumpDataError::ProgramShape)?;
    let live_in = program
        .memory_live_ins()
        .first()
        .copied()
        .ok_or(DirectExecutionGeometryInitialJumpDataError::ProgramShape)?;
    derive_execution_geometry_initial_jump_data_program(
        program, effect, live_in,
    )
    .ok_or(DirectExecutionGeometryInitialJumpDataError::ProgramShape)
}

fn derive_execution_geometry_initial_jump_data_program(
    program: &ExecutionGeometryRegionEffectProgram,
    effect: EffectOp,
    live_in: MemoryLiveIn,
) -> Option<DirectInitialJumpDataProgram> {
    let before = effect.before;
    let code_pointer = before.registers.code_pointer;
    let data_pointer = before.registers.data_pointer;
    if code_pointer != data_pointer
        || before.termination.is_some()
        || live_in.address != code_pointer
        || decode_profile_instruction(live_in.value, code_pointer) != Some(b'j')
    {
        return None;
    }
    let memory_words = program.execution_geometry().memory_words();
    let encrypted_value = encrypt_profile_cell(live_in.value)?;
    let next_code_pointer =
        profile_pointer_successor(code_pointer, memory_words)?;
    let next_data_pointer =
        profile_pointer_successor(live_in.value, memory_words)?;
    let expected_after = ProfileMachineObservation {
        registers: ProfileRegisters {
            accumulator: before.registers.accumulator,
            code_pointer: next_code_pointer,
            data_pointer: next_data_pointer,
        },
        ..before
    };
    let expected_encryption =
        (live_in.value != encrypted_value).then_some(ProfileMemoryWrite {
            address: code_pointer,
            after: encrypted_value,
            before: live_in.value,
        });
    if effect.after != expected_after
        || effect.input.is_some()
        || effect.output.is_some()
        || effect.memory_delta
            != (ProfileMemoryDelta {
                data: None,
                encryption: expected_encryption,
            })
    {
        return None;
    }
    Some(DirectInitialJumpDataProgram {
        encrypted_value,
        live_in,
        next_code_pointer,
        next_data_pointer,
        observation: before,
    })
}

pub(super) fn validate_execution_geometry_initial_jump_data_target(
    target: &NativeTargetIdentity,
) -> Result<(), DirectExecutionGeometryInitialJumpDataError> {
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(DirectExecutionGeometryInitialJumpDataError::TargetFormat);
    }
    if target.backend_id()
        != DIRECT_EXECUTION_GEOMETRY_INITIAL_JUMP_DATA_BACKEND_ID
        || target.backend_revision()
            != DIRECT_EXECUTION_GEOMETRY_INITIAL_JUMP_DATA_BACKEND_REVISION
        || target.native_abi_revision() != NATIVE_REGION_ABI_REVISION
    {
        return Err(DirectExecutionGeometryInitialJumpDataError::TargetBackend);
    }
    if !target.required_features().is_empty() {
        return Err(
            DirectExecutionGeometryInitialJumpDataError::TargetFeatures,
        );
    }
    Ok(())
}

pub(super) fn validate_execution_geometry_input_program(
    program: &ExecutionGeometryRegionEffectProgram,
) -> ExecutionGeometryInputShapeResult {
    if program.format_version() != EFFECT_IR_EXECUTION_GEOMETRY_VERSION
        || !program.fits_execution_geometry_capacity()
        || !program.fits_profile_capacity()
        || program.step_budget() != 1
        || program.memory_live_ins().len() != 1
        || program.effects().len() != 1
        || program.outcome() != (RunOutcome::BudgetExhausted { steps: 1 })
    {
        return Err(DirectExecutionGeometryInputError::ProgramShape);
    }
    let effect = program
        .effects()
        .first()
        .copied()
        .ok_or(DirectExecutionGeometryInputError::ProgramShape)?;
    let live_in = program
        .memory_live_ins()
        .first()
        .copied()
        .ok_or(DirectExecutionGeometryInputError::ProgramShape)?;
    let input_instruction = target_profile(program.profile_id())
        .map(|profile| profile.input_instruction())
        .ok_or(DirectExecutionGeometryInputError::ProgramShape)?;
    let geometry = program.execution_geometry();
    derive_input_effect(effect, live_in, DirectInputSemantics {
        eof_word: geometry.eof_word(),
        input_instruction,
        memory_words: geometry.memory_words(),
    })
    .ok_or(DirectExecutionGeometryInputError::ProgramShape)
}

pub(super) fn validate_execution_geometry_input_target(
    target: &NativeTargetIdentity,
) -> Result<(), DirectExecutionGeometryInputError> {
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(DirectExecutionGeometryInputError::TargetFormat);
    }
    if target.backend_id() != DIRECT_EXECUTION_GEOMETRY_INPUT_BACKEND_ID
        || target.backend_revision()
            != DIRECT_EXECUTION_GEOMETRY_INPUT_BACKEND_REVISION
        || target.native_abi_revision() != NATIVE_REGION_ABI_REVISION
    {
        return Err(DirectExecutionGeometryInputError::TargetBackend);
    }
    if !target.required_features().is_empty() {
        return Err(DirectExecutionGeometryInputError::TargetFeatures);
    }
    Ok(())
}

pub(super) fn validate_execution_geometry_jump_code_program(
    program: &ExecutionGeometryRegionEffectProgram,
) -> ExecutionGeometryJumpCodeShapeResult {
    if program.format_version() != EFFECT_IR_EXECUTION_GEOMETRY_VERSION
        || !program.fits_execution_geometry_capacity()
        || !program.fits_profile_capacity()
        || program.step_budget() != 1
        || program.memory_live_ins().len() != 3
        || program.effects().len() != 1
        || program.outcome() != (RunOutcome::BudgetExhausted { steps: 1 })
    {
        return Err(DirectExecutionGeometryJumpCodeError::ProgramShape);
    }
    let effect = program
        .effects()
        .first()
        .copied()
        .ok_or(DirectExecutionGeometryJumpCodeError::ProgramShape)?;
    derive_execution_geometry_jump_code_program(program, effect)
        .ok_or(DirectExecutionGeometryJumpCodeError::ProgramShape)
}

fn derive_execution_geometry_jump_code_program(
    program: &ExecutionGeometryRegionEffectProgram,
    effect: EffectOp,
) -> Option<DirectJumpCodeProgram> {
    let before = effect.before;
    let live_ins = execution_geometry_jump_code_live_ins(program, before)?;
    let code_live_in = live_ins.code;
    let data_live_in = live_ins.data;
    let encryption_live_in = live_ins.encryption;
    let code_pointer = before.registers.code_pointer;
    let data_pointer = before.registers.data_pointer;
    let encryption_pointer = data_live_in.value;
    if decode_profile_instruction(code_live_in.value, code_pointer)
        != Some(b'i')
    {
        return None;
    }
    let memory_words = program.execution_geometry().memory_words();
    if encryption_pointer >= memory_words {
        return None;
    }
    let encrypted_value = encrypt_profile_cell(encryption_live_in.value)?;
    let next_code_pointer =
        profile_pointer_successor(encryption_pointer, memory_words)?;
    let next_data_pointer =
        profile_pointer_successor(data_pointer, memory_words)?;
    let expected_after = ProfileMachineObservation {
        registers: ProfileRegisters {
            accumulator: before.registers.accumulator,
            code_pointer: next_code_pointer,
            data_pointer: next_data_pointer,
        },
        ..before
    };
    let expected_encryption = (encryption_live_in.value != encrypted_value)
        .then_some(ProfileMemoryWrite {
            address: encryption_pointer,
            after: encrypted_value,
            before: encryption_live_in.value,
        });
    if effect.after != expected_after
        || effect.input.is_some()
        || effect.output.is_some()
        || effect.memory_delta
            != (ProfileMemoryDelta {
                data: None,
                encryption: expected_encryption,
            })
    {
        return None;
    }
    Some(DirectJumpCodeProgram {
        code_live_in,
        commit: DirectCodeWriteCommit {
            encrypted_address: encryption_pointer,
            encrypted_value,
            next_code_pointer,
            next_data_pointer,
        },
        data_live_in,
        encryption_live_in,
        observation: before,
    })
}

fn execution_geometry_jump_code_live_ins(
    program: &ExecutionGeometryRegionEffectProgram,
    before: ProfileMachineObservation,
) -> Option<DirectJumpCodeLiveIns> {
    let code_pointer = before.registers.code_pointer;
    let data_pointer = before.registers.data_pointer;
    if code_pointer == data_pointer || before.termination.is_some() {
        return None;
    }
    let code = program
        .memory_live_ins()
        .iter()
        .copied()
        .find(|live_in| live_in.address == code_pointer)?;
    let data = program
        .memory_live_ins()
        .iter()
        .copied()
        .find(|live_in| live_in.address == data_pointer)?;
    let encryption_pointer = data.value;
    if encryption_pointer == code_pointer || encryption_pointer == data_pointer
    {
        return None;
    }
    let encryption = program
        .memory_live_ins()
        .iter()
        .copied()
        .find(|live_in| live_in.address == encryption_pointer)?;
    Some(DirectJumpCodeLiveIns { code, data, encryption })
}

pub(super) fn validate_execution_geometry_jump_code_target(
    target: &NativeTargetIdentity,
) -> Result<(), DirectExecutionGeometryJumpCodeError> {
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(DirectExecutionGeometryJumpCodeError::TargetFormat);
    }
    if target.backend_id() != DIRECT_EXECUTION_GEOMETRY_JUMP_CODE_BACKEND_ID
        || target.backend_revision()
            != DIRECT_EXECUTION_GEOMETRY_JUMP_CODE_BACKEND_REVISION
        || target.native_abi_revision() != NATIVE_REGION_ABI_REVISION
    {
        return Err(DirectExecutionGeometryJumpCodeError::TargetBackend);
    }
    if !target.required_features().is_empty() {
        return Err(DirectExecutionGeometryJumpCodeError::TargetFeatures);
    }
    Ok(())
}

pub(super) fn validate_execution_geometry_jump_data_program(
    program: &ExecutionGeometryRegionEffectProgram,
) -> ExecutionGeometryJumpDataShapeResult {
    if program.format_version() != EFFECT_IR_EXECUTION_GEOMETRY_VERSION
        || !program.fits_execution_geometry_capacity()
        || !program.fits_profile_capacity()
        || program.step_budget() != 1
        || program.memory_live_ins().len() != 2
        || program.effects().len() != 1
        || program.outcome() != (RunOutcome::BudgetExhausted { steps: 1 })
    {
        return Err(DirectExecutionGeometryJumpDataError::ProgramShape);
    }
    let effect = program
        .effects()
        .first()
        .copied()
        .ok_or(DirectExecutionGeometryJumpDataError::ProgramShape)?;
    derive_execution_geometry_jump_data_program(program, effect)
        .ok_or(DirectExecutionGeometryJumpDataError::ProgramShape)
}

fn derive_execution_geometry_jump_data_program(
    program: &ExecutionGeometryRegionEffectProgram,
    effect: EffectOp,
) -> Option<DirectJumpDataProgram> {
    let before = effect.before;
    let code_pointer = before.registers.code_pointer;
    let (code_live_in, data_live_in) =
        execution_geometry_jump_data_live_ins(program, before)?;
    if decode_profile_instruction(code_live_in.value, code_pointer)
        != Some(b'j')
    {
        return None;
    }
    let memory_words = program.execution_geometry().memory_words();
    if data_live_in.value >= memory_words {
        return None;
    }
    let encrypted_value = encrypt_profile_cell(code_live_in.value)?;
    let next_code_pointer =
        profile_pointer_successor(code_pointer, memory_words)?;
    let next_data_pointer =
        profile_pointer_successor(data_live_in.value, memory_words)?;
    let expected_after = ProfileMachineObservation {
        registers: ProfileRegisters {
            accumulator: before.registers.accumulator,
            code_pointer: next_code_pointer,
            data_pointer: next_data_pointer,
        },
        ..before
    };
    let expected_encryption = (code_live_in.value != encrypted_value)
        .then_some(ProfileMemoryWrite {
            address: code_pointer,
            after: encrypted_value,
            before: code_live_in.value,
        });
    if effect.after != expected_after
        || effect.input.is_some()
        || effect.output.is_some()
        || effect.memory_delta
            != (ProfileMemoryDelta {
                data: None,
                encryption: expected_encryption,
            })
    {
        return None;
    }
    Some(DirectJumpDataProgram {
        code_live_in,
        commit: DirectCodeWriteCommit {
            encrypted_address: code_pointer,
            encrypted_value,
            next_code_pointer,
            next_data_pointer,
        },
        data_live_in,
        observation: before,
    })
}

fn execution_geometry_jump_data_live_ins(
    program: &ExecutionGeometryRegionEffectProgram,
    before: ProfileMachineObservation,
) -> Option<(MemoryLiveIn, MemoryLiveIn)> {
    let code_pointer = before.registers.code_pointer;
    let data_pointer = before.registers.data_pointer;
    if code_pointer == data_pointer || before.termination.is_some() {
        return None;
    }
    let code_live_in = program
        .memory_live_ins()
        .iter()
        .copied()
        .find(|live_in| live_in.address == code_pointer)?;
    let data_live_in = program
        .memory_live_ins()
        .iter()
        .copied()
        .find(|live_in| live_in.address == data_pointer)?;
    Some((code_live_in, data_live_in))
}

pub(super) fn validate_execution_geometry_jump_data_target(
    target: &NativeTargetIdentity,
) -> Result<(), DirectExecutionGeometryJumpDataError> {
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(DirectExecutionGeometryJumpDataError::TargetFormat);
    }
    if target.backend_id() != DIRECT_EXECUTION_GEOMETRY_JUMP_DATA_BACKEND_ID
        || target.backend_revision()
            != DIRECT_EXECUTION_GEOMETRY_JUMP_DATA_BACKEND_REVISION
        || target.native_abi_revision() != NATIVE_REGION_ABI_REVISION
    {
        return Err(DirectExecutionGeometryJumpDataError::TargetBackend);
    }
    if !target.required_features().is_empty() {
        return Err(DirectExecutionGeometryJumpDataError::TargetFeatures);
    }
    Ok(())
}

pub(super) fn validate_execution_geometry_no_operation_program(
    program: &ExecutionGeometryRegionEffectProgram,
) -> ExecutionGeometryNoOperationShapeResult {
    if program.format_version() != EFFECT_IR_EXECUTION_GEOMETRY_VERSION
        || !program.fits_execution_geometry_capacity()
        || !program.fits_profile_capacity()
        || program.step_budget() != 1
        || program.memory_live_ins().len() != 1
        || program.effects().len() != 1
        || program.outcome() != (RunOutcome::BudgetExhausted { steps: 1 })
    {
        return Err(DirectExecutionGeometryNoOperationError::ProgramShape);
    }
    let effect = program
        .effects()
        .first()
        .copied()
        .ok_or(DirectExecutionGeometryNoOperationError::ProgramShape)?;
    let live_in = program
        .memory_live_ins()
        .first()
        .copied()
        .ok_or(DirectExecutionGeometryNoOperationError::ProgramShape)?;
    derive_no_operation_effect(
        effect,
        live_in,
        program.execution_geometry().memory_words(),
    )
    .ok_or(DirectExecutionGeometryNoOperationError::ProgramShape)
}

pub(super) fn validate_execution_geometry_no_operation_target(
    target: &NativeTargetIdentity,
) -> Result<(), DirectExecutionGeometryNoOperationError> {
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(DirectExecutionGeometryNoOperationError::TargetFormat);
    }
    if target.backend_id() != DIRECT_EXECUTION_GEOMETRY_NO_OPERATION_BACKEND_ID
        || target.backend_revision()
            != DIRECT_EXECUTION_GEOMETRY_NO_OPERATION_BACKEND_REVISION
        || target.native_abi_revision() != NATIVE_REGION_ABI_REVISION
    {
        return Err(DirectExecutionGeometryNoOperationError::TargetBackend);
    }
    if !target.required_features().is_empty() {
        return Err(DirectExecutionGeometryNoOperationError::TargetFeatures);
    }
    Ok(())
}

pub(super) fn validate_execution_geometry_output_program(
    program: &ExecutionGeometryRegionEffectProgram,
) -> ExecutionGeometryOutputShapeResult {
    if program.format_version() != EFFECT_IR_EXECUTION_GEOMETRY_VERSION
        || !program.fits_execution_geometry_capacity()
        || !program.fits_profile_capacity()
        || program.step_budget() != 1
        || program.memory_live_ins().len() != 1
        || program.effects().len() != 1
        || program.outcome() != (RunOutcome::BudgetExhausted { steps: 1 })
    {
        return Err(DirectExecutionGeometryOutputError::ProgramShape);
    }
    let effect = program
        .effects()
        .first()
        .copied()
        .ok_or(DirectExecutionGeometryOutputError::ProgramShape)?;
    let live_in = program
        .memory_live_ins()
        .first()
        .copied()
        .ok_or(DirectExecutionGeometryOutputError::ProgramShape)?;
    let output_instruction = target_profile(program.profile_id())
        .map(|profile| profile.output_instruction())
        .ok_or(DirectExecutionGeometryOutputError::ProgramShape)?;
    derive_output_effect(
        effect,
        live_in,
        program.execution_geometry().memory_words(),
        output_instruction,
    )
    .ok_or(DirectExecutionGeometryOutputError::ProgramShape)
}

pub(super) fn validate_execution_geometry_output_target(
    target: &NativeTargetIdentity,
) -> Result<(), DirectExecutionGeometryOutputError> {
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(DirectExecutionGeometryOutputError::TargetFormat);
    }
    if target.backend_id() != DIRECT_EXECUTION_GEOMETRY_OUTPUT_BACKEND_ID
        || target.backend_revision()
            != DIRECT_EXECUTION_GEOMETRY_OUTPUT_BACKEND_REVISION
        || target.native_abi_revision() != NATIVE_REGION_ABI_REVISION
    {
        return Err(DirectExecutionGeometryOutputError::TargetBackend);
    }
    if !target.required_features().is_empty() {
        return Err(DirectExecutionGeometryOutputError::TargetFeatures);
    }
    Ok(())
}

pub(super) fn validate_execution_geometry_rotate_program(
    program: &ExecutionGeometryRegionEffectProgram,
) -> ExecutionGeometryRotateShapeResult {
    if program.format_version() != EFFECT_IR_EXECUTION_GEOMETRY_VERSION
        || !program.fits_execution_geometry_capacity()
        || !program.fits_profile_capacity()
        || program.step_budget() != 1
        || program.memory_live_ins().len() != 2
        || program.effects().len() != 1
        || program.outcome() != (RunOutcome::BudgetExhausted { steps: 1 })
    {
        return Err(DirectExecutionGeometryRotateError::ProgramShape);
    }
    let effect = program
        .effects()
        .first()
        .copied()
        .ok_or(DirectExecutionGeometryRotateError::ProgramShape)?;
    derive_execution_geometry_rotate_program(program, effect)
        .ok_or(DirectExecutionGeometryRotateError::ProgramShape)
}

fn derive_execution_geometry_rotate_program(
    program: &ExecutionGeometryRegionEffectProgram,
    effect: EffectOp,
) -> Option<DirectRotateProgram> {
    let before = effect.before;
    let code_pointer = before.registers.code_pointer;
    let data_pointer = before.registers.data_pointer;
    if code_pointer == data_pointer || before.termination.is_some() {
        return None;
    }
    let code_live_in = program
        .memory_live_ins()
        .iter()
        .copied()
        .find(|live_in| live_in.address == code_pointer)?;
    let data_live_in = program
        .memory_live_ins()
        .iter()
        .copied()
        .find(|live_in| live_in.address == data_pointer)?;
    let commit = execution_geometry_rotate_commit(
        program,
        before,
        code_live_in,
        data_live_in,
    )?;
    let expected_after = ProfileMachineObservation {
        registers: ProfileRegisters {
            accumulator: commit.accumulator,
            code_pointer: commit.next_code_pointer,
            data_pointer: commit.next_data_pointer,
        },
        ..before
    };
    if effect.after != expected_after
        || effect.input.is_some()
        || effect.output.is_some()
        || effect.memory_delta
            != rotate_memory_delta(code_live_in, data_live_in, commit)
    {
        return None;
    }
    Some(DirectRotateProgram {
        code_live_in,
        commit,
        data_live_in,
        observation: before,
    })
}

fn execution_geometry_rotate_commit(
    program: &ExecutionGeometryRegionEffectProgram,
    before: ProfileMachineObservation,
    code_live_in: MemoryLiveIn,
    data_live_in: MemoryLiveIn,
) -> Option<DirectRotateCommit> {
    let code_pointer = before.registers.code_pointer;
    let data_pointer = before.registers.data_pointer;
    if decode_profile_instruction(code_live_in.value, code_pointer)
        != Some(b'*')
    {
        return None;
    }
    let memory_words = program.execution_geometry().memory_words();
    if data_live_in.value >= memory_words {
        return None;
    }
    let rotated_value = profile_rotate(data_live_in.value, memory_words);
    Some(DirectRotateCommit {
        accumulator: rotated_value,
        data_address: data_pointer,
        data_value: rotated_value,
        encrypted_address: code_pointer,
        encrypted_value: encrypt_profile_cell(code_live_in.value)?,
        next_code_pointer: profile_pointer_successor(
            code_pointer,
            memory_words,
        )?,
        next_data_pointer: profile_pointer_successor(
            data_pointer,
            memory_words,
        )?,
    })
}

pub(super) fn validate_execution_geometry_rotate_target(
    target: &NativeTargetIdentity,
) -> Result<(), DirectExecutionGeometryRotateError> {
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(DirectExecutionGeometryRotateError::TargetFormat);
    }
    if target.backend_id() != DIRECT_EXECUTION_GEOMETRY_ROTATE_BACKEND_ID
        || target.backend_revision()
            != DIRECT_EXECUTION_GEOMETRY_ROTATE_BACKEND_REVISION
        || target.native_abi_revision() != NATIVE_REGION_ABI_REVISION
    {
        return Err(DirectExecutionGeometryRotateError::TargetBackend);
    }
    if !target.required_features().is_empty() {
        return Err(DirectExecutionGeometryRotateError::TargetFeatures);
    }
    Ok(())
}

pub(super) fn validate_halt_fetch_program(
    program: &RegionEffectProgram,
) -> Result<DirectFetchedTerminalProgram, DirectHaltFetchError> {
    let selected =
        fetched_terminal_program(program, Termination::HaltInstruction)
            .ok_or(DirectHaltFetchError::ProgramShape)?;
    if decode_profile_instruction(
        selected.live_in.value,
        selected.observation.registers.code_pointer,
    ) == Some(b'v')
    {
        Ok(selected)
    } else {
        Err(DirectHaltFetchError::ProgramShape)
    }
}

pub(super) fn validate_halt_fetch_target(
    target: &NativeTargetIdentity,
) -> Result<(), DirectHaltFetchError> {
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(DirectHaltFetchError::TargetFormat);
    }
    if target.backend_id() != DIRECT_HALT_FETCH_BACKEND_ID
        || target.backend_revision() != DIRECT_HALT_FETCH_BACKEND_REVISION
        || target.native_abi_revision() != NATIVE_REGION_ABI_REVISION
    {
        return Err(DirectHaltFetchError::TargetBackend);
    }
    if !target.required_features().is_empty() {
        return Err(DirectHaltFetchError::TargetFeatures);
    }
    Ok(())
}

pub(super) fn validate_non_graphical_program(
    program: &RegionEffectProgram,
) -> Result<DirectFetchedTerminalProgram, DirectNonGraphicalError> {
    let selected =
        fetched_terminal_program(program, Termination::NonGraphicalCell)
            .ok_or(DirectNonGraphicalError::ProgramShape)?;
    if profile_cell_is_graphical(selected.live_in.value) {
        Err(DirectNonGraphicalError::ProgramShape)
    } else {
        Ok(selected)
    }
}

pub(super) fn validate_non_graphical_target(
    target: &NativeTargetIdentity,
) -> Result<(), DirectNonGraphicalError> {
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(DirectNonGraphicalError::TargetFormat);
    }
    if target.backend_id() != DIRECT_NON_GRAPHICAL_BACKEND_ID
        || target.backend_revision() != DIRECT_NON_GRAPHICAL_BACKEND_REVISION
        || target.native_abi_revision() != NATIVE_REGION_ABI_REVISION
    {
        return Err(DirectNonGraphicalError::TargetBackend);
    }
    if !target.required_features().is_empty() {
        return Err(DirectNonGraphicalError::TargetFeatures);
    }
    Ok(())
}

pub(super) fn validate_jump_code_program(
    program: &RegionEffectProgram,
) -> Result<DirectJumpCodeProgram, DirectJumpCodeError> {
    if !direct_program_header_supported(program)
        || !program.fits_declared_profile_capacity()
        || program.step_budget != 1
        || program.memory_live_ins.len() != 3
        || program.effects.len() != 1
        || program.outcome != (RunOutcome::BudgetExhausted { steps: 1 })
    {
        return Err(DirectJumpCodeError::ProgramShape);
    }
    let effect = program
        .effects
        .first()
        .copied()
        .ok_or(DirectJumpCodeError::ProgramShape)?;
    derive_jump_code_program(program, effect)
        .ok_or(DirectJumpCodeError::ProgramShape)
}

pub(super) fn jump_code_live_ins(
    program: &RegionEffectProgram,
    before: ProfileMachineObservation,
) -> Option<DirectJumpCodeLiveIns> {
    let code_pointer = before.registers.code_pointer;
    let data_pointer = before.registers.data_pointer;
    if code_pointer == data_pointer || before.termination.is_some() {
        return None;
    }
    let code_live_in = program
        .memory_live_ins
        .iter()
        .copied()
        .find(|live_in| live_in.address == code_pointer)?;
    let data_live_in = program
        .memory_live_ins
        .iter()
        .copied()
        .find(|live_in| live_in.address == data_pointer)?;
    let encryption_pointer = data_live_in.value;
    if encryption_pointer == code_pointer || encryption_pointer == data_pointer
    {
        return None;
    }
    let encryption_live_in = program
        .memory_live_ins
        .iter()
        .copied()
        .find(|live_in| live_in.address == encryption_pointer)?;
    Some(DirectJumpCodeLiveIns {
        code: code_live_in,
        data: data_live_in,
        encryption: encryption_live_in,
    })
}

pub(super) fn derive_jump_code_program(
    program: &RegionEffectProgram,
    effect: EffectOp,
) -> Option<DirectJumpCodeProgram> {
    let before = effect.before;
    let code_pointer = before.registers.code_pointer;
    let data_pointer = before.registers.data_pointer;
    let live_ins = jump_code_live_ins(program, before)?;
    let code_live_in = live_ins.code;
    let data_live_in = live_ins.data;
    let encryption_live_in = live_ins.encryption;
    if decode_profile_instruction(code_live_in.value, code_pointer)
        != Some(b'i')
    {
        return None;
    }
    let memory_words = direct_memory_words(program)?;
    let encryption_pointer = data_live_in.value;
    let encrypted_value = encrypt_profile_cell(encryption_live_in.value)?;
    let next_code_pointer =
        profile_pointer_successor(encryption_pointer, memory_words)?;
    let next_data_pointer =
        profile_pointer_successor(data_pointer, memory_words)?;
    let expected_after = ProfileMachineObservation {
        registers: ProfileRegisters {
            accumulator: before.registers.accumulator,
            code_pointer: next_code_pointer,
            data_pointer: next_data_pointer,
        },
        ..before
    };
    let expected_encryption = (encryption_live_in.value != encrypted_value)
        .then_some(ProfileMemoryWrite {
            address: encryption_pointer,
            after: encrypted_value,
            before: encryption_live_in.value,
        });
    if effect.after != expected_after
        || effect.input.is_some()
        || effect.output.is_some()
        || effect.memory_delta
            != (ProfileMemoryDelta {
                data: None,
                encryption: expected_encryption,
            })
    {
        return None;
    }
    Some(DirectJumpCodeProgram {
        code_live_in,
        commit: DirectCodeWriteCommit {
            encrypted_address: encryption_pointer,
            encrypted_value,
            next_code_pointer,
            next_data_pointer,
        },
        data_live_in,
        encryption_live_in,
        observation: before,
    })
}

pub(super) fn validate_jump_code_target(
    target: &NativeTargetIdentity,
) -> Result<(), DirectJumpCodeError> {
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(DirectJumpCodeError::TargetFormat);
    }
    if target.backend_id() != DIRECT_JUMP_CODE_BACKEND_ID
        || target.backend_revision() != DIRECT_JUMP_CODE_BACKEND_REVISION
        || target.native_abi_revision() != NATIVE_REGION_ABI_REVISION
    {
        return Err(DirectJumpCodeError::TargetBackend);
    }
    if !target.required_features().is_empty() {
        return Err(DirectJumpCodeError::TargetFeatures);
    }
    Ok(())
}

pub(super) fn validate_jump_data_program(
    program: &RegionEffectProgram,
) -> Result<DirectJumpDataProgram, DirectJumpDataError> {
    if !direct_program_header_supported(program)
        || !program.fits_declared_profile_capacity()
        || program.step_budget != 1
        || program.memory_live_ins.len() != 2
        || program.effects.len() != 1
        || program.outcome != (RunOutcome::BudgetExhausted { steps: 1 })
    {
        return Err(DirectJumpDataError::ProgramShape);
    }
    let effect = program
        .effects
        .first()
        .copied()
        .ok_or(DirectJumpDataError::ProgramShape)?;
    derive_jump_data_program(program, effect)
        .ok_or(DirectJumpDataError::ProgramShape)
}

pub(super) fn jump_data_live_ins(
    program: &RegionEffectProgram,
    before: ProfileMachineObservation,
) -> Option<(MemoryLiveIn, MemoryLiveIn)> {
    let code_pointer = before.registers.code_pointer;
    let data_pointer = before.registers.data_pointer;
    if code_pointer == data_pointer || before.termination.is_some() {
        return None;
    }
    let code_live_in = program
        .memory_live_ins
        .iter()
        .copied()
        .find(|live_in| live_in.address == code_pointer)?;
    let data_live_in = program
        .memory_live_ins
        .iter()
        .copied()
        .find(|live_in| live_in.address == data_pointer)?;
    Some((code_live_in, data_live_in))
}

pub(super) fn derive_jump_data_program(
    program: &RegionEffectProgram,
    effect: EffectOp,
) -> Option<DirectJumpDataProgram> {
    let before = effect.before;
    let code_pointer = before.registers.code_pointer;
    let (code_live_in, data_live_in) = jump_data_live_ins(program, before)?;
    if decode_profile_instruction(code_live_in.value, code_pointer)
        != Some(b'j')
    {
        return None;
    }
    let memory_words = direct_memory_words(program)?;
    let encrypted_value = encrypt_profile_cell(code_live_in.value)?;
    let next_code_pointer =
        profile_pointer_successor(code_pointer, memory_words)?;
    let next_data_pointer =
        profile_pointer_successor(data_live_in.value, memory_words)?;
    let expected_after = ProfileMachineObservation {
        registers: ProfileRegisters {
            accumulator: before.registers.accumulator,
            code_pointer: next_code_pointer,
            data_pointer: next_data_pointer,
        },
        ..before
    };
    let expected_encryption = (code_live_in.value != encrypted_value)
        .then_some(ProfileMemoryWrite {
            address: code_pointer,
            after: encrypted_value,
            before: code_live_in.value,
        });
    if effect.after != expected_after
        || effect.input.is_some()
        || effect.output.is_some()
        || effect.memory_delta
            != (ProfileMemoryDelta {
                data: None,
                encryption: expected_encryption,
            })
    {
        return None;
    }
    Some(DirectJumpDataProgram {
        code_live_in,
        commit: DirectCodeWriteCommit {
            encrypted_address: code_pointer,
            encrypted_value,
            next_code_pointer,
            next_data_pointer,
        },
        data_live_in,
        observation: before,
    })
}

pub(super) fn validate_jump_data_target(
    target: &NativeTargetIdentity,
) -> Result<(), DirectJumpDataError> {
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(DirectJumpDataError::TargetFormat);
    }
    if target.backend_id() != DIRECT_JUMP_DATA_BACKEND_ID
        || target.backend_revision() != DIRECT_JUMP_DATA_BACKEND_REVISION
        || target.native_abi_revision() != NATIVE_REGION_ABI_REVISION
    {
        return Err(DirectJumpDataError::TargetBackend);
    }
    if !target.required_features().is_empty() {
        return Err(DirectJumpDataError::TargetFeatures);
    }
    Ok(())
}

pub(super) fn validate_crazy_program(
    program: &RegionEffectProgram,
) -> Result<DirectCrazyProgram, DirectCrazyError> {
    if !direct_program_header_supported(program)
        || !program.fits_declared_profile_capacity()
        || program.step_budget != 1
        || program.memory_live_ins.len() != 2
        || program.effects.len() != 1
        || program.outcome != (RunOutcome::BudgetExhausted { steps: 1 })
    {
        return Err(DirectCrazyError::ProgramShape);
    }
    let effect = program
        .effects
        .first()
        .copied()
        .ok_or(DirectCrazyError::ProgramShape)?;
    derive_crazy_program(program, effect).ok_or(DirectCrazyError::ProgramShape)
}

pub(super) fn derive_crazy_program(
    program: &RegionEffectProgram,
    effect: EffectOp,
) -> Option<DirectCrazyProgram> {
    let before = effect.before;
    let (code_live_in, data_live_in) = rotate_live_ins(program, before)?;
    let commit = crazy_commit(program, before, code_live_in, data_live_in)?;
    let expected_after = ProfileMachineObservation {
        registers: ProfileRegisters {
            accumulator: commit.accumulator,
            code_pointer: commit.next_code_pointer,
            data_pointer: commit.next_data_pointer,
        },
        ..before
    };
    if effect.after != expected_after
        || effect.input.is_some()
        || effect.output.is_some()
        || effect.memory_delta
            != rotate_memory_delta(code_live_in, data_live_in, commit)
    {
        return None;
    }
    Some(DirectCrazyProgram {
        code_live_in,
        commit,
        data_live_in,
        observation: before,
    })
}

pub(super) fn crazy_commit(
    program: &RegionEffectProgram,
    before: ProfileMachineObservation,
    code_live_in: MemoryLiveIn,
    data_live_in: MemoryLiveIn,
) -> Option<DirectCrazyCommit> {
    let code_pointer = before.registers.code_pointer;
    let data_pointer = before.registers.data_pointer;
    if decode_profile_instruction(code_live_in.value, code_pointer)
        != Some(b'p')
    {
        return None;
    }
    let memory_words = direct_memory_words(program)?;
    if data_live_in.value >= memory_words
        || before.registers.accumulator >= memory_words
    {
        return None;
    }
    let value = profile_crazy(
        data_live_in.value,
        before.registers.accumulator,
        program.profile_requirement.word_trits,
    );
    Some(DirectCrazyCommit {
        accumulator: value,
        data_address: data_pointer,
        data_value: value,
        encrypted_address: code_pointer,
        encrypted_value: encrypt_profile_cell(code_live_in.value)?,
        next_code_pointer: profile_pointer_successor(
            code_pointer,
            memory_words,
        )?,
        next_data_pointer: profile_pointer_successor(
            data_pointer,
            memory_words,
        )?,
    })
}

pub(super) fn validate_crazy_target(
    target: &NativeTargetIdentity,
) -> Result<(), DirectCrazyError> {
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(DirectCrazyError::TargetFormat);
    }
    if target.backend_id() != DIRECT_CRAZY_BACKEND_ID
        || target.backend_revision() != DIRECT_CRAZY_BACKEND_REVISION
        || target.native_abi_revision() != NATIVE_REGION_ABI_REVISION
    {
        return Err(DirectCrazyError::TargetBackend);
    }
    if !target.required_features().is_empty() {
        return Err(DirectCrazyError::TargetFeatures);
    }
    Ok(())
}

pub(super) fn validate_input_program(
    program: &RegionEffectProgram,
) -> Result<DirectInputProgram, DirectInputError> {
    if !direct_program_header_supported(program)
        || !program.fits_declared_profile_capacity()
        || program.step_budget != 1
        || program.memory_live_ins.len() != 1
        || program.effects.len() != 1
        || program.outcome != (RunOutcome::BudgetExhausted { steps: 1 })
    {
        return Err(DirectInputError::ProgramShape);
    }
    let effect = program
        .effects
        .first()
        .copied()
        .ok_or(DirectInputError::ProgramShape)?;
    let live_in = program
        .memory_live_ins
        .first()
        .copied()
        .ok_or(DirectInputError::ProgramShape)?;
    derive_input_program(program, effect, live_in)
        .ok_or(DirectInputError::ProgramShape)
}

pub(super) fn derive_input_program(
    program: &RegionEffectProgram,
    effect: EffectOp,
    live_in: MemoryLiveIn,
) -> Option<DirectInputProgram> {
    let input_instruction =
        target_profile(&program.profile_id)?.input_instruction();
    derive_input_effect(effect, live_in, DirectInputSemantics {
        eof_word: profile_eof_word(program.profile_requirement.word_trits)?,
        input_instruction,
        memory_words: direct_memory_words(program)?,
    })
}

fn derive_input_effect(
    effect: EffectOp,
    live_in: MemoryLiveIn,
    semantics: DirectInputSemantics,
) -> Option<DirectInputProgram> {
    let DirectInputSemantics {
        eof_word,
        input_instruction,
        memory_words,
    } = semantics;
    let before = effect.before;
    let code_pointer = before.registers.code_pointer;
    let input = effect.input?;
    if before.termination.is_some()
        || live_in.address != code_pointer
        || decode_profile_instruction(live_in.value, code_pointer)
            != Some(input_instruction)
    {
        return None;
    }
    let (accumulator, next_input_consumed) =
        input_result(input, before.input_consumed, eof_word)?;
    let encrypted_value = encrypt_profile_cell(live_in.value)?;
    let next_code_pointer =
        profile_pointer_successor(code_pointer, memory_words)?;
    let next_data_pointer =
        profile_pointer_successor(before.registers.data_pointer, memory_words)?;
    let expected_after = ProfileMachineObservation {
        input_consumed: next_input_consumed,
        registers: ProfileRegisters {
            accumulator,
            code_pointer: next_code_pointer,
            data_pointer: next_data_pointer,
        },
        ..before
    };
    let expected_encryption =
        (live_in.value != encrypted_value).then_some(ProfileMemoryWrite {
            address: code_pointer,
            after: encrypted_value,
            before: live_in.value,
        });
    if effect.after != expected_after
        || effect.output.is_some()
        || effect.memory_delta
            != (ProfileMemoryDelta {
                data: None,
                encryption: expected_encryption,
            })
    {
        return None;
    }
    Some(DirectInputProgram {
        commit: DirectInputCommit {
            accumulator,
            encrypted_address: code_pointer,
            encrypted_value,
            next_code_pointer,
            next_data_pointer,
            next_input_consumed: u64::try_from(next_input_consumed).ok()?,
        },
        input,
        live_in,
        observation: before,
    })
}

fn input_result(
    input: TraceInput,
    input_consumed: usize,
    eof_word: u32,
) -> Option<(u32, usize)> {
    match input {
        TraceInput::Byte(byte) => {
            Some((u32::from(byte), input_consumed.checked_add(1)?))
        },
        TraceInput::EndOfInput => Some((eof_word, input_consumed)),
    }
}

pub(super) fn validate_input_target(
    target: &NativeTargetIdentity,
) -> Result<(), DirectInputError> {
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(DirectInputError::TargetFormat);
    }
    if target.backend_id() != DIRECT_INPUT_BACKEND_ID
        || target.backend_revision() != DIRECT_INPUT_BACKEND_REVISION
        || target.native_abi_revision() != NATIVE_REGION_ABI_REVISION
    {
        return Err(DirectInputError::TargetBackend);
    }
    if !target.required_features().is_empty() {
        return Err(DirectInputError::TargetFeatures);
    }
    Ok(())
}

pub(super) fn validate_output_program(
    program: &RegionEffectProgram,
) -> Result<DirectOutputProgram, DirectOutputError> {
    if !direct_program_header_supported(program)
        || !program.fits_declared_profile_capacity()
        || program.step_budget != 1
        || program.memory_live_ins.len() != 1
        || program.effects.len() != 1
        || program.outcome != (RunOutcome::BudgetExhausted { steps: 1 })
    {
        return Err(DirectOutputError::ProgramShape);
    }
    let effect = program
        .effects
        .first()
        .copied()
        .ok_or(DirectOutputError::ProgramShape)?;
    let live_in = program
        .memory_live_ins
        .first()
        .copied()
        .ok_or(DirectOutputError::ProgramShape)?;
    derive_output_program(program, effect, live_in)
        .ok_or(DirectOutputError::ProgramShape)
}

pub(super) fn derive_output_program(
    program: &RegionEffectProgram,
    effect: EffectOp,
    live_in: MemoryLiveIn,
) -> Option<DirectOutputProgram> {
    let output_instruction =
        target_profile(&program.profile_id)?.output_instruction();
    derive_output_effect(
        effect,
        live_in,
        direct_memory_words(program)?,
        output_instruction,
    )
}

fn derive_output_effect(
    effect: EffectOp,
    live_in: MemoryLiveIn,
    memory_words: u32,
    output_instruction: u8,
) -> Option<DirectOutputProgram> {
    let before = effect.before;
    let code_pointer = before.registers.code_pointer;
    if before.termination.is_some()
        || live_in.address != code_pointer
        || decode_profile_instruction(live_in.value, code_pointer)
            != Some(output_instruction)
    {
        return None;
    }
    let next_output_len = before.output_len.checked_add(1)?;
    let encrypted_value = encrypt_profile_cell(live_in.value)?;
    let next_code_pointer =
        profile_pointer_successor(code_pointer, memory_words)?;
    let next_data_pointer =
        profile_pointer_successor(before.registers.data_pointer, memory_words)?;
    let output_byte = profile_low_byte(before.registers.accumulator);
    let expected_after = ProfileMachineObservation {
        output_len: next_output_len,
        registers: ProfileRegisters {
            accumulator: before.registers.accumulator,
            code_pointer: next_code_pointer,
            data_pointer: next_data_pointer,
        },
        ..before
    };
    let expected_encryption =
        (live_in.value != encrypted_value).then_some(ProfileMemoryWrite {
            address: code_pointer,
            after: encrypted_value,
            before: live_in.value,
        });
    if effect.after != expected_after
        || effect.input.is_some()
        || effect.output != Some(output_byte)
        || effect.memory_delta
            != (ProfileMemoryDelta {
                data: None,
                encryption: expected_encryption,
            })
    {
        return None;
    }
    Some(DirectOutputProgram {
        commit: DirectOutputCommit {
            encrypted_address: code_pointer,
            encrypted_value,
            next_code_pointer,
            next_data_pointer,
            next_output_len: u64::try_from(next_output_len).ok()?,
            output_byte,
            output_index: u64::try_from(before.output_len).ok()?,
        },
        live_in,
        observation: before,
    })
}

pub(super) fn validate_output_target(
    target: &NativeTargetIdentity,
) -> Result<(), DirectOutputError> {
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(DirectOutputError::TargetFormat);
    }
    if target.backend_id() != DIRECT_OUTPUT_BACKEND_ID
        || target.backend_revision() != DIRECT_OUTPUT_BACKEND_REVISION
        || target.native_abi_revision() != NATIVE_REGION_ABI_REVISION
    {
        return Err(DirectOutputError::TargetBackend);
    }
    if !target.required_features().is_empty() {
        return Err(DirectOutputError::TargetFeatures);
    }
    Ok(())
}

pub(super) fn validate_rotate_program(
    program: &RegionEffectProgram,
) -> Result<DirectRotateProgram, DirectRotateError> {
    if !direct_program_header_supported(program)
        || !program.fits_declared_profile_capacity()
        || program.step_budget != 1
        || program.memory_live_ins.len() != 2
        || program.effects.len() != 1
        || program.outcome != (RunOutcome::BudgetExhausted { steps: 1 })
    {
        return Err(DirectRotateError::ProgramShape);
    }
    let effect = program
        .effects
        .first()
        .copied()
        .ok_or(DirectRotateError::ProgramShape)?;
    derive_rotate_program(program, effect)
        .ok_or(DirectRotateError::ProgramShape)
}

pub(super) fn derive_rotate_program(
    program: &RegionEffectProgram,
    effect: EffectOp,
) -> Option<DirectRotateProgram> {
    let before = effect.before;
    let (code_live_in, data_live_in) = rotate_live_ins(program, before)?;
    let commit = rotate_commit(program, before, code_live_in, data_live_in)?;
    let expected_after = ProfileMachineObservation {
        registers: ProfileRegisters {
            accumulator: commit.accumulator,
            code_pointer: commit.next_code_pointer,
            data_pointer: commit.next_data_pointer,
        },
        ..before
    };
    if effect.after != expected_after
        || effect.input.is_some()
        || effect.output.is_some()
        || effect.memory_delta
            != rotate_memory_delta(code_live_in, data_live_in, commit)
    {
        return None;
    }
    Some(DirectRotateProgram {
        code_live_in,
        commit,
        data_live_in,
        observation: before,
    })
}

pub(super) fn rotate_live_ins(
    program: &RegionEffectProgram,
    before: ProfileMachineObservation,
) -> Option<(MemoryLiveIn, MemoryLiveIn)> {
    let code_pointer = before.registers.code_pointer;
    let data_pointer = before.registers.data_pointer;
    if code_pointer == data_pointer || before.termination.is_some() {
        return None;
    }
    let code_live_in = program
        .memory_live_ins
        .iter()
        .copied()
        .find(|live_in| live_in.address == code_pointer)?;
    let data_live_in = program
        .memory_live_ins
        .iter()
        .copied()
        .find(|live_in| live_in.address == data_pointer)?;
    Some((code_live_in, data_live_in))
}

pub(super) fn rotate_commit(
    program: &RegionEffectProgram,
    before: ProfileMachineObservation,
    code_live_in: MemoryLiveIn,
    data_live_in: MemoryLiveIn,
) -> Option<DirectRotateCommit> {
    let code_pointer = before.registers.code_pointer;
    let data_pointer = before.registers.data_pointer;
    if decode_profile_instruction(code_live_in.value, code_pointer)
        != Some(b'*')
    {
        return None;
    }
    let memory_words = direct_memory_words(program)?;
    if data_live_in.value >= memory_words {
        return None;
    }
    let rotated_value = profile_rotate(data_live_in.value, memory_words);
    Some(DirectRotateCommit {
        accumulator: rotated_value,
        data_address: data_pointer,
        data_value: rotated_value,
        encrypted_address: code_pointer,
        encrypted_value: encrypt_profile_cell(code_live_in.value)?,
        next_code_pointer: profile_pointer_successor(
            code_pointer,
            memory_words,
        )?,
        next_data_pointer: profile_pointer_successor(
            data_pointer,
            memory_words,
        )?,
    })
}

pub(super) fn rotate_memory_delta(
    code_live_in: MemoryLiveIn,
    data_live_in: MemoryLiveIn,
    commit: DirectRotateCommit,
) -> ProfileMemoryDelta {
    let data = (data_live_in.value != commit.data_value).then_some(
        ProfileMemoryWrite {
            address: commit.data_address,
            after: commit.data_value,
            before: data_live_in.value,
        },
    );
    let encryption = (code_live_in.value != commit.encrypted_value).then_some(
        ProfileMemoryWrite {
            address: commit.encrypted_address,
            after: commit.encrypted_value,
            before: code_live_in.value,
        },
    );
    ProfileMemoryDelta { data, encryption }
}

pub(super) fn validate_rotate_target(
    target: &NativeTargetIdentity,
) -> Result<(), DirectRotateError> {
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(DirectRotateError::TargetFormat);
    }
    if target.backend_id() != DIRECT_ROTATE_BACKEND_ID
        || target.backend_revision() != DIRECT_ROTATE_BACKEND_REVISION
        || target.native_abi_revision() != NATIVE_REGION_ABI_REVISION
    {
        return Err(DirectRotateError::TargetBackend);
    }
    if !target.required_features().is_empty() {
        return Err(DirectRotateError::TargetFeatures);
    }
    Ok(())
}

pub(super) fn validate_no_operation_program(
    program: &RegionEffectProgram,
) -> Result<DirectNoOperationProgram, DirectNoOperationError> {
    if !direct_program_header_supported(program)
        || !program.fits_declared_profile_capacity()
        || program.step_budget != 1
        || program.memory_live_ins.len() != 1
        || program.effects.len() != 1
        || program.outcome != (RunOutcome::BudgetExhausted { steps: 1 })
    {
        return Err(DirectNoOperationError::ProgramShape);
    }
    let effect = program
        .effects
        .first()
        .ok_or(DirectNoOperationError::ProgramShape)?;
    let live_in = program
        .memory_live_ins
        .first()
        .copied()
        .ok_or(DirectNoOperationError::ProgramShape)?;
    derive_no_operation_program(program, *effect, live_in)
        .ok_or(DirectNoOperationError::ProgramShape)
}

pub(super) fn derive_no_operation_program(
    program: &RegionEffectProgram,
    effect: EffectOp,
    live_in: MemoryLiveIn,
) -> Option<DirectNoOperationProgram> {
    derive_no_operation_effect(effect, live_in, direct_memory_words(program)?)
}

fn derive_no_operation_effect(
    effect: EffectOp,
    live_in: MemoryLiveIn,
    memory_words: u32,
) -> Option<DirectNoOperationProgram> {
    let before = effect.before;
    let next_code_pointer =
        profile_pointer_successor(before.registers.code_pointer, memory_words)?;
    let next_data_pointer =
        profile_pointer_successor(before.registers.data_pointer, memory_words)?;
    let encrypted_value = encrypt_profile_cell(live_in.value)?;
    let expected_after = ProfileMachineObservation {
        registers: ProfileRegisters {
            accumulator: before.registers.accumulator,
            code_pointer: next_code_pointer,
            data_pointer: next_data_pointer,
        },
        ..before
    };
    let expected_encryption =
        (live_in.value != encrypted_value).then_some(ProfileMemoryWrite {
            address: before.registers.code_pointer,
            after: encrypted_value,
            before: live_in.value,
        });
    let expected_delta = ProfileMemoryDelta {
        data: None,
        encryption: expected_encryption,
    };
    if before.termination.is_some()
        || effect.after != expected_after
        || effect.input.is_some()
        || effect.output.is_some()
        || effect.memory_delta != expected_delta
        || live_in.address != before.registers.code_pointer
        || !profile_cell_decodes_to_no_operation(
            live_in.value,
            before.registers.code_pointer,
        )
    {
        return None;
    }
    Some(DirectNoOperationProgram {
        encrypted_value,
        live_in,
        next_code_pointer,
        next_data_pointer,
        observation: before,
    })
}

pub(super) fn validate_no_operation_target(
    target: &NativeTargetIdentity,
) -> Result<(), DirectNoOperationError> {
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(DirectNoOperationError::TargetFormat);
    }
    if target.backend_id() != DIRECT_NO_OPERATION_BACKEND_ID
        || target.backend_revision() != DIRECT_NO_OPERATION_BACKEND_REVISION
        || target.native_abi_revision() != NATIVE_REGION_ABI_REVISION
    {
        return Err(DirectNoOperationError::TargetBackend);
    }
    if !target.required_features().is_empty() {
        return Err(DirectNoOperationError::TargetFeatures);
    }
    Ok(())
}

pub(super) fn validate_halt_registers_program(
    program: &RegionEffectProgram,
) -> Result<ProfileMachineObservation, DirectHaltRegistersError> {
    if !direct_program_header_supported(program)
        || !program.fits_declared_profile_capacity()
        || program.step_budget != 1
        || !program.memory_live_ins.is_empty()
        || program.effects.len() != 1
        || program.outcome
            != (RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 1,
            })
    {
        return Err(DirectHaltRegistersError::ProgramShape);
    }
    let effect = program
        .effects
        .first()
        .ok_or(DirectHaltRegistersError::ProgramShape)?;
    let expected_after = ProfileMachineObservation {
        termination: Some(Termination::HaltInstruction),
        ..effect.before
    };
    if effect.before.termination.is_some()
        || effect.after != expected_after
        || effect.input.is_some()
        || effect.output.is_some()
        || effect.memory_delta != ProfileMemoryDelta::default()
    {
        return Err(DirectHaltRegistersError::ProgramShape);
    }
    Ok(effect.before)
}

pub(super) fn validate_halt_registers_target(
    target: &NativeTargetIdentity,
) -> Result<(), DirectHaltRegistersError> {
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(DirectHaltRegistersError::TargetFormat);
    }
    if target.backend_id() != DIRECT_HALT_REGISTERS_BACKEND_ID
        || target.backend_revision() != DIRECT_HALT_REGISTERS_BACKEND_REVISION
        || target.native_abi_revision() != NATIVE_REGION_ABI_REVISION
    {
        return Err(DirectHaltRegistersError::TargetBackend);
    }
    if !target.required_features().is_empty() {
        return Err(DirectHaltRegistersError::TargetFeatures);
    }
    Ok(())
}

pub(super) fn validate_initial_halt_program(
    program: &RegionEffectProgram,
) -> Result<(), DirectInitialHaltError> {
    if !direct_program_header_supported(program)
        || !program.fits_declared_profile_capacity()
        || program.step_budget != 1
        || !program.memory_live_ins.is_empty()
        || program.effects.len() != 1
        || program.outcome
            != (RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 1,
            })
    {
        return Err(DirectInitialHaltError::ProgramShape);
    }
    let effect = program
        .effects
        .first()
        .ok_or(DirectInitialHaltError::ProgramShape)?;
    let expected_after = ProfileMachineObservation {
        termination: Some(Termination::HaltInstruction),
        ..effect.before
    };
    if !is_zero_observation(effect.before)
        || effect.after != expected_after
        || effect.input.is_some()
        || effect.output.is_some()
        || effect.memory_delta != ProfileMemoryDelta::default()
    {
        return Err(DirectInitialHaltError::ProgramShape);
    }
    Ok(())
}

pub(super) fn validate_initial_halt_target(
    target: &NativeTargetIdentity,
) -> Result<(), DirectInitialHaltError> {
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(DirectInitialHaltError::TargetFormat);
    }
    if target.backend_id() != DIRECT_INITIAL_HALT_BACKEND_ID
        || target.backend_revision() != DIRECT_INITIAL_HALT_BACKEND_REVISION
        || target.native_abi_revision() != NATIVE_REGION_ABI_REVISION
    {
        return Err(DirectInitialHaltError::TargetBackend);
    }
    if !target.required_features().is_empty() {
        return Err(DirectInitialHaltError::TargetFeatures);
    }
    Ok(())
}

pub(super) fn validate_target(
    target: &NativeTargetIdentity,
) -> Result<(), DirectDeoptError> {
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(DirectDeoptError::TargetFormat);
    }
    if target.backend_id() != DIRECT_DEOPT_BACKEND_ID
        || target.backend_revision() != DIRECT_DEOPT_BACKEND_REVISION
        || target.native_abi_revision() != NATIVE_REGION_ABI_REVISION
    {
        return Err(DirectDeoptError::TargetBackend);
    }
    if !target.required_features().is_empty() {
        return Err(DirectDeoptError::TargetFeatures);
    }
    Ok(())
}
