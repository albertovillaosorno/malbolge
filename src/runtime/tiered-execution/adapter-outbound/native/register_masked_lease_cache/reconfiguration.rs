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
//   - Transactional resident-limit changes for register-masked v6 leases.
// - Must-Not:
//   - Reconcile prior retired entries, refresh hits, or reclaim live leases.
// - Allows:
//   - Inputs: v6 lease cache owner, adapter, and explicit requested limits.
//   - Outputs: exact evicted/retired keys or blocker/release ownership.
//   - Side effects: FIFO release or retirement required by one shrink request.
// - Split-When:
//   - Limit policy or asynchronous lease waiting gains independent ownership.
// - Merge-When:
//   - Admission and reconfiguration become one v6 resident transaction.
// - Summary:
//   - Shrinks active v6 authority while preserving exact leased resident
//     weight.
// - Description:
//   - Prior limits remain published until every required transition succeeds.
// - Usage:
//   - Called by `RegisterMaskedNativeLeaseCache::reconfigure_limits`.
// - Defaults:
//   - Existing retired entries are never reconciled implicitly.
//

//! Transactional weighted-limit changes for register-masked v6 residents.

use super::{
    Display, FormatResult, Formatter, NativeArtifactKey,
    NativeExecutableMemoryAdapter, NativeExecutableSequenceCacheLimits,
    RegisterMaskedNativeLeaseCache, RegisterMaskedNativeLeaseCacheBlock,
    RegisterMaskedNativeLeaseCacheEntryReleaseFailure,
    RegisterMaskedNativeLeaseCacheVictimOutcome, process_victim,
};

#[derive(Debug, Eq, PartialEq)]
struct RegisterMaskedReconfigurationContext {
    evicted_keys: Vec<NativeArtifactKey>,
    requested_limits: NativeExecutableSequenceCacheLimits,
    retained_limits: NativeExecutableSequenceCacheLimits,
    retired_keys: Vec<NativeArtifactKey>,
}

#[derive(Debug)]
enum RegisterMaskedReconfigurationFailureCause<E> {
    Leases(RegisterMaskedNativeLeaseCacheBlock),
    Release(Box<RegisterMaskedNativeLeaseCacheEntryReleaseFailure<E>>),
}

/// Successful v6 resident-limit publication and active FIFO removals.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RegisterMaskedNativeLeaseCacheReconfiguration {
    evicted_keys: Vec<NativeArtifactKey>,
    new_limits: NativeExecutableSequenceCacheLimits,
    previous_limits: NativeExecutableSequenceCacheLimits,
    retired_keys: Vec<NativeArtifactKey>,
}

/// Failed v6 resident-limit publication with exact blocker or cleanup owner.
#[derive(Debug)]
pub struct RegisterMaskedNativeLeaseCacheReconfigurationFailure<E> {
    cause: RegisterMaskedReconfigurationFailureCause<E>,
    evicted_keys: Vec<NativeArtifactKey>,
    requested_limits: NativeExecutableSequenceCacheLimits,
    retained_limits: NativeExecutableSequenceCacheLimits,
    retired_keys: Vec<NativeArtifactKey>,
}

/// Result of publishing new v6 resident limits after active FIFO processing.
pub type RegisterMaskedNativeLeaseCacheReconfigurationResult<E> = Result<
    RegisterMaskedNativeLeaseCacheReconfiguration,
    Box<RegisterMaskedNativeLeaseCacheReconfigurationFailure<E>>,
>;

type RegisterMaskedNativeLeaseCacheReconfigurationEvictionResult<E> = Result<
    (Vec<NativeArtifactKey>, Vec<NativeArtifactKey>),
    Box<RegisterMaskedNativeLeaseCacheReconfigurationFailure<E>>,
>;

impl RegisterMaskedNativeLeaseCacheReconfiguration {
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

impl<E> RegisterMaskedNativeLeaseCacheReconfigurationFailure<E> {
    /// Returns exact resident lease blockage, when publication cannot fit.
    #[must_use]
    pub const fn block(&self) -> Option<&RegisterMaskedNativeLeaseCacheBlock> {
        match &self.cause {
            RegisterMaskedReconfigurationFailureCause::Leases(block) => {
                Some(block)
            },
            RegisterMaskedReconfigurationFailureCause::Release(_) => None,
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
    ) -> Option<RegisterMaskedNativeLeaseCacheEntryReleaseFailure<E>> {
        match self.cause {
            RegisterMaskedReconfigurationFailureCause::Leases(_) => None,
            RegisterMaskedReconfigurationFailureCause::Release(failure) => {
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
    ) -> Option<&RegisterMaskedNativeLeaseCacheEntryReleaseFailure<E>> {
        match &self.cause {
            RegisterMaskedReconfigurationFailureCause::Leases(_) => None,
            RegisterMaskedReconfigurationFailureCause::Release(failure) => {
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
    for RegisterMaskedNativeLeaseCacheReconfigurationFailure<E>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(
            "register-masked native lease cache reconfiguration failed: ",
        )?;
        match &self.cause {
            RegisterMaskedReconfigurationFailureCause::Leases(_) => {
                f.write_str("resident leases block requested limits")
            },
            RegisterMaskedReconfigurationFailureCause::Release(failure) => {
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
) -> RegisterMaskedNativeLeaseCacheReconfiguration {
    RegisterMaskedNativeLeaseCacheReconfiguration {
        evicted_keys,
        new_limits,
        previous_limits,
        retired_keys,
    }
}

fn blocked_failure<E>(
    context: RegisterMaskedReconfigurationContext,
    cache: &RegisterMaskedNativeLeaseCache,
) -> RegisterMaskedNativeLeaseCacheReconfigurationFailure<E> {
    let block = RegisterMaskedNativeLeaseCacheBlock {
        limits: context.requested_limits,
        retired_keys: cache.retired_keys().cloned().collect(),
        usage: cache.usage,
    };
    RegisterMaskedNativeLeaseCacheReconfigurationFailure {
        cause: RegisterMaskedReconfigurationFailureCause::Leases(block),
        evicted_keys: context.evicted_keys,
        requested_limits: context.requested_limits,
        retained_limits: context.retained_limits,
        retired_keys: context.retired_keys,
    }
}

fn release_failure<E>(
    context: RegisterMaskedReconfigurationContext,
    failure: RegisterMaskedNativeLeaseCacheEntryReleaseFailure<E>,
) -> RegisterMaskedNativeLeaseCacheReconfigurationFailure<E> {
    RegisterMaskedNativeLeaseCacheReconfigurationFailure {
        cause: RegisterMaskedReconfigurationFailureCause::Release(Box::new(
            failure,
        )),
        evicted_keys: context.evicted_keys,
        requested_limits: context.requested_limits,
        retained_limits: context.retained_limits,
        retired_keys: context.retired_keys,
    }
}

pub(super) fn evict_for_reconfiguration<Adapter>(
    cache: &mut RegisterMaskedNativeLeaseCache,
    adapter: &mut Adapter,
    requested_limits: NativeExecutableSequenceCacheLimits,
    retained_limits: NativeExecutableSequenceCacheLimits,
) -> RegisterMaskedNativeLeaseCacheReconfigurationEvictionResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let mut evicted_keys = Vec::new();
    let mut retired_keys = Vec::new();
    while requested_limits.usage_exceeds(cache.usage) {
        let Some(victim) = cache.active.pop_front() else {
            return Err(Box::new(blocked_failure(
                RegisterMaskedReconfigurationContext {
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
            RegisterMaskedNativeLeaseCacheVictimOutcome::Released(weight) => {
                cache.usage.remove(weight);
            },
            RegisterMaskedNativeLeaseCacheVictimOutcome::ReleaseFailed {
                failure,
                weight,
            } => {
                cache.usage.remove(weight);
                let keyed = RegisterMaskedNativeLeaseCacheEntryReleaseFailure {
                    failure,
                    key: victim_key,
                };
                return Err(Box::new(release_failure(
                    RegisterMaskedReconfigurationContext {
                        evicted_keys,
                        requested_limits,
                        retained_limits,
                        retired_keys,
                    },
                    keyed,
                )));
            },
            RegisterMaskedNativeLeaseCacheVictimOutcome::Retired(entry) => {
                retired_keys.push(entry.key.clone());
                cache.retired.push_back(*entry);
            },
        }
    }
    Ok((evicted_keys, retired_keys))
}
