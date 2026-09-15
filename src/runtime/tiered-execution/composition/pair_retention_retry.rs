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
// - Allows:
//   - Inputs: configured conditional durable blob store, positive byte/attempt
//     bounds, caller reconciliation callback.
//   - Outputs: exact attempt count plus terminal typed CAS outcome.
//   - Side effects: one initial bounded load and at most the caller-selected
//     number of conditional durable publications.
// - Split-When:
//   - Backoff, cancellation, fairness, or automatic retention policy gains
//     authority.
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

/// Terminal evidence from caller-directed retention reconciliation retry.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeContinuationFileBlobPairRetentionReconcile<DurabilityError> {
    attempts: usize,
    outcome: NativeContinuationFileBlobPairRetentionJournalCas<DurabilityError>,
}

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

impl<DurabilityError>
    NativeContinuationFileBlobPairRetentionReconcile<DurabilityError>
{
    /// Returns the exact number of conditional publication attempts performed.
    #[must_use]
    pub const fn attempts(&self) -> usize {
        self.attempts
    }

    /// Consumes the retry evidence and returns the terminal typed CAS outcome.
    #[must_use]
    pub fn into_outcome(
        self,
    ) -> NativeContinuationFileBlobPairRetentionJournalCas<DurabilityError>
    {
        self.outcome
    }

    /// Returns the terminal typed CAS outcome.
    #[must_use]
    pub const fn outcome(
        &self,
    ) -> &NativeContinuationFileBlobPairRetentionJournalCas<DurabilityError>
    {
        &self.outcome
    }
}

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
    mut reconcile: Reconcile,
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
    let load = restore_file_blob_pair_retention_journal(store, maximum_bytes)
        .map_err(
        NativeContinuationFileBlobPairRetentionReconcileError::Journal,
    )?;
    let mut current = match load {
        NativeContinuationFileBlobPairRetentionJournalLoad::Missing => None,
        NativeContinuationFileBlobPairRetentionJournalLoad::Present {
            retention,
        } => Some(retention),
    };
    let maximum_attempt_count = maximum_attempts.get();
    let mut attempts = 0usize;
    loop {
        attempts = attempts.saturating_add(1);
        let replacement = reconcile(current.as_ref()).map_err(
            NativeContinuationFileBlobPairRetentionReconcileError::
                Reconciliation,
        )?;
        let attempt_outcome =
            compare_and_swap_file_blob_pair_retention_journal_durably(
                store,
                current.as_ref(),
                &replacement,
                maximum_bytes,
            )
            .map_err(
                NativeContinuationFileBlobPairRetentionReconcileError::Journal,
            )?;
        match attempt_outcome {
            JournalCas::Conflict { current: next_current }
                if attempts < maximum_attempt_count =>
            {
                current = next_current;
            },
            terminal @ (JournalCas::Conflict { .. }
            | JournalCas::Durable { .. }
            | JournalCas::Published { .. }) => {
                return Ok(NativeContinuationFileBlobPairRetentionReconcile {
                    attempts,
                    outcome: terminal,
                });
            },
        }
    }
}
