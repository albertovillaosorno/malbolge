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
//   - Resource-bounded LRU residency across reviewed v5 template families.
// - Must-Not:
//   - Erase typed resident identity, evict live leases, or merge execution
//     APIs.
// - Allows:
//   - Inputs: exact heterogeneous resident plans and one executable adapter.
//   - Outputs: cloneable leases, LRU disposition, and typed cleanup ownership.
//   - Side effects: resident load on miss and release of one unleased LRU
//     victim.
// - Split-When:
//   - Limit reconfiguration or concurrent mutation gains authority.
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
//   - Entries are always bounded; optional bytes/mappings use exact loaded
//     weight.
//

//! Resource-bounded LRU across reviewed explicit-geometry resident templates.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::mem::take;
use std::num::NonZeroUsize;
use std::sync::Arc;

use crate::execution_native::{
    ExecutionGeometryNativeRunner, NativeExecutableMemoryAdapter,
    NativeRegionBuffers,
};
use crate::geometry_native_cross_template_resident::{
    GeometryNativeLoadedResident, GeometryNativeResidentExecutionFailure,
    GeometryNativeResidentExecutionOutcome,
    GeometryNativeResidentExecutionResult, GeometryNativeResidentKind,
    GeometryNativeResidentLoadFailure, GeometryNativeResidentPlan,
    GeometryNativeResidentReleaseFailure, GeometryNativeResidentWeight,
    GeometryNativeResidentWeightError,
};

type ResidentLoadFailure<MemoryError> =
    GeometryNativeResidentLoadFailure<MemoryError>;
type ResidentReleaseFailure<MemoryError> =
    GeometryNativeResidentReleaseFailure<MemoryError>;
type CandidateCleanupFailure<MemoryError> =
    Option<Box<ResidentReleaseFailure<MemoryError>>>;
type WeightedVictimResult<MemoryError> =
    Result<(), WeightedVictimFailure<MemoryError>>;
type CrossLruFailure<MemoryError> =
    GeometryNativeCrossTemplateLruAcquireFailure<MemoryError>;
type CrossReconfigurationFailure<MemoryError> =
    GeometryNativeCrossTemplateLruReconfigurationFailure<MemoryError>;
type ReleaseAllEntryFailure<MemoryError> =
    GeometryNativeCrossTemplateLruReleaseAllEntryFailure<MemoryError>;

/// Positive resource limits for the heterogeneous v5 LRU.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GeometryNativeCrossTemplateLruLimits {
    entries: NonZeroUsize,
    mapped_bytes: Option<NonZeroUsize>,
    mappings: Option<NonZeroUsize>,
}

/// Successful publication of replacement heterogeneous LRU limits.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GeometryNativeCrossTemplateLruReconfiguration {
    new_limits: GeometryNativeCrossTemplateLruLimits,
    previous_limits: GeometryNativeCrossTemplateLruLimits,
    removed_residents: usize,
}

/// Failed heterogeneous LRU limit change retaining typed cleanup evidence.
#[derive(Debug, Eq, PartialEq)]
pub enum GeometryNativeCrossTemplateLruReconfigurationFailure<MemoryError> {
    /// One required typed resident release failed during shrink.
    Release {
        /// Exact variant-specific cleanup ownership for the failed victim.
        error: Box<ResidentReleaseFailure<MemoryError>>,
        /// Limits that remain published after this failure.
        previous_limits: GeometryNativeCrossTemplateLruLimits,
        /// Residents removed from active authority before failure returned.
        removed_residents: usize,
        /// Limits requested by the rejected reconfiguration.
        requested_limits: GeometryNativeCrossTemplateLruLimits,
    },
    /// Exact retained heterogeneous usage could not be represented safely.
    ResidentWeight {
        /// Exact aggregate resident-weight failure.
        error: GeometryNativeResidentWeightError,
        /// Limits that remain published after this failure.
        previous_limits: GeometryNativeCrossTemplateLruLimits,
        /// Residents removed from active authority before failure returned.
        removed_residents: usize,
        /// Limits requested by the rejected reconfiguration.
        requested_limits: GeometryNativeCrossTemplateLruLimits,
    },
    /// Remaining live leases prevent the requested shrink from fitting.
    Saturated {
        /// Residents with at least one external lease.
        leased_residents: usize,
        /// Limits that remain published after this failure.
        previous_limits: GeometryNativeCrossTemplateLruLimits,
        /// Residents removed from active authority before failure returned.
        removed_residents: usize,
        /// Limits requested by the rejected reconfiguration.
        requested_limits: GeometryNativeCrossTemplateLruLimits,
        /// Residents still retained when shrink became blocked.
        residents: usize,
    },
}

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
    /// Loaded candidate exceeds the complete mapped-byte limit.
    MappedBytes {
        /// Failed rollback retaining candidate cleanup ownership, when
        /// present.
        candidate_cleanup_failure: CandidateCleanupFailure<MemoryError>,
        /// Maximum admitted synchronized mapped bytes.
        limit: NonZeroUsize,
        /// Exact mapped bytes required by the candidate.
        required: usize,
    },
    /// Loaded candidate exceeds the complete live-mapping limit.
    Mappings {
        /// Failed rollback retaining candidate cleanup ownership, when
        /// present.
        candidate_cleanup_failure: CandidateCleanupFailure<MemoryError>,
        /// Maximum admitted live mappings.
        limit: NonZeroUsize,
        /// Exact mappings required by the candidate.
        required: usize,
    },
    /// Exact candidate or aggregate resident weight overflowed host `usize`.
    ResidentWeight {
        /// Failed rollback retaining candidate cleanup ownership, when
        /// present.
        candidate_cleanup_failure: CandidateCleanupFailure<MemoryError>,
        /// Exact weight derivation failure.
        error: GeometryNativeResidentWeightError,
    },
    /// Every resident is leased, so no legal victim exists.
    Saturated {
        /// Residents with at least one external lease.
        leased_residents: usize,
        /// Residents currently occupying the configured capacity.
        residents: usize,
    },
    /// Weighted eviction failed after the typed candidate was already loaded.
    WeightedEvictionRelease {
        /// Failed candidate rollback ownership, when its cleanup also failed.
        candidate_cleanup_failure: CandidateCleanupFailure<MemoryError>,
        /// Exact typed victim cleanup ownership from failed eviction.
        eviction_failure: Box<ResidentReleaseFailure<MemoryError>>,
        /// Residents already removed from active authority.
        removed_residents: usize,
    },
    /// Resource admission found no unleased victim after candidate loading.
    WeightedSaturated {
        /// Failed candidate rollback ownership, when its cleanup also failed.
        candidate_cleanup_failure: CandidateCleanupFailure<MemoryError>,
        /// Residents with at least one external lease.
        leased_residents: usize,
        /// Residents already removed before saturation was discovered.
        removed_residents: usize,
        /// Residents still retained when admission became blocked.
        residents: usize,
    },
}

/// Lease plus the LRU action used to acquire it.
#[derive(Debug)]
pub struct GeometryNativeCrossTemplateLruAcquisition {
    disposition: GeometryNativeCrossTemplateLruDisposition,
    lease: GeometryNativeCrossTemplateLruLease,
}

/// Typed execution outcome retaining the cache action that produced the lease.
#[derive(Debug, Eq, PartialEq)]
pub struct GeometryNativeCrossTemplateCachedExecution {
    disposition: GeometryNativeCrossTemplateLruDisposition,
    outcome: GeometryNativeResidentExecutionOutcome,
}

/// Typed execution failure retaining the cache action that produced the lease.
#[derive(Debug, Eq, PartialEq)]
pub struct GeometryNativeCrossTemplateCachedExecutionFailure<RunnerError> {
    disposition: GeometryNativeCrossTemplateLruDisposition,
    error: Box<GeometryNativeResidentExecutionFailure<RunnerError>>,
}

/// One pass releasing every heterogeneous resident without external leases.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GeometryNativeCrossTemplateLruReleaseAll {
    released_residents: Vec<GeometryNativeResidentPlan>,
    retained_residents: Vec<GeometryNativeResidentPlan>,
}

/// One exact resident whose release failed during a release-all pass.
#[derive(Debug, Eq, PartialEq)]
pub struct GeometryNativeCrossTemplateLruReleaseAllEntryFailure<MemoryError> {
    failure: Box<ResidentReleaseFailure<MemoryError>>,
    plan: GeometryNativeResidentPlan,
}

/// Aggregate release-all failure after attempting every unleased resident.
#[derive(Debug, Eq, PartialEq)]
pub struct GeometryNativeCrossTemplateLruReleaseAllFailure<MemoryError> {
    failures: Vec<ReleaseAllEntryFailure<MemoryError>>,
    released_residents: Vec<GeometryNativeResidentPlan>,
    retained_residents: Vec<GeometryNativeResidentPlan>,
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

/// Exact aggregate resource usage retained by heterogeneous residents.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GeometryNativeCrossTemplateLruUsage {
    entries: usize,
    mapped_bytes: usize,
    mappings: usize,
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
    mapped_byte_limit: Option<NonZeroUsize>,
    mapping_limit: Option<NonZeroUsize>,
    residents: Vec<Arc<GeometryNativeLoadedResident>>,
}

/// Consumed heterogeneous cache authority awaiting lease-safe reclamation.
#[derive(Debug)]
pub struct GeometryNativeCrossTemplateLruDrain {
    retired: Vec<Arc<GeometryNativeLoadedResident>>,
}

#[derive(Debug)]
struct WeightedCandidate {
    loaded: GeometryNativeLoadedResident,
    weight: GeometryNativeResidentWeight,
}

#[derive(Debug)]
enum WeightedVictimFailure<MemoryError> {
    Release(Box<ResidentReleaseFailure<MemoryError>>),
    Saturated,
}

/// Result of acquiring one exact heterogeneous resident lease.
pub type GeometryNativeCrossTemplateLruAcquireResult<MemoryError> = Result<
    GeometryNativeCrossTemplateLruAcquisition,
    Box<GeometryNativeCrossTemplateLruAcquireFailure<MemoryError>>,
>;

/// Result of executing through one acquired heterogeneous resident lease.
pub type GeometryNativeCrossTemplateCachedExecutionResult<RunnerError> = Result<
    GeometryNativeCrossTemplateCachedExecution,
    Box<GeometryNativeCrossTemplateCachedExecutionFailure<RunnerError>>,
>;

/// Result of transactionally publishing heterogeneous replacement limits.
pub type GeometryNativeCrossTemplateLruReconfigurationResult<MemoryError> =
    Result<
        GeometryNativeCrossTemplateLruReconfiguration,
        Box<GeometryNativeCrossTemplateLruReconfigurationFailure<MemoryError>>,
    >;

/// Result of attempting release for every currently unleased resident.
pub type GeometryNativeCrossTemplateLruReleaseAllResult<MemoryError> = Result<
    GeometryNativeCrossTemplateLruReleaseAll,
    Box<GeometryNativeCrossTemplateLruReleaseAllFailure<MemoryError>>,
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
            Self::MappedBytes { limit, required, .. } => {
                write!(f, "v5 cross LRU needs {required} bytes; limit {limit}")
            },
            Self::Mappings { limit, required, .. } => write!(
                f,
                "v5 cross LRU needs {required} mappings; limit {limit}"
            ),
            Self::ResidentWeight { error, .. } => Display::fmt(error, f),
            Self::Saturated {
                leased_residents,
                residents,
            } => write!(
                f,
                "v5 cross LRU full ({leased_residents}/{residents} leased)"
            ),
            Self::WeightedEvictionRelease { eviction_failure, .. } => write!(
                f,
                "v5 cross weighted victim release failed: {eviction_failure}"
            ),
            Self::WeightedSaturated {
                leased_residents,
                residents,
                ..
            } => write!(
                f,
                "v5 cross weighted full ({leased_residents}/{residents} leased)"
            ),
        }
    }
}

impl GeometryNativeCrossTemplateLruLimits {
    /// Returns the positive complete-resident limit.
    #[must_use]
    pub const fn entry_limit(self) -> NonZeroUsize {
        self.entries
    }

    /// Returns the optional exact synchronized mapped-byte limit.
    #[must_use]
    pub const fn mapped_byte_limit(self) -> Option<NonZeroUsize> {
        self.mapped_bytes
    }

    /// Returns the optional exact live-mapping limit.
    #[must_use]
    pub const fn mapping_limit(self) -> Option<NonZeroUsize> {
        self.mappings
    }

    /// Constructs limits with only a positive complete-resident bound.
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

    /// Adds an exact live-mapping limit.
    #[must_use]
    pub const fn with_mapping_limit(
        mut self,
        mapping_limit: NonZeroUsize,
    ) -> Self {
        self.mappings = Some(mapping_limit);
        self
    }
}

impl<RunnerError: Display> Display
    for GeometryNativeCrossTemplateCachedExecutionFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        let disposition = match self.disposition {
            GeometryNativeCrossTemplateLruDisposition::Evicted => "evicted",
            GeometryNativeCrossTemplateLruDisposition::Hit => "hit",
            GeometryNativeCrossTemplateLruDisposition::Inserted => "inserted",
        };
        write!(
            f,
            "v5 cross {disposition} resident execution failed: {}",
            self.error,
        )
    }
}

impl<MemoryError: Display> Display
    for GeometryNativeCrossTemplateLruReleaseAllFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "heterogeneous v5 release-all retained {} failed releases",
            self.failures.len(),
        )
    }
}

impl<MemoryError: Display> Display
    for GeometryNativeCrossTemplateLruReconfigurationFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Release { error, .. } => {
                write!(f, "v5 cross LRU limit release failed: {error}")
            },
            Self::ResidentWeight { error, .. } => Display::fmt(error, f),
            Self::Saturated {
                leased_residents,
                residents,
                ..
            } => write!(
                f,
                "v5 cross limit blocked ({leased_residents}/{residents} leased)"
            ),
        }
    }
}

impl GeometryNativeCrossTemplateCachedExecution {
    /// Returns the cache action that acquired the executed resident.
    #[must_use]
    pub const fn disposition(
        &self,
    ) -> GeometryNativeCrossTemplateLruDisposition {
        self.disposition
    }

    /// Consumes the cached execution and returns its typed outcome.
    #[must_use]
    pub fn into_outcome(self) -> GeometryNativeResidentExecutionOutcome {
        self.outcome
    }

    /// Returns the exact typed execution outcome.
    #[must_use]
    pub const fn outcome(&self) -> &GeometryNativeResidentExecutionOutcome {
        &self.outcome
    }
}

impl<RunnerError>
    GeometryNativeCrossTemplateCachedExecutionFailure<RunnerError>
{
    /// Returns the cache action that acquired the resident before failure.
    #[must_use]
    pub const fn disposition(
        &self,
    ) -> GeometryNativeCrossTemplateLruDisposition {
        self.disposition
    }

    /// Returns the exact typed execution failure.
    #[must_use]
    pub const fn error(
        &self,
    ) -> &GeometryNativeResidentExecutionFailure<RunnerError> {
        &self.error
    }

    /// Consumes the wrapper and returns the typed execution failure.
    #[must_use]
    pub fn into_error(
        self,
    ) -> GeometryNativeResidentExecutionFailure<RunnerError> {
        *self.error
    }
}

impl GeometryNativeCrossTemplateLruReconfiguration {
    /// Returns the limits published after successful reconfiguration.
    #[must_use]
    pub const fn new_limits(self) -> GeometryNativeCrossTemplateLruLimits {
        self.new_limits
    }

    /// Returns the limits that were published before this request.
    #[must_use]
    pub const fn previous_limits(self) -> GeometryNativeCrossTemplateLruLimits {
        self.previous_limits
    }

    /// Returns residents removed before the new limits were published.
    #[must_use]
    pub const fn removed_residents(self) -> usize {
        self.removed_residents
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

    /// Executes the acquired resident and drops this external lease afterward.
    ///
    /// Cache resident authority remains published after either success or
    /// failure; the returned wrapper preserves the acquisition disposition.
    ///
    /// # Errors
    ///
    /// Returns the exact typed execution failure plus the cache action that
    /// produced this acquisition.
    pub fn execute<Runner>(
        self,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> GeometryNativeCrossTemplateCachedExecutionResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        let disposition = self.disposition;
        self.lease
            .execute(runner, buffers)
            .map(|outcome| GeometryNativeCrossTemplateCachedExecution {
                disposition,
                outcome,
            })
            .map_err(|error| {
                Box::new(GeometryNativeCrossTemplateCachedExecutionFailure {
                    disposition,
                    error,
                })
            })
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

impl GeometryNativeCrossTemplateLruReleaseAll {
    /// Returns exact identities released by this pass.
    #[must_use]
    pub fn released_residents(&self) -> &[GeometryNativeResidentPlan] {
        &self.released_residents
    }

    /// Returns exact identities retained because external leases remain.
    #[must_use]
    pub fn retained_residents(&self) -> &[GeometryNativeResidentPlan] {
        &self.retained_residents
    }
}

impl<MemoryError>
    GeometryNativeCrossTemplateLruReleaseAllEntryFailure<MemoryError>
{
    /// Returns exact variant-specific cleanup ownership.
    #[must_use]
    pub fn failure(&self) -> &ResidentReleaseFailure<MemoryError> {
        self.failure.as_ref()
    }

    /// Consumes this entry and returns exact cleanup ownership.
    #[must_use]
    pub fn into_failure(self) -> ResidentReleaseFailure<MemoryError> {
        *self.failure
    }

    /// Returns the exact admitted identity removed from cache authority.
    #[must_use]
    pub const fn plan(&self) -> &GeometryNativeResidentPlan {
        &self.plan
    }
}

impl<MemoryError> GeometryNativeCrossTemplateLruReleaseAllFailure<MemoryError> {
    /// Returns every exact resident release failure from this pass.
    #[must_use]
    pub fn failures(&self) -> &[ReleaseAllEntryFailure<MemoryError>] {
        &self.failures
    }

    /// Returns identities released before or during this failed pass.
    #[must_use]
    pub fn released_residents(&self) -> &[GeometryNativeResidentPlan] {
        &self.released_residents
    }

    /// Returns identities still resident because external leases blocked
    /// release.
    #[must_use]
    pub fn retained_residents(&self) -> &[GeometryNativeResidentPlan] {
        &self.retained_residents
    }

    /// Retries all cleanup ownership already transferred out of the cache.
    ///
    /// # Errors
    ///
    /// Returns only refreshed failures after attempting every retained owner.
    pub fn retry<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> GeometryNativeCrossTemplateLruReleaseAllResult<MemoryError>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = MemoryError>,
    {
        let mut failures = Vec::new();
        let mut released_residents = self.released_residents;
        for entry in self.failures {
            let plan = entry.plan;
            match (*entry.failure).retry(adapter) {
                Ok(()) => released_residents.push(plan),
                Err(failure) => {
                    failures.push(ReleaseAllEntryFailure { failure, plan });
                },
            }
        }
        if failures.is_empty() {
            Ok(GeometryNativeCrossTemplateLruReleaseAll {
                released_residents,
                retained_residents: self.retained_residents,
            })
        } else {
            Err(Box::new(Self {
                failures,
                released_residents,
                retained_residents: self.retained_residents,
            }))
        }
    }
}

impl GeometryNativeCrossTemplateLruUsage {
    /// Returns the number of complete heterogeneous residents.
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
        if self.mapped_byte_limit.is_some() || self.mapping_limit.is_some() {
            return self.ensure_weighted(adapter, plan);
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

    fn ensure_weighted<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        plan: &GeometryNativeResidentPlan,
    ) -> GeometryNativeCrossTemplateLruAcquireResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let loaded = plan.load(adapter).map_err(|error| {
            Box::new(GeometryNativeCrossTemplateLruAcquireFailure::Load(error))
        })?;
        let weight = match loaded.resident_weight() {
            Ok(weight) => weight,
            Err(error) => {
                let candidate_cleanup_failure = loaded.release(adapter).err();
                return Err(Box::new(CrossLruFailure::ResidentWeight {
                    candidate_cleanup_failure,
                    error,
                }));
            },
        };
        if let Some(limit) = self.mapped_byte_limit
            && weight.mapped_bytes() > limit.get()
        {
            let candidate_cleanup_failure = loaded.release(adapter).err();
            return Err(Box::new(CrossLruFailure::MappedBytes {
                candidate_cleanup_failure,
                limit,
                required: weight.mapped_bytes(),
            }));
        }
        if let Some(limit) = self.mapping_limit
            && weight.mappings() > limit.get()
        {
            let candidate_cleanup_failure = loaded.release(adapter).err();
            return Err(Box::new(CrossLruFailure::Mappings {
                candidate_cleanup_failure,
                limit,
                required: weight.mappings(),
            }));
        }
        self.fit_weighted_candidate(adapter, WeightedCandidate {
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
            Ok(loaded) => loaded,
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
    ) -> GeometryNativeCrossTemplateLruAcquireResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let mut current_usage = match self.usage() {
            Ok(usage) => usage,
            Err(error) => {
                let candidate_cleanup_failure = candidate.cleanup(adapter);
                return Err(Box::new(CrossLruFailure::ResidentWeight {
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
                Ok(()) => {
                    removed_residents = removed_residents.saturating_add(1);
                },
                Err(WeightedVictimFailure::Release(eviction_failure)) => {
                    let candidate_cleanup_failure = candidate.cleanup(adapter);
                    let removed_with_failure =
                        removed_residents.saturating_add(1);
                    return Err(Box::new(
                        CrossLruFailure::WeightedEvictionRelease {
                            candidate_cleanup_failure,
                            eviction_failure,
                            removed_residents: removed_with_failure,
                        },
                    ));
                },
                Err(WeightedVictimFailure::Saturated) => {
                    let candidate_cleanup_failure = candidate.cleanup(adapter);
                    return Err(Box::new(CrossLruFailure::WeightedSaturated {
                        candidate_cleanup_failure,
                        leased_residents: self.leased_resident_count(),
                        removed_residents,
                        residents: self.residents.len(),
                    }));
                },
            }
            current_usage = match self.usage() {
                Ok(usage) => usage,
                Err(error) => {
                    let candidate_cleanup_failure = candidate.cleanup(adapter);
                    return Err(Box::new(CrossLruFailure::ResidentWeight {
                        candidate_cleanup_failure,
                        error,
                    }));
                },
            };
        }
        let resident = Arc::new(candidate.loaded);
        let lease = GeometryNativeCrossTemplateLruLease {
            resident: Arc::clone(&resident),
        };
        self.residents.push(resident);
        let disposition = Self::weighted_disposition(removed_residents);
        Ok(GeometryNativeCrossTemplateLruAcquisition { disposition, lease })
    }

    /// Consumes active lookup authority into a retired reconciliation handle.
    ///
    /// No adapter work occurs here. The returned drain owns every former cache
    /// resident until [`GeometryNativeCrossTemplateLruDrain::reconcile`] can
    /// release it or an external lease still retains it.
    #[must_use]
    pub fn into_drain(self) -> GeometryNativeCrossTemplateLruDrain {
        GeometryNativeCrossTemplateLruDrain { retired: self.residents }
    }

    fn leased_resident_count(&self) -> usize {
        self.residents
            .iter()
            .filter(|resident| Arc::strong_count(resident) > 1)
            .count()
    }

    /// Returns the currently published resource limits.
    #[must_use]
    pub const fn limits(&self) -> GeometryNativeCrossTemplateLruLimits {
        GeometryNativeCrossTemplateLruLimits {
            entries: self.capacity,
            mapped_bytes: self.mapped_byte_limit,
            mappings: self.mapping_limit,
        }
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
            mapped_byte_limit: None,
            mapping_limit: None,
            residents: Vec::new(),
        }
    }

    /// Constructs an empty heterogeneous LRU from exact resource limits.
    #[must_use]
    pub const fn new_with_limits(
        limits: GeometryNativeCrossTemplateLruLimits,
    ) -> Self {
        Self {
            capacity: limits.entry_limit(),
            mapped_byte_limit: limits.mapped_byte_limit(),
            mapping_limit: limits.mapping_limit(),
            residents: Vec::new(),
        }
    }

    fn position(&self, plan: &GeometryNativeResidentPlan) -> Option<usize> {
        self.residents
            .iter()
            .position(|resident| resident.matches_plan(plan))
    }

    /// Publishes replacement heterogeneous resource limits after LRU cleanup.
    ///
    /// Expansion or already-satisfied requests publish without adapter work.
    /// Shrink releases unleased LRU residents across template families until
    /// retained usage fits. Failure keeps the prior limits published even when
    /// earlier successful removals remain removed.
    ///
    /// # Errors
    ///
    /// Returns prior/requested limits with exact weight, saturation, or typed
    /// victim cleanup evidence.
    pub fn reconfigure_limits<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        requested_limits: GeometryNativeCrossTemplateLruLimits,
    ) -> GeometryNativeCrossTemplateLruReconfigurationResult<Adapter::Error>
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
                        CrossReconfigurationFailure::ResidentWeight {
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
                return Ok(GeometryNativeCrossTemplateLruReconfiguration {
                    new_limits: requested_limits,
                    previous_limits,
                    removed_residents,
                });
            }
            match self.evict_weighted_victim(adapter) {
                Ok(()) => {
                    removed_residents = removed_residents.saturating_add(1);
                },
                Err(WeightedVictimFailure::Release(error)) => {
                    let removed_with_failure =
                        removed_residents.saturating_add(1);
                    return Err(Box::new(
                        CrossReconfigurationFailure::Release {
                            error,
                            previous_limits,
                            removed_residents: removed_with_failure,
                            requested_limits,
                        },
                    ));
                },
                Err(WeightedVictimFailure::Saturated) => {
                    return Err(Box::new(
                        CrossReconfigurationFailure::Saturated {
                            leased_residents: self.leased_resident_count(),
                            previous_limits,
                            removed_residents,
                            requested_limits,
                            residents: self.residents.len(),
                        },
                    ));
                },
            }
        }
    }

    /// Releases every currently unleased resident in LRU-to-MRU order.
    ///
    /// Residents with external leases remain active in their original relative
    /// order. Every unleased resident is removed from cache authority before
    /// its specialized release runs, so failed release transfers exact
    /// cleanup ownership instead of restoring stale lookup authority.
    ///
    /// # Errors
    ///
    /// Returns exact plans plus typed cleanup ownership after attempting every
    /// releasable resident.
    pub fn release_all_unleased<Adapter>(
        &mut self,
        adapter: &mut Adapter,
    ) -> GeometryNativeCrossTemplateLruReleaseAllResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let residents = take(&mut self.residents);
        reconcile_residents(adapter, residents, &mut self.residents)
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

    /// Returns exact aggregate resource usage across all typed residents.
    ///
    /// # Errors
    ///
    /// Returns overflow when mapped bytes or mapping counts cannot be summed.
    pub fn usage(
        &self,
    ) -> Result<
        GeometryNativeCrossTemplateLruUsage,
        GeometryNativeResidentWeightError,
    > {
        resident_usage(&self.residents)
    }

    const fn usage_exceeds_limits(
        usage: GeometryNativeCrossTemplateLruUsage,
        limits: GeometryNativeCrossTemplateLruLimits,
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
        usage: GeometryNativeCrossTemplateLruUsage,
        candidate: &WeightedCandidate,
    ) -> bool {
        self.residents.len() >= self.capacity.get()
            || self.mapped_byte_limit.is_some_and(|limit| {
                usage
                    .mapped_bytes()
                    .checked_add(candidate.weight.mapped_bytes())
                    .is_none_or(|projected| projected > limit.get())
            })
            || self.mapping_limit.is_some_and(|limit| {
                usage
                    .mappings()
                    .checked_add(candidate.weight.mappings())
                    .is_none_or(|projected| projected > limit.get())
            })
    }

    const fn weighted_disposition(
        removed_residents: usize,
    ) -> GeometryNativeCrossTemplateLruDisposition {
        if removed_residents > 0 {
            GeometryNativeCrossTemplateLruDisposition::Evicted
        } else {
            GeometryNativeCrossTemplateLruDisposition::Inserted
        }
    }
}

impl GeometryNativeCrossTemplateLruDrain {
    /// Reports whether all retired resident ownership has been reclaimed.
    #[must_use]
    pub const fn is_empty(&self) -> bool {
        self.retired.is_empty()
    }

    /// Reconciles every retired resident that no longer has an external lease.
    ///
    /// Retained leases stay retired and never regain lookup authority. Failed
    /// releases transfer exact plan plus typed cleanup ownership out of this
    /// drain just as
    /// [`GeometryNativeCrossTemplateLruCache::release_all_unleased`]
    /// does for active residents.
    ///
    /// # Errors
    ///
    /// Returns aggregate typed cleanup evidence after attempting every
    /// currently releasable retired resident.
    pub fn reconcile<Adapter>(
        &mut self,
        adapter: &mut Adapter,
    ) -> GeometryNativeCrossTemplateLruReleaseAllResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let retired = take(&mut self.retired);
        reconcile_residents(adapter, retired, &mut self.retired)
    }

    /// Returns retired residents still held behind external leases.
    #[must_use]
    pub const fn retired_count(&self) -> usize {
        self.retired.len()
    }

    /// Returns exact retired identities in original LRU relative order.
    #[must_use]
    pub fn retired_residents(&self) -> Vec<GeometryNativeResidentPlan> {
        self.retired
            .iter()
            .map(|resident| resident.plan())
            .collect()
    }

    /// Returns exact mapping usage still owned by retired residents.
    ///
    /// # Errors
    ///
    /// Returns the same mapped-byte or mapping-count overflow evidence as
    /// active cache usage.
    pub fn usage(
        &self,
    ) -> Result<
        GeometryNativeCrossTemplateLruUsage,
        GeometryNativeResidentWeightError,
    > {
        resident_usage(&self.retired)
    }
}

impl GeometryNativeCrossTemplateLruLease {
    /// Executes the retained specialized owner without cache or adapter work.
    ///
    /// # Errors
    ///
    /// Returns the exact typed resident execution failure.
    pub fn execute<Runner>(
        &self,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> GeometryNativeResidentExecutionResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        self.resident.execute(runner, buffers)
    }

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

fn reconcile_residents<Adapter>(
    adapter: &mut Adapter,
    residents: Vec<Arc<GeometryNativeLoadedResident>>,
    retained: &mut Vec<Arc<GeometryNativeLoadedResident>>,
) -> GeometryNativeCrossTemplateLruReleaseAllResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let mut failures = Vec::new();
    let mut released_residents = Vec::new();
    let mut retained_residents = Vec::new();
    for resident in residents {
        let plan = resident.plan();
        if Arc::strong_count(&resident) > 1 {
            retained_residents.push(plan);
            retained.push(resident);
            continue;
        }
        match Arc::try_unwrap(resident) {
            Ok(loaded) => match loaded.release(adapter) {
                Ok(()) => released_residents.push(plan),
                Err(failure) => {
                    failures.push(ReleaseAllEntryFailure { failure, plan });
                },
            },
            Err(still_retained) => {
                retained_residents.push(plan);
                retained.push(still_retained);
            },
        }
    }
    if failures.is_empty() {
        Ok(GeometryNativeCrossTemplateLruReleaseAll {
            released_residents,
            retained_residents,
        })
    } else {
        Err(Box::new(GeometryNativeCrossTemplateLruReleaseAllFailure {
            failures,
            released_residents,
            retained_residents,
        }))
    }
}

fn resident_usage(
    residents: &[Arc<GeometryNativeLoadedResident>],
) -> Result<
    GeometryNativeCrossTemplateLruUsage,
    GeometryNativeResidentWeightError,
> {
    let mut mapped_bytes = 0usize;
    let mut mappings = 0usize;
    for resident in residents {
        let weight = resident.resident_weight()?;
        mapped_bytes = mapped_bytes
            .checked_add(weight.mapped_bytes())
            .ok_or(GeometryNativeResidentWeightError::MappedBytesOverflow)?;
        mappings = mappings
            .checked_add(weight.mappings())
            .ok_or(GeometryNativeResidentWeightError::MappingsOverflow)?;
    }
    Ok(GeometryNativeCrossTemplateLruUsage {
        entries: residents.len(),
        mapped_bytes,
        mappings,
    })
}
