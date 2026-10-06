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
//   - Root-tree regression coverage for executable cache-limit recommendation.
// - Must-Not:
//   - Define production policy or mutate executable-cache state.
// - Allows:
//   - Inputs: parent recommendation API and deterministic telemetry fixtures.
//   - Outputs: deterministic recommendation evidence.
//   - Side effects: none.
// - Split-When:
//   - Recommendation requires an independent integration lifecycle.
// - Merge-When:
//   - Parent recommendation no longer requires private regression access.
// - Summary:
//   - Proves reuse-driven cache-limit recommendation is pure and exact.
// - Description:
//   - Uses test-only retry-attempt evidence to build canonical telemetry.
// - Usage:
//   - Compiled only under Rust test configuration.
// - Defaults:
//   - No test publishes or applies recommended cache limits.
//

//! Regression coverage for pure executable-cache limit recommendation.

use std::num::{NonZeroU64, NonZeroUsize};

use crate::cached_cycle::{
    NativeContinuationCachedRetryAttempt,
    NativeContinuationCachedRetryTelemetry, summarize_cached_retry_attempts,
};
use crate::execution_native::{
    NativeExecutableSequenceCacheLimits,
    NativeExecutableSequenceLeaseCacheDisposition,
};

fn nonzero(value: usize, label: &str) -> Result<NonZeroUsize, String> {
    NonZeroUsize::new(value).ok_or_else(|| format!("{label} must be positive"))
}

fn nonzero_u64(value: u64, label: &str) -> Result<NonZeroU64, String> {
    NonZeroU64::new(value).ok_or_else(|| format!("{label} must be positive"))
}

fn telemetry() -> Result<NativeContinuationCachedRetryTelemetry, String> {
    summarize_cached_retry_attempts(&[
        NativeContinuationCachedRetryAttempt::from_test_evidence(
            1,
            2,
            NativeExecutableSequenceLeaseCacheDisposition::Hit,
        ),
        NativeContinuationCachedRetryAttempt::from_test_evidence(
            2,
            3,
            NativeExecutableSequenceLeaseCacheDisposition::Hit,
        ),
    ])
    .map_err(|error| error.to_string())
}

fn limits(
    entries: usize,
) -> Result<NativeExecutableSequenceCacheLimits, String> {
    Ok(NativeExecutableSequenceCacheLimits::new(nonzero(
        entries,
        "cache entries",
    )?))
}

fn weighted_limits(
    entries: usize,
    mappings: usize,
    bytes: usize,
) -> Result<NativeExecutableSequenceCacheLimits, String> {
    Ok(limits(entries)?
        .with_mapping_limit(nonzero(mappings, "cache mappings")?)
        .with_mapped_byte_limit(nonzero(bytes, "cache bytes")?))
}

fn threshold(
    attempts: usize,
    numerator: u64,
    denominator: u64,
) -> Result<super::NativeExecutableCacheLimitsReuseThreshold, String> {
    Ok(super::NativeExecutableCacheLimitsReuseThreshold::new(
        nonzero(attempts, "required attempts")?,
        nonzero_u64(numerator, "reuse numerator")?,
        nonzero_u64(denominator, "reuse denominator")?,
    ))
}

#[test]
fn insufficient_attempts_defer_without_limits() -> Result<(), String> {
    let current = limits(2)?;
    let candidates = super::NativeExecutableCacheLimitsRecommendationSet::new(
        limits(4)?,
        limits(1)?,
    );
    let recommendation =
        super::recommend_native_executable_cache_limits_from_reuse(
            telemetry()?,
            current,
            threshold(3, 1, 1)?,
            candidates,
        );
    let super::NativeExecutableCacheLimitsRecommendation::Deferred {
        observed_attempts,
        required_attempts,
    } = recommendation
    else {
        return Err(String::from(
            "insufficient reuse evidence selected limits",
        ));
    };
    if observed_attempts == 2
        && required_attempts.get() == 3
        && recommendation.limits().is_none()
    {
        Ok(())
    } else {
        Err(String::from("cache-limit deferral evidence drifted"))
    }
}

#[test]
fn exact_reuse_ratio_selects_meets_candidate() -> Result<(), String> {
    let current = limits(2)?;
    let meets = weighted_limits(4, 8, 65_536)?;
    let misses = limits(1)?;
    let recommendation =
        super::recommend_native_executable_cache_limits_from_reuse(
            telemetry()?,
            current,
            threshold(2, 1, 1)?,
            super::NativeExecutableCacheLimitsRecommendationSet::new(
                meets, misses,
            ),
        );
    let super::NativeExecutableCacheLimitsRecommendation::Reconfigure {
        current: observed_current,
        evidence,
        recommended,
        telemetry: observed,
    } = recommendation
    else {
        return Err(String::from("exact reuse ratio did not reconfigure"));
    };
    if observed_current == current
        && evidence == super::NativeExecutableCacheLimitsReuseEvidence::Meets
        && recommended == meets
        && recommendation.limits() == Some(meets)
        && observed.attempts() == 2
        && observed.hits() == 2
    {
        Ok(())
    } else {
        Err(String::from("cache-limit meets recommendation drifted"))
    }
}

#[test]
fn weak_reuse_ratio_selects_misses_candidate() -> Result<(), String> {
    use super::NativeExecutableCacheLimitsReuseMiss::BelowMinimumHitsPerAttempt;

    let current = limits(4)?;
    let meets = limits(6)?;
    let misses = weighted_limits(1, 2, 16_384)?;
    let recommendation =
        super::recommend_native_executable_cache_limits_from_reuse(
            telemetry()?,
            current,
            threshold(2, 3, 2)?,
            super::NativeExecutableCacheLimitsRecommendationSet::new(
                meets, misses,
            ),
        );
    let super::NativeExecutableCacheLimitsRecommendation::Reconfigure {
        evidence,
        recommended,
        ..
    } = recommendation
    else {
        return Err(String::from(
            "weak reuse ratio did not select misses limits",
        ));
    };
    if evidence
        == super::NativeExecutableCacheLimitsReuseEvidence::Misses(
            BelowMinimumHitsPerAttempt,
        )
        && recommended == misses
        && recommendation.limits() == Some(misses)
    {
        Ok(())
    } else {
        Err(String::from("cache-limit misses recommendation drifted"))
    }
}

#[test]
fn selected_current_limits_retain_policy() -> Result<(), String> {
    let current = weighted_limits(3, 5, 32_768)?;
    let recommendation =
        super::recommend_native_executable_cache_limits_from_reuse(
            telemetry()?,
            current,
            threshold(2, 1, 1)?,
            super::NativeExecutableCacheLimitsRecommendationSet::new(
                current,
                limits(1)?,
            ),
        );
    let super::NativeExecutableCacheLimitsRecommendation::Retain {
        evidence,
        limits,
        telemetry: observed,
    } = recommendation
    else {
        return Err(String::from(
            "matching reuse policy requested reconfigure",
        ));
    };
    if evidence == super::NativeExecutableCacheLimitsReuseEvidence::Meets
        && limits == current
        && recommendation.limits() == Some(current)
        && observed.hits() == 2
    {
        Ok(())
    } else {
        Err(String::from("cache-limit retain recommendation drifted"))
    }
}
