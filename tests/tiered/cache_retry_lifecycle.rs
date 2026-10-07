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
//   - Regression coverage for process-local cache-trigger retry lifecycle
//     state.
// - Must-Not:
//   - Execute cache activation, persistence, timing, or background scheduling.
// - Allows:
//   - Inputs: explicit retry bounds, conflict policy, and test conflict
//     evidence.
//   - Outputs: retained and cleared process-local typed stop evidence.
//   - Side effects: test-local lifecycle mutation only.
// - Split-When:
//   - Durable lifecycle state gains independent regression scope.
// - Merge-When:
//   - Parent lifecycle no longer requires private state-handoff coverage.
// - Summary:
//   - Proves lifecycle stop state is available to the higher coordinator.
// - Description:
//   - This test exercises no durable cursor or activation resource.
// - Usage:
//   - Compiled only under Rust test configuration.
// - Defaults:
//   - Fresh lifecycle state contains no stop evidence.
//

//! Regression coverage for cache-trigger retry lifecycle state.

use super::*;
use crate::retry_control::{
    NativeContinuationRetryConflict, NativeContinuationRetryDecision,
    NativeContinuationRetryDirective,
};

fn positive(value: usize) -> Result<NonZeroUsize, String> {
    NonZeroUsize::new(value)
        .ok_or_else(|| String::from("test value must be positive"))
}

#[test]
fn coordinator_handoff_retains_exact_product_stop() -> Result<(), String> {
    let policy = Policy::return_on_contention();
    let mut lifecycle = NativeExecutableCacheLimitsRetryLifecycle::new(
        positive(32)?,
        positive(3)?,
        policy,
    );
    if lifecycle.stop().is_some() {
        return Err(String::from("fresh lifecycle invented stop evidence"));
    }
    let conflict = NativeContinuationRetryConflict::new(2);
    let decision = policy.decide(conflict);
    let directive = lifecycle.stop_state_mut().resolve(conflict, decision);
    let stop = lifecycle
        .stop()
        .ok_or_else(|| String::from("lifecycle stop evidence disappeared"))?;
    if directive == NativeContinuationRetryDirective::Stop
        && stop.conflict() == conflict
        && stop.reason() == &StopReason::ContentionObserved
        && decision
            == NativeContinuationRetryDecision::Stop(
                StopReason::ContentionObserved,
            )
    {
        Ok(())
    } else {
        Err(String::from("lifecycle coordinator handoff drifted"))
    }
}
