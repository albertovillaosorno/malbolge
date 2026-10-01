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
//   - Typed bounded persistence and explicit eviction of cache-limit policy.
// - Must-Not:
//   - Persist executable mappings, FIFO entries, usage, native keys, or choose
//     storage locations.
// - Allows:
//   - Inputs: immutable cache limits, positive byte bound, and one blob store.
//   - Outputs: explicit missing/restored limits, publication, or removal
//     evidence.
//   - Side effects: delegated through bounded opaque-blob persistence only.
// - Split-When:
//   - Cache manifest migration, eviction journals, or concurrent ownership gain
//     independent authority.
// - Merge-When:
//   - One durable executable-cache policy owner subsumes limit persistence.
// - Summary:
//   - Persists or evicts cache limits without granting executable authority.
// - Description:
//   - Canonical limit framing is validated before publication and after
//     restore.
// - Usage:
//   - Bind one preconfigured durable blob to future executable-cache policy.
// - Defaults:
//   - Missing durable limits are explicit and never invent cache configuration.
//

//! Typed bounded persistence and eviction for executable-cache limit policy.

use std::num::NonZeroUsize;

use store_port::{
    NativeContinuationBlobStore as BlobStore,
    NativeContinuationDurableBlobStore as DurableBlobStore,
    NativeContinuationRemovableBlobStore as RemovableBlobStore,
};

use crate::execution_native::{
    NativeExecutableSequenceCacheLimits,
    NativeExecutableSequenceCacheLimitsCodecError,
    decode_native_executable_sequence_cache_limits,
    encode_native_executable_sequence_cache_limits,
};
use crate::{blob_persistence, blob_store as store_port};

type BlobDurablePersistence<DurabilityError> =
    blob_persistence::NativeContinuationBlobDurablePersistence<DurabilityError>;
type BlobLoad = blob_persistence::NativeContinuationBlobPersistenceLoad;

/// Durable removal state for one cache-limit policy blob.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeExecutableSequenceCacheLimitsDurableRemoval<DurabilityError> {
    /// Removal committed and durability confirmation completed.
    Durable,
    /// No durable cache-limit policy existed.
    Missing,
    /// Removal committed, then durability confirmation failed.
    Removed {
        /// Exact post-removal durability failure.
        durability_error: DurabilityError,
    },
}

/// Cache-limit publication plus explicit post-publication durability state.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeExecutableSequenceCacheLimitsDurablePersistence<DurabilityError>
{
    /// Canonical publication and durability confirmation both completed.
    Durable {
        /// Exact typed publication evidence.
        write: NativeExecutableSequenceCacheLimitsPersistenceWrite,
    },
    /// Canonical publication committed, but durability confirmation failed.
    Published {
        /// Exact post-publication durability failure.
        durability_error: DurabilityError,
        /// Exact typed publication evidence.
        write: NativeExecutableSequenceCacheLimitsPersistenceWrite,
    },
}

/// Why one typed executable-cache limit persistence operation failed closed.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeExecutableSequenceCacheLimitsPersistenceError<StoreError> {
    /// Bounded opaque-blob orchestration or its outbound store failed.
    Blob(blob_persistence::NativeContinuationBlobPersistenceError<StoreError>),
    /// Canonical executable-cache limit framing or semantics failed.
    Codec(NativeExecutableSequenceCacheLimitsCodecError),
}

/// Result of one bounded executable-cache limit restoration.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeExecutableSequenceCacheLimitsPersistenceLoad {
    /// No durable cache-limit policy exists at the configured location.
    Missing,
    /// Canonical bytes reconstructed exact executable-cache limits.
    Restored {
        /// Exact canonical byte count returned by the adapter.
        bytes: usize,
        /// Reconstructed caller-owned cache limits.
        limits: NativeExecutableSequenceCacheLimits,
    },
}

/// Publication evidence from one successful canonical limit replacement.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeExecutableSequenceCacheLimitsPersistenceWrite {
    bytes: usize,
}

/// Result of typed limit publication plus durability confirmation.
pub type NativeExecutableSequenceCacheLimitsDurablePersistenceResult<
    StoreError,
    DurabilityError,
> = Result<
    NativeExecutableSequenceCacheLimitsDurablePersistence<DurabilityError>,
    NativeExecutableSequenceCacheLimitsPersistenceError<StoreError>,
>;

/// Durable cache-limit removal result specialized to one store type.
pub type NativeExecutableSequenceCacheLimitsDurableRemovalStoreResult<Store> =
    Result<
        NativeExecutableSequenceCacheLimitsDurableRemoval<
            <Store as DurableBlobStore>::DurabilityError,
        >,
        NativeExecutableSequenceCacheLimitsPersistenceError<
            <Store as BlobStore>::Error,
        >,
    >;

/// Durable typed limit result specialized to one store type.
pub type NativeExecutableSequenceCacheLimitsDurableStoreResult<Store> =
    NativeExecutableSequenceCacheLimitsDurablePersistenceResult<
        <Store as BlobStore>::Error,
        <Store as DurableBlobStore>::DurabilityError,
    >;

/// Result of one typed executable-cache limit persistence operation.
pub type NativeExecutableSequenceCacheLimitsPersistenceResult<
    Value,
    StoreError,
> = Result<
    Value,
    NativeExecutableSequenceCacheLimitsPersistenceError<StoreError>,
>;

impl<DurabilityError>
    NativeExecutableSequenceCacheLimitsDurableRemoval<DurabilityError>
{
    /// Returns post-removal durability failure when confirmation failed.
    #[must_use]
    pub const fn durability_error(&self) -> Option<&DurabilityError> {
        match self {
            Self::Removed { durability_error } => Some(durability_error),
            Self::Durable | Self::Missing => None,
        }
    }

    /// Reports whether a durable publication was actually removed.
    #[must_use]
    pub const fn is_removed(&self) -> bool {
        matches!(self, Self::Durable | Self::Removed { .. })
    }
}

impl<DurabilityError>
    NativeExecutableSequenceCacheLimitsDurablePersistence<DurabilityError>
{
    /// Returns the exact committed canonical byte count.
    #[must_use]
    pub const fn bytes(&self) -> usize {
        match self {
            Self::Durable { write } | Self::Published { write, .. } => {
                write.bytes()
            },
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

impl NativeExecutableSequenceCacheLimitsPersistenceWrite {
    /// Returns the exact canonical byte count passed to the outbound store.
    #[must_use]
    pub const fn bytes(self) -> usize {
        self.bytes
    }
}

fn map_durable_persistence<DurabilityError>(
    outcome: BlobDurablePersistence<DurabilityError>,
) -> NativeExecutableSequenceCacheLimitsDurablePersistence<DurabilityError> {
    match outcome {
        BlobDurablePersistence::Durable { write } => {
            NativeExecutableSequenceCacheLimitsDurablePersistence::Durable {
                write: NativeExecutableSequenceCacheLimitsPersistenceWrite {
                    bytes: write.bytes(),
                },
            }
        },
        BlobDurablePersistence::Published { durability_error, write } => {
            NativeExecutableSequenceCacheLimitsDurablePersistence::Published {
                durability_error,
                write: NativeExecutableSequenceCacheLimitsPersistenceWrite {
                    bytes: write.bytes(),
                },
            }
        },
    }
}

/// Durably removes the cache-limit policy at the configured blob location.
///
/// Missing policy is a successful no-op. Once removal commits, a later
/// durability-confirmation failure remains committed absence evidence.
///
/// # Errors
///
/// Returns outbound coordination or removal failure before absence commits.
pub fn evict_native_executable_sequence_cache_limits_durably<Store>(
    store: &mut Store,
) -> NativeExecutableSequenceCacheLimitsDurableRemovalStoreResult<Store>
where
    Store: DurableBlobStore + RemovableBlobStore,
{
    let outcome = blob_persistence::remove_blob_durably(store)
        .map_err(NativeExecutableSequenceCacheLimitsPersistenceError::Blob)?;
    match outcome {
        blob_persistence::NativeContinuationBlobDurableRemoval::Durable => {
            Ok(NativeExecutableSequenceCacheLimitsDurableRemoval::Durable)
        },
        blob_persistence::NativeContinuationBlobDurableRemoval::Missing => {
            Ok(NativeExecutableSequenceCacheLimitsDurableRemoval::Missing)
        },
        blob_persistence::NativeContinuationBlobDurableRemoval::Removed {
            durability_error,
        } => Ok(NativeExecutableSequenceCacheLimitsDurableRemoval::Removed {
            durability_error,
        }),
    }
}

/// Persists one exact executable-cache limit policy as canonical bounded bytes.
///
/// # Errors
///
/// Returns codec, byte-limit, or outbound-store failure before publication.
pub fn persist_native_executable_sequence_cache_limits<Store>(
    store: &mut Store,
    limits: NativeExecutableSequenceCacheLimits,
    maximum_bytes: NonZeroUsize,
) -> NativeExecutableSequenceCacheLimitsPersistenceResult<
    NativeExecutableSequenceCacheLimitsPersistenceWrite,
    Store::Error,
>
where
    Store: BlobStore,
{
    let bytes = encode_native_executable_sequence_cache_limits(limits)
        .map_err(NativeExecutableSequenceCacheLimitsPersistenceError::Codec)?;
    let write = blob_persistence::persist_blob(store, &bytes, maximum_bytes)
        .map_err(NativeExecutableSequenceCacheLimitsPersistenceError::Blob)?;
    Ok(NativeExecutableSequenceCacheLimitsPersistenceWrite {
        bytes: write.bytes(),
    })
}

/// Persists one exact executable-cache limit policy and confirms durability.
///
/// # Errors
///
/// Returns codec, byte-limit, or store failure before publication.
pub fn persist_native_executable_sequence_cache_limits_durably<Store>(
    store: &mut Store,
    limits: NativeExecutableSequenceCacheLimits,
    maximum_bytes: NonZeroUsize,
) -> NativeExecutableSequenceCacheLimitsDurableStoreResult<Store>
where
    Store: DurableBlobStore,
{
    let bytes = encode_native_executable_sequence_cache_limits(limits)
        .map_err(NativeExecutableSequenceCacheLimitsPersistenceError::Codec)?;
    let outcome =
        blob_persistence::persist_blob_durably(store, &bytes, maximum_bytes)
            .map_err(
                NativeExecutableSequenceCacheLimitsPersistenceError::Blob,
            )?;
    Ok(map_durable_persistence(outcome))
}

/// Restores one exact executable-cache limit policy from canonical bounded
/// bytes.
///
/// # Errors
///
/// Returns store, byte-limit, or codec evidence without inventing missing
/// configuration.
pub fn restore_native_executable_sequence_cache_limits<Store>(
    store: &mut Store,
    maximum_bytes: NonZeroUsize,
) -> NativeExecutableSequenceCacheLimitsPersistenceResult<
    NativeExecutableSequenceCacheLimitsPersistenceLoad,
    Store::Error,
>
where
    Store: BlobStore,
{
    let load = blob_persistence::restore_blob(store, maximum_bytes)
        .map_err(NativeExecutableSequenceCacheLimitsPersistenceError::Blob)?;
    let BlobLoad::Present { bytes } = load else {
        return Ok(NativeExecutableSequenceCacheLimitsPersistenceLoad::Missing);
    };
    let length = bytes.len();
    let limits = decode_native_executable_sequence_cache_limits(&bytes)
        .map_err(NativeExecutableSequenceCacheLimitsPersistenceError::Codec)?;
    Ok(
        NativeExecutableSequenceCacheLimitsPersistenceLoad::Restored {
            bytes: length,
            limits,
        },
    )
}

#[cfg(test)]
#[path = "../../../../../tests/tiered/cache_limits_store.rs"]
mod tests;
