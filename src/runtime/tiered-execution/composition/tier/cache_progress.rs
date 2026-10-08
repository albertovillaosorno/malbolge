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
//   - Callback-completion progress notices for one finite supervised retry
//     worker without exposing mutable lifecycle or callback result values.
// - Must-Not:
//   - Detach workers, share retry state, guess wait readiness, block a worker
//     on a notification, preempt callbacks, or persist progress as authority.
// - Allows:
//   - Inputs: finite turn bound, borrowed worker resources, caller-owned turn,
//     and supervisor observing progress plus request-only cancellation.
//   - Outputs: typed callback progress and the exact joined worker result.
//   - Side effects: finite in-memory channel sends and one joined host worker.
// - Split-When:
//   - Durable progress or independent background ownership becomes required.
// - Merge-When:
//   - A shared scheduler owns callback progress and joined work supervision.
// - Summary:
//   - Makes finite callback completions observable without blocking workers.
// - Description:
//   - A successful channel send reports only callback completion and its
//     decision class; callback values remain with the worker and caller.
// - Usage:
//   - A supervisor may receive notices or request cancellation at any time.
// - Defaults:
//   - Receiver abandonment does not stop or poison the finite worker.
//

//! Finite scoped cache-worker progress reports and cooperative supervision.

use std::num::NonZeroUsize;
use std::ops::ControlFlow;
use std::sync::mpsc::{self, Receiver};

use crate::{
    executable_cache_limits_retry_lifecycle as lifecycle,
    executable_cache_limits_scoped_worker as worker,
    execution_interruptible_wait as interruptible,
};

type RetryLifecycle = lifecycle::NativeExecutableCacheLimitsRetryLifecycle;
type Resources<'resource> = worker::NativeCacheScopedWorkerResources<'resource>;
type CancelHandle = interruptible::NativeContinuationSystemCancellationHandle;

/// Caller-owned callback outcome classification, not a guest result.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeCacheScopedTurnProgressKind {
    /// A completed callback asked to stop the finite run.
    CallerStopped,
    /// A completed callback requested another finite turn.
    Continued,
    /// A completed callback returned an exact error to the worker.
    Failed,
}

/// Non-authoritative evidence that one callback returned to the worker.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeCacheScopedTurnProgress {
    /// One-based number of returned callbacks in this finite invocation.
    pub completed: usize,
    /// Classification of the returned callback without its owned value.
    pub kind: NativeCacheScopedTurnProgressKind,
}

/// Runs one joined finite worker with nonblocking callback progress notices.
///
/// Each returned callback produces exactly one ordered notice while the
/// receiver exists. A dropped receiver never blocks the worker; a supervisor
/// observing disconnection cannot infer a successful run or a cursor state.
/// Progress is in-memory observation only, not durable completion authority.
/// The final joined result remains the sole typed terminal evidence.
///
/// Notices use an unbounded channel, with at most `maximum_turns` enqueued
/// entries, so callers must choose a suitably small finite resource budget.
/// An executing callback cannot be interrupted; cancellation is cooperative
/// at the next turn boundary. No background worker survives this call.
///
/// # Errors
///
/// Propagates exact scoped-worker spawn and panic errors. Typed turn and wait
/// errors remain inside the joined worker completion.
pub fn run_scoped_cache_retry_worker_with_progress<
    Reason,
    Turn,
    TurnError,
    Supervisor,
    SupervisorResult,
>(
    maximum_turns: NonZeroUsize,
    resources: Resources<'_>,
    mut turn: Turn,
    supervise: Supervisor,
) -> worker::NativeCacheScopedWorkerResult<Reason, TurnError, SupervisorResult>
where
    Reason: Send,
    Turn: FnMut(&mut RetryLifecycle) -> Result<ControlFlow<Reason>, TurnError>
        + Send,
    TurnError: Send,
    Supervisor: FnOnce(
        &CancelHandle,
        &Receiver<NativeCacheScopedTurnProgress>,
    ) -> SupervisorResult,
{
    let (sender, receiver) = mpsc::channel();
    let mut completed = 0usize;
    worker::run_scoped_cache_retry_worker(
        maximum_turns,
        resources,
        move |lifecycle| {
            let result = turn(lifecycle);
            completed = completed.saturating_add(1);
            let kind = match &result {
                Ok(ControlFlow::Break(_reason)) => {
                    NativeCacheScopedTurnProgressKind::CallerStopped
                },
                Ok(ControlFlow::Continue(())) => {
                    NativeCacheScopedTurnProgressKind::Continued
                },
                Err(_error) => NativeCacheScopedTurnProgressKind::Failed,
            };
            let _observation =
                sender.send(NativeCacheScopedTurnProgress { completed, kind });
            result
        },
        |cancel| supervise(cancel, &receiver),
    )
}

#[cfg(test)]
#[path = "../../../../../tests/tiered/cache_worker_progress.rs"]
mod tests;
