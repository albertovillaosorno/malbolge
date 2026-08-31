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
//   - Semantic promotion of untrusted direct objects.
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
//   - Direct-native semantic verification.
// - Description:
//   - Isolates one direct-native responsibility from the facade.
// - Usage:
//   - Used only through the parent direct-native module.
// - Defaults:
//   - Unsupported values fail closed.
//

//! Semantic verification for direct-native objects.

use super::*;

/// Promotes only the exact canonical deopt-only object to semantic authority.
///
/// Byte equality here is semantic validation because v1 admits exactly two
/// reviewed instruction sequences: each sets the integer return register to the
/// guard-miss status `1` and returns without reading or writing guest state.
///
/// # Errors
///
/// Returns [`DirectDeoptError`] when target assumptions, COFF structure, or any
/// object byte differs from the canonical deoptimization stub.
pub fn verify_direct_deopt_stub(
    artifact: &UntrustedNativeObjectArtifact,
) -> Result<VerifiedDeoptNativeObjectArtifact, DirectDeoptError> {
    validate_target(artifact.key().target())?;
    let admitted = structurally_admit_coff(artifact)?;
    let expected = canonical_coff(artifact.key())?;
    if admitted.object() != expected {
        return Err(DirectDeoptError::ObjectBytes);
    }
    Ok(VerifiedDeoptNativeObjectArtifact { artifact: admitted })
}

/// Promotes only the canonical exact-observation halt object for its IR.
///
/// # Errors
///
/// Returns [`DirectHaltRegistersError`] for IR/identity/COFF/byte mismatch.
pub fn verify_direct_halt_registers(
    artifact: &UntrustedNativeObjectArtifact,
    program: &RegionEffectProgram,
) -> Result<VerifiedHaltRegistersNativeObjectArtifact, DirectHaltRegistersError>
{
    let observation = validate_halt_registers_program(program)?;
    validate_halt_registers_target(artifact.key().target())?;
    let expected_key =
        NativeArtifactKey::new(program, artifact.key().target().clone())?;
    if artifact.key() != &expected_key {
        return Err(DirectHaltRegistersError::ProgramShape);
    }
    let admitted = structurally_admit_coff(artifact)?;
    let expected = halt_registers_coff(artifact.key(), observation)?;
    if admitted.object() != expected {
        return Err(DirectHaltRegistersError::ObjectBytes);
    }
    Ok(VerifiedHaltRegistersNativeObjectArtifact { artifact: admitted })
}

/// Promotes only guarded crazy code bound to exact v5 geometry.
///
/// # Errors
///
/// Returns [`DirectExecutionGeometryCrazyError`] when v5 shape, identity,
/// target, COFF structure, or any canonical object byte differs.
pub fn verify_direct_execution_geometry_crazy(
    artifact: &UntrustedNativeObjectArtifact,
    program: &ExecutionGeometryRegionEffectProgram,
) -> Result<
    VerifiedExecutionGeometryCrazyNativeObjectArtifact,
    DirectExecutionGeometryCrazyError,
> {
    let selected = validate_execution_geometry_crazy_program(program)?;
    validate_execution_geometry_crazy_target(artifact.key().target())?;
    let expected_key = NativeArtifactKey::new_execution_geometry(
        program,
        artifact.key().target().clone(),
    )?;
    if artifact.key() != &expected_key {
        return Err(DirectExecutionGeometryCrazyError::ProgramShape);
    }
    let admitted = structurally_admit_coff(artifact)?;
    let expected = execution_geometry_crazy_coff(artifact.key(), selected)?;
    if admitted.object() != expected {
        return Err(DirectExecutionGeometryCrazyError::ObjectBytes);
    }
    Ok(VerifiedExecutionGeometryCrazyNativeObjectArtifact {
        artifact: admitted,
    })
}

/// Promotes only guarded initial-halt code bound to exact v5 geometry.
///
/// # Errors
///
/// Returns [`DirectExecutionGeometryInitialHaltError`] when v5 shape, identity,
/// target, COFF structure, or any canonical object byte differs.
pub fn verify_direct_execution_geometry_initial_halt(
    artifact: &UntrustedNativeObjectArtifact,
    program: &ExecutionGeometryRegionEffectProgram,
) -> Result<
    VerifiedExecutionGeometryInitialHaltNativeObjectArtifact,
    DirectExecutionGeometryInitialHaltError,
> {
    let selected = validate_execution_geometry_initial_halt_program(program)?;
    validate_execution_geometry_initial_halt_target(artifact.key().target())?;
    let expected_key = NativeArtifactKey::new_execution_geometry(
        program,
        artifact.key().target().clone(),
    )?;
    if artifact.key() != &expected_key {
        return Err(DirectExecutionGeometryInitialHaltError::ProgramShape);
    }
    let admitted = structurally_admit_coff(artifact)?;
    let expected =
        execution_geometry_initial_halt_coff(artifact.key(), selected)?;
    if admitted.object() != expected {
        return Err(DirectExecutionGeometryInitialHaltError::ObjectBytes);
    }
    Ok(VerifiedExecutionGeometryInitialHaltNativeObjectArtifact {
        artifact: admitted,
    })
}

/// Promotes only guarded aliasing initial jump-data code bound to exact v5
/// geometry.
///
/// # Errors
///
/// Returns [`DirectExecutionGeometryInitialJumpDataError`] when v5 shape,
/// identity, target, COFF structure, or any canonical object byte differs.
pub fn verify_direct_execution_geometry_initial_jump_data(
    artifact: &UntrustedNativeObjectArtifact,
    program: &ExecutionGeometryRegionEffectProgram,
) -> Result<
    VerifiedExecutionGeometryInitialJumpDataNativeObjectArtifact,
    DirectExecutionGeometryInitialJumpDataError,
> {
    let selected =
        validate_execution_geometry_initial_jump_data_program(program)?;
    validate_execution_geometry_initial_jump_data_target(
        artifact.key().target(),
    )?;
    let expected_key = NativeArtifactKey::new_execution_geometry(
        program,
        artifact.key().target().clone(),
    )?;
    if artifact.key() != &expected_key {
        return Err(DirectExecutionGeometryInitialJumpDataError::ProgramShape);
    }
    let admitted = structurally_admit_coff(artifact)?;
    let expected =
        execution_geometry_initial_jump_data_coff(artifact.key(), selected)?;
    if admitted.object() != expected {
        return Err(DirectExecutionGeometryInitialJumpDataError::ObjectBytes);
    }
    Ok(
        VerifiedExecutionGeometryInitialJumpDataNativeObjectArtifact {
            artifact: admitted,
        },
    )
}

/// Promotes only guarded input code bound to exact v5 geometry.
///
/// # Errors
///
/// Returns [`DirectExecutionGeometryInputError`] when v5 shape, identity,
/// target, COFF structure, or any canonical object byte differs.
pub fn verify_direct_execution_geometry_input(
    artifact: &UntrustedNativeObjectArtifact,
    program: &ExecutionGeometryRegionEffectProgram,
) -> Result<
    VerifiedExecutionGeometryInputNativeObjectArtifact,
    DirectExecutionGeometryInputError,
> {
    let selected = validate_execution_geometry_input_program(program)?;
    validate_execution_geometry_input_target(artifact.key().target())?;
    let expected_key = NativeArtifactKey::new_execution_geometry(
        program,
        artifact.key().target().clone(),
    )?;
    if artifact.key() != &expected_key {
        return Err(DirectExecutionGeometryInputError::ProgramShape);
    }
    let admitted = structurally_admit_coff(artifact)?;
    let expected = execution_geometry_input_coff(artifact.key(), selected)?;
    if admitted.object() != expected {
        return Err(DirectExecutionGeometryInputError::ObjectBytes);
    }
    Ok(VerifiedExecutionGeometryInputNativeObjectArtifact {
        artifact: admitted,
    })
}

/// Promotes only guarded no-operation code bound to exact v5 geometry.
///
/// # Errors
///
/// Returns [`DirectExecutionGeometryNoOperationError`] when v5 shape, identity,
/// target, COFF structure, or any canonical object byte differs.
pub fn verify_direct_execution_geometry_no_operation(
    artifact: &UntrustedNativeObjectArtifact,
    program: &ExecutionGeometryRegionEffectProgram,
) -> Result<
    VerifiedExecutionGeometryNoOperationNativeObjectArtifact,
    DirectExecutionGeometryNoOperationError,
> {
    let selected = validate_execution_geometry_no_operation_program(program)?;
    validate_execution_geometry_no_operation_target(artifact.key().target())?;
    let expected_key = NativeArtifactKey::new_execution_geometry(
        program,
        artifact.key().target().clone(),
    )?;
    if artifact.key() != &expected_key {
        return Err(DirectExecutionGeometryNoOperationError::ProgramShape);
    }
    let admitted = structurally_admit_coff(artifact)?;
    let expected =
        execution_geometry_no_operation_coff(artifact.key(), selected)?;
    if admitted.object() != expected {
        return Err(DirectExecutionGeometryNoOperationError::ObjectBytes);
    }
    Ok(VerifiedExecutionGeometryNoOperationNativeObjectArtifact {
        artifact: admitted,
    })
}

/// Promotes only guarded output code bound to exact v5 geometry.
///
/// # Errors
///
/// Returns [`DirectExecutionGeometryOutputError`] when v5 shape, identity,
/// target, COFF structure, or any canonical object byte differs.
pub fn verify_direct_execution_geometry_output(
    artifact: &UntrustedNativeObjectArtifact,
    program: &ExecutionGeometryRegionEffectProgram,
) -> Result<
    VerifiedExecutionGeometryOutputNativeObjectArtifact,
    DirectExecutionGeometryOutputError,
> {
    let selected = validate_execution_geometry_output_program(program)?;
    validate_execution_geometry_output_target(artifact.key().target())?;
    let expected_key = NativeArtifactKey::new_execution_geometry(
        program,
        artifact.key().target().clone(),
    )?;
    if artifact.key() != &expected_key {
        return Err(DirectExecutionGeometryOutputError::ProgramShape);
    }
    let admitted = structurally_admit_coff(artifact)?;
    let expected = execution_geometry_output_coff(artifact.key(), selected)?;
    if admitted.object() != expected {
        return Err(DirectExecutionGeometryOutputError::ObjectBytes);
    }
    Ok(VerifiedExecutionGeometryOutputNativeObjectArtifact {
        artifact: admitted,
    })
}

/// Promotes only guarded rotate code bound to exact v5 geometry.
///
/// # Errors
///
/// Returns [`DirectExecutionGeometryRotateError`] when v5 shape, identity,
/// target, COFF structure, or any canonical object byte differs.
pub fn verify_direct_execution_geometry_rotate(
    artifact: &UntrustedNativeObjectArtifact,
    program: &ExecutionGeometryRegionEffectProgram,
) -> Result<
    VerifiedExecutionGeometryRotateNativeObjectArtifact,
    DirectExecutionGeometryRotateError,
> {
    let selected = validate_execution_geometry_rotate_program(program)?;
    validate_execution_geometry_rotate_target(artifact.key().target())?;
    let expected_key = NativeArtifactKey::new_execution_geometry(
        program,
        artifact.key().target().clone(),
    )?;
    if artifact.key() != &expected_key {
        return Err(DirectExecutionGeometryRotateError::ProgramShape);
    }
    let admitted = structurally_admit_coff(artifact)?;
    let expected = execution_geometry_rotate_coff(artifact.key(), selected)?;
    if admitted.object() != expected {
        return Err(DirectExecutionGeometryRotateError::ObjectBytes);
    }
    Ok(VerifiedExecutionGeometryRotateNativeObjectArtifact {
        artifact: admitted,
    })
}

/// Promotes only the canonical graphical halt-fetch object for its exact IR.
///
/// # Errors
///
/// Returns [`DirectHaltFetchError`] for IR/identity/COFF/byte mismatch.
pub fn verify_direct_halt_fetch(
    artifact: &UntrustedNativeObjectArtifact,
    program: &RegionEffectProgram,
) -> Result<VerifiedHaltFetchNativeObjectArtifact, DirectHaltFetchError> {
    let selected = validate_halt_fetch_program(program)?;
    validate_halt_fetch_target(artifact.key().target())?;
    let expected_key =
        NativeArtifactKey::new(program, artifact.key().target().clone())?;
    if artifact.key() != &expected_key {
        return Err(DirectHaltFetchError::ProgramShape);
    }
    let admitted = structurally_admit_coff(artifact)?;
    let expected = halt_fetch_coff(artifact.key(), selected)?;
    if admitted.object() != expected {
        return Err(DirectHaltFetchError::ObjectBytes);
    }
    Ok(VerifiedHaltFetchNativeObjectArtifact { artifact: admitted })
}

/// Promotes only the exact canonical initial-halt object for its exact IR.
///
/// # Errors
///
/// Returns [`DirectInitialHaltError`] when IR shape, identity, COFF structure,
/// or any object byte differs from the reviewed initial-halt contract.
pub fn verify_direct_initial_halt(
    artifact: &UntrustedNativeObjectArtifact,
    program: &RegionEffectProgram,
) -> Result<VerifiedInitialHaltNativeObjectArtifact, DirectInitialHaltError> {
    validate_initial_halt_program(program)?;
    validate_initial_halt_target(artifact.key().target())?;
    let expected_key =
        NativeArtifactKey::new(program, artifact.key().target().clone())?;
    if artifact.key() != &expected_key {
        return Err(DirectInitialHaltError::ProgramShape);
    }
    let admitted = structurally_admit_coff(artifact)?;
    let expected = initial_halt_coff(artifact.key())?;
    if admitted.object() != expected {
        return Err(DirectInitialHaltError::ObjectBytes);
    }
    Ok(VerifiedInitialHaltNativeObjectArtifact { artifact: admitted })
}

/// Promotes only the canonical non-graphical object for its exact IR.
///
/// # Errors
///
/// Returns [`DirectNonGraphicalError`] for IR/identity/COFF/byte mismatch.
pub fn verify_direct_non_graphical(
    artifact: &UntrustedNativeObjectArtifact,
    program: &RegionEffectProgram,
) -> Result<VerifiedNonGraphicalNativeObjectArtifact, DirectNonGraphicalError> {
    let selected = validate_non_graphical_program(program)?;
    validate_non_graphical_target(artifact.key().target())?;
    let expected_key =
        NativeArtifactKey::new(program, artifact.key().target().clone())?;
    if artifact.key() != &expected_key {
        return Err(DirectNonGraphicalError::ProgramShape);
    }
    let admitted = structurally_admit_coff(artifact)?;
    let expected = non_graphical_coff(artifact.key(), selected)?;
    if admitted.object() != expected {
        return Err(DirectNonGraphicalError::ObjectBytes);
    }
    Ok(VerifiedNonGraphicalNativeObjectArtifact { artifact: admitted })
}

/// Promotes only the canonical jump-code object for its exact IR.
///
/// # Errors
///
/// Returns [`DirectJumpCodeError`] for IR/identity/COFF/byte mismatch.
pub fn verify_direct_jump_code(
    artifact: &UntrustedNativeObjectArtifact,
    program: &RegionEffectProgram,
) -> Result<VerifiedJumpCodeNativeObjectArtifact, DirectJumpCodeError> {
    let selected = validate_jump_code_program(program)?;
    validate_jump_code_target(artifact.key().target())?;
    let expected_key =
        NativeArtifactKey::new(program, artifact.key().target().clone())?;
    if artifact.key() != &expected_key {
        return Err(DirectJumpCodeError::ProgramShape);
    }
    let admitted = structurally_admit_coff(artifact)?;
    let expected = jump_code_coff(artifact.key(), selected)?;
    if admitted.object() != expected {
        return Err(DirectJumpCodeError::ObjectBytes);
    }
    Ok(VerifiedJumpCodeNativeObjectArtifact { artifact: admitted })
}

/// Promotes only the canonical jump-data object for its exact IR.
///
/// # Errors
///
/// Returns [`DirectJumpDataError`] for IR/identity/COFF/byte mismatch.
pub fn verify_direct_jump_data(
    artifact: &UntrustedNativeObjectArtifact,
    program: &RegionEffectProgram,
) -> Result<VerifiedJumpDataNativeObjectArtifact, DirectJumpDataError> {
    let selected = validate_jump_data_program(program)?;
    validate_jump_data_target(artifact.key().target())?;
    let expected_key =
        NativeArtifactKey::new(program, artifact.key().target().clone())?;
    if artifact.key() != &expected_key {
        return Err(DirectJumpDataError::ProgramShape);
    }
    let admitted = structurally_admit_coff(artifact)?;
    let expected = jump_data_coff(artifact.key(), selected)?;
    if admitted.object() != expected {
        return Err(DirectJumpDataError::ObjectBytes);
    }
    Ok(VerifiedJumpDataNativeObjectArtifact { artifact: admitted })
}

/// Promotes only the canonical crazy object for its exact IR.
///
/// # Errors
///
/// Returns [`DirectCrazyError`] for IR/identity/COFF/byte mismatch.
pub fn verify_direct_crazy(
    artifact: &UntrustedNativeObjectArtifact,
    program: &RegionEffectProgram,
) -> Result<VerifiedCrazyNativeObjectArtifact, DirectCrazyError> {
    let selected = validate_crazy_program(program)?;
    validate_crazy_target(artifact.key().target())?;
    let expected_key =
        NativeArtifactKey::new(program, artifact.key().target().clone())?;
    if artifact.key() != &expected_key {
        return Err(DirectCrazyError::ProgramShape);
    }
    let admitted = structurally_admit_coff(artifact)?;
    let expected = crazy_coff(artifact.key(), selected)?;
    if admitted.object() != expected {
        return Err(DirectCrazyError::ObjectBytes);
    }
    Ok(VerifiedCrazyNativeObjectArtifact { artifact: admitted })
}

/// Promotes only the canonical input object for its exact IR.
///
/// # Errors
///
/// Returns [`DirectInputError`] for IR/identity/COFF/byte mismatch.
pub fn verify_direct_input(
    artifact: &UntrustedNativeObjectArtifact,
    program: &RegionEffectProgram,
) -> Result<VerifiedInputNativeObjectArtifact, DirectInputError> {
    let selected = validate_input_program(program)?;
    validate_input_target(artifact.key().target())?;
    let expected_key =
        NativeArtifactKey::new(program, artifact.key().target().clone())?;
    if artifact.key() != &expected_key {
        return Err(DirectInputError::ProgramShape);
    }
    let admitted = structurally_admit_coff(artifact)?;
    let expected = input_coff(artifact.key(), selected)?;
    if admitted.object() != expected {
        return Err(DirectInputError::ObjectBytes);
    }
    Ok(VerifiedInputNativeObjectArtifact { artifact: admitted })
}

/// Promotes only the canonical output object for its exact IR.
///
/// # Errors
///
/// Returns [`DirectOutputError`] for IR/identity/COFF/byte mismatch.
pub fn verify_direct_output(
    artifact: &UntrustedNativeObjectArtifact,
    program: &RegionEffectProgram,
) -> Result<VerifiedOutputNativeObjectArtifact, DirectOutputError> {
    let selected = validate_output_program(program)?;
    validate_output_target(artifact.key().target())?;
    let expected_key =
        NativeArtifactKey::new(program, artifact.key().target().clone())?;
    if artifact.key() != &expected_key {
        return Err(DirectOutputError::ProgramShape);
    }
    let admitted = structurally_admit_coff(artifact)?;
    let expected = output_coff(artifact.key(), selected)?;
    if admitted.object() != expected {
        return Err(DirectOutputError::ObjectBytes);
    }
    Ok(VerifiedOutputNativeObjectArtifact { artifact: admitted })
}

/// Promotes only the canonical rotate object for its exact IR.
///
/// # Errors
///
/// Returns [`DirectRotateError`] for IR/identity/COFF/byte mismatch.
pub fn verify_direct_rotate(
    artifact: &UntrustedNativeObjectArtifact,
    program: &RegionEffectProgram,
) -> Result<VerifiedRotateNativeObjectArtifact, DirectRotateError> {
    let selected = validate_rotate_program(program)?;
    validate_rotate_target(artifact.key().target())?;
    let expected_key =
        NativeArtifactKey::new(program, artifact.key().target().clone())?;
    if artifact.key() != &expected_key {
        return Err(DirectRotateError::ProgramShape);
    }
    let admitted = structurally_admit_coff(artifact)?;
    let expected = rotate_coff(artifact.key(), selected)?;
    if admitted.object() != expected {
        return Err(DirectRotateError::ObjectBytes);
    }
    Ok(VerifiedRotateNativeObjectArtifact { artifact: admitted })
}

/// Promotes only the canonical no-operation object for its exact IR.
///
/// # Errors
///
/// Returns [`DirectNoOperationError`] for IR/identity/COFF/byte mismatch.
pub fn verify_direct_no_operation(
    artifact: &UntrustedNativeObjectArtifact,
    program: &RegionEffectProgram,
) -> Result<VerifiedNoOperationNativeObjectArtifact, DirectNoOperationError> {
    let selected = validate_no_operation_program(program)?;
    validate_no_operation_target(artifact.key().target())?;
    let expected_key =
        NativeArtifactKey::new(program, artifact.key().target().clone())?;
    if artifact.key() != &expected_key {
        return Err(DirectNoOperationError::ProgramShape);
    }
    let admitted = structurally_admit_coff(artifact)?;
    let expected = no_operation_coff(artifact.key(), selected)?;
    if admitted.object() != expected {
        return Err(DirectNoOperationError::ObjectBytes);
    }
    Ok(VerifiedNoOperationNativeObjectArtifact { artifact: admitted })
}
