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
//   - Typed bounded persistence and explicit eviction of cache-limit policy.
// - Must-Not:
//   - Persist executable mappings, FIFO entries, usage, native keys, or choose
//     storage locations.
// - Allows:
//   - Inputs: immutable cache limits, positive byte bound, and one blob store.
//   - Outputs: explicit missing/restored limits, publication, or removal
//     evidence.
//   - Side effects: delegated through bounded opaque-blob persistence only.
// - Split-When:
//   - Cache manifest migration, eviction journals, or concurrent ownership gain
//     independent authority.
// - Merge-When:
//   - One durable executable-cache policy owner subsumes limit persistence.
// - Summary:
//   - Persists or evicts cache limits without granting executable authority.
// - Description:
//   - Canonical limit framing is validated before publication and after
//     restore.
// - Usage:
//   - Bind one preconfigured durable blob to future executable-cache policy.
// - Defaults:
//   - Missing durable limits are explicit and never invent cache configuration.
//
//! Typed bounded persistence and eviction for executable-cache limit policy.

use std::num::NonZeroUsize;

use store_port::{
    NativeContinuationBlobStore as BlobStore,
    NativeContinuationDurableBlobStore as DurableBlobStore,
    NativeContinuationRemovableBlobStore as RemovableBlobStore,
};

use crate::execution_native::{
    NativeExecutableSequenceCacheLimits,
    NativeExecutableSequenceCacheLimitsCodecError,
    decode_native_executable_sequence_cache_limits,
    encode_native_executable_sequence_cache_limits,
};
use crate::{blob_persistence, blob_store as store_port};

type BlobDurablePersistence<DurabilityError> =
    blob_persistence::NativeContinuationBlobDurablePersistence<DurabilityError>;
type BlobLoad = blob_persistence::NativeContinuationBlobPersistenceLoad;

/// Durable removal state for one cache-limit policy blob.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeExecutableSequenceCacheLimitsDurableRemoval<DurabilityError> {
    /// Removal committed and durability confirmation completed.
    Durable,
    /// No durable cache-limit policy existed.
    Missing,
    /// Removal committed, then durability confirmation failed.
    Removed {
        /// Exact post-removal durability failure.
        durability_error: DurabilityError,
    },
}

/// Cache-limit publication plus explicit post-publication durability state.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeExecutableSequenceCacheLimitsDurablePersistence<DurabilityError>
{
    /// Canonical publication and durability confirmation both completed.
    Durable {
        /// Exact typed publication evidence.
        write: NativeExecutableSequenceCacheLimitsPersistenceWrite,
    },
    /// Canonical publication committed, but durability confirmation failed.
    Published {
        /// Exact post-publication durability failure.
        durability_error: DurabilityError,
        /// Exact typed publication evidence.
        write: NativeExecutableSequenceCacheLimitsPersistenceWrite,
    },
}

/// Why one typed executable-cache limit persistence operation failed closed.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeExecutableSequenceCacheLimitsPersistenceError<StoreError> {
    /// Bounded opaque-blob orchestration or its outbound store failed.
    Blob(blob_persistence::NativeContinuationBlobPersistenceError<StoreError>),
    /// Canonical executable-cache limit framing or semantics failed.
    Codec(NativeExecutableSequenceCacheLimitsCodecError),
}

/// Result of one bounded executable-cache limit restoration.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeExecutableSequenceCacheLimitsPersistenceLoad {
    /// No durable cache-limit policy exists at the configured location.
    Missing,
    /// Canonical bytes reconstructed exact executable-cache limits.
    Restored {
        /// Exact canonical byte count returned by the adapter.
        bytes: usize,
        /// Reconstructed caller-owned cache limits.
        limits: NativeExecutableSequenceCacheLimits,
    },
}

/// Publication evidence from one successful canonical limit replacement.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeExecutableSequenceCacheLimitsPersistenceWrite {
    bytes: usize,
}

/// Result of typed limit publication plus durability confirmation.
pub type NativeExecutableSequenceCacheLimitsDurablePersistenceResult<
    StoreError,
    DurabilityError,
> = Result<
    NativeExecutableSequenceCacheLimitsDurablePersistence<DurabilityError>,
    NativeExecutableSequenceCacheLimitsPersistenceError<StoreError>,
>;

/// Durable cache-limit removal result specialized to one store type.
pub type NativeExecutableSequenceCacheLimitsDurableRemovalStoreResult<Store> =
    Result<
        NativeExecutableSequenceCacheLimitsDurableRemoval<
            <Store as DurableBlobStore>::DurabilityError,
        >,
        NativeExecutableSequenceCacheLimitsPersistenceError<
            <Store as BlobStore>::Error,
        >,
    >;

/// Durable typed limit result specialized to one store type.
pub type NativeExecutableSequenceCacheLimitsDurableStoreResult<Store> =
    NativeExecutableSequenceCacheLimitsDurablePersistenceResult<
        <Store as BlobStore>::Error,
        <Store as DurableBlobStore>::DurabilityError,
    >;

/// Result of one typed executable-cache limit persistence operation.
pub type NativeExecutableSequenceCacheLimitsPersistenceResult<
    Value,
    StoreError,
> = Result<
    Value,
    NativeExecutableSequenceCacheLimitsPersistenceError<StoreError>,
>;

impl<DurabilityError>
    NativeExecutableSequenceCacheLimitsDurableRemoval<DurabilityError>
{
    /// Returns post-removal durability failure when confirmation failed.
    #[must_use]
    pub const fn durability_error(&self) -> Option<&DurabilityError> {
        match self {
            Self::Removed { durability_error } => Some(durability_error),
            Self::Durable | Self::Missing => None,
        }
    }

    /// Reports whether a durable publication was actually removed.
    #[must_use]
    pub const fn is_removed(&self) -> bool {
        matches!(self, Self::Durable | Self::Removed { .. })
    }
}

impl<DurabilityError>
    NativeExecutableSequenceCacheLimitsDurablePersistence<DurabilityError>
{
    /// Returns the exact committed canonical byte count.
    #[must_use]
    pub const fn bytes(&self) -> usize {
        match self {
            Self::Durable { write } | Self::Published { write, .. } => {
                write.bytes()
            },
        }
    }

    /// Returns post-publication durability failure when confirmation failed.
    #[must_use]
    pub const fn durability_error(&self) -> Option<&DurabilityError> {
        match self {
            Self::Durable { .. } => None,
            Self::Published { durability_error, .. } => Some(durability_error),
        }
    }

    /// Reports whether storage explicitly confirmed publication durability.
    #[must_use]
    pub const fn is_durable(&self) -> bool {
        matches!(self, Self::Durable { .. })
    }
}

impl NativeExecutableSequenceCacheLimitsPersistenceWrite {
    /// Returns the exact canonical byte count passed to the outbound store.
    #[must_use]
    pub const fn bytes(self) -> usize {
        self.bytes
    }
}

fn map_durable_persistence<DurabilityError>(
    outcome: BlobDurablePersistence<DurabilityError>,
) -> NativeExecutableSequenceCacheLimitsDurablePersistence<DurabilityError> {
    match outcome {
        BlobDurablePersistence::Durable { write } => {
            NativeExecutableSequenceCacheLimitsDurablePersistence::Durable {
                write: NativeExecutableSequenceCacheLimitsPersistenceWrite {
                    bytes: write.bytes(),
                },
            }
        },
        BlobDurablePersistence::Published { durability_error, write } => {
            NativeExecutableSequenceCacheLimitsDurablePersistence::Published {
                durability_error,
                write: NativeExecutableSequenceCacheLimitsPersistenceWrite {
                    bytes: write.bytes(),
                },
            }
        },
    }
}

/// Durably removes the cache-limit policy at the configured blob location.
///
/// Missing policy is a successful no-op. Once removal commits, a later
/// durability-confirmation failure remains committed absence evidence.
///
/// # Errors
///
/// Returns outbound coordination or removal failure before absence commits.
pub fn evict_native_executable_sequence_cache_limits_durably<Store>(
    store: &mut Store,
) -> NativeExecutableSequenceCacheLimitsDurableRemovalStoreResult<Store>
where
    Store: DurableBlobStore + RemovableBlobStore,
{
    let outcome = blob_persistence::remove_blob_durably(store)
        .map_err(NativeExecutableSequenceCacheLimitsPersistenceError::Blob)?;
    match outcome {
        blob_persistence::NativeContinuationBlobDurableRemoval::Durable => {
            Ok(NativeExecutableSequenceCacheLimitsDurableRemoval::Durable)
        },
        blob_persistence::NativeContinuationBlobDurableRemoval::Missing => {
            Ok(NativeExecutableSequenceCacheLimitsDurableRemoval::Missing)
        },
        blob_persistence::NativeContinuationBlobDurableRemoval::Removed {
            durability_error,
        } => Ok(NativeExecutableSequenceCacheLimitsDurableRemoval::Removed {
            durability_error,
        }),
    }
}

/// Persists one exact executable-cache limit policy as canonical bounded bytes.
///
/// # Errors
///
/// Returns codec, byte-limit, or outbound-store failure before publication.
pub fn persist_native_executable_sequence_cache_limits<Store>(
    store: &mut Store,
    limits: NativeExecutableSequenceCacheLimits,
    maximum_bytes: NonZeroUsize,
) -> NativeExecutableSequenceCacheLimitsPersistenceResult<
    NativeExecutableSequenceCacheLimitsPersistenceWrite,
    Store::Error,
>
where
    Store: BlobStore,
{
    let bytes = encode_native_executable_sequence_cache_limits(limits)
        .map_err(NativeExecutableSequenceCacheLimitsPersistenceError::Codec)?;
    let write = blob_persistence::persist_blob(store, &bytes, maximum_bytes)
        .map_err(NativeExecutableSequenceCacheLimitsPersistenceError::Blob)?;
    Ok(NativeExecutableSequenceCacheLimitsPersistenceWrite {
        bytes: write.bytes(),
    })
}

/// Persists one exact executable-cache limit policy and confirms durability.
///
/// # Errors
///
/// Returns codec, byte-limit, or store failure before publication.
pub fn persist_native_executable_sequence_cache_limits_durably<Store>(
    store: &mut Store,
    limits: NativeExecutableSequenceCacheLimits,
    maximum_bytes: NonZeroUsize,
) -> NativeExecutableSequenceCacheLimitsDurableStoreResult<Store>
where
    Store: DurableBlobStore,
{
    let bytes = encode_native_executable_sequence_cache_limits(limits)
        .map_err(NativeExecutableSequenceCacheLimitsPersistenceError::Codec)?;
    let outcome =
        blob_persistence::persist_blob_durably(store, &bytes, maximum_bytes)
            .map_err(
                NativeExecutableSequenceCacheLimitsPersistenceError::Blob,
            )?;
    Ok(map_durable_persistence(outcome))
}

/// Restores one exact executable-cache limit policy from canonical bounded
/// bytes.
///
/// # Errors
///
/// Returns store, byte-limit, or codec evidence without inventing missing
/// configuration.
pub fn restore_native_executable_sequence_cache_limits<Store>(
    store: &mut Store,
    maximum_bytes: NonZeroUsize,
) -> NativeExecutableSequenceCacheLimitsPersistenceResult<
    NativeExecutableSequenceCacheLimitsPersistenceLoad,
    Store::Error,
>
where
    Store: BlobStore,
{
    let load = blob_persistence::restore_blob(store, maximum_bytes)
        .map_err(NativeExecutableSequenceCacheLimitsPersistenceError::Blob)?;
    let BlobLoad::Present { bytes } = load else {
        return Ok(NativeExecutableSequenceCacheLimitsPersistenceLoad::Missing);
    };
    let length = bytes.len();
    let limits = decode_native_executable_sequence_cache_limits(&bytes)
        .map_err(NativeExecutableSequenceCacheLimitsPersistenceError::Codec)?;
    Ok(
        NativeExecutableSequenceCacheLimitsPersistenceLoad::Restored {
            bytes: length,
            limits,
        },
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[derive(Clone, Copy, Debug, Eq, PartialEq)]
    enum TestStoreError {
        Remove,
        Replace,
    }

    #[derive(Clone, Copy, Debug, Eq, PartialEq)]
    enum TestDurabilityError {
        Failed,
    }

    #[derive(Debug, Default)]
    struct MemoryStore {
        bytes: Option<Vec<u8>>,
        durability_calls: usize,
        fail_durability: bool,
        fail_remove: bool,
        fail_replace: bool,
        remove_calls: usize,
        replace_calls: usize,
    }

    impl BlobStore for MemoryStore {
        type Error = TestStoreError;

        fn load(
            &mut self,
            _maximum_bytes: NonZeroUsize,
        ) -> Result<Option<Vec<u8>>, Self::Error> {
            Ok(self.bytes.clone())
        }

        fn replace(&mut self, bytes: &[u8]) -> Result<(), Self::Error> {
            self.replace_calls = self.replace_calls.saturating_add(1);
            if self.fail_replace {
                return Err(TestStoreError::Replace);
            }
            self.bytes = Some(bytes.to_vec());
            Ok(())
        }
    }

    impl RemovableBlobStore for MemoryStore {
        fn remove(
            &mut self,
        ) -> crate::blob_store::NativeContinuationBlobRemovalResult<Self::Error>
        {
            self.remove_calls = self.remove_calls.saturating_add(1);
            if self.fail_remove {
                return Err(TestStoreError::Remove);
            }
            if self.bytes.take().is_some() {
                Ok(crate::blob_store::NativeContinuationBlobRemoval::Removed)
            } else {
                Ok(crate::blob_store::NativeContinuationBlobRemoval::Missing)
            }
        }
    }

    impl DurableBlobStore for MemoryStore {
        type DurabilityError = TestDurabilityError;

        fn confirm_durability(&mut self) -> Result<(), Self::DurabilityError> {
            self.durability_calls = self.durability_calls.saturating_add(1);
            if self.fail_durability {
                Err(TestDurabilityError::Failed)
            } else {
                Ok(())
            }
        }
    }

    fn positive(value: usize) -> Result<NonZeroUsize, String> {
        NonZeroUsize::new(value)
            .ok_or_else(|| String::from("test positive value missing"))
    }

    #[test]
    fn durable_eviction_removes_policy() -> Result<(), String> {
        let limits = NativeExecutableSequenceCacheLimits::new(positive(3)?);
        let mut store = MemoryStore::default();
        let _write = persist_native_executable_sequence_cache_limits(
            &mut store,
            limits,
            positive(40)?,
        )
        .map_err(|error| format!("{error:?}"))?;
        let outcome =
            evict_native_executable_sequence_cache_limits_durably(&mut store)
                .map_err(|error| format!("{error:?}"))?;
        let load = restore_native_executable_sequence_cache_limits(
            &mut store,
            positive(40)?,
        )
        .map_err(|error| format!("{error:?}"))?;
        if outcome == NativeExecutableSequenceCacheLimitsDurableRemoval::Durable
            && outcome.is_removed()
            && store.remove_calls == 1
            && store.durability_calls == 1
            && load
                == NativeExecutableSequenceCacheLimitsPersistenceLoad::Missing
        {
            Ok(())
        } else {
            Err(String::from("durable cache-limit eviction drifted"))
        }
    }

    #[test]
    fn eviction_durability_failure_retains_absence() -> Result<(), String> {
        let limits = NativeExecutableSequenceCacheLimits::new(positive(4)?);
        let mut store = MemoryStore {
            bytes: Some(
                encode_native_executable_sequence_cache_limits(limits)
                    .map_err(|error| format!("{error:?}"))?,
            ),
            fail_durability: true,
            ..MemoryStore::default()
        };
        let outcome =
            evict_native_executable_sequence_cache_limits_durably(&mut store)
                .map_err(|error| format!("{error:?}"))?;
        if outcome
            == (NativeExecutableSequenceCacheLimitsDurableRemoval::Removed {
                durability_error: TestDurabilityError::Failed,
            })
            && outcome.is_removed()
            && outcome.durability_error() == Some(&TestDurabilityError::Failed)
            && store.bytes.is_none()
            && store.durability_calls == 1
        {
            Ok(())
        } else {
            Err(String::from(
                "cache-limit eviction durability evidence drifted",
            ))
        }
    }

    #[test]
    fn missing_eviction_skips_durability() -> Result<(), String> {
        let mut store = MemoryStore::default();
        let outcome =
            evict_native_executable_sequence_cache_limits_durably(&mut store)
                .map_err(|error| format!("{error:?}"))?;
        if outcome == NativeExecutableSequenceCacheLimitsDurableRemoval::Missing
            && !outcome.is_removed()
            && store.remove_calls == 1
            && store.durability_calls == 0
        {
            Ok(())
        } else {
            Err(String::from("missing cache-limit eviction drifted"))
        }
    }

    #[test]
    fn exact_limits_round_trip() -> Result<(), String> {
        let limits = NativeExecutableSequenceCacheLimits::new(positive(3)?)
            .with_mapping_limit(positive(5)?)
            .with_mapped_byte_limit(positive(7_000)?);
        let mut store = MemoryStore::default();
        let write = persist_native_executable_sequence_cache_limits(
            &mut store,
            limits,
            positive(40)?,
        )
        .map_err(|error| format!("{error:?}"))?;
        let load = restore_native_executable_sequence_cache_limits(
            &mut store,
            positive(40)?,
        )
        .map_err(|error| format!("{error:?}"))?;
        let expected =
            NativeExecutableSequenceCacheLimitsPersistenceLoad::Restored {
                bytes: 40,
                limits,
            };
        if write.bytes() == 40 && store.replace_calls == 1 && load == expected {
            Ok(())
        } else {
            Err(String::from("cache-limit persistence round trip drifted"))
        }
    }

    #[test]
    fn missing_limits_remain_explicit() -> Result<(), String> {
        let mut store = MemoryStore::default();
        let load = restore_native_executable_sequence_cache_limits(
            &mut store,
            positive(40)?,
        )
        .map_err(|error| format!("{error:?}"))?;
        if load == NativeExecutableSequenceCacheLimitsPersistenceLoad::Missing
            && store.replace_calls == 0
        {
            Ok(())
        } else {
            Err(String::from("missing cache limits invented policy"))
        }
    }

    #[test]
    fn byte_limit_rejects_before_store_mutation() -> Result<(), String> {
        let limits = NativeExecutableSequenceCacheLimits::new(positive(2)?);
        let mut store = MemoryStore::default();
        let error = persist_native_executable_sequence_cache_limits(
            &mut store,
            limits,
            positive(39)?,
        );
        if matches!(
            error,
            Err(NativeExecutableSequenceCacheLimitsPersistenceError::Blob(
                blob_persistence::NativeContinuationBlobPersistenceError::
                    ByteLimit {
                        maximum_bytes,
                        observed_bytes: 40,
                    },
            )) if maximum_bytes == positive(39)?
        ) && store.replace_calls == 0
            && store.bytes.is_none()
        {
            Ok(())
        } else {
            Err(String::from("cache-limit byte bound mutated store"))
        }
    }

    #[test]
    fn durability_failure_keeps_committed_limits() -> Result<(), String> {
        let limits = NativeExecutableSequenceCacheLimits::new(positive(4)?);
        let mut store = MemoryStore {
            fail_durability: true,
            ..MemoryStore::default()
        };
        let outcome = persist_native_executable_sequence_cache_limits_durably(
            &mut store,
            limits,
            positive(40)?,
        )
        .map_err(|error| format!("{error:?}"))?;
        let load = restore_native_executable_sequence_cache_limits(
            &mut store,
            positive(40)?,
        )
        .map_err(|error| format!("{error:?}"))?;
        let expected =
            NativeExecutableSequenceCacheLimitsPersistenceLoad::Restored {
                bytes: 40,
                limits,
            };
        if !outcome.is_durable()
            && outcome.bytes() == 40
            && outcome.durability_error() == Some(&TestDurabilityError::Failed)
            && store.replace_calls == 1
            && load == expected
        {
            Ok(())
        } else {
            Err(String::from("durability failure lost committed limits"))
        }
    }

    #[test]
    fn file_store_round_trip_is_durable() -> Result<(), String> {
        use std::fs::{create_dir, remove_dir_all};
        use std::process;

        use crate::file_blob_store::NativeContinuationFileBlobStore;

        let directory = std::env::temp_dir()
            .join(format!("malbolge-cache-limits-{}", process::id(),));
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
        let limits = NativeExecutableSequenceCacheLimits::new(positive(8)?)
            .with_mapping_limit(positive(13)?)
            .with_mapped_byte_limit(positive(65_536)?);
        let mut store = NativeContinuationFileBlobStore::new(destination);
        let outcome = persist_native_executable_sequence_cache_limits_durably(
            &mut store,
            limits,
            positive(40)?,
        )
        .map_err(|error| format!("{error:?}"))?;
        let load = restore_native_executable_sequence_cache_limits(
            &mut store,
            positive(40)?,
        )
        .map_err(|error| format!("{error:?}"))?;
        let expected =
            NativeExecutableSequenceCacheLimitsPersistenceLoad::Restored {
                bytes: 40,
                limits,
            };
        let valid = outcome.is_durable()
            && outcome.bytes() == 40
            && outcome.durability_error().is_none()
            && load == expected;
        drop(store);
        remove_dir_all(&directory).map_err(|error| {
            format!("test directory removal failed: {error}")
        })?;
        if valid {
            Ok(())
        } else {
            Err(String::from("file cache-limit persistence drifted"))
        }
    }

    #[test]
    fn malformed_stored_limits_fail_closed() -> Result<(), String> {
        let mut store = MemoryStore {
            bytes: Some(vec![0; 40]),
            ..MemoryStore::default()
        };
        let error = restore_native_executable_sequence_cache_limits(
            &mut store,
            positive(40)?,
        );
        if error
            == Err(NativeExecutableSequenceCacheLimitsPersistenceError::Codec(
                NativeExecutableSequenceCacheLimitsCodecError::Magic,
            ))
            && store.replace_calls == 0
        {
            Ok(())
        } else {
            Err(String::from("malformed durable cache limits were admitted"))
        }
    }

    #[test]
    fn store_failure_preserves_previous_publication() -> Result<(), String> {
        let previous = vec![0x5a; 40];
        let limits = NativeExecutableSequenceCacheLimits::new(positive(6)?);
        let mut store = MemoryStore {
            bytes: Some(previous.clone()),
            fail_replace: true,
            ..MemoryStore::default()
        };
        let error = persist_native_executable_sequence_cache_limits(
            &mut store,
            limits,
            positive(40)?,
        );
        if error
            == Err(NativeExecutableSequenceCacheLimitsPersistenceError::Blob(
                blob_persistence::NativeContinuationBlobPersistenceError::Store(
                    TestStoreError::Replace,
                ),
            ))
            && store.replace_calls == 1
            && store.bytes == Some(previous)
        {
            Ok(())
        } else {
            Err(String::from("store failure changed durable cache limits"))
        }
    }
}
