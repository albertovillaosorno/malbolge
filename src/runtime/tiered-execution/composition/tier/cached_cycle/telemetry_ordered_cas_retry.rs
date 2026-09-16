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
//   - Caller-bounded retries of one-shot durable ordered-count CAS conflicts.
// - Must-Not:
//   - Retry non-conflicts, rebase caller order, sleep, or infer retry budgets.
//   - Infer caller cancellation, pacing, backoff, or fairness policy.
// - Allows:
//   - Inputs: one ordered CAS request, positive attempt limit, store, and
//     optional caller retry direction.
//   - Outputs: exact final one-shot outcome plus attempts consumed.
//   - Side effects: at most the caller-configured number of one-shot attempts.
// - Split-When:
//   - Asynchronous retry control or ordering service gains authority.
// - Merge-When:
//   - One distributed count owner owns retry timing and external order policy.
// - Summary:
//   - Repeats ordered durable CAS only after explicit storage conflict.
// - Description:
//   - Every retry reloads state; stale submitted order then fails normally.
// - Usage:
//   - Select a positive maximum attempt count for synchronous contention.
// - Defaults:
//   - No implicit retry count, timing policy, or order rewrite exists.
//

//! Caller-bounded synchronous retries for durable ordered count conflicts.

use std::num::NonZeroUsize;

use super::{
    NativeContinuationCachedRetryTelemetryOrderedCas,
    NativeContinuationCachedRetryTelemetryOrderedCasError,
    NativeContinuationCachedRetryTelemetryOrderedCasRequest,
    publish_cached_retry_telemetry_ordered_batch_durably,
};
use crate::blob_store::{
    NativeContinuationBlobStore as BlobStore,
    NativeContinuationConditionalBlobStore as ConditionalBlobStore,
    NativeContinuationDurableBlobStore as DurableBlobStore,
};
use crate::retry_control::{
    NativeContinuationRetryConflict, NativeContinuationRetryDirective,
};

/// Final one-shot ordered CAS outcome plus exact attempts consumed.
#[derive(Debug)]
pub struct NativeContinuationCachedRetryTelemetryOrderedCasRetry<
    DurabilityError,
> {
    attempts: usize,
    outcome: NativeContinuationCachedRetryTelemetryOrderedCas<DurabilityError>,
}

/// Result of caller-bounded ordered count CAS retry orchestration.
pub type NativeContinuationCachedRetryTelemetryOrderedCasRetryResult<
    StoreError,
    DurabilityError,
> = Result<
    NativeContinuationCachedRetryTelemetryOrderedCasRetry<DurabilityError>,
    NativeContinuationCachedRetryTelemetryOrderedCasError<StoreError>,
>;

/// Bounded ordered CAS retry result specialized to one durable store.
pub type NativeContinuationCachedRetryTelemetryOrderedCasRetryStoreResult<
    Store,
> = NativeContinuationCachedRetryTelemetryOrderedCasRetryResult<
    <Store as BlobStore>::Error,
    <Store as DurableBlobStore>::DurabilityError,
>;

impl<DurabilityError>
    NativeContinuationCachedRetryTelemetryOrderedCasRetry<DurabilityError>
{
    /// Returns the exact number of one-shot attempts consumed.
    #[must_use]
    pub const fn attempts(&self) -> usize {
        self.attempts
    }

    /// Consumes retry evidence into the exact final one-shot outcome.
    #[must_use]
    pub fn into_outcome(
        self,
    ) -> NativeContinuationCachedRetryTelemetryOrderedCas<DurabilityError> {
        self.outcome
    }

    /// Borrows the exact final one-shot outcome.
    #[must_use]
    pub const fn outcome(
        &self,
    ) -> &NativeContinuationCachedRetryTelemetryOrderedCas<DurabilityError>
    {
        &self.outcome
    }
}

/// Retries only ordered durable CAS conflicts up to a positive attempt limit.
///
/// # Errors
///
/// Returns the first non-conflict load, codec, stale-order, FIFO, or store
/// failure. Durable and committed publication stop immediately. A fresh load
/// that makes submitted order stale returns that error rather than rebasing it.
pub fn publish_cached_retry_telemetry_ordered_batch_durably_with_retries<
    Store,
>(
    store: &mut Store,
    request: NativeContinuationCachedRetryTelemetryOrderedCasRequest<'_>,
    maximum_attempts: NonZeroUsize,
) -> NativeContinuationCachedRetryTelemetryOrderedCasRetryStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    publish_cached_retry_ordered_batch_with_retry_control(
        store,
        request,
        maximum_attempts,
        |_conflict| NativeContinuationRetryDirective::Continue,
    )
}

/// Retries ordered CAS conflicts while the caller permits another attempt.
///
/// The control callback runs only after a retryable conflict and while another
/// attempt remains in the positive budget. `Stop` preserves the typed conflict;
/// `Continue` performs the same fresh load and one-shot CAS as the legacy retry
/// wrapper. No clock read, wait, backoff, or fairness action is inferred.
///
/// # Errors
///
/// Returns the first non-conflict load, codec, stale-order, FIFO, or store
/// failure. Durable and committed publication stop immediately.
pub fn publish_cached_retry_ordered_batch_with_retry_control<Store, Control>(
    store: &mut Store,
    request: NativeContinuationCachedRetryTelemetryOrderedCasRequest<'_>,
    maximum_attempts: NonZeroUsize,
    mut control: Control,
) -> NativeContinuationCachedRetryTelemetryOrderedCasRetryStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
    Control: FnMut(
        NativeContinuationRetryConflict,
    ) -> NativeContinuationRetryDirective,
{
    let mut attempts = 1usize;
    let mut outcome =
        publish_cached_retry_telemetry_ordered_batch_durably(store, request)?;
    while matches!(
        outcome,
        NativeContinuationCachedRetryTelemetryOrderedCas::Conflict { .. }
    ) && attempts < maximum_attempts.get()
    {
        if control(NativeContinuationRetryConflict::new(attempts))
            == NativeContinuationRetryDirective::Stop
        {
            break;
        }
        attempts = attempts.saturating_add(1);
        outcome = publish_cached_retry_telemetry_ordered_batch_durably(
            store, request,
        )?;
    }
    Ok(NativeContinuationCachedRetryTelemetryOrderedCasRetry {
        attempts,
        outcome,
    })
}
