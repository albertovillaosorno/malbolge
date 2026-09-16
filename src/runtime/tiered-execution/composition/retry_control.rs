// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Policy-neutral caller direction between synchronous retry conflicts.
//   - Shared exact attempt accounting and terminal retry evidence.
// - Must-Not:
//   - Sleep, measure time, select attempt budgets, or infer cancellation
//     policy.
// - Allows:
//   - Inputs: exact completed-attempt evidence and caller retry direction.
//   - Outputs: continue or stop before another retry attempt.
//   - Side effects: none; callers may perform their own synchronous pacing.
// - Split-When:
//   - Asynchronous scheduling requires an awaitable retry-control contract.
// - Merge-When:
//   - Another shared runtime boundary owns the same retry direction evidence.
// - Summary:
//   - Lets callers gate conflict retries without runtime timing policy.
// - Description:
//   - A stop directive preserves the current conflict as terminal evidence.
//   - Optional typed stop state retains the caller reason without interpreting
//     its taxonomy or converting it into runtime policy.
//   - Attempt accounting begins after the first one-shot attempt and never
//     exceeds the caller-selected positive maximum.
// - Usage:
//   - Invoke only between a retryable conflict and the next attempt.
// - Defaults:
//   - Retry loops may choose an always-continue wrapper for legacy behavior.
//

//! Policy-neutral caller direction between synchronous retry conflicts.

use std::num::NonZeroUsize;

/// Generic terminal outcome plus exact attempts consumed by a retry loop.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryEvidence<Outcome> {
    attempts: usize,
    outcome: Outcome,
}

impl<Outcome> NativeContinuationRetryEvidence<Outcome> {
    /// Returns the exact number of attempts consumed.
    #[must_use]
    pub const fn attempts(&self) -> usize {
        self.attempts
    }

    /// Consumes retry evidence and returns the terminal outcome.
    #[must_use]
    pub fn into_outcome(self) -> Outcome {
        self.outcome
    }

    /// Creates terminal evidence after exact completed attempts.
    #[must_use]
    pub(crate) const fn new(attempts: usize, outcome: Outcome) -> Self {
        Self { attempts, outcome }
    }

    /// Borrows the terminal outcome.
    #[must_use]
    pub const fn outcome(&self) -> &Outcome {
        &self.outcome
    }
}

/// Caller decision that may retain an opaque typed stop reason.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationRetryDecision<StopReason> {
    /// Perform another attempt when the caller-selected budget permits it.
    Continue,
    /// Stop and preserve the caller-owned reason with exact conflict evidence.
    Stop(StopReason),
}

/// Caller direction after one retryable conflict.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationRetryDirective {
    /// Perform another attempt when the caller-selected budget permits it.
    Continue,
    /// Stop immediately and preserve the current conflict as terminal evidence.
    Stop,
}

/// Exact caller-owned stop reason bound to the conflict that triggered it.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryStop<StopReason> {
    conflict: NativeContinuationRetryConflict,
    reason: StopReason,
}

impl<StopReason> NativeContinuationRetryStop<StopReason> {
    /// Returns the exact conflict evidence observed before caller stop.
    #[must_use]
    pub const fn conflict(&self) -> NativeContinuationRetryConflict {
        self.conflict
    }

    /// Consumes stop evidence and returns the caller-owned reason.
    #[must_use]
    pub fn into_reason(self) -> StopReason {
        self.reason
    }

    /// Borrows the caller-owned stop reason.
    #[must_use]
    pub const fn reason(&self) -> &StopReason {
        &self.reason
    }
}

/// Adapter state for preserving a typed caller stop reason.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryStopState<StopReason> {
    stop: Option<NativeContinuationRetryStop<StopReason>>,
}

impl<StopReason> NativeContinuationRetryStopState<StopReason> {
    /// Consumes state and returns retained caller stop evidence, when present.
    #[must_use]
    pub fn into_stop(self) -> Option<NativeContinuationRetryStop<StopReason>> {
        self.stop
    }

    /// Creates empty caller stop state.
    #[must_use]
    pub const fn new() -> Self {
        Self { stop: None }
    }

    /// Converts one typed decision into the reasonless runtime directive.
    pub fn resolve(
        &mut self,
        conflict: NativeContinuationRetryConflict,
        decision: NativeContinuationRetryDecision<StopReason>,
    ) -> NativeContinuationRetryDirective {
        match decision {
            NativeContinuationRetryDecision::Continue => {
                NativeContinuationRetryDirective::Continue
            },
            NativeContinuationRetryDecision::Stop(reason) => {
                self.stop =
                    Some(NativeContinuationRetryStop { conflict, reason });
                NativeContinuationRetryDirective::Stop
            },
        }
    }

    /// Borrows retained caller stop evidence, when present.
    #[must_use]
    pub const fn stop(
        &self,
    ) -> Option<&NativeContinuationRetryStop<StopReason>> {
        self.stop.as_ref()
    }
}

impl<StopReason> Default for NativeContinuationRetryStopState<StopReason> {
    fn default() -> Self {
        Self::new()
    }
}

/// Exact evidence supplied before another conflict retry may begin.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryConflict {
    completed_attempts: usize,
}

impl NativeContinuationRetryConflict {
    /// Returns the exact number of attempts completed before this decision.
    #[must_use]
    pub const fn completed_attempts(self) -> usize {
        self.completed_attempts
    }

    /// Creates exact retry-conflict evidence after completed attempts.
    #[must_use]
    pub(crate) const fn new(completed_attempts: usize) -> Self {
        Self { completed_attempts }
    }
}

/// Shared exact attempt accounting for synchronous retry loops.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct NativeContinuationRetryAttemptCursor {
    completed_attempts: usize,
    maximum_attempts: NonZeroUsize,
}

impl NativeContinuationRetryAttemptCursor {
    /// Advances to another attempt when the caller-selected budget allows it.
    pub(crate) const fn advance(&mut self) -> bool {
        if !self.can_retry() {
            return false;
        }
        self.completed_attempts = self.completed_attempts.saturating_add(1);
        true
    }

    /// Starts accounting after the first one-shot attempt has completed.
    #[must_use]
    pub(crate) const fn after_first(maximum_attempts: NonZeroUsize) -> Self {
        Self {
            completed_attempts: 1,
            maximum_attempts,
        }
    }

    /// Returns whether another attempt remains in the positive budget.
    #[must_use]
    pub(crate) const fn can_retry(self) -> bool {
        self.completed_attempts < self.maximum_attempts.get()
    }

    /// Returns the exact number of attempts completed so far.
    #[must_use]
    pub(crate) const fn completed_attempts(self) -> usize {
        self.completed_attempts
    }

    /// Returns exact retry-conflict evidence for the completed attempt count.
    #[must_use]
    pub(crate) const fn conflict(self) -> NativeContinuationRetryConflict {
        NativeContinuationRetryConflict::new(self.completed_attempts)
    }
}
