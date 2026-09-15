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
//   - Durable active-policy publication from ready cached-retry
//     recommendations.
// - Must-Not:
//   - Infer recommendations, mutate requests, choose storage paths, or retry
//     CAS.
// - Allows:
//   - Inputs: exact recommendation, expected active state, bound, and store.
//   - Outputs: deferred evidence or exact typed active-state CAS evidence.
//   - Side effects: one conditional durable publication for ready evidence
//     only.
// - Split-When:
//   - Multi-signal arbitration or distributed consensus gains authority.
// - Merge-When:
//   - One policy orchestrator owns recommendation, durable CAS, and binding.
// - Summary:
//   - Publishes ready telemetry policy across cycles without mutating requests.
// - Description:
//   - Deferral performs zero storage work; ready evidence retains its exact
//     CAS.
// - Usage:
//   - Publish recommendation durably, then bind returned active state
//     explicitly.
// - Defaults:
//   - Insufficient evidence never touches durable active-policy state.
//

//! Durable cross-cycle publication of cached-retry policy recommendations.

use std::num::NonZeroUsize;

use super::{
    NativeContinuationCachedRetryLatencyPolicyRecommendation,
    NativeContinuationCachedRetryPolicyRecommendation,
};
use crate::blob_store::{
    NativeContinuationBlobStore as BlobStore,
    NativeContinuationConditionalBlobStore as ConditionalBlobStore,
    NativeContinuationDurableBlobStore as DurableBlobStore,
};
use crate::retry_policy::NativeContinuationRetryPolicy;
use crate::retry_policy_cas::{
    NativeContinuationRetryPolicyStateCas,
    NativeContinuationRetryPolicyStateCasError,
    compare_and_swap_native_continuation_retry_policy_state_durably,
};
use crate::retry_policy_owner::NativeContinuationRetryPolicyState;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct DurablePolicyPublicationRequest {
    expected: Option<NativeContinuationRetryPolicyState>,
    maximum_bytes: NonZeroUsize,
    policy: Option<NativeContinuationRetryPolicy>,
}

/// Durable publication decision retaining its exact recommendation evidence.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryDurablePolicyPublication<
    Recommendation,
    DurabilityError,
> {
    /// Recommendation evidence was insufficient and storage was not touched.
    Deferred {
        /// Exact insufficient recommendation evidence.
        recommendation: Recommendation,
    },
    /// Ready recommendation attempted typed durable active-policy CAS.
    Ready {
        /// Exact durable/conflict publication evidence.
        publication: NativeContinuationRetryPolicyStateCas<DurabilityError>,
        /// Exact ready recommendation evidence that selected the candidate.
        recommendation: Recommendation,
    },
}

/// Result of durable recommendation publication before request binding.
pub type NativeContinuationCachedRetryDurablePolicyPublicationResult<
    Recommendation,
    StoreError,
    DurabilityError,
> = Result<
    NativeContinuationCachedRetryDurablePolicyPublication<
        Recommendation,
        DurabilityError,
    >,
    NativeContinuationRetryPolicyStateCasError<StoreError>,
>;

/// Durable recommendation publication result specialized to one store type.
pub type NativeContinuationCachedRetryDurablePolicyStoreResult<
    Recommendation,
    Store,
> = NativeContinuationCachedRetryDurablePolicyPublicationResult<
    Recommendation,
    <Store as BlobStore>::Error,
    <Store as DurableBlobStore>::DurabilityError,
>;

type DurablePolicyStoreResult<Recommendation, Store> =
    NativeContinuationCachedRetryDurablePolicyStoreResult<
        Recommendation,
        Store,
    >;

impl<Recommendation, DurabilityError>
    NativeContinuationCachedRetryDurablePolicyPublication<
        Recommendation,
        DurabilityError,
    >
{
    /// Reports whether insufficient evidence skipped durable publication.
    #[must_use]
    pub const fn is_deferred(&self) -> bool {
        matches!(self, Self::Deferred { .. })
    }

    /// Returns typed active-state CAS evidence when recommendation was ready.
    #[must_use]
    pub const fn publication(
        &self,
    ) -> Option<&NativeContinuationRetryPolicyStateCas<DurabilityError>> {
        match self {
            Self::Deferred { .. } => None,
            Self::Ready { publication, .. } => Some(publication),
        }
    }

    /// Returns the exact recommendation retained by this publication decision.
    #[must_use]
    pub const fn recommendation(&self) -> &Recommendation {
        match self {
            Self::Deferred { recommendation }
            | Self::Ready { recommendation, .. } => recommendation,
        }
    }
}

/// Durably publishes one count-telemetry recommendation into active policy.
///
/// # Errors
///
/// Returns typed active-state CAS failure for ready evidence only. Deferred
/// recommendation performs no storage operation and cannot return store error.
pub fn publish_cached_retry_policy_recommendation_durably<Store>(
    store: &mut Store,
    expected: Option<NativeContinuationRetryPolicyState>,
    recommendation: NativeContinuationCachedRetryPolicyRecommendation,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationCachedRetryDurablePolicyStoreResult<
    NativeContinuationCachedRetryPolicyRecommendation,
    Store,
>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    publish_recommendation_durably(
        store,
        recommendation,
        DurablePolicyPublicationRequest {
            expected,
            maximum_bytes,
            policy: recommendation.policy(),
        },
    )
}

/// Durably publishes one latency recommendation into active policy.
///
/// # Errors
///
/// Returns typed active-state CAS failure for ready evidence only. Deferred
/// recommendation performs no storage operation and cannot return store error.
pub fn publish_cached_retry_latency_policy_recommendation_durably<Store>(
    store: &mut Store,
    expected: Option<NativeContinuationRetryPolicyState>,
    recommendation: NativeContinuationCachedRetryLatencyPolicyRecommendation,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationCachedRetryDurablePolicyStoreResult<
    NativeContinuationCachedRetryLatencyPolicyRecommendation,
    Store,
>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    publish_recommendation_durably(
        store,
        recommendation,
        DurablePolicyPublicationRequest {
            expected,
            maximum_bytes,
            policy: recommendation.policy(),
        },
    )
}

fn publish_recommendation_durably<Store, Recommendation>(
    store: &mut Store,
    recommendation: Recommendation,
    request: DurablePolicyPublicationRequest,
) -> DurablePolicyStoreResult<Recommendation, Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    let Some(candidate) = request.policy else {
        return Ok(
            NativeContinuationCachedRetryDurablePolicyPublication::Deferred {
                recommendation,
            },
        );
    };
    let publication =
        compare_and_swap_native_continuation_retry_policy_state_durably(
            store,
            request.expected,
            candidate,
            request.maximum_bytes,
        )?;
    Ok(
        NativeContinuationCachedRetryDurablePolicyPublication::Ready {
            publication,
            recommendation,
        },
    )
}
