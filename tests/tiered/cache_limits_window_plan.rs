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
//   - Regression coverage for telemetry-window cache-policy planning.
// - Must-Not:
//   - Activate cache limits, publish durable state, or redefine window totals.
// - Allows:
//   - Inputs: deterministic window appends and caller-owned cache policy.
//   - Outputs: deterministic precedence-selection plans.
//   - Side effects: test-local telemetry-window mutation only.
// - Split-When:
//   - Planner gains an independent durable or activation lifecycle.
// - Merge-When:
//   - Parent planner no longer requires private regression access.
// - Summary:
//   - Proves policy consumes already-published retained aggregate telemetry.
// - Description:
//   - Aggregate readiness and FIFO eviction semantics remain window-owned.
// - Usage:
//   - Compiled only under Rust test configuration.
// - Defaults:
//   - No plan mutates cache or durable state.
//

//! Regression coverage for telemetry-window cache-limit policy planning.

use std::num::{NonZeroU64, NonZeroUsize};

use crate::cached_cycle::{
    NativeContinuationCachedRetryTelemetry,
    NativeContinuationCachedRetryTelemetryWindow,
};
use crate::executable_cache_limits_precedence::{
    NativeExecutableCacheLimitsPrecedence,
    NativeExecutableCacheLimitsPrecedenceSelection,
};
use crate::executable_cache_limits_recommendation::{
    NativeExecutableCacheLimitsPressureThreshold,
    NativeExecutableCacheLimitsRecommendationSet,
    NativeExecutableCacheLimitsReuseThreshold,
    NativeExecutableCacheLimitsTwoSignalRequest,
};
use crate::execution_native::NativeExecutableSequenceCacheLimits;

fn limits(
    entries: usize,
) -> Result<NativeExecutableSequenceCacheLimits, String> {
    NonZeroUsize::new(entries)
        .map(NativeExecutableSequenceCacheLimits::new)
        .ok_or_else(|| String::from("cache limit must be positive"))
}

fn nonzero(value: usize) -> Result<NonZeroUsize, String> {
    NonZeroUsize::new(value)
        .ok_or_else(|| String::from("test value must be positive"))
}

fn request(
    attempts: usize,
    reuse_misses: NativeExecutableSequenceCacheLimits,
    pressure_misses: NativeExecutableSequenceCacheLimits,
) -> Result<NativeExecutableCacheLimitsTwoSignalRequest, String> {
    let one = NonZeroU64::new(1)
        .ok_or_else(|| String::from("test ratio must be positive"))?;
    Ok(NativeExecutableCacheLimitsTwoSignalRequest::new(
        NativeExecutableCacheLimitsReuseThreshold::new(
            nonzero(attempts)?,
            one,
            one,
        ),
        NativeExecutableCacheLimitsRecommendationSet::new(
            limits(3)?,
            reuse_misses,
        ),
        NativeExecutableCacheLimitsPressureThreshold::new(
            nonzero(attempts)?,
            2,
            1,
        ),
        NativeExecutableCacheLimitsRecommendationSet::new(
            limits(3)?,
            pressure_misses,
        ),
    ))
}

fn telemetry(counts: [usize; 6]) -> NativeContinuationCachedRetryTelemetry {
    NativeContinuationCachedRetryTelemetry::from_test_counts(counts)
}

#[test]
fn plan_uses_published_window_totals_not_latest_observation()
-> Result<(), String> {
    let mut window =
        NativeContinuationCachedRetryTelemetryWindow::new(nonzero(2)?);
    let _first = window
        .append(telemetry([2, 4, 1, 0, 2, 1]))
        .map_err(|error| error.to_string())?;
    let second = window
        .append(telemetry([2, 4, 2, 0, 2, 1]))
        .map_err(|error| error.to_string())?;
    let current = limits(4)?;
    let pressure_limits = limits(2)?;
    let plan = super::plan_native_executable_cache_limits_after_window_append(
        &second,
        current,
        &request(4, limits(8)?, pressure_limits)?,
        NativeExecutableCacheLimitsPrecedence::Pressure,
    );
    let NativeExecutableCacheLimitsPrecedenceSelection::Selected {
        recommendation,
        ..
    } = plan.selection()
    else {
        return Err(String::from("window totals did not authorize precedence"));
    };
    if second.observation().telemetry().attempts() == 2
        && second.totals().attempts() == 4
        && recommendation.limits() == Some(pressure_limits)
        && plan.recommendation() == Some(recommendation)
        && plan.append() == second
    {
        Ok(())
    } else {
        Err(String::from("window-total policy plan drifted"))
    }
}

#[test]
fn plan_respects_fifo_eviction_before_recommendation() -> Result<(), String> {
    let mut window =
        NativeContinuationCachedRetryTelemetryWindow::new(nonzero(1)?);
    let _first = window
        .append(telemetry([4, 8, 3, 0, 4, 2]))
        .map_err(|error| error.to_string())?;
    let second = window
        .append(telemetry([4, 8, 0, 4, 0, 0]))
        .map_err(|error| error.to_string())?;
    let plan = super::plan_native_executable_cache_limits_after_window_append(
        &second,
        limits(4)?,
        &request(4, limits(8)?, limits(2)?)?,
        NativeExecutableCacheLimitsPrecedence::Pressure,
    );
    let recommendation = plan
        .recommendation()
        .ok_or_else(|| String::from("evicted evidence still blocked policy"))?;
    if second.evicted().is_some()
        && second.totals().evicted_keys() == 0
        && second.totals().hits() == 4
        && recommendation.limits() == Some(limits(3)?)
    {
        Ok(())
    } else {
        Err(String::from(
            "FIFO eviction did not precede policy planning",
        ))
    }
}

#[test]
fn plan_preserves_deferred_window_evidence() -> Result<(), String> {
    let mut window =
        NativeContinuationCachedRetryTelemetryWindow::new(nonzero(2)?);
    let append = window
        .append(telemetry([2, 4, 1, 0, 2, 1]))
        .map_err(|error| error.to_string())?;
    let plan = super::plan_native_executable_cache_limits_after_window_append(
        &append,
        limits(4)?,
        &request(4, limits(8)?, limits(2)?)?,
        NativeExecutableCacheLimitsPrecedence::Pressure,
    );
    if matches!(
        plan.selection(),
        NativeExecutableCacheLimitsPrecedenceSelection::Deferred { .. }
    ) && plan.recommendation().is_none()
        && plan.append() == append
    {
        Ok(())
    } else {
        Err(String::from("window planner overrode deferred evidence"))
    }
}
