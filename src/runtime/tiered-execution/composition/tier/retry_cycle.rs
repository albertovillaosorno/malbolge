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
//   - Bounded repetition of successful native guard-miss retry turns.
// - Must-Not:
//   - Retry runner/cleanup failures, infer limits, or discard semantic owners.
// - Allows:
//   - Inputs: exact suspension, attempts, host, policy, native adapters.
//   - Outputs: completion, normative result, native failure, or owned hard
//     error.
//   - Side effects: bounded native attempts and one selected normative
//     fallback.
// - Split-When:
//   - Async lifecycle, cache-aware execution, or telemetry gains policy.
// - Merge-When:
//   - Product orchestration owns the complete tiered lifecycle.
// - Summary:
//   - Repeats only successful guard misses under an immutable attempt bound.
// - Description:
//   - Every non-guard failure exits with semantic and cleanup ownership intact.
// - Usage:
//   - Execute one explicit bounded cycle from a `NativeRetry` suspension.
// - Defaults:
//   - Zero attempt limit falls back immediately; no failure is auto-retried.
//

//! Bounded multi-turn execution for successful native guard retries.

use crate::continuation_scheduler::{
    NativeContinuationScheduleDecision, NativeContinuationScheduleOutcome,
    NativeContinuationScheduleSuspension, NativeContinuationYieldTarget,
    schedule_native_interpreter_handoff,
};
use crate::execution_native::{
    NativeExecutableMemoryAdapter, NativeExecutableRunner,
};
use crate::interpreter_handoff::{
    NativeInterpreterHandoffCompletion,
    NativeInterpreterHandoffExecutionFailure,
};
use crate::native_retry::{
    NativeContinuationRetryCompletion, NativeContinuationRetryDisposition,
    NativeContinuationRetryResumption,
};
use crate::retry_policy::NativeContinuationRetryPolicy;
use crate::retry_router::{
    NativeContinuationRetryHost, NativeContinuationRetryRoutingFailure,
    NativeContinuationRetryRoutingRequest, route_native_continuation_retry,
};
use crate::retry_turn::{
    NativeContinuationRetryInterpreterTurn,
    NativeContinuationRetryNativeFailureTurn,
    NativeContinuationRetryTurnFailure, NativeContinuationRetryTurnOutcome,
    execute_native_continuation_retry_turn,
};

/// Complete request for one bounded retry cycle.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryCycleRequest {
    attempts: usize,
    host: NativeContinuationRetryHost,
    policy: NativeContinuationRetryPolicy,
    suspension: NativeContinuationScheduleSuspension,
}

/// Terminal or externally actionable result of one bounded retry cycle.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationRetryCycleOutcome<MemoryError, RunnerError> {
    /// Attempt policy or target format selected normative execution.
    Interpreter(Box<NativeContinuationRetryInterpreterTurn>),
    /// One native attempt completed the original semantic plan.
    NativeCompletion(Box<NativeContinuationRetryCycleCompletion>),
    /// Native execution failed; no automatic retry was attempted.
    NativeFailure(
        Box<NativeContinuationRetryNativeFailureTurn<MemoryError, RunnerError>>,
    ),
}

/// Verified complete result after one or more native retry attempts.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryCycleCompletion {
    attempts: usize,
    completion: Box<NativeContinuationRetryCompletion>,
}

/// Hard failure during routing, turn execution/rebase, or guard rescheduling.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationRetryCycleFailure<MemoryError, RunnerError> {
    /// A zero-step guard reschedule unexpectedly completed or failed.
    Reschedule(Box<NativeContinuationRetryCycleRescheduleFailure>),
    /// Policy or exact host planning failed with suspension ownership.
    Routing(Box<NativeContinuationRetryRoutingFailure>),
    /// The selected interpreter/native turn could not publish a disposition.
    Turn(Box<NativeContinuationRetryTurnFailure<MemoryError, RunnerError>>),
}

/// Unexpected result while converting a guard resumption back to `NativeRetry`.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationRetryCycleRescheduleFailure {
    /// Zero-step scheduling unexpectedly completed remaining semantic work.
    Completed(Box<NativeInterpreterHandoffCompletion>),
    /// Zero-step scheduling failed exact normative admission.
    Execution(Box<NativeInterpreterHandoffExecutionFailure>),
}

/// Result of executing one bounded retry cycle.
pub type NativeContinuationRetryCycleResult<MemoryError, RunnerError> = Result<
    NativeContinuationRetryCycleOutcome<MemoryError, RunnerError>,
    Box<NativeContinuationRetryCycleFailure<MemoryError, RunnerError>>,
>;

type NativeContinuationRetryAdapterCycleResult<MemoryAdapter, Runner> =
    NativeContinuationRetryCycleResult<
        <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
        <Runner as NativeExecutableRunner>::Error,
    >;
type NativeContinuationRetryRescheduleResult<MemoryError, RunnerError> = Result<
    NativeContinuationScheduleSuspension,
    Box<NativeContinuationRetryCycleFailure<MemoryError, RunnerError>>,
>;

impl NativeContinuationRetryCycleCompletion {
    /// Returns native attempts completed by this cycle.
    #[must_use]
    pub const fn attempts(&self) -> usize {
        self.attempts
    }

    /// Returns the exact verified mixed-tier completion.
    #[must_use]
    pub const fn completion(&self) -> &NativeContinuationRetryCompletion {
        &self.completion
    }

    /// Consumes this result into attempt evidence and completion ownership.
    #[must_use]
    pub fn into_parts(self) -> (usize, Box<NativeContinuationRetryCompletion>) {
        (self.attempts, self.completion)
    }
}

impl NativeContinuationRetryCycleRequest {
    /// Constructs one complete bounded retry cycle request.
    #[must_use]
    pub const fn new(
        policy: NativeContinuationRetryPolicy,
        suspension: NativeContinuationScheduleSuspension,
        attempts: usize,
        host: NativeContinuationRetryHost,
    ) -> Self {
        Self {
            attempts,
            host,
            policy,
            suspension,
        }
    }
}

/// Executes successful guard retries until completion, failure, or policy
/// fallback.
///
/// Only a successfully rebased native guard miss continues the loop. Native
/// runner/release failure returns immediately, and immutable policy bounds
/// every possible repeated native attempt.
///
/// # Errors
///
/// Returns [`NativeContinuationRetryCycleFailure`] with exact routing, turn, or
/// zero-step rescheduling ownership.
pub fn execute_native_continuation_retry_cycle<MemoryAdapter, Runner>(
    request: NativeContinuationRetryCycleRequest,
    memory_adapter: &mut MemoryAdapter,
    runner: &mut Runner,
) -> NativeContinuationRetryAdapterCycleResult<MemoryAdapter, Runner>
where
    MemoryAdapter: NativeExecutableMemoryAdapter,
    Runner: NativeExecutableRunner,
{
    let NativeContinuationRetryCycleRequest {
        mut attempts,
        host,
        policy,
        mut suspension,
    } = request;
    loop {
        let route = route_native_continuation_retry(
            NativeContinuationRetryRoutingRequest::new(
                policy, suspension, attempts, host,
            ),
        )
        .map_err(|failure| {
            Box::new(NativeContinuationRetryCycleFailure::Routing(failure))
        })?;
        let turn_outcome = execute_native_continuation_retry_turn(
            route,
            memory_adapter,
            runner,
        )
        .map_err(|failure| {
            Box::new(NativeContinuationRetryCycleFailure::Turn(failure))
        })?;
        match turn_outcome {
            NativeContinuationRetryTurnOutcome::Interpreter(
                interpreter_turn,
            ) => {
                return Ok(NativeContinuationRetryCycleOutcome::Interpreter(
                    interpreter_turn,
                ));
            },
            NativeContinuationRetryTurnOutcome::NativeFailure(failure_turn) => {
                return Ok(NativeContinuationRetryCycleOutcome::NativeFailure(
                    failure_turn,
                ));
            },
            NativeContinuationRetryTurnOutcome::NativeSuccess(success_turn) => {
                let (attempt, disposition) = success_turn.into_parts();
                attempts = attempt;
                match disposition {
                    NativeContinuationRetryDisposition::Completed(
                        completion_owner,
                    ) => {
                        let cycle_completion =
                            NativeContinuationRetryCycleCompletion {
                                attempts,
                                completion: completion_owner,
                            };
                        return Ok(completed_cycle(cycle_completion));
                    },
                    NativeContinuationRetryDisposition::Resumable(
                        resumption,
                    ) => {
                        suspension = reschedule_guard(*resumption)?;
                    },
                }
            },
        }
    }
}

fn completed_cycle<MemoryError, RunnerError>(
    completion: NativeContinuationRetryCycleCompletion,
) -> NativeContinuationRetryCycleOutcome<MemoryError, RunnerError> {
    NativeContinuationRetryCycleOutcome::NativeCompletion(Box::new(completion))
}

fn reschedule_guard<MemoryError, RunnerError>(
    resumption: NativeContinuationRetryResumption,
) -> NativeContinuationRetryRescheduleResult<MemoryError, RunnerError> {
    let decision = NativeContinuationScheduleDecision::yield_to(
        NativeContinuationYieldTarget::NativeRetry,
    );
    match schedule_native_interpreter_handoff(
        resumption.into_handoff(),
        decision,
    ) {
        Ok(NativeContinuationScheduleOutcome::Suspended(suspension)) => {
            Ok(suspension)
        },
        Ok(NativeContinuationScheduleOutcome::Completed(completion)) => {
            Err(Box::new(NativeContinuationRetryCycleFailure::Reschedule(
                Box::new(
                    NativeContinuationRetryCycleRescheduleFailure::Completed(
                        Box::new(completion),
                    ),
                ),
            )))
        },
        Err(failure) => Err(Box::new(
            NativeContinuationRetryCycleFailure::Reschedule(Box::new(
                NativeContinuationRetryCycleRescheduleFailure::Execution(
                    failure,
                ),
            )),
        )),
    }
}
