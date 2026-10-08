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
//   - One owned, finite, cancelable, explicitly joined host retry worker.
// - Must-Not:
//   - Detach a worker on handle drop, invent durable cursor authority, retry
//     failed product activation, or preempt an executing callback.
// - Allows:
//   - Inputs: owned lifecycle/pacer, owned fallible turn, positive turn bound.
//   - Outputs: owned resources and typed finite terminal result after join, or
//     recovered launch inputs on worker startup failure.
//   - Side effects: one standard-library thread and cooperative wait/cancel.
// - Split-When:
//   - A product scheduler gains durable queues or timed task ownership.
// - Merge-When:
//   - A host scheduler owns the same join and shutdown invariants.
// - Summary:
//   - Keeps finite retry state affine across a joinable host worker handle.
// - Description:
//   - Dropping an unfinished handle cancels and blocks until its worker joins.
//   - Thread spawn never consumes input state until the worker has started.
// - Usage:
//   - Explicit join returns recoverable lifecycle state and typed outcome.
// - Defaults:
//   - No background ownership escapes the lifetime of the returned handle.
//

//! Owned joinable finite cache-retry host worker with cancellation-first drop.

use std::num::NonZeroUsize;
use std::ops::ControlFlow;
use std::panic::{AssertUnwindSafe, catch_unwind};
use std::sync::mpsc;
use std::{io, thread};

use fallible::run_bounded_interruptible_fallible_cache_limits_retry_lifecycle;

use crate::{
    executable_cache_limits_retry_lifecycle as lifecycle,
    executable_cache_limits_retry_pacing as pacing,
    executable_cache_limits_retry_run as run,
    executable_cache_limits_retry_run_fallible as fallible,
    execution_interruptible_wait as interruptible,
};

type RetryLifecycle = lifecycle::NativeExecutableCacheLimitsRetryLifecycle;
type Pacer = pacing::NativeExecutableCacheLimitsRetryLifecyclePacer;
type CancelHandle = interruptible::NativeContinuationSystemCancellationHandle;
type WaitError = interruptible::NativeContinuationSystemInterruptibleWaitError;
type RunResult<Reason, TurnError> =
    fallible::NativeCacheLimitsFallibleRunResult<Reason, WaitError, TurnError>;

/// Owned, affine inputs for one finite host worker.
#[derive(Debug)]
pub struct NativeCacheOwnedWorkerResources {
    /// Process-local cursor authority stays owned until a joined completion.
    pub lifecycle: RetryLifecycle,
    /// Process-local retry pacing stays owned until a joined completion.
    pub pacer: Pacer,
}

impl NativeCacheOwnedWorkerResources {
    /// Transfers exclusive lifecycle and pacing ownership to one worker.
    #[must_use]
    pub const fn new(lifecycle: RetryLifecycle, pacer: Pacer) -> Self {
        Self { lifecycle, pacer }
    }
}

/// A typed finite worker terminal outcome; panic never authorizes progress.
#[derive(Debug)]
pub enum NativeCacheOwnedWorkerTerminal<Reason, TurnError> {
    /// Exact return from the finite fallible lifecycle runner.
    Returned(RunResult<Reason, TurnError>),
    /// Callback or run panicked; recovered cursor authority is revoked.
    WorkerPanicked,
}

/// Owned post-join lifecycle and typed terminal evidence.
#[derive(Debug)]
pub struct NativeCacheOwnedWorkerCompletion<Reason, TurnError> {
    /// Explicitly recovered state, with cursor revoked after worker panic.
    pub resources: NativeCacheOwnedWorkerResources,
    /// Exact typed completion or fail-closed worker panic.
    pub terminal: NativeCacheOwnedWorkerTerminal<Reason, TurnError>,
}

/// Why an owned launch failed before transferring its owned inputs.
#[derive(Debug)]
pub enum NativeCacheOwnedWorkerLaunchCause {
    /// Thread exited before accepting the caller-owned inputs.
    Handshake,
    /// Host could not create the worker thread.
    Spawn(io::Error),
}

/// Owned inputs recovered when thread startup could not complete.
#[derive(Debug)]
pub struct NativeCacheOwnedWorkerStartFailure<Turn> {
    /// Exact failed launch phase, with original host error when available.
    pub cause: NativeCacheOwnedWorkerLaunchCause,
    /// Unchanged lifecycle/pacer state, never sent to the failed worker.
    pub resources: NativeCacheOwnedWorkerResources,
    /// Original caller-owned callback, still available for another attempt.
    pub turn: Turn,
}

/// Unexpected infrastructure failure outside the protected retry callback.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeCacheOwnedWorkerJoinFailure {
    /// Worker startup receiver was abandoned before ownership transfer.
    HandoffAbandoned,
    /// The host worker panicked outside protected retry execution.
    ThreadPanicked,
}

/// Exact owned post-join completion or host infrastructure failure.
pub type NativeCacheOwnedWorkerJoinResult<Reason, TurnError> = Result<
    NativeCacheOwnedWorkerCompletion<Reason, TurnError>,
    NativeCacheOwnedWorkerJoinFailure,
>;

/// Explicit stop-request evidence plus an independently joined worker result.
#[derive(Debug)]
pub struct NativeCacheOwnedWorkerShutdown<Reason, TurnError> {
    /// Exact first/repeated cancellation request or synchronization failure.
    pub cancellation: Result<bool, WaitError>,
    /// The independently joined terminal result and owned resources, if any.
    pub joined: NativeCacheOwnedWorkerJoinResult<Reason, TurnError>,
}

/// Exact host thread handle with a separately recoverable owned completion.
type OwnedThread<Reason, TurnError> =
    thread::JoinHandle<NativeCacheOwnedWorkerJoinResult<Reason, TurnError>>;

/// Owned worker launch or boxed failure with unchanged caller inputs.
pub type NativeCacheOwnedWorkerStartResult<Reason, Turn, TurnError> = Result<
    NativeCacheOwnedWorkerHandle<Reason, TurnError>,
    Box<NativeCacheOwnedWorkerStartFailure<Turn>>,
>;

/// One finite owned worker whose destructor cancels and joins before returning.
#[derive(Debug)]
pub struct NativeCacheOwnedWorkerHandle<Reason, TurnError> {
    cancellation: CancelHandle,
    thread: Option<OwnedThread<Reason, TurnError>>,
}

impl<Reason, TurnError> NativeCacheOwnedWorkerHandle<Reason, TurnError> {
    /// Requests sticky cooperative stop without claiming callback preemption.
    ///
    /// # Errors
    ///
    /// Returns exact cancellation mutex poison without inventing a stop.
    pub fn cancel(&self) -> Result<bool, WaitError> {
        self.cancellation.cancel()
    }

    /// Requests cooperative cancellation then joins and retains both outcomes.
    ///
    /// This blocks until an in-flight callback returns. Even a failed stop
    /// request still joins the worker; its terminal result is never fabricated
    /// from the request outcome. A returned `true` only proves the first stop
    /// request, not that the worker observed it before normal completion.
    #[must_use]
    pub fn cancel_and_join(
        self,
    ) -> NativeCacheOwnedWorkerShutdown<Reason, TurnError> {
        let cancellation = self.cancel();
        let joined = self.join();
        NativeCacheOwnedWorkerShutdown { cancellation, joined }
    }

    /// Checks host thread completion, not durable or typed terminal evidence.
    #[must_use]
    pub fn is_finished(&self) -> bool {
        self.thread
            .as_ref()
            .is_none_or(thread::JoinHandle::is_finished)
    }

    /// Joins naturally and returns all owned state plus exact terminal result.
    ///
    /// Unlike drop, explicit join does not request cancellation. This blocks
    /// until any executing callback returns and the finite run terminates.
    ///
    /// # Errors
    ///
    /// Returns an unexpected thread panic outside protected retry execution.
    pub fn join(
        mut self,
    ) -> NativeCacheOwnedWorkerJoinResult<Reason, TurnError> {
        let join = self
            .thread
            .take()
            .ok_or(NativeCacheOwnedWorkerJoinFailure::ThreadPanicked)?;
        join.join().map_err(|_panic| {
            NativeCacheOwnedWorkerJoinFailure::ThreadPanicked
        })?
    }
}

impl<Reason, TurnError> Drop
    for NativeCacheOwnedWorkerHandle<Reason, TurnError>
{
    fn drop(&mut self) {
        if let Some(join) = self.thread.take() {
            let _request = self.cancellation.cancel();
            let _joined = join.join();
        }
    }
}

/// Starts a finite worker without moving inputs until thread startup succeeds.
///
/// On a launch error, both lifecycle/pacer and callback are returned unchanged.
/// On success, the returned handle must be explicitly joined or dropped. Drop
/// cancels then joins synchronously, even if the callback has not finished.
/// No host timer can preempt a running callback; no durable queue exists here.
/// If the worker callback or its destructor panics, process-local cursor
/// authority is revoked before returning owned resources and `WorkerPanicked`.
///
/// # Errors
///
/// Returns a typed spawn or handoff failure with unconsumed inputs.
pub fn start_owned_cache_retry_worker<Reason, Turn, TurnError>(
    maximum_turns: NonZeroUsize,
    resources: NativeCacheOwnedWorkerResources,
    turn: Turn,
) -> NativeCacheOwnedWorkerStartResult<Reason, Turn, TurnError>
where
    Reason: Send + 'static,
    Turn: FnMut(&mut RetryLifecycle) -> Result<ControlFlow<Reason>, TurnError>
        + Send
        + 'static,
    TurnError: Send + 'static,
{
    let (mut wait, cancellation) =
        interruptible::NativeContinuationSystemInterruptibleWait::new_pair();
    let (sender, receiver) =
        mpsc::sync_channel::<(NativeCacheOwnedWorkerResources, Turn)>(0);
    let thread = match thread::Builder::new().spawn(move || {
        let Ok((mut worker_resources, mut worker_turn)) = receiver.recv()
        else {
            return Err(NativeCacheOwnedWorkerJoinFailure::HandoffAbandoned);
        };
        let run = catch_unwind(AssertUnwindSafe(|| {
            let mut context =
                run::NativeExecutableCacheLimitsRetryLifecycleRunContext::new(
                    &mut worker_resources.pacer,
                    &mut worker_resources.lifecycle,
                    &mut wait,
                );
            run_bounded_interruptible_fallible_cache_limits_retry_lifecycle(
                maximum_turns,
                &mut context,
                &mut worker_turn,
            )
        }));
        // Caller-owned callback destructors can panic even after a successful
        // run. Drop the callback under independent protection before returning
        // its lifecycle to the supervisor. If both the run and drop panic,
        // neither can overrule process-local cursor revocation.
        let dropped = catch_unwind(AssertUnwindSafe(|| drop(worker_turn)));
        let terminal = match (run, dropped) {
            (Ok(result), Ok(())) => {
                NativeCacheOwnedWorkerTerminal::Returned(result)
            },
            (_run, _drop_panic) => {
                worker_resources.lifecycle.replace_expected_cursor(None);
                NativeCacheOwnedWorkerTerminal::WorkerPanicked
            },
        };
        Ok(NativeCacheOwnedWorkerCompletion {
            resources: worker_resources,
            terminal,
        })
    }) {
        Ok(thread) => thread,
        Err(error) => {
            return Err(Box::new(NativeCacheOwnedWorkerStartFailure {
                cause: NativeCacheOwnedWorkerLaunchCause::Spawn(error),
                resources,
                turn,
            }));
        },
    };
    if let Err(send) = sender.send((resources, turn)) {
        let _joined = thread.join();
        let (failed_resources, failed_turn) = send.0;
        return Err(Box::new(NativeCacheOwnedWorkerStartFailure {
            cause: NativeCacheOwnedWorkerLaunchCause::Handshake,
            resources: failed_resources,
            turn: failed_turn,
        }));
    }
    Ok(NativeCacheOwnedWorkerHandle {
        cancellation,
        thread: Some(thread),
    })
}

#[cfg(test)]
#[path = "../../../../../tests/tiered/cache_owned_worker.rs"]
mod tests;
