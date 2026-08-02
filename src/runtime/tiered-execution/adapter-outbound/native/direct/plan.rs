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
    JumpCode(NativeTargetIdentity),
    JumpData(NativeTargetIdentity),
    NoOperation(NativeTargetIdentity),
    NonGraphical(NativeTargetIdentity),
    Rotate(NativeTargetIdentity),
}

#[derive(Clone, Debug, Eq, PartialEq)]
enum PreparedDirectTarget {
    Crazy(NativeArtifactKey),
    Deopt(NativeArtifactKey),
    HaltFetch(NativeArtifactKey),
    HaltRegisters(NativeArtifactKey),
    InitialHalt(NativeArtifactKey),
    JumpCode(NativeArtifactKey),
    JumpData(NativeArtifactKey),
    NoOperation(NativeArtifactKey),
    NonGraphical(NativeArtifactKey),
    Rotate(NativeArtifactKey),
}

type VerifiedDirectSelectionResult<'requirement> =
    Result<VerifiedDirectNativeArtifact, DirectSelectionError<'requirement>>;

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

impl PreparedDirectTarget {
    fn emit_verified(
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
            Self::JumpCode(key) => emit_verified_jump_code(key, program),
            Self::JumpData(key) => emit_verified_jump_data(key, program),
            Self::NonGraphical(key) => {
                emit_verified_non_graphical(key, program)
            },
            Self::NoOperation(key) => emit_verified_no_operation(key, program),
            Self::Rotate(key) => emit_verified_rotate(key, program),
        }
    }

    const fn key(&self) -> &NativeArtifactKey {
        match self {
            Self::Crazy(key)
            | Self::Deopt(key)
            | Self::HaltFetch(key)
            | Self::HaltRegisters(key)
            | Self::InitialHalt(key)
            | Self::JumpCode(key)
            | Self::JumpData(key)
            | Self::NonGraphical(key)
            | Self::NoOperation(key)
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
    preflight_direct_selection(program, runtime)?;
    if host_os != HostOperatingSystem::Windows {
        return Err(DirectSelectionError::TargetFormat);
    }
    select_direct_target(program, host_os, host_isa)
        .prepare(program)?
        .emit_verified(program)
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
    if validate_no_operation_program(program).is_ok() {
        return SelectedDirectTarget::NoOperation(direct_target(
            DIRECT_NO_OPERATION_BACKEND_ID,
            DIRECT_NO_OPERATION_BACKEND_REVISION,
            host_os,
            host_isa,
        ));
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
