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
//   - Binding cached-retry count/latency codecs to bounded blob persistence.
// - Must-Not:
//   - Choose storage locations, perform filesystem I/O, infer policy, or merge
//     durable snapshots.
// - Allows:
//   - Inputs: one live count/latency owner, positive byte limit, and blob
//     store.
//   - Outputs: canonical durable bytes or reconstructed exact owner evidence.
//   - Side effects: delegated through the bounded persistence application use
//     case.
// - Split-When:
//   - Durable merge, migration, or multi-blob transactions gain authority.
// - Merge-When:
//   - Cached-cycle orchestration directly owns canonical persistence policy.
// - Summary:
//   - Adapts exact cached-retry telemetry owners to storage-neutral
//     persistence.
// - Description:
//   - Canonical codec validation surrounds the bounded blob application call.
// - Usage:
//   - Call explicitly for one preconfigured count or latency blob store.
// - Defaults:
//   - Missing durable state is explicit and never creates an empty owner.
//

//! Cached-retry telemetry codec binding for bounded durable persistence.

use std::num::NonZeroUsize;

use super::{
    NativeContinuationCachedRetryLatencyCodecError,
    NativeContinuationCachedRetryLatencyHistogram,
    NativeContinuationCachedRetryLatencySnapshotError,
    NativeContinuationCachedRetryTelemetryCodecError,
    NativeContinuationCachedRetryTelemetrySnapshotError,
    NativeContinuationCachedRetryTelemetryWindow,
    decode_cached_retry_latency_snapshot as decode_latency_snapshot,
    decode_cached_retry_telemetry_snapshot as decode_telemetry_snapshot,
    encode_cached_retry_latency_snapshot as encode_latency_snapshot,
    encode_cached_retry_telemetry_snapshot as encode_telemetry_snapshot,
};
use crate::{
    cached_retry_telemetry_blob_store as store_port,
    telemetry_blob_persistence as blob_persistence,
};

/// Why one cached-retry telemetry persistence operation failed closed.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryTelemetryPersistenceError<StoreError> {
    /// Bounded blob orchestration or its outbound store failed.
    Blob(
        blob_persistence::NativeContinuationTelemetryBlobPersistenceError<
            StoreError,
        >,
    ),
    /// Canonical count-telemetry framing or semantics failed.
    CountCodec(Box<NativeContinuationCachedRetryTelemetryCodecError>),
    /// Validated count snapshot could not reconstruct its live owner.
    CountSnapshot(Box<NativeContinuationCachedRetryTelemetrySnapshotError>),
    /// Canonical latency framing or semantics failed.
    LatencyCodec(Box<NativeContinuationCachedRetryLatencyCodecError>),
    /// Validated latency snapshot could not reconstruct its live owner.
    LatencySnapshot(Box<NativeContinuationCachedRetryLatencySnapshotError>),
}

/// Result of one bounded cached-retry telemetry load.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryTelemetryPersistenceLoad<Value> {
    /// No durable blob currently exists at the adapter-configured location.
    Missing,
    /// Canonical bytes reconstructed one exact live telemetry owner.
    Restored {
        /// Exact canonical byte count returned by the adapter.
        bytes: usize,
        /// Reconstructed live telemetry owner.
        value: Value,
    },
}

/// Result of one cached-retry persistence operation.
pub type NativeContinuationCachedRetryTelemetryPersistenceResult<
    Value,
    StoreError,
> = Result<
    Value,
    NativeContinuationCachedRetryTelemetryPersistenceError<StoreError>,
>;

/// Restored latency-owner result from one bounded persistence load.
pub type NativeContinuationCachedRetryTelemetryPersistenceLatencyLoad =
    NativeContinuationCachedRetryTelemetryPersistenceLoad<
        NativeContinuationCachedRetryLatencyHistogram,
    >;

/// Result of one bounded latency-owner restoration use case.
pub type NativeContinuationCachedRetryTelemetryPersistenceLatencyLoadResult<
    StoreError,
> = NativeContinuationCachedRetryTelemetryPersistenceResult<
    NativeContinuationCachedRetryTelemetryPersistenceLatencyLoad,
    StoreError,
>;

/// Restored count-window result from one bounded persistence load.
pub type NativeContinuationCachedRetryTelemetryPersistenceWindowLoad =
    NativeContinuationCachedRetryTelemetryPersistenceLoad<
        NativeContinuationCachedRetryTelemetryWindow,
    >;

/// Result of one bounded count-window restoration use case.
pub type NativeContinuationCachedRetryTelemetryPersistenceWindowLoadResult<
    StoreError,
> = NativeContinuationCachedRetryTelemetryPersistenceResult<
    NativeContinuationCachedRetryTelemetryPersistenceWindowLoad,
    StoreError,
>;

type BlobLoad =
    blob_persistence::NativeContinuationTelemetryBlobPersistenceLoad;
type PersistenceLoad<Value> =
    NativeContinuationCachedRetryTelemetryPersistenceLoad<Value>;

/// Publication evidence from one successful canonical telemetry replacement.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryTelemetryPersistenceWrite {
    bytes: usize,
}

impl NativeContinuationCachedRetryTelemetryPersistenceWrite {
    /// Returns the exact canonical byte count passed to the outbound store.
    #[must_use]
    pub const fn bytes(self) -> usize {
        self.bytes
    }
}

/// Persists one exact latency histogram as canonical bounded bytes.
///
/// # Errors
///
/// Returns codec, byte-limit, or outbound-store failure before claiming durable
/// publication.
pub fn persist_cached_retry_latency_histogram<Store>(
    store: &mut Store,
    histogram: &NativeContinuationCachedRetryLatencyHistogram,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationCachedRetryTelemetryPersistenceResult<
    NativeContinuationCachedRetryTelemetryPersistenceWrite,
    Store::Error,
>
where
    Store: store_port::NativeContinuationCachedRetryTelemetryBlobStore,
{
    let bytes = encode_latency_snapshot(&histogram.snapshot()).map_err(|error| {
        NativeContinuationCachedRetryTelemetryPersistenceError::LatencyCodec(
            Box::new(error),
        )
    })?;
    let write =
        blob_persistence::persist_telemetry_blob(store, &bytes, maximum_bytes)
            .map_err(
                NativeContinuationCachedRetryTelemetryPersistenceError::Blob,
            )?;
    Ok(NativeContinuationCachedRetryTelemetryPersistenceWrite {
        bytes: write.bytes(),
    })
}

/// Persists one exact count-telemetry FIFO as canonical bounded bytes.
///
/// # Errors
///
/// Returns codec, byte-limit, or outbound-store failure before claiming durable
/// publication.
pub fn persist_cached_retry_telemetry_window<Store>(
    store: &mut Store,
    window: &NativeContinuationCachedRetryTelemetryWindow,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationCachedRetryTelemetryPersistenceResult<
    NativeContinuationCachedRetryTelemetryPersistenceWrite,
    Store::Error,
>
where
    Store: store_port::NativeContinuationCachedRetryTelemetryBlobStore,
{
    let bytes =
        encode_telemetry_snapshot(&window.snapshot()).map_err(|error| {
            NativeContinuationCachedRetryTelemetryPersistenceError::CountCodec(
                Box::new(error),
            )
        })?;
    let write =
        blob_persistence::persist_telemetry_blob(store, &bytes, maximum_bytes)
            .map_err(
                NativeContinuationCachedRetryTelemetryPersistenceError::Blob,
            )?;
    Ok(NativeContinuationCachedRetryTelemetryPersistenceWrite {
        bytes: write.bytes(),
    })
}

/// Restores one exact latency histogram from canonical bounded bytes.
///
/// # Errors
///
/// Returns store, byte-limit, codec, or reconstruction evidence without
/// inventing empty state for a missing blob.
pub fn restore_cached_retry_latency_histogram<Store>(
    store: &mut Store,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationCachedRetryTelemetryPersistenceLatencyLoadResult<
    Store::Error,
>
where
    Store: store_port::NativeContinuationCachedRetryTelemetryBlobStore,
{
    let load = blob_persistence::restore_telemetry_blob(store, maximum_bytes)
        .map_err(
        NativeContinuationCachedRetryTelemetryPersistenceError::Blob,
    )?;
    let BlobLoad::Present { bytes } = load else {
        return Ok(PersistenceLoad::Missing);
    };
    let length = bytes.len();
    let snapshot = decode_latency_snapshot(&bytes).map_err(|error| {
        NativeContinuationCachedRetryTelemetryPersistenceError::LatencyCodec(
            Box::new(error),
        )
    })?;
    let histogram =
        NativeContinuationCachedRetryLatencyHistogram::from_snapshot(snapshot)
            .map_err(|error| {
                NativeContinuationCachedRetryTelemetryPersistenceError::
                    LatencySnapshot(Box::new(error))
            })?;
    Ok(PersistenceLoad::Restored {
        bytes: length,
        value: histogram,
    })
}

/// Restores one exact count-telemetry FIFO from canonical bounded bytes.
///
/// # Errors
///
/// Returns store, byte-limit, codec, or reconstruction evidence without
/// inventing empty state for a missing blob.
pub fn restore_cached_retry_telemetry_window<Store>(
    store: &mut Store,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationCachedRetryTelemetryPersistenceWindowLoadResult<
    Store::Error,
>
where
    Store: store_port::NativeContinuationCachedRetryTelemetryBlobStore,
{
    let load = blob_persistence::restore_telemetry_blob(store, maximum_bytes)
        .map_err(
        NativeContinuationCachedRetryTelemetryPersistenceError::Blob,
    )?;
    let BlobLoad::Present { bytes } = load else {
        return Ok(PersistenceLoad::Missing);
    };
    let length = bytes.len();
    let snapshot = decode_telemetry_snapshot(&bytes).map_err(|error| {
        NativeContinuationCachedRetryTelemetryPersistenceError::CountCodec(
            Box::new(error),
        )
    })?;
    let window = NativeContinuationCachedRetryTelemetryWindow::from_snapshot(
        snapshot,
    )
    .map_err(|error| {
        NativeContinuationCachedRetryTelemetryPersistenceError::CountSnapshot(
            Box::new(error),
        )
    })?;
    Ok(PersistenceLoad::Restored {
        bytes: length,
        value: window,
    })
}
