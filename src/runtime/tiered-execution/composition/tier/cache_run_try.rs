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
//   - Typed callback-failure adaptation for finite caller-owned retry turns.
// - Must-Not:
//   - Wait independently, mutate native policy, choose clocks, spawn work,
//     persist cursors, or erase already completed turn evidence.
// - Allows:
//   - Inputs: positive turn limit, borrowed runner context, and fallible turn.
//   - Outputs: typed terminal stop or exact wait/turn failure with progress.
//   - Side effects: only those delegated to the bounded retry runner.
// - Split-When:
//   - Dedicated product-native activation takes ownership of failure policy.
// - Merge-When:
//   - One product scheduler supersedes synchronous callback composition.
// - Summary:
//   - Preserves delegated turn failures and exact completed attempt counts.
// - Description:
//   - Returned callback errors are completed attempts; pre-turn wait failures
//     never claim the failed attempt as completed.
// - Usage:
//   - Call from a finite synchronous owner with explicit callback policy.
// - Defaults:
//   - No retry on a callback error; the first error ends this bounded run.
//

//! Fallible caller-owned turns under cooperative finite retry pacing.

use std::num::NonZeroUsize;
use std::ops::ControlFlow;

use crate::interruptible_wait::NativeContinuationInterruptibleWait;
use crate::{
    executable_cache_limits_retry_lifecycle as lifecycle,
    executable_cache_limits_retry_run as run,
};

type RetryLifecycle = lifecycle::NativeExecutableCacheLimitsRetryLifecycle;
type RunStop<Reason> =
    run::NativeExecutableCacheLimitsRetryLifecycleRunStop<Reason>;
type RunWaitFailure<Error> =
    run::NativeExecutableCacheLimitsRetryLifecycleRunWaitFailure<Error>;

/// Exact typed wait or callback failure in a finite lifecycle run.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeExecutableCacheLimitsRetryLifecycleRunFailure<
    WaitError,
    TurnError,
> {
    /// Returned callback error; completion includes the failed callback.
    Turn {
        /// Number of returned callbacks, including the failed callback.
        completed: usize,
        /// Exact caller-owned callback error.
        error: TurnError,
    },
    /// Pre-turn query/wait error; no new completed attempt is implied.
    Wait(RunWaitFailure<WaitError>),
}

/// Typed success or failure for a bounded fallible lifecycle run.
pub type NativeCacheLimitsFallibleRunResult<Reason, WaitError, TurnError> =
    Result<
        RunStop<Reason>,
        NativeExecutableCacheLimitsRetryLifecycleRunFailure<
            WaitError,
            TurnError,
        >,
    >;

/// Repeats caller-owned fallible work under bounded cooperative pacing.
///
/// `Ok(Continue)` requests another paced turn, `Ok(Break(reason))` stops with
/// typed caller evidence, and `Err(error)` stops with exact completed-attempt
/// count including the failed returned callback. This never retries a failed
/// activation automatically and never treats product stop reasons as shutdown.
///
/// # Errors
///
/// Returns an exact pre-turn wait/query error and completed count, or the
/// caller-owned turn error counting that returned invocation as completed.
pub fn run_bounded_interruptible_fallible_cache_limits_retry_lifecycle<
    Wait,
    Turn,
    Reason,
    TurnError,
>(
    maximum_turns: NonZeroUsize,
    context: &mut run::NativeExecutableCacheLimitsRetryLifecycleRunContext<
        '_,
        Wait,
    >,
    mut turn: Turn,
) -> NativeCacheLimitsFallibleRunResult<Reason, Wait::Error, TurnError>
where
    Wait: NativeContinuationInterruptibleWait,
    Turn: FnMut(&mut RetryLifecycle) -> Result<ControlFlow<Reason>, TurnError>,
{
    let result = run::run_bounded_interruptible_cache_limits_retry_lifecycle(
        maximum_turns,
        context,
        |lifecycle| match turn(lifecycle) {
            Ok(ControlFlow::Break(reason)) => ControlFlow::Break(Ok(reason)),
            Ok(ControlFlow::Continue(())) => ControlFlow::Continue(()),
            Err(error) => ControlFlow::Break(Err(error)),
        },
    )
    .map_err(NativeExecutableCacheLimitsRetryLifecycleRunFailure::Wait)?;
    match result {
        RunStop::CallerStopped {
            completed,
            reason: Ok(reason),
        } => Ok(RunStop::CallerStopped { completed, reason }),
        RunStop::CallerStopped {
            completed,
            reason: Err(error),
        } => Err(NativeExecutableCacheLimitsRetryLifecycleRunFailure::Turn {
            completed,
            error,
        }),
        RunStop::Cancelled { completed } => {
            Ok(RunStop::Cancelled { completed })
        },
        RunStop::CursorUnavailable { completed } => {
            Ok(RunStop::CursorUnavailable { completed })
        },
        RunStop::LimitReached { completed } => {
            Ok(RunStop::LimitReached { completed })
        },
    }
}

#[cfg(test)]
#[path = "../../../../../tests/tiered/cache_retry_run_fallible.rs"]
mod tests;
