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
//   - Synchronous monotonic latency instrumentation around one cached retry
//     cycle and transactional recording of its sample.
// - Must-Not:
//   - Change cycle routing, retry failed execution, persist telemetry, select
//     policy, or hide a completed/failed cycle behind telemetry failure.
// - Allows:
//   - Inputs: one cycle request, explicit execution resources, clock,
//     histogram.
//   - Outputs: exact cycle result plus recorded sample or typed telemetry
//     failure retaining that cycle result.
//   - Side effects: the ordinary cached cycle plus one clock interval and at
//     most one transactional histogram record.
// - Split-When:
//   - Async interval ownership, durable publication, or policy scheduling gains
//     authority.
// - Merge-When:
//   - Product orchestration owns measured execution through policy publication.
// - Summary:
//   - Measures and records one whole cached retry cycle without losing outcome.
// - Description:
//   - Clock or histogram failure occurs after cycle execution and preserves the
//     complete semantic result.
// - Usage:
//   - Supply one execution context and one latency instrumentation context.
// - Defaults:
//   - Exactly one sample is attempted per completed function invocation.
//

//! Synchronous measured execution for one complete cached retry cycle.

use super::{
    NativeContinuationCachedRetryCycleRequest,
    NativeContinuationCachedRetryCycleResult,
    NativeContinuationCachedRetryLatencyHistogram as LatencyHistogram,
    NativeContinuationCachedRetryLatencyHistogramError,
    NativeContinuationCachedRetryLatencyRecord,
    NativeContinuationCachedRetryLatencySample,
    begin_cached_retry_latency_measurement, execute_cached_native_retry_cycle,
    finish_cached_retry_latency_measurement,
};
use crate::execution_native::{
    NativeExecutableMemoryAdapter, NativeExecutableRunner,
    NativeExecutableSequenceLeaseCache,
};
use crate::monotonic_clock::NativeContinuationMonotonicClock;

/// Mutable execution resources for one measured cached retry cycle.
#[derive(Debug)]
pub struct NativeContinuationCachedRetryCycleExecution<
    'execution,
    MemoryAdapter,
    Runner,
> {
    cache: &'execution mut NativeExecutableSequenceLeaseCache,
    memory_adapter: &'execution mut MemoryAdapter,
    runner: &'execution mut Runner,
}

/// Mutable latency resources for one measured cached retry cycle.
#[derive(Debug)]
pub struct NativeContinuationCachedRetryCycleInstrumentation<'telemetry, Clock>
{
    clock: &'telemetry mut Clock,
    histogram: &'telemetry mut LatencyHistogram,
}

/// Result of one measured cycle retaining semantic execution in every branch.
#[derive(Debug)]
pub enum NativeContinuationCachedRetryMeasuredCycle<
    MemoryError,
    RunnerError,
    ClockError,
> {
    /// Cycle completed its semantic work but the clock could not finish.
    ClockFailure {
        /// Exact semantic result already produced by the cached cycle.
        cycle:
            NativeContinuationCachedRetryCycleResult<MemoryError, RunnerError>,
        /// Adapter-local monotonic clock failure.
        error: ClockError,
    },
    /// Cycle and clock completed, but transactional histogram record failed.
    HistogramFailure {
        /// Exact semantic result already produced by the cached cycle.
        cycle:
            NativeContinuationCachedRetryCycleResult<MemoryError, RunnerError>,
        /// Exact histogram overflow/failure evidence.
        error: NativeContinuationCachedRetryLatencyHistogramError,
        /// Exact completed monotonic sample that could not be recorded.
        sample: NativeContinuationCachedRetryLatencySample,
    },
    /// Cycle, monotonic timing, and histogram publication all completed.
    Recorded {
        /// Exact semantic result produced by the cached cycle.
        cycle:
            NativeContinuationCachedRetryCycleResult<MemoryError, RunnerError>,
        /// Exact transactional histogram publication evidence.
        record: NativeContinuationCachedRetryLatencyRecord,
        /// Exact monotonic sample represented by the record.
        sample: NativeContinuationCachedRetryLatencySample,
    },
}

type MeasuredCycle<MemoryError, RunnerError, ClockError> =
    NativeContinuationCachedRetryMeasuredCycle<
        MemoryError,
        RunnerError,
        ClockError,
    >;

impl<'execution, MemoryAdapter, Runner>
    NativeContinuationCachedRetryCycleExecution<
        'execution,
        MemoryAdapter,
        Runner,
    >
{
    /// Binds the cache, memory adapter, and runner for one cycle invocation.
    #[must_use]
    pub const fn new(
        cache: &'execution mut NativeExecutableSequenceLeaseCache,
        memory_adapter: &'execution mut MemoryAdapter,
        runner: &'execution mut Runner,
    ) -> Self {
        Self {
            cache,
            memory_adapter,
            runner,
        }
    }
}

impl<'telemetry, Clock>
    NativeContinuationCachedRetryCycleInstrumentation<'telemetry, Clock>
{
    /// Binds one monotonic clock and process-local latency histogram.
    #[must_use]
    pub const fn new(
        clock: &'telemetry mut Clock,
        histogram: &'telemetry mut LatencyHistogram,
    ) -> Self {
        Self { clock, histogram }
    }
}

impl<MemoryError, RunnerError, ClockError>
    NativeContinuationCachedRetryMeasuredCycle<
        MemoryError,
        RunnerError,
        ClockError,
    >
{
    /// Returns the exact semantic cached-cycle result.
    pub const fn cycle(
        &self,
    ) -> &NativeContinuationCachedRetryCycleResult<MemoryError, RunnerError>
    {
        match self {
            Self::ClockFailure { cycle, .. }
            | Self::HistogramFailure { cycle, .. }
            | Self::Recorded { cycle, .. } => cycle,
        }
    }

    /// Consumes measured evidence into the exact semantic cached-cycle result.
    ///
    /// # Errors
    ///
    /// Returns the original cached-cycle failure unchanged when semantic
    /// execution failed.
    pub fn into_cycle(
        self,
    ) -> NativeContinuationCachedRetryCycleResult<MemoryError, RunnerError>
    {
        match self {
            Self::ClockFailure { cycle, .. }
            | Self::HistogramFailure { cycle, .. }
            | Self::Recorded { cycle, .. } => cycle,
        }
    }

    /// Reports whether the completed interval was recorded transactionally.
    #[must_use]
    pub const fn is_recorded(&self) -> bool {
        matches!(self, Self::Recorded { .. })
    }

    /// Returns histogram publication evidence when recording succeeded.
    #[must_use]
    pub const fn record(
        &self,
    ) -> Option<NativeContinuationCachedRetryLatencyRecord> {
        match self {
            Self::Recorded { record, .. } => Some(*record),
            Self::ClockFailure { .. } | Self::HistogramFailure { .. } => None,
        }
    }

    /// Returns a completed monotonic sample when clock finishing succeeded.
    #[must_use]
    pub const fn sample(
        &self,
    ) -> Option<NativeContinuationCachedRetryLatencySample> {
        match self {
            Self::ClockFailure { .. } => None,
            Self::HistogramFailure { sample, .. }
            | Self::Recorded { sample, .. } => Some(*sample),
        }
    }
}

/// Executes, measures, and transactionally records one whole cached retry
/// cycle.
#[must_use]
pub fn execute_measured_cached_native_retry_cycle<
    MemoryAdapter,
    Runner,
    Clock,
    MemoryError,
    RunnerError,
    ClockError,
>(
    request: NativeContinuationCachedRetryCycleRequest,
    execution: &mut NativeContinuationCachedRetryCycleExecution<
        '_,
        MemoryAdapter,
        Runner,
    >,
    instrumentation: &mut NativeContinuationCachedRetryCycleInstrumentation<
        '_,
        Clock,
    >,
) -> MeasuredCycle<MemoryError, RunnerError, ClockError>
where
    Clock: NativeContinuationMonotonicClock<Error = ClockError>,
    MemoryAdapter: NativeExecutableMemoryAdapter<Error = MemoryError>,
    Runner: NativeExecutableRunner<Error = RunnerError>,
{
    let measurement =
        begin_cached_retry_latency_measurement(instrumentation.clock);
    let cycle = execute_cached_native_retry_cycle(
        request,
        execution.cache,
        execution.memory_adapter,
        execution.runner,
    );
    let sample = match finish_cached_retry_latency_measurement(
        instrumentation.clock,
        measurement,
    ) {
        Ok(sample) => sample,
        Err(error) => {
            return NativeContinuationCachedRetryMeasuredCycle::ClockFailure {
                cycle,
                error,
            };
        },
    };
    match instrumentation.histogram.record(sample) {
        Ok(record) => NativeContinuationCachedRetryMeasuredCycle::Recorded {
            cycle,
            record,
            sample,
        },
        Err(error) => {
            NativeContinuationCachedRetryMeasuredCycle::HistogramFailure {
                cycle,
                error,
                sample,
            }
        },
    }
}
