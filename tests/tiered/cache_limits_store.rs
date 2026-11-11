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
//   - Root-tree regression coverage for cache-limit persistence.
// - Must-Not:
//   - Define production semantics or replace the parent module's authority.
// - Allows:
//   - Inputs: the parent module's test-visible implementation surface.
//   - Outputs: deterministic regression evidence.
//   - Side effects: test-only in-memory or filesystem fixture effects.
// - Split-When:
//   - The regression surface requires an independent integration lifecycle.
// - Merge-When:
//   - The parent boundary no longer requires private regression access.
// - Summary:
//   - Proves cache-limit persistence behavior from the root test tree.
// - Description:
//   - Loaded as a test-only child module to retain private-item access.
// - Usage:
//   - Selected by the parent module only when Rust test configuration is set.
// - Defaults:
//   - Production builds never compile this regression module.
//

//! Root-tree regression coverage for cache-limit persistence.

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
        && load == NativeExecutableSequenceCacheLimitsPersistenceLoad::Missing
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
    create_dir(&directory)
        .map_err(|error| format!("test directory create failed: {error}"))?;
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
    remove_dir_all(&directory)
        .map_err(|error| format!("test directory removal failed: {error}"))?;
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
