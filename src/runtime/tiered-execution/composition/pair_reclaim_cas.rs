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
//   - One guarded durable retention-journal transition followed by reclamation.
// - Must-Not:
//   - Infer retention policy, retry conflicts, reorder revisions, or claim
//     rollback after journal publication.
// - Allows:
//   - Inputs: one coordinator, journal store, pair store, expected/replacement
//     retention, and one positive journal byte bound.
//   - Outputs: conflict or exact committed journal/reclamation evidence.
//   - Side effects: one journal CAS, journal durability confirmation, then
//     optional pair reclamation under one exclusive guard.
// - Split-When:
//   - Retry/reconciliation or asynchronous cleanup scheduling gains authority.
// - Merge-When:
//   - Another composition owner performs this exact guarded transition.
// - Summary:
//   - Durably advances retention before deleting superseded pair generations.
// - Description:
//   - Reclamation never starts until the committed journal is durable.
// - Usage:
//   - Call only with journal and pair adapters bound to the same coordinator.
// - Defaults:
//   - Conflict is non-mutating; committed journal failure never implies
//     rollback.
//

//! Guarded durable retention transition followed by pair reclamation.

use std::num::NonZeroUsize;

use crate::blob_pair_retention::NativeContinuationBlobPairRetention;
use crate::blob_store::{
    NativeContinuationBlobConditionalPublication,
    NativeContinuationDurableBlobStore as _,
};
use crate::file_blob_pair_store::{
    NativeContinuationFileBlobPairReclamation,
    NativeContinuationFileBlobPairReclamationError,
    NativeContinuationFileBlobPairRetentionCodecError,
    NativeContinuationFileBlobPairRevision,
    NativeContinuationFileBlobPairStore, decode_file_blob_pair_retention,
    encode_file_blob_pair_retention,
};
use crate::file_blob_store::{
    NativeContinuationFileBlobDurabilityError,
    NativeContinuationFileBlobPrelockedCasRequest,
    NativeContinuationFileBlobStore, NativeContinuationFileBlobStoreError,
};
use crate::file_coordination::{
    NativeContinuationFileCoordination, NativeContinuationFileCoordinationError,
};

/// One guarded retention transition request.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationFileBlobPairJournalTransitionRequest<'state> {
    expected: Option<
        &'state NativeContinuationBlobPairRetention<
            NativeContinuationFileBlobPairRevision,
        >,
    >,
    maximum_bytes: NonZeroUsize,
    replacement: &'state NativeContinuationBlobPairRetention<
        NativeContinuationFileBlobPairRevision,
    >,
}

impl<'state> NativeContinuationFileBlobPairJournalTransitionRequest<'state> {
    /// Binds expected/replacement retention and the positive journal byte
    /// bound.
    #[must_use]
    pub const fn new(
        expected: Option<
            &'state NativeContinuationBlobPairRetention<
                NativeContinuationFileBlobPairRevision,
            >,
        >,
        replacement: &'state NativeContinuationBlobPairRetention<
            NativeContinuationFileBlobPairRevision,
        >,
        maximum_bytes: NonZeroUsize,
    ) -> Self {
        Self {
            expected,
            maximum_bytes,
            replacement,
        }
    }
}

/// Outcome of one guarded durable journal transition plus reclamation.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationFileBlobPairJournalTransition {
    /// Expected journal differed; no publication or reclamation occurred.
    Conflict {
        /// Exact typed current journal state, or absence.
        current: Option<
            NativeContinuationBlobPairRetention<
                NativeContinuationFileBlobPairRevision,
            >,
        >,
    },
    /// Journal committed, but its directory durability confirmation failed.
    JournalPublished {
        /// Exact committed canonical journal byte count.
        bytes: usize,
        /// Exact post-publication journal durability failure.
        durability_error: NativeContinuationFileBlobDurabilityError,
    },
    /// Journal is durable and reclamation returned committed cleanup evidence.
    Reclaimed {
        /// Exact durably committed canonical journal byte count.
        bytes: usize,
        /// Exact cleanup and cleanup-durability evidence.
        reclamation: NativeContinuationFileBlobPairReclamation,
    },
    /// Journal is durable, but reclamation was rejected before deletion.
    ReclamationRejected {
        /// Exact durably committed canonical journal byte count.
        bytes: usize,
        /// Exact pre-deletion reclamation rejection.
        error: NativeContinuationFileBlobPairReclamationError,
    },
}

/// Why one guarded journal transition failed before publication.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationFileBlobPairJournalTransitionError {
    /// Expected or replacement canonical bytes exceed the positive bound.
    ByteLimit {
        /// Positive configured journal byte bound.
        maximum_bytes: NonZeroUsize,
        /// Exact canonical byte count that exceeded the bound.
        observed_bytes: usize,
    },
    /// Canonical retention encoding or conflict decoding failed closed.
    Codec(NativeContinuationFileBlobPairRetentionCodecError),
    /// Acquiring the shared filesystem coordination lock failed.
    Coordination(NativeContinuationFileCoordinationError),
    /// Journal CAS failed before publication completed.
    Journal(NativeContinuationFileBlobStoreError),
}

/// Durably transitions the retention journal, then reclaims under the same
/// lock.
///
/// Journal durability is confirmed before any generation deletion. Reclamation
/// rejection after that point is returned as committed journal evidence, not as
/// rollback.
///
/// # Errors
///
/// Returns only canonical admission/decoding, coordination, or prepublication
/// journal failure. Conflict and every postpublication state are outcomes.
pub fn transition_file_blob_pair_retention_and_reclaim(
    coordination: &NativeContinuationFileCoordination,
    journal: &mut NativeContinuationFileBlobStore,
    pair: &mut NativeContinuationFileBlobPairStore,
    request: NativeContinuationFileBlobPairJournalTransitionRequest<'_>,
) -> Result<
    NativeContinuationFileBlobPairJournalTransition,
    NativeContinuationFileBlobPairJournalTransitionError,
> {
    use NativeContinuationFileBlobPairJournalTransition as Transition;
    use NativeContinuationFileBlobPairJournalTransitionError as TransitionError;

    let expected_bytes = request
        .expected
        .map(|retention| encode_file_blob_pair_retention(retention.revisions()))
        .transpose()
        .map_err(TransitionError::Codec)?;
    let replacement_bytes =
        encode_file_blob_pair_retention(request.replacement.revisions())
            .map_err(TransitionError::Codec)?;
    if let Some(expected) = &expected_bytes {
        admit_byte_limit(expected.len(), request.maximum_bytes)?;
    }
    admit_byte_limit(replacement_bytes.len(), request.maximum_bytes)?;
    let guard = coordination
        .acquire_exclusive()
        .map_err(TransitionError::Coordination)?;
    let publication = journal
        .compare_and_swap_prelocked(
            &guard,
            NativeContinuationFileBlobPrelockedCasRequest::new(
                expected_bytes.as_deref(),
                &replacement_bytes,
                request.maximum_bytes,
            ),
        )
        .map_err(TransitionError::Journal)?;
    match publication {
        NativeContinuationBlobConditionalPublication::Conflict { current } => {
            return Ok(Transition::Conflict {
                current: current
                    .as_deref()
                    .map(decode_retention_owner)
                    .transpose()
                    .map_err(TransitionError::Codec)?,
            });
        },
        NativeContinuationBlobConditionalPublication::Published => {},
    }
    let bytes = replacement_bytes.len();
    if let Err(durability_error) = journal.confirm_durability() {
        return Ok(Transition::JournalPublished { bytes, durability_error });
    }
    match pair.reclaim_generations_preserving_prelocked(
        &guard,
        request.replacement.revisions(),
    ) {
        Ok(reclamation) => Ok(Transition::Reclaimed { bytes, reclamation }),
        Err(error) => Ok(Transition::ReclamationRejected { bytes, error }),
    }
}

const fn admit_byte_limit(
    observed_bytes: usize,
    maximum_bytes: NonZeroUsize,
) -> Result<(), NativeContinuationFileBlobPairJournalTransitionError> {
    if observed_bytes <= maximum_bytes.get() {
        Ok(())
    } else {
        Err(
            NativeContinuationFileBlobPairJournalTransitionError::ByteLimit {
                maximum_bytes,
                observed_bytes,
            },
        )
    }
}

fn decode_retention_owner(
    bytes: &[u8],
) -> Result<
    NativeContinuationBlobPairRetention<NativeContinuationFileBlobPairRevision>,
    NativeContinuationFileBlobPairRetentionCodecError,
> {
    let revisions = decode_file_blob_pair_retention(bytes)?;
    let mut retention = NativeContinuationBlobPairRetention::new();
    for revision in revisions {
        let _inserted = retention.retain(revision);
    }
    Ok(retention)
}
