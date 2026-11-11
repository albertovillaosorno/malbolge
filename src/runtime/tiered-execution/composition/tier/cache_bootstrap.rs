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
//   - Bounded durable restoration of cache-trigger cursor authority into one
//     process-local retry lifecycle owner.
// - Must-Not:
//   - Choose storage locations, execute activation, read clocks, sleep, spawn
//     work, or invent missing cursor state.
// - Allows:
//   - Inputs: one retry lifecycle owner and one configured blob store.
//   - Outputs: exact persistence-load evidence or typed restore failure.
//   - Side effects: bounded store read plus fail-closed lifecycle cursor
//     update.
// - Split-When:
//   - Cross-process leadership or asynchronous bootstrap gains independent
//     authority.
// - Merge-When:
//   - One product scheduler owns durable bootstrap and activation lifecycle.
// - Summary:
//   - Restores exact durable cache-trigger cursor authority fail-closed.
// - Description:
//   - Existing process-local cursor authority is cleared before every restore;
//     only canonical restored evidence installs replacement authority.
// - Usage:
//   - Call before deriving retained-cursor activation requests after startup or
//     explicit durable resynchronization.
// - Defaults:
//   - Missing or failed durable restore leaves lifecycle cursor authority
//     absent.
//

//! Durable bootstrap for process-local cache-trigger retry lifecycle state.

use crate::blob_store::NativeContinuationBlobStore as BlobStore;
use crate::{
    executable_cache_limits_retry_lifecycle as lifecycle,
    executable_cache_limits_trigger_cadence_persistence as persistence,
};

type Lifecycle = lifecycle::NativeExecutableCacheLimitsRetryLifecycle;
type Load =
    persistence::NativeExecutableCacheLimitsTriggerCadencePersistenceLoad;
type RestoreError<StoreError> =
    persistence::NativeExecutableCacheLimitsTriggerCadencePersistenceError<
        StoreError,
    >;
type RestoreResult<Store> =
    Result<Load, RestoreError<<Store as BlobStore>::Error>>;

/// Restores durable cursor authority into one process-local retry lifecycle.
///
/// Existing lifecycle cursor authority is cleared before the bounded store
/// read. Missing state or any restore failure therefore cannot retain stale
/// authority.
///
/// # Errors
///
/// Returns exact store, byte-limit, or canonical-codec restore failure.
pub fn restore_native_executable_cache_limits_retry_lifecycle_cursor<Store>(
    lifecycle: &mut Lifecycle,
    store: &mut Store,
) -> RestoreResult<Store>
where
    Store: BlobStore,
{
    lifecycle.replace_expected_cursor(None);
    let load =
        persistence::restore_native_executable_cache_limits_trigger_cadence(
            store,
            lifecycle.maximum_bytes(),
        )?;
    if let Load::Restored { cadence, .. } = load {
        lifecycle.replace_expected_cursor(Some(cadence));
    }
    Ok(load)
}

#[cfg(test)]
#[path = "../../../../../tests/tiered/cache_retry_bootstrap.rs"]
mod tests;
