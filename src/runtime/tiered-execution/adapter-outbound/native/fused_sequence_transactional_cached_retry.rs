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
//   - One transactional cache acquisition, exact retry binding, and execution.
// - Must-Not:
//   - Rebase semantics, return leases, retry cleanup, or hide committed cache
//     publication.
// - Allows:
//   - Inputs: admitted retry, fused lease cache, memory adapter, and runner.
//   - Outputs: resident execution or exact transaction/binding/execution owner.
//   - Side effects: transactional cache staging/publication plus one native
//     retry only after acquisition fully succeeds.
// - Split-When:
//   - Multi-turn transactional retry policy or lease return gains ownership.
// - Merge-When:
//   - Product orchestration requires transactional cache acquisition by
//     default.
// - Summary:
//   - Executes one fused retry only after transactional cache acquisition.
// - Description:
//   - Cache transaction failure restores retry ownership and prevents
//     execution.
// - Usage:
//   - Invoke after host routing when partial cache publication is unacceptable.
// - Defaults:
//   - Committed cleanup failure is terminal until its cleanup owner is handled.
//

//! Transactional cache acquisition and resident execution for one fused retry.

use super::fused_lease_cache::DirectFusedNativeLeaseCache;
use super::fused_sequence_cache_transaction::{
    DirectFusedNativeSequenceCacheTransactionFailure,
    acquire_direct_fused_native_sequence_transactionally as acquire_sequence,
};
use super::fused_sequence_leased_retry::{
    DirectFusedNativeLeasedRetry, DirectFusedNativeLeasedRetryAdmissionFailure,
    DirectFusedNativeLeasedRetryExecution,
    DirectFusedNativeLeasedRetryExecutionFailure,
};
use super::fused_sequence_retry::DirectFusedNativeRetry;
use super::platform::NativeExecutableMemoryAdapter;
use super::runner::DirectFusedNativeRunner;

/// Transaction failure retaining the admitted retry and all cache ownership.
#[derive(Debug)]
pub struct DirectFusedNativeTransactionalCachedRetryAcquisitionFailure<
    MemoryError,
> {
    failure: Box<DirectFusedNativeSequenceCacheTransactionFailure<MemoryError>>,
    retry: DirectFusedNativeRetry,
}

/// Failure in one transactionally acquired fused native retry attempt.
#[derive(Debug)]
pub enum DirectFusedNativeTransactionalCachedRetryFailure<
    MemoryError,
    RunnerError,
> {
    /// Transactional cache acquisition failed before resident execution.
    Acquisition(
        Box<
            DirectFusedNativeTransactionalCachedRetryAcquisitionFailure<
                MemoryError,
            >,
        >,
    ),
    /// Successful cache transaction could not bind to exact retry authority.
    Binding(Box<DirectFusedNativeLeasedRetryAdmissionFailure>),
    /// Resident execution failed while retaining every acquired lease.
    Execution(Box<DirectFusedNativeLeasedRetryExecutionFailure<RunnerError>>),
}

/// Retry plus exact transactional cache failure ownership.
pub type DirectFusedNativeTransactionalCachedRetryAcquisitionParts<
    MemoryError,
> = (
    DirectFusedNativeRetry,
    Box<DirectFusedNativeSequenceCacheTransactionFailure<MemoryError>>,
);

/// Result of one transactionally cache-aware fused native retry attempt.
pub type DirectFusedNativeTransactionalCachedRetryResult<
    MemoryError,
    RunnerError,
> = Result<
    DirectFusedNativeLeasedRetryExecution,
    Box<
        DirectFusedNativeTransactionalCachedRetryFailure<
            MemoryError,
            RunnerError,
        >,
    >,
>;

type TransactionalCachedRetryAdapterResult<MemoryAdapter, Runner> =
    DirectFusedNativeTransactionalCachedRetryResult<
        <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
        <Runner as DirectFusedNativeRunner>::Error,
    >;

impl<MemoryError>
    DirectFusedNativeTransactionalCachedRetryAcquisitionFailure<MemoryError>
{
    /// Returns the complete transactional cache failure.
    #[must_use]
    pub const fn failure(
        &self,
    ) -> &DirectFusedNativeSequenceCacheTransactionFailure<MemoryError> {
        &self.failure
    }

    /// Consumes this failure and restores retry plus cache ownership.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> DirectFusedNativeTransactionalCachedRetryAcquisitionParts<MemoryError>
    {
        (self.retry, self.failure)
    }

    /// Returns admitted retry ownership retained before cache acquisition.
    #[must_use]
    pub const fn retry(&self) -> &DirectFusedNativeRetry {
        &self.retry
    }
}

impl<MemoryError, RunnerError>
    DirectFusedNativeTransactionalCachedRetryFailure<MemoryError, RunnerError>
{
    /// Returns transactional cache acquisition ownership, when present.
    #[must_use]
    pub const fn acquisition(
        &self,
    ) -> Option<
        &DirectFusedNativeTransactionalCachedRetryAcquisitionFailure<
            MemoryError,
        >,
    > {
        match self {
            Self::Acquisition(failure) => Some(failure),
            Self::Binding(_) | Self::Execution(_) => None,
        }
    }

    /// Consumes this failure into retry/lease binding ownership.
    #[must_use]
    pub fn into_binding(
        self,
    ) -> Option<Box<DirectFusedNativeLeasedRetryAdmissionFailure>> {
        match self {
            Self::Binding(failure) => Some(failure),
            Self::Acquisition(_) | Self::Execution(_) => None,
        }
    }

    /// Consumes this failure into resident execution plus lease ownership.
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

const fn acquisition_failure<MemoryError>(
    failure: Box<DirectFusedNativeSequenceCacheTransactionFailure<MemoryError>>,
    retry: DirectFusedNativeRetry,
) -> DirectFusedNativeTransactionalCachedRetryAcquisitionFailure<MemoryError> {
    DirectFusedNativeTransactionalCachedRetryAcquisitionFailure {
        failure,
        retry,
    }
}

/// Transactionally acquires fused leases and executes one admitted retry.
///
/// Cache transaction failure is terminal for this attempt, including a
/// post-publication victim-cleanup failure. Native execution begins only after
/// the complete cache transaction succeeds and exact retry binding is admitted.
///
/// # Errors
///
/// Returns exact retry/cache, binding, or resident execution ownership.
pub fn execute_transactional_cached_direct_fused_native_retry<
    MemoryAdapter,
    Runner,
>(
    cache: &mut DirectFusedNativeLeaseCache,
    memory_adapter: &mut MemoryAdapter,
    runner: &mut Runner,
    retry: DirectFusedNativeRetry,
) -> TransactionalCachedRetryAdapterResult<MemoryAdapter, Runner>
where
    MemoryAdapter: NativeExecutableMemoryAdapter,
    Runner: DirectFusedNativeRunner,
{
    let acquisition =
        match acquire_sequence(cache, memory_adapter, retry.plan()) {
            Ok(acquisition) => acquisition,
            Err(failure) => {
                return Err(Box::new(
                DirectFusedNativeTransactionalCachedRetryFailure::Acquisition(
                    Box::new(acquisition_failure(failure, retry)),
                ),
            ));
            },
        };
    let leased = DirectFusedNativeLeasedRetry::new(retry, acquisition)
        .map_err(|failure| {
            Box::new(DirectFusedNativeTransactionalCachedRetryFailure::Binding(
                failure,
            ))
        })?;
    leased.execute(runner).map_err(|failure| {
        Box::new(DirectFusedNativeTransactionalCachedRetryFailure::Execution(
            failure,
        ))
    })
}
