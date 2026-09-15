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
//   - Typed durable save/restore of caller-selected filesystem pair retention.
// - Must-Not:
//   - Select revisions, infer chronology, schedule cleanup, or choose paths.
// - Allows:
//   - Inputs: exact retention owner, positive byte bound, configured blob
//     store.
//   - Outputs: missing/present retention or exact durable publication evidence.
//   - Side effects: one delegated blob load or durable replacement per call.
// - Split-When:
//   - Automatic retention or asynchronous journal scheduling gains authority.
// - Merge-When:
//   - Another composition service owns the same typed retention journal.
// - Summary:
//   - Binds canonical file-pair retention bytes to generic blob persistence.
// - Description:
//   - Missing state is explicit; malformed durable bytes fail closed.
// - Usage:
//   - Called only after higher-level code explicitly selects retained
//     revisions.
// - Defaults:
//   - Empty retention is a valid explicit journal, not missing state.
//

//! Typed durable journal orchestration for exact filesystem pair retention.

use std::num::NonZeroUsize;

use crate::blob_pair_retention::NativeContinuationBlobPairRetention;
use crate::blob_persistence::{
    NativeContinuationBlobConditionalDurablePersistence,
    NativeContinuationBlobDurablePersistence,
    NativeContinuationBlobPersistenceError,
    NativeContinuationBlobPersistenceLoad, compare_and_swap_blob_durably,
    persist_blob_durably, restore_blob,
};
use crate::blob_store::{
    NativeContinuationBlobStore, NativeContinuationConditionalBlobStore,
    NativeContinuationDurableBlobStore,
};
use crate::file_blob_pair_store::{
    NativeContinuationFileBlobPairRetentionCodecError,
    NativeContinuationFileBlobPairRevision, decode_file_blob_pair_retention,
    encode_file_blob_pair_retention,
};

/// Typed outcome of one conditional durable retention-journal publication.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationFileBlobPairRetentionJournalCas<DurabilityError> {
    /// Expected canonical retention differed; no publication occurred.
    Conflict {
        /// Exact typed current journal state, or absence, observed by the
        /// store.
        current: Option<
            NativeContinuationBlobPairRetention<
                NativeContinuationFileBlobPairRevision,
            >,
        >,
    },
    /// Conditional publication and durability confirmation both completed.
    Durable {
        /// Exact committed canonical byte count.
        bytes: usize,
    },
    /// Publication committed, then durability confirmation failed.
    Published {
        /// Exact committed canonical byte count.
        bytes: usize,
        /// Exact post-publication durability failure.
        durability_error: DurabilityError,
    },
}

/// Typed durable filesystem pair-retention journal load.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationFileBlobPairRetentionJournalLoad {
    /// No retention journal currently exists.
    Missing,
    /// One canonical exact-retention owner was restored.
    Present {
        /// Exact retained opaque revisions in caller insertion order.
        retention: NativeContinuationBlobPairRetention<
            NativeContinuationFileBlobPairRevision,
        >,
    },
}

/// Why typed filesystem pair-retention journal orchestration failed closed.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationFileBlobPairRetentionJournalError<StoreError> {
    /// Generic bounded blob persistence failed before typed decoding completed.
    Blob(NativeContinuationBlobPersistenceError<StoreError>),
    /// Canonical filesystem pair-retention bytes were invalid.
    Codec(NativeContinuationFileBlobPairRetentionCodecError),
}

/// Typed journal result specialized to one generic blob store.
pub type NativeContinuationFileBlobPairRetentionJournalStoreResult<
    Store,
    Value,
> = Result<
    Value,
    NativeContinuationFileBlobPairRetentionJournalError<
        <Store as NativeContinuationBlobStore>::Error,
    >,
>;

/// Conditional durable journal result specialized to one blob store.
pub type NativeContinuationFileBlobPairRetentionJournalCasStoreResult<Store> =
    NativeContinuationFileBlobPairRetentionJournalStoreResult<
        Store,
        NativeContinuationFileBlobPairRetentionJournalCas<
            <Store as NativeContinuationDurableBlobStore>::DurabilityError,
        >,
    >;

/// Durable typed retention-journal result specialized to one blob store.
pub type NativeContinuationFileBlobPairRetentionJournalDurableStoreResult<
    Store,
> = NativeContinuationFileBlobPairRetentionJournalStoreResult<
    Store,
    NativeContinuationBlobDurablePersistence<
        <Store as NativeContinuationDurableBlobStore>::DurabilityError,
    >,
>;

/// Conditionally persists one exact retention journal and confirms durability.
///
/// # Errors
///
/// Returns canonical encoding/decoding or bounded/store failure. Conflict is
/// typed non-mutating evidence; durability failure after publication remains
/// committed.
pub fn compare_and_swap_file_blob_pair_retention_journal_durably<Store>(
    store: &mut Store,
    expected: Option<
        &NativeContinuationBlobPairRetention<
            NativeContinuationFileBlobPairRevision,
        >,
    >,
    replacement: &NativeContinuationBlobPairRetention<
        NativeContinuationFileBlobPairRevision,
    >,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationFileBlobPairRetentionJournalCasStoreResult<Store>
where
    Store: NativeContinuationConditionalBlobStore
        + NativeContinuationDurableBlobStore,
{
    let expected_bytes = expected
        .map(|retention| encode_file_blob_pair_retention(retention.revisions()))
        .transpose()
        .map_err(NativeContinuationFileBlobPairRetentionJournalError::Codec)?;
    let replacement_bytes = encode_file_blob_pair_retention(
        replacement.revisions(),
    )
    .map_err(NativeContinuationFileBlobPairRetentionJournalError::Codec)?;
    let outcome = compare_and_swap_blob_durably(
        store,
        expected_bytes.as_deref(),
        &replacement_bytes,
        maximum_bytes,
    )
    .map_err(NativeContinuationFileBlobPairRetentionJournalError::Blob)?;
    match outcome {
        NativeContinuationBlobConditionalDurablePersistence::Conflict {
            current,
        } => Ok(NativeContinuationFileBlobPairRetentionJournalCas::Conflict {
            current: current
                .as_deref()
                .map(decode_retention_owner)
                .transpose()
                .map_err(
                    NativeContinuationFileBlobPairRetentionJournalError::Codec,
                )?,
        }),
        NativeContinuationBlobConditionalDurablePersistence::Durable {
            write,
        } => Ok(NativeContinuationFileBlobPairRetentionJournalCas::Durable {
            bytes: write.bytes(),
        }),
        NativeContinuationBlobConditionalDurablePersistence::Published {
            durability_error,
            write,
        } => Ok(
            NativeContinuationFileBlobPairRetentionJournalCas::Published {
                bytes: write.bytes(),
                durability_error,
            },
        ),
    }
}

/// Durably persists one exact retention owner through a configured blob store.
///
/// # Errors
///
/// Returns canonical encoding or prepublication bounded/store failure. A
/// durability-confirmation failure remains committed publication evidence.
pub fn persist_file_blob_pair_retention_journal_durably<Store>(
    store: &mut Store,
    retention: &NativeContinuationBlobPairRetention<
        NativeContinuationFileBlobPairRevision,
    >,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationFileBlobPairRetentionJournalDurableStoreResult<Store>
where
    Store: NativeContinuationDurableBlobStore,
{
    let bytes = encode_file_blob_pair_retention(retention.revisions())
        .map_err(NativeContinuationFileBlobPairRetentionJournalError::Codec)?;
    persist_blob_durably(store, &bytes, maximum_bytes)
        .map_err(NativeContinuationFileBlobPairRetentionJournalError::Blob)
}

/// Restores one bounded exact retention journal.
///
/// # Errors
///
/// Returns bounded/store failure or malformed canonical journal evidence.
pub fn restore_file_blob_pair_retention_journal<Store>(
    store: &mut Store,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationFileBlobPairRetentionJournalStoreResult<
    Store,
    NativeContinuationFileBlobPairRetentionJournalLoad,
>
where
    Store: NativeContinuationBlobStore,
{
    let load = restore_blob(store, maximum_bytes)
        .map_err(NativeContinuationFileBlobPairRetentionJournalError::Blob)?;
    let NativeContinuationBlobPersistenceLoad::Present { bytes } = load else {
        return Ok(NativeContinuationFileBlobPairRetentionJournalLoad::Missing);
    };
    let retention = decode_retention_owner(&bytes)
        .map_err(NativeContinuationFileBlobPairRetentionJournalError::Codec)?;
    Ok(
        NativeContinuationFileBlobPairRetentionJournalLoad::Present {
            retention,
        },
    )
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
