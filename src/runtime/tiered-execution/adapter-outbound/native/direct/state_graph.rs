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
//   - Deterministic admission of finite exact-state AOT graph claims.
// - Must-Not:
//   - Trust claimed edges, infer reduced-state equivalence, execute native
//     code,
//   - or publish partially prepared native graphs.
// - Allows:
//   - Inputs: complete VM checkpoints, one-step portable IR, and claimed edges.
//   - Outputs: verified finite topology plus one sealed native artifact set.
//   - Side effects: normative VM replay and process-local native preparation.
// - Split-When:
//   - Reduced dependency-state graph admission gains independent proof
//     evidence.
// - Merge-When:
//   - General AOT graph admission subsumes exact-state verification.
// - Summary:
//   - Replays every claimed node and proves exact closed graph transitions.
// - Description:
//   - Full checkpoints remain verifier authority; claimed IR is reprojected.
// - Usage:
//   - Called during AOT preparation before guest runtime dispatch.
// - Defaults:
//   - Open, unreachable, duplicate, tampered, or failed nodes reject
//     atomically.
//

//! Verifier-admitted finite exact-state graph preparation.

use malbolge::{
    ProfileMachine, ProfileMachineError, ProfileMachineState, ProfileStepTrace,
    RegionEffectProgram, StepOutcome, StepProgramProjectionError,
};

use super::preparation::prepare_ahead_of_execution_native_set_iter;
use super::{
    AheadOfExecutionPreparationError, DirectHost, Display, FormatResult,
    Formatter, RuntimeCapability, VerifiedAheadOfExecutionNativeSet,
};

/// One explicitly untrusted exact-state graph node claim.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AheadOfExecutionStateGraphNodeClaim {
    /// Complete exact machine state at node entry.
    pub entry: ProfileMachineState,
    /// Claimed exact one-step portable effect program.
    pub program: RegionEffectProgram,
    /// Claimed next node after continuation, or none after termination.
    pub successor: Option<usize>,
}

/// Explicitly untrusted finite exact-state graph claim.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct UntrustedAheadOfExecutionStateGraph {
    entry: usize,
    nodes: Vec<AheadOfExecutionStateGraphNodeClaim>,
}

/// Failure while deterministically verifying one finite exact-state graph.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum AheadOfExecutionStateGraphError {
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
    /// Normative execution rejected one claimed node transition.
    Machine {
        /// Zero-based failing node index.
        index: usize,
        /// Exact normative VM failure.
        error: ProfileMachineError,
    },
    /// One continuing node omits its required successor.
    MissingSuccessor {
        /// Zero-based open node index.
        index: usize,
    },
    /// Successful traced execution emitted no trace record.
    MissingTrace {
        /// Zero-based node index.
        index: usize,
    },
    /// A claimed one-step program differs from normative reprojection.
    ProgramMismatch {
        /// Zero-based mismatching node index.
        index: usize,
    },
    /// Normative trace projection failed for one transition.
    Projection {
        /// Zero-based failing node index.
        index: usize,
        /// Exact projection failure.
        error: StepProgramProjectionError,
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
    /// A terminated transition incorrectly claims another successor.
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

/// Verified finite exact-state topology admitted by normative replay.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedAheadOfExecutionStateGraph {
    entry: usize,
    nodes: Vec<AheadOfExecutionStateGraphNodeClaim>,
}

/// Fully verified exact-state graph plus all required native fast paths.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PreparedAheadOfExecutionStateGraph {
    graph: VerifiedAheadOfExecutionStateGraph,
    native: VerifiedAheadOfExecutionNativeSet,
}

/// Failure while verifying and atomically preparing one AOT state graph.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum AheadOfExecutionStateGraphPreparationError<'requirement> {
    /// Exact-state graph verification failed before native preparation.
    Graph(AheadOfExecutionStateGraphError),
    /// One verified graph node failed native fast-path preparation.
    Native(AheadOfExecutionPreparationError<'requirement>),
}

impl Display for AheadOfExecutionStateGraphError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::DuplicateEntry { first, index } => write!(
                f,
                "AOT graph nodes {first} and {index} duplicate entry state"
            ),
            Self::Empty => {
                f.write_str("AOT state graph requires at least one node")
            },
            Self::EntryOutOfRange { entry } => {
                write!(f, "AOT state-graph entry {entry} is out of range")
            },
            Self::Machine { error, index } => {
                write!(f, "AOT state-graph node {index} failed: {error}")
            },
            Self::MissingSuccessor { index } => {
                write!(f, "AOT state-graph node {index} is open")
            },
            Self::MissingTrace { index } => {
                write!(f, "AOT state-graph node {index} emitted no trace")
            },
            Self::ProgramMismatch { index } => {
                write!(
                    f,
                    "AOT state-graph node {index} program was not verified"
                )
            },
            Self::Projection { index, .. } => {
                write!(f, "AOT state-graph node {index} projection failed")
            },
            Self::SuccessorOutOfRange { index, successor } => write!(
                f,
                "AOT graph node {index} successor {successor} is out of range"
            ),
            Self::SuccessorStateMismatch { index, successor } => write!(
                f,
                "AOT state-graph edge {index}->{successor} changed exact state"
            ),
            Self::TerminalSuccessor { index } => write!(
                f,
                "AOT state-graph terminal node {index} claims a successor"
            ),
            Self::Unreachable { index } => {
                write!(f, "AOT state-graph node {index} is unreachable")
            },
        }
    }
}

impl Display for AheadOfExecutionStateGraphPreparationError<'_> {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Graph(error) => Display::fmt(error, f),
            Self::Native(error) => Display::fmt(error, f),
        }
    }
}

impl UntrustedAheadOfExecutionStateGraph {
    /// Constructs an explicitly untrusted finite exact-state graph claim.
    #[must_use]
    pub const fn new(
        entry: usize,
        nodes: Vec<AheadOfExecutionStateGraphNodeClaim>,
    ) -> Self {
        Self { entry, nodes }
    }

    /// Deterministically replays every claimed node and admits exact closure.
    ///
    /// # Errors
    ///
    /// Returns a state-graph error when topology is open, duplicated,
    /// unreachable, out of range, or normative replay differs.
    pub fn verify(
        &self,
    ) -> Result<
        VerifiedAheadOfExecutionStateGraph,
        AheadOfExecutionStateGraphError,
    > {
        verify_state_graph_claim(self)?;
        Ok(VerifiedAheadOfExecutionStateGraph {
            entry: self.entry,
            nodes: self.nodes.clone(),
        })
    }
}

impl VerifiedAheadOfExecutionStateGraph {
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

    /// Returns the number of verifier-admitted exact states.
    #[must_use]
    pub const fn len(&self) -> usize {
        self.nodes.len()
    }

    /// Returns one verifier-admitted node by zero-based index.
    #[must_use]
    pub fn node(
        &self,
        index: usize,
    ) -> Option<&AheadOfExecutionStateGraphNodeClaim> {
        self.nodes.get(index)
    }
}

impl PreparedAheadOfExecutionStateGraph {
    /// Returns the verifier-admitted finite exact-state topology.
    #[must_use]
    pub const fn graph(&self) -> &VerifiedAheadOfExecutionStateGraph {
        &self.graph
    }

    /// Returns the sealed native set prepared for every graph node.
    #[must_use]
    pub const fn native(&self) -> &VerifiedAheadOfExecutionNativeSet {
        &self.native
    }
}

/// Verifies exact graph closure and transactionally prepares every native node.
///
/// # Errors
///
/// Returns graph verification failures before native work. Native preparation
/// then remains all-or-nothing under the ordinary AOT contract.
pub fn prepare_ahead_of_execution_state_graph<'requirement>(
    claim: &'requirement UntrustedAheadOfExecutionStateGraph,
    runtime: &'static RuntimeCapability,
    host: DirectHost,
) -> Result<
    PreparedAheadOfExecutionStateGraph,
    AheadOfExecutionStateGraphPreparationError<'requirement>,
> {
    verify_state_graph_claim(claim)
        .map_err(AheadOfExecutionStateGraphPreparationError::Graph)?;
    let native = prepare_ahead_of_execution_native_set_iter(
        claim.nodes.iter().map(|node| &node.program),
        runtime,
        host,
    )
    .map_err(AheadOfExecutionStateGraphPreparationError::Native)?;
    Ok(PreparedAheadOfExecutionStateGraph {
        graph: VerifiedAheadOfExecutionStateGraph {
            entry: claim.entry,
            nodes: claim.nodes.clone(),
        },
        native,
    })
}

fn verify_state_graph_claim(
    claim: &UntrustedAheadOfExecutionStateGraph,
) -> Result<(), AheadOfExecutionStateGraphError> {
    if claim.nodes.is_empty() {
        return Err(AheadOfExecutionStateGraphError::Empty);
    }
    if claim.entry >= claim.nodes.len() {
        return Err(AheadOfExecutionStateGraphError::EntryOutOfRange {
            entry: claim.entry,
        });
    }
    for (index, node) in claim.nodes.iter().enumerate() {
        if let Some(first) = claim.nodes.get(..index).and_then(|prior| {
            prior
                .iter()
                .position(|candidate| candidate.entry == node.entry)
        }) {
            return Err(AheadOfExecutionStateGraphError::DuplicateEntry {
                first,
                index,
            });
        }
        if let Some(successor) = node.successor
            && successor >= claim.nodes.len()
        {
            return Err(AheadOfExecutionStateGraphError::SuccessorOutOfRange {
                index,
                successor,
            });
        }
    }
    for (index, node) in claim.nodes.iter().enumerate() {
        verify_node(claim, index, node)?;
    }
    verify_reachable(claim)
}

fn verify_reachable(
    claim: &UntrustedAheadOfExecutionStateGraph,
) -> Result<(), AheadOfExecutionStateGraphError> {
    let mut reachable = vec![false; claim.nodes.len()];
    let mut current = Some(claim.entry);
    while let Some(index) = current {
        let Some(node) = claim.nodes.get(index) else {
            return Err(AheadOfExecutionStateGraphError::EntryOutOfRange {
                entry: index,
            });
        };
        let Some(reached) = reachable.get_mut(index) else {
            return Err(AheadOfExecutionStateGraphError::EntryOutOfRange {
                entry: index,
            });
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
        .map_or(Ok(()), |index| {
            Err(AheadOfExecutionStateGraphError::Unreachable { index })
        })
}

fn verify_node(
    claim: &UntrustedAheadOfExecutionStateGraph,
    index: usize,
    node: &AheadOfExecutionStateGraphNodeClaim,
) -> Result<(), AheadOfExecutionStateGraphError> {
    let mut machine = ProfileMachine::from_snapshot(node.entry.clone());
    let mut observed_trace = None;
    let outcome = machine
        .step_traced(&mut |record: &ProfileStepTrace| {
            observed_trace = Some(*record);
        })
        .map_err(|error| AheadOfExecutionStateGraphError::Machine {
            index,
            error,
        })?;
    let trace_record = observed_trace
        .ok_or(AheadOfExecutionStateGraphError::MissingTrace { index })?;
    let projected = RegionEffectProgram::from_profile_step_trace(&trace_record)
        .map_err(|error| AheadOfExecutionStateGraphError::Projection {
            index,
            error,
        })?;
    if projected != node.program {
        return Err(AheadOfExecutionStateGraphError::ProgramMismatch { index });
    }

    match outcome {
        StepOutcome::Continued => {
            let successor = node.successor.ok_or(
                AheadOfExecutionStateGraphError::MissingSuccessor { index },
            )?;
            let successor_node = claim.nodes.get(successor).ok_or(
                AheadOfExecutionStateGraphError::SuccessorOutOfRange {
                    index,
                    successor,
                },
            )?;
            if machine.snapshot_state() != successor_node.entry {
                return Err(
                    AheadOfExecutionStateGraphError::SuccessorStateMismatch {
                        index,
                        successor,
                    },
                );
            }
        },
        StepOutcome::Terminated(_reason) => {
            if node.successor.is_some() {
                return Err(
                    AheadOfExecutionStateGraphError::TerminalSuccessor {
                        index,
                    },
                );
            }
        },
    }
    Ok(())
}
