// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - One synchronous cached-cycle execution plus atomic process-local count
//     and latency telemetry publication.
// - Must-Not:
//   - Persist telemetry, select policy, retry execution, or hide cycle results.
// - Allows:
//   - Inputs: one cycle request, execution resources, monotonic clock, count
//     window, and latency histogram.
//   - Outputs: exact cycle result plus typed telemetry publication evidence.
//   - Side effects: one cached cycle, one clock interval, and all-or-nothing
//     count-window plus latency-histogram publication.
// - Split-When:
//   - Durable publication, async ownership, or policy scheduling gains
//     authority.
// - Merge-When:
//   - Product orchestration owns observed execution through adaptive policy.
// - Summary:
//   - Publishes count and latency evidence from the same cached cycle
//     atomically.
// - Description:
//   - Candidate telemetry owners absorb all fallible updates before
//     publication.
// - Usage:
//   - Execute one cycle through explicit execution and observation contexts.
// - Defaults:
//   - Clock state advances even when process-local telemetry publication fails.
//

//! Atomic count and latency observation for one synchronous cached retry cycle.

use super::{
    NativeContinuationCachedRetryCycleExecution,
    NativeContinuationCachedRetryCycleInstrumentation,
    NativeContinuationCachedRetryCycleRequest,
    NativeContinuationCachedRetryCycleResult,
    NativeContinuationCachedRetryLatencyHistogram as LatencyHistogram,
    NativeContinuationCachedRetryLatencyHistogramError,
    NativeContinuationCachedRetryLatencyRecord,
    NativeContinuationCachedRetryLatencySample,
    NativeContinuationCachedRetryMeasuredCycle,
    NativeContinuationCachedRetryTelemetry,
    NativeContinuationCachedRetryTelemetryError,
    NativeContinuationCachedRetryTelemetryWindow,
    NativeContinuationCachedRetryTelemetryWindowAppend,
    NativeContinuationCachedRetryTelemetryWindowError,
    execute_measured_cached_native_retry_cycle,
    summarize_cached_retry_cycle_result,
};
use crate::execution_native::{
    NativeExecutableMemoryAdapter, NativeExecutableRunner,
};
use crate::monotonic_clock::NativeContinuationMonotonicClock;

/// Mutable process-local telemetry owners for one observed cached retry cycle.
#[derive(Debug)]
pub struct NativeContinuationCachedRetryCycleObservation<'telemetry, Clock> {
    clock: &'telemetry mut Clock,
    histogram: &'telemetry mut LatencyHistogram,
    window: &'telemetry mut NativeContinuationCachedRetryTelemetryWindow,
}

/// Telemetry publication evidence for one already-executed cached retry cycle.
#[derive(Debug)]
pub enum NativeContinuationCachedRetryCycleTelemetryPublication<ClockError> {
    /// The cycle completed but monotonic interval finishing failed.
    ClockFailure {
        /// Adapter-local monotonic clock failure.
        error: ClockError,
    },
    /// The cycle and clock completed but latency recording failed.
    HistogramFailure {
        /// Exact transactional histogram failure.
        error: NativeContinuationCachedRetryLatencyHistogramError,
        /// Exact completed sample rejected by the candidate histogram.
        sample: NativeContinuationCachedRetryLatencySample,
    },
    /// Count and latency evidence committed atomically to both caller owners.
    Published {
        /// Exact latency histogram publication evidence.
        latency: NativeContinuationCachedRetryLatencyRecord,
        /// Exact completed monotonic sample represented by the latency record.
        sample: NativeContinuationCachedRetryLatencySample,
        /// Exact count summary derived from this cycle result.
        telemetry: NativeContinuationCachedRetryTelemetry,
        /// Exact count-window publication evidence.
        window: Box<NativeContinuationCachedRetryTelemetryWindowAppend>,
    },
    /// The cycle and timing completed but count summarization overflowed.
    SummaryFailure {
        /// Exact count-telemetry aggregation failure.
        error: NativeContinuationCachedRetryTelemetryError,
        /// Exact completed sample retained from timing.
        sample: NativeContinuationCachedRetryLatencySample,
    },
    /// Both candidates were valid but count-window publication failed.
    WindowFailure {
        /// Exact completed sample retained from timing.
        sample: NativeContinuationCachedRetryLatencySample,
        /// Exact count summary rejected by the candidate window.
        telemetry: NativeContinuationCachedRetryTelemetry,
        /// Exact transactional count-window failure.
        error: NativeContinuationCachedRetryTelemetryWindowError,
    },
}

/// One exact cycle result with its independent telemetry-publication evidence.
#[derive(Debug)]
pub struct NativeContinuationCachedRetryObservedCycle<
    MemoryError,
    RunnerError,
    ClockError,
> {
    cycle: NativeContinuationCachedRetryCycleResult<MemoryError, RunnerError>,
    publication:
        NativeContinuationCachedRetryCycleTelemetryPublication<ClockError>,
}

type TelemetryPublication<ClockError> =
    NativeContinuationCachedRetryCycleTelemetryPublication<ClockError>;

struct ObservedCycleCandidate<MemoryError, RunnerError> {
    candidate_histogram: LatencyHistogram,
    cycle: NativeContinuationCachedRetryCycleResult<MemoryError, RunnerError>,
    latency: NativeContinuationCachedRetryLatencyRecord,
    sample: NativeContinuationCachedRetryLatencySample,
}

struct ObservedCycleTelemetryOwners<'telemetry> {
    histogram: &'telemetry mut LatencyHistogram,
    window: &'telemetry mut NativeContinuationCachedRetryTelemetryWindow,
}

type ObservedCycle<MemoryError, RunnerError, ClockError> =
    NativeContinuationCachedRetryObservedCycle<
        MemoryError,
        RunnerError,
        ClockError,
    >;

impl<'telemetry, Clock>
    NativeContinuationCachedRetryCycleObservation<'telemetry, Clock>
{
    /// Binds one clock and both process-local telemetry owners.
    #[must_use]
    pub const fn new(
        clock: &'telemetry mut Clock,
        histogram: &'telemetry mut LatencyHistogram,
        window: &'telemetry mut NativeContinuationCachedRetryTelemetryWindow,
    ) -> Self {
        Self { clock, histogram, window }
    }
}

impl<MemoryError, RunnerError, ClockError>
    NativeContinuationCachedRetryObservedCycle<
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
        &self.cycle
    }

    /// Consumes observation evidence into the exact semantic cycle result.
    ///
    /// # Errors
    ///
    /// Returns the original cached-cycle failure unchanged when execution
    /// failed.
    pub fn into_cycle(
        self,
    ) -> NativeContinuationCachedRetryCycleResult<MemoryError, RunnerError>
    {
        self.cycle
    }

    /// Reports whether both process-local telemetry owners were published.
    #[must_use]
    pub const fn is_published(&self) -> bool {
        matches!(self.publication, TelemetryPublication::Published { .. })
    }

    /// Returns exact telemetry-publication evidence for this cycle.
    #[must_use]
    pub const fn publication(
        &self,
    ) -> &NativeContinuationCachedRetryCycleTelemetryPublication<ClockError>
    {
        &self.publication
    }
}

/// Executes one cycle and atomically publishes its count and latency telemetry.
#[must_use]
pub fn execute_observed_cached_native_retry_cycle<
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
    observation: &mut NativeContinuationCachedRetryCycleObservation<'_, Clock>,
) -> ObservedCycle<MemoryError, RunnerError, ClockError>
where
    Clock: NativeContinuationMonotonicClock<Error = ClockError>,
    MemoryAdapter: NativeExecutableMemoryAdapter<Error = MemoryError>,
    Runner: NativeExecutableRunner<Error = RunnerError>,
{
    let mut candidate_histogram = observation.histogram.clone();
    let mut instrumentation =
        NativeContinuationCachedRetryCycleInstrumentation::new(
            observation.clock,
            &mut candidate_histogram,
        );
    let measured = execute_measured_cached_native_retry_cycle(
        request,
        execution,
        &mut instrumentation,
    );
    let (cycle, latency, sample) = match measured {
        NativeContinuationCachedRetryMeasuredCycle::ClockFailure {
            cycle,
            error,
        } => {
            return NativeContinuationCachedRetryObservedCycle {
                cycle,
                publication: TelemetryPublication::ClockFailure { error },
            };
        },
        NativeContinuationCachedRetryMeasuredCycle::HistogramFailure {
            cycle,
            error,
            sample,
        } => {
            return NativeContinuationCachedRetryObservedCycle {
                cycle,
                publication: TelemetryPublication::HistogramFailure {
                    error,
                    sample,
                },
            };
        },
        NativeContinuationCachedRetryMeasuredCycle::Recorded {
            cycle,
            record,
            sample,
        } => (cycle, record, sample),
    };
    let candidate = ObservedCycleCandidate {
        candidate_histogram,
        cycle,
        latency,
        sample,
    };
    let mut owners = ObservedCycleTelemetryOwners {
        histogram: observation.histogram,
        window: observation.window,
    };
    publish_observed_cycle_telemetry(candidate, &mut owners)
}

fn publish_observed_cycle_telemetry<MemoryError, RunnerError, ClockError>(
    candidate: ObservedCycleCandidate<MemoryError, RunnerError>,
    owners: &mut ObservedCycleTelemetryOwners<'_>,
) -> ObservedCycle<MemoryError, RunnerError, ClockError> {
    let ObservedCycleCandidate {
        candidate_histogram,
        cycle,
        latency,
        sample,
    } = candidate;
    let telemetry = match summarize_cached_retry_cycle_result(&cycle) {
        Ok(telemetry) => telemetry,
        Err(error) => {
            return NativeContinuationCachedRetryObservedCycle {
                cycle,
                publication: TelemetryPublication::SummaryFailure {
                    error,
                    sample,
                },
            };
        },
    };
    let mut candidate_window = owners.window.clone();
    let window_append = match candidate_window.append(telemetry) {
        Ok(window_append) => window_append,
        Err(error) => {
            return NativeContinuationCachedRetryObservedCycle {
                cycle,
                publication: TelemetryPublication::WindowFailure {
                    sample,
                    telemetry,
                    error,
                },
            };
        },
    };
    *owners.histogram = candidate_histogram;
    *owners.window = candidate_window;
    NativeContinuationCachedRetryObservedCycle {
        cycle,
        publication: TelemetryPublication::Published {
            latency,
            sample,
            telemetry,
            window: Box::new(window_append),
        },
    }
}
