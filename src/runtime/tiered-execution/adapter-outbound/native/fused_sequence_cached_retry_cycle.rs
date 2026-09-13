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
//   - Bounded cache-aware repetition of successfully rebased fused guard
//     misses.
// - Must-Not:
//   - Retry hard failures, infer attempt limits, release active lookup
//     authority, or roll back visible cache effects.
// - Allows:
//   - Inputs: exact suspension, attempt policy, host, fused cache, and
//     adapters.
//   - Outputs: normative fallback, completion, native failure, or owned
//     failure.
//   - Side effects: bounded resident acquisitions, native attempts, and
//     explicit lease-return reconciliation.
// - Split-When:
//   - Transactional cache rollback, telemetry, or asynchronous policy gains
//     independent ownership.
// - Merge-When:
//   - Product orchestration owns the complete cached tier lifecycle.
// - Summary:
//   - Reuses fused resident mappings across bounded native retry turns.
// - Description:
//   - Only successful guard misses continue; every other failure is terminal.
// - Usage:
//   - Execute from one scheduler `NativeRetry` suspension with fixed policy.
// - Defaults:
//   - Returned leases preserve active cache authority for exact subsequent
//     hits.
//

//! Bounded cache-aware fused native retry cycles.

use super::fused_lease_cache::{
    DirectFusedNativeLeaseCache, DirectFusedNativeLeaseCacheDisposition,
    DirectFusedNativeLeaseCacheReleaseSummary,
};
use super::fused_sequence_cached_retry::{
    DirectFusedNativeCachedRetryFailure,
    execute_cached_direct_fused_native_retry,
};
use super::fused_sequence_handoff::{
    DirectFusedNativeHandoffCompletion,
    DirectFusedNativeHandoffExecutionFailure,
};
use super::fused_sequence_leased_retry::{
    DirectFusedNativeLeasedRetryFailureRebaseFailure,
    DirectFusedNativeLeasedRetryRebaseFailure,
};
use super::fused_sequence_retry_policy::DirectFusedNativeRetryPolicy;
use super::fused_sequence_retry_rebase::{
    DirectFusedNativeRetryCompletion, DirectFusedNativeRetryDisposition,
    DirectFusedNativeRetryResumption,
};
use super::fused_sequence_retry_return::{
    DirectFusedNativeRetryFailureLeaseReturn,
    DirectFusedNativeRetryFailureLeaseReturnFailure,
    DirectFusedNativeRetryLeaseReturn,
    DirectFusedNativeRetryLeaseReturnFailure,
    return_direct_fused_native_retry_failure_leases,
    return_direct_fused_native_retry_leases,
};
use super::fused_sequence_retry_router::{
    DirectFusedNativeRetryHost, DirectFusedNativeRetryRoute,
    DirectFusedNativeRetryRoutingFailure,
    DirectFusedNativeRetryRoutingInterpreterRoute,
    DirectFusedNativeRetryRoutingNativeRoute,
    DirectFusedNativeRetryRoutingRequest, route_direct_fused_native_retry,
};
use super::fused_sequence_scheduler::{
    DirectFusedNativeScheduleDecision, DirectFusedNativeScheduleOutcome,
    DirectFusedNativeScheduleSuspension, DirectFusedNativeYieldTarget,
    schedule_direct_fused_native_handoff,
};
use super::platform::NativeExecutableMemoryAdapter;
use super::runner::DirectFusedNativeRunner;

/// Complete request for one bounded cache-aware fused retry cycle.
#[derive(Debug, Eq, PartialEq)]
pub struct DirectFusedNativeCachedRetryCycleRequest {
    attempts: usize,
    host: DirectFusedNativeRetryHost,
    policy: DirectFusedNativeRetryPolicy,
    suspension: DirectFusedNativeScheduleSuspension,
}

/// Cache and progress evidence for one successful resident native attempt.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DirectFusedNativeCachedRetryAttempt {
    attempt: usize,
    cache_dispositions: Vec<DirectFusedNativeLeaseCacheDisposition>,
    completed_steps: usize,
    reconciliation: DirectFusedNativeLeaseCacheReleaseSummary,
}

/// Normative fallback after zero or more fused native attempts.
#[derive(Debug, Eq, PartialEq)]
pub struct DirectFusedNativeCachedRetryInterpreterOutcome {
    attempts: usize,
    native_attempts: Vec<DirectFusedNativeCachedRetryAttempt>,
    outcome: DirectFusedNativeScheduleOutcome,
}

/// Verified completion after one or more fused resident attempts.
#[derive(Debug, Eq, PartialEq)]
pub struct DirectFusedNativeCachedRetryCompletion {
    attempts: usize,
    completion: Box<DirectFusedNativeRetryCompletion>,
    native_attempts: Vec<DirectFusedNativeCachedRetryAttempt>,
}

/// Failed native execution after semantic rebase and explicit lease return.
#[derive(Debug)]
pub struct DirectFusedNativeCachedRetryNativeFailure<RunnerError> {
    attempt: usize,
    failure: DirectFusedNativeRetryFailureLeaseReturn<RunnerError>,
    prior_attempts: Vec<DirectFusedNativeCachedRetryAttempt>,
}

/// Terminal result of one bounded cache-aware fused retry cycle.
#[derive(Debug)]
pub enum DirectFusedNativeCachedRetryCycleOutcome<RunnerError> {
    /// Attempt policy or host planning selected normative execution.
    Interpreter(Box<DirectFusedNativeCachedRetryInterpreterOutcome>),
    /// A resident native attempt completed the original semantic plan.
    NativeCompletion(Box<DirectFusedNativeCachedRetryCompletion>),
    /// Resident execution failed; no automatic native retry was attempted.
    NativeFailure(Box<DirectFusedNativeCachedRetryNativeFailure<RunnerError>>),
}

/// Unexpected result while zero-step rescheduling a successful guard miss.
#[derive(Debug, Eq, PartialEq)]
pub enum DirectFusedNativeCachedRetryRescheduleFailure {
    /// Zero-step scheduling unexpectedly completed semantic work.
    Completed(Box<DirectFusedNativeHandoffCompletion>),
    /// Zero-step scheduling failed normative admission.
    Execution(Box<DirectFusedNativeHandoffExecutionFailure>),
}

/// Hard failure retaining prior successful attempt evidence.
#[derive(Debug)]
pub enum DirectFusedNativeCachedRetryCycleFailure<MemoryError, RunnerError> {
    /// Cache acquisition or retry/lease binding failed before semantic rebase.
    Cached {
        /// One-based native attempt that failed.
        attempt: usize,
        /// Exact cache/binding/execution owner from the one-attempt boundary.
        failure:
            Box<DirectFusedNativeCachedRetryFailure<MemoryError, RunnerError>>,
        /// Successful attempts completed earlier in this cycle invocation.
        prior_attempts: Vec<DirectFusedNativeCachedRetryAttempt>,
    },
    /// Failed resident execution could not be semantically rebased.
    FailureRebase {
        /// One-based native attempt that failed semantic rebase.
        attempt: usize,
        /// Complete failed execution owner.
        failure:
            Box<DirectFusedNativeLeasedRetryFailureRebaseFailure<RunnerError>>,
        /// Successful attempts completed earlier in this cycle invocation.
        prior_attempts: Vec<DirectFusedNativeCachedRetryAttempt>,
    },
    /// Lease return/reconciliation failed after failed native execution.
    FailureReturn {
        /// One-based native attempt whose leases could not fully return.
        attempt: usize,
        /// Semantic/native evidence plus exact keyed cleanup retry ownership.
        failure: Box<
            DirectFusedNativeRetryFailureLeaseReturnFailure<
                MemoryError,
                RunnerError,
            >,
        >,
        /// Successful attempts completed earlier in this cycle invocation.
        prior_attempts: Vec<DirectFusedNativeCachedRetryAttempt>,
    },
    /// Normative fallback execution failed.
    Interpreter {
        /// Total completed native attempts before normative execution.
        attempts: usize,
        /// Exact normative execution failure.
        failure: Box<DirectFusedNativeHandoffExecutionFailure>,
        /// Successful attempts completed earlier in this cycle invocation.
        prior_attempts: Vec<DirectFusedNativeCachedRetryAttempt>,
    },
    /// Zero-step conversion of a guard resumption back to `NativeRetry` failed.
    Reschedule {
        /// Unexpected scheduler result.
        failure: Box<DirectFusedNativeCachedRetryRescheduleFailure>,
        /// Successful attempts completed before this rescheduling boundary.
        prior_attempts: Vec<DirectFusedNativeCachedRetryAttempt>,
    },
    /// Explicit lease return/reconciliation failed after successful execution.
    Return {
        /// One-based native attempt whose leases could not fully return.
        attempt: usize,
        /// Semantic evidence plus exact keyed cleanup retry ownership.
        failure: Box<DirectFusedNativeRetryLeaseReturnFailure<MemoryError>>,
        /// Successful attempts completed earlier in this cycle invocation.
        prior_attempts: Vec<DirectFusedNativeCachedRetryAttempt>,
    },
    /// Policy or exact host planning failed.
    Routing {
        /// Exact routing failure retaining the scheduler suspension.
        failure: Box<DirectFusedNativeRetryRoutingFailure>,
        /// Successful attempts completed earlier in this cycle invocation.
        prior_attempts: Vec<DirectFusedNativeCachedRetryAttempt>,
    },
    /// Successful resident execution could not be semantically rebased.
    SuccessRebase {
        /// One-based native attempt that failed semantic rebase.
        attempt: usize,
        /// Complete successful execution owner.
        failure: Box<DirectFusedNativeLeasedRetryRebaseFailure>,
        /// Successful attempts completed earlier in this cycle invocation.
        prior_attempts: Vec<DirectFusedNativeCachedRetryAttempt>,
    },
}

/// Result of one bounded cache-aware fused retry cycle.
pub type DirectFusedNativeCachedRetryCycleResult<MemoryError, RunnerError> =
    Result<
        DirectFusedNativeCachedRetryCycleOutcome<RunnerError>,
        Box<DirectFusedNativeCachedRetryCycleFailure<MemoryError, RunnerError>>,
    >;

type CachedRetryCycleAdapterResult<Adapter, Runner> =
    DirectFusedNativeCachedRetryCycleResult<
        <Adapter as NativeExecutableMemoryAdapter>::Error,
        <Runner as DirectFusedNativeRunner>::Error,
    >;

type CachedRetryCycleAdapterFailure<Adapter, Runner> =
    DirectFusedNativeCachedRetryFailure<
        <Adapter as NativeExecutableMemoryAdapter>::Error,
        <Runner as DirectFusedNativeRunner>::Error,
    >;

type CachedRetryCycleRescheduleResult<MemoryError, RunnerError> = Result<
    DirectFusedNativeScheduleSuspension,
    Box<DirectFusedNativeCachedRetryCycleFailure<MemoryError, RunnerError>>,
>;

type CachedRetryCycleRouteResult<Adapter, Runner> = Result<
    DirectFusedNativeCachedRetryProgress<
        <Runner as DirectFusedNativeRunner>::Error,
    >,
    Box<
        DirectFusedNativeCachedRetryCycleFailure<
            <Adapter as NativeExecutableMemoryAdapter>::Error,
            <Runner as DirectFusedNativeRunner>::Error,
        >,
    >,
>;

type CachedRetryCycleProgressResult<MemoryError, RunnerError> = Result<
    DirectFusedNativeCachedRetryProgress<RunnerError>,
    Box<DirectFusedNativeCachedRetryCycleFailure<MemoryError, RunnerError>>,
>;

type CachedRetryCycleRoutingResult<MemoryError, RunnerError> = Result<
    DirectFusedNativeRetryRoute,
    Box<DirectFusedNativeCachedRetryCycleFailure<MemoryError, RunnerError>>,
>;

struct DirectFusedNativeCachedRetryCycleContext<'context, Adapter, Runner> {
    adapter: &'context mut Adapter,
    cache: &'context mut DirectFusedNativeLeaseCache,
    runner: &'context mut Runner,
}

enum DirectFusedNativeCachedRetryProgress<RunnerError> {
    Continue {
        attempt: usize,
        evidence: DirectFusedNativeCachedRetryAttempt,
        suspension: Box<DirectFusedNativeScheduleSuspension>,
    },
    Terminal(DirectFusedNativeCachedRetryCycleOutcome<RunnerError>),
}

impl DirectFusedNativeCachedRetryCycleRequest {
    /// Constructs one complete bounded cache-aware fused retry request.
    #[must_use]
    pub const fn new(
        policy: DirectFusedNativeRetryPolicy,
        suspension: DirectFusedNativeScheduleSuspension,
        attempts: usize,
        host: DirectFusedNativeRetryHost,
    ) -> Self {
        Self {
            attempts,
            host,
            policy,
            suspension,
        }
    }
}

impl DirectFusedNativeCachedRetryAttempt {
    /// Returns the one-based native attempt number.
    #[must_use]
    pub const fn attempt(&self) -> usize {
        self.attempt
    }

    /// Returns cache insertion/hit evidence for every fused region.
    #[must_use]
    pub fn cache_dispositions(
        &self,
    ) -> &[DirectFusedNativeLeaseCacheDisposition] {
        &self.cache_dispositions
    }

    /// Returns semantic source steps committed by this native attempt.
    #[must_use]
    pub const fn completed_steps(&self) -> usize {
        self.completed_steps
    }

    /// Returns explicit retired-resident reconciliation evidence.
    #[must_use]
    pub const fn reconciliation(
        &self,
    ) -> &DirectFusedNativeLeaseCacheReleaseSummary {
        &self.reconciliation
    }
}

impl DirectFusedNativeCachedRetryInterpreterOutcome {
    /// Returns total completed native attempts before normative fallback.
    #[must_use]
    pub const fn attempts(&self) -> usize {
        self.attempts
    }

    /// Consumes this result into the exact normative scheduler outcome.
    #[must_use]
    pub fn into_outcome(self) -> DirectFusedNativeScheduleOutcome {
        self.outcome
    }

    /// Returns cache evidence for native attempts executed by this cycle.
    #[must_use]
    pub fn native_attempts(&self) -> &[DirectFusedNativeCachedRetryAttempt] {
        &self.native_attempts
    }

    /// Returns the exact normative scheduler outcome.
    #[must_use]
    pub const fn outcome(&self) -> &DirectFusedNativeScheduleOutcome {
        &self.outcome
    }
}

impl DirectFusedNativeCachedRetryCompletion {
    /// Returns total completed native attempts before semantic completion.
    #[must_use]
    pub const fn attempts(&self) -> usize {
        self.attempts
    }

    /// Returns the exact verified mixed-tier completion.
    #[must_use]
    pub const fn completion(&self) -> &DirectFusedNativeRetryCompletion {
        &self.completion
    }

    /// Returns cache evidence for native attempts executed by this cycle.
    #[must_use]
    pub fn native_attempts(&self) -> &[DirectFusedNativeCachedRetryAttempt] {
        &self.native_attempts
    }
}

impl<RunnerError> DirectFusedNativeCachedRetryNativeFailure<RunnerError> {
    /// Returns the one-based native attempt that failed.
    #[must_use]
    pub const fn attempt(&self) -> usize {
        self.attempt
    }

    /// Returns semantic/native/cache evidence after explicit lease return.
    #[must_use]
    pub const fn failure(
        &self,
    ) -> &DirectFusedNativeRetryFailureLeaseReturn<RunnerError> {
        &self.failure
    }

    /// Returns successful attempt evidence from earlier turns.
    #[must_use]
    pub fn prior_attempts(&self) -> &[DirectFusedNativeCachedRetryAttempt] {
        &self.prior_attempts
    }
}

/// Executes fused resident guard retries until completion, failure, or
/// fallback.
///
/// Only a successfully rebased `GuardMiss` is rescheduled to `NativeRetry`.
/// Each successful rebase returns external leases first, preserving active
/// cache lookup authority for an exact next-turn hit.
///
/// # Errors
///
/// Returns complete routing, cache, rebase, reconciliation, or scheduler
/// ownership for every hard failure.
pub fn execute_cached_direct_fused_native_retry_cycle<Adapter, Runner>(
    request: DirectFusedNativeCachedRetryCycleRequest,
    cache: &mut DirectFusedNativeLeaseCache,
    adapter: &mut Adapter,
    runner: &mut Runner,
) -> CachedRetryCycleAdapterResult<Adapter, Runner>
where
    Adapter: NativeExecutableMemoryAdapter,
    Runner: DirectFusedNativeRunner,
{
    let DirectFusedNativeCachedRetryCycleRequest {
        mut attempts,
        host,
        policy,
        mut suspension,
    } = request;
    let mut native_attempts = Vec::new();
    let mut context =
        DirectFusedNativeCachedRetryCycleContext { adapter, cache, runner };
    loop {
        let selected_route = route_cycle_retry::<Adapter::Error, Runner::Error>(
            DirectFusedNativeRetryRoutingRequest::new(
                policy, suspension, attempts, host,
            ),
            &native_attempts,
        )?;
        match selected_route {
            DirectFusedNativeRetryRoute::Interpreter(interpreter_route) => {
                return execute_interpreter_route(
                    *interpreter_route,
                    native_attempts,
                );
            },
            DirectFusedNativeRetryRoute::Native(native_route) => {
                match execute_native_route(
                    *native_route,
                    &mut context,
                    &native_attempts,
                )? {
                    DirectFusedNativeCachedRetryProgress::Continue {
                        attempt,
                        evidence,
                        suspension: next_suspension,
                    } => {
                        attempts = attempt;
                        native_attempts.push(evidence);
                        suspension = *next_suspension;
                    },
                    DirectFusedNativeCachedRetryProgress::Terminal(outcome) => {
                        return Ok(outcome);
                    },
                }
            },
        }
    }
}

fn execute_interpreter_route<MemoryError, RunnerError>(
    route: DirectFusedNativeRetryRoutingInterpreterRoute,
    native_attempts: Vec<DirectFusedNativeCachedRetryAttempt>,
) -> DirectFusedNativeCachedRetryCycleResult<MemoryError, RunnerError> {
    let attempts = route.attempts();
    let (handoff, decision) = route.into_parts();
    let outcome = schedule_direct_fused_native_handoff(handoff, decision)
        .map_err(|failure| {
            Box::new(DirectFusedNativeCachedRetryCycleFailure::Interpreter {
                attempts,
                failure,
                prior_attempts: native_attempts.clone(),
            })
        })?;
    Ok(DirectFusedNativeCachedRetryCycleOutcome::Interpreter(
        Box::new(DirectFusedNativeCachedRetryInterpreterOutcome {
            attempts,
            native_attempts,
            outcome,
        }),
    ))
}

fn execute_native_route<Adapter, Runner>(
    route: DirectFusedNativeRetryRoutingNativeRoute,
    context: &mut DirectFusedNativeCachedRetryCycleContext<'_, Adapter, Runner>,
    prior_attempts: &[DirectFusedNativeCachedRetryAttempt],
) -> CachedRetryCycleRouteResult<Adapter, Runner>
where
    Adapter: NativeExecutableMemoryAdapter,
    Runner: DirectFusedNativeRunner,
{
    let attempt = route.attempt();
    let execution_result = execute_cached_direct_fused_native_retry(
        context.cache,
        context.adapter,
        context.runner,
        route.into_retry(),
    );
    let execution = match execution_result {
        Ok(successful_execution) => successful_execution,
        Err(cached_failure) => {
            return handle_cached_failure(
                attempt,
                *cached_failure,
                context,
                prior_attempts,
            );
        },
    };
    let completed_steps = execution.outcome().completed_steps();
    let rebased = execution.rebase().map_err(|rebase_failure| {
        Box::new(DirectFusedNativeCachedRetryCycleFailure::SuccessRebase {
            attempt,
            failure: rebase_failure,
            prior_attempts: prior_attempts.to_vec(),
        })
    })?;
    let returned = return_direct_fused_native_retry_leases(
        context.cache,
        context.adapter,
        rebased,
    )
    .map_err(|return_failure| {
        Box::new(DirectFusedNativeCachedRetryCycleFailure::Return {
            attempt,
            failure: return_failure,
            prior_attempts: prior_attempts.to_vec(),
        })
    })?;
    route_returned_success(attempt, completed_steps, returned, prior_attempts)
}

fn route_returned_success<MemoryError, RunnerError>(
    attempt: usize,
    completed_steps: usize,
    returned: DirectFusedNativeRetryLeaseReturn,
    prior_attempts: &[DirectFusedNativeCachedRetryAttempt],
) -> CachedRetryCycleProgressResult<MemoryError, RunnerError> {
    let (disposition, cache_dispositions, reconciliation) =
        returned.into_parts();
    let evidence = DirectFusedNativeCachedRetryAttempt {
        attempt,
        cache_dispositions,
        completed_steps,
        reconciliation,
    };
    match disposition {
        DirectFusedNativeRetryDisposition::Completed(completion) => {
            let mut native_attempts = prior_attempts.to_vec();
            native_attempts.push(evidence);
            Ok(DirectFusedNativeCachedRetryProgress::Terminal(
                DirectFusedNativeCachedRetryCycleOutcome::NativeCompletion(
                    Box::new(DirectFusedNativeCachedRetryCompletion {
                        attempts: attempt,
                        completion,
                        native_attempts,
                    }),
                ),
            ))
        },
        DirectFusedNativeRetryDisposition::Resumable(resumption) => {
            let mut completed_attempts = prior_attempts.to_vec();
            completed_attempts.push(evidence.clone());
            let suspension =
                reschedule_guard(*resumption, &completed_attempts)?;
            Ok(DirectFusedNativeCachedRetryProgress::Continue {
                attempt,
                evidence,
                suspension: Box::new(suspension),
            })
        },
    }
}

fn handle_cached_failure<Adapter, Runner>(
    attempt: usize,
    cached_failure: CachedRetryCycleAdapterFailure<Adapter, Runner>,
    context: &mut DirectFusedNativeCachedRetryCycleContext<'_, Adapter, Runner>,
    prior_attempts: &[DirectFusedNativeCachedRetryAttempt],
) -> CachedRetryCycleRouteResult<Adapter, Runner>
where
    Adapter: NativeExecutableMemoryAdapter,
    Runner: DirectFusedNativeRunner,
{
    match cached_failure {
        DirectFusedNativeCachedRetryFailure::Execution(execution) => {
            let rebased = execution.rebase().map_err(|rebase_failure| {
                Box::new(
                    DirectFusedNativeCachedRetryCycleFailure::FailureRebase {
                        attempt,
                        failure: rebase_failure,
                        prior_attempts: prior_attempts.to_vec(),
                    },
                )
            })?;
            let returned = return_direct_fused_native_retry_failure_leases(
                context.cache,
                context.adapter,
                rebased,
            )
            .map_err(|return_failure| {
                Box::new(
                    DirectFusedNativeCachedRetryCycleFailure::FailureReturn {
                        attempt,
                        failure: return_failure,
                        prior_attempts: prior_attempts.to_vec(),
                    },
                )
            })?;
            Ok(DirectFusedNativeCachedRetryProgress::Terminal(
                DirectFusedNativeCachedRetryCycleOutcome::NativeFailure(
                    Box::new(DirectFusedNativeCachedRetryNativeFailure {
                        attempt,
                        failure: returned,
                        prior_attempts: prior_attempts.to_vec(),
                    }),
                ),
            ))
        },
        failure @ (DirectFusedNativeCachedRetryFailure::Acquisition(_)
        | DirectFusedNativeCachedRetryFailure::Binding(_)) => {
            Err(Box::new(DirectFusedNativeCachedRetryCycleFailure::Cached {
                attempt,
                failure: Box::new(failure),
                prior_attempts: prior_attempts.to_vec(),
            }))
        },
    }
}

fn reschedule_guard<MemoryError, RunnerError>(
    resumption: DirectFusedNativeRetryResumption,
    prior_attempts: &[DirectFusedNativeCachedRetryAttempt],
) -> CachedRetryCycleRescheduleResult<MemoryError, RunnerError> {
    let decision = DirectFusedNativeScheduleDecision::yield_to(
        DirectFusedNativeYieldTarget::NativeRetry,
    );
    match schedule_direct_fused_native_handoff(
        resumption.into_handoff(),
        decision,
    ) {
        Ok(DirectFusedNativeScheduleOutcome::Suspended(suspension)) => {
            Ok(suspension)
        },
        Ok(DirectFusedNativeScheduleOutcome::Completed(completion)) => Err(
            Box::new(DirectFusedNativeCachedRetryCycleFailure::Reschedule {
                failure: Box::new(
                    DirectFusedNativeCachedRetryRescheduleFailure::Completed(
                        Box::new(completion),
                    ),
                ),
                prior_attempts: prior_attempts.to_vec(),
            }),
        ),
        Err(schedule_failure) => Err(Box::new(
            DirectFusedNativeCachedRetryCycleFailure::Reschedule {
                failure: Box::new(
                    DirectFusedNativeCachedRetryRescheduleFailure::Execution(
                        schedule_failure,
                    ),
                ),
                prior_attempts: prior_attempts.to_vec(),
            },
        )),
    }
}

fn route_cycle_retry<MemoryError, RunnerError>(
    request: DirectFusedNativeRetryRoutingRequest,
    prior_attempts: &[DirectFusedNativeCachedRetryAttempt],
) -> CachedRetryCycleRoutingResult<MemoryError, RunnerError> {
    route_direct_fused_native_retry(request).map_err(|failure| {
        Box::new(DirectFusedNativeCachedRetryCycleFailure::Routing {
            failure,
            prior_attempts: prior_attempts.to_vec(),
        })
    })
}
