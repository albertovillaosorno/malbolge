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
//   - Transactional resident-limit changes for Crazy v6 leases.
// - Must-Not:
//   - Reconcile prior retired entries, refresh hits, or reclaim live leases.
// - Allows:
//   - Inputs: Crazy lease cache owner, adapter, and requested limits.
//   - Outputs: exact evicted/retired keys or blocker/release ownership.
//   - Side effects: FIFO release or retirement required by one shrink request.
// - Split-When:
//   - Limit policy or asynchronous lease waiting gains independent ownership.
// - Merge-When:
//   - Admission and reconfiguration become one Crazy transaction.
// - Summary:
//   - Shrinks active Crazy authority while preserving leased weight.
// - Description:
//   - Prior limits remain published until every required transition succeeds.
// - Usage:
//   - Called by `RegisterMaskedCrazyLeaseCache::reconfigure_limits`.
// - Defaults:
//   - Existing retired entries are never reconciled implicitly.
//

//! Transactional weighted-limit changes for Crazy v6 residents.

use super::{
    CacheVictimOutcome, Display, FormatResult, Formatter, NativeArtifactKey,
    NativeExecutableMemoryAdapter, NativeExecutableSequenceCacheLimits,
    RegisterMaskedCrazyLeaseCache, RegisterMaskedCrazyLeaseCacheBlock,
    RegisterMaskedCrazyLeaseCacheEntryReleaseFailure, process_victim,
};

#[derive(Debug, Eq, PartialEq)]
struct CrazyReconfigurationContext {
    evicted_keys: Vec<NativeArtifactKey>,
    requested_limits: NativeExecutableSequenceCacheLimits,
    retained_limits: NativeExecutableSequenceCacheLimits,
    retired_keys: Vec<NativeArtifactKey>,
}

#[derive(Debug)]
enum CrazyReconfigurationFailureCause<E> {
    Leases(RegisterMaskedCrazyLeaseCacheBlock),
    Release(Box<RegisterMaskedCrazyLeaseCacheEntryReleaseFailure<E>>),
}

/// Successful Crazy resident-limit publication and FIFO removals.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RegisterMaskedCrazyLeaseCacheReconfiguration {
    evicted_keys: Vec<NativeArtifactKey>,
    new_limits: NativeExecutableSequenceCacheLimits,
    previous_limits: NativeExecutableSequenceCacheLimits,
    retired_keys: Vec<NativeArtifactKey>,
}

/// Failed publication with exact Crazy blocker or cleanup ownership.
#[derive(Debug)]
pub struct RegisterMaskedCrazyLeaseCacheReconfigurationFailure<E> {
    cause: CrazyReconfigurationFailureCause<E>,
    evicted_keys: Vec<NativeArtifactKey>,
    requested_limits: NativeExecutableSequenceCacheLimits,
    retained_limits: NativeExecutableSequenceCacheLimits,
    retired_keys: Vec<NativeArtifactKey>,
}

/// Result of publishing new Crazy limits after active FIFO processing.
pub type RegisterMaskedCrazyLeaseCacheReconfigurationResult<E> = Result<
    RegisterMaskedCrazyLeaseCacheReconfiguration,
    Box<RegisterMaskedCrazyLeaseCacheReconfigurationFailure<E>>,
>;

type ReconfigurationEvictionResult<E> = Result<
    (Vec<NativeArtifactKey>, Vec<NativeArtifactKey>),
    Box<RegisterMaskedCrazyLeaseCacheReconfigurationFailure<E>>,
>;

impl RegisterMaskedCrazyLeaseCacheReconfiguration {
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

impl<E> RegisterMaskedCrazyLeaseCacheReconfigurationFailure<E> {
    /// Returns exact resident lease blockage, when publication cannot fit.
    #[must_use]
    pub const fn block(&self) -> Option<&RegisterMaskedCrazyLeaseCacheBlock> {
        match &self.cause {
            CrazyReconfigurationFailureCause::Leases(block) => Some(block),
            CrazyReconfigurationFailureCause::Release(_) => None,
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
    ) -> Option<RegisterMaskedCrazyLeaseCacheEntryReleaseFailure<E>> {
        match self.cause {
            CrazyReconfigurationFailureCause::Leases(_) => None,
            CrazyReconfigurationFailureCause::Release(failure) => {
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
    ) -> Option<&RegisterMaskedCrazyLeaseCacheEntryReleaseFailure<E>> {
        match &self.cause {
            CrazyReconfigurationFailureCause::Leases(_) => None,
            CrazyReconfigurationFailureCause::Release(failure) => Some(failure),
        }
    }

    /// Returns removed keys still resident behind live leases.
    #[must_use]
    pub fn retired_keys(&self) -> &[NativeArtifactKey] {
        &self.retired_keys
    }
}

impl<E: Display> Display
    for RegisterMaskedCrazyLeaseCacheReconfigurationFailure<E>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str("Crazy v6 lease cache reconfiguration failed: ")?;
        match &self.cause {
            CrazyReconfigurationFailureCause::Leases(_) => {
                f.write_str("resident leases block requested limits")
            },
            CrazyReconfigurationFailureCause::Release(failure) => {
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
) -> RegisterMaskedCrazyLeaseCacheReconfiguration {
    RegisterMaskedCrazyLeaseCacheReconfiguration {
        evicted_keys,
        new_limits,
        previous_limits,
        retired_keys,
    }
}

fn blocked_failure<E>(
    context: CrazyReconfigurationContext,
    cache: &RegisterMaskedCrazyLeaseCache,
) -> RegisterMaskedCrazyLeaseCacheReconfigurationFailure<E> {
    let block = RegisterMaskedCrazyLeaseCacheBlock {
        limits: context.requested_limits,
        retired_keys: cache.retired_keys().cloned().collect(),
        usage: cache.usage,
    };
    RegisterMaskedCrazyLeaseCacheReconfigurationFailure {
        cause: CrazyReconfigurationFailureCause::Leases(block),
        evicted_keys: context.evicted_keys,
        requested_limits: context.requested_limits,
        retained_limits: context.retained_limits,
        retired_keys: context.retired_keys,
    }
}

fn release_failure<E>(
    context: CrazyReconfigurationContext,
    failure: RegisterMaskedCrazyLeaseCacheEntryReleaseFailure<E>,
) -> RegisterMaskedCrazyLeaseCacheReconfigurationFailure<E> {
    RegisterMaskedCrazyLeaseCacheReconfigurationFailure {
        cause: CrazyReconfigurationFailureCause::Release(Box::new(failure)),
        evicted_keys: context.evicted_keys,
        requested_limits: context.requested_limits,
        retained_limits: context.retained_limits,
        retired_keys: context.retired_keys,
    }
}

pub(super) fn evict_for_reconfiguration<Adapter>(
    cache: &mut RegisterMaskedCrazyLeaseCache,
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
                CrazyReconfigurationContext {
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
                let keyed = RegisterMaskedCrazyLeaseCacheEntryReleaseFailure {
                    failure,
                    key: victim_key,
                };
                return Err(Box::new(release_failure(
                    CrazyReconfigurationContext {
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
