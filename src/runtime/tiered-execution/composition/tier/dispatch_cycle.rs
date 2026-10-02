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
//   - Bounded synchronous orchestration of queued affine continuation worker
//     turns under an explicit caller-provided decision sequence.
// - Must-Not:
//   - Spawn or detach workers, infer scheduling decisions, retry per-item
//     failures, persist queue state, or discard completed worker evidence.
// - Allows:
//   - Inputs: one dispatch queue and one finite ordered scheduler-decision
//     slice.
//   - Outputs: the complete ordered worked prefix plus an explicit stop reason.
//   - Side effects: only those of the delegated synchronous worker turns.
// - Split-When:
//   - Background/parallel lifecycle, durable orchestration, or distributed
//     scheduling gains independent policy.
// - Merge-When:
//   - One product coordinator owns queue admission, draining, and routing.
// - Summary:
//   - Drains a bounded explicit decision sequence without losing item evidence.
// - Description:
//   - Per-item semantic or timing failures remain worked evidence; only idle or
//     pre-dispatch backpressure stops the cycle before another owner moves.
// - Usage:
//   - Supply one explicit decision per desired FIFO worker turn.
// - Defaults:
//   - Empty decision slices do no work and stop as decision-exhausted.
//

//! Bounded synchronous orchestration for affine continuation dispatch workers.

use crate::cached_cycle::NativeContinuationCachedRetryLatencyIntervalBeginError;
use crate::continuation_dispatch_queue::NativeContinuationDispatchQueue;
use crate::continuation_dispatch_worker::{
    NativeContinuationDispatchWorkerCompletion,
    NativeContinuationDispatchWorkerTurn,
    execute_next_native_continuation_dispatch,
};
use crate::continuation_scheduler::NativeContinuationScheduleDecision;
use crate::monotonic_clock::NativeContinuationMonotonicClock;

/// Why one bounded synchronous dispatch-worker cycle stopped.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchWorkerCycleStop {
    /// Queue timing capacity/identity blocked before another handoff moved.
    Blocked(NativeContinuationCachedRetryLatencyIntervalBeginError),
    /// Every explicit caller-provided decision was consumed.
    DecisionsExhausted,
    /// The queue had no pending affine handoff for the next decision.
    Idle,
}

/// Ordered owned completions retained by one dispatch-worker cycle.
pub type NativeContinuationDispatchWorkerCompletionList<ClockError> =
    Vec<Box<NativeContinuationDispatchWorkerCompletion<ClockError>>>;

/// Complete evidence from one bounded synchronous dispatch-worker cycle.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationDispatchWorkerCycle<ClockError> {
    completions: NativeContinuationDispatchWorkerCompletionList<ClockError>,
    stop: NativeContinuationDispatchWorkerCycleStop,
}

impl<ClockError> NativeContinuationDispatchWorkerCycle<ClockError> {
    /// Returns worked completions in exact FIFO dispatch order.
    #[must_use]
    pub const fn completions(
        &self,
    ) -> &NativeContinuationDispatchWorkerCompletionList<ClockError> {
        &self.completions
    }

    /// Consumes the cycle into exact ordered worked completion ownership.
    #[must_use]
    pub fn into_completions(
        self,
    ) -> NativeContinuationDispatchWorkerCompletionList<ClockError> {
        self.completions
    }

    /// Returns why orchestration stopped before another worker turn.
    #[must_use]
    pub const fn stop(&self) -> NativeContinuationDispatchWorkerCycleStop {
        self.stop
    }
}

/// Executes at most one FIFO worker turn for each explicit scheduler decision.
///
/// Per-item semantic or latency failures are retained inside that item's worked
/// completion and do not cancel later independent queued owners. Empty queue or
/// pre-dispatch timing backpressure stops before consuming another handoff.
#[must_use]
pub fn execute_native_continuation_dispatch_cycle<Clock>(
    queue: &mut NativeContinuationDispatchQueue<Clock>,
    decisions: &[NativeContinuationScheduleDecision],
) -> NativeContinuationDispatchWorkerCycle<Clock::Error>
where
    Clock: NativeContinuationMonotonicClock,
{
    let mut completions = Vec::new();
    for decision in decisions {
        match execute_next_native_continuation_dispatch(queue, *decision) {
            Ok(NativeContinuationDispatchWorkerTurn::Idle) => {
                return NativeContinuationDispatchWorkerCycle {
                    completions,
                    stop: NativeContinuationDispatchWorkerCycleStop::Idle,
                };
            },
            Ok(NativeContinuationDispatchWorkerTurn::Worked(completion)) => {
                completions.push(completion);
            },
            Err(error) => {
                return NativeContinuationDispatchWorkerCycle {
                    completions,
                    stop: NativeContinuationDispatchWorkerCycleStop::Blocked(
                        error,
                    ),
                };
            },
        }
    }
    NativeContinuationDispatchWorkerCycle {
        completions,
        stop: NativeContinuationDispatchWorkerCycleStop::DecisionsExhausted,
    }
}
