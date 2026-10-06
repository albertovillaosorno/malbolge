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
//   - Inputs: optional expected combined state, local queue watermarks or one
//     exclusively borrowed queue, optional affine enqueue owner, explicit
//     reservation kind, positive byte bound, and one conditional durable store.
//   - Outputs: restored combined state, exact conflict state, committed next
//     state, bound dispatch identity or timed FIFO handoff, committed sync
//     failure, or typed queue/codec/storage/exhaustion failure.
//   - Side effects: one delegated conditional durable blob publication and, for
//     composed paths, one process-local enqueue or timing dispatch after
//     commit.
// - Split-When:
//   - Affine queue contents, multi-item transactions, or distributed consensus
//     gains authority.
// - Merge-When:
//   - Durable queue orchestration owns reservation and affine enqueue/dispatch
//     atomically.
// - Summary:
//   - Coordinates dispatch and timing reservations in one canonical CAS frame.
// - Description:
//   - Each transition advances exactly one selected watermark by one; composed
//     enqueue and timing dispatch preflight local admission before publication.
// - Usage:
//   - Restore state, reserve explicitly, or durably bind one identity enqueue
//     or one timing dispatch through the composed boundary.
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
use crate::interpreter_handoff::NativeInterpreterHandoff;
use crate::monotonic_clock::NativeContinuationMonotonicClock;
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

/// Immutable inputs for one queue-synchronized durable reservation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationDispatchReservationRequest {
    expected: Option<ReservationState>,
    maximum_bytes: NonZeroUsize,
    reservation: NativeContinuationDispatchReservationKind,
}

/// Inputs for one durable identity reservation plus local affine enqueue.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationDispatchDurableEnqueueRequest {
    expected: Option<ReservationState>,
    maximum_bytes: NonZeroUsize,
}

/// Inputs for one durable timing reservation plus local FIFO dispatch.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationDispatchDurableTimingRequest {
    expected: Option<ReservationState>,
    maximum_bytes: NonZeroUsize,
}

/// Why durable timing dispatch cannot begin before storage access.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchDurableTimingPreflightError {
    /// The configured in-flight timing bound is already full.
    Capacity {
        /// Exact number of dispatches awaiting completion.
        in_flight: usize,
        /// Positive configured concurrent dispatch bound.
        maximum_in_flight: NonZeroUsize,
    },
    /// No pending affine handoff exists to bind to a timing reservation.
    Idle,
}

/// Why a committed timing reservation unexpectedly failed local binding.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchDurableTimingBindFailure {
    /// Exact interval-begin failure returned by the local queue.
    Begin(cycle::NativeContinuationCachedRetryLatencyIntervalBeginError),
    /// The queue reported no pending handoff after successful preflight.
    MissingPending,
}

/// Result of durably reserving and binding one dispatch timing identity.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchDurableTiming<DurabilityError> {
    /// Durable timing committed and the oldest affine owner was dispatched.
    Bound {
        /// Exact caller-owned dispatched handoff.
        dispatch: Box<queue::NativeContinuationDispatchedHandoff>,
        /// Exact durable commit or committed durability-failure evidence.
        reservation:
            NativeContinuationDispatchReservationStateCas<DurabilityError>,
    },
    /// Durable timing committed but local binding unexpectedly failed.
    CommittedUnbound {
        /// Exact non-mutating local binding failure.
        failure: NativeContinuationDispatchDurableTimingBindFailure,
        /// Exact durable commit evidence that must be rebound locally.
        reservation:
            NativeContinuationDispatchReservationStateCas<DurabilityError>,
    },
    /// Durable state changed concurrently; local queue is unchanged.
    Conflict {
        /// Exact current durable state observed by the conditional store.
        current: Option<ReservationState>,
        /// Caller-supplied expected durable state.
        expected: Option<ReservationState>,
    },
}

/// Why durable reserve-and-dispatch failed before a durable outcome existed.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchDurableTimingError<StoreError> {
    /// Local queue cannot dispatch one timing reservation yet.
    Queue(NativeContinuationDispatchDurableTimingPreflightError),
    /// Durable timing reservation failed before commit/conflict evidence.
    Reservation(NativeContinuationDispatchReservationStateCasError<StoreError>),
}

/// Result of durably reserving and immediately binding one dispatch identity.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchDurableEnqueue<DurabilityError> {
    /// Durable reservation committed and the exact identity entered the queue.
    Bound {
        /// Exact process-local dispatch identity now owning the handoff.
        dispatch: queue::NativeContinuationDispatchId,
        /// Exact durable commit or committed durability-failure evidence.
        reservation:
            NativeContinuationDispatchReservationStateCas<DurabilityError>,
    },
    /// Durable reservation committed but local binding unexpectedly failed.
    ///
    /// This is fail-closed recovery evidence: the retained handoff may be
    /// retried with the committed reservation while synchronization prevents a
    /// later reservation from advancing past it.
    CommittedUnbound {
        /// Exact local enqueue failure retaining affine handoff ownership.
        failure: Box<queue::NativeContinuationDispatchEnqueueFailure>,
        /// Exact durable commit evidence that must be rebound locally.
        reservation:
            NativeContinuationDispatchReservationStateCas<DurabilityError>,
    },
    /// Durable state changed concurrently; local queue and handoff are
    /// unchanged.
    Conflict {
        /// Exact current durable state observed by the conditional store.
        current: Option<ReservationState>,
        /// Caller-supplied expected durable state.
        expected: Option<ReservationState>,
        /// Exact affine handoff never transferred to the queue.
        handoff: Box<NativeInterpreterHandoff>,
    },
}

/// Why durable reserve-and-enqueue failed before a durable outcome existed.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchDurableEnqueueError<StoreError> {
    /// Local queue cannot accept the exact next reserved identity.
    Queue {
        /// Exact non-mutating local admission error.
        error: queue::NativeContinuationDispatchEnqueueError,
        /// Exact affine handoff never transferred to the queue.
        handoff: Box<NativeInterpreterHandoff>,
    },
    /// Durable reservation failed before commit/conflict evidence existed.
    Reservation {
        /// Exact durable reservation failure.
        error: NativeContinuationDispatchReservationStateCasError<StoreError>,
        /// Exact affine handoff never transferred to the queue.
        handoff: Box<NativeInterpreterHandoff>,
    },
}

impl NativeContinuationDispatchDurableEnqueueRequest {
    /// Constructs one exact durable identity enqueue request.
    #[must_use]
    pub const fn new(
        expected: Option<ReservationState>,
        maximum_bytes: NonZeroUsize,
    ) -> Self {
        Self { expected, maximum_bytes }
    }
}

impl NativeContinuationDispatchDurableTimingRequest {
    /// Constructs one exact durable timing dispatch request.
    #[must_use]
    pub const fn new(
        expected: Option<ReservationState>,
        maximum_bytes: NonZeroUsize,
    ) -> Self {
        Self { expected, maximum_bytes }
    }
}

impl NativeContinuationDispatchReservationRequest {
    /// Constructs one exact checked reservation request.
    #[must_use]
    pub const fn new(
        expected: Option<ReservationState>,
        reservation: NativeContinuationDispatchReservationKind,
        maximum_bytes: NonZeroUsize,
    ) -> Self {
        Self {
            expected,
            maximum_bytes,
            reservation,
        }
    }
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
    /// Process-local queue watermarks do not match the durable state expected
    /// for this reservation.
    LocalStateMismatch {
        /// Exact process-local queue watermarks observed before storage
        /// access.
        local: ReservationState,
        /// Caller-supplied expected durable state, or missing state.
        expected: Option<ReservationState>,
    },
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

#[derive(Debug)]
enum DurableEnqueuePreflightError<StoreError> {
    Queue(queue::NativeContinuationDispatchEnqueueError),
    Reservation(NativeContinuationDispatchReservationStateCasError<StoreError>),
}

/// Typed durable identity enqueue result specialized to one durable store.
pub type NativeContinuationDispatchDurableEnqueueStoreResult<Store> = Result<
    NativeContinuationDispatchDurableEnqueue<
        <Store as DurableBlobStore>::DurabilityError,
    >,
    NativeContinuationDispatchDurableEnqueueError<<Store as BlobStore>::Error>,
>;

/// Typed durable timing dispatch result specialized to one durable store.
pub type NativeContinuationDispatchDurableTimingStoreResult<Store> = Result<
    NativeContinuationDispatchDurableTiming<
        <Store as DurableBlobStore>::DurabilityError,
    >,
    NativeContinuationDispatchDurableTimingError<<Store as BlobStore>::Error>,
>;

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

/// Advances exactly one selected watermark only while local queue watermarks
/// are synchronized with the caller's durable-state expectation.
///
/// This guard prevents a caller from publishing a second reservation after a
/// prior durable reservation has not yet been bound to the reconstructed local
/// queue. It does not persist or inspect affine handoff ownership.
///
/// # Errors
///
/// Returns local/durable watermark drift before any store access, or delegates
/// selected-watermark exhaustion, framing, byte-limit, and storage failures to
/// the durable reservation operation.
pub fn reserve_native_continuation_dispatch_if_synchronized_durably<
    Clock,
    Store,
>(
    store: &mut Store,
    local_queue: &queue::NativeContinuationDispatchQueue<Clock>,
    request: NativeContinuationDispatchReservationRequest,
) -> NativeContinuationDispatchReservationStateCasStoreResult<Store>
where
    Clock: NativeContinuationMonotonicClock,
    Store: ConditionalBlobStore + DurableBlobStore,
{
    let local = local_queue.watermarks();
    if local != request.expected.unwrap_or_else(zero_state) {
        return Err(CasError::LocalStateMismatch {
            local,
            expected: request.expected,
        });
    }
    reserve_native_continuation_dispatch_identity_durably(
        store,
        request.expected,
        request.reservation,
        request.maximum_bytes,
    )
}

fn preflight_durable_identity_enqueue<Clock, StoreError>(
    local_queue: &queue::NativeContinuationDispatchQueue<Clock>,
    request: NativeContinuationDispatchDurableEnqueueRequest,
) -> Result<ReservationState, DurableEnqueuePreflightError<StoreError>>
where
    Clock: NativeContinuationMonotonicClock,
{
    let local = local_queue.watermarks();
    let base = request.expected.unwrap_or_else(zero_state);
    if local != base {
        return Err(DurableEnqueuePreflightError::Reservation(
            CasError::LocalStateMismatch {
                local,
                expected: request.expected,
            },
        ));
    }
    let current = advance_state(
        base,
        NativeContinuationDispatchReservationKind::Identity,
    )
    .ok_or(DurableEnqueuePreflightError::Reservation(
        CasError::WatermarkExhausted {
            reservation: NativeContinuationDispatchReservationKind::Identity,
        },
    ))?;
    if local_queue.pending() >= local_queue.maximum_pending().get() {
        return Err(DurableEnqueuePreflightError::Queue(
            queue::NativeContinuationDispatchEnqueueError::Capacity {
                maximum_pending: local_queue.maximum_pending(),
                pending: local_queue.pending(),
            },
        ));
    }
    Ok(current)
}

/// Durably reserves the exact next dispatch identity and binds it locally.
///
/// Local synchronization and queue-capacity admission are checked before the
/// conditional store is touched. With exclusive mutable queue ownership, a
/// committed reservation can then bind through the already-validated exact
/// identity without a caller-visible reservation/enqueue gap. This does not
/// persist affine queue contents and does not claim crash-atomic storage plus
/// process-memory publication.
///
/// # Errors
///
/// Returns local synchronization, watermark exhaustion, queue admission, codec,
/// byte-limit, or storage failure while retaining the exact affine handoff.
pub fn reserve_and_enqueue_native_continuation_dispatch_identity_durably<
    Clock,
    Store,
>(
    store: &mut Store,
    local_queue: &mut queue::NativeContinuationDispatchQueue<Clock>,
    handoff: NativeInterpreterHandoff,
    request: NativeContinuationDispatchDurableEnqueueRequest,
) -> NativeContinuationDispatchDurableEnqueueStoreResult<Store>
where
    Clock: NativeContinuationMonotonicClock,
    Store: ConditionalBlobStore + DurableBlobStore,
{
    let current = match preflight_durable_identity_enqueue(local_queue, request)
    {
        Ok(current) => current,
        Err(preflight_error) => {
            return Err(match preflight_error {
                DurableEnqueuePreflightError::Queue(queue_error) => {
                    NativeContinuationDispatchDurableEnqueueError::Queue {
                        error: queue_error,
                        handoff: Box::new(handoff),
                    }
                },
                DurableEnqueuePreflightError::Reservation(
                    reservation_error,
                ) => {
                    NativeContinuationDispatchDurableEnqueueError::Reservation {
                        error: reservation_error,
                        handoff: Box::new(handoff),
                    }
                },
            });
        },
    };
    let reservation =
        match reserve_native_continuation_dispatch_identity_durably(
            store,
            request.expected,
            NativeContinuationDispatchReservationKind::Identity,
            request.maximum_bytes,
        ) {
            Ok(reservation) => reservation,
            Err(error) => {
                return Err(
                    NativeContinuationDispatchDurableEnqueueError::Reservation {
                        error,
                        handoff: Box::new(handoff),
                    },
                );
            },
        };
    if let NativeContinuationDispatchReservationStateCas::Conflict {
        current: durable_current,
        expected: durable_expected,
    } = reservation
    {
        return Ok(NativeContinuationDispatchDurableEnqueue::Conflict {
            current: durable_current,
            expected: durable_expected,
            handoff: Box::new(handoff),
        });
    }
    Ok(bind_committed_durable_identity(
        local_queue,
        handoff,
        current,
        reservation,
    ))
}

fn bind_committed_durable_identity<Clock, DurabilityError>(
    local_queue: &mut queue::NativeContinuationDispatchQueue<Clock>,
    handoff: NativeInterpreterHandoff,
    current: ReservationState,
    reservation: NativeContinuationDispatchReservationStateCas<DurabilityError>,
) -> NativeContinuationDispatchDurableEnqueue<DurabilityError>
where
    Clock: NativeContinuationMonotonicClock,
{
    match local_queue.enqueue_reserved(handoff, current.identity()) {
        Ok(dispatch) => NativeContinuationDispatchDurableEnqueue::Bound {
            dispatch,
            reservation,
        },
        Err(failure) => {
            NativeContinuationDispatchDurableEnqueue::CommittedUnbound {
                failure,
                reservation,
            }
        },
    }
}

fn preflight_durable_timing_dispatch<Clock, StoreError>(
    local_queue: &queue::NativeContinuationDispatchQueue<Clock>,
    request: NativeContinuationDispatchDurableTimingRequest,
) -> Result<
    ReservationState,
    NativeContinuationDispatchDurableTimingError<StoreError>,
>
where
    Clock: NativeContinuationMonotonicClock,
{
    let local = local_queue.watermarks();
    let base = request.expected.unwrap_or_else(zero_state);
    if local != base {
        return Err(NativeContinuationDispatchDurableTimingError::Reservation(
            CasError::LocalStateMismatch {
                local,
                expected: request.expected,
            },
        ));
    }
    let current =
        advance_state(base, NativeContinuationDispatchReservationKind::Timing)
            .ok_or(
                NativeContinuationDispatchDurableTimingError::Reservation(
                    CasError::WatermarkExhausted {
                        reservation:
                            NativeContinuationDispatchReservationKind::Timing,
                    },
                ),
            )?;
    if local_queue.pending() == 0 {
        return Err(NativeContinuationDispatchDurableTimingError::Queue(
            NativeContinuationDispatchDurableTimingPreflightError::Idle,
        ));
    }
    if local_queue.in_flight() >= local_queue.maximum_in_flight().get() {
        return Err(NativeContinuationDispatchDurableTimingError::Queue(
            NativeContinuationDispatchDurableTimingPreflightError::Capacity {
                in_flight: local_queue.in_flight(),
                maximum_in_flight: local_queue.maximum_in_flight(),
            },
        ));
    }
    Ok(current)
}

/// Durably reserves the next timing identity and dispatches the FIFO owner.
///
/// Local synchronization, pending ownership, and in-flight capacity are checked
/// before storage access. After commit, exclusive mutable queue ownership keeps
/// those facts stable while the exact reserved timing identity starts and the
/// oldest affine handoff transfers to the caller. This does not persist the
/// handoff or its monotonic clock start.
///
/// # Errors
///
/// Returns local synchronization, timing exhaustion, idle/capacity preflight,
/// codec, byte-limit, or storage failure before a durable outcome exists.
pub fn reserve_and_dispatch_native_continuation_timing_durably<Clock, Store>(
    store: &mut Store,
    local_queue: &mut queue::NativeContinuationDispatchQueue<Clock>,
    request: NativeContinuationDispatchDurableTimingRequest,
) -> NativeContinuationDispatchDurableTimingStoreResult<Store>
where
    Clock: NativeContinuationMonotonicClock,
    Store: ConditionalBlobStore + DurableBlobStore,
{
    let current = preflight_durable_timing_dispatch(local_queue, request)?;
    let reservation = reserve_native_continuation_dispatch_identity_durably(
        store,
        request.expected,
        NativeContinuationDispatchReservationKind::Timing,
        request.maximum_bytes,
    )
    .map_err(NativeContinuationDispatchDurableTimingError::Reservation)?;
    if let NativeContinuationDispatchReservationStateCas::Conflict {
        current: durable_current,
        expected: durable_expected,
    } = reservation
    {
        return Ok(NativeContinuationDispatchDurableTiming::Conflict {
            current: durable_current,
            expected: durable_expected,
        });
    }
    match local_queue.dispatch_next_reserved_timing(current.timing()) {
        Ok(Some(dispatch)) => {
            Ok(NativeContinuationDispatchDurableTiming::Bound {
                dispatch: Box::new(dispatch),
                reservation,
            })
        },
        Ok(None) => Ok(
            NativeContinuationDispatchDurableTiming::CommittedUnbound {
                failure:
                    NativeContinuationDispatchDurableTimingBindFailure::
                        MissingPending,
                reservation,
            },
        ),
        Err(error) => Ok(
            NativeContinuationDispatchDurableTiming::CommittedUnbound {
                failure:
                    NativeContinuationDispatchDurableTimingBindFailure::Begin(
                        error,
                    ),
                reservation,
            },
        ),
    }
}

/// Advances exactly one selected watermark in combined durable queue state.
///
/// # Errors
///
/// Returns selected-watermark exhaustion, framing rejection, byte-limit
/// failure, or outbound store failure before a typed outcome can be returned.
fn reserve_native_continuation_dispatch_identity_durably<Store>(
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
