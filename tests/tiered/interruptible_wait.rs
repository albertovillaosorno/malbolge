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
//   - Regression evidence for elapsed and cooperative cancellation outcomes.
// - Must-Not:
//   - Assert precise scheduling latency, spawn detached workers, or infer guest
//     semantics.
// - Allows:
//   - Inputs: positive durations and explicit cancellation handle requests.
//   - Outputs: exact elapsed, cancelled, and idempotent cancellation evidence.
//   - Side effects: test-owned thread join and bounded relative wait only.
// - Split-When:
//   - Async wake path gains independent fixtures.
// - Merge-When:
//   - Product lifecycle regressions cover all host cancellation behavior.
// - Summary:
//   - Proves that cancellation never masquerades as elapsed wait evidence.
// - Description:
//   - Cross-thread cancellation test joins every spawned thread.
// - Usage:
//   - Compiled only under Rust test configuration.
// - Defaults:
//   - Fresh wait endpoints are uncancelled.
//

//! Regression coverage for the standard interruptible wait adapter.

use std::sync::mpsc;
use std::thread;

use super::*;

fn positive(value: u64) -> Result<NonZeroU64, String> {
    NonZeroU64::new(value)
        .ok_or_else(|| String::from("test wait duration must be positive"))
}

#[test]
fn uncancelled_positive_wait_reports_elapsed() -> Result<(), String> {
    let (mut wait, _cancel) =
        NativeContinuationSystemInterruptibleWait::new_pair();
    let outcome = wait
        .wait_nanoseconds(positive(1)?)
        .map_err(|error| format!("{error:?}"))?;
    if outcome == Outcome::Elapsed
        && !wait.is_cancelled().map_err(|error| format!("{error:?}"))?
    {
        Ok(())
    } else {
        Err(String::from("positive uncancelled wait did not elapse"))
    }
}

#[test]
fn cancellation_before_wait_is_sticky_and_idempotent() -> Result<(), String> {
    let (mut wait, cancel) =
        NativeContinuationSystemInterruptibleWait::new_pair();
    let first = cancel.cancel().map_err(|error| format!("{error:?}"))?;
    let second = cancel.cancel().map_err(|error| format!("{error:?}"))?;
    let outcome = wait
        .wait_nanoseconds(positive(3_000_000_000)?)
        .map_err(|error| format!("{error:?}"))?;
    if first
        && !second
        && wait.is_cancelled().map_err(|error| format!("{error:?}"))?
        && outcome == Outcome::Cancelled
    {
        Ok(())
    } else {
        Err(String::from("sticky cancellation contract drifted"))
    }
}

#[test]
fn cancellation_from_other_thread_wakes_waiter() -> Result<(), String> {
    let (mut wait, cancel) =
        NativeContinuationSystemInterruptibleWait::new_pair();
    let (ready_tx, ready_rx) = mpsc::channel();
    let worker = thread::spawn(move || -> Result<Outcome, String> {
        ready_tx.send(()).map_err(|error| format!("{error:?}"))?;
        wait.wait_nanoseconds(positive(3_000_000_000)?)
            .map_err(|error| format!("{error:?}"))
    });
    let signal_result = ready_rx
        .recv()
        .map_err(|error| format!("{error:?}"))
        .and_then(|()| cancel.cancel().map_err(|error| format!("{error:?}")));
    let outcome = worker
        .join()
        .map_err(|_panic| String::from("interruptible waiter panicked"))??;
    if signal_result? && outcome == Outcome::Cancelled {
        Ok(())
    } else {
        Err(String::from(
            "cross-thread cancellation did not wake waiter",
        ))
    }
}
