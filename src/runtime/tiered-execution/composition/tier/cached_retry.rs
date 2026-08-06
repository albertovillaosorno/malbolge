// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - One exact lease-cache acquisition, binding, and loaded retry attempt.
// - Must-Not:
//   - Rebase semantics, return leases, retry cleanup, or loop automatically.
// - Allows:
//   - Inputs: admitted retry, lease cache, memory adapter, and native runner.
//   - Outputs: loaded execution or typed acquisition/binding/execution owner.
//   - Side effects: exact cache admission and one loaded sequence attempt.
// - Split-When:
//   - Cache policy or multi-turn lease reuse gains independent ownership.
// - Merge-When:
//   - Product orchestration owns acquisition through semantic completion.
// - Summary:
//   - Executes one admitted retry through exact process-local lease reuse.
// - Description:
//   - Acquisition failure restores retry ownership; later failures keep leases.
// - Usage:
//   - Invoke after retry planning/admission when a lease cache is available.
// - Defaults:
//   - Cache hit performs no executable-memory work and no lease is
//     auto-returned.
//

//! Cache acquisition and loaded execution for one admitted native retry.

use crate::execution_native::{
    NativeExecutableMemoryAdapter, NativeExecutableRunner,
    NativeExecutableSequenceLeaseCache,
    NativeExecutableSequenceLeaseCacheLoadFailure,
};
use crate::leased_retry::{
    NativeContinuationLeasedRetry,
    NativeContinuationLeasedRetryAdmissionFailure,
    NativeContinuationLeasedRetryExecution,
    NativeContinuationLeasedRetryExecutionFailure,
};
use crate::native_retry::NativeContinuationNativeRetry;

/// Cache acquisition failure retaining retry and exact load/cleanup ownership.
#[derive(Debug)]
pub struct NativeContinuationCachedRetryAcquisitionFailure<MemoryError> {
    failure: Box<NativeExecutableSequenceLeaseCacheLoadFailure<MemoryError>>,
    retry: NativeContinuationNativeRetry,
}

/// Failure in one cache-acquired loaded retry attempt.
#[derive(Debug)]
pub enum NativeContinuationCachedRetryFailure<MemoryError, RunnerError> {
    /// Exact lease-cache acquisition failed before loaded execution.
    Acquisition(
        Box<NativeContinuationCachedRetryAcquisitionFailure<MemoryError>>,
    ),
    /// Cache returned an acquisition whose key failed retry binding.
    Binding(Box<NativeContinuationLeasedRetryAdmissionFailure>),
    /// Loaded sequence execution failed while retaining the acquired lease.
    Execution(Box<NativeContinuationLeasedRetryExecutionFailure<RunnerError>>),
}

/// Admitted retry and exact cache acquisition failure owners.
pub type NativeContinuationCachedRetryAcquisitionParts<MemoryError> = (
    NativeContinuationNativeRetry,
    Box<NativeExecutableSequenceLeaseCacheLoadFailure<MemoryError>>,
);

/// Result of one cache-aware native retry attempt.
pub type NativeContinuationCachedRetryResult<MemoryError, RunnerError> = Result<
    NativeContinuationLeasedRetryExecution,
    Box<NativeContinuationCachedRetryFailure<MemoryError, RunnerError>>,
>;

type NativeContinuationCachedRetryAdapterResult<MemoryAdapter, Runner> =
    NativeContinuationCachedRetryResult<
        <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
        <Runner as NativeExecutableRunner>::Error,
    >;

impl<MemoryError> NativeContinuationCachedRetryAcquisitionFailure<MemoryError> {
    /// Returns exact lease-cache load, cleanup, eviction, or blockage evidence.
    #[must_use]
    pub const fn failure(
        &self,
    ) -> &NativeExecutableSequenceLeaseCacheLoadFailure<MemoryError> {
        &self.failure
    }

    /// Consumes this failure and restores retry plus cache failure ownership.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> NativeContinuationCachedRetryAcquisitionParts<MemoryError> {
        (self.retry, self.failure)
    }

    /// Returns the admitted retry retained before cache acquisition.
    #[must_use]
    pub const fn retry(&self) -> &NativeContinuationNativeRetry {
        &self.retry
    }
}

impl<MemoryError, RunnerError>
    NativeContinuationCachedRetryFailure<MemoryError, RunnerError>
{
    /// Returns cache acquisition ownership, when loading/reuse failed.
    #[must_use]
    pub const fn acquisition(
        &self,
    ) -> Option<&NativeContinuationCachedRetryAcquisitionFailure<MemoryError>>
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
    ) -> Option<Box<NativeContinuationLeasedRetryAdmissionFailure>> {
        match self {
            Self::Binding(failure) => Some(failure),
            Self::Acquisition(_) | Self::Execution(_) => None,
        }
    }

    /// Consumes this failure and returns loaded execution plus lease ownership.
    #[must_use]
    pub fn into_execution(
        self,
    ) -> Option<Box<NativeContinuationLeasedRetryExecutionFailure<RunnerError>>>
    {
        match self {
            Self::Execution(failure) => Some(failure),
            Self::Acquisition(_) | Self::Binding(_) => None,
        }
    }
}

/// Acquires an exact immutable lease and executes one admitted retry.
///
/// Cache hit reuses the existing resident sequence without executable-memory
/// operations. Inserted acquisitions retain exact eviction/retirement evidence.
/// The returned loaded execution owns the lease until the caller explicitly
/// returns or drops it.
///
/// # Errors
///
/// Returns [`NativeContinuationCachedRetryFailure`] with exact retry, cache,
/// binding, or loaded execution ownership for every failed phase.
pub fn execute_cached_native_retry<MemoryAdapter, Runner>(
    cache: &mut NativeExecutableSequenceLeaseCache,
    memory_adapter: &mut MemoryAdapter,
    runner: &mut Runner,
    retry: NativeContinuationNativeRetry,
) -> NativeContinuationCachedRetryAdapterResult<MemoryAdapter, Runner>
where
    MemoryAdapter: NativeExecutableMemoryAdapter,
    Runner: NativeExecutableRunner,
{
    let acquisition = match cache.ensure_plan(memory_adapter, retry.plan()) {
        Ok(acquisition) => acquisition,
        Err(failure) => {
            return Err(Box::new(
                NativeContinuationCachedRetryFailure::Acquisition(Box::new(
                    NativeContinuationCachedRetryAcquisitionFailure {
                        failure,
                        retry,
                    },
                )),
            ));
        },
    };
    let leased = NativeContinuationLeasedRetry::new(retry, acquisition)
        .map_err(|failure| {
            Box::new(NativeContinuationCachedRetryFailure::Binding(failure))
        })?;
    leased.execute(runner).map_err(|failure| {
        Box::new(NativeContinuationCachedRetryFailure::Execution(failure))
    })
}
