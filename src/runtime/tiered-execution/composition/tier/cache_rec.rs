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
//   - Pure executable-cache limit recommendation from exact reuse or pressure
//     telemetry evidence.
// - Must-Not:
//   - Reconfigure caches, publish durable policy, invent limit values, or retry
//     release/retirement failures.
// - Allows:
//   - Inputs: exact cached-retry telemetry, current limits, caller-selected
//     reuse or pressure threshold, and caller-owned limit candidates.
//   - Outputs: deferred, retain, or exact reconfiguration recommendation.
//   - Side effects: none.
// - Split-When:
//   - Signals beyond reuse/pressure or weighted arbitration gains authority.
// - Merge-When:
//   - One cache-policy owner subsumes evidence classification and activation.
// - Summary:
//   - Maps exact cache evidence to explicit caller-owned cache limits.
// - Description:
//   - Reuse and eviction/retirement pressure remain independent until exact
//     agreement-only arbitration.
// - Usage:
//   - Recommend first, then explicitly publish or apply any reconfiguration.
// - Defaults:
//   - Insufficient evidence defers; disagreement withholds combined authority.
//

//! Pure executable-cache limit recommendation from exact cache evidence.

use std::num::{NonZeroU64, NonZeroU128, NonZeroUsize};

use crate::cached_cycle::NativeContinuationCachedRetryTelemetry;
use crate::execution_native::NativeExecutableSequenceCacheLimits;

/// Caller-owned exact limits eligible for one cache-evidence recommendation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeExecutableCacheLimitsRecommendationSet {
    meets: NativeExecutableSequenceCacheLimits,
    misses: NativeExecutableSequenceCacheLimits,
}

/// Exact source evidence retained by one ready cache-limit recommendation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeExecutableCacheLimitsEvidence {
    /// Reuse and pressure independently selected the same exact limits.
    Agreement {
        /// Exact pressure evidence participating in agreement.
        pressure: NativeExecutableCacheLimitsPressureEvidence,
        /// Exact reuse evidence participating in agreement.
        reuse: NativeExecutableCacheLimitsReuseEvidence,
    },
    /// Eviction/retirement pressure evidence.
    Pressure(NativeExecutableCacheLimitsPressureEvidence),
    /// Active-cache reuse evidence.
    Reuse(NativeExecutableCacheLimitsReuseEvidence),
}

/// Caller-owned maximum pressure counts after a positive attempt gate.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeExecutableCacheLimitsPressureThreshold {
    maximum_evicted_keys: usize,
    maximum_insertions: usize,
    maximum_retired_keys: usize,
    required_attempts: NonZeroUsize,
}

/// One exact cache-pressure signal with caller-owned maximum semantics.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeExecutableCacheLimitsPressureSignal {
    /// Active cache keys evicted while admitting misses.
    EvictedKeys,
    /// Cache insertions represented by the exact telemetry.
    Insertions,
    /// Evicted keys still resident behind external leases.
    RetiredKeys,
}

/// Simultaneous cache-pressure threshold violations.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct NativeExecutableCacheLimitsPressureViolations {
    bits: u8,
}

/// Exact ready cache-pressure classification retained with a recommendation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeExecutableCacheLimitsPressureEvidence {
    /// One or more caller-owned maximums were exceeded.
    Pressured(NativeExecutableCacheLimitsPressureViolations),
    /// Every caller-owned maximum was met inclusively.
    WithinMaximums,
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
        evidence: NativeExecutableCacheLimitsEvidence,
        /// Exact caller-owned replacement limits.
        recommended: NativeExecutableSequenceCacheLimits,
        /// Exact telemetry used by the recommendation.
        telemetry: NativeContinuationCachedRetryTelemetry,
    },
    /// Ready evidence selected the already-active limits.
    Retain {
        /// Exact ready evidence selecting the current limits.
        evidence: NativeExecutableCacheLimitsEvidence,
        /// Exact current limits that should remain active.
        limits: NativeExecutableSequenceCacheLimits,
        /// Exact telemetry used by the recommendation.
        telemetry: NativeContinuationCachedRetryTelemetry,
    },
}

/// Caller-owned configuration for reuse/pressure agreement-only policy.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeExecutableCacheLimitsTwoSignalRequest {
    pressure_candidates: NativeExecutableCacheLimitsRecommendationSet,
    pressure_threshold: NativeExecutableCacheLimitsPressureThreshold,
    reuse_candidates: NativeExecutableCacheLimitsRecommendationSet,
    reuse_threshold: NativeExecutableCacheLimitsReuseThreshold,
}

/// Agreement-only arbitration across reuse and pressure recommendations.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeExecutableCacheLimitsTwoSignalRecommendation {
    /// Both ready signals selected the same exact cache limits.
    Agreed {
        /// Exact pressure recommendation retained unchanged.
        pressure: NativeExecutableCacheLimitsRecommendation,
        /// Exact combined recommendation authorized by agreement.
        recommendation: NativeExecutableCacheLimitsRecommendation,
        /// Exact reuse recommendation retained unchanged.
        reuse: NativeExecutableCacheLimitsRecommendation,
    },
    /// Both signals were ready but selected different exact limits.
    Conflict {
        /// Exact pressure recommendation retained unchanged.
        pressure: NativeExecutableCacheLimitsRecommendation,
        /// Exact reuse recommendation retained unchanged.
        reuse: NativeExecutableCacheLimitsRecommendation,
    },
    /// At least one evidence gate was not ready; no combined policy exists.
    Deferred {
        /// Exact pressure recommendation retained unchanged.
        pressure: NativeExecutableCacheLimitsRecommendation,
        /// Exact reuse recommendation retained unchanged.
        reuse: NativeExecutableCacheLimitsRecommendation,
    },
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct ReadyRecommendationParts {
    current: NativeExecutableSequenceCacheLimits,
    evidence: NativeExecutableCacheLimitsEvidence,
    limits: NativeExecutableSequenceCacheLimits,
    telemetry: NativeContinuationCachedRetryTelemetry,
}

impl NativeExecutableCacheLimitsTwoSignalRequest {
    /// Binds both caller-owned thresholds and both exact candidate tables.
    #[must_use]
    pub const fn new(
        reuse_threshold: NativeExecutableCacheLimitsReuseThreshold,
        reuse_candidates: NativeExecutableCacheLimitsRecommendationSet,
        pressure_threshold: NativeExecutableCacheLimitsPressureThreshold,
        pressure_candidates: NativeExecutableCacheLimitsRecommendationSet,
    ) -> Self {
        Self {
            pressure_candidates,
            pressure_threshold,
            reuse_candidates,
            reuse_threshold,
        }
    }
}

impl NativeExecutableCacheLimitsTwoSignalRecommendation {
    /// Returns combined policy authority only when both signals agree.
    #[must_use]
    pub const fn recommendation(
        self,
    ) -> Option<NativeExecutableCacheLimitsRecommendation> {
        match self {
            Self::Agreed { recommendation, .. } => Some(recommendation),
            Self::Conflict { .. } | Self::Deferred { .. } => None,
        }
    }
}

impl NativeExecutableCacheLimitsPressureSignal {
    const fn mask(self) -> u8 {
        match self {
            Self::EvictedKeys => 1,
            Self::Insertions => 2,
            Self::RetiredKeys => 4,
        }
    }
}

impl NativeExecutableCacheLimitsPressureThreshold {
    /// Returns the inclusive maximum active-key eviction count.
    #[must_use]
    pub const fn maximum_evicted_keys(self) -> usize {
        self.maximum_evicted_keys
    }

    /// Returns the inclusive maximum insertion count.
    #[must_use]
    pub const fn maximum_insertions(self) -> usize {
        self.maximum_insertions
    }

    /// Returns the inclusive maximum retired-key count.
    #[must_use]
    pub const fn maximum_retired_keys(self) -> usize {
        self.maximum_retired_keys
    }

    /// Constructs exact maximum pressure counts and a positive attempt gate.
    #[must_use]
    pub const fn new(
        required_attempts: NonZeroUsize,
        maximum_evicted_keys: usize,
        maximum_retired_keys: usize,
    ) -> Self {
        Self::new_with_insertions(
            required_attempts,
            maximum_evicted_keys,
            usize::MAX,
            maximum_retired_keys,
        )
    }

    /// Constructs exact pressure maxima including cache insertions.
    #[must_use]
    pub const fn new_with_insertions(
        required_attempts: NonZeroUsize,
        maximum_evicted_keys: usize,
        maximum_insertions: usize,
        maximum_retired_keys: usize,
    ) -> Self {
        Self {
            maximum_evicted_keys,
            maximum_insertions,
            maximum_retired_keys,
            required_attempts,
        }
    }

    /// Returns the positive attempt gate for pressure evidence.
    #[must_use]
    pub const fn required_attempts(self) -> NonZeroUsize {
        self.required_attempts
    }
}

impl NativeExecutableCacheLimitsPressureViolations {
    /// Reports whether one exact pressure signal exceeded its maximum.
    #[must_use]
    pub const fn contains(
        self,
        signal: NativeExecutableCacheLimitsPressureSignal,
    ) -> bool {
        self.bits & signal.mask() != 0
    }

    /// Reports whether all configured pressure maximums were met.
    #[must_use]
    pub const fn is_empty(self) -> bool {
        self.bits == 0
    }
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

const fn ready_recommendation_parts(
    recommendation: NativeExecutableCacheLimitsRecommendation,
) -> Option<ReadyRecommendationParts> {
    match recommendation {
        NativeExecutableCacheLimitsRecommendation::Deferred { .. } => None,
        NativeExecutableCacheLimitsRecommendation::Reconfigure {
            current,
            evidence,
            recommended,
            telemetry,
        } => Some(ReadyRecommendationParts {
            current,
            evidence,
            limits: recommended,
            telemetry,
        }),
        NativeExecutableCacheLimitsRecommendation::Retain {
            evidence,
            limits,
            telemetry,
        } => Some(ReadyRecommendationParts {
            current: limits,
            evidence,
            limits,
            telemetry,
        }),
    }
}

const fn pressure_evidence(
    evidence: NativeExecutableCacheLimitsEvidence,
) -> Option<NativeExecutableCacheLimitsPressureEvidence> {
    match evidence {
        NativeExecutableCacheLimitsEvidence::Pressure(pressure) => {
            Some(pressure)
        },
        NativeExecutableCacheLimitsEvidence::Agreement { .. }
        | NativeExecutableCacheLimitsEvidence::Reuse(_) => None,
    }
}

const fn reuse_evidence(
    evidence: NativeExecutableCacheLimitsEvidence,
) -> Option<NativeExecutableCacheLimitsReuseEvidence> {
    match evidence {
        NativeExecutableCacheLimitsEvidence::Reuse(reuse) => Some(reuse),
        NativeExecutableCacheLimitsEvidence::Agreement { .. }
        | NativeExecutableCacheLimitsEvidence::Pressure(_) => None,
    }
}

fn combine_ready_recommendations(
    reuse: ReadyRecommendationParts,
    pressure: ReadyRecommendationParts,
) -> Option<NativeExecutableCacheLimitsRecommendation> {
    let reuse_signal = reuse_evidence(reuse.evidence)?;
    let pressure_signal = pressure_evidence(pressure.evidence)?;
    if reuse.current != pressure.current
        || reuse.limits != pressure.limits
        || reuse.telemetry != pressure.telemetry
    {
        return None;
    }
    let evidence = NativeExecutableCacheLimitsEvidence::Agreement {
        pressure: pressure_signal,
        reuse: reuse_signal,
    };
    if reuse.limits == reuse.current {
        Some(NativeExecutableCacheLimitsRecommendation::Retain {
            evidence,
            limits: reuse.current,
            telemetry: reuse.telemetry,
        })
    } else {
        Some(NativeExecutableCacheLimitsRecommendation::Reconfigure {
            current: reuse.current,
            evidence,
            recommended: reuse.limits,
            telemetry: reuse.telemetry,
        })
    }
}

fn arbitrate_reuse_and_pressure(
    reuse: NativeExecutableCacheLimitsRecommendation,
    pressure: NativeExecutableCacheLimitsRecommendation,
) -> NativeExecutableCacheLimitsTwoSignalRecommendation {
    let (Some(reuse_parts), Some(pressure_parts)) = (
        ready_recommendation_parts(reuse),
        ready_recommendation_parts(pressure),
    ) else {
        return NativeExecutableCacheLimitsTwoSignalRecommendation::Deferred {
            pressure,
            reuse,
        };
    };
    combine_ready_recommendations(reuse_parts, pressure_parts).map_or(
        NativeExecutableCacheLimitsTwoSignalRecommendation::Conflict {
            pressure,
            reuse,
        },
        |recommendation| {
            NativeExecutableCacheLimitsTwoSignalRecommendation::Agreed {
                pressure,
                recommendation,
                reuse,
            }
        },
    )
}

/// Recommends caller-owned limits from exact eviction/retirement pressure.
#[must_use]
pub fn recommend_native_executable_cache_limits_from_pressure(
    telemetry: NativeContinuationCachedRetryTelemetry,
    current: NativeExecutableSequenceCacheLimits,
    threshold: NativeExecutableCacheLimitsPressureThreshold,
    candidates: NativeExecutableCacheLimitsRecommendationSet,
) -> NativeExecutableCacheLimitsRecommendation {
    if telemetry.attempts() < threshold.required_attempts.get() {
        return NativeExecutableCacheLimitsRecommendation::Deferred {
            observed_attempts: telemetry.attempts(),
            required_attempts: threshold.required_attempts,
        };
    }
    let mut bits = 0;
    if telemetry.evicted_keys() > threshold.maximum_evicted_keys {
        bits |= NativeExecutableCacheLimitsPressureSignal::EvictedKeys.mask();
    }
    if telemetry.insertions() > threshold.maximum_insertions {
        bits |= NativeExecutableCacheLimitsPressureSignal::Insertions.mask();
    }
    if telemetry.retired_keys() > threshold.maximum_retired_keys {
        bits |= NativeExecutableCacheLimitsPressureSignal::RetiredKeys.mask();
    }
    let violations = NativeExecutableCacheLimitsPressureViolations { bits };
    let (evidence, recommended) = if violations.is_empty() {
        (
            NativeExecutableCacheLimitsEvidence::Pressure(
                NativeExecutableCacheLimitsPressureEvidence::WithinMaximums,
            ),
            candidates.meets(),
        )
    } else {
        (
            NativeExecutableCacheLimitsEvidence::Pressure(
                NativeExecutableCacheLimitsPressureEvidence::Pressured(
                    violations,
                ),
            ),
            candidates.misses(),
        )
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

/// Recommends limits only when reuse and pressure select the same candidate.
#[must_use]
pub fn recommend_native_executable_cache_limits_from_reuse_and_pressure(
    telemetry: NativeContinuationCachedRetryTelemetry,
    current: NativeExecutableSequenceCacheLimits,
    request: &NativeExecutableCacheLimitsTwoSignalRequest,
) -> NativeExecutableCacheLimitsTwoSignalRecommendation {
    let reuse = recommend_native_executable_cache_limits_from_reuse(
        telemetry,
        current,
        request.reuse_threshold,
        request.reuse_candidates,
    );
    let pressure = recommend_native_executable_cache_limits_from_pressure(
        telemetry,
        current,
        request.pressure_threshold,
        request.pressure_candidates,
    );
    arbitrate_reuse_and_pressure(reuse, pressure)
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
            NativeExecutableCacheLimitsEvidence::Reuse(
                NativeExecutableCacheLimitsReuseEvidence::Meets,
            ),
            candidates.meets(),
        ),
        Ok(false) => (
            NativeExecutableCacheLimitsEvidence::Reuse(
                NativeExecutableCacheLimitsReuseEvidence::Misses(
                    NativeExecutableCacheLimitsReuseMiss::
                        BelowMinimumHitsPerAttempt,
                ),
            ),
            candidates.misses(),
        ),
        Err(reason) => (
            NativeExecutableCacheLimitsEvidence::Reuse(
                NativeExecutableCacheLimitsReuseEvidence::Misses(reason),
            ),
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
