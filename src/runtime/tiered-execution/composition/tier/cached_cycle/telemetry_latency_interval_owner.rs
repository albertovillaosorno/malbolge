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
//   - Bounded process-local ownership of overlapping cached-retry latency
//     intervals.
// - Must-Not:
//   - Execute work, spawn tasks, persist clock state, expose start tokens,
//     infer completion order, or correlate clocks across processes.
// - Allows:
//   - Inputs: one monotonic clock and a positive in-flight interval bound.
//   - Outputs: automatic interval IDs, explicit latency samples, cancellation,
//     or typed capacity/identity/clock failure evidence.
//   - Side effects: delegated monotonic begin/finish observations and bounded
//     process-local allocation only.
// - Split-When:
//   - Durable timing identity, task execution, or distributed ordering gains
//     authority.
// - Merge-When:
//   - Product async orchestration owns the complete interval lifecycle.
// - Summary:
//   - Owns multiple caller-delimited monotonic intervals without start leakage.
// - Description:
//   - Starts receive increasing one-based IDs and may finish in any order.
// - Usage:
//   - Begin before dispatch, retain the ID with caller work, then finish or
//     cancel that exact interval when the work resolves.
// - Defaults:
//   - Capacity and ID exhaustion fail before reading the clock; finish failure
//     consumes the interval because the opaque clock start was consumed.
//

//! Bounded process-local ownership for overlapping cached-retry latency timing.

use std::fmt::{Debug, Formatter, Result as FormatResult};
use std::num::NonZeroUsize;

use super::NativeContinuationCachedRetryLatencySample;
use crate::monotonic_clock::NativeContinuationMonotonicClock;

/// Automatically assigned process-local identity for one pending interval.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct NativeContinuationCachedRetryLatencyIntervalId(u64);

/// Why one automatic latency interval could not begin without mutation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryLatencyIntervalBeginError {
    /// The positive caller-selected in-flight interval bound is already full.
    Capacity {
        /// Exact number of intervals currently retained by the owner.
        in_flight: usize,
        /// Positive configured concurrent interval bound.
        maximum_in_flight: NonZeroUsize,
    },
    /// The one-based process-local interval identity space is exhausted.
    IdentityExhausted,
}

/// Why one owned latency interval could not finish successfully.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryLatencyIntervalFinishError<ClockError> {
    /// The clock consumed the interval start but could not produce elapsed
    /// time.
    Clock {
        /// Exact interval whose start token was consumed by the clock.
        interval: NativeContinuationCachedRetryLatencyIntervalId,
        /// Adapter-local monotonic clock failure.
        error: ClockError,
    },
    /// The selected interval was not retained by this owner.
    Unknown {
        /// Exact caller-supplied interval identity.
        interval: NativeContinuationCachedRetryLatencyIntervalId,
    },
}

type IntervalBeginError =
    NativeContinuationCachedRetryLatencyIntervalBeginError;
type IntervalFinishError<ClockError> =
    NativeContinuationCachedRetryLatencyIntervalFinishError<ClockError>;
type LatencyIntervalFinishResult<ClockError> = Result<
    NativeContinuationCachedRetryLatencySample,
    NativeContinuationCachedRetryLatencyIntervalFinishError<ClockError>,
>;

struct PendingLatencyInterval<Start> {
    id: NativeContinuationCachedRetryLatencyIntervalId,
    start: Start,
}

/// Process-local owner of bounded overlapping monotonic latency intervals.
pub struct NativeContinuationCachedRetryLatencyIntervalOwner<Clock>
where
    Clock: NativeContinuationMonotonicClock,
{
    clock: Clock,
    maximum_in_flight: NonZeroUsize,
    next_identity: u64,
    pending: Vec<PendingLatencyInterval<Clock::Start>>,
}

impl NativeContinuationCachedRetryLatencyIntervalId {
    /// Returns the exact one-based process-local interval identity.
    #[must_use]
    pub const fn value(self) -> u64 {
        self.0
    }
}

impl<Clock> Debug for NativeContinuationCachedRetryLatencyIntervalOwner<Clock>
where
    Clock: NativeContinuationMonotonicClock,
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.debug_struct("NativeContinuationCachedRetryLatencyIntervalOwner")
            .field("maximum_in_flight", &self.maximum_in_flight)
            .field("next_identity", &self.next_identity)
            .field("in_flight", &self.pending.len())
            .finish_non_exhaustive()
    }
}

impl<Clock> NativeContinuationCachedRetryLatencyIntervalOwner<Clock>
where
    Clock: NativeContinuationMonotonicClock,
{
    /// Begins one automatically identified latency interval.
    ///
    /// Capacity and identity exhaustion are checked before the monotonic clock
    /// is observed, so rejection never consumes clock state.
    ///
    /// # Errors
    ///
    /// Returns capacity or identity-exhaustion evidence without mutation.
    pub fn begin_interval(
        &mut self,
    ) -> Result<
        NativeContinuationCachedRetryLatencyIntervalId,
        NativeContinuationCachedRetryLatencyIntervalBeginError,
    > {
        if self.pending.len() >= self.maximum_in_flight.get() {
            return Err(IntervalBeginError::Capacity {
                in_flight: self.pending.len(),
                maximum_in_flight: self.maximum_in_flight,
            });
        }
        let next_identity = self
            .next_identity
            .checked_add(1)
            .ok_or(IntervalBeginError::IdentityExhausted)?;
        let id = NativeContinuationCachedRetryLatencyIntervalId(next_identity);
        let start = self.clock.begin();
        self.pending.push(PendingLatencyInterval { id, start });
        self.next_identity = next_identity;
        Ok(id)
    }

    /// Cancels one exact pending interval without finishing its clock sample.
    ///
    /// Returns `true` only when the interval was retained and is now consumed.
    pub fn cancel_interval(
        &mut self,
        interval: NativeContinuationCachedRetryLatencyIntervalId,
    ) -> bool {
        let Some(index) = self
            .pending
            .iter()
            .position(|candidate| candidate.id == interval)
        else {
            return false;
        };
        let _cancelled = self.pending.remove(index);
        true
    }

    /// Borrows the owned clock for read-only adapter diagnostics.
    #[must_use]
    pub const fn clock(&self) -> &Clock {
        &self.clock
    }

    /// Finishes one exact pending interval into an explicit latency sample.
    ///
    /// Intervals may finish in any order. The opaque start is removed before
    /// calling the clock because the clock consumes it; clock failure therefore
    /// remains terminal for this interval while all other intervals survive.
    ///
    /// # Errors
    ///
    /// Returns unknown identity without mutation, or exact adapter-local clock
    /// failure after consuming the selected interval.
    pub fn finish_interval(
        &mut self,
        interval: NativeContinuationCachedRetryLatencyIntervalId,
    ) -> LatencyIntervalFinishResult<Clock::Error> {
        let Some(index) = self
            .pending
            .iter()
            .position(|candidate| candidate.id == interval)
        else {
            return Err(IntervalFinishError::Unknown { interval });
        };
        let pending = self.pending.remove(index);
        self.clock
            .elapsed_nanoseconds(pending.start)
            .map(NativeContinuationCachedRetryLatencySample::new)
            .map_err(|error| IntervalFinishError::Clock { interval, error })
    }

    /// Returns the exact number of currently retained unfinished intervals.
    #[must_use]
    pub const fn in_flight(&self) -> usize {
        self.pending.len()
    }

    /// Returns the positive configured concurrent interval bound.
    #[must_use]
    pub const fn maximum_in_flight(&self) -> NonZeroUsize {
        self.maximum_in_flight
    }

    /// Constructs an empty automatic interval owner around one monotonic clock.
    #[must_use]
    pub const fn new(clock: Clock, maximum_in_flight: NonZeroUsize) -> Self {
        Self {
            clock,
            maximum_in_flight,
            next_identity: 0,
            pending: Vec::new(),
        }
    }
}
