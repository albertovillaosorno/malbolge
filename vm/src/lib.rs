// File:
//   - lib.rs
// Path:
//   - vm/src/lib.rs
//
// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE
// Path-Rule:
//   - All paths in this header are repository-root relative.
//
// Boundary-Contract:
// - Owns:
//   - Public classic Malbolge VM semantics and deterministic execution API.
// - Must-Not:
//   - Encode JIT, accelerator, compiler, or implicit historical behavior.
// - Allows:
//   - Inputs: validated source bytes, classic words, memory, and byte input.
//   - Outputs: deterministic state transitions, byte output, and diagnostics.
//   - Side effects: none outside caller-owned in-memory VM state.
// - Split-When:
//   - Split when another machine profile requires an independent semantic API.
// - Merge-When:
//   - Merge when another VM module owns the same classic transition boundary.
// - Summary:
//   - Exact safe-Rust implementation of the normative classic Malbolge machine.
// - Description:
//   - Exposes words, loading, memory, and single-step execution as one VM API.
// - Usage:
//   - Used by interpreters, verification, compiler tests, and future executors.
// - Defaults:
//   - `Machine` is normative; legacy behavior requires explicit opt-in.
//
// Related documents:
// - docs/technical/specification/malbolge-1998.md
// - docs/technical/runtime/vm/safe-rust-malbolge-vm.md
//
// Large file:
//   - false
//

//! Safe deterministic implementation of the classic Malbolge virtual machine.

mod batch;
mod capsule;
mod execution;
mod loader;
mod logical;
mod machine;
mod memory;
mod mode;
mod profile;
mod trace;
mod word;

pub use batch::{
    BatchError, BatchRequest, BatchResult, execute_batch,
    execute_batch_parallel,
};
pub use capsule::{
    Capsule, CapsuleBuildError, CapsuleError, build_capsule, parse_capsule,
};
pub use execution::{ExecutionError, ExecutionErrorKind, ExecutionMachine};
pub use loader::{LoadError, load};
pub use logical::{
    LogicalConcurrencyError, LogicalJoinError, LogicalTask, LogicalTaskId,
    LogicalTaskResult, execute_logical_tasks, execute_logical_tasks_parallel,
    join_logical_outputs,
};
pub use machine::{
    LegacyBehavior, Machine, MachineError, Registers, RunOutcome, StepOutcome,
    Termination,
};
pub use memory::{Memory, MemoryError};
pub use mode::{ExecutionMode, ExecutionModeParseError};
pub use profile::{
    ProfileDescriptor, ProfileFeature, ProfileKind, ProfileRequirementError,
    ProfileRequirementErrorKind, RuntimeCapability, current_profile,
    historical_profile, preflight_profile, safe_rust_classic_capability,
    target_profile,
};
pub use trace::{MachineObservation, StepTrace, TraceInput};
pub use word::{MAX_WORD_VALUE, MEMORY_WORDS, Word, WordError};
const GRAPHICAL_START: u16 = 33;
const XLAT2: &[u8; 94] = b"5z]&gqtyfr$(we4{WP)H-Zn,[%\\3dL+Q;>U!pJS72FhOA1C\
B6v^=I_0/8|jsb9m<.TVac`uY*MK'X~xDl}REokN:#?G\"i@";

const DECODE_TABLE_LEN: usize = 94;
include!(concat!(env!("OUT_DIR"), "/classic_decode_tables.rs"));

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
