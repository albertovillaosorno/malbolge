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
//   - Direct target preparation, cache policy, and tier selection.
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
//   - Direct-native planning and cache policy.
// - Description:
//   - Isolates one direct-native responsibility from the facade.
// - Usage:
//   - Used only through the parent direct-native module.
// - Defaults:
//   - Unsupported values fail closed.
//

//! Direct target planning and cache-aware selection.

use super::*;

#[derive(Clone, Debug, Eq, PartialEq)]
enum SelectedDirectTarget {
    Crazy(NativeTargetIdentity),
    Deopt(NativeTargetIdentity),
    HaltFetch(NativeTargetIdentity),
    HaltRegisters(NativeTargetIdentity),
    InitialHalt(NativeTargetIdentity),
    Input(NativeTargetIdentity),
    JumpCode(NativeTargetIdentity),
    JumpData(NativeTargetIdentity),
    NoOperation(NativeTargetIdentity),
    NonGraphical(NativeTargetIdentity),
    Output(NativeTargetIdentity),
    Rotate(NativeTargetIdentity),
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(super) enum PreparedDirectTarget {
    Crazy(NativeArtifactKey),
    Deopt(NativeArtifactKey),
    HaltFetch(NativeArtifactKey),
    HaltRegisters(NativeArtifactKey),
    InitialHalt(NativeArtifactKey),
    Input(NativeArtifactKey),
    JumpCode(NativeArtifactKey),
    JumpData(NativeArtifactKey),
    NoOperation(NativeArtifactKey),
    NonGraphical(NativeArtifactKey),
    Output(NativeArtifactKey),
    Rotate(NativeArtifactKey),
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(super) enum PreparedExecutionGeometryDirectTarget {
    Crazy(NativeArtifactKey),
    InitialHalt(NativeArtifactKey),
    InitialJumpData(NativeArtifactKey),
    Input(NativeArtifactKey),
    JumpCode(NativeArtifactKey),
    NoOperation(NativeArtifactKey),
    Output(NativeArtifactKey),
    Rotate(NativeArtifactKey),
}

type VerifiedDirectSelectionResult<'requirement> =
    Result<VerifiedDirectNativeArtifact, DirectSelectionError<'requirement>>;

/// Failure while selecting one reviewed explicit-geometry native template.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryDirectSelectionError {
    /// Guarded crazy emission or verification failed.
    Crazy(DirectExecutionGeometryCrazyError),
    /// Guarded initial-halt emission or verification failed.
    InitialHalt(DirectExecutionGeometryInitialHaltError),
    /// Guarded initial jump-data emission or verification failed.
    InitialJumpData(DirectExecutionGeometryInitialJumpDataError),
    /// Guarded input emission or verification failed.
    Input(DirectExecutionGeometryInputError),
    /// Guarded jump-code emission or verification failed.
    JumpCode(DirectExecutionGeometryJumpCodeError),
    /// Guarded no-operation emission or verification failed.
    NoOperation(DirectExecutionGeometryNoOperationError),
    /// Guarded output emission or verification failed.
    Output(DirectExecutionGeometryOutputError),
    /// The canonical profile identity does not match the v5 program header.
    ProfileIdentity,
    /// Guarded rotate emission or verification failed.
    Rotate(DirectExecutionGeometryRotateError),
    /// No reviewed v5 one-step template admits this program.
    UnsupportedProgram,
}

impl Display for ExecutionGeometryDirectSelectionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Crazy(error) => Display::fmt(error, f),
            Self::InitialHalt(error) => Display::fmt(error, f),
            Self::InitialJumpData(error) => Display::fmt(error, f),
            Self::Input(error) => Display::fmt(error, f),
            Self::JumpCode(error) => Display::fmt(error, f),
            Self::NoOperation(error) => Display::fmt(error, f),
            Self::Output(error) => Display::fmt(error, f),
            Self::ProfileIdentity => {
                f.write_str("v5 native selection profile identity drifted")
            },
            Self::Rotate(error) => Display::fmt(error, f),
            Self::UnsupportedProgram => f.write_str(
                "explicit-geometry IR has no reviewed native template",
            ),
        }
    }
}

impl VerifiedExecutionGeometryNativeCache {
    /// Removes every retained verified v5 artifact.
    pub fn clear(&mut self) {
        self.entries.clear();
    }

    /// Reports whether no verified v5 artifacts are retained.
    #[must_use]
    pub const fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    /// Returns the number of exact-key verified v5 artifacts.
    #[must_use]
    pub const fn len(&self) -> usize {
        self.entries.len()
    }
}

impl VerifiedDirectNativeCache {
    /// Removes every retained verified artifact.
    pub fn clear(&mut self) {
        self.entries.clear();
    }

    /// Invalidates future reuse of one exact verified artifact key.
    ///
    /// Outstanding [`Arc`] owners remain valid; invalidation only removes the
    /// cache entry used by later planning.
    pub fn invalidate(
        &mut self,
        artifact: &VerifiedDirectNativeArtifact,
    ) -> bool {
        self.entries.remove(artifact.key()).is_some()
    }

    /// Invalidates future reuse of every direct variant for one exact program.
    ///
    /// Outstanding [`Arc`] owners remain valid. Program identity construction
    /// fails before mutation when the IR exceeds its declared profile capacity.
    ///
    /// # Errors
    ///
    /// Returns [`NativeIdentityError`] when exact region identity cannot be
    /// constructed.
    pub fn invalidate_program(
        &mut self,
        program: &RegionEffectProgram,
    ) -> Result<usize, NativeIdentityError> {
        let identity = RegionEffectIdentity::new(program)?;
        Ok(self.entries.remove_region(&identity))
    }

    /// Invalidates every cached region for one artifact's exact direct target.
    ///
    /// The target includes host ISA, backend/revision, native ABI revision, and
    /// required features. Outstanding [`Arc`] owners remain valid.
    pub fn invalidate_target(
        &mut self,
        artifact: &VerifiedDirectNativeArtifact,
    ) -> usize {
        self.entries.remove_target(artifact.key().target())
    }

    /// Reports whether no verified direct artifacts are retained.
    #[must_use]
    pub const fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    /// Returns the number of exact-key verified direct artifacts.
    #[must_use]
    pub const fn len(&self) -> usize {
        self.entries.len()
    }
}

impl PreparedExecutionGeometryDirectTarget {
    pub(super) fn emit_verified(
        self,
        program: &ExecutionGeometryRegionEffectProgram,
    ) -> Result<
        VerifiedExecutionGeometryNativeArtifact,
        ExecutionGeometryDirectSelectionError,
    > {
        match self {
            Self::Crazy(key) => select_execution_geometry_crazy(
                program,
                key.target().host_os(),
                key.target().host_isa(),
            ),
            Self::InitialHalt(key) => select_execution_geometry_initial_halt(
                program,
                key.target().host_os(),
                key.target().host_isa(),
            ),
            Self::InitialJumpData(key) => {
                select_execution_geometry_initial_jump_data(
                    program,
                    key.target().host_os(),
                    key.target().host_isa(),
                )
            },
            Self::Input(key) => select_execution_geometry_input(
                program,
                key.target().host_os(),
                key.target().host_isa(),
            ),
            Self::JumpCode(key) => select_execution_geometry_jump_code(
                program,
                key.target().host_os(),
                key.target().host_isa(),
            ),
            Self::NoOperation(key) => select_execution_geometry_no_operation(
                program,
                key.target().host_os(),
                key.target().host_isa(),
            ),
            Self::Output(key) => select_execution_geometry_output(
                program,
                key.target().host_os(),
                key.target().host_isa(),
            ),
            Self::Rotate(key) => select_execution_geometry_rotate(
                program,
                key.target().host_os(),
                key.target().host_isa(),
            ),
        }
    }

    pub(super) const fn key(&self) -> &NativeArtifactKey {
        match self {
            Self::Crazy(key)
            | Self::InitialHalt(key)
            | Self::InitialJumpData(key)
            | Self::Input(key)
            | Self::JumpCode(key)
            | Self::NoOperation(key)
            | Self::Output(key)
            | Self::Rotate(key) => key,
        }
    }
}

impl PreparedDirectTarget {
    pub(super) fn emit_verified(
        self,
        program: &RegionEffectProgram,
    ) -> VerifiedDirectSelectionResult<'_> {
        match self {
            Self::Crazy(key) => emit_verified_crazy(key, program),
            Self::Deopt(key) => {
                validate_target(key.target()).map_err(|error| {
                    DirectSelectionError::Deopt(Box::new(error))
                })?;
                let artifact =
                    emit_direct_deopt_with_key(key).map_err(|error| {
                        DirectSelectionError::Deopt(Box::new(error))
                    })?;
                let verified =
                    verify_direct_deopt_stub(&artifact).map_err(|error| {
                        DirectSelectionError::Deopt(Box::new(error))
                    })?;
                Ok(VerifiedDirectNativeArtifact::Deopt(verified))
            },
            Self::HaltFetch(key) => emit_verified_halt_fetch(key, program),
            Self::HaltRegisters(key) => {
                let registers = validate_halt_registers_program(program)
                    .map_err(|error| {
                        DirectSelectionError::HaltRegisters(Box::new(error))
                    })?;
                validate_halt_registers_target(key.target()).map_err(
                    |error| {
                        DirectSelectionError::HaltRegisters(Box::new(error))
                    },
                )?;
                let artifact =
                    emit_direct_halt_registers_with_key(key, registers)
                        .map_err(|error| {
                            DirectSelectionError::HaltRegisters(Box::new(error))
                        })?;
                let verified = verify_direct_halt_registers(&artifact, program)
                    .map_err(|error| {
                        DirectSelectionError::HaltRegisters(Box::new(error))
                    })?;
                Ok(VerifiedDirectNativeArtifact::HaltRegisters(verified))
            },
            Self::InitialHalt(key) => emit_verified_initial_halt(key, program),
            Self::Input(key) => emit_verified_input(key, program),
            Self::JumpCode(key) => emit_verified_jump_code(key, program),
            Self::JumpData(key) => emit_verified_jump_data(key, program),
            Self::NonGraphical(key) => {
                emit_verified_non_graphical(key, program)
            },
            Self::NoOperation(key) => emit_verified_no_operation(key, program),
            Self::Output(key) => emit_verified_output(key, program),
            Self::Rotate(key) => emit_verified_rotate(key, program),
        }
    }

    pub(super) const fn is_deoptimization(&self) -> bool {
        matches!(self, Self::Deopt(_key))
    }

    pub(super) const fn key(&self) -> &NativeArtifactKey {
        match self {
            Self::Crazy(key)
            | Self::Deopt(key)
            | Self::HaltFetch(key)
            | Self::HaltRegisters(key)
            | Self::InitialHalt(key)
            | Self::Input(key)
            | Self::JumpCode(key)
            | Self::JumpData(key)
            | Self::NonGraphical(key)
            | Self::NoOperation(key)
            | Self::Output(key)
            | Self::Rotate(key) => key,
        }
    }
}

impl SelectedDirectTarget {
    fn prepare(
        self,
        program: &RegionEffectProgram,
    ) -> Result<PreparedDirectTarget, DirectSelectionError<'_>> {
        match self {
            Self::Crazy(target) => prepare_crazy_target(program, target),
            Self::Deopt(target) => NativeArtifactKey::new(program, target)
                .map(PreparedDirectTarget::Deopt)
                .map_err(|error| {
                    DirectSelectionError::Deopt(Box::new(
                        DirectDeoptError::Identity(error),
                    ))
                }),
            Self::HaltFetch(target) => NativeArtifactKey::new(program, target)
                .map(PreparedDirectTarget::HaltFetch)
                .map_err(|error| {
                    DirectSelectionError::HaltFetch(Box::new(
                        DirectHaltFetchError::Identity(error),
                    ))
                }),
            Self::HaltRegisters(target) => {
                NativeArtifactKey::new(program, target)
                    .map(PreparedDirectTarget::HaltRegisters)
                    .map_err(|error| {
                        DirectSelectionError::HaltRegisters(Box::new(
                            DirectHaltRegistersError::Identity(error),
                        ))
                    })
            },
            Self::InitialHalt(target) => {
                NativeArtifactKey::new(program, target)
                    .map(PreparedDirectTarget::InitialHalt)
                    .map_err(|error| {
                        DirectSelectionError::InitialHalt(Box::new(
                            DirectInitialHaltError::Identity(error),
                        ))
                    })
            },
            Self::Input(target) => prepare_input_target(program, target),
            Self::JumpCode(target) => prepare_jump_code_target(program, target),
            Self::JumpData(target) => NativeArtifactKey::new(program, target)
                .map(PreparedDirectTarget::JumpData)
                .map_err(|error| {
                    DirectSelectionError::JumpData(Box::new(
                        DirectJumpDataError::Identity(error),
                    ))
                }),
            Self::NonGraphical(target) => {
                NativeArtifactKey::new(program, target)
                    .map(PreparedDirectTarget::NonGraphical)
                    .map_err(|error| {
                        DirectSelectionError::NonGraphical(Box::new(
                            DirectNonGraphicalError::Identity(error),
                        ))
                    })
            },
            Self::NoOperation(target) => {
                prepare_no_operation_target(program, target)
            },
            Self::Output(target) => prepare_output_target(program, target),
            Self::Rotate(target) => prepare_rotate_target(program, target),
        }
    }
}
fn prepare_crazy_target(
    program: &RegionEffectProgram,
    target: NativeTargetIdentity,
) -> Result<PreparedDirectTarget, DirectSelectionError<'_>> {
    NativeArtifactKey::new(program, target)
        .map(PreparedDirectTarget::Crazy)
        .map_err(|error| {
            DirectSelectionError::Crazy(Box::new(DirectCrazyError::Identity(
                error,
            )))
        })
}

fn prepare_input_target(
    program: &RegionEffectProgram,
    target: NativeTargetIdentity,
) -> Result<PreparedDirectTarget, DirectSelectionError<'_>> {
    NativeArtifactKey::new(program, target)
        .map(PreparedDirectTarget::Input)
        .map_err(|error| {
            DirectSelectionError::Input(Box::new(DirectInputError::Identity(
                error,
            )))
        })
}

fn prepare_jump_code_target(
    program: &RegionEffectProgram,
    target: NativeTargetIdentity,
) -> Result<PreparedDirectTarget, DirectSelectionError<'_>> {
    NativeArtifactKey::new(program, target)
        .map(PreparedDirectTarget::JumpCode)
        .map_err(|error| {
            DirectSelectionError::JumpCode(Box::new(
                DirectJumpCodeError::Identity(error),
            ))
        })
}

fn emit_verified_initial_halt(
    key: NativeArtifactKey,
    program: &RegionEffectProgram,
) -> VerifiedDirectSelectionResult<'_> {
    validate_initial_halt_program(program)
        .map_err(|error| DirectSelectionError::InitialHalt(Box::new(error)))?;
    validate_initial_halt_target(key.target())
        .map_err(|error| DirectSelectionError::InitialHalt(Box::new(error)))?;
    let artifact = emit_direct_initial_halt_with_key(key)
        .map_err(|error| DirectSelectionError::InitialHalt(Box::new(error)))?;
    let verified = verify_direct_initial_halt(&artifact, program)
        .map_err(|error| DirectSelectionError::InitialHalt(Box::new(error)))?;
    Ok(VerifiedDirectNativeArtifact::InitialHalt(verified))
}

fn prepare_no_operation_target(
    program: &RegionEffectProgram,
    target: NativeTargetIdentity,
) -> Result<PreparedDirectTarget, DirectSelectionError<'_>> {
    NativeArtifactKey::new(program, target)
        .map(PreparedDirectTarget::NoOperation)
        .map_err(|error| {
            DirectSelectionError::NoOperation(Box::new(
                DirectNoOperationError::Identity(error),
            ))
        })
}

fn prepare_output_target(
    program: &RegionEffectProgram,
    target: NativeTargetIdentity,
) -> Result<PreparedDirectTarget, DirectSelectionError<'_>> {
    NativeArtifactKey::new(program, target)
        .map(PreparedDirectTarget::Output)
        .map_err(|error| {
            DirectSelectionError::Output(Box::new(DirectOutputError::Identity(
                error,
            )))
        })
}

fn prepare_rotate_target(
    program: &RegionEffectProgram,
    target: NativeTargetIdentity,
) -> Result<PreparedDirectTarget, DirectSelectionError<'_>> {
    NativeArtifactKey::new(program, target)
        .map(PreparedDirectTarget::Rotate)
        .map_err(|error| {
            DirectSelectionError::Rotate(Box::new(DirectRotateError::Identity(
                error,
            )))
        })
}

fn emit_verified_crazy(
    key: NativeArtifactKey,
    program: &RegionEffectProgram,
) -> VerifiedDirectSelectionResult<'_> {
    let selected = validate_crazy_program(program)
        .map_err(|error| DirectSelectionError::Crazy(Box::new(error)))?;
    validate_crazy_target(key.target())
        .map_err(|error| DirectSelectionError::Crazy(Box::new(error)))?;
    let artifact = emit_direct_crazy_with_key(key, selected)
        .map_err(|error| DirectSelectionError::Crazy(Box::new(error)))?;
    let verified = verify_direct_crazy(&artifact, program)
        .map_err(|error| DirectSelectionError::Crazy(Box::new(error)))?;
    Ok(VerifiedDirectNativeArtifact::Crazy(verified))
}

fn emit_verified_halt_fetch(
    key: NativeArtifactKey,
    program: &RegionEffectProgram,
) -> VerifiedDirectSelectionResult<'_> {
    let selected = validate_halt_fetch_program(program)
        .map_err(|error| DirectSelectionError::HaltFetch(Box::new(error)))?;
    validate_halt_fetch_target(key.target())
        .map_err(|error| DirectSelectionError::HaltFetch(Box::new(error)))?;
    let artifact = emit_direct_halt_fetch_with_key(key, selected)
        .map_err(|error| DirectSelectionError::HaltFetch(Box::new(error)))?;
    let verified = verify_direct_halt_fetch(&artifact, program)
        .map_err(|error| DirectSelectionError::HaltFetch(Box::new(error)))?;
    Ok(VerifiedDirectNativeArtifact::HaltFetch(verified))
}

fn emit_verified_input(
    key: NativeArtifactKey,
    program: &RegionEffectProgram,
) -> VerifiedDirectSelectionResult<'_> {
    let selected = validate_input_program(program)
        .map_err(|error| DirectSelectionError::Input(Box::new(error)))?;
    validate_input_target(key.target())
        .map_err(|error| DirectSelectionError::Input(Box::new(error)))?;
    let artifact = emit_direct_input_with_key(key, selected)
        .map_err(|error| DirectSelectionError::Input(Box::new(error)))?;
    let verified = verify_direct_input(&artifact, program)
        .map_err(|error| DirectSelectionError::Input(Box::new(error)))?;
    Ok(VerifiedDirectNativeArtifact::Input(verified))
}

fn emit_verified_jump_code(
    key: NativeArtifactKey,
    program: &RegionEffectProgram,
) -> VerifiedDirectSelectionResult<'_> {
    let selected = validate_jump_code_program(program)
        .map_err(|error| DirectSelectionError::JumpCode(Box::new(error)))?;
    validate_jump_code_target(key.target())
        .map_err(|error| DirectSelectionError::JumpCode(Box::new(error)))?;
    let artifact = emit_direct_jump_code_with_key(key, selected)
        .map_err(|error| DirectSelectionError::JumpCode(Box::new(error)))?;
    let verified = verify_direct_jump_code(&artifact, program)
        .map_err(|error| DirectSelectionError::JumpCode(Box::new(error)))?;
    Ok(VerifiedDirectNativeArtifact::JumpCode(verified))
}

fn emit_verified_jump_data(
    key: NativeArtifactKey,
    program: &RegionEffectProgram,
) -> VerifiedDirectSelectionResult<'_> {
    let selected = validate_jump_data_program(program)
        .map_err(|error| DirectSelectionError::JumpData(Box::new(error)))?;
    validate_jump_data_target(key.target())
        .map_err(|error| DirectSelectionError::JumpData(Box::new(error)))?;
    let artifact = emit_direct_jump_data_with_key(key, selected)
        .map_err(|error| DirectSelectionError::JumpData(Box::new(error)))?;
    let verified = verify_direct_jump_data(&artifact, program)
        .map_err(|error| DirectSelectionError::JumpData(Box::new(error)))?;
    Ok(VerifiedDirectNativeArtifact::JumpData(verified))
}

fn emit_verified_non_graphical(
    key: NativeArtifactKey,
    program: &RegionEffectProgram,
) -> VerifiedDirectSelectionResult<'_> {
    let selected = validate_non_graphical_program(program)
        .map_err(|error| DirectSelectionError::NonGraphical(Box::new(error)))?;
    validate_non_graphical_target(key.target())
        .map_err(|error| DirectSelectionError::NonGraphical(Box::new(error)))?;
    let artifact = emit_direct_non_graphical_with_key(key, selected)
        .map_err(|error| DirectSelectionError::NonGraphical(Box::new(error)))?;
    let verified = verify_direct_non_graphical(&artifact, program)
        .map_err(|error| DirectSelectionError::NonGraphical(Box::new(error)))?;
    Ok(VerifiedDirectNativeArtifact::NonGraphical(verified))
}

fn emit_verified_output(
    key: NativeArtifactKey,
    program: &RegionEffectProgram,
) -> VerifiedDirectSelectionResult<'_> {
    let selected = validate_output_program(program)
        .map_err(|error| DirectSelectionError::Output(Box::new(error)))?;
    validate_output_target(key.target())
        .map_err(|error| DirectSelectionError::Output(Box::new(error)))?;
    let artifact = emit_direct_output_with_key(key, selected)
        .map_err(|error| DirectSelectionError::Output(Box::new(error)))?;
    let verified = verify_direct_output(&artifact, program)
        .map_err(|error| DirectSelectionError::Output(Box::new(error)))?;
    Ok(VerifiedDirectNativeArtifact::Output(verified))
}

fn emit_verified_rotate(
    key: NativeArtifactKey,
    program: &RegionEffectProgram,
) -> VerifiedDirectSelectionResult<'_> {
    let selected = validate_rotate_program(program)
        .map_err(|error| DirectSelectionError::Rotate(Box::new(error)))?;
    validate_rotate_target(key.target())
        .map_err(|error| DirectSelectionError::Rotate(Box::new(error)))?;
    let artifact = emit_direct_rotate_with_key(key, selected)
        .map_err(|error| DirectSelectionError::Rotate(Box::new(error)))?;
    let verified = verify_direct_rotate(&artifact, program)
        .map_err(|error| DirectSelectionError::Rotate(Box::new(error)))?;
    Ok(VerifiedDirectNativeArtifact::Rotate(verified))
}

fn emit_verified_no_operation(
    key: NativeArtifactKey,
    program: &RegionEffectProgram,
) -> VerifiedDirectSelectionResult<'_> {
    let selected = validate_no_operation_program(program)
        .map_err(|error| DirectSelectionError::NoOperation(Box::new(error)))?;
    validate_no_operation_target(key.target())
        .map_err(|error| DirectSelectionError::NoOperation(Box::new(error)))?;
    let artifact = emit_direct_no_operation_with_key(key, selected)
        .map_err(|error| DirectSelectionError::NoOperation(Box::new(error)))?;
    let verified = verify_direct_no_operation(&artifact, program)
        .map_err(|error| DirectSelectionError::NoOperation(Box::new(error)))?;
    Ok(VerifiedDirectNativeArtifact::NoOperation(verified))
}

/// Selects and independently verifies one reviewed explicit-geometry template.
///
/// Selection is deterministic and fail-closed. Unsupported v5 programs do not
/// receive a deoptimization artifact, because no generic v5 deoptimization
/// contract exists. Canonical profile identity is revalidated before shape
/// dispatch, while exact execution geometry remains bound by v5 artifact keys.
///
/// # Errors
///
/// Returns [`ExecutionGeometryDirectSelectionError`] when canonical profile
/// identity drifts, no reviewed one-step template admits the program, or the
/// selected emitter/verifier rejects its exact target or object bytes.
pub fn select_verified_execution_geometry_direct_native(
    program: &ExecutionGeometryRegionEffectProgram,
    host_os: HostOperatingSystem,
    host_isa: HostIsa,
) -> Result<
    VerifiedExecutionGeometryNativeArtifact,
    ExecutionGeometryDirectSelectionError,
> {
    prepare_verified_execution_geometry_direct_target(
        program, host_os, host_isa,
    )?
    .emit_verified(program)
}

pub(super) fn prepare_verified_execution_geometry_direct_target(
    program: &ExecutionGeometryRegionEffectProgram,
    host_os: HostOperatingSystem,
    host_isa: HostIsa,
) -> Result<
    PreparedExecutionGeometryDirectTarget,
    ExecutionGeometryDirectSelectionError,
> {
    validate_execution_geometry_profile(program)?;
    let kind = select_execution_geometry_kind(program)
        .ok_or(ExecutionGeometryDirectSelectionError::UnsupportedProgram)?;
    prepare_execution_geometry_kind(
        program,
        kind,
        DirectHost::new(host_os, host_isa),
    )
}

fn select_execution_geometry_kind(
    program: &ExecutionGeometryRegionEffectProgram,
) -> Option<ExecutionGeometryDirectNativeKind> {
    if validate_execution_geometry_initial_halt_program(program).is_ok() {
        return Some(ExecutionGeometryDirectNativeKind::InitialHalt);
    }
    if validate_execution_geometry_initial_jump_data_program(program).is_ok() {
        return Some(ExecutionGeometryDirectNativeKind::InitialJumpData);
    }
    if validate_execution_geometry_crazy_program(program).is_ok() {
        return Some(ExecutionGeometryDirectNativeKind::Crazy);
    }
    if validate_execution_geometry_rotate_program(program).is_ok() {
        return Some(ExecutionGeometryDirectNativeKind::Rotate);
    }
    if validate_execution_geometry_input_program(program).is_ok() {
        return Some(ExecutionGeometryDirectNativeKind::Input);
    }
    if validate_execution_geometry_jump_code_program(program).is_ok() {
        return Some(ExecutionGeometryDirectNativeKind::JumpCode);
    }
    if validate_execution_geometry_output_program(program).is_ok() {
        return Some(ExecutionGeometryDirectNativeKind::Output);
    }
    if validate_execution_geometry_no_operation_program(program).is_ok() {
        return Some(ExecutionGeometryDirectNativeKind::NoOperation);
    }
    None
}

fn prepare_execution_geometry_kind(
    program: &ExecutionGeometryRegionEffectProgram,
    kind: ExecutionGeometryDirectNativeKind,
    host: DirectHost,
) -> Result<
    PreparedExecutionGeometryDirectTarget,
    ExecutionGeometryDirectSelectionError,
> {
    let (backend_id, backend_revision) = execution_geometry_backend(kind);
    let key = NativeArtifactKey::new_execution_geometry(
        program,
        direct_target(
            backend_id,
            backend_revision,
            host.operating_system,
            host.isa,
        ),
    )
    .map_err(|error| execution_geometry_identity_error(kind, error))?;
    Ok(prepared_execution_geometry_target(kind, key))
}

const fn execution_geometry_backend(
    kind: ExecutionGeometryDirectNativeKind,
) -> (&'static str, u32) {
    match kind {
        ExecutionGeometryDirectNativeKind::Crazy => (
            DIRECT_EXECUTION_GEOMETRY_CRAZY_BACKEND_ID,
            DIRECT_EXECUTION_GEOMETRY_CRAZY_BACKEND_REVISION,
        ),
        ExecutionGeometryDirectNativeKind::InitialHalt => (
            DIRECT_EXECUTION_GEOMETRY_INITIAL_HALT_BACKEND_ID,
            DIRECT_EXECUTION_GEOMETRY_INITIAL_HALT_BACKEND_REVISION,
        ),
        ExecutionGeometryDirectNativeKind::InitialJumpData => (
            DIRECT_EXECUTION_GEOMETRY_INITIAL_JUMP_DATA_BACKEND_ID,
            DIRECT_EXECUTION_GEOMETRY_INITIAL_JUMP_DATA_BACKEND_REVISION,
        ),
        ExecutionGeometryDirectNativeKind::Input => (
            DIRECT_EXECUTION_GEOMETRY_INPUT_BACKEND_ID,
            DIRECT_EXECUTION_GEOMETRY_INPUT_BACKEND_REVISION,
        ),
        ExecutionGeometryDirectNativeKind::JumpCode => (
            DIRECT_EXECUTION_GEOMETRY_JUMP_CODE_BACKEND_ID,
            DIRECT_EXECUTION_GEOMETRY_JUMP_CODE_BACKEND_REVISION,
        ),
        ExecutionGeometryDirectNativeKind::NoOperation => (
            DIRECT_EXECUTION_GEOMETRY_NO_OPERATION_BACKEND_ID,
            DIRECT_EXECUTION_GEOMETRY_NO_OPERATION_BACKEND_REVISION,
        ),
        ExecutionGeometryDirectNativeKind::Output => (
            DIRECT_EXECUTION_GEOMETRY_OUTPUT_BACKEND_ID,
            DIRECT_EXECUTION_GEOMETRY_OUTPUT_BACKEND_REVISION,
        ),
        ExecutionGeometryDirectNativeKind::Rotate => (
            DIRECT_EXECUTION_GEOMETRY_ROTATE_BACKEND_ID,
            DIRECT_EXECUTION_GEOMETRY_ROTATE_BACKEND_REVISION,
        ),
    }
}

const fn execution_geometry_identity_error(
    kind: ExecutionGeometryDirectNativeKind,
    error: NativeIdentityError,
) -> ExecutionGeometryDirectSelectionError {
    match kind {
        ExecutionGeometryDirectNativeKind::Crazy => {
            ExecutionGeometryDirectSelectionError::Crazy(
                DirectExecutionGeometryCrazyError::Identity(error),
            )
        },
        ExecutionGeometryDirectNativeKind::InitialHalt => {
            ExecutionGeometryDirectSelectionError::InitialHalt(
                DirectExecutionGeometryInitialHaltError::Identity(error),
            )
        },
        ExecutionGeometryDirectNativeKind::InitialJumpData => {
            ExecutionGeometryDirectSelectionError::InitialJumpData(
                DirectExecutionGeometryInitialJumpDataError::Identity(error),
            )
        },
        ExecutionGeometryDirectNativeKind::Input => {
            ExecutionGeometryDirectSelectionError::Input(
                DirectExecutionGeometryInputError::Identity(error),
            )
        },
        ExecutionGeometryDirectNativeKind::JumpCode => {
            ExecutionGeometryDirectSelectionError::JumpCode(
                DirectExecutionGeometryJumpCodeError::Identity(error),
            )
        },
        ExecutionGeometryDirectNativeKind::NoOperation => {
            ExecutionGeometryDirectSelectionError::NoOperation(
                DirectExecutionGeometryNoOperationError::Identity(error),
            )
        },
        ExecutionGeometryDirectNativeKind::Output => {
            ExecutionGeometryDirectSelectionError::Output(
                DirectExecutionGeometryOutputError::Identity(error),
            )
        },
        ExecutionGeometryDirectNativeKind::Rotate => {
            ExecutionGeometryDirectSelectionError::Rotate(
                DirectExecutionGeometryRotateError::Identity(error),
            )
        },
    }
}

const fn prepared_execution_geometry_target(
    kind: ExecutionGeometryDirectNativeKind,
    key: NativeArtifactKey,
) -> PreparedExecutionGeometryDirectTarget {
    match kind {
        ExecutionGeometryDirectNativeKind::Crazy => {
            PreparedExecutionGeometryDirectTarget::Crazy(key)
        },
        ExecutionGeometryDirectNativeKind::InitialHalt => {
            PreparedExecutionGeometryDirectTarget::InitialHalt(key)
        },
        ExecutionGeometryDirectNativeKind::InitialJumpData => {
            PreparedExecutionGeometryDirectTarget::InitialJumpData(key)
        },
        ExecutionGeometryDirectNativeKind::Input => {
            PreparedExecutionGeometryDirectTarget::Input(key)
        },
        ExecutionGeometryDirectNativeKind::JumpCode => {
            PreparedExecutionGeometryDirectTarget::JumpCode(key)
        },
        ExecutionGeometryDirectNativeKind::NoOperation => {
            PreparedExecutionGeometryDirectTarget::NoOperation(key)
        },
        ExecutionGeometryDirectNativeKind::Output => {
            PreparedExecutionGeometryDirectTarget::Output(key)
        },
        ExecutionGeometryDirectNativeKind::Rotate => {
            PreparedExecutionGeometryDirectTarget::Rotate(key)
        },
    }
}

fn select_execution_geometry_crazy(
    program: &ExecutionGeometryRegionEffectProgram,
    host_os: HostOperatingSystem,
    host_isa: HostIsa,
) -> Result<
    VerifiedExecutionGeometryNativeArtifact,
    ExecutionGeometryDirectSelectionError,
> {
    let artifact = emit_direct_execution_geometry_crazy_coff(
        program,
        direct_target(
            DIRECT_EXECUTION_GEOMETRY_CRAZY_BACKEND_ID,
            DIRECT_EXECUTION_GEOMETRY_CRAZY_BACKEND_REVISION,
            host_os,
            host_isa,
        ),
    )
    .map_err(ExecutionGeometryDirectSelectionError::Crazy)?;
    verify_direct_execution_geometry_crazy(&artifact, program)
        .map(VerifiedExecutionGeometryNativeArtifact::Crazy)
        .map_err(ExecutionGeometryDirectSelectionError::Crazy)
}

fn select_execution_geometry_initial_halt(
    program: &ExecutionGeometryRegionEffectProgram,
    host_os: HostOperatingSystem,
    host_isa: HostIsa,
) -> Result<
    VerifiedExecutionGeometryNativeArtifact,
    ExecutionGeometryDirectSelectionError,
> {
    let artifact = emit_direct_execution_geometry_initial_halt_coff(
        program,
        direct_target(
            DIRECT_EXECUTION_GEOMETRY_INITIAL_HALT_BACKEND_ID,
            DIRECT_EXECUTION_GEOMETRY_INITIAL_HALT_BACKEND_REVISION,
            host_os,
            host_isa,
        ),
    )
    .map_err(ExecutionGeometryDirectSelectionError::InitialHalt)?;
    verify_direct_execution_geometry_initial_halt(&artifact, program)
        .map(VerifiedExecutionGeometryNativeArtifact::InitialHalt)
        .map_err(ExecutionGeometryDirectSelectionError::InitialHalt)
}

fn select_execution_geometry_initial_jump_data(
    program: &ExecutionGeometryRegionEffectProgram,
    host_os: HostOperatingSystem,
    host_isa: HostIsa,
) -> Result<
    VerifiedExecutionGeometryNativeArtifact,
    ExecutionGeometryDirectSelectionError,
> {
    let artifact = emit_direct_execution_geometry_initial_jump_data_coff(
        program,
        direct_target(
            DIRECT_EXECUTION_GEOMETRY_INITIAL_JUMP_DATA_BACKEND_ID,
            DIRECT_EXECUTION_GEOMETRY_INITIAL_JUMP_DATA_BACKEND_REVISION,
            host_os,
            host_isa,
        ),
    )
    .map_err(ExecutionGeometryDirectSelectionError::InitialJumpData)?;
    verify_direct_execution_geometry_initial_jump_data(&artifact, program)
        .map(VerifiedExecutionGeometryNativeArtifact::InitialJumpData)
        .map_err(ExecutionGeometryDirectSelectionError::InitialJumpData)
}

fn select_execution_geometry_input(
    program: &ExecutionGeometryRegionEffectProgram,
    host_os: HostOperatingSystem,
    host_isa: HostIsa,
) -> Result<
    VerifiedExecutionGeometryNativeArtifact,
    ExecutionGeometryDirectSelectionError,
> {
    let artifact = emit_direct_execution_geometry_input_coff(
        program,
        direct_target(
            DIRECT_EXECUTION_GEOMETRY_INPUT_BACKEND_ID,
            DIRECT_EXECUTION_GEOMETRY_INPUT_BACKEND_REVISION,
            host_os,
            host_isa,
        ),
    )
    .map_err(ExecutionGeometryDirectSelectionError::Input)?;
    verify_direct_execution_geometry_input(&artifact, program)
        .map(VerifiedExecutionGeometryNativeArtifact::Input)
        .map_err(ExecutionGeometryDirectSelectionError::Input)
}

fn select_execution_geometry_jump_code(
    program: &ExecutionGeometryRegionEffectProgram,
    host_os: HostOperatingSystem,
    host_isa: HostIsa,
) -> Result<
    VerifiedExecutionGeometryNativeArtifact,
    ExecutionGeometryDirectSelectionError,
> {
    let artifact = emit_direct_execution_geometry_jump_code_coff(
        program,
        direct_target(
            DIRECT_EXECUTION_GEOMETRY_JUMP_CODE_BACKEND_ID,
            DIRECT_EXECUTION_GEOMETRY_JUMP_CODE_BACKEND_REVISION,
            host_os,
            host_isa,
        ),
    )
    .map_err(ExecutionGeometryDirectSelectionError::JumpCode)?;
    verify_direct_execution_geometry_jump_code(&artifact, program)
        .map(VerifiedExecutionGeometryNativeArtifact::JumpCode)
        .map_err(ExecutionGeometryDirectSelectionError::JumpCode)
}

fn select_execution_geometry_no_operation(
    program: &ExecutionGeometryRegionEffectProgram,
    host_os: HostOperatingSystem,
    host_isa: HostIsa,
) -> Result<
    VerifiedExecutionGeometryNativeArtifact,
    ExecutionGeometryDirectSelectionError,
> {
    let artifact = emit_direct_execution_geometry_no_operation_coff(
        program,
        direct_target(
            DIRECT_EXECUTION_GEOMETRY_NO_OPERATION_BACKEND_ID,
            DIRECT_EXECUTION_GEOMETRY_NO_OPERATION_BACKEND_REVISION,
            host_os,
            host_isa,
        ),
    )
    .map_err(ExecutionGeometryDirectSelectionError::NoOperation)?;
    verify_direct_execution_geometry_no_operation(&artifact, program)
        .map(VerifiedExecutionGeometryNativeArtifact::NoOperation)
        .map_err(ExecutionGeometryDirectSelectionError::NoOperation)
}

fn select_execution_geometry_output(
    program: &ExecutionGeometryRegionEffectProgram,
    host_os: HostOperatingSystem,
    host_isa: HostIsa,
) -> Result<
    VerifiedExecutionGeometryNativeArtifact,
    ExecutionGeometryDirectSelectionError,
> {
    let artifact = emit_direct_execution_geometry_output_coff(
        program,
        direct_target(
            DIRECT_EXECUTION_GEOMETRY_OUTPUT_BACKEND_ID,
            DIRECT_EXECUTION_GEOMETRY_OUTPUT_BACKEND_REVISION,
            host_os,
            host_isa,
        ),
    )
    .map_err(ExecutionGeometryDirectSelectionError::Output)?;
    verify_direct_execution_geometry_output(&artifact, program)
        .map(VerifiedExecutionGeometryNativeArtifact::Output)
        .map_err(ExecutionGeometryDirectSelectionError::Output)
}

fn select_execution_geometry_rotate(
    program: &ExecutionGeometryRegionEffectProgram,
    host_os: HostOperatingSystem,
    host_isa: HostIsa,
) -> Result<
    VerifiedExecutionGeometryNativeArtifact,
    ExecutionGeometryDirectSelectionError,
> {
    let artifact = emit_direct_execution_geometry_rotate_coff(
        program,
        direct_target(
            DIRECT_EXECUTION_GEOMETRY_ROTATE_BACKEND_ID,
            DIRECT_EXECUTION_GEOMETRY_ROTATE_BACKEND_REVISION,
            host_os,
            host_isa,
        ),
    )
    .map_err(ExecutionGeometryDirectSelectionError::Rotate)?;
    verify_direct_execution_geometry_rotate(&artifact, program)
        .map(VerifiedExecutionGeometryNativeArtifact::Rotate)
        .map_err(ExecutionGeometryDirectSelectionError::Rotate)
}

fn validate_execution_geometry_profile(
    program: &ExecutionGeometryRegionEffectProgram,
) -> Result<(), ExecutionGeometryDirectSelectionError> {
    let Some(profile) = target_profile(program.profile_id()) else {
        return Err(ExecutionGeometryDirectSelectionError::ProfileIdentity);
    };
    if profile.fingerprint() != program.profile_fingerprint()
        || TargetProfileRequirement::from_descriptor(profile)
            != *program.profile_requirement()
    {
        return Err(ExecutionGeometryDirectSelectionError::ProfileIdentity);
    }
    Ok(())
}

/// Selects the narrowest semantically admitted direct native template.
///
/// Program/profile capacity and runtime preflight occur before host/backend
/// selection. Exact halt, fetched-terminal, no-op, and jump-data subsets select
/// reviewed
/// state-applying fast paths; every remaining IR selects verified
/// deoptimization. Selection never converts profile, emitter, or verifier
/// errors into fallback; only admitted program shape controls which backend
/// identity is constructed.
///
/// # Errors
///
/// Returns [`DirectSelectionError`] for unsupported program/profile/runtime,
/// host format, or any emission/verification failure after deterministic
/// template selection.
pub fn select_verified_direct_native<'requirement>(
    program: &'requirement RegionEffectProgram,
    runtime: &'static RuntimeCapability,
    host_os: HostOperatingSystem,
    host_isa: HostIsa,
) -> VerifiedDirectSelectionResult<'requirement> {
    prepare_verified_direct_target(program, runtime, host_os, host_isa)?
        .emit_verified(program)
}

pub(super) fn prepare_verified_direct_target<'requirement>(
    program: &'requirement RegionEffectProgram,
    runtime: &'static RuntimeCapability,
    host_os: HostOperatingSystem,
    host_isa: HostIsa,
) -> Result<PreparedDirectTarget, DirectSelectionError<'requirement>> {
    preflight_direct_selection(program, runtime)?;
    if host_os != HostOperatingSystem::Windows {
        return Err(DirectSelectionError::TargetFormat);
    }
    select_direct_target(program, host_os, host_isa).prepare(program)
}

/// Selects a profile-preflighted direct or interpreter execution plan.
///
/// Unsupported direct host formats are an expected capability absence and map
/// to the interpreter. Profile errors and any failure after backend selection
/// remain errors; they are never converted to interpreter fallback.
///
/// # Errors
///
/// Returns [`DirectSelectionError`] for unsupported program/profile/runtime or
/// any direct emission/admission failure other than host-format absence.
pub fn select_preflighted_execution_tier<'requirement>(
    program: &'requirement RegionEffectProgram,
    runtime: &'static RuntimeCapability,
    host_os: HostOperatingSystem,
    host_isa: HostIsa,
) -> Result<PreflightedExecutionTier, DirectSelectionError<'requirement>> {
    match select_verified_direct_native(program, runtime, host_os, host_isa) {
        Ok(artifact) => {
            Ok(PreflightedExecutionTier::Direct(Box::new(artifact)))
        },
        Err(DirectSelectionError::TargetFormat) => {
            Ok(PreflightedExecutionTier::Interpreter)
        },
        Err(error) => Err(error),
    }
}

/// Selects a cache-aware profile-preflighted direct or interpreter plan.
///
/// Profile preflight and host-format selection happen before cache lookup. Only
/// semantically admitted direct artifacts can enter the caller-owned cache.
///
/// # Errors
///
/// Returns [`DirectSelectionError`] for unsupported program/profile/runtime or
/// any direct emission/admission failure other than host-format absence.
pub fn select_cached_preflighted_execution_tier<'requirement>(
    program: &'requirement RegionEffectProgram,
    runtime: &'static RuntimeCapability,
    host: DirectHost,
    cache: &mut VerifiedDirectNativeCache,
) -> Result<CachedPreflightedExecutionTier, DirectSelectionError<'requirement>>
{
    preflight_direct_selection(program, runtime)?;
    if host.operating_system != HostOperatingSystem::Windows {
        return Ok(CachedPreflightedExecutionTier::Interpreter);
    }
    let prepared =
        select_direct_target(program, host.operating_system, host.isa)
            .prepare(program)?;
    if let Some(artifact) = cache.entries.get(prepared.key()) {
        return Ok(CachedPreflightedExecutionTier::Direct {
            artifact: Arc::clone(artifact),
            cache: DirectCacheDisposition::Hit,
        });
    }
    let artifact = Arc::new(prepared.emit_verified(program)?);
    let inserted_key = artifact.key().clone();
    let _replaced = cache.entries.insert(inserted_key, Arc::clone(&artifact));
    Ok(CachedPreflightedExecutionTier::Direct {
        artifact,
        cache: DirectCacheDisposition::Inserted,
    })
}
fn preflight_direct_selection<'requirement>(
    program: &'requirement RegionEffectProgram,
    runtime: &'static RuntimeCapability,
) -> Result<(), DirectSelectionError<'requirement>> {
    if !program
        .profile_requirement
        .is_canonical_for(&program.profile_id)
    {
        return Err(DirectSelectionError::ProfileRequirement);
    }
    preflight_portable_profile_requirement(
        &program.profile_id,
        &program.profile_requirement,
        program.required_memory_words(),
        runtime,
    )
    .map_err(|error| DirectSelectionError::Profile(Box::new(error)))
}

fn select_direct_target(
    program: &RegionEffectProgram,
    host_os: HostOperatingSystem,
    host_isa: HostIsa,
) -> SelectedDirectTarget {
    if validate_initial_halt_program(program).is_ok() {
        return SelectedDirectTarget::InitialHalt(direct_target(
            DIRECT_INITIAL_HALT_BACKEND_ID,
            DIRECT_INITIAL_HALT_BACKEND_REVISION,
            host_os,
            host_isa,
        ));
    }
    if validate_halt_registers_program(program).is_ok() {
        return SelectedDirectTarget::HaltRegisters(direct_target(
            DIRECT_HALT_REGISTERS_BACKEND_ID,
            DIRECT_HALT_REGISTERS_BACKEND_REVISION,
            host_os,
            host_isa,
        ));
    }
    if validate_halt_fetch_program(program).is_ok() {
        return SelectedDirectTarget::HaltFetch(direct_target(
            DIRECT_HALT_FETCH_BACKEND_ID,
            DIRECT_HALT_FETCH_BACKEND_REVISION,
            host_os,
            host_isa,
        ));
    }
    if validate_non_graphical_program(program).is_ok() {
        return SelectedDirectTarget::NonGraphical(direct_target(
            DIRECT_NON_GRAPHICAL_BACKEND_ID,
            DIRECT_NON_GRAPHICAL_BACKEND_REVISION,
            host_os,
            host_isa,
        ));
    }
    if validate_jump_code_program(program).is_ok() {
        return selected_jump_code_target(host_os, host_isa);
    }
    if validate_jump_data_program(program).is_ok() {
        return selected_jump_data_target(host_os, host_isa);
    }
    if validate_crazy_program(program).is_ok() {
        return selected_crazy_target(host_os, host_isa);
    }
    if validate_rotate_program(program).is_ok() {
        return selected_rotate_target(host_os, host_isa);
    }
    if validate_input_program(program).is_ok() {
        return selected_input_target(host_os, host_isa);
    }
    if validate_output_program(program).is_ok() {
        return selected_output_target(host_os, host_isa);
    }
    if validate_no_operation_program(program).is_ok() {
        return selected_no_operation_target(host_os, host_isa);
    }
    SelectedDirectTarget::Deopt(direct_target(
        DIRECT_DEOPT_BACKEND_ID,
        DIRECT_DEOPT_BACKEND_REVISION,
        host_os,
        host_isa,
    ))
}

fn selected_crazy_target(
    host_os: HostOperatingSystem,
    host_isa: HostIsa,
) -> SelectedDirectTarget {
    SelectedDirectTarget::Crazy(direct_target(
        DIRECT_CRAZY_BACKEND_ID,
        DIRECT_CRAZY_BACKEND_REVISION,
        host_os,
        host_isa,
    ))
}

fn selected_input_target(
    host_os: HostOperatingSystem,
    host_isa: HostIsa,
) -> SelectedDirectTarget {
    SelectedDirectTarget::Input(direct_target(
        DIRECT_INPUT_BACKEND_ID,
        DIRECT_INPUT_BACKEND_REVISION,
        host_os,
        host_isa,
    ))
}

fn selected_no_operation_target(
    host_os: HostOperatingSystem,
    host_isa: HostIsa,
) -> SelectedDirectTarget {
    SelectedDirectTarget::NoOperation(direct_target(
        DIRECT_NO_OPERATION_BACKEND_ID,
        DIRECT_NO_OPERATION_BACKEND_REVISION,
        host_os,
        host_isa,
    ))
}

fn selected_output_target(
    host_os: HostOperatingSystem,
    host_isa: HostIsa,
) -> SelectedDirectTarget {
    SelectedDirectTarget::Output(direct_target(
        DIRECT_OUTPUT_BACKEND_ID,
        DIRECT_OUTPUT_BACKEND_REVISION,
        host_os,
        host_isa,
    ))
}

fn selected_rotate_target(
    host_os: HostOperatingSystem,
    host_isa: HostIsa,
) -> SelectedDirectTarget {
    SelectedDirectTarget::Rotate(direct_target(
        DIRECT_ROTATE_BACKEND_ID,
        DIRECT_ROTATE_BACKEND_REVISION,
        host_os,
        host_isa,
    ))
}

fn selected_jump_data_target(
    host_os: HostOperatingSystem,
    host_isa: HostIsa,
) -> SelectedDirectTarget {
    SelectedDirectTarget::JumpData(direct_target(
        DIRECT_JUMP_DATA_BACKEND_ID,
        DIRECT_JUMP_DATA_BACKEND_REVISION,
        host_os,
        host_isa,
    ))
}

fn selected_jump_code_target(
    host_os: HostOperatingSystem,
    host_isa: HostIsa,
) -> SelectedDirectTarget {
    SelectedDirectTarget::JumpCode(direct_target(
        DIRECT_JUMP_CODE_BACKEND_ID,
        DIRECT_JUMP_CODE_BACKEND_REVISION,
        host_os,
        host_isa,
    ))
}

fn direct_target(
    backend_id: &str,
    backend_revision: u32,
    host_os: HostOperatingSystem,
    host_isa: HostIsa,
) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(backend_id),
        backend_revision,
        host_isa,
        host_os,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

pub(super) const fn target_triple(isa: HostIsa) -> &'static str {
    match isa {
        HostIsa::AArch64 => "aarch64-pc-windows-msvc",
        HostIsa::X86_64 => "x86_64-pc-windows-msvc",
    }
}
