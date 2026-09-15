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
//   - Binding canonical count and latency telemetry to one atomic blob pair.
// - Must-Not:
//   - Choose storage locations, emulate atomicity, merge state, or select
//     policy.
// - Allows:
//   - Inputs: one count window, one latency histogram, bounds, and pair store.
//   - Outputs: atomic durable publication or exact reconstructed pair evidence.
//   - Side effects: delegated through atomic pair-persistence application use
//     cases.
// - Split-When:
//   - Migration or another telemetry-pair revision gains authority.
// - Merge-When:
//   - One cached-cycle transaction owner owns pair persistence and merging.
// - Summary:
//   - Persists canonical count and latency telemetry as one atomic pair.
// - Description:
//   - First member is count bytes; second member is latency bytes.
// - Usage:
//   - Use only with a store that actually implements atomic pair replacement.
// - Defaults:
//   - Missing pair state is explicit and never invents either telemetry owner.
//

//! Atomic count plus latency persistence for cached-retry telemetry.

use std::num::NonZeroUsize;

use pair_port::{
    NativeContinuationBlobPairStore as PairStore,
    NativeContinuationDurableBlobPairStore as DurablePairStore,
};

use super::{
    NativeContinuationCachedRetryLatencyCodecError,
    NativeContinuationCachedRetryLatencyHistogram,
    NativeContinuationCachedRetryLatencySnapshotError,
    NativeContinuationCachedRetryTelemetryCodecError,
    NativeContinuationCachedRetryTelemetrySnapshotError,
    NativeContinuationCachedRetryTelemetryWindow,
    decode_cached_retry_latency_snapshot as decode_latency,
    decode_cached_retry_telemetry_snapshot as decode_count,
    encode_cached_retry_latency_snapshot as encode_latency,
    encode_cached_retry_telemetry_snapshot as encode_count,
};
use crate::{
    blob_pair_persistence as pair_persistence, blob_pair_store as pair_port,
};

/// Immutable request for one atomic count plus latency publication.
#[derive(Clone, Copy, Debug)]
pub struct NativeContinuationCachedRetryTelemetryPairPersistenceRequest<'state>
{
    count_maximum_bytes: NonZeroUsize,
    histogram: &'state NativeContinuationCachedRetryLatencyHistogram,
    latency_maximum_bytes: NonZeroUsize,
    window: &'state NativeContinuationCachedRetryTelemetryWindow,
}

impl<'state>
    NativeContinuationCachedRetryTelemetryPairPersistenceRequest<'state>
{
    /// Constructs one explicit typed atomic telemetry-pair request.
    #[must_use]
    pub const fn new(
        window: &'state NativeContinuationCachedRetryTelemetryWindow,
        histogram: &'state NativeContinuationCachedRetryLatencyHistogram,
        count_maximum_bytes: NonZeroUsize,
        latency_maximum_bytes: NonZeroUsize,
    ) -> Self {
        Self {
            count_maximum_bytes,
            histogram,
            latency_maximum_bytes,
            window,
        }
    }
}

#[derive(Clone, Debug)]
pub(super) struct DecodedCachedRetryTelemetryPair {
    pub count_bytes: usize,
    pub histogram: NativeContinuationCachedRetryLatencyHistogram,
    pub latency_bytes: usize,
    pub window: NativeContinuationCachedRetryTelemetryWindow,
}

/// Typed atomic telemetry-pair publication plus explicit durability state.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryTelemetryPairDurablePersistence<
    DurabilityError,
> {
    /// Atomic pair publication and durability confirmation both completed.
    Durable {
        /// Exact canonical pair byte counts.
        write: NativeContinuationCachedRetryTelemetryPairPersistenceWrite,
    },
    /// Atomic pair publication committed, then durability confirmation failed.
    Published {
        /// Exact post-publication pair durability failure.
        durability_error: DurabilityError,
        /// Exact canonical pair byte counts.
        write: NativeContinuationCachedRetryTelemetryPairPersistenceWrite,
    },
}

/// Why one typed atomic telemetry-pair operation failed closed.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryTelemetryPairPersistenceError<StoreError>
{
    /// Canonical count framing or semantics failed.
    CountCodec(Box<NativeContinuationCachedRetryTelemetryCodecError>),
    /// Validated count snapshot could not reconstruct its live owner.
    CountSnapshot(Box<NativeContinuationCachedRetryTelemetrySnapshotError>),
    /// Canonical latency framing or semantics failed.
    LatencyCodec(Box<NativeContinuationCachedRetryLatencyCodecError>),
    /// Validated latency snapshot could not reconstruct its live owner.
    LatencySnapshot(Box<NativeContinuationCachedRetryLatencySnapshotError>),
    /// Atomic pair application orchestration or its outbound store failed.
    Pair(
        pair_persistence::NativeContinuationBlobPairPersistenceError<
            StoreError,
        >,
    ),
}

/// Result of one atomic typed telemetry-pair restoration.
#[derive(Clone, Debug)]
pub enum NativeContinuationCachedRetryTelemetryPairPersistenceLoad {
    /// No atomic count plus latency pair currently exists.
    Missing,
    /// Both canonical members reconstructed exact live telemetry owners.
    Restored {
        /// Exact canonical count member byte count.
        count_bytes: usize,
        /// Reconstructed exact latency histogram.
        histogram: Box<NativeContinuationCachedRetryLatencyHistogram>,
        /// Exact canonical latency member byte count.
        latency_bytes: usize,
        /// Reconstructed exact count window.
        window: Box<NativeContinuationCachedRetryTelemetryWindow>,
    },
}

/// Exact canonical pair byte counts from one committed publication.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryTelemetryPairPersistenceWrite {
    count_bytes: usize,
    latency_bytes: usize,
}

/// Durable typed telemetry-pair result specialized to one pair store.
pub type NativeContinuationCachedRetryTelemetryPairDurableStoreResult<Store> =
    Result<
        NativeContinuationCachedRetryTelemetryPairDurablePersistence<
            <Store as DurablePairStore>::DurabilityError,
        >,
        NativeContinuationCachedRetryTelemetryPairPersistenceError<
            <Store as PairStore>::Error,
        >,
    >;

/// Typed telemetry-pair restoration result specialized to one pair store.
pub type NativeContinuationCachedRetryTelemetryPairLoadStoreResult<Store> =
    Result<
        NativeContinuationCachedRetryTelemetryPairPersistenceLoad,
        NativeContinuationCachedRetryTelemetryPairPersistenceError<
            <Store as PairStore>::Error,
        >,
    >;

type PairDurable<DurabilityError> =
    pair_persistence::NativeContinuationBlobPairDurablePersistence<
        DurabilityError,
    >;
type PairError<StoreError> =
    NativeContinuationCachedRetryTelemetryPairPersistenceError<StoreError>;
type PairLoad = pair_persistence::NativeContinuationBlobPairPersistenceLoad;
type PairOutcome<DurabilityError> =
    NativeContinuationCachedRetryTelemetryPairDurablePersistence<
        DurabilityError,
    >;
type PairWrite = NativeContinuationCachedRetryTelemetryPairPersistenceWrite;

impl<DurabilityError>
    NativeContinuationCachedRetryTelemetryPairDurablePersistence<
        DurabilityError,
    >
{
    /// Returns post-publication pair durability failure when confirmation
    /// failed.
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

impl NativeContinuationCachedRetryTelemetryPairPersistenceWrite {
    /// Returns exact canonical count member byte count.
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

/// Atomically persists count and latency telemetry and confirms pair
/// durability.
///
/// # Errors
///
/// Returns codec, byte-limit, or pair-store failure before publication commits.
pub fn persist_cached_retry_telemetry_pair_durably<Store>(
    store: &mut Store,
    request: NativeContinuationCachedRetryTelemetryPairPersistenceRequest<'_>,
) -> NativeContinuationCachedRetryTelemetryPairDurableStoreResult<Store>
where
    Store: DurablePairStore,
{
    let count = encode_count(&request.window.snapshot())
        .map_err(|error| PairError::CountCodec(Box::new(error)))?;
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

/// Atomically restores count and latency telemetry from one durable pair.
///
/// # Errors
///
/// Returns pair-store, byte-limit, codec, or reconstruction evidence without
/// inventing either owner for missing pair state.
pub fn restore_cached_retry_telemetry_pair<Store>(
    store: &mut Store,
    count_maximum_bytes: NonZeroUsize,
    latency_maximum_bytes: NonZeroUsize,
) -> NativeContinuationCachedRetryTelemetryPairLoadStoreResult<Store>
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
        return Ok(
            NativeContinuationCachedRetryTelemetryPairPersistenceLoad::Missing,
        );
    };
    let decoded = decode_cached_retry_telemetry_pair(&first, &second)?;
    Ok(
        NativeContinuationCachedRetryTelemetryPairPersistenceLoad::Restored {
            count_bytes: decoded.count_bytes,
            histogram: Box::new(decoded.histogram),
            latency_bytes: decoded.latency_bytes,
            window: Box::new(decoded.window),
        },
    )
}

pub(super) fn decode_cached_retry_telemetry_pair<StoreError>(
    first: &[u8],
    second: &[u8],
) -> Result<
    DecodedCachedRetryTelemetryPair,
    NativeContinuationCachedRetryTelemetryPairPersistenceError<StoreError>,
> {
    let count_bytes = first.len();
    let count_snapshot = decode_count(first)
        .map_err(|error| PairError::CountCodec(Box::new(error)))?;
    let window = NativeContinuationCachedRetryTelemetryWindow::from_snapshot(
        count_snapshot,
    )
    .map_err(|error| PairError::CountSnapshot(Box::new(error)))?;
    let latency_bytes = second.len();
    let latency_snapshot = decode_latency(second)
        .map_err(|error| PairError::LatencyCodec(Box::new(error)))?;
    let histogram =
        NativeContinuationCachedRetryLatencyHistogram::from_snapshot(
            latency_snapshot,
        )
        .map_err(|error| PairError::LatencySnapshot(Box::new(error)))?;
    Ok(DecodedCachedRetryTelemetryPair {
        count_bytes,
        histogram,
        latency_bytes,
        window,
    })
}
