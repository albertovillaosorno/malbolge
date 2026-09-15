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
    NativeContinuationBlobDurablePersistence,
    NativeContinuationBlobPersistenceError,
    NativeContinuationBlobPersistenceLoad, persist_blob_durably, restore_blob,
};
use crate::blob_store::{
    NativeContinuationBlobStore, NativeContinuationDurableBlobStore,
};
use crate::file_blob_pair_store::{
    NativeContinuationFileBlobPairRetentionCodecError,
    NativeContinuationFileBlobPairRevision, decode_file_blob_pair_retention,
    encode_file_blob_pair_retention,
};

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

/// Durable typed retention-journal result specialized to one blob store.
pub type NativeContinuationFileBlobPairRetentionJournalDurableStoreResult<
    Store,
> = NativeContinuationFileBlobPairRetentionJournalStoreResult<
    Store,
    NativeContinuationBlobDurablePersistence<
        <Store as NativeContinuationDurableBlobStore>::DurabilityError,
    >,
>;

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
    let revisions = decode_file_blob_pair_retention(&bytes)
        .map_err(NativeContinuationFileBlobPairRetentionJournalError::Codec)?;
    let mut retention = NativeContinuationBlobPairRetention::new();
    for revision in revisions {
        let _inserted = retention.retain(revision);
    }
    Ok(
        NativeContinuationFileBlobPairRetentionJournalLoad::Present {
            retention,
        },
    )
}
