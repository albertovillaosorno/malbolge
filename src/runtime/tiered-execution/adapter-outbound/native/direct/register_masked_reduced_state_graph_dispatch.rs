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
//   - Bounded AOT-first runtime dispatch across an admitted dependency-reduced
//     register-masked v6 graph.
// - Must-Not:
//   - Infer graph edges, skip node/successor guards, emit artifacts at runtime,
//     or treat unsupported native shapes as semantic failures.
// - Allows:
//   - Inputs: admitted reduced topology, sealed AOT objects, actual runtime
//     checkpoints, host/runtime capability, and a caller-owned native executor.
//   - Outputs: terminal completion, explicit lower-tier fallback, or indexed
//     execution/selection failures.
//   - Side effects: only those performed by the supplied executor port.
// - Split-When:
//   - Executable residency/loading or scheduler policy gains graph ownership.
// - Merge-When:
//   - One general AOT graph coordinator subsumes exact and reduced dispatch.
// - Summary:
//   - Rechecks the actual runtime state before every reduced graph transition.
// - Description:
//   - Exact AOT lookup precedes execution; successor selection is authorized
//     only by the successor's admitted dependency guard on the actual exit.
// - Usage:
//   - Called after reduced graph admission and AOT preparation at guest
//     runtime.
// - Defaults:
//   - Guard miss, unsupported shape, uncovered object, host fallback, or budget
//     exhaustion returns the current state to lower tiers without guessing.
//

//! Bounded runtime dispatch across admitted dependency-reduced v6 AOT graphs.

use std::sync::Arc;

use malbolge::{
    ProfileMachineState, RegisterMaskedRegionEffectProgram, RunOutcome,
};

use super::{
    AheadOfExecutionRegisterMaskedSelectionError,
    AheadOfExecutionRegisterMaskedTier, DirectHost, Display, FormatResult,
    Formatter, RegisterMaskedDirectAdmissionErrorKind, RuntimeCapability,
    VerifiedAheadOfExecutionRegisterMaskedArtifact,
    VerifiedAheadOfExecutionRegisterMaskedReducedStateGraph,
    VerifiedAheadOfExecutionRegisterMaskedReducedStateGraphNode,
    VerifiedAheadOfExecutionRegisterMaskedSet,
    select_ahead_of_execution_register_masked_tier,
};

/// Host/AOT inputs shared by every turn of one reduced-graph dispatch.
#[derive(Clone, Copy, Debug)]
pub struct AheadOfExecutionRegisterMaskedReducedStateGraphDispatchEnvironment<
    'aot,
> {
    aot: &'aot VerifiedAheadOfExecutionRegisterMaskedSet,
    host: DirectHost,
    runtime: &'static RuntimeCapability,
}

/// Failure while coordinating verified reduced-graph native dispatch.
#[derive(Debug, Eq, PartialEq)]
pub enum AheadOfExecutionRegisterMaskedReducedStateGraphDispatchFailure<
    'requirement,
    ExecutorError,
> {
    /// Caller-owned native execution port failed one selected node.
    Execution {
        /// Number of transitions committed before the failing node.
        completed_transitions: usize,
        /// Stable executor-specific failure.
        error: ExecutorError,
        /// Zero-based node whose native execution failed.
        index: usize,
    },
    /// A native guard miss returned an observably changed complete state.
    GuardMissMutation {
        /// Zero-based node whose failed invocation changed state.
        index: usize,
    },
    /// Exact read-only AOT selection rejected a supposedly admitted node.
    Selection {
        /// Exact AOT selection failure.
        error: AheadOfExecutionRegisterMaskedSelectionError<'requirement>,
        /// Zero-based node whose lookup failed.
        index: usize,
    },
    /// Terminal native completion returned a different termination condition.
    TerminalStateMismatch {
        /// Zero-based terminal node whose actual state disagreed.
        index: usize,
    },
    /// Verified topology became internally inconsistent without unsafe code.
    Topology {
        /// Zero-based missing node/successor index.
        index: usize,
    },
}

/// Normal reason reduced-graph native dispatch returns to a lower tier.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum AheadOfExecutionRegisterMaskedReducedStateGraphDispatchFallback {
    /// Native invocation reported a semantic guard miss without mutation.
    NativeGuardMiss {
        /// Zero-based node whose native guard missed.
        index: usize,
    },
    /// The actual state does not satisfy the selected node's admitted guard.
    NodeGuardMiss {
        /// Zero-based node whose reduced guard rejected the runtime state.
        index: usize,
    },
    /// Actual native exit state does not satisfy the admitted successor guard.
    SuccessorGuardMiss {
        /// Zero-based source node whose applied transition completed.
        index: usize,
        /// Claimed successor whose reduced guard rejected the actual exit.
        successor: usize,
    },
    /// The selected host has no supported direct object format.
    TargetInterpreter {
        /// Zero-based node returned to interpreter execution.
        index: usize,
    },
    /// Caller-supplied native transition budget was exhausted safely.
    TransitionBudgetExhausted {
        /// Zero-based node that remains ready for a later dispatch turn.
        index: usize,
    },
    /// No exact precompiled object exists for this admitted semantic node.
    Uncovered {
        /// Zero-based node without an exact current AOT artifact.
        index: usize,
    },
}

/// Successful bounded reduced-graph dispatch result.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum AheadOfExecutionRegisterMaskedReducedStateGraphDispatchOutcome {
    /// A terminal graph node committed through exact AOT selection.
    Completed {
        /// Actual terminal runtime state after the last native transition.
        state: ProfileMachineState,
        /// Number of committed native graph transitions.
        transitions: usize,
    },
    /// Native dispatch stopped safely at an interpreter/lower-tier boundary.
    Fallback {
        /// Exact fail-closed reason dispatch stopped.
        reason: AheadOfExecutionRegisterMaskedReducedStateGraphDispatchFallback,
        /// Actual runtime state from which lower-tier execution may resume.
        state: ProfileMachineState,
        /// Number of native graph transitions committed before fallback.
        transitions: usize,
    },
}

/// Complete bounded dispatch request over one already-admitted reduced graph.
#[derive(Debug)]
pub struct AheadOfExecutionRegisterMaskedReducedStateGraphDispatchRequest<
    'graph,
    'aot,
> {
    entry: ProfileMachineState,
    environment:
        AheadOfExecutionRegisterMaskedReducedStateGraphDispatchEnvironment<
            'aot,
        >,
    graph: &'graph VerifiedAheadOfExecutionRegisterMaskedReducedStateGraph,
    transition_budget: usize,
}

/// One caller-owned native graph-node execution result.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum RegisterMaskedReducedStateGraphNativeExecution {
    /// Native completion committed one verified node transition.
    Applied(ProfileMachineState),
    /// Native semantic guard missed and returned the unchanged entry state.
    GuardMiss(ProfileMachineState),
}

/// Exact input presented to one caller-owned native graph-node executor.
#[derive(Clone, Copy, Debug)]
pub struct RegisterMaskedReducedStateGraphNativeExecutionRequest<'node> {
    artifact: &'node VerifiedAheadOfExecutionRegisterMaskedArtifact,
    entry: &'node ProfileMachineState,
    index: usize,
    program: &'node RegisterMaskedRegionEffectProgram,
}

/// Caller-owned execution port for one exactly selected reduced-graph AOT node.
///
/// Implementations are expected to load/invoke the supplied verified artifact
/// through the existing mask-aware native invocation boundary and return the
/// complete actual runtime checkpoint reconstructed after completion. The
/// dispatcher independently enforces graph guards and guard-miss atomicity.
pub trait RegisterMaskedReducedStateGraphNativeExecutor {
    /// Stable caller-owned native execution failure.
    type Error;

    /// Executes one exact AOT-selected v6 graph node from its runtime entry.
    ///
    /// # Errors
    ///
    /// Returns an executor-specific failure when loading, invocation, or
    /// completion cannot produce a safely admitted native result.
    fn execute(
        &mut self,
        request: RegisterMaskedReducedStateGraphNativeExecutionRequest<'_>,
    ) -> Result<RegisterMaskedReducedStateGraphNativeExecution, Self::Error>;
}

type DispatchFailure<'requirement, Executor> =
    AheadOfExecutionRegisterMaskedReducedStateGraphDispatchFailure<
        'requirement,
        <Executor as RegisterMaskedReducedStateGraphNativeExecutor>::Error,
    >;
type DispatchOutcome =
    AheadOfExecutionRegisterMaskedReducedStateGraphDispatchOutcome;
type DispatchResult<'requirement, Executor> =
    Result<DispatchOutcome, DispatchFailure<'requirement, Executor>>;
type Failure<'requirement, ExecutorError> =
    AheadOfExecutionRegisterMaskedReducedStateGraphDispatchFailure<
        'requirement,
        ExecutorError,
    >;
type Fallback = AheadOfExecutionRegisterMaskedReducedStateGraphDispatchFallback;
type NativeExecution = RegisterMaskedReducedStateGraphNativeExecution;
type ReducedGraph = VerifiedAheadOfExecutionRegisterMaskedReducedStateGraph;
type ReducedNode = VerifiedAheadOfExecutionRegisterMaskedReducedStateGraphNode;

type DispatchRequest<'graph, 'aot> =
    AheadOfExecutionRegisterMaskedReducedStateGraphDispatchRequest<
        'graph,
        'aot,
    >;
type NativeRequest<'node> =
    RegisterMaskedReducedStateGraphNativeExecutionRequest<'node>;

#[derive(Debug)]
struct DispatchContext<'graph, 'aot, 'executor, Executor> {
    environment:
        AheadOfExecutionRegisterMaskedReducedStateGraphDispatchEnvironment<
            'aot,
        >,
    executor: &'executor mut Executor,
    graph: &'graph ReducedGraph,
}

#[derive(Debug)]
struct DispatchCursor {
    index: usize,
    state: ProfileMachineState,
    transitions: usize,
}

#[derive(Clone, Debug, Eq, PartialEq)]
enum NodeArtifactSelection {
    Direct(Arc<VerifiedAheadOfExecutionRegisterMaskedArtifact>),
    Fallback(Fallback),
}

#[derive(Debug)]
enum TurnProgress {
    Continue(DispatchCursor),
    Terminal(DispatchOutcome),
}

impl<'aot>
    AheadOfExecutionRegisterMaskedReducedStateGraphDispatchEnvironment<'aot>
{
    /// Constructs immutable host and precompiled-object dispatch context.
    #[must_use]
    pub const fn new(
        aot: &'aot VerifiedAheadOfExecutionRegisterMaskedSet,
        runtime: &'static RuntimeCapability,
        host: DirectHost,
    ) -> Self {
        Self { aot, host, runtime }
    }
}

impl<'graph, 'aot>
    AheadOfExecutionRegisterMaskedReducedStateGraphDispatchRequest<'graph, 'aot>
{
    /// Constructs one bounded dispatch request from an actual runtime entry.
    #[must_use]
    pub const fn new(
        graph: &'graph ReducedGraph,
        environment:
            AheadOfExecutionRegisterMaskedReducedStateGraphDispatchEnvironment<
                'aot,
            >,
        entry: ProfileMachineState,
        transition_budget: usize,
    ) -> Self {
        Self {
            entry,
            environment,
            graph,
            transition_budget,
        }
    }
}

impl RegisterMaskedReducedStateGraphNativeExecutionRequest<'_> {
    /// Returns the exact verified AOT object selected for this graph node.
    #[must_use]
    pub const fn artifact(
        &self,
    ) -> &VerifiedAheadOfExecutionRegisterMaskedArtifact {
        self.artifact
    }

    /// Returns the complete actual runtime state at native node entry.
    #[must_use]
    pub const fn entry(&self) -> &ProfileMachineState {
        self.entry
    }

    /// Returns the zero-based admitted graph-node index.
    #[must_use]
    pub const fn index(&self) -> usize {
        self.index
    }

    /// Returns the exact product-owned v6 program selected for this node.
    #[must_use]
    pub const fn program(&self) -> &RegisterMaskedRegionEffectProgram {
        self.program
    }
}

impl<ExecutorError: Display> Display
    for AheadOfExecutionRegisterMaskedReducedStateGraphDispatchFailure<
        '_,
        ExecutorError,
    >
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Execution { error, index, .. } => write!(
                f,
                "reduced v6 graph node {index} execution failed: {error}"
            ),
            Self::GuardMissMutation { index } => write!(
                f,
                "reduced v6 graph node {index} guard miss changed runtime state"
            ),
            Self::Selection { error, index } => write!(
                f,
                "reduced v6 graph node {index} selection failed: {error}"
            ),
            Self::TerminalStateMismatch { index } => write!(
                f,
                "reduced v6 terminal node {index} returned wrong termination"
            ),
            Self::Topology { index } => {
                write!(f, "reduced v6 graph topology lost node {index}")
            },
        }
    }
}

impl<'graph, Executor> DispatchContext<'graph, '_, '_, Executor>
where
    Executor: RegisterMaskedReducedStateGraphNativeExecutor,
{
    fn advance_applied(
        &self,
        cursor: &DispatchCursor,
        node: &'graph ReducedNode,
        exit: ProfileMachineState,
    ) -> Result<TurnProgress, DispatchFailure<'graph, Executor>> {
        let transitions = cursor.transitions.saturating_add(1);
        match node.program().program.outcome {
            RunOutcome::BudgetExhausted { .. } => {
                self.advance_successor(cursor, node, exit)
            },
            RunOutcome::Terminated { reason, .. } => {
                if exit.io().termination() != Some(reason) {
                    return Err(Failure::TerminalStateMismatch {
                        index: cursor.index,
                    });
                }
                Ok(TurnProgress::Terminal(DispatchOutcome::Completed {
                    state: exit,
                    transitions,
                }))
            },
        }
    }

    fn advance_successor(
        &self,
        cursor: &DispatchCursor,
        node: &'graph ReducedNode,
        exit: ProfileMachineState,
    ) -> Result<TurnProgress, DispatchFailure<'graph, Executor>> {
        let successor = node
            .successor()
            .ok_or(Failure::Topology { index: cursor.index })?;
        let successor_node = self
            .graph
            .node(successor)
            .ok_or(Failure::Topology { index: successor })?;
        let transitions = cursor.transitions.saturating_add(1);
        if !successor_node.identity().matches(&exit) {
            return Ok(TurnProgress::Terminal(fallback(
                Fallback::SuccessorGuardMiss {
                    index: cursor.index,
                    successor,
                },
                exit,
                transitions,
            )));
        }
        Ok(TurnProgress::Continue(DispatchCursor {
            index: successor,
            state: exit,
            transitions,
        }))
    }

    fn execute_selected(
        &mut self,
        cursor: DispatchCursor,
        node: &'graph ReducedNode,
        artifact: &VerifiedAheadOfExecutionRegisterMaskedArtifact,
    ) -> Result<TurnProgress, DispatchFailure<'graph, Executor>> {
        let execution = self
            .executor
            .execute(NativeRequest {
                artifact,
                entry: &cursor.state,
                index: cursor.index,
                program: node.program(),
            })
            .map_err(|error| Failure::Execution {
                completed_transitions: cursor.transitions,
                error,
                index: cursor.index,
            })?;
        match execution {
            NativeExecution::Applied(exit) => {
                self.advance_applied(&cursor, node, exit)
            },
            NativeExecution::GuardMiss(guard_state) => {
                if guard_state != cursor.state {
                    return Err(Failure::GuardMissMutation {
                        index: cursor.index,
                    });
                }
                Ok(TurnProgress::Terminal(fallback(
                    Fallback::NativeGuardMiss { index: cursor.index },
                    cursor.state,
                    cursor.transitions,
                )))
            },
        }
    }

    fn execute_turn(
        &mut self,
        cursor: DispatchCursor,
        transition_budget: usize,
    ) -> Result<TurnProgress, DispatchFailure<'graph, Executor>> {
        let node = self
            .graph
            .node(cursor.index)
            .ok_or(Failure::Topology { index: cursor.index })?;
        if !node.identity().matches(&cursor.state) {
            return Ok(TurnProgress::Terminal(fallback(
                Fallback::NodeGuardMiss { index: cursor.index },
                cursor.state,
                cursor.transitions,
            )));
        }
        if cursor.transitions >= transition_budget {
            return Ok(TurnProgress::Terminal(fallback(
                Fallback::TransitionBudgetExhausted { index: cursor.index },
                cursor.state,
                cursor.transitions,
            )));
        }
        let artifact =
            match self.select_artifact(node.program(), cursor.index)? {
                NodeArtifactSelection::Direct(artifact) => artifact,
                NodeArtifactSelection::Fallback(reason) => {
                    return Ok(TurnProgress::Terminal(fallback(
                        reason,
                        cursor.state,
                        cursor.transitions,
                    )));
                },
            };
        self.execute_selected(cursor, node, artifact.as_ref())
    }

    fn select_artifact(
        &self,
        program: &'graph RegisterMaskedRegionEffectProgram,
        index: usize,
    ) -> Result<NodeArtifactSelection, DispatchFailure<'graph, Executor>> {
        let tier = match select_ahead_of_execution_register_masked_tier(
            program,
            self.environment.runtime,
            self.environment.host,
            self.environment.aot,
        ) {
            Ok(tier) => tier,
            Err(AheadOfExecutionRegisterMaskedSelectionError::Admission(
                error,
            )) if is_unsupported_program(&error) => {
                return Ok(NodeArtifactSelection::Fallback(
                    Fallback::Uncovered { index },
                ));
            },
            Err(error) => return Err(Failure::Selection { error, index }),
        };
        Ok(match tier {
            AheadOfExecutionRegisterMaskedTier::Direct(artifact) => {
                NodeArtifactSelection::Direct(artifact)
            },
            AheadOfExecutionRegisterMaskedTier::Interpreter => {
                NodeArtifactSelection::Fallback(Fallback::TargetInterpreter {
                    index,
                })
            },
            AheadOfExecutionRegisterMaskedTier::Uncovered => {
                NodeArtifactSelection::Fallback(Fallback::Uncovered { index })
            },
        })
    }
}

/// Dispatches exact precompiled v6 nodes while every actual state stays in the
/// admitted dependency-reduced graph.
///
/// Every committed continuing transition is followed by a fresh successor
/// dependency-guard check over the actual runtime exit state. A miss returns
/// that state to lower tiers; no alternate graph node is guessed. Unsupported
/// reviewed-native shape is treated exactly like an uncovered AOT object.
///
/// # Errors
///
/// Returns an indexed failure for AOT selection, executor failure, mutated
/// guard miss, impossible topology drift, or incompatible terminal completion.
pub fn dispatch_ahead_of_execution_register_masked_reduced_state_graph<
    'graph,
    Executor,
>(
    request: DispatchRequest<'graph, '_>,
    executor: &mut Executor,
) -> DispatchResult<'graph, Executor>
where
    Executor: RegisterMaskedReducedStateGraphNativeExecutor,
{
    let transition_budget = request.transition_budget;
    let mut cursor = DispatchCursor {
        index: request.graph.entry(),
        state: request.entry,
        transitions: 0,
    };
    let mut context = DispatchContext {
        environment: request.environment,
        executor,
        graph: request.graph,
    };
    loop {
        match context.execute_turn(cursor, transition_budget)? {
            TurnProgress::Continue(next) => cursor = next,
            TurnProgress::Terminal(outcome) => return Ok(outcome),
        }
    }
}

fn is_unsupported_program(
    error: &super::RegisterMaskedDirectAdmissionError<'_>,
) -> bool {
    error.kind() == RegisterMaskedDirectAdmissionErrorKind::UnsupportedProgram
}

const fn fallback(
    reason: Fallback,
    state: ProfileMachineState,
    transitions: usize,
) -> DispatchOutcome {
    DispatchOutcome::Fallback {
        reason,
        state,
        transitions,
    }
}
