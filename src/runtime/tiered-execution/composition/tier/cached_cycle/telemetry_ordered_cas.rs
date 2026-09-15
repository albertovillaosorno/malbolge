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
//   - One-shot durable ordered-batch publication for cached-retry count state.
// - Must-Not:
//   - Retry conflicts, source order, override persisted capacity, or split
//     state.
// - Allows:
//   - Inputs: external order, ordered summaries, missing-state capacity, bound,
//     and conditional durable store.
//   - Outputs: exact typed conflict, durable commit, committed sync failure, or
//     typed prepublication failure.
//   - Side effects: one bounded load and at most one conditional publication.
// - Split-When:
//   - Automatic conflict retry or external ordering service gains authority.
// - Merge-When:
//   - One distributed count owner owns load, ordered append, CAS, and retry.
// - Summary:
//   - Appends one ordered batch to durable combined watermark/FIFO state.
// - Description:
//   - CAS compares the exact raw combined-state bytes loaded before decoding.
// - Usage:
//   - Submit one externally ordered summary batch and handle conflict directly.
// - Defaults:
//   - Missing state uses caller capacity; conflict never retries itself.
//

//! One-shot durable CAS for externally ordered cached-retry count telemetry.

use std::num::NonZeroUsize;

use super::{
    NativeContinuationCachedRetryTelemetry,
    NativeContinuationCachedRetryTelemetryBatchOrder,
    NativeContinuationCachedRetryTelemetryOrderedStateCodecError,
    NativeContinuationCachedRetryTelemetryOrderedWindow,
    NativeContinuationCachedRetryTelemetryOrderedWindowAppend,
    NativeContinuationCachedRetryTelemetryOrderedWindowError,
    NativeContinuationCachedRetryTelemetryWindow,
    decode_cached_retry_telemetry_ordered_state,
    encode_cached_retry_telemetry_ordered_state,
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

/// Immutable request for one durable externally ordered count publication.
#[derive(Clone, Copy, Debug)]
pub struct NativeContinuationCachedRetryTelemetryOrderedCasRequest<'telemetry> {
    initial_capacity: NonZeroUsize,
    maximum_bytes: NonZeroUsize,
    order: NativeContinuationCachedRetryTelemetryBatchOrder,
    telemetry: &'telemetry [NativeContinuationCachedRetryTelemetry],
}

impl<'telemetry>
    NativeContinuationCachedRetryTelemetryOrderedCasRequest<'telemetry>
{
    /// Constructs one explicit one-shot ordered publication request.
    #[must_use]
    pub const fn new(
        initial_capacity: NonZeroUsize,
        order: NativeContinuationCachedRetryTelemetryBatchOrder,
        telemetry: &'telemetry [NativeContinuationCachedRetryTelemetry],
        maximum_bytes: NonZeroUsize,
    ) -> Self {
        Self {
            initial_capacity,
            maximum_bytes,
            order,
            telemetry,
        }
    }
}

/// Typed one-shot outcome of durable ordered count publication.
#[derive(Debug)]
pub enum NativeContinuationCachedRetryTelemetryOrderedCas<DurabilityError> {
    /// Durable bytes changed after the initial load; no retry was attempted.
    Conflict {
        /// Exact combined durable state observed at conflict, or missing
        /// state.
        current:
            Option<Box<NativeContinuationCachedRetryTelemetryOrderedWindow>>,
        /// Combined state decoded from bytes used as the CAS expectation.
        expected:
            Option<Box<NativeContinuationCachedRetryTelemetryOrderedWindow>>,
    },
    /// Ordered batch committed and durability confirmation completed.
    Durable {
        /// Exact canonical combined-state byte count committed by the store.
        bytes: usize,
        /// Exact combined ordered state now published.
        current: Box<NativeContinuationCachedRetryTelemetryOrderedWindow>,
        /// Exact local batch append evidence committed with external order.
        publication: NativeContinuationCachedRetryTelemetryOrderedWindowAppend,
        /// Durable combined state observed before publication, when present.
        previous:
            Option<Box<NativeContinuationCachedRetryTelemetryOrderedWindow>>,
    },
    /// Ordered batch committed, then durability confirmation failed.
    Published {
        /// Exact canonical combined-state byte count committed by the store.
        bytes: usize,
        /// Exact combined ordered state now process-visible.
        current: Box<NativeContinuationCachedRetryTelemetryOrderedWindow>,
        /// Exact post-publication durability failure.
        durability_error: DurabilityError,
        /// Exact local batch append evidence committed with external order.
        publication: NativeContinuationCachedRetryTelemetryOrderedWindowAppend,
        /// Durable combined state observed before publication, when present.
        previous:
            Option<Box<NativeContinuationCachedRetryTelemetryOrderedWindow>>,
    },
}

/// Why one-shot ordered count CAS failed before returning typed outcome.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryTelemetryOrderedCasError<StoreError> {
    /// Bounded load, conditional publication, or outbound store failed.
    Blob(NativeContinuationBlobPersistenceError<StoreError>),
    /// Canonical ordered-state framing or nested count semantics failed.
    Codec(Box<NativeContinuationCachedRetryTelemetryOrderedStateCodecError>),
    /// External order or transactional count-window append failed before CAS.
    Ordered(NativeContinuationCachedRetryTelemetryOrderedWindowError),
}

/// Result of one typed durable ordered count CAS operation.
pub type NativeContinuationCachedRetryTelemetryOrderedCasResult<
    StoreError,
    DurabilityError,
> = Result<
    NativeContinuationCachedRetryTelemetryOrderedCas<DurabilityError>,
    NativeContinuationCachedRetryTelemetryOrderedCasError<StoreError>,
>;

/// Durable ordered count CAS result specialized to one store implementation.
pub type NativeContinuationCachedRetryTelemetryOrderedCasStoreResult<Store> =
    NativeContinuationCachedRetryTelemetryOrderedCasResult<
        <Store as BlobStore>::Error,
        <Store as DurableBlobStore>::DurabilityError,
    >;

type OrderedCasError<StoreError> =
    NativeContinuationCachedRetryTelemetryOrderedCasError<StoreError>;
type OrderedCasOutcome<DurabilityError> =
    NativeContinuationCachedRetryTelemetryOrderedCas<DurabilityError>;
type OrderedOwner = NativeContinuationCachedRetryTelemetryOrderedWindow;
type MapPublicationResult<StoreError, DurabilityError> =
    Result<OrderedCasOutcome<DurabilityError>, OrderedCasError<StoreError>>;

/// Loads, appends, and conditionally publishes one externally ordered batch.
///
/// `initial_capacity` is used only when no durable combined state exists.
/// Existing persisted capacity remains authoritative after the first commit.
///
/// # Errors
///
/// Returns load/store, canonical codec, stale order, or transactional FIFO
/// failure. Concurrent state change is typed conflict evidence and is never
/// retried automatically.
pub fn publish_cached_retry_telemetry_ordered_batch_durably<Store>(
    store: &mut Store,
    request: NativeContinuationCachedRetryTelemetryOrderedCasRequest<'_>,
) -> NativeContinuationCachedRetryTelemetryOrderedCasStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    let load = restore_blob(store, request.maximum_bytes)
        .map_err(OrderedCasError::Blob)?;
    let (expected_bytes, previous, mut candidate) = match load {
        BlobLoad::Missing => (
            None,
            None,
            OrderedOwner::new(
                NativeContinuationCachedRetryTelemetryWindow::new(
                    request.initial_capacity,
                ),
            ),
        ),
        BlobLoad::Present { bytes } => {
            let previous = decode_ordered_state(&bytes)?;
            (Some(bytes), Some(previous.clone()), previous)
        },
    };
    let publication = candidate
        .append_ordered_batch(request.order, request.telemetry)
        .map_err(OrderedCasError::Ordered)?;
    let candidate_bytes =
        encode_cached_retry_telemetry_ordered_state(&candidate)
            .map_err(|error| OrderedCasError::Codec(Box::new(error)))?;
    let outcome = compare_and_swap_blob_durably(
        store,
        expected_bytes.as_deref(),
        &candidate_bytes,
        request.maximum_bytes,
    )
    .map_err(OrderedCasError::Blob)?;
    map_publication(outcome, previous, candidate, publication)
}

fn decode_ordered_state<StoreError>(
    bytes: &[u8],
) -> Result<OrderedOwner, OrderedCasError<StoreError>> {
    decode_cached_retry_telemetry_ordered_state(bytes)
        .map_err(|error| OrderedCasError::Codec(Box::new(error)))
}

fn map_publication<StoreError, DurabilityError>(
    outcome: BlobCasDurable<DurabilityError>,
    previous: Option<OrderedOwner>,
    candidate: OrderedOwner,
    publication: NativeContinuationCachedRetryTelemetryOrderedWindowAppend,
) -> MapPublicationResult<StoreError, DurabilityError> {
    match outcome {
        BlobCasDurable::Conflict { current: current_bytes } => {
            let current = current_bytes
                .as_deref()
                .map(decode_ordered_state)
                .transpose()?
                .map(Box::new);
            Ok(OrderedCasOutcome::Conflict {
                current,
                expected: previous.map(Box::new),
            })
        },
        BlobCasDurable::Durable { write } => Ok(OrderedCasOutcome::Durable {
            bytes: write.bytes(),
            current: Box::new(candidate),
            publication,
            previous: previous.map(Box::new),
        }),
        BlobCasDurable::Published { durability_error, write } => {
            Ok(OrderedCasOutcome::Published {
                bytes: write.bytes(),
                current: Box::new(candidate),
                durability_error,
                publication,
                previous: previous.map(Box::new),
            })
        },
    }
}
