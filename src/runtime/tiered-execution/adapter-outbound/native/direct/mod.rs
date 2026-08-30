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
//   - Canonical reviewed direct objects and byte-exact semantic admission.
// - Must-Not:
//   - Lower unsupported effects, bypass verifier guards, or trust compiler
//   - output.
// - Allows:
//   - Inputs: portable region IR, explicit runtime capability, and exact
//   - Windows native target identity.
//   - Outputs: profile-bound COFF candidates and verified direct artifacts.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - Split when general region-effect instruction selection outgrows
//   - templates.
// - Merge-When:
//   - Merge when all direct emitters share one reviewed instruction template.
// - Summary:
//   - Owns byte-canonical deopt and reviewed direct native templates.
// - Description:
//   - Emits reviewed x86-64/AArch64 objects for exact verified IR subsets.
// - Usage:
//   - Provides a safe deopt floor plus reviewed exact direct fast paths.
// - Defaults:
//   - Unsupported IR is rejected; no direct template is selected implicitly.
//

//! Canonical direct native templates with byte-exact semantic verification.

mod artifact;
mod coff;
mod emit;
mod error;
mod plan;
mod sequence;
mod shape;
mod verify;

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::sync::Arc;

pub use artifact::*;
use coff::*;
pub use emit::{
    emit_direct_crazy_coff, emit_direct_deopt_coff,
    emit_direct_execution_geometry_initial_halt_coff,
    emit_direct_execution_geometry_no_operation_coff,
    emit_direct_execution_geometry_rotate_coff, emit_direct_halt_fetch_coff,
    emit_direct_halt_registers_coff, emit_direct_initial_halt_coff,
    emit_direct_input_coff, emit_direct_jump_code_coff,
    emit_direct_jump_data_coff, emit_direct_no_operation_coff,
    emit_direct_non_graphical_coff, emit_direct_output_coff,
    emit_direct_rotate_coff,
};
use emit::{
    emit_direct_crazy_with_key, emit_direct_deopt_with_key,
    emit_direct_halt_fetch_with_key, emit_direct_halt_registers_with_key,
    emit_direct_initial_halt_with_key, emit_direct_input_with_key,
    emit_direct_jump_code_with_key, emit_direct_jump_data_with_key,
    emit_direct_no_operation_with_key, emit_direct_non_graphical_with_key,
    emit_direct_output_with_key, emit_direct_rotate_with_key,
};
pub use error::*;
use malbolge::{
    EFFECT_IR_EXECUTION_GEOMETRY_VERSION, EffectOp,
    ExecutionGeometryRegionEffectProgram, MemoryLiveIn,
    PortableProfileRequirementError, ProfileMachineObservation,
    ProfileMemoryDelta, ProfileMemoryWrite, ProfileRegisters,
    RegionEffectProgram, RunOutcome, RuntimeCapability, Termination,
    TraceInput, decode_profile_instruction, encrypt_profile_cell,
    is_canonical_effect_ir_version, preflight_portable_profile_requirement,
    profile_cell_decodes_to_no_operation, profile_cell_is_graphical,
    profile_crazy, profile_eof_word, profile_low_byte,
    profile_pointer_successor, profile_rotate, target_profile,
};
use plan::target_triple;
pub use plan::{
    select_cached_preflighted_execution_tier,
    select_preflighted_execution_tier, select_verified_direct_native,
};
pub use sequence::*;
use shape::*;
pub use verify::{
    verify_direct_crazy, verify_direct_deopt_stub,
    verify_direct_execution_geometry_initial_halt,
    verify_direct_execution_geometry_no_operation,
    verify_direct_execution_geometry_rotate, verify_direct_halt_fetch,
    verify_direct_halt_registers, verify_direct_initial_halt,
    verify_direct_input, verify_direct_jump_code, verify_direct_jump_data,
    verify_direct_no_operation, verify_direct_non_graphical,
    verify_direct_output, verify_direct_rotate,
};

use super::profile_metadata::canonical_profile_metadata;
use super::{
    CoffAdmissionError, NATIVE_REGION_ABI_REVISION,
    StructurallyAdmittedNativeObjectArtifact, UntrustedNativeObjectArtifact,
    aarch64, structurally_admit_coff, x86_64,
};
use crate::execution_cache::{
    HostIsa, HostOperatingSystem, NativeArtifactCache, NativeArtifactKey,
    NativeIdentityError, NativeTargetConfig, NativeTargetIdentity,
    RegionEffectIdentity,
};

const COFF_HEADER_BYTES: usize = 20;
const COFF_SECTION_BYTES: usize = 40;
const COFF_SYMBOL_BYTES: usize = 18;
const IMAGE_FILE_MACHINE_AMD64: u16 = 0x8664;
const IMAGE_FILE_MACHINE_ARM64: u16 = 0xaa64;
const IMAGE_SCN_X86_TEXT: u32 = 0x6050_0020;
const IMAGE_SCN_ARM64_TEXT: u32 = 0x6030_0020;
const IMAGE_SCN_PROFILE_METADATA: u32 = 0x4030_0040;
const IMAGE_SYM_CLASS_EXTERNAL: u8 = 2;
const IMAGE_SYM_DTYPE_FUNCTION: u16 = 0x0020;
const REQUIRED_ENTRY: &str = "malbolge_native_region_apply";

/// Backend identity for the first direct, semantically admitted native tier.
pub const DIRECT_DEOPT_BACKEND_ID: &str = "direct-deopt-stub";
/// Direct deoptimization-stub code-generation revision.
pub const DIRECT_DEOPT_BACKEND_REVISION: u32 = 4;
/// Backend identity for guarded explicit-geometry initial halt.
pub const DIRECT_EXECUTION_GEOMETRY_INITIAL_HALT_BACKEND_ID: &str =
    "direct-execution-geometry-initial-halt";
/// Guarded explicit-geometry initial-halt code-generation revision.
pub const DIRECT_EXECUTION_GEOMETRY_INITIAL_HALT_BACKEND_REVISION: u32 = 1;
/// Backend identity for explicit-geometry one-step no-operation.
pub const DIRECT_EXECUTION_GEOMETRY_NO_OPERATION_BACKEND_ID: &str =
    "direct-execution-geometry-no-operation";
/// Explicit-geometry no-operation code-generation revision.
pub const DIRECT_EXECUTION_GEOMETRY_NO_OPERATION_BACKEND_REVISION: u32 = 1;
/// Backend identity for explicit-geometry one-step rotate.
pub const DIRECT_EXECUTION_GEOMETRY_ROTATE_BACKEND_ID: &str =
    "direct-execution-geometry-rotate";
/// Explicit-geometry rotate code-generation revision.
pub const DIRECT_EXECUTION_GEOMETRY_ROTATE_BACKEND_REVISION: u32 = 1;
/// Backend identity for the first state-applying direct native fast path.
pub const DIRECT_INITIAL_HALT_BACKEND_ID: &str = "direct-initial-halt";
/// Direct initial-halt code-generation revision.
pub const DIRECT_INITIAL_HALT_BACKEND_REVISION: u32 = 4;
/// Backend identity for exact-observation one-step direct halt.
pub const DIRECT_HALT_REGISTERS_BACKEND_ID: &str = "direct-halt-registers";
/// Direct exact-observation halt code-generation revision.
pub const DIRECT_HALT_REGISTERS_BACKEND_REVISION: u32 = 5;

/// Backend identity for exact graphical halt fetch termination.
pub const DIRECT_HALT_FETCH_BACKEND_ID: &str = "direct-halt-fetch";
/// Direct graphical halt-fetch code-generation revision.
pub const DIRECT_HALT_FETCH_BACKEND_REVISION: u32 = 2;

/// Backend identity for exact non-graphical fetch termination.
pub const DIRECT_NON_GRAPHICAL_BACKEND_ID: &str = "direct-non-graphical";
/// Direct non-graphical termination code-generation revision.
pub const DIRECT_NON_GRAPHICAL_BACKEND_REVISION: u32 = 2;

/// Backend identity for exact one-step no-operation execution.
pub const DIRECT_NO_OPERATION_BACKEND_ID: &str = "direct-no-operation";
/// Direct no-operation code-generation revision.
pub const DIRECT_NO_OPERATION_BACKEND_REVISION: u32 = 2;

/// Backend identity for exact non-aliasing one-step jump-data execution.
pub const DIRECT_JUMP_DATA_BACKEND_ID: &str = "direct-jump-data";
/// Direct jump-data code-generation revision.
pub const DIRECT_JUMP_DATA_BACKEND_REVISION: u32 = 1;

/// Backend identity for exact non-aliasing one-step jump-code execution.
pub const DIRECT_JUMP_CODE_BACKEND_ID: &str = "direct-jump-code";
/// Direct jump-code code-generation revision.
pub const DIRECT_JUMP_CODE_BACKEND_REVISION: u32 = 1;

/// Backend identity for exact non-aliasing one-step crazy execution.
pub const DIRECT_CRAZY_BACKEND_ID: &str = "direct-crazy";
/// Direct crazy code-generation revision.
pub const DIRECT_CRAZY_BACKEND_REVISION: u32 = 1;

/// Backend identity for exact non-aliasing one-step rotate execution.
pub const DIRECT_ROTATE_BACKEND_ID: &str = "direct-rotate";
/// Direct rotate code-generation revision.
pub const DIRECT_ROTATE_BACKEND_REVISION: u32 = 1;

/// Backend identity for exact one-step output execution.
pub const DIRECT_OUTPUT_BACKEND_ID: &str = "direct-output";
/// Direct output code-generation revision.
pub const DIRECT_OUTPUT_BACKEND_REVISION: u32 = 1;

/// Backend identity for exact one-step input execution.
pub const DIRECT_INPUT_BACKEND_ID: &str = "direct-input";
/// Direct input code-generation revision.
pub const DIRECT_INPUT_BACKEND_REVISION: u32 = 1;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) struct DirectEntryObservation {
    pub(super) accumulator: u32,
    pub(super) code_pointer: u32,
    pub(super) data_pointer: u32,
    pub(super) input_consumed: u64,
    pub(super) output_len: u64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) struct DirectCodeWriteCommit {
    pub(super) encrypted_address: u32,
    pub(super) encrypted_value: u32,
    pub(super) next_code_pointer: u32,
    pub(super) next_data_pointer: u32,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) struct DirectFetchedCellGuard {
    pub(super) live_in_value: u32,
    pub(super) required_memory_words: u64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) struct DirectJumpDataGuard {
    pub(super) code_live_in: u32,
    pub(super) data_live_in: u32,
    pub(super) required_memory_words: u64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) struct DirectJumpCodeGuard {
    pub(super) code_live_in: u32,
    pub(super) data_live_in: u32,
    pub(super) encryption_live_in: u32,
    pub(super) required_memory_words: u64,
}

pub(super) type DirectCrazyGuard = DirectRotateGuard;
pub(super) type DirectCrazyCommit = DirectRotateCommit;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) struct DirectRotateGuard {
    pub(super) code_live_in: u32,
    pub(super) data_live_in: u32,
    pub(super) required_memory_words: u64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) struct DirectInputGuard {
    pub(super) code_live_in: u32,
    pub(super) input: TraceInput,
    pub(super) input_index: u64,
    pub(super) required_memory_words: u64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) struct DirectInputCommit {
    pub(super) accumulator: u32,
    pub(super) encrypted_address: u32,
    pub(super) encrypted_value: u32,
    pub(super) next_code_pointer: u32,
    pub(super) next_data_pointer: u32,
    pub(super) next_input_consumed: u64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) struct DirectOutputCommit {
    pub(super) encrypted_address: u32,
    pub(super) encrypted_value: u32,
    pub(super) next_code_pointer: u32,
    pub(super) next_data_pointer: u32,
    pub(super) next_output_len: u64,
    pub(super) output_byte: u8,
    pub(super) output_index: u64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) struct DirectRotateCommit {
    pub(super) accumulator: u32,
    pub(super) data_address: u32,
    pub(super) data_value: u32,
    pub(super) encrypted_address: u32,
    pub(super) encrypted_value: u32,
    pub(super) next_code_pointer: u32,
    pub(super) next_data_pointer: u32,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct DirectFetchedTerminalProgram {
    live_in: MemoryLiveIn,
    observation: ProfileMachineObservation,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct DirectNoOperationProgram {
    encrypted_value: u32,
    live_in: MemoryLiveIn,
    next_code_pointer: u32,
    next_data_pointer: u32,
    observation: ProfileMachineObservation,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct DirectJumpDataProgram {
    code_live_in: MemoryLiveIn,
    commit: DirectCodeWriteCommit,
    data_live_in: MemoryLiveIn,
    observation: ProfileMachineObservation,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct DirectJumpCodeProgram {
    code_live_in: MemoryLiveIn,
    commit: DirectCodeWriteCommit,
    data_live_in: MemoryLiveIn,
    encryption_live_in: MemoryLiveIn,
    observation: ProfileMachineObservation,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct DirectJumpCodeLiveIns {
    code: MemoryLiveIn,
    data: MemoryLiveIn,
    encryption: MemoryLiveIn,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct DirectCrazyProgram {
    code_live_in: MemoryLiveIn,
    commit: DirectCrazyCommit,
    data_live_in: MemoryLiveIn,
    observation: ProfileMachineObservation,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct DirectInputProgram {
    commit: DirectInputCommit,
    input: TraceInput,
    live_in: MemoryLiveIn,
    observation: ProfileMachineObservation,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct DirectOutputProgram {
    commit: DirectOutputCommit,
    live_in: MemoryLiveIn,
    observation: ProfileMachineObservation,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct DirectRotateProgram {
    code_live_in: MemoryLiveIn,
    commit: DirectRotateCommit,
    data_live_in: MemoryLiveIn,
    observation: ProfileMachineObservation,
}
