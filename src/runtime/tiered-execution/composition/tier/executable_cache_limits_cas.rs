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
//   - Conditional durable publication and guarded eviction of cache limits.
// - Must-Not:
//   - Reconfigure live caches, persist residency, choose storage locations, or
//     grant cross-process executable ownership.
// - Allows:
//   - Inputs: expected optional limits, candidate limits, byte bound, and one
//     conditional durable blob store.
//   - Outputs: exact publish/evict conflict state, durable commit, committed
//     durability failure, or typed prepublication failure.
//   - Side effects: delegated conditional blob publication and durability only.
// - Split-When:
//   - Revisioned cache-policy history or distributed consensus gains authority.
// - Merge-When:
//   - One cache-policy owner subsumes publication and live-cache activation.
// - Summary:
//   - Publishes cache-limit policy through exact canonical compare-and-swap.
// - Description:
//   - Conflicts decode current bounded bytes but never overwrite them.
// - Usage:
//   - Supply the last observed optional limits plus one replacement candidate.
// - Defaults:
//   - Missing expected state matches only a missing durable policy.
//

//! Durable compare-and-swap publication and guarded eviction for cache limits.

use std::num::NonZeroUsize;

use crate::blob_persistence::{
    NativeContinuationBlobConditionalDurablePersistence as BlobCasDurable,
    NativeContinuationBlobConditionalDurableRemoval as BlobCasRemoval,
    NativeContinuationBlobPersistenceError, compare_and_remove_blob_durably,
    compare_and_swap_blob_durably,
};
use crate::blob_store::{
    NativeContinuationBlobStore as BlobStore,
    NativeContinuationConditionalBlobStore as ConditionalBlobStore,
    NativeContinuationConditionalRemovableBlobStore as ConditionalRemoveStore,
    NativeContinuationDurableBlobStore as DurableBlobStore,
};
use crate::execution_native::{
    NativeExecutableSequenceCacheLimits,
    NativeExecutableSequenceCacheLimitsCodecError,
    decode_native_executable_sequence_cache_limits,
    encode_native_executable_sequence_cache_limits,
};

/// Typed outcome of guarded durable cache-limit policy eviction.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeExecutableSequenceCacheLimitsEviction<DurabilityError> {
    /// Durable state differed from the expected cache-limit policy.
    Conflict {
        /// Exact current durable limits, or absent when no policy exists.
        current: Option<NativeExecutableSequenceCacheLimits>,
        /// Exact caller-owned policy that was eligible for removal.
        expected: NativeExecutableSequenceCacheLimits,
    },
    /// Expected policy was removed and durability confirmation completed.
    Durable {
        /// Exact policy removed by this operation.
        previous: NativeExecutableSequenceCacheLimits,
    },
    /// Expected policy was removed, then durability confirmation failed.
    Removed {
        /// Exact post-removal durability failure.
        durability_error: DurabilityError,
        /// Exact policy removed by this operation.
        previous: NativeExecutableSequenceCacheLimits,
    },
}

/// Typed outcome of one durable cache-limit compare-and-swap publication.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeExecutableSequenceCacheLimitsCas<DurabilityError> {
    /// Durable bytes differed from the expected optional cache limits.
    Conflict {
        /// Candidate limits that were not published.
        candidate: NativeExecutableSequenceCacheLimits,
        /// Exact current durable limits, or absent when current state is
        /// absent.
        current: Option<NativeExecutableSequenceCacheLimits>,
        /// Caller-supplied expected limits used for canonical comparison.
        expected: Option<NativeExecutableSequenceCacheLimits>,
    },
    /// Candidate limits committed and durability confirmation completed.
    Durable {
        /// Exact canonical byte count committed by the store.
        bytes: usize,
        /// Exact limits published by this operation.
        current: NativeExecutableSequenceCacheLimits,
        /// Exact prior limits, or absent for initialization.
        previous: Option<NativeExecutableSequenceCacheLimits>,
    },
    /// Candidate limits committed, then durability confirmation failed.
    Published {
        /// Exact canonical byte count committed by the store.
        bytes: usize,
        /// Exact limits published by this operation.
        current: NativeExecutableSequenceCacheLimits,
        /// Exact post-publication durability failure.
        durability_error: DurabilityError,
        /// Exact prior limits, or absent for initialization.
        previous: Option<NativeExecutableSequenceCacheLimits>,
    },
}

/// Why durable cache-limit CAS failed before returning a typed outcome.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeExecutableSequenceCacheLimitsCasError<StoreError> {
    /// Bounded conditional blob orchestration or outbound store failed.
    Blob(NativeContinuationBlobPersistenceError<StoreError>),
    /// Canonical cache-limit framing or semantics failed.
    Codec(NativeExecutableSequenceCacheLimitsCodecError),
}

/// Result of one typed durable cache-limit CAS operation.
pub type NativeExecutableSequenceCacheLimitsCasResult<
    StoreError,
    DurabilityError,
> = Result<
    NativeExecutableSequenceCacheLimitsCas<DurabilityError>,
    NativeExecutableSequenceCacheLimitsCasError<StoreError>,
>;

/// Guarded cache-limit eviction result specialized to one store type.
pub type NativeExecutableSequenceCacheLimitsEvictionStoreResult<Store> = Result<
    NativeExecutableSequenceCacheLimitsEviction<
        <Store as DurableBlobStore>::DurabilityError,
    >,
    NativeExecutableSequenceCacheLimitsCasError<<Store as BlobStore>::Error>,
>;

/// Cache-limit CAS result specialized to one conditional durable store.
pub type NativeExecutableSequenceCacheLimitsCasStoreResult<Store> =
    NativeExecutableSequenceCacheLimitsCasResult<
        <Store as BlobStore>::Error,
        <Store as DurableBlobStore>::DurabilityError,
    >;

/// Durably evicts one exact cache-limit policy only while it remains current.
///
/// Canonical bytes of the expected policy are compared under the outbound
/// store removal authority. Conflict bytes are decoded before typed evidence is
/// returned, so malformed current state fails closed.
///
/// # Errors
///
/// Returns codec, byte-limit, or outbound coordination/removal failure before a
/// typed eviction outcome exists.
pub fn evict_native_executable_sequence_cache_limits_if_current_durably<Store>(
    store: &mut Store,
    expected: NativeExecutableSequenceCacheLimits,
    maximum_bytes: NonZeroUsize,
) -> NativeExecutableSequenceCacheLimitsEvictionStoreResult<Store>
where
    Store: ConditionalRemoveStore + DurableBlobStore,
{
    let expected_bytes =
        encode_native_executable_sequence_cache_limits(expected)
            .map_err(NativeExecutableSequenceCacheLimitsCasError::Codec)?;
    let outcome = compare_and_remove_blob_durably(
        store,
        Some(&expected_bytes),
        maximum_bytes,
    )
    .map_err(NativeExecutableSequenceCacheLimitsCasError::Blob)?;
    match outcome {
        BlobCasRemoval::Conflict { current: current_bytes } => {
            let current = current_bytes
                .as_deref()
                .map(decode_native_executable_sequence_cache_limits)
                .transpose()
                .map_err(NativeExecutableSequenceCacheLimitsCasError::Codec)?;
            Ok(NativeExecutableSequenceCacheLimitsEviction::Conflict {
                current,
                expected,
            })
        },
        BlobCasRemoval::Durable => {
            Ok(NativeExecutableSequenceCacheLimitsEviction::Durable {
                previous: expected,
            })
        },
        BlobCasRemoval::Missing => {
            Ok(NativeExecutableSequenceCacheLimitsEviction::Conflict {
                current: None,
                expected,
            })
        },
        BlobCasRemoval::Removed { durability_error } => {
            Ok(NativeExecutableSequenceCacheLimitsEviction::Removed {
                durability_error,
                previous: expected,
            })
        },
    }
}

/// Conditionally publishes one executable-cache limit policy durably.
///
/// Exact canonical bytes represent both expected and replacement values.
/// Conflict returns the exact bounded current durable policy after canonical
/// decoding. A durability error occurs only after the candidate committed.
///
/// # Errors
///
/// Returns codec rejection, byte-limit failure, or outbound
/// coordination/publication failure before a typed outcome can be returned.
pub fn compare_and_swap_native_executable_sequence_cache_limits_durably<Store>(
    store: &mut Store,
    expected: Option<NativeExecutableSequenceCacheLimits>,
    candidate: NativeExecutableSequenceCacheLimits,
    maximum_bytes: NonZeroUsize,
) -> NativeExecutableSequenceCacheLimitsCasStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    let expected_bytes = expected
        .map(encode_native_executable_sequence_cache_limits)
        .transpose()
        .map_err(NativeExecutableSequenceCacheLimitsCasError::Codec)?;
    let candidate_bytes =
        encode_native_executable_sequence_cache_limits(candidate)
            .map_err(NativeExecutableSequenceCacheLimitsCasError::Codec)?;
    let outcome = compare_and_swap_blob_durably(
        store,
        expected_bytes.as_deref(),
        &candidate_bytes,
        maximum_bytes,
    )
    .map_err(NativeExecutableSequenceCacheLimitsCasError::Blob)?;
    match outcome {
        BlobCasDurable::Conflict { current: current_bytes } => {
            let current = current_bytes
                .as_deref()
                .map(decode_native_executable_sequence_cache_limits)
                .transpose()
                .map_err(NativeExecutableSequenceCacheLimitsCasError::Codec)?;
            Ok(NativeExecutableSequenceCacheLimitsCas::Conflict {
                candidate,
                current,
                expected,
            })
        },
        BlobCasDurable::Durable { write } => {
            Ok(NativeExecutableSequenceCacheLimitsCas::Durable {
                bytes: write.bytes(),
                current: candidate,
                previous: expected,
            })
        },
        BlobCasDurable::Published { durability_error, write } => {
            Ok(NativeExecutableSequenceCacheLimitsCas::Published {
                bytes: write.bytes(),
                current: candidate,
                durability_error,
                previous: expected,
            })
        },
    }
}

#[cfg(test)]
#[path = "../../../../../tests/tiered/cache_limits_cas.rs"]
mod tests;
