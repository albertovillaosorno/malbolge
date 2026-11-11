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
//   - Regression coverage for conditional durable trigger-cursor publication.
// - Must-Not:
//   - Consume trigger slots, activate policy, choose storage locations, or
//     infer unattended lifecycle behavior.
// - Allows:
//   - Inputs: deterministic cursor states and conditional in-memory store.
//   - Outputs: exact durable/conflict/failure evidence.
//   - Side effects: test-local store mutation only.
// - Split-When:
//   - Trigger-slot transition ownership gains independent regression lifecycle.
// - Merge-When:
//   - Parent CAS module no longer requires private regression access.
// - Summary:
//   - Proves canonical cursor CAS conflicts and commits fail closed.
// - Description:
//   - Durability failure retains the candidate as the committed cursor.
// - Usage:
//   - Compiled only under Rust test configuration.
// - Defaults:
//   - Missing expected state initializes only missing durable state.
//

//! Regression coverage for conditional durable trigger-cursor publication.

use std::num::NonZeroU64;

use super::*;
use crate::blob_store::{
    NativeContinuationBlobConditionalPublication,
    NativeContinuationBlobConditionalPublicationResult,
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
    durability_calls: usize,
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

impl ConditionalBlobStore for MemoryStore {
    fn compare_and_swap(
        &mut self,
        expected: Option<&[u8]>,
        replacement: &[u8],
        _maximum_bytes: NonZeroUsize,
    ) -> NativeContinuationBlobConditionalPublicationResult<Self::Error> {
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
        self.durability_calls = self.durability_calls.saturating_add(1);
        if self.fail_durability {
            Err(DurabilityError::Failed)
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

fn encode(value: Cursor) -> Vec<u8> {
    codec::encode_native_executable_cache_limits_trigger_cadence(value)
}

#[test]
fn durability_failure_keeps_committed_candidate() -> Result<(), String> {
    let candidate = cursor(5, 3)?;
    let mut store = MemoryStore {
        fail_durability: true,
        ..MemoryStore::default()
    };
    let outcome = compare_and_swap_cache_trigger_cadence_durably(
        &mut store,
        None,
        candidate,
        positive(32)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    if outcome
        == (NativeExecutableCacheLimitsTriggerCadenceCas::Published {
            bytes: 32,
            current: candidate,
            durability_error: DurabilityError::Failed,
            previous: None,
        })
        && store.bytes == Some(encode(candidate))
        && store.durability_calls == 1
    {
        Ok(())
    } else {
        Err(String::from("cursor CAS durability evidence drifted"))
    }
}

#[test]
fn exact_expected_cursor_updates_durably() -> Result<(), String> {
    let expected = cursor(5, 3)?;
    let candidate = cursor(8, 3)?;
    let mut store = MemoryStore {
        bytes: Some(encode(expected)),
        ..MemoryStore::default()
    };
    let outcome = compare_and_swap_cache_trigger_cadence_durably(
        &mut store,
        Some(expected),
        candidate,
        positive(32)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    if outcome
        == (NativeExecutableCacheLimitsTriggerCadenceCas::Durable {
            bytes: 32,
            current: candidate,
            previous: Some(expected),
        })
        && store.bytes == Some(encode(candidate))
        && store.durability_calls == 1
    {
        Ok(())
    } else {
        Err(String::from("exact cursor CAS update drifted"))
    }
}

#[test]
fn malformed_conflict_fails_closed() -> Result<(), String> {
    let malformed = vec![0; 32];
    let mut store = MemoryStore {
        bytes: Some(malformed.clone()),
        ..MemoryStore::default()
    };
    let result = compare_and_swap_cache_trigger_cadence_durably(
        &mut store,
        None,
        cursor(5, 3)?,
        positive(32)?,
    );
    if result
        == Err(NativeExecutableCacheLimitsTriggerCadenceCasError::Codec(
            CursorCodecError::Magic,
        ))
        && store.bytes == Some(malformed)
        && store.durability_calls == 0
    {
        Ok(())
    } else {
        Err(String::from("malformed cursor conflict was admitted"))
    }
}

#[test]
fn missing_state_initializes_durably() -> Result<(), String> {
    let candidate = cursor(2, 4)?;
    let mut store = MemoryStore::default();
    let outcome = compare_and_swap_cache_trigger_cadence_durably(
        &mut store,
        None,
        candidate,
        positive(32)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    if outcome
        == (NativeExecutableCacheLimitsTriggerCadenceCas::Durable {
            bytes: 32,
            current: candidate,
            previous: None,
        })
        && store.bytes == Some(encode(candidate))
        && store.durability_calls == 1
    {
        Ok(())
    } else {
        Err(String::from("missing cursor CAS initialization drifted"))
    }
}

#[test]
fn stale_expected_returns_exact_current_cursor() -> Result<(), String> {
    let expected = cursor(2, 4)?;
    let current = cursor(6, 4)?;
    let candidate = cursor(10, 4)?;
    let current_bytes = encode(current);
    let mut store = MemoryStore {
        bytes: Some(current_bytes.clone()),
        ..MemoryStore::default()
    };
    let outcome = compare_and_swap_cache_trigger_cadence_durably(
        &mut store,
        Some(expected),
        candidate,
        positive(32)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    if outcome
        == (NativeExecutableCacheLimitsTriggerCadenceCas::Conflict {
            candidate,
            current: Some(current),
            expected: Some(expected),
        })
        && store.bytes == Some(current_bytes)
        && store.durability_calls == 0
    {
        Ok(())
    } else {
        Err(String::from("stale cursor CAS conflict evidence drifted"))
    }
}

#[test]
fn store_failure_is_prepublication_error() -> Result<(), String> {
    let mut store = MemoryStore {
        fail_store: true,
        ..MemoryStore::default()
    };
    let result = compare_and_swap_cache_trigger_cadence_durably(
        &mut store,
        None,
        cursor(3, 6)?,
        positive(32)?,
    );
    if matches!(
        result,
        Err(NativeExecutableCacheLimitsTriggerCadenceCasError::Blob(
            NativeContinuationBlobPersistenceError::Store(StoreError::Failed),
        ))
    ) && store.bytes.is_none()
        && store.durability_calls == 0
    {
        Ok(())
    } else {
        Err(String::from("cursor CAS store failure drifted"))
    }
}
