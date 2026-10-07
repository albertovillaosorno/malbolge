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
//   - Durable cadence-claim gating of explicit observed cache-limit activation.
// - Must-Not:
//   - Retry claim conflicts, spawn work, choose storage paths, or redefine
//     cache-limit recommendation/activation semantics.
// - Allows:
//   - Inputs: observed publication, expected cadence cursor, separate cursor
//     and policy resources, and existing observed activation request.
//   - Outputs: unpublished, withheld claim, claimed observed activation, or
//     exact claim/activation failure evidence.
//   - Side effects: one exact due-slot claim followed by existing activation
//     side effects only after that claim committed.
// - Split-When:
//   - Conflict retry, latency-aware claim gating, or unattended lifecycle gains
//     independent authority.
// - Merge-When:
//   - One product trigger owner subsumes claim, activation, and lifecycle.
// - Summary:
//   - Couples committed due-slot ownership to existing observed activation.
// - Description:
//   - Non-publication and uncommitted claims perform zero policy activation.
// - Usage:
//   - Use separate configured blob resources for trigger cursor and cache
//     policy.
// - Defaults:
//   - Activation failure does not roll back an already committed cadence claim.
//

//! Durable cadence-claim gating for explicit observed cache-limit activation.

use std::num::NonZeroUsize;

use crate::blob_store::{
    NativeContinuationBlobStore as BlobStore,
    NativeContinuationConditionalBlobStore as ConditionalBlobStore,
    NativeContinuationDurableBlobStore as DurableBlobStore,
};
use crate::execution_native::{
    NativeExecutableMemoryAdapter, NativeExecutableSequenceCache,
    NativeExecutableSequenceLeaseCache,
};
use crate::{
    cached_cycle as cached, executable_cache_limits_observed_activation as obs,
    executable_cache_limits_trigger_cadence as trigger,
    executable_cache_limits_trigger_cadence_cas as cursor_cas,
    executable_cache_limits_trigger_cadence_claim as cursor_claim,
};

type Cursor = trigger::NativeExecutableCacheLimitsTriggerCadence;
type Claim<DurabilityError> =
    cursor_claim::NativeExecutableCacheLimitsTriggerCadenceClaim<
        DurabilityError,
    >;
type ClaimError<StoreError> =
    cursor_cas::NativeExecutableCacheLimitsTriggerCadenceCasError<StoreError>;
type TelemetryPublication<ClockError> =
    cached::NativeContinuationCachedRetryCycleTelemetryPublication<ClockError>;

type ClaimedActivation<
    'publication,
    ClaimDurabilityError,
    Activation,
    ClockError,
> = NativeExecutableCacheLimitsClaimedObservedActivation<
    'publication,
    ClaimDurabilityError,
    Activation,
    ClockError,
>;

/// Caller-owned cursor inputs for one cadence-gated activation attempt.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeExecutableCacheLimitsClaimedObservedRequest {
    expected_cursor: Cursor,
    maximum_bytes: NonZeroUsize,
}

/// Separate cursor/policy resources for one ordinary-cache claimed activation.
#[derive(Debug)]
pub struct NativeExecutableCacheLimitsClaimedObservedCacheContext<
    'resource,
    CursorStore,
    PolicyStore,
    Adapter,
> {
    cursor_store: &'resource mut CursorStore,
    observed: obs::NativeExecutableCacheLimitsObservedCacheContext<
        'resource,
        PolicyStore,
        Adapter,
    >,
}

/// Separate cursor/policy resources for one lease-cache claimed activation.
#[derive(Debug)]
pub struct NativeExecutableCacheLimitsClaimedObservedLeaseContext<
    'resource,
    CursorStore,
    PolicyStore,
    Adapter,
> {
    cursor_store: &'resource mut CursorStore,
    observed: obs::NativeExecutableCacheLimitsObservedLeaseContext<
        'resource,
        PolicyStore,
        Adapter,
    >,
}

/// Result of one cadence-gated observed activation attempt.
#[derive(Debug)]
pub enum NativeExecutableCacheLimitsClaimedObservedActivation<
    'publication,
    ClaimDurabilityError,
    Activation,
    ClockError,
> {
    /// Cadence claim did not commit; no observed activation ran.
    ClaimWithheld {
        /// Exact withheld/noncommitted claim evidence.
        claim: Claim<ClaimDurabilityError>,
    },
    /// Due-slot claim committed, then existing observed activation completed.
    Claimed {
        /// Exact committed durable claim evidence.
        claim: Claim<ClaimDurabilityError>,
        /// Exact existing observed activation outcome.
        observed: Activation,
    },
    /// Telemetry was not atomically published; no cursor claim or policy ran.
    TelemetryUnpublished {
        /// Exact observed publication evidence retained by reference.
        publication: &'publication TelemetryPublication<ClockError>,
    },
}

/// Why cadence-gated observed activation failed before a normal outcome.
#[derive(Debug)]
pub enum NativeExecutableCacheLimitsClaimedObservedActivationError<
    ClaimStoreError,
    ClaimDurabilityError,
    ActivationError,
> {
    /// Due-slot claim failed before typed claim evidence existed.
    Claim(ClaimError<ClaimStoreError>),
    /// Claim committed, then existing observed activation failed.
    Observed {
        /// Exact committed claim that remains authoritative.
        claim: Claim<ClaimDurabilityError>,
        /// Exact existing observed activation failure.
        error: ActivationError,
    },
}

impl NativeExecutableCacheLimitsClaimedObservedRequest {
    /// Binds the last observed cursor to its bounded canonical byte budget.
    #[must_use]
    pub const fn new(
        expected_cursor: Cursor,
        maximum_bytes: NonZeroUsize,
    ) -> Self {
        Self {
            expected_cursor,
            maximum_bytes,
        }
    }
}

impl<'resource, CursorStore, PolicyStore, Adapter>
    NativeExecutableCacheLimitsClaimedObservedCacheContext<
        'resource,
        CursorStore,
        PolicyStore,
        Adapter,
    >
{
    /// Binds separate cursor store and ordinary-cache activation resources.
    #[must_use]
    pub const fn new(
        cursor_store: &'resource mut CursorStore,
        policy_store: &'resource mut PolicyStore,
        cache: &'resource mut NativeExecutableSequenceCache,
        adapter: &'resource mut Adapter,
    ) -> Self {
        Self {
            cursor_store,
            observed: obs::NativeExecutableCacheLimitsObservedCacheContext::new(
                policy_store,
                cache,
                adapter,
            ),
        }
    }
}

impl<'resource, CursorStore, PolicyStore, Adapter>
    NativeExecutableCacheLimitsClaimedObservedLeaseContext<
        'resource,
        CursorStore,
        PolicyStore,
        Adapter,
    >
{
    /// Binds separate cursor store and lease-cache activation resources.
    #[must_use]
    pub const fn new(
        cursor_store: &'resource mut CursorStore,
        policy_store: &'resource mut PolicyStore,
        cache: &'resource mut NativeExecutableSequenceLeaseCache,
        adapter: &'resource mut Adapter,
    ) -> Self {
        Self {
            cursor_store,
            observed: obs::NativeExecutableCacheLimitsObservedLeaseContext::new(
                policy_store,
                cache,
                adapter,
            ),
        }
    }
}

type CacheObserved<'publication, Store, Adapter, ClockError> =
    obs::NativeExecutableCacheLimitsObservedCacheActivation<
        'publication,
        Store,
        Adapter,
        ClockError,
    >;
type LeaseObserved<'publication, Store, Adapter, ClockError> =
    obs::NativeExecutableCacheLimitsObservedLeaseActivation<
        'publication,
        Store,
        Adapter,
        ClockError,
    >;
type ObservedFailure<Store> = Box<
    obs::NativeExecutableCacheLimitsObservedActivationFailure<
        <Store as BlobStore>::Error,
    >,
>;

type ClaimedResult<
    'publication,
    CursorStore,
    Activation,
    ClockError,
    ActivationError,
> = Result<
    NativeExecutableCacheLimitsClaimedObservedActivation<
        'publication,
        <CursorStore as DurableBlobStore>::DurabilityError,
        Activation,
        ClockError,
    >,
    Box<
        NativeExecutableCacheLimitsClaimedObservedActivationError<
            <CursorStore as BlobStore>::Error,
            <CursorStore as DurableBlobStore>::DurabilityError,
            ActivationError,
        >,
    >,
>;

/// Ordinary-cache cadence-gated observed activation result.
pub type NativeExecutableCacheLimitsClaimedObservedCacheResult<
    'publication,
    CursorStore,
    PolicyStore,
    Adapter,
    ClockError,
> = ClaimedResult<
    'publication,
    CursorStore,
    CacheObserved<'publication, PolicyStore, Adapter, ClockError>,
    ClockError,
    ObservedFailure<PolicyStore>,
>;

/// Lease-cache cadence-gated observed activation result.
pub type NativeExecutableCacheLimitsClaimedObservedLeaseResult<
    'publication,
    CursorStore,
    PolicyStore,
    Adapter,
    ClockError,
> = ClaimedResult<
    'publication,
    CursorStore,
    LeaseObserved<'publication, PolicyStore, Adapter, ClockError>,
    ClockError,
    ObservedFailure<PolicyStore>,
>;

fn activate_after_claim<
    'publication,
    CursorStore,
    Activation,
    ActivationError,
    ClockError,
    Apply,
>(
    publication: &'publication TelemetryPublication<ClockError>,
    cursor_store: &mut CursorStore,
    claim_request: NativeExecutableCacheLimitsClaimedObservedRequest,
    apply: Apply,
) -> ClaimedResult<
    'publication,
    CursorStore,
    Activation,
    ClockError,
    ActivationError,
>
where
    CursorStore: ConditionalBlobStore + DurableBlobStore,
    Apply: FnOnce() -> Result<Activation, ActivationError>,
{
    let TelemetryPublication::Published { window, .. } = publication else {
        return Ok(
            NativeExecutableCacheLimitsClaimedObservedActivation::
                TelemetryUnpublished { publication },
        );
    };
    let claim = cursor_claim::claim_cache_trigger_cadence_slot_durably(
        cursor_store,
        claim_request.expected_cursor,
        window,
        claim_request.maximum_bytes,
    )
    .map_err(|error| {
        Box::new(
            NativeExecutableCacheLimitsClaimedObservedActivationError::Claim(
                error,
            ),
        )
    })?;
    if !claim.is_committed() {
        return Ok(ClaimedActivation::ClaimWithheld { claim });
    }
    let observed = match apply() {
        Ok(observed) => observed,
        Err(error) => {
            return Err(Box::new(
                NativeExecutableCacheLimitsClaimedObservedActivationError::
                    Observed { claim, error },
            ));
        },
    };
    Ok(ClaimedActivation::Claimed { claim, observed })
}

/// Claims one due slot before ordinary-cache observed activation.
///
/// # Errors
///
/// Returns cursor-claim failure before activation, or existing observed
/// activation failure paired with the already committed claim.
pub fn activate_claimed_observed_cache_limits_durably<
    'publication,
    CursorStore,
    PolicyStore,
    Adapter,
    ClockError,
>(
    publication: &'publication TelemetryPublication<ClockError>,
    context: &mut NativeExecutableCacheLimitsClaimedObservedCacheContext<
        '_,
        CursorStore,
        PolicyStore,
        Adapter,
    >,
    claim_request: NativeExecutableCacheLimitsClaimedObservedRequest,
    request: &obs::NativeExecutableCacheLimitsObservedActivationRequest,
) -> NativeExecutableCacheLimitsClaimedObservedCacheResult<
    'publication,
    CursorStore,
    PolicyStore,
    Adapter,
    ClockError,
>
where
    CursorStore: ConditionalBlobStore + DurableBlobStore,
    PolicyStore: ConditionalBlobStore + DurableBlobStore,
    Adapter: NativeExecutableMemoryAdapter,
{
    let activate =
        obs::activate_observed_executable_sequence_cache_limits_durably;
    activate_after_claim(
        publication,
        context.cursor_store,
        claim_request,
        || activate(publication, &mut context.observed, request),
    )
}

/// Claims one due slot before lease-cache observed activation.
///
/// # Errors
///
/// Returns cursor-claim failure before activation, or existing observed
/// activation failure paired with the already committed claim.
pub fn activate_claimed_observed_lease_cache_limits_durably<
    'publication,
    CursorStore,
    PolicyStore,
    Adapter,
    ClockError,
>(
    publication: &'publication TelemetryPublication<ClockError>,
    context: &mut NativeExecutableCacheLimitsClaimedObservedLeaseContext<
        '_,
        CursorStore,
        PolicyStore,
        Adapter,
    >,
    claim_request: NativeExecutableCacheLimitsClaimedObservedRequest,
    request: &obs::NativeExecutableCacheLimitsObservedActivationRequest,
) -> NativeExecutableCacheLimitsClaimedObservedLeaseResult<
    'publication,
    CursorStore,
    PolicyStore,
    Adapter,
    ClockError,
>
where
    CursorStore: ConditionalBlobStore + DurableBlobStore,
    PolicyStore: ConditionalBlobStore + DurableBlobStore,
    Adapter: NativeExecutableMemoryAdapter,
{
    let activate =
        obs::activate_observed_executable_sequence_lease_cache_limits_durably;
    activate_after_claim(
        publication,
        context.cursor_store,
        claim_request,
        || activate(publication, &mut context.observed, request),
    )
}

#[cfg(test)]
#[path = "../../../../../tests/tiered/cache_trigger_observed.rs"]
mod tests;
