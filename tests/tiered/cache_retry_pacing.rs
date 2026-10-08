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

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
enum FakeWaitAction {
    Cancel,
    #[default]
    Elapse,
    ElapseThenCancel,
    Fail,
}

#[derive(Debug, Default)]
struct FakeInterruptibleWait {
    action: FakeWaitAction,
    calls: Vec<NonZeroU64>,
    cancelled: bool,
    query_error: bool,
}

impl NativeContinuationInterruptibleWait for FakeInterruptibleWait {
    type Error = &'static str;

    fn is_cancelled(&self) -> Result<bool, Self::Error> {
        if self.query_error {
            Err("query failed")
        } else {
            Ok(self.cancelled)
        }
    }

    fn wait_nanoseconds(
        &mut self,
        nanoseconds: NonZeroU64,
    ) -> Result<WaitOutcome, Self::Error> {
        self.calls.push(nanoseconds);
        match self.action {
            FakeWaitAction::Cancel => {
                self.cancelled = true;
                Ok(WaitOutcome::Cancelled)
            },
            FakeWaitAction::Elapse => Ok(WaitOutcome::Elapsed),
            FakeWaitAction::ElapseThenCancel => {
                self.cancelled = true;
                Ok(WaitOutcome::Elapsed)
            },
            FakeWaitAction::Fail => Err("wait failed"),
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

#[test]
fn paced_turn_executes_immediate_then_waited_repeats() -> Result<(), String> {
    let mut pacer =
        NativeExecutableCacheLimitsRetryLifecyclePacer::new(positive_u64(29)?);
    let mut lifecycle = lifecycle_with_cursor()?;
    let mut wait = FakeWait::default();
    let mut calls = 0usize;
    let first = execute_paced_cache_limits_retry_lifecycle_turn(
        &mut pacer,
        &mut lifecycle,
        &mut wait,
        |_lifecycle| {
            calls = calls.saturating_add(1);
            31u8
        },
    )
    .map_err(String::from)?;
    let second = execute_paced_cache_limits_retry_lifecycle_turn(
        &mut pacer,
        &mut lifecycle,
        &mut wait,
        |_lifecycle| {
            calls = calls.saturating_add(1);
            37u8
        },
    )
    .map_err(String::from)?;
    if matches!(
        first,
        NativeExecutableCacheLimitsRetryLifecycleTurn::Executed {
            outcome: 31,
            waited: false,
        }
    ) && matches!(
        second,
        NativeExecutableCacheLimitsRetryLifecycleTurn::Executed {
            outcome: 37,
            waited: true,
        }
    ) && calls == 2
        && wait.calls == [positive_u64(29)?]
    {
        Ok(())
    } else {
        Err(String::from("paced turn composition drifted"))
    }
}

#[test]
fn paced_turn_skips_execution_without_ready_evidence() -> Result<(), String> {
    let mut pacer =
        NativeExecutableCacheLimitsRetryLifecyclePacer::new(positive_u64(31)?);
    pacer.observe_turn_completed();
    let mut missing = RetryLifecycle::new(
        positive_usize(32)?,
        positive_usize(3)?,
        RetryPolicy::return_on_contention(),
    );
    let mut wait = FakeWait::default();
    let mut calls = 0usize;
    let unavailable = execute_paced_cache_limits_retry_lifecycle_turn(
        &mut pacer,
        &mut missing,
        &mut wait,
        |_lifecycle| calls = calls.saturating_add(1),
    )
    .map_err(String::from)?;
    if unavailable
        != NativeExecutableCacheLimitsRetryLifecycleTurn::CursorUnavailable
        || calls != 0
        || !wait.calls.is_empty()
    {
        return Err(String::from("cursorless paced turn executed work"));
    }

    let mut lifecycle = lifecycle_with_cursor()?;
    wait.fail = true;
    let error = execute_paced_cache_limits_retry_lifecycle_turn(
        &mut pacer,
        &mut lifecycle,
        &mut wait,
        |_lifecycle| calls = calls.saturating_add(1),
    )
    .err()
    .ok_or_else(|| String::from("paced wait failure disappeared"))?;
    if error == "wait failed" && calls == 0 && wait.calls == [positive_u64(31)?]
    {
        Ok(())
    } else {
        Err(String::from("failed paced turn executed caller work"))
    }
}

#[test]
fn interruptible_pacing_cursor_loss_prevents_cancellation_queries()
-> Result<(), String> {
    let mut pacer =
        NativeExecutableCacheLimitsRetryLifecyclePacer::new(positive_u64(41)?);
    let mut lifecycle = RetryLifecycle::new(
        positive_usize(32)?,
        positive_usize(3)?,
        RetryPolicy::return_on_contention(),
    );
    pacer.observe_turn_completed();
    let mut wait = FakeInterruptibleWait {
        query_error: true,
        ..FakeInterruptibleWait::default()
    };
    let mut calls = 0usize;
    let result = execute_interruptible_paced_cache_limits_retry_lifecycle_turn(
        &mut pacer,
        &mut lifecycle,
        &mut wait,
        |_lifecycle| calls = calls.saturating_add(1),
    )
    .map_err(String::from)?;
    if result
        == NativeExecutableCacheLimitsRetryLifecycleTurn::CursorUnavailable
        && wait.calls.is_empty()
        && calls == 0
    {
        Ok(())
    } else {
        Err(String::from("missing cursor touched cancellable resources"))
    }
}

#[test]
fn interruptible_pacing_immediate_cancel_skips_turn_and_does_not_complete()
-> Result<(), String> {
    let mut pacer =
        NativeExecutableCacheLimitsRetryLifecyclePacer::new(positive_u64(43)?);
    let mut lifecycle = lifecycle_with_cursor()?;
    let mut wait = FakeInterruptibleWait {
        cancelled: true,
        ..FakeInterruptibleWait::default()
    };
    let mut calls = 0usize;
    let result = execute_interruptible_paced_cache_limits_retry_lifecycle_turn(
        &mut pacer,
        &mut lifecycle,
        &mut wait,
        |_lifecycle| calls = calls.saturating_add(1),
    )
    .map_err(String::from)?;
    wait.cancelled = false;
    let next = execute_interruptible_paced_cache_limits_retry_lifecycle_turn(
        &mut pacer,
        &mut lifecycle,
        &mut wait,
        |_lifecycle| calls = calls.saturating_add(1),
    )
    .map_err(String::from)?;
    if result == NativeExecutableCacheLimitsRetryLifecycleTurn::Cancelled
        && matches!(
            next,
            NativeExecutableCacheLimitsRetryLifecycleTurn::Executed {
                outcome: (),
                waited: false,
            }
        )
        && calls == 1
        && wait.calls.is_empty()
    {
        Ok(())
    } else {
        Err(String::from(
            "initial cancellation consumed first readiness",
        ))
    }
}

#[test]
fn interruptible_pacing_repeat_wait_cancellation_skips_turn()
-> Result<(), String> {
    let mut pacer =
        NativeExecutableCacheLimitsRetryLifecyclePacer::new(positive_u64(47)?);
    pacer.observe_turn_completed();
    let mut lifecycle = lifecycle_with_cursor()?;
    let mut wait = FakeInterruptibleWait {
        action: FakeWaitAction::Cancel,
        ..FakeInterruptibleWait::default()
    };
    let mut calls = 0usize;
    let result = execute_interruptible_paced_cache_limits_retry_lifecycle_turn(
        &mut pacer,
        &mut lifecycle,
        &mut wait,
        |_lifecycle| calls = calls.saturating_add(1),
    )
    .map_err(String::from)?;
    if result == NativeExecutableCacheLimitsRetryLifecycleTurn::Cancelled
        && wait.calls == [positive_u64(47)?]
        && calls == 0
    {
        Ok(())
    } else {
        Err(String::from("cancelled wait executed lifecycle work"))
    }
}

#[test]
fn interruptible_pacing_rechecks_cancel_after_elapsed_wait()
-> Result<(), String> {
    let mut pacer =
        NativeExecutableCacheLimitsRetryLifecyclePacer::new(positive_u64(53)?);
    pacer.observe_turn_completed();
    let mut lifecycle = lifecycle_with_cursor()?;
    let mut wait = FakeInterruptibleWait {
        action: FakeWaitAction::ElapseThenCancel,
        ..FakeInterruptibleWait::default()
    };
    let mut calls = 0usize;
    let result = execute_interruptible_paced_cache_limits_retry_lifecycle_turn(
        &mut pacer,
        &mut lifecycle,
        &mut wait,
        |_lifecycle| calls = calls.saturating_add(1),
    )
    .map_err(String::from)?;
    if result == NativeExecutableCacheLimitsRetryLifecycleTurn::Cancelled
        && wait.calls == [positive_u64(53)?]
        && calls == 0
    {
        Ok(())
    } else {
        Err(String::from("late cancellation was ignored"))
    }
}

#[test]
fn interruptible_pacing_query_failure_skips_execution() -> Result<(), String> {
    let mut pacer =
        NativeExecutableCacheLimitsRetryLifecyclePacer::new(positive_u64(61)?);
    let mut lifecycle = lifecycle_with_cursor()?;
    let mut wait = FakeInterruptibleWait {
        query_error: true,
        ..FakeInterruptibleWait::default()
    };
    let mut calls = 0usize;
    let error = execute_interruptible_paced_cache_limits_retry_lifecycle_turn(
        &mut pacer,
        &mut lifecycle,
        &mut wait,
        |_lifecycle| calls = calls.saturating_add(1),
    )
    .err();
    if error == Some("query failed") && calls == 0 && wait.calls.is_empty() {
        Ok(())
    } else {
        Err(String::from("cancel query failure granted readiness"))
    }
}

#[test]
fn interruptible_pacing_reports_wait_failures_and_waited_execution()
-> Result<(), String> {
    let mut pacer =
        NativeExecutableCacheLimitsRetryLifecyclePacer::new(positive_u64(59)?);
    let mut lifecycle = lifecycle_with_cursor()?;
    let mut wait = FakeInterruptibleWait::default();
    let mut calls = 0usize;
    let immediate =
        execute_interruptible_paced_cache_limits_retry_lifecycle_turn(
            &mut pacer,
            &mut lifecycle,
            &mut wait,
            |_lifecycle| calls = calls.saturating_add(1),
        )
        .map_err(String::from)?;
    wait.action = FakeWaitAction::Fail;
    let wait_error =
        execute_interruptible_paced_cache_limits_retry_lifecycle_turn(
            &mut pacer,
            &mut lifecycle,
            &mut wait,
            |_lifecycle| calls = calls.saturating_add(1),
        )
        .err();
    wait.action = FakeWaitAction::Elapse;
    let repeated =
        execute_interruptible_paced_cache_limits_retry_lifecycle_turn(
            &mut pacer,
            &mut lifecycle,
            &mut wait,
            |_lifecycle| calls = calls.saturating_add(1),
        )
        .map_err(String::from)?;
    if matches!(
        immediate,
        NativeExecutableCacheLimitsRetryLifecycleTurn::Executed {
            outcome: (),
            waited: false,
        }
    ) && wait_error == Some("wait failed")
        && matches!(
            repeated,
            NativeExecutableCacheLimitsRetryLifecycleTurn::Executed {
                outcome: (),
                waited: true,
            }
        )
        && calls == 2
        && wait.calls == [positive_u64(59)?, positive_u64(59)?]
    {
        Ok(())
    } else {
        Err(String::from(
            "interruptible wait failure progression drifted",
        ))
    }
}
