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
//   - Canonical framing and exact-next durable CAS for the process-local
//     dispatch identity watermark.
// - Must-Not:
//   - Persist affine handoffs, timing intervals, queue capacity, bind reserved
//     identity to enqueue, infer storage paths, or coordinate processes.
// - Allows:
//   - Inputs: optional expected watermark, positive byte bound, conditional
//     durable store.
//   - Outputs: exact conflict watermark, durable next watermark, committed sync
//     failure, or typed framing/storage/exhaustion failure.
//   - Side effects: one delegated conditional durable blob publication.
// - Split-When:
//   - Reservation-to-enqueue binding or distributed identity allocation gains
//     authority.
// - Merge-When:
//   - Durable queue orchestration owns identity reservation and enqueue
//     atomically.
// - Summary:
//   - Advances canonical dispatch identity watermark exactly one step durably.
// - Description:
//   - Missing state starts at one; present state advances with checked
//     addition.
// - Usage:
//   - Restore/retain the committed watermark, then reconstruct an empty queue.
// - Defaults:
//   - Watermark zero is implicit only while durable state is missing.
//

//! Canonical durable process-local dispatch identity watermark.

use std::num::NonZeroUsize;

use crate::blob_persistence::{
    NativeContinuationBlobConditionalDurablePersistence as BlobCasDurable,
    NativeContinuationBlobPersistenceError, compare_and_swap_blob_durably,
};
use crate::blob_store::{
    NativeContinuationBlobStore as BlobStore,
    NativeContinuationConditionalBlobStore as ConditionalBlobStore,
    NativeContinuationDurableBlobStore as DurableBlobStore,
};
use crate::continuation_dispatch_queue as dispatch_queue;

const CODEC_LEN: usize = 16;
const MAGIC: [u8; 8] = *b"MBDQWM01";

type Watermark = dispatch_queue::NativeContinuationDispatchIdentityWatermark;

/// Canonical dispatch-watermark framing failure.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchIdentityWatermarkCodecError {
    /// Frame length differed from the fixed canonical size.
    Length {
        /// Exact observed frame byte count.
        observed: usize,
    },
    /// Canonical magic/version prefix differed.
    Magic,
}

/// Typed exact-next durable watermark CAS outcome.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchIdentityWatermarkCas<DurabilityError> {
    /// Durable bytes differed from the caller's expected watermark.
    Conflict {
        /// Exact current durable watermark, or missing state.
        current: Option<Watermark>,
        /// Caller-supplied expected durable watermark.
        expected: Option<Watermark>,
    },
    /// Next watermark committed and durability confirmation completed.
    Durable {
        /// Exact canonical byte count committed by the store.
        bytes: usize,
        /// Exact newly committed watermark.
        current: Watermark,
        /// Exact prior watermark, or missing state before watermark one.
        previous: Option<Watermark>,
    },
    /// Next watermark committed, then durability confirmation failed.
    Published {
        /// Exact canonical byte count committed by the store.
        bytes: usize,
        /// Exact newly committed watermark.
        current: Watermark,
        /// Exact post-publication durability failure.
        durability_error: DurabilityError,
        /// Exact prior watermark, or missing state before watermark one.
        previous: Option<Watermark>,
    },
}

/// Why exact-next durable watermark publication failed before an outcome.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchIdentityWatermarkCasError<StoreError> {
    /// Bounded conditional blob orchestration or outbound store failed.
    Blob(NativeContinuationBlobPersistenceError<StoreError>),
    /// Current durable bytes failed canonical watermark framing.
    Codec(NativeContinuationDispatchIdentityWatermarkCodecError),
    /// The caller's expected watermark cannot advance beyond `u64::MAX`.
    IdentityExhausted,
}

type WatermarkCasError<StoreError> =
    NativeContinuationDispatchIdentityWatermarkCasError<StoreError>;

/// Typed watermark CAS result specialized to one conditional durable store.
pub type NativeContinuationDispatchIdentityWatermarkCasStoreResult<Store> =
    Result<
        NativeContinuationDispatchIdentityWatermarkCas<
            <Store as DurableBlobStore>::DurabilityError,
        >,
        NativeContinuationDispatchIdentityWatermarkCasError<
            <Store as BlobStore>::Error,
        >,
    >;

/// Decodes one exact canonical dispatch identity watermark frame.
///
/// # Errors
///
/// Returns fixed framing rejection for length or magic/version drift.
pub fn decode_native_continuation_dispatch_watermark(
    bytes: &[u8],
) -> Result<Watermark, NativeContinuationDispatchIdentityWatermarkCodecError> {
    if bytes.len() != CODEC_LEN {
        return Err(
            NativeContinuationDispatchIdentityWatermarkCodecError::Length {
                observed: bytes.len(),
            },
        );
    }
    if !bytes.iter().take(MAGIC.len()).copied().eq(MAGIC) {
        return Err(
            NativeContinuationDispatchIdentityWatermarkCodecError::Magic,
        );
    }
    let mut value = [0u8; 8];
    for (slot, byte) in value
        .iter_mut()
        .zip(bytes.iter().skip(MAGIC.len()).copied())
    {
        *slot = byte;
    }
    Ok(Watermark::from_value(u64::from_le_bytes(value)))
}

/// Encodes one dispatch identity watermark as canonical fixed bytes.
#[must_use]
pub fn encode_native_continuation_dispatch_watermark(
    watermark: Watermark,
) -> [u8; CODEC_LEN] {
    let mut bytes = [0u8; CODEC_LEN];
    for (slot, byte) in bytes.iter_mut().take(MAGIC.len()).zip(MAGIC) {
        *slot = byte;
    }
    for (slot, byte) in bytes
        .iter_mut()
        .skip(MAGIC.len())
        .zip(watermark.value().to_le_bytes())
    {
        *slot = byte;
    }
    bytes
}

/// Advances the durable dispatch identity watermark by exactly one.
///
/// # Errors
///
/// Returns identity exhaustion, framing rejection, byte-limit failure, or
/// outbound store failure before a typed outcome can be returned.
pub fn advance_native_continuation_dispatch_watermark_durably<Store>(
    store: &mut Store,
    expected: Option<Watermark>,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationDispatchIdentityWatermarkCasStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    let next_value = match expected {
        None => 1,
        Some(watermark) => watermark
            .value()
            .checked_add(1)
            .ok_or(WatermarkCasError::IdentityExhausted)?,
    };
    let current = Watermark::from_value(next_value);
    let expected_bytes =
        expected.map(encode_native_continuation_dispatch_watermark);
    let current_bytes = encode_native_continuation_dispatch_watermark(current);
    let outcome = compare_and_swap_blob_durably(
        store,
        expected_bytes.as_ref().map(<[u8; CODEC_LEN]>::as_slice),
        &current_bytes,
        maximum_bytes,
    )
    .map_err(NativeContinuationDispatchIdentityWatermarkCasError::Blob)?;
    match outcome {
        BlobCasDurable::Conflict { current: bytes } => {
            let durable_current = bytes
                .as_deref()
                .map(decode_native_continuation_dispatch_watermark)
                .transpose()
                .map_err(
                    NativeContinuationDispatchIdentityWatermarkCasError::Codec,
                )?;
            Ok(NativeContinuationDispatchIdentityWatermarkCas::Conflict {
                current: durable_current,
                expected,
            })
        },
        BlobCasDurable::Durable { write } => {
            Ok(NativeContinuationDispatchIdentityWatermarkCas::Durable {
                bytes: write.bytes(),
                current,
                previous: expected,
            })
        },
        BlobCasDurable::Published { durability_error, write } => {
            Ok(NativeContinuationDispatchIdentityWatermarkCas::Published {
                bytes: write.bytes(),
                current,
                durability_error,
                previous: expected,
            })
        },
    }
}
