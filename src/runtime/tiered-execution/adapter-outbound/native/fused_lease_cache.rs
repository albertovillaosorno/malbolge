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
//   - Weighted FIFO residency and limit publication for exact fused owners.
// - Must-Not:
//   - Project authority into halt caches/sequences, reconcile retirement
//     implicitly on hit/miss, or refresh FIFO age on hits.
// - Allows:
//   - Inputs: exact fused native artifacts, published limits, and a memory
//     adapter.
//   - Outputs: cloneable leases, active/retired residency, eviction/block
//     evidence, and keyed retryable cleanup ownership.
//   - Side effects: executable load/release only through the supplied adapter.
// - Split-When:
//   - Sequence execution or asynchronous lease waiting needs independent
//     policy.
// - Merge-When:
//   - One reviewed terminal-kind executable store subsumes parallel caches.
// - Summary:
//   - Reuses exact fused native mappings under explicit weighted limits.
// - Description:
//   - Active lookup and retired leased residency are separate queues whose
//     exact weights share one published capacity account.
// - Usage:
//   - Ensure residents, reconfigure limits, invalidate, return/reconcile
//     leases, and release all explicitly.
// - Defaults:
//   - Hits and lease clone/drop perform no adapter work.
//

//! Weighted multi-entry lease cache for fused direct native executables.

#[path = "fused_lease_cache/reconfiguration.rs"]
mod reconfiguration;

use std::collections::VecDeque;
use std::fmt::{Display, Formatter, Result as FormatResult};
use std::num::NonZeroUsize;
use std::sync::Arc;

pub use reconfiguration::{
    DirectFusedNativeLeaseCacheReconfiguration,
    DirectFusedNativeLeaseCacheReconfigurationFailure,
    DirectFusedNativeLeaseCacheReconfigurationResult,
};

use super::direct::VerifiedDirectFusedSequenceObjectArtifact;
use super::executable_cache_capacity::{
    NativeExecutableSequenceCacheCapacityError,
    NativeExecutableSequenceCacheLimits, NativeExecutableSequenceCacheUsage,
    NativeExecutableSequenceWeight,
};
use super::fused_resident::{
    DirectFusedNativeExecutableOwner, DirectFusedNativeOwnerExecutionResult,
    DirectFusedNativeOwnerLoadFailure, DirectFusedNativeResidentWeight,
};
use super::invocation::NativeRegionBuffers;
use super::platform::{
    DirectFusedNativeExecutableReleaseFailure, NativeExecutableMemoryAdapter,
};
use super::runner::DirectFusedNativeRunner;
use crate::execution_cache::NativeArtifactKey;

type EntryReleaseFailure<E> = DirectFusedNativeLeaseCacheEntryReleaseFailure<E>;

type CacheInvalidation = DirectFusedNativeLeaseCacheInvalidation;

type CacheReconfigurationResult<E> =
    DirectFusedNativeLeaseCacheReconfigurationResult<E>;

#[derive(Debug)]
struct CacheValue {
    key: NativeArtifactKey,
    resident: Arc<DirectFusedNativeExecutableOwner>,
    weight: NativeExecutableSequenceWeight,
}

#[derive(Debug)]
struct CacheCandidate {
    key: NativeArtifactKey,
    owner: DirectFusedNativeExecutableOwner,
    weight: NativeExecutableSequenceWeight,
}

#[derive(Debug)]
struct CacheEvictionContext {
    candidate: CacheCandidate,
    evicted_keys: Vec<NativeArtifactKey>,
    retired_keys: Vec<NativeArtifactKey>,
}

#[derive(Debug)]
enum CacheVictimOutcome<E> {
    ReleaseFailed {
        failure: DirectFusedNativeExecutableReleaseFailure<E>,
        weight: NativeExecutableSequenceWeight,
    },
    Released(NativeExecutableSequenceWeight),
    Retired(Box<CacheValue>),
}

/// Caller-owned fixed-limit cache with exact fused native leases.
#[derive(Debug)]
pub struct DirectFusedNativeLeaseCache {
    active: VecDeque<CacheValue>,
    limits: NativeExecutableSequenceCacheLimits,
    retired: VecDeque<CacheValue>,
    usage: NativeExecutableSequenceCacheUsage,
}

/// Immutable external ownership of one exact fused native resident.
#[derive(Clone, Debug)]
pub struct DirectFusedNativeLease {
    key: NativeArtifactKey,
    resident: Arc<DirectFusedNativeExecutableOwner>,
}

/// Whether one acquisition reused or inserted active lookup state.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum DirectFusedNativeLeaseCacheDisposition {
    /// Exact active identity already existed; FIFO age was unchanged.
    Hit,
    /// One miss was published after oldest-first active FIFO processing.
    Inserted {
        /// Every key removed from active lookup in FIFO order.
        evicted: Vec<NativeArtifactKey>,
        /// Removed keys still resident behind external leases.
        retired: Vec<NativeArtifactKey>,
    },
}

/// Lease plus exact lookup/eviction evidence for one acquisition.
#[derive(Debug)]
pub struct DirectFusedNativeLeaseCacheAcquisition {
    disposition: DirectFusedNativeLeaseCacheDisposition,
    lease: DirectFusedNativeLease,
}

/// Exact resident state preventing one candidate from fitting fixed limits.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DirectFusedNativeLeaseCacheBlock {
    limits: NativeExecutableSequenceCacheLimits,
    retired_keys: Vec<NativeArtifactKey>,
    usage: NativeExecutableSequenceCacheUsage,
}

#[derive(Debug)]
enum LoadFailureCause<E> {
    Capacity(NativeExecutableSequenceCacheCapacityError),
    Identity,
    Leases(DirectFusedNativeLeaseCacheBlock),
    Load(Box<DirectFusedNativeOwnerLoadFailure<E>>),
    Release(DirectFusedNativeExecutableReleaseFailure<E>),
}

/// Failure while loading, weighing, evicting, or publishing one miss.
#[derive(Debug)]
pub struct DirectFusedNativeLeaseCacheLoadFailure<E> {
    candidate_cleanup_failure:
        Option<DirectFusedNativeExecutableReleaseFailure<E>>,
    cause: LoadFailureCause<E>,
    evicted_keys: Vec<NativeArtifactKey>,
    requested_key: NativeArtifactKey,
    retired_keys: Vec<NativeArtifactKey>,
}

/// Result of invalidating one exact active fused resident.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectFusedNativeLeaseCacheInvalidation {
    /// No active key matched the request.
    Missing,
    /// The unleased resident released immediately.
    Released,
    /// Lookup authority ended while external leases retained the mapping.
    Retired {
        /// External lease owners remaining after retirement.
        leases: usize,
    },
}

/// One keyed release failure removed from cache ownership for exact retry.
#[derive(Debug)]
pub struct DirectFusedNativeLeaseCacheEntryReleaseFailure<E> {
    failure: DirectFusedNativeExecutableReleaseFailure<E>,
    key: NativeArtifactKey,
}

/// Retry ownership retained after one failed cache insertion.
#[derive(Debug)]
pub struct DirectFusedNativeLeaseCacheLoadReleaseFailures<E> {
    candidate: Option<DirectFusedNativeLeaseCacheEntryReleaseFailure<E>>,
    eviction: Option<DirectFusedNativeLeaseCacheEntryReleaseFailure<E>>,
}

/// Successful reclamation pass over cache-owned fused residents.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DirectFusedNativeLeaseCacheReleaseSummary {
    released_keys: Vec<NativeArtifactKey>,
    retained_keys: Vec<NativeArtifactKey>,
}

/// Reclamation pass that transferred one or more failures for retry.
#[derive(Debug)]
pub struct DirectFusedNativeLeaseCacheReleaseFailure<E> {
    failures: Vec<DirectFusedNativeLeaseCacheEntryReleaseFailure<E>>,
    released_keys: Vec<NativeArtifactKey>,
    retained_keys: Vec<NativeArtifactKey>,
}

/// Fixed weighted capacity limits for this fused resident cache.
pub type DirectFusedNativeLeaseCacheLimits =
    NativeExecutableSequenceCacheLimits;

/// Exact active-plus-retired resource usage retained by this cache.
pub type DirectFusedNativeLeaseCacheUsage = NativeExecutableSequenceCacheUsage;

/// Capacity rejection produced by this fused resident cache.
pub type DirectFusedNativeLeaseCacheCapacityError =
    NativeExecutableSequenceCacheCapacityError;

/// Result of acquiring one active immutable fused resident lease.
pub type DirectFusedNativeLeaseCacheLoadResult<E> = Result<
    DirectFusedNativeLeaseCacheAcquisition,
    Box<DirectFusedNativeLeaseCacheLoadFailure<E>>,
>;

type CacheFitResult<E> = Result<
    (
        CacheCandidate,
        Vec<NativeArtifactKey>,
        Vec<NativeArtifactKey>,
    ),
    Box<DirectFusedNativeLeaseCacheLoadFailure<E>>,
>;

/// Result of invalidating one exact active fused resident.
pub type DirectFusedNativeLeaseCacheInvalidationResult<E> = Result<
    DirectFusedNativeLeaseCacheInvalidation,
    Box<DirectFusedNativeLeaseCacheEntryReleaseFailure<E>>,
>;

/// Result of reconciling retired fused residents.
pub type DirectFusedNativeLeaseCacheReconciliationResult<E> =
    DirectFusedNativeLeaseCacheReleaseResult<E>;

/// Result of reclaiming cache-owned fused residents.
pub type DirectFusedNativeLeaseCacheReleaseResult<E> = Result<
    DirectFusedNativeLeaseCacheReleaseSummary,
    Box<DirectFusedNativeLeaseCacheReleaseFailure<E>>,
>;

impl DirectFusedNativeLease {
    /// Executes through the retained exact mapping without adapter work.
    ///
    /// # Errors
    ///
    /// Returns exact preparation, binding, runner, or completion failure.
    pub fn execute<Runner>(
        &self,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> DirectFusedNativeOwnerExecutionResult<Runner::Error>
    where
        Runner: DirectFusedNativeRunner,
    {
        self.resident.execute(runner, buffers)
    }

    /// Returns the exact complete fused key retained by this lease.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        &self.key
    }

    /// Returns exact mapped bytes and mapping count for this resident.
    #[must_use]
    pub fn resident_weight(&self) -> DirectFusedNativeResidentWeight {
        self.resident.resident_weight()
    }

    /// Reports whether two leases share one exact resident allocation.
    #[must_use]
    pub fn shares_resident_with(&self, other: &Self) -> bool {
        Arc::ptr_eq(&self.resident, &other.resident)
    }

    /// Returns all strong owners, including active or retired cache authority.
    #[must_use]
    pub fn strong_owner_count(&self) -> usize {
        Arc::strong_count(&self.resident)
    }
}

impl DirectFusedNativeLeaseCacheDisposition {
    /// Returns every key removed from active lookup for this insertion.
    #[must_use]
    pub fn evicted_keys(&self) -> &[NativeArtifactKey] {
        match self {
            Self::Hit => &[],
            Self::Inserted { evicted, .. } => evicted,
        }
    }

    /// Reports whether this acquisition reused exact active lookup state.
    #[must_use]
    pub const fn is_hit(&self) -> bool {
        matches!(self, Self::Hit)
    }

    /// Returns removed keys still resident behind external leases.
    #[must_use]
    pub fn retired_keys(&self) -> &[NativeArtifactKey] {
        match self {
            Self::Hit => &[],
            Self::Inserted { retired, .. } => retired,
        }
    }
}

impl DirectFusedNativeLeaseCacheAcquisition {
    /// Returns exact lookup/eviction evidence.
    #[must_use]
    pub const fn disposition(&self) -> &DirectFusedNativeLeaseCacheDisposition {
        &self.disposition
    }

    /// Consumes this acquisition and returns its immutable external lease.
    #[must_use]
    pub fn into_lease(self) -> DirectFusedNativeLease {
        self.lease
    }

    /// Returns the immutable lease retained by this acquisition.
    #[must_use]
    pub const fn lease(&self) -> &DirectFusedNativeLease {
        &self.lease
    }
}

impl DirectFusedNativeLeaseCacheBlock {
    /// Returns fixed resident limits that could not admit the candidate.
    #[must_use]
    pub const fn limits(&self) -> DirectFusedNativeLeaseCacheLimits {
        self.limits
    }

    /// Returns retired keys whose mappings still count against capacity.
    #[must_use]
    pub fn retired_keys(&self) -> &[NativeArtifactKey] {
        &self.retired_keys
    }

    /// Returns exact resident usage when admission became blocked.
    #[must_use]
    pub const fn usage(&self) -> DirectFusedNativeLeaseCacheUsage {
        self.usage
    }
}

impl<E> DirectFusedNativeLeaseCacheLoadFailure<E> {
    /// Returns lease blockage when retired weight prevents candidate admission.
    #[must_use]
    pub const fn block(&self) -> Option<&DirectFusedNativeLeaseCacheBlock> {
        match &self.cause {
            LoadFailureCause::Leases(block) => Some(block),
            LoadFailureCause::Capacity(_)
            | LoadFailureCause::Identity
            | LoadFailureCause::Load(_)
            | LoadFailureCause::Release(_) => None,
        }
    }

    /// Returns candidate cleanup failure, when publication failed after load.
    #[must_use]
    pub const fn candidate_cleanup_failure(
        &self,
    ) -> Option<&DirectFusedNativeExecutableReleaseFailure<E>> {
        self.candidate_cleanup_failure.as_ref()
    }

    /// Returns candidate capacity rejection, when it cannot fit alone.
    #[must_use]
    pub const fn capacity_error(
        &self,
    ) -> Option<DirectFusedNativeLeaseCacheCapacityError> {
        match self.cause {
            LoadFailureCause::Capacity(error) => Some(error),
            LoadFailureCause::Identity
            | LoadFailureCause::Leases(_)
            | LoadFailureCause::Load(_)
            | LoadFailureCause::Release(_) => None,
        }
    }

    /// Returns every key released from active lookup before failure.
    #[must_use]
    pub fn evicted_keys(&self) -> &[NativeArtifactKey] {
        &self.evicted_keys
    }

    /// Consumes this failure and returns every retryable release owner.
    #[must_use]
    pub fn into_release_failures(
        self,
    ) -> DirectFusedNativeLeaseCacheLoadReleaseFailures<E> {
        let eviction_key = self
            .evicted_keys
            .last()
            .cloned()
            .unwrap_or_else(|| self.requested_key.clone());
        let eviction = match self.cause {
            LoadFailureCause::Release(failure) => {
                Some(DirectFusedNativeLeaseCacheEntryReleaseFailure {
                    failure,
                    key: eviction_key,
                })
            },
            LoadFailureCause::Capacity(_)
            | LoadFailureCause::Identity
            | LoadFailureCause::Leases(_)
            | LoadFailureCause::Load(_) => None,
        };
        let candidate = self.candidate_cleanup_failure.map(|failure| {
            DirectFusedNativeLeaseCacheEntryReleaseFailure {
                failure,
                key: self.requested_key,
            }
        });
        DirectFusedNativeLeaseCacheLoadReleaseFailures { candidate, eviction }
    }

    /// Returns owner-loading failure before resident state changed.
    #[must_use]
    pub const fn load_failure(
        &self,
    ) -> Option<&DirectFusedNativeOwnerLoadFailure<E>> {
        match &self.cause {
            LoadFailureCause::Load(failure) => Some(failure),
            LoadFailureCause::Capacity(_)
            | LoadFailureCause::Identity
            | LoadFailureCause::Leases(_)
            | LoadFailureCause::Release(_) => None,
        }
    }

    /// Returns failed FIFO victim release ownership, when present.
    #[must_use]
    pub const fn release_failure(
        &self,
    ) -> Option<&DirectFusedNativeExecutableReleaseFailure<E>> {
        match &self.cause {
            LoadFailureCause::Release(failure) => Some(failure),
            LoadFailureCause::Capacity(_)
            | LoadFailureCause::Identity
            | LoadFailureCause::Leases(_)
            | LoadFailureCause::Load(_) => None,
        }
    }

    /// Returns exact requested fused identity whose acquisition failed.
    #[must_use]
    pub const fn requested_key(&self) -> &NativeArtifactKey {
        &self.requested_key
    }

    /// Returns removed keys still resident behind external leases.
    #[must_use]
    pub fn retired_keys(&self) -> &[NativeArtifactKey] {
        &self.retired_keys
    }
}

impl<E: Display> Display for DirectFusedNativeLeaseCacheLoadFailure<E> {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str("fused native lease cache miss failed: ")?;
        match &self.cause {
            LoadFailureCause::Capacity(error) => {
                write!(f, "capacity: {error}")?;
            },
            LoadFailureCause::Identity => {
                f.write_str("exact fused artifact identity drifted")?;
            },
            LoadFailureCause::Leases(_) => {
                f.write_str("live resident leases block fixed capacity")?;
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

impl<E> DirectFusedNativeLeaseCacheEntryReleaseFailure<E> {
    /// Returns exact executable release ownership retained by this key.
    #[must_use]
    pub const fn failure(
        &self,
    ) -> &DirectFusedNativeExecutableReleaseFailure<E> {
        &self.failure
    }

    /// Consumes this keyed failure and returns exact executable ownership.
    #[must_use]
    pub fn into_failure(self) -> DirectFusedNativeExecutableReleaseFailure<E> {
        self.failure
    }

    /// Returns exact fused key whose release failed.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        &self.key
    }

    /// Retries this exact keyed release without losing ownership on failure.
    ///
    /// # Errors
    ///
    /// Returns refreshed keyed ownership when the adapter fails again.
    pub fn retry<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> Result<NativeArtifactKey, Box<Self>>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = E>,
    {
        let key = self.key;
        match self.failure.retry(adapter) {
            Ok(()) => Ok(key),
            Err(failure) => Err(Box::new(Self { failure, key })),
        }
    }
}

impl<E> DirectFusedNativeLeaseCacheLoadReleaseFailures<E> {
    /// Returns candidate cleanup failure, when candidate release also failed.
    #[must_use]
    pub const fn candidate_failure(
        &self,
    ) -> Option<&DirectFusedNativeLeaseCacheEntryReleaseFailure<E>> {
        self.candidate.as_ref()
    }

    /// Returns FIFO eviction failure, when victim release failed.
    #[must_use]
    pub const fn eviction_failure(
        &self,
    ) -> Option<&DirectFusedNativeLeaseCacheEntryReleaseFailure<E>> {
        self.eviction.as_ref()
    }

    /// Consumes this bundle and returns candidate cleanup ownership.
    #[must_use]
    pub fn into_candidate_failure(
        self,
    ) -> Option<DirectFusedNativeLeaseCacheEntryReleaseFailure<E>> {
        self.candidate
    }

    /// Consumes this bundle and returns FIFO eviction cleanup ownership.
    #[must_use]
    pub fn into_eviction_failure(
        self,
    ) -> Option<DirectFusedNativeLeaseCacheEntryReleaseFailure<E>> {
        self.eviction
    }

    /// Retries every executable still owned outside cache authority.
    ///
    /// # Errors
    ///
    /// Returns aggregate retained ownership after attempting every failure.
    pub fn retry<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> DirectFusedNativeLeaseCacheReconciliationResult<E>
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
        retry_keyed_release_failures(
            adapter,
            DirectFusedNativeLeaseCacheReleaseFailure {
                failures,
                released_keys: Vec::new(),
                retained_keys: Vec::new(),
            },
        )
    }
}

impl DirectFusedNativeLeaseCacheReleaseSummary {
    /// Returns keys released by this explicit pass.
    #[must_use]
    pub fn released_keys(&self) -> &[NativeArtifactKey] {
        &self.released_keys
    }

    /// Returns keys retained because external leases still exist.
    #[must_use]
    pub fn retained_keys(&self) -> &[NativeArtifactKey] {
        &self.retained_keys
    }
}

impl<E> DirectFusedNativeLeaseCacheReleaseFailure<E> {
    /// Returns every keyed release failure retained outside cache authority.
    #[must_use]
    pub fn failures(
        &self,
    ) -> &[DirectFusedNativeLeaseCacheEntryReleaseFailure<E>] {
        &self.failures
    }

    /// Consumes this result and returns every keyed retry owner.
    #[must_use]
    pub fn into_failures(
        self,
    ) -> Vec<DirectFusedNativeLeaseCacheEntryReleaseFailure<E>> {
        self.failures
    }

    /// Returns keys released before or after failed releases in this pass.
    #[must_use]
    pub fn released_keys(&self) -> &[NativeArtifactKey] {
        &self.released_keys
    }

    /// Returns keys retained because external leases still exist.
    #[must_use]
    pub fn retained_keys(&self) -> &[NativeArtifactKey] {
        &self.retained_keys
    }

    /// Retries every failed release removed from cache ownership.
    ///
    /// # Errors
    ///
    /// Returns only repeated keyed failures after attempting every owner.
    pub fn retry<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> DirectFusedNativeLeaseCacheReconciliationResult<E>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = E>,
    {
        retry_keyed_release_failures(adapter, self)
    }
}

impl<E: Display> Display for DirectFusedNativeLeaseCacheReleaseFailure<E> {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "fused native lease cache release had {} failure(s)",
            self.failures.len()
        )
    }
}

impl DirectFusedNativeLeaseCache {
    fn active_acquisition(
        entry: &CacheValue,
        disposition: DirectFusedNativeLeaseCacheDisposition,
    ) -> DirectFusedNativeLeaseCacheAcquisition {
        DirectFusedNativeLeaseCacheAcquisition {
            disposition,
            lease: DirectFusedNativeLease {
                key: entry.key.clone(),
                resident: Arc::clone(&entry.resident),
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

    /// Returns whether one exact key has active lookup authority.
    #[must_use]
    pub fn contains_key(&self, key: &NativeArtifactKey) -> bool {
        self.position(key).is_some()
    }

    /// Loads or reuses one exact fused resident and returns a lease.
    ///
    /// Hits perform no adapter operations and do not refresh FIFO age. Misses
    /// load completely before active FIFO release-or-retirement processing.
    ///
    /// # Errors
    ///
    /// Returns exact identity/load, capacity, lease-block, or cleanup evidence.
    pub fn ensure<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        artifact: &VerifiedDirectFusedSequenceObjectArtifact,
    ) -> DirectFusedNativeLeaseCacheLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let key = artifact.key().clone();
        if let Some(entry) = self.active.iter().find(|entry| entry.key == key)
            && entry.resident.artifact() == artifact
        {
            return Ok(Self::active_acquisition(
                entry,
                DirectFusedNativeLeaseCacheDisposition::Hit,
            ));
        }
        if self.position(&key).is_some() {
            return Err(Box::new(DirectFusedNativeLeaseCacheLoadFailure {
                candidate_cleanup_failure: None,
                cause: LoadFailureCause::Identity,
                evicted_keys: Vec::new(),
                requested_key: key,
                retired_keys: Vec::new(),
            }));
        }
        let owner = DirectFusedNativeExecutableOwner::load(adapter, artifact)
            .map_err(|failure| {
            Box::new(DirectFusedNativeLeaseCacheLoadFailure {
                candidate_cleanup_failure: None,
                cause: LoadFailureCause::Load(failure),
                evicted_keys: Vec::new(),
                requested_key: key.clone(),
                retired_keys: Vec::new(),
            })
        })?;
        self.publish_candidate(adapter, key, owner)
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
                return Err(Box::new(blocked_failure(
                    adapter,
                    CacheEvictionContext {
                        candidate,
                        evicted_keys,
                        retired_keys,
                    },
                    self,
                )));
            };
            evicted_keys.push(victim.key.clone());
            match process_victim(adapter, victim) {
                CacheVictimOutcome::Released(weight) => {
                    self.usage.remove(weight);
                },
                CacheVictimOutcome::ReleaseFailed { failure, weight } => {
                    self.usage.remove(weight);
                    let candidate_cleanup_failure = candidate
                        .owner
                        .release(adapter)
                        .err()
                        .map(|item| *item);
                    return Err(Box::new(
                        DirectFusedNativeLeaseCacheLoadFailure {
                            candidate_cleanup_failure,
                            cause: LoadFailureCause::Release(failure),
                            evicted_keys,
                            requested_key: candidate.key,
                            retired_keys,
                        },
                    ));
                },
                CacheVictimOutcome::Retired(entry) => {
                    retired_keys.push(entry.key.clone());
                    self.retired.push_back(*entry);
                },
            }
        }
        Ok((candidate, evicted_keys, retired_keys))
    }

    /// Invalidates one exact active key, releasing or retiring its resident.
    ///
    /// # Errors
    ///
    /// Returns keyed retryable release ownership when an unleased resident
    /// cannot release.
    pub fn invalidate_key<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        key: &NativeArtifactKey,
    ) -> DirectFusedNativeLeaseCacheInvalidationResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let Some(index) = self.position(key) else {
            return Ok(CacheInvalidation::Missing);
        };
        let Some(entry) = self.active.remove(index) else {
            return Ok(CacheInvalidation::Missing);
        };
        let leases = Arc::strong_count(&entry.resident).saturating_sub(1);
        match Arc::try_unwrap(entry.resident) {
            Ok(owner) => {
                self.usage.remove(entry.weight);
                owner
                    .release(adapter)
                    .map(|()| CacheInvalidation::Released)
                    .map_err(|failure| {
                        Box::new(EntryReleaseFailure {
                            failure: *failure,
                            key: entry.key,
                        })
                    })
            },
            Err(resident) => {
                self.retired.push_back(CacheValue {
                    key: entry.key,
                    resident,
                    weight: entry.weight,
                });
                Ok(CacheInvalidation::Retired { leases })
            },
        }
    }

    /// Returns whether no active or retired resident remains.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.active.is_empty() && self.retired.is_empty()
    }

    /// Returns active exact keys in FIFO insertion order.
    pub fn keys(&self) -> impl Iterator<Item = &NativeArtifactKey> {
        self.active.iter().map(|entry| &entry.key)
    }

    /// Returns every caller-selected fixed resident capacity limit.
    #[must_use]
    pub const fn limits(&self) -> DirectFusedNativeLeaseCacheLimits {
        self.limits
    }

    /// Constructs an empty cache with an entry-only limit.
    #[must_use]
    pub const fn new(capacity: NonZeroUsize) -> Self {
        Self::with_limits(NativeExecutableSequenceCacheLimits::new(capacity))
    }

    fn position(&self, key: &NativeArtifactKey) -> Option<usize> {
        self.active.iter().position(|entry| entry.key == *key)
    }

    fn publish_candidate<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        key: NativeArtifactKey,
        owner: DirectFusedNativeExecutableOwner,
    ) -> DirectFusedNativeLeaseCacheLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let resident_weight = owner.resident_weight();
        let weight = NativeExecutableSequenceWeight::from_parts(
            resident_weight.mapped_bytes(),
            resident_weight.mappings(),
        );
        if let Some(error) = self.limits.candidate_error(weight) {
            return Err(Box::new(capacity_failure(adapter, key, owner, error)));
        }
        let prepared_candidate = CacheCandidate { key, owner, weight };
        let (candidate, evicted_keys, retired_keys) =
            self.evict_until_fits(adapter, prepared_candidate)?;
        if let Err(error) = self.usage.add(candidate.weight) {
            return Err(Box::new(capacity_failure(
                adapter,
                candidate.key,
                candidate.owner,
                error,
            )));
        }
        let resident = Arc::new(candidate.owner);
        self.active.push_back(CacheValue {
            key: candidate.key.clone(),
            resident: Arc::clone(&resident),
            weight: candidate.weight,
        });
        Ok(DirectFusedNativeLeaseCacheAcquisition {
            disposition: DirectFusedNativeLeaseCacheDisposition::Inserted {
                evicted: evicted_keys,
                retired: retired_keys,
            },
            lease: DirectFusedNativeLease {
                key: candidate.key,
                resident,
            },
        })
    }

    /// Reclaims every retired resident whose final external lease has gone.
    ///
    /// # Errors
    ///
    /// Returns keyed release failures after attempting every releasable entry.
    pub fn reconcile_retired<Adapter>(
        &mut self,
        adapter: &mut Adapter,
    ) -> DirectFusedNativeLeaseCacheReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let mut failures = Vec::new();
        let mut released_keys = Vec::new();
        let mut retained_keys = Vec::new();
        let entries = self.retired.len();
        for _ in 0..entries {
            let Some(entry) = self.retired.pop_front() else {
                break;
            };
            let key = entry.key;
            let weight = entry.weight;
            match Arc::try_unwrap(entry.resident) {
                Err(resident) => {
                    retained_keys.push(key.clone());
                    self.retired.push_back(CacheValue {
                        key,
                        resident,
                        weight,
                    });
                },
                Ok(owner) => {
                    self.usage.remove(weight);
                    match owner.release(adapter) {
                        Ok(()) => released_keys.push(key),
                        Err(failure) => failures.push(EntryReleaseFailure {
                            failure: *failure,
                            key,
                        }),
                    }
                },
            }
        }
        reconciliation_result(released_keys, retained_keys, failures)
    }

    /// Publishes new weighted resident limits after active FIFO processing.
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
    ) -> CacheReconfigurationResult<Adapter::Error>
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
    /// Live leased mappings move to retirement without losing their weight.
    ///
    /// # Errors
    ///
    /// Returns keyed release failures after attempting every releasable entry.
    pub fn release_all<Adapter>(
        &mut self,
        adapter: &mut Adapter,
    ) -> DirectFusedNativeLeaseCacheReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        self.retired.extend(self.active.drain(..));
        self.reconcile_retired(adapter)
    }

    /// Returns total active plus retired resident count.
    #[must_use]
    pub fn resident_len(&self) -> usize {
        self.active.len().saturating_add(self.retired.len())
    }

    /// Returns retired keys in original FIFO order.
    pub fn retired_keys(&self) -> impl Iterator<Item = &NativeArtifactKey> {
        self.retired.iter().map(|entry| &entry.key)
    }

    /// Returns the number of retired residents awaiting lease reclamation.
    #[must_use]
    pub fn retired_len(&self) -> usize {
        self.retired.len()
    }

    /// Consumes one lease then reconciles all retired residents explicitly.
    ///
    /// # Errors
    ///
    /// Returns keyed release failures after attempting every releasable entry.
    pub fn return_lease<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        lease: DirectFusedNativeLease,
    ) -> DirectFusedNativeLeaseCacheReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        drop(lease);
        self.reconcile_retired(adapter)
    }

    /// Consumes exact leases together, then reconciles retired residents once.
    ///
    /// Active lookup authority remains active. Only residents already retired
    /// before this call can release after all supplied external owners drop.
    ///
    /// # Errors
    ///
    /// Returns keyed release failures after attempting every releasable retired
    /// resident.
    pub fn return_leases<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        leases: Vec<DirectFusedNativeLease>,
    ) -> DirectFusedNativeLeaseCacheReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        drop(leases);
        self.reconcile_retired(adapter)
    }

    /// Returns exact active plus retired resident resource usage.
    #[must_use]
    pub const fn usage(&self) -> DirectFusedNativeLeaseCacheUsage {
        self.usage
    }

    /// Constructs an empty cache with explicit fixed weighted limits.
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

fn blocked_failure<Adapter>(
    adapter: &mut Adapter,
    context: CacheEvictionContext,
    cache: &DirectFusedNativeLeaseCache,
) -> DirectFusedNativeLeaseCacheLoadFailure<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let block = DirectFusedNativeLeaseCacheBlock {
        limits: cache.limits,
        retired_keys: cache
            .retired
            .iter()
            .map(|entry| entry.key.clone())
            .collect(),
        usage: cache.usage,
    };
    let requested_key = context.candidate.key;
    let candidate_cleanup_failure = context
        .candidate
        .owner
        .release(adapter)
        .err()
        .map(|item| *item);
    DirectFusedNativeLeaseCacheLoadFailure {
        candidate_cleanup_failure,
        cause: LoadFailureCause::Leases(block),
        evicted_keys: context.evicted_keys,
        requested_key,
        retired_keys: context.retired_keys,
    }
}

fn capacity_failure<Adapter>(
    adapter: &mut Adapter,
    key: NativeArtifactKey,
    owner: DirectFusedNativeExecutableOwner,
    error: NativeExecutableSequenceCacheCapacityError,
) -> DirectFusedNativeLeaseCacheLoadFailure<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let candidate_cleanup_failure =
        owner.release(adapter).err().map(|item| *item);
    DirectFusedNativeLeaseCacheLoadFailure {
        candidate_cleanup_failure,
        cause: LoadFailureCause::Capacity(error),
        evicted_keys: Vec::new(),
        requested_key: key,
        retired_keys: Vec::new(),
    }
}

fn process_victim<Adapter>(
    adapter: &mut Adapter,
    victim: CacheValue,
) -> CacheVictimOutcome<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    match Arc::try_unwrap(victim.resident) {
        Err(resident) => CacheVictimOutcome::Retired(Box::new(CacheValue {
            key: victim.key,
            resident,
            weight: victim.weight,
        })),
        Ok(owner) => match owner.release(adapter) {
            Ok(()) => CacheVictimOutcome::Released(victim.weight),
            Err(failure) => CacheVictimOutcome::ReleaseFailed {
                failure: *failure,
                weight: victim.weight,
            },
        },
    }
}

fn reconciliation_result<E>(
    released_keys: Vec<NativeArtifactKey>,
    retained_keys: Vec<NativeArtifactKey>,
    failures: Vec<EntryReleaseFailure<E>>,
) -> DirectFusedNativeLeaseCacheReconciliationResult<E> {
    if failures.is_empty() {
        Ok(DirectFusedNativeLeaseCacheReleaseSummary {
            released_keys,
            retained_keys,
        })
    } else {
        Err(Box::new(DirectFusedNativeLeaseCacheReleaseFailure {
            failures,
            released_keys,
            retained_keys,
        }))
    }
}

fn retry_keyed_release_failures<Adapter>(
    adapter: &mut Adapter,
    pending: DirectFusedNativeLeaseCacheReleaseFailure<Adapter::Error>,
) -> DirectFusedNativeLeaseCacheReconciliationResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let mut failures = Vec::new();
    let mut released_keys = pending.released_keys;
    for entry in pending.failures {
        let key = entry.key;
        match entry.failure.retry(adapter) {
            Ok(()) => released_keys.push(key),
            Err(failure) => failures.push(EntryReleaseFailure { failure, key }),
        }
    }
    reconciliation_result(released_keys, pending.retained_keys, failures)
}
