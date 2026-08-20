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
//   - Bounded cache-aware repetition of successful native guard retries.
// - Must-Not:
//   - Retry load/runner failures, release active cache authority, or infer
//     policy.
// - Allows:
//   - Inputs: exact suspension, attempt policy, host, lease cache, and
//     adapters.
//   - Outputs: completion/fallback trace or exact cache/lease failure
//     ownership.
//   - Side effects: bounded cache acquisitions and loaded native attempts.
// - Split-When:
//   - Adaptive policy, latency histograms, or async ownership gains a
//     lifecycle.
// - Merge-When:
//   - Product orchestration owns the complete cached tiered lifecycle.
// - Summary:
//   - Reuses process-local mappings across a bounded native retry cycle.
// - Description:
//   - Successful leases are dropped after rebase; active cache authority
//     remains.
// - Usage:
//   - Execute one bounded cycle from a scheduler `NativeRetry` suspension.
// - Defaults:
//   - Acquisition and runner failures stop immediately with all owners intact.
//

//! Bounded cache-aware native continuation retry cycles.

#[path = "cached_cycle/telemetry.rs"]
mod telemetry;
#[path = "cached_cycle/telemetry_assessment.rs"]
mod telemetry_assessment;
#[path = "cached_cycle/telemetry_codec.rs"]
mod telemetry_codec;
#[path = "cached_cycle/telemetry_latency.rs"]
mod telemetry_latency;
#[path = "cached_cycle/telemetry_latency_codec.rs"]
mod telemetry_latency_codec;
#[path = "cached_cycle/telemetry_latency_merge.rs"]
mod telemetry_latency_merge;
#[path = "cached_cycle/telemetry_latency_snapshot.rs"]
mod telemetry_latency_snapshot;
#[path = "cached_cycle/telemetry_snapshot.rs"]
mod telemetry_snapshot;
#[path = "cached_cycle/telemetry_window.rs"]
mod telemetry_window;

use std::fmt::{Display, Formatter, Result as FormatResult};

pub use telemetry::{
    NativeContinuationCachedRetryTelemetry,
    NativeContinuationCachedRetryTelemetryError,
    NativeContinuationCachedRetryTelemetrySource,
    summarize_cached_retry_attempts,
};
pub use telemetry_assessment::{
    NativeContinuationCachedRetryTelemetryAssessment,
    NativeContinuationCachedRetryTelemetryAssessmentMaximums,
    NativeContinuationCachedRetryTelemetryAssessmentMinimums,
    NativeContinuationCachedRetryTelemetryAssessmentSignal,
    NativeContinuationCachedRetryTelemetryAssessmentThresholds,
    NativeContinuationCachedRetryTelemetryAssessmentViolations,
    assess_cached_retry_telemetry,
};
pub use telemetry_codec::{
    NativeContinuationCachedRetryTelemetryCodecError,
    NativeContinuationCachedRetryTelemetryCodecField,
    decode_cached_retry_telemetry_snapshot,
    encode_cached_retry_telemetry_snapshot,
};
pub use telemetry_latency::{
    NativeContinuationCachedRetryLatencyHistogram,
    NativeContinuationCachedRetryLatencyHistogramError,
    NativeContinuationCachedRetryLatencyRecord,
    NativeContinuationCachedRetryLatencySample,
};
pub use telemetry_latency_codec::{
    NativeContinuationCachedRetryLatencyCodecError,
    NativeContinuationCachedRetryLatencyCodecField,
    decode_cached_retry_latency_snapshot, encode_cached_retry_latency_snapshot,
};
pub use telemetry_latency_merge::{
    NativeContinuationCachedRetryLatencyMergeError,
    NativeContinuationCachedRetryLatencyMergeRecord,
};
pub use telemetry_latency_snapshot::{
    NativeContinuationCachedRetryLatencyHistogramSnapshot,
    NativeContinuationCachedRetryLatencySnapshotCounts,
    NativeContinuationCachedRetryLatencySnapshotError,
    NativeContinuationCachedRetryLatencySnapshotRange,
};
pub use telemetry_snapshot::{
    NativeContinuationCachedRetryTelemetrySnapshotError,
    NativeContinuationCachedRetryTelemetrySnapshotMetadata,
    NativeContinuationCachedRetryTelemetryWindowSnapshot,
    NativeContinuationCachedRetryTelemetryWindowSnapshotParts,
};
pub use telemetry_window::{
    NativeContinuationCachedRetryTelemetryObservation,
    NativeContinuationCachedRetryTelemetryWindow,
    NativeContinuationCachedRetryTelemetryWindowAppend,
    NativeContinuationCachedRetryTelemetryWindowCounter,
    NativeContinuationCachedRetryTelemetryWindowError,
    NativeContinuationCachedRetryTelemetryWindowReconfiguration,
    NativeContinuationCachedRetryTelemetryWindowReconfigurationResult,
};

use crate::cached_retry::{
    NativeContinuationCachedRetryFailure, execute_cached_native_retry,
};
use crate::continuation_scheduler::{
    NativeContinuationScheduleDecision, NativeContinuationScheduleOutcome,
    NativeContinuationScheduleSuspension, NativeContinuationYieldTarget,
    schedule_native_interpreter_handoff,
};
use crate::execution_native::{
    NativeExecutableMemoryAdapter, NativeExecutableRunner,
    NativeExecutableSequenceLeaseCache,
    NativeExecutableSequenceLeaseCacheDisposition,
};
use crate::interpreter_handoff::{
    NativeInterpreterHandoffCompletion,
    NativeInterpreterHandoffExecutionFailure,
};
use crate::leased_retry::{
    NativeContinuationLeasedRetryFailureDisposition,
    NativeContinuationLeasedRetryFailureRebaseFailure,
    NativeContinuationLeasedRetryRebaseFailure,
};
use crate::native_retry::{
    NativeContinuationRetryCompletion, NativeContinuationRetryDisposition,
    NativeContinuationRetryResumption,
};
use crate::retry_policy::NativeContinuationRetryPolicy;
use crate::retry_router::{
    NativeContinuationRetryHost, NativeContinuationRetryInterpreterRoute,
    NativeContinuationRetryNativeRoute, NativeContinuationRetryRoute,
    NativeContinuationRetryRoutingFailure,
    NativeContinuationRetryRoutingRequest, route_native_continuation_retry,
};

/// Complete request for one bounded cache-aware retry cycle.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryCycleRequest {
    attempts: usize,
    host: NativeContinuationRetryHost,
    policy: NativeContinuationRetryPolicy,
    suspension: NativeContinuationScheduleSuspension,
}

/// Cache evidence for one native attempt completed by this cycle invocation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryAttempt {
    attempt: usize,
    completed_steps: usize,
    disposition: NativeExecutableSequenceLeaseCacheDisposition,
}

/// Normative fallback selected after zero or more cache-aware native attempts.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryInterpreterOutcome {
    attempts: usize,
    native_attempts: Vec<NativeContinuationCachedRetryAttempt>,
    outcome: NativeContinuationScheduleOutcome,
}

/// Verified semantic completion after cache-aware native attempts.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryCompletion {
    attempts: usize,
    completion: Box<NativeContinuationRetryCompletion>,
    native_attempts: Vec<NativeContinuationCachedRetryAttempt>,
}

/// Native runner failure with its acquired lease and prior attempt evidence.
#[derive(Debug)]
pub struct NativeContinuationCachedRetryNativeFailure<RunnerError> {
    attempt: usize,
    failure: NativeContinuationLeasedRetryFailureDisposition<RunnerError>,
    prior_attempts: Vec<NativeContinuationCachedRetryAttempt>,
}

/// Cache acquisition or binding failure with prior attempt evidence.
#[derive(Debug)]
pub struct NativeContinuationCachedRetryAttemptFailure<MemoryError, RunnerError>
{
    attempt: usize,
    failure:
        Box<NativeContinuationCachedRetryFailure<MemoryError, RunnerError>>,
    prior_attempts: Vec<NativeContinuationCachedRetryAttempt>,
}

/// Terminal or externally actionable result of one cached retry cycle.
#[derive(Debug)]
pub enum NativeContinuationCachedRetryCycleOutcome<RunnerError> {
    /// Attempt policy or host format selected normative execution.
    Interpreter(Box<NativeContinuationCachedRetryInterpreterOutcome>),
    /// One loaded native attempt completed the original semantic plan.
    NativeCompletion(Box<NativeContinuationCachedRetryCompletion>),
    /// Loaded execution failed; no automatic retry was attempted.
    NativeFailure(Box<NativeContinuationCachedRetryNativeFailure<RunnerError>>),
}

/// Unexpected zero-step guard rescheduling result.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryRescheduleFailure {
    /// Zero-step scheduling unexpectedly completed semantic work.
    Completed(Box<NativeInterpreterHandoffCompletion>),
    /// Zero-step scheduling failed exact normative admission.
    Execution(Box<NativeInterpreterHandoffExecutionFailure>),
}

/// Routing failure retaining cache evidence from earlier successful attempts.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryRoutingCycleFailure {
    failure: Box<NativeContinuationRetryRoutingFailure>,
    prior_attempts: Vec<NativeContinuationCachedRetryAttempt>,
}

/// Hard failure during cached routing, acquisition, rebase, or rescheduling.
#[derive(Debug)]
pub enum NativeContinuationCachedRetryCycleFailure<MemoryError, RunnerError> {
    /// Cache acquisition/binding failed before a semantic disposition existed.
    Cached(
        Box<
            NativeContinuationCachedRetryAttemptFailure<
                MemoryError,
                RunnerError,
            >,
        >,
    ),
    /// Failed loaded execution could not be semantically rebased.
    FailureRebase(
        Box<NativeContinuationCachedRetryFailureRebaseCycle<RunnerError>>,
    ),
    /// Normative fallback execution failed at an exact checkpoint.
    Interpreter(Box<NativeContinuationCachedRetryInterpreterFailure>),
    /// Zero-step guard rescheduling failed closed.
    Reschedule(Box<NativeContinuationCachedRetryRescheduleFailure>),
    /// Attempt policy or exact host planning failed with suspension ownership.
    Routing(Box<NativeContinuationCachedRetryRoutingCycleFailure>),
    /// Successful loaded execution could not be semantically rebased.
    SuccessRebase(Box<NativeContinuationCachedRetrySuccessRebaseCycle>),
}

/// Normative failure after cached retry exhaustion or unavailable target
/// format.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryInterpreterFailure {
    attempts: usize,
    failure: Box<NativeInterpreterHandoffExecutionFailure>,
    native_attempts: Vec<NativeContinuationCachedRetryAttempt>,
}

/// Failed loaded attempt whose complete rebase owner was retained.
#[derive(Debug)]
pub struct NativeContinuationCachedRetryFailureRebaseCycle<RunnerError> {
    attempt: usize,
    failure:
        Box<NativeContinuationLeasedRetryFailureRebaseFailure<RunnerError>>,
    prior_attempts: Vec<NativeContinuationCachedRetryAttempt>,
}

/// Successful loaded attempt whose complete rebase owner was retained.
#[derive(Debug)]
pub struct NativeContinuationCachedRetrySuccessRebaseCycle {
    attempt: usize,
    failure: Box<NativeContinuationLeasedRetryRebaseFailure>,
    prior_attempts: Vec<NativeContinuationCachedRetryAttempt>,
}

/// Attempt, prior evidence, and exact cache/binding failure ownership.
pub type NativeContinuationCachedRetryAttemptFailureParts<
    MemoryError,
    RunnerError,
> = (
    usize,
    Vec<NativeContinuationCachedRetryAttempt>,
    Box<NativeContinuationCachedRetryFailure<MemoryError, RunnerError>>,
);

/// Prior attempt evidence plus exact routing failure ownership.
pub type NativeContinuationCachedRetryRoutingFailureParts = (
    Vec<NativeContinuationCachedRetryAttempt>,
    Box<NativeContinuationRetryRoutingFailure>,
);

/// Attempt, prior cache evidence, and complete failed loaded owner.
pub type NativeContinuationCachedRetryNativeFailureParts<RunnerError> = (
    usize,
    Vec<NativeContinuationCachedRetryAttempt>,
    NativeContinuationLeasedRetryFailureDisposition<RunnerError>,
);

/// Result of one bounded cache-aware retry cycle.
pub type NativeContinuationCachedRetryCycleResult<MemoryError, RunnerError> =
    Result<
        NativeContinuationCachedRetryCycleOutcome<RunnerError>,
        Box<
            NativeContinuationCachedRetryCycleFailure<MemoryError, RunnerError>,
        >,
    >;

type NativeContinuationCachedRetryAdapterCycleResult<MemoryAdapter, Runner> =
    NativeContinuationCachedRetryCycleResult<
        <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
        <Runner as NativeExecutableRunner>::Error,
    >;

type NativeContinuationCachedRetryRescheduleResult<MemoryError, RunnerError> =
    Result<
        NativeContinuationScheduleSuspension,
        Box<
            NativeContinuationCachedRetryCycleFailure<MemoryError, RunnerError>,
        >,
    >;

type NativeContinuationCachedRetryRoutingResult<MemoryError, RunnerError> =
    Result<
        NativeContinuationRetryRoute,
        Box<
            NativeContinuationCachedRetryCycleFailure<MemoryError, RunnerError>,
        >,
    >;

type NativeContinuationCachedRetryRouteResult<MemoryAdapter, Runner> = Result<
    NativeContinuationCachedRetryProgress<
        <Runner as NativeExecutableRunner>::Error,
    >,
    Box<
        NativeContinuationCachedRetryCycleFailure<
            <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
            <Runner as NativeExecutableRunner>::Error,
        >,
    >,
>;

type NativeContinuationCachedRetryAdapterFailure<MemoryAdapter, Runner> =
    NativeContinuationCachedRetryFailure<
        <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
        <Runner as NativeExecutableRunner>::Error,
    >;

struct NativeContinuationCachedRetryRouteContext<
    'context,
    MemoryAdapter,
    Runner,
> {
    cache: &'context mut NativeExecutableSequenceLeaseCache,
    memory_adapter: &'context mut MemoryAdapter,
    runner: &'context mut Runner,
}

#[derive(Debug)]
enum NativeContinuationCachedRetryProgress<RunnerError> {
    Continue {
        attempt: usize,
        evidence: NativeContinuationCachedRetryAttempt,
        suspension: Box<NativeContinuationScheduleSuspension>,
    },
    Terminal(NativeContinuationCachedRetryCycleOutcome<RunnerError>),
}

impl NativeContinuationCachedRetryAttempt {
    /// Returns the one-based native attempt number.
    #[must_use]
    pub const fn attempt(&self) -> usize {
        self.attempt
    }

    /// Returns semantic native steps committed by this attempt.
    #[must_use]
    pub const fn completed_steps(&self) -> usize {
        self.completed_steps
    }

    /// Returns exact cache hit/insertion evidence for this attempt.
    #[must_use]
    pub const fn disposition(
        &self,
    ) -> &NativeExecutableSequenceLeaseCacheDisposition {
        &self.disposition
    }

    #[cfg(test)]
    pub(crate) const fn from_test_evidence(
        attempt: usize,
        completed_steps: usize,
        disposition: NativeExecutableSequenceLeaseCacheDisposition,
    ) -> Self {
        Self {
            attempt,
            completed_steps,
            disposition,
        }
    }
}

impl<MemoryError, RunnerError>
    NativeContinuationCachedRetryAttemptFailure<MemoryError, RunnerError>
{
    /// Returns the one-based native attempt whose cache phase failed.
    #[must_use]
    pub const fn attempt(&self) -> usize {
        self.attempt
    }

    /// Returns exact cache acquisition or binding failure ownership.
    #[must_use]
    pub const fn failure(
        &self,
    ) -> &NativeContinuationCachedRetryFailure<MemoryError, RunnerError> {
        &self.failure
    }

    /// Consumes this owner into attempt, prior evidence, and exact failure.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> NativeContinuationCachedRetryAttemptFailureParts<
        MemoryError,
        RunnerError,
    > {
        (self.attempt, self.prior_attempts, self.failure)
    }

    /// Returns cache evidence from successful earlier attempts.
    #[must_use]
    pub fn prior_attempts(&self) -> &[NativeContinuationCachedRetryAttempt] {
        &self.prior_attempts
    }
}

impl NativeContinuationCachedRetryCompletion {
    /// Returns total native attempts completed before semantic completion.
    #[must_use]
    pub const fn attempts(&self) -> usize {
        self.attempts
    }

    /// Returns the exact verified mixed-tier completion.
    #[must_use]
    pub const fn completion(&self) -> &NativeContinuationRetryCompletion {
        &self.completion
    }

    /// Returns cache evidence for attempts executed by this cycle invocation.
    #[must_use]
    pub fn native_attempts(&self) -> &[NativeContinuationCachedRetryAttempt] {
        &self.native_attempts
    }

    /// Returns total native semantic steps committed by this cycle invocation.
    #[must_use]
    pub fn native_steps(&self) -> usize {
        self.native_attempts
            .iter()
            .map(NativeContinuationCachedRetryAttempt::completed_steps)
            .sum()
    }
}

impl<RunnerError> NativeContinuationCachedRetryNativeFailure<RunnerError> {
    /// Returns the one-based native attempt that failed.
    #[must_use]
    pub const fn attempt(&self) -> usize {
        self.attempt
    }

    /// Returns the loaded failure, semantic disposition, cache evidence, and
    /// lease.
    #[must_use]
    pub const fn failure(
        &self,
    ) -> &NativeContinuationLeasedRetryFailureDisposition<RunnerError> {
        &self.failure
    }

    /// Consumes this outcome into attempt evidence and the complete failure
    /// owner.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> NativeContinuationCachedRetryNativeFailureParts<RunnerError> {
        (self.attempt, self.prior_attempts, self.failure)
    }

    /// Returns cache evidence for successful prior attempts in this invocation.
    #[must_use]
    pub fn prior_attempts(&self) -> &[NativeContinuationCachedRetryAttempt] {
        &self.prior_attempts
    }
}

impl NativeContinuationCachedRetryInterpreterOutcome {
    /// Returns total native attempts completed before normative fallback.
    #[must_use]
    pub const fn attempts(&self) -> usize {
        self.attempts
    }

    /// Consumes this result and returns the exact scheduler outcome.
    #[must_use]
    pub fn into_outcome(self) -> NativeContinuationScheduleOutcome {
        self.outcome
    }

    /// Returns cache evidence for attempts executed by this cycle invocation.
    #[must_use]
    pub fn native_attempts(&self) -> &[NativeContinuationCachedRetryAttempt] {
        &self.native_attempts
    }

    /// Returns the exact scheduler outcome.
    #[must_use]
    pub const fn outcome(&self) -> &NativeContinuationScheduleOutcome {
        &self.outcome
    }
}

impl NativeContinuationCachedRetryCycleRequest {
    /// Constructs one complete bounded cache-aware retry cycle request.
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

impl NativeContinuationCachedRetryInterpreterFailure {
    /// Returns total native attempts completed before normative failure.
    #[must_use]
    pub const fn attempts(&self) -> usize {
        self.attempts
    }

    /// Returns the exact normative handoff failure.
    #[must_use]
    pub const fn failure(&self) -> &NativeInterpreterHandoffExecutionFailure {
        &self.failure
    }

    /// Returns cache evidence for attempts executed by this cycle invocation.
    #[must_use]
    pub fn native_attempts(&self) -> &[NativeContinuationCachedRetryAttempt] {
        &self.native_attempts
    }
}

impl<RunnerError> NativeContinuationCachedRetryFailureRebaseCycle<RunnerError> {
    /// Returns the one-based native attempt whose failure could not rebase.
    #[must_use]
    pub const fn attempt(&self) -> usize {
        self.attempt
    }

    /// Returns the complete failed loaded execution rebase owner.
    #[must_use]
    pub const fn failure(
        &self,
    ) -> &NativeContinuationLeasedRetryFailureRebaseFailure<RunnerError> {
        &self.failure
    }

    /// Returns cache evidence for successful prior attempts.
    #[must_use]
    pub fn prior_attempts(&self) -> &[NativeContinuationCachedRetryAttempt] {
        &self.prior_attempts
    }
}

impl Display for NativeContinuationCachedRetryRoutingCycleFailure {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        Display::fmt(self.failure.as_ref(), f)
    }
}

impl NativeContinuationCachedRetryRoutingCycleFailure {
    /// Returns exact host/policy routing failure ownership.
    #[must_use]
    pub const fn failure(&self) -> &NativeContinuationRetryRoutingFailure {
        &self.failure
    }

    /// Consumes this owner into prior evidence and exact routing failure.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> NativeContinuationCachedRetryRoutingFailureParts {
        (self.prior_attempts, self.failure)
    }

    /// Returns cache evidence from successful earlier attempts.
    #[must_use]
    pub fn prior_attempts(&self) -> &[NativeContinuationCachedRetryAttempt] {
        &self.prior_attempts
    }

    /// Returns the retained canonical profile diagnostic, when applicable.
    #[must_use]
    pub fn profile_diagnostic(&self) -> Option<&str> {
        self.failure.profile_diagnostic()
    }
}

impl NativeContinuationCachedRetrySuccessRebaseCycle {
    /// Returns the one-based native attempt whose success could not rebase.
    #[must_use]
    pub const fn attempt(&self) -> usize {
        self.attempt
    }

    /// Returns the complete successful loaded execution rebase owner.
    #[must_use]
    pub const fn failure(&self) -> &NativeContinuationLeasedRetryRebaseFailure {
        &self.failure
    }

    /// Returns cache evidence for successful prior attempts.
    #[must_use]
    pub fn prior_attempts(&self) -> &[NativeContinuationCachedRetryAttempt] {
        &self.prior_attempts
    }
}

/// Executes cache-aware guard retries until completion, failure, or fallback.
///
/// A successfully rebased guard miss drops only its external lease; active
/// cache authority remains, so an unchanged suffix becomes an exact hit on the
/// next attempt. Acquisition, binding, and runner failures never retry
/// automatically.
///
/// # Errors
///
/// Returns [`NativeContinuationCachedRetryCycleFailure`] with complete routing,
/// cache, lease, rebase, or normative ownership for every hard failure.
pub fn execute_cached_native_retry_cycle<MemoryAdapter, Runner>(
    request: NativeContinuationCachedRetryCycleRequest,
    cache: &mut NativeExecutableSequenceLeaseCache,
    memory_adapter: &mut MemoryAdapter,
    runner: &mut Runner,
) -> NativeContinuationCachedRetryAdapterCycleResult<MemoryAdapter, Runner>
where
    MemoryAdapter: NativeExecutableMemoryAdapter,
    Runner: NativeExecutableRunner,
{
    let NativeContinuationCachedRetryCycleRequest {
        mut attempts,
        host,
        policy,
        mut suspension,
    } = request;
    let mut native_attempts = Vec::new();
    loop {
        let selected_route =
            route_cached_retry::<MemoryAdapter::Error, Runner::Error>(
                NativeContinuationRetryRoutingRequest::new(
                    policy, suspension, attempts, host,
                ),
                &native_attempts,
            )?;
        match selected_route {
            NativeContinuationRetryRoute::Interpreter(interpreter_route) => {
                return execute_cached_interpreter_route(
                    *interpreter_route,
                    native_attempts,
                );
            },
            NativeContinuationRetryRoute::Native(native_route) => {
                let mut context = NativeContinuationCachedRetryRouteContext {
                    cache,
                    memory_adapter,
                    runner,
                };
                match execute_cached_native_route(
                    *native_route,
                    &mut context,
                    &native_attempts,
                )? {
                    NativeContinuationCachedRetryProgress::Continue {
                        attempt,
                        evidence,
                        suspension: next_suspension,
                    } => {
                        attempts = attempt;
                        native_attempts.push(evidence);
                        suspension = *next_suspension;
                    },
                    NativeContinuationCachedRetryProgress::Terminal(
                        outcome,
                    ) => {
                        return Ok(outcome);
                    },
                }
            },
        }
    }
}

fn route_cached_retry<MemoryError, RunnerError>(
    request: NativeContinuationRetryRoutingRequest,
    prior_attempts: &[NativeContinuationCachedRetryAttempt],
) -> NativeContinuationCachedRetryRoutingResult<MemoryError, RunnerError> {
    route_native_continuation_retry(request).map_err(|failure| {
        Box::new(NativeContinuationCachedRetryCycleFailure::Routing(
            Box::new(NativeContinuationCachedRetryRoutingCycleFailure {
                failure,
                prior_attempts: prior_attempts.to_vec(),
            }),
        ))
    })
}

fn execute_cached_native_route<MemoryAdapter, Runner>(
    route: NativeContinuationRetryNativeRoute,
    context: &mut NativeContinuationCachedRetryRouteContext<
        '_,
        MemoryAdapter,
        Runner,
    >,
    prior_attempts: &[NativeContinuationCachedRetryAttempt],
) -> NativeContinuationCachedRetryRouteResult<MemoryAdapter, Runner>
where
    MemoryAdapter: NativeExecutableMemoryAdapter,
    Runner: NativeExecutableRunner,
{
    let attempt = route.attempt();
    let execution = match execute_cached_native_retry(
        context.cache,
        context.memory_adapter,
        context.runner,
        route.into_retry(),
    ) {
        Ok(execution) => execution,
        Err(failure) => {
            return handle_cached_attempt_failure::<MemoryAdapter, Runner>(
                attempt,
                *failure,
                prior_attempts,
            );
        },
    };
    let completed_steps = execution.outcome().completed_steps();
    let rebased = execution.rebase().map_err(|failure| {
        Box::new(cached_success_rebase_failure(
            attempt,
            failure,
            prior_attempts,
        ))
    })?;
    let (disposition, cache_disposition, lease) = rebased.into_parts();
    let evidence = NativeContinuationCachedRetryAttempt {
        attempt,
        completed_steps,
        disposition: cache_disposition,
    };
    drop(lease);
    match disposition {
        NativeContinuationRetryDisposition::Completed(completion) => {
            let mut native_attempts = prior_attempts.to_vec();
            native_attempts.push(evidence);
            Ok(NativeContinuationCachedRetryProgress::Terminal(
                NativeContinuationCachedRetryCycleOutcome::NativeCompletion(
                    Box::new(NativeContinuationCachedRetryCompletion {
                        attempts: attempt,
                        completion,
                        native_attempts,
                    }),
                ),
            ))
        },
        NativeContinuationRetryDisposition::Resumable(resumption) => {
            let suspension = reschedule_cached_guard(*resumption)?;
            Ok(NativeContinuationCachedRetryProgress::Continue {
                attempt,
                evidence,
                suspension: Box::new(suspension),
            })
        },
    }
}

fn cached_success_rebase_failure<MemoryError, RunnerError>(
    attempt: usize,
    failure: Box<NativeContinuationLeasedRetryRebaseFailure>,
    prior_attempts: &[NativeContinuationCachedRetryAttempt],
) -> NativeContinuationCachedRetryCycleFailure<MemoryError, RunnerError> {
    NativeContinuationCachedRetryCycleFailure::SuccessRebase(Box::new(
        NativeContinuationCachedRetrySuccessRebaseCycle {
            attempt,
            failure,
            prior_attempts: prior_attempts.to_vec(),
        },
    ))
}

fn execute_cached_interpreter_route<MemoryError, RunnerError>(
    route: NativeContinuationRetryInterpreterRoute,
    native_attempts: Vec<NativeContinuationCachedRetryAttempt>,
) -> NativeContinuationCachedRetryCycleResult<MemoryError, RunnerError> {
    let attempts = route.attempts();
    let (handoff, decision) = route.into_parts();
    match schedule_native_interpreter_handoff(handoff, decision) {
        Ok(outcome) => {
            Ok(NativeContinuationCachedRetryCycleOutcome::Interpreter(
                Box::new(NativeContinuationCachedRetryInterpreterOutcome {
                    attempts,
                    native_attempts,
                    outcome,
                }),
            ))
        },
        Err(failure) => Err(Box::new(
            NativeContinuationCachedRetryCycleFailure::Interpreter(Box::new(
                NativeContinuationCachedRetryInterpreterFailure {
                    attempts,
                    failure,
                    native_attempts,
                },
            )),
        )),
    }
}

fn cached_native_failure_progress<RunnerError>(
    attempt: usize,
    failure: NativeContinuationLeasedRetryFailureDisposition<RunnerError>,
    prior_attempts: &[NativeContinuationCachedRetryAttempt],
) -> NativeContinuationCachedRetryProgress<RunnerError> {
    NativeContinuationCachedRetryProgress::Terminal(
        NativeContinuationCachedRetryCycleOutcome::NativeFailure(Box::new(
            NativeContinuationCachedRetryNativeFailure {
                attempt,
                failure,
                prior_attempts: prior_attempts.to_vec(),
            },
        )),
    )
}

fn handle_cached_attempt_failure<MemoryAdapter, Runner>(
    attempt: usize,
    failure: NativeContinuationCachedRetryAdapterFailure<MemoryAdapter, Runner>,
    prior_attempts: &[NativeContinuationCachedRetryAttempt],
) -> NativeContinuationCachedRetryRouteResult<MemoryAdapter, Runner>
where
    MemoryAdapter: NativeExecutableMemoryAdapter,
    Runner: NativeExecutableRunner,
{
    match failure {
        NativeContinuationCachedRetryFailure::Execution(execution) => {
            match execution.rebase() {
                Ok(failure_disposition) => Ok(cached_native_failure_progress(
                    attempt,
                    failure_disposition,
                    prior_attempts,
                )),
                Err(rebase_failure) => Err(Box::new(
                    NativeContinuationCachedRetryCycleFailure::FailureRebase(
                        Box::new(
                            NativeContinuationCachedRetryFailureRebaseCycle {
                                attempt,
                                failure: rebase_failure,
                                prior_attempts: prior_attempts.to_vec(),
                            },
                        ),
                    ),
                )),
            }
        },
        cached_failure
        @ (NativeContinuationCachedRetryFailure::Acquisition(
            _,
        )
        | NativeContinuationCachedRetryFailure::Binding(_)) => {
            Err(Box::new(NativeContinuationCachedRetryCycleFailure::Cached(
                Box::new(NativeContinuationCachedRetryAttemptFailure {
                    attempt,
                    failure: Box::new(cached_failure),
                    prior_attempts: prior_attempts.to_vec(),
                }),
            )))
        },
    }
}

fn reschedule_cached_guard<MemoryError, RunnerError>(
    resumption: NativeContinuationRetryResumption,
) -> NativeContinuationCachedRetryRescheduleResult<MemoryError, RunnerError> {
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
        Ok(NativeContinuationScheduleOutcome::Completed(completion)) => Err(
            Box::new(NativeContinuationCachedRetryCycleFailure::Reschedule(
                Box::new(
                    NativeContinuationCachedRetryRescheduleFailure::Completed(
                        Box::new(completion),
                    ),
                ),
            )),
        ),
        Err(failure) => Err(Box::new(
            NativeContinuationCachedRetryCycleFailure::Reschedule(Box::new(
                NativeContinuationCachedRetryRescheduleFailure::Execution(
                    failure,
                ),
            )),
        )),
    }
}
