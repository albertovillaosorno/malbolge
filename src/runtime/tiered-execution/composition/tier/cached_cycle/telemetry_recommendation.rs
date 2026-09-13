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
//   - Pure retry-policy recommendation from one exact telemetry assessment.
// - Must-Not:
//   - Publish policy, infer thresholds, inspect latency, or mutate telemetry.
// - Allows:
//   - Inputs: one assessment and caller-supplied policies for meets/misses.
//   - Outputs: deferred evidence or one exact recommended retry policy.
//   - Side effects: none.
// - Split-When:
//   - Durable/cross-cycle publication gains authority.
// - Merge-When:
//   - Caller orchestration owns assessment and publication atomically.
// - Summary:
//   - Maps exact count assessment to an explicit caller-configured policy.
// - Description:
//   - Insufficient evidence defers; ready evidence never invents policy values.
// - Usage:
//   - Assess telemetry first, then request a recommendation before publication.
// - Defaults:
//   - No policy is recommended before the positive attempt gate is met.
//

//! Pure retry-policy recommendation from exact cached-retry telemetry evidence.

use std::num::NonZeroUsize;

use super::{
    NativeContinuationCachedRetryTelemetry,
    NativeContinuationCachedRetryTelemetryAssessment,
    NativeContinuationCachedRetryTelemetryAssessmentViolations,
};
use crate::retry_policy::NativeContinuationRetryPolicy;

/// Caller-owned policies eligible for one assessment-based recommendation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryPolicyRecommendationSet {
    meets: NativeContinuationRetryPolicy,
    misses: NativeContinuationRetryPolicy,
}

/// Exact result of one count-based retry-policy recommendation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryPolicyRecommendation {
    /// The positive evidence gate was not reached, so publication must defer.
    Deferred {
        /// Attempts represented by the supplied assessment.
        observed_attempts: usize,
        /// Positive caller-required attempt count.
        required_attempts: NonZeroUsize,
    },
    /// Ready telemetry met every threshold and selected the configured policy.
    Meets {
        /// Exact policy selected by caller configuration.
        policy: NativeContinuationRetryPolicy,
        /// Exact telemetry that met the configured thresholds.
        telemetry: NativeContinuationCachedRetryTelemetry,
    },
    /// Ready telemetry missed thresholds and selected the configured policy.
    Misses {
        /// Exact policy selected by caller configuration.
        policy: NativeContinuationRetryPolicy,
        /// Exact telemetry that missed the configured thresholds.
        telemetry: NativeContinuationCachedRetryTelemetry,
        /// Every simultaneously missed configured signal.
        violations: NativeContinuationCachedRetryTelemetryAssessmentViolations,
    },
}

impl NativeContinuationCachedRetryPolicyRecommendationSet {
    /// Returns the policy configured for threshold-meeting evidence.
    #[must_use]
    pub const fn meets(self) -> NativeContinuationRetryPolicy {
        self.meets
    }

    /// Returns the policy configured for threshold-missing evidence.
    #[must_use]
    pub const fn misses(self) -> NativeContinuationRetryPolicy {
        self.misses
    }

    /// Constructs one explicit recommendation table.
    #[must_use]
    pub const fn new(
        meets: NativeContinuationRetryPolicy,
        misses: NativeContinuationRetryPolicy,
    ) -> Self {
        Self { meets, misses }
    }
}

impl NativeContinuationCachedRetryPolicyRecommendation {
    /// Returns the exact recommended policy once evidence is sufficient.
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

/// Recommends one caller-supplied retry policy without publishing it.
#[must_use]
pub const fn recommend_cached_retry_policy(
    assessment: NativeContinuationCachedRetryTelemetryAssessment,
    policies: NativeContinuationCachedRetryPolicyRecommendationSet,
) -> NativeContinuationCachedRetryPolicyRecommendation {
    match assessment {
        NativeContinuationCachedRetryTelemetryAssessment::Insufficient {
            observed_attempts,
            required_attempts,
        } => NativeContinuationCachedRetryPolicyRecommendation::Deferred {
            observed_attempts,
            required_attempts,
        },
        NativeContinuationCachedRetryTelemetryAssessment::Meets {
            telemetry,
        } => NativeContinuationCachedRetryPolicyRecommendation::Meets {
            policy: policies.meets(),
            telemetry,
        },
        NativeContinuationCachedRetryTelemetryAssessment::Misses {
            telemetry,
            violations,
        } => NativeContinuationCachedRetryPolicyRecommendation::Misses {
            policy: policies.misses(),
            telemetry,
            violations,
        },
    }
}
