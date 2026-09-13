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
//   - Delimiting one cached-retry latency interval around caller-owned work.
// - Must-Not:
//   - Execute retry work, read wall time, mutate histograms, or select policy.
// - Allows:
//   - Inputs: one monotonic clock and one opaque started measurement owner.
//   - Outputs: exact latency sample or unchanged adapter-local clock failure.
//   - Side effects: delegated begin/finish monotonic clock observations only.
// - Split-When:
//   - Automatic cycle instrumentation or async interval ownership gains policy.
// - Merge-When:
//   - Cached-cycle execution owns timing and sampling atomically.
// - Summary:
//   - Turns caller-delimited monotonic intervals into explicit latency samples.
// - Description:
//   - Caller work remains outside this boundary between begin and finish calls.
// - Usage:
//   - Begin before one cycle, retain work outcome, then finish into one sample.
// - Defaults:
//   - Finishing never records the sample into a histogram automatically.
//

//! Monotonic cached-retry latency measurement without hidden execution effects.

use super::NativeContinuationCachedRetryLatencySample;
use crate::monotonic_clock::NativeContinuationMonotonicClock;

/// Opaque started latency interval retaining the selected clock's start token.
#[derive(Debug)]
pub struct NativeContinuationCachedRetryLatencyMeasurement<Start> {
    start: Start,
}

/// Begins one cached-retry latency interval before caller-owned execution.
pub fn begin_cached_retry_latency_measurement<Clock>(
    clock: &mut Clock,
) -> NativeContinuationCachedRetryLatencyMeasurement<Clock::Start>
where
    Clock: NativeContinuationMonotonicClock,
{
    NativeContinuationCachedRetryLatencyMeasurement { start: clock.begin() }
}

/// Finishes one cached-retry latency interval into an explicit sample.
///
/// # Errors
///
/// Returns only the selected clock adapter's elapsed-time failure. Caller-owned
/// retry execution and its result are not consumed by this boundary.
pub fn finish_cached_retry_latency_measurement<Clock>(
    clock: &mut Clock,
    measurement: NativeContinuationCachedRetryLatencyMeasurement<Clock::Start>,
) -> Result<NativeContinuationCachedRetryLatencySample, Clock::Error>
where
    Clock: NativeContinuationMonotonicClock,
{
    clock
        .elapsed_nanoseconds(measurement.start)
        .map(NativeContinuationCachedRetryLatencySample::new)
}
