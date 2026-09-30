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
//   - Durable cache-limit CAS followed by live cache-limit activation.
// - Must-Not:
//   - Retry CAS conflicts, retry cache cleanup, reconcile retired leases,
//     persist executable residency, or pretend committed policy rolled back.
// - Allows:
//   - Inputs: expected optional limits, candidate limits, bounded conditional
//     durable store, one live cache owner, and its executable-memory adapter.
//   - Outputs: conflict, committed/live reconfiguration, or committed/live
//     reconfiguration failure with exact evidence from both boundaries.
//   - Side effects: one durable cache-limit CAS and, only after committed
//     publication, one transactional live-cache limit reconfiguration.
// - Split-When:
//   - Cross-process policy reconciliation or retry scheduling gains authority.
// - Merge-When:
//   - One cache lifecycle owner subsumes publication, activation, and recovery.
// - Summary:
//   - Applies only committed durable cache-limit policy to live cache state.
// - Description:
//   - Post-publication durability failure still denotes a committed candidate;
//     later live-cache failure is explicit divergence evidence, not rollback.
// - Usage:
//   - Use when one caller owns both durable policy publication and live cache.
// - Defaults:
//   - CAS conflict leaves live cache state untouched.
//
//! Durable cache-limit publication followed by live transactional activation.

use std::num::NonZeroUsize;

use crate::blob_store::{
    NativeContinuationBlobStore as BlobStore,
    NativeContinuationConditionalBlobStore as ConditionalBlobStore,
    NativeContinuationDurableBlobStore as DurableBlobStore,
};
use crate::executable_cache_limits_cas::{
    NativeExecutableSequenceCacheLimitsCas,
    NativeExecutableSequenceCacheLimitsCasError,
    compare_and_swap_native_executable_sequence_cache_limits_durably,
};
use crate::execution_native::{
    NativeExecutableMemoryAdapter, NativeExecutableSequenceCache,
    NativeExecutableSequenceCacheLimits,
    NativeExecutableSequenceCacheReconfiguration,
    NativeExecutableSequenceCacheReconfigurationFailure,
    NativeExecutableSequenceLeaseCache,
    NativeExecutableSequenceLeaseCacheReconfiguration,
    NativeExecutableSequenceLeaseCacheReconfigurationFailure,
};

/// Caller-owned inputs for one durable cache-limit publication and activation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeExecutableSequenceCacheLimitsDurableActivationRequest {
    candidate: NativeExecutableSequenceCacheLimits,
    expected: Option<NativeExecutableSequenceCacheLimits>,
    maximum_bytes: NonZeroUsize,
}

/// Durable publication plus one live-cache activation attempt.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeExecutableSequenceCacheLimitsDurableActivation<
    Reconfiguration,
    ReconfigurationFailure,
    DurabilityError,
> {
    /// Durable state differed from expectation; live cache stayed untouched.
    Conflict {
        /// Exact durable conflict evidence.
        publication: NativeExecutableSequenceCacheLimitsCas<DurabilityError>,
    },
    /// Policy committed but the live cache could not publish the same limits.
    ReconfigurationFailed {
        /// Exact committed durable publication evidence.
        publication: NativeExecutableSequenceCacheLimitsCas<DurabilityError>,
        /// Exact retained live-cache failure ownership.
        failure: ReconfigurationFailure,
    },
    /// Policy committed and the live cache published the same limits.
    Reconfigured {
        /// Exact committed durable publication evidence.
        publication: NativeExecutableSequenceCacheLimitsCas<DurabilityError>,
        /// Exact live-cache transition evidence.
        reconfiguration: Reconfiguration,
    },
}

/// Durable activation specialized to the ordinary executable-sequence cache.
pub type NativeExecutableSequenceCacheLimitsDurableCacheActivation<
    DurabilityError,
    AdapterError,
> = NativeExecutableSequenceCacheLimitsDurableActivation<
    NativeExecutableSequenceCacheReconfiguration,
    Box<NativeExecutableSequenceCacheReconfigurationFailure<AdapterError>>,
    DurabilityError,
>;

/// Durable activation specialized to the shared executable lease cache.
pub type NativeExecutableSequenceLeaseCacheLimitsDurableActivation<
    DurabilityError,
    AdapterError,
> = NativeExecutableSequenceCacheLimitsDurableActivation<
    NativeExecutableSequenceLeaseCacheReconfiguration,
    Box<NativeExecutableSequenceLeaseCacheReconfigurationFailure<AdapterError>>,
    DurabilityError,
>;

/// Ordinary-cache durable activation result specialized to store and adapter.
pub type NativeExecutableSequenceCacheLimitsDurableStoreResult<Store, Adapter> =
    Result<
        NativeExecutableSequenceCacheLimitsDurableCacheActivation<
            <Store as DurableBlobStore>::DurabilityError,
            <Adapter as NativeExecutableMemoryAdapter>::Error,
        >,
        NativeExecutableSequenceCacheLimitsCasError<
            <Store as BlobStore>::Error,
        >,
    >;

/// Lease-cache durable activation result specialized to store and adapter.
pub type NativeExecutableSequenceLeaseCacheLimitsDurableStoreResult<
    Store,
    Adapter,
> = Result<
    NativeExecutableSequenceLeaseCacheLimitsDurableActivation<
        <Store as DurableBlobStore>::DurabilityError,
        <Adapter as NativeExecutableMemoryAdapter>::Error,
    >,
    NativeExecutableSequenceCacheLimitsCasError<<Store as BlobStore>::Error>,
>;

impl NativeExecutableSequenceCacheLimitsDurableActivationRequest {
    /// Binds one expected durable state, replacement, and bounded byte budget.
    #[must_use]
    pub const fn new(
        expected: Option<NativeExecutableSequenceCacheLimits>,
        candidate: NativeExecutableSequenceCacheLimits,
        maximum_bytes: NonZeroUsize,
    ) -> Self {
        Self {
            candidate,
            expected,
            maximum_bytes,
        }
    }
}

impl<Reconfiguration, ReconfigurationFailure, DurabilityError>
    NativeExecutableSequenceCacheLimitsDurableActivation<
        Reconfiguration,
        ReconfigurationFailure,
        DurabilityError,
    >
{
    /// Returns whether durable and live policy agree after this operation.
    #[must_use]
    pub const fn is_reconfigured(&self) -> bool {
        matches!(self, Self::Reconfigured { .. })
    }

    /// Returns exact durable publication evidence for every typed outcome.
    #[must_use]
    pub const fn publication(
        &self,
    ) -> &NativeExecutableSequenceCacheLimitsCas<DurabilityError> {
        match self {
            Self::Conflict { publication }
            | Self::ReconfigurationFailed { publication, .. }
            | Self::Reconfigured { publication, .. } => publication,
        }
    }
}

fn activate_committed_limits<
    Reconfiguration,
    ReconfigurationFailure,
    DurabilityError,
    Apply,
>(
    publication: NativeExecutableSequenceCacheLimitsCas<DurabilityError>,
    apply: Apply,
) -> NativeExecutableSequenceCacheLimitsDurableActivation<
    Reconfiguration,
    ReconfigurationFailure,
    DurabilityError,
>
where
    Apply: FnOnce(
        NativeExecutableSequenceCacheLimits,
    ) -> Result<Reconfiguration, ReconfigurationFailure>,
{
    let committed_limits = match &publication {
        NativeExecutableSequenceCacheLimitsCas::Conflict { .. } => {
            return NativeExecutableSequenceCacheLimitsDurableActivation::
                Conflict { publication };
        },
        NativeExecutableSequenceCacheLimitsCas::Durable { current, .. }
        | NativeExecutableSequenceCacheLimitsCas::Published {
            current, ..
        } => *current,
    };
    match apply(committed_limits) {
        Ok(reconfiguration) => {
            NativeExecutableSequenceCacheLimitsDurableActivation::Reconfigured {
                publication,
                reconfiguration,
            }
        },
        Err(failure) => NativeExecutableSequenceCacheLimitsDurableActivation::
            ReconfigurationFailed {
                publication,
                failure,
            },
    }
}

/// Publishes cache-limit policy durably, then applies committed limits to the
/// ordinary executable-sequence cache.
///
/// Conflict performs no live-cache work. Both fully durable publication and
/// committed publication followed by durability-confirmation failure attempt
/// the same live reconfiguration. A live failure remains a typed outcome
/// because durable state already committed and cannot be represented as rolled
/// back.
///
/// # Errors
///
/// Returns only cache-limit CAS failures that happen before a typed publication
/// outcome exists.
pub fn publish_and_apply_executable_sequence_cache_limits_durably<
    Store,
    Adapter,
>(
    store: &mut Store,
    cache: &mut NativeExecutableSequenceCache,
    adapter: &mut Adapter,
    request: NativeExecutableSequenceCacheLimitsDurableActivationRequest,
) -> NativeExecutableSequenceCacheLimitsDurableStoreResult<Store, Adapter>
where
    Store: ConditionalBlobStore + DurableBlobStore,
    Adapter: NativeExecutableMemoryAdapter,
{
    let publication =
        compare_and_swap_native_executable_sequence_cache_limits_durably(
            store,
            request.expected,
            request.candidate,
            request.maximum_bytes,
        )?;
    Ok(activate_committed_limits(publication, |limits| {
        cache.reconfigure_limits(adapter, limits)
    }))
}

/// Publishes cache-limit policy durably, then applies committed limits to the
/// executable lease cache.
///
/// Conflict performs no live-cache work. Both fully durable publication and
/// committed publication followed by durability-confirmation failure attempt
/// lease-aware reconfiguration. Existing retired entries are not reconciled
/// implicitly, and any resident blockage or cleanup failure remains owned by
/// the returned typed outcome.
///
/// # Errors
///
/// Returns only cache-limit CAS failures that happen before a typed publication
/// outcome exists.
pub fn publish_and_apply_executable_sequence_lease_cache_limits_durably<
    Store,
    Adapter,
>(
    store: &mut Store,
    cache: &mut NativeExecutableSequenceLeaseCache,
    adapter: &mut Adapter,
    request: NativeExecutableSequenceCacheLimitsDurableActivationRequest,
) -> NativeExecutableSequenceLeaseCacheLimitsDurableStoreResult<Store, Adapter>
where
    Store: ConditionalBlobStore + DurableBlobStore,
    Adapter: NativeExecutableMemoryAdapter,
{
    let publication =
        compare_and_swap_native_executable_sequence_cache_limits_durably(
            store,
            request.expected,
            request.candidate,
            request.maximum_bytes,
        )?;
    Ok(activate_committed_limits(publication, |limits| {
        cache.reconfigure_limits(adapter, limits)
    }))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::blob_persistence::NativeContinuationBlobPersistenceError;
    use crate::blob_store::{
        NativeContinuationBlobConditionalPublication,
        NativeContinuationBlobConditionalPublicationResult,
    };
    use crate::execution_native::{
        NativeExecutableAllocationRequest, NativeExecutableCodeCopyReport,
        NativeExecutableMappingReport, NativeExecutableReleaseRequest,
        NativeInstructionSyncReport, NativeInstructionSyncRequest,
        encode_native_executable_sequence_cache_limits,
    };

    #[derive(Clone, Copy, Debug, Eq, PartialEq)]
    enum AdapterError {
        UnexpectedOperation,
    }

    #[derive(Clone, Copy, Debug, Eq, PartialEq)]
    enum DurabilityError {
        Failed,
    }

    #[derive(Clone, Copy, Debug, Eq, PartialEq)]
    enum StoreError {
        Failed,
    }

    #[derive(Debug, Default)]
    struct MemoryStore {
        bytes: Option<Vec<u8>>,
        fail_durability: bool,
        fail_store: bool,
    }

    #[derive(Debug, Default)]
    struct NoOpAdapter {
        calls: usize,
    }

    impl BlobStore for MemoryStore {
        type Error = StoreError;

        fn load(
            &mut self,
            _maximum_bytes: NonZeroUsize,
        ) -> Result<Option<Vec<u8>>, Self::Error> {
            if self.fail_store {
                Err(StoreError::Failed)
            } else {
                Ok(self.bytes.clone())
            }
        }

        fn replace(&mut self, bytes: &[u8]) -> Result<(), Self::Error> {
            if self.fail_store {
                Err(StoreError::Failed)
            } else {
                self.bytes = Some(bytes.to_vec());
                Ok(())
            }
        }
    }

    impl ConditionalBlobStore for MemoryStore {
        fn compare_and_swap(
            &mut self,
            expected: Option<&[u8]>,
            replacement: &[u8],
            _maximum_bytes: NonZeroUsize,
        ) -> NativeContinuationBlobConditionalPublicationResult<Self::Error>
        {
            if self.fail_store {
                return Err(StoreError::Failed);
            }
            if self.bytes.as_deref() != expected {
                return Ok(
                    NativeContinuationBlobConditionalPublication::Conflict {
                        current: self.bytes.clone(),
                    },
                );
            }
            self.bytes = Some(replacement.to_vec());
            Ok(NativeContinuationBlobConditionalPublication::Published)
        }
    }

    impl DurableBlobStore for MemoryStore {
        type DurabilityError = DurabilityError;

        fn confirm_durability(&mut self) -> Result<(), Self::DurabilityError> {
            if self.fail_durability {
                Err(DurabilityError::Failed)
            } else {
                Ok(())
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

    fn activation_request(
        expected: Option<NativeExecutableSequenceCacheLimits>,
        candidate: NativeExecutableSequenceCacheLimits,
    ) -> Result<
        NativeExecutableSequenceCacheLimitsDurableActivationRequest,
        String,
    > {
        Ok(
            NativeExecutableSequenceCacheLimitsDurableActivationRequest::new(
                expected,
                candidate,
                positive(40)?,
            ),
        )
    }

    fn limits(
        entries: usize,
    ) -> Result<NativeExecutableSequenceCacheLimits, String> {
        NonZeroUsize::new(entries)
            .map(NativeExecutableSequenceCacheLimits::new)
            .ok_or_else(|| String::from("test cache entry limit missing"))
    }

    fn positive(value: usize) -> Result<NonZeroUsize, String> {
        NonZeroUsize::new(value)
            .ok_or_else(|| String::from("test positive value missing"))
    }

    #[test]
    fn committed_failure_retains_publication_and_live_failure()
    -> Result<(), String> {
        let previous = limits(2)?;
        let candidate = limits(3)?;
        let publication = NativeExecutableSequenceCacheLimitsCas::Published {
            bytes: 40,
            current: candidate,
            durability_error: DurabilityError::Failed,
            previous: Some(previous),
        };
        let outcome = activate_committed_limits(publication, |limits| {
            if limits == candidate {
                Err::<(), &'static str>("blocked")
            } else {
                Err::<(), &'static str>("wrong limits")
            }
        });
        match outcome {
            NativeExecutableSequenceCacheLimitsDurableActivation::
                ReconfigurationFailed {
                    publication:
                        NativeExecutableSequenceCacheLimitsCas::Published {
                            current,
                            durability_error,
                            previous: retained_previous,
                            ..
                        },
                    failure,
                } if current == candidate
                    && durability_error == DurabilityError::Failed
                    && retained_previous == Some(previous)
                    && failure == "blocked" =>
            {
                Ok(())
            },
            _ => Err(String::from(
                "committed live failure lost durable publication evidence",
            )),
        }
    }

    #[test]
    fn conflict_leaves_ordinary_cache_untouched() -> Result<(), String> {
        let expected = limits(2)?;
        let current = limits(3)?;
        let candidate = limits(4)?;
        let initial = limits(5)?;
        let mut store = MemoryStore {
            bytes: Some(
                encode_native_executable_sequence_cache_limits(current)
                    .map_err(|error| format!("{error:?}"))?,
            ),
            ..MemoryStore::default()
        };
        let mut cache = NativeExecutableSequenceCache::with_limits(initial);
        let mut adapter = NoOpAdapter::default();
        let outcome =
            publish_and_apply_executable_sequence_cache_limits_durably(
                &mut store,
                &mut cache,
                &mut adapter,
                activation_request(Some(expected), candidate)?,
            )
            .map_err(|error| format!("{error:?}"))?;
        if matches!(
            outcome,
            NativeExecutableSequenceCacheLimitsDurableActivation::Conflict {
                publication:
                    NativeExecutableSequenceCacheLimitsCas::Conflict {
                        current: Some(observed),
                        ..
                    },
            } if observed == current
        ) && cache.limits() == initial
            && adapter.calls == 0
        {
            Ok(())
        } else {
            Err(String::from("CAS conflict changed ordinary live cache"))
        }
    }

    #[test]
    fn durable_commit_reconfigures_lease_cache() -> Result<(), String> {
        let initial = limits(5)?;
        let candidate = limits(2)?;
        let mut store = MemoryStore::default();
        let mut cache =
            NativeExecutableSequenceLeaseCache::with_limits(initial);
        let mut adapter = NoOpAdapter::default();
        let outcome =
            publish_and_apply_executable_sequence_lease_cache_limits_durably(
                &mut store,
                &mut cache,
                &mut adapter,
                activation_request(None, candidate)?,
            )
            .map_err(|error| format!("{error:?}"))?;
        match outcome {
            NativeExecutableSequenceCacheLimitsDurableActivation::Reconfigured {
                publication:
                    NativeExecutableSequenceCacheLimitsCas::Durable {
                        current,
                        ..
                    },
                reconfiguration,
            } if current == candidate
                && reconfiguration.limit_transition()
                    == (initial, candidate)
                && reconfiguration.evicted_keys().is_empty()
                && reconfiguration.retired_keys().is_empty()
                && cache.limits() == candidate
                && adapter.calls == 0 =>
            {
                Ok(())
            },
            _ => Err(String::from(
                "durable commit did not reconfigure lease cache",
            )),
        }
    }

    #[test]
    fn durable_commit_reconfigures_ordinary_cache() -> Result<(), String> {
        let initial = limits(5)?;
        let candidate = limits(2)?;
        let mut store = MemoryStore::default();
        let mut cache = NativeExecutableSequenceCache::with_limits(initial);
        let mut adapter = NoOpAdapter::default();
        let outcome =
            publish_and_apply_executable_sequence_cache_limits_durably(
                &mut store,
                &mut cache,
                &mut adapter,
                activation_request(None, candidate)?,
            )
            .map_err(|error| format!("{error:?}"))?;
        match outcome {
            NativeExecutableSequenceCacheLimitsDurableActivation::Reconfigured {
                publication:
                    NativeExecutableSequenceCacheLimitsCas::Durable {
                        current,
                        ..
                    },
                reconfiguration,
            } if current == candidate
                && reconfiguration.limit_transition()
                    == (initial, candidate)
                && reconfiguration.evicted_keys().is_empty()
                && cache.limits() == candidate
                && adapter.calls == 0 =>
            {
                Ok(())
            },
            _ => Err(String::from(
                "durable commit did not reconfigure ordinary cache",
            )),
        }
    }

    #[test]
    fn file_store_publication_and_live_activation_stay_aligned()
    -> Result<(), String> {
        use std::fs::{create_dir, remove_dir_all};
        use std::process;

        use crate::executable_cache_limits_persistence::{
            NativeExecutableSequenceCacheLimitsPersistenceLoad,
            restore_native_executable_sequence_cache_limits,
        };
        use crate::file_blob_store::NativeContinuationFileBlobStore;

        let directory = std::env::temp_dir()
            .join(format!("malbolge-cache-limit-live-{}", process::id(),));
        match remove_dir_all(&directory) {
            Ok(()) => {},
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {},
            Err(error) => {
                return Err(format!("test directory cleanup failed: {error}"));
            },
        }
        create_dir(&directory).map_err(|error| {
            format!("test directory create failed: {error}")
        })?;
        let destination = directory.join("limits.bin");
        let mut store = NativeContinuationFileBlobStore::new(destination);
        let initial = limits(5)?;
        let first = limits(3)?;
        let second = limits(2)?;
        let stale = limits(4)?;
        let mut cache = NativeExecutableSequenceCache::with_limits(initial);
        let mut adapter = NoOpAdapter::default();

        let initialized =
            publish_and_apply_executable_sequence_cache_limits_durably(
                &mut store,
                &mut cache,
                &mut adapter,
                activation_request(None, first)?,
            )
            .map_err(|error| format!("{error:?}"))?;
        let updated =
            publish_and_apply_executable_sequence_cache_limits_durably(
                &mut store,
                &mut cache,
                &mut adapter,
                activation_request(Some(first), second)?,
            )
            .map_err(|error| format!("{error:?}"))?;
        let conflicted =
            publish_and_apply_executable_sequence_cache_limits_durably(
                &mut store,
                &mut cache,
                &mut adapter,
                activation_request(Some(first), stale)?,
            )
            .map_err(|error| format!("{error:?}"))?;
        let restored = restore_native_executable_sequence_cache_limits(
            &mut store,
            positive(40)?,
        )
        .map_err(|error| format!("{error:?}"))?;
        let expected_restored =
            NativeExecutableSequenceCacheLimitsPersistenceLoad::Restored {
                bytes: 40,
                limits: second,
            };
        let valid = matches!(
            initialized,
            NativeExecutableSequenceCacheLimitsDurableActivation::Reconfigured {
                publication:
                    NativeExecutableSequenceCacheLimitsCas::Durable {
                        current,
                        ..
                    },
                ..
            } if current == first
        ) && matches!(
            updated,
            NativeExecutableSequenceCacheLimitsDurableActivation::Reconfigured {
                publication:
                    NativeExecutableSequenceCacheLimitsCas::Durable {
                        current,
                        ..
                    },
                ..
            } if current == second
        ) && matches!(
            conflicted,
            NativeExecutableSequenceCacheLimitsDurableActivation::Conflict {
                publication:
                    NativeExecutableSequenceCacheLimitsCas::Conflict {
                        current: Some(observed),
                        ..
                    },
            } if observed == second
        ) && cache.limits() == second
            && restored == expected_restored
            && adapter.calls == 0;
        drop(store);
        remove_dir_all(&directory).map_err(|error| {
            format!("test directory removal failed: {error}")
        })?;
        if valid {
            Ok(())
        } else {
            Err(String::from(
                "file durable publication and live cache drifted",
            ))
        }
    }

    #[test]
    fn post_commit_durability_failure_still_reconfigures_live_cache()
    -> Result<(), String> {
        let initial = limits(5)?;
        let candidate = limits(2)?;
        let mut store = MemoryStore {
            fail_durability: true,
            ..MemoryStore::default()
        };
        let mut cache = NativeExecutableSequenceCache::with_limits(initial);
        let mut adapter = NoOpAdapter::default();
        let outcome =
            publish_and_apply_executable_sequence_cache_limits_durably(
                &mut store,
                &mut cache,
                &mut adapter,
                activation_request(None, candidate)?,
            )
            .map_err(|error| format!("{error:?}"))?;
        match outcome {
            NativeExecutableSequenceCacheLimitsDurableActivation::Reconfigured {
                publication:
                    NativeExecutableSequenceCacheLimitsCas::Published {
                        current,
                        durability_error,
                        ..
                    },
                reconfiguration,
            } if current == candidate
                && durability_error == DurabilityError::Failed
                && reconfiguration.limit_transition()
                    == (initial, candidate)
                && cache.limits() == candidate
                && adapter.calls == 0 =>
            {
                Ok(())
            },
            _ => Err(String::from(
                "committed sync failure did not activate live cache",
            )),
        }
    }

    #[test]
    fn prepublication_store_failure_leaves_live_cache_untouched()
    -> Result<(), String> {
        let initial = limits(5)?;
        let candidate = limits(2)?;
        let mut store = MemoryStore {
            fail_store: true,
            ..MemoryStore::default()
        };
        let mut cache = NativeExecutableSequenceCache::with_limits(initial);
        let mut adapter = NoOpAdapter::default();
        let result = publish_and_apply_executable_sequence_cache_limits_durably(
            &mut store,
            &mut cache,
            &mut adapter,
            activation_request(None, candidate)?,
        );
        if matches!(
            result,
            Err(NativeExecutableSequenceCacheLimitsCasError::Blob(
                NativeContinuationBlobPersistenceError::Store(
                    StoreError::Failed,
                ),
            ))
        ) && cache.limits() == initial
            && adapter.calls == 0
        {
            Ok(())
        } else {
            Err(String::from(
                "prepublication store failure changed live cache",
            ))
        }
    }
}
