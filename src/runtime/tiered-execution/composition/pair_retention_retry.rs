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
//   - Caller-directed reconciliation and bounded CAS retry for exact pair
//     retention journals.
// - Must-Not:
//   - Choose union/intersection, infer chronology, reorder revisions, or sleep.
//   - Infer caller cancellation, pacing, backoff, or fairness policy.
// - Allows:
//   - Inputs: configured conditional durable blob store, positive byte/attempt
//     bounds, caller reconciliation callback, and optional retry direction.
//   - Outputs: exact attempt count plus terminal typed CAS outcome.
//   - Side effects: one initial bounded load and at most the caller-selected
//     number of conditional durable publications.
// - Split-When:
//   - Asynchronous retry control or automatic retention policy gains authority.
// - Merge-When:
//   - Another composition service owns the same reconciliation retry loop.
// - Summary:
//   - Retries retention CAS only after caller reconciliation of typed current
//     state.
// - Description:
//   - CAS conflict state is the next reconciliation input; successful or
//     committed publication stops immediately.
// - Usage:
//   - Used only when the caller can explicitly reconcile concurrent retention.
// - Defaults:
//   - No retry policy exists beyond the positive caller attempt budget.
//

//! Caller-owned reconciliation around exact retention-journal CAS conflicts.

use std::num::NonZeroUsize;

use crate::blob_pair_retention::NativeContinuationBlobPairRetention;
use crate::blob_store::{
    NativeContinuationBlobStore, NativeContinuationConditionalBlobStore,
    NativeContinuationDurableBlobStore,
};
use crate::file_blob_pair_store::NativeContinuationFileBlobPairRevision;
use crate::pair_retention_journal::{
    NativeContinuationFileBlobPairRetentionJournalCas,
    NativeContinuationFileBlobPairRetentionJournalError,
    NativeContinuationFileBlobPairRetentionJournalLoad,
    compare_and_swap_file_blob_pair_retention_journal_durably,
    restore_file_blob_pair_retention_journal,
};
use crate::retry_control::{
    NativeContinuationRetryAttemptCursor, NativeContinuationRetryConflict,
    NativeContinuationRetryDirective, NativeContinuationRetryEvidence,
};

/// Positive bounds for one retention-journal reconciliation retry loop.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationFileBlobPairRetentionReconcileRequest {
    maximum_attempts: NonZeroUsize,
    maximum_bytes: NonZeroUsize,
}

impl NativeContinuationFileBlobPairRetentionReconcileRequest {
    /// Binds the positive journal byte limit and retry attempt budget.
    #[must_use]
    pub const fn new(
        maximum_bytes: NonZeroUsize,
        maximum_attempts: NonZeroUsize,
    ) -> Self {
        Self {
            maximum_attempts,
            maximum_bytes,
        }
    }
}

/// Terminal evidence from caller-directed retention reconciliation retry.
pub type NativeContinuationFileBlobPairRetentionReconcile<DurabilityError> =
    NativeContinuationRetryEvidence<
        NativeContinuationFileBlobPairRetentionJournalCas<DurabilityError>,
    >;

/// Why caller-directed retention reconciliation stopped before a CAS outcome.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationFileBlobPairRetentionReconcileError<
    StoreError,
    ReconciliationError,
> {
    /// Typed durable journal orchestration failed closed.
    Journal(NativeContinuationFileBlobPairRetentionJournalError<StoreError>),
    /// Caller reconciliation rejected the observed current retention state.
    Reconciliation(ReconciliationError),
}

/// Reconciliation result specialized to one conditional durable blob store.
pub type NativeContinuationFileBlobPairRetentionReconcileStoreResult<
    Store,
    ReconciliationError,
> = Result<
    NativeContinuationFileBlobPairRetentionReconcile<
        <Store as NativeContinuationDurableBlobStore>::DurabilityError,
    >,
    NativeContinuationFileBlobPairRetentionReconcileError<
        <Store as NativeContinuationBlobStore>::Error,
        ReconciliationError,
    >,
>;

type Retention =
    NativeContinuationBlobPairRetention<NativeContinuationFileBlobPairRevision>;

type JournalCas<DurabilityError> =
    NativeContinuationFileBlobPairRetentionJournalCas<DurabilityError>;

/// Reconciles exact retention against current typed state and retries
/// conflicts.
///
/// The callback owns all retention-selection semantics. It is invoked once
/// before each CAS attempt with the exact typed state observed for that
/// attempt; `None` means no journal exists, while `Some(empty)` is an explicit
/// empty journal.
///
/// # Errors
///
/// Returns typed journal load/CAS failure or caller reconciliation failure.
/// Durable publication, committed durability failure, and exhausted conflict
/// budget are successful terminal evidence rather than errors.
pub fn reconcile_file_blob_pair_retention_journal_durably_with_retries<
    Store,
    Reconcile,
    ReconciliationError,
>(
    store: &mut Store,
    maximum_bytes: NonZeroUsize,
    maximum_attempts: NonZeroUsize,
    reconcile: Reconcile,
) -> NativeContinuationFileBlobPairRetentionReconcileStoreResult<
    Store,
    ReconciliationError,
>
where
    Store: NativeContinuationConditionalBlobStore
        + NativeContinuationDurableBlobStore,
    Reconcile:
        FnMut(Option<&Retention>) -> Result<Retention, ReconciliationError>,
{
    reconcile_file_blob_pair_retention_with_retry_control(
        store,
        NativeContinuationFileBlobPairRetentionReconcileRequest::new(
            maximum_bytes,
            maximum_attempts,
        ),
        reconcile,
        |_conflict| NativeContinuationRetryDirective::Continue,
    )
}

/// Reconciles retention and lets the caller gate every retryable conflict.
///
/// The control callback runs only after a retryable conflict and while another
/// attempt remains in the positive budget. `Stop` preserves the typed conflict;
/// `Continue` invokes caller reconciliation again with that exact current
/// state. This layer performs no clock read, wait, backoff, or fairness action.
///
/// # Errors
///
/// Returns typed journal load/CAS failure or caller reconciliation failure.
/// Durable publication and committed durability failure stop immediately.
pub fn reconcile_file_blob_pair_retention_with_retry_control<
    Store,
    Reconcile,
    Control,
    ReconciliationError,
>(
    store: &mut Store,
    request: NativeContinuationFileBlobPairRetentionReconcileRequest,
    mut reconcile: Reconcile,
    mut control: Control,
) -> NativeContinuationFileBlobPairRetentionReconcileStoreResult<
    Store,
    ReconciliationError,
>
where
    Store: NativeContinuationConditionalBlobStore
        + NativeContinuationDurableBlobStore,
    Reconcile:
        FnMut(Option<&Retention>) -> Result<Retention, ReconciliationError>,
    Control: FnMut(
        NativeContinuationRetryConflict,
    ) -> NativeContinuationRetryDirective,
{
    let load =
        restore_file_blob_pair_retention_journal(store, request.maximum_bytes)
            .map_err(
                NativeContinuationFileBlobPairRetentionReconcileError::Journal,
            )?;
    let mut current = match load {
        NativeContinuationFileBlobPairRetentionJournalLoad::Missing => None,
        NativeContinuationFileBlobPairRetentionJournalLoad::Present {
            retention,
        } => Some(retention),
    };
    let mut attempts = NativeContinuationRetryAttemptCursor::after_first(
        request.maximum_attempts,
    );
    loop {
        let replacement = reconcile(current.as_ref()).map_err(
            NativeContinuationFileBlobPairRetentionReconcileError::
                Reconciliation,
        )?;
        let attempt_outcome =
            compare_and_swap_file_blob_pair_retention_journal_durably(
                store,
                current.as_ref(),
                &replacement,
                request.maximum_bytes,
            )
            .map_err(
                NativeContinuationFileBlobPairRetentionReconcileError::Journal,
            )?;
        match attempt_outcome {
            JournalCas::Conflict { current: next_current }
                if attempts.can_retry() =>
            {
                if control(attempts.conflict())
                    == NativeContinuationRetryDirective::Stop
                    || !attempts.advance()
                {
                    return Ok(NativeContinuationRetryEvidence::new(
                        attempts.completed_attempts(),
                        JournalCas::Conflict { current: next_current },
                    ));
                }
                current = next_current;
            },
            terminal @ (JournalCas::Conflict { .. }
            | JournalCas::Durable { .. }
            | JournalCas::Published { .. }) => {
                return Ok(NativeContinuationRetryEvidence::new(
                    attempts.completed_attempts(),
                    terminal,
                ));
            },
        }
    }
}
