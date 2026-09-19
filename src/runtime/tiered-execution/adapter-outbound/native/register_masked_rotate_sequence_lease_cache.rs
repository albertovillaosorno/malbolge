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
//   - Shared immutable leases and deferred release for loaded rotate
//     register-masked v6 sequences.
// - Must-Not:
//   - Execute native code, hide retired weight, or release live leased
//     mappings.
// - Allows:
//   - Inputs: admitted rotate sequence plans, weighted limits, and adapter.
//   - Outputs: cloneable leases, active/retired state, and retryable cleanup.
//   - Side effects: executable sequence load/release through the supplied
//     adapter.
// - Split-When:
//   - Asynchronous reclamation or lease waiting gains independent policy.
// - Merge-When:
//   - One reviewed rotate sequence store subsumes borrowed and leased use.
// - Summary:
//   - Retains leased rotate mappings after FIFO lookup retirement.
// - Description:
//   - Retired leases keep exact capacity weight until explicit reconciliation.
// - Usage:
//   - Acquire leases, retire/invalidate keys, drop leases, then reconcile.
// - Defaults:
//   - Lease clone/drop performs no adapter work; FIFO age never refreshes.
//

//! Shared lease cache for loaded rotate register-masked v6 sequences.

#[path = "register_masked_rotate_sequence_lease_cache/reconciliation.rs"]
mod reconciliation;
#[path = "register_masked_rotate_sequence_lease_cache/reconfiguration.rs"]
mod reconfiguration;

use std::collections::VecDeque;
use std::fmt::{Display, Formatter, Result as FormatResult};
use std::num::NonZeroUsize;
use std::sync::Arc;

pub use reconciliation::{
    RegisterMaskedRotateNativeSequenceLeaseCacheEntryReleaseFailure,
    RegisterMaskedRotateNativeSequenceLeaseCacheLoadReleaseFailures,
    RegisterMaskedRotateNativeSequenceLeaseCacheReconciliation,
    RegisterMaskedRotateNativeSequenceLeaseCacheReleaseFailure,
    RegisterMaskedRotateNativeSequenceLeaseReconciliationResult,
};
pub use reconfiguration::{
    RegisterMaskedRotateNativeSequenceLeaseCacheReconfiguration,
    RegisterMaskedRotateNativeSequenceLeaseReconfigurationFailure,
    RegisterMaskedRotateNativeSequenceLeaseReconfigurationResult,
};

use super::executable_cache_capacity::{
    NativeExecutableSequenceCacheCapacityError,
    NativeExecutableSequenceCacheLimits, NativeExecutableSequenceCacheUsage,
    NativeExecutableSequenceWeight,
};
use super::platform::NativeExecutableMemoryAdapter;
use super::register_masked_rotate_loaded_sequence::{
    LoadedRegisterMaskedRotateNativeSequence,
    RegisterMaskedRotateNativeSequenceLoadFailure,
    RegisterMaskedRotateNativeSequenceReleaseFailure,
    load_register_masked_rotate_native_sequence,
};
use super::register_masked_rotate_sequence::{
    RegisterMaskedRotateNativeSequenceKey,
    RegisterMaskedRotateNativeSequencePlan,
};

#[derive(Debug)]
struct CacheValue {
    key: RegisterMaskedRotateNativeSequenceKey,
    sequence: Arc<LoadedRegisterMaskedRotateNativeSequence>,
    weight: NativeExecutableSequenceWeight,
}

#[derive(Debug)]
struct CacheCandidate {
    key: RegisterMaskedRotateNativeSequenceKey,
    sequence: LoadedRegisterMaskedRotateNativeSequence,
    weight: NativeExecutableSequenceWeight,
}

#[derive(Debug)]
struct CacheFailureContext {
    candidate: CacheCandidate,
    evicted_keys: Vec<RegisterMaskedRotateNativeSequenceKey>,
    retired_keys: Vec<RegisterMaskedRotateNativeSequenceKey>,
}

#[derive(Debug)]
enum CacheVictimOutcome<E> {
    ReleaseFailed {
        failure: Box<RegisterMaskedRotateNativeSequenceReleaseFailure<E>>,
        weight: NativeExecutableSequenceWeight,
    },
    Released(NativeExecutableSequenceWeight),
    Retired(CacheValue),
}

#[derive(Debug)]
enum LoadFailureCause<E> {
    Capacity(NativeExecutableSequenceCacheCapacityError),
    Leases(RegisterMaskedRotateNativeSequenceLeaseCacheBlock),
    Load(Box<RegisterMaskedRotateNativeSequenceLoadFailure<E>>),
    Release(Box<RegisterMaskedRotateNativeSequenceReleaseFailure<E>>),
}

/// Caller-owned weighted cache with cloneable immutable rotate leases.
#[derive(Debug)]
pub struct RegisterMaskedRotateNativeSequenceLeaseCache {
    active: VecDeque<CacheValue>,
    limits: NativeExecutableSequenceCacheLimits,
    retired: VecDeque<CacheValue>,
    usage: NativeExecutableSequenceCacheUsage,
}

/// Cloneable immutable ownership of one resident rotate sequence.
#[derive(Clone, Debug)]
pub struct RegisterMaskedRotateNativeSequenceLease {
    key: RegisterMaskedRotateNativeSequenceKey,
    sequence: Arc<LoadedRegisterMaskedRotateNativeSequence>,
}

/// Whether one acquisition reused or inserted active lookup state.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum RegisterMaskedRotateNativeSequenceLeaseCacheDisposition {
    /// Exact active identity already existed and FIFO age was unchanged.
    Hit,
    /// A new active identity was published after weighted FIFO processing.
    Inserted {
        /// Every key removed from active lookup in FIFO order.
        evicted: Vec<RegisterMaskedRotateNativeSequenceKey>,
        /// Removed keys whose mappings remain resident behind live leases.
        retired: Vec<RegisterMaskedRotateNativeSequenceKey>,
    },
}

/// Lease plus exact lookup and FIFO evidence for one acquisition.
#[derive(Debug)]
pub struct RegisterMaskedRotateNativeSequenceLeaseCacheAcquisition {
    disposition: RegisterMaskedRotateNativeSequenceLeaseCacheDisposition,
    lease: RegisterMaskedRotateNativeSequenceLease,
}

/// Exact retired resident state preventing one candidate from fitting limits.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RegisterMaskedRotateNativeSequenceLeaseCacheBlock {
    limits: NativeExecutableSequenceCacheLimits,
    retired_keys: Vec<RegisterMaskedRotateNativeSequenceKey>,
    usage: NativeExecutableSequenceCacheUsage,
}

/// Failure while loading, weighing, evicting, or publishing one leased miss.
#[derive(Debug)]
pub struct RegisterMaskedRotateNativeSequenceLeaseCacheLoadFailure<E> {
    candidate_cleanup_failure:
        Option<Box<RegisterMaskedRotateNativeSequenceReleaseFailure<E>>>,
    cause: LoadFailureCause<E>,
    evicted_keys: Vec<RegisterMaskedRotateNativeSequenceKey>,
    requested_key: RegisterMaskedRotateNativeSequenceKey,
    retired_keys: Vec<RegisterMaskedRotateNativeSequenceKey>,
}

/// Result of retiring or immediately releasing one active plan.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RegisterMaskedRotateNativeSequenceLeaseCacheInvalidation {
    /// No active key matched the requested plan.
    Missing,
    /// The sequence had no external leases and was released immediately.
    Released,
    /// Active lookup ended while mappings remained behind external leases.
    Retired {
        /// External lease owners remaining after retirement.
        leases: usize,
    },
}

/// Published weighted capacity limits for this rotate lease cache.
pub type RegisterMaskedRotateNativeSequenceLeaseCacheLimits =
    NativeExecutableSequenceCacheLimits;

/// Exact active-plus-retired resource usage retained by this lease cache.
pub type RegisterMaskedRotateNativeSequenceLeaseCacheUsage =
    NativeExecutableSequenceCacheUsage;

/// Capacity rejection produced by this rotate sequence lease cache.
pub type RegisterMaskedRotateNativeSequenceLeaseCacheCapacityError =
    NativeExecutableSequenceCacheCapacityError;

/// Result of acquiring one active immutable rotate sequence lease.
pub type RegisterMaskedRotateNativeSequenceLeaseCacheLoadResult<E> = Result<
    RegisterMaskedRotateNativeSequenceLeaseCacheAcquisition,
    Box<RegisterMaskedRotateNativeSequenceLeaseCacheLoadFailure<E>>,
>;

/// Result of invalidating one active rotate sequence lease-cache plan.
pub type RegisterMaskedRotateNativeSequenceLeaseCacheInvalidationResult<E> =
    Result<
        RegisterMaskedRotateNativeSequenceLeaseCacheInvalidation,
        Box<RegisterMaskedRotateNativeSequenceLeaseCacheEntryReleaseFailure<E>>,
    >;

type CacheDisposition = RegisterMaskedRotateNativeSequenceLeaseCacheDisposition;
type CacheInvalidation =
    RegisterMaskedRotateNativeSequenceLeaseCacheInvalidation;
type CacheLoadFailure<E> =
    RegisterMaskedRotateNativeSequenceLeaseCacheLoadFailure<E>;

type CacheFitResult<E> = Result<
    (
        CacheCandidate,
        Vec<RegisterMaskedRotateNativeSequenceKey>,
        Vec<RegisterMaskedRotateNativeSequenceKey>,
    ),
    Box<RegisterMaskedRotateNativeSequenceLeaseCacheLoadFailure<E>>,
>;

type CachePrepareResult<E> = Result<
    CacheCandidate,
    Box<RegisterMaskedRotateNativeSequenceLeaseCacheLoadFailure<E>>,
>;

impl RegisterMaskedRotateNativeSequenceLease {
    /// Returns the exact ordered sequence key retained by this lease.
    #[must_use]
    pub const fn key(&self) -> &RegisterMaskedRotateNativeSequenceKey {
        &self.key
    }

    /// Returns the immutable loaded sequence retained by this lease.
    #[must_use]
    pub fn sequence(&self) -> &LoadedRegisterMaskedRotateNativeSequence {
        self.sequence.as_ref()
    }

    /// Reports whether two leases retain the same loaded sequence allocation.
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

impl RegisterMaskedRotateNativeSequenceLeaseCacheDisposition {
    /// Returns every key removed from active lookup for this insertion.
    #[must_use]
    pub fn evicted_keys(&self) -> &[RegisterMaskedRotateNativeSequenceKey] {
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

    /// Returns removed keys still resident behind external leases.
    #[must_use]
    pub fn retired_keys(&self) -> &[RegisterMaskedRotateNativeSequenceKey] {
        match self {
            Self::Hit => &[],
            Self::Inserted { retired, .. } => retired,
        }
    }
}

impl RegisterMaskedRotateNativeSequenceLeaseCacheAcquisition {
    /// Returns exact lookup and FIFO processing evidence.
    #[must_use]
    pub const fn disposition(
        &self,
    ) -> &RegisterMaskedRotateNativeSequenceLeaseCacheDisposition {
        &self.disposition
    }

    /// Consumes this acquisition and returns its immutable lease.
    #[must_use]
    pub fn into_lease(self) -> RegisterMaskedRotateNativeSequenceLease {
        self.lease
    }

    /// Returns the immutable lease retained by this acquisition.
    #[must_use]
    pub const fn lease(&self) -> &RegisterMaskedRotateNativeSequenceLease {
        &self.lease
    }
}

impl RegisterMaskedRotateNativeSequenceLeaseCacheBlock {
    /// Returns limits that could not admit the candidate's resident weight.
    #[must_use]
    pub const fn limits(
        &self,
    ) -> RegisterMaskedRotateNativeSequenceLeaseCacheLimits {
        self.limits
    }

    /// Returns all retired keys whose mappings still count against capacity.
    #[must_use]
    pub fn retired_keys(&self) -> &[RegisterMaskedRotateNativeSequenceKey] {
        &self.retired_keys
    }

    /// Returns exact resident usage when admission became blocked.
    #[must_use]
    pub const fn usage(
        &self,
    ) -> RegisterMaskedRotateNativeSequenceLeaseCacheUsage {
        self.usage
    }
}

impl<E> RegisterMaskedRotateNativeSequenceLeaseCacheLoadFailure<E> {
    /// Returns resident lease blockage, when no further FIFO release can fit.
    #[must_use]
    pub const fn block(
        &self,
    ) -> Option<&RegisterMaskedRotateNativeSequenceLeaseCacheBlock> {
        match &self.cause {
            LoadFailureCause::Leases(block) => Some(block),
            LoadFailureCause::Capacity(_)
            | LoadFailureCause::Load(_)
            | LoadFailureCause::Release(_) => None,
        }
    }

    /// Returns failed candidate cleanup ownership, when present.
    #[must_use]
    pub fn candidate_cleanup_failure(
        &self,
    ) -> Option<&RegisterMaskedRotateNativeSequenceReleaseFailure<E>> {
        self.candidate_cleanup_failure.as_deref()
    }

    /// Returns candidate capacity rejection, when it cannot fit alone.
    #[must_use]
    pub const fn capacity_error(
        &self,
    ) -> Option<RegisterMaskedRotateNativeSequenceLeaseCacheCapacityError> {
        match self.cause {
            LoadFailureCause::Capacity(error) => Some(error),
            LoadFailureCause::Leases(_)
            | LoadFailureCause::Load(_)
            | LoadFailureCause::Release(_) => None,
        }
    }

    /// Returns every key removed from active lookup before failure.
    #[must_use]
    pub fn evicted_keys(&self) -> &[RegisterMaskedRotateNativeSequenceKey] {
        &self.evicted_keys
    }

    /// Consumes this failure and returns retryable release owners.
    #[must_use]
    pub fn into_release_failures(
        self,
    ) -> RegisterMaskedRotateNativeSequenceLeaseCacheLoadReleaseFailures<E>
    {
        let eviction_key = self
            .evicted_keys
            .last()
            .cloned()
            .unwrap_or_else(|| self.requested_key.clone());
        let eviction = match self.cause {
            LoadFailureCause::Release(failure) => Some(
                reconciliation::entry_release_failure(eviction_key, *failure),
            ),
            LoadFailureCause::Capacity(_)
            | LoadFailureCause::Leases(_)
            | LoadFailureCause::Load(_) => None,
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
    ) -> Option<&RegisterMaskedRotateNativeSequenceLoadFailure<E>> {
        match &self.cause {
            LoadFailureCause::Load(failure) => Some(failure),
            LoadFailureCause::Capacity(_)
            | LoadFailureCause::Leases(_)
            | LoadFailureCause::Release(_) => None,
        }
    }

    /// Returns failed FIFO victim release ownership, when present.
    #[must_use]
    pub const fn release_failure(
        &self,
    ) -> Option<&RegisterMaskedRotateNativeSequenceReleaseFailure<E>> {
        match &self.cause {
            LoadFailureCause::Release(failure) => Some(failure),
            LoadFailureCause::Capacity(_)
            | LoadFailureCause::Leases(_)
            | LoadFailureCause::Load(_) => None,
        }
    }

    /// Returns exact requested sequence identity whose acquisition failed.
    #[must_use]
    pub const fn requested_key(
        &self,
    ) -> &RegisterMaskedRotateNativeSequenceKey {
        &self.requested_key
    }

    /// Returns removed keys still resident behind live leases.
    #[must_use]
    pub fn retired_keys(&self) -> &[RegisterMaskedRotateNativeSequenceKey] {
        &self.retired_keys
    }
}

impl<E: Display> Display
    for RegisterMaskedRotateNativeSequenceLeaseCacheLoadFailure<E>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str("rotate v6 sequence lease cache miss failed: ")?;
        match &self.cause {
            LoadFailureCause::Capacity(error) => {
                write!(f, "capacity: {error}")?;
            },
            LoadFailureCause::Leases(_) => {
                f.write_str("resident leases block weighted capacity")?;
            },
            LoadFailureCause::Load(error) => write!(f, "load: {error}")?,
            LoadFailureCause::Release(error) => {
                write!(f, "eviction release: {error}")?;
            },
        }
        if self.candidate_cleanup_failure.is_some() {
            f.write_str("; candidate cleanup also failed")?;
        }
        Ok(())
    }
}

impl RegisterMaskedRotateNativeSequenceLeaseCache {
    fn active_acquisition(
        entry: &CacheValue,
        disposition: CacheDisposition,
    ) -> RegisterMaskedRotateNativeSequenceLeaseCacheAcquisition {
        RegisterMaskedRotateNativeSequenceLeaseCacheAcquisition {
            disposition,
            lease: RegisterMaskedRotateNativeSequenceLease {
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

    /// Returns whether one exact plan has active lookup authority.
    #[must_use]
    pub fn contains_plan(
        &self,
        plan: &RegisterMaskedRotateNativeSequencePlan,
    ) -> bool {
        let key = RegisterMaskedRotateNativeSequenceKey::from_plan(plan);
        self.position(&key).is_some()
    }

    /// Loads or reuses one exact rotate sequence and returns a lease.
    ///
    /// Hits perform no adapter work and do not refresh FIFO age. Misses load
    /// completely before active FIFO release-or-retirement processing.
    ///
    /// # Errors
    ///
    /// Returns exact load, capacity, lease-block, or release ownership
    /// evidence.
    pub fn ensure_plan<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        plan: &RegisterMaskedRotateNativeSequencePlan,
    ) -> RegisterMaskedRotateNativeSequenceLeaseCacheLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let key = RegisterMaskedRotateNativeSequenceKey::from_plan(plan);
        if let Some(entry) = self.active.iter().find(|entry| entry.key == key) {
            return Ok(Self::active_acquisition(entry, CacheDisposition::Hit));
        }
        let sequence =
            load_register_masked_rotate_native_sequence(plan, adapter)
                .map_err(|failure| {
                    Box::new(
                RegisterMaskedRotateNativeSequenceLeaseCacheLoadFailure {
                    candidate_cleanup_failure: None,
                    cause: LoadFailureCause::Load(failure),
                    evicted_keys: Vec::new(),
                    requested_key: key.clone(),
                    retired_keys: Vec::new(),
                },
            )
                })?;
        self.publish_candidate(adapter, key, sequence)
    }

    fn evict_until_fits<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        candidate: CacheCandidate,
    ) -> CacheFitResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let mut evicted_keys = Vec::new();
        let mut retired_keys = Vec::new();
        while self.limits.projected_exceeds(self.usage, candidate.weight) {
            let Some(victim) = self.active.pop_front() else {
                let context = CacheFailureContext {
                    candidate,
                    evicted_keys,
                    retired_keys,
                };
                return Err(Box::new(cache_blocked_failure(
                    adapter, context, self,
                )));
            };
            evicted_keys.push(victim.key.clone());
            match process_cache_victim(adapter, victim) {
                CacheVictimOutcome::ReleaseFailed { failure, weight } => {
                    self.usage.remove(weight);
                    let context = CacheFailureContext {
                        candidate,
                        evicted_keys,
                        retired_keys,
                    };
                    return Err(Box::new(cache_eviction_failure(
                        adapter, context, failure,
                    )));
                },
                CacheVictimOutcome::Released(weight) => {
                    self.usage.remove(weight);
                },
                CacheVictimOutcome::Retired(retired_entry) => {
                    retired_keys.push(retired_entry.key.clone());
                    self.retired.push_back(retired_entry);
                },
            }
        }
        Ok((candidate, evicted_keys, retired_keys))
    }

    /// Invalidates one exact active plan, releasing or retiring it.
    ///
    /// # Errors
    ///
    /// Returns keyed retryable release ownership for failed unleased cleanup.
    pub fn invalidate_plan<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        plan: &RegisterMaskedRotateNativeSequencePlan,
    ) -> RegisterMaskedRotateNativeSequenceLeaseCacheInvalidationResult<
        Adapter::Error,
    >
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let key = RegisterMaskedRotateNativeSequenceKey::from_plan(plan);
        let Some(index) = self.position(&key) else {
            return Ok(CacheInvalidation::Missing);
        };
        let Some(entry) = self.active.remove(index) else {
            return Ok(CacheInvalidation::Missing);
        };
        let leases = Arc::strong_count(&entry.sequence).saturating_sub(1);
        match Arc::try_unwrap(entry.sequence) {
            Ok(sequence) => {
                self.usage.remove(entry.weight);
                sequence
                    .release(adapter)
                    .map(|()| CacheInvalidation::Released)
                    .map_err(|failure| {
                        Box::new(reconciliation::entry_release_failure(
                            entry.key, *failure,
                        ))
                    })
            },
            Err(sequence) => {
                self.retired.push_back(CacheValue {
                    key: entry.key,
                    sequence,
                    weight: entry.weight,
                });
                Ok(CacheInvalidation::Retired { leases })
            },
        }
    }

    /// Returns whether no active or retired resident sequence remains.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.active.is_empty() && self.retired.is_empty()
    }

    /// Returns active exact keys in FIFO insertion order.
    pub fn keys(
        &self,
    ) -> impl Iterator<Item = &RegisterMaskedRotateNativeSequenceKey> {
        self.active.iter().map(|entry| &entry.key)
    }

    /// Returns every caller-selected resident capacity limit.
    #[must_use]
    pub const fn limits(
        &self,
    ) -> RegisterMaskedRotateNativeSequenceLeaseCacheLimits {
        self.limits
    }

    /// Constructs an empty shared lease cache with an entry-only limit.
    #[must_use]
    pub const fn new(capacity: NonZeroUsize) -> Self {
        Self::with_limits(NativeExecutableSequenceCacheLimits::new(capacity))
    }

    fn position(
        &self,
        key: &RegisterMaskedRotateNativeSequenceKey,
    ) -> Option<usize> {
        self.active.iter().position(|entry| entry.key == *key)
    }

    fn publish_candidate<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        key: RegisterMaskedRotateNativeSequenceKey,
        sequence: LoadedRegisterMaskedRotateNativeSequence,
    ) -> RegisterMaskedRotateNativeSequenceLeaseCacheLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let prepared =
            prepare_cache_candidate(adapter, self.limits, key, sequence)?;
        let (candidate, evicted, retired) =
            self.evict_until_fits(adapter, prepared)?;
        if let Err(error) = self.usage.add(candidate.weight) {
            return Err(Box::new(cache_capacity_failure(
                adapter,
                candidate.key,
                candidate.sequence,
                error,
            )));
        }
        let shared_sequence = Arc::new(candidate.sequence);
        self.active.push_back(CacheValue {
            key: candidate.key.clone(),
            sequence: Arc::clone(&shared_sequence),
            weight: candidate.weight,
        });
        Ok(RegisterMaskedRotateNativeSequenceLeaseCacheAcquisition {
            disposition: CacheDisposition::Inserted { evicted, retired },
            lease: RegisterMaskedRotateNativeSequenceLease {
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
    ) -> RegisterMaskedRotateNativeSequenceLeaseReconciliationResult<
        Adapter::Error,
    >
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
    /// Expansion and already-satisfied requests perform no adapter work. Shrink
    /// removes active lookup authority oldest-first, immediately releases
    /// unleased entries, and retires live leased entries without reducing their
    /// resident weight. Existing retired entries are never reclaimed
    /// implicitly.
    ///
    /// # Errors
    ///
    /// Returns exact resident blockage or keyed release ownership while prior
    /// limits remain published.
    pub fn reconfigure_limits<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        requested_limits: NativeExecutableSequenceCacheLimits,
    ) -> RegisterMaskedRotateNativeSequenceLeaseReconfigurationResult<
        Adapter::Error,
    >
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
    /// Live leased mappings move to retirement without losing capacity weight.
    ///
    /// # Errors
    ///
    /// Returns keyed release failures after attempting every releasable
    /// resident.
    pub fn release_all<Adapter>(
        &mut self,
        adapter: &mut Adapter,
    ) -> RegisterMaskedRotateNativeSequenceLeaseReconciliationResult<
        Adapter::Error,
    >
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        self.retired.extend(self.active.drain(..));
        self.reconcile_retired(adapter)
    }

    /// Returns total active plus retired resident sequence count.
    #[must_use]
    pub fn resident_len(&self) -> usize {
        self.active.len().saturating_add(self.retired.len())
    }

    /// Returns retired keys in original FIFO order.
    pub fn retired_keys(
        &self,
    ) -> impl Iterator<Item = &RegisterMaskedRotateNativeSequenceKey> {
        self.retired.iter().map(|entry| &entry.key)
    }

    /// Returns the number of retired sequences awaiting lease reclamation.
    #[must_use]
    pub fn retired_len(&self) -> usize {
        self.retired.len()
    }

    /// Consumes one lease then reconciles all retired residents explicitly.
    ///
    /// # Errors
    ///
    /// Returns keyed release failures after attempting every releasable
    /// resident.
    pub fn return_lease<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        lease: RegisterMaskedRotateNativeSequenceLease,
    ) -> RegisterMaskedRotateNativeSequenceLeaseReconciliationResult<
        Adapter::Error,
    >
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        drop(lease);
        self.reconcile_retired(adapter)
    }

    /// Returns exact active plus retired resident resource usage.
    #[must_use]
    pub const fn usage(
        &self,
    ) -> RegisterMaskedRotateNativeSequenceLeaseCacheUsage {
        self.usage
    }

    /// Constructs an empty shared lease cache with explicit resident limits.
    #[must_use]
    pub const fn with_limits(
        limits: RegisterMaskedRotateNativeSequenceLeaseCacheLimits,
    ) -> Self {
        Self {
            active: VecDeque::new(),
            limits,
            retired: VecDeque::new(),
            usage: NativeExecutableSequenceCacheUsage::empty(),
        }
    }
}

fn cache_blocked_failure<Adapter>(
    adapter: &mut Adapter,
    context: CacheFailureContext,
    cache: &RegisterMaskedRotateNativeSequenceLeaseCache,
) -> CacheLoadFailure<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let block = RegisterMaskedRotateNativeSequenceLeaseCacheBlock {
        limits: cache.limits,
        retired_keys: cache.retired_keys().cloned().collect(),
        usage: cache.usage,
    };
    cache_candidate_failure(adapter, context, LoadFailureCause::Leases(block))
}

fn cache_candidate_failure<Adapter>(
    adapter: &mut Adapter,
    context: CacheFailureContext,
    cause: LoadFailureCause<Adapter::Error>,
) -> CacheLoadFailure<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let candidate_cleanup_failure =
        context.candidate.sequence.release(adapter).err();
    RegisterMaskedRotateNativeSequenceLeaseCacheLoadFailure {
        candidate_cleanup_failure,
        cause,
        evicted_keys: context.evicted_keys,
        requested_key: context.candidate.key,
        retired_keys: context.retired_keys,
    }
}

fn cache_capacity_failure<Adapter>(
    adapter: &mut Adapter,
    key: RegisterMaskedRotateNativeSequenceKey,
    sequence: LoadedRegisterMaskedRotateNativeSequence,
    error: NativeExecutableSequenceCacheCapacityError,
) -> CacheLoadFailure<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let candidate_cleanup_failure = sequence.release(adapter).err();
    RegisterMaskedRotateNativeSequenceLeaseCacheLoadFailure {
        candidate_cleanup_failure,
        cause: LoadFailureCause::Capacity(error),
        evicted_keys: Vec::new(),
        requested_key: key,
        retired_keys: Vec::new(),
    }
}

fn cache_eviction_failure<Adapter>(
    adapter: &mut Adapter,
    context: CacheFailureContext,
    failure: Box<
        RegisterMaskedRotateNativeSequenceReleaseFailure<Adapter::Error>,
    >,
) -> CacheLoadFailure<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    cache_candidate_failure(
        adapter,
        context,
        LoadFailureCause::Release(failure),
    )
}

fn prepare_cache_candidate<Adapter>(
    adapter: &mut Adapter,
    limits: RegisterMaskedRotateNativeSequenceLeaseCacheLimits,
    key: RegisterMaskedRotateNativeSequenceKey,
    sequence: LoadedRegisterMaskedRotateNativeSequence,
) -> CachePrepareResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let Some(mapped_bytes) = sequence.mapped_bytes() else {
        return Err(Box::new(cache_capacity_failure(
            adapter,
            key,
            sequence,
            NativeExecutableSequenceCacheCapacityError::WeightOverflow,
        )));
    };
    let weight = NativeExecutableSequenceWeight::from_parts(
        mapped_bytes,
        sequence.len(),
    );
    if let Some(error) = limits.candidate_error(weight) {
        return Err(Box::new(cache_capacity_failure(
            adapter, key, sequence, error,
        )));
    }
    Ok(CacheCandidate { key, sequence, weight })
}

fn process_cache_victim<Adapter>(
    adapter: &mut Adapter,
    victim: CacheValue,
) -> CacheVictimOutcome<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    match Arc::try_unwrap(victim.sequence) {
        Err(sequence) => CacheVictimOutcome::Retired(CacheValue {
            key: victim.key,
            sequence,
            weight: victim.weight,
        }),
        Ok(sequence) => match sequence.release(adapter) {
            Ok(()) => CacheVictimOutcome::Released(victim.weight),
            Err(failure) => CacheVictimOutcome::ReleaseFailed {
                failure,
                weight: victim.weight,
            },
        },
    }
}
