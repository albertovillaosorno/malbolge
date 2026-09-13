// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Explicit selection between ordinary and transactional cached retry
//     acquisition for one admitted fused native retry.
// - Must-Not:
//   - Infer policy from cache state, change retry semantics, rebase, or return
//     leases.
// - Allows:
//   - Inputs: explicit acquisition mode, admitted retry, cache, adapter,
//     runner.
//   - Outputs: resident execution or mode-tagged exact failure ownership.
//   - Side effects: exactly those of the selected one-attempt coordinator.
// - Split-When:
//   - Bounded cycle policy or adaptive acquisition selection gains ownership.
// - Merge-When:
//   - Every cached retry call site uses one acquisition mode unconditionally.
// - Summary:
//   - Dispatches one cached fused retry through caller-selected cache
//     semantics.
// - Description:
//   - Selection is explicit and never changes ordinary or transactional rules.
// - Usage:
//   - Choose before execution when cache publication semantics are policy.
// - Defaults:
//   - No implicit default mode is inferred at this boundary.
//

//! Explicit cache-acquisition mode for one fused native retry attempt.

use super::fused_lease_cache::DirectFusedNativeLeaseCache;
use super::fused_sequence_cached_retry::{
    DirectFusedNativeCachedRetryFailure,
    execute_cached_direct_fused_native_retry,
};
use super::fused_sequence_leased_retry::DirectFusedNativeLeasedRetryExecution;
use super::fused_sequence_retry::DirectFusedNativeRetry;
use super::fused_sequence_transactional_cached_retry::{
    DirectFusedNativeTransactionalCachedRetryFailure,
    execute_transactional_cached_direct_fused_native_retry,
};
use super::platform::NativeExecutableMemoryAdapter;
use super::runner::DirectFusedNativeRunner;

/// Cache-publication semantics selected for one cached fused retry attempt.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectFusedNativeCachedRetryAcquisitionMode {
    /// Preserve completed per-region cache effects from ordinary acquisition.
    Ordinary,
    /// Stage and preflight the whole retry plan before cache publication.
    Transactional,
}

/// Explicit one-attempt cached retry selection plus admitted retry ownership.
#[derive(Debug, Eq, PartialEq)]
pub struct DirectFusedNativeSelectedCachedRetryRequest {
    mode: DirectFusedNativeCachedRetryAcquisitionMode,
    retry: DirectFusedNativeRetry,
}

/// Mode-tagged failure from one selected cached fused retry attempt.
#[derive(Debug)]
pub enum DirectFusedNativeSelectedCachedRetryFailure<MemoryError, RunnerError> {
    /// Ordinary acquisition/binding/execution failure ownership.
    Ordinary(
        Box<DirectFusedNativeCachedRetryFailure<MemoryError, RunnerError>>,
    ),
    /// Transactional acquisition/binding/execution failure ownership.
    Transactional(
        Box<
            DirectFusedNativeTransactionalCachedRetryFailure<
                MemoryError,
                RunnerError,
            >,
        >,
    ),
}

/// Result of one explicitly selected cached fused retry attempt.
pub type DirectFusedNativeSelectedCachedRetryResult<MemoryError, RunnerError> =
    Result<
        DirectFusedNativeLeasedRetryExecution,
        Box<
            DirectFusedNativeSelectedCachedRetryFailure<
                MemoryError,
                RunnerError,
            >,
        >,
    >;

type SelectedCachedRetryAdapterResult<MemoryAdapter, Runner> =
    DirectFusedNativeSelectedCachedRetryResult<
        <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
        <Runner as DirectFusedNativeRunner>::Error,
    >;

impl DirectFusedNativeSelectedCachedRetryRequest {
    /// Returns the selected cache-publication semantics.
    #[must_use]
    pub const fn mode(&self) -> DirectFusedNativeCachedRetryAcquisitionMode {
        self.mode
    }

    /// Constructs one explicit cache-acquisition selection for an admitted
    /// retry.
    #[must_use]
    pub const fn new(
        mode: DirectFusedNativeCachedRetryAcquisitionMode,
        retry: DirectFusedNativeRetry,
    ) -> Self {
        Self { mode, retry }
    }

    /// Returns the admitted retry retained by this request.
    #[must_use]
    pub const fn retry(&self) -> &DirectFusedNativeRetry {
        &self.retry
    }
}

/// Executes one admitted fused retry with explicit cache acquisition semantics.
///
/// This boundary performs no adaptive selection. `Ordinary` retains completed
/// per-region cache effects on later acquisition failure. `Transactional`
/// preserves whole-plan pre-publication rollback and committed-cleanup
/// ownership.
///
/// # Errors
///
/// Returns the selected coordinator's complete failure ownership tagged by
/// mode.
pub fn execute_selected_cached_direct_fused_native_retry<
    MemoryAdapter,
    Runner,
>(
    request: DirectFusedNativeSelectedCachedRetryRequest,
    cache: &mut DirectFusedNativeLeaseCache,
    memory_adapter: &mut MemoryAdapter,
    runner: &mut Runner,
) -> SelectedCachedRetryAdapterResult<MemoryAdapter, Runner>
where
    MemoryAdapter: NativeExecutableMemoryAdapter,
    Runner: DirectFusedNativeRunner,
{
    let DirectFusedNativeSelectedCachedRetryRequest { mode, retry } = request;
    match mode {
        DirectFusedNativeCachedRetryAcquisitionMode::Ordinary => {
            execute_cached_direct_fused_native_retry(
                cache,
                memory_adapter,
                runner,
                retry,
            )
            .map_err(|failure| {
                Box::new(DirectFusedNativeSelectedCachedRetryFailure::Ordinary(
                    failure,
                ))
            })
        },
        DirectFusedNativeCachedRetryAcquisitionMode::Transactional => {
            execute_transactional_cached_direct_fused_native_retry(
                cache,
                memory_adapter,
                runner,
                retry,
            )
            .map_err(|failure| {
                Box::new(
                    DirectFusedNativeSelectedCachedRetryFailure::Transactional(
                        failure,
                    ),
                )
            })
        },
    }
}
