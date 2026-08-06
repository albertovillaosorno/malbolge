// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Execution of one already-routed native continuation retry turn.
// - Must-Not:
//   - Select hosts, infer attempts, hide cleanup owners, or loop automatically.
// - Allows:
//   - Inputs: one exact route plus explicit native memory and runner adapters.
//   - Outputs: interpreter result, native disposition, or owned rebase failure.
//   - Side effects: one selected interpreter slice or one native retry attempt.
// - Split-When:
//   - Cache-aware execution or async lifecycle gains independent ownership.
// - Merge-When:
//   - Product orchestration owns route selection and execution atomically.
// - Summary:
//   - Executes one bounded routed turn and preserves every semantic/native
//     owner.
// - Description:
//   - Native failures split semantic disposition from retryable cleanup
//     evidence.
// - Usage:
//   - Execute the route returned by `route_native_continuation_retry()`.
// - Defaults:
//   - Exactly one route executes; no implicit loop, fallback, or cleanup retry.
//

//! One-turn execution for an already-routed native continuation retry.

use crate::continuation_scheduler::{
    NativeContinuationScheduleOutcome, schedule_native_interpreter_handoff,
};
use crate::execution_native::{
    NativeExecutableMemoryAdapter, NativeExecutableRunner,
    NativeSequenceExecutionFailure,
};
use crate::interpreter_handoff::NativeInterpreterHandoffExecutionFailure;
use crate::native_retry::{
    NativeContinuationRetryDisposition,
    NativeContinuationRetryFailureRebaseFailure,
    NativeContinuationRetryRebaseFailure,
};
use crate::retry_router::{
    NativeContinuationRetryInterpreterRoute,
    NativeContinuationRetryNativeRoute, NativeContinuationRetryRoute,
};

/// Result of executing one already-routed retry turn.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationRetryTurnOutcome<MemoryError, RunnerError> {
    /// The selected normative route executed through the continuation
    /// scheduler.
    Interpreter(Box<NativeContinuationRetryInterpreterTurn>),
    /// Native execution failed but semantic progress rebased successfully.
    NativeFailure(
        Box<NativeContinuationRetryNativeFailureTurn<MemoryError, RunnerError>>,
    ),
    /// Native execution succeeded and semantic progress rebased successfully.
    NativeSuccess(Box<NativeContinuationRetryNativeSuccessTurn>),
}

/// Successful interpreter-route execution evidence.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryInterpreterTurn {
    attempts: usize,
    outcome: NativeContinuationScheduleOutcome,
}

/// Failed native attempt with independent semantic and native failure owners.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryNativeFailureTurn<MemoryError, RunnerError> {
    attempt: usize,
    disposition: NativeContinuationRetryDisposition,
    failure: Box<NativeSequenceExecutionFailure<MemoryError, RunnerError>>,
}

/// Successful native attempt with its exact semantic disposition.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryNativeSuccessTurn {
    attempt: usize,
    disposition: NativeContinuationRetryDisposition,
}

/// Failure while executing or rebasing one already-routed retry turn.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationRetryTurnFailure<MemoryError, RunnerError> {
    /// Normative fallback execution failed at an exact checkpoint.
    Interpreter(Box<NativeContinuationRetryInterpreterTurnFailure>),
    /// Failed native execution could not be semantically rebased.
    NativeFailureRebase(
        Box<
            NativeContinuationRetryNativeFailureRebaseTurn<
                MemoryError,
                RunnerError,
            >,
        >,
    ),
    /// Successful native execution could not be semantically rebased.
    NativeSuccessRebase(Box<NativeContinuationRetryNativeSuccessRebaseTurn>),
}

/// Exact normative failure after a routed interpreter decision.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryInterpreterTurnFailure {
    attempts: usize,
    failure: Box<NativeInterpreterHandoffExecutionFailure>,
}

/// Failed native attempt whose complete owner was retained after rebase
/// failure.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryNativeFailureRebaseTurn<
    MemoryError,
    RunnerError,
> {
    attempt: usize,
    failure: Box<
        NativeContinuationRetryFailureRebaseFailure<MemoryError, RunnerError>,
    >,
}

/// Successful native attempt whose complete owner was retained after rebase
/// failure.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryNativeSuccessRebaseTurn {
    attempt: usize,
    failure: Box<NativeContinuationRetryRebaseFailure>,
}

/// Independent attempt, semantic disposition, and native failure owners.
pub type NativeContinuationRetryNativeFailureTurnParts<
    MemoryError,
    RunnerError,
> = (
    usize,
    NativeContinuationRetryDisposition,
    Box<NativeSequenceExecutionFailure<MemoryError, RunnerError>>,
);

/// Result of executing one exact routed retry turn.
pub type NativeContinuationRetryTurnResult<MemoryError, RunnerError> = Result<
    NativeContinuationRetryTurnOutcome<MemoryError, RunnerError>,
    Box<NativeContinuationRetryTurnFailure<MemoryError, RunnerError>>,
>;
type NativeContinuationRetryAdapterTurnResult<MemoryAdapter, Runner> =
    NativeContinuationRetryTurnResult<
        <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
        <Runner as NativeExecutableRunner>::Error,
    >;

impl NativeContinuationRetryInterpreterTurn {
    /// Returns completed native attempts before this interpreter route.
    #[must_use]
    pub const fn attempts(&self) -> usize {
        self.attempts
    }

    /// Consumes this turn and returns the exact scheduler outcome.
    #[must_use]
    pub fn into_outcome(self) -> NativeContinuationScheduleOutcome {
        self.outcome
    }

    /// Returns the exact scheduler outcome produced by this turn.
    #[must_use]
    pub const fn outcome(&self) -> &NativeContinuationScheduleOutcome {
        &self.outcome
    }
}

impl NativeContinuationRetryInterpreterTurnFailure {
    /// Returns completed native attempts before this interpreter failure.
    #[must_use]
    pub const fn attempts(&self) -> usize {
        self.attempts
    }

    /// Returns the exact normative handoff failure.
    #[must_use]
    pub const fn failure(&self) -> &NativeInterpreterHandoffExecutionFailure {
        &self.failure
    }

    /// Consumes this turn and returns the exact normative handoff failure.
    #[must_use]
    pub fn into_failure(self) -> Box<NativeInterpreterHandoffExecutionFailure> {
        self.failure
    }
}

impl<MemoryError, RunnerError>
    NativeContinuationRetryNativeFailureTurn<MemoryError, RunnerError>
{
    /// Returns the one-based native attempt number executed by this turn.
    #[must_use]
    pub const fn attempt(&self) -> usize {
        self.attempt
    }

    /// Returns the exact semantic disposition after failed native execution.
    #[must_use]
    pub const fn disposition(&self) -> &NativeContinuationRetryDisposition {
        &self.disposition
    }

    /// Returns the indexed native execution and cleanup failure owner.
    #[must_use]
    pub const fn failure(
        &self,
    ) -> &NativeSequenceExecutionFailure<MemoryError, RunnerError> {
        &self.failure
    }

    /// Consumes this turn into semantic disposition and native failure owners.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> NativeContinuationRetryNativeFailureTurnParts<MemoryError, RunnerError>
    {
        (self.attempt, self.disposition, self.failure)
    }
}

impl<MemoryError, RunnerError>
    NativeContinuationRetryNativeFailureRebaseTurn<MemoryError, RunnerError>
{
    /// Returns the one-based native attempt number executed by this turn.
    #[must_use]
    pub const fn attempt(&self) -> usize {
        self.attempt
    }

    /// Returns the complete failed retry rebase owner.
    #[must_use]
    pub const fn failure(
        &self,
    ) -> &NativeContinuationRetryFailureRebaseFailure<MemoryError, RunnerError>
    {
        &self.failure
    }

    /// Consumes this turn and restores the complete failed retry rebase owner.
    #[must_use]
    pub fn into_failure(
        self,
    ) -> NativeContinuationRetryFailureRebaseFailure<MemoryError, RunnerError>
    {
        *self.failure
    }
}

impl NativeContinuationRetryNativeSuccessTurn {
    /// Returns the one-based native attempt number executed by this turn.
    #[must_use]
    pub const fn attempt(&self) -> usize {
        self.attempt
    }

    /// Returns the exact semantic disposition after successful native
    /// execution.
    #[must_use]
    pub const fn disposition(&self) -> &NativeContinuationRetryDisposition {
        &self.disposition
    }

    /// Consumes this turn into attempt evidence and semantic disposition.
    #[must_use]
    pub fn into_parts(self) -> (usize, NativeContinuationRetryDisposition) {
        (self.attempt, self.disposition)
    }
}

impl NativeContinuationRetryNativeSuccessRebaseTurn {
    /// Returns the one-based native attempt number executed by this turn.
    #[must_use]
    pub const fn attempt(&self) -> usize {
        self.attempt
    }

    /// Returns the complete successful retry rebase failure owner.
    #[must_use]
    pub const fn failure(&self) -> &NativeContinuationRetryRebaseFailure {
        &self.failure
    }

    /// Consumes this turn and restores the complete successful rebase owner.
    #[must_use]
    pub fn into_failure(self) -> Box<NativeContinuationRetryRebaseFailure> {
        self.failure
    }
}

/// Executes exactly one already-routed retry turn.
///
/// Interpreter routes execute their configured scheduler decision. Native
/// routes execute one admitted retry and immediately rebase success or failure
/// evidence. No additional retry, fallback, or cleanup attempt is inferred.
///
/// # Errors
///
/// Returns [`NativeContinuationRetryTurnFailure`] while retaining the complete
/// normative or native rebase owner when the selected turn cannot publish a
/// semantic outcome.
pub fn execute_native_continuation_retry_turn<MemoryAdapter, Runner>(
    selected_route: NativeContinuationRetryRoute,
    memory_adapter: &mut MemoryAdapter,
    runner: &mut Runner,
) -> NativeContinuationRetryAdapterTurnResult<MemoryAdapter, Runner>
where
    MemoryAdapter: NativeExecutableMemoryAdapter,
    Runner: NativeExecutableRunner,
{
    match selected_route {
        NativeContinuationRetryRoute::Interpreter(interpreter_route) => {
            execute_interpreter_turn(*interpreter_route)
        },
        NativeContinuationRetryRoute::Native(native_route) => {
            execute_native_turn(*native_route, memory_adapter, runner)
        },
    }
}

fn execute_interpreter_turn<MemoryError, RunnerError>(
    route: NativeContinuationRetryInterpreterRoute,
) -> NativeContinuationRetryTurnResult<MemoryError, RunnerError> {
    let attempts = route.attempts();
    let (handoff, decision) = route.into_parts();
    match schedule_native_interpreter_handoff(handoff, decision) {
        Ok(outcome) => {
            Ok(NativeContinuationRetryTurnOutcome::Interpreter(Box::new(
                NativeContinuationRetryInterpreterTurn { attempts, outcome },
            )))
        },
        Err(failure) => {
            Err(Box::new(NativeContinuationRetryTurnFailure::Interpreter(
                Box::new(NativeContinuationRetryInterpreterTurnFailure {
                    attempts,
                    failure,
                }),
            )))
        },
    }
}

fn execute_native_turn<MemoryAdapter, Runner>(
    route: NativeContinuationRetryNativeRoute,
    memory_adapter: &mut MemoryAdapter,
    runner: &mut Runner,
) -> NativeContinuationRetryAdapterTurnResult<MemoryAdapter, Runner>
where
    MemoryAdapter: NativeExecutableMemoryAdapter,
    Runner: NativeExecutableRunner,
{
    let attempt = route.attempt();
    match route.into_retry().execute(memory_adapter, runner) {
        Ok(execution) => match execution.rebase() {
            Ok(disposition) => {
                Ok(NativeContinuationRetryTurnOutcome::NativeSuccess(Box::new(
                    NativeContinuationRetryNativeSuccessTurn {
                        attempt,
                        disposition,
                    },
                )))
            },
            Err(failure) => Err(Box::new(
                NativeContinuationRetryTurnFailure::NativeSuccessRebase(
                    Box::new(NativeContinuationRetryNativeSuccessRebaseTurn {
                        attempt,
                        failure,
                    }),
                ),
            )),
        },
        Err(execution_failure) => match execution_failure.rebase() {
            Ok(rebased) => {
                let (disposition, failure) = rebased.into_parts();
                Ok(NativeContinuationRetryTurnOutcome::NativeFailure(Box::new(
                    NativeContinuationRetryNativeFailureTurn {
                        attempt,
                        disposition,
                        failure,
                    },
                )))
            },
            Err(failure) => Err(Box::new(
                NativeContinuationRetryTurnFailure::NativeFailureRebase(
                    Box::new(NativeContinuationRetryNativeFailureRebaseTurn {
                        attempt,
                        failure,
                    }),
                ),
            )),
        },
    }
}
