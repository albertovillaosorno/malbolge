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
//   - Filesystem retention-journal authority for one guarded reclamation pass.
// - Must-Not:
//   - Select revisions, infer chronology, mutate journal policy, or acquire two
//     independent lock domains.
// - Allows:
//   - Inputs: one shared filesystem coordinator, one journal blob adapter, one
//     pair adapter, and one positive journal byte bound.
//   - Outputs: missing-journal no-op or exact reclamation evidence.
//   - Side effects: one exclusive lock acquisition, one journal read, and
//     optional generation reclamation under that same guard.
// - Split-When:
//   - Journal mutation and reclamation become one atomic write transaction.
// - Merge-When:
//   - Another composition owner performs the same guarded journal reclamation.
// - Summary:
//   - Reclaims pair generations from one retention journal under one lock.
// - Description:
//   - Missing journal never aliases an explicit empty retention journal.
// - Usage:
//   - Configure both file adapters with the same coordinator before calling.
// - Defaults:
//   - Missing journal performs no deletion; present empty journal preserves
//     only the current pair generation.
//

//! Guarded filesystem pair reclamation driven by exact durable retention.

use std::num::NonZeroUsize;

use crate::file_blob_pair_store::{
    NativeContinuationFileBlobPairReclamation,
    NativeContinuationFileBlobPairReclamationError,
    NativeContinuationFileBlobPairRetentionCodecError,
    NativeContinuationFileBlobPairStore, decode_file_blob_pair_retention,
};
use crate::file_blob_store::{
    NativeContinuationFileBlobStore, NativeContinuationFileBlobStoreError,
};
use crate::file_coordination::{
    NativeContinuationFileCoordination, NativeContinuationFileCoordinationError,
};

/// Outcome of one guarded journal-driven pair reclamation pass.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationFileBlobPairJournalReclamation {
    /// No journal exists, so no generation deletion was attempted.
    MissingJournal,
    /// Present journal was decoded and used as exact preservation authority.
    Reclaimed {
        /// Exact filesystem reclamation evidence.
        reclamation: NativeContinuationFileBlobPairReclamation,
        /// Number of exact revisions selected by the durable journal.
        retained_revisions: usize,
    },
}

/// Why guarded journal-driven pair reclamation failed closed.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationFileBlobPairJournalReclamationError {
    /// Canonical retention journal bytes were malformed.
    Codec(NativeContinuationFileBlobPairRetentionCodecError),
    /// Acquiring the shared filesystem transaction lock failed.
    Coordination(NativeContinuationFileCoordinationError),
    /// Loading bounded journal bytes failed.
    Journal(NativeContinuationFileBlobStoreError),
    /// Pair generation reclamation failed before or during cleanup.
    Reclamation(NativeContinuationFileBlobPairReclamationError),
}

/// Reclaims pair generations using one present retention journal under one
/// lock.
///
/// Missing journal state is a non-mutating outcome. An explicitly present empty
/// journal is different and authorizes reclamation of every superseded
/// generation not otherwise protected as current.
///
/// # Errors
///
/// Returns coordination, bounded journal read, canonical decoding, or pair
/// reclamation failure. The pair reclaimer retains its committed
/// partial-cleanup evidence when deletion has already occurred.
pub fn reclaim_file_blob_pair_from_retention_journal(
    coordination: &NativeContinuationFileCoordination,
    journal: &NativeContinuationFileBlobStore,
    pair: &mut NativeContinuationFileBlobPairStore,
    maximum_bytes: NonZeroUsize,
) -> Result<
    NativeContinuationFileBlobPairJournalReclamation,
    NativeContinuationFileBlobPairJournalReclamationError,
> {
    let guard = coordination.acquire_exclusive().map_err(
        NativeContinuationFileBlobPairJournalReclamationError::Coordination,
    )?;
    let Some(bytes) = journal.load_prelocked(&guard, maximum_bytes).map_err(
        NativeContinuationFileBlobPairJournalReclamationError::Journal,
    )?
    else {
        return Ok(
            NativeContinuationFileBlobPairJournalReclamation::MissingJournal,
        );
    };
    let revisions = decode_file_blob_pair_retention(&bytes).map_err(
        NativeContinuationFileBlobPairJournalReclamationError::Codec,
    )?;
    let reclamation = pair
        .reclaim_generations_preserving_prelocked(&guard, &revisions)
        .map_err(
            NativeContinuationFileBlobPairJournalReclamationError::Reclamation,
        )?;
    Ok(
        NativeContinuationFileBlobPairJournalReclamation::Reclaimed {
            reclamation,
            retained_revisions: revisions.len(),
        },
    )
}
