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
//     orchestration, including optional cumulative-latency agreement.
// - Must-Not:
//   - Execute cached cycles, mutate telemetry owners, infer policy
//     configuration, retry durable conflicts, or hide telemetry-publication
//     failures.
// - Allows:
//   - Inputs: immutable observed-cycle telemetry publication, caller-owned
//     window policy, optional latency policy, durable expectation, bounded
//     store, live cache, and memory adapter.
//   - Outputs: unpublished, planned-without-authority, activated, or exact
//     prepublication failure retaining its window or window-latency plan.
//   - Side effects: at most the existing durable/live activation transaction,
//     and only after telemetry publication produced recommendation authority.
// - Split-When:
//   - Product scheduling, retries, or asynchronous triggering gains authority.
// - Merge-When:
//   - One product owner subsumes observed execution through cache activation.
// - Summary:
//   - Triggers explicit cache policy only from successfully published
//     telemetry, with latency agreement when explicitly requested.
// - Description:
//   - Observation completes first; this separate use case may then plan and
//     act.
// - Usage:
//   - Invoke the window-only or latency-aware path after observed publication.
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
    executable_cache_limits_latency as cache_latency,
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

type LatencyRequest = cache_latency::NativeExecutableCacheLimitsLatencyRequest;
type WindowLatencyPlan =
    cache_latency::NativeExecutableCacheLimitsWindowLatencyPlan;

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

type ObservedLatencyActivationResult<
    'publication,
    Activation,
    ClockError,
    StoreError,
> = Result<
    NativeExecutableCacheLimitsObservedLatencyActivation<
        'publication,
        Activation,
        ClockError,
    >,
    Box<
        NativeExecutableCacheLimitsObservedLatencyActivationFailure<StoreError>,
    >,
>;

/// Caller-owned policy and durable inputs for one post-observation trigger.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeExecutableCacheLimitsObservedActivationRequest {
    expected: Option<NativeExecutableSequenceCacheLimits>,
    maximum_bytes: NonZeroUsize,
    policy: CachePolicyRequest,
    precedence: CachePrecedence,
}

/// Caller-owned latency-aware policy inputs for one post-observation trigger.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeExecutableCacheLimitsObservedLatencyActivationRequest {
    activation: NativeExecutableCacheLimitsObservedActivationRequest,
    latency: LatencyRequest,
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

/// Result of one latency-aware post-observation cache-policy trigger.
#[derive(Debug)]
pub enum NativeExecutableCacheLimitsObservedLatencyActivation<
    'publication,
    Activation,
    ClockError,
> {
    /// Window and latency agreed and reached durable/live activation.
    Activated {
        /// Exact downstream recommendation activation evidence.
        activation: Activation,
        /// Exact window-plus-latency plan authorizing activation.
        plan: WindowLatencyPlan,
    },
    /// Published telemetry lacked combined recommendation authority.
    Planned {
        /// Exact window-plus-latency plan withholding authority.
        plan: WindowLatencyPlan,
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

/// Latency-aware prepublication failure retaining combined policy evidence.
#[derive(Debug)]
pub struct NativeExecutableCacheLimitsObservedLatencyActivationFailure<
    StoreError,
> {
    activation: Box<RecommendedActivationFailure<StoreError>>,
    plan: WindowLatencyPlan,
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

/// Latency-aware ordinary-cache activation specialized to resource errors.
pub type NativeExecutableCacheLimitsObservedLatencyCacheActivation<
    'publication,
    Store,
    Adapter,
    ClockError,
> = NativeExecutableCacheLimitsObservedLatencyActivation<
    'publication,
    RecommendedCacheActivation<
        <Store as DurableBlobStore>::DurabilityError,
        <Adapter as NativeExecutableMemoryAdapter>::Error,
    >,
    ClockError,
>;

/// Latency-aware lease-cache activation specialized to resource errors.
pub type NativeExecutableCacheLimitsObservedLatencyLeaseActivation<
    'publication,
    Store,
    Adapter,
    ClockError,
> = NativeExecutableCacheLimitsObservedLatencyActivation<
    'publication,
    RecommendedLeaseActivation<
        <Store as DurableBlobStore>::DurabilityError,
        <Adapter as NativeExecutableMemoryAdapter>::Error,
    >,
    ClockError,
>;

/// Latency-aware ordinary-cache orchestration result.
pub type NativeExecutableCacheLimitsObservedLatencyCacheStoreResult<
    'publication,
    Store,
    Adapter,
    ClockError,
> = Result<
    NativeExecutableCacheLimitsObservedLatencyCacheActivation<
        'publication,
        Store,
        Adapter,
        ClockError,
    >,
    Box<
        NativeExecutableCacheLimitsObservedLatencyActivationFailure<
            <Store as BlobStore>::Error,
        >,
    >,
>;

/// Latency-aware lease-cache orchestration result.
pub type NativeExecutableCacheLimitsObservedLatencyLeaseStoreResult<
    'publication,
    Store,
    Adapter,
    ClockError,
> = Result<
    NativeExecutableCacheLimitsObservedLatencyLeaseActivation<
        'publication,
        Store,
        Adapter,
        ClockError,
    >,
    Box<
        NativeExecutableCacheLimitsObservedLatencyActivationFailure<
            <Store as BlobStore>::Error,
        >,
    >,
>;

impl NativeExecutableCacheLimitsObservedLatencyActivationRequest {
    /// Binds existing observed activation policy to one latency signal.
    #[must_use]
    pub const fn new(
        activation: &NativeExecutableCacheLimitsObservedActivationRequest,
        latency: LatencyRequest,
    ) -> Self {
        Self {
            activation: *activation,
            latency,
        }
    }
}

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

impl<StoreError>
    NativeExecutableCacheLimitsObservedLatencyActivationFailure<StoreError>
{
    /// Returns exact downstream prepublication activation failure evidence.
    #[must_use]
    pub const fn activation(
        &self,
    ) -> &RecommendedActivationFailure<StoreError> {
        &self.activation
    }

    /// Returns the exact combined plan whose activation failed.
    #[must_use]
    pub const fn plan(&self) -> WindowLatencyPlan {
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

fn trigger_observed_latency_activation<
    'publication,
    Activation,
    ClockError,
    StoreError,
    Apply,
>(
    publication: &'publication TelemetryPublication<ClockError>,
    live: NativeExecutableSequenceCacheLimits,
    request: &NativeExecutableCacheLimitsObservedLatencyActivationRequest,
    apply: Apply,
) -> ObservedLatencyActivationResult<
    'publication,
    Activation,
    ClockError,
    StoreError,
>
where
    Apply: FnOnce(
        &RecommendedActivationRequest,
    ) -> Result<
        Activation,
        Box<RecommendedActivationFailure<StoreError>>,
    >,
{
    let TelemetryPublication::Published { latency, window, .. } = publication
    else {
        return Ok(NativeExecutableCacheLimitsObservedLatencyActivation::
            TelemetryUnpublished { publication });
    };
    let window_plan =
        cache_window::plan_native_executable_cache_limits_after_window_append(
            window,
            live,
            &request.activation.policy,
            request.activation.precedence,
        );
    let plan = cache_latency::plan_native_executable_cache_limits_with_latency(
        &window_plan,
        *latency,
        request.latency,
    );
    let Some(recommendation) = plan.recommendation() else {
        return Ok(
            NativeExecutableCacheLimitsObservedLatencyActivation::Planned {
                plan,
            },
        );
    };
    let activation_request = RecommendedActivationRequest::new(
        request.activation.expected,
        recommendation,
        request.activation.maximum_bytes,
    );
    let activation = apply(&activation_request).map_err(|activation| {
        Box::new(
            NativeExecutableCacheLimitsObservedLatencyActivationFailure {
                activation,
                plan,
            },
        )
    })?;
    Ok(
        NativeExecutableCacheLimitsObservedLatencyActivation::Activated {
            activation,
            plan,
        },
    )
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

/// Triggers latency-aware ordinary-cache policy from published telemetry.
///
/// # Errors
///
/// Returns prepublication activation failure while retaining the exact
/// window-plus-latency plan that authorized the attempt.
pub fn activate_observed_cache_limits_with_latency_durably<
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
    request: &NativeExecutableCacheLimitsObservedLatencyActivationRequest,
) -> NativeExecutableCacheLimitsObservedLatencyCacheStoreResult<
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
    let activate =
        ac::activate_recommended_executable_sequence_cache_limits_durably;
    trigger_observed_latency_activation(
        publication,
        live,
        request,
        |activation| {
            activate(context.store, context.cache, context.adapter, activation)
        },
    )
}

/// Triggers latency-aware lease-cache policy from published telemetry.
///
/// # Errors
///
/// Returns prepublication activation failure while retaining the exact
/// window-plus-latency plan that authorized the attempt.
pub fn activate_observed_lease_cache_limits_with_latency_durably<
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
    request: &NativeExecutableCacheLimitsObservedLatencyActivationRequest,
) -> NativeExecutableCacheLimitsObservedLatencyLeaseStoreResult<
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
    let activate =
        ac::activate_recommended_executable_sequence_lease_cache_limits_durably;
    trigger_observed_latency_activation(
        publication,
        live,
        request,
        |activation| {
            activate(context.store, context.cache, context.adapter, activation)
        },
    )
}

#[cfg(test)]
#[path = "../../../../../tests/tiered/cache_limits_observed_activation.rs"]
mod tests;
