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
//   - Durable cadence-claim gating of explicit observed cache-limit activation,
//     including caller-bounded retry and product conflict-policy application.
// - Must-Not:
//   - Retry committed claims or activation failures, sleep/back off, spawn
//     work, choose storage paths, or redefine cache-limit policy semantics.
// - Allows:
//   - Inputs: observed publication, expected cadence cursor, positive optional
//     retry budget/direction, typed stop decision or product conflict policy,
//     separate cursor/policy resources, and activation request.
//   - Outputs: unpublished, withheld claim/retry with optional typed caller
//     stop evidence, claimed activation, or exact claim/retry/activation
//     failure evidence.
//   - Side effects: bounded due-slot claims followed by existing activation
//     side effects only after terminal retry evidence committed.
// - Split-When:
//   - Unattended lifecycle or asynchronous scheduling gains authority.
// - Merge-When:
//   - One product trigger owner subsumes claim, activation, and lifecycle.
// - Summary:
//   - Couples committed due-slot ownership/retry to existing observed
//     activation.
// - Description:
//   - Non-publication and uncommitted terminal evidence performs zero
//     activation.
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
use crate::retry_control::{
    NativeContinuationRetryConflict, NativeContinuationRetryDecision,
    NativeContinuationRetryDirective, NativeContinuationRetryStopState,
};
use crate::{
    cached_cycle as cached, executable_cache_limits_observed_activation as obs,
    executable_cache_limits_retry_policy as retry_policy,
    executable_cache_limits_retry_reason as retry_reason,
    executable_cache_limits_trigger_cadence as trigger,
    executable_cache_limits_trigger_cadence_cas as cursor_cas,
    executable_cache_limits_trigger_cadence_claim as cursor_claim,
    executable_cache_limits_trigger_cadence_claim_retry as cursor_retry,
};

type Cursor = trigger::NativeExecutableCacheLimitsTriggerCadence;
type Claim<DurabilityError> =
    cursor_claim::NativeExecutableCacheLimitsTriggerCadenceClaim<
        DurabilityError,
    >;
type ClaimError<StoreError> =
    cursor_cas::NativeExecutableCacheLimitsTriggerCadenceCasError<StoreError>;
type ClaimRetry<DurabilityError> =
    cursor_retry::NativeExecutableCacheLimitsTriggerCadenceClaimRetry<
        DurabilityError,
    >;
type ClaimRetryRequest<'append> =
    cursor_retry::NativeExecutableCacheLimitsTriggerCadenceClaimRetryRequest<
        'append,
    >;
type TelemetryPublication<ClockError> =
    cached::NativeContinuationCachedRetryCycleTelemetryPublication<ClockError>;
type RetryConflictPolicy =
    retry_policy::NativeExecutableCacheLimitsRetryConflictPolicy;
type RetryStopReason = retry_reason::NativeExecutableCacheLimitsRetryStopReason;

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

/// Caller-owned inputs for one bounded retry claim before activation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeExecutableCacheLimitsRetriedObservedRequest {
    expected_cursor: Cursor,
    maximum_attempts: NonZeroUsize,
    maximum_bytes: NonZeroUsize,
}

/// Caller-owned retry bounds plus policy-neutral conflict direction.
#[derive(Debug)]
pub struct NativeExecutableCacheLimitsControlledRetriedObservedRequest<Control>
{
    control: Control,
    retry: NativeExecutableCacheLimitsRetriedObservedRequest,
}

/// Caller-owned retry bounds, typed decisions, and retained stop evidence.
#[derive(Debug)]
pub struct NativeExecutableCacheLimitsReasonedRetriedObservedRequest<
    'stop,
    Control,
    StopReason,
> {
    control: Control,
    retry: NativeExecutableCacheLimitsRetriedObservedRequest,
    stop_state: &'stop mut NativeContinuationRetryStopState<StopReason>,
}

/// Product conflict policy plus retry bounds and retained stop evidence.
#[derive(Debug)]
pub struct NativeExecutableCacheLimitsPolicyRetriedObservedRequest<'stop> {
    policy: RetryConflictPolicy,
    retry: NativeExecutableCacheLimitsRetriedObservedRequest,
    stop_state: &'stop mut NativeContinuationRetryStopState<RetryStopReason>,
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

/// Result of bounded claim retry followed by optional observed activation.
#[derive(Debug)]
pub enum NativeExecutableCacheLimitsRetriedObservedActivation<
    'publication,
    ClaimDurabilityError,
    Activation,
    ClockError,
> {
    /// Terminal retry evidence did not commit; no observed activation ran.
    ClaimWithheld {
        /// Exact terminal claim plus completed claim-attempt count.
        retry: ClaimRetry<ClaimDurabilityError>,
    },
    /// Terminal retry evidence committed, then observed activation completed.
    Claimed {
        /// Exact committed terminal claim plus completed attempt count.
        retry: ClaimRetry<ClaimDurabilityError>,
        /// Exact existing observed activation outcome.
        observed: Activation,
    },
    /// Telemetry was not published; neither claim retry nor activation ran.
    TelemetryUnpublished {
        /// Exact observed publication evidence retained by reference.
        publication: &'publication TelemetryPublication<ClockError>,
    },
}

/// Why retry-gated observed activation failed before a normal outcome.
#[derive(Debug)]
pub enum NativeExecutableCacheLimitsRetriedObservedActivationError<
    ClaimStoreError,
    ClaimDurabilityError,
    ActivationError,
> {
    /// Claim retry failed before terminal retry evidence existed.
    Claim(ClaimError<ClaimStoreError>),
    /// Retry committed, then existing observed activation failed.
    Observed {
        /// Exact committed terminal claim plus completed attempt count.
        retry: ClaimRetry<ClaimDurabilityError>,
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

impl NativeExecutableCacheLimitsRetriedObservedRequest {
    /// Binds cursor state to positive canonical byte and claim-attempt bounds.
    #[must_use]
    pub const fn new(
        expected_cursor: Cursor,
        maximum_bytes: NonZeroUsize,
        maximum_attempts: NonZeroUsize,
    ) -> Self {
        Self {
            expected_cursor,
            maximum_attempts,
            maximum_bytes,
        }
    }
}

impl<Control>
    NativeExecutableCacheLimitsControlledRetriedObservedRequest<Control>
{
    /// Binds one retry request to caller conflict direction.
    #[must_use]
    pub const fn new(
        retry: NativeExecutableCacheLimitsRetriedObservedRequest,
        control: Control,
    ) -> Self {
        Self { control, retry }
    }
}

impl<'stop, Control, StopReason>
    NativeExecutableCacheLimitsReasonedRetriedObservedRequest<
        'stop,
        Control,
        StopReason,
    >
{
    /// Binds retry inputs to caller decisions and typed retained stop state.
    #[must_use]
    pub const fn new(
        retry: NativeExecutableCacheLimitsRetriedObservedRequest,
        stop_state: &'stop mut NativeContinuationRetryStopState<StopReason>,
        control: Control,
    ) -> Self {
        Self {
            control,
            retry,
            stop_state,
        }
    }
}

impl<'stop> NativeExecutableCacheLimitsPolicyRetriedObservedRequest<'stop> {
    /// Binds retry inputs to one explicit product conflict policy.
    #[must_use]
    pub const fn new(
        retry: NativeExecutableCacheLimitsRetriedObservedRequest,
        stop_state: &'stop mut NativeContinuationRetryStopState<
            RetryStopReason,
        >,
        policy: RetryConflictPolicy,
    ) -> Self {
        Self {
            policy,
            retry,
            stop_state,
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
type LatencyCacheObserved<'publication, Store, Adapter, ClockError> =
    obs::NativeExecutableCacheLimitsObservedLatencyCacheActivation<
        'publication,
        Store,
        Adapter,
        ClockError,
    >;
type LatencyLeaseObserved<'publication, Store, Adapter, ClockError> =
    obs::NativeExecutableCacheLimitsObservedLatencyLeaseActivation<
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
type LatencyObservedFailure<Store> = Box<
    obs::NativeExecutableCacheLimitsObservedLatencyActivationFailure<
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

type RetriedResult<
    'publication,
    CursorStore,
    Activation,
    ClockError,
    ActivationError,
> = Result<
    NativeExecutableCacheLimitsRetriedObservedActivation<
        'publication,
        <CursorStore as DurableBlobStore>::DurabilityError,
        Activation,
        ClockError,
    >,
    Box<
        NativeExecutableCacheLimitsRetriedObservedActivationError<
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

/// Latency-aware ordinary-cache cadence-gated observed activation result.
pub type NativeExecutableCacheLimitsClaimedObservedLatencyCacheResult<
    'publication,
    CursorStore,
    PolicyStore,
    Adapter,
    ClockError,
> = ClaimedResult<
    'publication,
    CursorStore,
    LatencyCacheObserved<'publication, PolicyStore, Adapter, ClockError>,
    ClockError,
    LatencyObservedFailure<PolicyStore>,
>;

/// Latency-aware lease-cache cadence-gated observed activation result.
pub type NativeExecutableCacheLimitsClaimedObservedLatencyLeaseResult<
    'publication,
    CursorStore,
    PolicyStore,
    Adapter,
    ClockError,
> = ClaimedResult<
    'publication,
    CursorStore,
    LatencyLeaseObserved<'publication, PolicyStore, Adapter, ClockError>,
    ClockError,
    LatencyObservedFailure<PolicyStore>,
>;

/// Retry-gated ordinary-cache observed activation result.
pub type NativeExecutableCacheLimitsRetriedObservedCacheResult<
    'publication,
    CursorStore,
    PolicyStore,
    Adapter,
    ClockError,
> = RetriedResult<
    'publication,
    CursorStore,
    CacheObserved<'publication, PolicyStore, Adapter, ClockError>,
    ClockError,
    ObservedFailure<PolicyStore>,
>;

/// Retry-gated lease-cache observed activation result.
pub type NativeExecutableCacheLimitsRetriedObservedLeaseResult<
    'publication,
    CursorStore,
    PolicyStore,
    Adapter,
    ClockError,
> = RetriedResult<
    'publication,
    CursorStore,
    LeaseObserved<'publication, PolicyStore, Adapter, ClockError>,
    ClockError,
    ObservedFailure<PolicyStore>,
>;

/// Retry-gated latency-aware ordinary-cache activation result.
pub type NativeExecutableCacheLimitsRetriedObservedLatencyCacheResult<
    'publication,
    CursorStore,
    PolicyStore,
    Adapter,
    ClockError,
> = RetriedResult<
    'publication,
    CursorStore,
    LatencyCacheObserved<'publication, PolicyStore, Adapter, ClockError>,
    ClockError,
    LatencyObservedFailure<PolicyStore>,
>;

/// Retry-gated latency-aware lease-cache activation result.
pub type NativeExecutableCacheLimitsRetriedObservedLatencyLeaseResult<
    'publication,
    CursorStore,
    PolicyStore,
    Adapter,
    ClockError,
> = RetriedResult<
    'publication,
    CursorStore,
    LatencyLeaseObserved<'publication, PolicyStore, Adapter, ClockError>,
    ClockError,
    LatencyObservedFailure<PolicyStore>,
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

fn activate_after_controlled_claim_retries<
    'publication,
    CursorStore,
    Activation,
    ActivationError,
    ClockError,
    Control,
    Apply,
>(
    publication: &'publication TelemetryPublication<ClockError>,
    cursor_store: &mut CursorStore,
    controlled: NativeExecutableCacheLimitsControlledRetriedObservedRequest<
        Control,
    >,
    apply: Apply,
) -> RetriedResult<
    'publication,
    CursorStore,
    Activation,
    ClockError,
    ActivationError,
>
where
    CursorStore: ConditionalBlobStore + DurableBlobStore,
    Control: FnMut(
        NativeContinuationRetryConflict,
    ) -> NativeContinuationRetryDirective,
    Apply: FnOnce() -> Result<Activation, ActivationError>,
{
    let TelemetryPublication::Published { window, .. } = publication else {
        return Ok(
            NativeExecutableCacheLimitsRetriedObservedActivation::
                TelemetryUnpublished { publication },
        );
    };
    let retry_request = controlled.retry;
    let request = ClaimRetryRequest::new(
        retry_request.expected_cursor,
        window,
        retry_request.maximum_bytes,
        retry_request.maximum_attempts,
    );
    let retry =
        cursor_retry::claim_cache_trigger_cadence_slot_with_retry_control(
            cursor_store,
            request,
            controlled.control,
        )
        .map_err(|error| {
            Box::new(
                NativeExecutableCacheLimitsRetriedObservedActivationError::
                    Claim(error),
            )
        })?;
    if !retry.outcome().is_committed() {
        return Ok(
            NativeExecutableCacheLimitsRetriedObservedActivation::
                ClaimWithheld { retry },
        );
    }
    let observed = match apply() {
        Ok(observed) => observed,
        Err(error) => {
            return Err(Box::new(
                NativeExecutableCacheLimitsRetriedObservedActivationError::
                    Observed { retry, error },
            ));
        },
    };
    Ok(
        NativeExecutableCacheLimitsRetriedObservedActivation::Claimed {
            retry,
            observed,
        },
    )
}

fn activate_after_reasoned_claim_retries<
    'publication,
    CursorStore,
    StopReason,
    Activation,
    ActivationError,
    ClockError,
    Control,
    Apply,
>(
    publication: &'publication TelemetryPublication<ClockError>,
    cursor_store: &mut CursorStore,
    reasoned: NativeExecutableCacheLimitsReasonedRetriedObservedRequest<
        '_,
        Control,
        StopReason,
    >,
    apply: Apply,
) -> RetriedResult<
    'publication,
    CursorStore,
    Activation,
    ClockError,
    ActivationError,
>
where
    CursorStore: ConditionalBlobStore + DurableBlobStore,
    Control: FnMut(
        NativeContinuationRetryConflict,
    ) -> NativeContinuationRetryDecision<StopReason>,
    Apply: FnOnce() -> Result<Activation, ActivationError>,
{
    let NativeExecutableCacheLimitsReasonedRetriedObservedRequest {
        mut control,
        retry,
        stop_state,
    } = reasoned;
    *stop_state = NativeContinuationRetryStopState::new();
    let controlled =
        NativeExecutableCacheLimitsControlledRetriedObservedRequest::new(
            retry,
            move |conflict| stop_state.resolve(conflict, control(conflict)),
        );
    activate_after_controlled_claim_retries(
        publication,
        cursor_store,
        controlled,
        apply,
    )
}

fn activate_after_policy_claim_retries<
    'publication,
    CursorStore,
    Activation,
    ActivationError,
    ClockError,
    Apply,
>(
    publication: &'publication TelemetryPublication<ClockError>,
    cursor_store: &mut CursorStore,
    policy_request: NativeExecutableCacheLimitsPolicyRetriedObservedRequest<'_>,
    apply: Apply,
) -> RetriedResult<
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
    let NativeExecutableCacheLimitsPolicyRetriedObservedRequest {
        policy,
        retry,
        stop_state,
    } = policy_request;
    let reasoned =
        NativeExecutableCacheLimitsReasonedRetriedObservedRequest::new(
            retry,
            stop_state,
            move |conflict| policy.decide(conflict),
        );
    activate_after_reasoned_claim_retries(
        publication,
        cursor_store,
        reasoned,
        apply,
    )
}

fn activate_after_claim_retries<
    'publication,
    CursorStore,
    Activation,
    ActivationError,
    ClockError,
    Apply,
>(
    publication: &'publication TelemetryPublication<ClockError>,
    cursor_store: &mut CursorStore,
    retry_request: NativeExecutableCacheLimitsRetriedObservedRequest,
    apply: Apply,
) -> RetriedResult<
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
    activate_after_controlled_claim_retries(
        publication,
        cursor_store,
        NativeExecutableCacheLimitsControlledRetriedObservedRequest::new(
            retry_request,
            |_conflict| NativeContinuationRetryDirective::Continue,
        ),
        apply,
    )
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

/// Claims one due slot before latency-aware ordinary-cache activation.
///
/// # Errors
///
/// Returns cursor-claim failure before activation, or latency-aware observed
/// activation failure paired with the already committed claim.
pub fn activate_claimed_observed_cache_limits_with_latency_durably<
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
    request: &obs::NativeExecutableCacheLimitsObservedLatencyActivationRequest,
) -> NativeExecutableCacheLimitsClaimedObservedLatencyCacheResult<
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
    let activate = obs::activate_observed_cache_limits_with_latency_durably;
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

/// Claims one due slot before latency-aware lease-cache activation.
///
/// # Errors
///
/// Returns cursor-claim failure before activation, or latency-aware observed
/// activation failure paired with the already committed claim.
pub fn activate_claimed_observed_lease_cache_limits_with_latency_durably<
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
    request: &obs::NativeExecutableCacheLimitsObservedLatencyActivationRequest,
) -> NativeExecutableCacheLimitsClaimedObservedLatencyLeaseResult<
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
        obs::activate_observed_lease_cache_limits_with_latency_durably;
    activate_after_claim(
        publication,
        context.cursor_store,
        claim_request,
        || activate(publication, &mut context.observed, request),
    )
}

/// Retries due-slot conflicts before ordinary-cache observed activation.
///
/// # Errors
///
/// Returns claim-retry failure, or existing observed activation failure paired
/// with exact committed retry evidence.
pub fn activate_retried_observed_cache_limits_durably<
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
    retry_request: NativeExecutableCacheLimitsRetriedObservedRequest,
    request: &obs::NativeExecutableCacheLimitsObservedActivationRequest,
) -> NativeExecutableCacheLimitsRetriedObservedCacheResult<
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
    activate_after_claim_retries(
        publication,
        context.cursor_store,
        retry_request,
        || activate(publication, &mut context.observed, request),
    )
}

/// Retries due-slot conflicts before latency-aware ordinary-cache activation.
///
/// # Errors
///
/// Returns claim-retry failure, or latency-aware observed activation failure
/// paired with exact committed retry evidence.
pub fn activate_retried_observed_cache_limits_with_latency_durably<
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
    retry_request: NativeExecutableCacheLimitsRetriedObservedRequest,
    request: &obs::NativeExecutableCacheLimitsObservedLatencyActivationRequest,
) -> NativeExecutableCacheLimitsRetriedObservedLatencyCacheResult<
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
    let activate = obs::activate_observed_cache_limits_with_latency_durably;
    activate_after_claim_retries(
        publication,
        context.cursor_store,
        retry_request,
        || activate(publication, &mut context.observed, request),
    )
}

/// Retries due-slot conflicts before lease-cache observed activation.
///
/// # Errors
///
/// Returns claim-retry failure, or existing observed activation failure paired
/// with exact committed retry evidence.
pub fn activate_retried_observed_lease_cache_limits_durably<
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
    retry_request: NativeExecutableCacheLimitsRetriedObservedRequest,
    request: &obs::NativeExecutableCacheLimitsObservedActivationRequest,
) -> NativeExecutableCacheLimitsRetriedObservedLeaseResult<
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
    activate_after_claim_retries(
        publication,
        context.cursor_store,
        retry_request,
        || activate(publication, &mut context.observed, request),
    )
}

/// Retries conflicts before latency-aware lease-cache observed activation.
///
/// # Errors
///
/// Returns claim-retry failure, or latency-aware observed activation failure
/// paired with exact committed retry evidence.
pub fn activate_retried_observed_lease_cache_limits_with_latency_durably<
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
    retry_request: NativeExecutableCacheLimitsRetriedObservedRequest,
    request: &obs::NativeExecutableCacheLimitsObservedLatencyActivationRequest,
) -> NativeExecutableCacheLimitsRetriedObservedLatencyLeaseResult<
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
        obs::activate_observed_lease_cache_limits_with_latency_durably;
    activate_after_claim_retries(
        publication,
        context.cursor_store,
        retry_request,
        || activate(publication, &mut context.observed, request),
    )
}

/// Applies caller conflict direction before ordinary-cache activation.
///
/// # Errors
///
/// Returns claim-retry failure, or observed activation failure paired with
/// exact committed retry evidence.
pub fn activate_controlled_retried_observed_cache_limits_durably<
    'publication,
    CursorStore,
    PolicyStore,
    Adapter,
    ClockError,
    Control,
>(
    publication: &'publication TelemetryPublication<ClockError>,
    context: &mut NativeExecutableCacheLimitsClaimedObservedCacheContext<
        '_,
        CursorStore,
        PolicyStore,
        Adapter,
    >,
    controlled: NativeExecutableCacheLimitsControlledRetriedObservedRequest<
        Control,
    >,
    request: &obs::NativeExecutableCacheLimitsObservedActivationRequest,
) -> NativeExecutableCacheLimitsRetriedObservedCacheResult<
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
    Control: FnMut(
        NativeContinuationRetryConflict,
    ) -> NativeContinuationRetryDirective,
{
    let activate =
        obs::activate_observed_executable_sequence_cache_limits_durably;
    activate_after_controlled_claim_retries(
        publication,
        context.cursor_store,
        controlled,
        || activate(publication, &mut context.observed, request),
    )
}

/// Applies caller conflict direction before latency-aware cache activation.
///
/// # Errors
///
/// Returns claim-retry failure, or latency-aware activation failure paired with
/// exact committed retry evidence.
pub fn activate_controlled_retried_observed_cache_limits_with_latency_durably<
    'publication,
    CursorStore,
    PolicyStore,
    Adapter,
    ClockError,
    Control,
>(
    publication: &'publication TelemetryPublication<ClockError>,
    context: &mut NativeExecutableCacheLimitsClaimedObservedCacheContext<
        '_,
        CursorStore,
        PolicyStore,
        Adapter,
    >,
    controlled: NativeExecutableCacheLimitsControlledRetriedObservedRequest<
        Control,
    >,
    request: &obs::NativeExecutableCacheLimitsObservedLatencyActivationRequest,
) -> NativeExecutableCacheLimitsRetriedObservedLatencyCacheResult<
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
    Control: FnMut(
        NativeContinuationRetryConflict,
    ) -> NativeContinuationRetryDirective,
{
    let activate = obs::activate_observed_cache_limits_with_latency_durably;
    activate_after_controlled_claim_retries(
        publication,
        context.cursor_store,
        controlled,
        || activate(publication, &mut context.observed, request),
    )
}

/// Applies caller conflict direction before lease-cache activation.
///
/// # Errors
///
/// Returns claim-retry failure, or observed activation failure paired with
/// exact committed retry evidence.
pub fn activate_controlled_retried_observed_lease_cache_limits_durably<
    'publication,
    CursorStore,
    PolicyStore,
    Adapter,
    ClockError,
    Control,
>(
    publication: &'publication TelemetryPublication<ClockError>,
    context: &mut NativeExecutableCacheLimitsClaimedObservedLeaseContext<
        '_,
        CursorStore,
        PolicyStore,
        Adapter,
    >,
    controlled: NativeExecutableCacheLimitsControlledRetriedObservedRequest<
        Control,
    >,
    request: &obs::NativeExecutableCacheLimitsObservedActivationRequest,
) -> NativeExecutableCacheLimitsRetriedObservedLeaseResult<
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
    Control: FnMut(
        NativeContinuationRetryConflict,
    ) -> NativeContinuationRetryDirective,
{
    let activate =
        obs::activate_observed_executable_sequence_lease_cache_limits_durably;
    activate_after_controlled_claim_retries(
        publication,
        context.cursor_store,
        controlled,
        || activate(publication, &mut context.observed, request),
    )
}

/// Applies caller direction before latency-aware lease-cache activation.
///
/// # Errors
///
/// Returns claim-retry failure, or latency-aware activation failure paired with
/// exact committed retry evidence.
pub fn activate_controlled_retried_lease_cache_limits_with_latency_durably<
    'publication,
    CursorStore,
    PolicyStore,
    Adapter,
    ClockError,
    Control,
>(
    publication: &'publication TelemetryPublication<ClockError>,
    context: &mut NativeExecutableCacheLimitsClaimedObservedLeaseContext<
        '_,
        CursorStore,
        PolicyStore,
        Adapter,
    >,
    controlled: NativeExecutableCacheLimitsControlledRetriedObservedRequest<
        Control,
    >,
    request: &obs::NativeExecutableCacheLimitsObservedLatencyActivationRequest,
) -> NativeExecutableCacheLimitsRetriedObservedLatencyLeaseResult<
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
    Control: FnMut(
        NativeContinuationRetryConflict,
    ) -> NativeContinuationRetryDirective,
{
    let activate =
        obs::activate_observed_lease_cache_limits_with_latency_durably;
    activate_after_controlled_claim_retries(
        publication,
        context.cursor_store,
        controlled,
        || activate(publication, &mut context.observed, request),
    )
}

/// Applies typed caller stop decisions before ordinary-cache activation.
///
/// Exact stop evidence is retained in the request's caller-owned stop state.
///
/// # Errors
///
/// Returns claim-retry failure, or observed activation failure paired with
/// exact committed retry evidence.
pub fn activate_reasoned_retried_observed_cache_limits_durably<
    'publication,
    CursorStore,
    PolicyStore,
    Adapter,
    StopReason,
    ClockError,
    Control,
>(
    publication: &'publication TelemetryPublication<ClockError>,
    context: &mut NativeExecutableCacheLimitsClaimedObservedCacheContext<
        '_,
        CursorStore,
        PolicyStore,
        Adapter,
    >,
    reasoned: NativeExecutableCacheLimitsReasonedRetriedObservedRequest<
        '_,
        Control,
        StopReason,
    >,
    request: &obs::NativeExecutableCacheLimitsObservedActivationRequest,
) -> NativeExecutableCacheLimitsRetriedObservedCacheResult<
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
    Control: FnMut(
        NativeContinuationRetryConflict,
    ) -> NativeContinuationRetryDecision<StopReason>,
{
    let activate =
        obs::activate_observed_executable_sequence_cache_limits_durably;
    activate_after_reasoned_claim_retries(
        publication,
        context.cursor_store,
        reasoned,
        || activate(publication, &mut context.observed, request),
    )
}

/// Applies typed stop decisions before latency-aware cache activation.
///
/// Exact stop evidence is retained in the request's caller-owned stop state.
///
/// # Errors
///
/// Returns claim-retry failure, or latency-aware activation failure paired with
/// exact committed retry evidence.
pub fn activate_reasoned_retried_observed_cache_limits_with_latency_durably<
    'publication,
    CursorStore,
    PolicyStore,
    Adapter,
    StopReason,
    ClockError,
    Control,
>(
    publication: &'publication TelemetryPublication<ClockError>,
    context: &mut NativeExecutableCacheLimitsClaimedObservedCacheContext<
        '_,
        CursorStore,
        PolicyStore,
        Adapter,
    >,
    reasoned: NativeExecutableCacheLimitsReasonedRetriedObservedRequest<
        '_,
        Control,
        StopReason,
    >,
    request: &obs::NativeExecutableCacheLimitsObservedLatencyActivationRequest,
) -> NativeExecutableCacheLimitsRetriedObservedLatencyCacheResult<
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
    Control: FnMut(
        NativeContinuationRetryConflict,
    ) -> NativeContinuationRetryDecision<StopReason>,
{
    let activate = obs::activate_observed_cache_limits_with_latency_durably;
    activate_after_reasoned_claim_retries(
        publication,
        context.cursor_store,
        reasoned,
        || activate(publication, &mut context.observed, request),
    )
}

/// Applies typed caller stop decisions before lease-cache activation.
///
/// Exact stop evidence is retained in the request's caller-owned stop state.
///
/// # Errors
///
/// Returns claim-retry failure, or observed activation failure paired with
/// exact committed retry evidence.
pub fn activate_reasoned_retried_observed_lease_cache_limits_durably<
    'publication,
    CursorStore,
    PolicyStore,
    Adapter,
    StopReason,
    ClockError,
    Control,
>(
    publication: &'publication TelemetryPublication<ClockError>,
    context: &mut NativeExecutableCacheLimitsClaimedObservedLeaseContext<
        '_,
        CursorStore,
        PolicyStore,
        Adapter,
    >,
    reasoned: NativeExecutableCacheLimitsReasonedRetriedObservedRequest<
        '_,
        Control,
        StopReason,
    >,
    request: &obs::NativeExecutableCacheLimitsObservedActivationRequest,
) -> NativeExecutableCacheLimitsRetriedObservedLeaseResult<
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
    Control: FnMut(
        NativeContinuationRetryConflict,
    ) -> NativeContinuationRetryDecision<StopReason>,
{
    let activate =
        obs::activate_observed_executable_sequence_lease_cache_limits_durably;
    activate_after_reasoned_claim_retries(
        publication,
        context.cursor_store,
        reasoned,
        || activate(publication, &mut context.observed, request),
    )
}

/// Applies typed stop decisions before latency-aware lease-cache activation.
///
/// Exact stop evidence is retained in the request's caller-owned stop state.
///
/// # Errors
///
/// Returns claim-retry failure, or latency-aware activation failure paired with
/// exact committed retry evidence.
pub fn activate_reasoned_retried_lease_cache_limits_with_latency_durably<
    'publication,
    CursorStore,
    PolicyStore,
    Adapter,
    StopReason,
    ClockError,
    Control,
>(
    publication: &'publication TelemetryPublication<ClockError>,
    context: &mut NativeExecutableCacheLimitsClaimedObservedLeaseContext<
        '_,
        CursorStore,
        PolicyStore,
        Adapter,
    >,
    reasoned: NativeExecutableCacheLimitsReasonedRetriedObservedRequest<
        '_,
        Control,
        StopReason,
    >,
    request: &obs::NativeExecutableCacheLimitsObservedLatencyActivationRequest,
) -> NativeExecutableCacheLimitsRetriedObservedLatencyLeaseResult<
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
    Control: FnMut(
        NativeContinuationRetryConflict,
    ) -> NativeContinuationRetryDecision<StopReason>,
{
    let activate =
        obs::activate_observed_lease_cache_limits_with_latency_durably;
    activate_after_reasoned_claim_retries(
        publication,
        context.cursor_store,
        reasoned,
        || activate(publication, &mut context.observed, request),
    )
}

/// Applies product conflict policy before ordinary-cache activation.
///
/// Exact typed stop evidence is retained in the request's caller-owned state.
///
/// # Errors
///
/// Returns claim-retry failure, or observed activation failure paired with
/// exact committed retry evidence.
pub fn activate_policy_retried_observed_cache_limits_durably<
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
    policy_request: NativeExecutableCacheLimitsPolicyRetriedObservedRequest<'_>,
    request: &obs::NativeExecutableCacheLimitsObservedActivationRequest,
) -> NativeExecutableCacheLimitsRetriedObservedCacheResult<
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
    activate_after_policy_claim_retries(
        publication,
        context.cursor_store,
        policy_request,
        || activate(publication, &mut context.observed, request),
    )
}

/// Applies product conflict policy before latency-aware cache activation.
///
/// Exact typed stop evidence is retained in the request's caller-owned state.
///
/// # Errors
///
/// Returns claim-retry failure, or latency-aware activation failure paired with
/// exact committed retry evidence.
pub fn activate_policy_retried_observed_cache_limits_with_latency_durably<
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
    policy_request: NativeExecutableCacheLimitsPolicyRetriedObservedRequest<'_>,
    request: &obs::NativeExecutableCacheLimitsObservedLatencyActivationRequest,
) -> NativeExecutableCacheLimitsRetriedObservedLatencyCacheResult<
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
    let activate = obs::activate_observed_cache_limits_with_latency_durably;
    activate_after_policy_claim_retries(
        publication,
        context.cursor_store,
        policy_request,
        || activate(publication, &mut context.observed, request),
    )
}

/// Applies product conflict policy before lease-cache activation.
///
/// Exact typed stop evidence is retained in the request's caller-owned state.
///
/// # Errors
///
/// Returns claim-retry failure, or observed activation failure paired with
/// exact committed retry evidence.
pub fn activate_policy_retried_observed_lease_cache_limits_durably<
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
    policy_request: NativeExecutableCacheLimitsPolicyRetriedObservedRequest<'_>,
    request: &obs::NativeExecutableCacheLimitsObservedActivationRequest,
) -> NativeExecutableCacheLimitsRetriedObservedLeaseResult<
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
    activate_after_policy_claim_retries(
        publication,
        context.cursor_store,
        policy_request,
        || activate(publication, &mut context.observed, request),
    )
}

/// Applies product conflict policy before latency-aware lease-cache activation.
///
/// Exact typed stop evidence is retained in the request's caller-owned state.
///
/// # Errors
///
/// Returns claim-retry failure, or latency-aware activation failure paired with
/// exact committed retry evidence.
pub fn activate_policy_retried_lease_cache_limits_with_latency_durably<
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
    policy_request: NativeExecutableCacheLimitsPolicyRetriedObservedRequest<'_>,
    request: &obs::NativeExecutableCacheLimitsObservedLatencyActivationRequest,
) -> NativeExecutableCacheLimitsRetriedObservedLatencyLeaseResult<
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
        obs::activate_observed_lease_cache_limits_with_latency_durably;
    activate_after_policy_claim_retries(
        publication,
        context.cursor_store,
        policy_request,
        || activate(publication, &mut context.observed, request),
    )
}

#[cfg(test)]
#[path = "../../../../../tests/tiered/cache_trigger_observed.rs"]
mod tests;
