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
//   - Transactional resident-limit changes for fused native leases.
// - Must-Not:
//   - Reconcile prior retired entries, refresh hits, or reclaim live leases.
// - Allows:
//   - Inputs: fused native lease cache owner, adapter, and requested limits.
//   - Outputs: exact evicted/retired keys or blocker/release ownership.
//   - Side effects: FIFO release or retirement required by one shrink request.
// - Split-When:
//   - Limit policy or asynchronous lease waiting gains independent ownership.
// - Merge-When:
//   - Admission and reconfiguration become one fused native transaction.
// - Summary:
//   - Shrinks active fused native authority while preserving leased weight.
// - Description:
//   - Prior limits remain published until every required transition succeeds.
// - Usage:
//   - Called by `DirectFusedNativeLeaseCache::reconfigure_limits`.
// - Defaults:
//   - Existing retired entries are never reconciled implicitly.
//

//! Transactional weighted-limit changes for fused native residents.

use super::{
    CacheVictimOutcome, DirectFusedNativeLeaseCache,
    DirectFusedNativeLeaseCacheBlock,
    DirectFusedNativeLeaseCacheEntryReleaseFailure, Display, FormatResult,
    Formatter, NativeArtifactKey, NativeExecutableMemoryAdapter,
    NativeExecutableSequenceCacheLimits, process_victim,
};

#[derive(Debug, Eq, PartialEq)]
struct FusedReconfigurationContext {
    evicted_keys: Vec<NativeArtifactKey>,
    requested_limits: NativeExecutableSequenceCacheLimits,
    retained_limits: NativeExecutableSequenceCacheLimits,
    retired_keys: Vec<NativeArtifactKey>,
}

#[derive(Debug)]
enum FusedReconfigurationFailureCause<E> {
    Leases(DirectFusedNativeLeaseCacheBlock),
    Release(Box<DirectFusedNativeLeaseCacheEntryReleaseFailure<E>>),
}

/// Successful fused native resident-limit publication and FIFO removals.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DirectFusedNativeLeaseCacheReconfiguration {
    evicted_keys: Vec<NativeArtifactKey>,
    new_limits: NativeExecutableSequenceCacheLimits,
    previous_limits: NativeExecutableSequenceCacheLimits,
    retired_keys: Vec<NativeArtifactKey>,
}

/// Failed publication with exact fused native blocker or cleanup ownership.
#[derive(Debug)]
pub struct DirectFusedNativeLeaseCacheReconfigurationFailure<E> {
    cause: FusedReconfigurationFailureCause<E>,
    evicted_keys: Vec<NativeArtifactKey>,
    requested_limits: NativeExecutableSequenceCacheLimits,
    retained_limits: NativeExecutableSequenceCacheLimits,
    retired_keys: Vec<NativeArtifactKey>,
}

/// Result of publishing new fused native limits after active FIFO processing.
pub type DirectFusedNativeLeaseCacheReconfigurationResult<E> = Result<
    DirectFusedNativeLeaseCacheReconfiguration,
    Box<DirectFusedNativeLeaseCacheReconfigurationFailure<E>>,
>;

type ReconfigurationEvictionResult<E> = Result<
    (Vec<NativeArtifactKey>, Vec<NativeArtifactKey>),
    Box<DirectFusedNativeLeaseCacheReconfigurationFailure<E>>,
>;

impl DirectFusedNativeLeaseCacheReconfiguration {
    /// Returns every active FIFO key removed before publication.
    #[must_use]
    pub fn evicted_keys(&self) -> &[NativeArtifactKey] {
        &self.evicted_keys
    }

    /// Returns `(previous, new)` resident capacity limits.
    #[must_use]
    pub const fn limit_transition(
        &self,
    ) -> (
        NativeExecutableSequenceCacheLimits,
        NativeExecutableSequenceCacheLimits,
    ) {
        (self.previous_limits, self.new_limits)
    }

    /// Returns removed keys still resident behind live leases.
    #[must_use]
    pub fn retired_keys(&self) -> &[NativeArtifactKey] {
        &self.retired_keys
    }
}

impl<E> DirectFusedNativeLeaseCacheReconfigurationFailure<E> {
    /// Returns exact resident lease blockage, when publication cannot fit.
    #[must_use]
    pub const fn block(&self) -> Option<&DirectFusedNativeLeaseCacheBlock> {
        match &self.cause {
            FusedReconfigurationFailureCause::Leases(block) => Some(block),
            FusedReconfigurationFailureCause::Release(_) => None,
        }
    }

    /// Returns every active FIFO key removed before publication failed.
    #[must_use]
    pub fn evicted_keys(&self) -> &[NativeArtifactKey] {
        &self.evicted_keys
    }

    /// Consumes this failure and returns exact keyed release ownership.
    #[must_use]
    pub fn into_release_failure(
        self,
    ) -> Option<DirectFusedNativeLeaseCacheEntryReleaseFailure<E>> {
        match self.cause {
            FusedReconfigurationFailureCause::Leases(_) => None,
            FusedReconfigurationFailureCause::Release(failure) => {
                Some(*failure)
            },
        }
    }

    /// Returns `(retained, requested)` limits for this failed publication.
    #[must_use]
    pub const fn limit_transition(
        &self,
    ) -> (
        NativeExecutableSequenceCacheLimits,
        NativeExecutableSequenceCacheLimits,
    ) {
        (self.retained_limits, self.requested_limits)
    }

    /// Returns exact keyed release ownership, when cleanup failed.
    #[must_use]
    pub const fn release_failure(
        &self,
    ) -> Option<&DirectFusedNativeLeaseCacheEntryReleaseFailure<E>> {
        match &self.cause {
            FusedReconfigurationFailureCause::Leases(_) => None,
            FusedReconfigurationFailureCause::Release(failure) => Some(failure),
        }
    }

    /// Returns removed keys still resident behind live leases.
    #[must_use]
    pub fn retired_keys(&self) -> &[NativeArtifactKey] {
        &self.retired_keys
    }
}

impl<E: Display> Display
    for DirectFusedNativeLeaseCacheReconfigurationFailure<E>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str("fused native lease cache reconfiguration failed: ")?;
        match &self.cause {
            FusedReconfigurationFailureCause::Leases(_) => {
                f.write_str("resident leases block requested limits")
            },
            FusedReconfigurationFailureCause::Release(failure) => {
                write!(f, "keyed release: {}", failure.failure())
            },
        }
    }
}

pub(super) const fn published(
    evicted_keys: Vec<NativeArtifactKey>,
    retired_keys: Vec<NativeArtifactKey>,
    new_limits: NativeExecutableSequenceCacheLimits,
    previous_limits: NativeExecutableSequenceCacheLimits,
) -> DirectFusedNativeLeaseCacheReconfiguration {
    DirectFusedNativeLeaseCacheReconfiguration {
        evicted_keys,
        new_limits,
        previous_limits,
        retired_keys,
    }
}

fn blocked_failure<E>(
    context: FusedReconfigurationContext,
    cache: &DirectFusedNativeLeaseCache,
) -> DirectFusedNativeLeaseCacheReconfigurationFailure<E> {
    let block = DirectFusedNativeLeaseCacheBlock {
        limits: context.requested_limits,
        retired_keys: cache.retired_keys().cloned().collect(),
        usage: cache.usage,
    };
    DirectFusedNativeLeaseCacheReconfigurationFailure {
        cause: FusedReconfigurationFailureCause::Leases(block),
        evicted_keys: context.evicted_keys,
        requested_limits: context.requested_limits,
        retained_limits: context.retained_limits,
        retired_keys: context.retired_keys,
    }
}

fn release_failure<E>(
    context: FusedReconfigurationContext,
    failure: DirectFusedNativeLeaseCacheEntryReleaseFailure<E>,
) -> DirectFusedNativeLeaseCacheReconfigurationFailure<E> {
    DirectFusedNativeLeaseCacheReconfigurationFailure {
        cause: FusedReconfigurationFailureCause::Release(Box::new(failure)),
        evicted_keys: context.evicted_keys,
        requested_limits: context.requested_limits,
        retained_limits: context.retained_limits,
        retired_keys: context.retired_keys,
    }
}

pub(super) fn evict_for_reconfiguration<Adapter>(
    cache: &mut DirectFusedNativeLeaseCache,
    adapter: &mut Adapter,
    requested_limits: NativeExecutableSequenceCacheLimits,
    retained_limits: NativeExecutableSequenceCacheLimits,
) -> ReconfigurationEvictionResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let mut evicted_keys = Vec::new();
    let mut retired_keys = Vec::new();
    while requested_limits.usage_exceeds(cache.usage) {
        let Some(victim) = cache.active.pop_front() else {
            return Err(Box::new(blocked_failure(
                FusedReconfigurationContext {
                    evicted_keys,
                    requested_limits,
                    retained_limits,
                    retired_keys,
                },
                cache,
            )));
        };
        let victim_key = victim.key.clone();
        evicted_keys.push(victim_key.clone());
        match process_victim(adapter, victim) {
            CacheVictimOutcome::Released(weight) => {
                cache.usage.remove(weight);
            },
            CacheVictimOutcome::ReleaseFailed { failure, weight } => {
                cache.usage.remove(weight);
                let keyed = DirectFusedNativeLeaseCacheEntryReleaseFailure {
                    failure,
                    key: victim_key,
                };
                return Err(Box::new(release_failure(
                    FusedReconfigurationContext {
                        evicted_keys,
                        requested_limits,
                        retained_limits,
                        retired_keys,
                    },
                    keyed,
                )));
            },
            CacheVictimOutcome::Retired(entry) => {
                retired_keys.push(entry.key.clone());
                cache.retired.push_back(*entry);
            },
        }
    }
    Ok((evicted_keys, retired_keys))
}
