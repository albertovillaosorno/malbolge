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
//   - Regression evidence for process-local cache-trigger lifecycle pacing.
// - Must-Not:
//   - Sleep a real thread, execute activation, or infer async cancellation.
// - Allows:
//   - Inputs: retained/missing cursor authority and deterministic fake waits.
//   - Outputs: immediate, delayed, unavailable, and wait-failure assertions.
//   - Side effects: test-local pacing and fake-wait mutation only.
// - Split-When:
//   - Async lifecycle ownership gains independent regression scope.
// - Merge-When:
//   - Product scheduler tests subsume deterministic pacing behavior.
// - Summary:
//   - Proves first-turn immediacy and exact repeated-turn delay selection.
// - Description:
//   - Cursor loss always fails closed before the wait dependency is touched.
// - Usage:
//   - Compiled only under Rust test configuration.
// - Defaults:
//   - Fake waits record exact requested nanoseconds without blocking.
//

//! Regression coverage for cache-trigger lifecycle pacing.

use std::num::NonZeroUsize;

use super::*;
use crate::{
    executable_cache_limits_retry_policy as retry_policy,
    executable_cache_limits_trigger_cadence as trigger,
};

type Cursor = trigger::NativeExecutableCacheLimitsTriggerCadence;
type RetryPolicy = retry_policy::NativeExecutableCacheLimitsRetryConflictPolicy;

#[derive(Debug, Default)]
struct FakeWait {
    calls: Vec<NonZeroU64>,
    fail: bool,
}

impl NativeContinuationRelativeWait for FakeWait {
    type Error = &'static str;

    fn wait_nanoseconds(
        &mut self,
        nanoseconds: NonZeroU64,
    ) -> Result<(), Self::Error> {
        self.calls.push(nanoseconds);
        if self.fail {
            Err("wait failed")
        } else {
            Ok(())
        }
    }
}

fn positive_usize(value: usize) -> Result<NonZeroUsize, String> {
    NonZeroUsize::new(value)
        .ok_or_else(|| String::from("test usize must be positive"))
}

fn positive_u64(value: u64) -> Result<NonZeroU64, String> {
    NonZeroU64::new(value)
        .ok_or_else(|| String::from("test u64 must be positive"))
}

fn lifecycle_with_cursor() -> Result<RetryLifecycle, String> {
    Ok(RetryLifecycle::new_with_cursor(
        Cursor::new(positive_u64(1)?, positive_u64(2)?),
        positive_usize(32)?,
        positive_usize(3)?,
        RetryPolicy::return_on_contention(),
    ))
}

#[test]
fn first_authorized_turn_is_immediate_then_repeats_wait_exactly()
-> Result<(), String> {
    let mut pacer =
        NativeExecutableCacheLimitsRetryLifecyclePacer::new(positive_u64(17)?);
    let lifecycle = lifecycle_with_cursor()?;
    let mut wait = FakeWait::default();
    let first = pacer
        .prepare_turn(&lifecycle, &mut wait)
        .map_err(String::from)?;
    if first
        != (NativeExecutableCacheLimitsRetryLifecyclePacing::Ready {
            waited: false,
        })
        || !wait.calls.is_empty()
    {
        return Err(String::from("first turn was not immediately ready"));
    }
    pacer.observe_turn_completed();
    let repeated = pacer
        .prepare_turn(&lifecycle, &mut wait)
        .map_err(String::from)?;
    if repeated
        == (NativeExecutableCacheLimitsRetryLifecyclePacing::Ready {
            waited: true,
        })
        && wait.calls == [positive_u64(17)?]
        && pacer.repeat_delay_nanoseconds() == positive_u64(17)?
    {
        Ok(())
    } else {
        Err(String::from("repeated turn did not wait exactly once"))
    }
}

#[test]
fn missing_cursor_fails_closed_before_wait() -> Result<(), String> {
    let mut pacer =
        NativeExecutableCacheLimitsRetryLifecyclePacer::new(positive_u64(19)?);
    pacer.observe_turn_completed();
    let lifecycle = RetryLifecycle::new(
        positive_usize(32)?,
        positive_usize(3)?,
        RetryPolicy::return_on_contention(),
    );
    let mut wait = FakeWait::default();
    let pacing = pacer
        .prepare_turn(&lifecycle, &mut wait)
        .map_err(String::from)?;
    if pacing
        == NativeExecutableCacheLimitsRetryLifecyclePacing::CursorUnavailable
        && wait.calls.is_empty()
    {
        Ok(())
    } else {
        Err(String::from("cursor loss touched wait dependency"))
    }
}

#[test]
fn failed_repeat_wait_grants_no_ready_evidence() -> Result<(), String> {
    let mut pacer =
        NativeExecutableCacheLimitsRetryLifecyclePacer::new(positive_u64(23)?);
    pacer.observe_turn_completed();
    let lifecycle = lifecycle_with_cursor()?;
    let mut wait = FakeWait {
        calls: Vec::new(),
        fail: true,
    };
    let error = pacer
        .prepare_turn(&lifecycle, &mut wait)
        .err()
        .ok_or_else(|| String::from("wait failure disappeared"))?;
    if error == "wait failed" && wait.calls == [positive_u64(23)?] {
        Ok(())
    } else {
        Err(String::from("wait failure did not preserve exact request"))
    }
}
