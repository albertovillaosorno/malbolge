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
//   - Applying restored executable-cache limit policy to caller-owned caches.
// - Must-Not:
//   - Persist executable mappings, choose storage locations, retry release
//     failures, reconcile retired leases, or invent missing policy.
// - Allows:
//   - Inputs: one bounded limit-policy store, cache owner, memory adapter, and
//     positive byte bound.
//   - Outputs: explicit missing policy or exact cache reconfiguration evidence.
//   - Side effects: bounded policy restore followed by the selected cache's
//     existing transactional limit reconfiguration.
// - Split-When:
//   - Policy arbitration or retry scheduling gains independent authority.
// - Merge-When:
//   - One cache-lifecycle owner subsumes durable policy restore and activation.
// - Summary:
//   - Applies durable cache limits without persisting executable residency.
// - Description:
//   - Ordinary and lease caches retain their distinct eviction semantics.
// - Usage:
//   - Invoke explicitly when a caller elects to activate durable cache policy.
// - Defaults:
//   - Missing or invalid durable policy never changes live cache limits.
//

//! Durable executable-cache limit activation for caller-owned caches.

use std::num::NonZeroUsize;

use crate::blob_store::NativeContinuationBlobStore as BlobStore;
use crate::executable_cache_limits_persistence::{
    NativeExecutableSequenceCacheLimitsPersistenceError,
    NativeExecutableSequenceCacheLimitsPersistenceLoad,
    restore_native_executable_sequence_cache_limits,
};
use crate::execution_native::{
    NativeExecutableMemoryAdapter, NativeExecutableSequenceCache,
    NativeExecutableSequenceCacheReconfiguration,
    NativeExecutableSequenceCacheReconfigurationFailure,
    NativeExecutableSequenceLeaseCache,
    NativeExecutableSequenceLeaseCacheReconfiguration,
    NativeExecutableSequenceLeaseCacheReconfigurationFailure,
};

/// Durable limit activation outcome for one ordinary executable cache.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeExecutableSequenceCacheLimitsActivation {
    /// No durable policy existed; live cache limits were not touched.
    Missing,
    /// Restored policy published through ordinary FIFO reconfiguration.
    Reconfigured {
        /// Exact canonical policy bytes restored before activation.
        bytes: usize,
        /// Exact ordinary-cache reconfiguration evidence.
        reconfiguration: NativeExecutableSequenceCacheReconfiguration,
    },
}

/// Failure while restoring or applying ordinary executable-cache limits.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeExecutableSequenceCacheLimitsActivationError<
    StoreError,
    AdapterError,
> {
    /// Durable policy restore failed before cache mutation.
    Persistence(
        NativeExecutableSequenceCacheLimitsPersistenceError<StoreError>,
    ),
    /// Cache reconfiguration failed while retaining its documented ownership.
    Reconfiguration(
        Box<NativeExecutableSequenceCacheReconfigurationFailure<AdapterError>>,
    ),
}

/// Result of one ordinary-cache durable limit activation.
pub type NativeExecutableSequenceCacheLimitsActivationResult<
    StoreError,
    AdapterError,
> = Result<
    NativeExecutableSequenceCacheLimitsActivation,
    NativeExecutableSequenceCacheLimitsActivationError<
        StoreError,
        AdapterError,
    >,
>;

/// Ordinary-cache activation result specialized to one store and adapter.
pub type NativeExecutableSequenceCacheLimitsStoreResult<Store, Adapter> =
    NativeExecutableSequenceCacheLimitsActivationResult<
        <Store as BlobStore>::Error,
        <Adapter as NativeExecutableMemoryAdapter>::Error,
    >;

/// Durable limit activation outcome for one executable lease cache.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeExecutableSequenceLeaseCacheLimitsActivation {
    /// No durable policy existed; live cache limits were not touched.
    Missing,
    /// Restored policy published through lease-aware reconfiguration.
    Reconfigured {
        /// Exact canonical policy bytes restored before activation.
        bytes: usize,
        /// Exact lease-cache reconfiguration evidence.
        reconfiguration: NativeExecutableSequenceLeaseCacheReconfiguration,
    },
}

/// Failure while restoring or applying executable lease-cache limits.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeExecutableSequenceLeaseCacheLimitsActivationError<
    StoreError,
    AdapterError,
> {
    /// Durable policy restore failed before cache mutation.
    Persistence(
        NativeExecutableSequenceCacheLimitsPersistenceError<StoreError>,
    ),
    /// Lease-aware reconfiguration retained exact blocker or cleanup ownership.
    Reconfiguration(
        Box<
            NativeExecutableSequenceLeaseCacheReconfigurationFailure<
                AdapterError,
            >,
        >,
    ),
}

/// Result of one lease-cache durable limit activation.
pub type NativeExecutableSequenceLeaseCacheLimitsActivationResult<
    StoreError,
    AdapterError,
> = Result<
    NativeExecutableSequenceLeaseCacheLimitsActivation,
    NativeExecutableSequenceLeaseCacheLimitsActivationError<
        StoreError,
        AdapterError,
    >,
>;

/// Lease-cache activation result specialized to one store and adapter.
pub type NativeExecutableSequenceLeaseCacheLimitsStoreResult<Store, Adapter> =
    NativeExecutableSequenceLeaseCacheLimitsActivationResult<
        <Store as BlobStore>::Error,
        <Adapter as NativeExecutableMemoryAdapter>::Error,
    >;

/// Restores durable limits and transactionally applies them to an ordinary
/// executable cache.
///
/// Missing durable policy is a successful no-op. Persistence failure occurs
/// before cache mutation. Reconfiguration failure retains the cache's exact
/// release or invariant ownership and its previously published limits.
///
/// # Errors
///
/// Returns durable-policy restore failure or ordinary-cache reconfiguration
/// failure without retrying either boundary.
pub fn restore_and_apply_native_executable_sequence_cache_limits<
    Store,
    Adapter,
>(
    store: &mut Store,
    cache: &mut NativeExecutableSequenceCache,
    adapter: &mut Adapter,
    maximum_bytes: NonZeroUsize,
) -> NativeExecutableSequenceCacheLimitsStoreResult<Store, Adapter>
where
    Store: BlobStore,
    Adapter: NativeExecutableMemoryAdapter,
{
    let load =
        restore_native_executable_sequence_cache_limits(store, maximum_bytes)
            .map_err(
            NativeExecutableSequenceCacheLimitsActivationError::Persistence,
        )?;
    let NativeExecutableSequenceCacheLimitsPersistenceLoad::Restored {
        bytes,
        limits,
    } = load
    else {
        return Ok(NativeExecutableSequenceCacheLimitsActivation::Missing);
    };
    let reconfiguration = cache.reconfigure_limits(adapter, limits).map_err(
        NativeExecutableSequenceCacheLimitsActivationError::Reconfiguration,
    )?;
    Ok(
        NativeExecutableSequenceCacheLimitsActivation::Reconfigured {
            bytes,
            reconfiguration,
        },
    )
}

/// Restores durable limits and transactionally applies them to an executable
/// lease cache.
///
/// Missing durable policy is a successful no-op. Persistence failure occurs
/// before cache mutation. Reconfiguration delegates eviction, retirement, and
/// resident blockage to the existing lease-cache transaction and never
/// reconciles retired entries implicitly.
///
/// # Errors
///
/// Returns durable-policy restore failure or lease-cache reconfiguration
/// failure without retrying either boundary.
pub fn restore_and_apply_native_executable_sequence_lease_cache_limits<
    Store,
    Adapter,
>(
    store: &mut Store,
    cache: &mut NativeExecutableSequenceLeaseCache,
    adapter: &mut Adapter,
    maximum_bytes: NonZeroUsize,
) -> NativeExecutableSequenceLeaseCacheLimitsStoreResult<Store, Adapter>
where
    Store: BlobStore,
    Adapter: NativeExecutableMemoryAdapter,
{
    let load = restore_native_executable_sequence_cache_limits(
        store,
        maximum_bytes,
    )
    .map_err(
        NativeExecutableSequenceLeaseCacheLimitsActivationError::Persistence,
    )?;
    let NativeExecutableSequenceCacheLimitsPersistenceLoad::Restored {
        bytes,
        limits,
    } = load
    else {
        return Ok(NativeExecutableSequenceLeaseCacheLimitsActivation::Missing);
    };
    let reconfiguration = cache
        .reconfigure_limits(adapter, limits)
        .map_err(
            NativeExecutableSequenceLeaseCacheLimitsActivationError::
                Reconfiguration,
        )?;
    Ok(
        NativeExecutableSequenceLeaseCacheLimitsActivation::Reconfigured {
            bytes,
            reconfiguration,
        },
    )
}

#[cfg(test)]
#[path = "../../../../../tests/tiered/cache_limits_activation.rs"]
mod tests;
