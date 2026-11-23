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
//! may clobber the cells. The checker tracks the live words through return;
//! unrelated C arithmetic and CFG operations remain unchecked.

use std::collections::{BTreeMap, BTreeSet};

use malbolge::{ProfileMachine, ProfileStepTrace, TraceInput, current_profile};

use super::source_input_trace::{
    SourceInputPrefixProof, SourceInputProbe, SourceInputSiteObservation,
    SourceInputTraceError, verify_source_input_site_output_with_effect_anchors,
    verify_source_input_site_return_compatible,
};
use super::typed_cfg_adapter::state_relocation::{
    GuestCodeEffectAnchor, GuestCodeInputSemantics, GuestCodeOperationAnchor,
    GuestCodeOperationEffect, GuestCodeProposals,
    bind_source_locked_cfg_code_targets_with_effect_anchors,
};
use super::typed_cfg_adapter::state_storage::{
    GuestFramePlacement, encode_i32_cells,
};

struct PendingInputStore {
    completed: Option<SourceInputStoreObservation>,
    expected: Vec<u32>,
    input: SourceInputSiteObservation,
    saw_matching_unrelated: bool,
    write_dependent: Vec<bool>,
    writes: Vec<Option<(usize, u32)>>,
}

// A conservative dynamic dependency shadow for an authentic profile trace.
// It deliberately overapproximates influence (including input-driven data
// addresses and code fetches) but never treats time after `/` as dependence.
#[derive(Default)]
struct GuestInfluence {
    accumulator: BTreeSet<usize>,
    code_pointer: BTreeSet<usize>,
    control: BTreeSet<usize>,
    data_pointer: BTreeSet<usize>,
    memory: BTreeMap<u32, BTreeSet<usize>>,
}

impl GuestInfluence {
    #[expect(
        clippy::too_many_lines,
        reason = "bounded VM data/control dependency propagation"
    )]
    fn step(
        &mut self,
        step: &ProfileStepTrace,
        input_index: Option<usize>,
    ) -> BTreeSet<usize> {
        if step.result.is_err() {
            return BTreeSet::new();
        }
        let code_address = step.before.registers.code_pointer;
        let data_address = step.before.registers.data_pointer;
        let mut reached = self.control.clone();
        reached.extend(self.code_pointer.iter().copied());
        reached.extend(
            self.memory
                .get(&code_address)
                .into_iter()
                .flatten()
                .copied(),
        );
        // A data-written opcode can select subsequent execution semantics.
        self.control.extend(reached.iter().copied());
        let mut data_result = BTreeSet::new();
        match step.decoded {
            Some(b'/') => {
                self.accumulator = reached.clone();
                self.accumulator.extend(input_index);
            },
            Some(b'j' | b'i') => {
                let mut destination = reached.clone();
                destination.extend(self.data_pointer.iter().copied());
                destination.extend(
                    self.memory
                        .get(&data_address)
                        .into_iter()
                        .flatten()
                        .copied(),
                );
                if step.decoded == Some(b'j') {
                    self.data_pointer = destination;
                } else {
                    self.code_pointer = destination.clone();
                    self.control.extend(destination);
                }
            },
            Some(b'p' | b'*') => {
                data_result.clone_from(&reached);
                data_result.extend(self.data_pointer.iter().copied());
                data_result.extend(
                    self.memory
                        .get(&data_address)
                        .into_iter()
                        .flatten()
                        .copied(),
                );
                if step.decoded == Some(b'p') {
                    data_result.extend(self.accumulator.iter().copied());
                }
                self.accumulator = data_result.clone();
                let _prior =
                    self.memory.insert(data_address, data_result.clone());
            },
            _ => {},
        }
        // Post-instruction encryption may use the *new* C after an `i`.
        // Preserve any preceding data write at the same address.
        if let Some(encryption) = step.memory_delta.encryption {
            let mut effect = self
                .memory
                .get(&encryption.address)
                .cloned()
                .unwrap_or_default();
            effect.extend(reached);
            effect.extend(self.code_pointer.iter().copied());
            let _prior = self.memory.insert(encryption.address, effect);
        }
        data_result
    }
}

/// One actual guest data write that completed a source input word.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SourceInputStoreCell {
    /// Actual code cell where the normative VM executed the p/* write.
    pub code_address: u32,
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
    /// Every actual p/* write to any reserved input-result frame word,
    /// including repeated, idempotent, and subsequently overwritten writes.
    pub frame_writes: Vec<SourceInputStoreCell>,
}

// Reconcile the most recent source definition of each reserved frame word.
// Keep width/address validation separate from the completion-state loop.
fn record_expected_cells(
    words: &mut BTreeMap<u32, u32>,
    pending: &PendingInputStore,
) -> Result<(), SourceInputTraceError> {
    for (offset, expected) in pending.expected.iter().enumerate() {
        let offset = u32::try_from(offset)
            .map_err(|_error| SourceInputTraceError::InputResultMismatch)?;
        let address = pending
            .input
            .destination
            .cell_address(offset)
            .ok_or(SourceInputTraceError::InputResultMismatch)?;
        let _previous = words.insert(address, *expected);
    }
    Ok(())
}

struct StoreTracker {
    error: Option<SourceInputTraceError>,
    influence: GuestInfluence,
    next_input: usize,
    pending: Vec<PendingInputStore>,
    trace_index: usize,
    words: BTreeMap<u32, u32>,
    frame_writes: Vec<SourceInputStoreCell>,
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
        let mut last_expected = BTreeMap::new();
        for pending in self.pending {
            record_expected_cells(&mut last_expected, &pending)?;
            if let Some(completed) = pending.completed {
                stores.push(completed);
            } else if pending.writes.iter().any(Option::is_none) {
                return Err(SourceInputTraceError::MissingInputResultStore);
            } else if pending.saw_matching_unrelated {
                return Err(SourceInputTraceError::InputResultUnrelatedToInput);
            } else {
                return Err(SourceInputTraceError::InputResultMismatch);
            }
        }
        // A previously completed store is not sufficient if subsequent guest
        // instructions corrupt its SSA result before the source return.
        for (address, expected) in last_expected {
            if self.words.get(&address) != Some(&expected) {
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
            influence: GuestInfluence::default(),
            next_input: 0,
            pending,
            trace_index: 0,
            words,
            frame_writes: Vec::new(),
        })
    }

    // Only actual guest data instructions can complete source-typed values.
    // The observed frame words are always read from normative VM deltas.
    #[expect(
        clippy::excessive_nesting,
        reason = "keep the final data-write and C32 cell obligations explicit"
    )]
    fn observe_data_write(
        &mut self,
        address: u32,
        step_index: usize,
        code_address: u32,
        dependencies: &BTreeSet<usize>,
    ) {
        if let Some(&value) = self.words.get(&address) {
            self.frame_writes.push(SourceInputStoreCell {
                code_address,
                address,
                trace_index: step_index,
                value,
            });
        }
        for (input_index, store) in
            self.pending.iter_mut().take(self.next_input).enumerate()
        {
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
            *write_step = Some((step_index, code_address));
            if let Some(dependent) = store.write_dependent.get_mut(cell_index) {
                *dependent = dependencies.contains(&input_index);
            }
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
                    let (write_index, write_code_address) =
                        store.writes.get(cell_offset).copied().flatten()?;
                    (actual_word == *expected_word).then_some(
                        SourceInputStoreCell {
                            code_address: write_code_address,
                            address: cell_address,
                            trace_index: write_index,
                            value: actual_word,
                        },
                    )
                })
                .collect::<Option<Vec<_>>>();
            if let Some(cells) = completed_cells {
                if store.write_dependent.iter().any(|dependent| *dependent) {
                    store.completed = Some(SourceInputStoreObservation {
                        cells,
                        input: store.input,
                    });
                } else {
                    store.saw_matching_unrelated = true;
                }
            }
        }
    }

    fn step(&mut self, step: &ProfileStepTrace) {
        let index = self.trace_index;
        self.trace_index = self.trace_index.saturating_add(1);
        if self.error.is_some() {
            return;
        }
        let input_index = step.input.map(|_input| self.next_input);
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

        // A jump-target XLAT2 may encrypt a source frame word without ever
        // fetching that cell. Such code/data aliasing cannot silently alter
        // a reserved SSA value or impersonate an input-result store.
        if step
            .memory_delta
            .encryption
            .is_some_and(|write| self.words.contains_key(&write.address))
        {
            self.error = Some(SourceInputTraceError::InputResultMismatch);
            return;
        }

        // Include actual data changes in observed memory state; even an
        // idempotent p/* is journaled as a real frame-write instruction.
        for write in [step.memory_delta.data, step.memory_delta.encryption]
            .into_iter()
            .flatten()
        {
            if let Some(word) = self.words.get_mut(&write.address) {
                *word = write.after;
            }
        }
        let dependencies = self.influence.step(step, input_index);
        if matches!(step.decoded, Some(b'p' | b'*')) && step.result.is_ok() {
            self.observe_data_write(
                step.before.registers.data_pointer,
                index,
                step.before.registers.code_pointer,
                &dependencies,
            );
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
        saw_matching_unrelated: false,
        write_dependent: vec![false; count],
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
/// is redefined by a later execution of its source read. The final definition
/// must also survive to the bounded guest return. No unchanged loader memory,
/// post-hoc host update, or code encryption may stand in for a guest write.
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
    verify_source_input_stored_prefix(probe, prefix)
}

impl SourceInputProbe<'_> {
    /// Check full-width physical C23 input-result stores after source-placed
    /// input effects and a source-compatible return. Input opcode placement
    /// alone cannot stand in for actually written SSA frame cells.
    ///
    /// # Errors
    ///
    /// Rejects every source-return/placement refusal, missing actual p/*
    /// writes, wrong signed C32 values or unverified data dependence.
    pub fn verify_stored_with_operation_anchors(
        self,
        proposals: GuestCodeProposals<'_>,
        anchors: &[GuestCodeOperationAnchor],
    ) -> Result<SourceInputStoredProof, SourceInputTraceError> {
        let prefix =
            self.verify_return_with_operation_anchors(proposals, anchors)?;
        verify_source_input_stored_prefix(self, prefix)
    }

    /// Require both source-compatible output at its actual guest code site
    /// and real input-dependent SSA frame writes at their exact effect sites.
    ///
    /// Both obligations apply to the same physical source and byte stream;
    /// two independent normative VM passes must agree on the complete trace
    /// outcome and output. This is not a proof of physical CFG linkage, guest
    /// arithmetic, or arbitrary source output-operand dataflow.
    ///
    /// # Errors
    ///
    /// Refuses unmatched source output, off-site physical output or frame
    /// writes, missing input dependence, and every return/input error.
    pub fn verify_output_and_stored_with_effect_anchors(
        self,
        proposals: GuestCodeProposals<'_>,
        operation_anchors: &[GuestCodeOperationAnchor],
        effect_anchors: &[GuestCodeEffectAnchor],
    ) -> Result<SourceInputStoredProof, SourceInputTraceError> {
        let prefix = verify_source_input_site_output_with_effect_anchors(
            self,
            proposals,
            operation_anchors,
            effect_anchors,
        )?;
        let (proof, steps) =
            verify_source_input_stored_prefix_with_steps(self, prefix)?;
        verify_source_input_store_effect_sites(
            self,
            proposals,
            operation_anchors,
            effect_anchors,
            &proof,
            &steps,
        )?;
        Ok(proof)
    }

    /// Require that each physical input-result write executes at its exact
    /// individually anchored, source-authenticated store-effect code site.
    ///
    /// A real input, source-compatible return, full typed value and input
    /// dependence are prerequisites. Pointer setup between effects is legal;
    /// a write at another code site is not proof of the placed source store.
    /// This is still not C arithmetic, phi or branch verification.
    ///
    /// # Errors
    ///
    /// Refuses all input/store prerequisites, forged or incompatible sparse
    /// placements and a matching guest value written at a foreign code site.
    pub fn verify_stored_with_effect_anchors(
        self,
        proposals: GuestCodeProposals<'_>,
        operation_anchors: &[GuestCodeOperationAnchor],
        effect_anchors: &[GuestCodeEffectAnchor],
    ) -> Result<SourceInputStoredProof, SourceInputTraceError> {
        let prefix = self.verify_return_with_effect_anchors(
            proposals,
            operation_anchors,
            effect_anchors,
        )?;
        let (proof, steps) =
            verify_source_input_stored_prefix_with_steps(self, prefix)?;
        verify_source_input_store_effect_sites(
            self,
            proposals,
            operation_anchors,
            effect_anchors,
            &proof,
            &steps,
        )?;
        Ok(proof)
    }
}

// Recompute store obligations from the same canonical source and bounded
// block placements. Only the traced real VM, never the layout proposal,
// supplies the code address and written word for each completed input store.
fn verify_source_input_store_effect_sites(
    probe: SourceInputProbe<'_>,
    proposals: GuestCodeProposals<'_>,
    operation_anchors: &[GuestCodeOperationAnchor],
    effect_anchors: &[GuestCodeEffectAnchor],
    proof: &SourceInputStoredProof,
    steps: &[ProfileStepTrace],
) -> Result<(), SourceInputTraceError> {
    let source_cells = u32::try_from(probe.physical_source.len())
        .map_err(|_error| SourceInputTraceError::InvalidProbeBound)?;
    let plan = bind_source_locked_cfg_code_targets_with_effect_anchors(
        probe.canonical,
        source_cells,
        probe.frame_base,
        proposals,
        operation_anchors,
        effect_anchors,
    )
    .map_err(|_error| SourceInputTraceError::InvalidSourcePlacement)?;
    let mut effects = BTreeMap::new();
    let mut allowed_frame_writes = BTreeSet::new();
    for site in &plan.operation_effect_sites {
        if let GuestCodeOperationEffect::Store { destination, .. } = site.effect
        {
            let key = (site.function, site.block, site.ordinal, destination);
            let _allowed =
                allowed_frame_writes.insert((site.code_address, destination));
            if effects.insert(key, site.code_address).is_some() {
                return Err(SourceInputTraceError::InvalidSourcePlacement);
            }
        }
    }
    // Check every reached frame mutation, not only the final successful
    // stores. Otherwise an unanchored earlier/later p/* could be invisible.
    for write in &proof.frame_writes {
        if !allowed_frame_writes.contains(&(write.code_address, write.address))
        {
            return Err(SourceInputTraceError::UnexpectedGuestStoreSite);
        }
    }
    for store in &proof.stores {
        for cell in &store.cells {
            let key = (
                store.input.function,
                store.input.block,
                store.input.ordinal,
                cell.address,
            );
            let expected = effects
                .get(&key)
                .ok_or(SourceInputTraceError::InvalidSourcePlacement)?;
            if cell.code_address != *expected {
                return Err(SourceInputTraceError::UnexpectedGuestStoreSite);
            }
        }
    }
    // A source Store effect is a single physical write per reached input
    // definition. Re-executing an already authorized site is not another
    // source effect, even when that second write leaves the word unchanged.
    // Keep the more specific wrong-site diagnostic above for foreign writes.
    verify_complete_frame_write_journal(proof)?;
    verify_source_frame_write_sites(&plan, steps)
}

// Only the physically reached p/* site can perform a source-frame store.
// Include all SSA and phi scratch cells, not merely input-result destinations.
// Even unchanged writes are effects and must be attributed to source code.
fn verify_source_frame_write_step(
    step: &ProfileStepTrace,
    frames: &[GuestFramePlacement],
    allowed: &BTreeMap<(u32, u32), Option<u32>>,
) -> Result<(), SourceInputTraceError> {
    if step.result.is_err() {
        return Ok(());
    }
    let is_frame_cell = |address| {
        frames
            .iter()
            .any(|frame| frame.base <= address && address < frame.end_exclusive)
    };
    let code_address = step.before.registers.code_pointer;
    // A source frame is data-only: even a no-op XLAT2 target cannot stand
    // in for a typed state write, nor can a fetched frame cell become code.
    if is_frame_cell(code_address)
        || step
            .memory_reads
            .encryption
            .is_some_and(|read| is_frame_cell(read.address))
        || step
            .memory_delta
            .encryption
            .is_some_and(|write| is_frame_cell(write.address))
    {
        return Err(SourceInputTraceError::InputResultMismatch);
    }
    if matches!(step.decoded, Some(b'p' | b'*')) {
        let data_address = step.before.registers.data_pointer;
        if is_frame_cell(data_address) {
            let literal = allowed
                .get(&(code_address, data_address))
                .ok_or(SourceInputTraceError::UnexpectedGuestStoreSite)?;
            // Actual p/* leaves the written word in A even when the memory
            // delta is empty because this particular write was idempotent.
            if literal.is_some_and(|expected| {
                expected != step.after.registers.accumulator
            }) {
                return Err(SourceInputTraceError::InputResultMismatch);
            }
        }
    }
    Ok(())
}

// The proposal can authorize only source operations and edge-local two-phase
// phi copy cells. It cannot add a new permission for a setup instruction to
// overwrite an unrelated local, even when the final I/O still looks right.
fn verify_source_frame_write_sites(
    plan: &super::typed_cfg_adapter::state_relocation::GuestAddressedCfgPlan,
    steps: &[ProfileStepTrace],
) -> Result<(), SourceInputTraceError> {
    let mut allowed = BTreeMap::new();
    for site in &plan.operation_effect_sites {
        if let GuestCodeOperationEffect::Store { destination, literal } =
            site.effect
        {
            if allowed
                .insert((site.code_address, destination), literal)
                .is_some()
            {
                return Err(SourceInputTraceError::InvalidSourcePlacement);
            }
        }
    }
    for edge in &plan.control_edges {
        for site in edge.snapshot_sites.iter().chain(&edge.commit_sites) {
            if allowed
                .insert((site.code_address, site.copy.destination), None)
                .is_some()
            {
                return Err(SourceInputTraceError::InvalidSourcePlacement);
            }
        }
    }
    // These are the original normative VM steps of the input-store replay.
    // The replay's outcome, input consumption and output were already checked
    // against the independent source I/O run before admission.
    for step in steps {
        verify_source_frame_write_step(
            step,
            &plan.relocated.state_placements,
            &allowed,
        )?;
    }
    Ok(())
}

// Each completed source input word owns exactly one physical p/* event.
// Use the normative trace index rather than source operand order: a C32
// high word may be stored before its low word. A repeated authorized
// instruction has no extra source effect to which it can be attributed.
fn verify_complete_frame_write_journal(
    proof: &SourceInputStoredProof,
) -> Result<(), SourceInputTraceError> {
    let mut attributed = proof
        .stores
        .iter()
        .flat_map(|store| store.cells.iter().copied())
        .collect::<Vec<_>>();
    attributed.sort_unstable_by_key(|cell| cell.trace_index);
    if attributed != proof.frame_writes {
        return Err(SourceInputTraceError::UnattributedGuestStore);
    }
    Ok(())
}

fn verify_source_input_stored_prefix(
    probe: SourceInputProbe<'_>,
    prefix: SourceInputPrefixProof,
) -> Result<SourceInputStoredProof, SourceInputTraceError> {
    verify_source_input_stored_prefix_with_steps(probe, prefix)
        .map(|(proof, _steps)| proof)
}

fn verify_source_input_stored_prefix_with_steps(
    probe: SourceInputProbe<'_>,
    prefix: SourceInputPrefixProof,
) -> Result<
    (SourceInputStoredProof, Vec<ProfileStepTrace>),
    SourceInputTraceError,
> {
    let mut machine = ProfileMachine::from_source(
        current_profile(),
        probe.physical_source,
        probe.input.to_vec(),
    )
    .map_err(|_error| SourceInputTraceError::InvalidGuestExecution)?;
    let mut tracker = StoreTracker::from_machine(&machine, &prefix)?;
    let mut physical_steps = Vec::new();
    let outcome = machine
        .run_traced(probe.step_budget, &mut |step| {
            tracker.step(step);
            physical_steps.push(*step);
        })
        .map_err(|_error| SourceInputTraceError::InvalidGuestExecution)?;
    if outcome != prefix.outcome
        || machine.input_consumed() != prefix.bytes_consumed
        || machine.output() != prefix.guest_output
    {
        return Err(SourceInputTraceError::InvalidGuestExecution);
    }
    let frame_writes = std::mem::take(&mut tracker.frame_writes);
    Ok((
        SourceInputStoredProof {
            prefix,
            stores: tracker.complete()?,
            frame_writes,
        },
        physical_steps,
    ))
}

#[cfg(test)]
#[path = "../../../../tests/compiler/source_input_store.rs"]
mod tests;
