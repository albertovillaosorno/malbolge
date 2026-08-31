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
//   - Single-resident lease reuse for one exact v5 no-operation/halt pair.
// - Must-Not:
//   - Mix sequence identities, invoke legacy cache keys, or release live
//     leases.
// - Allows:
//   - Inputs: admitted v5 sequence, executable-memory adapter, and runner.
//   - Outputs: immutable resident leases and explicit release disposition.
//   - Side effects: pair loading on miss and release after every lease is gone.
// - Split-When:
//   - Multi-entry eviction, weighted capacity, or concurrent mutation is
//     needed.
// - Merge-When:
//   - A general v5 native lease cache subsumes exact pair identity and cleanup.
// - Summary:
//   - Reuses one exact geometry-native pair behind cloneable leases.
// - Description:
//   - Uses full admitted-sequence equality and never canonical legacy identity.
// - Usage:
//   - Ensure a sequence, clone/use leases, drop them, then release the
//     resident.
// - Defaults:
//   - Different identity rejects; live leases block release without adapter
//     work.
//

//! Single-resident lease cache for the first multistep v5 native pair.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::sync::Arc;

use crate::execution_native::{
    ExecutionGeometryNativeRunner, NativeExecutableMemoryAdapter,
    NativeRegionBuffers,
};
use crate::geometry_native_sequence::{
    ExecutionGeometryNativeNoopHaltLoadedResult,
    ExecutionGeometryNativeNoopHaltPairLoadFailure,
    ExecutionGeometryNativeNoopHaltPairReleaseFailure,
    ExecutionGeometryNativeNoopHaltResidentWeight,
    ExecutionGeometryNativeNoopHaltResidentWeightError,
    ExecutionGeometryNativeNoopHaltSequence,
    LoadedExecutionGeometryNativeNoopHaltSequence,
};

/// Whether one lease acquisition loaded or reused resident mappings.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GeometryNativeNoopHaltPairCacheDisposition {
    /// The exact sequence already owned resident mappings.
    Hit,
    /// This acquisition loaded and published an empty resident slot.
    Inserted,
    /// An unleased different resident was released and replaced.
    Replaced,
}

/// Failure while acquiring one exact resident v5 pair.
#[derive(Debug, Eq, PartialEq)]
pub enum GeometryNativeNoopHaltPairCacheAcquireFailure<MemoryError> {
    /// A different exact sequence already owns the single resident slot.
    IdentityOccupied,
    /// Live leases prevent replacing a different resident identity.
    Leased {
        /// External resident owners that must be dropped first.
        leases: usize,
    },
    /// Loading the requested exact pair failed.
    Load(Box<ExecutionGeometryNativeNoopHaltPairLoadFailure<MemoryError>>),
    /// Releasing the previous unleased resident failed during replacement.
    Release(
        Box<ExecutionGeometryNativeNoopHaltPairReleaseFailure<MemoryError>>,
    ),
}

/// Lease plus whether its mappings were inserted or reused.
#[derive(Debug)]
pub struct GeometryNativeNoopHaltPairCacheAcquisition {
    disposition: GeometryNativeNoopHaltPairCacheDisposition,
    lease: GeometryNativeNoopHaltPairLease,
}

/// Explicit result of attempting to release the single resident pair.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GeometryNativeNoopHaltPairCacheRelease {
    /// External leases still retain the resident pair.
    Leased {
        /// Number of external lease owners blocking release.
        leases: usize,
    },
    /// No resident pair exists.
    Missing,
    /// The unleased resident pair released both mappings.
    Released,
}

/// One immutable external owner of the resident v5 pair.
#[derive(Clone, Debug)]
pub struct GeometryNativeNoopHaltPairLease {
    resident: Arc<LoadedExecutionGeometryNativeNoopHaltSequence>,
}

/// Single exact resident slot for cloneable v5 pair leases.
#[derive(Debug, Default)]
pub struct GeometryNativeNoopHaltPairLeaseCache {
    resident: Option<Arc<LoadedExecutionGeometryNativeNoopHaltSequence>>,
}

/// Result of acquiring one exact resident pair lease.
pub type GeometryNativeNoopHaltPairCacheAcquireResult<MemoryError> = Result<
    GeometryNativeNoopHaltPairCacheAcquisition,
    Box<GeometryNativeNoopHaltPairCacheAcquireFailure<MemoryError>>,
>;

/// Result of releasing the resident pair after all leases are gone.
pub type GeometryNativeNoopHaltPairCacheReleaseResult<MemoryError> = Result<
    GeometryNativeNoopHaltPairCacheRelease,
    Box<ExecutionGeometryNativeNoopHaltPairReleaseFailure<MemoryError>>,
>;

impl<MemoryError: Display> Display
    for GeometryNativeNoopHaltPairCacheAcquireFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::IdentityOccupied => {
                f.write_str("different v5 pair identity already resident")
            },
            Self::Leased { leases } => {
                write!(f, "v5 pair replacement blocked by {leases} lease(s)")
            },
            Self::Load(error) => {
                write!(f, "v5 pair resident load failed: {error}")
            },
            Self::Release(error) => {
                write!(f, "v5 pair replacement release failed: {error}")
            },
        }
    }
}

impl GeometryNativeNoopHaltPairCacheAcquisition {
    /// Returns whether this acquisition loaded or reused mappings.
    #[must_use]
    pub const fn disposition(
        &self,
    ) -> GeometryNativeNoopHaltPairCacheDisposition {
        self.disposition
    }

    /// Consumes the acquisition and returns its immutable external lease.
    #[must_use]
    pub fn into_lease(self) -> GeometryNativeNoopHaltPairLease {
        self.lease
    }

    /// Returns the immutable lease retained by this acquisition.
    #[must_use]
    pub const fn lease(&self) -> &GeometryNativeNoopHaltPairLease {
        &self.lease
    }
}

impl GeometryNativeNoopHaltPairLease {
    /// Executes through the resident exact pair without mapping operations.
    ///
    /// # Errors
    ///
    /// Returns indexed v5 runner/completion failure from the resident pair.
    pub fn execute<Runner>(
        &self,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> ExecutionGeometryNativeNoopHaltLoadedResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        self.resident.execute(runner, buffers)
    }

    /// Returns exact synchronized weight reported by the resident pair owner.
    ///
    /// # Errors
    ///
    /// Returns overflow when the two child owner weights cannot be summed.
    pub fn resident_weight(
        &self,
    ) -> Result<
        ExecutionGeometryNativeNoopHaltResidentWeight,
        ExecutionGeometryNativeNoopHaltResidentWeightError,
    > {
        self.resident.resident_weight()
    }

    /// Returns the exact admitted v5 sequence retained beside the mappings.
    #[must_use]
    pub fn sequence(&self) -> &ExecutionGeometryNativeNoopHaltSequence {
        self.resident.sequence()
    }

    /// Reports whether two leases share the same resident pair allocation.
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

impl GeometryNativeNoopHaltPairLeaseCache {
    /// Loads or reuses the exact requested sequence as one immutable lease.
    ///
    /// A different sequence cannot evict or replace the current resident. This
    /// deliberately keeps the first v5 cache boundary smaller than the legacy
    /// multi-entry cache and makes exact geometry identity visible.
    ///
    /// # Errors
    ///
    /// Returns [`GeometryNativeNoopHaltPairCacheAcquireFailure`] for occupied
    /// different identity or pair loading failure.
    pub fn ensure<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        sequence: &ExecutionGeometryNativeNoopHaltSequence,
    ) -> GeometryNativeNoopHaltPairCacheAcquireResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        if let Some(resident) = &self.resident {
            if resident.sequence() != sequence {
                use GeometryNativeNoopHaltPairCacheAcquireFailure as Failure;
                return Err(Box::new(Failure::IdentityOccupied));
            }
            return Ok(GeometryNativeNoopHaltPairCacheAcquisition {
                disposition: GeometryNativeNoopHaltPairCacheDisposition::Hit,
                lease: GeometryNativeNoopHaltPairLease {
                    resident: Arc::clone(resident),
                },
            });
        }
        let loaded = sequence.load_pair(adapter).map_err(|error| {
            Box::new(GeometryNativeNoopHaltPairCacheAcquireFailure::Load(error))
        })?;
        let replacement_resident = Arc::new(loaded);
        let lease = GeometryNativeNoopHaltPairLease {
            resident: Arc::clone(&replacement_resident),
        };
        self.resident = Some(replacement_resident);
        Ok(GeometryNativeNoopHaltPairCacheAcquisition {
            disposition: GeometryNativeNoopHaltPairCacheDisposition::Inserted,
            lease,
        })
    }

    /// Reports whether any exact pair currently owns the resident slot.
    #[must_use]
    pub const fn has_resident(&self) -> bool {
        self.resident.is_some()
    }

    /// Constructs one empty single-resident v5 pair lease cache.
    #[must_use]
    pub const fn new() -> Self {
        Self { resident: None }
    }

    /// Releases resident mappings only when no external leases remain.
    ///
    /// Live leases return [`GeometryNativeNoopHaltPairCacheRelease::Leased`]
    /// without calling the adapter. A cleanup failure empties the cache because
    /// retry ownership moves into the returned pair release failure.
    ///
    /// # Errors
    ///
    /// Returns exact pair cleanup retry ownership when either mapping fails to
    /// release.
    pub fn release_if_unleased<Adapter>(
        &mut self,
        adapter: &mut Adapter,
    ) -> GeometryNativeNoopHaltPairCacheReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let Some(resident) = self.resident.take() else {
            return Ok(GeometryNativeNoopHaltPairCacheRelease::Missing);
        };
        let leases = Arc::strong_count(&resident).saturating_sub(1);
        if leases > 0 {
            self.resident = Some(resident);
            return Ok(GeometryNativeNoopHaltPairCacheRelease::Leased {
                leases,
            });
        }
        match Arc::try_unwrap(resident) {
            Ok(loaded) => loaded
                .release(adapter)
                .map(|()| GeometryNativeNoopHaltPairCacheRelease::Released),
            Err(retained) => {
                let remaining_leases =
                    Arc::strong_count(&retained).saturating_sub(1);
                self.resident = Some(retained);
                Ok(GeometryNativeNoopHaltPairCacheRelease::Leased {
                    leases: remaining_leases,
                })
            },
        }
    }

    /// Replaces a different resident only after every external lease is gone.
    ///
    /// Equal identity delegates to ordinary hit acquisition. Different identity
    /// with live leases rejects before adapter work. For an unleased different
    /// resident, old mappings release completely before the new pair is loaded;
    /// any release or load failure leaves the cache empty and transfers exact
    /// cleanup ownership through the returned failure.
    ///
    /// # Errors
    ///
    /// Returns lease blockage, previous-resident cleanup ownership, or new pair
    /// load failure without publishing partial replacement state.
    pub fn replace_if_unleased<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        sequence: &ExecutionGeometryNativeNoopHaltSequence,
    ) -> GeometryNativeNoopHaltPairCacheAcquireResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let Some(current_resident) = self.resident.as_ref() else {
            return self.ensure(adapter, sequence);
        };
        if current_resident.sequence() == sequence {
            return self.ensure(adapter, sequence);
        }
        let current_leases =
            Arc::strong_count(current_resident).saturating_sub(1);
        if current_leases > 0 {
            return Err(Box::new(
                GeometryNativeNoopHaltPairCacheAcquireFailure::Leased {
                    leases: current_leases,
                },
            ));
        }
        match self.release_if_unleased(adapter) {
            Ok(
                GeometryNativeNoopHaltPairCacheRelease::Released
                | GeometryNativeNoopHaltPairCacheRelease::Missing,
            ) => {},
            Ok(GeometryNativeNoopHaltPairCacheRelease::Leased {
                leases: blocked_leases,
            }) => {
                return Err(Box::new(
                    GeometryNativeNoopHaltPairCacheAcquireFailure::Leased {
                        leases: blocked_leases,
                    },
                ));
            },
            Err(error) => {
                return Err(Box::new(
                    GeometryNativeNoopHaltPairCacheAcquireFailure::Release(
                        error,
                    ),
                ));
            },
        }
        let loaded = sequence.load_pair(adapter).map_err(|error| {
            Box::new(GeometryNativeNoopHaltPairCacheAcquireFailure::Load(error))
        })?;
        let replacement_resident = Arc::new(loaded);
        let lease = GeometryNativeNoopHaltPairLease {
            resident: Arc::clone(&replacement_resident),
        };
        self.resident = Some(replacement_resident);
        Ok(GeometryNativeNoopHaltPairCacheAcquisition {
            disposition: GeometryNativeNoopHaltPairCacheDisposition::Replaced,
            lease,
        })
    }

    /// Returns the number of external resident leases.
    #[must_use]
    pub fn resident_lease_count(&self) -> usize {
        self.resident
            .as_ref()
            .map_or(0, |resident| Arc::strong_count(resident).saturating_sub(1))
    }
}
