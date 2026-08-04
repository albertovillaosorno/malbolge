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
//   - Transactional resident-limit changes for the shared executable lease
//     cache.
// - Must-Not:
//   - Reconcile prior retired entries, refresh hits, or reclaim live leases.
// - Allows:
//   - Inputs: lease cache owner, adapter, and explicit requested limits.
//   - Outputs: exact evicted/retired keys or blocker/release ownership.
//   - Side effects: FIFO release or retirement required by one shrink request.
// - Split-When:
//   - Limit policy or asynchronous lease waiting gains independent ownership.
// - Merge-When:
//   - Admission and reconfiguration become one resident transaction.
// - Summary:
//   - Shrinks active authority while preserving exact leased resident weight.
// - Description:
//   - Prior limits remain published until every required transition succeeds.
// - Usage:
//   - Called by `NativeExecutableSequenceLeaseCache::reconfigure_limits`.
// - Defaults:
//   - Existing retired entries are never reconciled implicitly.
//

//! Transactional resident-limit changes for shared executable leases.

use super::*;

#[derive(Debug, Eq, PartialEq)]
struct LeaseCacheReconfigurationContext {
    evicted_keys: Vec<NativeExecutableSequenceKey>,
    requested_limits: NativeExecutableSequenceCacheLimits,
    retained_limits: NativeExecutableSequenceCacheLimits,
    retired_keys: Vec<NativeExecutableSequenceKey>,
}

#[derive(Debug, Eq, PartialEq)]
enum LeaseCacheReconfigurationFailureCause<E> {
    Leases(NativeExecutableSequenceLeaseCacheBlock),
    Release(NativeExecutableSequenceLeaseCacheEntryReleaseFailure<E>),
}

/// Successful resident-limit publication and active FIFO removals.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeExecutableSequenceLeaseCacheReconfiguration {
    evicted_keys: Vec<NativeExecutableSequenceKey>,
    new_limits: NativeExecutableSequenceCacheLimits,
    previous_limits: NativeExecutableSequenceCacheLimits,
    retired_keys: Vec<NativeExecutableSequenceKey>,
}

/// Failed resident-limit publication retaining exact blocker or cleanup owner.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeExecutableSequenceLeaseCacheReconfigurationFailure<E> {
    cause: LeaseCacheReconfigurationFailureCause<E>,
    evicted_keys: Vec<NativeExecutableSequenceKey>,
    requested_limits: NativeExecutableSequenceCacheLimits,
    retained_limits: NativeExecutableSequenceCacheLimits,
    retired_keys: Vec<NativeExecutableSequenceKey>,
}

/// Result of publishing new resident limits after active FIFO processing.
pub type NativeExecutableSequenceLeaseCacheReconfigurationResult<E> = Result<
    NativeExecutableSequenceLeaseCacheReconfiguration,
    Box<NativeExecutableSequenceLeaseCacheReconfigurationFailure<E>>,
>;

type NativeExecutableSequenceLeaseCacheReconfigurationEvictionResult<E> =
    Result<
        (
            Vec<NativeExecutableSequenceKey>,
            Vec<NativeExecutableSequenceKey>,
        ),
        Box<NativeExecutableSequenceLeaseCacheReconfigurationFailure<E>>,
    >;

impl NativeExecutableSequenceLeaseCacheReconfiguration {
    /// Returns every active FIFO key removed before publication.
    #[must_use]
    pub fn evicted_keys(&self) -> &[NativeExecutableSequenceKey] {
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
    pub fn retired_keys(&self) -> &[NativeExecutableSequenceKey] {
        &self.retired_keys
    }
}

impl<E> NativeExecutableSequenceLeaseCacheReconfigurationFailure<E> {
    /// Returns exact resident lease blockage, when publication cannot fit.
    #[must_use]
    pub const fn block(
        &self,
    ) -> Option<&NativeExecutableSequenceLeaseCacheBlock> {
        match &self.cause {
            LeaseCacheReconfigurationFailureCause::Leases(block) => Some(block),
            LeaseCacheReconfigurationFailureCause::Release(_) => None,
        }
    }

    /// Returns every active FIFO key removed before publication failed.
    #[must_use]
    pub fn evicted_keys(&self) -> &[NativeExecutableSequenceKey] {
        &self.evicted_keys
    }

    /// Consumes this failure and returns exact keyed release ownership.
    #[must_use]
    pub fn into_release_failure(
        self,
    ) -> Option<NativeExecutableSequenceLeaseCacheEntryReleaseFailure<E>> {
        match self.cause {
            LeaseCacheReconfigurationFailureCause::Leases(_) => None,
            LeaseCacheReconfigurationFailureCause::Release(failure) => {
                Some(failure)
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
    ) -> Option<&NativeExecutableSequenceLeaseCacheEntryReleaseFailure<E>> {
        match &self.cause {
            LeaseCacheReconfigurationFailureCause::Leases(_) => None,
            LeaseCacheReconfigurationFailureCause::Release(failure) => {
                Some(failure)
            },
        }
    }

    /// Returns removed keys still resident behind live leases.
    #[must_use]
    pub fn retired_keys(&self) -> &[NativeExecutableSequenceKey] {
        &self.retired_keys
    }
}

impl<E: Display> Display
    for NativeExecutableSequenceLeaseCacheReconfigurationFailure<E>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str("native executable lease cache reconfiguration failed: ")?;
        match &self.cause {
            LeaseCacheReconfigurationFailureCause::Leases(_) => {
                f.write_str("resident leases block requested limits")
            },
            LeaseCacheReconfigurationFailureCause::Release(failure) => {
                write!(f, "keyed release: {}", failure.failure())
            },
        }
    }
}

pub(super) const fn published(
    evicted_keys: Vec<NativeExecutableSequenceKey>,
    retired_keys: Vec<NativeExecutableSequenceKey>,
    new_limits: NativeExecutableSequenceCacheLimits,
    previous_limits: NativeExecutableSequenceCacheLimits,
) -> NativeExecutableSequenceLeaseCacheReconfiguration {
    NativeExecutableSequenceLeaseCacheReconfiguration {
        evicted_keys,
        new_limits,
        previous_limits,
        retired_keys,
    }
}

fn lease_cache_reconfiguration_blocked_failure<E>(
    context: LeaseCacheReconfigurationContext,
    cache: &NativeExecutableSequenceLeaseCache,
) -> NativeExecutableSequenceLeaseCacheReconfigurationFailure<E> {
    let block = NativeExecutableSequenceLeaseCacheBlock {
        limits: context.requested_limits,
        retired_keys: cache.retired_keys().cloned().collect(),
        usage: cache.usage,
    };
    NativeExecutableSequenceLeaseCacheReconfigurationFailure {
        cause: LeaseCacheReconfigurationFailureCause::Leases(block),
        evicted_keys: context.evicted_keys,
        requested_limits: context.requested_limits,
        retained_limits: context.retained_limits,
        retired_keys: context.retired_keys,
    }
}

fn lease_cache_reconfiguration_release_failure<E>(
    context: LeaseCacheReconfigurationContext,
    release_failure: NativeExecutableSequenceLeaseCacheEntryReleaseFailure<E>,
) -> NativeExecutableSequenceLeaseCacheReconfigurationFailure<E> {
    NativeExecutableSequenceLeaseCacheReconfigurationFailure {
        cause: LeaseCacheReconfigurationFailureCause::Release(release_failure),
        evicted_keys: context.evicted_keys,
        requested_limits: context.requested_limits,
        retained_limits: context.retained_limits,
        retired_keys: context.retired_keys,
    }
}

pub(super) fn evict_for_reconfiguration<Adapter>(
    cache: &mut NativeExecutableSequenceLeaseCache,
    adapter: &mut Adapter,
    requested_limits: NativeExecutableSequenceCacheLimits,
    retained_limits: NativeExecutableSequenceCacheLimits,
) -> NativeExecutableSequenceLeaseCacheReconfigurationEvictionResult<
    Adapter::Error,
>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let mut evicted_keys = Vec::new();
    let mut retired_keys = Vec::new();
    while requested_limits.usage_exceeds(cache.usage) {
        let Some(victim) = cache.active.pop_front() else {
            return Err(Box::new(lease_cache_reconfiguration_blocked_failure(
                LeaseCacheReconfigurationContext {
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
        match process_lease_cache_victim(adapter, victim) {
            LeaseCacheVictimOutcome::Released(weight) => {
                cache.usage.remove(weight);
            },
            LeaseCacheVictimOutcome::ReleaseFailed { failure, weight } => {
                cache.usage.remove(weight);
                let release_failure =
                    reconciliation::entry_release_failure(victim_key, *failure);
                return Err(Box::new(
                    lease_cache_reconfiguration_release_failure(
                        LeaseCacheReconfigurationContext {
                            evicted_keys,
                            requested_limits,
                            retained_limits,
                            retired_keys,
                        },
                        release_failure,
                    ),
                ));
            },
            LeaseCacheVictimOutcome::Retired(retired_entry) => {
                retired_keys.push(retired_entry.key.clone());
                cache.retired.push_back(retired_entry);
            },
        }
    }
    Ok((evicted_keys, retired_keys))
}
