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
//   - Regression coverage for durable bootstrap of process-local cache-trigger
//     retry lifecycle cursor authority.
// - Must-Not:
//   - Execute activation, timing, scheduling, or background work.
// - Allows:
//   - Inputs: deterministic blob-store fixtures and explicit lifecycle state.
//   - Outputs: exact restored/missing/failure evidence and resulting cursor
//     authority.
//   - Side effects: test-local memory mutation only.
// - Split-When:
//   - Cross-process bootstrap gains independent regression scope.
// - Merge-When:
//   - Parent bootstrap no longer requires private fixture coverage.
// - Summary:
//   - Proves durable bootstrap installs only canonical cursor authority.
// - Description:
//   - Missing or failed restore clears stale process-local cursor authority.
// - Usage:
//   - Compiled only under Rust test configuration.
// - Defaults:
//   - Fresh test stores contain no cursor publication.
//

//! Regression coverage for cache-trigger retry lifecycle durable bootstrap.

use std::num::{NonZeroU64, NonZeroUsize};

use super::*;
use crate::{
    executable_cache_limits_retry_policy as retry_policy,
    executable_cache_limits_trigger_cadence as trigger,
};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum TestStoreError {
    Load,
}

#[derive(Debug, Default)]
struct MemoryStore {
    bytes: Option<Vec<u8>>,
    fail_load: bool,
    load_calls: usize,
    replace_calls: usize,
}

impl BlobStore for MemoryStore {
    type Error = TestStoreError;

    fn load(
        &mut self,
        _maximum_bytes: NonZeroUsize,
    ) -> Result<Option<Vec<u8>>, Self::Error> {
        self.load_calls = self.load_calls.saturating_add(1);
        if self.fail_load {
            Err(TestStoreError::Load)
        } else {
            Ok(self.bytes.clone())
        }
    }

    fn replace(&mut self, bytes: &[u8]) -> Result<(), Self::Error> {
        self.replace_calls = self.replace_calls.saturating_add(1);
        self.bytes = Some(bytes.to_vec());
        Ok(())
    }
}

fn cursor(
    due_value: u64,
    interval_value: u64,
) -> Result<trigger::NativeExecutableCacheLimitsTriggerCadence, String> {
    let due = NonZeroU64::new(due_value)
        .ok_or_else(|| String::from("test due must be positive"))?;
    let interval = NonZeroU64::new(interval_value)
        .ok_or_else(|| String::from("test interval must be positive"))?;
    Ok(trigger::NativeExecutableCacheLimitsTriggerCadence::new(
        due, interval,
    ))
}

fn lifecycle(
    expected: trigger::NativeExecutableCacheLimitsTriggerCadence,
) -> Result<Lifecycle, String> {
    Ok(Lifecycle::new_with_cursor(
        expected,
        positive(32)?,
        positive(3)?,
        retry_policy::NativeExecutableCacheLimitsRetryConflictPolicy::
            return_on_contention(),
    ))
}

fn positive(value: usize) -> Result<NonZeroUsize, String> {
    NonZeroUsize::new(value)
        .ok_or_else(|| String::from("test value must be positive"))
}

#[test]
fn restored_cursor_replaces_stale_lifecycle_authority() -> Result<(), String> {
    let stale = cursor(1, 2)?;
    let restored = cursor(5, 3)?;
    let mut store = MemoryStore::default();
    let write =
        persistence::persist_native_executable_cache_limits_trigger_cadence(
            &mut store,
            restored,
            positive(32)?,
        )
        .map_err(|error| format!("{error:?}"))?;
    let mut lifecycle = lifecycle(stale)?;
    let load = restore_native_executable_cache_limits_retry_lifecycle_cursor(
        &mut lifecycle,
        &mut store,
    )
    .map_err(|error| format!("{error:?}"))?;
    if matches!(
        load,
        Load::Restored { bytes: 32, cadence } if cadence == restored
    ) && write.bytes() == 32
        && lifecycle.expected_cursor() == Some(restored)
        && store.load_calls == 1
        && store.replace_calls == 1
    {
        Ok(())
    } else {
        Err(String::from(
            "durable bootstrap did not replace stale cursor authority",
        ))
    }
}

#[test]
fn missing_cursor_clears_stale_lifecycle_authority() -> Result<(), String> {
    let stale = cursor(1, 2)?;
    let mut store = MemoryStore::default();
    let mut lifecycle = lifecycle(stale)?;
    let load = restore_native_executable_cache_limits_retry_lifecycle_cursor(
        &mut lifecycle,
        &mut store,
    )
    .map_err(|error| format!("{error:?}"))?;
    if load == Load::Missing
        && lifecycle.expected_cursor().is_none()
        && store.load_calls == 1
        && store.replace_calls == 0
    {
        Ok(())
    } else {
        Err(String::from(
            "missing durable cursor retained stale lifecycle authority",
        ))
    }
}

#[test]
fn restore_failures_clear_stale_lifecycle_authority() -> Result<(), String> {
    let stale = cursor(1, 2)?;
    let mut failed_store = MemoryStore {
        fail_load: true,
        ..MemoryStore::default()
    };
    let mut failed_lifecycle = lifecycle(stale)?;
    let store_error =
        restore_native_executable_cache_limits_retry_lifecycle_cursor(
            &mut failed_lifecycle,
            &mut failed_store,
        );
    if store_error.is_ok()
        || failed_lifecycle.expected_cursor().is_some()
        || failed_store.load_calls != 1
    {
        return Err(String::from(
            "store restore failure retained stale lifecycle authority",
        ));
    }

    let mut malformed_store = MemoryStore {
        bytes: Some(vec![0; 32]),
        ..MemoryStore::default()
    };
    let mut malformed_lifecycle = lifecycle(stale)?;
    let codec_error =
        restore_native_executable_cache_limits_retry_lifecycle_cursor(
            &mut malformed_lifecycle,
            &mut malformed_store,
        );
    if codec_error.is_err()
        && malformed_lifecycle.expected_cursor().is_none()
        && malformed_store.load_calls == 1
    {
        Ok(())
    } else {
        Err(String::from(
            "codec restore failure retained stale lifecycle authority",
        ))
    }
}
