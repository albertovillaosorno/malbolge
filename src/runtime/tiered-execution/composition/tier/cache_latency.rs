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
//   - Pure cache-limit recommendation from exact cumulative latency records and
//     conservative agreement with an existing window-scoped cache plan.
// - Must-Not:
//   - Read clocks, infer candidate limits, approximate histogram overflow,
//     mutate telemetry/cache/storage, or override missing window authority.
// - Allows:
//   - Inputs: cumulative latency record, caller-owned inclusive latency maxima,
//     caller-owned candidate limits, and one exact window-scoped cache plan.
//   - Outputs: deferred/ready latency evidence and deferred/agreed/conflicting
//     window-plus-latency policy evidence.
//   - Side effects: none.
// - Split-When:
//   - Histogram-overflow policy or caller-selected cross-signal precedence
//     gains authority.
// - Merge-When:
//   - One cache planner owns count, pressure, latency, and activation
//     atomically.
// - Summary:
//   - Adds exact average/maximum latency as an independent cache policy signal.
// - Description:
//   - Agreement is required before the existing window recommendation survives.
// - Usage:
//   - Recommend from a published cumulative latency record, then arbitrate with
//     the already-computed window plan.
// - Defaults:
//   - Insufficient latency or absent window authority cannot authorize limits.
//

//! Pure latency-driven cache-limit recommendation and agreement arbitration.

use std::num::NonZeroUsize;

use crate::cached_cycle::NativeContinuationCachedRetryLatencyRecord;
use crate::executable_cache_limits_recommendation::{
    NativeExecutableCacheLimitsRecommendation,
    NativeExecutableCacheLimitsRecommendationSet,
};
use crate::executable_cache_limits_window_plan as cache_window;
use crate::execution_native::NativeExecutableSequenceCacheLimits;

type WindowPlan = cache_window::NativeExecutableCacheLimitsWindowPlan;

/// Caller-owned inclusive latency maxima after a positive cumulative sample
/// gate.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeExecutableCacheLimitsLatencyThreshold {
    maximum_average_nanoseconds: u64,
    maximum_nanoseconds: u64,
    required_samples: NonZeroUsize,
}

/// One exact cumulative latency signal with caller-owned maximum semantics.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeExecutableCacheLimitsLatencySignal {
    /// Exact arithmetic mean across all samples represented by the record.
    AverageNanoseconds,
    /// Largest sample represented by the cumulative record.
    MaximumNanoseconds,
}

/// Simultaneous cumulative latency threshold violations.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct NativeExecutableCacheLimitsLatencyViolations {
    bits: u8,
}

/// Exact ready cumulative-latency classification.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeExecutableCacheLimitsLatencyEvidence {
    /// One or more caller-owned inclusive maxima were exceeded.
    Misses(NativeExecutableCacheLimitsLatencyViolations),
    /// Every represented latency maximum was met inclusively.
    WithinMaximums,
}

/// Exact latency-driven cache-limit recommendation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeExecutableCacheLimitsLatencyRecommendation {
    /// Positive cumulative sample gate was not reached.
    Deferred {
        /// Samples represented by the cumulative record.
        observed_samples: usize,
        /// Positive caller-required sample count.
        required_samples: NonZeroUsize,
    },
    /// Ready latency selected one exact caller-owned candidate.
    Ready {
        /// Exact latency classification selecting the candidate.
        evidence: NativeExecutableCacheLimitsLatencyEvidence,
        /// Exact caller-owned limits selected by latency.
        limits: NativeExecutableSequenceCacheLimits,
        /// Exact cumulative latency record used for recommendation.
        record: NativeContinuationCachedRetryLatencyRecord,
    },
}

/// Caller-owned configuration for one latency cache recommendation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeExecutableCacheLimitsLatencyRequest {
    candidates: NativeExecutableCacheLimitsRecommendationSet,
    threshold: NativeExecutableCacheLimitsLatencyThreshold,
}

/// Conservative arbitration between a window plan and latency recommendation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeExecutableCacheLimitsWindowLatencyPlan {
    /// Both ready signals selected identical exact limits.
    Agreed {
        /// Exact independent latency recommendation.
        latency: NativeExecutableCacheLimitsLatencyRecommendation,
        /// Existing window recommendation authorized by exact agreement.
        recommendation: NativeExecutableCacheLimitsRecommendation,
        /// Exact window-scoped plan retained unchanged.
        window: WindowPlan,
    },
    /// Both signals were ready but selected different exact limits.
    Conflict {
        /// Exact independent latency recommendation.
        latency: NativeExecutableCacheLimitsLatencyRecommendation,
        /// Exact window-scoped plan retained unchanged.
        window: WindowPlan,
    },
    /// At least one signal lacked recommendation authority.
    Deferred {
        /// Exact latency recommendation, ready or deferred.
        latency: NativeExecutableCacheLimitsLatencyRecommendation,
        /// Exact window-scoped plan retained unchanged.
        window: WindowPlan,
    },
}

impl NativeExecutableCacheLimitsLatencySignal {
    const fn mask(self) -> u8 {
        match self {
            Self::AverageNanoseconds => 1,
            Self::MaximumNanoseconds => 2,
        }
    }
}

impl NativeExecutableCacheLimitsLatencyThreshold {
    /// Returns the inclusive maximum arithmetic-mean latency.
    #[must_use]
    pub const fn maximum_average_nanoseconds(self) -> u64 {
        self.maximum_average_nanoseconds
    }

    /// Returns the inclusive maximum represented individual latency.
    #[must_use]
    pub const fn maximum_nanoseconds(self) -> u64 {
        self.maximum_nanoseconds
    }

    /// Constructs exact cumulative-latency thresholds.
    #[must_use]
    pub const fn new(
        required_samples: NonZeroUsize,
        maximum_average_nanoseconds: u64,
        maximum_nanoseconds: u64,
    ) -> Self {
        Self {
            maximum_average_nanoseconds,
            maximum_nanoseconds,
            required_samples,
        }
    }

    /// Returns the positive cumulative sample gate.
    #[must_use]
    pub const fn required_samples(self) -> NonZeroUsize {
        self.required_samples
    }
}

impl NativeExecutableCacheLimitsLatencyViolations {
    /// Reports whether one exact latency signal exceeded its inclusive maximum.
    #[must_use]
    pub const fn contains(
        self,
        signal: NativeExecutableCacheLimitsLatencySignal,
    ) -> bool {
        self.bits & signal.mask() != 0
    }

    /// Reports whether all configured latency maxima were met.
    #[must_use]
    pub const fn is_empty(self) -> bool {
        self.bits == 0
    }
}

impl NativeExecutableCacheLimitsLatencyRecommendation {
    /// Returns exact selected limits once cumulative latency is ready.
    #[must_use]
    pub const fn limits(self) -> Option<NativeExecutableSequenceCacheLimits> {
        match self {
            Self::Deferred { .. } => None,
            Self::Ready { limits, .. } => Some(limits),
        }
    }
}

impl NativeExecutableCacheLimitsLatencyRequest {
    /// Binds latency thresholds to exact caller-owned meets/misses candidates.
    #[must_use]
    pub const fn new(
        threshold: NativeExecutableCacheLimitsLatencyThreshold,
        candidates: NativeExecutableCacheLimitsRecommendationSet,
    ) -> Self {
        Self { candidates, threshold }
    }
}

impl NativeExecutableCacheLimitsWindowLatencyPlan {
    /// Returns cache-limit authority only after exact window/latency agreement.
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

fn average_exceeds(
    record: NativeContinuationCachedRetryLatencyRecord,
    maximum: u64,
) -> bool {
    let Ok(samples) = u128::try_from(record.samples()) else {
        return true;
    };
    let Some(maximum_total) = u128::from(maximum).checked_mul(samples) else {
        return true;
    };
    record.total_nanoseconds() > maximum_total
}

/// Recommends one exact caller-owned candidate from cumulative latency
/// evidence.
#[must_use]
pub fn recommend_native_executable_cache_limits_from_latency(
    record: NativeContinuationCachedRetryLatencyRecord,
    request: NativeExecutableCacheLimitsLatencyRequest,
) -> NativeExecutableCacheLimitsLatencyRecommendation {
    if record.samples() < request.threshold.required_samples.get() {
        return NativeExecutableCacheLimitsLatencyRecommendation::Deferred {
            observed_samples: record.samples(),
            required_samples: request.threshold.required_samples,
        };
    }
    let mut bits = 0;
    if average_exceeds(record, request.threshold.maximum_average_nanoseconds) {
        bits |=
            NativeExecutableCacheLimitsLatencySignal::AverageNanoseconds.mask();
    }
    if record.maximum_nanoseconds() > request.threshold.maximum_nanoseconds {
        bits |=
            NativeExecutableCacheLimitsLatencySignal::MaximumNanoseconds.mask();
    }
    let violations = NativeExecutableCacheLimitsLatencyViolations { bits };
    let (evidence, limits) = if violations.is_empty() {
        (
            NativeExecutableCacheLimitsLatencyEvidence::WithinMaximums,
            request.candidates.meets(),
        )
    } else {
        (
            NativeExecutableCacheLimitsLatencyEvidence::Misses(violations),
            request.candidates.misses(),
        )
    };
    NativeExecutableCacheLimitsLatencyRecommendation::Ready {
        evidence,
        limits,
        record,
    }
}

/// Requires existing window authority and latency to select identical limits.
#[must_use]
pub fn plan_native_executable_cache_limits_with_latency(
    window: &WindowPlan,
    record: NativeContinuationCachedRetryLatencyRecord,
    request: NativeExecutableCacheLimitsLatencyRequest,
) -> NativeExecutableCacheLimitsWindowLatencyPlan {
    let latency =
        recommend_native_executable_cache_limits_from_latency(record, request);
    match (window.recommendation(), latency.limits()) {
        (Some(recommendation), Some(latency_limits))
            if recommendation.limits() == Some(latency_limits) =>
        {
            NativeExecutableCacheLimitsWindowLatencyPlan::Agreed {
                latency,
                recommendation,
                window: *window,
            }
        },
        (Some(_), Some(_)) => {
            NativeExecutableCacheLimitsWindowLatencyPlan::Conflict {
                latency,
                window: *window,
            }
        },
        (None, _) | (_, None) => {
            NativeExecutableCacheLimitsWindowLatencyPlan::Deferred {
                latency,
                window: *window,
            }
        },
    }
}

#[cfg(test)]
#[path = "../../../../../tests/tiered/cache_limits_latency.rs"]
mod tests;
