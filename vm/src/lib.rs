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
//   - Encode JIT, accelerator, compiler, or historical C defect behavior.
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
//   - Implements normative 1998 semantics rather than historical C defects.
//
// Related documents:
// - docs/technical/specification/malbolge-1998.md
// - docs/technical/runtime/vm/safe-rust-malbolge-vm.md
//
// Large file:
//   - false
//

//! Safe deterministic implementation of the classic Malbolge virtual machine.

mod loader;
mod machine;
mod memory;
mod trace;
mod word;

pub use loader::{LoadError, load};
pub use machine::{
    Machine, MachineError, Registers, RunOutcome, StepOutcome, Termination,
};
pub use memory::{Memory, MemoryError};
pub use trace::{MachineObservation, StepTrace, TraceInput};
pub use word::{MAX_WORD_VALUE, MEMORY_WORDS, Word, WordError};
const GRAPHICAL_START: u16 = 33;
const TABLE_LEN: usize = 94;
const XLAT1: &[u8; 94] = b"+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA\"lI\
.v%{gJh4G\\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha";
const XLAT2: &[u8; 94] = b"5z]&gqtyfr$(we4{WP)H-Zn,[%\\3dL+Q;>U!pJS72FhOA1C\
B6v^=I_0/8|jsb9m<.TVac`uY*MK'X~xDl}REokN:#?G\"i@";

fn decode(cell: Word, code_pointer: Word) -> Option<u8> {
    let cell_offset = cell.value().saturating_sub(GRAPHICAL_START);
    let combined = usize::from(cell_offset)
        .saturating_add(usize::from(code_pointer.value()));
    XLAT1.get(combined.rem_euclid(TABLE_LEN)).copied()
}

fn encrypt(cell: Word) -> Option<Word> {
    let index = usize::from(cell.value().saturating_sub(GRAPHICAL_START));
    XLAT2.get(index).copied().map(Word::from_byte)
}
