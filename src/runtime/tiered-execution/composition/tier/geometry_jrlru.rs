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
//   - Entry-count plus optional mapped-byte and mapping-count LRU residency for
//     exact v5 theorem paths.
// - Must-Not:
//   - Evict leased theorem paths, reuse legacy keys, or estimate mapped-byte
//     weight.
// - Allows:
//   - Inputs: admitted theorem sequences, exact resident limits, adapter, and
//     runner.
//   - Outputs: cloneable leases, exact LRU disposition, and cleanup ownership.
//   - Side effects: load on miss and release of one unleased LRU victim.
// - Split-When:
//   - Cross-template residency, admission telemetry, or concurrent mutation
//     needs independent policy.
// - Merge-When:
//   - A general v5 cache preserves exact identity, leases, LRU, and cleanup.
// - Summary:
//   - Keeps multiple exact theorem owners with lease-aware LRU eviction.
// - Description:
//   - Recency is explicit and eviction never crosses a live Arc lease.
// - Usage:
//   - Ensure exact sequences, use leases, then release identities when desired.
// - Defaults:
//   - Full capacity evicts the least-recent unleased theorem path or rejects
//     safely.
//

//! Weighted LRU cache for complete explicit-geometry crazy theorem paths.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::num::NonZeroUsize;
use std::sync::Arc;

use crate::execution_native::{
    ExecutionGeometryNativeRunner, NativeExecutableMemoryAdapter,
    NativeRegionBuffers,
};
use crate::geometry_native_jump_rotate_crazy_halt_owner::{
    ExecutionGeometryNativeJumpRotateCrazyHaltLoadFailure,
    ExecutionGeometryNativeJumpRotateCrazyHaltReleaseFailure,
    ExecutionGeometryNativeJumpRotateCrazyHaltResidentWeight,
    ExecutionGeometryNativeJumpRotateCrazyHaltResidentWeightError,
    GeometryNativeJumpRotateCrazyHaltOwnedResult, LoadedCrazyTheoremSequence,
};
use crate::geometry_native_jump_rotate_crazy_halt_sequence as theorem_sequence;

/// Short cache-local alias for the exact admitted theorem sequence.
pub type CrazyTheoremSequence =
    theorem_sequence::ExecutionGeometryNativeJumpRotateCrazyHaltSequence;

type TheoremLoadFailure<MemoryError> =
    ExecutionGeometryNativeJumpRotateCrazyHaltLoadFailure<MemoryError>;
type TheoremReleaseFailure<MemoryError> =
    ExecutionGeometryNativeJumpRotateCrazyHaltReleaseFailure<MemoryError>;
type ResidentWeight = ExecutionGeometryNativeJumpRotateCrazyHaltResidentWeight;
type ResidentWeightError =
    ExecutionGeometryNativeJumpRotateCrazyHaltResidentWeightError;
type LruFailure<MemoryError> =
    GeometryNativeJumpRotateCrazyHaltLruAcquireFailure<MemoryError>;
type CandidateCleanupFailure<MemoryError> =
    Option<Box<TheoremReleaseFailure<MemoryError>>>;
type WeightedVictimResult<MemoryError> =
    Result<(), WeightedVictimFailure<MemoryError>>;
type ReconfigurationFailure<MemoryError> =
    GeometryNativeJumpRotateCrazyHaltLruReconfigurationFailure<MemoryError>;
type ReconfigurationResult<MemoryError> =
    GeometryNativeJumpRotateCrazyHaltLruReconfigurationResult<MemoryError>;
type AcquireResult<MemoryError> =
    GeometryNativeJumpRotateCrazyHaltLruAcquireResult<MemoryError>;
type ReleaseResult<MemoryError> =
    GeometryNativeJumpRotateCrazyHaltLruReleaseResult<MemoryError>;

/// Whether one multi-resident acquisition hit, inserted, or evicted.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GeometryNativeJumpRotateCrazyHaltLruDisposition {
    /// One unleased LRU resident was released before this identity loaded.
    Evicted,
    /// The exact resident already existed and moved to MRU position.
    Hit,
    /// Capacity had a vacant entry and this identity loaded there.
    Inserted,
}

/// Positive resident limits for the complete-theorem v5 LRU.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GeometryNativeJumpRotateCrazyHaltLruLimits {
    entries: NonZeroUsize,
    mapped_bytes: Option<NonZeroUsize>,
    mappings: Option<NonZeroUsize>,
}

/// Successful publication of replacement LRU limits.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GeometryNativeJumpRotateCrazyHaltLruReconfiguration {
    new_limits: GeometryNativeJumpRotateCrazyHaltLruLimits,
    previous_limits: GeometryNativeJumpRotateCrazyHaltLruLimits,
    removed_residents: usize,
}

/// Failed LRU limit change retaining prior limits and cleanup evidence.
#[derive(Debug, Eq, PartialEq)]
pub enum GeometryNativeJumpRotateCrazyHaltLruReconfigurationFailure<MemoryError>
{
    /// One required resident release failed during shrink.
    Release {
        /// Exact cleanup ownership for the failed removed resident.
        error: Box<TheoremReleaseFailure<MemoryError>>,
        /// Limits that remain published after this failure.
        previous_limits: GeometryNativeJumpRotateCrazyHaltLruLimits,
        /// Residents removed from active authority before failure returned.
        removed_residents: usize,
        /// Limits requested by the rejected reconfiguration.
        requested_limits: GeometryNativeJumpRotateCrazyHaltLruLimits,
    },
    /// Exact retained usage could not be represented safely.
    ResidentWeight {
        /// Exact resident-weight derivation failure.
        error: ResidentWeightError,
        /// Limits that remain published after this failure.
        previous_limits: GeometryNativeJumpRotateCrazyHaltLruLimits,
        /// Residents removed from active authority before failure returned.
        removed_residents: usize,
        /// Limits requested by the rejected reconfiguration.
        requested_limits: GeometryNativeJumpRotateCrazyHaltLruLimits,
    },
    /// Remaining live leases prevent the requested shrink from fitting.
    Saturated {
        /// Residents with at least one external lease.
        leased_residents: usize,
        /// Limits that remain published after this failure.
        previous_limits: GeometryNativeJumpRotateCrazyHaltLruLimits,
        /// Residents removed from active authority before failure returned.
        removed_residents: usize,
        /// Limits requested by the rejected reconfiguration.
        requested_limits: GeometryNativeJumpRotateCrazyHaltLruLimits,
        /// Residents still retained when shrink became blocked.
        residents: usize,
    },
}

/// Failure while acquiring one exact theorem path in the bounded LRU cache.
#[derive(Debug, Eq, PartialEq)]
pub enum GeometryNativeJumpRotateCrazyHaltLruAcquireFailure<MemoryError> {
    /// Releasing the selected unleased LRU victim failed.
    EvictionRelease(Box<TheoremReleaseFailure<MemoryError>>),
    /// Loading the requested exact theorem path failed.
    Load(Box<TheoremLoadFailure<MemoryError>>),
    /// Exact loaded candidate exceeds the configured mapped-byte limit.
    MappedBytes {
        /// Failed cleanup retaining the candidate, when release was
        /// incomplete.
        candidate_cleanup_failure:
            Option<Box<TheoremReleaseFailure<MemoryError>>>,
        /// Maximum admitted synchronized mapped bytes.
        limit: NonZeroUsize,
        /// Exact mapped bytes required by the candidate theorem path.
        required: usize,
    },
    /// Exact loaded candidate exceeds the configured mapping-count limit.
    Mappings {
        /// Failed cleanup retaining the candidate, when release was
        /// incomplete.
        candidate_cleanup_failure:
            Option<Box<TheoremReleaseFailure<MemoryError>>>,
        /// Maximum admitted live executable mappings.
        limit: NonZeroUsize,
        /// Exact live mappings required by the candidate theorem path.
        required: usize,
    },
    /// Exact candidate or aggregate resident weight overflowed host `usize`.
    ResidentWeight {
        /// Failed cleanup retaining the candidate, when release was
        /// incomplete.
        candidate_cleanup_failure:
            Option<Box<TheoremReleaseFailure<MemoryError>>>,
        /// Exact weight derivation failure.
        error: ResidentWeightError,
    },
    /// Every resident is leased, so no legal eviction victim exists.
    Saturated {
        /// Residents currently occupying the configured capacity.
        residents: usize,
        /// Residents with at least one external lease.
        leased_residents: usize,
    },
    /// Weighted eviction failed after the exact candidate was already loaded.
    WeightedEvictionRelease {
        /// Failed candidate cleanup ownership, when its rollback also failed.
        candidate_cleanup_failure:
            Option<Box<TheoremReleaseFailure<MemoryError>>>,
        /// Exact victim cleanup ownership from the failed eviction.
        eviction_failure: Box<TheoremReleaseFailure<MemoryError>>,
        /// Residents already removed from active cache authority.
        removed_residents: usize,
    },
    /// Weighted admission found no unleased victim after loading the candidate.
    WeightedSaturated {
        /// Failed cleanup retaining the candidate, when release was
        /// incomplete.
        candidate_cleanup_failure:
            Option<Box<TheoremReleaseFailure<MemoryError>>>,
        /// Residents with at least one external lease.
        leased_residents: usize,
        /// Residents currently occupying the configured cache.
        residents: usize,
        /// Residents already removed before saturation was discovered.
        removed_residents: usize,
    },
}

/// Lease plus the LRU action used to acquire it.
#[derive(Debug)]
pub struct GeometryNativeJumpRotateCrazyHaltLruAcquisition {
    disposition: GeometryNativeJumpRotateCrazyHaltLruDisposition,
    lease: GeometryNativeJumpRotateCrazyHaltLruLease,
}

/// Explicit outcome of releasing one exact resident identity.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GeometryNativeJumpRotateCrazyHaltLruRelease {
    /// External leases still retain this resident.
    Leased {
        /// External lease owners blocking release.
        leases: usize,
    },
    /// The requested identity is not resident.
    Missing,
    /// The unleased resident released all seven mappings.
    Released,
}

/// Exact aggregate synchronized mapping usage retained by this LRU cache.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GeometryNativeJumpRotateCrazyHaltLruUsage {
    entries: usize,
    mapped_bytes: usize,
    mappings: usize,
}

/// One immutable external owner of a multi-resident theorem path.
#[derive(Clone, Debug)]
pub struct GeometryNativeJumpRotateCrazyHaltLruLease {
    resident: Arc<LoadedCrazyTheoremSequence>,
}

/// Entry-count-bounded LRU resident set for complete v5 theorem paths.
#[derive(Debug)]
pub struct GeometryNativeJumpRotateCrazyHaltLruCache {
    capacity: NonZeroUsize,
    mapped_byte_limit: Option<NonZeroUsize>,
    mapping_limit: Option<NonZeroUsize>,
    residents: Vec<Arc<LoadedCrazyTheoremSequence>>,
}

#[derive(Debug)]
struct WeightedCandidate {
    limits: GeometryNativeJumpRotateCrazyHaltLruLimits,
    loaded: Box<LoadedCrazyTheoremSequence>,
    weight: ResidentWeight,
}

#[derive(Debug)]
enum WeightedVictimFailure<MemoryError> {
    Release(Box<TheoremReleaseFailure<MemoryError>>),
    Saturated,
}

/// Result of acquiring one exact LRU resident lease.
pub type GeometryNativeJumpRotateCrazyHaltLruAcquireResult<MemoryError> =
    Result<
        GeometryNativeJumpRotateCrazyHaltLruAcquisition,
        Box<GeometryNativeJumpRotateCrazyHaltLruAcquireFailure<MemoryError>>,
    >;

/// Result of transactionally publishing replacement LRU limits.
pub type GeometryNativeJumpRotateCrazyHaltLruReconfigurationResult<
    MemoryError,
> = Result<
    GeometryNativeJumpRotateCrazyHaltLruReconfiguration,
    Box<
        GeometryNativeJumpRotateCrazyHaltLruReconfigurationFailure<MemoryError>,
    >,
>;

/// Result of releasing one exact resident identity.
pub type GeometryNativeJumpRotateCrazyHaltLruReleaseResult<MemoryError> =
    Result<
        GeometryNativeJumpRotateCrazyHaltLruRelease,
        Box<TheoremReleaseFailure<MemoryError>>,
    >;

impl<MemoryError: Display> Display
    for GeometryNativeJumpRotateCrazyHaltLruAcquireFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::EvictionRelease(error) => {
                write!(f, "v5 LRU victim release failed: {error}")
            },
            Self::Load(error) => {
                write!(f, "v5 LRU theorem load failed: {error}")
            },
            Self::MappedBytes { limit, required, .. } => write!(
                f,
                "v5 LRU needs {required} mapped bytes; limit is {limit}"
            ),
            Self::Mappings { limit, required, .. } => {
                write!(f, "v5 LRU needs {required} mappings; limit is {limit}")
            },
            Self::ResidentWeight { error, .. } => Display::fmt(error, f),
            Self::Saturated {
                leased_residents,
                residents,
            } => write!(
                f,
                "v5 LRU saturated ({leased_residents}/{residents} leased)"
            ),
            Self::WeightedEvictionRelease { eviction_failure, .. } => write!(
                f,
                "v5 weighted LRU victim release failed: {eviction_failure}"
            ),
            Self::WeightedSaturated {
                leased_residents,
                residents,
                ..
            } => write!(
                f,
                "v5 weighted LRU full ({leased_residents}/{residents} leased)"
            ),
        }
    }
}

impl<MemoryError: Display> Display
    for GeometryNativeJumpRotateCrazyHaltLruReconfigurationFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Release { error, .. } => {
                write!(f, "v5 LRU reconfiguration release failed: {error}")
            },
            Self::ResidentWeight { error, .. } => Display::fmt(error, f),
            Self::Saturated {
                leased_residents,
                residents,
                ..
            } => write!(
                f,
                "v5 LRU limits blocked ({leased_residents}/{residents} leased)"
            ),
        }
    }
}

impl GeometryNativeJumpRotateCrazyHaltLruAcquisition {
    /// Returns the exact cache action used by this acquisition.
    #[must_use]
    pub const fn disposition(
        &self,
    ) -> GeometryNativeJumpRotateCrazyHaltLruDisposition {
        self.disposition
    }

    /// Consumes the acquisition and returns its immutable external lease.
    #[must_use]
    pub fn into_lease(self) -> GeometryNativeJumpRotateCrazyHaltLruLease {
        self.lease
    }

    /// Returns the immutable lease retained by this acquisition.
    #[must_use]
    pub const fn lease(&self) -> &GeometryNativeJumpRotateCrazyHaltLruLease {
        &self.lease
    }
}

impl GeometryNativeJumpRotateCrazyHaltLruLimits {
    /// Returns the positive whole-entry resident limit.
    #[must_use]
    pub const fn entry_limit(self) -> NonZeroUsize {
        self.entries
    }

    /// Returns the optional exact synchronized mapped-byte limit.
    #[must_use]
    pub const fn mapped_byte_limit(self) -> Option<NonZeroUsize> {
        self.mapped_bytes
    }

    /// Returns the optional exact live executable mapping-count limit.
    #[must_use]
    pub const fn mapping_limit(self) -> Option<NonZeroUsize> {
        self.mappings
    }

    /// Constructs limits with only a positive entry bound.
    #[must_use]
    pub const fn new(entry_limit: NonZeroUsize) -> Self {
        Self {
            entries: entry_limit,
            mapped_bytes: None,
            mappings: None,
        }
    }

    /// Adds an exact synchronized mapped-byte limit.
    #[must_use]
    pub const fn with_mapped_byte_limit(
        mut self,
        mapped_byte_limit: NonZeroUsize,
    ) -> Self {
        self.mapped_bytes = Some(mapped_byte_limit);
        self
    }

    /// Adds an exact live executable mapping-count limit.
    #[must_use]
    pub const fn with_mapping_limit(
        mut self,
        mapping_limit: NonZeroUsize,
    ) -> Self {
        self.mappings = Some(mapping_limit);
        self
    }
}

impl GeometryNativeJumpRotateCrazyHaltLruReconfiguration {
    /// Returns the limits published after successful reconfiguration.
    #[must_use]
    pub const fn new_limits(
        self,
    ) -> GeometryNativeJumpRotateCrazyHaltLruLimits {
        self.new_limits
    }

    /// Returns the limits that were published before this request.
    #[must_use]
    pub const fn previous_limits(
        self,
    ) -> GeometryNativeJumpRotateCrazyHaltLruLimits {
        self.previous_limits
    }

    /// Returns residents removed before the new limits were published.
    #[must_use]
    pub const fn removed_residents(self) -> usize {
        self.removed_residents
    }
}

impl GeometryNativeJumpRotateCrazyHaltLruUsage {
    /// Returns the number of complete resident theorem paths.
    #[must_use]
    pub const fn entries(self) -> usize {
        self.entries
    }

    /// Returns exact synchronized mapped bytes retained by all residents.
    #[must_use]
    pub const fn mapped_bytes(self) -> usize {
        self.mapped_bytes
    }

    /// Returns exact live executable mapping count across all residents.
    #[must_use]
    pub const fn mappings(self) -> usize {
        self.mappings
    }
}

impl GeometryNativeJumpRotateCrazyHaltLruLease {
    /// Executes through the resident exact theorem path without adapter work.
    ///
    /// # Errors
    ///
    /// Returns exact owned-theorem path binding or indexed execution failure.
    pub fn execute<Runner>(
        &self,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> GeometryNativeJumpRotateCrazyHaltOwnedResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        self.resident.execute(runner, buffers)
    }

    /// Returns exact resident weight from synchronized mapping reports.
    ///
    /// # Errors
    ///
    /// Returns overflow when mapped byte capacities cannot be summed.
    pub fn resident_weight(
        &self,
    ) -> Result<ResidentWeight, ResidentWeightError> {
        self.resident.resident_weight()
    }

    /// Returns the exact admitted sequence behind this resident.
    #[must_use]
    pub fn sequence(&self) -> &CrazyTheoremSequence {
        self.resident.sequence()
    }

    /// Reports whether two leases share one resident allocation.
    #[must_use]
    pub fn shares_resident_with(&self, other: &Self) -> bool {
        Arc::ptr_eq(&self.resident, &other.resident)
    }

    /// Returns all strong owners, including the cache resident owner.
    #[must_use]
    pub fn strong_owner_count(&self) -> usize {
        Arc::strong_count(&self.resident)
    }
}

impl WeightedCandidate {
    fn cleanup<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> CandidateCleanupFailure<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        self.loaded.release(adapter).err()
    }
}

impl GeometryNativeJumpRotateCrazyHaltLruCache {
    /// Returns the configured entry-count capacity.
    #[must_use]
    pub const fn capacity(&self) -> NonZeroUsize {
        self.capacity
    }

    /// Reports whether the complete exact sequence is resident.
    #[must_use]
    pub fn contains(&self, sequence: &CrazyTheoremSequence) -> bool {
        self.position(sequence).is_some()
    }

    /// Loads, hits, or lease-safely evicts to acquire one exact sequence.
    ///
    /// Exact hits move to MRU without adapter work. A full cache scans from LRU
    /// to MRU and selects the first resident with no external leases. Release
    /// failure removes only that victim and transfers retry ownership; a later
    /// load failure leaves its slot vacant rather than restoring stale state.
    ///
    /// # Errors
    ///
    /// Returns saturation, victim-release ownership, or exact theorem path-load
    /// failure.
    pub fn ensure<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        sequence: &CrazyTheoremSequence,
    ) -> AcquireResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        if let Some(index) = self.position(sequence) {
            let resident = self.residents.remove(index);
            let lease = GeometryNativeJumpRotateCrazyHaltLruLease {
                resident: Arc::clone(&resident),
            };
            self.residents.push(resident);
            return Ok(GeometryNativeJumpRotateCrazyHaltLruAcquisition {
                disposition:
                    GeometryNativeJumpRotateCrazyHaltLruDisposition::Hit,
                lease,
            });
        }
        let limits = self.limits();
        if limits.mapped_byte_limit().is_some()
            || limits.mapping_limit().is_some()
        {
            return self.ensure_weighted(adapter, sequence, limits);
        }
        if self.residents.len() < self.capacity.get() {
            return self.load_and_insert(
                adapter,
                sequence,
                GeometryNativeJumpRotateCrazyHaltLruDisposition::Inserted,
            );
        }
        let Some(victim_index) = self
            .residents
            .iter()
            .position(|resident| Arc::strong_count(resident) == 1)
        else {
            return Err(Box::new(LruFailure::Saturated {
                leased_residents: self.leased_resident_count(),
                residents: self.residents.len(),
            }));
        };
        let victim = self.residents.remove(victim_index);
        let loaded_victim = match Arc::try_unwrap(victim) {
            Ok(loaded) => loaded,
            Err(retained) => {
                self.residents.insert(victim_index, retained);
                return Err(Box::new(LruFailure::Saturated {
                    leased_residents: self.leased_resident_count(),
                    residents: self.residents.len(),
                }));
            },
        };
        loaded_victim
            .release(adapter)
            .map_err(|error| Box::new(LruFailure::EvictionRelease(error)))?;
        self.load_and_insert(
            adapter,
            sequence,
            GeometryNativeJumpRotateCrazyHaltLruDisposition::Evicted,
        )
    }

    fn ensure_weighted<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        sequence: &CrazyTheoremSequence,
        limits: GeometryNativeJumpRotateCrazyHaltLruLimits,
    ) -> AcquireResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let loaded_owner = LoadedCrazyTheoremSequence::load(sequence, adapter)
            .map_err(|error| Box::new(LruFailure::Load(error)))?;
        let loaded = Box::new(loaded_owner);
        let weight = match loaded.resident_weight() {
            Ok(weight) => weight,
            Err(error) => {
                let candidate_cleanup_failure = loaded.release(adapter).err();
                return Err(Box::new(LruFailure::ResidentWeight {
                    candidate_cleanup_failure,
                    error,
                }));
            },
        };
        if let Some(limit) = limits.mapped_byte_limit()
            && weight.mapped_bytes() > limit.get()
        {
            let candidate_cleanup_failure = loaded.release(adapter).err();
            return Err(Box::new(LruFailure::MappedBytes {
                candidate_cleanup_failure,
                limit,
                required: weight.mapped_bytes(),
            }));
        }
        if let Some(limit) = limits.mapping_limit()
            && weight.mappings() > limit.get()
        {
            let candidate_cleanup_failure = loaded.release(adapter).err();
            return Err(Box::new(LruFailure::Mappings {
                candidate_cleanup_failure,
                limit,
                required: weight.mappings(),
            }));
        }
        self.fit_weighted_candidate(adapter, WeightedCandidate {
            limits,
            loaded,
            weight,
        })
    }

    fn evict_weighted_victim<Adapter>(
        &mut self,
        adapter: &mut Adapter,
    ) -> WeightedVictimResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let Some(victim_index) = self
            .residents
            .iter()
            .position(|resident| Arc::strong_count(resident) == 1)
        else {
            return Err(WeightedVictimFailure::Saturated);
        };
        let victim = self.residents.remove(victim_index);
        let loaded_victim = match Arc::try_unwrap(victim) {
            Ok(loaded_victim) => loaded_victim,
            Err(retained) => {
                self.residents.insert(victim_index, retained);
                return Err(WeightedVictimFailure::Saturated);
            },
        };
        loaded_victim
            .release(adapter)
            .map_err(WeightedVictimFailure::Release)
    }

    fn fit_weighted_candidate<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        candidate: WeightedCandidate,
    ) -> AcquireResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let mut current_usage = match self.usage() {
            Ok(current_usage) => current_usage,
            Err(error) => {
                let candidate_cleanup_failure = candidate.cleanup(adapter);
                return Err(Box::new(LruFailure::ResidentWeight {
                    candidate_cleanup_failure,
                    error,
                }));
            },
        };
        let mut removed_residents = 0usize;
        while self
            .weighted_candidate_requires_eviction(current_usage, &candidate)
        {
            match self.evict_weighted_victim(adapter) {
                Ok(()) => {},
                Err(WeightedVictimFailure::Release(eviction_failure)) => {
                    let candidate_cleanup_failure = candidate.cleanup(adapter);
                    return Err(Box::new(
                        LruFailure::WeightedEvictionRelease {
                            candidate_cleanup_failure,
                            eviction_failure,
                            removed_residents: removed_residents
                                .saturating_add(1),
                        },
                    ));
                },
                Err(WeightedVictimFailure::Saturated) => {
                    let candidate_cleanup_failure = candidate.cleanup(adapter);
                    return Err(Box::new(LruFailure::WeightedSaturated {
                        candidate_cleanup_failure,
                        leased_residents: self.leased_resident_count(),
                        residents: self.residents.len(),
                        removed_residents,
                    }));
                },
            }
            current_usage = match self.usage() {
                Ok(next_usage) => next_usage,
                Err(error) => {
                    let candidate_cleanup_failure = candidate.cleanup(adapter);
                    return Err(Box::new(LruFailure::ResidentWeight {
                        candidate_cleanup_failure,
                        error,
                    }));
                },
            };
            removed_residents = removed_residents.saturating_add(1);
        }
        let resident: Arc<LoadedCrazyTheoremSequence> =
            Arc::from(candidate.loaded);
        let lease = GeometryNativeJumpRotateCrazyHaltLruLease {
            resident: Arc::clone(&resident),
        };
        self.residents.push(resident);
        let disposition = Self::weighted_disposition(removed_residents);
        Ok(GeometryNativeJumpRotateCrazyHaltLruAcquisition {
            disposition,
            lease,
        })
    }

    fn leased_resident_count(&self) -> usize {
        self.residents
            .iter()
            .filter(|resident| Arc::strong_count(resident) > 1)
            .count()
    }

    /// Returns the currently published resident limits.
    #[must_use]
    pub const fn limits(&self) -> GeometryNativeJumpRotateCrazyHaltLruLimits {
        GeometryNativeJumpRotateCrazyHaltLruLimits {
            entries: self.capacity,
            mapped_bytes: self.mapped_byte_limit,
            mappings: self.mapping_limit,
        }
    }

    fn load_and_insert<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        sequence: &CrazyTheoremSequence,
        disposition: GeometryNativeJumpRotateCrazyHaltLruDisposition,
    ) -> AcquireResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let loaded = LoadedCrazyTheoremSequence::load(sequence, adapter)
            .map_err(|error| Box::new(LruFailure::Load(error)))?;
        let resident = Arc::new(loaded);
        let lease = GeometryNativeJumpRotateCrazyHaltLruLease {
            resident: Arc::clone(&resident),
        };
        self.residents.push(resident);
        Ok(GeometryNativeJumpRotateCrazyHaltLruAcquisition {
            disposition,
            lease,
        })
    }

    /// Returns the optional exact synchronized mapped-byte limit.
    #[must_use]
    pub const fn mapped_byte_limit(&self) -> Option<NonZeroUsize> {
        self.mapped_byte_limit
    }

    /// Constructs an empty LRU cache with nonzero entry-count capacity.
    #[must_use]
    pub const fn new(capacity: NonZeroUsize) -> Self {
        Self {
            capacity,
            mapped_byte_limit: None,
            mapping_limit: None,
            residents: Vec::new(),
        }
    }

    /// Constructs an empty LRU with entry and exact mapped-byte limits.
    #[must_use]
    pub const fn new_with_mapped_byte_limit(
        capacity: NonZeroUsize,
        mapped_byte_limit: NonZeroUsize,
    ) -> Self {
        Self {
            capacity,
            mapped_byte_limit: Some(mapped_byte_limit),
            mapping_limit: None,
            residents: Vec::new(),
        }
    }

    /// Constructs an empty LRU with entry and exact mapping-count limits.
    #[must_use]
    pub const fn new_with_mapping_limit(
        capacity: NonZeroUsize,
        mapping_limit: NonZeroUsize,
    ) -> Self {
        Self {
            capacity,
            mapped_byte_limit: None,
            mapping_limit: Some(mapping_limit),
            residents: Vec::new(),
        }
    }

    fn position(&self, sequence: &CrazyTheoremSequence) -> Option<usize> {
        self.residents
            .iter()
            .position(|resident| resident.sequence() == sequence)
    }

    /// Publishes replacement entry/byte limits after required LRU cleanup.
    ///
    /// Expansion or already-satisfied limits publish without adapter work.
    /// Shrink releases unleased LRU residents until retained usage fits. On
    /// blockage or cleanup failure the previous limits remain published even
    /// though successfully removed residents stay removed.
    ///
    /// # Errors
    ///
    /// Returns retained prior limits plus exact blocker, weight, or cleanup
    /// ownership evidence.
    pub fn reconfigure_limits<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        requested_limits: GeometryNativeJumpRotateCrazyHaltLruLimits,
    ) -> ReconfigurationResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let previous_limits = self.limits();
        let mut removed_residents = 0usize;
        loop {
            let usage = match self.usage() {
                Ok(usage) => usage,
                Err(error) => {
                    return Err(Box::new(
                        ReconfigurationFailure::ResidentWeight {
                            error,
                            previous_limits,
                            removed_residents,
                            requested_limits,
                        },
                    ));
                },
            };
            if !Self::usage_exceeds_limits(usage, requested_limits) {
                self.capacity = requested_limits.entry_limit();
                self.mapped_byte_limit = requested_limits.mapped_byte_limit();
                self.mapping_limit = requested_limits.mapping_limit();
                return Ok(
                    GeometryNativeJumpRotateCrazyHaltLruReconfiguration {
                        new_limits: requested_limits,
                        previous_limits,
                        removed_residents,
                    },
                );
            }
            match self.evict_weighted_victim(adapter) {
                Ok(()) => {
                    removed_residents = removed_residents.saturating_add(1);
                },
                Err(WeightedVictimFailure::Release(error)) => {
                    let removed_with_failure =
                        removed_residents.saturating_add(1);
                    return Err(Box::new(ReconfigurationFailure::Release {
                        error,
                        previous_limits,
                        removed_residents: removed_with_failure,
                        requested_limits,
                    }));
                },
                Err(WeightedVictimFailure::Saturated) => {
                    return Err(Box::new(ReconfigurationFailure::Saturated {
                        leased_residents: self.leased_resident_count(),
                        previous_limits,
                        removed_residents,
                        requested_limits,
                        residents: self.residents.len(),
                    }));
                },
            }
        }
    }

    /// Releases one exact resident only when it has no external leases.
    ///
    /// Cleanup failure removes the resident and transfers exact retry
    /// ownership. Other identities remain untouched.
    ///
    /// # Errors
    ///
    /// Returns exact theorem path cleanup ownership when release is incomplete.
    pub fn release_if_unleased<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        sequence: &CrazyTheoremSequence,
    ) -> ReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let Some(index) = self.position(sequence) else {
            return Ok(GeometryNativeJumpRotateCrazyHaltLruRelease::Missing);
        };
        let leases = self.residents.get(index).map_or(0, |resident| {
            Arc::strong_count(resident).saturating_sub(1)
        });
        if leases > 0 {
            return Ok(GeometryNativeJumpRotateCrazyHaltLruRelease::Leased {
                leases,
            });
        }
        let resident = self.residents.remove(index);
        match Arc::try_unwrap(resident) {
            Ok(loaded) => loaded.release(adapter).map(|()| {
                GeometryNativeJumpRotateCrazyHaltLruRelease::Released
            }),
            Err(retained) => {
                let remaining = Arc::strong_count(&retained).saturating_sub(1);
                self.residents.insert(index, retained);
                Ok(GeometryNativeJumpRotateCrazyHaltLruRelease::Leased {
                    leases: remaining,
                })
            },
        }
    }

    /// Returns the number of currently resident exact theorem paths.
    #[must_use]
    pub const fn resident_count(&self) -> usize {
        self.residents.len()
    }

    /// Returns external lease owners for one exact resident identity.
    #[must_use]
    pub fn resident_lease_count(
        &self,
        sequence: &CrazyTheoremSequence,
    ) -> usize {
        self.position(sequence).map_or(0, |index| {
            self.residents.get(index).map_or(0, |resident| {
                Arc::strong_count(resident).saturating_sub(1)
            })
        })
    }

    /// Returns exact aggregate usage from every synchronized resident mapping.
    ///
    /// # Errors
    ///
    /// Returns overflow if resident weights or their aggregate cannot fit
    /// usize.
    pub fn usage(
        &self,
    ) -> Result<GeometryNativeJumpRotateCrazyHaltLruUsage, ResidentWeightError>
    {
        let mut mapped_bytes = 0usize;
        let mut mappings = 0usize;
        for resident in &self.residents {
            let weight = resident.resident_weight()?;
            mapped_bytes = mapped_bytes
                .checked_add(weight.mapped_bytes())
                .ok_or(ResidentWeightError::MappedBytesOverflow)?;
            mappings = mappings
                .checked_add(weight.mappings())
                .ok_or(ResidentWeightError::MappingsOverflow)?;
        }
        Ok(GeometryNativeJumpRotateCrazyHaltLruUsage {
            entries: self.residents.len(),
            mapped_bytes,
            mappings,
        })
    }

    const fn usage_exceeds_limits(
        usage: GeometryNativeJumpRotateCrazyHaltLruUsage,
        limits: GeometryNativeJumpRotateCrazyHaltLruLimits,
    ) -> bool {
        usage.entries() > limits.entry_limit().get()
            || match limits.mapped_byte_limit() {
                Some(limit) => usage.mapped_bytes() > limit.get(),
                None => false,
            }
            || match limits.mapping_limit() {
                Some(limit) => usage.mappings() > limit.get(),
                None => false,
            }
    }

    fn weighted_candidate_requires_eviction(
        &self,
        usage: GeometryNativeJumpRotateCrazyHaltLruUsage,
        candidate: &WeightedCandidate,
    ) -> bool {
        self.residents.len() >= self.capacity.get()
            || candidate.limits.mapped_byte_limit().is_some_and(|limit| {
                usage
                    .mapped_bytes()
                    .checked_add(candidate.weight.mapped_bytes())
                    .is_none_or(|projected| projected > limit.get())
            })
            || candidate.limits.mapping_limit().is_some_and(|limit| {
                usage
                    .mappings()
                    .checked_add(candidate.weight.mappings())
                    .is_none_or(|projected| projected > limit.get())
            })
    }

    const fn weighted_disposition(
        removed_residents: usize,
    ) -> GeometryNativeJumpRotateCrazyHaltLruDisposition {
        if removed_residents > 0 {
            GeometryNativeJumpRotateCrazyHaltLruDisposition::Evicted
        } else {
            GeometryNativeJumpRotateCrazyHaltLruDisposition::Inserted
        }
    }
}
