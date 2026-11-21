// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Real VM evidence for source-authenticated input-result frame writes.
// - Must-Not:
//   - Equate a completed input store with C arithmetic, phi or branch linkage.
// - Allows:
//   - Inputs: validated source-input anchors and exact physical VM bytes.
//   - Outputs: actual C32/byte word-store moments with trace provenance.
//   - Side effects: bounded, isolated current-profile VM replay only.
// - Split-When:
//   - Complete source operation and guest dataflow verification subsumes it.
// - Merge-When:
//   - A physically linked C23 checksum backend verifies all its state writes.
// - Summary:
//   - Refuses input-only guest programs that never store their C result.

//! Physical guest-state write evidence for source-typed input destinations.
//!
//! An input opcode only changes A. This independent opt-in gate requires
//! subsequent real rotate/crazy data writes to materialize the exact signed
//! C23 or byte input result in every source-reserved guest frame cell.
//! Matching the result once is necessary, not sufficient: later guest code
//! can clobber the cells, and unrelated C operations remain unchecked.

use std::collections::BTreeMap;

use malbolge::{ProfileMachine, ProfileStepTrace, TraceInput, current_profile};

use super::source_input_trace::{
    SourceInputPrefixProof, SourceInputProbe, SourceInputSiteObservation,
    SourceInputTraceError, verify_source_input_site_return_compatible,
};
use super::typed_cfg_adapter::state_relocation::GuestCodeInputSemantics;
use super::typed_cfg_adapter::state_storage::encode_i32_cells;

struct PendingInputStore {
    completed: Option<SourceInputStoreObservation>,
    expected: Vec<u32>,
    input: SourceInputSiteObservation,
    writes: Vec<Option<usize>>,
}

/// One actual guest data write that completed a source input word.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SourceInputStoreCell {
    /// Exact absolute source-reserved guest word.
    pub address: u32,
    /// Zero-based physical VM step that wrote this cell.
    pub trace_index: usize,
    /// Exact VM-observed word, not a host-simulated write.
    pub value: u32,
}

/// A full source-typed result was physically present after guest data writes.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SourceInputStoreObservation {
    /// One cell for a byte, two for the full-width signed C23 value.
    pub cells: Vec<SourceInputStoreCell>,
    /// Authenticated input effect whose SSA result became materialized.
    pub input: SourceInputSiteObservation,
}

/// Bounded physical input/return evidence and exact state-write moments.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SourceInputStoredProof {
    /// The independently accepted actual VM input/return path.
    pub prefix: SourceInputPrefixProof,
    /// One completed word-store observation per physical input event.
    pub stores: Vec<SourceInputStoreObservation>,
}

struct StoreTracker {
    error: Option<SourceInputTraceError>,
    next_input: usize,
    pending: Vec<PendingInputStore>,
    trace_index: usize,
    words: BTreeMap<u32, u32>,
}

impl StoreTracker {
    fn complete(
        self,
    ) -> Result<Vec<SourceInputStoreObservation>, SourceInputTraceError> {
        if let Some(error) = self.error {
            return Err(error);
        }
        if self.next_input != self.pending.len() {
            return Err(SourceInputTraceError::InvalidInputTransition);
        }
        let mut stores = Vec::new();
        for pending in self.pending {
            if let Some(completed) = pending.completed {
                stores.push(completed);
            } else if pending.writes.iter().any(Option::is_none) {
                return Err(SourceInputTraceError::MissingInputResultStore);
            } else {
                return Err(SourceInputTraceError::InputResultMismatch);
            }
        }
        Ok(stores)
    }

    fn from_machine(
        machine: &ProfileMachine,
        prefix: &SourceInputPrefixProof,
    ) -> Result<Self, SourceInputTraceError> {
        let mut words = BTreeMap::new();
        let mut pending = Vec::new();
        for input in &prefix.observations {
            let store = pending_store(*input)?;
            for offset in 0..store.expected.len() {
                let index = u32::try_from(offset)
                    .ok()
                    .ok_or(SourceInputTraceError::InputResultMismatch)?;
                let address = input
                    .destination
                    .cell_address(index)
                    .ok_or(SourceInputTraceError::InputResultMismatch)?;
                let value = machine
                    .memory_word(address)
                    .ok()
                    .ok_or(SourceInputTraceError::InputResultMismatch)?;
                let _previous = words.insert(address, value);
            }
            pending.push(store);
        }
        Ok(Self {
            error: None,
            next_input: 0,
            pending,
            trace_index: 0,
            words,
        })
    }

    // Only actual guest data instructions can complete source-typed values.
    // The observed frame words are always read from normative VM deltas.
    fn observe_data_write(&mut self, address: u32, step_index: usize) {
        for store in self.pending.iter_mut().take(self.next_input) {
            if store.completed.is_some()
                || store.input.trace_index >= step_index
            {
                continue;
            }
            let Some(cell_index) = address
                .checked_sub(store.input.destination.address)
                .and_then(|offset| usize::try_from(offset).ok())
                .filter(|offset| *offset < store.writes.len())
            else {
                continue;
            };
            let Some(write_step) = store.writes.get_mut(cell_index) else {
                continue;
            };
            *write_step = Some(step_index);
            if store.writes.iter().any(Option::is_none) {
                continue;
            }
            let completed_cells = store
                .expected
                .iter()
                .enumerate()
                .map(|(cell_offset, expected_word)| {
                    let offset = u32::try_from(cell_offset).ok()?;
                    let cell_address =
                        store.input.destination.cell_address(offset)?;
                    let actual_word = *self.words.get(&cell_address)?;
                    let write_index =
                        store.writes.get(cell_offset).copied().flatten()?;
                    (actual_word == *expected_word).then_some(
                        SourceInputStoreCell {
                            address: cell_address,
                            trace_index: write_index,
                            value: actual_word,
                        },
                    )
                })
                .collect::<Option<Vec<_>>>();
            if let Some(cells) = completed_cells {
                store.completed = Some(SourceInputStoreObservation {
                    cells,
                    input: store.input,
                });
            }
        }
    }

    fn step(&mut self, step: &ProfileStepTrace) {
        let index = self.trace_index;
        self.trace_index = self.trace_index.saturating_add(1);
        if self.error.is_some() {
            return;
        }
        if let Some(input) = step.input {
            let Some(store) = self.pending.get(self.next_input) else {
                self.error =
                    Some(SourceInputTraceError::InvalidInputTransition);
                return;
            };
            if store.input.trace_index != index || store.input.input != input {
                self.error =
                    Some(SourceInputTraceError::InvalidInputTransition);
                return;
            }
            // A repeated read must not overwrite an unmaterialized prior SSA.
            if self.pending.iter().take(self.next_input).any(|earlier| {
                earlier.input.destination == store.input.destination
                    && earlier.completed.is_none()
            }) {
                self.error =
                    Some(SourceInputTraceError::MissingInputResultStore);
                return;
            }
            self.next_input = self.next_input.saturating_add(1);
        }

        // A fetched instruction inside an allocated C frame is not a
        // legitimate data write, even if encryption is a no-op. Reject any
        // such code/frame alias rather than pretending a code mutation is C.
        if self.words.contains_key(&step.before.registers.code_pointer) {
            self.error = Some(SourceInputTraceError::InputResultMismatch);
            return;
        }

        // Include actual code encryption in observed memory state, but it
        // cannot itself count as a source result's guest data write.
        for write in [step.memory_delta.data, step.memory_delta.encryption]
            .into_iter()
            .flatten()
        {
            if let Some(word) = self.words.get_mut(&write.address) {
                *word = write.after;
            }
        }
        if matches!(step.decoded, Some(b'p' | b'*')) && step.result.is_ok() {
            self.observe_data_write(step.before.registers.data_pointer, index);
        }
    }
}

fn pending_store(
    input: SourceInputSiteObservation,
) -> Result<PendingInputStore, SourceInputTraceError> {
    let expected = match (input.semantics, input.input) {
        (GuestCodeInputSemantics::ByteU8, TraceInput::Byte(byte))
            if input.destination.words == 1 =>
        {
            vec![u32::from(byte)]
        },
        (GuestCodeInputSemantics::SignedC23 { .. }, value)
            if input.destination.words == 2 =>
        {
            let bits = match value {
                TraceInput::Byte(byte) => u32::from(byte),
                TraceInput::EndOfInput => u32::MAX,
            };
            encode_i32_cells(bits).to_vec()
        },
        _ => return Err(SourceInputTraceError::InputResultMismatch),
    };
    let count = expected.len();
    Ok(PendingInputStore {
        completed: None,
        expected,
        input,
        writes: vec![None; count],
    })
}

/// Require real target memory operations to materialize source-typed input
/// results after their actual input instructions.
///
/// This independently replays the exact physical source and binary stream
/// after the source input/return check. Every input must be followed by guest
/// data writes to **every** reserved result word; those words must jointly
/// equal the source C23/byte scalar at one observed step before that SSA input
/// is redefined by a later execution of its source read. No unchanged loader
/// memory or post-hoc host state update can stand in for a guest write.
///
/// This is deliberately stricter than the input/return or I/O-output gates.
/// A positive result does not prove later uses of the scalar, code control,
/// phi copies, arithmetic, output, or complete source compilation.
///
/// # Errors
///
/// Refuses any incomplete source return/input path, missing physical data
/// writes, incorrect actual stored word values or nondeterministic replay.
pub fn verify_source_input_site_stored_results(
    probe: SourceInputProbe<'_>,
) -> Result<SourceInputStoredProof, SourceInputTraceError> {
    let prefix = verify_source_input_site_return_compatible(probe)?;
    let mut machine = ProfileMachine::from_source(
        current_profile(),
        probe.physical_source,
        probe.input.to_vec(),
    )
    .map_err(|_error| SourceInputTraceError::InvalidGuestExecution)?;
    let mut tracker = StoreTracker::from_machine(&machine, &prefix)?;
    let outcome = machine
        .run_traced(probe.step_budget, &mut |step| tracker.step(step))
        .map_err(|_error| SourceInputTraceError::InvalidGuestExecution)?;
    if outcome != prefix.outcome
        || machine.input_consumed() != prefix.bytes_consumed
        || machine.output() != prefix.guest_output
    {
        return Err(SourceInputTraceError::InvalidGuestExecution);
    }
    Ok(SourceInputStoredProof {
        prefix,
        stores: tracker.complete()?,
    })
}

#[cfg(test)]
#[path = "../../../../tests/compiler/source_input_store.rs"]
mod tests;
