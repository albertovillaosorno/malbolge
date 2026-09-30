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
//   - Pure arbitration between exact count and latency retry-policy
//     recommendations.
// - Must-Not:
//   - Assess telemetry, infer policy precedence, publish policy, or mutate
//     evidence.
// - Allows:
//   - Inputs: one count recommendation and one latency recommendation.
//   - Outputs: deferred, agreed, or conflicting recommendation evidence.
//   - Side effects: none.
// - Split-When:
//   - Additional signals or caller-selected precedence gain authority.
// - Merge-When:
//   - Product orchestration owns assessment through durable policy publication.
// - Summary:
//   - Requires ready count and latency evidence to agree on one exact policy.
// - Description:
//   - Missing evidence or disagreement cannot authorize policy publication.
// - Usage:
//   - Arbitrate independently assessed count and latency recommendations before
//     any request-scoped or durable publication.
// - Defaults:
//   - No signal has implicit precedence.
//

//! Conservative count-plus-latency retry-policy recommendation arbitration.

use super::{
    NativeContinuationCachedRetryLatencyPolicyRecommendation,
    NativeContinuationCachedRetryPolicyRecommendation,
};
use crate::retry_policy::NativeContinuationRetryPolicy;

/// Exact result of count-plus-latency retry-policy arbitration.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryPolicyArbitration {
    /// Both ready signals selected the identical retry policy.
    Agreed {
        /// Exact count recommendation participating in agreement.
        count: NativeContinuationCachedRetryPolicyRecommendation,
        /// Exact latency recommendation participating in agreement.
        latency: NativeContinuationCachedRetryLatencyPolicyRecommendation,
        /// Exact policy selected independently by both signals.
        policy: NativeContinuationRetryPolicy,
    },
    /// Both signals were ready but selected different retry policies.
    Conflict {
        /// Exact ready count recommendation.
        count: NativeContinuationCachedRetryPolicyRecommendation,
        /// Policy selected by count evidence.
        count_policy: NativeContinuationRetryPolicy,
        /// Exact ready latency recommendation.
        latency: NativeContinuationCachedRetryLatencyPolicyRecommendation,
        /// Policy selected by latency evidence.
        latency_policy: NativeContinuationRetryPolicy,
    },
    /// At least one signal lacked sufficient evidence to select policy.
    Deferred {
        /// Exact count recommendation, ready or deferred.
        count: NativeContinuationCachedRetryPolicyRecommendation,
        /// Exact latency recommendation, ready or deferred.
        latency: NativeContinuationCachedRetryLatencyPolicyRecommendation,
    },
}

impl NativeContinuationCachedRetryPolicyArbitration {
    /// Returns policy authority only when both ready signals exactly agree.
    #[must_use]
    pub const fn policy(self) -> Option<NativeContinuationRetryPolicy> {
        match self {
            Self::Agreed { policy, .. } => Some(policy),
            Self::Conflict { .. } | Self::Deferred { .. } => None,
        }
    }
}

/// Arbitrates count and latency recommendations without signal precedence.
#[must_use]
pub fn arbitrate_cached_retry_policy_recommendations(
    count: NativeContinuationCachedRetryPolicyRecommendation,
    latency: NativeContinuationCachedRetryLatencyPolicyRecommendation,
) -> NativeContinuationCachedRetryPolicyArbitration {
    match (count.policy(), latency.policy()) {
        (Some(count_policy), Some(latency_policy))
            if count_policy == latency_policy =>
        {
            NativeContinuationCachedRetryPolicyArbitration::Agreed {
                count,
                latency,
                policy: count_policy,
            }
        },
        (Some(count_policy), Some(latency_policy)) => {
            NativeContinuationCachedRetryPolicyArbitration::Conflict {
                count,
                count_policy,
                latency,
                latency_policy,
            }
        },
        (None, _) | (_, None) => {
            NativeContinuationCachedRetryPolicyArbitration::Deferred {
                count,
                latency,
            }
        },
    }
}
