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
//   - Process-local cache-trigger retry configuration and retained product stop
//     evidence across repeated observed-activation calls.
// - Must-Not:
//   - Execute activation, load/store cursors, read clocks, sleep, spawn work,
//     or infer an expected durable cursor.
// - Allows:
//   - Inputs: positive retry/byte bounds and explicit product conflict policy.
//   - Outputs: immutable retry configuration and latest typed stop evidence.
//   - Side effects: process-local stop-state mutation by the higher activation
//     coordinator only.
// - Split-When:
//   - Durable lifecycle configuration or asynchronous scheduling gains
//     independent authority.
// - Merge-When:
//   - One product scheduler owns retry configuration and activation resources.
// - Summary:
//   - Reuses cache-trigger retry policy and stop state across observations.
// - Description:
//   - Durable expected-cursor ownership remains outside this state owner.
// - Usage:
//   - Build one owner, then bind it through the observed activation
//     coordinator.
// - Defaults:
//   - New owners contain no retained stop evidence.
//

//! Process-local lifecycle state for policy-driven cache-trigger retries.

use std::num::NonZeroUsize;

use crate::retry_control::{
    NativeContinuationRetryStop, NativeContinuationRetryStopState,
};
use crate::{
    executable_cache_limits_retry_policy as retry_policy,
    executable_cache_limits_retry_reason as retry_reason,
};

type Policy = retry_policy::NativeExecutableCacheLimitsRetryConflictPolicy;
type StopReason = retry_reason::NativeExecutableCacheLimitsRetryStopReason;

/// Reusable process-local policy and stop state for observed cache activation.
#[derive(Debug)]
pub struct NativeExecutableCacheLimitsRetryLifecycle {
    maximum_attempts: NonZeroUsize,
    maximum_bytes: NonZeroUsize,
    policy: Policy,
    stop_state: NativeContinuationRetryStopState<StopReason>,
}

impl NativeExecutableCacheLimitsRetryLifecycle {
    /// Returns the positive mechanical attempt budget.
    #[must_use]
    pub const fn maximum_attempts(&self) -> NonZeroUsize {
        self.maximum_attempts
    }

    /// Returns the positive canonical cursor byte bound.
    #[must_use]
    pub const fn maximum_bytes(&self) -> NonZeroUsize {
        self.maximum_bytes
    }

    /// Creates one explicit process-local retry lifecycle owner.
    #[must_use]
    pub const fn new(
        maximum_bytes: NonZeroUsize,
        maximum_attempts: NonZeroUsize,
        policy: Policy,
    ) -> Self {
        Self {
            maximum_attempts,
            maximum_bytes,
            policy,
            stop_state: NativeContinuationRetryStopState::new(),
        }
    }

    /// Returns the immutable product conflict policy.
    #[must_use]
    pub const fn policy(&self) -> Policy {
        self.policy
    }

    /// Borrows the latest explicit product stop evidence, when present.
    #[must_use]
    pub const fn stop(
        &self,
    ) -> Option<&NativeContinuationRetryStop<StopReason>> {
        self.stop_state.stop()
    }

    pub(crate) const fn stop_state_mut(
        &mut self,
    ) -> &mut NativeContinuationRetryStopState<StopReason> {
        &mut self.stop_state
    }
}

#[cfg(test)]
#[path = "../../../../../tests/tiered/cache_retry_lifecycle.rs"]
mod tests;
