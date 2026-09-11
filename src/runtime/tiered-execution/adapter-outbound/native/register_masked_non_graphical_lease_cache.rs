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
//   - Fixed-limit multi-entry FIFO residency for exact non-graphical v6 owners.
// - Must-Not:
//   - Project authority into halt caches/sequences, retire live residents, or
//     refresh FIFO age on hits.
// - Allows:
//   - Inputs: exact non-graphical v6 programs/artifacts, fixed weighted limits,
//     and a memory adapter.
//   - Outputs: cloneable leases, exact usage, eviction/block evidence, and
//     keyed retryable cleanup ownership.
//   - Side effects: executable load/release only through the supplied adapter.
// - Split-When:
//   - Live retirement, invalidation, dynamic reconfiguration, or sequence
//     execution needs independent policy.
// - Merge-When:
//   - One reviewed terminal-kind executable store subsumes parallel caches.
// - Summary:
//   - Reuses exact non-graphical v6 mappings under fixed weighted FIFO limits.
// - Description:
//   - Misses evict the oldest unleased active entries; live leases stay active
//     and charged rather than gaining retirement authority.
// - Usage:
//   - Ensure exact residents and explicitly release unleased cache ownership.
// - Defaults:
//   - Hits and lease clone/drop perform no adapter work.
//

//! Fixed-limit multi-entry lease cache for non-graphical register-masked v6.

use std::collections::VecDeque;
use std::fmt::{Display, Formatter, Result as FormatResult};
use std::num::NonZeroUsize;
use std::sync::Arc;

use malbolge::{ProfileMachineObservation, RegisterMaskedRegionEffectProgram};

use super::direct::VerifiedRegisterMaskedNonGraphicalNativeObjectArtifact;
use super::executable_cache_capacity::{
    NativeExecutableSequenceCacheCapacityError,
    NativeExecutableSequenceCacheLimits, NativeExecutableSequenceCacheUsage,
    NativeExecutableSequenceWeight,
};
use super::invocation::NativeRegionBuffers;
use super::platform::{
    NativeExecutableMemoryAdapter,
    RegisterMaskedNonGraphicalNativeExecutableReleaseFailure,
};
use super::register_masked_resident::{
    RegisterMaskedNativeResidentWeight,
    RegisterMaskedNonGraphicalNativeExecutableOwner,
    RegisterMaskedNonGraphicalNativeOwnerExecutionResult,
    RegisterMaskedNonGraphicalNativeOwnerLoadFailure,
};
use super::runner::RegisterMaskedNonGraphicalNativeRunner;
use crate::execution_cache::NativeArtifactKey;

type OwnerLoadFailure<E> = RegisterMaskedNonGraphicalNativeOwnerLoadFailure<E>;
type EntryReleaseFailure<E> =
    RegisterMaskedNonGraphicalLeaseCacheEntryReleaseFailure<E>;

#[derive(Debug)]
struct CacheValue {
    key: NativeArtifactKey,
    resident: Arc<RegisterMaskedNonGraphicalNativeExecutableOwner>,
    weight: NativeExecutableSequenceWeight,
}

#[derive(Debug)]
struct CacheCandidate {
    key: NativeArtifactKey,
    owner: RegisterMaskedNonGraphicalNativeExecutableOwner,
    weight: NativeExecutableSequenceWeight,
}

/// Caller-owned fixed-limit cache with exact non-graphical v6 leases.
#[derive(Debug)]
pub struct RegisterMaskedNonGraphicalLeaseCache {
    active: VecDeque<CacheValue>,
    limits: NativeExecutableSequenceCacheLimits,
    usage: NativeExecutableSequenceCacheUsage,
}

/// Immutable external ownership of one exact non-graphical v6 resident.
#[derive(Clone, Debug)]
pub struct RegisterMaskedNonGraphicalLease {
    key: NativeArtifactKey,
    resident: Arc<RegisterMaskedNonGraphicalNativeExecutableOwner>,
}

/// Whether one acquisition reused or inserted active lookup state.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum RegisterMaskedNonGraphicalLeaseCacheDisposition {
    /// Exact active identity already existed; FIFO age was unchanged.
    Hit,
    /// One miss was published after oldest-unleased FIFO eviction.
    Inserted {
        /// Every key released from active lookup in eviction order.
        evicted: Vec<NativeArtifactKey>,
    },
}

/// Lease plus exact lookup/eviction evidence for one acquisition.
#[derive(Debug)]
pub struct RegisterMaskedNonGraphicalLeaseCacheAcquisition {
    disposition: RegisterMaskedNonGraphicalLeaseCacheDisposition,
    lease: RegisterMaskedNonGraphicalLease,
}

/// Exact active state preventing one candidate from fitting fixed limits.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RegisterMaskedNonGraphicalLeaseCacheBlock {
    leased_keys: Vec<NativeArtifactKey>,
    limits: NativeExecutableSequenceCacheLimits,
    usage: NativeExecutableSequenceCacheUsage,
}

#[derive(Debug)]
enum LoadFailureCause<E> {
    Capacity(NativeExecutableSequenceCacheCapacityError),
    Leases(RegisterMaskedNonGraphicalLeaseCacheBlock),
    Load(Box<RegisterMaskedNonGraphicalNativeOwnerLoadFailure<E>>),
    Release(RegisterMaskedNonGraphicalNativeExecutableReleaseFailure<E>),
}

/// Failure while loading, weighing, evicting, or publishing one miss.
#[derive(Debug)]
pub struct RegisterMaskedNonGraphicalLeaseCacheLoadFailure<E> {
    candidate_cleanup_failure:
        Option<RegisterMaskedNonGraphicalNativeExecutableReleaseFailure<E>>,
    cause: LoadFailureCause<E>,
    evicted_keys: Vec<NativeArtifactKey>,
    requested_key: NativeArtifactKey,
}

/// One keyed release failure removed from cache ownership for exact retry.
#[derive(Debug)]
pub struct RegisterMaskedNonGraphicalLeaseCacheEntryReleaseFailure<E> {
    failure: RegisterMaskedNonGraphicalNativeExecutableReleaseFailure<E>,
    key: NativeArtifactKey,
}

/// Retry ownership retained after one failed cache insertion.
#[derive(Debug)]
pub struct RegisterMaskedNonGraphicalLeaseCacheLoadReleaseFailures<E> {
    candidate:
        Option<RegisterMaskedNonGraphicalLeaseCacheEntryReleaseFailure<E>>,
    eviction:
        Option<RegisterMaskedNonGraphicalLeaseCacheEntryReleaseFailure<E>>,
}

/// Successful explicit release pass over active cache ownership.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RegisterMaskedNonGraphicalLeaseCacheReleaseSummary {
    released_keys: Vec<NativeArtifactKey>,
    retained_keys: Vec<NativeArtifactKey>,
}

/// Explicit release pass that transferred one or more failures for retry.
#[derive(Debug)]
pub struct RegisterMaskedNonGraphicalLeaseCacheReleaseFailure<E> {
    failures: Vec<RegisterMaskedNonGraphicalLeaseCacheEntryReleaseFailure<E>>,
    released_keys: Vec<NativeArtifactKey>,
    retained_keys: Vec<NativeArtifactKey>,
}

/// Fixed weighted capacity limits for this non-graphical resident cache.
pub type RegisterMaskedNonGraphicalLeaseCacheLimits =
    NativeExecutableSequenceCacheLimits;

/// Exact active resource usage retained by this non-graphical cache.
pub type RegisterMaskedNonGraphicalLeaseCacheUsage =
    NativeExecutableSequenceCacheUsage;

/// Capacity rejection produced by this non-graphical resident cache.
pub type RegisterMaskedNonGraphicalLeaseCacheCapacityError =
    NativeExecutableSequenceCacheCapacityError;

/// Result of acquiring one active immutable non-graphical resident lease.
pub type RegisterMaskedNonGraphicalLeaseCacheLoadResult<E> = Result<
    RegisterMaskedNonGraphicalLeaseCacheAcquisition,
    Box<RegisterMaskedNonGraphicalLeaseCacheLoadFailure<E>>,
>;

type CacheFitResult<E> = Result<
    (CacheCandidate, Vec<NativeArtifactKey>),
    Box<RegisterMaskedNonGraphicalLeaseCacheLoadFailure<E>>,
>;

/// Result of explicitly releasing every currently unleased active resident.
pub type RegisterMaskedNonGraphicalLeaseCacheReleaseResult<E> = Result<
    RegisterMaskedNonGraphicalLeaseCacheReleaseSummary,
    Box<RegisterMaskedNonGraphicalLeaseCacheReleaseFailure<E>>,
>;

impl RegisterMaskedNonGraphicalLease {
    /// Executes through the retained exact mapping without adapter work.
    ///
    /// # Errors
    ///
    /// Returns exact preparation, binding, runner, or completion failure.
    pub fn execute<Runner>(
        &self,
        runner: &mut Runner,
        entry: ProfileMachineObservation,
        buffers: NativeRegionBuffers<'_>,
    ) -> RegisterMaskedNonGraphicalNativeOwnerExecutionResult<Runner::Error>
    where
        Runner: RegisterMaskedNonGraphicalNativeRunner,
    {
        self.resident.execute(runner, entry, buffers)
    }

    /// Returns the exact complete v6 key retained by this lease.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        &self.key
    }

    /// Returns exact mapped bytes and mapping count for this resident.
    #[must_use]
    pub fn resident_weight(&self) -> RegisterMaskedNativeResidentWeight {
        self.resident.resident_weight()
    }

    /// Reports whether two leases share one exact resident allocation.
    #[must_use]
    pub fn shares_resident_with(&self, other: &Self) -> bool {
        Arc::ptr_eq(&self.resident, &other.resident)
    }

    /// Returns all strong owners, including active cache authority.
    #[must_use]
    pub fn strong_owner_count(&self) -> usize {
        Arc::strong_count(&self.resident)
    }
}

impl RegisterMaskedNonGraphicalLeaseCacheDisposition {
    /// Returns every key released from active lookup for this insertion.
    #[must_use]
    pub fn evicted_keys(&self) -> &[NativeArtifactKey] {
        match self {
            Self::Hit => &[],
            Self::Inserted { evicted } => evicted,
        }
    }

    /// Reports whether this acquisition reused exact active lookup state.
    #[must_use]
    pub const fn is_hit(&self) -> bool {
        matches!(self, Self::Hit)
    }
}

impl RegisterMaskedNonGraphicalLeaseCacheAcquisition {
    /// Returns exact lookup/eviction evidence.
    #[must_use]
    pub const fn disposition(
        &self,
    ) -> &RegisterMaskedNonGraphicalLeaseCacheDisposition {
        &self.disposition
    }

    /// Consumes this acquisition and returns its immutable external lease.
    #[must_use]
    pub fn into_lease(self) -> RegisterMaskedNonGraphicalLease {
        self.lease
    }

    /// Returns the immutable lease retained by this acquisition.
    #[must_use]
    pub const fn lease(&self) -> &RegisterMaskedNonGraphicalLease {
        &self.lease
    }
}

impl RegisterMaskedNonGraphicalLeaseCacheBlock {
    /// Returns exact active keys whose external leases prevent eviction.
    #[must_use]
    pub fn leased_keys(&self) -> &[NativeArtifactKey] {
        &self.leased_keys
    }

    /// Returns fixed resident limits that could not admit the candidate.
    #[must_use]
    pub const fn limits(&self) -> RegisterMaskedNonGraphicalLeaseCacheLimits {
        self.limits
    }

    /// Returns exact active resident usage when admission became blocked.
    #[must_use]
    pub const fn usage(&self) -> RegisterMaskedNonGraphicalLeaseCacheUsage {
        self.usage
    }
}

impl<E> RegisterMaskedNonGraphicalLeaseCacheLoadFailure<E> {
    /// Returns resident lease blockage when no unleased victim can make room.
    #[must_use]
    pub const fn block(
        &self,
    ) -> Option<&RegisterMaskedNonGraphicalLeaseCacheBlock> {
        match &self.cause {
            LoadFailureCause::Leases(block) => Some(block),
            LoadFailureCause::Capacity(_)
            | LoadFailureCause::Load(_)
            | LoadFailureCause::Release(_) => None,
        }
    }

    /// Returns candidate cleanup failure, when publication failed after load.
    #[must_use]
    pub const fn candidate_cleanup_failure(
        &self,
    ) -> Option<&RegisterMaskedNonGraphicalNativeExecutableReleaseFailure<E>>
    {
        self.candidate_cleanup_failure.as_ref()
    }

    /// Returns candidate capacity rejection, when it cannot fit alone.
    #[must_use]
    pub const fn capacity_error(
        &self,
    ) -> Option<RegisterMaskedNonGraphicalLeaseCacheCapacityError> {
        match self.cause {
            LoadFailureCause::Capacity(error) => Some(error),
            LoadFailureCause::Leases(_)
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
    ) -> RegisterMaskedNonGraphicalLeaseCacheLoadReleaseFailures<E> {
        let eviction_key = self
            .evicted_keys
            .last()
            .cloned()
            .unwrap_or_else(|| self.requested_key.clone());
        let eviction = match self.cause {
            LoadFailureCause::Release(failure) => {
                Some(RegisterMaskedNonGraphicalLeaseCacheEntryReleaseFailure {
                    failure,
                    key: eviction_key,
                })
            },
            LoadFailureCause::Capacity(_)
            | LoadFailureCause::Leases(_)
            | LoadFailureCause::Load(_) => None,
        };
        let candidate = self.candidate_cleanup_failure.map(|failure| {
            RegisterMaskedNonGraphicalLeaseCacheEntryReleaseFailure {
                failure,
                key: self.requested_key,
            }
        });
        RegisterMaskedNonGraphicalLeaseCacheLoadReleaseFailures {
            candidate,
            eviction,
        }
    }

    /// Returns owner-loading failure before resident state changed.
    #[must_use]
    pub const fn load_failure(
        &self,
    ) -> Option<&RegisterMaskedNonGraphicalNativeOwnerLoadFailure<E>> {
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
    ) -> Option<&RegisterMaskedNonGraphicalNativeExecutableReleaseFailure<E>>
    {
        match &self.cause {
            LoadFailureCause::Release(failure) => Some(failure),
            LoadFailureCause::Capacity(_)
            | LoadFailureCause::Leases(_)
            | LoadFailureCause::Load(_) => None,
        }
    }

    /// Returns exact requested v6 identity whose acquisition failed.
    #[must_use]
    pub const fn requested_key(&self) -> &NativeArtifactKey {
        &self.requested_key
    }
}

impl<E: Display> Display
    for RegisterMaskedNonGraphicalLeaseCacheLoadFailure<E>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str("non-graphical v6 lease cache miss failed: ")?;
        match &self.cause {
            LoadFailureCause::Capacity(error) => {
                write!(f, "capacity: {error}")?;
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

impl<E> RegisterMaskedNonGraphicalLeaseCacheEntryReleaseFailure<E> {
    /// Returns exact executable release ownership retained by this key.
    #[must_use]
    pub const fn failure(
        &self,
    ) -> &RegisterMaskedNonGraphicalNativeExecutableReleaseFailure<E> {
        &self.failure
    }

    /// Consumes this keyed failure and returns exact executable ownership.
    #[must_use]
    pub fn into_failure(
        self,
    ) -> RegisterMaskedNonGraphicalNativeExecutableReleaseFailure<E> {
        self.failure
    }

    /// Returns exact v6 key whose release failed.
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

impl<E> RegisterMaskedNonGraphicalLeaseCacheLoadReleaseFailures<E> {
    /// Returns candidate cleanup failure, when candidate release also failed.
    #[must_use]
    pub const fn candidate_failure(
        &self,
    ) -> Option<&RegisterMaskedNonGraphicalLeaseCacheEntryReleaseFailure<E>>
    {
        self.candidate.as_ref()
    }

    /// Returns FIFO eviction failure, when victim release failed.
    #[must_use]
    pub const fn eviction_failure(
        &self,
    ) -> Option<&RegisterMaskedNonGraphicalLeaseCacheEntryReleaseFailure<E>>
    {
        self.eviction.as_ref()
    }

    /// Consumes this bundle and returns candidate cleanup ownership.
    #[must_use]
    pub fn into_candidate_failure(
        self,
    ) -> Option<RegisterMaskedNonGraphicalLeaseCacheEntryReleaseFailure<E>>
    {
        self.candidate
    }

    /// Consumes this bundle and returns FIFO eviction cleanup ownership.
    #[must_use]
    pub fn into_eviction_failure(
        self,
    ) -> Option<RegisterMaskedNonGraphicalLeaseCacheEntryReleaseFailure<E>>
    {
        self.eviction
    }
}

impl RegisterMaskedNonGraphicalLeaseCacheReleaseSummary {
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

impl<E> RegisterMaskedNonGraphicalLeaseCacheReleaseFailure<E> {
    /// Consumes this result and returns every keyed retry owner.
    #[must_use]
    pub fn into_failures(
        self,
    ) -> Vec<RegisterMaskedNonGraphicalLeaseCacheEntryReleaseFailure<E>> {
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
}

impl<E: Display> Display
    for RegisterMaskedNonGraphicalLeaseCacheReleaseFailure<E>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "non-graphical v6 lease cache release had {} failure(s)",
            self.failures.len()
        )
    }
}

impl RegisterMaskedNonGraphicalLeaseCache {
    fn active_acquisition(
        entry: &CacheValue,
        disposition: RegisterMaskedNonGraphicalLeaseCacheDisposition,
    ) -> RegisterMaskedNonGraphicalLeaseCacheAcquisition {
        RegisterMaskedNonGraphicalLeaseCacheAcquisition {
            disposition,
            lease: RegisterMaskedNonGraphicalLease {
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

    /// Loads or reuses one exact non-graphical resident and returns a lease.
    ///
    /// Hits perform no adapter operations and do not refresh FIFO age. Misses
    /// load completely before the oldest unleased active residents are evicted.
    ///
    /// # Errors
    ///
    /// Returns exact identity/load, capacity, lease-block, or cleanup evidence.
    pub fn ensure<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        program: &RegisterMaskedRegionEffectProgram,
        artifact: &VerifiedRegisterMaskedNonGraphicalNativeObjectArtifact,
    ) -> RegisterMaskedNonGraphicalLeaseCacheLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let key = artifact.key().clone();
        if let Some(entry) = self.active.iter().find(|entry| entry.key == key)
            && entry.resident.program() == program
            && entry.resident.artifact() == artifact
        {
            return Ok(Self::active_acquisition(
                entry,
                RegisterMaskedNonGraphicalLeaseCacheDisposition::Hit,
            ));
        }
        if self.position(&key).is_some() {
            let failure = Box::new(OwnerLoadFailure::ArtifactIdentity);
            return Err(Box::new(
                RegisterMaskedNonGraphicalLeaseCacheLoadFailure {
                    candidate_cleanup_failure: None,
                    cause: LoadFailureCause::Load(failure),
                    evicted_keys: Vec::new(),
                    requested_key: key,
                },
            ));
        }
        let owner = RegisterMaskedNonGraphicalNativeExecutableOwner::load(
            adapter, program, artifact,
        )
        .map_err(|failure| {
            Box::new(RegisterMaskedNonGraphicalLeaseCacheLoadFailure {
                candidate_cleanup_failure: None,
                cause: LoadFailureCause::Load(failure),
                evicted_keys: Vec::new(),
                requested_key: key.clone(),
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
        while self.limits.projected_exceeds(self.usage, candidate.weight) {
            let Some(index) = self.oldest_unleased_position() else {
                return Err(Box::new(blocked_failure(
                    adapter,
                    candidate,
                    evicted_keys,
                    self,
                )));
            };
            let Some(victim) = self.active.remove(index) else {
                return Err(Box::new(blocked_failure(
                    adapter,
                    candidate,
                    evicted_keys,
                    self,
                )));
            };
            let CacheValue {
                key: victim_key,
                resident: victim_resident,
                weight,
            } = victim;
            let victim_owner = match Arc::try_unwrap(victim_resident) {
                Ok(victim_owner) => victim_owner,
                Err(recovered_resident) => {
                    self.active.insert(index, CacheValue {
                        key: victim_key,
                        resident: recovered_resident,
                        weight,
                    });
                    return Err(Box::new(blocked_failure(
                        adapter,
                        candidate,
                        evicted_keys,
                        self,
                    )));
                },
            };
            self.usage.remove(weight);
            evicted_keys.push(victim_key);
            if let Err(failure) = victim_owner.release(adapter) {
                let candidate_cleanup_failure =
                    candidate.owner.release(adapter).err().map(|item| *item);
                return Err(Box::new(
                    RegisterMaskedNonGraphicalLeaseCacheLoadFailure {
                        candidate_cleanup_failure,
                        cause: LoadFailureCause::Release(*failure),
                        evicted_keys,
                        requested_key: candidate.key,
                    },
                ));
            }
        }
        Ok((candidate, evicted_keys))
    }

    /// Returns whether no active resident remains under cache authority.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.active.is_empty()
    }

    /// Returns active exact keys in FIFO insertion order.
    pub fn keys(&self) -> impl Iterator<Item = &NativeArtifactKey> {
        self.active.iter().map(|entry| &entry.key)
    }

    /// Returns every caller-selected fixed resident capacity limit.
    #[must_use]
    pub const fn limits(&self) -> RegisterMaskedNonGraphicalLeaseCacheLimits {
        self.limits
    }

    /// Constructs an empty cache with an entry-only limit.
    #[must_use]
    pub const fn new(capacity: NonZeroUsize) -> Self {
        Self::with_limits(NativeExecutableSequenceCacheLimits::new(capacity))
    }

    fn oldest_unleased_position(&self) -> Option<usize> {
        self.active
            .iter()
            .position(|entry| Arc::strong_count(&entry.resident) == 1)
    }

    fn position(&self, key: &NativeArtifactKey) -> Option<usize> {
        self.active.iter().position(|entry| entry.key == *key)
    }

    fn publish_candidate<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        key: NativeArtifactKey,
        owner: RegisterMaskedNonGraphicalNativeExecutableOwner,
    ) -> RegisterMaskedNonGraphicalLeaseCacheLoadResult<Adapter::Error>
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
        let (candidate, evicted_keys) =
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
        Ok(RegisterMaskedNonGraphicalLeaseCacheAcquisition {
            disposition:
                RegisterMaskedNonGraphicalLeaseCacheDisposition::Inserted {
                    evicted: evicted_keys,
                },
            lease: RegisterMaskedNonGraphicalLease {
                key: candidate.key,
                resident,
            },
        })
    }

    /// Releases every unleased active resident, retaining live leased entries.
    ///
    /// Release failures transfer exact mapping ownership out of this cache.
    ///
    /// # Errors
    ///
    /// Returns all keyed retry owners after attempting every unleased entry.
    pub fn release_all<Adapter>(
        &mut self,
        adapter: &mut Adapter,
    ) -> RegisterMaskedNonGraphicalLeaseCacheReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let entries = self.active.len();
        let mut failures = Vec::new();
        let mut released_keys = Vec::new();
        let mut retained_keys = Vec::new();
        for _ in 0..entries {
            let Some(entry) = self.active.pop_front() else {
                break;
            };
            let key = entry.key;
            let weight = entry.weight;
            match Arc::try_unwrap(entry.resident) {
                Err(resident) => {
                    retained_keys.push(key.clone());
                    self.active.push_back(CacheValue { key, resident, weight });
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
        if failures.is_empty() {
            Ok(RegisterMaskedNonGraphicalLeaseCacheReleaseSummary {
                released_keys,
                retained_keys,
            })
        } else {
            Err(Box::new(
                RegisterMaskedNonGraphicalLeaseCacheReleaseFailure {
                    failures,
                    released_keys,
                    retained_keys,
                },
            ))
        }
    }

    /// Returns exact active resident resource usage.
    #[must_use]
    pub const fn usage(&self) -> RegisterMaskedNonGraphicalLeaseCacheUsage {
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
            usage: NativeExecutableSequenceCacheUsage::empty(),
        }
    }
}

fn blocked_failure<Adapter>(
    adapter: &mut Adapter,
    candidate: CacheCandidate,
    evicted_keys: Vec<NativeArtifactKey>,
    cache: &RegisterMaskedNonGraphicalLeaseCache,
) -> RegisterMaskedNonGraphicalLeaseCacheLoadFailure<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let block = RegisterMaskedNonGraphicalLeaseCacheBlock {
        leased_keys: cache
            .active
            .iter()
            .filter(|entry| Arc::strong_count(&entry.resident) > 1)
            .map(|entry| entry.key.clone())
            .collect(),
        limits: cache.limits,
        usage: cache.usage,
    };
    let requested_key = candidate.key;
    let candidate_cleanup_failure =
        candidate.owner.release(adapter).err().map(|item| *item);
    RegisterMaskedNonGraphicalLeaseCacheLoadFailure {
        candidate_cleanup_failure,
        cause: LoadFailureCause::Leases(block),
        evicted_keys,
        requested_key,
    }
}

fn capacity_failure<Adapter>(
    adapter: &mut Adapter,
    key: NativeArtifactKey,
    owner: RegisterMaskedNonGraphicalNativeExecutableOwner,
    error: NativeExecutableSequenceCacheCapacityError,
) -> RegisterMaskedNonGraphicalLeaseCacheLoadFailure<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let candidate_cleanup_failure =
        owner.release(adapter).err().map(|item| *item);
    RegisterMaskedNonGraphicalLeaseCacheLoadFailure {
        candidate_cleanup_failure,
        cause: LoadFailureCause::Capacity(error),
        evicted_keys: Vec::new(),
        requested_key: key,
    }
}
