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
//   - Transactional resident-limit changes for JumpCode v6 leases.
// - Must-Not:
//   - Reconcile prior retired entries, refresh hits, or reclaim live leases.
// - Allows:
//   - Inputs: JumpCode lease cache owner, adapter, and requested limits.
//   - JumpCodes: exact evicted/retired keys or blocker/release ownership.
//   - Side effects: FIFO release or retirement required by one shrink request.
// - Split-When:
//   - Limit policy or asynchronous lease waiting gains independent ownership.
// - Merge-When:
//   - Admission and reconfiguration become one JumpCode transaction.
// - Summary:
//   - Shrinks active JumpCode authority while preserving leased weight.
// - Description:
//   - Prior limits remain published until every required transition succeeds.
// - Usage:
//   - Called by `RegisterMaskedJumpCodeLeaseCache::reconfigure_limits`.
// - Defaults:
//   - Existing retired entries are never reconciled implicitly.
//

//! Transactional weighted-limit changes for `JumpCode` v6 residents.

use super::{
    CacheVictimOutcome, Display, FormatResult, Formatter, NativeArtifactKey,
    NativeExecutableMemoryAdapter, NativeExecutableSequenceCacheLimits,
    RegisterMaskedJumpCodeLeaseCache, RegisterMaskedJumpCodeLeaseCacheBlock,
    RegisterMaskedJumpCodeLeaseCacheEntryReleaseFailure, process_victim,
};

#[derive(Debug, Eq, PartialEq)]
struct JumpCodeReconfigurationContext {
    evicted_keys: Vec<NativeArtifactKey>,
    requested_limits: NativeExecutableSequenceCacheLimits,
    retained_limits: NativeExecutableSequenceCacheLimits,
    retired_keys: Vec<NativeArtifactKey>,
}

#[derive(Debug)]
enum JumpCodeReconfigurationFailureCause<E> {
    Leases(RegisterMaskedJumpCodeLeaseCacheBlock),
    Release(Box<RegisterMaskedJumpCodeLeaseCacheEntryReleaseFailure<E>>),
}

/// Successful `JumpCode` resident-limit publication and FIFO removals.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RegisterMaskedJumpCodeLeaseCacheReconfiguration {
    evicted_keys: Vec<NativeArtifactKey>,
    new_limits: NativeExecutableSequenceCacheLimits,
    previous_limits: NativeExecutableSequenceCacheLimits,
    retired_keys: Vec<NativeArtifactKey>,
}

/// Failed publication with exact `JumpCode` blocker or cleanup ownership.
#[derive(Debug)]
pub struct RegisterMaskedJumpCodeLeaseCacheReconfigurationFailure<E> {
    cause: JumpCodeReconfigurationFailureCause<E>,
    evicted_keys: Vec<NativeArtifactKey>,
    requested_limits: NativeExecutableSequenceCacheLimits,
    retained_limits: NativeExecutableSequenceCacheLimits,
    retired_keys: Vec<NativeArtifactKey>,
}

/// Result of publishing new `JumpCode` limits after active FIFO processing.
pub type RegisterMaskedJumpCodeLeaseCacheReconfigurationResult<E> = Result<
    RegisterMaskedJumpCodeLeaseCacheReconfiguration,
    Box<RegisterMaskedJumpCodeLeaseCacheReconfigurationFailure<E>>,
>;

type ReconfigurationEvictionResult<E> = Result<
    (Vec<NativeArtifactKey>, Vec<NativeArtifactKey>),
    Box<RegisterMaskedJumpCodeLeaseCacheReconfigurationFailure<E>>,
>;

impl RegisterMaskedJumpCodeLeaseCacheReconfiguration {
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

impl<E> RegisterMaskedJumpCodeLeaseCacheReconfigurationFailure<E> {
    /// Returns exact resident lease blockage, when publication cannot fit.
    #[must_use]
    pub const fn block(
        &self,
    ) -> Option<&RegisterMaskedJumpCodeLeaseCacheBlock> {
        match &self.cause {
            JumpCodeReconfigurationFailureCause::Leases(block) => Some(block),
            JumpCodeReconfigurationFailureCause::Release(_) => None,
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
    ) -> Option<RegisterMaskedJumpCodeLeaseCacheEntryReleaseFailure<E>> {
        match self.cause {
            JumpCodeReconfigurationFailureCause::Leases(_) => None,
            JumpCodeReconfigurationFailureCause::Release(failure) => {
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
    ) -> Option<&RegisterMaskedJumpCodeLeaseCacheEntryReleaseFailure<E>> {
        match &self.cause {
            JumpCodeReconfigurationFailureCause::Leases(_) => None,
            JumpCodeReconfigurationFailureCause::Release(failure) => {
                Some(failure)
            },
        }
    }

    /// Returns removed keys still resident behind live leases.
    #[must_use]
    pub fn retired_keys(&self) -> &[NativeArtifactKey] {
        &self.retired_keys
    }
}

impl<E: Display> Display
    for RegisterMaskedJumpCodeLeaseCacheReconfigurationFailure<E>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str("JumpCode v6 lease cache reconfiguration failed: ")?;
        match &self.cause {
            JumpCodeReconfigurationFailureCause::Leases(_) => {
                f.write_str("resident leases block requested limits")
            },
            JumpCodeReconfigurationFailureCause::Release(failure) => {
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
) -> RegisterMaskedJumpCodeLeaseCacheReconfiguration {
    RegisterMaskedJumpCodeLeaseCacheReconfiguration {
        evicted_keys,
        new_limits,
        previous_limits,
        retired_keys,
    }
}

fn blocked_failure<E>(
    context: JumpCodeReconfigurationContext,
    cache: &RegisterMaskedJumpCodeLeaseCache,
) -> RegisterMaskedJumpCodeLeaseCacheReconfigurationFailure<E> {
    let block = RegisterMaskedJumpCodeLeaseCacheBlock {
        limits: context.requested_limits,
        retired_keys: cache.retired_keys().cloned().collect(),
        usage: cache.usage,
    };
    RegisterMaskedJumpCodeLeaseCacheReconfigurationFailure {
        cause: JumpCodeReconfigurationFailureCause::Leases(block),
        evicted_keys: context.evicted_keys,
        requested_limits: context.requested_limits,
        retained_limits: context.retained_limits,
        retired_keys: context.retired_keys,
    }
}

fn release_failure<E>(
    context: JumpCodeReconfigurationContext,
    failure: RegisterMaskedJumpCodeLeaseCacheEntryReleaseFailure<E>,
) -> RegisterMaskedJumpCodeLeaseCacheReconfigurationFailure<E> {
    RegisterMaskedJumpCodeLeaseCacheReconfigurationFailure {
        cause: JumpCodeReconfigurationFailureCause::Release(Box::new(failure)),
        evicted_keys: context.evicted_keys,
        requested_limits: context.requested_limits,
        retained_limits: context.retained_limits,
        retired_keys: context.retired_keys,
    }
}

pub(super) fn evict_for_reconfiguration<Adapter>(
    cache: &mut RegisterMaskedJumpCodeLeaseCache,
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
                JumpCodeReconfigurationContext {
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
                let keyed =
                    RegisterMaskedJumpCodeLeaseCacheEntryReleaseFailure {
                        failure,
                        key: victim_key,
                    };
                return Err(Box::new(release_failure(
                    JumpCodeReconfigurationContext {
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
