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
//   - Nonblocking capacity-limited callback progress for finite joined workers.
// - Must-Not:
//   - Block worker callbacks on consumers, detach threads, lose callback
//     results, treat progress as cursor authority, or persist observations.
// - Allows:
//   - Inputs: positive buffer capacity and turn limit, borrowed lifecycle and
//     pacer, fallible turn, and caller-owned progress supervisor.
//   - Outputs: exact worker result and aggregate transport admission/drop
//     counters, independent from the supervisor's observation.
//   - Side effects: bounded process-local notices and one joined host thread.
// - Split-When:
//   - Durable or externally managed worker progress becomes authoritative.
// - Merge-When:
//   - One product-owned scheduler subsumes bounded callback observation.
// - Summary:
//   - Bounds queued progress and reports exact nonblocking delivery outcomes.
// - Description:
//   - A full or abandoned receiver drops only the advisory notice, never the
//     turn result. A joined worker remains sole terminal execution evidence.
// - Usage:
//   - A caller must choose a positive capacity matching its memory budget.
// - Defaults:
//   - A channel drop never implicitly cancels guest-independent work.
//

//! Nonblocking bounded advisory progress for a joined cache retry worker.

use std::num::NonZeroUsize;
use std::ops::ControlFlow;
use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::mpsc::{self, Receiver, TrySendError};

use crate::{
    executable_cache_limits_retry_lifecycle as lifecycle,
    executable_cache_limits_scoped_worker as worker,
    executable_cache_limits_scoped_worker_progress as progress,
    execution_interruptible_wait as interruptible,
};

type RetryLifecycle = lifecycle::NativeExecutableCacheLimitsRetryLifecycle;
type Resources<'resource> = worker::NativeCacheScopedWorkerResources<'resource>;
type CancelHandle = interruptible::NativeContinuationSystemCancellationHandle;
type Notice = progress::NativeCacheScopedTurnProgress;
type Kind = progress::NativeCacheScopedTurnProgressKind;

/// Exact advisory notification transport outcomes after the worker joins.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct NativeCacheScopedBoundedProgressTotals {
    /// Successfully enqueued notices (not necessarily read by the consumer).
    pub enqueued: usize,
    /// Notices omitted because the finite queue was at its capacity.
    pub full: usize,
    /// Notices omitted because the receiver had already been abandoned.
    pub receiver_gone: usize,
}

/// Positive queue and turn resource bounds for a scoped progress run.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeCacheScopedBoundedProgressLimits {
    /// Maximum notices retained in memory before older gaps become possible.
    pub capacity: NonZeroUsize,
    /// Maximum caller-owned callback attempts for this scoped run.
    pub maximum_turns: NonZeroUsize,
}

impl NativeCacheScopedBoundedProgressLimits {
    /// Bundles explicit nonzero observation and execution limits.
    #[must_use]
    pub const fn new(
        capacity: NonZeroUsize,
        maximum_turns: NonZeroUsize,
    ) -> Self {
        Self { capacity, maximum_turns }
    }
}

/// Independently retained run/supervisor result and progress admission counts.
#[derive(Debug)]
pub struct NativeCacheScopedBoundedProgressCompletion<
    Reason,
    TurnError,
    SupervisorResult,
> {
    /// Non-authoritative transport totals, never cursor or completion rights.
    pub totals: NativeCacheScopedBoundedProgressTotals,
    /// Exact joined worker outcome plus supervisor's independent result.
    pub worker: worker::NativeCacheScopedWorkerCompletion<
        Reason,
        TurnError,
        SupervisorResult,
    >,
}

/// Exact outer worker infrastructure result for the bounded observation path.
pub type NativeCacheScopedBoundedProgressResult<
    Reason,
    TurnError,
    SupervisorResult,
> = Result<
    NativeCacheScopedBoundedProgressCompletion<
        Reason,
        TurnError,
        SupervisorResult,
    >,
    worker::NativeCacheScopedWorkerError,
>;

#[derive(Debug, Default)]
struct ProgressCounters {
    enqueued: AtomicUsize,
    full: AtomicUsize,
    receiver_gone: AtomicUsize,
}

impl ProgressCounters {
    fn snapshot(&self) -> NativeCacheScopedBoundedProgressTotals {
        // Scope join synchronizes all callback writes before this read.
        NativeCacheScopedBoundedProgressTotals {
            enqueued: self.enqueued.load(Ordering::Relaxed),
            full: self.full.load(Ordering::Relaxed),
            receiver_gone: self.receiver_gone.load(Ordering::Relaxed),
        }
    }
}

/// Joins a finite worker with a nonblocking, capacity-bounded progress queue.
///
/// Exactly one notice is attempted for each callback that *returns*. Only
/// enqueue admission is claimed: a successful send does not prove consumption.
/// A full queue or abandoned receiver drops the notice and increments a
/// distinct exact counter; it never blocks, retries, or cancels a callback.
/// The supervisor owns the receiver and may explicitly drop it mid-run.
/// At most `capacity` notices can be queued at a time, independent of turn
/// count. A receiver can observe gaps in one-based callback indices and must
/// not infer terminal success from stream closure. Only `worker.run` is
/// terminal.
///
/// The returned totals count `enqueued + full + receiver_gone` attempts; this
/// equals the number of returned callbacks when the worker has a typed result.
/// Panic retains the scoped worker's existing fail-closed cursor revocation
/// and is returned without fabricated final progress totals.
///
/// # Errors
///
/// Propagates exact spawn/panic failure; typed callback/wait errors are
/// retained independently inside the joined worker result.
pub fn run_scoped_cache_retry_worker_bounded_progress<
    Reason,
    Turn,
    TurnError,
    Supervisor,
    SupervisorResult,
>(
    limits: NativeCacheScopedBoundedProgressLimits,
    resources: Resources<'_>,
    mut turn: Turn,
    supervise: Supervisor,
) -> NativeCacheScopedBoundedProgressResult<Reason, TurnError, SupervisorResult>
where
    Reason: Send,
    Turn: FnMut(&mut RetryLifecycle) -> Result<ControlFlow<Reason>, TurnError>
        + Send,
    TurnError: Send,
    Supervisor: FnOnce(&CancelHandle, Receiver<Notice>) -> SupervisorResult,
{
    let (sender, receiver) = mpsc::sync_channel(limits.capacity.get());
    let counters = Arc::new(ProgressCounters::default());
    let worker_counters = Arc::clone(&counters);
    let mut completed = 0usize;
    let result = worker::run_scoped_cache_retry_worker(
        limits.maximum_turns,
        resources,
        move |lifecycle| {
            let result = turn(lifecycle);
            completed = completed.saturating_add(1);
            let kind = match &result {
                Ok(ControlFlow::Break(_)) => Kind::CallerStopped,
                Ok(ControlFlow::Continue(())) => Kind::Continued,
                Err(_) => Kind::Failed,
            };
            let notice = Notice { completed, kind };
            match sender.try_send(notice) {
                Ok(()) => {
                    let _previous = worker_counters
                        .enqueued
                        .fetch_add(1, Ordering::Relaxed);
                },
                Err(TrySendError::Full(_)) => {
                    let _previous =
                        worker_counters.full.fetch_add(1, Ordering::Relaxed);
                },
                Err(TrySendError::Disconnected(_)) => {
                    let _previous = worker_counters
                        .receiver_gone
                        .fetch_add(1, Ordering::Relaxed);
                },
            }
            result
        },
        move |cancel| supervise(cancel, receiver),
    )?;
    Ok(NativeCacheScopedBoundedProgressCompletion {
        totals: counters.snapshot(),
        worker: result,
    })
}

#[cfg(test)]
#[path = "../../../../../tests/tiered/cache_progress_bounded.rs"]
mod tests;
