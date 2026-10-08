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
//   - Owned finite worker join, cancellation, and fail-closed panic
//     regressions.
// - Must-Not:
//   - Rely on timing sleeps, spawn detached threads, or invent durable cursor
//     authority after callback panic.
// - Allows:
//   - Inputs: test-owned retry lifecycle/pacer and typed callback fixtures.
//   - Outputs: exact finite run, lifecycle recovery, and observed join
//     behavior.
//   - Side effects: test-local synchronized threads, always explicitly joined.
// - Split-When:
//   - Durable worker queue acceptance needs a separate test owner.
// - Merge-When:
//   - Product scheduler tests subsume this owned worker boundary.
// - Summary:
//   - Proves owned worker handles cannot silently detach finite retry work.
// - Description:
//   - Cancellation uses synchronization channels rather than wall-clock races.
// - Usage:
//   - Rust test-only owned worker lifecycle fixtures.
// - Defaults:
//   - Independent process-local resources and fresh cancellation per test.
//

//! Owned finite host-worker lifecycle and shutdown regressions.

use std::num::NonZeroU64;
use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};

use super::*;
use crate::{
    executable_cache_limits_retry_policy as policy,
    executable_cache_limits_retry_run_fallible as failed,
    executable_cache_limits_trigger_cadence as cadence,
};

type RunStop<Reason> =
    run::NativeExecutableCacheLimitsRetryLifecycleRunStop<Reason>;

fn positive(value: usize) -> Result<NonZeroUsize, String> {
    NonZeroUsize::new(value).ok_or_else(|| String::from("zero turns"))
}

fn nanos(value: u64) -> Result<NonZeroU64, String> {
    NonZeroU64::new(value).ok_or_else(|| String::from("zero nanoseconds"))
}

fn resources() -> Result<NativeCacheOwnedWorkerResources, String> {
    let cursor = cadence::NativeExecutableCacheLimitsTriggerCadence::new(
        nanos(1)?,
        nanos(2)?,
    );
    Ok(NativeCacheOwnedWorkerResources::new(
        RetryLifecycle::new_with_cursor(
            cursor, positive(15)?, positive(2)?,
            policy::NativeExecutableCacheLimitsRetryConflictPolicy::
                return_on_contention(),
        ),
        Pacer::new(nanos(1)?),
    ))
}

#[test]
fn owned_worker_joins_at_exact_finite_limit() -> Result<(), String> {
    let handle = start_owned_cache_retry_worker(
        positive(3)?,
        resources()?,
        |_current| {
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
    )
    .map_err(|_failure| String::from("worker startup failed"))?;
    let finished = handle.join().map_err(|error| format!("{error:?}"))?;
    if matches!(
        finished.terminal,
        NativeCacheOwnedWorkerTerminal::Returned(Ok(RunStop::LimitReached {
            completed: 3
        }))
    ) && finished.resources.lifecycle.expected_cursor().is_some()
    {
        Ok(())
    } else {
        Err(String::from("joined owned worker changed retry authority"))
    }
}

#[test]
fn owned_worker_cancel_prevents_next_paced_callback() -> Result<(), String> {
    let mut state = resources()?;
    state.pacer = Pacer::new(nanos(5_000_000_000)?);
    let (signal, recv) = mpsc::sync_channel::<()>(0);
    let callbacks = Arc::new(AtomicUsize::new(0));
    let counted = Arc::clone(&callbacks);
    let handle =
        start_owned_cache_retry_worker(positive(4)?, state, move |_current| {
            let _previous = counted.fetch_add(1, Ordering::SeqCst);
            signal.send(()).map_err(|_error| "signal failed")?;
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        })
        .map_err(|_failure| String::from("worker startup failed"))?;
    recv.recv()
        .map_err(|_error| String::from("first callback missing"))?;
    let first = handle.cancel().map_err(|error| format!("{error:?}"))?;
    let repeated = handle.cancel().map_err(|error| format!("{error:?}"))?;
    let finished = handle.join().map_err(|error| format!("{error:?}"))?;
    if first
        && !repeated
        && matches!(
            finished.terminal,
            NativeCacheOwnedWorkerTerminal::Returned(Ok(RunStop::Cancelled {
                completed: 1
            }))
        )
        && callbacks.load(Ordering::SeqCst) == 1
    {
        Ok(())
    } else {
        Err(String::from(
            "owned worker cancellation allowed extra callback",
        ))
    }
}

#[test]
fn dropping_handle_cancels_and_joins_before_return() -> Result<(), String> {
    let mut state = resources()?;
    state.pacer = Pacer::new(nanos(5_000_000_000)?);
    let (signal, recv) = mpsc::sync_channel::<()>(0);
    let callbacks = Arc::new(AtomicUsize::new(0));
    let counted = Arc::clone(&callbacks);
    let handle =
        start_owned_cache_retry_worker(positive(4)?, state, move |_current| {
            let _previous = counted.fetch_add(1, Ordering::SeqCst);
            signal.send(()).map_err(|_error| "signal failed")?;
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        })
        .map_err(|_failure| String::from("worker startup failed"))?;
    recv.recv()
        .map_err(|_error| String::from("first callback missing"))?;
    drop(handle);
    if callbacks.load(Ordering::SeqCst) == 1 {
        Ok(())
    } else {
        Err(String::from("dropping joinable handle leaked work"))
    }
}

#[test]
fn owned_worker_retains_typed_callback_failure() -> Result<(), String> {
    let handle = start_owned_cache_retry_worker(
        positive(3)?,
        resources()?,
        |_current| Err::<ControlFlow<&'static str>, _>("activation failed"),
    )
    .map_err(|_failure| String::from("worker startup failed"))?;
    let finished = handle.join().map_err(|error| format!("{error:?}"))?;
    if matches!(
        finished.terminal,
        NativeCacheOwnedWorkerTerminal::Returned(Err(
            failed::NativeExecutableCacheLimitsRetryLifecycleRunFailure::Turn {
                completed: 1,
                error: "activation failed",
            }
        ))
    ) && finished.resources.lifecycle.expected_cursor().is_some()
    {
        Ok(())
    } else {
        Err(String::from("returned failure erased exact turn evidence"))
    }
}

#[test]
fn callback_panic_revokes_cursor_but_recovers_owned_resources()
-> Result<(), String> {
    use std::panic::resume_unwind;

    let handle = start_owned_cache_retry_worker(
        positive(3)?,
        resources()?,
        |current| -> Result<ControlFlow<&'static str>, &'static str> {
            let forged =
                cadence::NativeExecutableCacheLimitsTriggerCadence::new(
                    nanos(20).map_err(|_error| "invalid duration")?,
                    nanos(21).map_err(|_error| "invalid duration")?,
                );
            current.replace_expected_cursor(Some(forged));
            resume_unwind(Box::new("callback panic"));
        },
    )
    .map_err(|_failure| String::from("worker startup failed"))?;
    let finished = handle.join().map_err(|error| format!("{error:?}"))?;
    if matches!(
        finished.terminal,
        NativeCacheOwnedWorkerTerminal::WorkerPanicked
    ) && finished.resources.lifecycle.expected_cursor().is_none()
    {
        Ok(())
    } else {
        Err(String::from(
            "panic permitted cursor reuse or lost resources",
        ))
    }
}

#[test]
fn cursorless_owned_worker_runs_no_callback() -> Result<(), String> {
    let mut state = resources()?;
    state.lifecycle.replace_expected_cursor(None);
    let callbacks = Arc::new(AtomicUsize::new(0));
    let counted = Arc::clone(&callbacks);
    let handle =
        start_owned_cache_retry_worker(positive(3)?, state, move |_current| {
            let _previous = counted.fetch_add(1, Ordering::SeqCst);
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        })
        .map_err(|_failure| String::from("worker startup failed"))?;
    let finished = handle.join().map_err(|error| format!("{error:?}"))?;
    if matches!(
        finished.terminal,
        NativeCacheOwnedWorkerTerminal::Returned(Ok(
            RunStop::CursorUnavailable { completed: 0 }
        ))
    ) && callbacks.load(Ordering::SeqCst) == 0
    {
        Ok(())
    } else {
        Err(String::from("missing cursor admitted callback"))
    }
}

#[test]
fn independent_owned_worker_invocations_do_not_share_stop_state()
-> Result<(), String> {
    let first = start_owned_cache_retry_worker(
        positive(1)?,
        resources()?,
        |_current| {
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
    )
    .map_err(|_failure| String::from("first startup failed"))?;
    let previous = first.join().map_err(|error| format!("{error:?}"))?;
    let second = start_owned_cache_retry_worker(
        positive(1)?,
        previous.resources,
        |_current| Ok::<_, &'static str>(ControlFlow::Break("second joined")),
    )
    .map_err(|_failure| String::from("second startup failed"))?;
    let finished = second.join().map_err(|error| format!("{error:?}"))?;
    if matches!(
        finished.terminal,
        NativeCacheOwnedWorkerTerminal::Returned(Ok(RunStop::CallerStopped {
            completed: 1,
            reason: "second joined"
        }))
    ) {
        Ok(())
    } else {
        Err(String::from("owned worker reused prior cancellation scope"))
    }
}

#[test]
fn owned_handle_can_be_joined_from_separate_supervisor_thread()
-> Result<(), String> {
    let caller = thread::current().id();
    let handle = start_owned_cache_retry_worker(
        positive(2)?,
        resources()?,
        |_current| {
            Ok::<_, &'static str>(ControlFlow::Break(thread::current().id()))
        },
    )
    .map_err(|_failure| String::from("startup failed"))?;
    let (supervisor, joined) =
        thread::spawn(move || (thread::current().id(), handle.join()))
            .join()
            .map_err(|_panic| String::from("supervisor panicked"))?;
    let finished = joined.map_err(|error| format!("{error:?}"))?;
    let NativeCacheOwnedWorkerTerminal::Returned(Ok(RunStop::CallerStopped {
        completed: 1,
        reason: worker_id,
    })) = finished.terminal
    else {
        return Err(String::from("worker did not return typed joined stop"));
    };
    if supervisor != caller && worker_id != supervisor && worker_id != caller {
        Ok(())
    } else {
        Err(String::from("owned work escaped host thread isolation"))
    }
}

#[test]
fn handle_reports_not_finished_while_callback_is_in_flight()
-> Result<(), String> {
    let (started_tx, started_rx) = mpsc::sync_channel::<()>(0);
    let (release_tx, release_rx) = mpsc::sync_channel::<()>(0);
    let handle = start_owned_cache_retry_worker(
        positive(1)?,
        resources()?,
        move |_current| {
            started_tx.send(()).map_err(|_error| "started failed")?;
            release_rx.recv().map_err(|_error| "release failed")?;
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
    )
    .map_err(|_failure| String::from("startup failed"))?;
    started_rx
        .recv()
        .map_err(|_error| String::from("no callback"))?;
    let still_running = !handle.is_finished();
    release_tx
        .send(())
        .map_err(|_error| String::from("no release"))?;
    let finished = handle.join().map_err(|error| format!("{error:?}"))?;
    if still_running
        && matches!(
            finished.terminal,
            NativeCacheOwnedWorkerTerminal::Returned(Ok(
                RunStop::LimitReached { completed: 1 }
            ))
        )
    {
        Ok(())
    } else {
        Err(String::from("poll fabricated early terminal evidence"))
    }
}

#[test]
fn dropped_handle_waits_for_running_callback_before_shutdown()
-> Result<(), String> {
    let (started_tx, started_rx) = mpsc::sync_channel::<()>(0);
    let (release_tx, release_rx) = mpsc::sync_channel::<()>(0);
    let (drop_started_tx, drop_started_rx) =
        mpsc::sync_channel::<Result<bool, WaitError>>(0);
    let (drop_completed_tx, drop_completed_rx) = mpsc::channel::<()>();
    let callbacks = Arc::new(AtomicUsize::new(0));
    let counted = Arc::clone(&callbacks);
    let handle = start_owned_cache_retry_worker(
        positive(3)?,
        resources()?,
        move |_current| {
            let _previous = counted.fetch_add(1, Ordering::SeqCst);
            started_tx.send(()).map_err(|_error| "started failed")?;
            release_rx.recv().map_err(|_error| "release failed")?;
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
    )
    .map_err(|_failure| String::from("startup failed"))?;
    started_rx
        .recv()
        .map_err(|_error| String::from("no callback"))?;
    let dropper = thread::spawn(move || {
        // Stop is sequenced before releasing the executing callback.
        let requested = handle.cancel();
        let _started = drop_started_tx.send(requested);
        drop(handle);
        let _completed = drop_completed_tx.send(());
    });
    let stopped = drop_started_rx
        .recv()
        .map_err(|_error| String::from("no dropper"))?;
    let premature = drop_completed_rx.try_recv();
    release_tx
        .send(())
        .map_err(|_error| String::from("no release"))?;
    dropper
        .join()
        .map_err(|_panic| String::from("dropper panicked"))?;
    if stopped == Ok(true)
        && premature == Err(mpsc::TryRecvError::Empty)
        && drop_completed_rx.recv().is_ok()
        && callbacks.load(Ordering::SeqCst) == 1
    {
        Ok(())
    } else {
        Err(String::from("dropping handle failed to join finite work"))
    }
}

#[test]
fn recovered_panicking_worker_cannot_retry_without_trusted_cursor()
-> Result<(), String> {
    use std::panic::resume_unwind;

    let first = start_owned_cache_retry_worker(
        positive(3)?,
        resources()?,
        |current| -> Result<ControlFlow<&'static str>, &'static str> {
            let forged =
                cadence::NativeExecutableCacheLimitsTriggerCadence::new(
                    nanos(30).map_err(|_error| "invalid duration")?,
                    nanos(31).map_err(|_error| "invalid duration")?,
                );
            current.replace_expected_cursor(Some(forged));
            resume_unwind(Box::new("untrusted callback panic"));
        },
    )
    .map_err(|_failure| String::from("first startup failed"))?;
    let prior = first.join().map_err(|error| format!("{error:?}"))?;
    if !matches!(
        prior.terminal,
        NativeCacheOwnedWorkerTerminal::WorkerPanicked
    ) || prior.resources.lifecycle.expected_cursor().is_some()
    {
        return Err(String::from("panic did not revoke forged cursor"));
    }
    let callbacks = Arc::new(AtomicUsize::new(0));
    let counted = Arc::clone(&callbacks);
    let second = start_owned_cache_retry_worker(
        positive(2)?,
        prior.resources,
        move |_current| {
            let _previous = counted.fetch_add(1, Ordering::SeqCst);
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
    )
    .map_err(|_failure| String::from("second startup failed"))?;
    let recovered = second.join().map_err(|error| format!("{error:?}"))?;
    if matches!(
        recovered.terminal,
        NativeCacheOwnedWorkerTerminal::Returned(Ok(
            RunStop::CursorUnavailable { completed: 0 }
        ))
    ) && callbacks.load(Ordering::SeqCst) == 0
    {
        Ok(())
    } else {
        Err(String::from(
            "recovered owned state bypassed missing cursor",
        ))
    }
}

#[test]
fn cancel_and_join_preserves_first_stop_and_exact_completion()
-> Result<(), String> {
    let mut state = resources()?;
    state.pacer = Pacer::new(nanos(5_000_000_000)?);
    let (signal, receiver) = mpsc::sync_channel::<()>(0);
    let callbacks = Arc::new(AtomicUsize::new(0));
    let counted = Arc::clone(&callbacks);
    let handle =
        start_owned_cache_retry_worker(positive(4)?, state, move |_current| {
            let _previous = counted.fetch_add(1, Ordering::SeqCst);
            signal.send(()).map_err(|_error| "signal failed")?;
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        })
        .map_err(|_failure| String::from("startup failed"))?;
    receiver
        .recv()
        .map_err(|_error| String::from("no callback"))?;
    let shutdown = handle.cancel_and_join();
    let finished = shutdown.joined.map_err(|error| format!("{error:?}"))?;
    if shutdown.cancellation == Ok(true)
        && matches!(
            finished.terminal,
            NativeCacheOwnedWorkerTerminal::Returned(Ok(RunStop::Cancelled {
                completed: 1
            }))
        )
        && finished.resources.lifecycle.expected_cursor().is_some()
        && callbacks.load(Ordering::SeqCst) == 1
    {
        Ok(())
    } else {
        Err(String::from("first stop lost exact joined evidence"))
    }
}

#[test]
fn repeated_stop_and_join_retains_both_outcomes() -> Result<(), String> {
    let mut state = resources()?;
    state.pacer = Pacer::new(nanos(5_000_000_000)?);
    let (signal, receiver) = mpsc::sync_channel::<()>(0);
    let handle =
        start_owned_cache_retry_worker(positive(4)?, state, move |_current| {
            signal.send(()).map_err(|_error| "signal failed")?;
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        })
        .map_err(|_failure| String::from("startup failed"))?;
    receiver
        .recv()
        .map_err(|_error| String::from("no callback"))?;
    let original = handle.cancel().map_err(|error| format!("{error:?}"))?;
    let shutdown = handle.cancel_and_join();
    let finished = shutdown.joined.map_err(|error| format!("{error:?}"))?;
    if original
        && shutdown.cancellation == Ok(false)
        && matches!(
            finished.terminal,
            NativeCacheOwnedWorkerTerminal::Returned(Ok(RunStop::Cancelled {
                completed: 1
            }))
        )
        && finished.resources.lifecycle.expected_cursor().is_some()
    {
        Ok(())
    } else {
        Err(String::from(
            "repeated stop changed worker terminal evidence",
        ))
    }
}

#[test]
fn shutdown_retains_callback_error() -> Result<(), String> {
    type Failure<Wait, Turn> =
        failed::NativeExecutableCacheLimitsRetryLifecycleRunFailure<Wait, Turn>;

    let (signal, receiver) = mpsc::sync_channel::<()>(0);
    let handle = start_owned_cache_retry_worker(
        positive(4)?,
        resources()?,
        move |_current| {
            signal.send(()).map_err(|_error| "signal failed")?;
            Err::<ControlFlow<&'static str>, _>("original turn failure")
        },
    )
    .map_err(|_failure| String::from("startup failed"))?;
    receiver
        .recv()
        .map_err(|_error| String::from("no callback"))?;
    let shutdown = handle.cancel_and_join();
    let finished = shutdown.joined.map_err(|error| format!("{error:?}"))?;
    if shutdown.cancellation == Ok(true)
        && matches!(
            finished.terminal,
            NativeCacheOwnedWorkerTerminal::Returned(Err(Failure::Turn {
                completed: 1,
                error: "original turn failure",
            }))
        )
        && finished.resources.lifecycle.expected_cursor().is_some()
    {
        Ok(())
    } else {
        Err(String::from("shutdown erased completed callback failure"))
    }
}

#[test]
fn cancel_and_join_retains_worker_panic_and_revokes_cursor()
-> Result<(), String> {
    use std::panic::resume_unwind;

    let (signal, receiver) = mpsc::sync_channel::<()>(0);
    let handle = start_owned_cache_retry_worker(
        positive(3)?,
        resources()?,
        move |current| -> Result<ControlFlow<&'static str>, &'static str> {
            signal.send(()).map_err(|_error| "signal failed")?;
            let forged =
                cadence::NativeExecutableCacheLimitsTriggerCadence::new(
                    nanos(48).map_err(|_error| "invalid duration")?,
                    nanos(49).map_err(|_error| "invalid duration")?,
                );
            current.replace_expected_cursor(Some(forged));
            resume_unwind(Box::new("worker panic after signal"));
        },
    )
    .map_err(|_failure| String::from("startup failed"))?;
    receiver
        .recv()
        .map_err(|_error| String::from("no callback"))?;
    let shutdown = handle.cancel_and_join();
    let finished = shutdown.joined.map_err(|error| format!("{error:?}"))?;
    if shutdown.cancellation == Ok(true)
        && matches!(
            finished.terminal,
            NativeCacheOwnedWorkerTerminal::WorkerPanicked
        )
        && finished.resources.lifecycle.expected_cursor().is_none()
    {
        Ok(())
    } else {
        Err(String::from(
            "shutdown masked panic or trusted forged cursor",
        ))
    }
}
