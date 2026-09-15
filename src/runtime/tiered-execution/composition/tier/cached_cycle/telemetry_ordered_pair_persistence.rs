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
//   - Atomic persistence of ordered count state plus latency telemetry.
// - Must-Not:
//   - Infer external order, emulate atomicity, merge conflicts, or choose
//     paths.
// - Allows:
//   - Inputs: one ordered count owner, one latency histogram, bounds, pair
//     store.
//   - Outputs: durable publication or exact reconstructed combined evidence.
//   - Side effects: delegated through atomic blob-pair application use cases.
// - Split-When:
//   - Ordered-pair CAS, migration, or reconciliation gains authority.
// - Merge-When:
//   - One distributed telemetry owner subsumes ordered pair persistence.
// - Summary:
//   - Persists external count order and latency evidence in one atomic pair.
// - Description:
//   - First member is ordered count state; second member is latency state.
// - Usage:
//   - Use when restart-safe count ordering must travel with latency telemetry.
// - Defaults:
//   - Missing pair state is explicit and never invents order or telemetry.
//

//! Atomic ordered-count plus latency persistence for cached-retry telemetry.

use std::num::NonZeroUsize;

use pair_port::{
    NativeContinuationBlobPairStore as PairStore,
    NativeContinuationDurableBlobPairStore as DurablePairStore,
};

use super::{
    NativeContinuationCachedRetryLatencyCodecError,
    NativeContinuationCachedRetryLatencyHistogram,
    NativeContinuationCachedRetryLatencySnapshotError,
    NativeContinuationCachedRetryTelemetryOrderedStateCodecError,
    NativeContinuationCachedRetryTelemetryOrderedWindow,
    decode_cached_retry_latency_snapshot as decode_latency,
    decode_cached_retry_telemetry_ordered_state as decode_ordered,
    encode_cached_retry_latency_snapshot as encode_latency,
    encode_cached_retry_telemetry_ordered_state as encode_ordered,
};
use crate::{
    blob_pair_persistence as pair_persistence, blob_pair_store as pair_port,
};

/// Immutable request for one atomic ordered-count plus latency publication.
#[derive(Clone, Copy, Debug)]
pub struct NativeContinuationCachedRetryTelemetryOrderedPairPersistenceRequest<
    'state,
> {
    count_maximum_bytes: NonZeroUsize,
    histogram: &'state NativeContinuationCachedRetryLatencyHistogram,
    latency_maximum_bytes: NonZeroUsize,
    ordered: &'state NativeContinuationCachedRetryTelemetryOrderedWindow,
}

impl<'state>
    NativeContinuationCachedRetryTelemetryOrderedPairPersistenceRequest<'state>
{
    /// Constructs one explicit ordered telemetry-pair persistence request.
    #[must_use]
    pub const fn new(
        ordered: &'state NativeContinuationCachedRetryTelemetryOrderedWindow,
        histogram: &'state NativeContinuationCachedRetryLatencyHistogram,
        maximum_bytes: (NonZeroUsize, NonZeroUsize),
    ) -> Self {
        let (count_maximum_bytes, latency_maximum_bytes) = maximum_bytes;
        Self {
            count_maximum_bytes,
            histogram,
            latency_maximum_bytes,
            ordered,
        }
    }
}

/// Durable ordered telemetry-pair publication plus explicit durability state.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryTelemetryOrderedPairDurablePersistence<
    DurabilityError,
> {
    /// Atomic publication and durability confirmation both completed.
    Durable {
        /// Exact canonical member byte counts.
        write:
            NativeContinuationCachedRetryTelemetryOrderedPairPersistenceWrite,
    },
    /// Atomic publication committed, then durability confirmation failed.
    Published {
        /// Exact post-publication durability failure.
        durability_error: DurabilityError,
        /// Exact canonical member byte counts.
        write:
            NativeContinuationCachedRetryTelemetryOrderedPairPersistenceWrite,
    },
}

/// Why one ordered telemetry-pair persistence operation failed closed.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryTelemetryOrderedPairPersistenceError<
    StoreError,
> {
    /// Canonical latency framing or semantics failed.
    LatencyCodec(Box<NativeContinuationCachedRetryLatencyCodecError>),
    /// Validated latency snapshot could not reconstruct its live owner.
    LatencySnapshot(Box<NativeContinuationCachedRetryLatencySnapshotError>),
    /// Canonical ordered count framing or nested count semantics failed.
    OrderedCodec(
        Box<NativeContinuationCachedRetryTelemetryOrderedStateCodecError>,
    ),
    /// Atomic pair application orchestration or its outbound store failed.
    Pair(
        pair_persistence::NativeContinuationBlobPairPersistenceError<
            StoreError,
        >,
    ),
}

/// Result of one atomic ordered telemetry-pair restoration.
#[derive(Clone, Debug)]
pub enum NativeContinuationCachedRetryTelemetryOrderedPairPersistenceLoad {
    /// No ordered count plus latency pair currently exists.
    Missing,
    /// Both canonical members reconstructed exact live telemetry owners.
    Restored {
        /// Exact canonical ordered-count member byte count.
        count_bytes: usize,
        /// Reconstructed exact latency histogram.
        histogram: Box<NativeContinuationCachedRetryLatencyHistogram>,
        /// Exact canonical latency member byte count.
        latency_bytes: usize,
        /// Reconstructed exact ordered count owner.
        ordered: Box<NativeContinuationCachedRetryTelemetryOrderedWindow>,
    },
}

/// Exact canonical member byte counts from one committed publication.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryTelemetryOrderedPairPersistenceWrite {
    count_bytes: usize,
    latency_bytes: usize,
}

/// Durable ordered telemetry-pair result specialized to one pair store.
pub type NativeContinuationCachedRetryTelemetryOrderedPairDurableStoreResult<
    Store,
> = Result<
    NativeContinuationCachedRetryTelemetryOrderedPairDurablePersistence<
        <Store as DurablePairStore>::DurabilityError,
    >,
    NativeContinuationCachedRetryTelemetryOrderedPairPersistenceError<
        <Store as PairStore>::Error,
    >,
>;

/// Ordered telemetry-pair restoration result specialized to one pair store.
pub type NativeContinuationCachedRetryTelemetryOrderedPairLoadStoreResult<
    Store,
> = Result<
    NativeContinuationCachedRetryTelemetryOrderedPairPersistenceLoad,
    NativeContinuationCachedRetryTelemetryOrderedPairPersistenceError<
        <Store as PairStore>::Error,
    >,
>;

type PairDurable<DurabilityError> =
    pair_persistence::NativeContinuationBlobPairDurablePersistence<
        DurabilityError,
    >;
type PairError<StoreError> =
    NativeContinuationCachedRetryTelemetryOrderedPairPersistenceError<
        StoreError,
    >;
type PairLoad = pair_persistence::NativeContinuationBlobPairPersistenceLoad;
type OrderedPairRequest<'state> =
    NativeContinuationCachedRetryTelemetryOrderedPairPersistenceRequest<'state>;
type OrderedPairLoad =
    NativeContinuationCachedRetryTelemetryOrderedPairPersistenceLoad;
type PairOutcome<DurabilityError> =
    NativeContinuationCachedRetryTelemetryOrderedPairDurablePersistence<
        DurabilityError,
    >;
type PairWrite =
    NativeContinuationCachedRetryTelemetryOrderedPairPersistenceWrite;

impl<DurabilityError>
    NativeContinuationCachedRetryTelemetryOrderedPairDurablePersistence<
        DurabilityError,
    >
{
    /// Returns post-publication durability failure when confirmation failed.
    #[must_use]
    pub const fn durability_error(&self) -> Option<&DurabilityError> {
        match self {
            Self::Durable { .. } => None,
            Self::Published { durability_error, .. } => Some(durability_error),
        }
    }

    /// Reports whether pair durability was explicitly confirmed.
    #[must_use]
    pub const fn is_durable(&self) -> bool {
        matches!(self, Self::Durable { .. })
    }

    /// Returns exact committed canonical byte counts for both members.
    #[must_use]
    pub const fn write(&self) -> PairWrite {
        match self {
            Self::Durable { write } | Self::Published { write, .. } => *write,
        }
    }
}

impl NativeContinuationCachedRetryTelemetryOrderedPairPersistenceWrite {
    /// Returns exact canonical ordered-count member byte count.
    #[must_use]
    pub const fn count_bytes(self) -> usize {
        self.count_bytes
    }

    /// Returns exact canonical latency member byte count.
    #[must_use]
    pub const fn latency_bytes(self) -> usize {
        self.latency_bytes
    }
}

/// Atomically persists ordered count plus latency telemetry and confirms
/// durability.
///
/// # Errors
///
/// Returns codec, byte-limit, or pair-store failure before publication commits.
pub fn persist_cached_retry_telemetry_ordered_pair_durably<Store>(
    store: &mut Store,
    request: OrderedPairRequest<'_>,
) -> NativeContinuationCachedRetryTelemetryOrderedPairDurableStoreResult<Store>
where
    Store: DurablePairStore,
{
    let count = encode_ordered(request.ordered)
        .map_err(|error| PairError::OrderedCodec(Box::new(error)))?;
    let latency = encode_latency(&request.histogram.snapshot())
        .map_err(|error| PairError::LatencyCodec(Box::new(error)))?;
    let outcome = pair_persistence::persist_blob_pair_durably(
        store,
        pair_persistence::NativeContinuationBlobPairPersistenceRequest::new(
            &count,
            &latency,
            request.count_maximum_bytes,
            request.latency_maximum_bytes,
        ),
    )
    .map_err(PairError::Pair)?;
    Ok(match outcome {
        PairDurable::Durable { write } => PairOutcome::Durable {
            write: PairWrite {
                count_bytes: write.first_bytes(),
                latency_bytes: write.second_bytes(),
            },
        },
        PairDurable::Published { durability_error, write } => {
            PairOutcome::Published {
                durability_error,
                write: PairWrite {
                    count_bytes: write.first_bytes(),
                    latency_bytes: write.second_bytes(),
                },
            }
        },
    })
}

/// Atomically restores ordered count plus latency telemetry from one pair.
///
/// # Errors
///
/// Returns pair-store, byte-limit, codec, or reconstruction evidence without
/// inventing either owner for missing pair state.
pub fn restore_cached_retry_telemetry_ordered_pair<Store>(
    store: &mut Store,
    count_maximum_bytes: NonZeroUsize,
    latency_maximum_bytes: NonZeroUsize,
) -> NativeContinuationCachedRetryTelemetryOrderedPairLoadStoreResult<Store>
where
    Store: PairStore,
{
    let load = pair_persistence::restore_blob_pair(
        store,
        count_maximum_bytes,
        latency_maximum_bytes,
    )
    .map_err(PairError::Pair)?;
    let PairLoad::Present { first, second } = load else {
        return Ok(OrderedPairLoad::Missing);
    };
    let count_bytes = first.len();
    let ordered = decode_ordered(&first)
        .map_err(|error| PairError::OrderedCodec(Box::new(error)))?;
    let latency_bytes = second.len();
    let latency_snapshot = decode_latency(&second)
        .map_err(|error| PairError::LatencyCodec(Box::new(error)))?;
    let histogram =
        NativeContinuationCachedRetryLatencyHistogram::from_snapshot(
            latency_snapshot,
        )
        .map_err(|error| PairError::LatencySnapshot(Box::new(error)))?;
    Ok(OrderedPairLoad::Restored {
        count_bytes,
        histogram: Box::new(histogram),
        latency_bytes,
        ordered: Box::new(ordered),
    })
}
