// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Exact checked arithmetic for retained cached-retry telemetry summaries.
// - Must-Not:
//   - Mutate a window, select retention policy, or hide overflow/underflow.
// - Allows:
//   - Inputs: exact summaries, observation sequences, and retained slices.
//   - Outputs: exact aggregate summaries or stable counter evidence.
//   - Side effects: none.
// - Split-When:
//   - New metric families require independent arithmetic or error categories.
// - Merge-When:
//   - One summary type owns all exact arithmetic internally.
// - Summary:
//   - Adds, subtracts, and folds cached-retry telemetry without saturation.
// - Description:
//   - Every failure identifies the exact sequence and counter involved.
// - Usage:
//   - Used by append, capacity reconfiguration, and snapshot validation.
// - Defaults:
//   - Empty retained slices aggregate to the exact zero summary.
//

//! Exact arithmetic for cached-retry telemetry retention.

use super::*;

pub(super) fn add_telemetry(
    left: NativeContinuationCachedRetryTelemetry,
    right: NativeContinuationCachedRetryTelemetry,
    sequence: u64,
) -> Result<
    NativeContinuationCachedRetryTelemetry,
    NativeContinuationCachedRetryTelemetryWindowError,
> {
    let attempts = checked_add_counter(
        left.attempts(),
        right.attempts(),
        sequence,
        NativeContinuationCachedRetryTelemetryWindowCounter::Attempts,
    )?;
    let completed_steps = checked_add_counter(
        left.completed_steps(),
        right.completed_steps(),
        sequence,
        NativeContinuationCachedRetryTelemetryWindowCounter::CompletedSteps,
    )?;
    let evicted_keys = checked_add_counter(
        left.evicted_keys(),
        right.evicted_keys(),
        sequence,
        NativeContinuationCachedRetryTelemetryWindowCounter::EvictedKeys,
    )?;
    let hits = checked_add_counter(
        left.hits(),
        right.hits(),
        sequence,
        NativeContinuationCachedRetryTelemetryWindowCounter::Hits,
    )?;
    let insertions = checked_add_counter(
        left.insertions(),
        right.insertions(),
        sequence,
        NativeContinuationCachedRetryTelemetryWindowCounter::Insertions,
    )?;
    let retired_keys = checked_add_counter(
        left.retired_keys(),
        right.retired_keys(),
        sequence,
        NativeContinuationCachedRetryTelemetryWindowCounter::RetiredKeys,
    )?;
    Ok(NativeContinuationCachedRetryTelemetry::from_counts([
        attempts,
        completed_steps,
        evicted_keys,
        hits,
        insertions,
        retired_keys,
    ]))
}

pub(super) fn aggregate_telemetry_observations(
    observations: &[NativeContinuationCachedRetryTelemetryObservation],
) -> Result<
    NativeContinuationCachedRetryTelemetry,
    NativeContinuationCachedRetryTelemetryWindowError,
> {
    observations.iter().try_fold(
        NativeContinuationCachedRetryTelemetry::empty(),
        |totals, observation| {
            add_telemetry(
                totals,
                observation.telemetry(),
                observation.sequence(),
            )
        },
    )
}

pub(super) fn subtract_telemetry(
    left: NativeContinuationCachedRetryTelemetry,
    right: NativeContinuationCachedRetryTelemetry,
    sequence: u64,
) -> Result<
    NativeContinuationCachedRetryTelemetry,
    NativeContinuationCachedRetryTelemetryWindowError,
> {
    let attempts = checked_sub_counter(
        left.attempts(),
        right.attempts(),
        sequence,
        NativeContinuationCachedRetryTelemetryWindowCounter::Attempts,
    )?;
    let completed_steps = checked_sub_counter(
        left.completed_steps(),
        right.completed_steps(),
        sequence,
        NativeContinuationCachedRetryTelemetryWindowCounter::CompletedSteps,
    )?;
    let evicted_keys = checked_sub_counter(
        left.evicted_keys(),
        right.evicted_keys(),
        sequence,
        NativeContinuationCachedRetryTelemetryWindowCounter::EvictedKeys,
    )?;
    let hits = checked_sub_counter(
        left.hits(),
        right.hits(),
        sequence,
        NativeContinuationCachedRetryTelemetryWindowCounter::Hits,
    )?;
    let insertions = checked_sub_counter(
        left.insertions(),
        right.insertions(),
        sequence,
        NativeContinuationCachedRetryTelemetryWindowCounter::Insertions,
    )?;
    let retired_keys = checked_sub_counter(
        left.retired_keys(),
        right.retired_keys(),
        sequence,
        NativeContinuationCachedRetryTelemetryWindowCounter::RetiredKeys,
    )?;
    Ok(NativeContinuationCachedRetryTelemetry::from_counts([
        attempts,
        completed_steps,
        evicted_keys,
        hits,
        insertions,
        retired_keys,
    ]))
}

fn checked_add_counter(
    left: usize,
    right: usize,
    sequence: u64,
    counter: NativeContinuationCachedRetryTelemetryWindowCounter,
) -> Result<usize, NativeContinuationCachedRetryTelemetryWindowError> {
    left.checked_add(right).ok_or(
        NativeContinuationCachedRetryTelemetryWindowError::AggregateOverflow {
            sequence,
            counter,
        },
    )
}

fn checked_sub_counter(
    left: usize,
    right: usize,
    sequence: u64,
    counter: NativeContinuationCachedRetryTelemetryWindowCounter,
) -> Result<usize, NativeContinuationCachedRetryTelemetryWindowError> {
    left.checked_sub(right).ok_or(
        NativeContinuationCachedRetryTelemetryWindowError::AggregateUnderflow {
            sequence,
            counter,
        },
    )
}
