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
//   - One explicitly scoped host worker that executes finite cache-trigger
//     retry lifecycle turns under caller-owned cooperative cancellation.
// - Must-Not:
//   - Detach work, persist affine lifecycle ownership, invent native policy,
//     preempt executing callbacks, or start unattended scheduling.
// - Allows:
//   - Inputs: positive turn limit, borrowed lifecycle/pacer, owned callback,
//     and one supervisor callback with a request-only cancellation handle.
//   - Outputs: exact worker run result and supervisor result, or typed spawn/
//     worker-panic failure.
//   - Side effects: one scoped standard-library host thread and delegated
//     waits.
// - Split-When:
//   - Product-managed background worker pools gain explicit durable ownership.
// - Merge-When:
//   - One product scheduler subsumes joined finite execution.
// - Summary:
//   - Joins a cancellable finite host worker before returning to the caller.
// - Description:
//   - The supervisor runs concurrently with the bounded worker, and may request
//     sticky stop. Neither side can leak a detached worker from this function.
// - Usage:
//   - The supervisor must eventually return so the worker can be joined.
// - Defaults:
//   - A fresh cancellation scope starts uncancelled for every invocation.
//

//! Scoped host-thread execution of finite cache-trigger lifecycle runs.

use std::num::NonZeroUsize;
use std::ops::ControlFlow;
use std::panic::{AssertUnwindSafe, catch_unwind, resume_unwind};
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

/// Worker-run completion and supervisor's caller-owned result.
#[derive(Debug)]
pub struct NativeCacheScopedWorkerCompletion<
    Reason,
    TurnError,
    SupervisorResult,
> {
    /// Exact finite worker result, including typed wait/turn failures.
    pub run: fallible::NativeCacheLimitsFallibleRunResult<
        Reason,
        WaitError,
        TurnError,
    >,
    /// Exact result returned by the concurrently executing supervisor.
    pub supervisor: SupervisorResult,
}

/// Failure to start or join an explicitly scoped worker thread.
#[derive(Debug)]
pub enum NativeCacheScopedWorkerError {
    /// Host refused to start the worker; borrowed lifecycle remains local.
    Spawn(io::Error),
    /// The worker panicked; no terminal result may be fabricated.
    WorkerPanicked,
}

/// Borrowed lifecycle and pacer for one scoped finite worker.
#[derive(Debug)]
pub struct NativeCacheScopedWorkerResources<'resource> {
    /// Process-local retained retry cursor and policy.
    pub lifecycle: &'resource mut RetryLifecycle,
    /// Process-local finite-loop pacing state.
    pub pacer: &'resource mut Pacer,
}

impl<'resource> NativeCacheScopedWorkerResources<'resource> {
    /// Binds exclusive process-local ownership to one worker scope.
    #[must_use]
    pub const fn new(
        lifecycle: &'resource mut RetryLifecycle,
        pacer: &'resource mut Pacer,
    ) -> Self {
        Self { lifecycle, pacer }
    }
}

/// Exact result or infrastructure failure for one scoped worker.
pub type NativeCacheScopedWorkerResult<Reason, TurnError, SupervisorResult> =
    Result<
        NativeCacheScopedWorkerCompletion<Reason, TurnError, SupervisorResult>,
        NativeCacheScopedWorkerError,
    >;

/// Returned supervisor error plus exact cancellation-request evidence.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeCacheScopedSupervisorFailure<Error> {
    /// `true` for the first stop request, `false` if already cancelled.
    /// A failed request retains its exact synchronization error.
    pub cancellation: Result<bool, WaitError>,
    /// The unchanged error reported by the caller-owned supervisor.
    pub error: Error,
}

/// Outcome of a scoped run with an explicitly fallible supervisor.
pub type NativeCacheScopedFallibleSupervisorResult<
    Reason,
    TurnError,
    SupervisorResult,
    SupervisorError,
> = NativeCacheScopedWorkerResult<
    Reason,
    TurnError,
    Result<
        SupervisorResult,
        NativeCacheScopedSupervisorFailure<SupervisorError>,
    >,
>;

/// Supervises one finite worker, requesting stop when supervision fails.
///
/// `Ok` leaves cancellation to the caller; `Err` requests sticky cooperative
/// stop before the worker is joined and retains both the supervisor error and
/// the exact request outcome. The worker can finish an already-running callback
/// before stopping. The returned worker outcome remains independent, including
/// a possible completed turn or worker error during the cancellation race.
///
/// The ordinary `run_scoped_cache_retry_worker` keeps its original semantics:
/// generic supervisor return values never implicitly request cancellation.
///
/// # Errors
///
/// Preserves the existing typed worker spawn/panic errors. Supervisor errors
/// live in the completion, alongside cancellation-request evidence.
pub fn run_scoped_cache_retry_worker_fallible_supervisor<
    Reason,
    Turn,
    TurnError,
    Supervisor,
    SupervisorResult,
    SupervisorError,
>(
    maximum_turns: NonZeroUsize,
    resources: NativeCacheScopedWorkerResources<'_>,
    turn: Turn,
    supervise: Supervisor,
) -> NativeCacheScopedFallibleSupervisorResult<
    Reason,
    TurnError,
    SupervisorResult,
    SupervisorError,
>
where
    Reason: Send,
    Turn: FnMut(&mut RetryLifecycle) -> Result<ControlFlow<Reason>, TurnError>
        + Send,
    TurnError: Send,
    Supervisor:
        FnOnce(&CancelHandle) -> Result<SupervisorResult, SupervisorError>,
{
    run_scoped_cache_retry_worker(maximum_turns, resources, turn, |cancel| {
        supervise(cancel).map_err(|error| NativeCacheScopedSupervisorFailure {
            cancellation: cancel.cancel(),
            error,
        })
    })
}

/// Starts exactly one scoped worker and joins it before returning.
///
/// The worker borrows the retry lifecycle and pacer, uses a fresh standard
/// interruptible wait, and executes at most `maximum_turns` callback attempts.
/// The supervisor receives only a cancellation request handle; it cannot
/// access mutable lifecycle state. The worker is *always joined* in the scope,
/// including when the supervisor returns before the worker finishes.
///
/// Cancellation is a cooperative pre-turn boundary, not an interruption of
/// native code, an atomic callback-start handshake, or a hard time deadline.
/// A panicking supervisor requests cancellation, joins the worker, then
/// resumes the original panic. A panicking worker is returned as an error;
/// its process-local cursor authority is cleared before returning.
/// If both panic, the supervisor's original panic takes precedence after join.
/// Both worker and supervisor panic clear cursor authority before reusing
/// state. Synchronization poison when requesting cancellation cannot mask that
/// panic.
///
/// # Errors
///
/// Returns exact spawn failure or typed worker panic; neither is converted
/// into a fabricated run result or a completed-turn count.
pub fn run_scoped_cache_retry_worker<
    Reason,
    Turn,
    TurnError,
    Supervisor,
    SupervisorResult,
>(
    maximum_turns: NonZeroUsize,
    resources: NativeCacheScopedWorkerResources<'_>,
    turn: Turn,
    supervise: Supervisor,
) -> NativeCacheScopedWorkerResult<Reason, TurnError, SupervisorResult>
where
    Reason: Send,
    Turn: FnMut(&mut RetryLifecycle) -> Result<ControlFlow<Reason>, TurnError>
        + Send,
    TurnError: Send,
    Supervisor: FnOnce(&CancelHandle) -> SupervisorResult,
{
    let NativeCacheScopedWorkerResources { lifecycle, pacer } = resources;
    let result = catch_unwind(AssertUnwindSafe(|| {
        run_scoped_cache_retry_worker_inner(
            maximum_turns,
            NativeCacheScopedWorkerResources::new(&mut *lifecycle, &mut *pacer),
            turn,
            supervise,
        )
    }));
    match result {
        Ok(Err(NativeCacheScopedWorkerError::WorkerPanicked)) => {
            lifecycle.replace_expected_cursor(None);
            Err(NativeCacheScopedWorkerError::WorkerPanicked)
        },
        Ok(completion) => completion,
        Err(payload) => {
            lifecycle.replace_expected_cursor(None);
            resume_unwind(payload)
        },
    }
}

fn run_scoped_cache_retry_worker_inner<
    Reason,
    Turn,
    TurnError,
    Supervisor,
    SupervisorResult,
>(
    maximum_turns: NonZeroUsize,
    resources: NativeCacheScopedWorkerResources<'_>,
    mut turn: Turn,
    supervise: Supervisor,
) -> NativeCacheScopedWorkerResult<Reason, TurnError, SupervisorResult>
where
    Reason: Send,
    Turn: FnMut(&mut RetryLifecycle) -> Result<ControlFlow<Reason>, TurnError>
        + Send,
    TurnError: Send,
    Supervisor: FnOnce(&CancelHandle) -> SupervisorResult,
{
    let (mut wait, cancel) =
        interruptible::NativeContinuationSystemInterruptibleWait::new_pair();
    thread::scope(|scope| {
        let worker = thread::Builder::new()
            .spawn_scoped(scope, move || {
                let mut context = run::
                    NativeExecutableCacheLimitsRetryLifecycleRunContext::new(
                    resources.pacer, resources.lifecycle, &mut wait,
                );
                run_bounded_interruptible_fallible_cache_limits_retry_lifecycle(
                    maximum_turns,
                    &mut context,
                    &mut turn,
                )
            })
            .map_err(NativeCacheScopedWorkerError::Spawn)?;
        let supervised = catch_unwind(AssertUnwindSafe(|| supervise(&cancel)));
        if supervised.is_err() {
            let _request = cancel.cancel();
        }
        let joined = worker.join();
        let supervisor = match supervised {
            Ok(value) => value,
            Err(payload) => resume_unwind(payload),
        };
        let run = joined
            .map_err(|_panic| NativeCacheScopedWorkerError::WorkerPanicked)?;
        Ok(NativeCacheScopedWorkerCompletion { run, supervisor })
    })
}

#[cfg(test)]
#[path = "../../../../../tests/tiered/cache_scoped_worker.rs"]
mod tests;
