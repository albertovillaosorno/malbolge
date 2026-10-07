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
//   - Explicit post-observation cache-limit planning and activation
//     orchestration.
// - Must-Not:
//   - Execute cached cycles, mutate telemetry owners, infer policy
//     configuration, retry durable conflicts, or hide telemetry-publication
//     failures.
// - Allows:
//   - Inputs: immutable observed-cycle telemetry publication, caller-owned
//     cache policy, durable expectation, bounded store, live cache, and memory
//     adapter.
//   - Outputs: unpublished, planned-without-authority, activated, or exact
//     prepublication activation failure retaining the originating plan.
//   - Side effects: at most the existing durable/live activation transaction,
//     and only after telemetry publication produced recommendation authority.
// - Split-When:
//   - Product scheduling, retries, or asynchronous triggering gains authority.
// - Merge-When:
//   - One product owner subsumes observed execution through cache activation.
// - Summary:
//   - Triggers explicit cache policy only from successfully published
//     telemetry.
// - Description:
//   - Observation completes first; this separate use case may then plan and
//     act.
// - Usage:
//   - Invoke explicitly after one observed cycle returns publication evidence.
// - Defaults:
//   - Failed telemetry or non-authoritative plans perform no storage/cache
//     work.
//

//! Explicit cache-limit orchestration after observed telemetry publication.

use std::num::NonZeroUsize;

use crate::blob_store::{
    NativeContinuationBlobStore as BlobStore,
    NativeContinuationConditionalBlobStore as ConditionalBlobStore,
    NativeContinuationDurableBlobStore as DurableBlobStore,
};
use crate::execution_native::{
    NativeExecutableMemoryAdapter, NativeExecutableSequenceCache,
    NativeExecutableSequenceCacheLimits, NativeExecutableSequenceLeaseCache,
};
use crate::{
    cached_cycle as cached, executable_cache_limits_durable_activation as ac,
    executable_cache_limits_precedence as cache_precedence,
    executable_cache_limits_recommendation as cache_rec,
    executable_cache_limits_window_plan as cache_window,
};

type CachePolicyRequest =
    cache_rec::NativeExecutableCacheLimitsTwoSignalRequest;
type CachePrecedence = cache_precedence::NativeExecutableCacheLimitsPrecedence;
type RecommendedActivationFailure<StoreError> =
    ac::NativeExecutableCacheLimitsRecommendedActivationFailure<StoreError>;
type RecommendedActivationRequest =
    ac::NativeExecutableCacheLimitsRecommendedActivationRequest;
type RecommendedCacheActivation<DurabilityError, AdapterError> =
    ac::NativeExecutableCacheLimitsRecommendedCacheActivation<
        DurabilityError,
        AdapterError,
    >;
type RecommendedLeaseActivation<DurabilityError, AdapterError> =
    ac::NativeExecutableCacheLimitsRecommendedLeaseActivation<
        DurabilityError,
        AdapterError,
    >;
type TelemetryPublication<ClockError> =
    cached::NativeContinuationCachedRetryCycleTelemetryPublication<ClockError>;
type WindowPlan = cache_window::NativeExecutableCacheLimitsWindowPlan;

type ObservedActivationResult<
    'publication,
    Activation,
    ClockError,
    StoreError,
> = Result<
    NativeExecutableCacheLimitsObservedActivation<
        'publication,
        Activation,
        ClockError,
    >,
    Box<NativeExecutableCacheLimitsObservedActivationFailure<StoreError>>,
>;

/// Caller-owned policy and durable inputs for one post-observation trigger.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeExecutableCacheLimitsObservedActivationRequest {
    expected: Option<NativeExecutableSequenceCacheLimits>,
    maximum_bytes: NonZeroUsize,
    policy: CachePolicyRequest,
    precedence: CachePrecedence,
}

/// Mutable resources for one ordinary-cache observed activation attempt.
#[derive(Debug)]
pub struct NativeExecutableCacheLimitsObservedCacheContext<
    'resource,
    Store,
    Adapter,
> {
    adapter: &'resource mut Adapter,
    cache: &'resource mut NativeExecutableSequenceCache,
    store: &'resource mut Store,
}

/// Mutable resources for one lease-cache observed activation attempt.
#[derive(Debug)]
pub struct NativeExecutableCacheLimitsObservedLeaseContext<
    'resource,
    Store,
    Adapter,
> {
    adapter: &'resource mut Adapter,
    cache: &'resource mut NativeExecutableSequenceLeaseCache,
    store: &'resource mut Store,
}

/// Result of one explicit post-observation cache-policy trigger.
#[derive(Debug)]
pub enum NativeExecutableCacheLimitsObservedActivation<
    'publication,
    Activation,
    ClockError,
> {
    /// Published telemetry reached existing durable/live activation.
    Activated {
        /// Exact downstream recommendation activation evidence.
        activation: Activation,
        /// Exact window plan authorizing activation.
        plan: WindowPlan,
    },
    /// Published telemetry produced no recommendation authority; no CAS ran.
    Planned {
        /// Exact window-scoped policy plan.
        plan: WindowPlan,
    },
    /// Telemetry was not atomically published; no planning or activation ran.
    TelemetryUnpublished {
        /// Exact observed-cycle publication evidence retained by reference.
        publication: &'publication TelemetryPublication<ClockError>,
    },
}

/// Prepublication activation failure paired with the exact originating plan.
#[derive(Debug)]
pub struct NativeExecutableCacheLimitsObservedActivationFailure<StoreError> {
    activation: Box<RecommendedActivationFailure<StoreError>>,
    plan: WindowPlan,
}

/// Ordinary-cache observed activation specialized to store/adapter errors.
pub type NativeExecutableCacheLimitsObservedCacheActivation<
    'publication,
    Store,
    Adapter,
    ClockError,
> = NativeExecutableCacheLimitsObservedActivation<
    'publication,
    RecommendedCacheActivation<
        <Store as DurableBlobStore>::DurabilityError,
        <Adapter as NativeExecutableMemoryAdapter>::Error,
    >,
    ClockError,
>;

/// Lease-cache observed activation specialized to store/adapter errors.
pub type NativeExecutableCacheLimitsObservedLeaseActivation<
    'publication,
    Store,
    Adapter,
    ClockError,
> = NativeExecutableCacheLimitsObservedActivation<
    'publication,
    RecommendedLeaseActivation<
        <Store as DurableBlobStore>::DurabilityError,
        <Adapter as NativeExecutableMemoryAdapter>::Error,
    >,
    ClockError,
>;

/// Ordinary-cache observed orchestration result specialized to store/adapter.
pub type NativeExecutableCacheLimitsObservedCacheStoreResult<
    'publication,
    Store,
    Adapter,
    ClockError,
> = Result<
    NativeExecutableCacheLimitsObservedCacheActivation<
        'publication,
        Store,
        Adapter,
        ClockError,
    >,
    Box<
        NativeExecutableCacheLimitsObservedActivationFailure<
            <Store as BlobStore>::Error,
        >,
    >,
>;

/// Lease-cache observed orchestration result specialized to store/adapter.
pub type NativeExecutableCacheLimitsObservedLeaseStoreResult<
    'publication,
    Store,
    Adapter,
    ClockError,
> = Result<
    NativeExecutableCacheLimitsObservedLeaseActivation<
        'publication,
        Store,
        Adapter,
        ClockError,
    >,
    Box<
        NativeExecutableCacheLimitsObservedActivationFailure<
            <Store as BlobStore>::Error,
        >,
    >,
>;

impl NativeExecutableCacheLimitsObservedActivationRequest {
    /// Binds policy, precedence, durable expectation, and bounded byte budget.
    #[must_use]
    pub const fn new(
        policy: &CachePolicyRequest,
        precedence: CachePrecedence,
        expected: Option<NativeExecutableSequenceCacheLimits>,
        maximum_bytes: NonZeroUsize,
    ) -> Self {
        Self {
            expected,
            maximum_bytes,
            policy: *policy,
            precedence,
        }
    }
}

impl<'resource, Store, Adapter>
    NativeExecutableCacheLimitsObservedCacheContext<'resource, Store, Adapter>
{
    /// Binds one mutable durable store, ordinary cache, and memory adapter.
    #[must_use]
    pub const fn new(
        store: &'resource mut Store,
        cache: &'resource mut NativeExecutableSequenceCache,
        adapter: &'resource mut Adapter,
    ) -> Self {
        Self { adapter, cache, store }
    }
}

impl<'resource, Store, Adapter>
    NativeExecutableCacheLimitsObservedLeaseContext<'resource, Store, Adapter>
{
    /// Binds one mutable durable store, lease cache, and memory adapter.
    #[must_use]
    pub const fn new(
        store: &'resource mut Store,
        cache: &'resource mut NativeExecutableSequenceLeaseCache,
        adapter: &'resource mut Adapter,
    ) -> Self {
        Self { adapter, cache, store }
    }
}

impl<StoreError>
    NativeExecutableCacheLimitsObservedActivationFailure<StoreError>
{
    /// Returns exact downstream prepublication activation failure evidence.
    #[must_use]
    pub const fn activation(
        &self,
    ) -> &RecommendedActivationFailure<StoreError> {
        &self.activation
    }

    /// Returns the exact plan whose activation failed before publication.
    #[must_use]
    pub const fn plan(&self) -> WindowPlan {
        self.plan
    }
}

fn trigger_observed_activation<
    'publication,
    Activation,
    ClockError,
    StoreError,
    Apply,
>(
    publication: &'publication TelemetryPublication<ClockError>,
    live: NativeExecutableSequenceCacheLimits,
    request: &NativeExecutableCacheLimitsObservedActivationRequest,
    apply: Apply,
) -> ObservedActivationResult<'publication, Activation, ClockError, StoreError>
where
    Apply: FnOnce(
        &RecommendedActivationRequest,
    ) -> Result<
        Activation,
        Box<RecommendedActivationFailure<StoreError>>,
    >,
{
    let TelemetryPublication::Published { window, .. } = publication else {
        return Ok(NativeExecutableCacheLimitsObservedActivation::
            TelemetryUnpublished { publication });
    };
    let plan =
        cache_window::plan_native_executable_cache_limits_after_window_append(
            window,
            live,
            &request.policy,
            request.precedence,
        );
    let Some(recommendation) = plan.recommendation() else {
        return Ok(NativeExecutableCacheLimitsObservedActivation::Planned {
            plan,
        });
    };
    let activation_request = RecommendedActivationRequest::new(
        request.expected,
        recommendation,
        request.maximum_bytes,
    );
    let activation = apply(&activation_request).map_err(|activation| {
        Box::new(NativeExecutableCacheLimitsObservedActivationFailure {
            activation,
            plan,
        })
    })?;
    Ok(NativeExecutableCacheLimitsObservedActivation::Activated {
        activation,
        plan,
    })
}

/// Triggers ordinary-cache policy only after successful observed telemetry.
///
/// # Errors
///
/// Returns prepublication activation failure while retaining the exact
/// window-scoped plan that authorized the attempt.
pub fn activate_observed_executable_sequence_cache_limits_durably<
    'publication,
    Store,
    Adapter,
    ClockError,
>(
    publication: &'publication TelemetryPublication<ClockError>,
    context: &mut NativeExecutableCacheLimitsObservedCacheContext<
        '_,
        Store,
        Adapter,
    >,
    request: &NativeExecutableCacheLimitsObservedActivationRequest,
) -> NativeExecutableCacheLimitsObservedCacheStoreResult<
    'publication,
    Store,
    Adapter,
    ClockError,
>
where
    Store: ConditionalBlobStore + DurableBlobStore,
    Adapter: NativeExecutableMemoryAdapter,
{
    let live = context.cache.limits();
    trigger_observed_activation(publication, live, request, |activation| {
        ac::activate_recommended_executable_sequence_cache_limits_durably(
            context.store,
            context.cache,
            context.adapter,
            activation,
        )
    })
}

/// Triggers lease-cache policy only after successful observed telemetry.
///
/// # Errors
///
/// Returns prepublication activation failure while retaining the exact
/// window-scoped plan that authorized the attempt.
pub fn activate_observed_executable_sequence_lease_cache_limits_durably<
    'publication,
    Store,
    Adapter,
    ClockError,
>(
    publication: &'publication TelemetryPublication<ClockError>,
    context: &mut NativeExecutableCacheLimitsObservedLeaseContext<
        '_,
        Store,
        Adapter,
    >,
    request: &NativeExecutableCacheLimitsObservedActivationRequest,
) -> NativeExecutableCacheLimitsObservedLeaseStoreResult<
    'publication,
    Store,
    Adapter,
    ClockError,
>
where
    Store: ConditionalBlobStore + DurableBlobStore,
    Adapter: NativeExecutableMemoryAdapter,
{
    let live = context.cache.limits();
    trigger_observed_activation(publication, live, request, |activation| {
        ac::activate_recommended_executable_sequence_lease_cache_limits_durably(
            context.store,
            context.cache,
            context.adapter,
            activation,
        )
    })
}

#[cfg(test)]
#[path = "../../../../../tests/tiered/cache_limits_observed_activation.rs"]
mod tests;
