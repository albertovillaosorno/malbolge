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
//   - Bounded process-local queue ownership for affine interpreter handoffs and
//     their dispatch-to-completion latency tracking.
// - Must-Not:
//   - Spawn workers, execute handoffs, persist queue state, infer completion
//     order, or correlate work identities across processes.
// - Allows:
//   - Inputs: affine handoffs, one monotonic clock, and positive
//     pending/in-flight bounds.
//   - Outputs: automatic work IDs, FIFO dispatched owners, recovered pending
//     cancellation, latency samples, or typed capacity/identity/completion
//     error.
//   - Side effects: bounded process-local allocation and delegated monotonic
//     observations only.
// - Split-When:
//   - Worker execution, durable queue identity, or distributed scheduling gains
//     authority.
// - Merge-When:
//   - One product coordinator owns queueing, dispatch, execution, and
//     completion.
// - Summary:
//   - Queues affine handoffs and tracks bounded dispatch completion by work ID.
// - Description:
//   - Queue admission retains handoff ownership on failure; dispatch starts one
//     hidden monotonic interval and completion may arrive out of dispatch
//     order.
// - Usage:
//   - Enqueue handoffs, dispatch FIFO owners to caller workers, then complete
//     the returned work ID after the caller resolves that exact owner.
// - Defaults:
//   - Full pending or in-flight capacity fails before ownership transfer;
//     unknown completion is non-mutating.
//

//! Bounded process-local affine-handoff dispatch and completion ownership.

use std::collections::VecDeque;
use std::fmt::{Debug, Formatter, Result as FormatResult};
use std::num::NonZeroUsize;

use crate::cached_cycle::{
    NativeContinuationCachedRetryLatencyIntervalBeginError,
    NativeContinuationCachedRetryLatencyIntervalFinishError,
    NativeContinuationCachedRetryLatencyIntervalId,
    NativeContinuationCachedRetryLatencyIntervalOwner,
    NativeContinuationCachedRetryLatencySample,
};
use crate::interpreter_handoff::NativeInterpreterHandoff;
use crate::monotonic_clock::NativeContinuationMonotonicClock;

/// Automatically assigned process-local identity for one queued handoff.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct NativeContinuationDispatchId(u64);

/// Why one affine handoff could not enter the pending queue.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchEnqueueError {
    /// The positive caller-selected pending queue bound is already full.
    Capacity {
        /// Positive configured pending queue bound.
        maximum_pending: NonZeroUsize,
        /// Exact number of handoffs currently retained as pending.
        pending: usize,
    },
    /// The one-based process-local work identity space is exhausted.
    IdentityExhausted,
}

/// Recoverable failed enqueue retaining the exact affine handoff owner.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationDispatchEnqueueFailure {
    error: NativeContinuationDispatchEnqueueError,
    handoff: NativeInterpreterHandoff,
}

/// Caller-owned handoff removed from the queue for external execution.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationDispatchedHandoff {
    handoff: NativeInterpreterHandoff,
    id: NativeContinuationDispatchId,
}

/// Why one returned dispatch identity could not close its latency interval.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchCompletionError<ClockError> {
    /// The monotonic clock consumed this dispatch start but failed to finish.
    Clock {
        /// Exact dispatch whose timing failed terminally.
        dispatch: NativeContinuationDispatchId,
        /// Adapter-local monotonic clock failure.
        error: ClockError,
    },
    /// Internal interval ownership was missing for a known dispatch.
    IntervalDrift {
        /// Exact dispatch whose hidden interval could not be found.
        dispatch: NativeContinuationDispatchId,
    },
    /// The caller supplied no currently tracked dispatched work identity.
    Unknown {
        /// Exact caller-supplied work identity.
        dispatch: NativeContinuationDispatchId,
    },
}

type LatencyIntervalFinishError<ClockError> =
    NativeContinuationCachedRetryLatencyIntervalFinishError<ClockError>;

struct InFlightDispatch {
    dispatch: NativeContinuationDispatchId,
    interval: NativeContinuationCachedRetryLatencyIntervalId,
}

struct PendingDispatch {
    handoff: NativeInterpreterHandoff,
    id: NativeContinuationDispatchId,
}

/// Bounded process-local owner for pending and externally dispatched handoffs.
pub struct NativeContinuationDispatchQueue<Clock>
where
    Clock: NativeContinuationMonotonicClock,
{
    in_flight: Vec<InFlightDispatch>,
    latency: NativeContinuationCachedRetryLatencyIntervalOwner<Clock>,
    maximum_pending: NonZeroUsize,
    next_identity: u64,
    pending: VecDeque<PendingDispatch>,
}

/// Completion result for one exact dispatched handoff identity.
pub type NativeContinuationDispatchCompletionResult<ClockError> = Result<
    NativeContinuationCachedRetryLatencySample,
    NativeContinuationDispatchCompletionError<ClockError>,
>;

/// Dispatch result preserving pending ownership when timing capacity is full.
pub type NativeContinuationDispatchResult = Result<
    Option<NativeContinuationDispatchedHandoff>,
    NativeContinuationCachedRetryLatencyIntervalBeginError,
>;

/// Enqueue result retaining the handoff inside any failed owner.
pub type NativeContinuationDispatchEnqueueResult = Result<
    NativeContinuationDispatchId,
    Box<NativeContinuationDispatchEnqueueFailure>,
>;

impl NativeContinuationDispatchEnqueueFailure {
    /// Returns why enqueue rejected the retained affine handoff.
    #[must_use]
    pub const fn error(&self) -> NativeContinuationDispatchEnqueueError {
        self.error
    }

    /// Restores the exact affine handoff rejected before queue ownership.
    #[must_use]
    pub fn into_handoff(self) -> NativeInterpreterHandoff {
        self.handoff
    }
}

impl NativeContinuationDispatchId {
    /// Returns the exact one-based process-local dispatch identity.
    #[must_use]
    pub const fn value(self) -> u64 {
        self.0
    }
}

impl NativeContinuationDispatchedHandoff {
    /// Returns this externally owned work identity.
    #[must_use]
    pub const fn id(&self) -> NativeContinuationDispatchId {
        self.id
    }

    /// Transfers the exact affine handoff to the caller's execution boundary.
    #[must_use]
    pub fn into_handoff(self) -> NativeInterpreterHandoff {
        self.handoff
    }
}

impl<Clock> Debug for NativeContinuationDispatchQueue<Clock>
where
    Clock: NativeContinuationMonotonicClock,
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.debug_struct("NativeContinuationDispatchQueue")
            .field("in_flight", &self.in_flight.len())
            .field("maximum_in_flight", &self.latency.maximum_in_flight())
            .field("maximum_pending", &self.maximum_pending)
            .field("next_identity", &self.next_identity)
            .field("pending", &self.pending.len())
            .finish_non_exhaustive()
    }
}

impl<Clock> NativeContinuationDispatchQueue<Clock>
where
    Clock: NativeContinuationMonotonicClock,
{
    /// Cancels one pending work identity and restores its affine handoff owner.
    pub fn cancel_pending(
        &mut self,
        dispatch: NativeContinuationDispatchId,
    ) -> Option<NativeInterpreterHandoff> {
        let index = self
            .pending
            .iter()
            .position(|candidate| candidate.id == dispatch)?;
        self.pending.remove(index).map(|pending| pending.handoff)
    }

    /// Borrows the owned monotonic clock for read-only adapter diagnostics.
    #[must_use]
    pub const fn clock(&self) -> &Clock {
        self.latency.clock()
    }

    /// Closes latency tracking for one exact caller-resolved dispatch identity.
    ///
    /// Completion may arrive out of dispatch order. The tracking entry is
    /// consumed before finishing the hidden interval because that interval's
    /// opaque clock start is itself consumed by the clock.
    ///
    /// # Errors
    ///
    /// Returns unknown identity without mutation, adapter-local clock failure
    /// after consuming only the selected dispatch, or internal interval drift.
    pub fn complete(
        &mut self,
        dispatch: NativeContinuationDispatchId,
    ) -> NativeContinuationDispatchCompletionResult<Clock::Error> {
        let Some(index) = self
            .in_flight
            .iter()
            .position(|candidate| candidate.dispatch == dispatch)
        else {
            return Err(NativeContinuationDispatchCompletionError::Unknown {
                dispatch,
            });
        };
        let in_flight = self.in_flight.remove(index);
        self.latency.finish_interval(in_flight.interval).map_err(
            |interval_error| match interval_error {
                LatencyIntervalFinishError::Clock { error, .. } => {
                    NativeContinuationDispatchCompletionError::Clock {
                        dispatch,
                        error,
                    }
                },
                LatencyIntervalFinishError::Unknown { .. } => {
                    NativeContinuationDispatchCompletionError::IntervalDrift {
                        dispatch,
                    }
                },
            },
        )
    }

    /// Dispatches the oldest pending affine owner and begins its latency
    /// interval.
    ///
    /// In-flight interval capacity is checked before pending ownership moves,
    /// so capacity failure leaves FIFO queue state unchanged.
    ///
    /// # Errors
    ///
    /// Returns interval capacity or identity failure without removing a pending
    /// handoff.
    pub fn dispatch_next(&mut self) -> NativeContinuationDispatchResult {
        if self.pending.is_empty() {
            return Ok(None);
        }
        let interval = self.latency.begin_interval()?;
        let Some(pending) = self.pending.pop_front() else {
            let _cancelled = self.latency.cancel_interval(interval);
            return Ok(None);
        };
        self.in_flight.push(InFlightDispatch {
            dispatch: pending.id,
            interval,
        });
        Ok(Some(NativeContinuationDispatchedHandoff {
            handoff: pending.handoff,
            id: pending.id,
        }))
    }

    /// Enqueues one affine handoff under a new one-based process-local work ID.
    ///
    /// # Errors
    ///
    /// Returns capacity or identity exhaustion while retaining the exact
    /// handoff in the failure owner.
    pub fn enqueue(
        &mut self,
        handoff: NativeInterpreterHandoff,
    ) -> NativeContinuationDispatchEnqueueResult {
        if self.pending.len() >= self.maximum_pending.get() {
            return Err(Box::new(NativeContinuationDispatchEnqueueFailure {
                error: NativeContinuationDispatchEnqueueError::Capacity {
                    maximum_pending: self.maximum_pending,
                    pending: self.pending.len(),
                },
                handoff,
            }));
        }
        let Some(next_identity) = self.next_identity.checked_add(1) else {
            return Err(Box::new(NativeContinuationDispatchEnqueueFailure {
                error:
                    NativeContinuationDispatchEnqueueError::IdentityExhausted,
                handoff,
            }));
        };
        let id = NativeContinuationDispatchId(next_identity);
        self.pending.push_back(PendingDispatch { handoff, id });
        self.next_identity = next_identity;
        Ok(id)
    }

    /// Returns the exact number of dispatches awaiting caller completion.
    #[must_use]
    pub const fn in_flight(&self) -> usize {
        self.in_flight.len()
    }

    /// Returns the positive configured concurrent dispatch bound.
    #[must_use]
    pub const fn maximum_in_flight(&self) -> NonZeroUsize {
        self.latency.maximum_in_flight()
    }

    /// Returns the positive configured pending queue bound.
    #[must_use]
    pub const fn maximum_pending(&self) -> NonZeroUsize {
        self.maximum_pending
    }

    /// Constructs an empty process-local affine handoff dispatch queue.
    #[must_use]
    pub const fn new(
        clock: Clock,
        maximum_pending: NonZeroUsize,
        maximum_in_flight: NonZeroUsize,
    ) -> Self {
        Self {
            in_flight: Vec::new(),
            latency: NativeContinuationCachedRetryLatencyIntervalOwner::new(
                clock,
                maximum_in_flight,
            ),
            maximum_pending,
            next_identity: 0,
            pending: VecDeque::new(),
        }
    }

    /// Returns the exact number of affine handoffs awaiting dispatch.
    #[must_use]
    pub fn pending(&self) -> usize {
        self.pending.len()
    }
}
