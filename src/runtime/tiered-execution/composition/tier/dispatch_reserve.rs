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
//   - Canonical durable coordination state for exact dispatch and timing
//     reservation watermarks plus one-field-at-a-time conditional transitions.
// - Must-Not:
//   - Persist affine handoffs, clock starts, latency samples, queue capacities,
//     choose storage paths, spawn workers, or infer distributed scheduling.
// - Allows:
//   - Inputs: optional expected combined state, explicit reservation kind,
//     positive byte bound, and one conditional durable store.
//   - Outputs: restored combined state, exact conflict state, committed next
//     state, committed sync failure, or typed codec/storage/exhaustion failure.
//   - Side effects: one delegated conditional durable blob publication.
// - Split-When:
//   - Affine queue contents, multi-item transactions, or distributed consensus
//     gains authority.
// - Merge-When:
//   - Durable queue orchestration owns reservation and affine enqueue/dispatch
//     atomically.
// - Summary:
//   - Coordinates dispatch and timing reservations in one canonical CAS frame.
// - Description:
//   - Each transition advances exactly one selected watermark by one.
// - Usage:
//   - Restore state, reserve one identity, then bind it to the local queue.
// - Defaults:
//   - Missing durable state represents dispatch zero and timing zero.
//

//! Canonical combined durable reservation state for dispatch orchestration.

use std::num::NonZeroUsize;

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
use crate::{cached_cycle as cycle, continuation_dispatch_queue as queue};

const CODEC_LEN: usize = 24;
const IDENTITY_OFFSET: usize = 8;
const MAGIC: [u8; 8] = *b"MBDQRS01";
const TIMING_OFFSET: usize = 16;

type DispatchWatermark = queue::NativeContinuationDispatchIdentityWatermark;
type TimingWatermark =
    cycle::NativeContinuationCachedRetryLatencyIntervalWatermark;
type ReservationState = queue::NativeContinuationDispatchQueueWatermarks;

/// Which durable queue reservation watermark advances in one transition.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchReservationKind {
    /// Reserve exactly the next dispatch/work identity.
    Identity,
    /// Reserve exactly the next latency timing identity.
    Timing,
}

/// Canonical combined reservation-state framing failure.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchReservationStateCodecError {
    /// Frame length differed from the fixed canonical size.
    Length {
        /// Exact observed frame byte count.
        observed: usize,
    },
    /// Canonical magic/version prefix differed.
    Magic,
}

/// Typed durable combined reservation-state CAS outcome.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchReservationStateCas<DurabilityError> {
    /// Durable bytes differed from the caller's expected combined state.
    Conflict {
        /// Exact current durable state, or missing state.
        current: Option<ReservationState>,
        /// Caller-supplied expected durable state.
        expected: Option<ReservationState>,
    },
    /// Next combined state committed and durability confirmation completed.
    Durable {
        /// Exact canonical byte count committed by the store.
        bytes: usize,
        /// Exact newly committed combined state.
        current: ReservationState,
        /// Exact prior combined state, or missing state before first
        /// reservation.
        previous: Option<ReservationState>,
    },
    /// Next combined state committed, then durability confirmation failed.
    Published {
        /// Exact canonical byte count committed by the store.
        bytes: usize,
        /// Exact newly committed combined state.
        current: ReservationState,
        /// Exact post-publication durability failure.
        durability_error: DurabilityError,
        /// Exact prior combined state, or missing state before first
        /// reservation.
        previous: Option<ReservationState>,
    },
}

/// Why one combined reservation transition failed before an outcome.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchReservationStateCasError<StoreError> {
    /// Bounded conditional blob orchestration or outbound store failed.
    Blob(NativeContinuationBlobPersistenceError<StoreError>),
    /// Current durable bytes failed canonical combined-state framing.
    Codec(NativeContinuationDispatchReservationStateCodecError),
    /// Selected watermark cannot advance beyond `u64::MAX`.
    WatermarkExhausted {
        /// Exact reservation kind whose identity space is exhausted.
        reservation: NativeContinuationDispatchReservationKind,
    },
}

/// Result of bounded durable combined reservation-state restoration.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchReservationStateLoad {
    /// No combined durable reservation state currently exists.
    Missing,
    /// Exact decoded combined state restored from canonical durable bytes.
    Restored(ReservationState),
}

/// Why bounded combined-state restoration failed.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchReservationStateLoadError<StoreError> {
    /// Bounded blob restoration or outbound store failed.
    Blob(NativeContinuationBlobPersistenceError<StoreError>),
    /// Restored bytes failed canonical combined-state framing.
    Codec(NativeContinuationDispatchReservationStateCodecError),
}

type CasError<StoreError> =
    NativeContinuationDispatchReservationStateCasError<StoreError>;
type LoadError<StoreError> =
    NativeContinuationDispatchReservationStateLoadError<StoreError>;

/// Typed combined-state CAS result specialized to one durable store.
pub type NativeContinuationDispatchReservationStateCasStoreResult<Store> =
    Result<
        NativeContinuationDispatchReservationStateCas<
            <Store as DurableBlobStore>::DurabilityError,
        >,
        NativeContinuationDispatchReservationStateCasError<
            <Store as BlobStore>::Error,
        >,
    >;

/// Typed combined-state load result specialized to one blob store.
pub type NativeContinuationDispatchReservationStateLoadStoreResult<Store> =
    Result<
        NativeContinuationDispatchReservationStateLoad,
        NativeContinuationDispatchReservationStateLoadError<
            <Store as BlobStore>::Error,
        >,
    >;

/// Decodes one exact canonical combined reservation-state frame.
///
/// # Errors
///
/// Returns fixed framing rejection for length or magic/version drift.
pub fn decode_native_continuation_dispatch_reservation_state(
    bytes: &[u8],
) -> Result<
    ReservationState,
    NativeContinuationDispatchReservationStateCodecError,
> {
    if bytes.len() != CODEC_LEN {
        return Err(
            NativeContinuationDispatchReservationStateCodecError::Length {
                observed: bytes.len(),
            },
        );
    }
    if !bytes.iter().take(MAGIC.len()).copied().eq(MAGIC) {
        return Err(
            NativeContinuationDispatchReservationStateCodecError::Magic,
        );
    }
    let identity = decode_u64(bytes, IDENTITY_OFFSET);
    let timing = decode_u64(bytes, TIMING_OFFSET);
    Ok(ReservationState::new(
        DispatchWatermark::from_value(identity),
        TimingWatermark::from_value(timing),
    ))
}

/// Encodes combined dispatch/timing reservation watermarks as canonical bytes.
#[must_use]
pub fn encode_native_continuation_dispatch_reservation_state(
    state: ReservationState,
) -> [u8; CODEC_LEN] {
    let mut bytes = [0u8; CODEC_LEN];
    for (slot, byte) in bytes.iter_mut().take(MAGIC.len()).zip(MAGIC) {
        *slot = byte;
    }
    for (slot, byte) in bytes
        .iter_mut()
        .skip(IDENTITY_OFFSET)
        .take(8)
        .zip(state.identity().value().to_le_bytes())
    {
        *slot = byte;
    }
    for (slot, byte) in bytes
        .iter_mut()
        .skip(TIMING_OFFSET)
        .take(8)
        .zip(state.timing().value().to_le_bytes())
    {
        *slot = byte;
    }
    bytes
}

/// Restores one bounded canonical combined reservation state.
///
/// # Errors
///
/// Returns bounded blob failure or canonical framing rejection.
pub fn restore_native_continuation_dispatch_reservation_state<Store>(
    store: &mut Store,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationDispatchReservationStateLoadStoreResult<Store>
where
    Store: BlobStore,
{
    match restore_blob(store, maximum_bytes).map_err(LoadError::Blob)? {
        BlobLoad::Missing => {
            Ok(NativeContinuationDispatchReservationStateLoad::Missing)
        },
        BlobLoad::Present { bytes } => {
            let state =
                decode_native_continuation_dispatch_reservation_state(&bytes)
                    .map_err(LoadError::Codec)?;
            Ok(NativeContinuationDispatchReservationStateLoad::Restored(
                state,
            ))
        },
    }
}

/// Advances exactly one selected watermark in combined durable queue state.
///
/// # Errors
///
/// Returns selected-watermark exhaustion, framing rejection, byte-limit
/// failure, or outbound store failure before a typed outcome can be returned.
pub fn reserve_native_continuation_dispatch_identity_durably<Store>(
    store: &mut Store,
    expected: Option<ReservationState>,
    reservation: NativeContinuationDispatchReservationKind,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationDispatchReservationStateCasStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    let base = expected.unwrap_or_else(zero_state);
    let current = advance_state(base, reservation)
        .ok_or(CasError::WatermarkExhausted { reservation })?;
    let expected_bytes =
        expected.map(encode_native_continuation_dispatch_reservation_state);
    let current_bytes =
        encode_native_continuation_dispatch_reservation_state(current);
    let outcome = compare_and_swap_blob_durably(
        store,
        expected_bytes.as_ref().map(<[u8; CODEC_LEN]>::as_slice),
        &current_bytes,
        maximum_bytes,
    )
    .map_err(CasError::Blob)?;
    match outcome {
        BlobCasDurable::Conflict { current: bytes } => {
            let durable_current = bytes
                .as_deref()
                .map(decode_native_continuation_dispatch_reservation_state)
                .transpose()
                .map_err(CasError::Codec)?;
            Ok(NativeContinuationDispatchReservationStateCas::Conflict {
                current: durable_current,
                expected,
            })
        },
        BlobCasDurable::Durable { write } => {
            Ok(NativeContinuationDispatchReservationStateCas::Durable {
                bytes: write.bytes(),
                current,
                previous: expected,
            })
        },
        BlobCasDurable::Published { durability_error, write } => {
            Ok(NativeContinuationDispatchReservationStateCas::Published {
                bytes: write.bytes(),
                current,
                durability_error,
                previous: expected,
            })
        },
    }
}

fn advance_state(
    state: ReservationState,
    reservation: NativeContinuationDispatchReservationKind,
) -> Option<ReservationState> {
    let identity = state.identity().value();
    let timing = state.timing().value();
    match reservation {
        NativeContinuationDispatchReservationKind::Identity => {
            Some(ReservationState::new(
                DispatchWatermark::from_value(identity.checked_add(1)?),
                TimingWatermark::from_value(timing),
            ))
        },
        NativeContinuationDispatchReservationKind::Timing => {
            Some(ReservationState::new(
                DispatchWatermark::from_value(identity),
                TimingWatermark::from_value(timing.checked_add(1)?),
            ))
        },
    }
}

fn decode_u64(bytes: &[u8], start: usize) -> u64 {
    let mut value = [0u8; 8];
    for (slot, byte) in value
        .iter_mut()
        .zip(bytes.iter().skip(start).take(8).copied())
    {
        *slot = byte;
    }
    u64::from_le_bytes(value)
}

const fn zero_state() -> ReservationState {
    ReservationState::new(
        DispatchWatermark::from_value(0),
        TimingWatermark::from_value(0),
    )
}
