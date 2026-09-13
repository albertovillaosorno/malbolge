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
//   - Explicit fused retry lease return after successful semantic rebase.
// - Must-Not:
//   - Rebase semantics, acquire residents, schedule retries, or hide cleanup.
// - Allows:
//   - Inputs: rebased leased retry result, fused lease cache, memory adapter.
//   - Outputs: semantic/native evidence plus explicit reconciliation evidence.
//   - Side effects: drops supplied leases and reconciles retired cache owners.
// - Split-When:
//   - Multi-turn retry policy or transactional cache rollback gains ownership.
// - Merge-When:
//   - Product orchestration owns retry execution through cache lifecycle end.
// - Summary:
//   - Returns rebased fused retry leases without consuming semantic evidence.
// - Description:
//   - Active lookup remains; retired mappings may release with keyed retries.
// - Usage:
//   - Invoke after resident retry execution rebases successfully.
// - Defaults:
//   - Cleanup failure never overwrites semantic or native failure evidence.
//

//! Explicit cache lease return after fused native retry semantic rebase.

use super::fused_lease_cache::{
    DirectFusedNativeLeaseCache, DirectFusedNativeLeaseCacheDisposition,
    DirectFusedNativeLeaseCacheReleaseFailure,
    DirectFusedNativeLeaseCacheReleaseSummary,
};
use super::fused_sequence_execution::DirectFusedNativeSequenceExecutionFailure;
use super::fused_sequence_leased_retry::{
    DirectFusedNativeLeasedRetryDisposition,
    DirectFusedNativeLeasedRetryFailureDisposition,
};
use super::fused_sequence_retry_rebase::DirectFusedNativeRetryDisposition;
use super::platform::NativeExecutableMemoryAdapter;

/// Successful semantic rebase after every external retry lease was returned.
#[derive(Debug)]
pub struct DirectFusedNativeRetryLeaseReturn {
    cache_dispositions: Vec<DirectFusedNativeLeaseCacheDisposition>,
    disposition: DirectFusedNativeRetryDisposition,
    reconciliation: DirectFusedNativeLeaseCacheReleaseSummary,
}

/// Cleanup failure after successful semantic rebase and lease consumption.
#[derive(Debug)]
pub struct DirectFusedNativeRetryLeaseReturnFailure<MemoryError> {
    cache_dispositions: Vec<DirectFusedNativeLeaseCacheDisposition>,
    disposition: DirectFusedNativeRetryDisposition,
    reconciliation: Box<DirectFusedNativeLeaseCacheReleaseFailure<MemoryError>>,
}

/// Failed native execution after semantic rebase and explicit lease return.
#[derive(Debug)]
pub struct DirectFusedNativeRetryFailureLeaseReturn<RunnerError> {
    cache_dispositions: Vec<DirectFusedNativeLeaseCacheDisposition>,
    disposition: DirectFusedNativeRetryDisposition,
    failure: Box<DirectFusedNativeSequenceExecutionFailure<RunnerError>>,
    reconciliation: DirectFusedNativeLeaseCacheReleaseSummary,
}

/// Cleanup failure while returning a semantically rebased failed retry.
#[derive(Debug)]
pub struct DirectFusedNativeRetryFailureLeaseReturnFailure<
    MemoryError,
    RunnerError,
> {
    cache_dispositions: Vec<DirectFusedNativeLeaseCacheDisposition>,
    disposition: DirectFusedNativeRetryDisposition,
    failure: Box<DirectFusedNativeSequenceExecutionFailure<RunnerError>>,
    reconciliation: Box<DirectFusedNativeLeaseCacheReleaseFailure<MemoryError>>,
}

/// Result of explicitly returning leases after successful resident rebase.
pub type DirectFusedNativeRetryLeaseReturnResult<MemoryError> = Result<
    DirectFusedNativeRetryLeaseReturn,
    Box<DirectFusedNativeRetryLeaseReturnFailure<MemoryError>>,
>;

/// Semantic, cache, and keyed cleanup owners after failed lease return.
pub type DirectFusedNativeRetryLeaseReturnFailureParts<MemoryError> = (
    DirectFusedNativeRetryDisposition,
    Vec<DirectFusedNativeLeaseCacheDisposition>,
    Box<DirectFusedNativeLeaseCacheReleaseFailure<MemoryError>>,
);

/// Result of returning leases after failed resident execution was rebased.
pub type DirectFusedNativeRetryFailureLeaseReturnResult<
    MemoryError,
    RunnerError,
> = Result<
    DirectFusedNativeRetryFailureLeaseReturn<RunnerError>,
    Box<
        DirectFusedNativeRetryFailureLeaseReturnFailure<
            MemoryError,
            RunnerError,
        >,
    >,
>;

impl DirectFusedNativeRetryLeaseReturn {
    /// Returns exact cache insertion/hit evidence retained from acquisition.
    #[must_use]
    pub fn cache_dispositions(
        &self,
    ) -> &[DirectFusedNativeLeaseCacheDisposition] {
        &self.cache_dispositions
    }

    /// Returns the exact mixed-tier semantic disposition.
    #[must_use]
    pub const fn disposition(&self) -> &DirectFusedNativeRetryDisposition {
        &self.disposition
    }

    /// Returns explicit retired-resident reconciliation evidence.
    #[must_use]
    pub const fn reconciliation(
        &self,
    ) -> &DirectFusedNativeLeaseCacheReleaseSummary {
        &self.reconciliation
    }
}

impl<MemoryError> DirectFusedNativeRetryLeaseReturnFailure<MemoryError> {
    /// Returns exact cache insertion/hit evidence retained from acquisition.
    #[must_use]
    pub fn cache_dispositions(
        &self,
    ) -> &[DirectFusedNativeLeaseCacheDisposition] {
        &self.cache_dispositions
    }

    /// Returns the exact mixed-tier semantic disposition.
    #[must_use]
    pub const fn disposition(&self) -> &DirectFusedNativeRetryDisposition {
        &self.disposition
    }

    /// Consumes this failure into semantic, cache, and cleanup owners.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> DirectFusedNativeRetryLeaseReturnFailureParts<MemoryError> {
        (
            self.disposition,
            self.cache_dispositions,
            self.reconciliation,
        )
    }

    /// Returns exact keyed cleanup ownership transferred outside cache
    /// authority.
    #[must_use]
    pub const fn reconciliation(
        &self,
    ) -> &DirectFusedNativeLeaseCacheReleaseFailure<MemoryError> {
        &self.reconciliation
    }
}

impl<RunnerError> DirectFusedNativeRetryFailureLeaseReturn<RunnerError> {
    /// Returns exact cache insertion/hit evidence retained from acquisition.
    #[must_use]
    pub fn cache_dispositions(
        &self,
    ) -> &[DirectFusedNativeLeaseCacheDisposition] {
        &self.cache_dispositions
    }

    /// Returns the exact mixed-tier semantic disposition.
    #[must_use]
    pub const fn disposition(&self) -> &DirectFusedNativeRetryDisposition {
        &self.disposition
    }

    /// Returns native runner/completion failure ownership retained separately.
    #[must_use]
    pub const fn failure(
        &self,
    ) -> &DirectFusedNativeSequenceExecutionFailure<RunnerError> {
        &self.failure
    }

    /// Returns explicit retired-resident reconciliation evidence.
    #[must_use]
    pub const fn reconciliation(
        &self,
    ) -> &DirectFusedNativeLeaseCacheReleaseSummary {
        &self.reconciliation
    }
}

impl<MemoryError, RunnerError>
    DirectFusedNativeRetryFailureLeaseReturnFailure<MemoryError, RunnerError>
{
    /// Returns exact cache insertion/hit evidence retained from acquisition.
    #[must_use]
    pub fn cache_dispositions(
        &self,
    ) -> &[DirectFusedNativeLeaseCacheDisposition] {
        &self.cache_dispositions
    }

    /// Returns the exact mixed-tier semantic disposition.
    #[must_use]
    pub const fn disposition(&self) -> &DirectFusedNativeRetryDisposition {
        &self.disposition
    }

    /// Returns native runner/completion failure ownership retained separately.
    #[must_use]
    pub const fn failure(
        &self,
    ) -> &DirectFusedNativeSequenceExecutionFailure<RunnerError> {
        &self.failure
    }

    /// Returns exact keyed cleanup ownership transferred outside cache
    /// authority.
    #[must_use]
    pub const fn reconciliation(
        &self,
    ) -> &DirectFusedNativeLeaseCacheReleaseFailure<MemoryError> {
        &self.reconciliation
    }
}

/// Returns all leases from a successfully rebased resident retry.
///
/// # Errors
///
/// Returns semantic/cache evidence beside exact keyed cleanup retry ownership.
pub fn return_direct_fused_native_retry_leases<Adapter>(
    cache: &mut DirectFusedNativeLeaseCache,
    adapter: &mut Adapter,
    rebased: DirectFusedNativeLeasedRetryDisposition,
) -> DirectFusedNativeRetryLeaseReturnResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let (disposition, cache_dispositions, sequence) = rebased.into_parts();
    match cache.return_leases(adapter, sequence.into_leases()) {
        Ok(reconciliation) => Ok(DirectFusedNativeRetryLeaseReturn {
            cache_dispositions,
            disposition,
            reconciliation,
        }),
        Err(reconciliation) => {
            Err(Box::new(DirectFusedNativeRetryLeaseReturnFailure {
                cache_dispositions,
                disposition,
                reconciliation,
            }))
        },
    }
}

/// Returns all leases after failed resident execution was semantically rebased.
///
/// # Errors
///
/// Returns semantic/native/cache evidence beside exact keyed cleanup ownership.
pub fn return_direct_fused_native_retry_failure_leases<Adapter, RunnerError>(
    cache: &mut DirectFusedNativeLeaseCache,
    adapter: &mut Adapter,
    rebased: DirectFusedNativeLeasedRetryFailureDisposition<RunnerError>,
) -> DirectFusedNativeRetryFailureLeaseReturnResult<Adapter::Error, RunnerError>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let (disposition, failure, cache_dispositions, sequence) =
        rebased.into_parts();
    match cache.return_leases(adapter, sequence.into_leases()) {
        Ok(reconciliation) => Ok(DirectFusedNativeRetryFailureLeaseReturn {
            cache_dispositions,
            disposition,
            failure,
            reconciliation,
        }),
        Err(reconciliation) => {
            Err(Box::new(DirectFusedNativeRetryFailureLeaseReturnFailure {
                cache_dispositions,
                disposition,
                failure,
                reconciliation,
            }))
        },
    }
}
