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
//   - Collision-safe exact-state graph construction for classic VM research.
// - Must-Not:
//   - Treat hashes as semantic identity or merge reduced/approximate states.
// - Allows:
//   - Inputs: valid classic source, deterministic input, and bounded steps.
//   - Outputs: exact nodes, deterministic edges, and deduplication statistics.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - Split when a proved reduced-state key has independent lifecycle evidence.
// - Merge-When:
//   - Merge when native execution owns the same exact graph representation.
// - Summary:
//   - Establishes the conservative exact-state baseline for graph reductions.
// - Description:
//   - Hash buckets are always confirmed against complete machine snapshots.
// - Usage:
//   - Research baseline consumed by `tests/state_graph_research.rs`.
// - Defaults:
//   - Classic 1998 only; current 14-trit graph reduction is not claimed yet.
//

//! Collision-safe exact-state graph baseline for self-modifying Malbolge.

use std::collections::BTreeMap;

use malbolge::{
    ExecutionMode, InterpreterUndefinedBehavior, MEMORY_WORDS, Machine,
    MachineError, Registers, StepOutcome, StepTrace, Termination, Word,
};

const FNV_OFFSET: u64 = 14_695_981_039_346_656_037;
const FNV_PRIME: u64 = 1_099_511_628_211;
const HISTORICAL_PROFILE_ID: &str = "malbolge-1998";

type DigestFunction = fn(&ExactStateSnapshot) -> u64;
type MemoryImage = Box<[u16]>;

/// Stable node identifier inside one exact-state graph.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ExactNodeId(u32);

/// Stable kind of one exact graph step result.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExactStepKind {
    /// One normative transition committed and execution may continue.
    Continued,
    /// Self-encryption was rejected atomically.
    RejectedEncryption,
    /// The guest terminated with a normative reason.
    Terminated(Termination),
}

/// Exact normalized result retained by one graph edge.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ExactStepResult {
    /// Stable result category.
    pub kind: ExactStepKind,
    /// Encryption pointer for rejection, zero otherwise.
    pub pointer: u16,
    /// Rejected non-graphical value, zero otherwise.
    pub value: u16,
}

/// One deterministic exact-state graph edge.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ExactStateEdge {
    /// Decoded instruction byte when decode was reached.
    pub decoded: Option<u8>,
    /// Source node before the requested semantic step.
    pub from: ExactNodeId,
    /// Exact normalized result of the requested step.
    pub result: ExactStepResult,
    /// Destination node after the request returns.
    pub to: ExactNodeId,
}

/// Complete classic-machine state used to confirm graph identity.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExactStateSnapshot {
    input: Box<[u8]>,
    input_consumed: usize,
    memory: Box<[u16]>,
    output: Box<[u8]>,
    profile_id: &'static str,
    registers: Registers,
    termination: Option<Termination>,
}

/// Reduced future-state key that drops consumed input byte contents only.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct FutureInputSnapshot {
    input_consumed: usize,
    memory: Box<[u16]>,
    output: Box<[u8]>,
    profile_id: &'static str,
    registers: Registers,
    remaining_input: Box<[u8]>,
    termination: Option<Termination>,
}

/// Reduced key for a machine whose termination is already stable.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TerminalFutureSnapshot {
    output: Box<[u8]>,
    profile_id: &'static str,
    termination: Termination,
}

/// Collision-safe exact-state graph and deterministic observation statistics.
#[derive(Clone, Debug)]
pub struct ExactStateGraph {
    buckets: BTreeMap<u64, Vec<ExactNodeId>>,
    deduplicated_observations: usize,
    digest: DigestFunction,
    edges: Vec<ExactStateEdge>,
    nodes: Vec<ExactStateSnapshot>,
    observations: usize,
}

/// Failure while constructing or extending the exact research graph.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum StateGraphError {
    /// Supplied deterministic input is shorter than the machine cursor.
    InputCursorOutOfRange,
    /// Classic source could not initialize a machine.
    Load(malbolge::LoadError),
    /// Terminal future projection was requested from a live machine.
    MachineNotTerminated,
    /// Public VM memory access unexpectedly failed.
    Memory(malbolge::MemoryError),
    /// Exact graph node count exceeded the stable identifier domain.
    NodeIdentityOverflow,
    /// A non-encryption VM failure escaped the admitted exact baseline.
    UnexpectedMachine(MachineError),
}

impl ExactNodeId {
    /// Returns the stable zero-based node index.
    #[must_use]
    pub const fn value(self) -> u32 {
        self.0
    }
}

impl ExactStateGraph {
    /// Returns how many observations reused an already-confirmed exact node.
    #[must_use]
    pub const fn deduplicated_observations(&self) -> usize {
        self.deduplicated_observations
    }

    /// Returns the number of unique deterministic edges.
    #[must_use]
    pub const fn edge_count(&self) -> usize {
        self.edges.len()
    }

    fn existing_node(
        &self,
        digest: u64,
        snapshot: &ExactStateSnapshot,
    ) -> Result<Option<ExactNodeId>, StateGraphError> {
        let Some(candidates) = self.buckets.get(&digest) else {
            return Ok(None);
        };
        for candidate in candidates {
            let index = usize::try_from(candidate.value())
                .map_err(|_error| StateGraphError::NodeIdentityOverflow)?;
            if self.nodes.get(index) == Some(snapshot) {
                return Ok(Some(*candidate));
            }
        }
        Ok(None)
    }

    fn insert_edge(&mut self, edge: ExactStateEdge) {
        if !self.edges.contains(&edge) {
            self.edges.push(edge);
        }
    }

    /// Creates the default graph using the deterministic FNV-1a state digest.
    #[must_use]
    pub fn new() -> Self {
        Self::with_digest(exact_state_digest)
    }

    /// Returns the number of exact unique states.
    #[must_use]
    pub const fn node_count(&self) -> usize {
        self.nodes.len()
    }

    /// Returns the total number of state observations offered to the graph.
    #[must_use]
    pub const fn observations(&self) -> usize {
        self.observations
    }

    fn observe(
        &mut self,
        machine: &Machine,
        input: &[u8],
    ) -> Result<ExactNodeId, StateGraphError> {
        let snapshot = exact_snapshot(machine, input)?;
        self.observations = self.observations.saturating_add(1);
        let digest = (self.digest)(&snapshot);
        if let Some(candidate) = self.existing_node(digest, &snapshot)? {
            self.deduplicated_observations =
                self.deduplicated_observations.saturating_add(1);
            return Ok(candidate);
        }
        let raw_id = u32::try_from(self.nodes.len())
            .map_err(|_error| StateGraphError::NodeIdentityOverflow)?;
        let node_id = ExactNodeId(raw_id);
        self.nodes.push(snapshot);
        self.buckets.entry(digest).or_default().push(node_id);
        Ok(node_id)
    }

    /// Records one bounded classic execution into the exact-state graph.
    ///
    /// # Errors
    ///
    /// Returns [`StateGraphError`] on loader, memory, identifier, or unexpected
    /// machine failure. Invalid self-encryption is a modeled terminal edge.
    pub fn record_run(
        &mut self,
        source: &[u8],
        input: &[u8],
        step_budget: usize,
    ) -> Result<(), StateGraphError> {
        let mut machine = Machine::from_source(source, input.to_vec())
            .map_err(StateGraphError::Load)?;
        let mut from = self.observe(&machine, input)?;
        for _step in 0..step_budget {
            let mut trace = None;
            let result = machine.step_traced(&mut |record: &StepTrace| {
                trace = Some(*record);
            });
            let record = trace.ok_or(StateGraphError::UnexpectedMachine(
                MachineError::TranslationTableInvariant,
            ))?;
            let normalized = normalize_step_result(result)?;
            let to = self.observe(&machine, input)?;
            self.insert_edge(ExactStateEdge {
                decoded: record.decoded,
                from,
                result: normalized,
                to,
            });
            from = to;
            if normalized.kind != ExactStepKind::Continued {
                break;
            }
        }
        Ok(())
    }

    /// Creates a graph with an explicit digest function for collision testing.
    ///
    /// The digest never decides equality. Every bucket candidate is compared
    /// against the complete [`ExactStateSnapshot`] before a merge occurs.
    #[must_use]
    pub fn with_digest(digest: DigestFunction) -> Self {
        Self {
            buckets: BTreeMap::new(),
            deduplicated_observations: 0,
            digest,
            edges: Vec::new(),
            nodes: Vec::new(),
            observations: 0,
        }
    }
}

impl Default for ExactStateGraph {
    fn default() -> Self {
        Self::new()
    }
}

/// Returns the only execution mode admitted by this exact research baseline.
#[must_use]
pub const fn admitted_mode() -> ExecutionMode {
    ExecutionMode::Interpreter
}

/// Digest function that deliberately maps every state to one bucket.
///
/// This exists to make collision-safety testable: exact confirmation must still
/// keep distinct snapshots separate.
#[must_use]
pub const fn constant_collision_digest(_snapshot: &ExactStateSnapshot) -> u64 {
    0
}

fn exact_snapshot(
    machine: &Machine,
    input: &[u8],
) -> Result<ExactStateSnapshot, StateGraphError> {
    Ok(ExactStateSnapshot {
        input: input.into(),
        input_consumed: machine.input_consumed(),
        memory: memory_snapshot(machine)?,
        output: machine.output().into(),
        profile_id: HISTORICAL_PROFILE_ID,
        registers: machine.registers(),
        termination: machine.termination(),
    })
}

fn exact_state_digest(snapshot: &ExactStateSnapshot) -> u64 {
    let mut hash = FNV_OFFSET;
    hash = hash_bytes(hash, snapshot.profile_id.as_bytes());
    hash = hash_bytes(hash, &snapshot.input);
    hash = hash_usize(hash, snapshot.input_consumed);
    hash = hash_bytes(hash, &snapshot.output);
    hash = hash_word(hash, snapshot.registers.accumulator);
    hash = hash_word(hash, snapshot.registers.code_pointer);
    hash = hash_word(hash, snapshot.registers.data_pointer);
    hash = hash_byte(hash, termination_tag(snapshot.termination));
    for value in &snapshot.memory {
        hash = hash_bytes(hash, &value.to_le_bytes());
    }
    hash
}

/// Builds the first proved reduced key by dropping consumed input contents.
///
/// # Errors
///
/// Returns [`StateGraphError`] when memory observation fails or the caller's
/// input bytes cannot represent the machine's committed cursor.
pub fn future_input_snapshot(
    machine: &Machine,
    input: &[u8],
) -> Result<FutureInputSnapshot, StateGraphError> {
    let cursor = machine.input_consumed();
    let remaining_input = input
        .get(cursor..)
        .ok_or(StateGraphError::InputCursorOutOfRange)?;
    Ok(FutureInputSnapshot {
        input_consumed: cursor,
        memory: memory_snapshot(machine)?,
        output: machine.output().into(),
        profile_id: HISTORICAL_PROFILE_ID,
        registers: machine.registers(),
        remaining_input: remaining_input.into(),
        termination: machine.termination(),
    })
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

fn hash_usize(hash: u64, value: usize) -> u64 {
    hash_bytes(hash, &value.to_le_bytes())
}

fn hash_word(hash: u64, value: Word) -> u64 {
    hash_bytes(hash, &value.value().to_le_bytes())
}

fn memory_snapshot(machine: &Machine) -> Result<MemoryImage, StateGraphError> {
    let mut memory = Vec::with_capacity(MEMORY_WORDS);
    for raw in 0..MEMORY_WORDS {
        let raw_word = u16::try_from(raw)
            .map_err(|_error| StateGraphError::NodeIdentityOverflow)?;
        let address = Word::new(raw_word)
            .map_err(|_error| StateGraphError::NodeIdentityOverflow)?;
        let value = machine
            .memory_word(address)
            .map_err(StateGraphError::Memory)?;
        memory.push(value.value());
    }
    Ok(memory.into_boxed_slice())
}

const fn normalize_step_result(
    result: Result<StepOutcome, MachineError>,
) -> Result<ExactStepResult, StateGraphError> {
    match result {
        Ok(StepOutcome::Continued) => Ok(ExactStepResult {
            kind: ExactStepKind::Continued,
            pointer: 0,
            value: 0,
        }),
        Ok(StepOutcome::Terminated(reason)) => Ok(ExactStepResult {
            kind: ExactStepKind::Terminated(reason),
            pointer: 0,
            value: 0,
        }),
        Err(
            MachineError::InvalidEncryptionTarget { pointer, value }
            | MachineError::UnsupportedInterpreterBehavior(
                InterpreterUndefinedBehavior::InvalidSelfEncryptionTarget {
                    pointer,
                    value,
                },
            ),
        ) => Ok(ExactStepResult {
            kind: ExactStepKind::RejectedEncryption,
            pointer: pointer.value(),
            value: value.value(),
        }),
        Err(error) => Err(StateGraphError::UnexpectedMachine(error)),
    }
}

/// Builds a reduced future key for an already terminated classic machine.
///
/// # Errors
///
/// Returns [`StateGraphError::MachineNotTerminated`] while execution is live.
pub fn terminal_future_snapshot(
    machine: &Machine,
) -> Result<TerminalFutureSnapshot, StateGraphError> {
    let termination = machine
        .termination()
        .ok_or(StateGraphError::MachineNotTerminated)?;
    Ok(TerminalFutureSnapshot {
        output: machine.output().into(),
        profile_id: HISTORICAL_PROFILE_ID,
        termination,
    })
}

const fn termination_tag(termination: Option<Termination>) -> u8 {
    match termination {
        None => 0,
        Some(Termination::HaltInstruction) => 1,
        Some(Termination::NonGraphicalCell) => 2,
    }
}
