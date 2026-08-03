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
//   - Bounded process-local reuse and deterministic FIFO eviction of loaded
//   - executable sequences.
// - Must-Not:
//   - Invoke code, share mappings concurrently, or hide failed release
//     ownership.
// - Allows:
//   - Inputs: exact cached or uncached verified sequence plans and one adapter.
//   - Outputs: borrowed cache hits/inserts or explicit load/eviction failures.
//   - Side effects: executable loads and releases through the supplied adapter.
// - Split-When:
//   - Concurrent leases or cross-process executable stores gain ownership.
// - Merge-When:
//   - One platform owner subsumes executable loading, reuse, and eviction.
// - Summary:
//   - Reuses exact loaded chains under a caller-selected positive capacity.
// - Description:
//   - Hits preserve FIFO age; misses publish only after load and eviction
//     succeed.
// - Usage:
//   - Ensure a plan, execute the borrowed ready sequence, then invalidate or
//     clear.
// - Defaults:
//   - Eviction removes the oldest insertion and never refreshes on a hit.
//

//! Bounded exact-plan cache for loaded executable sequences.

use std::collections::VecDeque;
use std::fmt::{Display, Formatter, Result as FormatResult};
use std::num::NonZeroUsize;

use super::direct::{
    CachedVerifiedDirectSequencePlan, VerifiedDirectSequencePlan,
};
use super::executable_sequence::{
    NativeExecutableSequenceLoadFailure, NativeExecutableSequenceLoadResult,
    NativeExecutableSequenceReleaseFailure, ReadyNativeExecutableSequence,
    load_cached_verified_native_sequence, load_verified_native_sequence,
    release_native_executable_sequence,
};
use super::platform::NativeExecutableMemoryAdapter;
use crate::execution_cache::NativeArtifactKey;

/// Exact ordered identity for one loaded direct-native sequence.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeExecutableSequenceKey {
    artifact_keys: Vec<NativeArtifactKey>,
}

/// Whether ensuring one loaded sequence reused or inserted cache state.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeExecutableSequenceCacheDisposition {
    /// Complete sequence identity already existed; FIFO age was unchanged.
    Hit,
    /// A newly loaded sequence entered the cache.
    Inserted {
        /// Exact oldest sequence removed to make capacity, when applicable.
        evicted: Option<NativeExecutableSequenceKey>,
    },
}

#[derive(Debug, Eq, PartialEq)]
struct NativeExecutableSequenceCacheValue {
    key: NativeExecutableSequenceKey,
    sequence: ReadyNativeExecutableSequence,
}

/// Caller-owned positive-capacity FIFO cache of loaded executable sequences.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeExecutableSequenceCache {
    capacity: NonZeroUsize,
    entries: VecDeque<NativeExecutableSequenceCacheValue>,
}

/// Borrowed cache result retaining exact disposition and loaded sequence.
#[derive(Debug)]
pub struct NativeExecutableSequenceCacheEntry<'cache> {
    disposition: NativeExecutableSequenceCacheDisposition,
    key: &'cache NativeExecutableSequenceKey,
    sequence: &'cache ReadyNativeExecutableSequence,
}

/// Internal cache-state inconsistency rejected before exposing a borrow.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeExecutableSequenceCacheInvariantError {
    /// A previously located or published exact key could not be borrowed.
    EntryMissing,
}

#[derive(Debug, Eq, PartialEq)]
enum NativeExecutableSequenceCacheLoadFailureCause<E> {
    Eviction(Box<NativeExecutableSequenceReleaseFailure<E>>),
    Invariant(NativeExecutableSequenceCacheInvariantError),
    Load(Box<NativeExecutableSequenceLoadFailure<E>>),
}

/// Failed releases retained by one unsuccessful cache publication.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeExecutableSequenceCacheLoadReleaseFailures<E> {
    candidate: Option<NativeExecutableSequenceReleaseFailure<E>>,
    eviction: Option<NativeExecutableSequenceReleaseFailure<E>>,
}

/// Failure while loading or publishing one exact sequence cache miss.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeExecutableSequenceCacheLoadFailure<E> {
    candidate_cleanup_failure:
        Option<Box<NativeExecutableSequenceReleaseFailure<E>>>,
    cause: NativeExecutableSequenceCacheLoadFailureCause<E>,
    evicted_key: Option<NativeExecutableSequenceKey>,
    requested_key: NativeExecutableSequenceKey,
}

/// Aggregate failure while releasing all entries removed from one cache.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeExecutableSequenceCacheReleaseFailure<E> {
    attempted_entries: usize,
    failures: Vec<NativeExecutableSequenceReleaseFailure<E>>,
    released_entries: usize,
}

/// Result of invalidating and releasing one exact loaded sequence entry.
pub type NativeExecutableSequenceCacheInvalidationResult<E> =
    Result<bool, Box<NativeExecutableSequenceReleaseFailure<E>>>;

/// Result of ensuring one exact loaded sequence inside a cache.
pub type NativeExecutableSequenceCacheLoadResult<'cache, E> = Result<
    NativeExecutableSequenceCacheEntry<'cache>,
    Box<NativeExecutableSequenceCacheLoadFailure<E>>,
>;

/// Result of releasing every sequence removed from one cache.
pub type NativeExecutableSequenceCacheReleaseResult<E> =
    Result<(), Box<NativeExecutableSequenceCacheReleaseFailure<E>>>;

type NativeExecutableSequenceCacheEvictionResult<E> = Result<
    Option<NativeExecutableSequenceKey>,
    Box<NativeExecutableSequenceCacheLoadFailure<E>>,
>;

type NativeExecutableSequenceCachePublicationResult<E> = Result<
    NativeExecutableSequenceCacheDisposition,
    Box<NativeExecutableSequenceCacheLoadFailure<E>>,
>;

impl NativeExecutableSequenceKey {
    /// Returns every exact artifact key in semantic execution order.
    #[must_use]
    pub fn artifact_keys(&self) -> &[NativeArtifactKey] {
        &self.artifact_keys
    }

    /// Derives exact ordered identity from one cache-aware verified plan.
    #[must_use]
    pub fn from_cached_plan(plan: &CachedVerifiedDirectSequencePlan) -> Self {
        Self {
            artifact_keys: plan
                .artifacts()
                .iter()
                .map(|artifact| artifact.key().clone())
                .collect(),
        }
    }

    /// Derives exact ordered identity from one uncached verified plan.
    #[must_use]
    pub fn from_plan(plan: &VerifiedDirectSequencePlan) -> Self {
        Self {
            artifact_keys: plan
                .artifacts()
                .iter()
                .map(|artifact| artifact.key().clone())
                .collect(),
        }
    }

    /// Returns whether this key contains no artifact positions.
    #[must_use]
    pub const fn is_empty(&self) -> bool {
        self.artifact_keys.is_empty()
    }

    /// Returns the number of artifact positions in this exact sequence key.
    #[must_use]
    pub const fn len(&self) -> usize {
        self.artifact_keys.len()
    }
}

impl NativeExecutableSequenceCacheDisposition {
    /// Returns the exact evicted key for an inserted miss, when applicable.
    #[must_use]
    pub const fn evicted_key(&self) -> Option<&NativeExecutableSequenceKey> {
        match self {
            Self::Hit => None,
            Self::Inserted { evicted } => evicted.as_ref(),
        }
    }

    /// Reports whether this ensure operation reused existing mappings.
    #[must_use]
    pub const fn is_hit(&self) -> bool {
        matches!(self, Self::Hit)
    }
}

impl NativeExecutableSequenceCacheEntry<'_> {
    /// Returns whether this entry was reused or newly inserted.
    #[must_use]
    pub const fn disposition(
        &self,
    ) -> &NativeExecutableSequenceCacheDisposition {
        &self.disposition
    }

    /// Returns the exact ordered identity admitted by this entry.
    #[must_use]
    pub const fn key(&self) -> &NativeExecutableSequenceKey {
        self.key
    }

    /// Returns the ready executable sequence borrowed from the cache.
    #[must_use]
    pub const fn sequence(&self) -> &ReadyNativeExecutableSequence {
        self.sequence
    }
}

impl<E> NativeExecutableSequenceCacheLoadReleaseFailures<E> {
    /// Returns failed candidate cleanup after unsuccessful eviction.
    #[must_use]
    pub const fn candidate_failure(
        &self,
    ) -> Option<&NativeExecutableSequenceReleaseFailure<E>> {
        self.candidate.as_ref()
    }

    /// Returns failed oldest-entry release after unsuccessful eviction.
    #[must_use]
    pub const fn eviction_failure(
        &self,
    ) -> Option<&NativeExecutableSequenceReleaseFailure<E>> {
        self.eviction.as_ref()
    }

    /// Retries every mapping still owned by this failed publication.
    ///
    /// # Errors
    ///
    /// Returns aggregate failure when at least one sequence still owns
    /// mappings.
    pub fn retry<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> NativeExecutableSequenceCacheReleaseResult<E>
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

impl<E> NativeExecutableSequenceCacheLoadFailure<E> {
    /// Returns candidate cleanup failure after eviction publication failed.
    #[must_use]
    pub const fn candidate_cleanup_failure(
        &self,
    ) -> Option<&NativeExecutableSequenceReleaseFailure<E>> {
        match &self.candidate_cleanup_failure {
            Some(failure) => Some(failure),
            None => None,
        }
    }

    /// Returns the exact oldest key removed for attempted eviction.
    #[must_use]
    pub const fn evicted_key(&self) -> Option<&NativeExecutableSequenceKey> {
        self.evicted_key.as_ref()
    }

    /// Returns failed oldest-entry release, when eviction could not complete.
    #[must_use]
    pub const fn eviction_failure(
        &self,
    ) -> Option<&NativeExecutableSequenceReleaseFailure<E>> {
        match &self.cause {
            NativeExecutableSequenceCacheLoadFailureCause::Eviction(
                failure,
            ) => Some(failure),
            NativeExecutableSequenceCacheLoadFailureCause::Invariant(_)
            | NativeExecutableSequenceCacheLoadFailureCause::Load(_) => None,
        }
    }

    /// Consumes this failure and returns every retryable release owner.
    #[must_use]
    pub fn into_release_failures(
        self,
    ) -> NativeExecutableSequenceCacheLoadReleaseFailures<E> {
        let eviction = match self.cause {
            NativeExecutableSequenceCacheLoadFailureCause::Eviction(
                failure,
            ) => Some(*failure),
            NativeExecutableSequenceCacheLoadFailureCause::Invariant(_)
            | NativeExecutableSequenceCacheLoadFailureCause::Load(_) => None,
        };
        NativeExecutableSequenceCacheLoadReleaseFailures {
            candidate: self.candidate_cleanup_failure.map(|failure| *failure),
            eviction,
        }
    }

    /// Returns internal cache-state inconsistency, when detected.
    #[must_use]
    pub const fn invariant_error(
        &self,
    ) -> Option<NativeExecutableSequenceCacheInvariantError> {
        match self.cause {
            NativeExecutableSequenceCacheLoadFailureCause::Eviction(_)
            | NativeExecutableSequenceCacheLoadFailureCause::Load(_) => None,
            NativeExecutableSequenceCacheLoadFailureCause::Invariant(error) => {
                Some(error)
            },
        }
    }

    /// Returns candidate loading failure before cache state changed.
    #[must_use]
    pub const fn load_failure(
        &self,
    ) -> Option<&NativeExecutableSequenceLoadFailure<E>> {
        match &self.cause {
            NativeExecutableSequenceCacheLoadFailureCause::Eviction(_)
            | NativeExecutableSequenceCacheLoadFailureCause::Invariant(_) => {
                None
            },
            NativeExecutableSequenceCacheLoadFailureCause::Load(failure) => {
                Some(failure)
            },
        }
    }

    /// Returns exact requested sequence identity whose ensure operation failed.
    #[must_use]
    pub const fn requested_key(&self) -> &NativeExecutableSequenceKey {
        &self.requested_key
    }
}

impl<E> NativeExecutableSequenceCacheReleaseFailure<E> {
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
    pub fn failures(&self) -> &[NativeExecutableSequenceReleaseFailure<E>] {
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
            .map(NativeExecutableSequenceReleaseFailure::failed_count)
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
    ) -> NativeExecutableSequenceCacheReleaseResult<E>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = E>,
    {
        retry_cache_release_failures(adapter, self.failures)
    }
}

impl Display for NativeExecutableSequenceCacheInvariantError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::EntryMissing => "located exact entry is missing",
        })
    }
}

impl<E: Display> Display for NativeExecutableSequenceCacheLoadFailure<E> {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str("native executable sequence cache miss failed: ")?;
        match &self.cause {
            NativeExecutableSequenceCacheLoadFailureCause::Eviction(error) => {
                write!(f, "eviction: {error}")?;
            },
            NativeExecutableSequenceCacheLoadFailureCause::Invariant(error) => {
                write!(f, "invariant: {error}")?;
            },
            NativeExecutableSequenceCacheLoadFailureCause::Load(error) => {
                write!(f, "load: {error}")?;
            },
        }
        if self.candidate_cleanup_failure.is_some() {
            f.write_str("; candidate cleanup also failed")?;
        }
        Ok(())
    }
}

impl<E: Display> Display for NativeExecutableSequenceCacheReleaseFailure<E> {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "native executable sequence cache retained {} of {} entries",
            self.failed_entries(),
            self.attempted_entries
        )
    }
}

impl NativeExecutableSequenceCache {
    /// Returns the maximum number of loaded sequence entries retained.
    #[must_use]
    pub const fn capacity(&self) -> NonZeroUsize {
        self.capacity
    }

    /// Returns whether one exact cache-aware plan is currently loaded.
    #[must_use]
    pub fn contains_cached_plan(
        &self,
        plan: &CachedVerifiedDirectSequencePlan,
    ) -> bool {
        let key = NativeExecutableSequenceKey::from_cached_plan(plan);
        self.contains_key(&key)
    }

    fn contains_key(&self, key: &NativeExecutableSequenceKey) -> bool {
        self.position(key).is_some()
    }

    /// Returns whether one exact uncached plan is currently loaded.
    #[must_use]
    pub fn contains_plan(&self, plan: &VerifiedDirectSequencePlan) -> bool {
        let key = NativeExecutableSequenceKey::from_plan(plan);
        self.contains_key(&key)
    }

    /// Loads or reuses one exact cache-aware verified sequence.
    ///
    /// A hit performs no memory-adapter operation and preserves FIFO age. A
    /// miss loads the candidate before attempting oldest-entry eviction.
    ///
    /// # Errors
    ///
    /// Returns [`NativeExecutableSequenceCacheLoadFailure`] when candidate load
    /// or required eviction release fails.
    pub fn ensure_cached_plan<'cache, Adapter>(
        &'cache mut self,
        memory_adapter: &mut Adapter,
        plan: &CachedVerifiedDirectSequencePlan,
    ) -> NativeExecutableSequenceCacheLoadResult<'cache, Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let key = NativeExecutableSequenceKey::from_cached_plan(plan);
        self.ensure_with(memory_adapter, &key, |loader| {
            load_cached_verified_native_sequence(loader, plan)
        })
    }

    /// Loads or reuses one exact uncached verified sequence.
    ///
    /// A hit performs no memory-adapter operation and preserves FIFO age. A
    /// miss loads the candidate before attempting oldest-entry eviction.
    ///
    /// # Errors
    ///
    /// Returns [`NativeExecutableSequenceCacheLoadFailure`] when candidate load
    /// or required eviction release fails.
    pub fn ensure_plan<'cache, Adapter>(
        &'cache mut self,
        memory_adapter: &mut Adapter,
        plan: &VerifiedDirectSequencePlan,
    ) -> NativeExecutableSequenceCacheLoadResult<'cache, Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let key = NativeExecutableSequenceKey::from_plan(plan);
        self.ensure_with(memory_adapter, &key, |loader| {
            load_verified_native_sequence(loader, plan)
        })
    }

    fn ensure_with<'cache, Adapter, Load>(
        &'cache mut self,
        memory_adapter: &mut Adapter,
        key: &NativeExecutableSequenceKey,
        load: Load,
    ) -> NativeExecutableSequenceCacheLoadResult<'cache, Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
        Load: FnOnce(
            &mut Adapter,
        )
            -> NativeExecutableSequenceLoadResult<Adapter::Error>,
    {
        if self.contains_key(key) {
            return self.entry_for_key(
                key,
                NativeExecutableSequenceCacheDisposition::Hit,
            );
        }
        let candidate = load(memory_adapter).map_err(|failure| {
            Box::new(NativeExecutableSequenceCacheLoadFailure {
                candidate_cleanup_failure: None,
                cause: NativeExecutableSequenceCacheLoadFailureCause::Load(
                    failure,
                ),
                evicted_key: None,
                requested_key: key.clone(),
            })
        })?;
        let disposition =
            self.publish_candidate(memory_adapter, key.clone(), candidate)?;
        self.entry_for_key(key, disposition)
    }

    fn entry_for_key<'cache, E>(
        &'cache self,
        key: &NativeExecutableSequenceKey,
        disposition: NativeExecutableSequenceCacheDisposition,
    ) -> NativeExecutableSequenceCacheLoadResult<'cache, E> {
        self.entries
            .iter()
            .find(|entry| entry.key == *key)
            .map_or_else(
                || Err(Box::new(cache_invariant_failure(key.clone()))),
                |entry| {
                    Ok(NativeExecutableSequenceCacheEntry {
                        disposition,
                        key: &entry.key,
                        sequence: &entry.sequence,
                    })
                },
            )
    }

    fn evict_oldest<Adapter>(
        &mut self,
        memory_adapter: &mut Adapter,
        requested_key: &NativeExecutableSequenceKey,
        candidate: ReadyNativeExecutableSequence,
    ) -> NativeExecutableSequenceCacheEvictionResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let Some(victim) = self.entries.pop_front() else {
            self.entries.push_back(NativeExecutableSequenceCacheValue {
                key: requested_key.clone(),
                sequence: candidate,
            });
            return Ok(None);
        };
        let evicted_key = victim.key;
        match release_native_executable_sequence(
            memory_adapter,
            victim.sequence,
        ) {
            Ok(()) => {
                self.entries.push_back(NativeExecutableSequenceCacheValue {
                    key: requested_key.clone(),
                    sequence: candidate,
                });
                Ok(Some(evicted_key))
            },
            Err(eviction_failure) => {
                let candidate_cleanup_failure =
                    release_native_executable_sequence(
                        memory_adapter,
                        candidate,
                    )
                    .err();
                Err(Box::new(NativeExecutableSequenceCacheLoadFailure {
                    candidate_cleanup_failure,
                    cause:
                        NativeExecutableSequenceCacheLoadFailureCause::Eviction(
                            eviction_failure,
                        ),
                    evicted_key: Some(evicted_key),
                    requested_key: requested_key.clone(),
                }))
            },
        }
    }

    /// Invalidates and releases one exact cache-aware verified sequence.
    ///
    /// # Errors
    ///
    /// Returns exact release ownership when cleanup fails.
    pub fn invalidate_cached_plan<Adapter>(
        &mut self,
        memory_adapter: &mut Adapter,
        plan: &CachedVerifiedDirectSequencePlan,
    ) -> NativeExecutableSequenceCacheInvalidationResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let key = NativeExecutableSequenceKey::from_cached_plan(plan);
        self.invalidate_key(memory_adapter, &key)
    }

    fn invalidate_key<Adapter>(
        &mut self,
        memory_adapter: &mut Adapter,
        key: &NativeExecutableSequenceKey,
    ) -> NativeExecutableSequenceCacheInvalidationResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let Some(index) = self.position(key) else {
            return Ok(false);
        };
        let Some(entry) = self.entries.remove(index) else {
            return Ok(false);
        };
        release_native_executable_sequence(memory_adapter, entry.sequence)
            .map(|()| true)
    }

    /// Invalidates and releases one exact uncached verified sequence.
    ///
    /// # Errors
    ///
    /// Returns exact release ownership when cleanup fails.
    pub fn invalidate_plan<Adapter>(
        &mut self,
        memory_adapter: &mut Adapter,
        plan: &VerifiedDirectSequencePlan,
    ) -> NativeExecutableSequenceCacheInvalidationResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let key = NativeExecutableSequenceKey::from_plan(plan);
        self.invalidate_key(memory_adapter, &key)
    }

    /// Returns whether no loaded executable sequences are retained.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    /// Returns exact cached sequence keys in FIFO insertion order.
    pub fn keys(&self) -> impl Iterator<Item = &NativeExecutableSequenceKey> {
        self.entries.iter().map(|entry| &entry.key)
    }

    /// Returns the number of loaded executable sequence entries.
    #[must_use]
    pub fn len(&self) -> usize {
        self.entries.len()
    }

    /// Constructs one empty caller-owned cache with positive entry capacity.
    #[must_use]
    pub const fn new(capacity: NonZeroUsize) -> Self {
        Self {
            capacity,
            entries: VecDeque::new(),
        }
    }

    fn position(&self, key: &NativeExecutableSequenceKey) -> Option<usize> {
        self.entries.iter().position(|entry| entry.key == *key)
    }

    fn publish_candidate<Adapter>(
        &mut self,
        memory_adapter: &mut Adapter,
        key: NativeExecutableSequenceKey,
        candidate: ReadyNativeExecutableSequence,
    ) -> NativeExecutableSequenceCachePublicationResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let evicted = if self.entries.len() == self.capacity.get() {
            self.evict_oldest(memory_adapter, &key, candidate)?
        } else {
            self.entries.push_back(NativeExecutableSequenceCacheValue {
                key,
                sequence: candidate,
            });
            None
        };
        Ok(NativeExecutableSequenceCacheDisposition::Inserted { evicted })
    }

    /// Removes and releases every loaded sequence in FIFO insertion order.
    ///
    /// # Errors
    ///
    /// Returns aggregate retained cleanup ownership after attempting all
    /// entries.
    pub fn release_all<Adapter>(
        &mut self,
        memory_adapter: &mut Adapter,
    ) -> NativeExecutableSequenceCacheReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let entries = self.entries.drain(..).collect::<Vec<_>>();
        release_cache_values(memory_adapter, entries)
    }
}

const fn cache_invariant_failure<E>(
    requested_key: NativeExecutableSequenceKey,
) -> NativeExecutableSequenceCacheLoadFailure<E> {
    NativeExecutableSequenceCacheLoadFailure {
        candidate_cleanup_failure: None,
        cause: NativeExecutableSequenceCacheLoadFailureCause::Invariant(
            NativeExecutableSequenceCacheInvariantError::EntryMissing,
        ),
        evicted_key: None,
        requested_key,
    }
}

fn cache_release_result<E>(
    attempted_entries: usize,
    released_entries: usize,
    failures: Vec<NativeExecutableSequenceReleaseFailure<E>>,
) -> NativeExecutableSequenceCacheReleaseResult<E> {
    if failures.is_empty() {
        Ok(())
    } else {
        Err(Box::new(NativeExecutableSequenceCacheReleaseFailure {
            attempted_entries,
            failures,
            released_entries,
        }))
    }
}

fn release_cache_values<Adapter>(
    memory_adapter: &mut Adapter,
    entries: Vec<NativeExecutableSequenceCacheValue>,
) -> NativeExecutableSequenceCacheReleaseResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let attempted_entries = entries.len();
    let mut failures = Vec::new();
    let mut released_entries = 0usize;
    for entry in entries {
        match release_native_executable_sequence(memory_adapter, entry.sequence)
        {
            Ok(()) => {
                released_entries = released_entries.saturating_add(1);
            },
            Err(failure) => failures.push(*failure),
        }
    }
    cache_release_result(attempted_entries, released_entries, failures)
}

fn retry_cache_release_failures<Adapter>(
    memory_adapter: &mut Adapter,
    pending: Vec<NativeExecutableSequenceReleaseFailure<Adapter::Error>>,
) -> NativeExecutableSequenceCacheReleaseResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let attempted_entries = pending.len();
    let mut failures = Vec::new();
    let mut released_entries = 0usize;
    for failure in pending {
        match failure.retry(memory_adapter) {
            Ok(()) => {
                released_entries = released_entries.saturating_add(1);
            },
            Err(retry_failure) => failures.push(*retry_failure),
        }
    }
    cache_release_result(attempted_entries, released_entries, failures)
}
