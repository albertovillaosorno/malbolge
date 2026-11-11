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
//   - Process-local cache-trigger retry configuration, latest safe expected
//     cursor, and retained product stop evidence across observed activations.
// - Must-Not:
//   - Execute activation, load/store cursors, read clocks, sleep, spawn work,
//     or infer an expected durable cursor.
// - Allows:
//   - Inputs: positive retry/byte bounds, explicit product conflict policy,
//     optional expected cursor, and exact terminal claim-retry evidence.
//   - Outputs: immutable retry configuration, latest safe expected cursor, and
//     latest typed stop evidence.
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
//   - Cursor state advances only from exact terminal claim evidence.
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
    executable_cache_limits_trigger_cadence as trigger,
    executable_cache_limits_trigger_cadence_claim_retry as claim_retry,
};

type Cursor = trigger::NativeExecutableCacheLimitsTriggerCadence;
type Policy = retry_policy::NativeExecutableCacheLimitsRetryConflictPolicy;
type Retry<DurabilityError> =
    claim_retry::NativeExecutableCacheLimitsTriggerCadenceClaimRetry<
        DurabilityError,
    >;
type StopReason = retry_reason::NativeExecutableCacheLimitsRetryStopReason;

/// Reusable process-local policy and stop state for observed cache activation.
#[derive(Debug)]
pub struct NativeExecutableCacheLimitsRetryLifecycle {
    expected_cursor: Option<Cursor>,
    maximum_attempts: NonZeroUsize,
    maximum_bytes: NonZeroUsize,
    policy: Policy,
    stop_state: NativeContinuationRetryStopState<StopReason>,
}

impl NativeExecutableCacheLimitsRetryLifecycle {
    /// Returns the latest safe expected durable cursor, when available.
    #[must_use]
    pub const fn expected_cursor(&self) -> Option<Cursor> {
        self.expected_cursor
    }

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
            expected_cursor: None,
            maximum_attempts,
            maximum_bytes,
            policy,
            stop_state: NativeContinuationRetryStopState::new(),
        }
    }

    /// Creates one lifecycle owner with an initial expected durable cursor.
    #[must_use]
    pub const fn new_with_cursor(
        expected_cursor: Cursor,
        maximum_bytes: NonZeroUsize,
        maximum_attempts: NonZeroUsize,
        policy: Policy,
    ) -> Self {
        Self {
            expected_cursor: Some(expected_cursor),
            maximum_attempts,
            maximum_bytes,
            policy,
            stop_state: NativeContinuationRetryStopState::new(),
        }
    }

    /// Advances expected cursor state from exact terminal retry evidence.
    pub const fn observe_retry<DurabilityError>(
        &mut self,
        retry: &Retry<DurabilityError>,
    ) {
        self.expected_cursor = retry.outcome().next_expected_cursor();
    }

    /// Returns the immutable product conflict policy.
    #[must_use]
    pub const fn policy(&self) -> Policy {
        self.policy
    }

    pub(crate) const fn replace_expected_cursor(
        &mut self,
        expected_cursor: Option<Cursor>,
    ) {
        self.expected_cursor = expected_cursor;
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
