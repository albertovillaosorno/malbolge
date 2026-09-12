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
//   - One exact fused resident slot and cloneable immutable external leases.
// - Must-Not:
//   - Evict, replace, retire, reconfigure, or execute multi-entry sequences.
// - Allows:
//   - Inputs: verified fused artifacts, adapter, runner, and caller buffers.
//   - Outputs: exact leases, hit/insert evidence, and retryable cleanup
//     ownership.
//   - Side effects: owner load/release only through the supplied adapter.
// - Split-When:
//   - Multi-entry eviction, retirement, or reconfiguration policy is required.
// - Merge-When:
//   - One general fused resident store subsumes this exact single slot.
// - Summary:
//   - Shares one exact fused executable mapping without hidden replacement.
// - Description:
//   - Exact hits clone Arc ownership; live leases prevent adapter release.
// - Usage:
//   - Ensure an artifact, execute through the lease, then release explicitly.
// - Defaults:
//   - Hit, lease clone/drop, and blocked release perform no adapter operations.
//

//! Single-resident exact lease reuse for fused direct native executables.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::sync::Arc;

use super::direct::VerifiedDirectFusedSequenceObjectArtifact;
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

/// Whether one fused resident acquisition inserted or reused the exact owner.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectFusedNativeResidentCacheDisposition {
    /// The exact fused resident already existed and was leased without I/O.
    Hit,
    /// The exact fused mapping was loaded into the previously empty slot.
    Inserted,
}

/// Failure while acquiring one exact fused resident lease.
#[derive(Debug, Eq, PartialEq)]
pub enum DirectFusedNativeResidentCacheAcquireFailure<MemoryError> {
    /// A different exact fused identity already occupies the resident slot.
    IdentityOccupied,
    /// Loading the requested exact fused owner failed.
    Load(Box<DirectFusedNativeOwnerLoadFailure<MemoryError>>),
}

/// Explicit result of attempting to release the single fused resident.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectFusedNativeResidentCacheRelease {
    /// External leases still retain the resident mapping.
    Leased {
        /// Number of external lease owners blocking release.
        leases: usize,
    },
    /// No resident mapping exists.
    Missing,
    /// The unleased resident mapping released successfully.
    Released,
}

/// One immutable external lease of the exact fused resident.
#[derive(Clone, Debug)]
pub struct DirectFusedNativeResidentLease {
    resident: Arc<DirectFusedNativeExecutableOwner>,
}

/// Lease plus whether one acquisition inserted or reused the resident mapping.
#[derive(Debug)]
pub struct DirectFusedNativeResidentCacheAcquisition {
    disposition: DirectFusedNativeResidentCacheDisposition,
    lease: DirectFusedNativeResidentLease,
}

/// Single exact resident slot for cloneable fused executable leases.
#[derive(Debug, Default)]
pub struct DirectFusedNativeResidentLeaseCache {
    resident: Option<Arc<DirectFusedNativeExecutableOwner>>,
}

/// Result of acquiring one exact fused resident lease.
pub type DirectFusedNativeResidentCacheAcquireResult<MemoryError> = Result<
    DirectFusedNativeResidentCacheAcquisition,
    Box<DirectFusedNativeResidentCacheAcquireFailure<MemoryError>>,
>;

/// Result of releasing the fused resident after all external leases are gone.
pub type DirectFusedNativeResidentCacheReleaseResult<MemoryError> = Result<
    DirectFusedNativeResidentCacheRelease,
    Box<DirectFusedNativeExecutableReleaseFailure<MemoryError>>,
>;

impl<MemoryError: Display> Display
    for DirectFusedNativeResidentCacheAcquireFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::IdentityOccupied => {
                f.write_str("different fused native identity already resident")
            },
            Self::Load(error) => Display::fmt(error, f),
        }
    }
}

impl DirectFusedNativeResidentCacheAcquisition {
    /// Returns whether this acquisition inserted or reused the resident.
    #[must_use]
    pub const fn disposition(
        &self,
    ) -> DirectFusedNativeResidentCacheDisposition {
        self.disposition
    }

    /// Consumes this acquisition and returns its immutable external lease.
    #[must_use]
    pub fn into_lease(self) -> DirectFusedNativeResidentLease {
        self.lease
    }

    /// Returns the immutable lease retained by this acquisition.
    #[must_use]
    pub const fn lease(&self) -> &DirectFusedNativeResidentLease {
        &self.lease
    }
}

impl DirectFusedNativeResidentLease {
    /// Executes through the resident fused mapping without adapter work.
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

    /// Returns the exact fused native key retained by this lease.
    #[must_use]
    pub fn key(&self) -> &NativeArtifactKey {
        self.resident.key()
    }

    /// Returns exact synchronized weight reported by the resident owner.
    #[must_use]
    pub fn resident_weight(&self) -> DirectFusedNativeResidentWeight {
        self.resident.resident_weight()
    }

    /// Reports whether two leases share the same resident owner allocation.
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

impl DirectFusedNativeResidentLeaseCache {
    /// Loads or reuses one exact fused resident as an immutable lease.
    ///
    /// A different artifact cannot replace the resident through this minimal
    /// boundary; release the old resident explicitly first.
    ///
    /// # Errors
    ///
    /// Returns identity occupancy or exact owner-loading failure.
    pub fn ensure<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        artifact: &VerifiedDirectFusedSequenceObjectArtifact,
    ) -> DirectFusedNativeResidentCacheAcquireResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        use DirectFusedNativeResidentCacheAcquireFailure as Failure;

        if let Some(resident) = &self.resident {
            if resident.artifact() != artifact {
                return Err(Box::new(Failure::IdentityOccupied));
            }
            return Ok(DirectFusedNativeResidentCacheAcquisition {
                disposition: DirectFusedNativeResidentCacheDisposition::Hit,
                lease: DirectFusedNativeResidentLease {
                    resident: Arc::clone(resident),
                },
            });
        }
        let loaded = DirectFusedNativeExecutableOwner::load(adapter, artifact)
            .map_err(|error| Box::new(Failure::Load(error)))?;
        let resident = Arc::new(loaded);
        let lease = DirectFusedNativeResidentLease {
            resident: Arc::clone(&resident),
        };
        self.resident = Some(resident);
        Ok(DirectFusedNativeResidentCacheAcquisition {
            disposition: DirectFusedNativeResidentCacheDisposition::Inserted,
            lease,
        })
    }

    /// Reports whether one exact fused mapping is currently resident.
    #[must_use]
    pub const fn has_resident(&self) -> bool {
        self.resident.is_some()
    }

    /// Constructs one empty single-resident fused lease cache.
    #[must_use]
    pub const fn new() -> Self {
        Self { resident: None }
    }

    /// Releases the resident only when no external lease remains.
    ///
    /// Live leases block adapter release. Cleanup failure empties cache
    /// authority and transfers exact ready-executable retry ownership
    /// through the failure.
    ///
    /// # Errors
    ///
    /// Returns exact fused cleanup retry ownership on release failure.
    pub fn release_if_unleased<Adapter>(
        &mut self,
        adapter: &mut Adapter,
    ) -> DirectFusedNativeResidentCacheReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        use DirectFusedNativeResidentCacheRelease as Release;

        let Some(resident) = self.resident.take() else {
            return Ok(Release::Missing);
        };
        let leases = Arc::strong_count(&resident).saturating_sub(1);
        if leases > 0 {
            self.resident = Some(resident);
            return Ok(Release::Leased { leases });
        }
        match Arc::try_unwrap(resident) {
            Ok(owner) => owner.release(adapter).map(|()| Release::Released),
            Err(retained) => {
                let remaining_leases =
                    Arc::strong_count(&retained).saturating_sub(1);
                self.resident = Some(retained);
                Ok(Release::Leased { leases: remaining_leases })
            },
        }
    }

    /// Returns the number of external leases retaining the resident mapping.
    #[must_use]
    pub fn resident_lease_count(&self) -> usize {
        self.resident
            .as_ref()
            .map_or(0, |resident| Arc::strong_count(resident).saturating_sub(1))
    }
}
