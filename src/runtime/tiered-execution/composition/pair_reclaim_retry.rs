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
//   - Caller-directed bounded retry around guarded retention/reclamation
//     transitions.
// - Must-Not:
//   - Choose retention merge policy, retry committed journal state, sleep, or
//     infer chronology.
// - Allows:
//   - Inputs: shared coordinator/adapters, positive byte/attempt bounds, caller
//     reconciliation callback.
//   - Outputs: exact transition attempt count plus terminal transition outcome.
//   - Side effects: one initial typed journal load and at most the selected
//     number of guarded journal/reclamation transitions.
// - Split-When:
//   - Backoff, cancellation, fairness, or automatic retention policy gains
//     authority.
// - Merge-When:
//   - Another composition owner performs this exact guarded retry loop.
// - Summary:
//   - Retries only prepublication journal conflict after caller reconciliation.
// - Description:
//   - Every committed journal or cleanup outcome stops immediately.
// - Usage:
//   - Use only when the caller can reconcile each exact typed current journal.
// - Defaults:
//   - No policy exists beyond the positive caller-selected attempt budget.
//

//! Caller-owned reconciliation around guarded retention/reclamation conflicts.

use std::num::NonZeroUsize;

use crate::blob_pair_retention::NativeContinuationBlobPairRetention;
use crate::file_blob_pair_store::{
    NativeContinuationFileBlobPairRevision, NativeContinuationFileBlobPairStore,
};
use crate::file_blob_store::{
    NativeContinuationFileBlobStore, NativeContinuationFileBlobStoreError,
};
use crate::file_coordination::NativeContinuationFileCoordination;
use crate::pair_retention_journal::{
    NativeContinuationFileBlobPairRetentionJournalError,
    NativeContinuationFileBlobPairRetentionJournalLoad,
    restore_file_blob_pair_retention_journal,
};
use crate::pair_retention_reclamation_transition::{
    NativeContinuationFileBlobPairJournalTransition,
    NativeContinuationFileBlobPairJournalTransitionError,
    NativeContinuationFileBlobPairJournalTransitionRequest,
    transition_file_blob_pair_retention_and_reclaim,
};
use crate::retry_control::{
    NativeContinuationRetryAttemptCursor, NativeContinuationRetryConflict,
    NativeContinuationRetryDirective,
};

type Retention =
    NativeContinuationBlobPairRetention<NativeContinuationFileBlobPairRevision>;

type TransitionRetentionLoadResult = Result<
    Option<Retention>,
    NativeContinuationFileBlobPairRetentionJournalError<
        NativeContinuationFileBlobStoreError,
    >,
>;

/// Shared filesystem state participating in guarded transition retry.
#[derive(Debug)]
pub struct NativeContinuationFileBlobPairJournalTransitionRetryContext<'state> {
    coordination: &'state NativeContinuationFileCoordination,
    journal: &'state mut NativeContinuationFileBlobStore,
    pair: &'state mut NativeContinuationFileBlobPairStore,
}

impl<'state>
    NativeContinuationFileBlobPairJournalTransitionRetryContext<'state>
{
    /// Binds one shared coordinator and both coordinated filesystem adapters.
    #[must_use]
    pub const fn new(
        coordination: &'state NativeContinuationFileCoordination,
        journal: &'state mut NativeContinuationFileBlobStore,
        pair: &'state mut NativeContinuationFileBlobPairStore,
    ) -> Self {
        Self {
            coordination,
            journal,
            pair,
        }
    }
}

/// Positive limits for one caller-directed guarded transition retry loop.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationFileBlobPairJournalTransitionRetryRequest {
    maximum_attempts: NonZeroUsize,
    maximum_bytes: NonZeroUsize,
}

impl NativeContinuationFileBlobPairJournalTransitionRetryRequest {
    /// Binds the positive journal byte limit and transition attempt budget.
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

/// Terminal evidence from caller-directed guarded transition retry.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationFileBlobPairJournalTransitionRetry {
    attempts: usize,
    outcome: NativeContinuationFileBlobPairJournalTransition,
}

/// Why caller-directed guarded transition retry stopped before an outcome.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationFileBlobPairJournalTransitionRetryError<
    ReconciliationError,
> {
    /// Initial typed durable journal restore failed closed.
    Journal(
        NativeContinuationFileBlobPairRetentionJournalError<
            NativeContinuationFileBlobStoreError,
        >,
    ),
    /// Caller reconciliation rejected the exact typed current state.
    Reconciliation(ReconciliationError),
    /// One guarded transition failed before journal publication.
    Transition(NativeContinuationFileBlobPairJournalTransitionError),
}

impl NativeContinuationFileBlobPairJournalTransitionRetry {
    /// Returns the exact number of guarded transition attempts performed.
    #[must_use]
    pub const fn attempts(&self) -> usize {
        self.attempts
    }

    /// Consumes retry evidence and returns the terminal transition outcome.
    #[must_use]
    pub fn into_outcome(
        self,
    ) -> NativeContinuationFileBlobPairJournalTransition {
        self.outcome
    }

    /// Borrows the terminal transition outcome.
    #[must_use]
    pub const fn outcome(
        &self,
    ) -> &NativeContinuationFileBlobPairJournalTransition {
        &self.outcome
    }
}

const fn transition_retry_evidence(
    attempts: usize,
    outcome: NativeContinuationFileBlobPairJournalTransition,
) -> NativeContinuationFileBlobPairJournalTransitionRetry {
    NativeContinuationFileBlobPairJournalTransitionRetry { attempts, outcome }
}

fn restore_transition_retry_retention(
    journal: &mut NativeContinuationFileBlobStore,
    maximum_bytes: NonZeroUsize,
) -> TransitionRetentionLoadResult {
    let load =
        restore_file_blob_pair_retention_journal(journal, maximum_bytes)?;
    Ok(match load {
        NativeContinuationFileBlobPairRetentionJournalLoad::Missing => None,
        NativeContinuationFileBlobPairRetentionJournalLoad::Present {
            retention,
        } => Some(retention),
    })
}

/// Reconciles exact retention and retries guarded transitions only on conflict.
///
/// The callback owns all retention-selection semantics and receives the exact
/// typed current journal observed for each attempt. `None` means missing state;
/// `Some(empty)` remains an explicit empty journal.
///
/// # Errors
///
/// Returns initial journal restore failure, caller reconciliation failure, or a
/// prepublication guarded transition failure. Every committed journal/cleanup
/// state and an exhausted final conflict are successful terminal evidence.
pub fn reconcile_file_blob_pair_retention_and_reclaim_with_retries<
    Reconcile,
    ReconciliationError,
>(
    context: NativeContinuationFileBlobPairJournalTransitionRetryContext<'_>,
    request: NativeContinuationFileBlobPairJournalTransitionRetryRequest,
    reconcile: Reconcile,
) -> Result<
    NativeContinuationFileBlobPairJournalTransitionRetry,
    NativeContinuationFileBlobPairJournalTransitionRetryError<
        ReconciliationError,
    >,
>
where
    Reconcile:
        FnMut(Option<&Retention>) -> Result<Retention, ReconciliationError>,
{
    reconcile_file_blob_pair_retention_reclaim_with_control(
        context,
        request,
        reconcile,
        |_conflict| NativeContinuationRetryDirective::Continue,
    )
}

/// Reconciles retention and lets the caller gate every retryable conflict.
///
/// The control callback runs only when another attempt remains in the positive
/// attempt budget. It runs after the conflict attempt has released its
/// filesystem guard and before the next reconciliation callback. The runtime
/// performs no wait, clock read, fairness action, or cancellation inference.
///
/// # Errors
///
/// Returns the same initial journal, reconciliation, and prepublication
/// transition failures as the default retry wrapper. A caller `Stop` directive
/// returns the current conflict as successful terminal evidence.
pub fn reconcile_file_blob_pair_retention_reclaim_with_control<
    Reconcile,
    Control,
    ReconciliationError,
>(
    context: NativeContinuationFileBlobPairJournalTransitionRetryContext<'_>,
    request: NativeContinuationFileBlobPairJournalTransitionRetryRequest,
    mut reconcile: Reconcile,
    mut control: Control,
) -> Result<
    NativeContinuationFileBlobPairJournalTransitionRetry,
    NativeContinuationFileBlobPairJournalTransitionRetryError<
        ReconciliationError,
    >,
>
where
    Reconcile:
        FnMut(Option<&Retention>) -> Result<Retention, ReconciliationError>,
    Control: FnMut(
        NativeContinuationRetryConflict,
    ) -> NativeContinuationRetryDirective,
{
    use NativeContinuationFileBlobPairJournalTransition as Transition;
    use NativeContinuationFileBlobPairJournalTransitionRetryError as RetryError;

    let NativeContinuationFileBlobPairJournalTransitionRetryContext {
        coordination,
        journal,
        pair,
    } = context;
    let mut current =
        restore_transition_retry_retention(journal, request.maximum_bytes)
            .map_err(RetryError::Journal)?;
    let mut attempts = NativeContinuationRetryAttemptCursor::after_first(
        request.maximum_attempts,
    );
    loop {
        let replacement =
            reconcile(current.as_ref()).map_err(RetryError::Reconciliation)?;
        let outcome = transition_file_blob_pair_retention_and_reclaim(
            coordination,
            journal,
            pair,
            NativeContinuationFileBlobPairJournalTransitionRequest::new(
                current.as_ref(),
                &replacement,
                request.maximum_bytes,
            ),
        )
        .map_err(RetryError::Transition)?;
        match outcome {
            Transition::Conflict { current: next_current }
                if attempts.can_retry() =>
            {
                let directive = control(attempts.conflict());
                if directive == NativeContinuationRetryDirective::Stop
                    || !attempts.advance()
                {
                    return Ok(transition_retry_evidence(
                        attempts.completed_attempts(),
                        Transition::Conflict { current: next_current },
                    ));
                }
                current = next_current;
            },
            terminal @ (Transition::Conflict { .. }
            | Transition::JournalPublished { .. }
            | Transition::Reclaimed { .. }
            | Transition::ReclamationRejected { .. }) => {
                return Ok(transition_retry_evidence(
                    attempts.completed_attempts(),
                    terminal,
                ));
            },
        }
    }
}
