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
//   - Ordered acquisition of fused-region leases for one admitted sequence.
// - Must-Not:
//   - Hide cache eviction/retirement, execute code, or invent rollback policy.
// - Allows:
//   - Inputs: fused sequence plan, fused lease cache, and memory adapter.
//   - Outputs: admitted leased sequence or indexed acquisition evidence.
//   - Side effects: only explicit per-region cache `ensure()` operations.
// - Split-When:
//   - Transactional cache rollback or continuation scheduling gains policy.
// - Merge-When:
//   - One reviewed cache coordinator owns acquisition and leased execution.
// - Summary:
//   - Acquires exact region leases while preserving visible cache mutations.
// - Description:
//   - Failure returns every earlier lease and disposition without hidden undo.
// - Usage:
//   - Acquire once, execute the returned leased sequence, then return leases.
// - Defaults:
//   - Cache FIFO/retirement changes from completed ensures remain
//     authoritative.
//

//! Ordered fused-sequence acquisition through the existing lease cache.

use std::fmt::{Display, Formatter, Result as FormatResult};

use super::fused_lease_cache::{
    DirectFusedNativeLease, DirectFusedNativeLeaseCache,
    DirectFusedNativeLeaseCacheDisposition,
    DirectFusedNativeLeaseCacheLoadFailure,
};
use super::fused_sequence_lease::{
    DirectFusedNativeLeasedSequence,
    DirectFusedNativeLeasedSequenceAdmissionError,
};
use super::fused_sequence_plan::DirectFusedNativeSequencePlan;
use super::platform::NativeExecutableMemoryAdapter;

#[derive(Debug)]
enum DirectFusedNativeSequenceCacheFailureCause<E> {
    Admission(DirectFusedNativeLeasedSequenceAdmissionError),
    Cache(Box<DirectFusedNativeLeaseCacheLoadFailure<E>>),
}

/// Indexed cache-acquisition failure retaining every earlier region lease.
#[derive(Debug)]
pub struct DirectFusedNativeSequenceCacheAcquireFailure<E> {
    acquired_dispositions: Vec<DirectFusedNativeLeaseCacheDisposition>,
    cause: DirectFusedNativeSequenceCacheFailureCause<E>,
    index: usize,
    leases: Vec<DirectFusedNativeLease>,
}

/// Successful ordered fused-sequence cache acquisition.
#[derive(Debug)]
pub struct DirectFusedNativeSequenceCacheAcquisition {
    dispositions: Vec<DirectFusedNativeLeaseCacheDisposition>,
    sequence: DirectFusedNativeLeasedSequence,
}

/// Result of acquiring every exact fused-region lease in one admitted plan.
pub type DirectFusedNativeSequenceCacheAcquireResult<E> = Result<
    DirectFusedNativeSequenceCacheAcquisition,
    Box<DirectFusedNativeSequenceCacheAcquireFailure<E>>,
>;

impl<E> DirectFusedNativeSequenceCacheAcquireFailure<E> {
    /// Returns the number of exact leases acquired before failure.
    #[must_use]
    pub const fn acquired_count(&self) -> usize {
        self.leases.len()
    }

    /// Returns dispositions from successful acquisitions before failure.
    #[must_use]
    pub fn acquired_dispositions(
        &self,
    ) -> &[DirectFusedNativeLeaseCacheDisposition] {
        &self.acquired_dispositions
    }

    /// Returns impossible post-acquisition lease-topology rejection, if any.
    #[must_use]
    pub const fn admission_error(
        &self,
    ) -> Option<DirectFusedNativeLeasedSequenceAdmissionError> {
        match &self.cause {
            DirectFusedNativeSequenceCacheFailureCause::Admission(error) => {
                Some(*error)
            },
            DirectFusedNativeSequenceCacheFailureCause::Cache(_) => None,
        }
    }

    /// Returns the exact per-region cache failure, when acquisition failed.
    #[must_use]
    pub const fn cache_failure(
        &self,
    ) -> Option<&DirectFusedNativeLeaseCacheLoadFailure<E>> {
        match &self.cause {
            DirectFusedNativeSequenceCacheFailureCause::Cache(error) => {
                Some(error)
            },
            DirectFusedNativeSequenceCacheFailureCause::Admission(_) => None,
        }
    }

    /// Returns the zero-based fused region whose acquisition failed.
    #[must_use]
    pub const fn index(&self) -> usize {
        self.index
    }

    /// Consumes this failure and returns every earlier exact lease.
    #[must_use]
    pub fn into_leases(self) -> Vec<DirectFusedNativeLease> {
        self.leases
    }

    /// Returns every earlier exact lease retained by this failure.
    #[must_use]
    pub fn leases(&self) -> &[DirectFusedNativeLease] {
        &self.leases
    }
}

impl<E: Display> Display for DirectFusedNativeSequenceCacheAcquireFailure<E> {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "fused sequence cache acquisition failed at {}: ",
            self.index
        )?;
        match &self.cause {
            DirectFusedNativeSequenceCacheFailureCause::Admission(error) => {
                Display::fmt(error, f)
            },
            DirectFusedNativeSequenceCacheFailureCause::Cache(error) => {
                Display::fmt(error, f)
            },
        }
    }
}

impl DirectFusedNativeSequenceCacheAcquisition {
    /// Returns every exact per-region cache disposition in semantic order.
    #[must_use]
    pub fn dispositions(&self) -> &[DirectFusedNativeLeaseCacheDisposition] {
        &self.dispositions
    }

    /// Consumes this acquisition and returns the admitted leased sequence.
    #[must_use]
    pub fn into_sequence(self) -> DirectFusedNativeLeasedSequence {
        self.sequence
    }

    /// Returns the admitted lease-backed sequence.
    #[must_use]
    pub const fn sequence(&self) -> &DirectFusedNativeLeasedSequence {
        &self.sequence
    }
}

/// Acquires every exact region lease for one admitted fused sequence.
///
/// Each successful `ensure()` retains its ordinary cache effects. A later
/// failure therefore does not silently restore FIFO lookup or retired state;
/// instead it returns every earlier lease/disposition plus the exact failing
/// cache evidence. Complete success revalidates ordered lease identity before
/// publishing the leased sequence.
///
/// # Errors
///
/// Returns indexed cache or final lease-topology rejection with ownership.
pub fn acquire_direct_fused_native_sequence<Adapter>(
    cache: &mut DirectFusedNativeLeaseCache,
    adapter: &mut Adapter,
    plan: &DirectFusedNativeSequencePlan,
) -> DirectFusedNativeSequenceCacheAcquireResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let mut dispositions = Vec::with_capacity(plan.len());
    let mut leases = Vec::with_capacity(plan.len());
    for (index, artifact) in plan.artifacts().iter().enumerate() {
        let acquisition = match cache.ensure(adapter, artifact) {
            Ok(acquisition) => acquisition,
            Err(error) => {
                return Err(Box::new(
                    DirectFusedNativeSequenceCacheAcquireFailure {
                        acquired_dispositions: dispositions,
                        cause:
                            DirectFusedNativeSequenceCacheFailureCause::Cache(
                                error,
                            ),
                        index,
                        leases,
                    },
                ));
            },
        };
        dispositions.push(acquisition.disposition().clone());
        leases.push(acquisition.into_lease());
    }
    let sequence = DirectFusedNativeLeasedSequence::new(plan, leases).map_err(
        |failure| {
            Box::new(DirectFusedNativeSequenceCacheAcquireFailure {
                acquired_dispositions: dispositions.clone(),
                cause: DirectFusedNativeSequenceCacheFailureCause::Admission(
                    failure.error(),
                ),
                index: plan.len(),
                leases: (*failure).into_leases(),
            })
        },
    )?;
    Ok(DirectFusedNativeSequenceCacheAcquisition { dispositions, sequence })
}
