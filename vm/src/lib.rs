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
mod execution;
mod loader;
mod machine;
mod memory;
mod mode;
mod trace;
mod word;

pub use batch::{
    BatchError, BatchRequest, BatchResult, execute_batch,
    execute_batch_parallel,
};
pub use execution::{ExecutionError, ExecutionErrorKind, ExecutionMachine};
pub use loader::{LoadError, load};
pub use machine::{
    LegacyBehavior, Machine, MachineError, Registers, RunOutcome, StepOutcome,
    Termination,
};
pub use memory::{Memory, MemoryError};
pub use mode::{ExecutionMode, ExecutionModeParseError};
pub use trace::{MachineObservation, StepTrace, TraceInput};
pub use word::{MAX_WORD_VALUE, MEMORY_WORDS, Word, WordError};
const GRAPHICAL_START: u16 = 33;
const XLAT2: &[u8; 94] = b"5z]&gqtyfr$(we4{WP)H-Zn,[%\\3dL+Q;>U!pJS72FhOA1C\
B6v^=I_0/8|jsb9m<.TVac`uY*MK'X~xDl}REokN:#?G\"i@";

const DECODE_TABLE_LEN: usize = 94;
include!(concat!(env!("OUT_DIR"), "/classic_decode_tables.rs"));

fn decode(cell: Word, code_pointer: Word) -> Option<u8> {
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

#[cfg(test)]
mod tests {
    use super::{DECODE_TABLE_LEN, GRAPHICAL_START, decode};
    use crate::{MAX_WORD_VALUE, Word};

    const TEST_XLAT1: &[u8; DECODE_TABLE_LEN] =
        b"+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA\"lI\
.v%{gJh4G\\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha";

    fn check_decode(cell: Word, code_pointer: Word) -> Result<(), String> {
        let cell_offset =
            usize::from(cell.value().saturating_sub(GRAPHICAL_START));
        let combined =
            cell_offset.saturating_add(usize::from(code_pointer.value()));
        let translation_index = combined.rem_euclid(DECODE_TABLE_LEN);
        let expected = TEST_XLAT1
            .get(translation_index)
            .copied()
            .ok_or_else(|| "scalar decode index escaped XLAT1".to_owned())?;
        let observed = decode(cell, code_pointer).ok_or_else(|| {
            "optimized decode rejected graphical cell".to_owned()
        })?;
        if observed == expected {
            Ok(())
        } else {
            let pointer = code_pointer.value();
            let cell_value = cell.value();
            let location =
                format!("decode mismatch: C={pointer}, cell={cell_value}");
            Err(format!(
                "{location}: expected={expected}, observed={observed}"
            ))
        }
    }

    #[test]
    fn decode_table_matches_scalar_definition() -> Result<(), String> {
        let mut pointer_raw = 0u16;
        loop {
            let code_pointer =
                Word::new(pointer_raw).map_err(|error| format!("{error}"))?;
            let mut cell_raw = GRAPHICAL_START;
            while cell_raw <= 126 {
                let cell =
                    Word::new(cell_raw).map_err(|error| format!("{error}"))?;
                check_decode(cell, code_pointer)?;
                cell_raw = cell_raw.saturating_add(1);
            }
            if pointer_raw == MAX_WORD_VALUE {
                break;
            }
            pointer_raw = pointer_raw.saturating_add(1);
        }
        Ok(())
    }
}
