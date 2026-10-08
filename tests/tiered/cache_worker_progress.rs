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
//   - Deterministic finite callback-progress and cancellation regressions.
// - Must-Not:
//   - Depend on precise clocks, detach threads, or infer cursor authority from
//     advisory callback progress observations.
// - Allows:
//   - Inputs: short finite runs, test-local borrowed lifecycle and pacer.
//   - Outputs: ordered notices, typed worker outcomes, and cancellation tests.
//   - Side effects: one joined worker per test and test-local channels.
// - Split-When:
//   - Durable progress and scheduling require independent regression suites.
// - Merge-When:
//   - The product worker gains one authoritative shared progress protocol.
// - Summary:
//   - Proves callback notices cannot outrank terminal worker evidence.
// - Description:
//   - Simulated finite runs and cancellation use exact handshakes, not sleeps.
// - Usage:
//   - Compiled only for deterministic Rust test harnesses.
// - Defaults:
//   - Fresh lifecycle and process-local pacing for every fixture.
//

//! Scoped cache worker callback progress test fixtures.

use std::num::NonZeroU64;
use std::panic::resume_unwind;
use std::sync::mpsc::RecvError;

use super::*;
use crate::{
    executable_cache_limits_retry_pacing as pacing,
    executable_cache_limits_retry_policy as policy,
    executable_cache_limits_retry_run as run,
    executable_cache_limits_retry_run_fallible as fallible,
    executable_cache_limits_trigger_cadence as cadence,
};

// Separate contexts prevent channel state leaking between tests.
type Pacer = pacing::NativeExecutableCacheLimitsRetryLifecyclePacer;
type RunStop<Reason> =
    run::NativeExecutableCacheLimitsRetryLifecycleRunStop<Reason>;
type Fixture = (RetryLifecycle, Pacer);
type Notice = NativeCacheScopedTurnProgress;
type Kind = NativeCacheScopedTurnProgressKind;
type RunFailure<WaitError, TurnError> =
    fallible::NativeExecutableCacheLimitsRetryLifecycleRunFailure<
        WaitError,
        TurnError,
    >;

fn positive(value: usize) -> Result<NonZeroUsize, String> {
    NonZeroUsize::new(value).ok_or_else(|| String::from("zero turn limit"))
}

fn nanos(value: u64) -> Result<NonZeroU64, String> {
    NonZeroU64::new(value).ok_or_else(|| String::from("zero duration"))
}

fn fixture() -> Result<Fixture, String> {
    let tick = cadence::NativeExecutableCacheLimitsTriggerCadence::new(
        nanos(1)?,
        nanos(2)?,
    );
    Ok((
        RetryLifecycle::new_with_cursor(
            tick, positive(15)?, positive(2)?,
            policy::NativeExecutableCacheLimitsRetryConflictPolicy::
                return_on_contention(),
        ),
        Pacer::new(nanos(1)?),
    ))
}

#[test]
fn finite_progress_notices_are_ordered_and_exact() -> Result<(), String> {
    let (mut lifecycle, mut pacer) = fixture()?;
    let result = run_scoped_cache_retry_worker_with_progress(
        positive(3)?,
        Resources::new(&mut lifecycle, &mut pacer),
        |_current| {
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
        |_cancel, notices| notices.iter().collect::<Vec<_>>(),
    )
    .map_err(|error| format!("{error:?}"))?;
    let expected = vec![
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
    ];
    if result.run == Ok(RunStop::LimitReached { completed: 3 })
        && result.supervisor == expected
    {
        Ok(())
    } else {
        Err(String::from("finite progress lost exact ordering"))
    }
}

#[test]
fn supervisor_can_cancel_from_first_completion_notice() -> Result<(), String> {
    let (mut lifecycle, _default_pacer) = fixture()?;
    let mut pacer = Pacer::new(nanos(5_000_000_000)?);
    let mut called = 0usize;
    let result = run_scoped_cache_retry_worker_with_progress(
        positive(4)?,
        Resources::new(&mut lifecycle, &mut pacer),
        |_current| {
            called += 1;
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
        |cancel, notices| {
            let first = notices.recv().map_err(|_error| "missing notice")?;
            let cancelled =
                cancel.cancel().map_err(|_error| "cancel failed")?;
            Ok::<_, &'static str>((first, cancelled))
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    if result.run == Ok(RunStop::Cancelled { completed: 1 })
        && result.supervisor
            == Ok((
                Notice {
                    completed: 1,
                    kind: Kind::Continued,
                },
                true,
            ))
        && called == 1
    {
        Ok(())
    } else {
        Err(String::from("notice cancellation allowed extra callbacks"))
    }
}

#[test]
fn caller_stop_notifies_without_exposing_reason() -> Result<(), String> {
    let (mut lifecycle, mut pacer) = fixture()?;
    let result = run_scoped_cache_retry_worker_with_progress(
        positive(3)?,
        Resources::new(&mut lifecycle, &mut pacer),
        |_current| Ok::<_, &'static str>(ControlFlow::Break("private reason")),
        |_cancel, notices| notices.iter().collect::<Vec<_>>(),
    )
    .map_err(|error| format!("{error:?}"))?;
    if result.run
        == Ok(RunStop::CallerStopped {
            completed: 1,
            reason: "private reason",
        })
        && result.supervisor
            == vec![Notice {
                completed: 1,
                kind: Kind::CallerStopped,
            }]
    {
        Ok(())
    } else {
        Err(String::from("stop reason leaked or callback not reported"))
    }
}

#[test]
fn failure_notice_does_not_erase_exact_turn_error() -> Result<(), String> {
    let (mut lifecycle, mut pacer) = fixture()?;
    let result = run_scoped_cache_retry_worker_with_progress(
        positive(3)?,
        Resources::new(&mut lifecycle, &mut pacer),
        |_current| {
            Err::<ControlFlow<&'static str>, &'static str>("private error")
        },
        |_cancel, notices| notices.iter().collect::<Vec<_>>(),
    )
    .map_err(|error| format!("{error:?}"))?;
    if result.run
        == Err(RunFailure::Turn {
            completed: 1,
            error: "private error",
        })
        && result.supervisor
            == vec![Notice {
                completed: 1,
                kind: Kind::Failed,
            }]
    {
        Ok(())
    } else {
        Err(String::from("callback error lost typed evidence"))
    }
}

#[test]
fn cursorless_run_closes_stream_without_fabricated_progress()
-> Result<(), String> {
    let (mut lifecycle, mut pacer) = fixture()?;
    lifecycle.replace_expected_cursor(None);
    let mut called = 0usize;
    let result = run_scoped_cache_retry_worker_with_progress(
        positive(3)?,
        Resources::new(&mut lifecycle, &mut pacer),
        |_current| {
            called += 1;
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
        |_cancel, notices| notices.recv(),
    )
    .map_err(|error| format!("{error:?}"))?;
    if result.run == Ok(RunStop::CursorUnavailable { completed: 0 })
        && result.supervisor == Err(RecvError)
        && called == 0
    {
        Ok(())
    } else {
        Err(String::from("cursorless run fabricated callback evidence"))
    }
}

#[test]
fn ignoring_progress_does_not_block_worker() -> Result<(), String> {
    let (mut lifecycle, mut pacer) = fixture()?;
    let mut called = 0usize;
    let result = run_scoped_cache_retry_worker_with_progress(
        positive(4)?,
        Resources::new(&mut lifecycle, &mut pacer),
        |_current| {
            called += 1;
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
        |_cancel, _notices| "ignored",
    )
    .map_err(|error| format!("{error:?}"))?;
    if result.run == Ok(RunStop::LimitReached { completed: 4 })
        && result.supervisor == "ignored"
        && called == 4
    {
        Ok(())
    } else {
        Err(String::from("unobserved progress blocked finite work"))
    }
}

#[test]
fn panicking_turn_does_not_fabricate_returned_notice() -> Result<(), String> {
    let (mut lifecycle, mut pacer) = fixture()?;
    let result = run_scoped_cache_retry_worker_with_progress(
        positive(3)?,
        Resources::new(&mut lifecycle, &mut pacer),
        |_current| -> Result<ControlFlow<&'static str>, &'static str> {
            resume_unwind(Box::new("turn panic"));
        },
        |_cancel, notices| notices.recv(),
    );
    if matches!(
        result,
        Err(worker::NativeCacheScopedWorkerError::WorkerPanicked)
    ) && lifecycle.expected_cursor().is_none()
    {
        Ok(())
    } else {
        Err(String::from("panic was misreported as callback completion"))
    }
}

#[test]
fn an_in_flight_callback_never_emits_completion_progress() -> Result<(), String>
{
    use std::sync::mpsc::TryRecvError;

    let (mut lifecycle, _default_pacer) = fixture()?;
    let mut pacer = Pacer::new(nanos(5_000_000_000)?);
    let (entry_tx, entry_rx) = mpsc::sync_channel::<()>(0);
    let (release_tx, release_rx) = mpsc::sync_channel::<()>(0);
    let result = run_scoped_cache_retry_worker_with_progress(
        positive(3)?,
        Resources::new(&mut lifecycle, &mut pacer),
        move |_current| {
            entry_tx.send(()).map_err(|_error| "entry failed")?;
            release_rx.recv().map_err(|_error| "release failed")?;
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
        |cancel, notices| {
            entry_rx.recv().map_err(|_error| "entry missing")?;
            let premature = notices.try_recv();
            release_tx.send(()).map_err(|_error| "release failed")?;
            let first = notices.recv().map_err(|_error| "notice missing")?;
            let requested =
                cancel.cancel().map_err(|_error| "cancel failed")?;
            Ok::<_, &'static str>((premature, first, requested))
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    if result.run == Ok(RunStop::Cancelled { completed: 1 })
        && result.supervisor
            == Ok((
                Err(TryRecvError::Empty),
                Notice {
                    completed: 1,
                    kind: Kind::Continued,
                },
                true,
            ))
    {
        Ok(())
    } else {
        Err(String::from("notice preceded completion or cancellation"))
    }
}

#[test]
fn continued_then_failed_reports_exact_terminal_error() -> Result<(), String> {
    let (mut lifecycle, mut pacer) = fixture()?;
    let mut called = 0usize;
    let result = run_scoped_cache_retry_worker_with_progress(
        positive(4)?,
        Resources::new(&mut lifecycle, &mut pacer),
        |_current| {
            called = called.saturating_add(1);
            if called == 2 {
                Err("second callback failed")
            } else {
                Ok(ControlFlow::<&'static str>::Continue(()))
            }
        },
        |_cancel, notices| notices.iter().collect::<Vec<_>>(),
    )
    .map_err(|error| format!("{error:?}"))?;
    if result.run
        == Err(RunFailure::Turn {
            completed: 2,
            error: "second callback failed",
        })
        && result.supervisor
            == vec![
                Notice {
                    completed: 1,
                    kind: Kind::Continued,
                },
                Notice {
                    completed: 2,
                    kind: Kind::Failed,
                },
            ]
        && called == 2
        && lifecycle.expected_cursor().is_some()
    {
        Ok(())
    } else {
        Err(String::from("failed callback lost ordered progress"))
    }
}

#[test]
fn worker_panic_after_one_completion_closes_stream() -> Result<(), String> {
    let (mut lifecycle, mut pacer) = fixture()?;
    let mut called = 0usize;
    let mut observed = Vec::new();
    let result = run_scoped_cache_retry_worker_with_progress(
        positive(4)?,
        Resources::new(&mut lifecycle, &mut pacer),
        |_current| {
            called = called.saturating_add(1);
            if called == 2 {
                resume_unwind(Box::new("second callback panic"));
            }
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
        |_cancel, notices| observed.extend(notices.iter()),
    );
    if matches!(
        result,
        Err(worker::NativeCacheScopedWorkerError::WorkerPanicked)
    ) && lifecycle.expected_cursor().is_none()
        && called == 2
        && observed
            == vec![Notice {
                completed: 1,
                kind: Kind::Continued,
            }]
    {
        Ok(())
    } else {
        Err(String::from("panicking callback retained cursor authority"))
    }
}

#[test]
fn cursor_loss_after_report_blocks_next_turn() -> Result<(), String> {
    let (mut lifecycle, mut pacer) = fixture()?;
    let result = run_scoped_cache_retry_worker_with_progress(
        positive(4)?,
        Resources::new(&mut lifecycle, &mut pacer),
        |current| {
            current.replace_expected_cursor(None);
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
        |_cancel, notices| notices.iter().collect::<Vec<_>>(),
    )
    .map_err(|error| format!("{error:?}"))?;
    if result.run == Ok(RunStop::CursorUnavailable { completed: 1 })
        && result.supervisor
            == vec![Notice {
                completed: 1,
                kind: Kind::Continued,
            }]
        && lifecycle.expected_cursor().is_none()
    {
        Ok(())
    } else {
        Err(String::from("progress overrode revoked cursor authority"))
    }
}
