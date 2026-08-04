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
//   - Shared immutable leases and deferred release for loaded native sequences.
// - Must-Not:
//   - Invoke code, hide resident weight, or release a mapping with live leases.
// - Allows:
//   - Inputs: verified sequence plans, weighted limits, and a memory adapter.
//   - Outputs: cloneable leases, active/retired state, and retryable cleanup.
//   - Side effects: executable loads and explicit releases through the adapter.
// - Split-When:
//   - Durable or cross-process lease ownership gains independent policy.
// - Merge-When:
//   - One executable-store owner subsumes lookup, leasing, and reclamation.
// - Summary:
//   - Keeps leased mappings resident after lookup retirement until
//     reconciliation.
// - Description:
//   - Arc leases are immutable; retired residents keep exact capacity weight.
// - Usage:
//   - Acquire leases, retire or evict keys, drop leases, then reconcile
//     explicitly.
// - Defaults:
//   - Lease clone/drop performs no adapter operation; FIFO age never refreshes.
//

//! Shared lease cache for immutable loaded executable sequences.

#[path = "executable_lease_cache/reconciliation.rs"]
mod reconciliation;

#[path = "executable_lease_cache/reconfiguration.rs"]
mod reconfiguration;

use std::collections::VecDeque;
use std::fmt::{Display, Formatter, Result as FormatResult};
use std::num::NonZeroUsize;
use std::sync::Arc;

pub use reconciliation::{
    NativeExecutableSequenceLeaseCacheEntryReleaseFailure,
    NativeExecutableSequenceLeaseCacheLoadReleaseFailures,
    NativeExecutableSequenceLeaseCacheReconciliation,
    NativeExecutableSequenceLeaseCacheReconciliationResult,
    NativeExecutableSequenceLeaseCacheReleaseFailure,
};
pub use reconfiguration::{
    NativeExecutableSequenceLeaseCacheReconfiguration,
    NativeExecutableSequenceLeaseCacheReconfigurationFailure,
    NativeExecutableSequenceLeaseCacheReconfigurationResult,
};

use super::direct::{
    CachedVerifiedDirectSequencePlan, VerifiedDirectSequencePlan,
};
use super::executable_cache::NativeExecutableSequenceKey;
use super::executable_cache_capacity::{
    NativeExecutableSequenceCacheCapacityError,
    NativeExecutableSequenceCacheLimits, NativeExecutableSequenceCacheUsage,
    NativeExecutableSequenceWeight,
};
use super::executable_sequence::{
    NativeExecutableSequenceLoadFailure, NativeExecutableSequenceLoadResult,
    NativeExecutableSequenceReleaseFailure, ReadyNativeExecutableSequence,
    load_cached_verified_native_sequence, load_verified_native_sequence,
    release_native_executable_sequence,
};
use super::platform::NativeExecutableMemoryAdapter;

#[derive(Debug, Eq, PartialEq)]
struct NativeExecutableSequenceLeaseCacheValue {
    key: NativeExecutableSequenceKey,
    sequence: Arc<ReadyNativeExecutableSequence>,
    weight: NativeExecutableSequenceWeight,
}

#[derive(Debug, Eq, PartialEq)]
struct NativeExecutableSequenceLeaseCacheCandidate {
    key: NativeExecutableSequenceKey,
    sequence: ReadyNativeExecutableSequence,
    weight: NativeExecutableSequenceWeight,
}

#[derive(Debug, Eq, PartialEq)]
enum LeaseCacheVictimOutcome<E> {
    ReleaseFailed {
        failure: Box<NativeExecutableSequenceReleaseFailure<E>>,
        weight: NativeExecutableSequenceWeight,
    },
    Released(NativeExecutableSequenceWeight),
    Retired(NativeExecutableSequenceLeaseCacheValue),
}

#[derive(Debug, Eq, PartialEq)]
struct LeaseCacheFailureContext {
    candidate: NativeExecutableSequenceLeaseCacheCandidate,
    evicted_keys: Vec<NativeExecutableSequenceKey>,
    retired_keys: Vec<NativeExecutableSequenceKey>,
}

/// Caller-owned weighted cache with cloneable immutable executable leases.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeExecutableSequenceLeaseCache {
    active: VecDeque<NativeExecutableSequenceLeaseCacheValue>,
    limits: NativeExecutableSequenceCacheLimits,
    retired: VecDeque<NativeExecutableSequenceLeaseCacheValue>,
    usage: NativeExecutableSequenceCacheUsage,
}

/// Cloneable immutable ownership of one resident executable sequence.
#[derive(Clone, Debug)]
pub struct NativeExecutableSequenceLease {
    key: NativeExecutableSequenceKey,
    sequence: Arc<ReadyNativeExecutableSequence>,
}

/// Whether one acquisition reused or inserted active lookup state.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeExecutableSequenceLeaseCacheDisposition {
    /// Exact active identity already existed and FIFO age was unchanged.
    Hit,
    /// A new active identity was published after weighted FIFO processing.
    Inserted {
        /// Every key removed from active lookup in FIFO order.
        evicted: Vec<NativeExecutableSequenceKey>,
        /// Removed keys whose mappings remain resident behind live leases.
        retired: Vec<NativeExecutableSequenceKey>,
    },
}

/// Lease plus exact lookup/eviction evidence for one acquisition.
#[derive(Debug)]
pub struct NativeExecutableSequenceLeaseCacheAcquisition {
    disposition: NativeExecutableSequenceLeaseCacheDisposition,
    lease: NativeExecutableSequenceLease,
}

/// Exact resident state preventing one candidate from fitting weighted limits.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeExecutableSequenceLeaseCacheBlock {
    limits: NativeExecutableSequenceCacheLimits,
    retired_keys: Vec<NativeExecutableSequenceKey>,
    usage: NativeExecutableSequenceCacheUsage,
}

#[derive(Debug, Eq, PartialEq)]
enum LeaseCacheLoadFailureCause<E> {
    Capacity(NativeExecutableSequenceCacheCapacityError),
    Leases(NativeExecutableSequenceLeaseCacheBlock),
    Load(Box<NativeExecutableSequenceLoadFailure<E>>),
    Release(Box<NativeExecutableSequenceReleaseFailure<E>>),
}

/// Failure while loading, weighing, evicting, or publishing one leased miss.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeExecutableSequenceLeaseCacheLoadFailure<E> {
    candidate_cleanup_failure:
        Option<Box<NativeExecutableSequenceReleaseFailure<E>>>,
    cause: LeaseCacheLoadFailureCause<E>,
    evicted_keys: Vec<NativeExecutableSequenceKey>,
    requested_key: NativeExecutableSequenceKey,
    retired_keys: Vec<NativeExecutableSequenceKey>,
}

/// Result of retiring or immediately releasing one active key.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeExecutableSequenceLeaseCacheInvalidation {
    /// No active key matched the requested plan.
    Missing,
    /// The sequence had no external leases and was released immediately.
    Released,
    /// Active lookup ended while mappings remained resident behind leases.
    Retired {
        /// External lease owners remaining after retirement.
        leases: usize,
    },
}

/// Result of acquiring one active immutable sequence lease.
pub type NativeExecutableSequenceLeaseCacheLoadResult<E> = Result<
    NativeExecutableSequenceLeaseCacheAcquisition,
    Box<NativeExecutableSequenceLeaseCacheLoadFailure<E>>,
>;

/// Result of invalidating one active leased-cache plan.
pub type NativeExecutableSequenceLeaseCacheInvalidationResult<E> = Result<
    NativeExecutableSequenceLeaseCacheInvalidation,
    Box<NativeExecutableSequenceReleaseFailure<E>>,
>;

type NativeExecutableSequenceLeaseCachePrepareResult<E> = Result<
    NativeExecutableSequenceLeaseCacheCandidate,
    Box<NativeExecutableSequenceLeaseCacheLoadFailure<E>>,
>;

type NativeExecutableSequenceLeaseCacheFitResult<E> = Result<
    (
        NativeExecutableSequenceLeaseCacheCandidate,
        Vec<NativeExecutableSequenceKey>,
        Vec<NativeExecutableSequenceKey>,
    ),
    Box<NativeExecutableSequenceLeaseCacheLoadFailure<E>>,
>;

impl NativeExecutableSequenceLease {
    /// Returns the exact ordered key retained by this lease.
    #[must_use]
    pub const fn key(&self) -> &NativeExecutableSequenceKey {
        &self.key
    }

    /// Returns the immutable ready sequence retained by this lease.
    #[must_use]
    pub fn sequence(&self) -> &ReadyNativeExecutableSequence {
        self.sequence.as_ref()
    }

    /// Reports whether two leases retain the same resident sequence allocation.
    #[must_use]
    pub fn shares_resident_with(&self, other: &Self) -> bool {
        Arc::ptr_eq(&self.sequence, &other.sequence)
    }

    /// Returns all strong owners, including active or retired cache authority.
    #[must_use]
    pub fn strong_owner_count(&self) -> usize {
        Arc::strong_count(&self.sequence)
    }
}

impl NativeExecutableSequenceLeaseCacheDisposition {
    /// Returns every key removed from active lookup for this insertion.
    #[must_use]
    pub fn evicted_keys(&self) -> &[NativeExecutableSequenceKey] {
        match self {
            Self::Hit => &[],
            Self::Inserted { evicted, .. } => evicted,
        }
    }

    /// Reports whether this acquisition reused existing active lookup state.
    #[must_use]
    pub const fn is_hit(&self) -> bool {
        matches!(self, Self::Hit)
    }

    /// Returns removed keys still resident behind live leases.
    #[must_use]
    pub fn retired_keys(&self) -> &[NativeExecutableSequenceKey] {
        match self {
            Self::Hit => &[],
            Self::Inserted { retired, .. } => retired,
        }
    }
}

impl NativeExecutableSequenceLeaseCacheAcquisition {
    /// Returns exact lookup and FIFO processing evidence.
    #[must_use]
    pub const fn disposition(
        &self,
    ) -> &NativeExecutableSequenceLeaseCacheDisposition {
        &self.disposition
    }

    /// Consumes this acquisition and returns its immutable lease.
    #[must_use]
    pub fn into_lease(self) -> NativeExecutableSequenceLease {
        self.lease
    }

    /// Returns the immutable lease retained by this acquisition.
    #[must_use]
    pub const fn lease(&self) -> &NativeExecutableSequenceLease {
        &self.lease
    }
}

impl NativeExecutableSequenceLeaseCacheBlock {
    /// Returns limits that could not admit the candidate's resident weight.
    #[must_use]
    pub const fn limits(&self) -> NativeExecutableSequenceCacheLimits {
        self.limits
    }

    /// Returns all retired keys whose mappings still count against capacity.
    #[must_use]
    pub fn retired_keys(&self) -> &[NativeExecutableSequenceKey] {
        &self.retired_keys
    }

    /// Returns exact resident usage when admission became blocked.
    #[must_use]
    pub const fn usage(&self) -> NativeExecutableSequenceCacheUsage {
        self.usage
    }
}

impl<E> NativeExecutableSequenceLeaseCacheLoadFailure<E> {
    /// Returns resident lease blockage, when no further FIFO release can fit.
    #[must_use]
    pub const fn block(
        &self,
    ) -> Option<&NativeExecutableSequenceLeaseCacheBlock> {
        match &self.cause {
            LeaseCacheLoadFailureCause::Leases(block) => Some(block),
            LeaseCacheLoadFailureCause::Capacity(_)
            | LeaseCacheLoadFailureCause::Load(_)
            | LeaseCacheLoadFailureCause::Release(_) => None,
        }
    }

    /// Returns failed candidate cleanup ownership, when present.
    #[must_use]
    pub fn candidate_cleanup_failure(
        &self,
    ) -> Option<&NativeExecutableSequenceReleaseFailure<E>> {
        self.candidate_cleanup_failure.as_deref()
    }

    /// Returns candidate capacity rejection, when it cannot fit alone.
    #[must_use]
    pub const fn capacity_error(
        &self,
    ) -> Option<NativeExecutableSequenceCacheCapacityError> {
        match self.cause {
            LeaseCacheLoadFailureCause::Capacity(error) => Some(error),
            LeaseCacheLoadFailureCause::Leases(_)
            | LeaseCacheLoadFailureCause::Load(_)
            | LeaseCacheLoadFailureCause::Release(_) => None,
        }
    }

    /// Returns every key removed from active lookup before failure.
    #[must_use]
    pub fn evicted_keys(&self) -> &[NativeExecutableSequenceKey] {
        &self.evicted_keys
    }

    /// Consumes this failure and returns retryable release owners.
    #[must_use]
    pub fn into_release_failures(
        self,
    ) -> NativeExecutableSequenceLeaseCacheLoadReleaseFailures<E> {
        let eviction_key = self
            .evicted_keys
            .last()
            .cloned()
            .unwrap_or_else(|| self.requested_key.clone());
        let eviction = match self.cause {
            LeaseCacheLoadFailureCause::Release(failure) => Some(
                reconciliation::entry_release_failure(eviction_key, *failure),
            ),
            LeaseCacheLoadFailureCause::Capacity(_)
            | LeaseCacheLoadFailureCause::Leases(_)
            | LeaseCacheLoadFailureCause::Load(_) => None,
        };
        let candidate = self.candidate_cleanup_failure.map(|failure| {
            reconciliation::entry_release_failure(self.requested_key, *failure)
        });
        reconciliation::load_release_failures(candidate, eviction)
    }

    /// Returns candidate loading failure before resident state changed.
    #[must_use]
    pub const fn load_failure(
        &self,
    ) -> Option<&NativeExecutableSequenceLoadFailure<E>> {
        match &self.cause {
            LeaseCacheLoadFailureCause::Load(failure) => Some(failure),
            LeaseCacheLoadFailureCause::Capacity(_)
            | LeaseCacheLoadFailureCause::Leases(_)
            | LeaseCacheLoadFailureCause::Release(_) => None,
        }
    }

    /// Returns failed FIFO victim release ownership, when present.
    #[must_use]
    pub const fn release_failure(
        &self,
    ) -> Option<&NativeExecutableSequenceReleaseFailure<E>> {
        match &self.cause {
            LeaseCacheLoadFailureCause::Release(failure) => Some(failure),
            LeaseCacheLoadFailureCause::Capacity(_)
            | LeaseCacheLoadFailureCause::Leases(_)
            | LeaseCacheLoadFailureCause::Load(_) => None,
        }
    }

    /// Returns exact requested sequence identity whose acquisition failed.
    #[must_use]
    pub const fn requested_key(&self) -> &NativeExecutableSequenceKey {
        &self.requested_key
    }

    /// Returns removed keys still resident behind live leases.
    #[must_use]
    pub fn retired_keys(&self) -> &[NativeExecutableSequenceKey] {
        &self.retired_keys
    }
}

impl<E: Display> Display for NativeExecutableSequenceLeaseCacheLoadFailure<E> {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str("native executable sequence lease cache miss failed: ")?;
        match &self.cause {
            LeaseCacheLoadFailureCause::Capacity(error) => {
                write!(f, "capacity: {error}")?;
            },
            LeaseCacheLoadFailureCause::Leases(_) => {
                f.write_str("resident leases block weighted capacity")?;
            },
            LeaseCacheLoadFailureCause::Load(error) => {
                write!(f, "load: {error}")?;
            },
            LeaseCacheLoadFailureCause::Release(error) => {
                write!(f, "eviction release: {error}")?;
            },
        }
        if self.candidate_cleanup_failure.is_some() {
            f.write_str("; candidate cleanup also failed")?;
        }
        Ok(())
    }
}

impl NativeExecutableSequenceLeaseCache {
    fn active_acquisition(
        entry: &NativeExecutableSequenceLeaseCacheValue,
        disposition: NativeExecutableSequenceLeaseCacheDisposition,
    ) -> NativeExecutableSequenceLeaseCacheAcquisition {
        NativeExecutableSequenceLeaseCacheAcquisition {
            disposition,
            lease: NativeExecutableSequenceLease {
                key: entry.key.clone(),
                sequence: Arc::clone(&entry.sequence),
            },
        }
    }

    /// Returns the number of active lookup entries.
    #[must_use]
    pub fn active_len(&self) -> usize {
        self.active.len()
    }

    /// Returns the positive resident entry capacity.
    #[must_use]
    pub const fn capacity(&self) -> NonZeroUsize {
        self.limits.entry_limit()
    }

    /// Returns whether one exact cache-aware plan has active lookup authority.
    #[must_use]
    pub fn contains_cached_plan(
        &self,
        plan: &CachedVerifiedDirectSequencePlan,
    ) -> bool {
        let key = NativeExecutableSequenceKey::from_cached_plan(plan);
        self.position(&key).is_some()
    }

    /// Returns whether one exact uncached plan has active lookup authority.
    #[must_use]
    pub fn contains_plan(&self, plan: &VerifiedDirectSequencePlan) -> bool {
        let key = NativeExecutableSequenceKey::from_plan(plan);
        self.position(&key).is_some()
    }

    /// Loads or reuses one exact cache-aware sequence and returns a cloneable
    /// lease.
    ///
    /// # Errors
    ///
    /// Returns exact load, capacity, lease-block, or release ownership
    /// evidence.
    pub fn ensure_cached_plan<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        plan: &CachedVerifiedDirectSequencePlan,
    ) -> NativeExecutableSequenceLeaseCacheLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let key = NativeExecutableSequenceKey::from_cached_plan(plan);
        self.ensure_with(adapter, key, |loader| {
            load_cached_verified_native_sequence(loader, plan)
        })
    }

    /// Loads or reuses one exact uncached sequence and returns a cloneable
    /// lease.
    ///
    /// # Errors
    ///
    /// Returns exact load, capacity, lease-block, or release ownership
    /// evidence.
    pub fn ensure_plan<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        plan: &VerifiedDirectSequencePlan,
    ) -> NativeExecutableSequenceLeaseCacheLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let key = NativeExecutableSequenceKey::from_plan(plan);
        self.ensure_with(adapter, key, |loader| {
            load_verified_native_sequence(loader, plan)
        })
    }

    fn ensure_with<Adapter, Load>(
        &mut self,
        adapter: &mut Adapter,
        key: NativeExecutableSequenceKey,
        load: Load,
    ) -> NativeExecutableSequenceLeaseCacheLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
        Load: FnOnce(
            &mut Adapter,
        )
            -> NativeExecutableSequenceLoadResult<Adapter::Error>,
    {
        if let Some(entry) = self.active.iter().find(|entry| entry.key == key) {
            return Ok(Self::active_acquisition(
                entry,
                NativeExecutableSequenceLeaseCacheDisposition::Hit,
            ));
        }
        let sequence = load(adapter).map_err(|failure| {
            Box::new(lease_cache_load_failure(key.clone(), failure))
        })?;
        self.publish_candidate(adapter, key, sequence)
    }

    fn evict_until_fits<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        candidate: NativeExecutableSequenceLeaseCacheCandidate,
    ) -> NativeExecutableSequenceLeaseCacheFitResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let mut evicted_keys = Vec::new();
        let mut retired_keys = Vec::new();
        while self.limits.projected_exceeds(self.usage, candidate.weight) {
            let Some(victim) = self.active.pop_front() else {
                let context = LeaseCacheFailureContext {
                    candidate,
                    evicted_keys,
                    retired_keys,
                };
                return Err(Box::new(lease_cache_blocked_failure(
                    adapter, context, self,
                )));
            };
            evicted_keys.push(victim.key.clone());
            match process_lease_cache_victim(adapter, victim) {
                LeaseCacheVictimOutcome::Released(weight) => {
                    self.usage.remove(weight);
                },
                LeaseCacheVictimOutcome::ReleaseFailed { failure, weight } => {
                    self.usage.remove(weight);
                    let context = LeaseCacheFailureContext {
                        candidate,
                        evicted_keys,
                        retired_keys,
                    };
                    return Err(Box::new(lease_cache_eviction_failure(
                        adapter, context, failure,
                    )));
                },
                LeaseCacheVictimOutcome::Retired(retired_entry) => {
                    retired_keys.push(retired_entry.key.clone());
                    self.retired.push_back(retired_entry);
                },
            }
        }
        Ok((candidate, evicted_keys, retired_keys))
    }

    /// Invalidates one exact cache-aware plan, releasing or retiring it.
    ///
    /// # Errors
    ///
    /// Returns exact release ownership when an unleased sequence cannot
    /// release.
    pub fn invalidate_cached_plan<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        plan: &CachedVerifiedDirectSequencePlan,
    ) -> NativeExecutableSequenceLeaseCacheInvalidationResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let key = NativeExecutableSequenceKey::from_cached_plan(plan);
        self.invalidate_key(adapter, &key)
    }

    fn invalidate_key<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        key: &NativeExecutableSequenceKey,
    ) -> NativeExecutableSequenceLeaseCacheInvalidationResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let Some(index) = self.position(key) else {
            return Ok(NativeExecutableSequenceLeaseCacheInvalidation::Missing);
        };
        let Some(entry) = self.active.remove(index) else {
            return Ok(NativeExecutableSequenceLeaseCacheInvalidation::Missing);
        };
        let leases = Arc::strong_count(&entry.sequence).saturating_sub(1);
        match Arc::try_unwrap(entry.sequence) {
            Ok(sequence) => {
                self.usage.remove(entry.weight);
                release_native_executable_sequence(adapter, sequence).map(
                    |()| {
                        NativeExecutableSequenceLeaseCacheInvalidation::Released
                    },
                )
            },
            Err(sequence) => {
                self.retired.push_back(
                    NativeExecutableSequenceLeaseCacheValue {
                        key: entry.key,
                        sequence,
                        weight: entry.weight,
                    },
                );
                Ok(NativeExecutableSequenceLeaseCacheInvalidation::Retired {
                    leases,
                })
            },
        }
    }

    /// Invalidates one exact uncached plan, releasing or retiring it.
    ///
    /// # Errors
    ///
    /// Returns exact release ownership when an unleased sequence cannot
    /// release.
    pub fn invalidate_plan<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        plan: &VerifiedDirectSequencePlan,
    ) -> NativeExecutableSequenceLeaseCacheInvalidationResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let key = NativeExecutableSequenceKey::from_plan(plan);
        self.invalidate_key(adapter, &key)
    }

    /// Returns whether no active or retired resident sequence remains.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.active.is_empty() && self.retired.is_empty()
    }

    /// Returns active exact keys in FIFO insertion order.
    pub fn keys(&self) -> impl Iterator<Item = &NativeExecutableSequenceKey> {
        self.active.iter().map(|entry| &entry.key)
    }

    /// Returns every caller-selected resident capacity limit.
    #[must_use]
    pub const fn limits(&self) -> NativeExecutableSequenceCacheLimits {
        self.limits
    }

    /// Constructs an empty shared lease cache with an entry-only limit.
    #[must_use]
    pub const fn new(capacity: NonZeroUsize) -> Self {
        Self::with_limits(NativeExecutableSequenceCacheLimits::new(capacity))
    }

    fn position(&self, key: &NativeExecutableSequenceKey) -> Option<usize> {
        self.active.iter().position(|entry| entry.key == *key)
    }

    fn publish_candidate<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        key: NativeExecutableSequenceKey,
        sequence: ReadyNativeExecutableSequence,
    ) -> NativeExecutableSequenceLeaseCacheLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let prepared =
            prepare_lease_cache_candidate(adapter, self.limits, key, sequence)?;
        let (candidate, evicted, retired) =
            self.evict_until_fits(adapter, prepared)?;
        if let Err(error) = self.usage.add(candidate.weight) {
            return Err(Box::new(lease_cache_capacity_failure(
                adapter,
                candidate.key,
                candidate.sequence,
                error,
            )));
        }
        let shared_sequence = Arc::new(candidate.sequence);
        self.active
            .push_back(NativeExecutableSequenceLeaseCacheValue {
                key: candidate.key.clone(),
                sequence: Arc::clone(&shared_sequence),
                weight: candidate.weight,
            });
        Ok(NativeExecutableSequenceLeaseCacheAcquisition {
            disposition:
                NativeExecutableSequenceLeaseCacheDisposition::Inserted {
                    evicted,
                    retired,
                },
            lease: NativeExecutableSequenceLease {
                key: candidate.key,
                sequence: shared_sequence,
            },
        })
    }

    /// Reclaims every retired sequence whose final external lease has gone.
    ///
    /// # Errors
    ///
    /// Returns keyed release failures after attempting every releasable
    /// resident.
    pub fn reconcile_retired<Adapter>(
        &mut self,
        adapter: &mut Adapter,
    ) -> NativeExecutableSequenceLeaseCacheReconciliationResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        reconciliation::reconcile_retired_values(
            adapter,
            &mut self.retired,
            &mut self.usage,
        )
    }

    /// Publishes new resident limits after active FIFO processing.
    ///
    /// Expansion and already-satisfied requests publish without adapter work.
    /// Shrink removes active lookup authority oldest-first, immediately
    /// releases unleased entries, and retires live leased entries without
    /// reducing their resident weight. Existing retired entries are never
    /// reclaimed implicitly.
    ///
    /// # Errors
    ///
    /// Returns exact resident blockage or keyed release ownership while the
    /// previous limits remain published.
    pub fn reconfigure_limits<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        requested_limits: NativeExecutableSequenceCacheLimits,
    ) -> NativeExecutableSequenceLeaseCacheReconfigurationResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let previous_limits = self.limits;
        let (evicted_keys, retired_keys) =
            reconfiguration::evict_for_reconfiguration(
                self,
                adapter,
                requested_limits,
                previous_limits,
            )?;
        self.limits = requested_limits;
        Ok(reconfiguration::published(
            evicted_keys,
            retired_keys,
            requested_limits,
            previous_limits,
        ))
    }

    /// Removes all active lookup authority and reclaims every unleased
    /// resident.
    ///
    /// # Errors
    ///
    /// Returns keyed release failures after attempting every releasable
    /// resident.
    pub fn release_all<Adapter>(
        &mut self,
        adapter: &mut Adapter,
    ) -> NativeExecutableSequenceLeaseCacheReconciliationResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        self.retired.extend(self.active.drain(..));
        self.reconcile_retired(adapter)
    }

    /// Returns the total number of active plus retired resident sequences.
    #[must_use]
    pub fn resident_len(&self) -> usize {
        self.active.len().saturating_add(self.retired.len())
    }

    /// Returns retired keys in original FIFO order.
    pub fn retired_keys(
        &self,
    ) -> impl Iterator<Item = &NativeExecutableSequenceKey> {
        self.retired.iter().map(|entry| &entry.key)
    }

    /// Returns the number of retired sequences awaiting lease reclamation.
    #[must_use]
    pub fn retired_len(&self) -> usize {
        self.retired.len()
    }

    /// Consumes one lease and immediately reconciles every retired resident.
    ///
    /// # Errors
    ///
    /// Returns keyed release failures after attempting every releasable
    /// resident.
    pub fn return_lease<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        lease: NativeExecutableSequenceLease,
    ) -> NativeExecutableSequenceLeaseCacheReconciliationResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        drop(lease);
        self.reconcile_retired(adapter)
    }

    /// Returns exact active plus retired resident resource usage.
    #[must_use]
    pub const fn usage(&self) -> NativeExecutableSequenceCacheUsage {
        self.usage
    }

    /// Constructs an empty shared lease cache with explicit resident limits.
    #[must_use]
    pub const fn with_limits(
        limits: NativeExecutableSequenceCacheLimits,
    ) -> Self {
        Self {
            active: VecDeque::new(),
            limits,
            retired: VecDeque::new(),
            usage: NativeExecutableSequenceCacheUsage::empty(),
        }
    }
}

fn lease_cache_blocked_failure<Adapter>(
    adapter: &mut Adapter,
    context: LeaseCacheFailureContext,
    cache: &NativeExecutableSequenceLeaseCache,
) -> NativeExecutableSequenceLeaseCacheLoadFailure<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let block = NativeExecutableSequenceLeaseCacheBlock {
        limits: cache.limits,
        retired_keys: cache.retired_keys().cloned().collect(),
        usage: cache.usage,
    };
    lease_cache_candidate_failure(
        adapter,
        context,
        LeaseCacheLoadFailureCause::Leases(block),
    )
}

fn lease_cache_candidate_failure<Adapter>(
    adapter: &mut Adapter,
    context: LeaseCacheFailureContext,
    cause: LeaseCacheLoadFailureCause<Adapter::Error>,
) -> NativeExecutableSequenceLeaseCacheLoadFailure<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let candidate_cleanup_failure =
        release_native_executable_sequence(adapter, context.candidate.sequence)
            .err();
    NativeExecutableSequenceLeaseCacheLoadFailure {
        candidate_cleanup_failure,
        cause,
        evicted_keys: context.evicted_keys,
        requested_key: context.candidate.key,
        retired_keys: context.retired_keys,
    }
}

fn lease_cache_capacity_failure<Adapter>(
    adapter: &mut Adapter,
    key: NativeExecutableSequenceKey,
    sequence: ReadyNativeExecutableSequence,
    error: NativeExecutableSequenceCacheCapacityError,
) -> NativeExecutableSequenceLeaseCacheLoadFailure<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let candidate_cleanup_failure =
        release_native_executable_sequence(adapter, sequence).err();
    NativeExecutableSequenceLeaseCacheLoadFailure {
        candidate_cleanup_failure,
        cause: LeaseCacheLoadFailureCause::Capacity(error),
        evicted_keys: Vec::new(),
        requested_key: key,
        retired_keys: Vec::new(),
    }
}

fn lease_cache_eviction_failure<Adapter>(
    adapter: &mut Adapter,
    context: LeaseCacheFailureContext,
    failure: Box<NativeExecutableSequenceReleaseFailure<Adapter::Error>>,
) -> NativeExecutableSequenceLeaseCacheLoadFailure<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    lease_cache_candidate_failure(
        adapter,
        context,
        LeaseCacheLoadFailureCause::Release(failure),
    )
}

const fn lease_cache_load_failure<E>(
    requested_key: NativeExecutableSequenceKey,
    failure: Box<NativeExecutableSequenceLoadFailure<E>>,
) -> NativeExecutableSequenceLeaseCacheLoadFailure<E> {
    NativeExecutableSequenceLeaseCacheLoadFailure {
        candidate_cleanup_failure: None,
        cause: LeaseCacheLoadFailureCause::Load(failure),
        evicted_keys: Vec::new(),
        requested_key,
        retired_keys: Vec::new(),
    }
}

fn prepare_lease_cache_candidate<Adapter>(
    adapter: &mut Adapter,
    limits: NativeExecutableSequenceCacheLimits,
    key: NativeExecutableSequenceKey,
    sequence: ReadyNativeExecutableSequence,
) -> NativeExecutableSequenceLeaseCachePrepareResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let weight = match NativeExecutableSequenceWeight::from_sequence(&sequence)
    {
        Ok(weight) => weight,
        Err(error) => {
            return Err(Box::new(lease_cache_capacity_failure(
                adapter, key, sequence, error,
            )));
        },
    };
    if let Some(error) = limits.candidate_error(weight) {
        return Err(Box::new(lease_cache_capacity_failure(
            adapter, key, sequence, error,
        )));
    }
    Ok(NativeExecutableSequenceLeaseCacheCandidate { key, sequence, weight })
}

fn process_lease_cache_victim<Adapter>(
    adapter: &mut Adapter,
    victim: NativeExecutableSequenceLeaseCacheValue,
) -> LeaseCacheVictimOutcome<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    match Arc::try_unwrap(victim.sequence) {
        Err(sequence) => LeaseCacheVictimOutcome::Retired(
            NativeExecutableSequenceLeaseCacheValue {
                key: victim.key,
                sequence,
                weight: victim.weight,
            },
        ),
        Ok(sequence) => {
            match release_native_executable_sequence(adapter, sequence) {
                Ok(()) => LeaseCacheVictimOutcome::Released(victim.weight),
                Err(failure) => LeaseCacheVictimOutcome::ReleaseFailed {
                    failure,
                    weight: victim.weight,
                },
            }
        },
    }
}
