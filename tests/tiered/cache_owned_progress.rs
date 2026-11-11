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
//   - Owned finite worker progress admission, cancellation, and panic tests.
// - Must-Not:
//   - Trust advisory notices as cursor state, detach workers, or use sleeps to
//     determine cross-thread callback order.
// - Allows:
//   - Inputs: local bounded progress limits and finite owned retry resources.
//   - Outputs: exact notice gaps, post-join totals, typed work results.
//   - Side effects: handshake-controlled host threads, joined before return.
// - Split-When:
//   - Durable progress authority requires independent integration evidence.
// - Merge-When:
//   - One product scheduler owns finite progress admission and completions.
// - Summary:
//   - Proves nonblocking owned progress cannot change worker terminal truth.
// - Description:
//   - Capacity saturation, observer abandonment, and callback panic retain
//     exact independent worker and transport evidence.
// - Usage:
//   - Test-only finite cross-thread owned worker fixtures.
// - Defaults:
//   - Fresh retry state and cancellation for every test.
//

//! Joinable owned cache worker progress observation tests.

use std::num::{NonZeroU64, NonZeroUsize};
use std::panic::resume_unwind;
use std::thread;

use super::*;
use crate::{
    executable_cache_limits_retry_pacing as pacing,
    executable_cache_limits_retry_policy as policy,
    executable_cache_limits_retry_run as run,
    executable_cache_limits_retry_run_fallible as fallible,
    executable_cache_limits_trigger_cadence as cadence,
};

type RunStop<Reason> =
    run::NativeExecutableCacheLimitsRetryLifecycleRunStop<Reason>;
type RunFailure<Wait, Turn> =
    fallible::NativeExecutableCacheLimitsRetryLifecycleRunFailure<Wait, Turn>;

struct PanicOnDrop;

impl Drop for PanicOnDrop {
    fn drop(&mut self) {
        resume_unwind(Box::new("observed callback cleanup panic"));
    }
}

type PendingStop<Reason, TurnError> = Result<
    (
        Result<bool, WaitError>,
        NativeCacheOwnedProgressHandle<Reason, TurnError>,
    ),
    String,
>;

fn expect_pending_stop<Reason, TurnError>(
    outcome: NativeCacheOwnedProgressTryShutdown<Reason, TurnError>,
) -> PendingStop<Reason, TurnError> {
    match outcome {
        NativeCacheOwnedProgressTryShutdown::Pending {
            cancellation,
            worker,
        } => Ok((cancellation, worker)),
        NativeCacheOwnedProgressTryShutdown::Joined(_joined) => {
            Err(String::from("in-flight worker returned joined"))
        },
    }
}

fn positive(value: usize) -> Result<NonZeroUsize, String> {
    NonZeroUsize::new(value).ok_or_else(|| String::from("zero limit"))
}

fn nanos(value: u64) -> Result<NonZeroU64, String> {
    NonZeroU64::new(value).ok_or_else(|| String::from("zero duration"))
}

fn resources() -> Result<owned::NativeCacheOwnedWorkerResources, String> {
    let trigger = cadence::NativeExecutableCacheLimitsTriggerCadence::new(
        nanos(1)?,
        nanos(2)?,
    );
    Ok(owned::NativeCacheOwnedWorkerResources::new(
        RetryLifecycle::new_with_cursor(
            trigger, positive(12)?, positive(3)?,
            policy::NativeExecutableCacheLimitsRetryConflictPolicy::
                return_on_contention(),
        ),
        pacing::NativeExecutableCacheLimitsRetryLifecyclePacer::new(nanos(1)?),
    ))
}

fn limits(capacity: usize, turns: usize) -> Result<Limits, String> {
    Ok(Limits::new(positive(capacity)?, positive(turns)?))
}

#[test]
fn owned_progress_keeps_ordered_notices_and_typed_limit() -> Result<(), String>
{
    let handle = start_owned_cache_retry_worker_with_bounded_progress(
        limits(3, 3)?,
        resources()?,
        |_current| {
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
    )
    .map_err(|_failure| String::from("startup failed"))?;
    let observations = handle
        .progress()
        .ok_or("receiver missing")?
        .iter()
        .collect::<Vec<_>>();
    let result = handle.join();
    let joined = result.joined.map_err(|error| format!("{error:?}"))?;
    if matches!(
        joined.terminal,
        owned::NativeCacheOwnedWorkerTerminal::Returned(Ok(
            RunStop::LimitReached { completed: 3 }
        ))
    ) && observations
        == vec![
            Notice {
                completed: 1,
                kind: Kind::Continued,
            },
            Notice {
                completed: 2,
                kind: Kind::Continued,
            },
            Notice {
                completed: 3,
                kind: Kind::Continued,
            },
        ]
        && result.totals
            == (Totals {
                enqueued: 3,
                full: 0,
                receiver_gone: 0,
            })
        && joined.resources.lifecycle.expected_cursor().is_some()
    {
        Ok(())
    } else {
        Err(String::from("ordered progress changed exact typed limit"))
    }
}

#[test]
fn owned_full_queue_preserves_finite_callbacks() -> Result<(), String> {
    let mut called = 0usize;
    let handle = start_owned_cache_retry_worker_with_bounded_progress(
        limits(1, 20)?,
        resources()?,
        move |_current| {
            called = called.saturating_add(1);
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
    )
    .map_err(|_failure| String::from("startup failed"))?;
    let result = handle.join();
    let joined = result.joined.map_err(|error| format!("{error:?}"))?;
    if matches!(
        joined.terminal,
        owned::NativeCacheOwnedWorkerTerminal::Returned(Ok(
            RunStop::LimitReached { completed: 20 }
        ))
    ) && result.totals
        == (Totals {
            enqueued: 1,
            full: 19,
            receiver_gone: 0,
        })
    {
        Ok(())
    } else {
        Err(String::from("full owned queue blocked or lost work"))
    }
}

#[test]
fn owned_receiver_abandonment_retains_exact_lost_notice() -> Result<(), String>
{
    let (release_tx, release_rx) = mpsc::sync_channel::<()>(0);
    let mut called = 0usize;
    let mut handle = start_owned_cache_retry_worker_with_bounded_progress(
        limits(1, 2)?,
        resources()?,
        move |_current| {
            called = called.saturating_add(1);
            if called == 2 {
                release_rx.recv().map_err(|_error| "release missing")?;
            }
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
    )
    .map_err(|_failure| String::from("startup failed"))?;
    let receiver = handle.take_progress_receiver().ok_or("receiver missing")?;
    let first = receiver
        .recv()
        .map_err(|_error| String::from("no first notice"))?;
    drop(receiver);
    release_tx
        .send(())
        .map_err(|_error| String::from("cannot release"))?;
    let result = handle.join();
    let joined = result.joined.map_err(|error| format!("{error:?}"))?;
    if first
        == (Notice {
            completed: 1,
            kind: Kind::Continued,
        })
        && matches!(
            joined.terminal,
            owned::NativeCacheOwnedWorkerTerminal::Returned(Ok(
                RunStop::LimitReached { completed: 2 }
            ))
        )
        && result.totals
            == (Totals {
                enqueued: 1,
                full: 0,
                receiver_gone: 1,
            })
    {
        Ok(())
    } else {
        Err(String::from("receiver abandonment changed owned outcome"))
    }
}

#[test]
fn owned_notice_supervisor_cancels_before_second_turn() -> Result<(), String> {
    let mut state = resources()?;
    state.pacer = pacing::NativeExecutableCacheLimitsRetryLifecyclePacer::new(
        nanos(5_000_000_000)?,
    );
    let calls = Arc::new(AtomicUsize::new(0));
    let counted = Arc::clone(&calls);
    let handle = start_owned_cache_retry_worker_with_bounded_progress(
        limits(1, 4)?,
        state,
        move |_current| {
            let _previous = counted.fetch_add(1, Ordering::SeqCst);
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
    )
    .map_err(|_failure| String::from("startup failed"))?;
    let first = handle
        .progress()
        .ok_or("receiver missing")?
        .recv()
        .map_err(|_error| String::from("first notice missing"))?;
    let shutdown = handle.cancel_and_join();
    let joined = shutdown
        .shutdown
        .joined
        .map_err(|error| format!("{error:?}"))?;
    if first
        == (Notice {
            completed: 1,
            kind: Kind::Continued,
        })
        && shutdown.shutdown.cancellation == Ok(true)
        && matches!(
            joined.terminal,
            owned::NativeCacheOwnedWorkerTerminal::Returned(Ok(
                RunStop::Cancelled { completed: 1 }
            ))
        )
        && shutdown.totals
            == (Totals {
                enqueued: 1,
                full: 0,
                receiver_gone: 0,
            })
        && calls.load(Ordering::SeqCst) == 1
    {
        Ok(())
    } else {
        Err(String::from("progress-aware stop admitted another turn"))
    }
}

#[test]
fn owned_progress_keeps_private_callback_failure() -> Result<(), String> {
    let handle = start_owned_cache_retry_worker_with_bounded_progress(
        limits(1, 3)?,
        resources()?,
        |_current| Err::<ControlFlow<&'static str>, _>("activation failed"),
    )
    .map_err(|_failure| String::from("startup failed"))?;
    let notice = handle
        .progress()
        .ok_or("receiver missing")?
        .recv()
        .map_err(|_error| String::from("error notice missing"))?;
    let result = handle.join();
    let joined = result.joined.map_err(|error| format!("{error:?}"))?;
    if notice
        == (Notice {
            completed: 1,
            kind: Kind::Failed,
        })
        && matches!(
            joined.terminal,
            owned::NativeCacheOwnedWorkerTerminal::Returned(Err(
                RunFailure::Turn {
                    completed: 1,
                    error: "activation failed"
                }
            ))
        )
        && result.totals
            == (Totals {
                enqueued: 1,
                full: 0,
                receiver_gone: 0,
            })
        && joined.resources.lifecycle.expected_cursor().is_some()
    {
        Ok(())
    } else {
        Err(String::from("progress lost exact activation failure"))
    }
}

#[test]
fn owned_progress_cursorless_run_emits_zero_notices() -> Result<(), String> {
    let mut state = resources()?;
    state.lifecycle.replace_expected_cursor(None);
    let handle = start_owned_cache_retry_worker_with_bounded_progress(
        limits(1, 4)?,
        state,
        |_current| {
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
    )
    .map_err(|_failure| String::from("startup failed"))?;
    let disconnected =
        handle.progress().ok_or("receiver missing")?.recv().is_err();
    let result = handle.join();
    let joined = result.joined.map_err(|error| format!("{error:?}"))?;
    if disconnected
        && matches!(
            joined.terminal,
            owned::NativeCacheOwnedWorkerTerminal::Returned(Ok(
                RunStop::CursorUnavailable { completed: 0 }
            ))
        )
        && result.totals == Totals::default()
    {
        Ok(())
    } else {
        Err(String::from("cursorless worker fabricated progress"))
    }
}

#[test]
fn owned_callback_panic_emits_no_false_completion() -> Result<(), String> {
    let handle = start_owned_cache_retry_worker_with_bounded_progress(
        limits(1, 4)?,
        resources()?,
        |_current| -> Result<ControlFlow<&'static str>, &'static str> {
            resume_unwind(Box::new("callback panic"));
        },
    )
    .map_err(|_failure| String::from("startup failed"))?;
    let disconnected =
        handle.progress().ok_or("receiver missing")?.recv().is_err();
    let result = handle.join();
    let joined = result.joined.map_err(|error| format!("{error:?}"))?;
    if disconnected
        && matches!(
            joined.terminal,
            owned::NativeCacheOwnedWorkerTerminal::WorkerPanicked
        )
        && joined.resources.lifecycle.expected_cursor().is_none()
        && result.totals == Totals::default()
    {
        Ok(())
    } else {
        Err(String::from("panic invented progress or cursor authority"))
    }
}

#[test]
fn owned_callback_destructor_panic_still_returns_progress_totals()
-> Result<(), String> {
    let destructor = PanicOnDrop;
    let handle = start_owned_cache_retry_worker_with_bounded_progress(
        limits(1, 1)?,
        resources()?,
        move |_current| {
            let _hold = &destructor;
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
    )
    .map_err(|_failure| String::from("startup failed"))?;
    let notice = handle
        .progress()
        .ok_or("receiver missing")?
        .recv()
        .map_err(|_error| String::from("notice missing"))?;
    let result = handle.join();
    let joined = result.joined.map_err(|error| format!("{error:?}"))?;
    if notice
        == (Notice {
            completed: 1,
            kind: Kind::Continued,
        })
        && matches!(
            joined.terminal,
            owned::NativeCacheOwnedWorkerTerminal::WorkerPanicked
        )
        && joined.resources.lifecycle.expected_cursor().is_none()
        && result.totals
            == (Totals {
                enqueued: 1,
                full: 0,
                receiver_gone: 0,
            })
    {
        Ok(())
    } else {
        Err(String::from(
            "destructor panic kept untrusted cursor authority",
        ))
    }
}

#[test]
fn partial_progress_before_worker_panic_never_authorizes_retry()
-> Result<(), String> {
    let mut called = 0usize;
    let handle = start_owned_cache_retry_worker_with_bounded_progress(
        limits(2, 3)?,
        resources()?,
        move |_current| {
            called = called.saturating_add(1);
            if called == 2 {
                resume_unwind(Box::new("second callback panic"));
            }
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
    )
    .map_err(|_failure| String::from("startup failed"))?;
    let observations = handle
        .progress()
        .ok_or("receiver missing")?
        .iter()
        .collect::<Vec<_>>();
    let result = handle.join();
    let joined = result.joined.map_err(|error| format!("{error:?}"))?;
    if observations
        == vec![Notice {
            completed: 1,
            kind: Kind::Continued,
        }]
        && matches!(
            joined.terminal,
            owned::NativeCacheOwnedWorkerTerminal::WorkerPanicked
        )
        && joined.resources.lifecycle.expected_cursor().is_none()
        && result.totals
            == (Totals {
                enqueued: 1,
                full: 0,
                receiver_gone: 0,
            })
    {
        Ok(())
    } else {
        Err(String::from("partial progress invented terminal success"))
    }
}

#[test]
fn dropped_receiver_before_callback_return_counts_every_notice()
-> Result<(), String> {
    let (started_tx, started_rx) = mpsc::sync_channel::<()>(0);
    let (release_tx, release_rx) = mpsc::sync_channel::<()>(0);
    let mut called = 0usize;
    let mut handle = start_owned_cache_retry_worker_with_bounded_progress(
        limits(2, 3)?,
        resources()?,
        move |_current| {
            called = called.saturating_add(1);
            if called == 1 {
                started_tx.send(()).map_err(|_error| "entry closed")?;
                release_rx.recv().map_err(|_error| "release closed")?;
            }
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
    )
    .map_err(|_failure| String::from("startup failed"))?;
    started_rx
        .recv()
        .map_err(|_error| String::from("no callback"))?;
    let receiver = handle.take_progress_receiver().ok_or("receiver missing")?;
    drop(receiver);
    release_tx
        .send(())
        .map_err(|_error| String::from("cannot release"))?;
    let result = handle.join();
    let joined = result.joined.map_err(|error| format!("{error:?}"))?;
    if matches!(
        joined.terminal,
        owned::NativeCacheOwnedWorkerTerminal::Returned(Ok(
            RunStop::LimitReached { completed: 3 }
        ))
    ) && result.totals
        == (Totals {
            enqueued: 0,
            full: 0,
            receiver_gone: 3,
        })
    {
        Ok(())
    } else {
        Err(String::from("abandoned receiver altered worker execution"))
    }
}

#[test]
fn dropping_owned_progress_handle_still_joins_finite_worker()
-> Result<(), String> {
    let mut state = resources()?;
    state.pacer = pacing::NativeExecutableCacheLimitsRetryLifecyclePacer::new(
        nanos(5_000_000_000)?,
    );
    let calls = Arc::new(AtomicUsize::new(0));
    let counted = Arc::clone(&calls);
    let handle = start_owned_cache_retry_worker_with_bounded_progress(
        limits(1, 4)?,
        state,
        move |_current| {
            let _previous = counted.fetch_add(1, Ordering::SeqCst);
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
    )
    .map_err(|_failure| String::from("startup failed"))?;
    let first = handle
        .progress()
        .ok_or("receiver missing")?
        .recv()
        .map_err(|_error| String::from("notice missing"))?;
    drop(handle);
    if first
        == (Notice {
            completed: 1,
            kind: Kind::Continued,
        })
        && calls.load(Ordering::SeqCst) == 1
    {
        Ok(())
    } else {
        Err(String::from("dropping progress owner detached its worker"))
    }
}

#[test]
fn returned_notice_cannot_override_revoked_cursor() -> Result<(), String> {
    let handle = start_owned_cache_retry_worker_with_bounded_progress(
        limits(1, 4)?,
        resources()?,
        |current| {
            current.replace_expected_cursor(None);
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
    )
    .map_err(|_failure| String::from("startup failed"))?;
    let notice = handle
        .progress()
        .ok_or("receiver missing")?
        .recv()
        .map_err(|_error| String::from("notice missing"))?;
    let result = handle.join();
    let joined = result.joined.map_err(|error| format!("{error:?}"))?;
    if notice
        == (Notice {
            completed: 1,
            kind: Kind::Continued,
        })
        && matches!(
            joined.terminal,
            owned::NativeCacheOwnedWorkerTerminal::Returned(Ok(
                RunStop::CursorUnavailable { completed: 1 }
            ))
        )
        && joined.resources.lifecycle.expected_cursor().is_none()
        && result.totals
            == (Totals {
                enqueued: 1,
                full: 0,
                receiver_gone: 0,
            })
    {
        Ok(())
    } else {
        Err(String::from("advisory progress overrode cursor revocation"))
    }
}

#[test]
fn dropped_caller_stop_notice_never_erases_exact_stop() -> Result<(), String> {
    let mut called = 0usize;
    let handle = start_owned_cache_retry_worker_with_bounded_progress(
        limits(1, 4)?,
        resources()?,
        move |_current| {
            called = called.saturating_add(1);
            if called == 2 {
                Ok::<_, &'static str>(ControlFlow::Break("caller stopped"))
            } else {
                Ok(ControlFlow::Continue(()))
            }
        },
    )
    .map_err(|_failure| String::from("startup failed"))?;
    let result = handle.join();
    let joined = result.joined.map_err(|error| format!("{error:?}"))?;
    if matches!(
        joined.terminal,
        owned::NativeCacheOwnedWorkerTerminal::Returned(Ok(
            RunStop::CallerStopped {
                completed: 2,
                reason: "caller stopped"
            }
        ))
    ) && result.totals
        == (Totals {
            enqueued: 1,
            full: 1,
            receiver_gone: 0,
        })
        && joined.resources.lifecycle.expected_cursor().is_some()
    {
        Ok(())
    } else {
        Err(String::from(
            "missing stop notice erased completed worker result",
        ))
    }
}

#[test]
fn queue_full_does_not_mask_later_callback_error() -> Result<(), String> {
    let mut called = 0usize;
    let handle = start_owned_cache_retry_worker_with_bounded_progress(
        limits(1, 4)?,
        resources()?,
        move |_current| {
            called = called.saturating_add(1);
            if called == 2 {
                Err("exact second turn error")
            } else {
                Ok(ControlFlow::<&'static str>::Continue(()))
            }
        },
    )
    .map_err(|_failure| String::from("startup failed"))?;
    let result = handle.join();
    let joined = result.joined.map_err(|error| format!("{error:?}"))?;
    if matches!(
        joined.terminal,
        owned::NativeCacheOwnedWorkerTerminal::Returned(Err(
            RunFailure::Turn {
                completed: 2,
                error: "exact second turn error",
            }
        ))
    ) && result.totals
        == (Totals {
            enqueued: 1,
            full: 1,
            receiver_gone: 0,
        })
        && joined.resources.lifecycle.expected_cursor().is_some()
    {
        Ok(())
    } else {
        Err(String::from(
            "full observation queue erased exact turn error",
        ))
    }
}

#[test]
fn repeated_owned_progress_stop_keeps_independent_join_result()
-> Result<(), String> {
    let mut state = resources()?;
    state.pacer = pacing::NativeExecutableCacheLimitsRetryLifecyclePacer::new(
        nanos(5_000_000_000)?,
    );
    let handle = start_owned_cache_retry_worker_with_bounded_progress(
        limits(1, 4)?,
        state,
        |_current| {
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
    )
    .map_err(|_failure| String::from("startup failed"))?;
    let first = handle
        .progress()
        .ok_or("receiver missing")?
        .recv()
        .map_err(|_error| String::from("notice missing"))?;
    let requested = handle.cancel().map_err(|error| format!("{error:?}"))?;
    let shutdown = handle.cancel_and_join();
    let joined = shutdown
        .shutdown
        .joined
        .map_err(|error| format!("{error:?}"))?;
    if requested
        && shutdown.shutdown.cancellation == Ok(false)
        && first
            == (Notice {
                completed: 1,
                kind: Kind::Continued,
            })
        && matches!(
            joined.terminal,
            owned::NativeCacheOwnedWorkerTerminal::Returned(Ok(
                RunStop::Cancelled { completed: 1 }
            ))
        )
        && shutdown.totals
            == (Totals {
                enqueued: 1,
                full: 0,
                receiver_gone: 0,
            })
    {
        Ok(())
    } else {
        Err(String::from("repeated stop lost exact worker evidence"))
    }
}

#[test]
fn dropping_progress_owner_joins_in_flight_callback() -> Result<(), String> {
    let (started_tx, started_rx) = mpsc::sync_channel::<()>(0);
    let (release_tx, release_rx) = mpsc::sync_channel::<()>(0);
    let (drop_started_tx, drop_started_rx) =
        mpsc::sync_channel::<Result<bool, WaitError>>(0);
    let (drop_done_tx, drop_done_rx) = mpsc::channel::<()>();
    let callbacks = Arc::new(AtomicUsize::new(0));
    let counted = Arc::clone(&callbacks);
    let handle = start_owned_cache_retry_worker_with_bounded_progress(
        limits(1, 4)?,
        resources()?,
        move |_current| {
            let _previous = counted.fetch_add(1, Ordering::SeqCst);
            started_tx.send(()).map_err(|_error| "entry failed")?;
            release_rx.recv().map_err(|_error| "release failed")?;
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
    )
    .map_err(|_failure| String::from("startup failed"))?;
    started_rx
        .recv()
        .map_err(|_error| String::from("callback missing"))?;
    let dropper = thread::spawn(move || {
        let request = handle.cancel();
        let _sent = drop_started_tx.send(request);
        drop(handle);
        let _finished = drop_done_tx.send(());
    });
    let request = drop_started_rx
        .recv()
        .map_err(|_error| String::from("stop request missing"))?;
    let premature = drop_done_rx.try_recv();
    release_tx
        .send(())
        .map_err(|_error| String::from("release failed"))?;
    dropper
        .join()
        .map_err(|_panic| String::from("dropper panicked"))?;
    if request == Ok(true)
        && premature == Err(mpsc::TryRecvError::Empty)
        && drop_done_rx.recv().is_ok()
        && callbacks.load(Ordering::SeqCst) == 1
    {
        Ok(())
    } else {
        Err(String::from(
            "dropped progress owner detached an active callback",
        ))
    }
}

#[test]
fn pending_progress_try_join_keeps_receiver_and_cancel_scope()
-> Result<(), String> {
    let (entered_tx, entered_rx) = mpsc::sync_channel::<()>(0);
    let (release_tx, release_rx) = mpsc::sync_channel::<()>(0);
    let handle = start_owned_cache_retry_worker_with_bounded_progress(
        limits(1, 4)?,
        resources()?,
        move |_current| {
            entered_tx.send(()).map_err(|_error| "entry failed")?;
            release_rx.recv().map_err(|_error| "release failed")?;
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
    )
    .map_err(|_failure| String::from("startup failed"))?;
    entered_rx
        .recv()
        .map_err(|_error| String::from("entry missing"))?;
    let pending = match handle.try_join() {
        NativeCacheOwnedProgressTryJoin::Pending(recovered) => recovered,
        NativeCacheOwnedProgressTryJoin::Joined(_finished) => {
            return Err(String::from("in-flight progress falsely joined"));
        },
    };
    let stop = pending.cancel().map_err(|error| format!("{error:?}"))?;
    release_tx
        .send(())
        .map_err(|_error| String::from("release missing"))?;
    let first = pending
        .progress()
        .ok_or("receiver lost")?
        .recv()
        .map_err(|_error| String::from("notice missing"))?;
    let finished = pending.join();
    let joined = finished.joined.map_err(|error| format!("{error:?}"))?;
    if stop
        && first
            == (Notice {
                completed: 1,
                kind: Kind::Continued,
            })
        && finished.totals
            == (Totals {
                enqueued: 1,
                full: 0,
                receiver_gone: 0,
            })
        && matches!(
            joined.terminal,
            owned::NativeCacheOwnedWorkerTerminal::Returned(Ok(
                RunStop::Cancelled { completed: 1 }
            ))
        )
        && joined.resources.lifecycle.expected_cursor().is_some()
    {
        Ok(())
    } else {
        Err(String::from(
            "pending progress join lost receiver or terminal",
        ))
    }
}

#[test]
fn completed_progress_try_join_returns_final_counts_without_cancel()
-> Result<(), String> {
    let handle = start_owned_cache_retry_worker_with_bounded_progress(
        limits(1, 1)?,
        resources()?,
        |_current| Ok::<_, &'static str>(ControlFlow::Break("done")),
    )
    .map_err(|_failure| String::from("startup failed"))?;
    while !handle.is_finished() {
        thread::yield_now();
    }
    let finished = match handle.try_join() {
        NativeCacheOwnedProgressTryJoin::Joined(finished) => finished,
        NativeCacheOwnedProgressTryJoin::Pending(_handle) => {
            return Err(String::from(
                "finished progress thread reported pending",
            ));
        },
    };
    let joined = finished.joined.map_err(|error| format!("{error:?}"))?;
    if finished.totals
        == (Totals {
            enqueued: 1,
            full: 0,
            receiver_gone: 0,
        })
        && matches!(
            joined.terminal,
            owned::NativeCacheOwnedWorkerTerminal::Returned(Ok(
                RunStop::CallerStopped {
                    completed: 1,
                    reason: "done"
                }
            ))
        )
        && joined.resources.lifecycle.expected_cursor().is_some()
    {
        Ok(())
    } else {
        Err(String::from(
            "nonblocking progress join rewrote terminal evidence",
        ))
    }
}

#[test]
fn pending_progress_try_join_retains_taken_receiver_ownership()
-> Result<(), String> {
    let (entered_tx, entered_rx) = mpsc::sync_channel::<()>(0);
    let (release_tx, release_rx) = mpsc::sync_channel::<()>(0);
    let mut handle = start_owned_cache_retry_worker_with_bounded_progress(
        limits(1, 1)?,
        resources()?,
        move |_current| {
            entered_tx.send(()).map_err(|_error| "entry failed")?;
            release_rx.recv().map_err(|_error| "release failed")?;
            Ok::<_, &'static str>(ControlFlow::Break("complete"))
        },
    )
    .map_err(|_failure| String::from("startup failed"))?;
    let receiver = handle.take_progress_receiver().ok_or("receiver missing")?;
    entered_rx
        .recv()
        .map_err(|_error| String::from("entry missing"))?;
    let pending = match handle.try_join() {
        NativeCacheOwnedProgressTryJoin::Pending(recovered) => recovered,
        NativeCacheOwnedProgressTryJoin::Joined(_finished) => {
            return Err(String::from("in-flight callback already joined"));
        },
    };
    if pending.progress().is_some() {
        return Err(String::from("taken receiver unexpectedly duplicated"));
    }
    release_tx
        .send(())
        .map_err(|_error| String::from("release missing"))?;
    let notice = receiver
        .recv()
        .map_err(|_error| String::from("notice missing"))?;
    let finished = pending.join();
    let joined = finished.joined.map_err(|error| format!("{error:?}"))?;
    if notice
        == (Notice {
            completed: 1,
            kind: Kind::CallerStopped,
        })
        && finished.totals
            == (Totals {
                enqueued: 1,
                full: 0,
                receiver_gone: 0,
            })
        && matches!(
            joined.terminal,
            owned::NativeCacheOwnedWorkerTerminal::Returned(Ok(
                RunStop::CallerStopped {
                    completed: 1,
                    reason: "complete"
                }
            ))
        )
    {
        Ok(())
    } else {
        Err(String::from(
            "pending poll transferred receiver unexpectedly",
        ))
    }
}

#[test]
fn live_progress_snapshot_excludes_in_flight_callback() -> Result<(), String> {
    let (entered_tx, entered_rx) = mpsc::sync_channel::<()>(0);
    let (release_tx, release_rx) = mpsc::sync_channel::<()>(0);
    let handle = start_owned_cache_retry_worker_with_bounded_progress(
        limits(1, 1)?,
        resources()?,
        move |_current| {
            entered_tx.send(()).map_err(|_error| "entry failed")?;
            release_rx.recv().map_err(|_error| "release failed")?;
            Ok::<_, &'static str>(ControlFlow::Break("done"))
        },
    )
    .map_err(|_failure| String::from("startup failed"))?;
    entered_rx
        .recv()
        .map_err(|_error| String::from("entry missing"))?;
    if handle.progress_totals() != Totals::default() {
        return Err(String::from("in-flight callback inflated live counts"));
    }
    release_tx
        .send(())
        .map_err(|_error| String::from("release missing"))?;
    let notice = handle
        .progress()
        .ok_or("receiver missing")?
        .recv()
        .map_err(|_error| String::from("notice missing"))?;
    while handle.progress_totals().enqueued == 0 {
        thread::yield_now();
    }
    let live = handle.progress_totals();
    let finished = handle.join();
    let joined = finished.joined.map_err(|error| format!("{error:?}"))?;
    if notice
        == (Notice {
            completed: 1,
            kind: Kind::CallerStopped,
        })
        && live
            == (Totals {
                enqueued: 1,
                full: 0,
                receiver_gone: 0,
            })
        && finished.totals == live
        && matches!(
            joined.terminal,
            owned::NativeCacheOwnedWorkerTerminal::Returned(Ok(
                RunStop::CallerStopped {
                    completed: 1,
                    reason: "done"
                }
            ))
        )
    {
        Ok(())
    } else {
        Err(String::from("live snapshot rewrote terminal result"))
    }
}

#[test]
fn live_progress_snapshot_tracks_full_queue_without_draining()
-> Result<(), String> {
    let (entered_tx, entered_rx) = mpsc::sync_channel::<()>(0);
    let (release_tx, release_rx) = mpsc::sync_channel::<()>(0);
    let mut completed = 0usize;
    let handle = start_owned_cache_retry_worker_with_bounded_progress(
        limits(1, 2)?,
        resources()?,
        move |_current| {
            completed = completed.saturating_add(1);
            if completed == 2 {
                entered_tx.send(()).map_err(|_error| "entry failed")?;
                release_rx.recv().map_err(|_error| "release failed")?;
            }
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
    )
    .map_err(|_failure| String::from("startup failed"))?;
    entered_rx
        .recv()
        .map_err(|_error| String::from("entry missing"))?;
    let first = handle.progress_totals();
    release_tx
        .send(())
        .map_err(|_error| String::from("release missing"))?;
    while handle.progress_totals().full == 0 {
        thread::yield_now();
    }
    let live = handle.progress_totals();
    let finished = handle.join();
    let joined = finished.joined.map_err(|error| format!("{error:?}"))?;
    if first
        == (Totals {
            enqueued: 1,
            full: 0,
            receiver_gone: 0,
        })
        && live
            == (Totals {
                enqueued: 1,
                full: 1,
                receiver_gone: 0,
            })
        && finished.totals == live
        && matches!(
            joined.terminal,
            owned::NativeCacheOwnedWorkerTerminal::Returned(Ok(
                RunStop::LimitReached { completed: 2 }
            ))
        )
    {
        Ok(())
    } else {
        Err(String::from("live saturation changed finite work"))
    }
}

#[test]
fn pending_join_preserves_live_progress_snapshot_and_receiver_loss()
-> Result<(), String> {
    let (entered_tx, entered_rx) = mpsc::sync_channel::<()>(0);
    let (release_tx, release_rx) = mpsc::sync_channel::<()>(0);
    let mut handle = start_owned_cache_retry_worker_with_bounded_progress(
        limits(1, 1)?,
        resources()?,
        move |_current| {
            entered_tx.send(()).map_err(|_error| "entry failed")?;
            release_rx.recv().map_err(|_error| "release failed")?;
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
    )
    .map_err(|_failure| String::from("startup failed"))?;
    let receiver = handle.take_progress_receiver().ok_or("receiver missing")?;
    drop(receiver);
    entered_rx
        .recv()
        .map_err(|_error| String::from("entry missing"))?;
    let pending = match handle.try_join() {
        NativeCacheOwnedProgressTryJoin::Pending(recovered) => recovered,
        NativeCacheOwnedProgressTryJoin::Joined(_finished) => {
            return Err(String::from("unfinished worker falsely joined"));
        },
    };
    if pending.progress_totals() != Totals::default() {
        return Err(String::from("poll fabricated returned callback"));
    }
    release_tx
        .send(())
        .map_err(|_error| String::from("release missing"))?;
    while pending.progress_totals().receiver_gone == 0 {
        thread::yield_now();
    }
    let live = pending.progress_totals();
    let finished = pending.join();
    let joined = finished.joined.map_err(|error| format!("{error:?}"))?;
    if live
        == (Totals {
            enqueued: 0,
            full: 0,
            receiver_gone: 1,
        })
        && finished.totals == live
        && matches!(
            joined.terminal,
            owned::NativeCacheOwnedWorkerTerminal::Returned(Ok(
                RunStop::LimitReached { completed: 1 }
            ))
        )
    {
        Ok(())
    } else {
        Err(String::from("pending snapshot lost explicit receiver drop"))
    }
}

#[test]
fn live_progress_snapshot_does_not_authorize_after_callback_panic()
-> Result<(), String> {
    let (entered_tx, entered_rx) = mpsc::sync_channel::<()>(0);
    let (release_tx, release_rx) = mpsc::sync_channel::<()>(0);
    let mut called = 0usize;
    let handle = start_owned_cache_retry_worker_with_bounded_progress(
        limits(1, 3)?,
        resources()?,
        move |current| {
            called = called.saturating_add(1);
            if called == 2 {
                entered_tx.send(()).map_err(|_error| "entry failed")?;
                release_rx.recv().map_err(|_error| "release failed")?;
                current.replace_expected_cursor(None);
                resume_unwind(Box::new("second callback panic"));
            }
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
    )
    .map_err(|_failure| String::from("startup failed"))?;
    entered_rx
        .recv()
        .map_err(|_error| String::from("entry missing"))?;
    let live = handle.progress_totals();
    release_tx
        .send(())
        .map_err(|_error| String::from("release missing"))?;
    let finished = handle.join();
    let joined = finished.joined.map_err(|error| format!("{error:?}"))?;
    if live
        == (Totals {
            enqueued: 1,
            full: 0,
            receiver_gone: 0,
        })
        && finished.totals == live
        && matches!(
            joined.terminal,
            owned::NativeCacheOwnedWorkerTerminal::WorkerPanicked
        )
        && joined.resources.lifecycle.expected_cursor().is_none()
    {
        Ok(())
    } else {
        Err(String::from("live observation authorized panicking worker"))
    }
}

#[test]
fn finished_progress_try_join_keeps_exact_returned_turn_error()
-> Result<(), String> {
    let handle = start_owned_cache_retry_worker_with_bounded_progress(
        limits(1, 3)?,
        resources()?,
        |_current| Err::<ControlFlow<&'static str>, _>("exact turn failure"),
    )
    .map_err(|_failure| String::from("startup failed"))?;
    while !handle.is_finished() {
        thread::yield_now();
    }
    let finished = match handle.try_join() {
        NativeCacheOwnedProgressTryJoin::Joined(finished) => finished,
        NativeCacheOwnedProgressTryJoin::Pending(_pending) => {
            return Err(String::from(
                "finished failed worker remained pending",
            ));
        },
    };
    let joined = finished.joined.map_err(|error| format!("{error:?}"))?;
    if finished.totals
        == (Totals {
            enqueued: 1,
            full: 0,
            receiver_gone: 0,
        })
        && matches!(
            joined.terminal,
            owned::NativeCacheOwnedWorkerTerminal::Returned(Err(
                RunFailure::Turn {
                    completed: 1,
                    error: "exact turn failure"
                }
            ))
        )
        && joined.resources.lifecycle.expected_cursor().is_some()
    {
        Ok(())
    } else {
        Err(String::from("nonblocking join erased returned turn error"))
    }
}

#[test]
fn pending_progress_try_shutdown_retains_receiver_and_repeated_stop()
-> Result<(), String> {
    let (entered_tx, entered_rx) = mpsc::sync_channel::<()>(0);
    let (release_tx, release_rx) = mpsc::sync_channel::<()>(0);
    let handle = start_owned_cache_retry_worker_with_bounded_progress(
        limits(1, 3)?,
        resources()?,
        move |_current| {
            entered_tx.send(()).map_err(|_error| "entry failed")?;
            release_rx.recv().map_err(|_error| "release failed")?;
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
    )
    .map_err(|_failure| String::from("startup failed"))?;
    entered_rx
        .recv()
        .map_err(|_error| String::from("entry missing"))?;
    let (first_request, pending) =
        expect_pending_stop(handle.try_cancel_and_join())?;
    let (repeat_request, recovered) =
        expect_pending_stop(pending.try_cancel_and_join())?;
    release_tx
        .send(())
        .map_err(|_error| String::from("release missing"))?;
    let first = recovered
        .progress()
        .ok_or("receiver lost")?
        .recv()
        .map_err(|_error| String::from("notice missing"))?;
    let finished = recovered.join();
    let joined = finished.joined.map_err(|error| format!("{error:?}"))?;
    if first_request == Ok(true)
        && repeat_request == Ok(false)
        && first
            == (Notice {
                completed: 1,
                kind: Kind::Continued,
            })
        && finished.totals
            == (Totals {
                enqueued: 1,
                full: 0,
                receiver_gone: 0,
            })
        && matches!(
            joined.terminal,
            owned::NativeCacheOwnedWorkerTerminal::Returned(Ok(
                RunStop::Cancelled { completed: 1 }
            ))
        )
        && joined.resources.lifecycle.expected_cursor().is_some()
    {
        Ok(())
    } else {
        Err(String::from("pending stop lost receiver or exact work"))
    }
}

#[test]
fn completed_progress_try_shutdown_retains_terminal_and_final_counts()
-> Result<(), String> {
    let handle = start_owned_cache_retry_worker_with_bounded_progress(
        limits(2, 1)?,
        resources()?,
        |_current| Ok::<_, &'static str>(ControlFlow::Break("completed")),
    )
    .map_err(|_failure| String::from("startup failed"))?;
    while !handle.is_finished() {
        thread::yield_now();
    }
    let completed = match handle.try_cancel_and_join() {
        NativeCacheOwnedProgressTryShutdown::Joined(shutdown) => shutdown,
        NativeCacheOwnedProgressTryShutdown::Pending { .. } => {
            return Err(String::from(
                "finished progress worker reported pending",
            ));
        },
    };
    let joined = completed
        .shutdown
        .joined
        .map_err(|error| format!("{error:?}"))?;
    if completed.shutdown.cancellation == Ok(true)
        && completed.totals
            == (Totals {
                enqueued: 1,
                full: 0,
                receiver_gone: 0,
            })
        && matches!(
            joined.terminal,
            owned::NativeCacheOwnedWorkerTerminal::Returned(Ok(
                RunStop::CallerStopped {
                    completed: 1,
                    reason: "completed"
                }
            ))
        )
        && joined.resources.lifecycle.expected_cursor().is_some()
    {
        Ok(())
    } else {
        Err(String::from(
            "late stop masked exact progress or caller stop",
        ))
    }
}

#[test]
fn progress_try_shutdown_counts_abandoned_receiver_after_stop()
-> Result<(), String> {
    let (entered_tx, entered_rx) = mpsc::sync_channel::<()>(0);
    let (release_tx, release_rx) = mpsc::sync_channel::<()>(0);
    let mut handle = start_owned_cache_retry_worker_with_bounded_progress(
        limits(1, 3)?,
        resources()?,
        move |_current| {
            entered_tx.send(()).map_err(|_error| "entry failed")?;
            release_rx.recv().map_err(|_error| "release failed")?;
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
    )
    .map_err(|_failure| String::from("startup failed"))?;
    entered_rx
        .recv()
        .map_err(|_error| String::from("entry missing"))?;
    drop(handle.take_progress_receiver());
    let (request, pending) = expect_pending_stop(handle.try_cancel_and_join())?;
    release_tx
        .send(())
        .map_err(|_error| String::from("release failed"))?;
    let completed = pending.join();
    let joined = completed.joined.map_err(|error| format!("{error:?}"))?;
    if request == Ok(true)
        && completed.totals
            == (Totals {
                enqueued: 0,
                full: 0,
                receiver_gone: 1,
            })
        && matches!(
            joined.terminal,
            owned::NativeCacheOwnedWorkerTerminal::Returned(Ok(
                RunStop::Cancelled { completed: 1 }
            ))
        )
        && joined.resources.lifecycle.expected_cursor().is_some()
    {
        Ok(())
    } else {
        Err(String::from(
            "pending stop lost abandoned transport evidence",
        ))
    }
}

#[test]
fn pending_progress_try_shutdown_keeps_exact_callback_failure()
-> Result<(), String> {
    let (started_tx, started_rx) = mpsc::sync_channel::<()>(0);
    let (release_tx, release_rx) = mpsc::sync_channel::<()>(0);
    let handle = start_owned_cache_retry_worker_with_bounded_progress(
        limits(1, 2)?,
        resources()?,
        move |_current| {
            started_tx.send(()).map_err(|_error| "entry failed")?;
            release_rx.recv().map_err(|_error| "release failed")?;
            Err::<ControlFlow<&'static str>, _>("typed activation failure")
        },
    )
    .map_err(|_failure| String::from("startup failed"))?;
    started_rx
        .recv()
        .map_err(|_error| String::from("entry missing"))?;
    let (request, pending) = expect_pending_stop(handle.try_cancel_and_join())?;
    release_tx
        .send(())
        .map_err(|_error| String::from("release failed"))?;
    let notice = pending
        .progress()
        .ok_or("receiver missing")?
        .recv()
        .map_err(|_error| String::from("notice missing"))?;
    let completed = pending.join();
    let joined = completed.joined.map_err(|error| format!("{error:?}"))?;
    if request == Ok(true)
        && notice
            == (Notice {
                completed: 1,
                kind: Kind::Failed,
            })
        && completed.totals
            == (Totals {
                enqueued: 1,
                full: 0,
                receiver_gone: 0,
            })
        && matches!(
            joined.terminal,
            owned::NativeCacheOwnedWorkerTerminal::Returned(Err(
                RunFailure::Turn {
                    completed: 1,
                    error: "typed activation failure"
                }
            ))
        )
        && joined.resources.lifecycle.expected_cursor().is_some()
    {
        Ok(())
    } else {
        Err(String::from(
            "stop request erased callback failure progress",
        ))
    }
}

#[test]
fn pending_progress_try_shutdown_does_not_mask_destructor_panic()
-> Result<(), String> {
    let (started_tx, started_rx) = mpsc::sync_channel::<()>(0);
    let (release_tx, release_rx) = mpsc::sync_channel::<()>(0);
    let destructor = PanicOnDrop;
    let handle = start_owned_cache_retry_worker_with_bounded_progress(
        limits(1, 2)?,
        resources()?,
        move |_current| {
            let _keep = &destructor;
            started_tx.send(()).map_err(|_error| "entry failed")?;
            release_rx.recv().map_err(|_error| "release failed")?;
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
    )
    .map_err(|_failure| String::from("startup failed"))?;
    started_rx
        .recv()
        .map_err(|_error| String::from("entry missing"))?;
    let (request, pending) = expect_pending_stop(handle.try_cancel_and_join())?;
    release_tx
        .send(())
        .map_err(|_error| String::from("release failed"))?;
    let notice = pending
        .progress()
        .ok_or("receiver missing")?
        .recv()
        .map_err(|_error| String::from("notice missing"))?;
    let completed = pending.join();
    let joined = completed.joined.map_err(|error| format!("{error:?}"))?;
    if request == Ok(true)
        && notice
            == (Notice {
                completed: 1,
                kind: Kind::Continued,
            })
        && completed.totals
            == (Totals {
                enqueued: 1,
                full: 0,
                receiver_gone: 0,
            })
        && matches!(
            joined.terminal,
            owned::NativeCacheOwnedWorkerTerminal::WorkerPanicked
        )
        && joined.resources.lifecycle.expected_cursor().is_none()
    {
        Ok(())
    } else {
        Err(String::from("stop request admitted destructor panic"))
    }
}
