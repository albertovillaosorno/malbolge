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
//   - Product-owned reduced dependency identity for register-masked v6 AOT
//     graph evidence.
// - Must-Not:
//   - Trust research types, infer unproved dependencies, execute native code,
//     or skip successor guards.
// - Allows:
//   - Inputs: exact witness checkpoints, v6 programs, claimed dependency
//     identities, and topology.
//   - Outputs: replay-admitted reduced graph evidence and candidate guard
//     checks.
//   - Side effects: normative VM replay and process-local allocation only.
// - Split-When:
//   - Runtime graph dispatch or durable reduced-graph serialization gains
//     ownership.
// - Merge-When:
//   - Exact and reduced graph admission share one proved identity model.
// - Summary:
//   - Imports reduced graph evidence without trusting research implementation.
// - Description:
//   - Reprojects v6 from exact witnesses and derives every reduced guard field.
// - Usage:
//   - AOT preparation/import boundary before guarded native graph dispatch.
// - Defaults:
//   - Any identity, program, edge, or topology mismatch rejects atomically.
//

//! Product-owned admission for reduced register-masked v6 graph evidence.

use malbolge::{
    MemoryLiveIn, ProfileExecutionGeometry, ProfileMachine,
    ProfileMachineError, ProfileMachineState, ProfileRegisterSet,
    ProfileRegisters, ProfileStepTrace, RegisterMaskedRegionEffectProgram,
    RegisterMaskedRegionProjectionError, RunOutcome, Termination, TraceInput,
};

use super::{Display, FormatResult, Formatter};

/// Caller-supplied reduced dependency identity with no verification authority.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RegisterMaskedDependencyIdentityClaim {
    /// Opaque exact execution geometry required by the region.
    pub geometry: ProfileExecutionGeometry,
    /// Ordered verifier-claimed entry-memory live-ins.
    pub memory_live_ins: Vec<MemoryLiveIn>,
    /// Entry registers selected by the claimed live-in mask.
    pub register_live_ins: ProfileRegisterSet,
    /// Claimed entry register values; non-live fields must be zero.
    pub register_values: ProfileRegisters,
    /// Ordered input observations relative to the candidate cursor.
    pub relative_inputs: Vec<TraceInput>,
    /// Required prior termination state.
    pub termination: Option<Termination>,
}

/// One explicitly untrusted dependency-reduced v6 graph node.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AheadOfExecutionRegisterMaskedReducedStateGraphNodeClaim {
    /// Claimed reduced identity independently derived during admission.
    pub identity: RegisterMaskedDependencyIdentityClaim,
    /// Claimed register-masked v6 bounded-region effect program.
    pub program: RegisterMaskedRegionEffectProgram,
    /// Claimed successor node after budget exhaustion.
    pub successor: Option<usize>,
    /// Complete exact witness used only for deterministic verification.
    pub witness: ProfileMachineState,
}

/// Explicitly untrusted dependency-reduced finite graph evidence.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct UntrustedAheadOfExecutionRegisterMaskedReducedStateGraph {
    entry: usize,
    nodes: Vec<AheadOfExecutionRegisterMaskedReducedStateGraphNodeClaim>,
}

/// Verifier-derived reduced identity safe only as a runtime guard predicate.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedRegisterMaskedDependencyIdentity {
    geometry: ProfileExecutionGeometry,
    memory_live_ins: Vec<MemoryLiveIn>,
    register_live_ins: ProfileRegisterSet,
    register_values: ProfileRegisters,
    relative_inputs: Vec<TraceInput>,
    termination: Option<Termination>,
}

/// One replay-verified dependency-reduced graph node.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedAheadOfExecutionRegisterMaskedReducedStateGraphNode {
    identity: VerifiedRegisterMaskedDependencyIdentity,
    program: RegisterMaskedRegionEffectProgram,
    successor: Option<usize>,
}

type VerifiedReducedNode =
    VerifiedAheadOfExecutionRegisterMaskedReducedStateGraphNode;

/// Replay-admitted dependency-reduced topology with no execution authority.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedAheadOfExecutionRegisterMaskedReducedStateGraph {
    entry: usize,
    nodes: Vec<VerifiedAheadOfExecutionRegisterMaskedReducedStateGraphNode>,
}

/// Failure while independently admitting reduced v6 graph evidence.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum AheadOfExecutionRegisterMaskedReducedStateGraphError {
    /// Two nodes claim the same complete reduced dependency identity.
    DuplicateIdentity {
        /// Earlier duplicate node index.
        first: usize,
        /// Later duplicate node index.
        index: usize,
    },
    /// At least one graph node is required.
    Empty,
    /// The declared graph entry index is outside the node array.
    EntryOutOfRange {
        /// Invalid graph entry index.
        entry: usize,
    },
    /// Claimed dependency identity differs from verifier-derived identity.
    IdentityMismatch {
        /// Zero-based mismatching node index.
        index: usize,
    },
    /// Normative witness execution failed.
    Machine {
        /// Zero-based failing node index.
        index: usize,
        /// Exact normative VM failure.
        error: ProfileMachineError,
    },
    /// A budget-exhausted node omits its required successor.
    MissingSuccessor {
        /// Zero-based open node index.
        index: usize,
    },
    /// Claimed v6 program differs from normative witness reprojection.
    ProgramMismatch {
        /// Zero-based mismatching node index.
        index: usize,
    },
    /// Normative bounded-region reprojection failed.
    Projection {
        /// Zero-based failing node index.
        index: usize,
        /// Exact v6 projection failure.
        error: RegisterMaskedRegionProjectionError,
    },
    /// Witness exit does not satisfy the claimed successor dependency guard.
    SuccessorIdentityMismatch {
        /// Zero-based source node index.
        index: usize,
        /// Claimed successor index.
        successor: usize,
    },
    /// One successor points outside the finite node array.
    SuccessorOutOfRange {
        /// Zero-based source node index.
        index: usize,
        /// Invalid successor index.
        successor: usize,
    },
    /// A terminated bounded transition incorrectly claims a successor.
    TerminalSuccessor {
        /// Zero-based terminal node index.
        index: usize,
    },
    /// One node is outside the declared entry's successor closure.
    Unreachable {
        /// First unreachable node index.
        index: usize,
    },
}

type ReducedGraphError = AheadOfExecutionRegisterMaskedReducedStateGraphError;
type VerifiedNodeReplay = (
    VerifiedRegisterMaskedDependencyIdentity,
    ProfileMachineState,
);
type VerifiedNodeSet = (Vec<VerifiedReducedNode>, Vec<ProfileMachineState>);

impl Display for AheadOfExecutionRegisterMaskedReducedStateGraphError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::DuplicateIdentity { first, index } => write!(
                f,
                "reduced v6 AOT nodes {first} and {index} duplicate identity"
            ),
            Self::Empty => f.write_str("reduced v6 AOT graph requires a node"),
            Self::EntryOutOfRange { entry } => {
                write!(f, "reduced v6 AOT graph entry {entry} is out of range")
            },
            Self::IdentityMismatch { index } => {
                write!(
                    f,
                    "reduced v6 AOT graph node {index} identity mismatched"
                )
            },
            Self::Machine { error, index } => {
                write!(f, "reduced v6 AOT graph node {index} failed: {error}")
            },
            Self::MissingSuccessor { index } => {
                write!(f, "reduced v6 AOT graph node {index} is open")
            },
            Self::ProgramMismatch { index } => {
                write!(
                    f,
                    "reduced v6 AOT graph node {index} program mismatched"
                )
            },
            Self::Projection { index, .. } => {
                write!(f, "reduced v6 AOT graph node {index} projection failed")
            },
            Self::SuccessorOutOfRange { index, successor } => write!(
                f,
                "reduced v6 AOT graph {index} has invalid successor {successor}"
            ),
            Self::SuccessorIdentityMismatch { index, successor } => write!(
                f,
                "reduced v6 edge {index}->{successor} missed successor guard"
            ),
            Self::TerminalSuccessor { index } => write!(
                f,
                "reduced v6 AOT terminal node {index} has a successor"
            ),
            Self::Unreachable { index } => {
                write!(f, "reduced v6 AOT graph node {index} is unreachable")
            },
        }
    }
}

impl RegisterMaskedDependencyIdentityClaim {
    /// Derives one untrusted reduced identity proposal from a witness/program.
    ///
    /// This helper grants no authority; graph admission derives the same fields
    /// independently after normative replay and exact v6 reprojection.
    #[must_use]
    pub fn from_witness_and_program(
        witness: &ProfileMachineState,
        program: &RegisterMaskedRegionEffectProgram,
    ) -> Self {
        let register_values = masked_register_values(
            witness.registers(),
            program.register_live_ins,
        );
        Self {
            geometry: witness.geometry(),
            memory_live_ins: program.program.memory_live_ins.clone(),
            register_live_ins: program.register_live_ins,
            register_values,
            relative_inputs: relative_inputs(program),
            termination: witness.io().termination(),
        }
    }
}

impl VerifiedRegisterMaskedDependencyIdentity {
    /// Returns true only when a complete checkpoint satisfies this reduced
    /// guard.
    #[must_use]
    pub fn matches(&self, candidate: &ProfileMachineState) -> bool {
        self.geometry == candidate.geometry()
            && self.termination == candidate.io().termination()
            && registers_match(
                self.register_values,
                candidate.registers(),
                self.register_live_ins,
            )
            && memory_matches(&self.memory_live_ins, candidate.memory())
            && input_matches(&self.relative_inputs, candidate.io())
    }

    /// Returns the verifier-derived entry-memory live-ins.
    #[must_use]
    pub fn memory_live_ins(&self) -> &[MemoryLiveIn] {
        &self.memory_live_ins
    }

    /// Returns the verifier-derived entry-register live-in mask.
    #[must_use]
    pub const fn register_live_ins(&self) -> ProfileRegisterSet {
        self.register_live_ins
    }

    /// Returns masked live register values; non-live values are zero.
    #[must_use]
    pub const fn register_values(&self) -> ProfileRegisters {
        self.register_values
    }

    /// Returns ordered input observations relative to the candidate cursor.
    #[must_use]
    pub fn relative_inputs(&self) -> &[TraceInput] {
        &self.relative_inputs
    }
}

impl UntrustedAheadOfExecutionRegisterMaskedReducedStateGraph {
    /// Constructs explicitly untrusted dependency-reduced graph evidence.
    #[must_use]
    pub const fn new(
        entry: usize,
        nodes: Vec<AheadOfExecutionRegisterMaskedReducedStateGraphNodeClaim>,
    ) -> Self {
        Self { entry, nodes }
    }

    /// Replays all witnesses and independently admits reduced identities/edges.
    ///
    /// # Errors
    ///
    /// Returns a typed mismatch for false identity, program, topology, or edge
    /// claims. The result grants no native execution or dispatch authority.
    pub fn verify(
        &self,
    ) -> Result<
        VerifiedAheadOfExecutionRegisterMaskedReducedStateGraph,
        AheadOfExecutionRegisterMaskedReducedStateGraphError,
    > {
        verify_reduced_graph(self)
    }
}

impl VerifiedAheadOfExecutionRegisterMaskedReducedStateGraph {
    /// Returns the zero-based admitted graph entry node.
    #[must_use]
    pub const fn entry(&self) -> usize {
        self.entry
    }

    /// Reports whether the graph contains no admitted nodes.
    #[must_use]
    pub const fn is_empty(&self) -> bool {
        self.nodes.is_empty()
    }

    /// Returns the admitted node count.
    #[must_use]
    pub const fn len(&self) -> usize {
        self.nodes.len()
    }

    /// Returns one admitted reduced graph node by index.
    #[must_use]
    pub fn node(
        &self,
        index: usize,
    ) -> Option<&VerifiedAheadOfExecutionRegisterMaskedReducedStateGraphNode>
    {
        self.nodes.get(index)
    }
}

impl VerifiedAheadOfExecutionRegisterMaskedReducedStateGraphNode {
    /// Returns the verifier-derived reduced entry guard.
    #[must_use]
    pub const fn identity(&self) -> &VerifiedRegisterMaskedDependencyIdentity {
        &self.identity
    }

    /// Returns the exactly reprojected product-owned v6 program.
    #[must_use]
    pub const fn program(&self) -> &RegisterMaskedRegionEffectProgram {
        &self.program
    }

    /// Returns the admitted successor index after budget exhaustion.
    #[must_use]
    pub const fn successor(&self) -> Option<usize> {
        self.successor
    }
}

fn derive_identity(
    witness: &ProfileMachineState,
    program: &RegisterMaskedRegionEffectProgram,
) -> VerifiedRegisterMaskedDependencyIdentity {
    VerifiedRegisterMaskedDependencyIdentity {
        geometry: witness.geometry(),
        memory_live_ins: program.program.memory_live_ins.clone(),
        register_live_ins: program.register_live_ins,
        register_values: masked_register_values(
            witness.registers(),
            program.register_live_ins,
        ),
        relative_inputs: relative_inputs(program),
        termination: witness.io().termination(),
    }
}

fn input_matches(
    inputs: &[TraceInput],
    io: &malbolge::ProfileMachineIoState,
) -> bool {
    let mut cursor = io.input_consumed();
    for input in inputs {
        match input {
            TraceInput::Byte(byte) => {
                if io.input().get(cursor).copied() != Some(*byte) {
                    return false;
                }
                cursor = cursor.saturating_add(1);
            },
            TraceInput::EndOfInput => {
                if cursor != io.input().len() {
                    return false;
                }
            },
        }
    }
    true
}

const fn masked_register_values(
    registers: ProfileRegisters,
    live_ins: ProfileRegisterSet,
) -> ProfileRegisters {
    ProfileRegisters {
        accumulator: if live_ins.accumulator {
            registers.accumulator
        } else {
            0
        },
        code_pointer: if live_ins.code_pointer {
            registers.code_pointer
        } else {
            0
        },
        data_pointer: if live_ins.data_pointer {
            registers.data_pointer
        } else {
            0
        },
    }
}

fn memory_matches(live_ins: &[MemoryLiveIn], memory: &[u32]) -> bool {
    live_ins.iter().all(|live_in| {
        usize::try_from(live_in.address)
            .ok()
            .and_then(|index| memory.get(index))
            .copied()
            == Some(live_in.value)
    })
}

const fn registers_match(
    expected: ProfileRegisters,
    candidate: ProfileRegisters,
    live_ins: ProfileRegisterSet,
) -> bool {
    (!live_ins.accumulator || expected.accumulator == candidate.accumulator)
        && (!live_ins.code_pointer
            || expected.code_pointer == candidate.code_pointer)
        && (!live_ins.data_pointer
            || expected.data_pointer == candidate.data_pointer)
}

fn relative_inputs(
    program: &RegisterMaskedRegionEffectProgram,
) -> Vec<TraceInput> {
    program
        .program
        .effects
        .iter()
        .filter_map(|effect| effect.input)
        .collect()
}

fn verify_node(
    claim: &AheadOfExecutionRegisterMaskedReducedStateGraphNodeClaim,
    index: usize,
) -> Result<VerifiedNodeReplay, ReducedGraphError> {
    let mut machine = ProfileMachine::from_snapshot(claim.witness.clone());
    let mut traces = Vec::new();
    let outcome = machine
        .run_traced(
            claim.program.program.step_budget,
            &mut |trace: &ProfileStepTrace| traces.push(*trace),
        )
        .map_err(|error| ReducedGraphError::Machine { index, error })?;
    let projected =
        RegisterMaskedRegionEffectProgram::from_profile_region_traces(
            claim.witness.profile(),
            &traces,
            claim.program.program.step_budget,
            outcome,
        )
        .map_err(|error| ReducedGraphError::Projection { index, error })?;
    if projected != claim.program {
        return Err(ReducedGraphError::ProgramMismatch { index });
    }
    let identity = derive_identity(&claim.witness, &projected);
    if claim.identity
        != (RegisterMaskedDependencyIdentityClaim {
            geometry: identity.geometry,
            memory_live_ins: identity.memory_live_ins.clone(),
            register_live_ins: identity.register_live_ins,
            register_values: identity.register_values,
            relative_inputs: identity.relative_inputs.clone(),
            termination: identity.termination,
        })
    {
        return Err(ReducedGraphError::IdentityMismatch { index });
    }
    Ok((identity, machine.snapshot_state()))
}

fn verify_reachable(
    claim: &UntrustedAheadOfExecutionRegisterMaskedReducedStateGraph,
) -> Result<(), ReducedGraphError> {
    let mut reachable = vec![false; claim.nodes.len()];
    let mut current = Some(claim.entry);
    while let Some(index) = current {
        let node = claim
            .nodes
            .get(index)
            .ok_or(ReducedGraphError::EntryOutOfRange { entry: index })?;
        let reached = reachable
            .get_mut(index)
            .ok_or(ReducedGraphError::EntryOutOfRange { entry: index })?;
        if *reached {
            break;
        }
        *reached = true;
        current = node.successor;
    }
    reachable
        .iter()
        .position(|value| !*value)
        .map_or(Ok(()), |index| {
            Err(ReducedGraphError::Unreachable { index })
        })
}

fn verify_claim_shape(
    claim: &UntrustedAheadOfExecutionRegisterMaskedReducedStateGraph,
) -> Result<(), ReducedGraphError> {
    if claim.nodes.is_empty() {
        return Err(ReducedGraphError::Empty);
    }
    if claim.entry >= claim.nodes.len() {
        return Err(ReducedGraphError::EntryOutOfRange { entry: claim.entry });
    }
    for (index, node) in claim.nodes.iter().enumerate() {
        if let Some(successor) = node.successor
            && successor >= claim.nodes.len()
        {
            return Err(ReducedGraphError::SuccessorOutOfRange {
                index,
                successor,
            });
        }
    }
    Ok(())
}

fn verify_edges(
    claim: &UntrustedAheadOfExecutionRegisterMaskedReducedStateGraph,
    verified_nodes: &[VerifiedReducedNode],
    exits: &[ProfileMachineState],
) -> Result<(), ReducedGraphError> {
    for (index, node) in claim.nodes.iter().enumerate() {
        match node.program.program.outcome {
            RunOutcome::BudgetExhausted { .. } => {
                let successor = node
                    .successor
                    .ok_or(ReducedGraphError::MissingSuccessor { index })?;
                let successor_node = verified_nodes.get(successor).ok_or(
                    ReducedGraphError::SuccessorOutOfRange { index, successor },
                )?;
                let exit = exits.get(index).ok_or(
                    ReducedGraphError::EntryOutOfRange { entry: index },
                )?;
                if !successor_node.identity.matches(exit) {
                    return Err(ReducedGraphError::SuccessorIdentityMismatch {
                        index,
                        successor,
                    });
                }
            },
            RunOutcome::Terminated { .. } => {
                if node.successor.is_some() {
                    return Err(ReducedGraphError::TerminalSuccessor { index });
                }
            },
        }
    }
    Ok(())
}

fn verify_nodes(
    claim: &UntrustedAheadOfExecutionRegisterMaskedReducedStateGraph,
) -> Result<VerifiedNodeSet, ReducedGraphError> {
    let mut verified_nodes: Vec<VerifiedReducedNode> =
        Vec::with_capacity(claim.nodes.len());
    let mut exits = Vec::with_capacity(claim.nodes.len());
    for (index, node) in claim.nodes.iter().enumerate() {
        let (identity, exit) = verify_node(node, index)?;
        if let Some(first) = verified_nodes
            .iter()
            .position(|candidate| candidate.identity == identity)
        {
            return Err(ReducedGraphError::DuplicateIdentity { first, index });
        }
        exits.push(exit);
        verified_nodes.push(VerifiedReducedNode {
            identity,
            program: node.program.clone(),
            successor: node.successor,
        });
    }
    Ok((verified_nodes, exits))
}

fn verify_reduced_graph(
    claim: &UntrustedAheadOfExecutionRegisterMaskedReducedStateGraph,
) -> Result<
    VerifiedAheadOfExecutionRegisterMaskedReducedStateGraph,
    ReducedGraphError,
> {
    verify_claim_shape(claim)?;
    let (verified_nodes, exits) = verify_nodes(claim)?;
    verify_edges(claim, &verified_nodes, &exits)?;
    verify_reachable(claim)?;
    Ok(VerifiedAheadOfExecutionRegisterMaskedReducedStateGraph {
        entry: claim.entry,
        nodes: verified_nodes,
    })
}
