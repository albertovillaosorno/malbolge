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
//   - Multi-entry weighted FIFO residency for exact register-masked v6 owners.
// - Must-Not:
//   - Project v6 authority into legacy/v5 types, refresh FIFO age on hits, or
//     release mappings while external leases remain.
// - Allows:
//   - Inputs: exact v6 programs/artifacts, fixed weighted limits, and a memory
//     adapter.
//   - Outputs: cloneable leases, active/retired residency, eviction evidence,
//     and keyed retryable cleanup ownership.
//   - Side effects: executable load/release only through the supplied adapter.
// - Split-When:
//   - Dynamic limit reconfiguration or durable/cross-process residency gains
//     independent ownership.
// - Merge-When:
//   - One general register-masked executable store subsumes single and
//     multi-entry residency.
// - Summary:
//   - Reuses exact v6 mappings under weighted FIFO limits without revoking live
//     leases.
// - Description:
//   - Active lookup and retired leased residency are separate queues whose
//     exact weights share one capacity account.
// - Usage:
//   - Ensure exact residents, return/drop leases, reconcile retired mappings,
//     and release all explicitly.
// - Defaults:
//   - Hits and lease clone/drop perform no adapter work; eviction is oldest
//     active first.
//

//! Weighted multi-entry FIFO lease cache for register-masked v6 executables.

use std::collections::VecDeque;
use std::fmt::{Display, Formatter, Result as FormatResult};
use std::num::NonZeroUsize;
use std::sync::Arc;

use malbolge::{ProfileMachineObservation, RegisterMaskedRegionEffectProgram};

use super::direct::VerifiedRegisterMaskedHaltFetchNativeObjectArtifact;
use super::executable_cache_capacity::{
    NativeExecutableSequenceCacheCapacityError,
    NativeExecutableSequenceCacheLimits, NativeExecutableSequenceCacheUsage,
    NativeExecutableSequenceWeight,
};
use super::invocation::NativeRegionBuffers;
use super::platform::{
    NativeExecutableMemoryAdapter, RegisterMaskedNativeExecutableReleaseFailure,
};
use super::register_masked_resident::{
    RegisterMaskedNativeExecutableOwner,
    RegisterMaskedNativeOwnerExecutionResult,
    RegisterMaskedNativeOwnerLoadFailure,
};
use super::runner::RegisterMaskedNativeRunner;
use crate::execution_cache::NativeArtifactKey;

#[derive(Debug)]
struct RegisterMaskedNativeLeaseCacheValue {
    key: NativeArtifactKey,
    resident: Arc<RegisterMaskedNativeExecutableOwner>,
    weight: NativeExecutableSequenceWeight,
}

#[derive(Debug)]
struct RegisterMaskedNativeLeaseCacheCandidate {
    key: NativeArtifactKey,
    owner: RegisterMaskedNativeExecutableOwner,
    weight: NativeExecutableSequenceWeight,
}

#[derive(Debug)]
struct RegisterMaskedNativeLeaseCacheEvictionContext {
    candidate: RegisterMaskedNativeLeaseCacheCandidate,
    evicted_keys: Vec<NativeArtifactKey>,
    retired_keys: Vec<NativeArtifactKey>,
}

#[derive(Debug)]
enum RegisterMaskedNativeLeaseCacheVictimOutcome<E> {
    ReleaseFailed {
        failure: RegisterMaskedNativeExecutableReleaseFailure<E>,
        weight: NativeExecutableSequenceWeight,
    },
    Released(NativeExecutableSequenceWeight),
    Retired(Box<RegisterMaskedNativeLeaseCacheValue>),
}

/// Caller-owned weighted FIFO cache with cloneable exact v6 resident leases.
#[derive(Debug)]
pub struct RegisterMaskedNativeLeaseCache {
    active: VecDeque<RegisterMaskedNativeLeaseCacheValue>,
    limits: NativeExecutableSequenceCacheLimits,
    retired: VecDeque<RegisterMaskedNativeLeaseCacheValue>,
    usage: NativeExecutableSequenceCacheUsage,
}

/// Immutable external ownership of one exact register-masked resident.
#[derive(Clone, Debug)]
pub struct RegisterMaskedNativeLease {
    key: NativeArtifactKey,
    resident: Arc<RegisterMaskedNativeExecutableOwner>,
}

/// Whether one multi-entry acquisition reused or inserted active lookup state.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum RegisterMaskedNativeLeaseCacheDisposition {
    /// Exact active identity already existed; FIFO age was unchanged.
    Hit,
    /// One miss was published after oldest-first resident processing.
    Inserted {
        /// Every key removed from active lookup in FIFO order.
        evicted: Vec<NativeArtifactKey>,
        /// Removed keys still resident behind external leases.
        retired: Vec<NativeArtifactKey>,
    },
}

/// Lease plus exact lookup/eviction evidence for one v6 acquisition.
#[derive(Debug)]
pub struct RegisterMaskedNativeLeaseCacheAcquisition {
    disposition: RegisterMaskedNativeLeaseCacheDisposition,
    lease: RegisterMaskedNativeLease,
}

/// Exact resident state preventing one candidate from fitting fixed limits.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RegisterMaskedNativeLeaseCacheBlock {
    limits: NativeExecutableSequenceCacheLimits,
    retired_keys: Vec<NativeArtifactKey>,
    usage: NativeExecutableSequenceCacheUsage,
}

#[derive(Debug)]
enum RegisterMaskedNativeLeaseCacheLoadFailureCause<E> {
    Capacity(NativeExecutableSequenceCacheCapacityError),
    Leases(RegisterMaskedNativeLeaseCacheBlock),
    Load(Box<RegisterMaskedNativeOwnerLoadFailure<E>>),
    Release(RegisterMaskedNativeExecutableReleaseFailure<E>),
}

/// Failure while loading, weighing, evicting, or publishing one v6 miss.
#[derive(Debug)]
pub struct RegisterMaskedNativeLeaseCacheLoadFailure<E> {
    candidate_cleanup_failure:
        Option<RegisterMaskedNativeExecutableReleaseFailure<E>>,
    cause: RegisterMaskedNativeLeaseCacheLoadFailureCause<E>,
    evicted_keys: Vec<NativeArtifactKey>,
    requested_key: NativeArtifactKey,
    retired_keys: Vec<NativeArtifactKey>,
}

/// Result of invalidating one exact active v6 resident.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RegisterMaskedNativeLeaseCacheInvalidation {
    /// No active key matched the request.
    Missing,
    /// The unleased resident released immediately.
    Released,
    /// Lookup authority ended while external leases kept the mapping resident.
    Retired {
        /// External lease owners remaining after retirement.
        leases: usize,
    },
}

/// One keyed release failure removed from cache ownership for exact retry.
#[derive(Debug)]
pub struct RegisterMaskedNativeLeaseCacheEntryReleaseFailure<E> {
    failure: RegisterMaskedNativeExecutableReleaseFailure<E>,
    key: NativeArtifactKey,
}

/// Successful reclamation pass over retired v6 residents.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RegisterMaskedNativeLeaseCacheReconciliation {
    released_keys: Vec<NativeArtifactKey>,
    retained_keys: Vec<NativeArtifactKey>,
}

/// Aggregate reclamation failure after attempting every releasable resident.
#[derive(Debug)]
pub struct RegisterMaskedNativeLeaseCacheReleaseFailure<E> {
    failures: Vec<RegisterMaskedNativeLeaseCacheEntryReleaseFailure<E>>,
    released_keys: Vec<NativeArtifactKey>,
    retained_keys: Vec<NativeArtifactKey>,
}

/// Release owners retained after one failed cache insertion.
#[derive(Debug)]
pub struct RegisterMaskedNativeLeaseCacheLoadReleaseFailures<E> {
    candidate: Option<RegisterMaskedNativeLeaseCacheEntryReleaseFailure<E>>,
    eviction: Option<RegisterMaskedNativeLeaseCacheEntryReleaseFailure<E>>,
}

/// Fixed weighted capacity limits for the multi-entry v6 resident cache.
pub type RegisterMaskedNativeLeaseCacheLimits =
    NativeExecutableSequenceCacheLimits;

/// Exact active-plus-retired resource usage retained by the v6 cache.
pub type RegisterMaskedNativeLeaseCacheUsage =
    NativeExecutableSequenceCacheUsage;

/// Capacity rejection produced by the multi-entry v6 resident cache.
pub type RegisterMaskedNativeLeaseCacheCapacityError =
    NativeExecutableSequenceCacheCapacityError;

/// Result of acquiring one active immutable v6 resident lease.
pub type RegisterMaskedNativeLeaseCacheLoadResult<E> = Result<
    RegisterMaskedNativeLeaseCacheAcquisition,
    Box<RegisterMaskedNativeLeaseCacheLoadFailure<E>>,
>;

type RegisterMaskedNativeLeaseCacheFitResult<E> = Result<
    (
        RegisterMaskedNativeLeaseCacheCandidate,
        Vec<NativeArtifactKey>,
        Vec<NativeArtifactKey>,
    ),
    Box<RegisterMaskedNativeLeaseCacheLoadFailure<E>>,
>;

/// Result of invalidating one exact active resident.
pub type RegisterMaskedNativeLeaseCacheInvalidationResult<E> = Result<
    RegisterMaskedNativeLeaseCacheInvalidation,
    Box<RegisterMaskedNativeLeaseCacheEntryReleaseFailure<E>>,
>;

/// Result of reconciling retired register-masked residents.
pub type RegisterMaskedNativeLeaseCacheReconciliationResult<E> = Result<
    RegisterMaskedNativeLeaseCacheReconciliation,
    Box<RegisterMaskedNativeLeaseCacheReleaseFailure<E>>,
>;

impl RegisterMaskedNativeLease {
    /// Executes through the retained exact v6 mapping without adapter work.
    ///
    /// # Errors
    ///
    /// Returns exact preparation, runner, or completion failure.
    pub fn execute<Runner>(
        &self,
        runner: &mut Runner,
        entry: ProfileMachineObservation,
        buffers: NativeRegionBuffers<'_>,
    ) -> RegisterMaskedNativeOwnerExecutionResult<Runner::Error>
    where
        Runner: RegisterMaskedNativeRunner,
    {
        self.resident.execute(runner, entry, buffers)
    }

    /// Returns the exact complete v6 native key retained by this lease.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        &self.key
    }

    /// Returns exact mapped bytes and mapping count for this resident.
    #[must_use]
    pub fn resident_weight(
        &self,
    ) -> super::register_masked_resident::RegisterMaskedNativeResidentWeight
    {
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

impl RegisterMaskedNativeLeaseCacheDisposition {
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

impl RegisterMaskedNativeLeaseCacheAcquisition {
    /// Returns exact lookup/eviction evidence.
    #[must_use]
    pub const fn disposition(
        &self,
    ) -> &RegisterMaskedNativeLeaseCacheDisposition {
        &self.disposition
    }

    /// Consumes this acquisition and returns its immutable external lease.
    #[must_use]
    pub fn into_lease(self) -> RegisterMaskedNativeLease {
        self.lease
    }

    /// Returns the immutable lease retained by this acquisition.
    #[must_use]
    pub const fn lease(&self) -> &RegisterMaskedNativeLease {
        &self.lease
    }
}

impl RegisterMaskedNativeLeaseCacheBlock {
    /// Returns fixed resident limits that could not admit the candidate.
    #[must_use]
    pub const fn limits(&self) -> RegisterMaskedNativeLeaseCacheLimits {
        self.limits
    }

    /// Returns retired keys whose mappings still count against capacity.
    #[must_use]
    pub fn retired_keys(&self) -> &[NativeArtifactKey] {
        &self.retired_keys
    }

    /// Returns exact resident usage when admission became blocked.
    #[must_use]
    pub const fn usage(&self) -> RegisterMaskedNativeLeaseCacheUsage {
        self.usage
    }
}

impl<E> RegisterMaskedNativeLeaseCacheLoadFailure<E> {
    /// Returns resident lease blockage, when no active FIFO victim remains.
    #[must_use]
    pub const fn block(&self) -> Option<&RegisterMaskedNativeLeaseCacheBlock> {
        match &self.cause {
            RegisterMaskedNativeLeaseCacheLoadFailureCause::Leases(block) => {
                Some(block)
            },
            RegisterMaskedNativeLeaseCacheLoadFailureCause::Capacity(_)
            | RegisterMaskedNativeLeaseCacheLoadFailureCause::Load(_)
            | RegisterMaskedNativeLeaseCacheLoadFailureCause::Release(_) => {
                None
            },
        }
    }

    /// Returns candidate cleanup failure, when publication failed after load.
    #[must_use]
    pub const fn candidate_cleanup_failure(
        &self,
    ) -> Option<&RegisterMaskedNativeExecutableReleaseFailure<E>> {
        self.candidate_cleanup_failure.as_ref()
    }

    /// Returns candidate capacity rejection, when it cannot fit alone.
    #[must_use]
    pub const fn capacity_error(
        &self,
    ) -> Option<RegisterMaskedNativeLeaseCacheCapacityError> {
        match self.cause {
            RegisterMaskedNativeLeaseCacheLoadFailureCause::Capacity(error) => {
                Some(error)
            },
            RegisterMaskedNativeLeaseCacheLoadFailureCause::Leases(_)
            | RegisterMaskedNativeLeaseCacheLoadFailureCause::Load(_)
            | RegisterMaskedNativeLeaseCacheLoadFailureCause::Release(_) => {
                None
            },
        }
    }

    /// Returns every key removed from active lookup before failure.
    #[must_use]
    pub fn evicted_keys(&self) -> &[NativeArtifactKey] {
        &self.evicted_keys
    }

    /// Consumes this failure and returns every retryable release owner.
    #[must_use]
    pub fn into_release_failures(
        self,
    ) -> RegisterMaskedNativeLeaseCacheLoadReleaseFailures<E> {
        let eviction_key = self
            .evicted_keys
            .last()
            .cloned()
            .unwrap_or_else(|| self.requested_key.clone());
        let eviction = match self.cause {
            RegisterMaskedNativeLeaseCacheLoadFailureCause::Release(
                failure,
            ) => Some(RegisterMaskedNativeLeaseCacheEntryReleaseFailure {
                failure,
                key: eviction_key,
            }),
            RegisterMaskedNativeLeaseCacheLoadFailureCause::Capacity(_)
            | RegisterMaskedNativeLeaseCacheLoadFailureCause::Leases(_)
            | RegisterMaskedNativeLeaseCacheLoadFailureCause::Load(_) => None,
        };
        let candidate = self.candidate_cleanup_failure.map(|failure| {
            RegisterMaskedNativeLeaseCacheEntryReleaseFailure {
                failure,
                key: self.requested_key,
            }
        });
        RegisterMaskedNativeLeaseCacheLoadReleaseFailures {
            candidate,
            eviction,
        }
    }

    /// Returns owner-loading failure before resident state changed.
    #[must_use]
    pub const fn load_failure(
        &self,
    ) -> Option<&RegisterMaskedNativeOwnerLoadFailure<E>> {
        match &self.cause {
            RegisterMaskedNativeLeaseCacheLoadFailureCause::Load(failure) => {
                Some(failure)
            },
            RegisterMaskedNativeLeaseCacheLoadFailureCause::Capacity(_)
            | RegisterMaskedNativeLeaseCacheLoadFailureCause::Leases(_)
            | RegisterMaskedNativeLeaseCacheLoadFailureCause::Release(_) => {
                None
            },
        }
    }

    /// Returns failed FIFO victim release ownership, when present.
    #[must_use]
    pub const fn release_failure(
        &self,
    ) -> Option<&RegisterMaskedNativeExecutableReleaseFailure<E>> {
        match &self.cause {
            RegisterMaskedNativeLeaseCacheLoadFailureCause::Release(
                failure,
            ) => Some(failure),
            RegisterMaskedNativeLeaseCacheLoadFailureCause::Capacity(_)
            | RegisterMaskedNativeLeaseCacheLoadFailureCause::Leases(_)
            | RegisterMaskedNativeLeaseCacheLoadFailureCause::Load(_) => None,
        }
    }

    /// Returns exact requested v6 identity whose acquisition failed.
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

impl<E: Display> Display for RegisterMaskedNativeLeaseCacheLoadFailure<E> {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str("register-masked v6 lease cache miss failed: ")?;
        match &self.cause {
            RegisterMaskedNativeLeaseCacheLoadFailureCause::Capacity(error) => {
                write!(f, "capacity: {error}")?;
            },
            RegisterMaskedNativeLeaseCacheLoadFailureCause::Leases(_) => {
                f.write_str("resident leases block weighted capacity")?;
            },
            RegisterMaskedNativeLeaseCacheLoadFailureCause::Load(error) => {
                write!(f, "load: {error}")?;
            },
            RegisterMaskedNativeLeaseCacheLoadFailureCause::Release(error) => {
                write!(f, "eviction release: {error}")?;
            },
        }
        if self.candidate_cleanup_failure.is_some() {
            f.write_str("; candidate cleanup also failed")?;
        }
        Ok(())
    }
}

impl<E> RegisterMaskedNativeLeaseCacheEntryReleaseFailure<E> {
    /// Returns exact executable release ownership retained by this key.
    #[must_use]
    pub const fn failure(
        &self,
    ) -> &RegisterMaskedNativeExecutableReleaseFailure<E> {
        &self.failure
    }

    /// Consumes this keyed failure and returns exact executable ownership.
    #[must_use]
    pub fn into_failure(
        self,
    ) -> RegisterMaskedNativeExecutableReleaseFailure<E> {
        self.failure
    }

    /// Returns exact v6 key whose release failed.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        &self.key
    }
}

impl RegisterMaskedNativeLeaseCacheReconciliation {
    /// Returns retired keys released during this reconciliation pass.
    #[must_use]
    pub fn released_keys(&self) -> &[NativeArtifactKey] {
        &self.released_keys
    }

    /// Returns retired keys still resident behind external leases.
    #[must_use]
    pub fn retained_keys(&self) -> &[NativeArtifactKey] {
        &self.retained_keys
    }
}

impl<E> RegisterMaskedNativeLeaseCacheReleaseFailure<E> {
    /// Returns every keyed release failure retained outside cache authority.
    #[must_use]
    pub fn failures(
        &self,
    ) -> &[RegisterMaskedNativeLeaseCacheEntryReleaseFailure<E>] {
        &self.failures
    }

    /// Returns keys released before or during this failed pass.
    #[must_use]
    pub fn released_keys(&self) -> &[NativeArtifactKey] {
        &self.released_keys
    }

    /// Returns retired keys still resident behind external leases.
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
    ) -> RegisterMaskedNativeLeaseCacheReconciliationResult<E>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = E>,
    {
        retry_keyed_release_failures(adapter, self)
    }
}

impl<E: Display> Display for RegisterMaskedNativeLeaseCacheReleaseFailure<E> {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "register-masked v6 lease cache retained {} failed releases",
            self.failures.len(),
        )
    }
}

impl<E> RegisterMaskedNativeLeaseCacheLoadReleaseFailures<E> {
    /// Returns failed candidate cleanup ownership, when present.
    #[must_use]
    pub fn candidate_failure(
        &self,
    ) -> Option<&RegisterMaskedNativeExecutableReleaseFailure<E>> {
        self.candidate
            .as_ref()
            .map(RegisterMaskedNativeLeaseCacheEntryReleaseFailure::failure)
    }

    /// Returns failed FIFO victim release ownership, when present.
    #[must_use]
    pub fn eviction_failure(
        &self,
    ) -> Option<&RegisterMaskedNativeExecutableReleaseFailure<E>> {
        self.eviction
            .as_ref()
            .map(RegisterMaskedNativeLeaseCacheEntryReleaseFailure::failure)
    }

    /// Retries every executable still owned outside the leased cache.
    ///
    /// # Errors
    ///
    /// Returns aggregate retained ownership after attempting every failure.
    pub fn retry<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> RegisterMaskedNativeLeaseCacheReconciliationResult<E>
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
            RegisterMaskedNativeLeaseCacheReleaseFailure {
                failures,
                released_keys: Vec::new(),
                retained_keys: Vec::new(),
            },
        )
    }
}

impl RegisterMaskedNativeLeaseCache {
    fn active_acquisition(
        entry: &RegisterMaskedNativeLeaseCacheValue,
        disposition: RegisterMaskedNativeLeaseCacheDisposition,
    ) -> RegisterMaskedNativeLeaseCacheAcquisition {
        RegisterMaskedNativeLeaseCacheAcquisition {
            disposition,
            lease: RegisterMaskedNativeLease {
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

    /// Loads or reuses one exact v6 resident and returns a cloneable lease.
    ///
    /// Hits perform no executable-memory adapter operations and do not refresh
    /// FIFO age. Misses load completely before weighted eviction begins.
    ///
    /// # Errors
    ///
    /// Returns exact identity/load, capacity, lease-block, or cleanup evidence.
    pub fn ensure<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        program: &RegisterMaskedRegionEffectProgram,
        artifact: &VerifiedRegisterMaskedHaltFetchNativeObjectArtifact,
    ) -> RegisterMaskedNativeLeaseCacheLoadResult<Adapter::Error>
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
                RegisterMaskedNativeLeaseCacheDisposition::Hit,
            ));
        }
        if self.position(&key).is_some() {
            let failure = Box::new(
                RegisterMaskedNativeOwnerLoadFailure::ArtifactIdentity,
            );
            return Err(Box::new(RegisterMaskedNativeLeaseCacheLoadFailure {
                candidate_cleanup_failure: None,
                cause: RegisterMaskedNativeLeaseCacheLoadFailureCause::Load(
                    failure,
                ),
                evicted_keys: Vec::new(),
                requested_key: key,
                retired_keys: Vec::new(),
            }));
        }
        let owner = RegisterMaskedNativeExecutableOwner::load(
            adapter, program, artifact,
        )
        .map_err(|failure| {
            Box::new(RegisterMaskedNativeLeaseCacheLoadFailure {
                candidate_cleanup_failure: None,
                cause: RegisterMaskedNativeLeaseCacheLoadFailureCause::Load(
                    failure,
                ),
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
        candidate: RegisterMaskedNativeLeaseCacheCandidate,
    ) -> RegisterMaskedNativeLeaseCacheFitResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let mut evicted_keys = Vec::new();
        let mut retired_keys = Vec::new();
        while self.limits.projected_exceeds(self.usage, candidate.weight) {
            let Some(victim) = self.active.pop_front() else {
                let context = RegisterMaskedNativeLeaseCacheEvictionContext {
                    candidate,
                    evicted_keys,
                    retired_keys,
                };
                return Err(Box::new(blocked_failure(adapter, context, self)));
            };
            evicted_keys.push(victim.key.clone());
            match process_victim(adapter, victim) {
                RegisterMaskedNativeLeaseCacheVictimOutcome::Released(
                    weight,
                ) => {
                    self.usage.remove(weight);
                },
                RegisterMaskedNativeLeaseCacheVictimOutcome::ReleaseFailed {
                    failure,
                    weight,
                } => {
                    self.usage.remove(weight);
                    let candidate_cleanup_failure = candidate
                        .owner
                        .release(adapter)
                        .err()
                        .map(|item| *item);
                    let cause =
                        RegisterMaskedNativeLeaseCacheLoadFailureCause::Release(
                            failure,
                        );
                    return Err(Box::new(
                        RegisterMaskedNativeLeaseCacheLoadFailure {
                            candidate_cleanup_failure,
                            cause,
                            evicted_keys,
                            requested_key: candidate.key,
                            retired_keys,
                        },
                    ));
                },
                RegisterMaskedNativeLeaseCacheVictimOutcome::Retired(entry) => {
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
    ) -> RegisterMaskedNativeLeaseCacheInvalidationResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let Some(index) = self.position(key) else {
            return Ok(RegisterMaskedNativeLeaseCacheInvalidation::Missing);
        };
        let Some(entry) = self.active.remove(index) else {
            return Ok(RegisterMaskedNativeLeaseCacheInvalidation::Missing);
        };
        let leases = Arc::strong_count(&entry.resident).saturating_sub(1);
        match Arc::try_unwrap(entry.resident) {
            Ok(owner) => {
                self.usage.remove(entry.weight);
                owner
                    .release(adapter)
                    .map(|()| {
                        RegisterMaskedNativeLeaseCacheInvalidation::Released
                    })
                    .map_err(|failure| {
                        Box::new(
                            RegisterMaskedNativeLeaseCacheEntryReleaseFailure {
                                failure: *failure,
                                key: entry.key,
                            },
                        )
                    })
            },
            Err(resident) => {
                self.retired.push_back(RegisterMaskedNativeLeaseCacheValue {
                    key: entry.key,
                    resident,
                    weight: entry.weight,
                });
                Ok(RegisterMaskedNativeLeaseCacheInvalidation::Retired {
                    leases,
                })
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
    pub const fn limits(&self) -> RegisterMaskedNativeLeaseCacheLimits {
        self.limits
    }

    /// Constructs an empty multi-entry v6 cache with an entry-only limit.
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
        owner: RegisterMaskedNativeExecutableOwner,
    ) -> RegisterMaskedNativeLeaseCacheLoadResult<Adapter::Error>
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
        let prepared_candidate =
            RegisterMaskedNativeLeaseCacheCandidate { key, owner, weight };
        let (candidate, evicted, retired) =
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
        self.active.push_back(RegisterMaskedNativeLeaseCacheValue {
            key: candidate.key.clone(),
            resident: Arc::clone(&resident),
            weight: candidate.weight,
        });
        Ok(RegisterMaskedNativeLeaseCacheAcquisition {
            disposition: RegisterMaskedNativeLeaseCacheDisposition::Inserted {
                evicted,
                retired,
            },
            lease: RegisterMaskedNativeLease {
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
    ) -> RegisterMaskedNativeLeaseCacheReconciliationResult<Adapter::Error>
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
                    self.retired.push_back(
                        RegisterMaskedNativeLeaseCacheValue {
                            key,
                            resident,
                            weight,
                        },
                    );
                },
                Ok(owner) => {
                    self.usage.remove(weight);
                    match owner.release(adapter) {
                        Ok(()) => released_keys.push(key),
                        Err(failure) => failures.push(
                            RegisterMaskedNativeLeaseCacheEntryReleaseFailure {
                                failure: *failure,
                                key,
                            },
                        ),
                    }
                },
            }
        }
        reconciliation_result(released_keys, retained_keys, failures)
    }

    /// Removes all active lookup authority and reclaims every unleased
    /// resident.
    ///
    /// # Errors
    ///
    /// Returns keyed release failures after attempting every releasable entry.
    pub fn release_all<Adapter>(
        &mut self,
        adapter: &mut Adapter,
    ) -> RegisterMaskedNativeLeaseCacheReconciliationResult<Adapter::Error>
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
        lease: RegisterMaskedNativeLease,
    ) -> RegisterMaskedNativeLeaseCacheReconciliationResult<Adapter::Error>
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

    /// Constructs an empty multi-entry v6 cache with explicit fixed limits.
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
    context: RegisterMaskedNativeLeaseCacheEvictionContext,
    cache: &RegisterMaskedNativeLeaseCache,
) -> RegisterMaskedNativeLeaseCacheLoadFailure<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let block = RegisterMaskedNativeLeaseCacheBlock {
        limits: cache.limits,
        retired_keys: cache
            .retired
            .iter()
            .map(|entry| entry.key.clone())
            .collect(),
        usage: cache.usage,
    };
    let candidate_cleanup_failure = context
        .candidate
        .owner
        .release(adapter)
        .err()
        .map(|item| *item);
    RegisterMaskedNativeLeaseCacheLoadFailure {
        candidate_cleanup_failure,
        cause: RegisterMaskedNativeLeaseCacheLoadFailureCause::Leases(block),
        evicted_keys: context.evicted_keys,
        requested_key: context.candidate.key,
        retired_keys: context.retired_keys,
    }
}

fn capacity_failure<Adapter>(
    adapter: &mut Adapter,
    key: NativeArtifactKey,
    owner: RegisterMaskedNativeExecutableOwner,
    error: NativeExecutableSequenceCacheCapacityError,
) -> RegisterMaskedNativeLeaseCacheLoadFailure<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let candidate_cleanup_failure =
        owner.release(adapter).err().map(|item| *item);
    RegisterMaskedNativeLeaseCacheLoadFailure {
        candidate_cleanup_failure,
        cause: RegisterMaskedNativeLeaseCacheLoadFailureCause::Capacity(error),
        evicted_keys: Vec::new(),
        requested_key: key,
        retired_keys: Vec::new(),
    }
}

fn process_victim<Adapter>(
    adapter: &mut Adapter,
    victim: RegisterMaskedNativeLeaseCacheValue,
) -> RegisterMaskedNativeLeaseCacheVictimOutcome<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    match Arc::try_unwrap(victim.resident) {
        Err(resident) => RegisterMaskedNativeLeaseCacheVictimOutcome::Retired(
            Box::new(RegisterMaskedNativeLeaseCacheValue {
                key: victim.key,
                resident,
                weight: victim.weight,
            }),
        ),
        Ok(owner) => match owner.release(adapter) {
            Ok(()) => RegisterMaskedNativeLeaseCacheVictimOutcome::Released(
                victim.weight,
            ),
            Err(failure) => {
                RegisterMaskedNativeLeaseCacheVictimOutcome::ReleaseFailed {
                    failure: *failure,
                    weight: victim.weight,
                }
            },
        },
    }
}

fn reconciliation_result<E>(
    released_keys: Vec<NativeArtifactKey>,
    retained_keys: Vec<NativeArtifactKey>,
    failures: Vec<RegisterMaskedNativeLeaseCacheEntryReleaseFailure<E>>,
) -> RegisterMaskedNativeLeaseCacheReconciliationResult<E> {
    if failures.is_empty() {
        Ok(RegisterMaskedNativeLeaseCacheReconciliation {
            released_keys,
            retained_keys,
        })
    } else {
        Err(Box::new(RegisterMaskedNativeLeaseCacheReleaseFailure {
            failures,
            released_keys,
            retained_keys,
        }))
    }
}

fn retry_keyed_release_failures<Adapter>(
    adapter: &mut Adapter,
    pending: RegisterMaskedNativeLeaseCacheReleaseFailure<Adapter::Error>,
) -> RegisterMaskedNativeLeaseCacheReconciliationResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let mut failures = Vec::new();
    let mut released_keys = pending.released_keys;
    for entry in pending.failures {
        let key = entry.key;
        match entry.failure.retry(adapter) {
            Ok(()) => released_keys.push(key),
            Err(failure) => {
                failures.push(
                    RegisterMaskedNativeLeaseCacheEntryReleaseFailure {
                        failure,
                        key,
                    },
                );
            },
        }
    }
    reconciliation_result(released_keys, pending.retained_keys, failures)
}
