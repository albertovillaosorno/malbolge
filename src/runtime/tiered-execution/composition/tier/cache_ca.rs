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
//   - Conditional durable publication of cache-trigger cadence cursor state.
// - Must-Not:
//   - Observe telemetry, consume cadence slots, run cache policy, choose
//     storage locations, or spawn unattended lifecycle work.
// - Allows:
//   - Inputs: expected optional cursor, candidate cursor, positive byte bound,
//     and one conditional durable blob store.
//   - Outputs: exact conflict state, durable commit, committed durability
//     failure, or typed prepublication failure.
//   - Side effects: delegated conditional blob publication and durability only.
// - Split-When:
//   - Trigger-slot transition validation or distributed consensus gains
//     independent authority.
// - Merge-When:
//   - One durable trigger owner subsumes cursor publication and consumption.
// - Summary:
//   - Publishes canonical trigger cursors through exact compare-and-swap.
// - Description:
//   - Conflict bytes are decoded before typed current-state evidence is
//     returned.
// - Usage:
//   - Supply the last observed optional cursor plus one caller-owned candidate.
// - Defaults:
//   - Missing expected state matches only a missing durable cursor.
//

//! Durable compare-and-swap publication for cache-trigger cadence cursors.

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
use crate::{
    executable_cache_limits_trigger_cadence as trigger,
    executable_cache_limits_trigger_cadence_codec as codec,
};

type Cursor = trigger::NativeExecutableCacheLimitsTriggerCadence;
type CursorCodecError =
    codec::NativeExecutableCacheLimitsTriggerCadenceCodecError;

/// Typed outcome of one durable trigger-cursor compare-and-swap publication.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeExecutableCacheLimitsTriggerCadenceCas<DurabilityError> {
    /// Durable bytes differed from the expected optional trigger cursor.
    Conflict {
        /// Candidate cursor that was not published.
        candidate: Cursor,
        /// Exact current durable cursor, or absent when current state is
        /// absent.
        current: Option<Cursor>,
        /// Caller-supplied expected cursor used for canonical comparison.
        expected: Option<Cursor>,
    },
    /// Candidate cursor committed and durability confirmation completed.
    Durable {
        /// Exact canonical byte count committed by the store.
        bytes: usize,
        /// Exact cursor published by this operation.
        current: Cursor,
        /// Exact prior cursor, or absent for initialization.
        previous: Option<Cursor>,
    },
    /// Candidate cursor committed, then durability confirmation failed.
    Published {
        /// Exact canonical byte count committed by the store.
        bytes: usize,
        /// Exact cursor published by this operation.
        current: Cursor,
        /// Exact post-publication durability failure.
        durability_error: DurabilityError,
        /// Exact prior cursor, or absent for initialization.
        previous: Option<Cursor>,
    },
}

/// Why durable trigger-cursor CAS failed before returning a typed outcome.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeExecutableCacheLimitsTriggerCadenceCasError<StoreError> {
    /// Bounded conditional blob orchestration or outbound store failed.
    Blob(NativeContinuationBlobPersistenceError<StoreError>),
    /// Canonical trigger-cursor framing or semantics failed on conflict decode.
    Codec(CursorCodecError),
}

/// Result of one typed durable trigger-cursor CAS operation.
pub type NativeExecutableCacheLimitsTriggerCadenceCasResult<
    StoreError,
    DurabilityError,
> = Result<
    NativeExecutableCacheLimitsTriggerCadenceCas<DurabilityError>,
    NativeExecutableCacheLimitsTriggerCadenceCasError<StoreError>,
>;

/// Trigger-cursor CAS result specialized to one conditional durable store.
pub type NativeExecutableCacheLimitsTriggerCadenceCasStoreResult<Store> =
    NativeExecutableCacheLimitsTriggerCadenceCasResult<
        <Store as BlobStore>::Error,
        <Store as DurableBlobStore>::DurabilityError,
    >;

fn decode_cursor(bytes: &[u8]) -> Result<Cursor, CursorCodecError> {
    codec::decode_native_executable_cache_limits_trigger_cadence(bytes)
}

fn encode_cursor(cadence: Cursor) -> Vec<u8> {
    codec::encode_native_executable_cache_limits_trigger_cadence(cadence)
}

/// Conditionally publishes one cache-trigger cadence cursor durably.
///
/// Exact canonical bytes represent both expected and replacement values.
/// Conflict returns exact bounded current durable cursor after canonical
/// decode. A durability error occurs only after the candidate committed.
///
/// # Errors
///
/// Returns conflict-codec rejection, byte-limit failure, or outbound
/// coordination/publication failure before a typed outcome can be returned.
pub fn compare_and_swap_cache_trigger_cadence_durably<Store>(
    store: &mut Store,
    expected: Option<Cursor>,
    candidate: Cursor,
    maximum_bytes: NonZeroUsize,
) -> NativeExecutableCacheLimitsTriggerCadenceCasStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    let expected_bytes = expected.map(encode_cursor);
    let candidate_bytes = encode_cursor(candidate);
    let outcome = compare_and_swap_blob_durably(
        store,
        expected_bytes.as_deref(),
        &candidate_bytes,
        maximum_bytes,
    )
    .map_err(NativeExecutableCacheLimitsTriggerCadenceCasError::Blob)?;
    match outcome {
        BlobCasDurable::Conflict { current: current_bytes } => {
            let current = current_bytes
                .as_deref()
                .map(decode_cursor)
                .transpose()
                .map_err(
                    NativeExecutableCacheLimitsTriggerCadenceCasError::Codec,
                )?;
            Ok(NativeExecutableCacheLimitsTriggerCadenceCas::Conflict {
                candidate,
                current,
                expected,
            })
        },
        BlobCasDurable::Durable { write } => {
            Ok(NativeExecutableCacheLimitsTriggerCadenceCas::Durable {
                bytes: write.bytes(),
                current: candidate,
                previous: expected,
            })
        },
        BlobCasDurable::Published { durability_error, write } => {
            Ok(NativeExecutableCacheLimitsTriggerCadenceCas::Published {
                bytes: write.bytes(),
                current: candidate,
                durability_error,
                previous: expected,
            })
        },
    }
}

#[cfg(test)]
#[path = "../../../../../tests/tiered/cache_cursor_cas.rs"]
mod tests;
