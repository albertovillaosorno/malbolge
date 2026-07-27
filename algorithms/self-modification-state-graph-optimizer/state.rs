// File:
//   - state.rs
// Path:
//   - algorithms/self-modification-state-graph-optimizer/state.rs
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
//   - Incremental exact state identity over one indexed-memory execution
//     lineage.
// - Must-Not:
//   - Merge on digest alone or compare unrelated full roots implicitly.
// - Allows:
//   - Inputs: validated profile checkpoints and exact public step traces.
//   - Outputs: incremental states, exact graph IDs, and oracle checkpoints.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - Split when cross-lineage content-addressed roots gain independent
//     evidence.
// - Merge-When:
//   - Merge when production graph/native tiers own the same exact state
//     identity.
// - Summary:
//   - Deduplicates indexed states without per-observation full-memory hashing.
// - Description:
//   - Digests bucket candidates; shared lineage plus exact fields confirm
//     merges.
// - Usage:
//   - Research candidate composed by `tests/state_graph_research.rs`.
// - Defaults:
//   - Foreign root/input lineages fail closed rather than trigger full
//     compares.
//
// Related documents:
// - algorithms/self-modification-state-graph-optimizer/index.rs
// - math/algorithms/self-modification-state-graph-optimizer.tex
//
// Large file:
//   - false

//! Incremental collision-safe state identity above bounded radix memory.

use std::collections::BTreeMap;
use std::ptr;
use std::sync::Arc;

use malbolge::{
    ProfileDescriptor, ProfileMachineError, ProfileMachineIoState,
    ProfileMachineObservation, ProfileMachineState, ProfileMemoryDelta,
    ProfileRegisters, ProfileStepTrace, Termination, TraceInput,
};

use crate::execution_ir::EffectOp;
use crate::indexed::{IndexedMemoryError, IndexedProfileMemory};
use crate::persistent_output::PersistentOutput;

const FNV_OFFSET: u64 = 14_695_981_039_346_656_037;
const FNV_PRIME: u64 = 1_099_511_628_211;

type IndexedDigestFunction = fn(&IndexedMachineState) -> u64;
type OutputTransition = Result<PersistentOutput, IndexedStateError>;

/// Exact incremental profile-machine state inside one execution lineage.
#[derive(Clone, Debug)]
pub struct IndexedMachineState {
    input: Arc<[u8]>,
    input_cursor: usize,
    input_digest: u64,
    memory: IndexedProfileMemory,
    output: PersistentOutput,
    profile: &'static ProfileDescriptor,
    profile_digest: u64,
    registers: ProfileRegisters,
    termination: Option<Termination>,
}

/// Stable node identifier inside one indexed state graph.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct IndexedNodeId(u32);

/// Collision-confirmed state graph bound to one immutable root/input lineage.
#[derive(Clone, Debug)]
pub struct IndexedStateGraph {
    buckets: BTreeMap<u64, Vec<IndexedNodeId>>,
    deduplicated_observations: usize,
    digest: IndexedDigestFunction,
    nodes: Vec<IndexedMachineState>,
    observations: usize,
}

/// Failure while constructing or evolving incremental state identity.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum IndexedStateError {
    /// One trace begins at a state different from the indexed state.
    BeforeObservationMismatch,
    /// A trace input effect disagrees with the immutable input stream/cursor.
    InputTraceMismatch,
    /// Indexed memory rejected an address, patch, or radix invariant.
    Memory(IndexedMemoryError),
    /// A materialized oracle checkpoint failed runtime validation.
    OracleCheckpoint(ProfileMachineError),
    /// A trace output effect disagrees with output-length observations.
    OutputTraceMismatch,
    /// A trace names a profile different from this indexed state.
    ProfileMismatch,
}

/// Failure while adding one incremental state to a lineage-bound graph.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum IndexedStateGraphError {
    /// A candidate does not share the graph's immutable input and memory root.
    ForeignLineage,
    /// Stable node IDs exhausted their u32 domain.
    NodeIdentityOverflow,
}

impl From<IndexedMemoryError> for IndexedStateError {
    fn from(error: IndexedMemoryError) -> Self {
        Self::Memory(error)
    }
}

impl From<ProfileMachineError> for IndexedStateError {
    fn from(error: ProfileMachineError) -> Self {
        Self::OracleCheckpoint(error)
    }
}

impl IndexedMachineState {
    /// Applies one validated memory-only delta while preserving all other
    /// state.
    ///
    /// # Errors
    ///
    /// Returns [`IndexedStateError`] when the indexed memory rejects the delta.
    pub fn apply_memory_delta(
        &self,
        delta: ProfileMemoryDelta,
    ) -> Result<Self, IndexedStateError> {
        Ok(Self {
            input: Arc::clone(&self.input),
            input_cursor: self.input_cursor,
            input_digest: self.input_digest,
            memory: self.memory.apply(delta)?,
            output: self.output.clone(),
            profile: self.profile,
            profile_digest: self.profile_digest,
            registers: self.registers,
            termination: self.termination,
        })
    }

    /// Applies one exact runtime trace to a new incremental state.
    ///
    /// # Errors
    ///
    /// Returns [`IndexedStateError`] when trace/profile/I/O observations
    /// disagree or indexed memory rejects the exact committed delta.
    pub fn apply_trace(
        &self,
        trace: &ProfileStepTrace,
    ) -> Result<Self, IndexedStateError> {
        self.validate_before(trace)?;
        let input_cursor = self.next_input_cursor(trace)?;
        let output = self.next_output(trace)?;
        let memory = self.memory.apply(trace.memory_delta)?;
        Ok(Self {
            input: Arc::clone(&self.input),
            input_cursor,
            input_digest: self.input_digest,
            memory,
            output,
            profile: self.profile,
            profile_digest: self.profile_digest,
            registers: trace.after.registers,
            termination: trace.after.termination,
        })
    }

    /// Applies one verifier-admitted compact effect to this exact lineage.
    ///
    /// # Errors
    ///
    /// Returns [`IndexedStateError`] when the before observation, deterministic
    /// input/output evolution, or indexed memory invariant disagrees.
    pub(crate) fn apply_verified_effect(
        &self,
        effect: &EffectOp,
    ) -> Result<Self, IndexedStateError> {
        self.validate_before_observation(effect.before)?;
        let input_cursor = self.next_input_cursor_effect(
            effect.input,
            effect.after.input_consumed,
        )?;
        let output =
            self.next_output_effect(effect.output, effect.after.output_len)?;
        let memory = self.memory.apply_verified(effect.memory_delta)?;
        Ok(Self {
            input: Arc::clone(&self.input),
            input_cursor,
            input_digest: self.input_digest,
            memory,
            output,
            profile: self.profile,
            profile_digest: self.profile_digest,
            registers: effect.after.registers,
            termination: effect.after.termination,
        })
    }

    pub(crate) fn apply_verified_trace_effect(
        &self,
        trace: &ProfileStepTrace,
    ) -> Result<Self, IndexedStateError> {
        if !ptr::eq(self.profile, trace.profile) {
            return Err(IndexedStateError::ProfileMismatch);
        }
        self.apply_verified_effect(&EffectOp::from_trace(trace))
    }

    /// Returns exact equality for all state except mutable memory overrides.
    #[must_use]
    pub fn exact_non_memory_eq(&self, other: &Self) -> bool {
        self.shares_lineage(other)
            && self.input_cursor == other.input_cursor
            && self.output.exact_output_eq(&other.output)
            && self.registers == other.registers
            && self.termination == other.termination
    }

    /// Returns exact equality inside the same immutable execution lineage.
    #[must_use]
    pub fn exact_state_eq(&self, other: &Self) -> bool {
        ptr::eq(self.profile, other.profile)
            && Arc::ptr_eq(&self.input, &other.input)
            && self.input_cursor == other.input_cursor
            && self.output.exact_output_eq(&other.output)
            && self.registers == other.registers
            && self.termination == other.termination
            && self.memory.exact_memory_eq(&other.memory)
    }

    /// Constructs the root incremental state from one validated checkpoint.
    ///
    /// # Errors
    ///
    /// Returns [`IndexedStateError`] if the bounded radix candidate rejects the
    /// checkpoint memory geometry.
    pub fn from_checkpoint(
        state: &ProfileMachineState,
    ) -> Result<Self, IndexedStateError> {
        let io = state.io();
        let input = Arc::<[u8]>::from(io.input());
        let input_digest = hash_bytes(FNV_OFFSET, &input);
        let output = PersistentOutput::from_bytes(io.output());
        let profile_digest =
            hash_bytes(FNV_OFFSET, state.profile().fingerprint().as_bytes());
        Ok(Self {
            input,
            input_cursor: io.input_consumed(),
            input_digest,
            memory: IndexedProfileMemory::from_state(state)?,
            output,
            profile: state.profile(),
            profile_digest,
            registers: state.registers(),
            termination: io.termination(),
        })
    }

    /// Materializes one complete validated checkpoint for oracle comparison.
    ///
    /// # Errors
    ///
    /// Returns [`IndexedStateError`] if memory materialization or runtime
    /// checkpoint validation fails.
    pub fn materialize_checkpoint(
        &self,
    ) -> Result<ProfileMachineState, IndexedStateError> {
        let io = ProfileMachineIoState::new(
            self.input.to_vec(),
            self.input_cursor,
            self.output.materialize(),
            self.termination,
        )?;
        Ok(ProfileMachineState::new(
            self.profile,
            self.memory.materialize()?,
            self.registers,
            io,
        )?)
    }

    /// Reads one current indexed memory word without materializing the root.
    ///
    /// # Errors
    ///
    /// Returns [`IndexedStateError`] when the address is outside the lineage
    /// root or the bounded radix violates an internal invariant.
    pub fn memory_word(&self, address: u32) -> Result<u32, IndexedStateError> {
        Ok(self.memory.read(address)?)
    }

    fn next_input_cursor(
        &self,
        trace: &ProfileStepTrace,
    ) -> Result<usize, IndexedStateError> {
        self.next_input_cursor_effect(trace.input, trace.after.input_consumed)
    }

    fn next_input_cursor_effect(
        &self,
        input: Option<TraceInput>,
        after_input_consumed: usize,
    ) -> Result<usize, IndexedStateError> {
        match input {
            None => {
                if after_input_consumed == self.input_cursor {
                    Ok(self.input_cursor)
                } else {
                    Err(IndexedStateError::InputTraceMismatch)
                }
            },
            Some(TraceInput::Byte(byte)) => {
                let expected = self.input.get(self.input_cursor).copied();
                let next = self.input_cursor.saturating_add(1);
                if expected == Some(byte) && after_input_consumed == next {
                    Ok(next)
                } else {
                    Err(IndexedStateError::InputTraceMismatch)
                }
            },
            Some(TraceInput::EndOfInput) => {
                if self.input_cursor == self.input.len()
                    && after_input_consumed == self.input_cursor
                {
                    Ok(self.input_cursor)
                } else {
                    Err(IndexedStateError::InputTraceMismatch)
                }
            },
        }
    }

    fn next_output(&self, trace: &ProfileStepTrace) -> OutputTransition {
        self.next_output_effect(trace.output, trace.after.output_len)
    }

    fn next_output_effect(
        &self,
        output: Option<u8>,
        after_output_len: usize,
    ) -> OutputTransition {
        output.map_or_else(
            || {
                if after_output_len == self.output.len() {
                    Ok(self.output.clone())
                } else {
                    Err(IndexedStateError::OutputTraceMismatch)
                }
            },
            |byte| {
                let expected_len = self.output.len().saturating_add(1);
                if after_output_len == expected_len {
                    Ok(self.output.append(byte))
                } else {
                    Err(IndexedStateError::OutputTraceMismatch)
                }
            },
        )
    }

    /// Returns the canonical profile fingerprint bound to this state lineage.
    #[must_use]
    pub const fn profile_fingerprint(&self) -> &'static str {
        self.profile.fingerprint()
    }

    fn shares_lineage(&self, other: &Self) -> bool {
        ptr::eq(self.profile, other.profile)
            && Arc::ptr_eq(&self.input, &other.input)
            && self.memory.shares_root(&other.memory)
    }

    /// Returns a deterministic constant-size bucket digest for this state.
    ///
    /// Digest equality never authorizes a merge without
    /// [`Self::exact_state_eq`].
    #[must_use]
    pub fn state_digest(&self) -> u64 {
        let mut hash = FNV_OFFSET;
        hash = hash_u64(hash, self.profile_digest);
        hash = hash_u64(hash, self.input_digest);
        hash = hash_usize(hash, self.input_cursor);
        hash = hash_u64(hash, self.output.digest());
        hash = hash_termination(hash, self.termination);
        hash = hash_u32(hash, self.registers.accumulator);
        hash = hash_u32(hash, self.registers.code_pointer);
        hash = hash_u32(hash, self.registers.data_pointer);
        hash_u64(hash, self.memory.overlay_digest())
    }

    fn validate_before(
        &self,
        trace: &ProfileStepTrace,
    ) -> Result<(), IndexedStateError> {
        if !ptr::eq(self.profile, trace.profile) {
            return Err(IndexedStateError::ProfileMismatch);
        }
        self.validate_before_observation(trace.before)
    }

    fn validate_before_observation(
        &self,
        before: ProfileMachineObservation,
    ) -> Result<(), IndexedStateError> {
        if before.input_consumed != self.input_cursor
            || before.output_len != self.output.len()
            || before.registers != self.registers
            || before.termination != self.termination
        {
            return Err(IndexedStateError::BeforeObservationMismatch);
        }
        Ok(())
    }
}

impl IndexedNodeId {
    /// Returns the stable zero-based node index.
    #[must_use]
    pub const fn value(self) -> u32 {
        self.0
    }
}

impl IndexedStateGraph {
    /// Returns how many observations reused an exact incremental state.
    #[must_use]
    pub const fn deduplicated_observations(&self) -> usize {
        self.deduplicated_observations
    }

    fn existing_node(
        &self,
        digest: u64,
        state: &IndexedMachineState,
    ) -> Result<Option<IndexedNodeId>, IndexedStateGraphError> {
        let Some(candidates) = self.buckets.get(&digest) else {
            return Ok(None);
        };
        for candidate in candidates {
            let index =
                usize::try_from(candidate.value()).map_err(|_error| {
                    IndexedStateGraphError::NodeIdentityOverflow
                })?;
            if self
                .nodes
                .get(index)
                .is_some_and(|node| node.exact_state_eq(state))
            {
                return Ok(Some(*candidate));
            }
        }
        Ok(None)
    }

    /// Creates a graph bound to one initial incremental state lineage.
    #[must_use]
    pub fn new(seed: IndexedMachineState) -> Self {
        Self::with_digest(seed, IndexedMachineState::state_digest)
    }

    /// Returns the number of exact unique incremental states.
    #[must_use]
    pub const fn node_count(&self) -> usize {
        self.nodes.len()
    }

    /// Returns the total number of observations offered to the graph.
    #[must_use]
    pub const fn observations(&self) -> usize {
        self.observations
    }

    /// Records one state using digest buckets plus exact collision
    /// confirmation.
    ///
    /// # Errors
    ///
    /// Returns [`IndexedStateGraphError`] for foreign root/input lineage or
    /// node identifier exhaustion.
    pub fn observe(
        &mut self,
        state: IndexedMachineState,
    ) -> Result<IndexedNodeId, IndexedStateGraphError> {
        self.observations = self.observations.saturating_add(1);
        let seed = self
            .nodes
            .first()
            .ok_or(IndexedStateGraphError::NodeIdentityOverflow)?;
        if !seed.shares_lineage(&state) {
            return Err(IndexedStateGraphError::ForeignLineage);
        }
        let digest = (self.digest)(&state);
        if let Some(candidate) = self.existing_node(digest, &state)? {
            self.deduplicated_observations =
                self.deduplicated_observations.saturating_add(1);
            return Ok(candidate);
        }
        let raw_id = u32::try_from(self.nodes.len())
            .map_err(|_error| IndexedStateGraphError::NodeIdentityOverflow)?;
        let node_id = IndexedNodeId(raw_id);
        self.nodes.push(state);
        self.buckets.entry(digest).or_default().push(node_id);
        Ok(node_id)
    }

    /// Creates a lineage-bound graph with an explicit adversarial digest.
    #[must_use]
    pub fn with_digest(
        seed: IndexedMachineState,
        digest: IndexedDigestFunction,
    ) -> Self {
        let seed_digest = digest(&seed);
        let seed_id = IndexedNodeId(0);
        let mut buckets = BTreeMap::new();
        let _previous_bucket = buckets.insert(seed_digest, vec![seed_id]);
        Self {
            buckets,
            deduplicated_observations: 0,
            digest,
            nodes: vec![seed],
            observations: 1,
        }
    }
}

/// Digest function mapping every incremental state to one adversarial bucket.
#[must_use]
pub const fn constant_indexed_collision_digest(
    _state: &IndexedMachineState,
) -> u64 {
    0
}

fn hash_byte(hash: u64, value: u8) -> u64 {
    (hash ^ u64::from(value)).wrapping_mul(FNV_PRIME)
}

fn hash_bytes(mut hash: u64, values: &[u8]) -> u64 {
    for value in values {
        hash = hash_byte(hash, *value);
    }
    hash
}

fn hash_termination(hash: u64, termination: Option<Termination>) -> u64 {
    let tag = match termination {
        None => 0,
        Some(Termination::HaltInstruction) => 1,
        Some(Termination::NonGraphicalCell) => 2,
    };
    hash_byte(hash, tag)
}

fn hash_u32(mut hash: u64, value: u32) -> u64 {
    for byte in value.to_le_bytes() {
        hash = hash_byte(hash, byte);
    }
    hash
}

fn hash_u64(mut hash: u64, value: u64) -> u64 {
    for byte in value.to_le_bytes() {
        hash = hash_byte(hash, byte);
    }
    hash
}

fn hash_usize(mut hash: u64, value: usize) -> u64 {
    for byte in value.to_le_bytes() {
        hash = hash_byte(hash, byte);
    }
    hash
}
