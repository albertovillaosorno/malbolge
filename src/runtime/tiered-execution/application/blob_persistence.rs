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
//   - Explicit bounded persistence use cases for one opaque byte blob.
// - Must-Not:
//   - Choose storage locations, interpret application bytes, select policy, or
//     coordinate multiple blobs.
// - Allows:
//   - Inputs: immutable admitted bytes, positive byte limit, and blob store.
//   - Outputs: missing/present owned bytes or exact publication evidence.
//   - Side effects: one delegated bounded load or atomic replacement per call.
// - Split-When:
//   - Multi-blob transactions, migration, or durable merge gains authority.
// - Merge-When:
//   - Another application service owns the exact bounded blob use case.
// - Summary:
//   - Coordinates byte bounds with replaceable durable blob storage.
// - Description:
//   - Size is checked before publication and again after every adapter load.
// - Usage:
//   - Called by typed composition after canonical encoding.
// - Defaults:
//   - Missing durable state is explicit and never invents empty bytes.
//

//! Explicit bounded persistence orchestration for one opaque byte blob.

use std::num::NonZeroUsize;

use store_port::{
    NativeContinuationBlobStore as BlobStore,
    NativeContinuationDurableBlobStore as DurableBlobStore,
};

use crate::blob_store as store_port;

/// Outcome after publication plus explicit durability confirmation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationBlobDurablePersistence<DurabilityError> {
    /// Publication and the adapter's durability confirmation both completed.
    Durable {
        /// Exact committed byte count.
        write: NativeContinuationBlobPersistenceWrite,
    },
    /// Publication committed, but durability confirmation failed afterward.
    Published {
        /// Exact post-publication durability failure.
        durability_error: DurabilityError,
        /// Exact committed byte count.
        write: NativeContinuationBlobPersistenceWrite,
    },
}

/// Why one explicit blob persistence use case failed closed.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationBlobPersistenceError<StoreError> {
    /// Admitted or adapter-returned bytes exceed the caller's positive bound.
    ByteLimit {
        /// Positive caller-configured byte limit.
        maximum_bytes: NonZeroUsize,
        /// Exact supplied or returned byte count.
        observed_bytes: usize,
    },
    /// The selected outbound store failed after application admission.
    Store(StoreError),
}

/// Result of one bounded blob load.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationBlobPersistenceLoad {
    /// No durable blob currently exists at the adapter-configured location.
    Missing,
    /// One bounded durable blob was loaded without interpreting its bytes.
    Present {
        /// Exact bytes returned by the outbound adapter.
        bytes: Vec<u8>,
    },
}

/// Result of one persistence use case with exact application failure evidence.
pub type NativeContinuationBlobPersistenceResult<Value, StoreError> =
    Result<Value, NativeContinuationBlobPersistenceError<StoreError>>;

/// Result of publication plus optional durability confirmation.
pub type NativeContinuationBlobDurablePersistenceResult<
    StoreError,
    DurabilityError,
> = Result<
    NativeContinuationBlobDurablePersistence<DurabilityError>,
    NativeContinuationBlobPersistenceError<StoreError>,
>;

/// Durable publication result specialized to one outbound store type.
pub type NativeContinuationBlobDurableStoreResult<Store> =
    NativeContinuationBlobDurablePersistenceResult<
        <Store as BlobStore>::Error,
        <Store as DurableBlobStore>::DurabilityError,
    >;

/// Publication evidence from one successful blob replacement.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationBlobPersistenceWrite {
    bytes: usize,
}

impl<DurabilityError>
    NativeContinuationBlobDurablePersistence<DurabilityError>
{
    /// Returns the exact committed byte count in either durability state.
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

    /// Reports whether publication durability was explicitly confirmed.
    #[must_use]
    pub const fn is_durable(&self) -> bool {
        matches!(self, Self::Durable { .. })
    }
}

impl NativeContinuationBlobPersistenceWrite {
    /// Returns the exact admitted byte count passed to the outbound store.
    #[must_use]
    pub const fn bytes(self) -> usize {
        self.bytes
    }
}

/// Persists one blob and then explicitly confirms publication durability.
///
/// # Errors
///
/// Returns only prepublication byte-limit or store failures. A durability
/// confirmation failure is returned as committed `Published` evidence.
pub fn persist_blob_durably<Store>(
    store: &mut Store,
    bytes: &[u8],
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationBlobDurableStoreResult<Store>
where
    Store: DurableBlobStore,
{
    let write = persist_blob(store, bytes, maximum_bytes)?;
    match store.confirm_durability() {
        Ok(()) => {
            Ok(NativeContinuationBlobDurablePersistence::Durable { write })
        },
        Err(durability_error) => {
            Ok(NativeContinuationBlobDurablePersistence::Published {
                durability_error,
                write,
            })
        },
    }
}

/// Persists one admitted blob under an explicit positive byte bound.
///
/// # Errors
///
/// Returns byte-limit or outbound-store failure before claiming publication.
pub fn persist_blob<Store>(
    store: &mut Store,
    bytes: &[u8],
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationBlobPersistenceResult<
    NativeContinuationBlobPersistenceWrite,
    Store::Error,
>
where
    Store: BlobStore,
{
    admit_byte_limit(bytes.len(), maximum_bytes)?;
    store
        .replace(bytes)
        .map_err(NativeContinuationBlobPersistenceError::Store)?;
    Ok(NativeContinuationBlobPersistenceWrite { bytes: bytes.len() })
}

/// Restores one bounded blob without interpreting its bytes.
///
/// # Errors
///
/// Returns store or byte-limit evidence. The application rechecks the adapter
/// result before exposing bytes to telemetry-specific decoding.
pub fn restore_blob<Store>(
    store: &mut Store,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationBlobPersistenceResult<
    NativeContinuationBlobPersistenceLoad,
    Store::Error,
>
where
    Store: BlobStore,
{
    let Some(bytes) = store
        .load(maximum_bytes)
        .map_err(NativeContinuationBlobPersistenceError::Store)?
    else {
        return Ok(NativeContinuationBlobPersistenceLoad::Missing);
    };
    admit_byte_limit(bytes.len(), maximum_bytes)?;
    Ok(NativeContinuationBlobPersistenceLoad::Present { bytes })
}

const fn admit_byte_limit<StoreError>(
    observed_bytes: usize,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationBlobPersistenceResult<(), StoreError> {
    if observed_bytes <= maximum_bytes.get() {
        Ok(())
    } else {
        Err(NativeContinuationBlobPersistenceError::ByteLimit {
            maximum_bytes,
            observed_bytes,
        })
    }
}
