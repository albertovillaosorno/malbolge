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
mod tests {
    use std::convert::Infallible;

    use super::*;
    use crate::blob_store::{
        NativeContinuationBlobRemoval, NativeContinuationBlobRemovalResult,
        NativeContinuationDurableBlobStore,
        NativeContinuationRemovableBlobStore,
    };
    use crate::executable_cache_limits_persistence::{
        NativeExecutableSequenceCacheLimitsDurableRemoval,
        evict_native_executable_sequence_cache_limits_durably,
    };
    use crate::execution_native::{
        NativeExecutableAllocationRequest, NativeExecutableCodeCopyReport,
        NativeExecutableMappingReport, NativeExecutableReleaseRequest,
        NativeExecutableSequenceCacheLimits, NativeInstructionSyncReport,
        NativeInstructionSyncRequest,
    };

    #[derive(Clone, Copy, Debug, Eq, PartialEq)]
    enum AdapterError {
        UnexpectedOperation,
    }

    #[derive(Clone, Copy, Debug, Eq, PartialEq)]
    enum StoreError {
        Replace,
    }

    #[derive(Debug, Default)]
    struct NoOpAdapter {
        calls: usize,
    }

    #[derive(Debug, Default)]
    struct MemoryStore {
        bytes: Option<Vec<u8>>,
    }

    impl BlobStore for MemoryStore {
        type Error = StoreError;

        fn load(
            &mut self,
            _maximum_bytes: NonZeroUsize,
        ) -> Result<Option<Vec<u8>>, Self::Error> {
            Ok(self.bytes.clone())
        }

        fn replace(&mut self, _bytes: &[u8]) -> Result<(), Self::Error> {
            Err(StoreError::Replace)
        }
    }

    impl NativeContinuationDurableBlobStore for MemoryStore {
        type DurabilityError = Infallible;

        fn confirm_durability(&mut self) -> Result<(), Self::DurabilityError> {
            Ok(())
        }
    }

    impl NativeContinuationRemovableBlobStore for MemoryStore {
        fn remove(
            &mut self,
        ) -> NativeContinuationBlobRemovalResult<Self::Error> {
            if self.bytes.take().is_some() {
                Ok(NativeContinuationBlobRemoval::Removed)
            } else {
                Ok(NativeContinuationBlobRemoval::Missing)
            }
        }
    }

    impl NativeExecutableMemoryAdapter for NoOpAdapter {
        type Error = AdapterError;

        fn allocate_writable(
            &mut self,
            _request: NativeExecutableAllocationRequest,
        ) -> Result<NativeExecutableMappingReport, Self::Error> {
            self.calls = self.calls.saturating_add(1);
            Err(AdapterError::UnexpectedOperation)
        }

        fn copy_code(
            &mut self,
            _mapping: NativeExecutableMappingReport,
            _code: &[u8],
        ) -> Result<NativeExecutableCodeCopyReport, Self::Error> {
            self.calls = self.calls.saturating_add(1);
            Err(AdapterError::UnexpectedOperation)
        }

        fn protect_read_execute(
            &mut self,
            _mapping: NativeExecutableMappingReport,
        ) -> Result<NativeExecutableMappingReport, Self::Error> {
            self.calls = self.calls.saturating_add(1);
            Err(AdapterError::UnexpectedOperation)
        }

        fn release(
            &mut self,
            _request: NativeExecutableReleaseRequest,
        ) -> Result<(), Self::Error> {
            self.calls = self.calls.saturating_add(1);
            Err(AdapterError::UnexpectedOperation)
        }

        fn synchronize_instructions(
            &mut self,
            _request: NativeInstructionSyncRequest,
        ) -> Result<NativeInstructionSyncReport, Self::Error> {
            self.calls = self.calls.saturating_add(1);
            Err(AdapterError::UnexpectedOperation)
        }
    }

    fn encoded_limits(entry_limit: usize) -> Result<Vec<u8>, String> {
        let entry_limit = NonZeroUsize::new(entry_limit)
            .ok_or_else(|| String::from("test entry limit missing"))?;
        crate::execution_native::encode_native_executable_sequence_cache_limits(
            NativeExecutableSequenceCacheLimits::new(entry_limit),
        )
        .map_err(|error| format!("{error:?}"))
    }

    fn positive(value: usize) -> Result<NonZeroUsize, String> {
        NonZeroUsize::new(value)
            .ok_or_else(|| String::from("test positive value missing"))
    }

    #[test]
    fn lease_cache_missing_policy_is_no_op() -> Result<(), String> {
        let initial = NativeExecutableSequenceCacheLimits::new(positive(5)?);
        let mut cache =
            NativeExecutableSequenceLeaseCache::with_limits(initial);
        let mut adapter = NoOpAdapter::default();
        let mut store = MemoryStore::default();
        let activation =
            restore_and_apply_native_executable_sequence_lease_cache_limits(
                &mut store,
                &mut cache,
                &mut adapter,
                positive(40)?,
            )
            .map_err(|error| format!("{error:?}"))?;
        if activation
            == NativeExecutableSequenceLeaseCacheLimitsActivation::Missing
            && cache.limits() == initial
            && adapter.calls == 0
        {
            Ok(())
        } else {
            Err(String::from("missing lease-cache policy changed state"))
        }
    }

    #[test]
    fn lease_cache_restored_policy_reconfigures_empty_cache()
    -> Result<(), String> {
        let initial = NativeExecutableSequenceCacheLimits::new(positive(5)?);
        let requested = NativeExecutableSequenceCacheLimits::new(positive(2)?);
        let mut cache =
            NativeExecutableSequenceLeaseCache::with_limits(initial);
        let mut adapter = NoOpAdapter::default();
        let mut store = MemoryStore {
            bytes: Some(encoded_limits(2)?),
        };
        let activation =
            restore_and_apply_native_executable_sequence_lease_cache_limits(
                &mut store,
                &mut cache,
                &mut adapter,
                positive(40)?,
            )
            .map_err(|error| format!("{error:?}"))?;
        let NativeExecutableSequenceLeaseCacheLimitsActivation::Reconfigured {
            bytes,
            reconfiguration,
        } = activation
        else {
            return Err(String::from("restored lease policy stayed missing"));
        };
        if bytes == 40
            && reconfiguration.limit_transition() == (initial, requested)
            && reconfiguration.evicted_keys().is_empty()
            && reconfiguration.retired_keys().is_empty()
            && cache.limits() == requested
            && adapter.calls == 0
        {
            Ok(())
        } else {
            Err(String::from("lease-cache policy activation drifted"))
        }
    }

    #[test]
    fn ordinary_cache_invalid_policy_fails_before_mutation()
    -> Result<(), String> {
        let initial = NativeExecutableSequenceCacheLimits::new(positive(4)?);
        let mut cache = NativeExecutableSequenceCache::with_limits(initial);
        let mut adapter = NoOpAdapter::default();
        let mut store = MemoryStore { bytes: Some(vec![0; 40]) };
        let activation =
            restore_and_apply_native_executable_sequence_cache_limits(
                &mut store,
                &mut cache,
                &mut adapter,
                positive(40)?,
            );
        if matches!(
            activation,
            Err(
                NativeExecutableSequenceCacheLimitsActivationError::Persistence(
                    _
                ),
            )
        ) && cache.limits() == initial
            && adapter.calls == 0
        {
            Ok(())
        } else {
            Err(String::from(
                "invalid durable policy changed ordinary cache",
            ))
        }
    }

    #[test]
    fn evicted_policy_does_not_change_live_cache() -> Result<(), String> {
        let initial = NativeExecutableSequenceCacheLimits::new(positive(5)?);
        let mut cache = NativeExecutableSequenceCache::with_limits(initial);
        let mut adapter = NoOpAdapter::default();
        let mut store = MemoryStore {
            bytes: Some(encoded_limits(2)?),
        };
        let eviction =
            evict_native_executable_sequence_cache_limits_durably(&mut store)
                .map_err(|error| format!("{error:?}"))?;
        let activation =
            restore_and_apply_native_executable_sequence_cache_limits(
                &mut store,
                &mut cache,
                &mut adapter,
                positive(40)?,
            )
            .map_err(|error| format!("{error:?}"))?;
        if eviction
            == NativeExecutableSequenceCacheLimitsDurableRemoval::Durable
            && activation
                == NativeExecutableSequenceCacheLimitsActivation::Missing
            && cache.limits() == initial
            && adapter.calls == 0
        {
            Ok(())
        } else {
            Err(String::from(
                "durable policy eviction changed live cache state",
            ))
        }
    }

    #[test]
    fn ordinary_cache_missing_policy_is_no_op() -> Result<(), String> {
        let initial = NativeExecutableSequenceCacheLimits::new(positive(4)?);
        let mut cache = NativeExecutableSequenceCache::with_limits(initial);
        let mut adapter = NoOpAdapter::default();
        let mut store = MemoryStore::default();
        let activation =
            restore_and_apply_native_executable_sequence_cache_limits(
                &mut store,
                &mut cache,
                &mut adapter,
                positive(40)?,
            )
            .map_err(|error| format!("{error:?}"))?;
        if activation == NativeExecutableSequenceCacheLimitsActivation::Missing
            && cache.limits() == initial
            && adapter.calls == 0
        {
            Ok(())
        } else {
            Err(String::from("missing ordinary-cache policy changed state"))
        }
    }

    #[test]
    fn ordinary_cache_restored_policy_reconfigures_empty_cache()
    -> Result<(), String> {
        let initial = NativeExecutableSequenceCacheLimits::new(positive(4)?);
        let requested = NativeExecutableSequenceCacheLimits::new(positive(2)?);
        let mut cache = NativeExecutableSequenceCache::with_limits(initial);
        let mut adapter = NoOpAdapter::default();
        let mut store = MemoryStore {
            bytes: Some(encoded_limits(2)?),
        };
        let activation =
            restore_and_apply_native_executable_sequence_cache_limits(
                &mut store,
                &mut cache,
                &mut adapter,
                positive(40)?,
            )
            .map_err(|error| format!("{error:?}"))?;
        let NativeExecutableSequenceCacheLimitsActivation::Reconfigured {
            bytes,
            reconfiguration,
        } = activation
        else {
            return Err(String::from(
                "restored ordinary policy stayed missing",
            ));
        };
        if bytes == 40
            && reconfiguration.limit_transition() == (initial, requested)
            && reconfiguration.evicted_keys().is_empty()
            && cache.limits() == requested
            && adapter.calls == 0
        {
            Ok(())
        } else {
            Err(String::from("ordinary-cache policy activation drifted"))
        }
    }
}
