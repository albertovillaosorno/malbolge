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
//   - Caller-bounded synchronous retry of exact cache-trigger claim conflicts.
// - Must-Not:
//   - Retry committed claims, invent missing cadence, catch up missed slots,
//     sleep/back off, or activate cache policy.
// - Allows:
//   - Inputs: immutable append evidence, expected cursor, positive byte/attempt
//     bounds, conditional durable store, and optional caller retry direction.
//   - Outputs: terminal typed claim plus exact completed-attempt count.
//   - Side effects: at most the caller-selected number of one-shot claims.
// - Split-When:
//   - Asynchronous retry control or product conflict policy gains authority.
// - Merge-When:
//   - One product trigger owner subsumes contention retry and activation.
// - Summary:
//   - Refreshes exact cursor conflict state before another due-slot claim.
// - Description:
//   - Refreshed non-due state stops normally without another durable CAS.
// - Usage:
//   - Select a positive synchronous attempt budget for cursor contention.
// - Defaults:
//   - Missing conflict state is terminal because no cadence may be invented.
//

//! Caller-bounded synchronous retries for cache-trigger cadence claim
//! conflicts.

use std::num::NonZeroUsize;

use crate::blob_store::{
    NativeContinuationBlobStore as BlobStore,
    NativeContinuationConditionalBlobStore as ConditionalBlobStore,
    NativeContinuationDurableBlobStore as DurableBlobStore,
};
use crate::cached_cycle::NativeContinuationCachedRetryTelemetryWindowAppend;
use crate::retry_control::{
    NativeContinuationRetryAttemptCursor, NativeContinuationRetryConflict,
    NativeContinuationRetryDecision, NativeContinuationRetryDirective,
    NativeContinuationRetryEvidence, NativeContinuationRetryStop,
    NativeContinuationRetryStopState,
};
use crate::{
    executable_cache_limits_trigger_cadence as trigger,
    executable_cache_limits_trigger_cadence_cas as cursor_cas,
    executable_cache_limits_trigger_cadence_claim as claim,
};

type Cursor = trigger::NativeExecutableCacheLimitsTriggerCadence;
type CursorCas<DurabilityError> =
    cursor_cas::NativeExecutableCacheLimitsTriggerCadenceCas<DurabilityError>;
type Claim<DurabilityError> =
    claim::NativeExecutableCacheLimitsTriggerCadenceClaim<DurabilityError>;

/// Immutable inputs for one bounded trigger-claim retry loop.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeExecutableCacheLimitsTriggerCadenceClaimRetryRequest<'append> {
    append: &'append NativeContinuationCachedRetryTelemetryWindowAppend,
    expected: Cursor,
    maximum_attempts: NonZeroUsize,
    maximum_bytes: NonZeroUsize,
}

/// Terminal trigger claim plus exact number of claim attempts consumed.
pub type NativeExecutableCacheLimitsTriggerCadenceClaimRetry<DurabilityError> =
    NativeContinuationRetryEvidence<Claim<DurabilityError>>;

/// Terminal retry evidence plus optional typed caller stop reason.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeExecutableCacheLimitsTriggerCadenceReasonedClaimRetry<
    DurabilityError,
    StopReason,
> {
    retry: NativeExecutableCacheLimitsTriggerCadenceClaimRetry<DurabilityError>,
    stop: Option<NativeContinuationRetryStop<StopReason>>,
}

/// Bounded trigger-claim retry result specialized to one durable store.
pub type NativeExecutableCacheLimitsTriggerCadenceClaimRetryStoreResult<Store> =
    Result<
        NativeExecutableCacheLimitsTriggerCadenceClaimRetry<
            <Store as DurableBlobStore>::DurabilityError,
        >,
        cursor_cas::NativeExecutableCacheLimitsTriggerCadenceCasError<
            <Store as BlobStore>::Error,
        >,
    >;

/// Reason-preserving claim-retry result specialized to one durable store.
pub type NativeExecutableCacheLimitsTriggerCadenceReasonedRetryStoreResult<
    Store,
    StopReason,
> = Result<
    NativeExecutableCacheLimitsTriggerCadenceReasonedClaimRetry<
        <Store as DurableBlobStore>::DurabilityError,
        StopReason,
    >,
    cursor_cas::NativeExecutableCacheLimitsTriggerCadenceCasError<
        <Store as BlobStore>::Error,
    >,
>;

impl<DurabilityError, StopReason>
    NativeExecutableCacheLimitsTriggerCadenceReasonedClaimRetry<
        DurabilityError,
        StopReason,
    >
{
    /// Returns the exact number of claim attempts consumed.
    #[must_use]
    pub const fn attempts(&self) -> usize {
        self.retry.attempts()
    }

    /// Consumes evidence and returns the terminal claim retry.
    #[must_use]
    pub fn into_retry(
        self,
    ) -> NativeExecutableCacheLimitsTriggerCadenceClaimRetry<DurabilityError>
    {
        self.retry
    }

    /// Borrows the exact terminal claim outcome.
    #[must_use]
    pub const fn outcome(&self) -> &Claim<DurabilityError> {
        self.retry.outcome()
    }

    /// Borrows typed caller stop evidence when the caller explicitly stopped.
    #[must_use]
    pub const fn stop(
        &self,
    ) -> Option<&NativeContinuationRetryStop<StopReason>> {
        self.stop.as_ref()
    }
}

impl<'append>
    NativeExecutableCacheLimitsTriggerCadenceClaimRetryRequest<'append>
{
    /// Binds exact append/cursor state to positive byte and attempt bounds.
    #[must_use]
    pub const fn new(
        expected: Cursor,
        append: &'append NativeContinuationCachedRetryTelemetryWindowAppend,
        maximum_bytes: NonZeroUsize,
        maximum_attempts: NonZeroUsize,
    ) -> Self {
        Self {
            append,
            expected,
            maximum_attempts,
            maximum_bytes,
        }
    }
}

/// Retries only typed cursor conflicts up to a positive attempt limit.
///
/// # Errors
///
/// Returns the first byte-limit, codec, or store failure. Durable publication
/// and committed durability failure stop immediately. Final conflict or
/// refreshed non-due evidence is successful terminal evidence.
pub fn claim_cache_trigger_cadence_slot_durably_with_retries<Store>(
    store: &mut Store,
    request: NativeExecutableCacheLimitsTriggerCadenceClaimRetryRequest<'_>,
) -> NativeExecutableCacheLimitsTriggerCadenceClaimRetryStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    claim_cache_trigger_cadence_slot_with_retry_control(
        store,
        request,
        |_conflict| NativeContinuationRetryDirective::Continue,
    )
}

/// Retries typed conflicts while preserving an opaque caller stop reason.
///
/// The typed control callback is consulted only for a retryable conflict while
/// another attempt remains. A caller `Stop(reason)` retains that reason bound
/// to the exact completed-attempt conflict. Budget exhaustion, non-due refresh,
/// committed publication, and failures never invent a stop reason.
///
/// # Errors
///
/// Returns the first byte-limit, codec, or store failure. Durable and committed
/// publication stop immediately.
pub fn claim_cache_trigger_cadence_slot_with_retry_decision<
    Store,
    StopReason,
    Control,
>(
    store: &mut Store,
    request: NativeExecutableCacheLimitsTriggerCadenceClaimRetryRequest<'_>,
    mut control: Control,
) -> NativeExecutableCacheLimitsTriggerCadenceReasonedRetryStoreResult<
    Store,
    StopReason,
>
where
    Store: ConditionalBlobStore + DurableBlobStore,
    Control: FnMut(
        NativeContinuationRetryConflict,
    ) -> NativeContinuationRetryDecision<StopReason>,
{
    let mut stop_state = NativeContinuationRetryStopState::new();
    let retry = claim_cache_trigger_cadence_slot_with_retry_control(
        store,
        request,
        |conflict| stop_state.resolve(conflict, control(conflict)),
    )?;
    Ok(
        NativeExecutableCacheLimitsTriggerCadenceReasonedClaimRetry {
            retry,
            stop: stop_state.into_stop(),
        },
    )
}

/// Retries typed cursor conflicts while the caller permits another attempt.
///
/// The control callback runs only after a retryable conflict with a decoded
/// current cursor and while another attempt remains. `Continue` refreshes the
/// expected cursor from that exact conflict state and revalidates the same
/// append. No clock read, wait, backoff, catch-up, or missing-state invention
/// occurs.
///
/// # Errors
///
/// Returns the first byte-limit, codec, or store failure. Durable and committed
/// publication stop immediately.
pub fn claim_cache_trigger_cadence_slot_with_retry_control<Store, Control>(
    store: &mut Store,
    request: NativeExecutableCacheLimitsTriggerCadenceClaimRetryRequest<'_>,
    mut control: Control,
) -> NativeExecutableCacheLimitsTriggerCadenceClaimRetryStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
    Control: FnMut(
        NativeContinuationRetryConflict,
    ) -> NativeContinuationRetryDirective,
{
    let mut expected = request.expected;
    let mut outcome = claim::claim_cache_trigger_cadence_slot_durably(
        store,
        expected,
        request.append,
        request.maximum_bytes,
    )?;
    let mut attempts = NativeContinuationRetryAttemptCursor::after_first(
        request.maximum_attempts,
    );
    loop {
        let next_expected = match &outcome {
            Claim::Attempted {
                publication:
                    CursorCas::Conflict {
                        current: Some(current), ..
                    },
                ..
            } if attempts.can_retry() => *current,
            Claim::Attempted { .. } | Claim::Withheld { .. } => break,
        };
        if control(attempts.conflict())
            == NativeContinuationRetryDirective::Stop
            || !attempts.advance()
        {
            break;
        }
        expected = next_expected;
        outcome = claim::claim_cache_trigger_cadence_slot_durably(
            store,
            expected,
            request.append,
            request.maximum_bytes,
        )?;
    }
    Ok(NativeContinuationRetryEvidence::new(
        attempts.completed_attempts(),
        outcome,
    ))
}

#[cfg(test)]
#[path = "../../../../../tests/tiered/cache_trigger_claim_retry.rs"]
mod tests;
