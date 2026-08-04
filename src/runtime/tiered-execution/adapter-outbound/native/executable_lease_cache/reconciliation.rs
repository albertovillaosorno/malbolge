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
//   - Explicit reclamation and retry ownership for retired executable leases.
// - Must-Not:
//   - Restore active lookup authority, infer cache limits, or retry implicitly.
// - Allows:
//   - Inputs: retired residents or release owners plus one memory adapter.
//   - Outputs: exact released/retained keys or keyed retryable failures.
//   - Side effects: release attempts for residents with no external leases.
// - Split-When:
//   - Retry scheduling or durable release journals gain independent ownership.
// - Merge-When:
//   - Lease return and cache reconfiguration become one transaction.
// - Summary:
//   - Reclaims retired mappings while retaining every failed release owner.
// - Description:
//   - Attempts all releasable entries and preserves live leased residents.
// - Usage:
//   - Called by explicit return, drain, reconciliation, and cleanup retry APIs.
// - Defaults:
//   - No active entry is reclaimed and no failure is retried automatically.
//

//! Explicit reclamation and keyed release retry for executable leases.

use super::*;

#[derive(Debug, Eq, PartialEq)]
enum LeaseCacheReconcileOutcome<E> {
    ReleaseFailed {
        failure: Box<NativeExecutableSequenceReleaseFailure<E>>,
        key: NativeExecutableSequenceKey,
        weight: NativeExecutableSequenceWeight,
    },
    Released {
        key: NativeExecutableSequenceKey,
        weight: NativeExecutableSequenceWeight,
    },
    Retained(NativeExecutableSequenceLeaseCacheValue),
}

/// Failed releases retained after one unsuccessful leased-cache insertion.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeExecutableSequenceLeaseCacheLoadReleaseFailures<E> {
    candidate: Option<NativeExecutableSequenceLeaseCacheEntryReleaseFailure<E>>,
    eviction: Option<NativeExecutableSequenceLeaseCacheEntryReleaseFailure<E>>,
}

/// Successful explicit reclamation pass over retired resident sequences.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeExecutableSequenceLeaseCacheReconciliation {
    released_keys: Vec<NativeExecutableSequenceKey>,
    retained_keys: Vec<NativeExecutableSequenceKey>,
}

/// One sequence release failure removed from cache ownership for exact retry.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeExecutableSequenceLeaseCacheEntryReleaseFailure<E> {
    failure: NativeExecutableSequenceReleaseFailure<E>,
    key: NativeExecutableSequenceKey,
}

/// Aggregate explicit reclamation failure after attempting every releasable
/// entry.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeExecutableSequenceLeaseCacheReleaseFailure<E> {
    failures: Vec<NativeExecutableSequenceLeaseCacheEntryReleaseFailure<E>>,
    released_keys: Vec<NativeExecutableSequenceKey>,
    retained_keys: Vec<NativeExecutableSequenceKey>,
}

/// Result of reconciling retired resident sequences.
pub type NativeExecutableSequenceLeaseCacheReconciliationResult<E> = Result<
    NativeExecutableSequenceLeaseCacheReconciliation,
    Box<NativeExecutableSequenceLeaseCacheReleaseFailure<E>>,
>;

impl NativeExecutableSequenceLeaseCacheReconciliation {
    /// Returns retired keys released during this reconciliation pass.
    #[must_use]
    pub fn released_keys(&self) -> &[NativeExecutableSequenceKey] {
        &self.released_keys
    }

    /// Returns retired keys still resident behind external leases.
    #[must_use]
    pub fn retained_keys(&self) -> &[NativeExecutableSequenceKey] {
        &self.retained_keys
    }
}

impl<E> NativeExecutableSequenceLeaseCacheEntryReleaseFailure<E> {
    /// Returns exact sequence release ownership retained by this entry.
    #[must_use]
    pub const fn failure(&self) -> &NativeExecutableSequenceReleaseFailure<E> {
        &self.failure
    }

    /// Consumes this entry failure and returns exact sequence release
    /// ownership.
    #[must_use]
    pub fn into_failure(self) -> NativeExecutableSequenceReleaseFailure<E> {
        self.failure
    }

    /// Returns exact retired key whose release failed.
    #[must_use]
    pub const fn key(&self) -> &NativeExecutableSequenceKey {
        &self.key
    }
}

impl<E> NativeExecutableSequenceLeaseCacheLoadReleaseFailures<E> {
    /// Returns failed candidate cleanup ownership, when present.
    #[must_use]
    pub fn candidate_failure(
        &self,
    ) -> Option<&NativeExecutableSequenceReleaseFailure<E>> {
        self.candidate
            .as_ref()
            .map(NativeExecutableSequenceLeaseCacheEntryReleaseFailure::failure)
    }

    /// Returns failed FIFO victim release ownership, when present.
    #[must_use]
    pub fn eviction_failure(
        &self,
    ) -> Option<&NativeExecutableSequenceReleaseFailure<E>> {
        self.eviction
            .as_ref()
            .map(NativeExecutableSequenceLeaseCacheEntryReleaseFailure::failure)
    }

    /// Retries every mapping still owned outside the leased cache.
    ///
    /// # Errors
    ///
    /// Returns aggregate retained release ownership after attempting both
    /// owners.
    pub fn retry<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> NativeExecutableSequenceLeaseCacheReconciliationResult<E>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = E>,
    {
        retry_unkeyed_release_failures(adapter, self)
    }
}

impl<E> NativeExecutableSequenceLeaseCacheReleaseFailure<E> {
    /// Returns every keyed sequence release failure retained outside the cache.
    #[must_use]
    pub fn failures(
        &self,
    ) -> &[NativeExecutableSequenceLeaseCacheEntryReleaseFailure<E>] {
        &self.failures
    }

    /// Returns retired keys released before or during this failed pass.
    #[must_use]
    pub fn released_keys(&self) -> &[NativeExecutableSequenceKey] {
        &self.released_keys
    }

    /// Returns retired keys still resident behind external leases.
    #[must_use]
    pub fn retained_keys(&self) -> &[NativeExecutableSequenceKey] {
        &self.retained_keys
    }

    /// Retries all releases removed from cache ownership.
    ///
    /// # Errors
    ///
    /// Returns only repeated keyed failures after attempting every owner.
    pub fn retry<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> NativeExecutableSequenceLeaseCacheReconciliationResult<E>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = E>,
    {
        retry_keyed_release_failures(adapter, self)
    }
}

impl<E: Display> Display
    for NativeExecutableSequenceLeaseCacheReleaseFailure<E>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "native executable lease cache retained {} failed releases",
            self.failures.len(),
        )
    }
}

pub(super) const fn entry_release_failure<E>(
    key: NativeExecutableSequenceKey,
    failure: NativeExecutableSequenceReleaseFailure<E>,
) -> NativeExecutableSequenceLeaseCacheEntryReleaseFailure<E> {
    NativeExecutableSequenceLeaseCacheEntryReleaseFailure { failure, key }
}

pub(super) const fn load_release_failures<E>(
    candidate: Option<NativeExecutableSequenceLeaseCacheEntryReleaseFailure<E>>,
    eviction: Option<NativeExecutableSequenceLeaseCacheEntryReleaseFailure<E>>,
) -> NativeExecutableSequenceLeaseCacheLoadReleaseFailures<E> {
    NativeExecutableSequenceLeaseCacheLoadReleaseFailures {
        candidate,
        eviction,
    }
}

pub(super) fn reconcile_retired_values<Adapter>(
    adapter: &mut Adapter,
    retired: &mut VecDeque<NativeExecutableSequenceLeaseCacheValue>,
    usage: &mut NativeExecutableSequenceCacheUsage,
) -> NativeExecutableSequenceLeaseCacheReconciliationResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let mut failures = Vec::new();
    let mut released_keys = Vec::new();
    let mut retained_keys = Vec::new();
    let entries = retired.len();
    for _ in 0..entries {
        let Some(entry) = retired.pop_front() else {
            break;
        };
        match process_retired_lease_cache_value(adapter, entry) {
            LeaseCacheReconcileOutcome::ReleaseFailed {
                failure,
                key,
                weight,
            } => {
                usage.remove(weight);
                failures.push(
                    NativeExecutableSequenceLeaseCacheEntryReleaseFailure {
                        failure: *failure,
                        key,
                    },
                );
            },
            LeaseCacheReconcileOutcome::Released { key, weight } => {
                usage.remove(weight);
                released_keys.push(key);
            },
            LeaseCacheReconcileOutcome::Retained(retained_entry) => {
                retained_keys.push(retained_entry.key.clone());
                retired.push_back(retained_entry);
            },
        }
    }
    reconciliation_result(released_keys, retained_keys, failures)
}

fn process_retired_lease_cache_value<Adapter>(
    adapter: &mut Adapter,
    entry: NativeExecutableSequenceLeaseCacheValue,
) -> LeaseCacheReconcileOutcome<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let key = entry.key;
    let weight = entry.weight;
    match Arc::try_unwrap(entry.sequence) {
        Err(sequence) => LeaseCacheReconcileOutcome::Retained(
            NativeExecutableSequenceLeaseCacheValue { key, sequence, weight },
        ),
        Ok(sequence) => {
            match release_native_executable_sequence(adapter, sequence) {
                Ok(()) => LeaseCacheReconcileOutcome::Released { key, weight },
                Err(failure) => LeaseCacheReconcileOutcome::ReleaseFailed {
                    failure,
                    key,
                    weight,
                },
            }
        },
    }
}

fn reconciliation_result<E>(
    released_keys: Vec<NativeExecutableSequenceKey>,
    retained_keys: Vec<NativeExecutableSequenceKey>,
    failures: Vec<NativeExecutableSequenceLeaseCacheEntryReleaseFailure<E>>,
) -> NativeExecutableSequenceLeaseCacheReconciliationResult<E> {
    if failures.is_empty() {
        Ok(NativeExecutableSequenceLeaseCacheReconciliation {
            released_keys,
            retained_keys,
        })
    } else {
        Err(Box::new(NativeExecutableSequenceLeaseCacheReleaseFailure {
            failures,
            released_keys,
            retained_keys,
        }))
    }
}

fn retry_keyed_release_failures<Adapter>(
    adapter: &mut Adapter,
    pending: NativeExecutableSequenceLeaseCacheReleaseFailure<Adapter::Error>,
) -> NativeExecutableSequenceLeaseCacheReconciliationResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let mut failures = Vec::new();
    let mut released_keys = pending.released_keys;
    for entry in pending.failures {
        let key = entry.key;
        match entry.failure.retry(adapter) {
            Ok(()) => released_keys.push(key),
            Err(failure) => failures.push(
                NativeExecutableSequenceLeaseCacheEntryReleaseFailure {
                    failure: *failure,
                    key,
                },
            ),
        }
    }
    reconciliation_result(released_keys, pending.retained_keys, failures)
}

fn retry_unkeyed_release_failures<Adapter>(
    adapter: &mut Adapter,
    pending: NativeExecutableSequenceLeaseCacheLoadReleaseFailures<
        Adapter::Error,
    >,
) -> NativeExecutableSequenceLeaseCacheReconciliationResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let mut failures = Vec::with_capacity(2);
    if let Some(eviction) = pending.eviction {
        failures.push(eviction);
    }
    if let Some(candidate) = pending.candidate {
        failures.push(candidate);
    }
    retry_keyed_release_failures(
        adapter,
        NativeExecutableSequenceLeaseCacheReleaseFailure {
            failures,
            released_keys: Vec::new(),
            retained_keys: Vec::new(),
        },
    )
}
