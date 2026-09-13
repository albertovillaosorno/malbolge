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
//   - Pure retry-policy recommendation from one exact latency assessment.
// - Must-Not:
//   - Publish policy, infer thresholds, read clocks, or mutate latency
//     evidence.
// - Allows:
//   - Inputs: one latency assessment and caller-supplied meets/misses policies.
//   - Outputs: deferred evidence or one exact recommended retry policy.
//   - Side effects: none.
// - Split-When:
//   - Durable/cross-cycle policy publication gains authority.
// - Merge-When:
//   - Caller orchestration owns latency recommendation and publication
//     atomically.
// - Summary:
//   - Maps exact latency assessment to an explicit caller-configured policy.
// - Description:
//   - Insufficient evidence defers; ready evidence never invents policy values.
// - Usage:
//   - Assess latency first, then request a recommendation before publication.
// - Defaults:
//   - No policy is recommended before the positive sample gate is met.
//

//! Pure retry-policy recommendation from exact cached-retry latency evidence.

use std::num::NonZeroUsize;

use super::{
    NativeContinuationCachedRetryLatencyAssessment,
    NativeContinuationCachedRetryLatencyAssessmentEvidence,
    NativeContinuationCachedRetryLatencyAssessmentViolations,
    NativeContinuationCachedRetryPolicyRecommendationSet,
};
use crate::retry_policy::NativeContinuationRetryPolicy;

/// Exact result of one latency-driven retry-policy recommendation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryLatencyPolicyRecommendation {
    /// The positive sample gate was not reached, so publication must defer.
    Deferred {
        /// Samples represented by the supplied assessment.
        observed_samples: usize,
        /// Positive caller-required sample count.
        required_samples: NonZeroUsize,
    },
    /// Ready latency met every threshold and selected the configured policy.
    Meets {
        /// Exact ready latency evidence that met the thresholds.
        evidence: NativeContinuationCachedRetryLatencyAssessmentEvidence,
        /// Exact policy selected by caller configuration.
        policy: NativeContinuationRetryPolicy,
    },
    /// Ready latency missed thresholds and selected the configured policy.
    Misses {
        /// Exact ready latency evidence that missed the thresholds.
        evidence: NativeContinuationCachedRetryLatencyAssessmentEvidence,
        /// Exact policy selected by caller configuration.
        policy: NativeContinuationRetryPolicy,
        /// Every simultaneously missed configured latency signal.
        violations: NativeContinuationCachedRetryLatencyAssessmentViolations,
    },
}

impl NativeContinuationCachedRetryLatencyPolicyRecommendation {
    /// Returns the exact recommended policy once latency evidence is
    /// sufficient.
    #[must_use]
    pub const fn policy(self) -> Option<NativeContinuationRetryPolicy> {
        match self {
            Self::Deferred { .. } => None,
            Self::Meets { policy, .. } | Self::Misses { policy, .. } => {
                Some(policy)
            },
        }
    }
}

/// Recommends one caller-supplied retry policy from exact latency assessment.
#[must_use]
pub const fn recommend_cached_retry_latency_policy(
    assessment: NativeContinuationCachedRetryLatencyAssessment,
    policies: NativeContinuationCachedRetryPolicyRecommendationSet,
) -> NativeContinuationCachedRetryLatencyPolicyRecommendation {
    match assessment {
        NativeContinuationCachedRetryLatencyAssessment::Insufficient {
            observed_samples,
            required_samples,
        } => {
            NativeContinuationCachedRetryLatencyPolicyRecommendation::Deferred {
                observed_samples,
                required_samples,
            }
        },
        NativeContinuationCachedRetryLatencyAssessment::Meets { evidence } => {
            NativeContinuationCachedRetryLatencyPolicyRecommendation::Meets {
                evidence,
                policy: policies.meets(),
            }
        },
        NativeContinuationCachedRetryLatencyAssessment::Misses {
            evidence,
            violations,
        } => NativeContinuationCachedRetryLatencyPolicyRecommendation::Misses {
            evidence,
            policy: policies.misses(),
            violations,
        },
    }
}
