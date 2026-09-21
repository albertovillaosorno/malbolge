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
//   - Weighted FIFO residency for loaded Crazy v6 sequences.
// - Must-Not:
//   - Execute native code, refresh FIFO age on hits, or share borrowed entries
//     concurrently across cache mutation or external lease ownership.
// - Allows:
//   - Inputs: admitted plans, weighted limits, and one memory adapter.
//   - Outputs: borrowed exact hits/inserts plus explicit eviction/load
//     failures.
//   - Side effects: sequence load/release only through the supplied adapter.
// - Split-When:
//   - Live external leases or asynchronous cleanup gain authority.
// - Merge-When:
//   - One reviewed Crazy sequence store subsumes cache and lease policy.
// - Summary:
//   - Reuses exact loaded Crazy chains under weighted FIFO limits.
// - Description:
//   - Hits perform no adapter work; admission and limit changes release oldest
//     entries before publishing weighted authority.
// - Usage:
//   - Ensure an admitted plan, execute the borrowed loaded sequence, then
//     invalidate or release all explicitly.
// - Defaults:
//   - Entry limits are required; mapping and mapped-byte limits are optional.
//

//! Weighted FIFO cache for loaded Crazy register-masked v6 sequences.

#[path = "register_masked_crazy_sequence_cache/reconfiguration.rs"]
mod reconfiguration;

use std::collections::VecDeque;
use std::fmt::{Display, Formatter, Result as FormatResult};
use std::num::NonZeroUsize;

pub use reconfiguration::{
    RegisterMaskedCrazyNativeSequenceCacheReconfiguration,
    RegisterMaskedCrazyNativeSequenceCacheReconfigurationFailure,
    RegisterMaskedCrazyNativeSequenceCacheReconfigurationResult,
};

use super::executable_cache_capacity::{
    NativeExecutableSequenceCacheCapacityError,
    NativeExecutableSequenceCacheLimits, NativeExecutableSequenceCacheUsage,
    NativeExecutableSequenceWeight,
};
use super::platform::NativeExecutableMemoryAdapter;
use super::register_masked_crazy_loaded_sequence::{
    LoadedRegisterMaskedCrazyNativeSequence,
    RegisterMaskedCrazyNativeSequenceLoadFailure,
    RegisterMaskedCrazyNativeSequenceReleaseFailure,
    load_register_masked_crazy_native_sequence,
};
use super::register_masked_crazy_sequence::{
    RegisterMaskedCrazyNativeSequenceKey, RegisterMaskedCrazyNativeSequencePlan,
};

#[derive(Debug)]
struct CacheValue {
    key: RegisterMaskedCrazyNativeSequenceKey,
    sequence: LoadedRegisterMaskedCrazyNativeSequence,
    weight: NativeExecutableSequenceWeight,
}

#[derive(Debug)]
struct CacheCandidate {
    key: RegisterMaskedCrazyNativeSequenceKey,
    sequence: LoadedRegisterMaskedCrazyNativeSequence,
    weight: NativeExecutableSequenceWeight,
}

#[derive(Debug)]
struct CacheCapacityFailureContext {
    error: NativeExecutableSequenceCacheCapacityError,
    evicted_keys: Vec<RegisterMaskedCrazyNativeSequenceKey>,
    key: RegisterMaskedCrazyNativeSequenceKey,
    sequence: LoadedRegisterMaskedCrazyNativeSequence,
}

#[derive(Debug)]
enum LoadFailureCause<E> {
    Capacity(NativeExecutableSequenceCacheCapacityError),
    Eviction(Box<RegisterMaskedCrazyNativeSequenceReleaseFailure<E>>),
    Invariant(RegisterMaskedCrazyNativeSequenceCacheInvariantError),
    Load(Box<RegisterMaskedCrazyNativeSequenceLoadFailure<E>>),
}

/// Caller-owned exact-plan cache with one positive FIFO entry limit.
#[derive(Debug)]
pub struct RegisterMaskedCrazyNativeSequenceCache {
    entries: VecDeque<CacheValue>,
    limits: NativeExecutableSequenceCacheLimits,
    usage: NativeExecutableSequenceCacheUsage,
}

/// Whether ensuring one plan reused or inserted loaded cache state.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum RegisterMaskedCrazyNativeSequenceCacheDisposition {
    /// Exact ordered identity already existed; FIFO age was unchanged.
    Hit,
    /// A fully loaded miss entered the cache.
    Inserted {
        /// Exact oldest keys released before the candidate was published.
        evicted: Vec<RegisterMaskedCrazyNativeSequenceKey>,
    },
}

/// Borrowed cache result retaining exact disposition and loaded sequence.
#[derive(Debug)]
pub struct RegisterMaskedCrazyNativeSequenceCacheEntry<'cache> {
    disposition: RegisterMaskedCrazyNativeSequenceCacheDisposition,
    key: &'cache RegisterMaskedCrazyNativeSequenceKey,
    sequence: &'cache LoadedRegisterMaskedCrazyNativeSequence,
}

/// Internal cache inconsistency rejected before exposing a borrow.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RegisterMaskedCrazyNativeSequenceCacheInvariantError {
    /// A just-located or just-published exact key could not be borrowed.
    EntryMissing,
}

/// Failed releases retained by one unsuccessful cache publication.
#[derive(Debug)]
pub struct RegisterMaskedCrazyNativeSequenceCacheLoadReleaseFailures<E> {
    candidate: Option<RegisterMaskedCrazyNativeSequenceReleaseFailure<E>>,
    eviction: Option<RegisterMaskedCrazyNativeSequenceReleaseFailure<E>>,
}

/// Failure while loading, evicting, or publishing one exact cache miss.
#[derive(Debug)]
pub struct RegisterMaskedCrazyNativeSequenceCacheLoadFailure<E> {
    candidate_cleanup_failure:
        Option<Box<RegisterMaskedCrazyNativeSequenceReleaseFailure<E>>>,
    cause: LoadFailureCause<E>,
    evicted_keys: Vec<RegisterMaskedCrazyNativeSequenceKey>,
    requested_key: RegisterMaskedCrazyNativeSequenceKey,
}

/// Aggregate cleanup failure after removing cache-owned sequence entries.
#[derive(Debug)]
pub struct RegisterMaskedCrazyNativeSequenceCacheReleaseFailure<E> {
    attempted_entries: usize,
    failures: Vec<RegisterMaskedCrazyNativeSequenceReleaseFailure<E>>,
    released_entries: usize,
}

type CapacityError = NativeExecutableSequenceCacheCapacityError;
type CacheInvalidationResult<E> =
    RegisterMaskedCrazyNativeSequenceCacheInvalidationResult<E>;
type CacheLoadResult<'cache, E> =
    RegisterMaskedCrazyNativeSequenceCacheLoadResult<'cache, E>;
type CacheReleaseResult<E> =
    RegisterMaskedCrazyNativeSequenceCacheReleaseResult<E>;
type CacheReconfigurationResult<E> =
    RegisterMaskedCrazyNativeSequenceCacheReconfigurationResult<E>;

type CachePublicationResult<E> = Result<
    RegisterMaskedCrazyNativeSequenceCacheDisposition,
    Box<RegisterMaskedCrazyNativeSequenceCacheLoadFailure<E>>,
>;
type CacheFitResult<E> = Result<
    (CacheCandidate, Vec<RegisterMaskedCrazyNativeSequenceKey>),
    Box<RegisterMaskedCrazyNativeSequenceCacheLoadFailure<E>>,
>;
type CachePrepareResult<E> = Result<
    CacheCandidate,
    Box<RegisterMaskedCrazyNativeSequenceCacheLoadFailure<E>>,
>;
type SequenceReleaseFailure<E> =
    RegisterMaskedCrazyNativeSequenceReleaseFailure<E>;

/// Published weighted capacity limits for this Crazy sequence cache.
pub type RegisterMaskedCrazyNativeSequenceCacheLimits =
    NativeExecutableSequenceCacheLimits;

/// Exact resources retained by this Crazy sequence cache.
pub type RegisterMaskedCrazyNativeSequenceCacheUsage =
    NativeExecutableSequenceCacheUsage;

/// Capacity rejection produced by this Crazy sequence cache.
pub type RegisterMaskedCrazyNativeSequenceCacheCapacityError =
    NativeExecutableSequenceCacheCapacityError;

/// Result of loading or reusing one exact Crazy sequence plan.
pub type RegisterMaskedCrazyNativeSequenceCacheLoadResult<'cache, E> = Result<
    RegisterMaskedCrazyNativeSequenceCacheEntry<'cache>,
    Box<RegisterMaskedCrazyNativeSequenceCacheLoadFailure<E>>,
>;

/// Result of invalidating one exact loaded Crazy sequence.
pub type RegisterMaskedCrazyNativeSequenceCacheInvalidationResult<E> =
    Result<bool, Box<RegisterMaskedCrazyNativeSequenceReleaseFailure<E>>>;

/// Result of releasing every sequence removed from cache authority.
pub type RegisterMaskedCrazyNativeSequenceCacheReleaseResult<E> =
    Result<(), Box<RegisterMaskedCrazyNativeSequenceCacheReleaseFailure<E>>>;

impl RegisterMaskedCrazyNativeSequenceCacheDisposition {
    /// Returns the first exact FIFO key evicted for an inserted miss.
    #[must_use]
    pub fn evicted_key(&self) -> Option<&RegisterMaskedCrazyNativeSequenceKey> {
        self.evicted_keys().first()
    }

    /// Returns every exact FIFO key evicted to admit this acquisition.
    #[must_use]
    pub fn evicted_keys(&self) -> &[RegisterMaskedCrazyNativeSequenceKey] {
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

impl RegisterMaskedCrazyNativeSequenceCacheEntry<'_> {
    /// Returns exact hit/insert evidence for this borrowed entry.
    #[must_use]
    pub const fn disposition(
        &self,
    ) -> &RegisterMaskedCrazyNativeSequenceCacheDisposition {
        &self.disposition
    }

    /// Returns exact ordered identity retained by this cache entry.
    #[must_use]
    pub const fn key(&self) -> &RegisterMaskedCrazyNativeSequenceKey {
        self.key
    }

    /// Returns the loaded sequence borrowed from cache authority.
    #[must_use]
    pub const fn sequence(&self) -> &LoadedRegisterMaskedCrazyNativeSequence {
        self.sequence
    }
}

impl Display for RegisterMaskedCrazyNativeSequenceCacheInvariantError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::EntryMissing => "located exact Crazy sequence is missing",
        })
    }
}

impl<E> RegisterMaskedCrazyNativeSequenceCacheLoadFailure<E> {
    /// Returns failed candidate cleanup after unsuccessful publication.
    #[must_use]
    pub const fn candidate_cleanup_failure(
        &self,
    ) -> Option<&RegisterMaskedCrazyNativeSequenceReleaseFailure<E>> {
        match &self.candidate_cleanup_failure {
            Some(failure) => Some(failure),
            None => None,
        }
    }

    /// Returns weighted capacity rejection, when the candidate cannot fit.
    #[must_use]
    pub const fn capacity_error(
        &self,
    ) -> Option<RegisterMaskedCrazyNativeSequenceCacheCapacityError> {
        match self.cause {
            LoadFailureCause::Capacity(error) => Some(error),
            LoadFailureCause::Eviction(_)
            | LoadFailureCause::Invariant(_)
            | LoadFailureCause::Load(_) => None,
        }
    }

    /// Returns the first exact FIFO key removed before publication failed.
    #[must_use]
    pub fn evicted_key(&self) -> Option<&RegisterMaskedCrazyNativeSequenceKey> {
        self.evicted_keys.first()
    }

    /// Returns every exact FIFO key removed before publication failed.
    #[must_use]
    pub fn evicted_keys(&self) -> &[RegisterMaskedCrazyNativeSequenceKey] {
        &self.evicted_keys
    }

    /// Returns failed oldest-entry cleanup, when eviction could not complete.
    #[must_use]
    pub const fn eviction_failure(
        &self,
    ) -> Option<&RegisterMaskedCrazyNativeSequenceReleaseFailure<E>> {
        match &self.cause {
            LoadFailureCause::Eviction(failure) => Some(failure),
            LoadFailureCause::Capacity(_)
            | LoadFailureCause::Invariant(_)
            | LoadFailureCause::Load(_) => None,
        }
    }

    /// Consumes this failure and returns every retryable release owner.
    #[must_use]
    pub fn into_release_failures(
        self,
    ) -> RegisterMaskedCrazyNativeSequenceCacheLoadReleaseFailures<E> {
        let eviction = match self.cause {
            LoadFailureCause::Eviction(failure) => Some(*failure),
            LoadFailureCause::Capacity(_)
            | LoadFailureCause::Invariant(_)
            | LoadFailureCause::Load(_) => None,
        };
        RegisterMaskedCrazyNativeSequenceCacheLoadReleaseFailures {
            candidate: self.candidate_cleanup_failure.map(|failure| *failure),
            eviction,
        }
    }

    /// Returns internal cache-state inconsistency, when detected.
    #[must_use]
    pub const fn invariant_error(
        &self,
    ) -> Option<RegisterMaskedCrazyNativeSequenceCacheInvariantError> {
        match self.cause {
            LoadFailureCause::Invariant(error) => Some(error),
            LoadFailureCause::Capacity(_)
            | LoadFailureCause::Eviction(_)
            | LoadFailureCause::Load(_) => None,
        }
    }

    /// Returns candidate loading failure before cache state changed.
    #[must_use]
    pub const fn load_failure(
        &self,
    ) -> Option<&RegisterMaskedCrazyNativeSequenceLoadFailure<E>> {
        match &self.cause {
            LoadFailureCause::Load(failure) => Some(failure),
            LoadFailureCause::Capacity(_)
            | LoadFailureCause::Eviction(_)
            | LoadFailureCause::Invariant(_) => None,
        }
    }

    /// Returns exact requested ordered identity whose ensure failed.
    #[must_use]
    pub const fn requested_key(&self) -> &RegisterMaskedCrazyNativeSequenceKey {
        &self.requested_key
    }
}

impl<E: Display> Display
    for RegisterMaskedCrazyNativeSequenceCacheLoadFailure<E>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str("Crazy v6 sequence cache miss failed: ")?;
        match &self.cause {
            LoadFailureCause::Capacity(error) => {
                write!(f, "capacity: {error}")?;
            },
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

impl<E> RegisterMaskedCrazyNativeSequenceCacheLoadReleaseFailures<E> {
    /// Returns failed candidate cleanup after unsuccessful publication.
    #[must_use]
    pub const fn candidate_failure(
        &self,
    ) -> Option<&RegisterMaskedCrazyNativeSequenceReleaseFailure<E>> {
        self.candidate.as_ref()
    }

    /// Returns failed oldest-entry cleanup after unsuccessful eviction.
    #[must_use]
    pub const fn eviction_failure(
        &self,
    ) -> Option<&RegisterMaskedCrazyNativeSequenceReleaseFailure<E>> {
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
    ) -> RegisterMaskedCrazyNativeSequenceCacheReleaseResult<E>
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

impl<E> RegisterMaskedCrazyNativeSequenceCacheReleaseFailure<E> {
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
    ) -> &[RegisterMaskedCrazyNativeSequenceReleaseFailure<E>] {
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
    ) -> RegisterMaskedCrazyNativeSequenceCacheReleaseResult<E>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = E>,
    {
        retry_cache_release_failures(adapter, self.failures)
    }
}

impl<E: Display> Display
    for RegisterMaskedCrazyNativeSequenceCacheReleaseFailure<E>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "Crazy v6 sequence cache retained {} of {} entries",
            self.failed_entries(),
            self.attempted_entries,
        )
    }
}

impl RegisterMaskedCrazyNativeSequenceCache {
    /// Returns the maximum number of loaded sequence entries retained.
    #[must_use]
    pub const fn capacity(&self) -> NonZeroUsize {
        self.limits.entry_limit()
    }

    /// Returns whether one exact admitted plan is currently loaded.
    #[must_use]
    pub fn contains_plan(
        &self,
        plan: &RegisterMaskedCrazyNativeSequencePlan,
    ) -> bool {
        let key = RegisterMaskedCrazyNativeSequenceKey::from_plan(plan);
        self.position(&key).is_some()
    }

    /// Loads or reuses one exact admitted Crazy sequence.
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
        plan: &RegisterMaskedCrazyNativeSequencePlan,
    ) -> CacheLoadResult<'cache, Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let key = RegisterMaskedCrazyNativeSequenceKey::from_plan(plan);
        if self.position(&key).is_some() {
            return self.entry_for_key(
                &key,
                RegisterMaskedCrazyNativeSequenceCacheDisposition::Hit,
            );
        }
        let sequence = load_register_masked_crazy_native_sequence(
            plan, adapter,
        )
        .map_err(|failure| {
            Box::new(RegisterMaskedCrazyNativeSequenceCacheLoadFailure {
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
        key: &RegisterMaskedCrazyNativeSequenceKey,
        disposition: RegisterMaskedCrazyNativeSequenceCacheDisposition,
    ) -> RegisterMaskedCrazyNativeSequenceCacheLoadResult<'cache, E> {
        self.entries
            .iter()
            .find(|entry| entry.key == *key)
            .map_or_else(
                || Err(Box::new(cache_invariant_failure(key.clone()))),
                |entry| {
                    Ok(RegisterMaskedCrazyNativeSequenceCacheEntry {
                        disposition,
                        key: &entry.key,
                        sequence: &entry.sequence,
                    })
                },
            )
    }

    fn evict_until_fits<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        candidate: CacheCandidate,
    ) -> CacheFitResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let mut evicted = Vec::new();
        while self.limits.projected_exceeds(self.usage, candidate.weight) {
            let Some(victim) = self.entries.pop_front() else {
                let context = CacheCapacityFailureContext {
                    error: CapacityError::WeightOverflow,
                    evicted_keys: evicted,
                    key: candidate.key,
                    sequence: candidate.sequence,
                };
                return Err(Box::new(cache_capacity_failure(adapter, context)));
            };
            self.usage.remove(victim.weight);
            evicted.push(victim.key);
            if let Err(eviction_failure) = victim.sequence.release(adapter) {
                let candidate_cleanup_failure =
                    candidate.sequence.release(adapter).err();
                return Err(Box::new(
                    RegisterMaskedCrazyNativeSequenceCacheLoadFailure {
                        candidate_cleanup_failure,
                        cause: LoadFailureCause::Eviction(eviction_failure),
                        evicted_keys: evicted,
                        requested_key: candidate.key,
                    },
                ));
            }
        }
        Ok((candidate, evicted))
    }

    /// Invalidates and releases one exact admitted plan.
    ///
    /// # Errors
    ///
    /// Returns exact retained sequence cleanup ownership when release fails.
    pub fn invalidate_plan<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        plan: &RegisterMaskedCrazyNativeSequencePlan,
    ) -> CacheInvalidationResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let key = RegisterMaskedCrazyNativeSequenceKey::from_plan(plan);
        let Some(index) = self.position(&key) else {
            return Ok(false);
        };
        let Some(entry) = self.entries.remove(index) else {
            return Ok(false);
        };
        self.usage.remove(entry.weight);
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
    ) -> impl Iterator<Item = &RegisterMaskedCrazyNativeSequenceKey> {
        self.entries.iter().map(|entry| &entry.key)
    }

    /// Returns the number of loaded sequence entries.
    #[must_use]
    pub fn len(&self) -> usize {
        self.entries.len()
    }

    /// Returns every caller-selected weighted capacity limit.
    #[must_use]
    pub const fn limits(&self) -> RegisterMaskedCrazyNativeSequenceCacheLimits {
        self.limits
    }

    /// Constructs one empty cache with a positive entry limit.
    #[must_use]
    pub const fn new(capacity: NonZeroUsize) -> Self {
        Self::with_limits(NativeExecutableSequenceCacheLimits::new(capacity))
    }

    fn position(
        &self,
        key: &RegisterMaskedCrazyNativeSequenceKey,
    ) -> Option<usize> {
        self.entries.iter().position(|entry| entry.key == *key)
    }

    fn publish_candidate<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        key: RegisterMaskedCrazyNativeSequenceKey,
        sequence: LoadedRegisterMaskedCrazyNativeSequence,
    ) -> CachePublicationResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let prepared_candidate =
            prepare_cache_candidate(adapter, self.limits, key, sequence)?;
        let (candidate, evicted) =
            self.evict_until_fits(adapter, prepared_candidate)?;
        if let Err(error) = self.usage.add(candidate.weight) {
            let context = CacheCapacityFailureContext {
                error,
                evicted_keys: evicted,
                key: candidate.key,
                sequence: candidate.sequence,
            };
            return Err(Box::new(cache_capacity_failure(adapter, context)));
        }
        self.entries.push_back(CacheValue {
            key: candidate.key,
            sequence: candidate.sequence,
            weight: candidate.weight,
        });
        Ok(
            RegisterMaskedCrazyNativeSequenceCacheDisposition::Inserted {
                evicted,
            },
        )
    }

    /// Publishes new weighted limits after required FIFO eviction.
    ///
    /// Expansion and already-satisfied requests perform no adapter work. A
    /// shrinking request keeps prior limits published until every required
    /// oldest-entry release succeeds.
    ///
    /// # Errors
    ///
    /// Returns exact failed release or internal invariant ownership.
    pub fn reconfigure_limits<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        requested_limits: RegisterMaskedCrazyNativeSequenceCacheLimits,
    ) -> CacheReconfigurationResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let previous_limits = self.limits;
        let evicted_keys = reconfiguration::evict_for_reconfiguration(
            self,
            adapter,
            requested_limits,
            previous_limits,
        )?;
        self.limits = requested_limits;
        Ok(reconfiguration::published(
            evicted_keys,
            requested_limits,
            previous_limits,
        ))
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
        self.usage.reset();
        release_cache_values(adapter, entries)
    }

    /// Returns exact resources currently retained under cache authority.
    #[must_use]
    pub const fn usage(&self) -> RegisterMaskedCrazyNativeSequenceCacheUsage {
        self.usage
    }

    /// Constructs one empty cache with explicit weighted limits.
    #[must_use]
    pub const fn with_limits(
        limits: RegisterMaskedCrazyNativeSequenceCacheLimits,
    ) -> Self {
        Self {
            entries: VecDeque::new(),
            limits,
            usage: NativeExecutableSequenceCacheUsage::empty(),
        }
    }
}

fn cache_capacity_failure<Adapter>(
    adapter: &mut Adapter,
    context: CacheCapacityFailureContext,
) -> RegisterMaskedCrazyNativeSequenceCacheLoadFailure<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let candidate_cleanup_failure = context.sequence.release(adapter).err();
    RegisterMaskedCrazyNativeSequenceCacheLoadFailure {
        candidate_cleanup_failure,
        cause: LoadFailureCause::Capacity(context.error),
        evicted_keys: context.evicted_keys,
        requested_key: context.key,
    }
}

fn prepare_cache_candidate<Adapter>(
    adapter: &mut Adapter,
    limits: RegisterMaskedCrazyNativeSequenceCacheLimits,
    key: RegisterMaskedCrazyNativeSequenceKey,
    sequence: LoadedRegisterMaskedCrazyNativeSequence,
) -> CachePrepareResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let Some(mapped_bytes) = sequence.mapped_bytes() else {
        let context = CacheCapacityFailureContext {
            error: CapacityError::WeightOverflow,
            evicted_keys: Vec::new(),
            key,
            sequence,
        };
        return Err(Box::new(cache_capacity_failure(adapter, context)));
    };
    let weight = NativeExecutableSequenceWeight::from_parts(
        mapped_bytes,
        sequence.len(),
    );
    if let Some(error) = limits.candidate_error(weight) {
        let context = CacheCapacityFailureContext {
            error,
            evicted_keys: Vec::new(),
            key,
            sequence,
        };
        return Err(Box::new(cache_capacity_failure(adapter, context)));
    }
    Ok(CacheCandidate { key, sequence, weight })
}

const fn cache_invariant_failure<E>(
    requested_key: RegisterMaskedCrazyNativeSequenceKey,
) -> RegisterMaskedCrazyNativeSequenceCacheLoadFailure<E> {
    RegisterMaskedCrazyNativeSequenceCacheLoadFailure {
        candidate_cleanup_failure: None,
        cause: LoadFailureCause::Invariant(
            RegisterMaskedCrazyNativeSequenceCacheInvariantError::EntryMissing,
        ),
        evicted_keys: Vec::new(),
        requested_key,
    }
}

fn cache_release_result<E>(
    attempted_entries: usize,
    released_entries: usize,
    failures: Vec<RegisterMaskedCrazyNativeSequenceReleaseFailure<E>>,
) -> RegisterMaskedCrazyNativeSequenceCacheReleaseResult<E> {
    if failures.is_empty() {
        Ok(())
    } else {
        Err(Box::new(
            RegisterMaskedCrazyNativeSequenceCacheReleaseFailure {
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
        RegisterMaskedCrazyNativeSequenceReleaseFailure<Adapter::Error>,
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
