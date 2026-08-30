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
//   - Entry-count-bounded LRU residency for exact v5 jump/rotate/halt triples.
// - Must-Not:
//   - Evict leased triples, reuse legacy keys, or infer byte-weighted capacity.
// - Allows:
//   - Inputs: admitted full-path sequences, entry capacity, adapter, and
//     runner.
//   - Outputs: cloneable leases, exact LRU disposition, and cleanup ownership.
//   - Side effects: load on miss and release of one unleased LRU victim.
// - Split-When:
//   - Byte-weighted budgets, cross-template residency, or concurrent mutation
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

//! Entry-count-bounded LRU cache for full explicit-geometry native triples.

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
    /// Every resident is leased, so no legal eviction victim exists.
    Saturated {
        /// Residents currently occupying the configured capacity.
        residents: usize,
        /// Residents with at least one external lease.
        leased_residents: usize,
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
    residents: Vec<Arc<LoadedExecutionGeometryNativeJumpRotateHaltSequence>>,
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
            Self::Saturated {
                leased_residents,
                residents,
            } => write!(
                f,
                "v5 LRU saturated ({leased_residents}/{residents} leased)"
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
            return Err(Box::new(
                GeometryNativeJumpRotateHaltLruAcquireFailure::Saturated {
                    leased_residents: self.leased_resident_count(),
                    residents: self.residents.len(),
                },
            ));
        };
        let victim = self.residents.remove(victim_index);
        let loaded_victim = match Arc::try_unwrap(victim) {
            Ok(loaded) => loaded,
            Err(retained) => {
                self.residents.insert(victim_index, retained);
                return Err(Box::new(
                    GeometryNativeJumpRotateHaltLruAcquireFailure::Saturated {
                        leased_residents: self.leased_resident_count(),
                        residents: self.residents.len(),
                    },
                ));
            },
        };
        loaded_victim.release(adapter).map_err(|error| {
            Box::new(
                GeometryNativeJumpRotateHaltLruAcquireFailure::EvictionRelease(
                    error,
                ),
            )
        })?;
        self.load_and_insert(
            adapter,
            sequence,
            GeometryNativeJumpRotateHaltLruDisposition::Evicted,
        )
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
        let loaded = sequence.load_triple(adapter).map_err(|error| {
            Box::new(GeometryNativeJumpRotateHaltLruAcquireFailure::Load(error))
        })?;
        let resident = Arc::new(loaded);
        let lease = GeometryNativeJumpRotateHaltLruLease {
            resident: Arc::clone(&resident),
        };
        self.residents.push(resident);
        Ok(GeometryNativeJumpRotateHaltLruAcquisition { disposition, lease })
    }

    /// Constructs an empty LRU cache with nonzero entry-count capacity.
    #[must_use]
    pub const fn new(capacity: NonZeroUsize) -> Self {
        Self {
            capacity,
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
}
