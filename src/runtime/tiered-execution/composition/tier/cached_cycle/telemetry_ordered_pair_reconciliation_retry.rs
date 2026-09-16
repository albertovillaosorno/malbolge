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
//   - Infer caller cancellation, pacing, backoff, or fairness policy.
// - Allows:
//   - Inputs: one reconciliation request, positive attempt limit, store, and
//     optional caller retry direction.
//   - Outputs: exact final one-shot outcome plus attempts consumed.
//   - Side effects: at most the caller-configured number of reconciliations.
// - Split-When:
//   - Asynchronous retry control or ordering service gains authority.
// - Merge-When:
//   - One distributed telemetry owner owns retry timing and reconciliation.
// - Summary:
//   - Repeats complete ordered-pair reconciliation only after CAS conflict.
// - Description:
//   - Every continued retry reloads/remerges; stale external order fails
//     normally.
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
use crate::retry_control::{
    NativeContinuationRetryAttemptCursor, NativeContinuationRetryConflict,
    NativeContinuationRetryDirective,
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
    reconcile_cached_retry_ordered_pair_with_retry_control(
        store,
        request,
        maximum_attempts,
        |_conflict| NativeContinuationRetryDirective::Continue,
    )
}

/// Retries reconciliation conflicts while the caller permits another attempt.
///
/// The control callback runs only after a retryable conflict and only when the
/// positive attempt budget still permits another attempt. It receives the exact
/// number of completed attempts. `Stop` preserves the current typed conflict;
/// `Continue` performs the same complete fresh reconciliation as the legacy
/// retry wrapper. This layer performs no clock read, wait, or fairness action.
///
/// # Errors
///
/// Returns the first stale-order, count, latency, codec, bound, or store
/// failure. Durable and committed publication stop immediately.
pub fn reconcile_cached_retry_ordered_pair_with_retry_control<Store, Control>(
    store: &mut Store,
    request: NativeContinuationCachedRetryOrderedPairReconciliationRequest<'_>,
    maximum_attempts: NonZeroUsize,
    mut control: Control,
) -> RetryStoreResult<Store>
where
    Store: ConditionalPairStore + DurablePairStore,
    Control: FnMut(
        NativeContinuationRetryConflict,
    ) -> NativeContinuationRetryDirective,
{
    let mut outcome =
        reconcile_cached_retry_telemetry_ordered_pair_durably(store, request)?;
    let mut attempts =
        NativeContinuationRetryAttemptCursor::after_first(maximum_attempts);
    while matches!(
        outcome,
        NativeContinuationCachedRetryOrderedPairReconciliation::Conflict { .. }
    ) && attempts.can_retry()
    {
        if control(attempts.conflict())
            == NativeContinuationRetryDirective::Stop
            || !attempts.advance()
        {
            break;
        }
        outcome = reconcile_cached_retry_telemetry_ordered_pair_durably(
            store, request,
        )?;
    }
    Ok(
        NativeContinuationCachedRetryOrderedPairReconciliationRetry {
            attempts: attempts.completed_attempts(),
            outcome,
        },
    )
}
