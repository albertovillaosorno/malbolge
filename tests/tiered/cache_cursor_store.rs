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
//   - Regression coverage for bounded trigger-cursor persistence and restore.
// - Must-Not:
//   - Define CAS ownership, scheduling, cache activation, or storage locations.
// - Allows:
//   - Inputs: deterministic in-memory blob-store fixtures and cadence cursors.
//   - Outputs: exact persistence, durability, missing, and failure evidence.
//   - Side effects: test-local memory mutation only.
// - Split-When:
//   - Conditional cursor ownership gains independent regression lifecycle.
// - Merge-When:
//   - Parent persistence module no longer requires private regression access.
// - Summary:
//   - Proves canonical cursor persistence fails closed and retains commit
//     state.
// - Description:
//   - Durability failure never masquerades as publication rollback.
// - Usage:
//   - Compiled only under Rust test configuration.
// - Defaults:
//   - Missing durable cursor state remains explicit.
//

//! Regression coverage for cache-trigger cadence cursor persistence.

use std::num::NonZeroU64;

use super::*;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum TestDurabilityError {
    Failed,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum TestStoreError {
    Replace,
}

#[derive(Debug, Default)]
struct MemoryStore {
    bytes: Option<Vec<u8>>,
    durability_calls: usize,
    fail_durability: bool,
    fail_replace: bool,
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

fn cursor(due_value: u64, interval_value: u64) -> Result<Cursor, String> {
    let due = NonZeroU64::new(due_value)
        .ok_or_else(|| String::from("test due sequence must be positive"))?;
    let interval = NonZeroU64::new(interval_value)
        .ok_or_else(|| String::from("test interval must be positive"))?;
    Ok(Cursor::new(due, interval))
}

fn positive(value: usize) -> Result<NonZeroUsize, String> {
    NonZeroUsize::new(value)
        .ok_or_else(|| String::from("test byte bound must be positive"))
}

#[test]
fn active_cursor_round_trips() -> Result<(), String> {
    let cadence = cursor(5, 3)?;
    let mut store = MemoryStore::default();
    let write = persist_native_executable_cache_limits_trigger_cadence(
        &mut store,
        cadence,
        positive(32)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    let load = restore_native_executable_cache_limits_trigger_cadence(
        &mut store,
        positive(32)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    let expected =
        NativeExecutableCacheLimitsTriggerCadencePersistenceLoad::Restored {
            bytes: 32,
            cadence,
        };
    if write.bytes() == 32 && store.replace_calls == 1 && load == expected {
        Ok(())
    } else {
        Err(String::from("active cursor persistence drifted"))
    }
}

#[test]
fn byte_limit_rejects_before_store_mutation() -> Result<(), String> {
    let mut store = MemoryStore::default();
    let error = persist_native_executable_cache_limits_trigger_cadence(
        &mut store,
        cursor(2, 4)?,
        positive(31)?,
    );
    if matches!(
        error,
        Err(NativeExecutableCacheLimitsTriggerCadencePersistenceError::Blob(
            blob_persistence::NativeContinuationBlobPersistenceError::
                ByteLimit {
                    maximum_bytes,
                    observed_bytes: 32,
                },
        )) if maximum_bytes == positive(31)?
    ) && store.replace_calls == 0
        && store.bytes.is_none()
    {
        Ok(())
    } else {
        Err(String::from("cursor byte bound mutated store"))
    }
}

#[test]
fn durability_failure_keeps_committed_cursor() -> Result<(), String> {
    let cadence = cursor(8, 5)?;
    let mut store = MemoryStore {
        fail_durability: true,
        ..MemoryStore::default()
    };
    let outcome =
        persist_native_executable_cache_limits_trigger_cadence_durably(
            &mut store,
            cadence,
            positive(32)?,
        )
        .map_err(|error| format!("{error:?}"))?;
    let load = restore_native_executable_cache_limits_trigger_cadence(
        &mut store,
        positive(32)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    let expected =
        NativeExecutableCacheLimitsTriggerCadencePersistenceLoad::Restored {
            bytes: 32,
            cadence,
        };
    if !outcome.is_durable()
        && outcome.bytes() == 32
        && outcome.durability_error() == Some(&TestDurabilityError::Failed)
        && store.durability_calls == 1
        && store.replace_calls == 1
        && load == expected
    {
        Ok(())
    } else {
        Err(String::from("cursor durability failure lost commit"))
    }
}

#[test]
fn exhausted_cursor_round_trips() -> Result<(), String> {
    let interval = NonZeroU64::new(7)
        .ok_or_else(|| String::from("test interval must be positive"))?;
    let cadence = Cursor::exhausted(interval);
    let mut store = MemoryStore::default();
    let outcome =
        persist_native_executable_cache_limits_trigger_cadence_durably(
            &mut store,
            cadence,
            positive(32)?,
        )
        .map_err(|error| format!("{error:?}"))?;
    let load = restore_native_executable_cache_limits_trigger_cadence(
        &mut store,
        positive(32)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    if outcome.is_durable()
        && outcome.bytes() == 32
        && load
            == (NativeExecutableCacheLimitsTriggerCadencePersistenceLoad::
                Restored {
                    bytes: 32,
                    cadence,
                })
    {
        Ok(())
    } else {
        Err(String::from("exhausted cursor persistence drifted"))
    }
}

#[test]
fn malformed_stored_cursor_fails_closed() -> Result<(), String> {
    let mut store = MemoryStore {
        bytes: Some(vec![0; 32]),
        ..MemoryStore::default()
    };
    let error = restore_native_executable_cache_limits_trigger_cadence(
        &mut store,
        positive(32)?,
    );
    if error
        == Err(
            NativeExecutableCacheLimitsTriggerCadencePersistenceError::Codec(
                CursorCodecError::Magic,
            ),
        )
        && store.replace_calls == 0
    {
        Ok(())
    } else {
        Err(String::from("malformed durable cursor was admitted"))
    }
}

#[test]
fn missing_cursor_remains_explicit() -> Result<(), String> {
    let mut store = MemoryStore::default();
    let load = restore_native_executable_cache_limits_trigger_cadence(
        &mut store,
        positive(32)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    if load == NativeExecutableCacheLimitsTriggerCadencePersistenceLoad::Missing
        && store.replace_calls == 0
    {
        Ok(())
    } else {
        Err(String::from("missing durable cursor invented state"))
    }
}

#[test]
fn store_failure_preserves_previous_publication() -> Result<(), String> {
    let previous = vec![0x5a; 32];
    let mut store = MemoryStore {
        bytes: Some(previous.clone()),
        fail_replace: true,
        ..MemoryStore::default()
    };
    let error = persist_native_executable_cache_limits_trigger_cadence(
        &mut store,
        cursor(3, 6)?,
        positive(32)?,
    );
    if error
        == Err(
            NativeExecutableCacheLimitsTriggerCadencePersistenceError::Blob(
                blob_persistence::NativeContinuationBlobPersistenceError::Store(
                    TestStoreError::Replace,
                ),
            ),
        )
        && store.replace_calls == 1
        && store.bytes == Some(previous)
    {
        Ok(())
    } else {
        Err(String::from(
            "cursor store failure changed prior publication",
        ))
    }
}
