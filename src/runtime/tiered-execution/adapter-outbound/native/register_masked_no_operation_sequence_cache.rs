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
//   - Entry-count-bounded FIFO residency for loaded no-operation v6 sequences.
// - Must-Not:
//   - Execute native code, refresh FIFO age on hits, share borrowed entries
//     concurrently across cache mutation, or claim weighted/lease policy.
// - Allows:
//   - Inputs: admitted no-operation sequence plans and one memory adapter.
//   - Outputs: borrowed exact hits/inserts plus explicit eviction/load
//     failures.
//   - Side effects: sequence load/release only through the supplied adapter.
// - Split-When:
//   - Live external leases or weighted reconfiguration gain authority.
// - Merge-When:
//   - One reviewed no-operation sequence store subsumes cache and lease policy.
// - Summary:
//   - Reuses exact loaded no-operation chains under a fixed FIFO entry limit.
// - Description:
//   - Hits perform no adapter work; misses load fully before oldest-first
//     release and publish only after required cleanup succeeds.
// - Usage:
//   - Ensure an admitted plan, execute the borrowed loaded sequence, then
//     invalidate or release all explicitly.
// - Defaults:
//   - Capacity counts complete loaded sequences, not individual mappings.
//

//! Fixed-entry FIFO cache for loaded no-operation register-masked v6 sequences.

use std::collections::VecDeque;
use std::fmt::{Display, Formatter, Result as FormatResult};
use std::num::NonZeroUsize;

use super::platform::NativeExecutableMemoryAdapter;
use super::register_masked_no_operation_loaded_sequence::{
    LoadedRegisterMaskedNoOperationNativeSequence,
    RegisterMaskedNoOperationNativeSequenceLoadFailure,
    RegisterMaskedNoOperationNativeSequenceReleaseFailure,
    load_register_masked_no_operation_native_sequence,
};
use super::register_masked_no_operation_sequence::{
    RegisterMaskedNoOperationNativeSequenceKey,
    RegisterMaskedNoOperationNativeSequencePlan,
};

#[derive(Debug)]
struct CacheValue {
    key: RegisterMaskedNoOperationNativeSequenceKey,
    sequence: LoadedRegisterMaskedNoOperationNativeSequence,
}

#[derive(Debug)]
enum LoadFailureCause<E> {
    Eviction(Box<RegisterMaskedNoOperationNativeSequenceReleaseFailure<E>>),
    Invariant(RegisterMaskedNoOperationNativeSequenceCacheInvariantError),
    Load(Box<RegisterMaskedNoOperationNativeSequenceLoadFailure<E>>),
}

/// Caller-owned exact-plan cache with one positive FIFO entry limit.
#[derive(Debug)]
pub struct RegisterMaskedNoOperationNativeSequenceCache {
    capacity: NonZeroUsize,
    entries: VecDeque<CacheValue>,
}

/// Whether ensuring one plan reused or inserted loaded cache state.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum RegisterMaskedNoOperationNativeSequenceCacheDisposition {
    /// Exact ordered identity already existed; FIFO age was unchanged.
    Hit,
    /// A fully loaded miss entered the cache.
    Inserted {
        /// Exact oldest keys released before the candidate was published.
        evicted: Vec<RegisterMaskedNoOperationNativeSequenceKey>,
    },
}

/// Borrowed cache result retaining exact disposition and loaded sequence.
#[derive(Debug)]
pub struct RegisterMaskedNoOperationNativeSequenceCacheEntry<'cache> {
    disposition: RegisterMaskedNoOperationNativeSequenceCacheDisposition,
    key: &'cache RegisterMaskedNoOperationNativeSequenceKey,
    sequence: &'cache LoadedRegisterMaskedNoOperationNativeSequence,
}

/// Internal cache inconsistency rejected before exposing a borrow.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RegisterMaskedNoOperationNativeSequenceCacheInvariantError {
    /// A just-located or just-published exact key could not be borrowed.
    EntryMissing,
}

/// Failed releases retained by one unsuccessful cache publication.
#[derive(Debug)]
pub struct RegisterMaskedNoOperationNativeSequenceCacheLoadReleaseFailures<E> {
    candidate: Option<RegisterMaskedNoOperationNativeSequenceReleaseFailure<E>>,
    eviction: Option<RegisterMaskedNoOperationNativeSequenceReleaseFailure<E>>,
}

/// Failure while loading, evicting, or publishing one exact cache miss.
#[derive(Debug)]
pub struct RegisterMaskedNoOperationNativeSequenceCacheLoadFailure<E> {
    candidate_cleanup_failure:
        Option<Box<RegisterMaskedNoOperationNativeSequenceReleaseFailure<E>>>,
    cause: LoadFailureCause<E>,
    evicted_keys: Vec<RegisterMaskedNoOperationNativeSequenceKey>,
    requested_key: RegisterMaskedNoOperationNativeSequenceKey,
}

/// Aggregate cleanup failure after removing cache-owned sequence entries.
#[derive(Debug)]
pub struct RegisterMaskedNoOperationNativeSequenceCacheReleaseFailure<E> {
    attempted_entries: usize,
    failures: Vec<RegisterMaskedNoOperationNativeSequenceReleaseFailure<E>>,
    released_entries: usize,
}

type CacheReleaseResult<E> =
    RegisterMaskedNoOperationNativeSequenceCacheReleaseResult<E>;

type CachePublicationResult<E> = Result<
    RegisterMaskedNoOperationNativeSequenceCacheDisposition,
    Box<RegisterMaskedNoOperationNativeSequenceCacheLoadFailure<E>>,
>;
type SequenceReleaseFailure<E> =
    RegisterMaskedNoOperationNativeSequenceReleaseFailure<E>;

/// Result of loading or reusing one exact no-operation sequence plan.
pub type RegisterMaskedNoOperationNativeSequenceCacheLoadResult<'cache, E> =
    Result<
        RegisterMaskedNoOperationNativeSequenceCacheEntry<'cache>,
        Box<RegisterMaskedNoOperationNativeSequenceCacheLoadFailure<E>>,
    >;

/// Result of invalidating one exact loaded no-operation sequence.
pub type RegisterMaskedNoOperationNativeSequenceCacheInvalidationResult<E> =
    Result<bool, Box<RegisterMaskedNoOperationNativeSequenceReleaseFailure<E>>>;

/// Result of releasing every sequence removed from cache authority.
pub type RegisterMaskedNoOperationNativeSequenceCacheReleaseResult<E> = Result<
    (),
    Box<RegisterMaskedNoOperationNativeSequenceCacheReleaseFailure<E>>,
>;

impl RegisterMaskedNoOperationNativeSequenceCacheDisposition {
    /// Returns the first exact FIFO key evicted for an inserted miss.
    #[must_use]
    pub fn evicted_key(
        &self,
    ) -> Option<&RegisterMaskedNoOperationNativeSequenceKey> {
        self.evicted_keys().first()
    }

    /// Returns every exact FIFO key evicted to admit this acquisition.
    #[must_use]
    pub fn evicted_keys(
        &self,
    ) -> &[RegisterMaskedNoOperationNativeSequenceKey] {
        match self {
            Self::Hit => &[],
            Self::Inserted { evicted } => evicted,
        }
    }

    /// Reports whether this acquisition reused loaded mappings.
    #[must_use]
    pub const fn is_hit(&self) -> bool {
        matches!(self, Self::Hit)
    }
}

impl RegisterMaskedNoOperationNativeSequenceCacheEntry<'_> {
    /// Returns exact hit/insert evidence for this borrowed entry.
    #[must_use]
    pub const fn disposition(
        &self,
    ) -> &RegisterMaskedNoOperationNativeSequenceCacheDisposition {
        &self.disposition
    }

    /// Returns exact ordered identity retained by this cache entry.
    #[must_use]
    pub const fn key(&self) -> &RegisterMaskedNoOperationNativeSequenceKey {
        self.key
    }

    /// Returns the loaded sequence borrowed from cache authority.
    #[must_use]
    pub const fn sequence(
        &self,
    ) -> &LoadedRegisterMaskedNoOperationNativeSequence {
        self.sequence
    }
}

impl Display for RegisterMaskedNoOperationNativeSequenceCacheInvariantError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::EntryMissing => {
                "located exact no-operation sequence is missing"
            },
        })
    }
}

impl<E> RegisterMaskedNoOperationNativeSequenceCacheLoadFailure<E> {
    /// Returns failed candidate cleanup after unsuccessful publication.
    #[must_use]
    pub const fn candidate_cleanup_failure(
        &self,
    ) -> Option<&RegisterMaskedNoOperationNativeSequenceReleaseFailure<E>> {
        match &self.candidate_cleanup_failure {
            Some(failure) => Some(failure),
            None => None,
        }
    }

    /// Returns the first exact FIFO key removed before publication failed.
    #[must_use]
    pub fn evicted_key(
        &self,
    ) -> Option<&RegisterMaskedNoOperationNativeSequenceKey> {
        self.evicted_keys.first()
    }

    /// Returns every exact FIFO key removed before publication failed.
    #[must_use]
    pub fn evicted_keys(
        &self,
    ) -> &[RegisterMaskedNoOperationNativeSequenceKey] {
        &self.evicted_keys
    }

    /// Returns failed oldest-entry cleanup, when eviction could not complete.
    #[must_use]
    pub const fn eviction_failure(
        &self,
    ) -> Option<&RegisterMaskedNoOperationNativeSequenceReleaseFailure<E>> {
        match &self.cause {
            LoadFailureCause::Eviction(failure) => Some(failure),
            LoadFailureCause::Invariant(_) | LoadFailureCause::Load(_) => None,
        }
    }

    /// Consumes this failure and returns every retryable release owner.
    #[must_use]
    pub fn into_release_failures(
        self,
    ) -> RegisterMaskedNoOperationNativeSequenceCacheLoadReleaseFailures<E>
    {
        let eviction = match self.cause {
            LoadFailureCause::Eviction(failure) => Some(*failure),
            LoadFailureCause::Invariant(_) | LoadFailureCause::Load(_) => None,
        };
        RegisterMaskedNoOperationNativeSequenceCacheLoadReleaseFailures {
            candidate: self.candidate_cleanup_failure.map(|failure| *failure),
            eviction,
        }
    }

    /// Returns internal cache-state inconsistency, when detected.
    #[must_use]
    pub const fn invariant_error(
        &self,
    ) -> Option<RegisterMaskedNoOperationNativeSequenceCacheInvariantError>
    {
        match self.cause {
            LoadFailureCause::Invariant(error) => Some(error),
            LoadFailureCause::Eviction(_) | LoadFailureCause::Load(_) => None,
        }
    }

    /// Returns candidate loading failure before cache state changed.
    #[must_use]
    pub const fn load_failure(
        &self,
    ) -> Option<&RegisterMaskedNoOperationNativeSequenceLoadFailure<E>> {
        match &self.cause {
            LoadFailureCause::Load(failure) => Some(failure),
            LoadFailureCause::Eviction(_) | LoadFailureCause::Invariant(_) => {
                None
            },
        }
    }

    /// Returns exact requested ordered identity whose ensure failed.
    #[must_use]
    pub const fn requested_key(
        &self,
    ) -> &RegisterMaskedNoOperationNativeSequenceKey {
        &self.requested_key
    }
}

impl<E: Display> Display
    for RegisterMaskedNoOperationNativeSequenceCacheLoadFailure<E>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str("no-operation v6 sequence cache miss failed: ")?;
        match &self.cause {
            LoadFailureCause::Eviction(error) => {
                write!(f, "eviction: {error}")?;
            },
            LoadFailureCause::Invariant(error) => {
                write!(f, "invariant: {error}")?;
            },
            LoadFailureCause::Load(error) => write!(f, "load: {error}")?,
        }
        if self.candidate_cleanup_failure.is_some() {
            f.write_str("; candidate cleanup also failed")?;
        }
        Ok(())
    }
}

impl<E> RegisterMaskedNoOperationNativeSequenceCacheLoadReleaseFailures<E> {
    /// Returns failed candidate cleanup after unsuccessful publication.
    #[must_use]
    pub const fn candidate_failure(
        &self,
    ) -> Option<&RegisterMaskedNoOperationNativeSequenceReleaseFailure<E>> {
        self.candidate.as_ref()
    }

    /// Returns failed oldest-entry cleanup after unsuccessful eviction.
    #[must_use]
    pub const fn eviction_failure(
        &self,
    ) -> Option<&RegisterMaskedNoOperationNativeSequenceReleaseFailure<E>> {
        self.eviction.as_ref()
    }

    /// Retries every sequence still owned by this failed publication.
    ///
    /// # Errors
    ///
    /// Returns aggregate failure while at least one sequence still owns
    /// mappings.
    pub fn retry<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> RegisterMaskedNoOperationNativeSequenceCacheReleaseResult<E>
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
        retry_cache_release_failures(adapter, failures)
    }
}

impl<E> RegisterMaskedNoOperationNativeSequenceCacheReleaseFailure<E> {
    /// Returns the number of cache entries attempted by this release pass.
    #[must_use]
    pub const fn attempted_entries(&self) -> usize {
        self.attempted_entries
    }

    /// Returns the number of removed entries still retaining mappings.
    #[must_use]
    pub const fn failed_entries(&self) -> usize {
        self.failures.len()
    }

    /// Returns each retained per-sequence cleanup failure.
    #[must_use]
    pub fn failures(
        &self,
    ) -> &[RegisterMaskedNoOperationNativeSequenceReleaseFailure<E>] {
        &self.failures
    }

    /// Returns the number of cache entries fully released by this pass.
    #[must_use]
    pub const fn released_entries(&self) -> usize {
        self.released_entries
    }

    /// Returns the number of individual mappings still retained.
    #[must_use]
    pub fn retained_mappings(&self) -> usize {
        self.failures
            .iter()
            .map(SequenceReleaseFailure::failed_count)
            .fold(0usize, usize::saturating_add)
    }

    /// Retries every removed cache entry that still owns mappings.
    ///
    /// # Errors
    ///
    /// Returns another aggregate failure retaining repeated cleanup failures.
    pub fn retry<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> RegisterMaskedNoOperationNativeSequenceCacheReleaseResult<E>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = E>,
    {
        retry_cache_release_failures(adapter, self.failures)
    }
}

impl<E: Display> Display
    for RegisterMaskedNoOperationNativeSequenceCacheReleaseFailure<E>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "no-operation v6 sequence cache retained {} of {} entries",
            self.failed_entries(),
            self.attempted_entries,
        )
    }
}

impl RegisterMaskedNoOperationNativeSequenceCache {
    /// Returns the maximum number of loaded sequence entries retained.
    #[must_use]
    pub const fn capacity(&self) -> NonZeroUsize {
        self.capacity
    }

    /// Returns whether one exact admitted plan is currently loaded.
    #[must_use]
    pub fn contains_plan(
        &self,
        plan: &RegisterMaskedNoOperationNativeSequencePlan,
    ) -> bool {
        let key = RegisterMaskedNoOperationNativeSequenceKey::from_plan(plan);
        self.position(&key).is_some()
    }

    /// Loads or reuses one exact admitted no-operation sequence.
    ///
    /// A hit performs no adapter work and preserves FIFO age. A miss loads the
    /// complete candidate before releasing the oldest entry when capacity is
    /// full.
    ///
    /// # Errors
    ///
    /// Returns exact load, eviction, candidate-cleanup, or invariant evidence.
    pub fn ensure_plan<'cache, Adapter>(
        &'cache mut self,
        adapter: &mut Adapter,
        plan: &RegisterMaskedNoOperationNativeSequencePlan,
    ) -> RegisterMaskedNoOperationNativeSequenceCacheLoadResult<
        'cache,
        Adapter::Error,
    >
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let key = RegisterMaskedNoOperationNativeSequenceKey::from_plan(plan);
        if self.position(&key).is_some() {
            return self.entry_for_key(
                &key,
                RegisterMaskedNoOperationNativeSequenceCacheDisposition::Hit,
            );
        }
        let sequence = load_register_masked_no_operation_native_sequence(
            plan, adapter,
        )
        .map_err(|failure| {
            Box::new(RegisterMaskedNoOperationNativeSequenceCacheLoadFailure {
                candidate_cleanup_failure: None,
                cause: LoadFailureCause::Load(failure),
                evicted_keys: Vec::new(),
                requested_key: key.clone(),
            })
        })?;
        let disposition =
            self.publish_candidate(adapter, key.clone(), sequence)?;
        self.entry_for_key(&key, disposition)
    }

    fn entry_for_key<'cache, E>(
        &'cache self,
        key: &RegisterMaskedNoOperationNativeSequenceKey,
        disposition: RegisterMaskedNoOperationNativeSequenceCacheDisposition,
    ) -> RegisterMaskedNoOperationNativeSequenceCacheLoadResult<'cache, E> {
        self.entries
            .iter()
            .find(|entry| entry.key == *key)
            .map_or_else(
                || Err(Box::new(cache_invariant_failure(key.clone()))),
                |entry| {
                    Ok(RegisterMaskedNoOperationNativeSequenceCacheEntry {
                        disposition,
                        key: &entry.key,
                        sequence: &entry.sequence,
                    })
                },
            )
    }

    /// Invalidates and releases one exact admitted plan.
    ///
    /// # Errors
    ///
    /// Returns exact retained sequence cleanup ownership when release fails.
    pub fn invalidate_plan<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        plan: &RegisterMaskedNoOperationNativeSequencePlan,
    ) -> RegisterMaskedNoOperationNativeSequenceCacheInvalidationResult<
        Adapter::Error,
    >
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let key = RegisterMaskedNoOperationNativeSequenceKey::from_plan(plan);
        let Some(index) = self.position(&key) else {
            return Ok(false);
        };
        let Some(entry) = self.entries.remove(index) else {
            return Ok(false);
        };
        entry.sequence.release(adapter).map(|()| true)
    }

    /// Returns whether no loaded sequence entries remain under cache authority.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    /// Returns exact cached keys in FIFO insertion order.
    pub fn keys(
        &self,
    ) -> impl Iterator<Item = &RegisterMaskedNoOperationNativeSequenceKey> {
        self.entries.iter().map(|entry| &entry.key)
    }

    /// Returns the number of loaded sequence entries.
    #[must_use]
    pub fn len(&self) -> usize {
        self.entries.len()
    }

    /// Constructs one empty cache with a positive entry limit.
    #[must_use]
    pub const fn new(capacity: NonZeroUsize) -> Self {
        Self {
            capacity,
            entries: VecDeque::new(),
        }
    }

    fn position(
        &self,
        key: &RegisterMaskedNoOperationNativeSequenceKey,
    ) -> Option<usize> {
        self.entries.iter().position(|entry| entry.key == *key)
    }

    fn publish_candidate<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        key: RegisterMaskedNoOperationNativeSequenceKey,
        sequence: LoadedRegisterMaskedNoOperationNativeSequence,
    ) -> CachePublicationResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let mut evicted = Vec::new();
        if self.entries.len() >= self.capacity.get()
            && let Some(victim) = self.entries.pop_front()
        {
            evicted.push(victim.key);
            if let Err(eviction_failure) = victim.sequence.release(adapter) {
                let candidate_cleanup_failure = sequence.release(adapter).err();
                return Err(Box::new(
                    RegisterMaskedNoOperationNativeSequenceCacheLoadFailure {
                        candidate_cleanup_failure,
                        cause: LoadFailureCause::Eviction(eviction_failure),
                        evicted_keys: evicted,
                        requested_key: key,
                    },
                ));
            }
        }
        self.entries.push_back(CacheValue { key, sequence });
        Ok(
            RegisterMaskedNoOperationNativeSequenceCacheDisposition::Inserted {
                evicted,
            },
        )
    }

    /// Removes and releases every loaded sequence in FIFO insertion order.
    ///
    /// # Errors
    ///
    /// Returns aggregate retained cleanup ownership after attempting all
    /// entries.
    pub fn release_all<Adapter>(
        &mut self,
        adapter: &mut Adapter,
    ) -> CacheReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let entries = self.entries.drain(..).collect::<Vec<_>>();
        release_cache_values(adapter, entries)
    }
}

const fn cache_invariant_failure<E>(
    requested_key: RegisterMaskedNoOperationNativeSequenceKey,
) -> RegisterMaskedNoOperationNativeSequenceCacheLoadFailure<E> {
    RegisterMaskedNoOperationNativeSequenceCacheLoadFailure {
        candidate_cleanup_failure: None,
        cause: LoadFailureCause::Invariant(
            RegisterMaskedNoOperationNativeSequenceCacheInvariantError::
                EntryMissing,
        ),
        evicted_keys: Vec::new(),
        requested_key,
    }
}

fn cache_release_result<E>(
    attempted_entries: usize,
    released_entries: usize,
    failures: Vec<RegisterMaskedNoOperationNativeSequenceReleaseFailure<E>>,
) -> RegisterMaskedNoOperationNativeSequenceCacheReleaseResult<E> {
    if failures.is_empty() {
        Ok(())
    } else {
        Err(Box::new(
            RegisterMaskedNoOperationNativeSequenceCacheReleaseFailure {
                attempted_entries,
                failures,
                released_entries,
            },
        ))
    }
}

fn release_cache_values<Adapter>(
    adapter: &mut Adapter,
    entries: Vec<CacheValue>,
) -> CacheReleaseResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let attempted_entries = entries.len();
    let mut failures = Vec::new();
    let mut released_entries = 0usize;
    for entry in entries {
        match entry.sequence.release(adapter) {
            Ok(()) => released_entries = released_entries.saturating_add(1),
            Err(failure) => failures.push(*failure),
        }
    }
    cache_release_result(attempted_entries, released_entries, failures)
}

fn retry_cache_release_failures<Adapter>(
    adapter: &mut Adapter,
    pending: Vec<
        RegisterMaskedNoOperationNativeSequenceReleaseFailure<Adapter::Error>,
    >,
) -> CacheReleaseResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let attempted_entries = pending.len();
    let mut failures = Vec::new();
    let mut released_entries = 0usize;
    for failure in pending {
        match failure.retry(adapter) {
            Ok(()) => released_entries = released_entries.saturating_add(1),
            Err(retry_failure) => failures.push(*retry_failure),
        }
    }
    cache_release_result(attempted_entries, released_entries, failures)
}
