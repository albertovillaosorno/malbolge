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
//   - Binding canonical ordered count state to bounded durable blob
//     persistence.
// - Must-Not:
//   - Source order, choose paths, retry conflicts, or persist split state.
// - Allows:
//   - Inputs: one ordered owner, positive byte bound, and blob store.
//   - Outputs: durable publication evidence or exact restored ordered
//     ownership.
//   - Side effects: delegated through bounded opaque-blob persistence only.
// - Split-When:
//   - Conditional ordered publication or migration gains authority.
// - Merge-When:
//   - One durable ordered telemetry lifecycle owns publication and CAS.
// - Summary:
//   - Persists order watermark and count window as one canonical blob.
// - Description:
//   - Restart restores watermark and FIFO together from one validated document.
// - Usage:
//   - Persist or restore one preconfigured ordered count-telemetry blob.
// - Defaults:
//   - Missing durable state is explicit and never invents an order watermark.
//

//! Durable persistence for caller-ordered cached-retry count telemetry.

use std::num::NonZeroUsize;

use super::{
    NativeContinuationCachedRetryTelemetryOrderedStateCodecError,
    NativeContinuationCachedRetryTelemetryOrderedWindow,
    decode_cached_retry_telemetry_ordered_state,
    encode_cached_retry_telemetry_ordered_state,
};
use crate::blob_persistence::{
    NativeContinuationBlobDurablePersistence as BlobDurablePersistence,
    NativeContinuationBlobPersistenceError,
    NativeContinuationBlobPersistenceLoad as BlobLoad, persist_blob_durably,
    restore_blob,
};
use crate::blob_store::{
    NativeContinuationBlobStore as BlobStore,
    NativeContinuationDurableBlobStore as DurableBlobStore,
};

/// Ordered telemetry publication plus explicit durability state.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryTelemetryOrderedDurablePersistence<
    DurabilityError,
> {
    /// Canonical ordered state committed and durability was confirmed.
    Durable {
        /// Exact canonical byte count committed by the store.
        bytes: usize,
    },
    /// Canonical ordered state committed, then durability confirmation failed.
    Published {
        /// Exact canonical byte count committed by the store.
        bytes: usize,
        /// Exact post-publication durability failure.
        durability_error: DurabilityError,
    },
}

/// Why typed ordered telemetry persistence failed closed.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryTelemetryOrderedPersistenceError<
    StoreError,
> {
    /// Bounded opaque-blob orchestration or outbound store failed.
    Blob(NativeContinuationBlobPersistenceError<StoreError>),
    /// Canonical ordered-state framing or nested count semantics failed.
    Codec(Box<NativeContinuationCachedRetryTelemetryOrderedStateCodecError>),
}

/// Result of one bounded ordered telemetry restoration.
#[derive(Debug)]
pub enum NativeContinuationCachedRetryTelemetryOrderedPersistenceLoad {
    /// No durable ordered telemetry currently exists at the configured
    /// location.
    Missing,
    /// Canonical bytes reconstructed exact order watermark plus count window.
    Restored {
        /// Exact canonical byte count returned by the adapter.
        bytes: usize,
        /// Reconstructed ordered count-telemetry ownership.
        value: NativeContinuationCachedRetryTelemetryOrderedWindow,
    },
}

/// Durable ordered telemetry result specialized to one store type.
pub type NativeContinuationCachedRetryTelemetryOrderedDurableStoreResult<
    Store,
> = Result<
    NativeContinuationCachedRetryTelemetryOrderedDurablePersistence<
        <Store as DurableBlobStore>::DurabilityError,
    >,
    NativeContinuationCachedRetryTelemetryOrderedPersistenceError<
        <Store as BlobStore>::Error,
    >,
>;

/// Ordered telemetry restoration result specialized to one store type.
pub type NativeContinuationCachedRetryTelemetryOrderedLoadStoreResult<Store> =
    Result<
        NativeContinuationCachedRetryTelemetryOrderedPersistenceLoad,
        NativeContinuationCachedRetryTelemetryOrderedPersistenceError<
            <Store as BlobStore>::Error,
        >,
    >;

/// Persists exact ordered count telemetry and confirms store durability.
///
/// # Errors
///
/// Returns codec, byte-limit, or store failure before publication commits.
pub fn persist_cached_retry_telemetry_ordered_state_durably<Store>(
    store: &mut Store,
    ordered: &NativeContinuationCachedRetryTelemetryOrderedWindow,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationCachedRetryTelemetryOrderedDurableStoreResult<Store>
where
    Store: DurableBlobStore,
{
    let bytes =
        encode_cached_retry_telemetry_ordered_state(ordered).map_err(
            |error| {
                NativeContinuationCachedRetryTelemetryOrderedPersistenceError::
                Codec(Box::new(error))
            },
        )?;
    let outcome = persist_blob_durably(store, &bytes, maximum_bytes).map_err(
        NativeContinuationCachedRetryTelemetryOrderedPersistenceError::Blob,
    )?;
    Ok(match outcome {
        BlobDurablePersistence::Durable { write } => {
            NativeContinuationCachedRetryTelemetryOrderedDurablePersistence::
                Durable {
                    bytes: write.bytes(),
                }
        },
        BlobDurablePersistence::Published {
            durability_error,
            write,
        } => {
            NativeContinuationCachedRetryTelemetryOrderedDurablePersistence::
                Published {
                    bytes: write.bytes(),
                    durability_error,
                }
        },
    })
}

/// Restores exact ordered count telemetry from canonical bounded bytes.
///
/// # Errors
///
/// Returns store, byte-limit, or ordered-state codec evidence without inventing
/// missing state.
pub fn restore_cached_retry_telemetry_ordered_state<Store>(
    store: &mut Store,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationCachedRetryTelemetryOrderedLoadStoreResult<Store>
where
    Store: BlobStore,
{
    let load = restore_blob(store, maximum_bytes).map_err(
        NativeContinuationCachedRetryTelemetryOrderedPersistenceError::Blob,
    )?;
    let BlobLoad::Present { bytes } = load else {
        return Ok(
            NativeContinuationCachedRetryTelemetryOrderedPersistenceLoad::
                Missing,
        );
    };
    let length = bytes.len();
    let value =
        decode_cached_retry_telemetry_ordered_state(&bytes).map_err(
            |error| {
                NativeContinuationCachedRetryTelemetryOrderedPersistenceError::
                Codec(Box::new(error))
            },
        )?;
    Ok(
        NativeContinuationCachedRetryTelemetryOrderedPersistenceLoad::Restored {
            bytes: length,
            value,
        },
    )
}
