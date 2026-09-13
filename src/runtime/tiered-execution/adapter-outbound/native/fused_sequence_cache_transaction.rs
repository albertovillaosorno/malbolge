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
//   - Transactional cache acquisition for one admitted fused sequence plan.
// - Must-Not:
//   - Execute leases, schedule continuations, or weaken cache batch rollback.
// - Allows:
//   - Inputs: admitted fused plan, fused lease cache, and memory adapter.
//   - Outputs: leased sequence or exact batch/admission failure ownership.
//   - Side effects: delegated transactional cache load/publication/cleanup
//     only.
// - Split-When:
//   - Retry execution or asynchronous cache mutation gains policy.
// - Merge-When:
//   - Sequence cache acquisition becomes transaction-only.
// - Summary:
//   - Binds an atomic cache batch to exact fused sequence topology.
// - Description:
//   - Pre-publication cache failure leaves prior cache authority unchanged.
// - Usage:
//   - Prefer when whole-plan cache publication must avoid partial misses.
// - Defaults:
//   - Post-publication cleanup failure remains explicit committed ownership.
//

//! Transactional fused-sequence cache acquisition.

use std::fmt::{Display, Formatter, Result as FormatResult};

use super::fused_lease_cache::{
    DirectFusedNativeLeaseCache, DirectFusedNativeLeaseCacheBatchFailure,
    DirectFusedNativeLeaseCacheDisposition,
};
use super::fused_sequence_cache::DirectFusedNativeSequenceCacheAcquisition;
use super::fused_sequence_lease::{
    DirectFusedNativeLeasedSequence,
    DirectFusedNativeLeasedSequenceAdmissionError,
    DirectFusedNativeLeasedSequenceAdmissionFailure,
};
use super::fused_sequence_plan::DirectFusedNativeSequencePlan;
use super::platform::NativeExecutableMemoryAdapter;

/// Cache dispositions and exact leases retained after topology rejection.
pub type DirectFusedNativeSequenceCacheAdmissionFailureParts = (
    Vec<DirectFusedNativeLeaseCacheDisposition>,
    DirectFusedNativeLeasedSequenceAdmissionFailure,
);

#[derive(Debug)]
enum TransactionFailureCause<E> {
    Admission(Box<DirectFusedNativeLeasedSequenceAdmissionFailure>),
    Batch(Box<DirectFusedNativeLeaseCacheBatchFailure<E>>),
}

/// Transactional sequence-cache rejection with exact retained ownership.
#[derive(Debug)]
pub struct DirectFusedNativeSequenceCacheTransactionFailure<E> {
    cause: TransactionFailureCause<E>,
    dispositions: Vec<DirectFusedNativeLeaseCacheDisposition>,
}

/// Result of transactionally acquiring one admitted fused sequence.
pub type DirectFusedNativeSequenceCacheTransactionResult<E> = Result<
    DirectFusedNativeSequenceCacheAcquisition,
    Box<DirectFusedNativeSequenceCacheTransactionFailure<E>>,
>;

impl<E> DirectFusedNativeSequenceCacheTransactionFailure<E> {
    /// Returns post-batch lease-topology rejection, when present.
    #[must_use]
    pub const fn admission_error(
        &self,
    ) -> Option<DirectFusedNativeLeasedSequenceAdmissionError> {
        match &self.cause {
            TransactionFailureCause::Admission(failure) => {
                Some(failure.error())
            },
            TransactionFailureCause::Batch(_) => None,
        }
    }

    /// Returns transactional cache-batch failure, when present.
    #[must_use]
    pub const fn batch_failure(
        &self,
    ) -> Option<&DirectFusedNativeLeaseCacheBatchFailure<E>> {
        match &self.cause {
            TransactionFailureCause::Admission(_) => None,
            TransactionFailureCause::Batch(failure) => Some(failure),
        }
    }

    /// Returns exact dispositions retained before topology rejection.
    #[must_use]
    pub fn dispositions(&self) -> &[DirectFusedNativeLeaseCacheDisposition] {
        &self.dispositions
    }

    /// Consumes topology rejection into dispositions plus exact leases.
    #[must_use]
    pub fn into_admission_parts(
        self,
    ) -> Option<DirectFusedNativeSequenceCacheAdmissionFailureParts> {
        match self.cause {
            TransactionFailureCause::Admission(failure) => {
                Some((self.dispositions, *failure))
            },
            TransactionFailureCause::Batch(_) => None,
        }
    }

    /// Consumes this failure into the transactional cache-batch owner.
    #[must_use]
    pub fn into_batch_failure(
        self,
    ) -> Option<DirectFusedNativeLeaseCacheBatchFailure<E>> {
        match self.cause {
            TransactionFailureCause::Admission(_) => None,
            TransactionFailureCause::Batch(failure) => Some(*failure),
        }
    }
}

impl<E: Display> Display
    for DirectFusedNativeSequenceCacheTransactionFailure<E>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str("transactional fused sequence cache acquisition failed: ")?;
        match &self.cause {
            TransactionFailureCause::Admission(failure) => {
                Display::fmt(&failure.error(), f)
            },
            TransactionFailureCause::Batch(failure) => Display::fmt(failure, f),
        }
    }
}

/// Acquires one admitted fused sequence without publishing partial misses.
///
/// Every cache miss is loaded and capacity-preflighted before active/retired
/// authority changes. Batch failure before publication leaves the prior cache
/// queues and usage unchanged; staged cleanup failure remains retryable. A
/// post-publication FIFO cleanup failure retains the committed batch through
/// the returned batch failure.
///
/// # Errors
///
/// Returns exact transactional batch or final lease-topology ownership.
pub fn acquire_direct_fused_native_sequence_transactionally<Adapter>(
    cache: &mut DirectFusedNativeLeaseCache,
    adapter: &mut Adapter,
    plan: &DirectFusedNativeSequencePlan,
) -> DirectFusedNativeSequenceCacheTransactionResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let batch = cache
        .acquire_batch_transactionally(adapter, plan.artifacts())
        .map_err(|failure| {
            Box::new(DirectFusedNativeSequenceCacheTransactionFailure {
                cause: TransactionFailureCause::Batch(failure),
                dispositions: Vec::new(),
            })
        })?;
    let (dispositions, leases) = batch.into_parts();
    let sequence = DirectFusedNativeLeasedSequence::new(plan, leases).map_err(
        |failure| {
            Box::new(DirectFusedNativeSequenceCacheTransactionFailure {
                cause: TransactionFailureCause::Admission(failure),
                dispositions: dispositions.clone(),
            })
        },
    )?;
    Ok(DirectFusedNativeSequenceCacheAcquisition { dispositions, sequence })
}
