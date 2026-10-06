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

type CacheEvidence = super::NativeExecutableCacheLimitsEvidence;
type CacheRecommendation = super::NativeExecutableCacheLimitsRecommendation;
type PressureEvidence = super::NativeExecutableCacheLimitsPressureEvidence;
type ReuseEvidence = super::NativeExecutableCacheLimitsReuseEvidence;
type TwoSignalRecommendation =
    super::NativeExecutableCacheLimitsTwoSignalRecommendation;

fn two_signal_request(
    reuse_threshold: super::NativeExecutableCacheLimitsReuseThreshold,
    reuse_candidates: super::NativeExecutableCacheLimitsRecommendationSet,
    pressure_threshold: super::NativeExecutableCacheLimitsPressureThreshold,
    pressure_candidates: super::NativeExecutableCacheLimitsRecommendationSet,
) -> super::NativeExecutableCacheLimitsTwoSignalRequest {
    super::NativeExecutableCacheLimitsTwoSignalRequest::new(
        reuse_threshold,
        reuse_candidates,
        pressure_threshold,
        pressure_candidates,
    )
}

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

fn pressure_telemetry() -> NativeContinuationCachedRetryTelemetry {
    NativeContinuationCachedRetryTelemetry::from_test_counts([4, 8, 3, 0, 4, 2])
}

fn pressure_threshold(
    attempts: usize,
    maximum_evicted_keys: usize,
    maximum_retired_keys: usize,
) -> Result<super::NativeExecutableCacheLimitsPressureThreshold, String> {
    Ok(super::NativeExecutableCacheLimitsPressureThreshold::new(
        nonzero(attempts, "pressure attempts")?,
        maximum_evicted_keys,
        maximum_retired_keys,
    ))
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
fn two_signal_agreement_reconfigures_with_combined_evidence()
-> Result<(), String> {
    let current = limits(4)?;
    let agreed = weighted_limits(8, 12, 131_072)?;
    let arbitration =
        super::recommend_native_executable_cache_limits_from_reuse_and_pressure(
            pressure_telemetry(),
            current,
            &two_signal_request(
                threshold(4, 1, 1)?,
                super::NativeExecutableCacheLimitsRecommendationSet::new(
                    limits(2)?,
                    agreed,
                ),
                pressure_threshold(4, 2, 1)?,
                super::NativeExecutableCacheLimitsRecommendationSet::new(
                    limits(2)?,
                    agreed,
                ),
            ),
        );
    let TwoSignalRecommendation::Agreed {
        pressure,
        recommendation,
        reuse,
    } = arbitration
    else {
        return Err(String::from("ready cache signals did not agree"));
    };
    let CacheRecommendation::Reconfigure {
        evidence, recommended, ..
    } = recommendation
    else {
        return Err(String::from("cache agreement did not reconfigure"));
    };
    let CacheEvidence::Agreement {
        pressure: PressureEvidence::Pressured(violations),
        reuse:
            ReuseEvidence::Misses(
                super::NativeExecutableCacheLimitsReuseMiss::
                    BelowMinimumHitsPerAttempt,
            ),
    } = evidence
    else {
        return Err(String::from("cache agreement lost combined evidence"));
    };
    if recommended == agreed
        && pressure.limits() == Some(agreed)
        && reuse.limits() == Some(agreed)
        && violations.contains(
            super::NativeExecutableCacheLimitsPressureSignal::EvictedKeys,
        )
        && violations.contains(
            super::NativeExecutableCacheLimitsPressureSignal::RetiredKeys,
        )
        && arbitration.recommendation() == Some(recommendation)
    {
        Ok(())
    } else {
        Err(String::from("cache agreement evidence drifted"))
    }
}

#[test]
fn two_signal_agreement_retains_current_limits() -> Result<(), String> {
    let current = weighted_limits(4, 6, 65_536)?;
    let arbitration =
        super::recommend_native_executable_cache_limits_from_reuse_and_pressure(
            pressure_telemetry(),
            current,
            &two_signal_request(
                threshold(4, 1, 1)?,
                super::NativeExecutableCacheLimitsRecommendationSet::new(
                    limits(2)?,
                    current,
                ),
                pressure_threshold(4, 2, 1)?,
                super::NativeExecutableCacheLimitsRecommendationSet::new(
                    limits(2)?,
                    current,
                ),
            ),
        );
    let Some(recommendation) = arbitration.recommendation() else {
        return Err(String::from(
            "matching cache signals withheld current limits",
        ));
    };
    if matches!(
        recommendation,
        CacheRecommendation::Retain {
            evidence: CacheEvidence::Agreement { .. },
            limits,
            ..
        } if limits == current
    ) && recommendation.limits() == Some(current)
    {
        Ok(())
    } else {
        Err(String::from("cache agreement retain evidence drifted"))
    }
}

#[test]
fn two_signal_conflict_withholds_policy() -> Result<(), String> {
    let current = limits(4)?;
    let reuse_limits = limits(8)?;
    let pressure_limits = limits(2)?;
    let arbitration =
        super::recommend_native_executable_cache_limits_from_reuse_and_pressure(
            pressure_telemetry(),
            current,
            &two_signal_request(
                threshold(4, 1, 1)?,
                super::NativeExecutableCacheLimitsRecommendationSet::new(
                    limits(3)?,
                    reuse_limits,
                ),
                pressure_threshold(4, 3, 2)?,
                super::NativeExecutableCacheLimitsRecommendationSet::new(
                    pressure_limits,
                    limits(9)?,
                ),
            ),
        );
    if matches!(
        arbitration,
        TwoSignalRecommendation::Conflict {
            pressure,
            reuse,
        } if pressure.limits() == Some(pressure_limits)
            && reuse.limits() == Some(reuse_limits)
    ) && arbitration.recommendation().is_none()
    {
        Ok(())
    } else {
        Err(String::from("cache signal conflict authorized policy"))
    }
}

#[test]
fn two_signal_deferral_withholds_ready_peer() -> Result<(), String> {
    let current = limits(4)?;
    let arbitration =
        super::recommend_native_executable_cache_limits_from_reuse_and_pressure(
            pressure_telemetry(),
            current,
            &two_signal_request(
                threshold(5, 1, 1)?,
                super::NativeExecutableCacheLimitsRecommendationSet::new(
                    limits(2)?,
                    limits(8)?,
                ),
                pressure_threshold(4, 2, 1)?,
                super::NativeExecutableCacheLimitsRecommendationSet::new(
                    limits(2)?,
                    limits(8)?,
                ),
            ),
        );
    if matches!(
        arbitration,
        TwoSignalRecommendation::Deferred {
            pressure,
            reuse:
                CacheRecommendation::Deferred { .. },
        } if pressure.limits() == Some(limits(8)?)
    ) && arbitration.recommendation().is_none()
    {
        Ok(())
    } else {
        Err(String::from("cache signal deferral authorized ready peer"))
    }
}

#[test]
fn pressure_attempt_gate_defers_without_limits() -> Result<(), String> {
    let current = limits(2)?;
    let recommendation =
        super::recommend_native_executable_cache_limits_from_pressure(
            pressure_telemetry(),
            current,
            pressure_threshold(5, 3, 2)?,
            super::NativeExecutableCacheLimitsRecommendationSet::new(
                limits(4)?,
                limits(1)?,
            ),
        );
    let CacheRecommendation::Deferred {
        observed_attempts,
        required_attempts,
    } = recommendation
    else {
        return Err(String::from("pressure attempt gate selected limits"));
    };
    if observed_attempts == 4
        && required_attempts.get() == 5
        && recommendation.limits().is_none()
    {
        Ok(())
    } else {
        Err(String::from("pressure deferral evidence drifted"))
    }
}

#[test]
fn pressure_inclusive_maximums_select_meets_candidate() -> Result<(), String> {
    let current = limits(2)?;
    let meets = weighted_limits(5, 7, 65_536)?;
    let recommendation =
        super::recommend_native_executable_cache_limits_from_pressure(
            pressure_telemetry(),
            current,
            pressure_threshold(4, 3, 2)?,
            super::NativeExecutableCacheLimitsRecommendationSet::new(
                meets,
                limits(1)?,
            ),
        );
    let CacheRecommendation::Reconfigure {
        evidence,
        recommended,
        telemetry,
        ..
    } = recommendation
    else {
        return Err(String::from("inclusive pressure maximums did not meet"));
    };
    if evidence == CacheEvidence::Pressure(PressureEvidence::WithinMaximums)
        && recommended == meets
        && telemetry.evicted_keys() == 3
        && telemetry.retired_keys() == 2
        && recommendation.limits() == Some(meets)
    {
        Ok(())
    } else {
        Err(String::from("pressure maximum evidence drifted"))
    }
}

#[test]
fn pressure_retains_matching_candidate() -> Result<(), String> {
    let current = weighted_limits(3, 5, 32_768)?;
    let recommendation =
        super::recommend_native_executable_cache_limits_from_pressure(
            pressure_telemetry(),
            current,
            pressure_threshold(4, 3, 2)?,
            super::NativeExecutableCacheLimitsRecommendationSet::new(
                current,
                limits(1)?,
            ),
        );
    let CacheRecommendation::Retain { evidence, limits, .. } = recommendation
    else {
        return Err(String::from("matching pressure policy reconfigured"));
    };
    if evidence == CacheEvidence::Pressure(PressureEvidence::WithinMaximums)
        && limits == current
        && recommendation.limits() == Some(current)
    {
        Ok(())
    } else {
        Err(String::from("pressure retain evidence drifted"))
    }
}

#[test]
fn pressure_reports_simultaneous_violations() -> Result<(), String> {
    use super::NativeExecutableCacheLimitsPressureSignal::{
        EvictedKeys, RetiredKeys,
    };

    let current = limits(4)?;
    let misses = weighted_limits(8, 12, 131_072)?;
    let recommendation =
        super::recommend_native_executable_cache_limits_from_pressure(
            pressure_telemetry(),
            current,
            pressure_threshold(4, 2, 1)?,
            super::NativeExecutableCacheLimitsRecommendationSet::new(
                limits(2)?,
                misses,
            ),
        );
    let CacheRecommendation::Reconfigure {
        evidence, recommended, ..
    } = recommendation
    else {
        return Err(String::from("pressure violations did not reconfigure"));
    };
    let CacheEvidence::Pressure(PressureEvidence::Pressured(violations)) =
        evidence
    else {
        return Err(String::from("pressure violations lost source evidence"));
    };
    if violations.contains(EvictedKeys)
        && violations.contains(RetiredKeys)
        && !violations.is_empty()
        && recommended == misses
        && recommendation.limits() == Some(misses)
    {
        Ok(())
    } else {
        Err(String::from("simultaneous pressure evidence drifted"))
    }
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
    let CacheRecommendation::Deferred {
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
    let CacheRecommendation::Reconfigure {
        current: observed_current,
        evidence,
        recommended,
        telemetry: observed,
    } = recommendation
    else {
        return Err(String::from("exact reuse ratio did not reconfigure"));
    };
    if observed_current == current
        && evidence
            == CacheEvidence::Reuse(
                super::NativeExecutableCacheLimitsReuseEvidence::Meets,
            )
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
    let CacheRecommendation::Reconfigure {
        evidence, recommended, ..
    } = recommendation
    else {
        return Err(String::from(
            "weak reuse ratio did not select misses limits",
        ));
    };
    if evidence
        == CacheEvidence::Reuse(
            super::NativeExecutableCacheLimitsReuseEvidence::Misses(
                BelowMinimumHitsPerAttempt,
            ),
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
    let CacheRecommendation::Retain {
        evidence,
        limits,
        telemetry: observed,
    } = recommendation
    else {
        return Err(String::from(
            "matching reuse policy requested reconfigure",
        ));
    };
    if evidence
        == CacheEvidence::Reuse(
            super::NativeExecutableCacheLimitsReuseEvidence::Meets,
        )
        && limits == current
        && recommendation.limits() == Some(current)
        && observed.hits() == 2
    {
        Ok(())
    } else {
        Err(String::from("cache-limit retain recommendation drifted"))
    }
}
