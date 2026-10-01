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
//   - Durable active-policy publication plus exact cached-cycle request
//     binding.
// - Must-Not:
//   - Infer recommendations, retry conflicts, choose storage paths, or execute.
// - Allows:
//   - Inputs: one request, expected active state, recommendation/arbitration
//     evidence, byte bound, and conditional durable store.
//   - Outputs: unchanged no-policy/CAS-conflict request or request bound to
//     committed revisioned active state with exact durable publication
//     evidence.
//   - Side effects: delegated conditional durable policy publication only.
// - Split-When:
//   - Process-local owner synchronization or conflict retry gains authority.
// - Merge-When:
//   - Product orchestration owns telemetry assessment through cycle execution.
// - Summary:
//   - Binds only policy state proven committed by durable active-state CAS.
// - Description:
//   - No-policy evidence and CAS conflict leave request policy untouched;
//     post-commit sync failure still binds committed state with durability
//     error.
// - Usage:
//   - Consume recommendation/arbitration evidence before its target cached
//     cycle.
// - Defaults:
//   - No committed active state means no request-policy mutation.
//

//! Durable cached-retry policy evidence publication and request binding.

use std::num::NonZeroUsize;

use super::{
    NativeContinuationCachedRetryActivePolicyPublication,
    NativeContinuationCachedRetryCycleRequest,
    NativeContinuationCachedRetryDurablePolicyPublication,
    NativeContinuationCachedRetryLatencyPolicyRecommendation,
    NativeContinuationCachedRetryPolicyArbitration,
    NativeContinuationCachedRetryPolicyRecommendation,
    publish_cached_retry_active_policy,
    publish_cached_retry_latency_policy_recommendation_durably,
    publish_cached_retry_policy_arbitration_durably,
    publish_cached_retry_policy_recommendation_durably,
};
use crate::blob_store::{
    NativeContinuationBlobStore as BlobStore,
    NativeContinuationConditionalBlobStore as ConditionalBlobStore,
    NativeContinuationDurableBlobStore as DurableBlobStore,
};
use crate::retry_policy_cas::{
    NativeContinuationRetryPolicyStateCas,
    NativeContinuationRetryPolicyStateCasError,
};
use crate::retry_policy_owner::NativeContinuationRetryPolicyState;

/// Durable publication plus request binding for one exact recommendation.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryDurablePolicyBinding<
    Recommendation,
    DurabilityError,
> {
    /// Candidate state committed and was bound into the returned request.
    Bound {
        /// Exact request-scoped active-state binding evidence.
        binding: NativeContinuationCachedRetryActivePolicyPublication,
        /// Exact durable publication evidence, including sync failure if any.
        publication: NativeContinuationCachedRetryDurablePolicyPublication<
            Recommendation,
            DurabilityError,
        >,
    },
    /// Durable state differed from the caller's expectation; request unchanged.
    Conflict {
        /// Exact durable conflict evidence.
        publication: NativeContinuationCachedRetryDurablePolicyPublication<
            Recommendation,
            DurabilityError,
        >,
        /// Unchanged cached-cycle request owner.
        request: Box<NativeContinuationCachedRetryCycleRequest>,
    },
    /// Input exposed no publishable policy; request is unchanged.
    Deferred {
        /// Exact non-publishable durable-publication evidence.
        publication: NativeContinuationCachedRetryDurablePolicyPublication<
            Recommendation,
            DurabilityError,
        >,
        /// Unchanged cached-cycle request owner.
        request: Box<NativeContinuationCachedRetryCycleRequest>,
    },
}

/// Caller-owned inputs for one durable policy publication plus request binding.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryDurablePolicyBindingRequest {
    expected: Option<NativeContinuationRetryPolicyState>,
    maximum_bytes: NonZeroUsize,
    request: NativeContinuationCachedRetryCycleRequest,
}

/// Durable policy binding result specialized to one store type.
pub type NativeContinuationCachedRetryDurablePolicyBindingStoreResult<
    Recommendation,
    Store,
> = Result<
    NativeContinuationCachedRetryDurablePolicyBinding<
        Recommendation,
        <Store as DurableBlobStore>::DurabilityError,
    >,
    NativeContinuationRetryPolicyStateCasError<<Store as BlobStore>::Error>,
>;

impl<Recommendation, DurabilityError>
    NativeContinuationCachedRetryDurablePolicyBinding<
        Recommendation,
        DurabilityError,
    >
{
    /// Returns committed active state when the request was rebound.
    #[must_use]
    pub const fn active_state(
        &self,
    ) -> Option<NativeContinuationRetryPolicyState> {
        match self {
            Self::Bound { binding, .. } => Some(binding.active_state()),
            Self::Conflict { .. } | Self::Deferred { .. } => None,
        }
    }

    /// Consumes orchestration evidence into the resulting cached-cycle request.
    #[must_use]
    pub fn into_request(self) -> NativeContinuationCachedRetryCycleRequest {
        match self {
            Self::Bound { binding, .. } => binding.into_request(),
            Self::Conflict { request, .. } | Self::Deferred { request, .. } => {
                *request
            },
        }
    }

    /// Reports whether committed durable state was bound into the request.
    #[must_use]
    pub const fn is_bound(&self) -> bool {
        matches!(self, Self::Bound { .. })
    }

    /// Returns exact durable recommendation-publication evidence.
    #[must_use]
    pub const fn publication(
        &self,
    ) -> &NativeContinuationCachedRetryDurablePolicyPublication<
        Recommendation,
        DurabilityError,
    > {
        match self {
            Self::Bound { publication, .. }
            | Self::Conflict { publication, .. }
            | Self::Deferred { publication, .. } => publication,
        }
    }

    /// Returns the resulting cached-cycle request.
    #[must_use]
    pub fn request(&self) -> &NativeContinuationCachedRetryCycleRequest {
        match self {
            Self::Bound { binding, .. } => binding.request(),
            Self::Conflict { request, .. } | Self::Deferred { request, .. } => {
                request
            },
        }
    }
}

impl NativeContinuationCachedRetryDurablePolicyBindingRequest {
    /// Binds explicit durable-state expectations to one future cycle request.
    #[must_use]
    pub const fn new(
        request: NativeContinuationCachedRetryCycleRequest,
        expected: Option<NativeContinuationRetryPolicyState>,
        maximum_bytes: NonZeroUsize,
    ) -> Self {
        Self {
            expected,
            maximum_bytes,
            request,
        }
    }
}

fn bind_durable_publication<Recommendation, DurabilityError>(
    request: NativeContinuationCachedRetryCycleRequest,
    publication: NativeContinuationCachedRetryDurablePolicyPublication<
        Recommendation,
        DurabilityError,
    >,
) -> NativeContinuationCachedRetryDurablePolicyBinding<
    Recommendation,
    DurabilityError,
> {
    let committed_state =
        publication.publication().and_then(|outcome| match outcome {
            NativeContinuationRetryPolicyStateCas::Durable {
                current, ..
            }
            | NativeContinuationRetryPolicyStateCas::Published {
                current,
                ..
            } => Some(*current),
            NativeContinuationRetryPolicyStateCas::Conflict { .. } => None,
        });
    if let Some(state) = committed_state {
        return NativeContinuationCachedRetryDurablePolicyBinding::Bound {
            binding: publish_cached_retry_active_policy(request, state),
            publication,
        };
    }
    if publication.is_deferred() {
        NativeContinuationCachedRetryDurablePolicyBinding::Deferred {
            publication,
            request: Box::new(request),
        }
    } else {
        NativeContinuationCachedRetryDurablePolicyBinding::Conflict {
            publication,
            request: Box::new(request),
        }
    }
}

/// Durably publishes and binds one latency recommendation into its next
/// request.
///
/// # Errors
///
/// Returns typed durable active-state CAS failure before any binding occurs.
pub fn publish_and_bind_cached_retry_latency_policy_recommendation_durably<
    Store,
>(
    store: &mut Store,
    binding: NativeContinuationCachedRetryDurablePolicyBindingRequest,
    recommendation: NativeContinuationCachedRetryLatencyPolicyRecommendation,
) -> NativeContinuationCachedRetryDurablePolicyBindingStoreResult<
    NativeContinuationCachedRetryLatencyPolicyRecommendation,
    Store,
>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    let publication =
        publish_cached_retry_latency_policy_recommendation_durably(
            store,
            binding.expected,
            recommendation,
            binding.maximum_bytes,
        )?;
    Ok(bind_durable_publication(binding.request, publication))
}

/// Durably publishes and binds one agreed multi-signal policy arbitration.
///
/// # Errors
///
/// Returns typed durable active-state CAS failure before any binding occurs.
/// Deferred or conflicting signal evidence performs no storage operation.
pub fn publish_and_bind_cached_retry_policy_arbitration_durably<Store>(
    store: &mut Store,
    binding: NativeContinuationCachedRetryDurablePolicyBindingRequest,
    arbitration: &NativeContinuationCachedRetryPolicyArbitration,
) -> NativeContinuationCachedRetryDurablePolicyBindingStoreResult<
    NativeContinuationCachedRetryPolicyArbitration,
    Store,
>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    let publication = publish_cached_retry_policy_arbitration_durably(
        store,
        binding.expected,
        arbitration,
        binding.maximum_bytes,
    )?;
    Ok(bind_durable_publication(binding.request, publication))
}

/// Durably publishes and binds one count recommendation into its next request.
///
/// # Errors
///
/// Returns typed durable active-state CAS failure before any binding occurs.
pub fn publish_and_bind_cached_retry_policy_recommendation_durably<Store>(
    store: &mut Store,
    binding: NativeContinuationCachedRetryDurablePolicyBindingRequest,
    recommendation: NativeContinuationCachedRetryPolicyRecommendation,
) -> NativeContinuationCachedRetryDurablePolicyBindingStoreResult<
    NativeContinuationCachedRetryPolicyRecommendation,
    Store,
>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    let publication = publish_cached_retry_policy_recommendation_durably(
        store,
        binding.expected,
        recommendation,
        binding.maximum_bytes,
    )?;
    Ok(bind_durable_publication(binding.request, publication))
}
