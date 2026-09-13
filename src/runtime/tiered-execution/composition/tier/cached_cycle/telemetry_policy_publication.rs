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
//   - Request-scoped publication of one cached-retry policy recommendation.
// - Must-Not:
//   - Infer recommendations, mutate durable/global policy, or execute a tier.
// - Allows:
//   - Inputs: one cached-cycle request and one exact recommendation.
//   - Outputs: deferred request or request with the recommended policy
//     published.
//   - Side effects: none outside the consumed and returned request owner.
// - Split-When:
//   - Durable/cross-cycle publication or concurrent policy ownership is added.
// - Merge-When:
//   - Recommendation and request construction become one atomic use case.
// - Summary:
//   - Publishes sufficient recommendation evidence into one future cycle
//     request.
// - Description:
//   - Deferral leaves policy unchanged; publication retains previous policy.
// - Usage:
//   - Consume a recommendation immediately before executing its target request.
// - Defaults:
//   - Insufficient evidence never changes the request policy.
//

//! Request-scoped publication of cached-retry policy recommendations.

use super::{
    NativeContinuationCachedRetryCycleRequest,
    NativeContinuationCachedRetryLatencyPolicyRecommendation,
    NativeContinuationCachedRetryPolicyRecommendation,
};
use crate::retry_policy::NativeContinuationRetryPolicy;

/// Request owner after one explicit latency-recommendation publication
/// decision.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryLatencyPolicyPublication {
    /// Latency evidence was insufficient; the request policy is unchanged.
    Deferred {
        /// Exact latency recommendation evidence that deferred publication.
        recommendation:
            NativeContinuationCachedRetryLatencyPolicyRecommendation,
        /// Unchanged cached-cycle request owner.
        request: Box<NativeContinuationCachedRetryCycleRequest>,
    },
    /// Sufficient latency evidence replaced the request-scoped retry policy.
    Published {
        /// Exact policy now carried by the returned request.
        current_policy: NativeContinuationRetryPolicy,
        /// Policy carried by the request before publication.
        previous_policy: NativeContinuationRetryPolicy,
        /// Exact sufficient latency recommendation evidence.
        recommendation:
            NativeContinuationCachedRetryLatencyPolicyRecommendation,
        /// Cached-cycle request carrying the published policy.
        request: Box<NativeContinuationCachedRetryCycleRequest>,
    },
}

impl NativeContinuationCachedRetryLatencyPolicyPublication {
    /// Consumes publication evidence into the cached-cycle request owner.
    #[must_use]
    pub fn into_request(self) -> NativeContinuationCachedRetryCycleRequest {
        match self {
            Self::Deferred { request, .. }
            | Self::Published { request, .. } => *request,
        }
    }

    /// Reports whether sufficient latency evidence published replacement
    /// policy.
    #[must_use]
    pub const fn is_published(&self) -> bool {
        matches!(self, Self::Published { .. })
    }

    /// Returns the exact latency recommendation used for this decision.
    #[must_use]
    pub const fn recommendation(
        &self,
    ) -> NativeContinuationCachedRetryLatencyPolicyRecommendation {
        match self {
            Self::Deferred { recommendation, .. }
            | Self::Published { recommendation, .. } => *recommendation,
        }
    }

    /// Returns the request resulting from this publication decision.
    #[must_use]
    pub fn request(&self) -> &NativeContinuationCachedRetryCycleRequest {
        match self {
            Self::Deferred { request, .. }
            | Self::Published { request, .. } => request,
        }
    }
}

/// Request owner after one explicit recommendation-publication decision.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryPolicyPublication {
    /// Evidence was insufficient; the request policy remains unchanged.
    Deferred {
        /// Exact recommendation evidence that deferred publication.
        recommendation: NativeContinuationCachedRetryPolicyRecommendation,
        /// Unchanged cached-cycle request owner.
        request: Box<NativeContinuationCachedRetryCycleRequest>,
    },
    /// Sufficient evidence replaced the request-scoped retry policy.
    Published {
        /// Exact policy now carried by the returned request.
        current_policy: NativeContinuationRetryPolicy,
        /// Policy carried by the request before publication.
        previous_policy: NativeContinuationRetryPolicy,
        /// Exact sufficient recommendation evidence.
        recommendation: NativeContinuationCachedRetryPolicyRecommendation,
        /// Cached-cycle request carrying the published policy.
        request: Box<NativeContinuationCachedRetryCycleRequest>,
    },
}

impl NativeContinuationCachedRetryPolicyPublication {
    /// Consumes publication evidence into the cached-cycle request owner.
    #[must_use]
    pub fn into_request(self) -> NativeContinuationCachedRetryCycleRequest {
        match self {
            Self::Deferred { request, .. }
            | Self::Published { request, .. } => *request,
        }
    }

    /// Reports whether sufficient evidence published a replacement policy.
    #[must_use]
    pub const fn is_published(&self) -> bool {
        matches!(self, Self::Published { .. })
    }

    /// Returns the exact recommendation used for this publication decision.
    #[must_use]
    pub const fn recommendation(
        &self,
    ) -> NativeContinuationCachedRetryPolicyRecommendation {
        match self {
            Self::Deferred { recommendation, .. }
            | Self::Published { recommendation, .. } => *recommendation,
        }
    }

    /// Returns the request resulting from this publication decision.
    #[must_use]
    pub fn request(&self) -> &NativeContinuationCachedRetryCycleRequest {
        match self {
            Self::Deferred { request, .. }
            | Self::Published { request, .. } => request,
        }
    }
}

/// Publishes one sufficient recommendation into one cached-cycle request.
#[must_use]
pub fn publish_cached_retry_policy_recommendation(
    mut request: NativeContinuationCachedRetryCycleRequest,
    recommendation: NativeContinuationCachedRetryPolicyRecommendation,
) -> NativeContinuationCachedRetryPolicyPublication {
    let Some(current_policy) = recommendation.policy() else {
        return NativeContinuationCachedRetryPolicyPublication::Deferred {
            recommendation,
            request: Box::new(request),
        };
    };
    let previous_policy = request.policy;
    request.policy = current_policy;
    NativeContinuationCachedRetryPolicyPublication::Published {
        current_policy,
        previous_policy,
        recommendation,
        request: Box::new(request),
    }
}

/// Publishes one sufficient latency recommendation into one cached-cycle
/// request.
#[must_use]
pub fn publish_cached_retry_latency_policy_recommendation(
    mut request: NativeContinuationCachedRetryCycleRequest,
    recommendation: NativeContinuationCachedRetryLatencyPolicyRecommendation,
) -> NativeContinuationCachedRetryLatencyPolicyPublication {
    let Some(current_policy) = recommendation.policy() else {
        return NativeContinuationCachedRetryLatencyPolicyPublication::Deferred {
            recommendation,
            request: Box::new(request),
        };
    };
    let previous_policy = request.policy;
    request.policy = current_policy;
    NativeContinuationCachedRetryLatencyPolicyPublication::Published {
        current_policy,
        previous_policy,
        recommendation,
        request: Box::new(request),
    }
}
