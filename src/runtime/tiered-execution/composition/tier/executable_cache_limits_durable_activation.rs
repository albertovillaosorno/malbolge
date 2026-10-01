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
//   - Durable cache-limit CAS followed by live cache-limit activation.
// - Must-Not:
//   - Retry CAS conflicts, retry cache cleanup, reconcile retired leases,
//     persist executable residency, or pretend committed policy rolled back.
// - Allows:
//   - Inputs: expected optional limits, candidate limits, bounded conditional
//     durable store, one live cache owner, and its executable-memory adapter.
//   - Outputs: conflict, committed/live reconfiguration, or committed/live
//     reconfiguration failure with exact evidence from both boundaries.
//   - Side effects: one durable cache-limit CAS and, only after committed
//     publication, one transactional live-cache limit reconfiguration.
// - Split-When:
//   - Cross-process policy reconciliation or retry scheduling gains authority.
// - Merge-When:
//   - One cache lifecycle owner subsumes publication, activation, and recovery.
// - Summary:
//   - Applies only committed durable cache-limit policy to live cache state.
// - Description:
//   - Post-publication durability failure still denotes a committed candidate;
//     later live-cache failure is explicit divergence evidence, not rollback.
// - Usage:
//   - Use when one caller owns both durable policy publication and live cache.
// - Defaults:
//   - CAS conflict leaves live cache state untouched.
//
//! Durable cache-limit publication followed by live transactional activation.

use std::num::NonZeroUsize;

use crate::blob_store::{
    NativeContinuationBlobStore as BlobStore,
    NativeContinuationConditionalBlobStore as ConditionalBlobStore,
    NativeContinuationDurableBlobStore as DurableBlobStore,
};
use crate::executable_cache_limits_cas::{
    NativeExecutableSequenceCacheLimitsCas,
    NativeExecutableSequenceCacheLimitsCasError,
    compare_and_swap_native_executable_sequence_cache_limits_durably,
};
use crate::execution_native::{
    NativeExecutableMemoryAdapter, NativeExecutableSequenceCache,
    NativeExecutableSequenceCacheLimits,
    NativeExecutableSequenceCacheReconfiguration,
    NativeExecutableSequenceCacheReconfigurationFailure,
    NativeExecutableSequenceLeaseCache,
    NativeExecutableSequenceLeaseCacheReconfiguration,
    NativeExecutableSequenceLeaseCacheReconfigurationFailure,
};

/// Caller-owned inputs for one durable cache-limit publication and activation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeExecutableSequenceCacheLimitsDurableActivationRequest {
    candidate: NativeExecutableSequenceCacheLimits,
    expected: Option<NativeExecutableSequenceCacheLimits>,
    maximum_bytes: NonZeroUsize,
}

/// Durable publication plus one live-cache activation attempt.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeExecutableSequenceCacheLimitsDurableActivation<
    Reconfiguration,
    ReconfigurationFailure,
    DurabilityError,
> {
    /// Durable state differed from expectation; live cache stayed untouched.
    Conflict {
        /// Exact durable conflict evidence.
        publication: NativeExecutableSequenceCacheLimitsCas<DurabilityError>,
    },
    /// Policy committed but the live cache could not publish the same limits.
    ReconfigurationFailed {
        /// Exact committed durable publication evidence.
        publication: NativeExecutableSequenceCacheLimitsCas<DurabilityError>,
        /// Exact retained live-cache failure ownership.
        failure: ReconfigurationFailure,
    },
    /// Policy committed and the live cache published the same limits.
    Reconfigured {
        /// Exact committed durable publication evidence.
        publication: NativeExecutableSequenceCacheLimitsCas<DurabilityError>,
        /// Exact live-cache transition evidence.
        reconfiguration: Reconfiguration,
    },
}

/// Durable activation specialized to the ordinary executable-sequence cache.
pub type NativeExecutableSequenceCacheLimitsDurableCacheActivation<
    DurabilityError,
    AdapterError,
> = NativeExecutableSequenceCacheLimitsDurableActivation<
    NativeExecutableSequenceCacheReconfiguration,
    Box<NativeExecutableSequenceCacheReconfigurationFailure<AdapterError>>,
    DurabilityError,
>;

/// Durable activation specialized to the shared executable lease cache.
pub type NativeExecutableSequenceLeaseCacheLimitsDurableActivation<
    DurabilityError,
    AdapterError,
> = NativeExecutableSequenceCacheLimitsDurableActivation<
    NativeExecutableSequenceLeaseCacheReconfiguration,
    Box<NativeExecutableSequenceLeaseCacheReconfigurationFailure<AdapterError>>,
    DurabilityError,
>;

/// Ordinary-cache durable activation result specialized to store and adapter.
pub type NativeExecutableSequenceCacheLimitsDurableStoreResult<Store, Adapter> =
    Result<
        NativeExecutableSequenceCacheLimitsDurableCacheActivation<
            <Store as DurableBlobStore>::DurabilityError,
            <Adapter as NativeExecutableMemoryAdapter>::Error,
        >,
        NativeExecutableSequenceCacheLimitsCasError<
            <Store as BlobStore>::Error,
        >,
    >;

/// Lease-cache durable activation result specialized to store and adapter.
pub type NativeExecutableSequenceLeaseCacheLimitsDurableStoreResult<
    Store,
    Adapter,
> = Result<
    NativeExecutableSequenceLeaseCacheLimitsDurableActivation<
        <Store as DurableBlobStore>::DurabilityError,
        <Adapter as NativeExecutableMemoryAdapter>::Error,
    >,
    NativeExecutableSequenceCacheLimitsCasError<<Store as BlobStore>::Error>,
>;

impl NativeExecutableSequenceCacheLimitsDurableActivationRequest {
    /// Binds one expected durable state, replacement, and bounded byte budget.
    #[must_use]
    pub const fn new(
        expected: Option<NativeExecutableSequenceCacheLimits>,
        candidate: NativeExecutableSequenceCacheLimits,
        maximum_bytes: NonZeroUsize,
    ) -> Self {
        Self {
            candidate,
            expected,
            maximum_bytes,
        }
    }
}

impl<Reconfiguration, ReconfigurationFailure, DurabilityError>
    NativeExecutableSequenceCacheLimitsDurableActivation<
        Reconfiguration,
        ReconfigurationFailure,
        DurabilityError,
    >
{
    /// Returns whether durable and live policy agree after this operation.
    #[must_use]
    pub const fn is_reconfigured(&self) -> bool {
        matches!(self, Self::Reconfigured { .. })
    }

    /// Returns exact durable publication evidence for every typed outcome.
    #[must_use]
    pub const fn publication(
        &self,
    ) -> &NativeExecutableSequenceCacheLimitsCas<DurabilityError> {
        match self {
            Self::Conflict { publication }
            | Self::ReconfigurationFailed { publication, .. }
            | Self::Reconfigured { publication, .. } => publication,
        }
    }
}

fn activate_committed_limits<
    Reconfiguration,
    ReconfigurationFailure,
    DurabilityError,
    Apply,
>(
    publication: NativeExecutableSequenceCacheLimitsCas<DurabilityError>,
    apply: Apply,
) -> NativeExecutableSequenceCacheLimitsDurableActivation<
    Reconfiguration,
    ReconfigurationFailure,
    DurabilityError,
>
where
    Apply: FnOnce(
        NativeExecutableSequenceCacheLimits,
    ) -> Result<Reconfiguration, ReconfigurationFailure>,
{
    let committed_limits = match &publication {
        NativeExecutableSequenceCacheLimitsCas::Conflict { .. } => {
            return NativeExecutableSequenceCacheLimitsDurableActivation::
                Conflict { publication };
        },
        NativeExecutableSequenceCacheLimitsCas::Durable { current, .. }
        | NativeExecutableSequenceCacheLimitsCas::Published {
            current, ..
        } => *current,
    };
    match apply(committed_limits) {
        Ok(reconfiguration) => {
            NativeExecutableSequenceCacheLimitsDurableActivation::Reconfigured {
                publication,
                reconfiguration,
            }
        },
        Err(failure) => NativeExecutableSequenceCacheLimitsDurableActivation::
            ReconfigurationFailed {
                publication,
                failure,
            },
    }
}

/// Publishes cache-limit policy durably, then applies committed limits to the
/// ordinary executable-sequence cache.
///
/// Conflict performs no live-cache work. Both fully durable publication and
/// committed publication followed by durability-confirmation failure attempt
/// the same live reconfiguration. A live failure remains a typed outcome
/// because durable state already committed and cannot be represented as rolled
/// back.
///
/// # Errors
///
/// Returns only cache-limit CAS failures that happen before a typed publication
/// outcome exists.
pub fn publish_and_apply_executable_sequence_cache_limits_durably<
    Store,
    Adapter,
>(
    store: &mut Store,
    cache: &mut NativeExecutableSequenceCache,
    adapter: &mut Adapter,
    request: NativeExecutableSequenceCacheLimitsDurableActivationRequest,
) -> NativeExecutableSequenceCacheLimitsDurableStoreResult<Store, Adapter>
where
    Store: ConditionalBlobStore + DurableBlobStore,
    Adapter: NativeExecutableMemoryAdapter,
{
    let publication =
        compare_and_swap_native_executable_sequence_cache_limits_durably(
            store,
            request.expected,
            request.candidate,
            request.maximum_bytes,
        )?;
    Ok(activate_committed_limits(publication, |limits| {
        cache.reconfigure_limits(adapter, limits)
    }))
}

/// Publishes cache-limit policy durably, then applies committed limits to the
/// executable lease cache.
///
/// Conflict performs no live-cache work. Both fully durable publication and
/// committed publication followed by durability-confirmation failure attempt
/// lease-aware reconfiguration. Existing retired entries are not reconciled
/// implicitly, and any resident blockage or cleanup failure remains owned by
/// the returned typed outcome.
///
/// # Errors
///
/// Returns only cache-limit CAS failures that happen before a typed publication
/// outcome exists.
pub fn publish_and_apply_executable_sequence_lease_cache_limits_durably<
    Store,
    Adapter,
>(
    store: &mut Store,
    cache: &mut NativeExecutableSequenceLeaseCache,
    adapter: &mut Adapter,
    request: NativeExecutableSequenceCacheLimitsDurableActivationRequest,
) -> NativeExecutableSequenceLeaseCacheLimitsDurableStoreResult<Store, Adapter>
where
    Store: ConditionalBlobStore + DurableBlobStore,
    Adapter: NativeExecutableMemoryAdapter,
{
    let publication =
        compare_and_swap_native_executable_sequence_cache_limits_durably(
            store,
            request.expected,
            request.candidate,
            request.maximum_bytes,
        )?;
    Ok(activate_committed_limits(publication, |limits| {
        cache.reconfigure_limits(adapter, limits)
    }))
}

#[cfg(test)]
#[path = "../../../../../tests/tiered/cache_limits_durable_activation.rs"]
mod tests;
