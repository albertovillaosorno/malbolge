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
mod tests {
    use super::*;
    use crate::blob_store::{
        NativeContinuationBlobConditionalPublication,
        NativeContinuationBlobConditionalPublicationResult,
        NativeContinuationBlobConditionalRemoval,
        NativeContinuationBlobConditionalRemovalResult,
        NativeContinuationBlobRemoval, NativeContinuationBlobRemovalResult,
        NativeContinuationRemovableBlobStore,
    };

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

    impl ConditionalRemoveStore for MemoryStore {
        fn compare_and_remove(
            &mut self,
            expected: Option<&[u8]>,
            _maximum_bytes: NonZeroUsize,
        ) -> NativeContinuationBlobConditionalRemovalResult<Self::Error>
        {
            if self.fail_store {
                return Err(StoreError::Failed);
            }
            if self.bytes.as_deref() != expected {
                return Ok(
                    NativeContinuationBlobConditionalRemoval::Conflict {
                        current: self.bytes.clone(),
                    },
                );
            }
            if self.bytes.take().is_some() {
                Ok(NativeContinuationBlobConditionalRemoval::Removed)
            } else {
                Ok(NativeContinuationBlobConditionalRemoval::Missing)
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

    impl NativeContinuationRemovableBlobStore for MemoryStore {
        fn remove(
            &mut self,
        ) -> NativeContinuationBlobRemovalResult<Self::Error> {
            if self.fail_store {
                return Err(StoreError::Failed);
            }
            if self.bytes.take().is_some() {
                Ok(NativeContinuationBlobRemoval::Removed)
            } else {
                Ok(NativeContinuationBlobRemoval::Missing)
            }
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
    fn conflict_returns_exact_current_limits() -> Result<(), String> {
        let expected = limits(2)?;
        let current = limits(3)?;
        let candidate = limits(4)?;
        let current_bytes =
            encode_native_executable_sequence_cache_limits(current)
                .map_err(|error| format!("{error:?}"))?;
        let mut store = MemoryStore {
            bytes: Some(current_bytes.clone()),
            ..MemoryStore::default()
        };
        let outcome =
            compare_and_swap_native_executable_sequence_cache_limits_durably(
                &mut store,
                Some(expected),
                candidate,
                positive(40)?,
            )
            .map_err(|error| format!("{error:?}"))?;
        if outcome
            == (NativeExecutableSequenceCacheLimitsCas::Conflict {
                candidate,
                current: Some(current),
                expected: Some(expected),
            })
            && store.bytes == Some(current_bytes)
        {
            Ok(())
        } else {
            Err(String::from("cache-limit CAS conflict evidence drifted"))
        }
    }

    #[test]
    fn durability_failure_keeps_committed_candidate() -> Result<(), String> {
        let candidate = limits(5)?;
        let mut store = MemoryStore {
            fail_durability: true,
            ..MemoryStore::default()
        };
        let outcome =
            compare_and_swap_native_executable_sequence_cache_limits_durably(
                &mut store,
                None,
                candidate,
                positive(40)?,
            )
            .map_err(|error| format!("{error:?}"))?;
        let bytes = store
            .bytes
            .as_deref()
            .ok_or_else(|| String::from("committed cache limits missing"))?;
        let restored = decode_native_executable_sequence_cache_limits(bytes)
            .map_err(|error| format!("{error:?}"))?;
        if outcome
            == (NativeExecutableSequenceCacheLimitsCas::Published {
                bytes: 40,
                current: candidate,
                durability_error: DurabilityError::Failed,
                previous: None,
            })
            && restored == candidate
        {
            Ok(())
        } else {
            Err(String::from("cache-limit durability evidence drifted"))
        }
    }

    #[test]
    fn eviction_conflict_returns_current_policy() -> Result<(), String> {
        let expected = limits(2)?;
        let current = limits(3)?;
        let current_bytes =
            encode_native_executable_sequence_cache_limits(current)
                .map_err(|error| format!("{error:?}"))?;
        let mut store = MemoryStore {
            bytes: Some(current_bytes.clone()),
            ..MemoryStore::default()
        };
        let outcome =
            evict_native_executable_sequence_cache_limits_if_current_durably(
                &mut store,
                expected,
                positive(40)?,
            )
            .map_err(|error| format!("{error:?}"))?;
        if outcome
            == (NativeExecutableSequenceCacheLimitsEviction::Conflict {
                current: Some(current),
                expected,
            })
            && store.bytes == Some(current_bytes)
        {
            Ok(())
        } else {
            Err(String::from("cache-limit eviction conflict drifted"))
        }
    }

    #[test]
    fn eviction_match_removes_policy() -> Result<(), String> {
        let expected = limits(4)?;
        let bytes = encode_native_executable_sequence_cache_limits(expected)
            .map_err(|error| format!("{error:?}"))?;
        let mut store = MemoryStore {
            bytes: Some(bytes),
            ..MemoryStore::default()
        };
        let outcome =
            evict_native_executable_sequence_cache_limits_if_current_durably(
                &mut store,
                expected,
                positive(40)?,
            )
            .map_err(|error| format!("{error:?}"))?;
        if outcome
            == (NativeExecutableSequenceCacheLimitsEviction::Durable {
                previous: expected,
            })
            && store.bytes.is_none()
        {
            Ok(())
        } else {
            Err(String::from("current cache-limit policy was not evicted"))
        }
    }

    #[test]
    fn eviction_malformed_conflict_fails_closed() -> Result<(), String> {
        let expected = limits(5)?;
        let mut store = MemoryStore {
            bytes: Some(vec![0; 40]),
            ..MemoryStore::default()
        };
        let result =
            evict_native_executable_sequence_cache_limits_if_current_durably(
                &mut store,
                expected,
                positive(40)?,
            );
        if matches!(
            result,
            Err(NativeExecutableSequenceCacheLimitsCasError::Codec(
                NativeExecutableSequenceCacheLimitsCodecError::Magic,
            ))
        ) && store.bytes == Some(vec![0; 40])
        {
            Ok(())
        } else {
            Err(String::from(
                "malformed cache-limit eviction conflict was admitted",
            ))
        }
    }

    #[test]
    fn eviction_durability_failure_retains_removal() -> Result<(), String> {
        let expected = limits(6)?;
        let bytes = encode_native_executable_sequence_cache_limits(expected)
            .map_err(|error| format!("{error:?}"))?;
        let mut store = MemoryStore {
            bytes: Some(bytes),
            fail_durability: true,
            ..MemoryStore::default()
        };
        let outcome =
            evict_native_executable_sequence_cache_limits_if_current_durably(
                &mut store,
                expected,
                positive(40)?,
            )
            .map_err(|error| format!("{error:?}"))?;
        if outcome
            == (NativeExecutableSequenceCacheLimitsEviction::Removed {
                durability_error: DurabilityError::Failed,
                previous: expected,
            })
            && store.bytes.is_none()
        {
            Ok(())
        } else {
            Err(String::from(
                "cache-limit eviction durability evidence drifted",
            ))
        }
    }

    #[test]
    fn eviction_missing_policy_is_conflict() -> Result<(), String> {
        let expected = limits(7)?;
        let mut store = MemoryStore::default();
        let outcome =
            evict_native_executable_sequence_cache_limits_if_current_durably(
                &mut store,
                expected,
                positive(40)?,
            )
            .map_err(|error| format!("{error:?}"))?;
        if outcome
            == (NativeExecutableSequenceCacheLimitsEviction::Conflict {
                current: None,
                expected,
            })
            && store.bytes.is_none()
        {
            Ok(())
        } else {
            Err(String::from("missing cache-limit policy was not conflict"))
        }
    }

    #[test]
    fn file_store_compare_and_swap_round_trip() -> Result<(), String> {
        use std::fs::{create_dir, remove_dir_all};
        use std::process;

        use crate::executable_cache_limits_persistence::{
            NativeExecutableSequenceCacheLimitsPersistenceLoad,
            restore_native_executable_sequence_cache_limits,
        };
        use crate::file_blob_store::NativeContinuationFileBlobStore;

        let directory = std::env::temp_dir()
            .join(format!("malbolge-cache-limits-cas-{}", process::id(),));
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
        let first = limits(9)?;
        let second = limits(10)?;
        let stale_candidate = limits(11)?;
        let initialized =
            compare_and_swap_native_executable_sequence_cache_limits_durably(
                &mut store,
                None,
                first,
                positive(40)?,
            )
            .map_err(|error| format!("{error:?}"))?;
        let updated =
            compare_and_swap_native_executable_sequence_cache_limits_durably(
                &mut store,
                Some(first),
                second,
                positive(40)?,
            )
            .map_err(|error| format!("{error:?}"))?;
        let conflict =
            compare_and_swap_native_executable_sequence_cache_limits_durably(
                &mut store,
                Some(first),
                stale_candidate,
                positive(40)?,
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
        let valid = initialized
            == NativeExecutableSequenceCacheLimitsCas::Durable {
                bytes: 40,
                current: first,
                previous: None,
            }
            && updated
                == NativeExecutableSequenceCacheLimitsCas::Durable {
                    bytes: 40,
                    current: second,
                    previous: Some(first),
                }
            && conflict
                == NativeExecutableSequenceCacheLimitsCas::Conflict {
                    candidate: stale_candidate,
                    current: Some(second),
                    expected: Some(first),
                }
            && restored == expected_restored;
        drop(store);
        remove_dir_all(&directory).map_err(|error| {
            format!("test directory removal failed: {error}")
        })?;
        if valid {
            Ok(())
        } else {
            Err(String::from("file cache-limit CAS round trip drifted"))
        }
    }

    #[test]
    fn file_store_guarded_eviction_preserves_newer() -> Result<(), String> {
        use std::fs::{create_dir_all, remove_dir_all};
        use std::io::ErrorKind;
        use std::{env, process};

        use crate::executable_cache_limits_persistence::{
            NativeExecutableSequenceCacheLimitsPersistenceLoad,
            persist_native_executable_sequence_cache_limits_durably,
            restore_native_executable_sequence_cache_limits,
        };
        use crate::file_blob_store::NativeContinuationFileBlobStore;

        let directory = env::temp_dir()
            .join(format!("malbolge-cache-limit-eviction-{}", process::id(),));
        match remove_dir_all(&directory) {
            Ok(()) => {},
            Err(error) if error.kind() == ErrorKind::NotFound => {},
            Err(error) => {
                return Err(format!("test directory cleanup failed: {error}"));
            },
        }
        create_dir_all(&directory).map_err(|error| {
            format!("test directory create failed: {error}")
        })?;
        let first = limits(8)?;
        let current = limits(9)?;
        let mut store =
            NativeContinuationFileBlobStore::new(directory.join("limits.bin"));
        let _write = persist_native_executable_sequence_cache_limits_durably(
            &mut store,
            current,
            positive(40)?,
        )
        .map_err(|error| format!("{error:?}"))?;
        let conflict =
            evict_native_executable_sequence_cache_limits_if_current_durably(
                &mut store,
                first,
                positive(40)?,
            )
            .map_err(|error| format!("{error:?}"))?;
        let removed =
            evict_native_executable_sequence_cache_limits_if_current_durably(
                &mut store,
                current,
                positive(40)?,
            )
            .map_err(|error| format!("{error:?}"))?;
        let load = restore_native_executable_sequence_cache_limits(
            &mut store,
            positive(40)?,
        )
        .map_err(|error| format!("{error:?}"))?;
        drop(store);
        remove_dir_all(&directory).map_err(|error| {
            format!("test directory removal failed: {error}")
        })?;
        if matches!(
            conflict,
            NativeExecutableSequenceCacheLimitsEviction::Conflict {
                current: Some(observed),
                ..
            } if observed == current
        ) && matches!(
            removed,
            NativeExecutableSequenceCacheLimitsEviction::Durable {
                previous,
            } if previous == current
        ) && load
            == NativeExecutableSequenceCacheLimitsPersistenceLoad::Missing
        {
            Ok(())
        } else {
            Err(String::from("file cache-limit eviction evidence drifted"))
        }
    }

    #[test]
    fn malformed_conflict_fails_closed() -> Result<(), String> {
        let mut store = MemoryStore {
            bytes: Some(vec![0; 40]),
            ..MemoryStore::default()
        };
        let result =
            compare_and_swap_native_executable_sequence_cache_limits_durably(
                &mut store,
                None,
                limits(6)?,
                positive(40)?,
            );
        if matches!(
            result,
            Err(NativeExecutableSequenceCacheLimitsCasError::Codec(
                NativeExecutableSequenceCacheLimitsCodecError::Magic,
            ))
        ) && store.bytes == Some(vec![0; 40])
        {
            Ok(())
        } else {
            Err(String::from("malformed cache-limit conflict was admitted"))
        }
    }

    #[test]
    fn missing_state_initializes_durably() -> Result<(), String> {
        let candidate = limits(7)?;
        let mut store = MemoryStore::default();
        let outcome =
            compare_and_swap_native_executable_sequence_cache_limits_durably(
                &mut store,
                None,
                candidate,
                positive(40)?,
            )
            .map_err(|error| format!("{error:?}"))?;
        let restored = store
            .bytes
            .as_deref()
            .map(decode_native_executable_sequence_cache_limits)
            .transpose()
            .map_err(|error| format!("{error:?}"))?;
        if outcome
            == (NativeExecutableSequenceCacheLimitsCas::Durable {
                bytes: 40,
                current: candidate,
                previous: None,
            })
            && restored == Some(candidate)
        {
            Ok(())
        } else {
            Err(String::from("cache-limit CAS initialization drifted"))
        }
    }

    #[test]
    fn store_failure_is_prepublication_error() -> Result<(), String> {
        let mut store = MemoryStore {
            fail_store: true,
            ..MemoryStore::default()
        };
        let result =
            compare_and_swap_native_executable_sequence_cache_limits_durably(
                &mut store,
                None,
                limits(8)?,
                positive(40)?,
            );
        if matches!(
            result,
            Err(NativeExecutableSequenceCacheLimitsCasError::Blob(
                NativeContinuationBlobPersistenceError::Store(
                    StoreError::Failed,
                ),
            ))
        ) && store.bytes.is_none()
        {
            Ok(())
        } else {
            Err(String::from("cache-limit CAS store failure drifted"))
        }
    }
}
