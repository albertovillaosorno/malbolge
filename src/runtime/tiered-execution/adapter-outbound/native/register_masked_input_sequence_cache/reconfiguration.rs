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
//   - Transactional weighted-limit publication for the Input cache.
// - Must-Not:
//   - Admit candidates, refresh FIFO hits, or reconcile external leases.
// - Allows:
//   - Inputs: cache owner, memory adapter, and requested weighted limits.
//   - Inputs: exact limit transition or retryable FIFO-release failure.
//   - Side effects: required oldest-entry releases before publication.
// - Split-When:
//   - Lease retirement or asynchronous cleanup gains independent policy.
// - Merge-When:
//   - Candidate admission and limit changes share one reviewed transaction.
// - Summary:
//   - Shrinks Input cache limits through explicit FIFO cleanup.
// - Description:
//   - Prior limits remain published until every required release succeeds.
// - Usage:
//   - Called only by the Input sequence cache limit coordinator.
// - Defaults:
//   - Expansion and already-satisfied requests perform no adapter work.
//

//! Weighted-limit reconfiguration for cached Input sequences.

use super::{
    Display, FormatResult, Formatter, NativeExecutableMemoryAdapter,
    RegisterMaskedInputNativeSequenceCache,
    RegisterMaskedInputNativeSequenceCacheInvariantError,
    RegisterMaskedInputNativeSequenceCacheLimits,
    RegisterMaskedInputNativeSequenceKey,
    RegisterMaskedInputNativeSequenceReleaseFailure,
};

#[derive(Debug)]
enum ReconfigurationFailureCause<E> {
    Invariant(RegisterMaskedInputNativeSequenceCacheInvariantError),
    Release(Box<RegisterMaskedInputNativeSequenceReleaseFailure<E>>),
}

/// Successful weighted-limit publication and its FIFO removals.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RegisterMaskedInputNativeSequenceCacheReconfiguration {
    evicted_keys: Vec<RegisterMaskedInputNativeSequenceKey>,
    new_limits: RegisterMaskedInputNativeSequenceCacheLimits,
    previous_limits: RegisterMaskedInputNativeSequenceCacheLimits,
}

/// Failed weighted-limit publication retaining exact cleanup ownership.
#[derive(Debug)]
pub struct RegisterMaskedInputNativeSequenceCacheReconfigurationFailure<E> {
    cause: ReconfigurationFailureCause<E>,
    evicted_keys: Vec<RegisterMaskedInputNativeSequenceKey>,
    requested_limits: RegisterMaskedInputNativeSequenceCacheLimits,
    retained_limits: RegisterMaskedInputNativeSequenceCacheLimits,
}

/// Result of publishing new weighted limits after required FIFO cleanup.
pub type RegisterMaskedInputNativeSequenceCacheReconfigurationResult<E> =
    Result<
        RegisterMaskedInputNativeSequenceCacheReconfiguration,
        Box<RegisterMaskedInputNativeSequenceCacheReconfigurationFailure<E>>,
    >;

type ReconfigurationEvictionResult<E> = Result<
    Vec<RegisterMaskedInputNativeSequenceKey>,
    Box<RegisterMaskedInputNativeSequenceCacheReconfigurationFailure<E>>,
>;

impl RegisterMaskedInputNativeSequenceCacheReconfiguration {
    /// Returns exact FIFO keys removed before the new limits were published.
    #[must_use]
    pub fn evicted_keys(&self) -> &[RegisterMaskedInputNativeSequenceKey] {
        &self.evicted_keys
    }

    /// Returns `(previous, new)` weighted limits for this publication.
    #[must_use]
    pub const fn limit_transition(
        &self,
    ) -> (
        RegisterMaskedInputNativeSequenceCacheLimits,
        RegisterMaskedInputNativeSequenceCacheLimits,
    ) {
        (self.previous_limits, self.new_limits)
    }
}

impl<E> RegisterMaskedInputNativeSequenceCacheReconfigurationFailure<E> {
    /// Returns exact FIFO keys removed before reconfiguration failed.
    #[must_use]
    pub fn evicted_keys(&self) -> &[RegisterMaskedInputNativeSequenceKey] {
        &self.evicted_keys
    }

    /// Consumes this failure and returns retryable release ownership.
    #[must_use]
    pub fn into_release_failure(
        self,
    ) -> Option<RegisterMaskedInputNativeSequenceReleaseFailure<E>> {
        match self.cause {
            ReconfigurationFailureCause::Invariant(_) => None,
            ReconfigurationFailureCause::Release(failure) => Some(*failure),
        }
    }

    /// Returns internal cache-state inconsistency, when detected.
    #[must_use]
    pub const fn invariant_error(
        &self,
    ) -> Option<RegisterMaskedInputNativeSequenceCacheInvariantError> {
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
        RegisterMaskedInputNativeSequenceCacheLimits,
        RegisterMaskedInputNativeSequenceCacheLimits,
    ) {
        (self.retained_limits, self.requested_limits)
    }

    /// Returns exact failed FIFO release ownership, when present.
    #[must_use]
    pub const fn release_failure(
        &self,
    ) -> Option<&RegisterMaskedInputNativeSequenceReleaseFailure<E>> {
        match &self.cause {
            ReconfigurationFailureCause::Invariant(_) => None,
            ReconfigurationFailureCause::Release(failure) => Some(failure),
        }
    }
}

impl<E: Display> Display
    for RegisterMaskedInputNativeSequenceCacheReconfigurationFailure<E>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str("Input v6 cache reconfiguration failed: ")?;
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
    evicted_keys: Vec<RegisterMaskedInputNativeSequenceKey>,
    new_limits: RegisterMaskedInputNativeSequenceCacheLimits,
    previous_limits: RegisterMaskedInputNativeSequenceCacheLimits,
) -> RegisterMaskedInputNativeSequenceCacheReconfiguration {
    RegisterMaskedInputNativeSequenceCacheReconfiguration {
        evicted_keys,
        new_limits,
        previous_limits,
    }
}

const fn invariant_failure<E>(
    evicted_keys: Vec<RegisterMaskedInputNativeSequenceKey>,
    requested_limits: RegisterMaskedInputNativeSequenceCacheLimits,
    retained_limits: RegisterMaskedInputNativeSequenceCacheLimits,
) -> RegisterMaskedInputNativeSequenceCacheReconfigurationFailure<E> {
    RegisterMaskedInputNativeSequenceCacheReconfigurationFailure {
        cause: ReconfigurationFailureCause::Invariant(
            RegisterMaskedInputNativeSequenceCacheInvariantError::EntryMissing,
        ),
        evicted_keys,
        requested_limits,
        retained_limits,
    }
}

const fn release_failure<E>(
    evicted_keys: Vec<RegisterMaskedInputNativeSequenceKey>,
    failure: Box<RegisterMaskedInputNativeSequenceReleaseFailure<E>>,
    requested_limits: RegisterMaskedInputNativeSequenceCacheLimits,
    retained_limits: RegisterMaskedInputNativeSequenceCacheLimits,
) -> RegisterMaskedInputNativeSequenceCacheReconfigurationFailure<E> {
    RegisterMaskedInputNativeSequenceCacheReconfigurationFailure {
        cause: ReconfigurationFailureCause::Release(failure),
        evicted_keys,
        requested_limits,
        retained_limits,
    }
}

pub(super) fn evict_for_reconfiguration<Adapter>(
    cache: &mut RegisterMaskedInputNativeSequenceCache,
    adapter: &mut Adapter,
    requested_limits: RegisterMaskedInputNativeSequenceCacheLimits,
    retained_limits: RegisterMaskedInputNativeSequenceCacheLimits,
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
