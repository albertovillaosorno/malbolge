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
//   - Entry-count-bounded LRU residency across reviewed v5 template families.
// - Must-Not:
//   - Erase typed resident identity, evict live leases, or merge execution
//     APIs.
// - Allows:
//   - Inputs: exact heterogeneous resident plans and one executable adapter.
//   - Outputs: cloneable leases, LRU disposition, and typed cleanup ownership.
//   - Side effects: resident load on miss and release of one unleased LRU
//     victim.
// - Split-When:
//   - Weighted limits, reconfiguration, or concurrent mutation gain authority.
// - Merge-When:
//   - A general v5 cache preserves typed plans, leases, LRU, and cleanup
//     exactly.
// - Summary:
//   - Reuses reviewed heterogeneous v5 residents under one lease-safe LRU.
// - Description:
//   - Uses typed resident plans as identity and never falls back to legacy
//     keys.
// - Usage:
//   - Ensure exact plans, use immutable leases, then release identities
//     explicitly.
// - Defaults:
//   - Capacity counts complete residents; all-leased saturation is side-effect
//     free.
//

//! Entry-count LRU cache across reviewed explicit-geometry resident templates.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::num::NonZeroUsize;
use std::sync::Arc;

use crate::execution_native::NativeExecutableMemoryAdapter;
use crate::geometry_native_cross_template_resident::{
    GeometryNativeLoadedResident, GeometryNativeResidentKind,
    GeometryNativeResidentLoadFailure, GeometryNativeResidentPlan,
    GeometryNativeResidentReleaseFailure, GeometryNativeResidentWeight,
    GeometryNativeResidentWeightError,
};

type ResidentLoadFailure<MemoryError> =
    GeometryNativeResidentLoadFailure<MemoryError>;
type ResidentReleaseFailure<MemoryError> =
    GeometryNativeResidentReleaseFailure<MemoryError>;

/// Whether one heterogeneous acquisition hit, inserted, or evicted.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GeometryNativeCrossTemplateLruDisposition {
    /// One unleased LRU resident was released before this plan loaded.
    Evicted,
    /// The exact typed resident already existed and moved to MRU position.
    Hit,
    /// Capacity had a vacant entry and this plan loaded there.
    Inserted,
}

/// Failure while acquiring one typed heterogeneous resident.
#[derive(Debug, Eq, PartialEq)]
pub enum GeometryNativeCrossTemplateLruAcquireFailure<MemoryError> {
    /// Releasing the selected typed LRU victim failed.
    EvictionRelease(Box<ResidentReleaseFailure<MemoryError>>),
    /// Loading the requested typed resident failed.
    Load(Box<ResidentLoadFailure<MemoryError>>),
    /// Every resident is leased, so no legal victim exists.
    Saturated {
        /// Residents with at least one external lease.
        leased_residents: usize,
        /// Residents currently occupying the configured capacity.
        residents: usize,
    },
}

/// Lease plus the LRU action used to acquire it.
#[derive(Debug)]
pub struct GeometryNativeCrossTemplateLruAcquisition {
    disposition: GeometryNativeCrossTemplateLruDisposition,
    lease: GeometryNativeCrossTemplateLruLease,
}

/// Explicit outcome of releasing one exact heterogeneous resident identity.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GeometryNativeCrossTemplateLruRelease {
    /// External leases still retain this resident.
    Leased {
        /// External lease owners blocking release.
        leases: usize,
    },
    /// The requested typed identity is not resident.
    Missing,
    /// The unleased specialized owner released all of its mappings.
    Released,
}

/// One immutable external owner of a heterogeneous v5 resident.
#[derive(Clone, Debug)]
pub struct GeometryNativeCrossTemplateLruLease {
    resident: Arc<GeometryNativeLoadedResident>,
}

/// Entry-count-bounded heterogeneous LRU resident set.
#[derive(Debug)]
pub struct GeometryNativeCrossTemplateLruCache {
    capacity: NonZeroUsize,
    residents: Vec<Arc<GeometryNativeLoadedResident>>,
}

/// Result of acquiring one exact heterogeneous resident lease.
pub type GeometryNativeCrossTemplateLruAcquireResult<MemoryError> = Result<
    GeometryNativeCrossTemplateLruAcquisition,
    Box<GeometryNativeCrossTemplateLruAcquireFailure<MemoryError>>,
>;

/// Result of releasing one exact heterogeneous resident identity.
pub type GeometryNativeCrossTemplateLruReleaseResult<MemoryError> = Result<
    GeometryNativeCrossTemplateLruRelease,
    Box<ResidentReleaseFailure<MemoryError>>,
>;

impl<MemoryError: Display> Display
    for GeometryNativeCrossTemplateLruAcquireFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::EvictionRelease(error) => {
                write!(f, "heterogeneous v5 LRU victim release failed: {error}")
            },
            Self::Load(error) => {
                write!(f, "heterogeneous v5 LRU resident load failed: {error}")
            },
            Self::Saturated {
                leased_residents,
                residents,
            } => write!(
                f,
                "v5 cross LRU full ({leased_residents}/{residents} leased)"
            ),
        }
    }
}

impl GeometryNativeCrossTemplateLruAcquisition {
    /// Returns the exact cache action used by this acquisition.
    #[must_use]
    pub const fn disposition(
        &self,
    ) -> GeometryNativeCrossTemplateLruDisposition {
        self.disposition
    }

    /// Consumes the acquisition and returns its immutable external lease.
    #[must_use]
    pub fn into_lease(self) -> GeometryNativeCrossTemplateLruLease {
        self.lease
    }

    /// Returns the immutable lease retained by this acquisition.
    #[must_use]
    pub const fn lease(&self) -> &GeometryNativeCrossTemplateLruLease {
        &self.lease
    }
}

impl GeometryNativeCrossTemplateLruCache {
    /// Returns the configured complete-resident capacity.
    #[must_use]
    pub const fn capacity(&self) -> NonZeroUsize {
        self.capacity
    }

    /// Reports whether the complete typed plan is resident.
    #[must_use]
    pub fn contains(&self, plan: &GeometryNativeResidentPlan) -> bool {
        self.position(plan).is_some()
    }

    /// Loads, hits, or lease-safely evicts one exact heterogeneous resident.
    ///
    /// Hits refresh MRU position without adapter work. A full cache scans from
    /// LRU toward MRU for the first resident with no external lease. Failed
    /// victim release removes only that resident and transfers typed cleanup
    /// ownership; a later load failure leaves the vacancy reusable.
    ///
    /// # Errors
    ///
    /// Returns typed load failure, victim cleanup ownership, or all-leased
    /// saturation.
    pub fn ensure<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        plan: &GeometryNativeResidentPlan,
    ) -> GeometryNativeCrossTemplateLruAcquireResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        if let Some(index) = self.position(plan) {
            let resident = self.residents.remove(index);
            let lease = GeometryNativeCrossTemplateLruLease {
                resident: Arc::clone(&resident),
            };
            self.residents.push(resident);
            return Ok(GeometryNativeCrossTemplateLruAcquisition {
                disposition: GeometryNativeCrossTemplateLruDisposition::Hit,
                lease,
            });
        }
        if self.residents.len() < self.capacity.get() {
            return self.load_and_insert(
                adapter,
                plan,
                GeometryNativeCrossTemplateLruDisposition::Inserted,
            );
        }
        let Some(victim_index) = self
            .residents
            .iter()
            .position(|resident| Arc::strong_count(resident) == 1)
        else {
            return Err(Box::new(
                GeometryNativeCrossTemplateLruAcquireFailure::Saturated {
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
                    GeometryNativeCrossTemplateLruAcquireFailure::Saturated {
                        leased_residents: self.leased_resident_count(),
                        residents: self.residents.len(),
                    },
                ));
            },
        };
        loaded_victim.release(adapter).map_err(|error| {
            Box::new(
                GeometryNativeCrossTemplateLruAcquireFailure::EvictionRelease(
                    error,
                ),
            )
        })?;
        self.load_and_insert(
            adapter,
            plan,
            GeometryNativeCrossTemplateLruDisposition::Evicted,
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
        plan: &GeometryNativeResidentPlan,
        disposition: GeometryNativeCrossTemplateLruDisposition,
    ) -> GeometryNativeCrossTemplateLruAcquireResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let loaded = plan.load(adapter).map_err(|error| {
            Box::new(GeometryNativeCrossTemplateLruAcquireFailure::Load(error))
        })?;
        let resident = Arc::new(loaded);
        let lease = GeometryNativeCrossTemplateLruLease {
            resident: Arc::clone(&resident),
        };
        self.residents.push(resident);
        Ok(GeometryNativeCrossTemplateLruAcquisition { disposition, lease })
    }

    /// Constructs an empty heterogeneous LRU with nonzero entry capacity.
    #[must_use]
    pub const fn new(capacity: NonZeroUsize) -> Self {
        Self {
            capacity,
            residents: Vec::new(),
        }
    }

    fn position(&self, plan: &GeometryNativeResidentPlan) -> Option<usize> {
        self.residents
            .iter()
            .position(|resident| resident.matches_plan(plan))
    }

    /// Releases one exact typed resident only when it has no external leases.
    ///
    /// # Errors
    ///
    /// Returns variant-specific cleanup ownership when release is incomplete.
    pub fn release_if_unleased<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        plan: &GeometryNativeResidentPlan,
    ) -> GeometryNativeCrossTemplateLruReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let Some(index) = self.position(plan) else {
            return Ok(GeometryNativeCrossTemplateLruRelease::Missing);
        };
        let leases = self.residents.get(index).map_or(0, |resident| {
            Arc::strong_count(resident).saturating_sub(1)
        });
        if leases > 0 {
            return Ok(GeometryNativeCrossTemplateLruRelease::Leased {
                leases,
            });
        }
        let resident = self.residents.remove(index);
        match Arc::try_unwrap(resident) {
            Ok(loaded) => loaded
                .release(adapter)
                .map(|()| GeometryNativeCrossTemplateLruRelease::Released),
            Err(retained) => {
                let remaining = Arc::strong_count(&retained).saturating_sub(1);
                self.residents.insert(index, retained);
                Ok(GeometryNativeCrossTemplateLruRelease::Leased {
                    leases: remaining,
                })
            },
        }
    }

    /// Returns the number of currently resident typed owners.
    #[must_use]
    pub const fn resident_count(&self) -> usize {
        self.residents.len()
    }

    /// Returns external lease owners for one exact typed identity.
    #[must_use]
    pub fn resident_lease_count(
        &self,
        plan: &GeometryNativeResidentPlan,
    ) -> usize {
        self.position(plan).map_or(0, |index| {
            self.residents.get(index).map_or(0, |resident| {
                Arc::strong_count(resident).saturating_sub(1)
            })
        })
    }
}

impl GeometryNativeCrossTemplateLruLease {
    /// Returns the reviewed template retained by this lease.
    #[must_use]
    pub fn kind(&self) -> GeometryNativeResidentKind {
        self.resident.kind()
    }

    /// Reports whether this lease retains the complete exact typed plan.
    #[must_use]
    pub fn matches_plan(&self, plan: &GeometryNativeResidentPlan) -> bool {
        self.resident.matches_plan(plan)
    }

    /// Returns the loaded specialized owner for variant-specific execution.
    #[must_use]
    pub fn resident(&self) -> &GeometryNativeLoadedResident {
        &self.resident
    }

    /// Returns exact synchronized mapping weight for this leased resident.
    ///
    /// # Errors
    ///
    /// Returns overflow when mapped byte reports cannot be summed.
    pub fn resident_weight(
        &self,
    ) -> Result<GeometryNativeResidentWeight, GeometryNativeResidentWeightError>
    {
        self.resident.resident_weight()
    }

    /// Reports whether two leases share one loaded resident allocation.
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
