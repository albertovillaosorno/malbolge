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
//   - Explicit product direction for cache-trigger claim conflicts.
// - Must-Not:
//   - Execute retries, select mechanical attempt budgets, sleep, read clocks,
//     persist policy, or spawn unattended work.
// - Allows:
//   - Inputs: exact completed-attempt conflict evidence and immutable policy.
//   - Outputs: typed continue or stop decision using the product reason
//     taxonomy.
//   - Side effects: none.
// - Split-When:
//   - Adaptive evidence or persisted policy gains independent authority.
// - Merge-When:
//   - One product lifecycle owner subsumes conflict policy and execution.
// - Summary:
//   - Converts exact cache-trigger contention evidence into product direction.
// - Description:
//   - Mechanical retry-budget exhaustion remains reasonless and separate.
// - Usage:
//   - Invoke only when the retry boundary requests direction after a conflict.
// - Defaults:
//   - No implicit policy exists; callers construct one explicitly.
//

//! Product conflict policy for cache-trigger retries.

use std::num::NonZeroUsize;

use crate::executable_cache_limits_retry_reason as retry_reason;
use crate::retry_control::{
    NativeContinuationRetryConflict, NativeContinuationRetryDecision,
};

type Decision = NativeContinuationRetryDecision<RetryStopReason>;
type PolicyKind = NativeExecutableCacheLimitsRetryConflictPolicyKind;
type RetryStopReason = retry_reason::NativeExecutableCacheLimitsRetryStopReason;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum NativeExecutableCacheLimitsRetryConflictPolicyKind {
    AttemptLimit(NonZeroUsize),
    ReturnOnContention,
}

/// Immutable product policy for one retryable cache-trigger conflict.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeExecutableCacheLimitsRetryConflictPolicy {
    kind: NativeExecutableCacheLimitsRetryConflictPolicyKind,
}

impl NativeExecutableCacheLimitsRetryConflictPolicy {
    /// Continues until completed conflicting attempts reach the positive limit.
    #[must_use]
    pub const fn attempt_limit(limit: NonZeroUsize) -> Self {
        Self {
            kind: PolicyKind::AttemptLimit(limit),
        }
    }

    /// Returns typed product direction for one exact retry conflict.
    #[must_use]
    pub const fn decide(
        self,
        conflict: NativeContinuationRetryConflict,
    ) -> Decision {
        match self.kind {
            PolicyKind::AttemptLimit(limit) => {
                if conflict.completed_attempts() >= limit.get() {
                    NativeContinuationRetryDecision::Stop(
                        RetryStopReason::PolicyLimit,
                    )
                } else {
                    NativeContinuationRetryDecision::Continue
                }
            },
            PolicyKind::ReturnOnContention => {
                NativeContinuationRetryDecision::Stop(
                    RetryStopReason::ContentionObserved,
                )
            },
        }
    }

    /// Stops on the first conflict presented by the retry boundary.
    #[must_use]
    pub const fn return_on_contention() -> Self {
        Self {
            kind: PolicyKind::ReturnOnContention,
        }
    }
}

#[cfg(test)]
#[path = "../../../../../tests/tiered/cache_retry_policy.rs"]
mod tests;
