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
//   - Regression coverage for cache-trigger product conflict policy.
// - Must-Not:
//   - Execute retries, infer timing, or mutate durable/runtime state.
// - Allows:
//   - Inputs: exact completed-attempt conflict evidence and explicit policy.
//   - Outputs: exact typed continue/stop decisions.
//   - Side effects: none.
// - Split-When:
//   - Adaptive conflict evidence gains independent regression scope.
// - Merge-When:
//   - Parent policy no longer requires private conflict construction access.
// - Summary:
//   - Proves product conflict policy remains distinct from retry budgets.
// - Description:
//   - Policy limits name explicit stops; mechanical exhaustion stays elsewhere.
// - Usage:
//   - Compiled only under Rust test configuration.
// - Defaults:
//   - No implicit policy is tested or assumed.
//

//! Regression coverage for cache-trigger product conflict policy.

use super::*;
use crate::executable_cache_limits_retry_reason as retry_reason;

type RetryStopReason = retry_reason::NativeExecutableCacheLimitsRetryStopReason;

#[test]
fn return_on_contention_names_first_conflict() {
    let policy =
        NativeExecutableCacheLimitsRetryConflictPolicy::return_on_contention();
    let decision = policy.decide(NativeContinuationRetryConflict::new(1));
    assert_eq!(
        decision,
        NativeContinuationRetryDecision::Stop(
            RetryStopReason::ContentionObserved,
        ),
    );
}

#[test]
fn attempt_limit_continues_before_limit() -> Result<(), String> {
    let Some(limit) = NonZeroUsize::new(2) else {
        return Err(String::from("two must be positive"));
    };
    let policy =
        NativeExecutableCacheLimitsRetryConflictPolicy::attempt_limit(limit);
    if policy.decide(NativeContinuationRetryConflict::new(1))
        == NativeContinuationRetryDecision::Continue
    {
        Ok(())
    } else {
        Err(String::from("attempt limit stopped before threshold"))
    }
}

#[test]
fn attempt_limit_names_explicit_policy_stop() -> Result<(), String> {
    let Some(limit) = NonZeroUsize::new(2) else {
        return Err(String::from("two must be positive"));
    };
    let policy =
        NativeExecutableCacheLimitsRetryConflictPolicy::attempt_limit(limit);
    if policy.decide(NativeContinuationRetryConflict::new(2))
        == NativeContinuationRetryDecision::Stop(RetryStopReason::PolicyLimit)
    {
        Ok(())
    } else {
        Err(String::from("attempt limit did not name policy stop"))
    }
}
