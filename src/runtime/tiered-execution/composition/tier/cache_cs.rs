// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Typed bounded persistence and restoration of cache-trigger cadence
//     cursors.
// - Must-Not:
//   - Choose storage locations, perform CAS, infer scheduling, activate policy,
//     or assign cross-process trigger ownership.
// - Allows:
//   - Inputs: one validated cadence cursor, positive byte bound, and blob
//     store.
//   - Outputs: explicit missing/restored cursor or publication durability
//     evidence.
//   - Side effects: delegated through bounded opaque-blob persistence only.
// - Split-When:
//   - Conditional ownership, migration, or eviction gains independent
//     authority.
// - Merge-When:
//   - One durable trigger-cursor owner subsumes persistence and concurrency.
// - Summary:
//   - Persists canonical cache-trigger cadence without scheduling authority.
// - Description:
//   - Canonical framing is validated after every bounded restore.
// - Usage:
//   - Bind one preconfigured durable blob to caller-owned trigger cadence
//     state.
// - Defaults:
//   - Missing durable cursor state remains explicit and invents no cadence.
//

//! Typed bounded persistence for cache-policy trigger cadence cursors.

use std::num::NonZeroUsize;

use store_port::{
    NativeContinuationBlobStore as BlobStore,
    NativeContinuationDurableBlobStore as DurableBlobStore,
};

use crate::{
    blob_persistence, blob_store as store_port,
    executable_cache_limits_trigger_cadence as trigger,
    executable_cache_limits_trigger_cadence_codec as codec,
};

type BlobDurablePersistence<DurabilityError> =
    blob_persistence::NativeContinuationBlobDurablePersistence<DurabilityError>;
type BlobLoad = blob_persistence::NativeContinuationBlobPersistenceLoad;
type Cursor = trigger::NativeExecutableCacheLimitsTriggerCadence;
type CursorCodecError =
    codec::NativeExecutableCacheLimitsTriggerCadenceCodecError;

type CursorDurablePersistence<DurabilityError> =
    NativeExecutableCacheLimitsTriggerCadenceDurablePersistence<
        DurabilityError,
    >;

/// Cursor publication plus explicit post-publication durability state.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeExecutableCacheLimitsTriggerCadenceDurablePersistence<
    DurabilityError,
> {
    /// Canonical publication and durability confirmation both completed.
    Durable {
        /// Exact committed canonical byte count.
        bytes: usize,
    },
    /// Canonical publication committed, then durability confirmation failed.
    Published {
        /// Exact committed canonical byte count.
        bytes: usize,
        /// Exact post-publication durability failure.
        durability_error: DurabilityError,
    },
}

/// Why typed trigger-cursor persistence failed closed.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeExecutableCacheLimitsTriggerCadencePersistenceError<StoreError> {
    /// Bounded opaque-blob orchestration or outbound store failed.
    Blob(blob_persistence::NativeContinuationBlobPersistenceError<StoreError>),
    /// Canonical trigger-cursor framing or semantics failed on restore.
    Codec(CursorCodecError),
}

/// Result of one bounded trigger-cursor restoration.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeExecutableCacheLimitsTriggerCadencePersistenceLoad {
    /// No durable trigger cursor exists at the configured blob location.
    Missing,
    /// Canonical bytes reconstructed one exact trigger cadence cursor.
    Restored {
        /// Exact canonical byte count returned by the adapter.
        bytes: usize,
        /// Reconstructed caller-owned cadence cursor.
        cadence: Cursor,
    },
}

/// Publication evidence from one successful canonical cursor replacement.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeExecutableCacheLimitsTriggerCadencePersistenceWrite {
    bytes: usize,
}

/// Durable typed cursor result specialized to one store type.
pub type NativeExecutableCacheLimitsTriggerCadenceDurableStoreResult<Store> =
    Result<
        NativeExecutableCacheLimitsTriggerCadenceDurablePersistence<
            <Store as DurableBlobStore>::DurabilityError,
        >,
        NativeExecutableCacheLimitsTriggerCadencePersistenceError<
            <Store as BlobStore>::Error,
        >,
    >;

/// Result of one typed trigger-cursor persistence operation.
pub type NativeExecutableCacheLimitsTriggerCadencePersistenceResult<
    Value,
    StoreError,
> = Result<
    Value,
    NativeExecutableCacheLimitsTriggerCadencePersistenceError<StoreError>,
>;

impl<DurabilityError> CursorDurablePersistence<DurabilityError> {
    /// Returns the exact committed canonical byte count.
    #[must_use]
    pub const fn bytes(&self) -> usize {
        match self {
            Self::Durable { bytes } | Self::Published { bytes, .. } => *bytes,
        }
    }

    /// Returns post-publication durability failure when confirmation failed.
    #[must_use]
    pub const fn durability_error(&self) -> Option<&DurabilityError> {
        match self {
            Self::Durable { .. } => None,
            Self::Published { durability_error, .. } => Some(durability_error),
        }
    }

    /// Reports whether storage explicitly confirmed publication durability.
    #[must_use]
    pub const fn is_durable(&self) -> bool {
        matches!(self, Self::Durable { .. })
    }
}

impl NativeExecutableCacheLimitsTriggerCadencePersistenceWrite {
    /// Returns the exact canonical byte count passed to the outbound store.
    #[must_use]
    pub const fn bytes(self) -> usize {
        self.bytes
    }
}

fn map_durable_persistence<DurabilityError>(
    outcome: BlobDurablePersistence<DurabilityError>,
) -> CursorDurablePersistence<DurabilityError> {
    match outcome {
        BlobDurablePersistence::Durable { write } => {
            CursorDurablePersistence::Durable { bytes: write.bytes() }
        },
        BlobDurablePersistence::Published { durability_error, write } => {
            CursorDurablePersistence::Published {
                bytes: write.bytes(),
                durability_error,
            }
        },
    }
}

/// Persists one exact trigger cadence cursor as canonical bounded bytes.
///
/// # Errors
///
/// Returns byte-limit or outbound-store failure before publication.
pub fn persist_native_executable_cache_limits_trigger_cadence<Store>(
    store: &mut Store,
    cadence: Cursor,
    maximum_bytes: NonZeroUsize,
) -> NativeExecutableCacheLimitsTriggerCadencePersistenceResult<
    NativeExecutableCacheLimitsTriggerCadencePersistenceWrite,
    Store::Error,
>
where
    Store: BlobStore,
{
    let bytes =
        codec::encode_native_executable_cache_limits_trigger_cadence(cadence);
    let write = blob_persistence::persist_blob(store, &bytes, maximum_bytes)
        .map_err(
            NativeExecutableCacheLimitsTriggerCadencePersistenceError::Blob,
        )?;
    Ok(NativeExecutableCacheLimitsTriggerCadencePersistenceWrite {
        bytes: write.bytes(),
    })
}

/// Persists one exact trigger cadence cursor and confirms durability.
///
/// # Errors
///
/// Returns byte-limit or outbound-store failure before publication.
pub fn persist_native_executable_cache_limits_trigger_cadence_durably<Store>(
    store: &mut Store,
    cadence: Cursor,
    maximum_bytes: NonZeroUsize,
) -> NativeExecutableCacheLimitsTriggerCadenceDurableStoreResult<Store>
where
    Store: DurableBlobStore,
{
    let bytes =
        codec::encode_native_executable_cache_limits_trigger_cadence(cadence);
    let outcome =
        blob_persistence::persist_blob_durably(store, &bytes, maximum_bytes)
            .map_err(
                NativeExecutableCacheLimitsTriggerCadencePersistenceError::Blob,
            )?;
    Ok(map_durable_persistence(outcome))
}

/// Restores one exact trigger cadence cursor from canonical bounded bytes.
///
/// # Errors
///
/// Returns store, byte-limit, or codec evidence without inventing missing
/// state.
pub fn restore_native_executable_cache_limits_trigger_cadence<Store>(
    store: &mut Store,
    maximum_bytes: NonZeroUsize,
) -> NativeExecutableCacheLimitsTriggerCadencePersistenceResult<
    NativeExecutableCacheLimitsTriggerCadencePersistenceLoad,
    Store::Error,
>
where
    Store: BlobStore,
{
    let load = blob_persistence::restore_blob(store, maximum_bytes).map_err(
        NativeExecutableCacheLimitsTriggerCadencePersistenceError::Blob,
    )?;
    let BlobLoad::Present { bytes } = load else {
        return Ok(
            NativeExecutableCacheLimitsTriggerCadencePersistenceLoad::Missing,
        );
    };
    let length = bytes.len();
    let cadence =
        codec::decode_native_executable_cache_limits_trigger_cadence(&bytes)
            .map_err(
            NativeExecutableCacheLimitsTriggerCadencePersistenceError::Codec,
        )?;
    Ok(
        NativeExecutableCacheLimitsTriggerCadencePersistenceLoad::Restored {
            bytes: length,
            cadence,
        },
    )
}

#[cfg(test)]
#[path = "../../../../../tests/tiered/cache_cursor_store.rs"]
mod tests;
