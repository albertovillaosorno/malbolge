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
//   - Root-tree regression coverage for bounded blob persistence.
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
//   - Proves bounded blob persistence behavior from the root test tree.
// - Description:
//   - Loaded as a test-only child module to retain private-item access.
// - Usage:
//   - Selected by the parent module only when Rust test configuration is set.
// - Defaults:
//   - Production builds never compile this regression module.
//

//! Root-tree regression coverage for bounded blob persistence.

use std::fs::{create_dir_all, remove_dir_all};
use std::io::ErrorKind;
use std::{env, process};

use super::*;
use crate::blob_store::{
    NativeContinuationBlobConditionalRemoval,
    NativeContinuationBlobConditionalRemovalResult,
    NativeContinuationBlobRemoval, NativeContinuationBlobRemovalResult,
    NativeContinuationBlobStore,
    NativeContinuationConditionalRemovableBlobStore,
    NativeContinuationDurableBlobStore, NativeContinuationRemovableBlobStore,
};
use crate::file_blob_store::NativeContinuationFileBlobStore;

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
    durability_calls: usize,
    fail_durability: bool,
    fail_remove: bool,
}

impl NativeContinuationBlobStore for MemoryStore {
    type Error = StoreError;

    fn load(
        &mut self,
        _maximum_bytes: NonZeroUsize,
    ) -> Result<Option<Vec<u8>>, Self::Error> {
        Ok(self.bytes.clone())
    }

    fn replace(&mut self, bytes: &[u8]) -> Result<(), Self::Error> {
        self.bytes = Some(bytes.to_vec());
        Ok(())
    }
}

impl NativeContinuationConditionalRemovableBlobStore for MemoryStore {
    fn compare_and_remove(
        &mut self,
        expected: Option<&[u8]>,
        _maximum_bytes: NonZeroUsize,
    ) -> NativeContinuationBlobConditionalRemovalResult<Self::Error> {
        if self.bytes.as_deref() != expected {
            return Ok(NativeContinuationBlobConditionalRemoval::Conflict {
                current: self.bytes.clone(),
            });
        }
        if self.fail_remove {
            return Err(StoreError::Failed);
        }
        if self.bytes.take().is_some() {
            Ok(NativeContinuationBlobConditionalRemoval::Removed)
        } else {
            Ok(NativeContinuationBlobConditionalRemoval::Missing)
        }
    }
}

impl NativeContinuationRemovableBlobStore for MemoryStore {
    fn remove(&mut self) -> NativeContinuationBlobRemovalResult<Self::Error> {
        if self.fail_remove {
            return Err(StoreError::Failed);
        }
        if self.bytes.take().is_some() {
            Ok(NativeContinuationBlobRemoval::Removed)
        } else {
            Ok(NativeContinuationBlobRemoval::Missing)
        }
    }
}

impl NativeContinuationDurableBlobStore for MemoryStore {
    type DurabilityError = DurabilityError;

    fn confirm_durability(&mut self) -> Result<(), Self::DurabilityError> {
        self.durability_calls = self.durability_calls.saturating_add(1);
        if self.fail_durability {
            Err(DurabilityError::Failed)
        } else {
            Ok(())
        }
    }
}

#[test]
fn conditional_durability_failure_retains_removal() -> Result<(), String> {
    let expected = vec![4, 5, 6];
    let mut store = MemoryStore {
        bytes: Some(expected.clone()),
        fail_durability: true,
        ..MemoryStore::default()
    };
    let maximum_bytes = NonZeroUsize::new(expected.len())
        .ok_or_else(|| String::from("test bound missing"))?;
    let outcome = compare_and_remove_blob_durably(
        &mut store,
        Some(&expected),
        maximum_bytes,
    )
    .map_err(|error| format!("{error:?}"))?;
    if outcome
        == (NativeContinuationBlobConditionalDurableRemoval::Removed {
            durability_error: DurabilityError::Failed,
        })
        && store.bytes.is_none()
        && store.durability_calls == 1
    {
        Ok(())
    } else {
        Err(String::from(
            "conditional durability failure lost committed removal",
        ))
    }
}

#[test]
fn conditional_missing_skips_durability_confirmation() -> Result<(), String> {
    let mut store = MemoryStore::default();
    let maximum_bytes = NonZeroUsize::new(8)
        .ok_or_else(|| String::from("test bound missing"))?;
    let outcome =
        compare_and_remove_blob_durably(&mut store, None, maximum_bytes)
            .map_err(|error| format!("{error:?}"))?;
    if outcome == NativeContinuationBlobConditionalDurableRemoval::Missing
        && store.durability_calls == 0
    {
        Ok(())
    } else {
        Err(String::from(
            "conditional missing removal requested durability",
        ))
    }
}

#[test]
fn conditional_conflict_preserves_publication() -> Result<(), String> {
    let current = vec![7, 8, 9];
    let expected = vec![1, 2, 3];
    let mut store = MemoryStore {
        bytes: Some(current.clone()),
        ..MemoryStore::default()
    };
    let maximum_bytes = NonZeroUsize::new(current.len())
        .ok_or_else(|| String::from("test bound missing"))?;
    let outcome = compare_and_remove_blob_durably(
        &mut store,
        Some(&expected),
        maximum_bytes,
    )
    .map_err(|error| format!("{error:?}"))?;
    if outcome.conflict() == Some(current.as_slice())
        && store.bytes == Some(current)
        && store.durability_calls == 0
    {
        Ok(())
    } else {
        Err(String::from(
            "conditional removal conflict changed publication",
        ))
    }
}

#[test]
fn conditional_removal_match_confirms_absence() -> Result<(), String> {
    let expected = vec![10, 11, 12];
    let mut store = MemoryStore {
        bytes: Some(expected.clone()),
        ..MemoryStore::default()
    };
    let maximum_bytes = NonZeroUsize::new(expected.len())
        .ok_or_else(|| String::from("test bound missing"))?;
    let outcome = compare_and_remove_blob_durably(
        &mut store,
        Some(&expected),
        maximum_bytes,
    )
    .map_err(|error| format!("{error:?}"))?;
    if outcome == NativeContinuationBlobConditionalDurableRemoval::Durable
        && store.bytes.is_none()
        && store.durability_calls == 1
    {
        Ok(())
    } else {
        Err(String::from("conditional removal did not confirm absence"))
    }
}

#[test]
fn conditional_file_store_rejects_stale_removal() -> Result<(), String> {
    let directory = env::temp_dir().join(format!(
        "malbolge-blob-conditional-remove-{}",
        process::id(),
    ));
    match remove_dir_all(&directory) {
        Ok(()) => {},
        Err(error) if error.kind() == ErrorKind::NotFound => {},
        Err(error) => {
            return Err(format!("test directory cleanup failed: {error}"));
        },
    }
    create_dir_all(&directory)
        .map_err(|error| format!("test directory create failed: {error}"))?;
    let current = [13, 14, 15];
    let stale = [1, 2, 3];
    let maximum_bytes = NonZeroUsize::new(current.len())
        .ok_or_else(|| String::from("test bound missing"))?;
    let destination = directory.join("blob.bin");
    let mut store = NativeContinuationFileBlobStore::new(destination);
    let _write = persist_blob(&mut store, &current, maximum_bytes)
        .map_err(|error| format!("{error:?}"))?;
    let conflict = compare_and_remove_blob_durably(
        &mut store,
        Some(&stale),
        maximum_bytes,
    )
    .map_err(|error| format!("{error:?}"))?;
    let removed = compare_and_remove_blob_durably(
        &mut store,
        Some(&current),
        maximum_bytes,
    )
    .map_err(|error| format!("{error:?}"))?;
    let load = restore_blob(&mut store, maximum_bytes)
        .map_err(|error| format!("{error:?}"))?;
    drop(store);
    remove_dir_all(&directory)
        .map_err(|error| format!("test directory removal failed: {error}"))?;
    if conflict.conflict() == Some(current.as_slice())
        && removed == NativeContinuationBlobConditionalDurableRemoval::Durable
        && load == NativeContinuationBlobPersistenceLoad::Missing
    {
        Ok(())
    } else {
        Err(String::from("file conditional removal evidence drifted"))
    }
}

#[test]
fn durable_removal_confirms_committed_absence() -> Result<(), String> {
    let mut store = MemoryStore {
        bytes: Some(vec![1, 2, 3]),
        ..MemoryStore::default()
    };
    let outcome = remove_blob_durably(&mut store)
        .map_err(|error| format!("{error:?}"))?;
    if outcome == NativeContinuationBlobDurableRemoval::Durable
        && store.bytes.is_none()
        && store.durability_calls == 1
    {
        Ok(())
    } else {
        Err(String::from("durable removal evidence drifted"))
    }
}

#[test]
fn durability_failure_keeps_removed_state() -> Result<(), String> {
    let mut store = MemoryStore {
        bytes: Some(vec![4, 5, 6]),
        fail_durability: true,
        ..MemoryStore::default()
    };
    let outcome = remove_blob_durably(&mut store)
        .map_err(|error| format!("{error:?}"))?;
    if outcome
        == (NativeContinuationBlobDurableRemoval::Removed {
            durability_error: DurabilityError::Failed,
        })
        && store.bytes.is_none()
        && store.durability_calls == 1
    {
        Ok(())
    } else {
        Err(String::from(
            "durability failure did not retain committed removal",
        ))
    }
}

#[test]
fn file_store_removal_round_trip() -> Result<(), String> {
    let directory =
        env::temp_dir().join(format!("malbolge-blob-remove-{}", process::id()));
    match remove_dir_all(&directory) {
        Ok(()) => {},
        Err(error) if error.kind() == ErrorKind::NotFound => {},
        Err(error) => {
            return Err(format!("test directory cleanup failed: {error}"));
        },
    }
    create_dir_all(&directory)
        .map_err(|error| format!("test directory create failed: {error}"))?;
    let destination = directory.join("blob.bin");
    let mut store = NativeContinuationFileBlobStore::new(destination);
    let _write = persist_blob(
        &mut store,
        &[7, 8, 9],
        NonZeroUsize::new(3)
            .ok_or_else(|| String::from("test bound missing"))?,
    )
    .map_err(|error| format!("{error:?}"))?;
    let removed = remove_blob_durably(&mut store)
        .map_err(|error| format!("{error:?}"))?;
    let missing = remove_blob_durably(&mut store)
        .map_err(|error| format!("{error:?}"))?;
    let load = restore_blob(
        &mut store,
        NonZeroUsize::new(3)
            .ok_or_else(|| String::from("test bound missing"))?,
    )
    .map_err(|error| format!("{error:?}"))?;
    drop(store);
    remove_dir_all(&directory)
        .map_err(|error| format!("test directory removal failed: {error}"))?;
    if removed == NativeContinuationBlobDurableRemoval::Durable
        && missing == NativeContinuationBlobDurableRemoval::Missing
        && load == NativeContinuationBlobPersistenceLoad::Missing
    {
        Ok(())
    } else {
        Err(String::from("file blob removal round trip drifted"))
    }
}

#[test]
fn missing_removal_skips_durability_confirmation() -> Result<(), String> {
    let mut store = MemoryStore::default();
    let outcome = remove_blob_durably(&mut store)
        .map_err(|error| format!("{error:?}"))?;
    if outcome == NativeContinuationBlobDurableRemoval::Missing
        && store.durability_calls == 0
    {
        Ok(())
    } else {
        Err(String::from("missing removal requested durability"))
    }
}

#[test]
fn removal_failure_preserves_publication() -> Result<(), String> {
    let original = vec![10, 11, 12];
    let mut store = MemoryStore {
        bytes: Some(original.clone()),
        fail_remove: true,
        ..MemoryStore::default()
    };
    let outcome = remove_blob_durably(&mut store);
    if matches!(
        outcome,
        Err(NativeContinuationBlobPersistenceError::Store(
            StoreError::Failed,
        ))
    ) && store.bytes == Some(original)
        && store.durability_calls == 0
    {
        Ok(())
    } else {
        Err(String::from("failed removal changed publication"))
    }
}
