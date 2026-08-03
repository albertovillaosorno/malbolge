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
//   - Canonical untrusted-object emission entrypoints.
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
//   - Direct-native object emission.
// - Description:
//   - Isolates one direct-native responsibility from the facade.
// - Usage:
//   - Used only through the parent direct-native module.
// - Defaults:
//   - Unsupported values fail closed.
//

//! Canonical direct-native object emission.

use super::*;

/// Emits a deterministic direct native object that always requests deopt.
///
/// The resulting object is still untrusted until [`verify_direct_deopt_stub`]
/// performs structural admission and exact canonical-byte verification.
///
/// # Errors
///
/// Returns [`DirectDeoptError`] for unsupported target assumptions or an
/// unrepresentable native identity.
pub fn emit_direct_deopt_coff(
    program: &RegionEffectProgram,
    target: NativeTargetIdentity,
) -> Result<UntrustedNativeObjectArtifact, DirectDeoptError> {
    validate_target(&target)?;
    let key = NativeArtifactKey::new(program, target)?;
    emit_direct_deopt_with_key(key)
}

/// Emits a one-step halt fast path bound to one exact entry observation.
///
/// # Errors
///
/// Returns [`DirectHaltRegistersError`] when IR/target is outside this subset.
pub fn emit_direct_halt_registers_coff(
    program: &RegionEffectProgram,
    target: NativeTargetIdentity,
) -> Result<UntrustedNativeObjectArtifact, DirectHaltRegistersError> {
    let observation = validate_halt_registers_program(program)?;
    validate_halt_registers_target(&target)?;
    let key = NativeArtifactKey::new(program, target)?;
    emit_direct_halt_registers_with_key(key, observation)
}

/// Emits the exact graphical halt-fetch termination fast path.
///
/// # Errors
///
/// Returns [`DirectHaltFetchError`] when IR/target is outside this subset.
pub fn emit_direct_halt_fetch_coff(
    program: &RegionEffectProgram,
    target: NativeTargetIdentity,
) -> Result<UntrustedNativeObjectArtifact, DirectHaltFetchError> {
    let selected = validate_halt_fetch_program(program)?;
    validate_halt_fetch_target(&target)?;
    let key = NativeArtifactKey::new(program, target)?;
    emit_direct_halt_fetch_with_key(key, selected)
}

/// Emits a direct native fast path for the exact initial-halt IR subset.
///
/// # Errors
///
/// Returns [`DirectInitialHaltError`] when the program/target is outside the
/// reviewed subset or native identity cannot be represented.
pub fn emit_direct_initial_halt_coff(
    program: &RegionEffectProgram,
    target: NativeTargetIdentity,
) -> Result<UntrustedNativeObjectArtifact, DirectInitialHaltError> {
    validate_initial_halt_program(program)?;
    validate_initial_halt_target(&target)?;
    let key = NativeArtifactKey::new(program, target)?;
    emit_direct_initial_halt_with_key(key)
}

/// Emits the exact non-graphical fetch termination fast path.
///
/// # Errors
///
/// Returns [`DirectNonGraphicalError`] when IR/target is outside this subset.
pub fn emit_direct_non_graphical_coff(
    program: &RegionEffectProgram,
    target: NativeTargetIdentity,
) -> Result<UntrustedNativeObjectArtifact, DirectNonGraphicalError> {
    let selected = validate_non_graphical_program(program)?;
    validate_non_graphical_target(&target)?;
    let key = NativeArtifactKey::new(program, target)?;
    emit_direct_non_graphical_with_key(key, selected)
}

/// Emits one exact non-aliasing jump-code fast path.
///
/// # Errors
///
/// Returns [`DirectJumpCodeError`] when IR/target is outside this subset.
pub fn emit_direct_jump_code_coff(
    program: &RegionEffectProgram,
    target: NativeTargetIdentity,
) -> Result<UntrustedNativeObjectArtifact, DirectJumpCodeError> {
    let selected = validate_jump_code_program(program)?;
    validate_jump_code_target(&target)?;
    let key = NativeArtifactKey::new(program, target)?;
    emit_direct_jump_code_with_key(key, selected)
}

/// Emits one exact non-aliasing jump-data fast path.
///
/// # Errors
///
/// Returns [`DirectJumpDataError`] when IR/target is outside this subset.
pub fn emit_direct_jump_data_coff(
    program: &RegionEffectProgram,
    target: NativeTargetIdentity,
) -> Result<UntrustedNativeObjectArtifact, DirectJumpDataError> {
    let selected = validate_jump_data_program(program)?;
    validate_jump_data_target(&target)?;
    let key = NativeArtifactKey::new(program, target)?;
    emit_direct_jump_data_with_key(key, selected)
}

/// Emits one exact non-aliasing crazy fast path.
///
/// # Errors
///
/// Returns [`DirectCrazyError`] when IR/target is outside this subset.
pub fn emit_direct_crazy_coff(
    program: &RegionEffectProgram,
    target: NativeTargetIdentity,
) -> Result<UntrustedNativeObjectArtifact, DirectCrazyError> {
    let selected = validate_crazy_program(program)?;
    validate_crazy_target(&target)?;
    let key = NativeArtifactKey::new(program, target)?;
    emit_direct_crazy_with_key(key, selected)
}

/// Emits one exact input fast path for a byte or end-of-input.
///
/// # Errors
///
/// Returns [`DirectInputError`] when IR/target is outside this subset.
pub fn emit_direct_input_coff(
    program: &RegionEffectProgram,
    target: NativeTargetIdentity,
) -> Result<UntrustedNativeObjectArtifact, DirectInputError> {
    let selected = validate_input_program(program)?;
    validate_input_target(&target)?;
    let key = NativeArtifactKey::new(program, target)?;
    emit_direct_input_with_key(key, selected)
}

/// Emits one exact output fast path.
///
/// # Errors
///
/// Returns [`DirectOutputError`] when IR/target is outside this subset.
pub fn emit_direct_output_coff(
    program: &RegionEffectProgram,
    target: NativeTargetIdentity,
) -> Result<UntrustedNativeObjectArtifact, DirectOutputError> {
    let selected = validate_output_program(program)?;
    validate_output_target(&target)?;
    let key = NativeArtifactKey::new(program, target)?;
    emit_direct_output_with_key(key, selected)
}

/// Emits one exact non-aliasing rotate fast path.
///
/// # Errors
///
/// Returns [`DirectRotateError`] when IR/target is outside this subset.
pub fn emit_direct_rotate_coff(
    program: &RegionEffectProgram,
    target: NativeTargetIdentity,
) -> Result<UntrustedNativeObjectArtifact, DirectRotateError> {
    let selected = validate_rotate_program(program)?;
    validate_rotate_target(&target)?;
    let key = NativeArtifactKey::new(program, target)?;
    emit_direct_rotate_with_key(key, selected)
}

/// Emits one exact no-operation fetch/encryption/advance fast path.
///
/// # Errors
///
/// Returns [`DirectNoOperationError`] when IR/target is outside this subset.
pub fn emit_direct_no_operation_coff(
    program: &RegionEffectProgram,
    target: NativeTargetIdentity,
) -> Result<UntrustedNativeObjectArtifact, DirectNoOperationError> {
    let selected = validate_no_operation_program(program)?;
    validate_no_operation_target(&target)?;
    let key = NativeArtifactKey::new(program, target)?;
    emit_direct_no_operation_with_key(key, selected)
}

pub(super) fn emit_direct_deopt_with_key(
    key: NativeArtifactKey,
) -> Result<UntrustedNativeObjectArtifact, DirectDeoptError> {
    let triple = target_triple(key.target().host_isa());
    let object = canonical_coff(&key)?;
    Ok(UntrustedNativeObjectArtifact::from_emitter_output(
        key, object, triple,
    ))
}

pub(super) fn emit_direct_halt_registers_with_key(
    key: NativeArtifactKey,
    observation: ProfileMachineObservation,
) -> Result<UntrustedNativeObjectArtifact, DirectHaltRegistersError> {
    let triple = target_triple(key.target().host_isa());
    let object = halt_registers_coff(&key, observation)?;
    Ok(UntrustedNativeObjectArtifact::from_emitter_output(
        key, object, triple,
    ))
}

pub(super) fn emit_direct_halt_fetch_with_key(
    key: NativeArtifactKey,
    selected: DirectFetchedTerminalProgram,
) -> Result<UntrustedNativeObjectArtifact, DirectHaltFetchError> {
    let triple = target_triple(key.target().host_isa());
    let object = halt_fetch_coff(&key, selected)?;
    Ok(UntrustedNativeObjectArtifact::from_emitter_output(
        key, object, triple,
    ))
}

pub(super) fn emit_direct_initial_halt_with_key(
    key: NativeArtifactKey,
) -> Result<UntrustedNativeObjectArtifact, DirectInitialHaltError> {
    let triple = target_triple(key.target().host_isa());
    let object = initial_halt_coff(&key)?;
    Ok(UntrustedNativeObjectArtifact::from_emitter_output(
        key, object, triple,
    ))
}

pub(super) fn emit_direct_non_graphical_with_key(
    key: NativeArtifactKey,
    selected: DirectFetchedTerminalProgram,
) -> Result<UntrustedNativeObjectArtifact, DirectNonGraphicalError> {
    let triple = target_triple(key.target().host_isa());
    let object = non_graphical_coff(&key, selected)?;
    Ok(UntrustedNativeObjectArtifact::from_emitter_output(
        key, object, triple,
    ))
}

pub(super) fn emit_direct_jump_code_with_key(
    key: NativeArtifactKey,
    selected: DirectJumpCodeProgram,
) -> Result<UntrustedNativeObjectArtifact, DirectJumpCodeError> {
    let triple = target_triple(key.target().host_isa());
    let object = jump_code_coff(&key, selected)?;
    Ok(UntrustedNativeObjectArtifact::from_emitter_output(
        key, object, triple,
    ))
}

pub(super) fn emit_direct_jump_data_with_key(
    key: NativeArtifactKey,
    selected: DirectJumpDataProgram,
) -> Result<UntrustedNativeObjectArtifact, DirectJumpDataError> {
    let triple = target_triple(key.target().host_isa());
    let object = jump_data_coff(&key, selected)?;
    Ok(UntrustedNativeObjectArtifact::from_emitter_output(
        key, object, triple,
    ))
}

pub(super) fn emit_direct_crazy_with_key(
    key: NativeArtifactKey,
    selected: DirectCrazyProgram,
) -> Result<UntrustedNativeObjectArtifact, DirectCrazyError> {
    let triple = target_triple(key.target().host_isa());
    let object = crazy_coff(&key, selected)?;
    Ok(UntrustedNativeObjectArtifact::from_emitter_output(
        key, object, triple,
    ))
}

pub(super) fn emit_direct_input_with_key(
    key: NativeArtifactKey,
    selected: DirectInputProgram,
) -> Result<UntrustedNativeObjectArtifact, DirectInputError> {
    let triple = target_triple(key.target().host_isa());
    let object = input_coff(&key, selected)?;
    Ok(UntrustedNativeObjectArtifact::from_emitter_output(
        key, object, triple,
    ))
}

pub(super) fn emit_direct_output_with_key(
    key: NativeArtifactKey,
    selected: DirectOutputProgram,
) -> Result<UntrustedNativeObjectArtifact, DirectOutputError> {
    let triple = target_triple(key.target().host_isa());
    let object = output_coff(&key, selected)?;
    Ok(UntrustedNativeObjectArtifact::from_emitter_output(
        key, object, triple,
    ))
}

pub(super) fn emit_direct_rotate_with_key(
    key: NativeArtifactKey,
    selected: DirectRotateProgram,
) -> Result<UntrustedNativeObjectArtifact, DirectRotateError> {
    let triple = target_triple(key.target().host_isa());
    let object = rotate_coff(&key, selected)?;
    Ok(UntrustedNativeObjectArtifact::from_emitter_output(
        key, object, triple,
    ))
}

pub(super) fn emit_direct_no_operation_with_key(
    key: NativeArtifactKey,
    selected: DirectNoOperationProgram,
) -> Result<UntrustedNativeObjectArtifact, DirectNoOperationError> {
    let triple = target_triple(key.target().host_isa());
    let object = no_operation_coff(&key, selected)?;
    Ok(UntrustedNativeObjectArtifact::from_emitter_output(
        key, object, triple,
    ))
}
