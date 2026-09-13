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
//   - One cache acquisition, exact lease binding, and resident fused retry.
// - Must-Not:
//   - Rebase semantics, return leases, hide cache effects, or retry cleanup.
// - Allows:
//   - Inputs: admitted retry, fused lease cache, memory adapter, and runner.
//   - Outputs: resident execution or exact acquisition/binding/execution owner.
//   - Side effects: ordinary per-region cache acquisition plus one native
//     retry.
// - Split-When:
//   - Multi-turn retry policy or lease-return orchestration gains ownership.
// - Merge-When:
//   - Product orchestration owns cache acquisition through semantic completion.
// - Summary:
//   - Executes one admitted fused retry through exact process-local lease
//     reuse.
// - Description:
//   - Acquisition failure restores retry ownership; later failures retain
//     leases.
// - Usage:
//   - Invoke after fused host routing admits exact retry authority.
// - Defaults:
//   - Completed cache effects remain visible; no implicit rollback occurs.
//

//! Cache acquisition and resident execution for one admitted fused retry.

use super::fused_lease_cache::DirectFusedNativeLeaseCache;
use super::fused_sequence_cache::{
    DirectFusedNativeSequenceCacheAcquireFailure,
    acquire_direct_fused_native_sequence,
};
use super::fused_sequence_leased_retry::{
    DirectFusedNativeLeasedRetry, DirectFusedNativeLeasedRetryAdmissionFailure,
    DirectFusedNativeLeasedRetryExecution,
    DirectFusedNativeLeasedRetryExecutionFailure,
};
use super::fused_sequence_retry::DirectFusedNativeRetry;
use super::platform::NativeExecutableMemoryAdapter;
use super::runner::DirectFusedNativeRunner;

/// Cache acquisition failure retaining retry and exact cache failure ownership.
#[derive(Debug)]
pub struct DirectFusedNativeCachedRetryAcquisitionFailure<MemoryError> {
    failure: Box<DirectFusedNativeSequenceCacheAcquireFailure<MemoryError>>,
    retry: DirectFusedNativeRetry,
}

/// Failure in one cache-acquired fused native retry attempt.
#[derive(Debug)]
pub enum DirectFusedNativeCachedRetryFailure<MemoryError, RunnerError> {
    /// Exact fused sequence cache acquisition failed before resident execution.
    Acquisition(
        Box<DirectFusedNativeCachedRetryAcquisitionFailure<MemoryError>>,
    ),
    /// Cache acquisition could not bind to the exact admitted retry plan.
    Binding(Box<DirectFusedNativeLeasedRetryAdmissionFailure>),
    /// Resident fused sequence execution failed while retaining every lease.
    Execution(Box<DirectFusedNativeLeasedRetryExecutionFailure<RunnerError>>),
}

/// Retry and exact cache-acquisition failure owners.
pub type DirectFusedNativeCachedRetryAcquisitionParts<MemoryError> = (
    DirectFusedNativeRetry,
    Box<DirectFusedNativeSequenceCacheAcquireFailure<MemoryError>>,
);

/// Result of one cache-aware fused native retry attempt.
pub type DirectFusedNativeCachedRetryResult<MemoryError, RunnerError> = Result<
    DirectFusedNativeLeasedRetryExecution,
    Box<DirectFusedNativeCachedRetryFailure<MemoryError, RunnerError>>,
>;

type CachedRetryAdapterResult<MemoryAdapter, Runner> =
    DirectFusedNativeCachedRetryResult<
        <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
        <Runner as DirectFusedNativeRunner>::Error,
    >;

impl<MemoryError> DirectFusedNativeCachedRetryAcquisitionFailure<MemoryError> {
    /// Returns the exact indexed cache acquisition failure.
    #[must_use]
    pub const fn failure(
        &self,
    ) -> &DirectFusedNativeSequenceCacheAcquireFailure<MemoryError> {
        &self.failure
    }

    /// Consumes this failure and restores retry plus cache failure ownership.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> DirectFusedNativeCachedRetryAcquisitionParts<MemoryError> {
        (self.retry, self.failure)
    }

    /// Returns the admitted retry retained before cache acquisition.
    #[must_use]
    pub const fn retry(&self) -> &DirectFusedNativeRetry {
        &self.retry
    }
}

impl<MemoryError, RunnerError>
    DirectFusedNativeCachedRetryFailure<MemoryError, RunnerError>
{
    /// Returns cache acquisition ownership, when loading/reuse failed.
    #[must_use]
    pub const fn acquisition(
        &self,
    ) -> Option<&DirectFusedNativeCachedRetryAcquisitionFailure<MemoryError>>
    {
        match self {
            Self::Acquisition(failure) => Some(failure),
            Self::Binding(_) | Self::Execution(_) => None,
        }
    }

    /// Consumes this failure and returns retry/lease binding ownership.
    #[must_use]
    pub fn into_binding(
        self,
    ) -> Option<Box<DirectFusedNativeLeasedRetryAdmissionFailure>> {
        match self {
            Self::Binding(failure) => Some(failure),
            Self::Acquisition(_) | Self::Execution(_) => None,
        }
    }

    /// Consumes this failure and returns resident execution plus lease
    /// ownership.
    #[must_use]
    pub fn into_execution(
        self,
    ) -> Option<Box<DirectFusedNativeLeasedRetryExecutionFailure<RunnerError>>>
    {
        match self {
            Self::Execution(failure) => Some(failure),
            Self::Acquisition(_) | Self::Binding(_) => None,
        }
    }
}

/// Acquires exact fused-region leases and executes one admitted retry.
///
/// Cache hits reuse existing resident mappings without memory-adapter work.
/// Insertions and later acquisition failures preserve the ordinary visible
/// FIFO/retirement effects of each completed per-region `ensure()`. The
/// returned execution owns every lease until the caller explicitly drops or
/// returns it.
///
/// # Errors
///
/// Returns [`DirectFusedNativeCachedRetryFailure`] with exact retry, cache,
/// binding, or resident execution ownership for every failed phase.
pub fn execute_cached_direct_fused_native_retry<MemoryAdapter, Runner>(
    cache: &mut DirectFusedNativeLeaseCache,
    memory_adapter: &mut MemoryAdapter,
    runner: &mut Runner,
    retry: DirectFusedNativeRetry,
) -> CachedRetryAdapterResult<MemoryAdapter, Runner>
where
    MemoryAdapter: NativeExecutableMemoryAdapter,
    Runner: DirectFusedNativeRunner,
{
    let acquisition = match acquire_direct_fused_native_sequence(
        cache,
        memory_adapter,
        retry.plan(),
    ) {
        Ok(acquisition) => acquisition,
        Err(failure) => {
            return Err(Box::new(
                DirectFusedNativeCachedRetryFailure::Acquisition(Box::new(
                    DirectFusedNativeCachedRetryAcquisitionFailure {
                        failure,
                        retry,
                    },
                )),
            ));
        },
    };
    let leased = DirectFusedNativeLeasedRetry::new(retry, acquisition)
        .map_err(|failure| {
            Box::new(DirectFusedNativeCachedRetryFailure::Binding(failure))
        })?;
    leased.execute(runner).map_err(|failure| {
        Box::new(DirectFusedNativeCachedRetryFailure::Execution(failure))
    })
}
