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
//   - Bounded progress queue and typed transport drop evidence regressions.
// - Must-Not:
//   - Assume concurrent scheduling order, block joined worker in tests, or turn
//     advisory delivery into cursor or durable completion authority.
// - Allows:
//   - Inputs: positive queue capacity and turns, test-local lifecycle/pacer.
//   - Outputs: exact counted attempts, bounded enqueues, and typed results.
//   - Side effects: one supervised and joined host worker per test.
// - Split-When:
//   - A durable progress transport needs distinct integration fixtures.
// - Merge-When:
//   - An authoritative product scheduler owns these same bounded queues.
// - Summary:
//   - Proves bounded observation loss never mutates work or terminal evidence.
// - Description:
//   - Scheduling-independent count invariants cover queue saturation and
//     receiver abandonment while rendezvous makes cancellation deterministic.
// - Usage:
//   - Rust test-only cross-thread observation fixtures.
// - Defaults:
//   - New lifecycle and pacer for each test run.
//

//! Capacity-bounded worker-progress transport regression tests.

use std::num::NonZeroU64;

use super::*;
use crate::{
    executable_cache_limits_retry_pacing as pacing,
    executable_cache_limits_retry_policy as policy,
    executable_cache_limits_retry_run as run,
    executable_cache_limits_retry_run_fallible as fallible,
    executable_cache_limits_trigger_cadence as trigger,
};

type Fixture = (
    RetryLifecycle,
    pacing::NativeExecutableCacheLimitsRetryLifecyclePacer,
);
type RunStop<Reason> =
    run::NativeExecutableCacheLimitsRetryLifecycleRunStop<Reason>;
type TurnFailure<Wait, Turn> =
    fallible::NativeExecutableCacheLimitsRetryLifecycleRunFailure<Wait, Turn>;

fn limit(value: usize) -> Result<NonZeroUsize, String> {
    NonZeroUsize::new(value).ok_or_else(|| String::from("zero limit"))
}

fn nanos(value: u64) -> Result<NonZeroU64, String> {
    NonZeroU64::new(value).ok_or_else(|| String::from("zero duration"))
}

fn fixture() -> Result<Fixture, String> {
    let cadence = trigger::NativeExecutableCacheLimitsTriggerCadence::new(
        nanos(1)?,
        nanos(2)?,
    );
    Ok((
        RetryLifecycle::new_with_cursor(
            cadence, limit(15)?, limit(2)?,
            policy::NativeExecutableCacheLimitsRetryConflictPolicy::
                return_on_contention(),
        ),
        pacing::NativeExecutableCacheLimitsRetryLifecyclePacer::new(nanos(1)?),
    ))
}

fn total(totals: NativeCacheScopedBoundedProgressTotals) -> usize {
    totals
        .enqueued
        .saturating_add(totals.full)
        .saturating_add(totals.receiver_gone)
}

#[test]
fn bounded_queue_does_not_block_unobserved_finite_work() -> Result<(), String> {
    let (mut lifecycle, mut pacer) = fixture()?;
    let mut called = 0usize;
    let result = run_scoped_cache_retry_worker_bounded_progress(
        NativeCacheScopedBoundedProgressLimits::new(limit(1)?, limit(32)?),
        Resources::new(&mut lifecycle, &mut pacer),
        |_current| {
            called = called.saturating_add(1);
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
        |_cancel, _notices| "not observed",
    )
    .map_err(|error| format!("{error:?}"))?;
    if result.worker.run == Ok(RunStop::LimitReached { completed: 32 })
        && result.worker.supervisor == "not observed"
        && called == 32
        && total(result.totals) == 32
        && result.totals.enqueued <= 1
        && result
            .totals
            .full
            .saturating_add(result.totals.receiver_gone)
            >= 31
    {
        Ok(())
    } else {
        Err(String::from("bounded queue blocked or erased finite work"))
    }
}

#[test]
fn first_admitted_notice_remains_classified_after_abandonment()
-> Result<(), String> {
    let (mut lifecycle, mut pacer) = fixture()?;
    let result = run_scoped_cache_retry_worker_bounded_progress(
        NativeCacheScopedBoundedProgressLimits::new(limit(2)?, limit(20)?),
        Resources::new(&mut lifecycle, &mut pacer),
        |_current| {
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
        |_cancel, notices| notices.recv(),
    )
    .map_err(|error| format!("{error:?}"))?;
    if result.worker.run == Ok(RunStop::LimitReached { completed: 20 })
        && result.worker.supervisor
            == Ok(Notice {
                completed: 1,
                kind: Kind::Continued,
            })
        && total(result.totals) == 20
        && result.totals.enqueued >= 1
        && result.totals.enqueued <= 3
    {
        Ok(())
    } else {
        Err(String::from(
            "admitted notice lost bounded transport evidence",
        ))
    }
}

#[test]
fn supervisor_cancellation_after_notice_preserves_exact_counts()
-> Result<(), String> {
    let (mut lifecycle, _default_pacer) = fixture()?;
    let mut pacer = pacing::NativeExecutableCacheLimitsRetryLifecyclePacer::new(
        nanos(5_000_000_000)?,
    );
    let mut called = 0usize;
    let result = run_scoped_cache_retry_worker_bounded_progress(
        NativeCacheScopedBoundedProgressLimits::new(limit(1)?, limit(4)?),
        Resources::new(&mut lifecycle, &mut pacer),
        |_current| {
            called = called.saturating_add(1);
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
        |cancel, notices| {
            let first = notices.recv().map_err(|_error| "missing notice")?;
            let requested =
                cancel.cancel().map_err(|_error| "cancel failed")?;
            Ok::<_, &'static str>((first, requested))
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    if result.worker.run == Ok(RunStop::Cancelled { completed: 1 })
        && result.worker.supervisor
            == Ok((
                Notice {
                    completed: 1,
                    kind: Kind::Continued,
                },
                true,
            ))
        && called == 1
        && result.totals
            == (NativeCacheScopedBoundedProgressTotals {
                enqueued: 1,
                full: 0,
                receiver_gone: 0,
            })
    {
        Ok(())
    } else {
        Err(String::from("cancellation after notice lost exact counts"))
    }
}

#[test]
fn a_returned_callback_error_remains_terminal_authority() -> Result<(), String>
{
    let (mut lifecycle, mut pacer) = fixture()?;
    let result = run_scoped_cache_retry_worker_bounded_progress(
        NativeCacheScopedBoundedProgressLimits::new(limit(1)?, limit(3)?),
        Resources::new(&mut lifecycle, &mut pacer),
        |_current| Err::<ControlFlow<&'static str>, _>("callback failed"),
        |_cancel, notices| notices.recv(),
    )
    .map_err(|error| format!("{error:?}"))?;
    if result.worker.run
        == Err(TurnFailure::Turn {
            completed: 1,
            error: "callback failed",
        })
        && result.worker.supervisor
            == Ok(Notice {
                completed: 1,
                kind: Kind::Failed,
            })
        && result.totals
            == (NativeCacheScopedBoundedProgressTotals {
                enqueued: 1,
                full: 0,
                receiver_gone: 0,
            })
        && lifecycle.expected_cursor().is_some()
    {
        Ok(())
    } else {
        Err(String::from(
            "bounded transport erased typed callback error",
        ))
    }
}

#[test]
fn cursorless_worker_emits_no_bounded_notices() -> Result<(), String> {
    let (mut lifecycle, mut pacer) = fixture()?;
    lifecycle.replace_expected_cursor(None);
    let mut called = 0usize;
    let result = run_scoped_cache_retry_worker_bounded_progress(
        NativeCacheScopedBoundedProgressLimits::new(limit(2)?, limit(4)?),
        Resources::new(&mut lifecycle, &mut pacer),
        |_current| {
            called = called.saturating_add(1);
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
        |_cancel, notices| notices.recv(),
    )
    .map_err(|error| format!("{error:?}"))?;
    if result.worker.run == Ok(RunStop::CursorUnavailable { completed: 0 })
        && result.worker.supervisor.is_err()
        && called == 0
        && result.totals == NativeCacheScopedBoundedProgressTotals::default()
    {
        Ok(())
    } else {
        Err(String::from("cursorless worker fabricated bounded notice"))
    }
}

#[test]
fn saturated_queue_drops_notices_but_finishes_every_turn() -> Result<(), String>
{
    use std::sync::mpsc::sync_channel;

    let (mut lifecycle, mut pacer) = fixture()?;
    let (entered_tx, entered_rx) = sync_channel::<()>(0);
    let mut called = 0usize;
    let result = run_scoped_cache_retry_worker_bounded_progress(
        NativeCacheScopedBoundedProgressLimits::new(limit(1)?, limit(3)?),
        Resources::new(&mut lifecycle, &mut pacer),
        move |_current| {
            called = called.saturating_add(1);
            if called == 3 {
                entered_tx.send(()).map_err(|_error| "entry failed")?;
            }
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
        |_cancel, _notices| entered_rx.recv(),
    )
    .map_err(|error| format!("{error:?}"))?;
    if result.worker.run == Ok(RunStop::LimitReached { completed: 3 })
        && result.worker.supervisor.is_ok()
        && result.totals.enqueued == 1
        && result.totals.full >= 1
        && total(result.totals) == 3
    {
        Ok(())
    } else {
        Err(String::from(
            "full progress queue altered callback sequence",
        ))
    }
}

#[test]
fn explicit_receiver_drop_counts_missing_notices() -> Result<(), String> {
    use std::sync::mpsc::sync_channel;

    let (mut lifecycle, mut pacer) = fixture()?;
    let (release_tx, release_rx) = sync_channel::<()>(0);
    let mut called = 0usize;
    let result = run_scoped_cache_retry_worker_bounded_progress(
        NativeCacheScopedBoundedProgressLimits::new(limit(1)?, limit(2)?),
        Resources::new(&mut lifecycle, &mut pacer),
        move |_current| {
            called = called.saturating_add(1);
            if called == 2 {
                release_rx.recv().map_err(|_error| "release failed")?;
            }
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
        |_cancel, notices| {
            let first = notices.recv().map_err(|_error| "notice missing")?;
            drop(notices);
            release_tx.send(()).map_err(|_error| "release failed")?;
            Ok::<_, &'static str>(first)
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    if result.worker.run == Ok(RunStop::LimitReached { completed: 2 })
        && result.worker.supervisor
            == Ok(Notice {
                completed: 1,
                kind: Kind::Continued,
            })
        && result.totals.enqueued == 1
        && result.totals.full == 0
        && result.totals.receiver_gone == 1
        && total(result.totals) == 2
    {
        Ok(())
    } else {
        Err(String::from(
            "receiver drop did not retain exact loss count",
        ))
    }
}

#[test]
fn fallible_bounded_supervisor_cancels_on_first_notice() -> Result<(), String> {
    let (mut lifecycle, _default_pacer) = fixture()?;
    let mut pacer = pacing::NativeExecutableCacheLimitsRetryLifecyclePacer::new(
        nanos(5_000_000_000)?,
    );
    let mut called = 0usize;
    let result = run_scoped_cache_retry_worker_bounded_fallible_progress(
        NativeCacheScopedBoundedProgressLimits::new(limit(1)?, limit(4)?),
        Resources::new(&mut lifecycle, &mut pacer),
        |_current| {
            called = called.saturating_add(1);
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
        |_cancel, notices| {
            let _first = notices.recv().map_err(|_error| "notice missing")?;
            Err::<(), _>("observer failed")
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    if result.worker.run == Ok(RunStop::Cancelled { completed: 1 })
        && result.worker.supervisor
            == Err(worker::NativeCacheScopedSupervisorFailure {
                cancellation: Ok(true),
                error: "observer failed",
            })
        && called == 1
        && total(result.totals) == 1
        && result.totals.enqueued == 1
        && lifecycle.expected_cursor().is_some()
    {
        Ok(())
    } else {
        Err(String::from("fallible bounded supervisor failed to cancel"))
    }
}

#[test]
fn fallible_bounded_supervisor_success_preserves_all_turns()
-> Result<(), String> {
    let (mut lifecycle, mut pacer) = fixture()?;
    let result = run_scoped_cache_retry_worker_bounded_fallible_progress(
        NativeCacheScopedBoundedProgressLimits::new(limit(3)?, limit(3)?),
        Resources::new(&mut lifecycle, &mut pacer),
        |_current| {
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
        |_cancel, notices| {
            Ok::<_, &'static str>(notices.iter().collect::<Vec<_>>())
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    if result.worker.run == Ok(RunStop::LimitReached { completed: 3 })
        && result.worker.supervisor
            == Ok(vec![
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
            ])
        && result.totals.enqueued == 3
        && result.totals.full == 0
        && result.totals.receiver_gone == 0
    {
        Ok(())
    } else {
        Err(String::from(
            "successful supervisor mutated bounded turn result",
        ))
    }
}

#[test]
fn fallible_supervisor_and_callback_errors_remain_independent()
-> Result<(), String> {
    let (mut lifecycle, mut pacer) = fixture()?;
    let result = run_scoped_cache_retry_worker_bounded_fallible_progress(
        NativeCacheScopedBoundedProgressLimits::new(limit(1)?, limit(3)?),
        Resources::new(&mut lifecycle, &mut pacer),
        |_current| {
            Err::<ControlFlow<&'static str>, &'static str>("activation failed")
        },
        |_cancel, notices| {
            let observed = notices.recv().map_err(|_error| "missing error")?;
            if observed.kind == Kind::Failed {
                Err::<(), _>("supervisor failed")
            } else {
                Ok(())
            }
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    if result.worker.run
        == Err(TurnFailure::Turn {
            completed: 1,
            error: "activation failed",
        })
        && result.worker.supervisor
            == Err(worker::NativeCacheScopedSupervisorFailure {
                cancellation: Ok(true),
                error: "supervisor failed",
            })
        && total(result.totals) == 1
        && lifecycle.expected_cursor().is_some()
    {
        Ok(())
    } else {
        Err(String::from("supervisor failure erased callback error"))
    }
}

#[test]
fn repeated_cancellation_reports_exact_prior_request() -> Result<(), String> {
    let (mut lifecycle, mut pacer) = fixture()?;
    lifecycle.replace_expected_cursor(None);
    let result = run_scoped_cache_retry_worker_bounded_fallible_progress(
        NativeCacheScopedBoundedProgressLimits::new(limit(1)?, limit(3)?),
        Resources::new(&mut lifecycle, &mut pacer),
        |_current| {
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
        |cancel, _notices| {
            let first = cancel.cancel().map_err(|_error| "cancel failed")?;
            if first {
                Err::<(), _>("already cancelled")
            } else {
                Ok(())
            }
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    if result.worker.run == Ok(RunStop::CursorUnavailable { completed: 0 })
        && result.worker.supervisor
            == Err(worker::NativeCacheScopedSupervisorFailure {
                cancellation: Ok(false),
                error: "already cancelled",
            })
        && result.totals == NativeCacheScopedBoundedProgressTotals::default()
    {
        Ok(())
    } else {
        Err(String::from(
            "repeat request invented progress or lost outcome",
        ))
    }
}

#[test]
fn supervisor_panic_preserves_original_payload_and_revokes_cursor()
-> Result<(), String> {
    use std::panic::{AssertUnwindSafe, catch_unwind, resume_unwind};

    let (mut lifecycle, _default_pacer) = fixture()?;
    let mut pacer = pacing::NativeExecutableCacheLimitsRetryLifecyclePacer::new(
        nanos(5_000_000_000)?,
    );
    let bounds =
        NativeCacheScopedBoundedProgressLimits::new(limit(1)?, limit(4)?);
    let mut called = 0usize;
    let result = catch_unwind(AssertUnwindSafe(|| {
        let _outcome = run_scoped_cache_retry_worker_bounded_fallible_progress(
            bounds,
            Resources::new(&mut lifecycle, &mut pacer),
            |_current| {
                called = called.saturating_add(1);
                Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
            },
            |_cancel, notices| -> Result<(), &'static str> {
                let _notice = notices.recv();
                resume_unwind(Box::new("supervisor panic retained"));
            },
        );
    }));
    let payload = result.err().ok_or_else(|| {
        String::from("supervisor panic improperly returned success")
    })?;
    if payload.downcast_ref::<&'static str>().copied()
        == Some("supervisor panic retained")
        && lifecycle.expected_cursor().is_none()
        && called == 1
    {
        Ok(())
    } else {
        Err(String::from("supervisor panic leaked cursor authority"))
    }
}

#[test]
fn worker_panic_after_one_return_cannot_fabricate_bounded_totals()
-> Result<(), String> {
    use std::panic::resume_unwind;

    let (mut lifecycle, mut pacer) = fixture()?;
    let mut called = 0usize;
    let mut observed = Vec::new();
    let result = run_scoped_cache_retry_worker_bounded_progress(
        NativeCacheScopedBoundedProgressLimits::new(limit(2)?, limit(4)?),
        Resources::new(&mut lifecycle, &mut pacer),
        |_current| {
            called = called.saturating_add(1);
            if called == 2 {
                resume_unwind(Box::new("untrusted second callback"));
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
        Err(String::from("worker panic leaked typed progress authority"))
    }
}

#[test]
fn returned_callback_cursor_loss_blocks_next_turn() -> Result<(), String> {
    let (mut lifecycle, mut pacer) = fixture()?;
    let result = run_scoped_cache_retry_worker_bounded_progress(
        NativeCacheScopedBoundedProgressLimits::new(limit(1)?, limit(3)?),
        Resources::new(&mut lifecycle, &mut pacer),
        |current| {
            current.replace_expected_cursor(None);
            Ok::<_, &'static str>(ControlFlow::<&'static str>::Continue(()))
        },
        |_cancel, notices| notices.recv(),
    )
    .map_err(|error| format!("{error:?}"))?;
    if result.worker.run == Ok(RunStop::CursorUnavailable { completed: 1 })
        && result.worker.supervisor
            == Ok(Notice {
                completed: 1,
                kind: Kind::Continued,
            })
        && result.totals.enqueued == 1
        && total(result.totals) == 1
        && lifecycle.expected_cursor().is_none()
    {
        Ok(())
    } else {
        Err(String::from("progress overrode lost cursor authority"))
    }
}

#[test]
fn missing_final_stop_notice_never_erases_caller_stop() -> Result<(), String> {
    let (mut lifecycle, mut pacer) = fixture()?;
    let mut called = 0usize;
    let result = run_scoped_cache_retry_worker_bounded_progress(
        NativeCacheScopedBoundedProgressLimits::new(limit(1)?, limit(3)?),
        Resources::new(&mut lifecycle, &mut pacer),
        |_current| {
            called = called.saturating_add(1);
            if called == 2 {
                Ok::<_, &'static str>(ControlFlow::Break("typed stop"))
            } else {
                Ok(ControlFlow::Continue(()))
            }
        },
        |_cancel, notices| notices.recv(),
    )
    .map_err(|error| format!("{error:?}"))?;
    if result.worker.run
        == Ok(RunStop::CallerStopped {
            completed: 2,
            reason: "typed stop",
        })
        && result.worker.supervisor
            == Ok(Notice {
                completed: 1,
                kind: Kind::Continued,
            })
        && total(result.totals) == 2
        && lifecycle.expected_cursor().is_some()
    {
        Ok(())
    } else {
        Err(String::from(
            "missing stop notice erased terminal authority",
        ))
    }
}
