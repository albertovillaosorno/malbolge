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
//   - Bounded synchronous repetition of caller-owned cache-trigger turns with
//     cooperative relative-wait cancellation.
// - Must-Not:
//   - Own durable cursor storage, choose cache policy, spawn work, read clocks,
//     or interpret guest instructions.
// - Allows:
//   - Inputs: positive turn limit, retained lifecycle owner, pacing state,
//     interruptible wait, and one caller-owned turn callback.
//   - Outputs: typed terminal stop or wait-failure evidence with completed turn
//     counts.
//   - Side effects: only bounded caller-owned turns and delegated relative
//     waits.
// - Split-When:
//   - Background workers, mid-turn preemption, or async cancellation becomes
//     separately owned.
// - Merge-When:
//   - One product scheduler owns repeat invocation and worker lifecycle.
// - Summary:
//   - Runs a caller-driven finite lifecycle loop without spawning workers.
// - Description:
//   - Every returned callback counts as one completed turn, including a caller
//     break; failed pre-turn waits preserve earlier completed progress.
// - Usage:
//   - The caller invokes and owns the entire synchronous bounded run.
// - Defaults:
//   - An explicit positive turn limit is mandatory.
//

//! Bounded synchronous repetition of cooperative cache-trigger lifecycle turns.

use std::num::NonZeroUsize;
use std::ops::ControlFlow;

use crate::executable_cache_limits_retry_lifecycle as lifecycle;
use crate::executable_cache_limits_retry_pacing::{
    NativeExecutableCacheLimitsRetryLifecyclePacer as Pacer,
    NativeExecutableCacheLimitsRetryLifecycleTurn as TurnOutcome,
    execute_interruptible_paced_cache_limits_retry_lifecycle_turn as run_turn,
};
use crate::interruptible_wait::NativeContinuationInterruptibleWait;

type RetryLifecycle = lifecycle::NativeExecutableCacheLimitsRetryLifecycle;

/// Terminal evidence for one finite caller-owned lifecycle run.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeExecutableCacheLimitsRetryLifecycleRunStop<Reason> {
    /// One caller-owned turn returned its explicit stop reason.
    CallerStopped {
        /// Number of completed turns including the stopping turn.
        completed: usize,
        /// Exact caller-owned stop evidence.
        reason: Reason,
    },
    /// Cooperative cancellation withheld the next turn.
    Cancelled {
        /// Number of completed turns before cancellation.
        completed: usize,
    },
    /// Cursor authority was missing before the next turn.
    CursorUnavailable {
        /// Number of completed turns before cursor loss.
        completed: usize,
    },
    /// The explicit positive turn limit was reached.
    LimitReached {
        /// Exact completed-turn count equal to the requested limit.
        completed: usize,
    },
}

/// Exact delegated wait error and progress before the failed attempt.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeExecutableCacheLimitsRetryLifecycleRunWaitFailure<Error> {
    /// Completed caller-owned turns before the failed wait/query.
    pub completed: usize,
    /// Exact underlying cancellation query or relative-wait error.
    pub error: Error,
}

/// Exact result of one bounded interruptible run.
pub type NativeExecutableCacheLimitsRunResult<Reason, WaitError> = Result<
    NativeExecutableCacheLimitsRetryLifecycleRunStop<Reason>,
    NativeExecutableCacheLimitsRetryLifecycleRunWaitFailure<WaitError>,
>;

type RunStop<Reason> = NativeExecutableCacheLimitsRetryLifecycleRunStop<Reason>;

/// Borrowed resources for one caller-owned finite lifecycle run.
#[derive(Debug)]
pub struct NativeExecutableCacheLimitsRetryLifecycleRunContext<'resource, Wait>
{
    lifecycle: &'resource mut RetryLifecycle,
    pacer: &'resource mut Pacer,
    wait: &'resource mut Wait,
}

impl<'resource, Wait>
    NativeExecutableCacheLimitsRetryLifecycleRunContext<'resource, Wait>
{
    /// Binds one process-local lifecycle, pacer, and interruptible wait.
    #[must_use]
    pub const fn new(
        pacer: &'resource mut Pacer,
        lifecycle: &'resource mut RetryLifecycle,
        wait: &'resource mut Wait,
    ) -> Self {
        Self { lifecycle, pacer, wait }
    }
}

/// Runs at most one positive bounded set of caller-owned lifecycle turns.
///
/// The callback chooses whether to continue or stop; neither its decision nor
/// retry-stop evidence changes native policy. No thread, timer, or background
/// work is created. Waiting, cancellation and cursor loss are checked before
/// each turn, and every returned callback is counted exactly once.
///
/// # Errors
///
/// Returns the exact delegated cancellation or wait error with the count of
/// earlier completed turns, without counting the failed attempt as a turn.
pub fn run_bounded_interruptible_cache_limits_retry_lifecycle<
    Wait,
    Turn,
    Reason,
>(
    maximum_turns: NonZeroUsize,
    context: &mut NativeExecutableCacheLimitsRetryLifecycleRunContext<'_, Wait>,
    mut turn: Turn,
) -> NativeExecutableCacheLimitsRunResult<Reason, Wait::Error>
where
    Wait: NativeContinuationInterruptibleWait,
    Turn: FnMut(&mut RetryLifecycle) -> ControlFlow<Reason>,
{
    let mut completed = 0usize;
    for _ in 0..maximum_turns.get() {
        let result =
            run_turn(context.pacer, context.lifecycle, context.wait, &mut turn)
                .map_err(|error| {
                    NativeExecutableCacheLimitsRetryLifecycleRunWaitFailure {
                        completed,
                        error,
                    }
                })?;
        match result {
            TurnOutcome::Cancelled => {
                return Ok(RunStop::Cancelled { completed });
            },
            TurnOutcome::CursorUnavailable => {
                return Ok(RunStop::CursorUnavailable { completed });
            },
            TurnOutcome::Executed {
                outcome: ControlFlow::Break(reason),
                ..
            } => {
                completed = completed.saturating_add(1);
                return Ok(RunStop::CallerStopped { completed, reason });
            },
            TurnOutcome::Executed {
                outcome: ControlFlow::Continue(()),
                ..
            } => {
                completed = completed.saturating_add(1);
            },
        }
    }
    Ok(RunStop::LimitReached { completed })
}

#[cfg(test)]
#[path = "../../../../../tests/tiered/cache_retry_run.rs"]
mod tests;
