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
//   - One-shot durable merge publication for cached-retry latency histograms.
// - Must-Not:
//   - Retry conflicts, infer finer distributions, choose storage paths, or
//     coordinate multiple blobs.
// - Allows:
//   - Inputs: one source histogram, positive byte bound, and conditional store.
//   - Outputs: exact typed conflict, durable commit, committed sync failure, or
//     typed prepublication failure.
//   - Side effects: one bounded load and at most one conditional publication.
// - Split-When:
//   - Automatic conflict retry or multi-blob aggregation gains authority.
// - Merge-When:
//   - One distributed telemetry owner owns load, merge, CAS, and retry policy.
// - Summary:
//   - Merges one exact histogram into durable state with optimistic
//     concurrency.
// - Description:
//   - CAS compares the exact raw bytes loaded before canonical decoding.
// - Usage:
//   - Submit one immutable local histogram and handle conflict explicitly.
// - Defaults:
//   - Missing state initializes from the source; conflict never retries itself.
//

//! One-shot optimistic durable merge for cached-retry latency histograms.

use std::num::NonZeroUsize;

use super::{
    NativeContinuationCachedRetryLatencyCodecError,
    NativeContinuationCachedRetryLatencyHistogram,
    NativeContinuationCachedRetryLatencyNormalizedMergeError,
    NativeContinuationCachedRetryLatencySnapshotError,
    decode_cached_retry_latency_snapshot, encode_cached_retry_latency_snapshot,
    merge_cached_retry_latency_histograms_exact,
};
use crate::blob_persistence::{
    NativeContinuationBlobConditionalDurablePersistence as BlobCasDurable,
    NativeContinuationBlobPersistenceError,
    NativeContinuationBlobPersistenceLoad as BlobLoad,
    compare_and_swap_blob_durably, restore_blob,
};
use crate::blob_store::{
    NativeContinuationBlobStore as BlobStore,
    NativeContinuationConditionalBlobStore as ConditionalBlobStore,
    NativeContinuationDurableBlobStore as DurableBlobStore,
};

/// Typed one-shot outcome of durable cached-retry latency merge publication.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryLatencyDurableMerge<DurabilityError> {
    /// Durable bytes changed after the initial load; no retry was attempted.
    Conflict {
        /// Exact typed durable state observed by conditional publication.
        current: Option<Box<NativeContinuationCachedRetryLatencyHistogram>>,
        /// Typed state decoded from the bytes used as CAS expectation.
        expected: Option<Box<NativeContinuationCachedRetryLatencyHistogram>>,
    },
    /// Merged histogram committed and durability confirmation completed.
    Durable {
        /// Exact canonical merged byte count committed by the store.
        bytes: usize,
        /// Exact merged histogram now published.
        current: Box<NativeContinuationCachedRetryLatencyHistogram>,
        /// Durable histogram observed before this merge, when present.
        previous: Option<Box<NativeContinuationCachedRetryLatencyHistogram>>,
    },
    /// Merged histogram committed, then durability confirmation failed.
    Published {
        /// Exact canonical merged byte count committed by the store.
        bytes: usize,
        /// Exact merged histogram now process-visible.
        current: Box<NativeContinuationCachedRetryLatencyHistogram>,
        /// Exact post-publication durability failure.
        durability_error: DurabilityError,
        /// Durable histogram observed before this merge, when present.
        previous: Option<Box<NativeContinuationCachedRetryLatencyHistogram>>,
    },
}

/// Why one-shot durable latency merge failed before returning typed outcome.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryLatencyDurableMergeError<StoreError> {
    /// Bounded load, conditional publication, or outbound store failed.
    Blob(NativeContinuationBlobPersistenceError<StoreError>),
    /// Canonical latency framing or semantics failed.
    Codec(Box<NativeContinuationCachedRetryLatencyCodecError>),
    /// Exact schema normalization or histogram merge failed.
    Merge(Box<NativeContinuationCachedRetryLatencyNormalizedMergeError>),
    /// Validated latency snapshot could not reconstruct a histogram.
    Snapshot(Box<NativeContinuationCachedRetryLatencySnapshotError>),
}

/// Result of one typed durable latency merge operation.
pub type NativeContinuationCachedRetryLatencyDurableMergeResult<
    StoreError,
    DurabilityError,
> = Result<
    NativeContinuationCachedRetryLatencyDurableMerge<DurabilityError>,
    NativeContinuationCachedRetryLatencyDurableMergeError<StoreError>,
>;

/// Durable latency merge result specialized to one store implementation.
pub type NativeContinuationCachedRetryLatencyDurableMergeStoreResult<Store> =
    NativeContinuationCachedRetryLatencyDurableMergeResult<
        <Store as BlobStore>::Error,
        <Store as DurableBlobStore>::DurabilityError,
    >;

type Histogram = NativeContinuationCachedRetryLatencyHistogram;
type MergeError<StoreError> =
    NativeContinuationCachedRetryLatencyDurableMergeError<StoreError>;
type MergeOutcome<DurabilityError> =
    NativeContinuationCachedRetryLatencyDurableMerge<DurabilityError>;
type MapPublicationResult<StoreError, DurabilityError> =
    Result<MergeOutcome<DurabilityError>, MergeError<StoreError>>;

/// Loads, exactly merges, and conditionally publishes one latency histogram.
///
/// # Errors
///
/// Returns load/store, canonical codec, reconstruction, or exact normalized
/// merge failure. Concurrent state change is returned as typed conflict
/// evidence and is never retried automatically.
pub fn merge_cached_retry_latency_histogram_durably<Store>(
    store: &mut Store,
    source: &NativeContinuationCachedRetryLatencyHistogram,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationCachedRetryLatencyDurableMergeStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    let load = restore_blob(store, maximum_bytes).map_err(MergeError::Blob)?;
    let (expected_bytes, previous, candidate) = match load {
        BlobLoad::Missing => (None, None, source.clone()),
        BlobLoad::Present { bytes } => {
            let previous = decode_histogram(&bytes)?;
            let candidate =
                merge_cached_retry_latency_histograms_exact(&previous, source)
                    .map_err(|error| MergeError::Merge(Box::new(error)))?
                    .into_histogram();
            (Some(bytes), Some(previous), candidate)
        },
    };
    let candidate_bytes =
        encode_cached_retry_latency_snapshot(&candidate.snapshot())
            .map_err(|error| MergeError::Codec(Box::new(error)))?;
    let publication = compare_and_swap_blob_durably(
        store,
        expected_bytes.as_deref(),
        &candidate_bytes,
        maximum_bytes,
    )
    .map_err(MergeError::Blob)?;
    map_publication(publication, previous, candidate)
}

fn decode_histogram<StoreError>(
    bytes: &[u8],
) -> Result<Histogram, MergeError<StoreError>> {
    let snapshot = decode_cached_retry_latency_snapshot(bytes)
        .map_err(|error| MergeError::Codec(Box::new(error)))?;
    Histogram::from_snapshot(snapshot)
        .map_err(|error| MergeError::Snapshot(Box::new(error)))
}

fn map_publication<StoreError, DurabilityError>(
    publication: BlobCasDurable<DurabilityError>,
    previous: Option<Histogram>,
    candidate: Histogram,
) -> MapPublicationResult<StoreError, DurabilityError> {
    match publication {
        BlobCasDurable::Conflict { current: current_bytes } => {
            let current = current_bytes
                .as_deref()
                .map(decode_histogram)
                .transpose()?
                .map(Box::new);
            Ok(MergeOutcome::Conflict {
                current,
                expected: previous.map(Box::new),
            })
        },
        BlobCasDurable::Durable { write } => Ok(MergeOutcome::Durable {
            bytes: write.bytes(),
            current: Box::new(candidate),
            previous: previous.map(Box::new),
        }),
        BlobCasDurable::Published { durability_error, write } => {
            Ok(MergeOutcome::Published {
                bytes: write.bytes(),
                current: Box::new(candidate),
                durability_error,
                previous: previous.map(Box::new),
            })
        },
    }
}
