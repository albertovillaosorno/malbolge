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
//   - Deterministic admission of finite register-masked v6 AOT graph claims.
// - Must-Not:
//   - Trust research topology, infer reduced-state equivalence, execute native
//     code, or publish partially prepared graphs.
// - Allows:
//   - Inputs: complete VM checkpoints, v6 portable IR, and claimed successors.
//   - Outputs: replay-verified topology plus one sealed v6 native artifact set.
//   - Side effects: normative VM replay and process-local native preparation.
// - Split-When:
//   - Dependency-reduced node identity gains independent proof evidence.
// - Merge-When:
//   - General AOT graph admission subsumes register-masked region replay.
// - Summary:
//   - Replays every bounded v6 node and proves exact closed transitions.
// - Description:
//   - Full checkpoints remain topology authority; v6 IR is reprojected.
// - Usage:
//   - Called during AOT preparation before any graph-native runtime dispatch.
// - Defaults:
//   - Open, unreachable, duplicate, tampered, or failed nodes reject
//     atomically.
//

//! Verifier-admitted finite register-masked v6 state-graph preparation.

use malbolge::{
    ProfileMachine, ProfileMachineError, ProfileMachineState, ProfileStepTrace,
    RegisterMaskedRegionEffectProgram, RegisterMaskedRegionProjectionError,
    RunOutcome,
};

use super::{
    AheadOfExecutionRegisterMaskedPreparationError, DirectHost, Display,
    FormatResult, Formatter, RuntimeCapability,
    VerifiedAheadOfExecutionRegisterMaskedSet,
    prepare_register_masked_set_iter,
};

/// One explicitly untrusted register-masked v6 graph node claim.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AheadOfExecutionRegisterMaskedStateGraphNodeClaim {
    /// Complete exact machine state at bounded-region entry.
    pub entry: ProfileMachineState,
    /// Claimed register-masked v6 portable effect program.
    pub program: RegisterMaskedRegionEffectProgram,
    /// Claimed next node after budget exhaustion, or none after termination.
    pub successor: Option<usize>,
}

/// Explicitly untrusted finite register-masked v6 graph claim.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct UntrustedAheadOfExecutionRegisterMaskedStateGraph {
    entry: usize,
    nodes: Vec<AheadOfExecutionRegisterMaskedStateGraphNodeClaim>,
}

/// Failure while deterministically verifying one finite v6 state graph.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum AheadOfExecutionRegisterMaskedStateGraphError {
    /// Two nodes claim the same complete entry state.
    DuplicateEntry {
        /// Earlier duplicate node index.
        first: usize,
        /// Later duplicate node index.
        index: usize,
    },
    /// A graph must contain at least one node.
    Empty,
    /// The declared graph entry index is outside the node array.
    EntryOutOfRange {
        /// Invalid declared graph entry index.
        entry: usize,
    },
    /// Normative execution rejected one claimed bounded transition.
    Machine {
        /// Zero-based failing node index.
        index: usize,
        /// Exact normative VM failure.
        error: ProfileMachineError,
    },
    /// One budget-exhausted node omits its required successor.
    MissingSuccessor {
        /// Zero-based open node index.
        index: usize,
    },
    /// A claimed v6 program differs from normative multi-step reprojection.
    ProgramMismatch {
        /// Zero-based mismatching node index.
        index: usize,
    },
    /// Normative region projection failed for one bounded transition.
    Projection {
        /// Zero-based failing node index.
        index: usize,
        /// Exact v6 region projection failure.
        error: RegisterMaskedRegionProjectionError,
    },
    /// One successor points outside the finite node array.
    SuccessorOutOfRange {
        /// Zero-based source node index.
        index: usize,
        /// Invalid successor index.
        successor: usize,
    },
    /// Normative exit state differs from the claimed successor entry.
    SuccessorStateMismatch {
        /// Zero-based source node index.
        index: usize,
        /// Claimed successor index.
        successor: usize,
    },
    /// A terminated bounded transition incorrectly claims another successor.
    TerminalSuccessor {
        /// Zero-based terminal node index.
        index: usize,
    },
    /// A node exists outside the graph entry's reachable closure.
    Unreachable {
        /// First unreachable node index.
        index: usize,
    },
}

type GraphError = AheadOfExecutionRegisterMaskedStateGraphError;

/// Verified finite exact topology whose node programs are v6 bounded regions.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedAheadOfExecutionRegisterMaskedStateGraph {
    entry: usize,
    nodes: Vec<AheadOfExecutionRegisterMaskedStateGraphNodeClaim>,
}

/// Fully verified v6 graph plus all currently supported native fast paths.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PreparedAheadOfExecutionRegisterMaskedStateGraph {
    graph: VerifiedAheadOfExecutionRegisterMaskedStateGraph,
    native: VerifiedAheadOfExecutionRegisterMaskedSet,
}

/// Failure while verifying and atomically preparing one v6 state graph.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum AheadOfExecutionRegisterMaskedStateGraphPreparationError<'requirement>
{
    /// Register-masked graph verification failed before native preparation.
    Graph(AheadOfExecutionRegisterMaskedStateGraphError),
    /// One verified graph node failed v6 native fast-path preparation.
    Native(AheadOfExecutionRegisterMaskedPreparationError<'requirement>),
}

impl Display for AheadOfExecutionRegisterMaskedStateGraphError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::DuplicateEntry { first, index } => write!(
                f,
                "v6 AOT graph nodes {first} and {index} duplicate entry state"
            ),
            Self::Empty => f.write_str("v6 AOT state graph requires a node"),
            Self::EntryOutOfRange { entry } => {
                write!(f, "v6 AOT graph entry {entry} is out of range")
            },
            Self::Machine { error, index } => {
                write!(f, "v6 AOT graph node {index} failed: {error}")
            },
            Self::MissingSuccessor { index } => {
                write!(f, "v6 AOT graph node {index} is open")
            },
            Self::ProgramMismatch { index } => {
                write!(f, "v6 AOT graph node {index} program was not verified")
            },
            Self::Projection { index, .. } => {
                write!(f, "v6 AOT graph node {index} projection failed")
            },
            Self::SuccessorOutOfRange { index, successor } => write!(
                f,
                "v6 AOT graph {index} has out-of-range successor {successor}"
            ),
            Self::SuccessorStateMismatch { index, successor } => write!(
                f,
                "v6 AOT graph edge {index}->{successor} changed exact state"
            ),
            Self::TerminalSuccessor { index } => {
                write!(f, "v6 AOT graph terminal node {index} has a successor")
            },
            Self::Unreachable { index } => {
                write!(f, "v6 AOT graph node {index} is unreachable")
            },
        }
    }
}

impl Display for AheadOfExecutionRegisterMaskedStateGraphPreparationError<'_> {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Graph(error) => Display::fmt(error, f),
            Self::Native(error) => Display::fmt(error, f),
        }
    }
}

impl UntrustedAheadOfExecutionRegisterMaskedStateGraph {
    /// Constructs an explicitly untrusted finite v6 state-graph claim.
    #[must_use]
    pub const fn new(
        entry: usize,
        nodes: Vec<AheadOfExecutionRegisterMaskedStateGraphNodeClaim>,
    ) -> Self {
        Self { entry, nodes }
    }

    /// Replays every bounded node and admits only exact closed topology.
    ///
    /// # Errors
    ///
    /// Returns a graph error when topology or normative v6 reprojection
    /// differs.
    pub fn verify(
        &self,
    ) -> Result<
        VerifiedAheadOfExecutionRegisterMaskedStateGraph,
        AheadOfExecutionRegisterMaskedStateGraphError,
    > {
        verify_register_masked_state_graph_claim(self)?;
        Ok(VerifiedAheadOfExecutionRegisterMaskedStateGraph {
            entry: self.entry,
            nodes: self.nodes.clone(),
        })
    }
}

impl VerifiedAheadOfExecutionRegisterMaskedStateGraph {
    /// Returns the zero-based verified graph entry node.
    #[must_use]
    pub const fn entry(&self) -> usize {
        self.entry
    }

    /// Reports whether the verified graph contains no nodes.
    #[must_use]
    pub const fn is_empty(&self) -> bool {
        self.nodes.is_empty()
    }

    /// Returns the number of verifier-admitted exact entry states.
    #[must_use]
    pub const fn len(&self) -> usize {
        self.nodes.len()
    }

    /// Returns one verifier-admitted bounded-region node by zero-based index.
    #[must_use]
    pub fn node(
        &self,
        index: usize,
    ) -> Option<&AheadOfExecutionRegisterMaskedStateGraphNodeClaim> {
        self.nodes.get(index)
    }
}

impl PreparedAheadOfExecutionRegisterMaskedStateGraph {
    /// Returns the replay-verified finite v6 topology.
    #[must_use]
    pub const fn graph(
        &self,
    ) -> &VerifiedAheadOfExecutionRegisterMaskedStateGraph {
        &self.graph
    }

    /// Returns the sealed native v6 set prepared for every graph node.
    #[must_use]
    pub const fn native(&self) -> &VerifiedAheadOfExecutionRegisterMaskedSet {
        &self.native
    }
}

/// Verifies v6 graph closure and transactionally prepares every native node.
///
/// # Errors
///
/// Returns graph verification failures before native work. Native preparation
/// remains all-or-nothing and may reject verified multi-step programs until a
/// matching direct shape exists.
pub fn prepare_ahead_of_execution_register_masked_state_graph<'requirement>(
    claim: &'requirement UntrustedAheadOfExecutionRegisterMaskedStateGraph,
    runtime: &'static RuntimeCapability,
    host: DirectHost,
) -> Result<
    PreparedAheadOfExecutionRegisterMaskedStateGraph,
    AheadOfExecutionRegisterMaskedStateGraphPreparationError<'requirement>,
> {
    verify_register_masked_state_graph_claim(claim).map_err(
        AheadOfExecutionRegisterMaskedStateGraphPreparationError::Graph,
    )?;
    let native = prepare_register_masked_set_iter(
        claim.nodes.iter().map(|node| &node.program),
        runtime,
        host,
    )
    .map_err(
        AheadOfExecutionRegisterMaskedStateGraphPreparationError::Native,
    )?;
    Ok(PreparedAheadOfExecutionRegisterMaskedStateGraph {
        graph: VerifiedAheadOfExecutionRegisterMaskedStateGraph {
            entry: claim.entry,
            nodes: claim.nodes.clone(),
        },
        native,
    })
}

fn verify_node(
    claim: &UntrustedAheadOfExecutionRegisterMaskedStateGraph,
    index: usize,
    node: &AheadOfExecutionRegisterMaskedStateGraphNodeClaim,
) -> Result<(), GraphError> {
    let mut machine = ProfileMachine::from_snapshot(node.entry.clone());
    let mut traces = Vec::new();
    let outcome = machine
        .run_traced(
            node.program.step_budget,
            &mut |trace: &ProfileStepTrace| traces.push(*trace),
        )
        .map_err(|error| GraphError::Machine { index, error })?;
    let projected =
        RegisterMaskedRegionEffectProgram::from_profile_region_traces(
            node.entry.profile(),
            &traces,
            node.program.step_budget,
            outcome,
        )
        .map_err(|error| GraphError::Projection { index, error })?;
    if projected != node.program {
        return Err(GraphError::ProgramMismatch { index });
    }
    verify_successor(claim, index, outcome, &machine.snapshot_state())
}

fn verify_reachable(
    claim: &UntrustedAheadOfExecutionRegisterMaskedStateGraph,
) -> Result<(), GraphError> {
    let mut reachable = vec![false; claim.nodes.len()];
    let mut current = Some(claim.entry);
    while let Some(index) = current {
        let Some(node) = claim.nodes.get(index) else {
            return Err(GraphError::EntryOutOfRange { entry: index });
        };
        let Some(reached) = reachable.get_mut(index) else {
            return Err(GraphError::EntryOutOfRange { entry: index });
        };
        if *reached {
            break;
        }
        *reached = true;
        current = node.successor;
    }
    reachable
        .iter()
        .position(|value| !*value)
        .map_or(Ok(()), |index| Err(GraphError::Unreachable { index }))
}

fn verify_register_masked_state_graph_claim(
    claim: &UntrustedAheadOfExecutionRegisterMaskedStateGraph,
) -> Result<(), GraphError> {
    if claim.nodes.is_empty() {
        return Err(GraphError::Empty);
    }
    if claim.entry >= claim.nodes.len() {
        return Err(GraphError::EntryOutOfRange { entry: claim.entry });
    }
    for (index, node) in claim.nodes.iter().enumerate() {
        if let Some(first) = claim.nodes.get(..index).and_then(|prior| {
            prior
                .iter()
                .position(|candidate| candidate.entry == node.entry)
        }) {
            return Err(GraphError::DuplicateEntry { first, index });
        }
        if let Some(successor) = node.successor
            && successor >= claim.nodes.len()
        {
            return Err(GraphError::SuccessorOutOfRange { index, successor });
        }
    }
    for (index, node) in claim.nodes.iter().enumerate() {
        verify_node(claim, index, node)?;
    }
    verify_reachable(claim)
}

fn verify_successor(
    claim: &UntrustedAheadOfExecutionRegisterMaskedStateGraph,
    index: usize,
    outcome: RunOutcome,
    exit: &ProfileMachineState,
) -> Result<(), GraphError> {
    let node = claim
        .nodes
        .get(index)
        .ok_or(GraphError::EntryOutOfRange { entry: index })?;
    match outcome {
        RunOutcome::BudgetExhausted { .. } => {
            let successor = node
                .successor
                .ok_or(GraphError::MissingSuccessor { index })?;
            let successor_node = claim
                .nodes
                .get(successor)
                .ok_or(GraphError::SuccessorOutOfRange { index, successor })?;
            if exit != &successor_node.entry {
                return Err(GraphError::SuccessorStateMismatch {
                    index,
                    successor,
                });
            }
        },
        RunOutcome::Terminated { .. } => {
            if node.successor.is_some() {
                return Err(GraphError::TerminalSuccessor { index });
            }
        },
    }
    Ok(())
}
