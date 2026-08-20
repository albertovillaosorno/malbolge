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
//   - Transactional publication of weighted executable-cache limit changes.
// - Must-Not:
//   - Admit candidates, refresh FIFO hits, or release unrelated cache entries.
// - Allows:
//   - Inputs: cache owner, memory adapter, and explicit requested limits.
//   - Outputs: exact transition evidence or retained release/invariant failure.
//   - Side effects: required oldest-entry releases before limit publication.
// - Split-When:
//   - Limit policy or release retry scheduling gains independent ownership.
// - Merge-When:
//   - Candidate admission and reconfiguration share one transaction.
// - Summary:
//   - Shrinks weighted limits transactionally while preserving prior authority.
// - Description:
//   - Publishes only after every required FIFO release succeeds.
// - Usage:
//   - Called exclusively by
//     `NativeExecutableSequenceCache::reconfigure_limits`.
// - Defaults:
//   - Expansion and already-satisfied requests perform no adapter work.
//

//! Transactional weighted-limit reconfiguration for executable sequences.

use super::*;

#[derive(Debug, Eq, PartialEq)]
enum NativeExecutableSequenceCacheReconfigurationFailureCause<E> {
    Invariant(NativeExecutableSequenceCacheInvariantError),
    Release(Box<NativeExecutableSequenceReleaseFailure<E>>),
}

/// Successful weighted-limit publication and its FIFO removals.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeExecutableSequenceCacheReconfiguration {
    evicted_keys: Vec<NativeExecutableSequenceKey>,
    new_limits: NativeExecutableSequenceCacheLimits,
    previous_limits: NativeExecutableSequenceCacheLimits,
}

/// Failed weighted-limit publication retaining exact cleanup ownership.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeExecutableSequenceCacheReconfigurationFailure<E> {
    cause: NativeExecutableSequenceCacheReconfigurationFailureCause<E>,
    evicted_keys: Vec<NativeExecutableSequenceKey>,
    requested_limits: NativeExecutableSequenceCacheLimits,
    retained_limits: NativeExecutableSequenceCacheLimits,
}

/// Result of publishing new weighted limits after required FIFO cleanup.
pub type NativeExecutableSequenceCacheReconfigurationResult<E> = Result<
    NativeExecutableSequenceCacheReconfiguration,
    Box<NativeExecutableSequenceCacheReconfigurationFailure<E>>,
>;

type NativeExecutableSequenceCacheReconfigurationEvictionResult<E> = Result<
    Vec<NativeExecutableSequenceKey>,
    Box<NativeExecutableSequenceCacheReconfigurationFailure<E>>,
>;

impl NativeExecutableSequenceCacheReconfiguration {
    /// Returns exact FIFO keys removed before the new limits were published.
    #[must_use]
    pub fn evicted_keys(&self) -> &[NativeExecutableSequenceKey] {
        &self.evicted_keys
    }

    /// Returns `(previous, new)` weighted limits for this publication.
    #[must_use]
    pub const fn limit_transition(
        &self,
    ) -> (
        NativeExecutableSequenceCacheLimits,
        NativeExecutableSequenceCacheLimits,
    ) {
        (self.previous_limits, self.new_limits)
    }
}

impl<E> NativeExecutableSequenceCacheReconfigurationFailure<E> {
    /// Returns exact FIFO keys removed before reconfiguration failed.
    #[must_use]
    pub fn evicted_keys(&self) -> &[NativeExecutableSequenceKey] {
        &self.evicted_keys
    }

    /// Consumes this failure and returns retryable release ownership.
    #[must_use]
    pub fn into_release_failure(
        self,
    ) -> Option<NativeExecutableSequenceReleaseFailure<E>> {
        match self.cause {
            NativeExecutableSequenceCacheReconfigurationFailureCause::Invariant(
                _,
            ) => None,
            NativeExecutableSequenceCacheReconfigurationFailureCause::Release(
                failure,
            ) => Some(*failure),
        }
    }

    /// Returns internal cache-state inconsistency, when detected.
    #[must_use]
    pub const fn invariant_error(
        &self,
    ) -> Option<NativeExecutableSequenceCacheInvariantError> {
        match self.cause {
            NativeExecutableSequenceCacheReconfigurationFailureCause::Invariant(
                error,
            ) => Some(error),
            NativeExecutableSequenceCacheReconfigurationFailureCause::Release(
                _,
            ) => None,
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

    /// Returns exact failed FIFO release ownership, when present.
    #[must_use]
    pub const fn release_failure(
        &self,
    ) -> Option<&NativeExecutableSequenceReleaseFailure<E>> {
        match &self.cause {
            NativeExecutableSequenceCacheReconfigurationFailureCause::Invariant(
                _,
            ) => None,
            NativeExecutableSequenceCacheReconfigurationFailureCause::Release(
                failure,
            ) => Some(failure),
        }
    }
}

impl<E: Display> Display
    for NativeExecutableSequenceCacheReconfigurationFailure<E>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(
            "native executable sequence cache reconfiguration failed: ",
        )?;
        match &self.cause {
            NativeExecutableSequenceCacheReconfigurationFailureCause::Invariant(
                error,
            ) => write!(f, "invariant: {error}"),
            NativeExecutableSequenceCacheReconfigurationFailureCause::Release(
                error,
            ) => write!(f, "release: {error}"),
        }
    }
}

pub(super) const fn published(
    evicted_keys: Vec<NativeExecutableSequenceKey>,
    new_limits: NativeExecutableSequenceCacheLimits,
    previous_limits: NativeExecutableSequenceCacheLimits,
) -> NativeExecutableSequenceCacheReconfiguration {
    NativeExecutableSequenceCacheReconfiguration {
        evicted_keys,
        new_limits,
        previous_limits,
    }
}

pub(super) const fn cache_reconfiguration_invariant_failure<E>(
    evicted_keys: Vec<NativeExecutableSequenceKey>,
    requested_limits: NativeExecutableSequenceCacheLimits,
    retained_limits: NativeExecutableSequenceCacheLimits,
) -> NativeExecutableSequenceCacheReconfigurationFailure<E> {
    NativeExecutableSequenceCacheReconfigurationFailure {
        cause:
            NativeExecutableSequenceCacheReconfigurationFailureCause::Invariant(
                NativeExecutableSequenceCacheInvariantError::EntryMissing,
            ),
        evicted_keys,
        requested_limits,
        retained_limits,
    }
}

pub(super) const fn cache_reconfiguration_release_failure<E>(
    evicted_keys: Vec<NativeExecutableSequenceKey>,
    release_failure: Box<NativeExecutableSequenceReleaseFailure<E>>,
    requested_limits: NativeExecutableSequenceCacheLimits,
    retained_limits: NativeExecutableSequenceCacheLimits,
) -> NativeExecutableSequenceCacheReconfigurationFailure<E> {
    NativeExecutableSequenceCacheReconfigurationFailure {
        cause:
            NativeExecutableSequenceCacheReconfigurationFailureCause::Release(
                release_failure,
            ),
        evicted_keys,
        requested_limits,
        retained_limits,
    }
}

pub(super) fn evict_for_reconfiguration<Adapter>(
    cache: &mut NativeExecutableSequenceCache,
    memory_adapter: &mut Adapter,
    requested_limits: NativeExecutableSequenceCacheLimits,
    retained_limits: NativeExecutableSequenceCacheLimits,
) -> NativeExecutableSequenceCacheReconfigurationEvictionResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let mut evicted_keys = Vec::new();
    while requested_limits.usage_exceeds(cache.usage) {
        let Some(victim) = cache.entries.pop_front() else {
            return Err(Box::new(cache_reconfiguration_invariant_failure(
                evicted_keys,
                requested_limits,
                retained_limits,
            )));
        };
        cache.usage.remove(victim.weight);
        evicted_keys.push(victim.key);
        if let Err(release_failure) =
            release_native_executable_sequence(memory_adapter, victim.sequence)
        {
            return Err(Box::new(cache_reconfiguration_release_failure(
                evicted_keys,
                release_failure,
                requested_limits,
                retained_limits,
            )));
        }
    }
    Ok(evicted_keys)
}
