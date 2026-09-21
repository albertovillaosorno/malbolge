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
//   - Transactional weighted-limit publication for the Crazy cache.
// - Must-Not:
//   - Admit candidates, refresh FIFO hits, or reconcile external leases.
// - Allows:
//   - Inputs: cache owner, memory adapter, and requested weighted limits.
//   - Outputs: exact limit transition or retryable FIFO-release failure.
//   - Side effects: required oldest-entry releases before publication.
// - Split-When:
//   - Lease retirement or asynchronous cleanup gains independent policy.
// - Merge-When:
//   - Candidate admission and limit changes share one reviewed transaction.
// - Summary:
//   - Shrinks Crazy cache limits through explicit FIFO cleanup.
// - Description:
//   - Prior limits remain published until every required release succeeds.
// - Usage:
//   - Called only by the Crazy sequence cache limit coordinator.
// - Defaults:
//   - Expansion and already-satisfied requests perform no adapter work.
//

//! Weighted-limit reconfiguration for cached Crazy sequences.

use super::{
    Display, FormatResult, Formatter, NativeExecutableMemoryAdapter,
    RegisterMaskedCrazyNativeSequenceCache,
    RegisterMaskedCrazyNativeSequenceCacheInvariantError,
    RegisterMaskedCrazyNativeSequenceCacheLimits,
    RegisterMaskedCrazyNativeSequenceKey,
    RegisterMaskedCrazyNativeSequenceReleaseFailure,
};

#[derive(Debug)]
enum ReconfigurationFailureCause<E> {
    Invariant(RegisterMaskedCrazyNativeSequenceCacheInvariantError),
    Release(Box<RegisterMaskedCrazyNativeSequenceReleaseFailure<E>>),
}

/// Successful weighted-limit publication and its FIFO removals.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RegisterMaskedCrazyNativeSequenceCacheReconfiguration {
    evicted_keys: Vec<RegisterMaskedCrazyNativeSequenceKey>,
    new_limits: RegisterMaskedCrazyNativeSequenceCacheLimits,
    previous_limits: RegisterMaskedCrazyNativeSequenceCacheLimits,
}

/// Failed weighted-limit publication retaining exact cleanup ownership.
#[derive(Debug)]
pub struct RegisterMaskedCrazyNativeSequenceCacheReconfigurationFailure<E> {
    cause: ReconfigurationFailureCause<E>,
    evicted_keys: Vec<RegisterMaskedCrazyNativeSequenceKey>,
    requested_limits: RegisterMaskedCrazyNativeSequenceCacheLimits,
    retained_limits: RegisterMaskedCrazyNativeSequenceCacheLimits,
}

/// Result of publishing new weighted limits after required FIFO cleanup.
pub type RegisterMaskedCrazyNativeSequenceCacheReconfigurationResult<E> =
    Result<
        RegisterMaskedCrazyNativeSequenceCacheReconfiguration,
        Box<RegisterMaskedCrazyNativeSequenceCacheReconfigurationFailure<E>>,
    >;

type ReconfigurationEvictionResult<E> = Result<
    Vec<RegisterMaskedCrazyNativeSequenceKey>,
    Box<RegisterMaskedCrazyNativeSequenceCacheReconfigurationFailure<E>>,
>;

impl RegisterMaskedCrazyNativeSequenceCacheReconfiguration {
    /// Returns exact FIFO keys removed before the new limits were published.
    #[must_use]
    pub fn evicted_keys(&self) -> &[RegisterMaskedCrazyNativeSequenceKey] {
        &self.evicted_keys
    }

    /// Returns `(previous, new)` weighted limits for this publication.
    #[must_use]
    pub const fn limit_transition(
        &self,
    ) -> (
        RegisterMaskedCrazyNativeSequenceCacheLimits,
        RegisterMaskedCrazyNativeSequenceCacheLimits,
    ) {
        (self.previous_limits, self.new_limits)
    }
}

impl<E> RegisterMaskedCrazyNativeSequenceCacheReconfigurationFailure<E> {
    /// Returns exact FIFO keys removed before reconfiguration failed.
    #[must_use]
    pub fn evicted_keys(&self) -> &[RegisterMaskedCrazyNativeSequenceKey] {
        &self.evicted_keys
    }

    /// Consumes this failure and returns retryable release ownership.
    #[must_use]
    pub fn into_release_failure(
        self,
    ) -> Option<RegisterMaskedCrazyNativeSequenceReleaseFailure<E>> {
        match self.cause {
            ReconfigurationFailureCause::Invariant(_) => None,
            ReconfigurationFailureCause::Release(failure) => Some(*failure),
        }
    }

    /// Returns internal cache-state inconsistency, when detected.
    #[must_use]
    pub const fn invariant_error(
        &self,
    ) -> Option<RegisterMaskedCrazyNativeSequenceCacheInvariantError> {
        match self.cause {
            ReconfigurationFailureCause::Invariant(error) => Some(error),
            ReconfigurationFailureCause::Release(_) => None,
        }
    }

    /// Returns `(retained, requested)` limits for this failed publication.
    #[must_use]
    pub const fn limit_transition(
        &self,
    ) -> (
        RegisterMaskedCrazyNativeSequenceCacheLimits,
        RegisterMaskedCrazyNativeSequenceCacheLimits,
    ) {
        (self.retained_limits, self.requested_limits)
    }

    /// Returns exact failed FIFO release ownership, when present.
    #[must_use]
    pub const fn release_failure(
        &self,
    ) -> Option<&RegisterMaskedCrazyNativeSequenceReleaseFailure<E>> {
        match &self.cause {
            ReconfigurationFailureCause::Invariant(_) => None,
            ReconfigurationFailureCause::Release(failure) => Some(failure),
        }
    }
}

impl<E: Display> Display
    for RegisterMaskedCrazyNativeSequenceCacheReconfigurationFailure<E>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str("Crazy v6 cache reconfiguration failed: ")?;
        match &self.cause {
            ReconfigurationFailureCause::Invariant(error) => {
                write!(f, "invariant: {error}")
            },
            ReconfigurationFailureCause::Release(error) => {
                write!(f, "release: {error}")
            },
        }
    }
}

pub(super) const fn published(
    evicted_keys: Vec<RegisterMaskedCrazyNativeSequenceKey>,
    new_limits: RegisterMaskedCrazyNativeSequenceCacheLimits,
    previous_limits: RegisterMaskedCrazyNativeSequenceCacheLimits,
) -> RegisterMaskedCrazyNativeSequenceCacheReconfiguration {
    RegisterMaskedCrazyNativeSequenceCacheReconfiguration {
        evicted_keys,
        new_limits,
        previous_limits,
    }
}

const fn invariant_failure<E>(
    evicted_keys: Vec<RegisterMaskedCrazyNativeSequenceKey>,
    requested_limits: RegisterMaskedCrazyNativeSequenceCacheLimits,
    retained_limits: RegisterMaskedCrazyNativeSequenceCacheLimits,
) -> RegisterMaskedCrazyNativeSequenceCacheReconfigurationFailure<E> {
    RegisterMaskedCrazyNativeSequenceCacheReconfigurationFailure {
        cause: ReconfigurationFailureCause::Invariant(
            RegisterMaskedCrazyNativeSequenceCacheInvariantError::EntryMissing,
        ),
        evicted_keys,
        requested_limits,
        retained_limits,
    }
}

const fn release_failure<E>(
    evicted_keys: Vec<RegisterMaskedCrazyNativeSequenceKey>,
    failure: Box<RegisterMaskedCrazyNativeSequenceReleaseFailure<E>>,
    requested_limits: RegisterMaskedCrazyNativeSequenceCacheLimits,
    retained_limits: RegisterMaskedCrazyNativeSequenceCacheLimits,
) -> RegisterMaskedCrazyNativeSequenceCacheReconfigurationFailure<E> {
    RegisterMaskedCrazyNativeSequenceCacheReconfigurationFailure {
        cause: ReconfigurationFailureCause::Release(failure),
        evicted_keys,
        requested_limits,
        retained_limits,
    }
}

pub(super) fn evict_for_reconfiguration<Adapter>(
    cache: &mut RegisterMaskedCrazyNativeSequenceCache,
    adapter: &mut Adapter,
    requested_limits: RegisterMaskedCrazyNativeSequenceCacheLimits,
    retained_limits: RegisterMaskedCrazyNativeSequenceCacheLimits,
) -> ReconfigurationEvictionResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let mut evicted_keys = Vec::new();
    while requested_limits.usage_exceeds(cache.usage) {
        let Some(victim) = cache.entries.pop_front() else {
            return Err(Box::new(invariant_failure(
                evicted_keys,
                requested_limits,
                retained_limits,
            )));
        };
        cache.usage.remove(victim.weight);
        evicted_keys.push(victim.key);
        if let Err(failure) = victim.sequence.release(adapter) {
            return Err(Box::new(release_failure(
                evicted_keys,
                failure,
                requested_limits,
                retained_limits,
            )));
        }
    }
    Ok(evicted_keys)
}
