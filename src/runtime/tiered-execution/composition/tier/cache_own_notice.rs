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
//   - Joinable owned finite retry worker with bounded advisory progress.
// - Must-Not:
//   - Detach workers, block on progress delivery, turn observations into cursor
//     authority, or replace typed completion with queue counters.
// - Allows:
//   - Inputs: positive queue/turn bounds, owned retry resources and callback.
//   - Outputs: owned cancelable handle, optional receiver, and exact joined
//     worker outcome with separate progress transport totals.
//   - Side effects: bounded in-memory channel and one joined host thread.
// - Split-When:
//   - Durable work/observation identities become scheduler responsibilities.
// - Merge-When:
//   - A common host task owner admits progress as an optional observation.
// - Summary:
//   - Composes owned finite workers with nonblocking bounded observations.
// - Description:
//   - The original callback is retained within a typed launch failure's wrapped
//     callback; no dropped notice changes execution or cancellation.
// - Usage:
//   - Poll or take the progress receiver, then join or cancel-and-join.
// - Defaults:
//   - Dropping an unfinished owner cancels and joins the underlying worker.
//

//! Owned finite worker with independently bounded advisory callback progress.

use std::ops::ControlFlow;
use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::mpsc::{self, Receiver, SyncSender, TrySendError};

use crate::{
    executable_cache_limits_owned_worker as owned,
    executable_cache_limits_retry_lifecycle as lifecycle,
    executable_cache_limits_scoped_worker_bounded_progress as bounded,
    executable_cache_limits_scoped_worker_progress as progress,
    execution_interruptible_wait as interruptible,
};

type RetryLifecycle = lifecycle::NativeExecutableCacheLimitsRetryLifecycle;
type Notice = progress::NativeCacheScopedTurnProgress;
type Kind = progress::NativeCacheScopedTurnProgressKind;
type Totals = bounded::NativeCacheScopedBoundedProgressTotals;
type Limits = bounded::NativeCacheScopedBoundedProgressLimits;
type WaitError = interruptible::NativeContinuationSystemInterruptibleWaitError;

/// Type-erased owned callback keeps the original turn on launch failure.
type ObservedTurn<Reason, TurnError> = Box<
    dyn FnMut(&mut RetryLifecycle) -> Result<ControlFlow<Reason>, TurnError>
        + Send,
>;

/// Start result preserving all original inputs in the boxed observer callback.
pub type NativeCacheOwnedProgressStartResult<Reason, TurnError> = Result<
    NativeCacheOwnedProgressHandle<Reason, TurnError>,
    Box<
        owned::NativeCacheOwnedWorkerStartFailure<
            ObservedTurn<Reason, TurnError>,
        >,
    >,
>;

#[derive(Debug, Default)]
struct Counters {
    enqueued: AtomicUsize,
    full: AtomicUsize,
    receiver_gone: AtomicUsize,
}

impl Counters {
    fn snapshot(&self) -> Totals {
        // A joined thread has finished all atomic counter increments.
        Totals {
            enqueued: self.enqueued.load(Ordering::Relaxed),
            full: self.full.load(Ordering::Relaxed),
            receiver_gone: self.receiver_gone.load(Ordering::Relaxed),
        }
    }
}

/// Exact post-join owned result plus bounded advisory transport evidence.
#[derive(Debug)]
pub struct NativeCacheOwnedProgressCompletion<Reason, TurnError> {
    /// Independent typed joined worker result and recovered owned resources.
    pub joined: owned::NativeCacheOwnedWorkerJoinResult<Reason, TurnError>,
    /// Accepted/full/disconnected notices, not proof of consumer observation.
    pub totals: Totals,
}

/// Exact cancel-and-join result plus bounded transport evidence.
#[derive(Debug)]
pub struct NativeCacheOwnedProgressShutdown<Reason, TurnError> {
    /// Worker stop request and joined terminal outcome remain independent.
    pub shutdown: owned::NativeCacheOwnedWorkerShutdown<Reason, TurnError>,
    /// Complete attempted progress admission, after the host worker joins.
    pub totals: Totals,
}

/// Explicitly owned finite progress worker; dropping it still joins.
#[derive(Debug)]
pub struct NativeCacheOwnedProgressHandle<Reason, TurnError> {
    counters: Arc<Counters>,
    receiver: Option<Receiver<Notice>>,
    worker: owned::NativeCacheOwnedWorkerHandle<Reason, TurnError>,
}

impl<Reason, TurnError> NativeCacheOwnedProgressHandle<Reason, TurnError> {
    /// Requests sticky stop without asserting guest callback preemption.
    ///
    /// # Errors
    ///
    /// Retains exact cancellation synchronization failures.
    pub fn cancel(&self) -> Result<bool, WaitError> {
        self.worker.cancel()
    }

    /// Requests cooperative stop then joins and retains both typed results.
    #[must_use]
    pub fn cancel_and_join(
        self,
    ) -> NativeCacheOwnedProgressShutdown<Reason, TurnError> {
        let Self {
            counters,
            receiver: _receiver,
            worker,
        } = self;
        let shutdown = worker.cancel_and_join();
        NativeCacheOwnedProgressShutdown {
            shutdown,
            totals: counters.snapshot(),
        }
    }

    /// Host thread completion is not yet typed/durable success.
    #[must_use]
    pub fn is_finished(&self) -> bool {
        self.worker.is_finished()
    }

    /// Explicit natural join; never requests cancellation implicitly.
    #[must_use]
    pub fn join(self) -> NativeCacheOwnedProgressCompletion<Reason, TurnError> {
        let Self {
            counters,
            receiver: _receiver,
            worker,
        } = self;
        let joined = worker.join();
        NativeCacheOwnedProgressCompletion {
            joined,
            totals: counters.snapshot(),
        }
    }

    /// Borrows an advisory receiver without taking its ownership.
    #[must_use]
    pub const fn progress(&self) -> Option<&Receiver<Notice>> {
        self.receiver.as_ref()
    }

    /// Transfers receiver ownership to the caller, including ability to drop.
    #[must_use]
    pub const fn take_progress_receiver(&mut self) -> Option<Receiver<Notice>> {
        self.receiver.take()
    }
}

/// Starts a joinable owned worker with a positive-capacity progress stream.
///
/// This adapter adds a callback wrapper; on thread startup failure, the
/// returned boxed callback still owns the original callback and can be
/// resubmitted to the base owned worker without discarding it. The receiver
/// is caller-owned and can be taken/dropped while the worker runs.
///
/// Progress is emitted after a callback returns, never before. An unobserved,
/// full or abandoned queue drops the notice without blocking work, and join
/// reports exact transport outcomes separately from owned lifecycle authority.
/// Callback/wrapper destructor panic remains protected by the base worker.
///
/// # Errors
///
/// Returns exact owned launch failure with recoverable resources and the
/// wrapped callback, with no detached host thread.
pub fn start_owned_cache_retry_worker_with_bounded_progress<
    Reason,
    Turn,
    TurnError,
>(
    limits: Limits,
    resources: owned::NativeCacheOwnedWorkerResources,
    mut turn: Turn,
) -> NativeCacheOwnedProgressStartResult<Reason, TurnError>
where
    Reason: Send + 'static,
    Turn: FnMut(&mut RetryLifecycle) -> Result<ControlFlow<Reason>, TurnError>
        + Send
        + 'static,
    TurnError: Send + 'static,
{
    let (sender, receiver) = mpsc::sync_channel(limits.capacity.get());
    let counters = Arc::new(Counters::default());
    let worker_counters = Arc::clone(&counters);
    let mut completed = 0usize;
    let observed_turn: ObservedTurn<Reason, TurnError> =
        Box::new(move |lifecycle: &mut RetryLifecycle| {
            let result = turn(lifecycle);
            completed = completed.saturating_add(1);
            let kind = match &result {
                Ok(ControlFlow::Break(_)) => Kind::CallerStopped,
                Ok(ControlFlow::Continue(())) => Kind::Continued,
                Err(_) => Kind::Failed,
            };
            try_emit(&sender, &worker_counters, Notice { completed, kind });
            result
        });
    let worker = owned::start_owned_cache_retry_worker(
        limits.maximum_turns,
        resources,
        observed_turn,
    )?;
    Ok(NativeCacheOwnedProgressHandle {
        counters,
        receiver: Some(receiver),
        worker,
    })
}

fn try_emit(sender: &SyncSender<Notice>, counters: &Counters, notice: Notice) {
    match sender.try_send(notice) {
        Ok(()) => {
            let _previous = counters.enqueued.fetch_add(1, Ordering::Relaxed);
        },
        Err(TrySendError::Full(_)) => {
            let _previous = counters.full.fetch_add(1, Ordering::Relaxed);
        },
        Err(TrySendError::Disconnected(_)) => {
            let _previous =
                counters.receiver_gone.fetch_add(1, Ordering::Relaxed);
        },
    }
}

#[cfg(test)]
#[path = "../../../../../tests/tiered/cache_owned_progress.rs"]
mod tests;
