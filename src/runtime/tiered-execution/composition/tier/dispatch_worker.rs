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
//   - One synchronous process-local worker turn from queued affine handoff
//     dispatch through explicit scheduler execution and latency completion.
// - Must-Not:
//   - Spawn threads, detach work, persist queue identity, choose scheduling
//     policy, retry semantic failures, or hide completion-timing failure.
// - Allows:
//   - Inputs: one bounded dispatch queue and one explicit scheduler decision.
//   - Outputs: idle evidence, one identified semantic result plus independent
//     latency completion, or pre-dispatch capacity/identity failure.
//   - Side effects: normative interpreter work selected by the caller and the
//     queue's delegated monotonic observations.
// - Split-When:
//   - Parallel/background workers, persistent pools, or distributed execution
//     gain independent lifecycle or failure semantics.
// - Merge-When:
//   - One product coordinator owns dequeue, execution, timing, and routing.
// - Summary:
//   - Executes one queued affine handoff synchronously without conflating
//     semantic and timing outcomes.
// - Description:
//   - A dispatched handoff is scheduled exactly once; timing completion runs
//     after either semantic success or semantic failure.
// - Usage:
//   - Call `execute_next_native_continuation_dispatch()` with one explicit
//     decision for the next FIFO owner.
// - Defaults:
//   - Empty queues are idle; queue backpressure returns before handoff
//     transfer.
//

//! Synchronous execution of one bounded affine continuation dispatch.

use crate::cached_cycle::{
    NativeContinuationCachedRetryLatencyIntervalBeginError,
    NativeContinuationCachedRetryLatencySample,
};
use crate::continuation_dispatch_queue::{
    NativeContinuationDispatchCompletionError, NativeContinuationDispatchId,
    NativeContinuationDispatchQueue,
};
use crate::continuation_scheduler::{
    NativeContinuationScheduleDecision, NativeContinuationScheduleOutcome,
    schedule_native_interpreter_handoff,
};
use crate::interpreter_handoff::NativeInterpreterHandoffExecutionFailure;
use crate::monotonic_clock::NativeContinuationMonotonicClock;

/// Semantic disposition produced while executing one dispatched handoff.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchWorkerSemantic {
    /// Normative scheduler work failed while retaining exact failure evidence.
    Failed(Box<NativeInterpreterHandoffExecutionFailure>),
    /// The explicit scheduler decision completed or suspended successfully.
    Scheduled(Box<NativeContinuationScheduleOutcome>),
}

/// One identified synchronous worker result with independent timing evidence.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationDispatchWorkerCompletion<ClockError> {
    dispatch: NativeContinuationDispatchId,
    latency: Result<
        NativeContinuationCachedRetryLatencySample,
        NativeContinuationDispatchCompletionError<ClockError>,
    >,
    semantic: NativeContinuationDispatchWorkerSemantic,
}

/// Result of attempting one synchronous process-local worker turn.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchWorkerTurn<ClockError> {
    /// No affine handoff was queued, so no clock interval or scheduler ran.
    Idle,
    /// One FIFO handoff was executed and its timing completion was attempted.
    Worked(Box<NativeContinuationDispatchWorkerCompletion<ClockError>>),
}

/// Result of one synchronous worker-turn attempt.
pub type NativeContinuationDispatchWorkerResult<ClockError> = Result<
    NativeContinuationDispatchWorkerTurn<ClockError>,
    NativeContinuationCachedRetryLatencyIntervalBeginError,
>;

impl<ClockError> NativeContinuationDispatchWorkerCompletion<ClockError> {
    /// Returns the exact process-local work identity that was executed.
    #[must_use]
    pub const fn dispatch(&self) -> NativeContinuationDispatchId {
        self.dispatch
    }

    /// Returns independent dispatch-to-completion latency evidence.
    ///
    /// # Errors
    ///
    /// Returns the exact timing-completion failure without changing semantic
    /// disposition.
    pub const fn latency(
        &self,
    ) -> Result<
        &NativeContinuationCachedRetryLatencySample,
        &NativeContinuationDispatchCompletionError<ClockError>,
    > {
        self.latency.as_ref()
    }

    /// Returns the retained semantic scheduler disposition.
    #[must_use]
    pub const fn semantic(&self) -> &NativeContinuationDispatchWorkerSemantic {
        &self.semantic
    }
}

/// Executes at most one queued affine handoff under one explicit decision.
///
/// Queue dispatch starts latency tracking before ownership moves. The scheduler
/// then consumes the handoff exactly once. Timing completion runs afterward for
/// both scheduler success and scheduler failure, and its result remains
/// independent from semantic disposition.
///
/// # Errors
///
/// Returns the queue's interval begin failure before pending ownership moves.
pub fn execute_next_native_continuation_dispatch<Clock>(
    queue: &mut NativeContinuationDispatchQueue<Clock>,
    decision: NativeContinuationScheduleDecision,
) -> NativeContinuationDispatchWorkerResult<Clock::Error>
where
    Clock: NativeContinuationMonotonicClock,
{
    let Some(work) = queue.dispatch_next()? else {
        return Ok(NativeContinuationDispatchWorkerTurn::Idle);
    };
    let dispatch = work.id();
    let semantic = match schedule_native_interpreter_handoff(
        work.into_handoff(),
        decision,
    ) {
        Ok(outcome) => NativeContinuationDispatchWorkerSemantic::Scheduled(
            Box::new(outcome),
        ),
        Err(failure) => {
            NativeContinuationDispatchWorkerSemantic::Failed(failure)
        },
    };
    let latency = queue.complete(dispatch);
    Ok(NativeContinuationDispatchWorkerTurn::Worked(Box::new(
        NativeContinuationDispatchWorkerCompletion {
            dispatch,
            latency,
            semantic,
        },
    )))
}
