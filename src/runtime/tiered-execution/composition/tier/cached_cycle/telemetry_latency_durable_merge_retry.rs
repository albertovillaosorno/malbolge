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
// - Allows:
//   - Inputs: source histogram, positive attempt limit, byte bound, and store.
//   - Outputs: exact final one-shot outcome plus attempts consumed.
//   - Side effects: at most the caller-configured number of one-shot attempts.
// - Split-When:
//   - Backoff, cancellation, fairness, or asynchronous scheduling gains policy.
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
    let mut attempts = 1usize;
    let mut outcome = merge_cached_retry_latency_histogram_durably(
        store,
        source,
        maximum_bytes,
    )?;
    while matches!(
        outcome,
        NativeContinuationCachedRetryLatencyDurableMerge::Conflict { .. }
    ) && attempts < maximum_attempts.get()
    {
        attempts = attempts.saturating_add(1);
        outcome = merge_cached_retry_latency_histogram_durably(
            store,
            source,
            maximum_bytes,
        )?;
    }
    Ok(NativeContinuationCachedRetryLatencyDurableMergeRetry {
        attempts,
        outcome,
    })
}
