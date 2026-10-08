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
//   - Deterministic scoped worker and supervisor cancellation regression tests.
// - Must-Not:
//   - Spawn detached workers, depend on exact wall-clock timings, or persist
//     retry state.
// - Allows:
//   - Inputs: explicit positive turn counts, test-local synchronization, and
//     borrowed process-local retry lifecycle state.
//   - Outputs: joined terminal progress and typed cancellation/failure
//     evidence.
//   - Side effects: short bounded host threads, all joined before return.
// - Split-When:
//   - Background scheduler and worker pools gain independent test scope.
// - Merge-When:
//   - One scheduler test suite owns the same scoped lifecycle behavior.
// - Summary:
//   - Proves finite workers do not escape their cancellation scope.
// - Description:
//   - Supervisor cancellation is sequenced by channels, never sleep races.
// - Usage:
//   - Compiled only under Rust test configuration.
// - Defaults:
//   - Positive nanosecond pacing prevents flaky elapsed-time assertions.
//

//! Joined and cancellable scoped cache-trigger worker regression tests.

use std::num::NonZeroU64;
use std::panic::resume_unwind;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, mpsc};

use super::*;
use crate::{
    executable_cache_limits_retry_policy as policy,
    executable_cache_limits_trigger_cadence as trigger,
};
type RunStop<Reason> =
    run::NativeExecutableCacheLimitsRetryLifecycleRunStop<Reason>;
type Resources = (RetryLifecycle, Pacer);

fn positive_u64(value: u64) -> Result<NonZeroU64, String> {
    NonZeroU64::new(value).ok_or_else(|| String::from("zero duration"))
}

fn positive_usize(value: usize) -> Result<NonZeroUsize, String> {
    NonZeroUsize::new(value).ok_or_else(|| String::from("zero limit"))
}

fn resources() -> Result<Resources, String> {
    let cadence = trigger::NativeExecutableCacheLimitsTriggerCadence::new(
        positive_u64(1)?,
        positive_u64(2)?,
    );
    let lifecycle = RetryLifecycle::new_with_cursor(
        cadence, positive_usize(15)?, positive_usize(2)?,
        policy::NativeExecutableCacheLimitsRetryConflictPolicy::
            return_on_contention(),
    );
    Ok((lifecycle, Pacer::new(positive_u64(1)?)))
}

#[test]
fn joined_worker_reaches_exact_limit() -> Result<(), String> {
    let (mut lifecycle, mut pacer) = resources()?;
    let mut called = 0usize;
    let completed = run_scoped_cache_retry_worker(
        positive_usize(3)?,
        NativeCacheScopedWorkerResources::new(&mut lifecycle, &mut pacer),
        |_current| {
            called = called.saturating_add(1);
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
        |_cancel| "supervised",
    )
    .map_err(|error| format!("{error:?}"))?;
    if completed.run == Ok(RunStop::LimitReached { completed: 3 })
        && completed.supervisor == "supervised"
        && called == 3
    {
        Ok(())
    } else {
        Err(String::from(
            "joined bounded run lost exact terminal evidence",
        ))
    }
}

#[test]
fn supervisor_cancels_after_first_callback_before_next_turn()
-> Result<(), String> {
    let (mut lifecycle, _initial_pacer) = resources()?;
    let mut pacer = Pacer::new(positive_u64(5_000_000_000)?);
    let (signal, receiver) = mpsc::sync_channel::<()>(0);
    let mut called = 0usize;
    let completed = run_scoped_cache_retry_worker(
        positive_usize(4)?,
        NativeCacheScopedWorkerResources::new(&mut lifecycle, &mut pacer),
        |_current| {
            called = called.saturating_add(1);
            signal.send(()).map_err(|_send| "signal-failed")?;
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
        |cancel| {
            receiver.recv().map_err(|_recv| "no first callback")?;
            cancel.cancel().map_err(|_error| "cancel-failed")
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    if completed.run == Ok(RunStop::Cancelled { completed: 1 })
        && completed.supervisor == Ok(true)
        && called == 1
    {
        Ok(())
    } else {
        Err(String::from(
            "supervisor cancellation allowed next callback",
        ))
    }
}

#[test]
fn failed_worker_callback_retains_exact_typed_failure() -> Result<(), String> {
    let (mut lifecycle, mut pacer) = resources()?;
    let completed = run_scoped_cache_retry_worker(
        positive_usize(3)?,
        NativeCacheScopedWorkerResources::new(&mut lifecycle, &mut pacer),
        |_current| Err::<ControlFlow<&'static str>, _>("activation-failed"),
        |_cancel| (),
    )
    .map_err(|error| format!("{error:?}"))?;
    if completed.run == Err(fallible::
        NativeExecutableCacheLimitsRetryLifecycleRunFailure::Turn {
        completed: 1, error: "activation-failed",
    }) {
        Ok(())
    } else {
        Err(String::from("worker callback failure lost exact evidence"))
    }
}

#[test]
fn worker_runs_on_distinct_host_thread_and_joins() -> Result<(), String> {
    let (mut lifecycle, mut pacer) = resources()?;
    let caller = thread::current().id();
    let finished = run_scoped_cache_retry_worker(
        positive_usize(2)?,
        NativeCacheScopedWorkerResources::new(&mut lifecycle, &mut pacer),
        |_current| {
            Ok::<_, &'static str>(ControlFlow::Break(thread::current().id()))
        },
        |_cancel| thread::current().id(),
    )
    .map_err(|error| format!("{error:?}"))?;
    let Ok(RunStop::CallerStopped {
        completed: 1,
        reason: worker_id,
    }) = finished.run
    else {
        return Err(String::from("joined worker lost typed stop"));
    };
    if worker_id != caller && finished.supervisor == caller {
        Ok(())
    } else {
        Err(String::from("scope did not isolate host worker thread"))
    }
}

#[test]
fn worker_panic_returns_typed_failure_after_join() -> Result<(), String> {
    let (mut lifecycle, mut pacer) = resources()?;
    let result = run_scoped_cache_retry_worker(
        positive_usize(2)?,
        NativeCacheScopedWorkerResources::new(&mut lifecycle, &mut pacer),
        |_current| -> Result<ControlFlow<&'static str>, &'static str> {
            resume_unwind(Box::new("intentional worker panic"));
        },
        |_cancel| "supervisor-returned",
    );
    if matches!(result, Err(NativeCacheScopedWorkerError::WorkerPanicked)) {
        Ok(())
    } else {
        Err(String::from("worker panic fabricated lifecycle completion"))
    }
}

#[test]
fn supervisor_failure_does_not_erase_worker_result() -> Result<(), String> {
    let (mut lifecycle, mut pacer) = resources()?;
    let finished = run_scoped_cache_retry_worker(
        positive_usize(2)?,
        NativeCacheScopedWorkerResources::new(&mut lifecycle, &mut pacer),
        |_current| Ok::<_, &'static str>(ControlFlow::Break("finished")),
        |_cancel| Err::<(), _>("supervisor-failed"),
    )
    .map_err(|error| format!("{error:?}"))?;
    if finished.run
        == Ok(RunStop::CallerStopped {
            completed: 1,
            reason: "finished",
        })
        && finished.supervisor == Err("supervisor-failed")
    {
        Ok(())
    } else {
        Err(String::from("supervisor outcome erased worker evidence"))
    }
}

#[test]
fn cancellation_during_callback_waits_for_completion() -> Result<(), String> {
    let (mut lifecycle, mut pacer) = resources()?;
    let (started_tx, started_rx) = mpsc::sync_channel::<()>(0);
    let (release_tx, release_rx) = mpsc::sync_channel::<()>(0);
    let called = Arc::new(AtomicUsize::new(0));
    let worker_called = Arc::clone(&called);
    let finished = run_scoped_cache_retry_worker(
        positive_usize(3)?,
        NativeCacheScopedWorkerResources::new(&mut lifecycle, &mut pacer),
        move |_current| {
            let _previous = worker_called.fetch_add(1, Ordering::SeqCst);
            started_tx.send(()).map_err(|_error| "signal-failed")?;
            release_rx.recv().map_err(|_error| "release-failed")?;
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
        |cancel| {
            started_rx.recv().map_err(|_error| "not-started")?;
            let first = cancel.cancel().map_err(|_error| "cancel-failed")?;
            release_tx.send(()).map_err(|_error| "release-failed")?;
            Ok::<_, &'static str>(first)
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    if finished.run == Ok(RunStop::Cancelled { completed: 1 })
        && finished.supervisor == Ok(true)
        && called.load(Ordering::SeqCst) == 1
    {
        Ok(())
    } else {
        Err(String::from("cancelled callback fabricated preemption"))
    }
}

#[test]
fn panicking_supervisor_joins_worker_before_unwind() -> Result<(), String> {
    use std::panic::{AssertUnwindSafe, catch_unwind};

    let (mut lifecycle, mut pacer) = resources()?;
    let mut observed = 0usize;
    let limit = positive_usize(3)?;
    let result = catch_unwind(AssertUnwindSafe(|| {
        let _outcome = run_scoped_cache_retry_worker(
            limit,
            NativeCacheScopedWorkerResources::new(&mut lifecycle, &mut pacer),
            |_current| {
                observed = observed.saturating_add(1);
                Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
            },
            |_cancel| resume_unwind(Box::new("intentional supervisor panic")),
        );
    }));
    if result.is_err() && observed == 3 {
        Ok(())
    } else {
        Err(String::from("supervisor panic escaped before worker join"))
    }
}

#[test]
fn cursorless_scope_never_executes_callback() -> Result<(), String> {
    let (mut lifecycle, mut pacer) = resources()?;
    lifecycle.replace_expected_cursor(None);
    let mut called = 0usize;
    let completed = run_scoped_cache_retry_worker(
        positive_usize(3)?,
        NativeCacheScopedWorkerResources::new(&mut lifecycle, &mut pacer),
        |_current| {
            called = called.saturating_add(1);
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
        |_cancel| "supervised",
    )
    .map_err(|error| format!("{error:?}"))?;
    if completed.run == Ok(RunStop::CursorUnavailable { completed: 0 })
        && completed.supervisor == "supervised"
        && called == 0
        && lifecycle.expected_cursor().is_none()
    {
        Ok(())
    } else {
        Err(String::from("scoped worker ran without cursor authority"))
    }
}

#[test]
fn failed_callback_cursor_loss_withholds_later_scoped_invocation()
-> Result<(), String> {
    let (mut lifecycle, mut pacer) = resources()?;
    let first = run_scoped_cache_retry_worker(
        positive_usize(3)?,
        NativeCacheScopedWorkerResources::new(&mut lifecycle, &mut pacer),
        |current| {
            current.replace_expected_cursor(None);
            Err::<ControlFlow<&'static str>, &'static str>("claim-failed")
        },
        |_cancel| (),
    )
    .map_err(|error| format!("{error:?}"))?;
    if first.run != Err(fallible::
        NativeExecutableCacheLimitsRetryLifecycleRunFailure::Turn {
        completed: 1, error: "claim-failed",
    }) {
        return Err(String::from("first failure lost owned cursor evidence"));
    }
    let mut called = 0usize;
    let second = run_scoped_cache_retry_worker(
        positive_usize(3)?,
        NativeCacheScopedWorkerResources::new(&mut lifecycle, &mut pacer),
        |_current| {
            called = called.saturating_add(1);
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
        |_cancel| (),
    )
    .map_err(|error| format!("{error:?}"))?;
    if second.run == Ok(RunStop::CursorUnavailable { completed: 0 })
        && called == 0
    {
        Ok(())
    } else {
        Err(String::from(
            "followup worker ignored lost cursor authority",
        ))
    }
}

#[test]
fn scoped_cancellation_does_not_poison_next_run() -> Result<(), String> {
    let (mut lifecycle, mut pacer) = resources()?;
    let (started_tx, started_rx) = mpsc::sync_channel::<()>(0);
    let (release_tx, release_rx) = mpsc::sync_channel::<()>(0);
    let first = run_scoped_cache_retry_worker(
        positive_usize(3)?,
        NativeCacheScopedWorkerResources::new(&mut lifecycle, &mut pacer),
        move |_current| {
            started_tx.send(()).map_err(|_error| "start-failed")?;
            release_rx.recv().map_err(|_error| "release-failed")?;
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
        |cancel| {
            started_rx.recv().map_err(|_error| "start-failed")?;
            let new = cancel.cancel().map_err(|_error| "cancel-failed")?;
            release_tx.send(()).map_err(|_error| "release-failed")?;
            Ok::<_, &'static str>(new)
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    if first.run != Ok(RunStop::Cancelled { completed: 1 })
        || first.supervisor != Ok(true)
    {
        return Err(String::from("first scope failed to cancel exactly"));
    }
    let second = run_scoped_cache_retry_worker(
        positive_usize(2)?,
        NativeCacheScopedWorkerResources::new(&mut lifecycle, &mut pacer),
        |_current| Ok::<_, &'static str>(ControlFlow::Break("resume")),
        |_cancel| "second-supervisor",
    )
    .map_err(|error| format!("{error:?}"))?;
    if second.run
        == Ok(RunStop::CallerStopped {
            completed: 1,
            reason: "resume",
        })
        && second.supervisor == "second-supervisor"
    {
        Ok(())
    } else {
        Err(String::from("sticky cancellation crossed worker scopes"))
    }
}
