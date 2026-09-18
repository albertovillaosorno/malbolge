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
//   - Explicit reclamation and retry ownership for retired no-operation leases.
// - Must-Not:
//   - Restore active lookup authority, infer limits, or retry implicitly.
// - Allows:
//   - Inputs: retired residents or release owners plus one memory adapter.
//   - Outputs: exact released/retained keys or keyed retryable failures.
//   - Side effects: release attempts only for residents without external
//     leases.
// - Split-When:
//   - Retry scheduling or durable cleanup journals gain independent ownership.
// - Merge-When:
//   - Lease return and weighted reconfiguration become one transaction.
// - Summary:
//   - Reclaims retired no-operation mappings and retains failed release owners.
// - Description:
//   - Attempts all releasable entries while preserving live leased residents.
// - Usage:
//   - Called by return, drain, reconciliation, and explicit retry APIs.
// - Defaults:
//   - Active entries are never reclaimed and failures are never retried
//     silently.
//

//! Explicit reclamation and keyed retry for no-operation sequence leases.

use super::{
    Arc, CacheValue, Display, FormatResult, Formatter,
    NativeExecutableMemoryAdapter, NativeExecutableSequenceCacheUsage,
    NativeExecutableSequenceWeight, RegisterMaskedNoOperationNativeSequenceKey,
    RegisterMaskedNoOperationNativeSequenceReleaseFailure, VecDeque,
};

#[derive(Debug)]
enum ReconcileOutcome<E> {
    ReleaseFailed {
        failure: Box<RegisterMaskedNoOperationNativeSequenceReleaseFailure<E>>,
        key: RegisterMaskedNoOperationNativeSequenceKey,
        weight: NativeExecutableSequenceWeight,
    },
    Released {
        key: RegisterMaskedNoOperationNativeSequenceKey,
        weight: NativeExecutableSequenceWeight,
    },
    Retained(CacheValue),
}

/// Failed releases retained after one unsuccessful leased-cache insertion.
#[derive(Debug)]
pub struct RegisterMaskedNoOperationNativeSequenceLeaseCacheLoadReleaseFailures<
    E,
> {
    candidate: Option<
        RegisterMaskedNoOperationNativeSequenceLeaseCacheEntryReleaseFailure<E>,
    >,
    eviction: Option<
        RegisterMaskedNoOperationNativeSequenceLeaseCacheEntryReleaseFailure<E>,
    >,
}

/// Successful explicit reclamation pass over retired no-operation sequences.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RegisterMaskedNoOperationNativeSequenceLeaseCacheReconciliation {
    released_keys: Vec<RegisterMaskedNoOperationNativeSequenceKey>,
    retained_keys: Vec<RegisterMaskedNoOperationNativeSequenceKey>,
}

/// One keyed sequence release failure removed from cache ownership for retry.
#[derive(Debug)]
pub struct RegisterMaskedNoOperationNativeSequenceLeaseCacheEntryReleaseFailure<
    E,
> {
    failure: RegisterMaskedNoOperationNativeSequenceReleaseFailure<E>,
    key: RegisterMaskedNoOperationNativeSequenceKey,
}

/// Aggregate reclamation failure after attempting every releasable entry.
#[derive(Debug)]
pub struct RegisterMaskedNoOperationNativeSequenceLeaseCacheReleaseFailure<E> {
    failures: Vec<
        RegisterMaskedNoOperationNativeSequenceLeaseCacheEntryReleaseFailure<E>,
    >,
    released_keys: Vec<RegisterMaskedNoOperationNativeSequenceKey>,
    retained_keys: Vec<RegisterMaskedNoOperationNativeSequenceKey>,
}

/// Result of reconciling retired no-operation resident sequences.
pub type RegisterMaskedNoOperationNativeSequenceLeaseReconciliationResult<E> =
    Result<
        RegisterMaskedNoOperationNativeSequenceLeaseCacheReconciliation,
        Box<RegisterMaskedNoOperationNativeSequenceLeaseCacheReleaseFailure<E>>,
    >;

type EntryReleaseFailure<E> =
    RegisterMaskedNoOperationNativeSequenceLeaseCacheEntryReleaseFailure<E>;

impl RegisterMaskedNoOperationNativeSequenceLeaseCacheReconciliation {
    /// Returns retired keys released during this reclamation pass.
    #[must_use]
    pub fn released_keys(
        &self,
    ) -> &[RegisterMaskedNoOperationNativeSequenceKey] {
        &self.released_keys
    }

    /// Returns retired keys still resident behind external leases.
    #[must_use]
    pub fn retained_keys(
        &self,
    ) -> &[RegisterMaskedNoOperationNativeSequenceKey] {
        &self.retained_keys
    }
}

impl<E>
    RegisterMaskedNoOperationNativeSequenceLeaseCacheEntryReleaseFailure<E>
{
    /// Returns exact sequence release ownership retained by this entry.
    #[must_use]
    pub const fn failure(
        &self,
    ) -> &RegisterMaskedNoOperationNativeSequenceReleaseFailure<E> {
        &self.failure
    }

    /// Consumes this keyed entry and returns exact sequence release ownership.
    #[must_use]
    pub fn into_failure(
        self,
    ) -> RegisterMaskedNoOperationNativeSequenceReleaseFailure<E> {
        self.failure
    }

    /// Returns exact retired key whose release failed.
    #[must_use]
    pub const fn key(&self) -> &RegisterMaskedNoOperationNativeSequenceKey {
        &self.key
    }
}

impl<E: Display> Display
    for RegisterMaskedNoOperationNativeSequenceLeaseCacheEntryReleaseFailure<E>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "no-operation v6 sequence lease keyed release failed: {}",
            self.failure,
        )
    }
}

impl<E>
    RegisterMaskedNoOperationNativeSequenceLeaseCacheLoadReleaseFailures<E>
{
    /// Returns failed candidate cleanup ownership, when present.
    #[must_use]
    pub fn candidate_failure(
        &self,
    ) -> Option<&RegisterMaskedNoOperationNativeSequenceReleaseFailure<E>> {
        self.candidate.as_ref().map(EntryReleaseFailure::failure)
    }

    /// Returns failed FIFO victim release ownership, when present.
    #[must_use]
    pub fn eviction_failure(
        &self,
    ) -> Option<&RegisterMaskedNoOperationNativeSequenceReleaseFailure<E>> {
        self.eviction.as_ref().map(EntryReleaseFailure::failure)
    }

    /// Retries every mapping still owned outside the lease cache.
    ///
    /// # Errors
    ///
    /// Returns aggregate repeated keyed failures after attempting all owners.
    pub fn retry<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> RegisterMaskedNoOperationNativeSequenceLeaseReconciliationResult<E>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = E>,
    {
        let mut failures = Vec::with_capacity(2);
        if let Some(eviction) = self.eviction {
            failures.push(eviction);
        }
        if let Some(candidate) = self.candidate {
            failures.push(candidate);
        }
        retry_keyed_release_failures(adapter, Vec::new(), Vec::new(), failures)
    }
}

impl<E> RegisterMaskedNoOperationNativeSequenceLeaseCacheReleaseFailure<E> {
    /// Returns every keyed release failure retained outside cache ownership.
    #[must_use]
    pub fn failures(
        &self,
    ) -> &[
        RegisterMaskedNoOperationNativeSequenceLeaseCacheEntryReleaseFailure<E>
    ]{
        &self.failures
    }

    /// Returns retired keys released before or during this failed pass.
    #[must_use]
    pub fn released_keys(
        &self,
    ) -> &[RegisterMaskedNoOperationNativeSequenceKey] {
        &self.released_keys
    }

    /// Returns retired keys still resident behind external leases.
    #[must_use]
    pub fn retained_keys(
        &self,
    ) -> &[RegisterMaskedNoOperationNativeSequenceKey] {
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
    ) -> RegisterMaskedNoOperationNativeSequenceLeaseReconciliationResult<E>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = E>,
    {
        retry_keyed_release_failures(
            adapter,
            self.released_keys,
            self.retained_keys,
            self.failures,
        )
    }
}

impl<E: Display> Display
    for RegisterMaskedNoOperationNativeSequenceLeaseCacheReleaseFailure<E>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "no-operation v6 sequence lease cache retained {} failed releases",
            self.failures.len(),
        )
    }
}

pub(super) const fn entry_release_failure<E>(
    key: RegisterMaskedNoOperationNativeSequenceKey,
    failure: RegisterMaskedNoOperationNativeSequenceReleaseFailure<E>,
) -> RegisterMaskedNoOperationNativeSequenceLeaseCacheEntryReleaseFailure<E> {
    RegisterMaskedNoOperationNativeSequenceLeaseCacheEntryReleaseFailure {
        failure,
        key,
    }
}

pub(super) const fn load_release_failures<E>(
    candidate: Option<
        RegisterMaskedNoOperationNativeSequenceLeaseCacheEntryReleaseFailure<E>,
    >,
    eviction: Option<
        RegisterMaskedNoOperationNativeSequenceLeaseCacheEntryReleaseFailure<E>,
    >,
) -> RegisterMaskedNoOperationNativeSequenceLeaseCacheLoadReleaseFailures<E> {
    RegisterMaskedNoOperationNativeSequenceLeaseCacheLoadReleaseFailures {
        candidate,
        eviction,
    }
}

pub(super) fn reconcile_retired_values<Adapter>(
    adapter: &mut Adapter,
    retired: &mut VecDeque<CacheValue>,
    usage: &mut NativeExecutableSequenceCacheUsage,
) -> RegisterMaskedNoOperationNativeSequenceLeaseReconciliationResult<
    Adapter::Error,
>
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
        match process_retired_value(adapter, entry) {
            ReconcileOutcome::ReleaseFailed { failure, key, weight } => {
                usage.remove(weight);
                failures.push(entry_release_failure(key, *failure));
            },
            ReconcileOutcome::Released { key, weight } => {
                usage.remove(weight);
                released_keys.push(key);
            },
            ReconcileOutcome::Retained(retained_entry) => {
                retained_keys.push(retained_entry.key.clone());
                retired.push_back(retained_entry);
            },
        }
    }
    reconciliation_result(released_keys, retained_keys, failures)
}

fn process_retired_value<Adapter>(
    adapter: &mut Adapter,
    entry: CacheValue,
) -> ReconcileOutcome<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let key = entry.key;
    let weight = entry.weight;
    match Arc::try_unwrap(entry.sequence) {
        Err(sequence) => {
            ReconcileOutcome::Retained(CacheValue { key, sequence, weight })
        },
        Ok(sequence) => match sequence.release(adapter) {
            Ok(()) => ReconcileOutcome::Released { key, weight },
            Err(failure) => {
                ReconcileOutcome::ReleaseFailed { failure, key, weight }
            },
        },
    }
}

fn reconciliation_result<E>(
    released_keys: Vec<RegisterMaskedNoOperationNativeSequenceKey>,
    retained_keys: Vec<RegisterMaskedNoOperationNativeSequenceKey>,
    failures: Vec<
        RegisterMaskedNoOperationNativeSequenceLeaseCacheEntryReleaseFailure<E>,
    >,
) -> RegisterMaskedNoOperationNativeSequenceLeaseReconciliationResult<E> {
    if failures.is_empty() {
        Ok(
            RegisterMaskedNoOperationNativeSequenceLeaseCacheReconciliation {
                released_keys,
                retained_keys,
            },
        )
    } else {
        Err(Box::new(
            RegisterMaskedNoOperationNativeSequenceLeaseCacheReleaseFailure {
                failures,
                released_keys,
                retained_keys,
            },
        ))
    }
}

fn retry_keyed_release_failures<Adapter>(
    adapter: &mut Adapter,
    mut released_keys: Vec<RegisterMaskedNoOperationNativeSequenceKey>,
    retained_keys: Vec<RegisterMaskedNoOperationNativeSequenceKey>,
    pending: Vec<
        RegisterMaskedNoOperationNativeSequenceLeaseCacheEntryReleaseFailure<
            Adapter::Error,
        >,
    >,
) -> RegisterMaskedNoOperationNativeSequenceLeaseReconciliationResult<
    Adapter::Error,
>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let mut failures = Vec::new();
    for entry in pending {
        let key = entry.key;
        match entry.failure.retry(adapter) {
            Ok(()) => released_keys.push(key),
            Err(failure) => failures.push(entry_release_failure(key, *failure)),
        }
    }
    reconciliation_result(released_keys, retained_keys, failures)
}
