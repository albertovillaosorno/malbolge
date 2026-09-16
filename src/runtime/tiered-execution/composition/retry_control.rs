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
// - Usage:
//   - Invoke only between a retryable conflict and the next attempt.
// - Defaults:
//   - Retry loops may choose an always-continue wrapper for legacy behavior.
//

//! Policy-neutral caller direction between synchronous retry conflicts.

/// Caller direction after one retryable conflict.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationRetryDirective {
    /// Perform another attempt when the caller-selected budget permits it.
    Continue,
    /// Stop immediately and preserve the current conflict as terminal evidence.
    Stop,
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
