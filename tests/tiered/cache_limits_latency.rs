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
//   - Regression coverage for latency-driven cache-limit recommendation and
//     conservative agreement with window-scoped cache policy.
// - Must-Not:
//   - Read clocks, mutate production cache/storage, or redefine window policy.
// - Allows:
//   - Inputs: deterministic cumulative latency records and window plans.
//   - Outputs: deterministic latency recommendation/arbitration evidence.
//   - Side effects: test-local histogram/window mutation only.
// - Split-When:
//   - Latency policy gains durable activation lifecycle coverage.
// - Merge-When:
//   - Parent latency module no longer requires private regression access.
// - Summary:
//   - Proves exact latency gates, violations, agreement, and conflict behavior.
// - Description:
//   - Overflow thresholds use exact cumulative record evidence.
// - Usage:
//   - Compiled only under Rust test configuration.
// - Defaults:
//   - Missing latency or window authority cannot authorize cache limits.
//

//! Regression coverage for latency-driven cache-limit policy.

use std::num::{NonZeroU64, NonZeroUsize};

use crate::cached_cycle::{
    NativeContinuationCachedRetryLatencyHistogram,
    NativeContinuationCachedRetryLatencyRecord,
    NativeContinuationCachedRetryLatencySample,
    NativeContinuationCachedRetryTelemetry,
    NativeContinuationCachedRetryTelemetryWindow,
};
use crate::executable_cache_limits_precedence as cache_select;
use crate::executable_cache_limits_recommendation::{
    NativeExecutableCacheLimitsPressureThreshold,
    NativeExecutableCacheLimitsRecommendationSet,
    NativeExecutableCacheLimitsReuseThreshold,
    NativeExecutableCacheLimitsTwoSignalRequest,
};
use crate::executable_cache_limits_window_plan::{
    NativeExecutableCacheLimitsWindowPlan,
    plan_native_executable_cache_limits_after_window_append,
};
use crate::execution_native::NativeExecutableSequenceCacheLimits;

type CachePrecedence = cache_select::NativeExecutableCacheLimitsPrecedence;
type LatencyEvidence = super::NativeExecutableCacheLimitsLatencyEvidence;

fn nonzero(value: usize) -> Result<NonZeroUsize, String> {
    NonZeroUsize::new(value)
        .ok_or_else(|| String::from("test value must be positive"))
}

fn limits(
    entries: usize,
) -> Result<NativeExecutableSequenceCacheLimits, String> {
    nonzero(entries).map(NativeExecutableSequenceCacheLimits::new)
}

fn latency_record(
    samples: &[u64],
) -> Result<NativeContinuationCachedRetryLatencyRecord, String> {
    let mut histogram =
        NativeContinuationCachedRetryLatencyHistogram::new(vec![50, 100, 200])
            .map_err(|error| error.to_string())?;
    let mut record = None;
    for sample in samples {
        record = Some(
            histogram
                .record(NativeContinuationCachedRetryLatencySample::new(
                    *sample,
                ))
                .map_err(|error| error.to_string())?,
        );
    }
    record.ok_or_else(|| String::from("latency fixture needs one sample"))
}

fn latency_threshold(
    required_samples: usize,
    average: u64,
    maximum: u64,
) -> Result<super::NativeExecutableCacheLimitsLatencyThreshold, String> {
    Ok(super::NativeExecutableCacheLimitsLatencyThreshold::new(
        nonzero(required_samples)?,
        average,
        maximum,
    ))
}

fn latency_threshold_with_overflow(
    required_samples: usize,
    average: u64,
    maximum: u64,
    overflow: usize,
) -> Result<super::NativeExecutableCacheLimitsLatencyThreshold, String> {
    Ok(
        super::NativeExecutableCacheLimitsLatencyThreshold::new_with_overflow(
            nonzero(required_samples)?,
            average,
            maximum,
            overflow,
        ),
    )
}

fn window_plan(
    reuse_misses: NativeExecutableSequenceCacheLimits,
    pressure_misses: NativeExecutableSequenceCacheLimits,
    precedence: CachePrecedence,
) -> Result<NativeExecutableCacheLimitsWindowPlan, String> {
    let telemetry = NativeContinuationCachedRetryTelemetry::from_test_counts([
        4, 8, 3, 0, 4, 2,
    ]);
    let mut window =
        NativeContinuationCachedRetryTelemetryWindow::new(nonzero(2)?);
    let append = window
        .append(telemetry)
        .map_err(|error| error.to_string())?;
    let one = NonZeroU64::new(1)
        .ok_or_else(|| String::from("test ratio must be positive"))?;
    let request = NativeExecutableCacheLimitsTwoSignalRequest::new(
        NativeExecutableCacheLimitsReuseThreshold::new(nonzero(4)?, one, one),
        NativeExecutableCacheLimitsRecommendationSet::new(
            limits(3)?,
            reuse_misses,
        ),
        NativeExecutableCacheLimitsPressureThreshold::new(nonzero(4)?, 2, 1),
        NativeExecutableCacheLimitsRecommendationSet::new(
            limits(3)?,
            pressure_misses,
        ),
    );
    Ok(plan_native_executable_cache_limits_after_window_append(
        &append,
        limits(4)?,
        &request,
        precedence,
    ))
}

#[test]
fn latency_sample_gate_defers_without_limits() -> Result<(), String> {
    let record = latency_record(&[10, 20])?;
    let recommendation =
        super::recommend_native_executable_cache_limits_from_latency(
            record,
            super::NativeExecutableCacheLimitsLatencyRequest::new(
                latency_threshold(3, 20, 30)?,
                NativeExecutableCacheLimitsRecommendationSet::new(
                    limits(3)?,
                    limits(6)?,
                ),
            ),
        );
    if matches!(
        recommendation,
        super::NativeExecutableCacheLimitsLatencyRecommendation::Deferred {
            observed_samples: 2,
            required_samples,
        } if required_samples.get() == 3
    ) && recommendation.limits().is_none()
    {
        Ok(())
    } else {
        Err(String::from("latency sample gate authorized limits"))
    }
}

#[test]
fn latency_inclusive_maxima_select_meets_candidate() -> Result<(), String> {
    let meets = limits(3)?;
    let record = latency_record(&[20, 40])?;
    let recommendation =
        super::recommend_native_executable_cache_limits_from_latency(
            record,
            super::NativeExecutableCacheLimitsLatencyRequest::new(
                latency_threshold(2, 30, 40)?,
                NativeExecutableCacheLimitsRecommendationSet::new(
                    meets,
                    limits(6)?,
                ),
            ),
        );
    if matches!(
        recommendation,
        super::NativeExecutableCacheLimitsLatencyRecommendation::Ready {
            evidence: LatencyEvidence::WithinMaximums,
            limits,
            record: observed,
        } if limits == meets && observed == record
    ) && recommendation.limits() == Some(meets)
    {
        Ok(())
    } else {
        Err(String::from("inclusive latency maxima did not meet"))
    }
}

#[test]
fn latency_inclusive_overflow_maximum_selects_meets() -> Result<(), String> {
    let meets = limits(3)?;
    let record = latency_record(&[250, 20])?;
    let recommendation =
        super::recommend_native_executable_cache_limits_from_latency(
            record,
            super::NativeExecutableCacheLimitsLatencyRequest::new(
                latency_threshold_with_overflow(2, 200, 300, 1)?,
                NativeExecutableCacheLimitsRecommendationSet::new(
                    meets,
                    limits(6)?,
                ),
            ),
        );
    if record.above_maximum() == 1
        && recommendation.limits() == Some(meets)
        && matches!(
            recommendation,
            super::NativeExecutableCacheLimitsLatencyRecommendation::Ready {
                evidence: LatencyEvidence::WithinMaximums,
                ..
            }
        )
    {
        Ok(())
    } else {
        Err(String::from("inclusive overflow maximum did not meet"))
    }
}

#[test]
fn latency_overflow_violation_selects_misses() -> Result<(), String> {
    use super::NativeExecutableCacheLimitsLatencySignal::OverflowSamples;

    let misses = limits(6)?;
    let record = latency_record(&[250, 20])?;
    let recommendation =
        super::recommend_native_executable_cache_limits_from_latency(
            record,
            super::NativeExecutableCacheLimitsLatencyRequest::new(
                latency_threshold_with_overflow(2, 200, 300, 0)?,
                NativeExecutableCacheLimitsRecommendationSet::new(
                    limits(3)?,
                    misses,
                ),
            ),
        );
    let super::NativeExecutableCacheLimitsLatencyRecommendation::Ready {
        evidence: LatencyEvidence::Misses(violations),
        limits,
        ..
    } = recommendation
    else {
        return Err(String::from("overflow violation did not select misses"));
    };
    if record.above_maximum() == 1
        && violations.contains(OverflowSamples)
        && limits == misses
    {
        Ok(())
    } else {
        Err(String::from("overflow violation evidence drifted"))
    }
}

#[test]
fn latency_reports_simultaneous_average_and_maximum_violations()
-> Result<(), String> {
    use super::NativeExecutableCacheLimitsLatencySignal::{
        AverageNanoseconds, MaximumNanoseconds,
    };

    let misses = limits(6)?;
    let record = latency_record(&[100, 100, 1, 1])?;
    let recommendation =
        super::recommend_native_executable_cache_limits_from_latency(
            record,
            super::NativeExecutableCacheLimitsLatencyRequest::new(
                latency_threshold(4, 40, 80)?,
                NativeExecutableCacheLimitsRecommendationSet::new(
                    limits(3)?,
                    misses,
                ),
            ),
        );
    let super::NativeExecutableCacheLimitsLatencyRecommendation::Ready {
        evidence: LatencyEvidence::Misses(violations),
        limits,
        ..
    } = recommendation
    else {
        return Err(String::from("latency violations did not select misses"));
    };
    if violations.contains(AverageNanoseconds)
        && violations.contains(MaximumNanoseconds)
        && !violations.is_empty()
        && limits == misses
    {
        Ok(())
    } else {
        Err(String::from("simultaneous latency evidence drifted"))
    }
}

#[test]
fn window_and_latency_agreement_preserves_window_recommendation()
-> Result<(), String> {
    let candidate = limits(2)?;
    let window =
        window_plan(candidate, candidate, CachePrecedence::AgreementOnly)?;
    let record = latency_record(&[100, 100, 1, 1])?;
    let plan = super::plan_native_executable_cache_limits_with_latency(
        &window,
        record,
        super::NativeExecutableCacheLimitsLatencyRequest::new(
            latency_threshold(4, 40, 80)?,
            NativeExecutableCacheLimitsRecommendationSet::new(
                limits(3)?,
                candidate,
            ),
        ),
    );
    let recommendation = plan.recommendation().ok_or_else(|| {
        String::from("latency agreement withheld window policy")
    })?;
    if matches!(
        plan,
        super::NativeExecutableCacheLimitsWindowLatencyPlan::Agreed {
            latency,
            window: observed,
            ..
        } if latency.limits() == Some(candidate) && observed == window
    ) && recommendation.limits() == Some(candidate)
    {
        Ok(())
    } else {
        Err(String::from("window/latency agreement evidence drifted"))
    }
}

#[test]
fn window_and_latency_conflict_withholds_authority() -> Result<(), String> {
    let window_limits = limits(2)?;
    let latency_limits = limits(8)?;
    let window = window_plan(
        window_limits,
        window_limits,
        CachePrecedence::AgreementOnly,
    )?;
    let plan = super::plan_native_executable_cache_limits_with_latency(
        &window,
        latency_record(&[100, 100, 1, 1])?,
        super::NativeExecutableCacheLimitsLatencyRequest::new(
            latency_threshold(4, 40, 80)?,
            NativeExecutableCacheLimitsRecommendationSet::new(
                limits(3)?,
                latency_limits,
            ),
        ),
    );
    if matches!(
        plan,
        super::NativeExecutableCacheLimitsWindowLatencyPlan::Conflict {
            latency,
            window: observed,
        } if latency.limits() == Some(latency_limits) && observed == window
    ) && plan.recommendation().is_none()
    {
        Ok(())
    } else {
        Err(String::from("latency conflict authorized window policy"))
    }
}

#[test]
fn missing_window_authority_stays_deferred_with_ready_latency()
-> Result<(), String> {
    let window =
        window_plan(limits(8)?, limits(2)?, CachePrecedence::AgreementOnly)?;
    if window.recommendation().is_some() {
        return Err(String::from("window fixture unexpectedly authoritative"));
    }
    let latency_limits = limits(2)?;
    let plan = super::plan_native_executable_cache_limits_with_latency(
        &window,
        latency_record(&[100, 100, 1, 1])?,
        super::NativeExecutableCacheLimitsLatencyRequest::new(
            latency_threshold(4, 40, 80)?,
            NativeExecutableCacheLimitsRecommendationSet::new(
                limits(3)?,
                latency_limits,
            ),
        ),
    );
    if matches!(
        plan,
        super::NativeExecutableCacheLimitsWindowLatencyPlan::Deferred {
            latency,
            window: observed,
        } if latency.limits() == Some(latency_limits) && observed == window
    ) && plan.recommendation().is_none()
    {
        Ok(())
    } else {
        Err(String::from("latency overrode missing window authority"))
    }
}
