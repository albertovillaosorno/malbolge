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
//   - Deterministic tests of bounded synchronous lifecycle stop evidence.
// - Must-Not:
//   - Spawn threads, read clocks, or touch persistent store state.
// - Allows:
//   - Inputs: explicit turn budgets, fake cancellation, and retained cursors.
//   - Outputs: exact completed counts for limit, break, cancellation, and loss.
//   - Side effects: test-local fake wait and callback observations only.
// - Split-When:
//   - Async run orchestration gains independent regression scope.
// - Merge-When:
//   - Product scheduler tests subsume all bounded synchronous evidence.
// - Summary:
//   - Proves bounded runner never fabricates completed turns.
// - Description:
//   - Fake waits record requests but never block the host.
// - Usage:
//   - Compiled only under Rust test configuration.
// - Defaults:
//   - Fresh fake waits elapse without cancellation.
//

//! Regression evidence for bounded synchronous cache-trigger lifecycle runs.

use std::num::NonZeroU64;

use super::*;
use crate::{
    executable_cache_limits_retry_policy as retry_policy,
    executable_cache_limits_trigger_cadence as trigger,
    interruptible_wait as interruptible,
};

type RunStop<Reason> = NativeExecutableCacheLimitsRetryLifecycleRunStop<Reason>;
type WaitOutcome = interruptible::NativeContinuationInterruptibleWaitOutcome;

#[derive(Clone, Copy, Debug, Default)]
enum FakeAction {
    Cancel,
    #[default]
    Elapse,
    Fail,
}

#[derive(Debug, Default)]
struct FakeWait {
    action: FakeAction,
    calls: Vec<NonZeroU64>,
    cancelled: bool,
}

impl NativeContinuationInterruptibleWait for FakeWait {
    type Error = &'static str;

    fn is_cancelled(&self) -> Result<bool, Self::Error> {
        Ok(self.cancelled)
    }

    fn wait_nanoseconds(
        &mut self,
        nanoseconds: NonZeroU64,
    ) -> Result<WaitOutcome, Self::Error> {
        self.calls.push(nanoseconds);
        match self.action {
            FakeAction::Cancel => {
                self.cancelled = true;
                Ok(WaitOutcome::Cancelled)
            },
            FakeAction::Elapse => Ok(WaitOutcome::Elapsed),
            FakeAction::Fail => Err("wait failed"),
        }
    }
}

fn positive(value: usize) -> Result<NonZeroUsize, String> {
    NonZeroUsize::new(value).ok_or_else(|| String::from("zero test limit"))
}

fn lifecycle() -> Result<RetryLifecycle, String> {
    let first = NonZeroU64::new(1)
        .ok_or_else(|| String::from("test due must be nonzero"))?;
    let second = NonZeroU64::new(2)
        .ok_or_else(|| String::from("test interval must be nonzero"))?;
    Ok(RetryLifecycle::new_with_cursor(
        trigger::NativeExecutableCacheLimitsTriggerCadence::new(first, second),
        positive(32)?,
        positive(3)?,
        retry_policy::NativeExecutableCacheLimitsRetryConflictPolicy::
            return_on_contention(),
    ))
}

fn pacer() -> Result<Pacer, String> {
    let duration = NonZeroU64::new(13)
        .ok_or_else(|| String::from("test delay must be nonzero"))?;
    Ok(Pacer::new(duration))
}

#[test]
fn limit_stops_after_exact_completed_turns() -> Result<(), String> {
    let mut lifecycle = lifecycle()?;
    let mut pacer = pacer()?;
    let mut wait = FakeWait::default();
    let mut called = 0usize;
    let result = run_bounded_interruptible_cache_limits_retry_lifecycle(
        positive(3)?,
        &mut NativeExecutableCacheLimitsRetryLifecycleRunContext::new(
            &mut pacer,
            &mut lifecycle,
            &mut wait,
        ),
        |_lifecycle| {
            called = called.saturating_add(1);
            ControlFlow::<&'static str>::Continue(())
        },
    )
    .map_err(String::from)?;
    if result == (RunStop::LimitReached { completed: 3 })
        && called == 3
        && wait.calls.len() == 2
    {
        Ok(())
    } else {
        Err(String::from("bounded limit or delay count drifted"))
    }
}

#[test]
fn caller_stop_includes_stopping_turn() -> Result<(), String> {
    let mut lifecycle = lifecycle()?;
    let mut pacer = pacer()?;
    let mut wait = FakeWait::default();
    let mut called = 0usize;
    let result = run_bounded_interruptible_cache_limits_retry_lifecycle(
        positive(5)?,
        &mut NativeExecutableCacheLimitsRetryLifecycleRunContext::new(
            &mut pacer,
            &mut lifecycle,
            &mut wait,
        ),
        |_lifecycle| {
            called = called.saturating_add(1);
            if called == 2 {
                ControlFlow::Break("policy-stop")
            } else {
                ControlFlow::Continue(())
            }
        },
    )
    .map_err(String::from)?;
    if result
        == (RunStop::CallerStopped {
            completed: 2,
            reason: "policy-stop",
        })
        && called == 2
        && wait.calls.len() == 1
    {
        Ok(())
    } else {
        Err(String::from("caller stop lost terminal evidence"))
    }
}

#[test]
fn cancelled_next_wait_does_not_count_another_turn() -> Result<(), String> {
    let mut lifecycle = lifecycle()?;
    let mut pacer = pacer()?;
    let mut wait = FakeWait {
        action: FakeAction::Cancel,
        ..FakeWait::default()
    };
    let mut called = 0usize;
    let result = run_bounded_interruptible_cache_limits_retry_lifecycle(
        positive(5)?,
        &mut NativeExecutableCacheLimitsRetryLifecycleRunContext::new(
            &mut pacer,
            &mut lifecycle,
            &mut wait,
        ),
        |_lifecycle| {
            called = called.saturating_add(1);
            ControlFlow::<&'static str>::Continue(())
        },
    )
    .map_err(String::from)?;
    if result == (RunStop::Cancelled { completed: 1 })
        && called == 1
        && wait.calls.len() == 1
    {
        Ok(())
    } else {
        Err(String::from("cancelled wait fabricated completed work"))
    }
}

#[test]
fn cursor_loss_after_completed_turn_stops_before_second_wait()
-> Result<(), String> {
    let mut lifecycle = lifecycle()?;
    let mut pacer = pacer()?;
    let mut wait = FakeWait::default();
    let result = run_bounded_interruptible_cache_limits_retry_lifecycle(
        positive(4)?,
        &mut NativeExecutableCacheLimitsRetryLifecycleRunContext::new(
            &mut pacer,
            &mut lifecycle,
            &mut wait,
        ),
        |current| {
            current.replace_expected_cursor(None);
            ControlFlow::<&'static str>::Continue(())
        },
    )
    .map_err(String::from)?;
    if result == (RunStop::CursorUnavailable { completed: 1 })
        && wait.calls.is_empty()
    {
        Ok(())
    } else {
        Err(String::from("cursor loss did not withhold later work"))
    }
}

#[test]
fn failing_wait_keeps_exact_error_and_completed_pacing() -> Result<(), String> {
    let mut lifecycle = lifecycle()?;
    let mut pacer = pacer()?;
    let mut wait = FakeWait {
        action: FakeAction::Fail,
        ..FakeWait::default()
    };
    let mut called = 0usize;
    let result = run_bounded_interruptible_cache_limits_retry_lifecycle(
        positive(4)?,
        &mut NativeExecutableCacheLimitsRetryLifecycleRunContext::new(
            &mut pacer,
            &mut lifecycle,
            &mut wait,
        ),
        |_lifecycle| {
            called = called.saturating_add(1);
            ControlFlow::<&'static str>::Continue(())
        },
    );
    if result.err() == Some("wait failed")
        && called == 1
        && wait.calls.len() == 1
    {
        Ok(())
    } else {
        Err(String::from("wait failure was converted to stop evidence"))
    }
}
