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
//   - Public classic and profile-driven Malbolge execution semantics.
// - Must-Not:
//   - Encode JIT, accelerator, compiler, or implicit historical behavior.
// - Allows:
//   - Inputs: canonical profiles, validated source, machine state, byte input.
//   - Outputs: deterministic classic/profiled transitions, I/O, diagnostics.
//   - Side effects: none outside caller-owned in-memory VM state.
// - Split-When:
//   - Split when another machine profile requires an independent semantic API.
// - Merge-When:
//   - Merge when another VM module owns the same classic transition boundary.
// - Summary:
//   - Safe-Rust classic and schema-v2 profile-driven Malbolge interpreters.
// - Description:
//   - Keeps classic type safety while admitting explicit scalable profiles.
// - Usage:
//   - Used by interpreters, verification, compiler tests, and future executors.
// - Defaults:
//   - `Machine` stays classic; `ProfileMachine` requires explicit profile.
//

//! Safe deterministic classic and profile-driven Malbolge interpreters.

#[path = "../domain/annotated.rs"]
mod annotated;
mod batch;
#[path = "../domain/capsule.rs"]
mod capsule;
#[path = "../domain/execution.rs"]
mod execution;
#[path = "../domain/loader.rs"]
mod loader;
#[path = "../domain/logical.rs"]
mod logical;
#[path = "../domain/machine.rs"]
mod machine;
#[path = "../domain/memory.rs"]
mod memory;
#[path = "../domain/mode.rs"]
mod mode;
#[path = "../domain/profile.rs"]
mod profile;
#[path = "../domain/profile_arithmetic.rs"]
pub mod profile_arithmetic;
#[path = "../domain/profile_machine.rs"]
mod profile_machine;
#[path = "../domain/profile_trace.rs"]
mod profile_trace;
#[path = "../domain/trace.rs"]
mod trace;
#[path = "../contract/word.rs"]
mod word;

pub use annotated::{
    AnnotatedLoadError, AnnotatedSourceError, AnnotatedSourceLocation,
    CanonicalizedAnnotatedSource, canonicalize_annotated_source,
    format_annotated_source,
};
pub use batch::{
    BatchBackendCompletion, BatchBackendRequest, BatchError,
    BatchExecutionBackend, BatchExecutionOrigin, BatchExecutionReport,
    BatchRequest, BatchResult, ProfileBatchBackendCompletion,
    ProfileBatchBackendRequest, ProfileBatchExecutionBackend,
    ProfileBatchRequest, ProfileBatchResult, execute_batch,
    execute_batch_parallel, execute_batch_with_backend,
    execute_batch_with_backend_report, execute_profile_batch,
    execute_profile_batch_parallel, execute_profile_batch_with_backend,
    execute_profile_batch_with_backend_report,
};
pub use capsule::{
    Capsule, CapsuleBuildError, CapsuleError, build_capsule, parse_capsule,
};
pub use execution::{ExecutionError, ExecutionErrorKind, ExecutionMachine};
pub use loader::{LoadError, load};
pub use logical::{
    LogicalConcurrencyError, LogicalJoinError, LogicalTask, LogicalTaskId,
    LogicalTaskResult, ProfileLogicalJoinError, ProfileLogicalTask,
    ProfileLogicalTaskResult, execute_logical_tasks,
    execute_logical_tasks_parallel, execute_profile_logical_tasks,
    execute_profile_logical_tasks_parallel, join_logical_outputs,
    join_profile_logical_outputs,
};
pub use machine::{
    LegacyBehavior, Machine, MachineError, MachineIoState, MachineState,
    MachineStateError, Registers, RunOutcome, StepOutcome, Termination,
};
pub use memory::{Memory, MemoryError};
pub use mode::{ExecutionMode, ExecutionModeParseError};
pub use profile::{
    PortableProfileRequirementError, ProfileDescriptor, ProfileFeature,
    ProfileKind, ProfileRequirementError, ProfileRequirementErrorKind,
    RuntimeCapability, RuntimeProfileRequirementError,
    TargetProfileRequirement, current_profile, historical_profile,
    preflight_portable_profile_requirement, preflight_profile,
    preflight_runtime_requirement, safe_rust_classic_capability,
    safe_rust_profiled_capability, target_profile,
};
pub use profile_arithmetic::{
    profile_crazy, profile_eof_word, profile_low_byte,
};
pub use profile_machine::{
    ProfileLoadError, ProfileMachine, ProfileMachineError,
    ProfileMachineIoState, ProfileMachineState, ProfileRegisterName,
    ProfileRegisters, decode_profile_instruction, encrypt_profile_cell,
    profile_cell_decodes_to_no_operation, profile_cell_is_graphical,
    profile_pointer_successor, profile_rotate,
};
pub use profile_trace::{
    ProfileMachineObservation, ProfileMemoryDelta, ProfileMemoryRead,
    ProfileMemoryReads, ProfileMemoryWrite, ProfileStepTrace,
};
pub use trace::{
    MachineObservation, MemoryDelta, MemoryWrite, StepTrace, TraceInput,
};
pub use word::{MAX_WORD_VALUE, MEMORY_WORDS, Word, WordError};
const CRAZY_CHUNK_TRITS: u8 = 5;
const CRAZY_CHUNK_VALUES: u16 = 243;
const GRAPHICAL_START: u16 = 33;
const XLAT2: &[u8; 94] = b"5z]&gqtyfr$(we4{WP)H-Zn,[%\\3dL+Q;>U!pJS72FhOA1C\
B6v^=I_0/8|jsb9m<.TVac`uY*MK'X~xDl}REokN:#?G\"i@";

const DECODE_TABLE_LEN: usize = 94;
include!(concat!(env!("OUT_DIR"), "/classic_decode_tables.rs"));
include!(concat!(env!("OUT_DIR"), "/ternary_tables.rs"));

fn crazy_chunk_lookup(data: u16, accumulator: u16) -> u16 {
    let index = usize::from(data)
        .saturating_mul(usize::from(CRAZY_CHUNK_VALUES))
        .saturating_add(usize::from(accumulator));
    CRAZY_CHUNK_TABLE
        .get(index)
        .copied()
        .unwrap_or_else(|| crazy_chunk_scalar(data, accumulator))
}

const fn crazy_chunk_scalar(data: u16, accumulator: u16) -> u16 {
    let mut remaining_data = data;
    let mut remaining_accumulator = accumulator;
    let mut result = 0u16;
    let mut place = 1u16;
    let mut trit = 0u8;
    while trit < CRAZY_CHUNK_TRITS {
        let output = crazy_trit(
            remaining_data.rem_euclid(3),
            remaining_accumulator.rem_euclid(3),
        );
        result = result.saturating_add(output.saturating_mul(place));
        place = place.saturating_mul(3);
        remaining_data = remaining_data.div_euclid(3);
        remaining_accumulator = remaining_accumulator.div_euclid(3);
        trit = trit.saturating_add(1);
    }
    result
}

const fn crazy_trit(data: u16, accumulator: u16) -> u16 {
    if ((data == 0 || data == 1) && accumulator == 0)
        || (data == 2 && accumulator == 2)
    {
        1
    } else if (data == 1 && accumulator == 2)
        || (data == 2 && (accumulator == 0 || accumulator == 1))
    {
        2
    } else {
        0
    }
}

/// Decodes one instruction cell at its exact code-pointer position.
///
/// Returns `None` when `cell` is outside graphical ASCII. Graphical cells use
/// the normative position-dependent Malbolge translation table.
#[must_use]
pub fn decode_instruction(cell: Word, code_pointer: Word) -> Option<u8> {
    if !cell.is_graphical() {
        return None;
    }
    let phase = CODE_PHASE.get(usize::from(code_pointer.value())).copied()?;
    let cell_offset = usize::from(cell.value().saturating_sub(GRAPHICAL_START));
    let index = cell_offset
        .saturating_mul(DECODE_TABLE_LEN)
        .saturating_add(usize::from(phase));
    DECODE_TABLE.get(index).copied()
}

fn encrypt(cell: Word) -> Option<Word> {
    let index = usize::from(cell.value().saturating_sub(GRAPHICAL_START));
    XLAT2.get(index).copied().map(Word::from_byte)
}
