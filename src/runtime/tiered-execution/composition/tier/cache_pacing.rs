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
//   - Process-local wait selection before explicit repeated cache-trigger
//     lifecycle turns.
// - Must-Not:
//   - Execute activation, choose retry policy, read clocks, persist state,
//     spawn workers, or treat retained conflict-stop evidence as shutdown.
// - Allows:
//   - Inputs: retained lifecycle cursor authority, one positive repeat delay,
//     explicit completed-turn observation, and a relative-wait dependency.
//   - Outputs: cursor-unavailable or ready evidence retaining whether waiting
//     occurred.
//   - Side effects: at most one delegated relative wait before a repeated turn.
// - Split-When:
//   - Cancellation, background workers, or asynchronous wake ownership gains
//     independent lifecycle semantics.
// - Merge-When:
//   - One product scheduler owns pacing and complete lifecycle turn execution.
// - Summary:
//   - Runs the first authorized turn immediately and paces later turns.
// - Description:
//   - Cursor loss fails closed before waiting; a failed wait grants no ready
//     evidence and may be retried by the caller.
// - Usage:
//   - Observe completion only after the caller finishes one explicit turn.
// - Defaults:
//   - Newly created pacing owners permit the first authorized turn immediately.
//

//! Process-local pacing for explicit repeated cache-trigger lifecycle turns.

use std::num::NonZeroU64;

use crate::executable_cache_limits_retry_lifecycle as lifecycle;
use crate::relative_wait::NativeContinuationRelativeWait;

type RetryLifecycle = lifecycle::NativeExecutableCacheLimitsRetryLifecycle;

/// Result of one paced caller-owned lifecycle turn.
pub type NativeExecutableCacheLimitsRetryLifecycleTurnResult<
    Outcome,
    WaitError,
> = Result<NativeExecutableCacheLimitsRetryLifecycleTurn<Outcome>, WaitError>;

/// Readiness evidence produced before one explicit lifecycle turn.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeExecutableCacheLimitsRetryLifecyclePacing {
    /// No safe retained cursor exists, so no turn or wait is authorized.
    CursorUnavailable,
    /// One lifecycle turn is ready for caller-owned execution.
    Ready {
        /// Whether this readiness required the configured relative wait.
        waited: bool,
    },
}

/// Result of composing pacing with one caller-owned lifecycle turn.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeExecutableCacheLimitsRetryLifecycleTurn<Outcome> {
    /// No safe cursor existed, so neither waiting nor turn execution occurred.
    CursorUnavailable,
    /// One caller-owned turn completed after optional repeat pacing.
    Executed {
        /// Exact caller-owned turn outcome.
        outcome: Outcome,
        /// Whether the turn followed the configured repeated-turn wait.
        waited: bool,
    },
}

/// Process-local selection of immediate-first and delayed repeated turns.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeExecutableCacheLimitsRetryLifecyclePacer {
    repeat_delay_nanoseconds: NonZeroU64,
    turn_completed: bool,
}

impl NativeExecutableCacheLimitsRetryLifecyclePacer {
    /// Creates pacing with one explicit positive delay between completed turns.
    #[must_use]
    pub const fn new(repeat_delay_nanoseconds: NonZeroU64) -> Self {
        Self {
            repeat_delay_nanoseconds,
            turn_completed: false,
        }
    }

    /// Records that caller-owned execution completed one lifecycle turn.
    pub const fn observe_turn_completed(&mut self) {
        self.turn_completed = true;
    }

    /// Prepares one explicit lifecycle turn without granting background work.
    ///
    /// The first authorized turn is immediately ready. After one caller-owned
    /// turn is explicitly observed complete, every later authorized turn waits
    /// through the supplied dependency first. Retained product stop evidence is
    /// intentionally not a shutdown signal: the activation boundary clears and
    /// recomputes that evidence for each new observation.
    ///
    /// # Errors
    ///
    /// Returns the exact delegated wait failure and grants no ready evidence.
    pub fn prepare_turn<Wait>(
        &self,
        lifecycle: &RetryLifecycle,
        wait: &mut Wait,
    ) -> Result<NativeExecutableCacheLimitsRetryLifecyclePacing, Wait::Error>
    where
        Wait: NativeContinuationRelativeWait,
    {
        if lifecycle.expected_cursor().is_none() {
            return Ok(
                NativeExecutableCacheLimitsRetryLifecyclePacing::
                    CursorUnavailable,
            );
        }
        if !self.turn_completed {
            return Ok(
                NativeExecutableCacheLimitsRetryLifecyclePacing::Ready {
                    waited: false,
                },
            );
        }
        wait.wait_nanoseconds(self.repeat_delay_nanoseconds)?;
        Ok(NativeExecutableCacheLimitsRetryLifecyclePacing::Ready {
            waited: true,
        })
    }

    /// Returns the configured positive delay before every repeated turn.
    #[must_use]
    pub const fn repeat_delay_nanoseconds(&self) -> NonZeroU64 {
        self.repeat_delay_nanoseconds
    }
}

/// Paces and executes at most one explicit caller-owned lifecycle turn.
///
/// Missing cursor authority returns without touching the wait dependency or
/// invoking `turn`. Wait failure returns before `turn`. Once `turn` returns,
/// completion is recorded even when its caller-owned outcome represents a
/// semantic failure; the next authorized turn is therefore paced.
///
/// # Errors
///
/// Returns the exact delegated relative-wait failure before turn execution.
pub fn execute_paced_cache_limits_retry_lifecycle_turn<Wait, Turn, Outcome>(
    pacer: &mut NativeExecutableCacheLimitsRetryLifecyclePacer,
    lifecycle: &mut RetryLifecycle,
    wait: &mut Wait,
    turn: Turn,
) -> NativeExecutableCacheLimitsRetryLifecycleTurnResult<Outcome, Wait::Error>
where
    Wait: NativeContinuationRelativeWait,
    Turn: FnOnce(&mut RetryLifecycle) -> Outcome,
{
    match pacer.prepare_turn(lifecycle, wait)? {
        NativeExecutableCacheLimitsRetryLifecyclePacing::CursorUnavailable => {
            Ok(NativeExecutableCacheLimitsRetryLifecycleTurn::CursorUnavailable)
        },
        NativeExecutableCacheLimitsRetryLifecyclePacing::Ready { waited } => {
            let outcome = turn(lifecycle);
            pacer.observe_turn_completed();
            Ok(NativeExecutableCacheLimitsRetryLifecycleTurn::Executed {
                outcome,
                waited,
            })
        },
    }
}

#[cfg(test)]
#[path = "../../../../../tests/tiered/cache_retry_pacing.rs"]
mod tests;
