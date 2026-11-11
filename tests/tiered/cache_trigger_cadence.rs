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
//   - Regression coverage for exact cache-policy trigger sequence cadence.
// - Must-Not:
//   - Read clocks, activate policy, mutate cache/storage, or spawn background
//     work.
// - Allows:
//   - Inputs: deterministic successful telemetry-window append evidence.
//   - Outputs: deterministic cadence eligibility evidence and cursor state.
//   - Side effects: test-local telemetry-window and cursor mutation only.
// - Split-When:
//   - Durable cursor or product lifecycle coverage gains independent ownership.
// - Merge-When:
//   - Parent cadence module no longer requires private regression access.
// - Summary:
//   - Proves defer, due, missed, replay, and exhaustion cadence semantics.
// - Description:
//   - Exact due consumption is the only transition that advances the cursor.
// - Usage:
//   - Compiled only under Rust test configuration.
// - Defaults:
//   - Missed due sequences fail closed without implicit catch-up.
//

//! Regression coverage for publication-sequence cache trigger cadence.

use std::num::{NonZeroU64, NonZeroUsize};

use crate::cached_cycle::{
    NativeContinuationCachedRetryTelemetry,
    NativeContinuationCachedRetryTelemetryWindow,
    NativeContinuationCachedRetryTelemetryWindowAppend,
};

type CadenceDecision = super::NativeExecutableCacheLimitsTriggerCadenceDecision;

fn nonzero_u64(value: u64) -> Result<NonZeroU64, String> {
    NonZeroU64::new(value)
        .ok_or_else(|| String::from("test cadence value must be positive"))
}

fn nonzero_usize(value: usize) -> Result<NonZeroUsize, String> {
    NonZeroUsize::new(value)
        .ok_or_else(|| String::from("test capacity must be positive"))
}

fn append(
    window: &mut NativeContinuationCachedRetryTelemetryWindow,
) -> Result<NativeContinuationCachedRetryTelemetryWindowAppend, String> {
    window
        .append(NativeContinuationCachedRetryTelemetry::default())
        .map_err(|error| error.to_string())
}

#[test]
fn cadence_defers_before_due_without_advancing() -> Result<(), String> {
    let mut window =
        NativeContinuationCachedRetryTelemetryWindow::new(nonzero_usize(2)?);
    let first = append(&mut window)?;
    let due = nonzero_u64(2)?;
    let mut cadence = super::NativeExecutableCacheLimitsTriggerCadence::new(
        due,
        nonzero_u64(3)?,
    );
    let decision = cadence.observe(&first);
    if decision
        == (CadenceDecision::Deferred {
            observed_sequence: 1,
            due_sequence: due,
        })
        && cadence.next_due_sequence() == Some(due)
    {
        Ok(())
    } else {
        Err(String::from("pre-due publication advanced cadence"))
    }
}

#[test]
fn cadence_exact_due_advances_by_interval() -> Result<(), String> {
    let mut window =
        NativeContinuationCachedRetryTelemetryWindow::new(nonzero_usize(2)?);
    let _first = append(&mut window)?;
    let second = append(&mut window)?;
    let mut cadence = super::NativeExecutableCacheLimitsTriggerCadence::new(
        nonzero_u64(2)?,
        nonzero_u64(3)?,
    );
    let next = nonzero_u64(5)?;
    let decision = cadence.observe(&second);
    if decision
        == (CadenceDecision::Due {
            observed_sequence: nonzero_u64(2)?,
            next_due_sequence: Some(next),
        })
        && cadence.interval() == nonzero_u64(3)?
        && cadence.next_due_sequence() == Some(next)
    {
        Ok(())
    } else {
        Err(String::from(
            "exact due publication did not advance cadence",
        ))
    }
}

#[test]
fn cadence_skipped_due_fails_closed_without_advancing() -> Result<(), String> {
    let mut window =
        NativeContinuationCachedRetryTelemetryWindow::new(nonzero_usize(3)?);
    let _first = append(&mut window)?;
    let _second = append(&mut window)?;
    let third = append(&mut window)?;
    let due = nonzero_u64(2)?;
    let mut cadence = super::NativeExecutableCacheLimitsTriggerCadence::new(
        due,
        nonzero_u64(3)?,
    );
    let decision = cadence.observe(&third);
    if decision
        == (CadenceDecision::Missed {
            observed_sequence: 3,
            due_sequence: due,
        })
        && cadence.next_due_sequence() == Some(due)
    {
        Ok(())
    } else {
        Err(String::from("missed cadence slot advanced implicitly"))
    }
}

#[test]
fn cadence_replay_of_consumed_due_cannot_trigger_twice() -> Result<(), String> {
    let mut window =
        NativeContinuationCachedRetryTelemetryWindow::new(nonzero_usize(2)?);
    let _first = append(&mut window)?;
    let second = append(&mut window)?;
    let mut cadence = super::NativeExecutableCacheLimitsTriggerCadence::new(
        nonzero_u64(2)?,
        nonzero_u64(3)?,
    );
    let first_decision = cadence.observe(&second);
    let replay = cadence.observe(&second);
    let next = nonzero_u64(5)?;
    if matches!(first_decision, CadenceDecision::Due { .. })
        && replay
            == (CadenceDecision::Deferred {
                observed_sequence: 2,
                due_sequence: next,
            })
        && cadence.next_due_sequence() == Some(next)
    {
        Ok(())
    } else {
        Err(String::from("consumed due publication triggered twice"))
    }
}

#[test]
fn cadence_supports_explicit_late_first_due() -> Result<(), String> {
    let mut window =
        NativeContinuationCachedRetryTelemetryWindow::new(nonzero_usize(3)?);
    let first = append(&mut window)?;
    let second = append(&mut window)?;
    let third = append(&mut window)?;
    let due = nonzero_u64(3)?;
    let mut cadence = super::NativeExecutableCacheLimitsTriggerCadence::new(
        due,
        nonzero_u64(2)?,
    );
    if !matches!(cadence.observe(&first), CadenceDecision::Deferred { .. })
        || !matches!(cadence.observe(&second), CadenceDecision::Deferred { .. })
        || !matches!(
            cadence.observe(&third),
            CadenceDecision::Due {
                observed_sequence,
                ..
            } if observed_sequence == due
        )
    {
        return Err(String::from("explicit late first due drifted"));
    }
    Ok(())
}

#[test]
fn cadence_exhaustion_stops_future_eligibility() -> Result<(), String> {
    let mut window =
        NativeContinuationCachedRetryTelemetryWindow::new(nonzero_usize(1)?);
    window.force_counters_for_test(0, u64::MAX - 1);
    let final_append = append(&mut window)?;
    let due = nonzero_u64(u64::MAX)?;
    let mut cadence = super::NativeExecutableCacheLimitsTriggerCadence::new(
        due,
        nonzero_u64(1)?,
    );
    let decision = cadence.observe(&final_append);
    let after = cadence.observe(&final_append);
    if decision
        == (CadenceDecision::Due {
            observed_sequence: due,
            next_due_sequence: None,
        })
        && after
            == (CadenceDecision::Exhausted {
                observed_sequence: u64::MAX,
            })
        && cadence.next_due_sequence().is_none()
    {
        Ok(())
    } else {
        Err(String::from("cadence exhaustion retained future authority"))
    }
}
