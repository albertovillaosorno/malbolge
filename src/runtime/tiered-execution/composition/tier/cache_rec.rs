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
//   - Pure executable-cache limit recommendation from exact reuse telemetry.
// - Must-Not:
//   - Reconfigure caches, publish durable policy, invent limit values, or retry
//     release/retirement failures.
// - Allows:
//   - Inputs: exact cached-retry telemetry, current limits, caller-selected
//     reuse threshold, and caller-owned meets/misses limit candidates.
//   - Outputs: deferred, retain, or exact reconfiguration recommendation.
//   - Side effects: none.
// - Split-When:
//   - Additional cache-policy signals or weighted arbitration gains authority.
// - Merge-When:
//   - One cache-policy owner subsumes evidence classification and activation.
// - Summary:
//   - Maps normalized cache reuse to explicit caller-owned cache limits.
// - Description:
//   - Exact hit-per-attempt evidence selects only preconfigured limits.
// - Usage:
//   - Recommend first, then explicitly publish or apply any reconfiguration.
// - Defaults:
//   - Insufficient attempts defer; arithmetic failure selects misses limits.
//

//! Pure executable-cache limit recommendation from exact cache-reuse evidence.

use std::num::{NonZeroU64, NonZeroU128, NonZeroUsize};

use crate::cached_cycle::NativeContinuationCachedRetryTelemetry;
use crate::execution_native::NativeExecutableSequenceCacheLimits;

/// Caller-owned exact limits eligible for one reuse-based recommendation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeExecutableCacheLimitsRecommendationSet {
    meets: NativeExecutableSequenceCacheLimits,
    misses: NativeExecutableSequenceCacheLimits,
}

/// Caller-owned normalized cache-reuse evidence threshold.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeExecutableCacheLimitsReuseThreshold {
    minimum_hits_denominator: NonZeroU64,
    minimum_hits_numerator: NonZeroU64,
    required_attempts: NonZeroUsize,
}

/// Stable reason ready reuse evidence selected the misses limits.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeExecutableCacheLimitsReuseMiss {
    /// Exact rational comparison overflowed `u128` and failed closed.
    ArithmeticOverflow,
    /// Active-cache hits per attempt missed the caller minimum.
    BelowMinimumHitsPerAttempt,
}

/// Exact ready cache-reuse classification retained with a recommendation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeExecutableCacheLimitsReuseEvidence {
    /// Ready reuse met the caller-owned minimum ratio.
    Meets,
    /// Ready reuse failed closed to the misses candidate.
    Misses(NativeExecutableCacheLimitsReuseMiss),
}

/// Exact pure recommendation for one current executable-cache limit policy.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeExecutableCacheLimitsRecommendation {
    /// Positive attempt gate was not reached; policy must not change.
    Deferred {
        /// Attempts represented by the supplied telemetry.
        observed_attempts: usize,
        /// Positive caller-required attempt count.
        required_attempts: NonZeroUsize,
    },
    /// Ready evidence selected exact caller-owned replacement limits.
    Reconfigure {
        /// Exact current limits supplied to the recommendation.
        current: NativeExecutableSequenceCacheLimits,
        /// Exact ready evidence selecting the replacement.
        evidence: NativeExecutableCacheLimitsReuseEvidence,
        /// Exact caller-owned replacement limits.
        recommended: NativeExecutableSequenceCacheLimits,
        /// Exact telemetry used by the recommendation.
        telemetry: NativeContinuationCachedRetryTelemetry,
    },
    /// Ready evidence selected the already-active limits.
    Retain {
        /// Exact ready evidence selecting the current limits.
        evidence: NativeExecutableCacheLimitsReuseEvidence,
        /// Exact current limits that should remain active.
        limits: NativeExecutableSequenceCacheLimits,
        /// Exact telemetry used by the recommendation.
        telemetry: NativeContinuationCachedRetryTelemetry,
    },
}

impl NativeExecutableCacheLimitsRecommendationSet {
    /// Returns exact limits selected by threshold-meeting evidence.
    #[must_use]
    pub const fn meets(self) -> NativeExecutableSequenceCacheLimits {
        self.meets
    }

    /// Returns exact limits selected by threshold-missing evidence.
    #[must_use]
    pub const fn misses(self) -> NativeExecutableSequenceCacheLimits {
        self.misses
    }

    /// Constructs one explicit reuse-to-limits recommendation table.
    #[must_use]
    pub const fn new(
        meets: NativeExecutableSequenceCacheLimits,
        misses: NativeExecutableSequenceCacheLimits,
    ) -> Self {
        Self { meets, misses }
    }
}

impl NativeExecutableCacheLimitsReuseThreshold {
    /// Returns the exact minimum hits-per-attempt denominator.
    #[must_use]
    pub const fn minimum_hits_denominator(self) -> NonZeroU64 {
        self.minimum_hits_denominator
    }

    /// Returns the exact minimum hits-per-attempt numerator.
    #[must_use]
    pub const fn minimum_hits_numerator(self) -> NonZeroU64 {
        self.minimum_hits_numerator
    }

    /// Constructs one exact positive active-cache-hit ratio threshold.
    #[must_use]
    pub const fn new(
        required_attempts: NonZeroUsize,
        minimum_hits_numerator: NonZeroU64,
        minimum_hits_denominator: NonZeroU64,
    ) -> Self {
        Self {
            minimum_hits_denominator,
            minimum_hits_numerator,
            required_attempts,
        }
    }

    /// Returns the positive attempt gate for reuse evidence.
    #[must_use]
    pub const fn required_attempts(self) -> NonZeroUsize {
        self.required_attempts
    }
}

impl NativeExecutableCacheLimitsRecommendation {
    /// Returns exact recommended limits once evidence is ready.
    #[must_use]
    pub const fn limits(self) -> Option<NativeExecutableSequenceCacheLimits> {
        match self {
            Self::Deferred { .. } => None,
            Self::Retain { limits, .. } => Some(limits),
            Self::Reconfigure { recommended, .. } => Some(recommended),
        }
    }
}

fn classify_cache_reuse(
    telemetry: NativeContinuationCachedRetryTelemetry,
    threshold: NativeExecutableCacheLimitsReuseThreshold,
) -> Result<bool, NativeExecutableCacheLimitsReuseMiss> {
    let Ok(hits) = u128::try_from(telemetry.hits()) else {
        return Err(NativeExecutableCacheLimitsReuseMiss::ArithmeticOverflow);
    };
    let Ok(attempts) = u128::try_from(telemetry.attempts()) else {
        return Err(NativeExecutableCacheLimitsReuseMiss::ArithmeticOverflow);
    };
    let weighted_hits = hits
        .checked_mul(
            NonZeroU128::from(threshold.minimum_hits_denominator).get(),
        )
        .ok_or(NativeExecutableCacheLimitsReuseMiss::ArithmeticOverflow)?;
    let required_hits = attempts
        .checked_mul(NonZeroU128::from(threshold.minimum_hits_numerator).get())
        .ok_or(NativeExecutableCacheLimitsReuseMiss::ArithmeticOverflow)?;
    Ok(weighted_hits >= required_hits)
}

/// Recommends exact caller-owned cache limits without mutating cache state.
#[must_use]
pub fn recommend_native_executable_cache_limits_from_reuse(
    telemetry: NativeContinuationCachedRetryTelemetry,
    current: NativeExecutableSequenceCacheLimits,
    threshold: NativeExecutableCacheLimitsReuseThreshold,
    candidates: NativeExecutableCacheLimitsRecommendationSet,
) -> NativeExecutableCacheLimitsRecommendation {
    if telemetry.attempts() < threshold.required_attempts.get() {
        return NativeExecutableCacheLimitsRecommendation::Deferred {
            observed_attempts: telemetry.attempts(),
            required_attempts: threshold.required_attempts,
        };
    }
    let classification = classify_cache_reuse(telemetry, threshold);
    let (evidence, recommended) = match classification {
        Ok(true) => (
            NativeExecutableCacheLimitsReuseEvidence::Meets,
            candidates.meets(),
        ),
        Ok(false) => (
            NativeExecutableCacheLimitsReuseEvidence::Misses(
                NativeExecutableCacheLimitsReuseMiss::
                    BelowMinimumHitsPerAttempt,
            ),
            candidates.misses(),
        ),
        Err(reason) => (
            NativeExecutableCacheLimitsReuseEvidence::Misses(reason),
            candidates.misses(),
        ),
    };
    if recommended == current {
        NativeExecutableCacheLimitsRecommendation::Retain {
            evidence,
            limits: current,
            telemetry,
        }
    } else {
        NativeExecutableCacheLimitsRecommendation::Reconfigure {
            current,
            evidence,
            recommended,
            telemetry,
        }
    }
}

#[cfg(test)]
#[path = "../../../../../tests/tiered/cache_limits_recommendation.rs"]
mod tests;
