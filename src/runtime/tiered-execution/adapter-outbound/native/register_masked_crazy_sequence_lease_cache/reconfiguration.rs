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
//   - Transactional resident-limit changes for Crazy sequence leases.
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
//   - Called by the Crazy sequence lease cache reconfiguration API.
// - Defaults:
//   - Existing retired entries are never reconciled implicitly.
//

//! Transactional limit changes for Crazy sequence lease residency.

use super::{
    CacheVictimOutcome, Display, FormatResult, Formatter,
    NativeExecutableMemoryAdapter, NativeExecutableSequenceCacheLimits,
    RegisterMaskedCrazyNativeSequenceKey,
    RegisterMaskedCrazyNativeSequenceLeaseCache,
    RegisterMaskedCrazyNativeSequenceLeaseCacheBlock,
    RegisterMaskedCrazyNativeSequenceLeaseCacheEntryReleaseFailure,
    process_cache_victim, reconciliation,
};

#[derive(Debug)]
struct ReconfigurationContext {
    evicted_keys: Vec<RegisterMaskedCrazyNativeSequenceKey>,
    requested_limits: NativeExecutableSequenceCacheLimits,
    retained_limits: NativeExecutableSequenceCacheLimits,
    retired_keys: Vec<RegisterMaskedCrazyNativeSequenceKey>,
}

#[derive(Debug)]
enum ReconfigurationFailureCause<E> {
    Leases(RegisterMaskedCrazyNativeSequenceLeaseCacheBlock),
    Release(RegisterMaskedCrazyNativeSequenceLeaseCacheEntryReleaseFailure<E>),
}

/// Successful limit publication and active FIFO removals.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RegisterMaskedCrazyNativeSequenceLeaseCacheReconfiguration {
    evicted_keys: Vec<RegisterMaskedCrazyNativeSequenceKey>,
    new_limits: NativeExecutableSequenceCacheLimits,
    previous_limits: NativeExecutableSequenceCacheLimits,
    retired_keys: Vec<RegisterMaskedCrazyNativeSequenceKey>,
}

/// Failed limit publication retaining exact blocker or cleanup ownership.
#[derive(Debug)]
pub struct RegisterMaskedCrazyNativeSequenceLeaseReconfigurationFailure<E> {
    cause: ReconfigurationFailureCause<E>,
    evicted_keys: Vec<RegisterMaskedCrazyNativeSequenceKey>,
    requested_limits: NativeExecutableSequenceCacheLimits,
    retained_limits: NativeExecutableSequenceCacheLimits,
    retired_keys: Vec<RegisterMaskedCrazyNativeSequenceKey>,
}

/// Result of publishing new limits after active FIFO processing.
pub type RegisterMaskedCrazyNativeSequenceLeaseReconfigurationResult<E> =
    Result<
        RegisterMaskedCrazyNativeSequenceLeaseCacheReconfiguration,
        Box<RegisterMaskedCrazyNativeSequenceLeaseReconfigurationFailure<E>>,
    >;

type EntryReleaseFailure<E> =
    RegisterMaskedCrazyNativeSequenceLeaseCacheEntryReleaseFailure<E>;

type ReconfigurationEvictionResult<E> = Result<
    (
        Vec<RegisterMaskedCrazyNativeSequenceKey>,
        Vec<RegisterMaskedCrazyNativeSequenceKey>,
    ),
    Box<RegisterMaskedCrazyNativeSequenceLeaseReconfigurationFailure<E>>,
>;

impl RegisterMaskedCrazyNativeSequenceLeaseCacheReconfiguration {
    /// Returns every active FIFO key removed before publication.
    #[must_use]
    pub fn evicted_keys(&self) -> &[RegisterMaskedCrazyNativeSequenceKey] {
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
    pub fn retired_keys(&self) -> &[RegisterMaskedCrazyNativeSequenceKey] {
        &self.retired_keys
    }
}

impl<E> RegisterMaskedCrazyNativeSequenceLeaseReconfigurationFailure<E> {
    /// Returns exact resident lease blockage, when publication cannot fit.
    #[must_use]
    pub const fn block(
        &self,
    ) -> Option<&RegisterMaskedCrazyNativeSequenceLeaseCacheBlock> {
        match &self.cause {
            ReconfigurationFailureCause::Leases(block) => Some(block),
            ReconfigurationFailureCause::Release(_) => None,
        }
    }

    /// Returns every active FIFO key removed before publication failed.
    #[must_use]
    pub fn evicted_keys(&self) -> &[RegisterMaskedCrazyNativeSequenceKey] {
        &self.evicted_keys
    }

    /// Consumes this failure and returns exact keyed release ownership.
    #[must_use]
    pub fn into_release_failure(self) -> Option<EntryReleaseFailure<E>> {
        match self.cause {
            ReconfigurationFailureCause::Leases(_) => None,
            ReconfigurationFailureCause::Release(failure) => Some(failure),
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
    ) -> Option<
        &RegisterMaskedCrazyNativeSequenceLeaseCacheEntryReleaseFailure<E>,
    > {
        match &self.cause {
            ReconfigurationFailureCause::Leases(_) => None,
            ReconfigurationFailureCause::Release(failure) => Some(failure),
        }
    }

    /// Returns removed keys still resident behind live leases.
    #[must_use]
    pub fn retired_keys(&self) -> &[RegisterMaskedCrazyNativeSequenceKey] {
        &self.retired_keys
    }
}

impl<E: Display> Display
    for RegisterMaskedCrazyNativeSequenceLeaseReconfigurationFailure<E>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str("Crazy v6 sequence lease reconfiguration failed: ")?;
        match &self.cause {
            ReconfigurationFailureCause::Leases(_) => {
                f.write_str("resident leases block requested limits")
            },
            ReconfigurationFailureCause::Release(failure) => {
                write!(f, "keyed release: {}", failure.failure())
            },
        }
    }
}

pub(super) fn evict_for_reconfiguration<Adapter>(
    cache: &mut RegisterMaskedCrazyNativeSequenceLeaseCache,
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
            let context = ReconfigurationContext {
                evicted_keys,
                requested_limits,
                retained_limits,
                retired_keys,
            };
            return Err(Box::new(blocked_failure(context, cache)));
        };
        let victim_key = victim.key.clone();
        evicted_keys.push(victim_key.clone());
        match process_cache_victim(adapter, victim) {
            CacheVictimOutcome::Released(weight) => cache.usage.remove(weight),
            CacheVictimOutcome::ReleaseFailed { failure, weight } => {
                cache.usage.remove(weight);
                let keyed =
                    reconciliation::entry_release_failure(victim_key, *failure);
                let context = ReconfigurationContext {
                    evicted_keys,
                    requested_limits,
                    retained_limits,
                    retired_keys,
                };
                return Err(Box::new(release_failure(context, keyed)));
            },
            CacheVictimOutcome::Retired(retired_entry) => {
                retired_keys.push(retired_entry.key.clone());
                cache.retired.push_back(retired_entry);
            },
        }
    }
    Ok((evicted_keys, retired_keys))
}

pub(super) const fn published(
    evicted_keys: Vec<RegisterMaskedCrazyNativeSequenceKey>,
    retired_keys: Vec<RegisterMaskedCrazyNativeSequenceKey>,
    new_limits: NativeExecutableSequenceCacheLimits,
    previous_limits: NativeExecutableSequenceCacheLimits,
) -> RegisterMaskedCrazyNativeSequenceLeaseCacheReconfiguration {
    RegisterMaskedCrazyNativeSequenceLeaseCacheReconfiguration {
        evicted_keys,
        new_limits,
        previous_limits,
        retired_keys,
    }
}

fn blocked_failure<E>(
    context: ReconfigurationContext,
    cache: &RegisterMaskedCrazyNativeSequenceLeaseCache,
) -> RegisterMaskedCrazyNativeSequenceLeaseReconfigurationFailure<E> {
    let block = RegisterMaskedCrazyNativeSequenceLeaseCacheBlock {
        limits: context.requested_limits,
        retired_keys: cache.retired_keys().cloned().collect(),
        usage: cache.usage,
    };
    RegisterMaskedCrazyNativeSequenceLeaseReconfigurationFailure {
        cause: ReconfigurationFailureCause::Leases(block),
        evicted_keys: context.evicted_keys,
        requested_limits: context.requested_limits,
        retained_limits: context.retained_limits,
        retired_keys: context.retired_keys,
    }
}

fn release_failure<E>(
    context: ReconfigurationContext,
    failure: EntryReleaseFailure<E>,
) -> RegisterMaskedCrazyNativeSequenceLeaseReconfigurationFailure<E> {
    RegisterMaskedCrazyNativeSequenceLeaseReconfigurationFailure {
        cause: ReconfigurationFailureCause::Release(failure),
        evicted_keys: context.evicted_keys,
        requested_limits: context.requested_limits,
        retained_limits: context.retained_limits,
        retired_keys: context.retired_keys,
    }
}
