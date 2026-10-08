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
//   - Deterministic typed caller-error and wait-error progression tests.
// - Must-Not:
//   - Read clocks, use native code, persist state, or spawn workers.
// - Allows:
//   - Inputs: test-local fake waits, positive finite limits, lifecycle cursors.
//   - Outputs: exact callback error/stop progress and delegated wait evidence.
//   - Side effects: test-local counters only.
// - Split-When:
//   - A product policy adapter adds independent failure tests.
// - Merge-When:
//   - One integrated scheduler subsumes synchronous turn regressions.
// - Summary:
//   - Proves fallible finite runs account for returned callback failures.
// - Description:
//   - Exact failure class and completed counts stay independently observable.
// - Usage:
//   - Compiled only under Rust test configuration.
// - Defaults:
//   - Fake waits complete without wall-clock sleeping.
//

//! Focused fallible bounded lifecycle regression tests.

use std::num::NonZeroU64;

use super::*;
use crate::{
    executable_cache_limits_retry_pacing as pacing,
    executable_cache_limits_retry_policy as policy,
    executable_cache_limits_trigger_cadence as trigger,
    interruptible_wait as interruptible,
};

type WaitOutcome = interruptible::NativeContinuationInterruptibleWaitOutcome;
type Pacer = pacing::NativeExecutableCacheLimitsRetryLifecyclePacer;
type Context<'resource> =
    run::NativeExecutableCacheLimitsRetryLifecycleRunContext<
        'resource,
        FakeWait,
    >;
type RunError = NativeExecutableCacheLimitsRetryLifecycleRunFailure<
    &'static str,
    &'static str,
>;

type Resources = (RetryLifecycle, Pacer, FakeWait);

#[derive(Debug, Default)]
struct FakeWait {
    calls: usize,
    cancelled: bool,
    fail_on_wait: bool,
    query_error: bool,
}

impl NativeContinuationInterruptibleWait for FakeWait {
    type Error = &'static str;

    fn is_cancelled(&self) -> Result<bool, Self::Error> {
        if self.query_error {
            Err("query-failed")
        } else {
            Ok(self.cancelled)
        }
    }

    fn wait_nanoseconds(
        &mut self,
        _nanoseconds: NonZeroU64,
    ) -> Result<WaitOutcome, Self::Error> {
        self.calls = self.calls.saturating_add(1);
        if self.fail_on_wait {
            Err("wait-failed")
        } else {
            Ok(WaitOutcome::Elapsed)
        }
    }
}

fn positive(value: usize) -> Result<NonZeroUsize, String> {
    NonZeroUsize::new(value).ok_or_else(|| String::from("zero test bound"))
}

fn resources() -> Result<Resources, String> {
    let start = NonZeroU64::new(1)
        .ok_or_else(|| String::from("nonzero cursor start"))?;
    let delay =
        NonZeroU64::new(2).ok_or_else(|| String::from("nonzero delay"))?;
    let cadence =
        trigger::NativeExecutableCacheLimitsTriggerCadence::new(start, delay);
    let lifecycle = RetryLifecycle::new_with_cursor(
        cadence,
        positive(12)?,
        positive(2)?,
        policy::NativeExecutableCacheLimitsRetryConflictPolicy::
            return_on_contention(),
    );
    Ok((lifecycle, Pacer::new(delay), FakeWait::default()))
}

#[test]
fn callback_failure_counts_returned_attempt() -> Result<(), String> {
    let (mut lifecycle, mut pacer, mut wait) = resources()?;
    let mut called = 0usize;
    let result =
        run_bounded_interruptible_fallible_cache_limits_retry_lifecycle(
            positive(4)?,
            &mut Context::new(&mut pacer, &mut lifecycle, &mut wait),
            |_lifecycle| {
                called = called.saturating_add(1);
                if called == 2 {
                    Err("activation-failed")
                } else {
                    Ok(ControlFlow::<&'static str>::Continue(()))
                }
            },
        );
    if result
        == Err(RunError::Turn {
            completed: 2,
            error: "activation-failed",
        })
        && called == 2
        && wait.calls == 1
    {
        Ok(())
    } else {
        Err(String::from("returned turn error lost exact progress"))
    }
}

#[test]
fn callback_stop_retains_reason_and_completed_count() -> Result<(), String> {
    let (mut lifecycle, mut pacer, mut wait) = resources()?;
    let result =
        run_bounded_interruptible_fallible_cache_limits_retry_lifecycle(
            positive(3)?,
            &mut Context::new(&mut pacer, &mut lifecycle, &mut wait),
            |_lifecycle| Ok::<_, &'static str>(ControlFlow::Break("stop")),
        );
    if result
        == Ok(RunStop::CallerStopped {
            completed: 1,
            reason: "stop",
        })
        && wait.calls == 0
    {
        Ok(())
    } else {
        Err(String::from("caller break result drifted"))
    }
}

#[test]
fn delegated_query_failure_does_not_count_failed_turn() -> Result<(), String> {
    let (mut lifecycle, mut pacer, mut wait) = resources()?;
    wait.query_error = true;
    let mut called = 0usize;
    let result =
        run_bounded_interruptible_fallible_cache_limits_retry_lifecycle(
            positive(3)?,
            &mut Context::new(&mut pacer, &mut lifecycle, &mut wait),
            |_lifecycle| {
                called = called.saturating_add(1);
                Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
            },
        );
    if result
        == Err(RunError::Wait(RunWaitFailure {
            completed: 0,
            error: "query-failed",
        }))
        && called == 0
        && wait.calls == 0
    {
        Ok(())
    } else {
        Err(String::from("query failure was counted as a callback"))
    }
}

#[test]
fn delegated_wait_failure_preserves_previous_callback() -> Result<(), String> {
    let (mut lifecycle, mut pacer, mut wait) = resources()?;
    wait.fail_on_wait = true;
    let mut called = 0usize;
    let result =
        run_bounded_interruptible_fallible_cache_limits_retry_lifecycle(
            positive(3)?,
            &mut Context::new(&mut pacer, &mut lifecycle, &mut wait),
            |_lifecycle| {
                called = called.saturating_add(1);
                Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
            },
        );
    if result
        == Err(RunError::Wait(RunWaitFailure {
            completed: 1,
            error: "wait-failed",
        }))
        && called == 1
        && wait.calls == 1
    {
        Ok(())
    } else {
        Err(String::from("wait failure erased completed callback"))
    }
}

#[test]
fn successful_fallible_run_reaches_exact_limit() -> Result<(), String> {
    let (mut lifecycle, mut pacer, mut wait) = resources()?;
    let mut called = 0usize;
    let result =
        run_bounded_interruptible_fallible_cache_limits_retry_lifecycle(
            positive(3)?,
            &mut Context::new(&mut pacer, &mut lifecycle, &mut wait),
            |_lifecycle| {
                called = called.saturating_add(1);
                Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
            },
        );
    if result == Ok(RunStop::LimitReached { completed: 3 })
        && called == 3
        && wait.calls == 2
    {
        Ok(())
    } else {
        Err(String::from("successful fallible run lost terminal limit"))
    }
}

#[test]
fn cancellation_wins_before_any_fallible_callback() -> Result<(), String> {
    let (mut lifecycle, mut pacer, mut wait) = resources()?;
    wait.cancelled = true;
    let mut called = 0usize;
    let result =
        run_bounded_interruptible_fallible_cache_limits_retry_lifecycle(
            positive(3)?,
            &mut Context::new(&mut pacer, &mut lifecycle, &mut wait),
            |_lifecycle| {
                called = called.saturating_add(1);
                Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
            },
        );
    if result == Ok(RunStop::Cancelled { completed: 0 })
        && called == 0
        && wait.calls == 0
    {
        Ok(())
    } else {
        Err(String::from("cancelled run invoked fallible callback"))
    }
}

#[test]
fn absent_cursor_skips_fallible_callbacks_and_wait_queries()
-> Result<(), String> {
    let (mut lifecycle, mut pacer, mut wait) = resources()?;
    lifecycle.replace_expected_cursor(None);
    wait.query_error = true;
    let mut called = 0usize;
    let result =
        run_bounded_interruptible_fallible_cache_limits_retry_lifecycle(
            positive(3)?,
            &mut Context::new(&mut pacer, &mut lifecycle, &mut wait),
            |_lifecycle| {
                called = called.saturating_add(1);
                Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
            },
        );
    if result == Ok(RunStop::CursorUnavailable { completed: 0 })
        && called == 0
        && wait.calls == 0
    {
        Ok(())
    } else {
        Err(String::from("cursorless run touched fallible resources"))
    }
}
