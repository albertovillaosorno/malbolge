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

use std::convert::Infallible;
use std::num::NonZeroU64;

use super::*;
use crate::retry_control::{
    NativeContinuationRetryConflict, NativeContinuationRetryDecision,
    NativeContinuationRetryDirective, NativeContinuationRetryEvidence,
};
use crate::{
    executable_cache_limits_trigger_cadence as trigger,
    executable_cache_limits_trigger_cadence_cas as cursor_cas,
    executable_cache_limits_trigger_cadence_claim as claim,
};

type TriggerDecision =
    trigger::NativeExecutableCacheLimitsTriggerCadenceDecision;

fn positive(value: usize) -> Result<NonZeroUsize, String> {
    NonZeroUsize::new(value)
        .ok_or_else(|| String::from("test value must be positive"))
}

fn cursor(due_value: u64, interval_value: u64) -> Result<Cursor, String> {
    let due = NonZeroU64::new(due_value)
        .ok_or_else(|| String::from("test due must be positive"))?;
    let interval = NonZeroU64::new(interval_value)
        .ok_or_else(|| String::from("test interval must be positive"))?;
    Ok(Cursor::new(due, interval))
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

#[test]
fn retry_evidence_advances_and_clears_expected_cursor() -> Result<(), String> {
    let policy = Policy::return_on_contention();
    let initial = cursor(1, 2)?;
    let refreshed = cursor(3, 2)?;
    let mut lifecycle =
        NativeExecutableCacheLimitsRetryLifecycle::new_with_cursor(
            initial,
            positive(32)?,
            positive(3)?,
            policy,
        );
    let due = NonZeroU64::new(3)
        .ok_or_else(|| String::from("test due must be positive"))?;
    let withheld = claim::NativeExecutableCacheLimitsTriggerCadenceClaim::<
        Infallible,
    >::Withheld {
        decision: TriggerDecision::Deferred {
            observed_sequence: 1,
            due_sequence: due,
        },
        expected: refreshed,
    };
    let retry = NativeContinuationRetryEvidence::new(2, withheld);
    lifecycle.observe_retry(&retry);
    if lifecycle.expected_cursor() != Some(refreshed) {
        return Err(String::from(
            "withheld retry lost refreshed expected cursor",
        ));
    }

    let candidate = cursor(5, 2)?;
    let due_sequence = NonZeroU64::new(3)
        .ok_or_else(|| String::from("test due must be positive"))?;
    let missing = claim::NativeExecutableCacheLimitsTriggerCadenceClaim::<
        Infallible,
    >::Attempted {
        decision: TriggerDecision::Due {
            observed_sequence: due_sequence,
            next_due_sequence: NonZeroU64::new(5),
        },
        publication:
            cursor_cas::NativeExecutableCacheLimitsTriggerCadenceCas::Conflict {
                candidate,
                current: None,
                expected: Some(refreshed),
            },
    };
    let missing_retry = NativeContinuationRetryEvidence::new(1, missing);
    lifecycle.observe_retry(&missing_retry);
    if lifecycle.expected_cursor().is_none() {
        Ok(())
    } else {
        Err(String::from(
            "missing conflict state retained stale expected cursor",
        ))
    }
}
