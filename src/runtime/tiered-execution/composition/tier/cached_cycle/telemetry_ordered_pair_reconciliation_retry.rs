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
//   - Caller-bounded retries of ordered pair reconciliation conflicts.
// - Must-Not:
//   - Retry non-conflicts, rewrite order, sleep, or infer attempt budgets.
// - Allows:
//   - Inputs: one reconciliation request, positive attempt limit, and store.
//   - Outputs: exact final one-shot outcome plus attempts consumed.
//   - Side effects: at most the caller-configured number of reconciliations.
// - Split-When:
//   - Backoff, cancellation, fairness, or ordering service gains authority.
// - Merge-When:
//   - One distributed telemetry owner owns retry timing and reconciliation.
// - Summary:
//   - Repeats complete ordered-pair reconciliation only after CAS conflict.
// - Description:
//   - Every retry reloads and remerges; stale external order fails normally.
// - Usage:
//   - Select a positive maximum attempt count for synchronous contention.
// - Defaults:
//   - No implicit retry count, timing policy, or order rewrite exists.
//

//! Caller-bounded retries for ordered count plus latency reconciliation.

use std::num::NonZeroUsize;

use super::{
    NativeContinuationCachedRetryOrderedPairReconciliation,
    NativeContinuationCachedRetryOrderedPairReconciliationError,
    NativeContinuationCachedRetryOrderedPairReconciliationRequest,
    reconcile_cached_retry_telemetry_ordered_pair_durably,
};
use crate::blob_pair_store::{
    NativeContinuationBlobPairStore as PairStore,
    NativeContinuationConditionalBlobPairStore as ConditionalPairStore,
    NativeContinuationDurableBlobPairStore as DurablePairStore,
};

/// Final reconciliation outcome plus exact attempts consumed.
#[derive(Debug)]
pub struct NativeContinuationCachedRetryOrderedPairReconciliationRetry<
    Revision,
    DurabilityError,
> {
    attempts: usize,
    outcome: NativeContinuationCachedRetryOrderedPairReconciliation<
        Revision,
        DurabilityError,
    >,
}

/// Bounded reconciliation retry result specialized to one durable pair store.
pub type NativeContinuationCachedRetryOrderedPairReconciliationRetryStoreResult<
    Store,
> = Result<
    NativeContinuationCachedRetryOrderedPairReconciliationRetry<
        <Store as ConditionalPairStore>::Revision,
        <Store as DurablePairStore>::DurabilityError,
    >,
    NativeContinuationCachedRetryOrderedPairReconciliationError<
        <Store as PairStore>::Error,
    >,
>;

type RetryStoreResult<Store> =
    NativeContinuationCachedRetryOrderedPairReconciliationRetryStoreResult<
        Store,
    >;

impl<Revision, DurabilityError>
    NativeContinuationCachedRetryOrderedPairReconciliationRetry<
        Revision,
        DurabilityError,
    >
{
    /// Returns the exact number of reconciliation attempts consumed.
    #[must_use]
    pub const fn attempts(&self) -> usize {
        self.attempts
    }

    /// Borrows the exact final one-shot reconciliation outcome.
    #[must_use]
    pub const fn outcome(
        &self,
    ) -> &NativeContinuationCachedRetryOrderedPairReconciliation<
        Revision,
        DurabilityError,
    > {
        &self.outcome
    }
}

/// Retries only one-shot reconciliation conflicts up to a positive limit.
///
/// # Errors
///
/// Returns the first stale-order, count, latency, codec, bound, or store
/// failure. Durable and committed publication stop immediately. Every conflict
/// retry performs a complete fresh load, reconciliation, and conditional write.
pub fn reconcile_cached_retry_telemetry_ordered_pair_durably_with_retries<
    Store,
>(
    store: &mut Store,
    request: NativeContinuationCachedRetryOrderedPairReconciliationRequest<'_>,
    maximum_attempts: NonZeroUsize,
) -> RetryStoreResult<Store>
where
    Store: ConditionalPairStore + DurablePairStore,
{
    let mut attempts = 1usize;
    let mut outcome =
        reconcile_cached_retry_telemetry_ordered_pair_durably(store, request)?;
    while matches!(
        outcome,
        NativeContinuationCachedRetryOrderedPairReconciliation::Conflict { .. }
    ) && attempts < maximum_attempts.get()
    {
        attempts = attempts.saturating_add(1);
        outcome = reconcile_cached_retry_telemetry_ordered_pair_durably(
            store, request,
        )?;
    }
    Ok(
        NativeContinuationCachedRetryOrderedPairReconciliationRetry {
            attempts,
            outcome,
        },
    )
}
