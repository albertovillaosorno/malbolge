// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Pure caller-configured assessment of exact cached-retry latency evidence.
// - Must-Not:
//   - Read clocks, mutate histograms, infer thresholds, or select retry policy.
// - Allows:
//   - Inputs: one latency histogram and explicit inclusive thresholds.
//   - Outputs: insufficient, meeting, or multi-signal miss evidence.
//   - Side effects: none.
// - Split-When:
//   - Latency-driven recommendation or durable publication gains authority.
// - Merge-When:
//   - Caller orchestration owns latency assessment and recommendation
//     atomically.
// - Summary:
//   - Classifies exact histogram evidence against caller-owned latency limits.
// - Description:
//   - Sample count gates assessment; exact mean comparison uses integer math.
// - Usage:
//   - Assess one live or reconstructed histogram before policy recommendation.
// - Defaults:
//   - Inclusive maxima meet their thresholds exactly.
//

//! Caller-configured exact cached-retry latency assessment.

use std::num::NonZeroUsize;

use super::NativeContinuationCachedRetryLatencyHistogram;

/// Exact ready evidence retained by one latency assessment.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryLatencyAssessmentEvidence {
    above_maximum: usize,
    maximum_nanoseconds: Option<u64>,
    samples: usize,
    total_nanoseconds: u128,
}

/// Exact result of one caller-configured latency assessment.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryLatencyAssessment {
    /// The positive sample gate was not reached, so no latency claim was made.
    Insufficient {
        /// Samples represented by the supplied histogram.
        observed_samples: usize,
        /// Positive caller-required sample count.
        required_samples: NonZeroUsize,
    },
    /// Every configured inclusive maximum was met.
    Meets {
        /// Exact evidence that met all configured thresholds.
        evidence: NativeContinuationCachedRetryLatencyAssessmentEvidence,
    },
    /// The sample gate was met and one or more exact signals missed.
    Misses {
        /// Exact evidence that missed configured thresholds.
        evidence: NativeContinuationCachedRetryLatencyAssessmentEvidence,
        /// Every simultaneously missed configured signal.
        violations: NativeContinuationCachedRetryLatencyAssessmentViolations,
    },
}

/// One exact ready-latency signal with a configured inclusive maximum.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryLatencyAssessmentSignal {
    /// Exact arithmetic mean latency across all recorded samples.
    AverageNanoseconds,
    /// Largest recorded latency sample.
    MaximumNanoseconds,
    /// Samples above the histogram's final inclusive bucket bound.
    OverflowSamples,
}

/// Complete caller-owned thresholds for one pure latency assessment.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryLatencyAssessmentThresholds {
    maximum_average_nanoseconds: u64,
    maximum_nanoseconds: u64,
    maximum_overflow_samples: usize,
    samples: NonZeroUsize,
}

/// Every ready-latency signal that missed its configured maximum.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryLatencyAssessmentViolations {
    bits: u8,
}

impl NativeContinuationCachedRetryLatencyAssessmentEvidence {
    /// Returns samples above the final configured histogram bound.
    #[must_use]
    pub const fn above_maximum(self) -> usize {
        self.above_maximum
    }

    /// Returns the largest recorded latency, when retained by the histogram.
    #[must_use]
    pub const fn maximum_nanoseconds(self) -> Option<u64> {
        self.maximum_nanoseconds
    }

    /// Returns the exact number of recorded samples.
    #[must_use]
    pub const fn samples(self) -> usize {
        self.samples
    }

    /// Returns the exact sum of all recorded latency nanoseconds.
    #[must_use]
    pub const fn total_nanoseconds(self) -> u128 {
        self.total_nanoseconds
    }
}

impl NativeContinuationCachedRetryLatencyAssessmentSignal {
    const fn mask(self) -> u8 {
        match self {
            Self::AverageNanoseconds => 1,
            Self::MaximumNanoseconds => 2,
            Self::OverflowSamples => 4,
        }
    }
}

impl NativeContinuationCachedRetryLatencyAssessmentThresholds {
    /// Returns the inclusive maximum exact arithmetic mean latency.
    #[must_use]
    pub const fn maximum_average_nanoseconds(self) -> u64 {
        self.maximum_average_nanoseconds
    }

    /// Returns the inclusive maximum individual latency sample.
    #[must_use]
    pub const fn maximum_nanoseconds(self) -> u64 {
        self.maximum_nanoseconds
    }

    /// Returns the inclusive maximum overflow-bin sample count.
    #[must_use]
    pub const fn maximum_overflow_samples(self) -> usize {
        self.maximum_overflow_samples
    }

    /// Constructs one complete caller-owned latency threshold set.
    #[must_use]
    pub const fn new(
        samples: NonZeroUsize,
        maximum_average_nanoseconds: u64,
        maximum_nanoseconds: u64,
        maximum_overflow_samples: usize,
    ) -> Self {
        Self {
            maximum_average_nanoseconds,
            maximum_nanoseconds,
            maximum_overflow_samples,
            samples,
        }
    }

    /// Returns the positive sample gate required before assessment.
    #[must_use]
    pub const fn samples(self) -> NonZeroUsize {
        self.samples
    }
}

impl NativeContinuationCachedRetryLatencyAssessmentViolations {
    /// Reports whether one exact latency signal missed its configured maximum.
    #[must_use]
    pub const fn contains(
        self,
        signal: NativeContinuationCachedRetryLatencyAssessmentSignal,
    ) -> bool {
        self.bits & signal.mask() != 0
    }

    /// Reports whether every ready-latency threshold was met.
    #[must_use]
    pub const fn is_empty(self) -> bool {
        self.bits == 0
    }
}

/// Assesses exact latency evidence without selecting or publishing retry
/// policy.
#[must_use]
pub fn assess_cached_retry_latency(
    histogram: &NativeContinuationCachedRetryLatencyHistogram,
    thresholds: NativeContinuationCachedRetryLatencyAssessmentThresholds,
) -> NativeContinuationCachedRetryLatencyAssessment {
    if histogram.samples() < thresholds.samples().get() {
        return NativeContinuationCachedRetryLatencyAssessment::Insufficient {
            observed_samples: histogram.samples(),
            required_samples: thresholds.samples(),
        };
    }
    let evidence = NativeContinuationCachedRetryLatencyAssessmentEvidence {
        above_maximum: histogram.above_maximum(),
        maximum_nanoseconds: histogram.maximum_nanoseconds(),
        samples: histogram.samples(),
        total_nanoseconds: histogram.total_nanoseconds(),
    };
    let mut bits = 0;
    if exact_average_exceeds(
        evidence.total_nanoseconds(),
        evidence.samples(),
        thresholds.maximum_average_nanoseconds(),
    ) {
        bits |= NativeContinuationCachedRetryLatencyAssessmentSignal::
            AverageNanoseconds
            .mask();
    }
    if evidence
        .maximum_nanoseconds()
        .is_none_or(|maximum| maximum > thresholds.maximum_nanoseconds())
    {
        bits |= NativeContinuationCachedRetryLatencyAssessmentSignal::
            MaximumNanoseconds
            .mask();
    }
    if evidence.above_maximum() > thresholds.maximum_overflow_samples() {
        bits |= NativeContinuationCachedRetryLatencyAssessmentSignal::
            OverflowSamples
            .mask();
    }
    let violations =
        NativeContinuationCachedRetryLatencyAssessmentViolations { bits };
    if violations.is_empty() {
        NativeContinuationCachedRetryLatencyAssessment::Meets { evidence }
    } else {
        NativeContinuationCachedRetryLatencyAssessment::Misses {
            evidence,
            violations,
        }
    }
}

fn exact_average_exceeds(total: u128, samples: usize, maximum: u64) -> bool {
    let Ok(sample_count) = u128::try_from(samples) else {
        return true;
    };
    let Some(maximum_total) = u128::from(maximum).checked_mul(sample_count)
    else {
        return true;
    };
    total > maximum_total
}
