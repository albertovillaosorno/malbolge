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
//   - Entry-count and optional mapped-byte LRU residency for exact v5 triples.
// - Must-Not:
//   - Evict leased triples, reuse legacy keys, or estimate mapped-byte weight.
// - Allows:
//   - Inputs: admitted full-path sequences, entry capacity, adapter, and
//     runner.
//   - Outputs: cloneable leases, exact LRU disposition, and cleanup ownership.
//   - Side effects: load on miss and release of one unleased LRU victim.
// - Split-When:
//   - Cross-template residency, mapping-count limits, or concurrent mutation
//     needs independent policy.
// - Merge-When:
//   - A general v5 cache preserves exact identity, leases, LRU, and cleanup.
// - Summary:
//   - Keeps multiple exact full-path triples with lease-aware LRU eviction.
// - Description:
//   - Recency is explicit and eviction never crosses a live Arc lease.
// - Usage:
//   - Ensure exact sequences, use leases, then release identities when desired.
// - Defaults:
//   - Full capacity evicts the least-recent unleased triple or rejects safely.
//

//! Weighted LRU cache for full explicit-geometry native triples.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::num::NonZeroUsize;
use std::sync::Arc;

use crate::execution_native::{
    ExecutionGeometryNativeRunner, NativeExecutableMemoryAdapter,
    NativeRegionBuffers,
};
use crate::geometry_native_jump_rotate_halt_sequence::{
    ExecutionGeometryNativeJumpRotateHaltOwnedResult,
    ExecutionGeometryNativeJumpRotateHaltResidentWeight,
    ExecutionGeometryNativeJumpRotateHaltResidentWeightError,
    ExecutionGeometryNativeJumpRotateHaltSequence,
    ExecutionGeometryNativeJumpRotateHaltTripleLoadFailure,
    ExecutionGeometryNativeJumpRotateHaltTripleReleaseFailure,
    LoadedExecutionGeometryNativeJumpRotateHaltSequence,
};

type TripleLoadFailure<MemoryError> =
    ExecutionGeometryNativeJumpRotateHaltTripleLoadFailure<MemoryError>;
type TripleReleaseFailure<MemoryError> =
    ExecutionGeometryNativeJumpRotateHaltTripleReleaseFailure<MemoryError>;
type ResidentWeight = ExecutionGeometryNativeJumpRotateHaltResidentWeight;
type ResidentWeightError =
    ExecutionGeometryNativeJumpRotateHaltResidentWeightError;
type LruFailure<MemoryError> =
    GeometryNativeJumpRotateHaltLruAcquireFailure<MemoryError>;
type CandidateCleanupFailure<MemoryError> =
    Option<Box<TripleReleaseFailure<MemoryError>>>;
type WeightedVictimResult<MemoryError> =
    Result<(), WeightedVictimFailure<MemoryError>>;

/// Whether one multi-resident acquisition hit, inserted, or evicted.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GeometryNativeJumpRotateHaltLruDisposition {
    /// One unleased LRU resident was released before this identity loaded.
    Evicted,
    /// The exact resident already existed and moved to MRU position.
    Hit,
    /// Capacity had a vacant entry and this identity loaded there.
    Inserted,
}

/// Failure while acquiring one exact triple in the bounded LRU cache.
#[derive(Debug, Eq, PartialEq)]
pub enum GeometryNativeJumpRotateHaltLruAcquireFailure<MemoryError> {
    /// Releasing the selected unleased LRU victim failed.
    EvictionRelease(Box<TripleReleaseFailure<MemoryError>>),
    /// Loading the requested exact triple failed.
    Load(Box<TripleLoadFailure<MemoryError>>),
    /// Exact loaded candidate exceeds the configured mapped-byte limit.
    MappedBytes {
        /// Failed cleanup retaining the candidate, when release was
        /// incomplete.
        candidate_cleanup_failure:
            Option<Box<TripleReleaseFailure<MemoryError>>>,
        /// Maximum admitted synchronized mapped bytes.
        limit: NonZeroUsize,
        /// Exact mapped bytes required by the candidate triple.
        required: usize,
    },
    /// Exact candidate or aggregate resident weight overflowed host `usize`.
    ResidentWeight {
        /// Failed cleanup retaining the candidate, when release was
        /// incomplete.
        candidate_cleanup_failure:
            Option<Box<TripleReleaseFailure<MemoryError>>>,
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
            Option<Box<TripleReleaseFailure<MemoryError>>>,
        /// Exact victim cleanup ownership from the failed eviction.
        eviction_failure: Box<TripleReleaseFailure<MemoryError>>,
        /// Residents already removed from active cache authority.
        removed_residents: usize,
    },
    /// Weighted admission found no unleased victim after loading the candidate.
    WeightedSaturated {
        /// Failed cleanup retaining the candidate, when release was
        /// incomplete.
        candidate_cleanup_failure:
            Option<Box<TripleReleaseFailure<MemoryError>>>,
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
pub struct GeometryNativeJumpRotateHaltLruAcquisition {
    disposition: GeometryNativeJumpRotateHaltLruDisposition,
    lease: GeometryNativeJumpRotateHaltLruLease,
}

/// Explicit outcome of releasing one exact resident identity.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GeometryNativeJumpRotateHaltLruRelease {
    /// External leases still retain this resident.
    Leased {
        /// External lease owners blocking release.
        leases: usize,
    },
    /// The requested identity is not resident.
    Missing,
    /// The unleased resident released all three mappings.
    Released,
}

/// Exact aggregate synchronized mapping usage retained by this LRU cache.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GeometryNativeJumpRotateHaltLruUsage {
    entries: usize,
    mapped_bytes: usize,
    mappings: usize,
}

/// One immutable external owner of a multi-resident full-path triple.
#[derive(Clone, Debug)]
pub struct GeometryNativeJumpRotateHaltLruLease {
    resident: Arc<LoadedExecutionGeometryNativeJumpRotateHaltSequence>,
}

/// Entry-count-bounded LRU resident set for full-path v5 triples.
#[derive(Debug)]
pub struct GeometryNativeJumpRotateHaltLruCache {
    capacity: NonZeroUsize,
    mapped_byte_limit: Option<NonZeroUsize>,
    residents: Vec<Arc<LoadedExecutionGeometryNativeJumpRotateHaltSequence>>,
}

#[derive(Debug)]
struct WeightedCandidate {
    loaded: Box<LoadedExecutionGeometryNativeJumpRotateHaltSequence>,
    mapped_byte_limit: NonZeroUsize,
    weight: ResidentWeight,
}

#[derive(Debug)]
enum WeightedVictimFailure<MemoryError> {
    Release(Box<TripleReleaseFailure<MemoryError>>),
    Saturated,
}

/// Result of acquiring one exact LRU resident lease.
pub type GeometryNativeJumpRotateHaltLruAcquireResult<MemoryError> = Result<
    GeometryNativeJumpRotateHaltLruAcquisition,
    Box<GeometryNativeJumpRotateHaltLruAcquireFailure<MemoryError>>,
>;

/// Result of releasing one exact resident identity.
pub type GeometryNativeJumpRotateHaltLruReleaseResult<MemoryError> = Result<
    GeometryNativeJumpRotateHaltLruRelease,
    Box<TripleReleaseFailure<MemoryError>>,
>;

impl<MemoryError: Display> Display
    for GeometryNativeJumpRotateHaltLruAcquireFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::EvictionRelease(error) => {
                write!(f, "v5 LRU victim release failed: {error}")
            },
            Self::Load(error) => {
                write!(f, "v5 LRU triple load failed: {error}")
            },
            Self::MappedBytes { limit, required, .. } => write!(
                f,
                "v5 LRU needs {required} mapped bytes; limit is {limit}"
            ),
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

impl GeometryNativeJumpRotateHaltLruAcquisition {
    /// Returns the exact cache action used by this acquisition.
    #[must_use]
    pub const fn disposition(
        &self,
    ) -> GeometryNativeJumpRotateHaltLruDisposition {
        self.disposition
    }

    /// Consumes the acquisition and returns its immutable external lease.
    #[must_use]
    pub fn into_lease(self) -> GeometryNativeJumpRotateHaltLruLease {
        self.lease
    }

    /// Returns the immutable lease retained by this acquisition.
    #[must_use]
    pub const fn lease(&self) -> &GeometryNativeJumpRotateHaltLruLease {
        &self.lease
    }
}

impl GeometryNativeJumpRotateHaltLruUsage {
    /// Returns the number of complete resident triples.
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

impl GeometryNativeJumpRotateHaltLruLease {
    /// Executes through the resident exact triple without adapter work.
    ///
    /// # Errors
    ///
    /// Returns exact owned-triple binding or indexed execution failure.
    pub fn execute<Runner>(
        &self,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> ExecutionGeometryNativeJumpRotateHaltOwnedResult<Runner::Error>
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
    pub fn sequence(&self) -> &ExecutionGeometryNativeJumpRotateHaltSequence {
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

impl GeometryNativeJumpRotateHaltLruCache {
    /// Returns the configured entry-count capacity.
    #[must_use]
    pub const fn capacity(&self) -> NonZeroUsize {
        self.capacity
    }

    /// Reports whether the complete exact sequence is resident.
    #[must_use]
    pub fn contains(
        &self,
        sequence: &ExecutionGeometryNativeJumpRotateHaltSequence,
    ) -> bool {
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
    /// Returns saturation, victim-release ownership, or exact triple-load
    /// failure.
    pub fn ensure<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        sequence: &ExecutionGeometryNativeJumpRotateHaltSequence,
    ) -> GeometryNativeJumpRotateHaltLruAcquireResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        if let Some(index) = self.position(sequence) {
            let resident = self.residents.remove(index);
            let lease = GeometryNativeJumpRotateHaltLruLease {
                resident: Arc::clone(&resident),
            };
            self.residents.push(resident);
            return Ok(GeometryNativeJumpRotateHaltLruAcquisition {
                disposition: GeometryNativeJumpRotateHaltLruDisposition::Hit,
                lease,
            });
        }
        if let Some(mapped_byte_limit) = self.mapped_byte_limit {
            return self.ensure_weighted(adapter, sequence, mapped_byte_limit);
        }
        if self.residents.len() < self.capacity.get() {
            return self.load_and_insert(
                adapter,
                sequence,
                GeometryNativeJumpRotateHaltLruDisposition::Inserted,
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
            GeometryNativeJumpRotateHaltLruDisposition::Evicted,
        )
    }

    fn ensure_weighted<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        sequence: &ExecutionGeometryNativeJumpRotateHaltSequence,
        mapped_byte_limit: NonZeroUsize,
    ) -> GeometryNativeJumpRotateHaltLruAcquireResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let loaded_triple = sequence
            .load_triple(adapter)
            .map_err(|error| Box::new(LruFailure::Load(error)))?;
        let loaded = Box::new(loaded_triple);
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
        if weight.mapped_bytes() > mapped_byte_limit.get() {
            let candidate_cleanup_failure = loaded.release(adapter).err();
            return Err(Box::new(LruFailure::MappedBytes {
                candidate_cleanup_failure,
                limit: mapped_byte_limit,
                required: weight.mapped_bytes(),
            }));
        }
        self.fit_weighted_candidate(adapter, WeightedCandidate {
            loaded,
            mapped_byte_limit,
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
    ) -> GeometryNativeJumpRotateHaltLruAcquireResult<Adapter::Error>
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
        let resident: Arc<LoadedExecutionGeometryNativeJumpRotateHaltSequence> =
            Arc::from(candidate.loaded);
        let lease = GeometryNativeJumpRotateHaltLruLease {
            resident: Arc::clone(&resident),
        };
        self.residents.push(resident);
        let disposition = Self::weighted_disposition(removed_residents);
        Ok(GeometryNativeJumpRotateHaltLruAcquisition { disposition, lease })
    }

    fn leased_resident_count(&self) -> usize {
        self.residents
            .iter()
            .filter(|resident| Arc::strong_count(resident) > 1)
            .count()
    }

    fn load_and_insert<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        sequence: &ExecutionGeometryNativeJumpRotateHaltSequence,
        disposition: GeometryNativeJumpRotateHaltLruDisposition,
    ) -> GeometryNativeJumpRotateHaltLruAcquireResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let loaded = sequence
            .load_triple(adapter)
            .map_err(|error| Box::new(LruFailure::Load(error)))?;
        let resident = Arc::new(loaded);
        let lease = GeometryNativeJumpRotateHaltLruLease {
            resident: Arc::clone(&resident),
        };
        self.residents.push(resident);
        Ok(GeometryNativeJumpRotateHaltLruAcquisition { disposition, lease })
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
            residents: Vec::new(),
        }
    }

    fn position(
        &self,
        sequence: &ExecutionGeometryNativeJumpRotateHaltSequence,
    ) -> Option<usize> {
        self.residents
            .iter()
            .position(|resident| resident.sequence() == sequence)
    }

    /// Releases one exact resident only when it has no external leases.
    ///
    /// Cleanup failure removes the resident and transfers exact retry
    /// ownership. Other identities remain untouched.
    ///
    /// # Errors
    ///
    /// Returns exact triple cleanup ownership when release is incomplete.
    pub fn release_if_unleased<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        sequence: &ExecutionGeometryNativeJumpRotateHaltSequence,
    ) -> GeometryNativeJumpRotateHaltLruReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let Some(index) = self.position(sequence) else {
            return Ok(GeometryNativeJumpRotateHaltLruRelease::Missing);
        };
        let leases = self.residents.get(index).map_or(0, |resident| {
            Arc::strong_count(resident).saturating_sub(1)
        });
        if leases > 0 {
            return Ok(GeometryNativeJumpRotateHaltLruRelease::Leased {
                leases,
            });
        }
        let resident = self.residents.remove(index);
        match Arc::try_unwrap(resident) {
            Ok(loaded) => loaded
                .release(adapter)
                .map(|()| GeometryNativeJumpRotateHaltLruRelease::Released),
            Err(retained) => {
                let remaining = Arc::strong_count(&retained).saturating_sub(1);
                self.residents.insert(index, retained);
                Ok(GeometryNativeJumpRotateHaltLruRelease::Leased {
                    leases: remaining,
                })
            },
        }
    }

    /// Returns the number of currently resident exact triples.
    #[must_use]
    pub const fn resident_count(&self) -> usize {
        self.residents.len()
    }

    /// Returns external lease owners for one exact resident identity.
    #[must_use]
    pub fn resident_lease_count(
        &self,
        sequence: &ExecutionGeometryNativeJumpRotateHaltSequence,
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
    ) -> Result<GeometryNativeJumpRotateHaltLruUsage, ResidentWeightError> {
        let mut mapped_bytes = 0usize;
        let mut mappings = 0usize;
        for resident in &self.residents {
            let weight = resident.resident_weight()?;
            mapped_bytes = mapped_bytes
                .checked_add(weight.mapped_bytes())
                .ok_or(ResidentWeightError::MappedBytesOverflow)?;
            mappings = mappings
                .checked_add(weight.mappings())
                .ok_or(ResidentWeightError::MappedBytesOverflow)?;
        }
        Ok(GeometryNativeJumpRotateHaltLruUsage {
            entries: self.residents.len(),
            mapped_bytes,
            mappings,
        })
    }

    fn weighted_candidate_requires_eviction(
        &self,
        usage: GeometryNativeJumpRotateHaltLruUsage,
        candidate: &WeightedCandidate,
    ) -> bool {
        self.residents.len() >= self.capacity.get()
            || usage
                .mapped_bytes()
                .checked_add(candidate.weight.mapped_bytes())
                .is_none_or(|projected| {
                    projected > candidate.mapped_byte_limit.get()
                })
    }

    const fn weighted_disposition(
        removed_residents: usize,
    ) -> GeometryNativeJumpRotateHaltLruDisposition {
        if removed_residents > 0 {
            GeometryNativeJumpRotateHaltLruDisposition::Evicted
        } else {
            GeometryNativeJumpRotateHaltLruDisposition::Inserted
        }
    }
}
