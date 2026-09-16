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
//   - Caller-bounded retries of one-shot durable latency merge conflicts.
// - Must-Not:
//   - Retry non-conflicts, sleep/back off, infer budgets, or hide final
//     conflict.
//   - Infer caller cancellation, pacing, backoff, or fairness policy.
// - Allows:
//   - Inputs: source histogram, positive attempt/byte bounds, store, and
//     optional caller retry direction.
//   - Outputs: exact final one-shot outcome plus attempts consumed.
//   - Side effects: at most the caller-configured number of one-shot attempts.
// - Split-When:
//   - Asynchronous retry control gains authority.
// - Merge-When:
//   - One distributed telemetry owner owns retry timing and cancellation.
// - Summary:
//   - Repeats durable latency merge only after explicit CAS conflict.
// - Description:
//   - Every retry begins with a fresh bounded load and preserves final
//     conflict.
// - Usage:
//   - Select a positive maximum attempt count for synchronous contention.
// - Defaults:
//   - No implicit retry count or timing policy exists.
//

//! Caller-bounded synchronous retries for durable latency merge conflicts.

use std::num::NonZeroUsize;

use super::{
    NativeContinuationCachedRetryLatencyDurableMerge,
    NativeContinuationCachedRetryLatencyDurableMergeError,
    NativeContinuationCachedRetryLatencyHistogram,
    merge_cached_retry_latency_histogram_durably,
};
use crate::blob_store::{
    NativeContinuationBlobStore as BlobStore,
    NativeContinuationConditionalBlobStore as ConditionalBlobStore,
    NativeContinuationDurableBlobStore as DurableBlobStore,
};
use crate::retry_control::{
    NativeContinuationRetryConflict, NativeContinuationRetryDirective,
};

/// Immutable inputs for one bounded latency-merge retry loop.
#[derive(Clone, Copy, Debug)]
pub struct NativeContinuationCachedRetryLatencyDurableMergeRetryRequest<'source>
{
    maximum_attempts: NonZeroUsize,
    maximum_bytes: NonZeroUsize,
    source: &'source NativeContinuationCachedRetryLatencyHistogram,
}

impl<'source>
    NativeContinuationCachedRetryLatencyDurableMergeRetryRequest<'source>
{
    /// Binds source telemetry and the positive retry/load bounds.
    #[must_use]
    pub const fn new(
        source: &'source NativeContinuationCachedRetryLatencyHistogram,
        maximum_bytes: NonZeroUsize,
        maximum_attempts: NonZeroUsize,
    ) -> Self {
        Self {
            maximum_attempts,
            maximum_bytes,
            source,
        }
    }
}

/// Final one-shot durable merge outcome plus exact attempts consumed.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryLatencyDurableMergeRetry<
    DurabilityError,
> {
    attempts: usize,
    outcome: NativeContinuationCachedRetryLatencyDurableMerge<DurabilityError>,
}

/// Result of caller-bounded durable latency merge retry orchestration.
pub type NativeContinuationCachedRetryLatencyDurableMergeRetryResult<
    StoreError,
    DurabilityError,
> = Result<
    NativeContinuationCachedRetryLatencyDurableMergeRetry<DurabilityError>,
    NativeContinuationCachedRetryLatencyDurableMergeError<StoreError>,
>;

/// Bounded retry result specialized to one conditional durable store.
pub type NativeContinuationCachedRetryLatencyDurableMergeRetryStoreResult<
    Store,
> = NativeContinuationCachedRetryLatencyDurableMergeRetryResult<
    <Store as BlobStore>::Error,
    <Store as DurableBlobStore>::DurabilityError,
>;

impl<DurabilityError>
    NativeContinuationCachedRetryLatencyDurableMergeRetry<DurabilityError>
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
    ) -> NativeContinuationCachedRetryLatencyDurableMerge<DurabilityError> {
        self.outcome
    }

    /// Borrows the exact final one-shot outcome.
    #[must_use]
    pub const fn outcome(
        &self,
    ) -> &NativeContinuationCachedRetryLatencyDurableMerge<DurabilityError>
    {
        &self.outcome
    }
}

/// Retries only durable latency merge conflicts up to a positive attempt limit.
///
/// # Errors
///
/// Returns the first non-conflict load, codec, schema, or store failure.
/// Durable and committed publication stop immediately. The final conflict is
/// returned as successful typed outcome when the caller-selected attempt limit
/// is spent.
pub fn merge_cached_retry_latency_histogram_durably_with_retries<Store>(
    store: &mut Store,
    source: &NativeContinuationCachedRetryLatencyHistogram,
    maximum_bytes: NonZeroUsize,
    maximum_attempts: NonZeroUsize,
) -> NativeContinuationCachedRetryLatencyDurableMergeRetryStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    merge_cached_retry_latency_with_retry_control(
        store,
        NativeContinuationCachedRetryLatencyDurableMergeRetryRequest::new(
            source,
            maximum_bytes,
            maximum_attempts,
        ),
        |_conflict| NativeContinuationRetryDirective::Continue,
    )
}

/// Retries latency merge conflicts while the caller permits another attempt.
///
/// The control callback runs only after a retryable conflict and while another
/// attempt remains in the positive budget. `Stop` preserves the typed conflict;
/// `Continue` performs the same fresh bounded load and merge as the legacy
/// wrapper. This layer performs no clock read, wait, backoff, or fairness
/// action.
///
/// # Errors
///
/// Returns the first non-conflict load, codec, schema, or store failure.
/// Durable and committed publication stop immediately.
pub fn merge_cached_retry_latency_with_retry_control<Store, Control>(
    store: &mut Store,
    request: NativeContinuationCachedRetryLatencyDurableMergeRetryRequest<'_>,
    mut control: Control,
) -> NativeContinuationCachedRetryLatencyDurableMergeRetryStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
    Control: FnMut(
        NativeContinuationRetryConflict,
    ) -> NativeContinuationRetryDirective,
{
    let mut attempts = 1usize;
    let mut outcome = merge_cached_retry_latency_histogram_durably(
        store,
        request.source,
        request.maximum_bytes,
    )?;
    while matches!(
        outcome,
        NativeContinuationCachedRetryLatencyDurableMerge::Conflict { .. }
    ) && attempts < request.maximum_attempts.get()
    {
        if control(NativeContinuationRetryConflict::new(attempts))
            == NativeContinuationRetryDirective::Stop
        {
            break;
        }
        attempts = attempts.saturating_add(1);
        outcome = merge_cached_retry_latency_histogram_durably(
            store,
            request.source,
            request.maximum_bytes,
        )?;
    }
    Ok(NativeContinuationCachedRetryLatencyDurableMergeRetry {
        attempts,
        outcome,
    })
}
