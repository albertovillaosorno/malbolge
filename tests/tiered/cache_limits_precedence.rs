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
//   - Regression coverage for explicit cache-limit precedence selection.
// - Must-Not:
//   - Mutate caches, publish policy, or redefine recommendation evidence.
// - Allows:
//   - Inputs: deterministic reuse/pressure arbitration fixtures.
//   - Outputs: deterministic precedence-selection evidence.
//   - Side effects: none.
// - Split-When:
//   - Precedence requires independent publication lifecycle coverage.
// - Merge-When:
//   - Parent precedence module no longer requires private regression access.
// - Summary:
//   - Proves agreement/deferral invariants and explicit conflict selection.
// - Description:
//   - Ready disagreement is resolved only by caller-selected signal authority.
// - Usage:
//   - Compiled only under Rust test configuration.
// - Defaults:
//   - Agreement-only precedence withholds conflict.
//

//! Regression coverage for pure cache-limit precedence selection.

use std::num::{NonZeroU64, NonZeroUsize};

use crate::cached_cycle::NativeContinuationCachedRetryTelemetry;
use crate::executable_cache_limits_recommendation as cache_rec;
use crate::execution_native::NativeExecutableSequenceCacheLimits;

type TwoSignalRecommendation =
    cache_rec::NativeExecutableCacheLimitsTwoSignalRecommendation;

fn limits(
    entries: usize,
) -> Result<NativeExecutableSequenceCacheLimits, String> {
    NonZeroUsize::new(entries)
        .map(NativeExecutableSequenceCacheLimits::new)
        .ok_or_else(|| String::from("cache limit must be positive"))
}

fn nonzero(value: usize) -> Result<NonZeroUsize, String> {
    NonZeroUsize::new(value)
        .ok_or_else(|| String::from("attempt gate must be positive"))
}

fn one() -> Result<NonZeroU64, String> {
    NonZeroU64::new(1).ok_or_else(|| String::from("ratio must be positive"))
}

fn telemetry() -> NativeContinuationCachedRetryTelemetry {
    NativeContinuationCachedRetryTelemetry::from_test_counts([4, 8, 3, 0, 4, 2])
}

fn arbitration(
    reuse_attempts: usize,
    reuse_misses: NativeExecutableSequenceCacheLimits,
    pressure_misses: NativeExecutableSequenceCacheLimits,
) -> Result<TwoSignalRecommendation, String> {
    let ratio = one()?;
    let request = cache_rec::NativeExecutableCacheLimitsTwoSignalRequest::new(
        cache_rec::NativeExecutableCacheLimitsReuseThreshold::new(
            nonzero(reuse_attempts)?,
            ratio,
            ratio,
        ),
        cache_rec::NativeExecutableCacheLimitsRecommendationSet::new(
            limits(3)?,
            reuse_misses,
        ),
        cache_rec::NativeExecutableCacheLimitsPressureThreshold::new(
            nonzero(4)?,
            2,
            1,
        ),
        cache_rec::NativeExecutableCacheLimitsRecommendationSet::new(
            limits(3)?,
            pressure_misses,
        ),
    );
    Ok(cache_rec::
        recommend_native_executable_cache_limits_from_reuse_and_pressure(
            telemetry(),
            limits(4)?,
            &request,
        ))
}

#[test]
fn agreement_is_invariant_under_all_precedence_modes() -> Result<(), String> {
    let candidate = limits(8)?;
    let arbitration = arbitration(4, candidate, candidate)?;
    let expected = arbitration
        .recommendation()
        .ok_or_else(|| String::from("agreement fixture withheld policy"))?;
    for precedence in [
        super::NativeExecutableCacheLimitsPrecedence::AgreementOnly,
        super::NativeExecutableCacheLimitsPrecedence::Pressure,
        super::NativeExecutableCacheLimitsPrecedence::Reuse,
    ] {
        let selection = super::select_native_executable_cache_limits_precedence(
            &arbitration,
            precedence,
        );
        if !matches!(
            selection,
            super::NativeExecutableCacheLimitsPrecedenceSelection::Agreed {
                arbitration: observed,
                recommendation,
            } if observed == arbitration && recommendation == expected
        ) || selection.recommendation() != Some(expected)
        {
            return Err(String::from("precedence changed existing agreement"));
        }
    }
    Ok(())
}

#[test]
fn agreement_only_withholds_ready_conflict() -> Result<(), String> {
    let arbitration = arbitration(4, limits(8)?, limits(2)?)?;
    let selection = super::select_native_executable_cache_limits_precedence(
        &arbitration,
        super::NativeExecutableCacheLimitsPrecedence::AgreementOnly,
    );
    if matches!(
        selection,
        super::NativeExecutableCacheLimitsPrecedenceSelection::Withheld {
            arbitration: observed,
        } if observed == arbitration
    ) && selection.recommendation().is_none()
    {
        Ok(())
    } else {
        Err(String::from("agreement-only precedence resolved conflict"))
    }
}

#[test]
fn explicit_precedence_selects_exact_conflicting_signal() -> Result<(), String>
{
    let reuse_limits = limits(8)?;
    let pressure_limits = limits(2)?;
    let arbitration = arbitration(4, reuse_limits, pressure_limits)?;
    for (precedence, expected) in [
        (
            super::NativeExecutableCacheLimitsPrecedence::Pressure,
            pressure_limits,
        ),
        (
            super::NativeExecutableCacheLimitsPrecedence::Reuse,
            reuse_limits,
        ),
    ] {
        let selection = super::select_native_executable_cache_limits_precedence(
            &arbitration,
            precedence,
        );
        let super::NativeExecutableCacheLimitsPrecedenceSelection::Selected {
            arbitration: observed,
            precedence: observed_precedence,
            recommendation,
        } = selection
        else {
            return Err(String::from("ready conflict was not selected"));
        };
        if observed != arbitration
            || observed_precedence != precedence
            || recommendation.limits() != Some(expected)
            || selection.recommendation() != Some(recommendation)
        {
            return Err(String::from("precedence selected wrong cache limits"));
        }
    }
    Ok(())
}

#[test]
fn deferred_arbitration_cannot_be_overridden() -> Result<(), String> {
    let arbitration = arbitration(5, limits(8)?, limits(2)?)?;
    for precedence in [
        super::NativeExecutableCacheLimitsPrecedence::Pressure,
        super::NativeExecutableCacheLimitsPrecedence::Reuse,
    ] {
        let selection = super::select_native_executable_cache_limits_precedence(
            &arbitration,
            precedence,
        );
        if !matches!(
            selection,
            super::NativeExecutableCacheLimitsPrecedenceSelection::Deferred {
                arbitration: observed,
            } if observed == arbitration
        ) || selection.recommendation().is_some()
        {
            return Err(String::from("precedence overrode deferred evidence"));
        }
    }
    Ok(())
}

#[test]
fn unavailable_selected_signal_withholds_authority() -> Result<(), String> {
    let deferred = arbitration(5, limits(8)?, limits(2)?)?;
    let TwoSignalRecommendation::Deferred { pressure, reuse } = deferred else {
        return Err(String::from("deferred fixture unexpectedly ready"));
    };
    let malformed = TwoSignalRecommendation::Conflict { pressure, reuse };
    let selection = super::select_native_executable_cache_limits_precedence(
        &malformed,
        super::NativeExecutableCacheLimitsPrecedence::Reuse,
    );
    if matches!(
        selection,
        super::NativeExecutableCacheLimitsPrecedenceSelection::Unavailable {
            arbitration: observed,
            precedence: super::NativeExecutableCacheLimitsPrecedence::Reuse,
        } if observed == malformed
    ) && selection.recommendation().is_none()
    {
        Ok(())
    } else {
        Err(String::from("unavailable signal gained cache authority"))
    }
}
