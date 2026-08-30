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
//   - Single-resident lease reuse for one exact v5 jump/rotate/halt triple.
// - Must-Not:
//   - Mix sequence identities, invoke legacy cache keys, or release live
//     leases.
// - Allows:
//   - Inputs: admitted v5 sequence, executable-memory adapter, and runner.
//   - Outputs: immutable resident leases and explicit release disposition.
//   - Side effects: triple loading on miss and release after every lease is
//     gone.
// - Split-When:
//   - Multi-entry eviction, weighted capacity, or concurrent mutation is
//     needed.
// - Merge-When:
//   - A general v5 native lease cache subsumes exact triple identity and
//     cleanup.
// - Summary:
//   - Reuses one exact geometry-native triple behind cloneable leases.
// - Description:
//   - Uses full admitted-sequence equality and never canonical legacy identity.
// - Usage:
//   - Ensure a sequence, clone/use leases, drop them, then release the
//     resident.
// - Defaults:
//   - Different identity rejects; live leases block release without adapter
//     work.
//

//! Single-resident lease cache for the explicit-geometry jump/rotate/halt
//! triple.

use std::fmt::{Display, Formatter, Result as FormatResult};
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

type TripleCacheFailure<MemoryError> =
    GeometryNativeJumpRotateHaltTripleCacheAcquireFailure<MemoryError>;

/// Whether one lease acquisition loaded or reused resident mappings.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GeometryNativeJumpRotateHaltTripleCacheDisposition {
    /// The exact sequence already owned resident mappings.
    Hit,
    /// This acquisition loaded and published an empty resident slot.
    Inserted,
    /// An unleased different resident was released and replaced.
    Replaced,
}

/// Failure while acquiring one exact resident v5 triple.
#[derive(Debug, Eq, PartialEq)]
pub enum GeometryNativeJumpRotateHaltTripleCacheAcquireFailure<MemoryError> {
    /// A different exact sequence already owns the single resident slot.
    IdentityOccupied,
    /// Live leases prevent replacing a different resident identity.
    Leased {
        /// External resident owners that must be dropped first.
        leases: usize,
    },
    /// Loading the requested exact triple failed.
    Load(
        Box<
            ExecutionGeometryNativeJumpRotateHaltTripleLoadFailure<MemoryError>,
        >,
    ),
    /// Releasing the previous unleased resident failed during replacement.
    Release(
        Box<
            ExecutionGeometryNativeJumpRotateHaltTripleReleaseFailure<
                MemoryError,
            >,
        >,
    ),
}

/// Lease plus whether its mappings were inserted or reused.
#[derive(Debug)]
pub struct GeometryNativeJumpRotateHaltTripleCacheAcquisition {
    disposition: GeometryNativeJumpRotateHaltTripleCacheDisposition,
    lease: GeometryNativeJumpRotateHaltTripleLease,
}

/// Explicit result of attempting to release the single resident triple.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GeometryNativeJumpRotateHaltTripleCacheRelease {
    /// External leases still retain the resident triple.
    Leased {
        /// Number of external lease owners blocking release.
        leases: usize,
    },
    /// No resident triple exists.
    Missing,
    /// The unleased resident triple released all mappings.
    Released,
}

/// One immutable external owner of the resident v5 triple.
#[derive(Clone, Debug)]
pub struct GeometryNativeJumpRotateHaltTripleLease {
    resident: Arc<LoadedExecutionGeometryNativeJumpRotateHaltSequence>,
}

/// Single exact resident slot for cloneable v5 triple leases.
#[derive(Debug, Default)]
pub struct GeometryNativeJumpRotateHaltTripleLeaseCache {
    resident: Option<Arc<LoadedExecutionGeometryNativeJumpRotateHaltSequence>>,
}

/// Result of acquiring one exact resident triple lease.
pub type GeometryNativeJumpRotateHaltTripleCacheAcquireResult<MemoryError> =
    Result<
        GeometryNativeJumpRotateHaltTripleCacheAcquisition,
        Box<GeometryNativeJumpRotateHaltTripleCacheAcquireFailure<MemoryError>>,
    >;

/// Result of releasing the resident triple after all leases are gone.
pub type GeometryNativeJumpRotateHaltTripleCacheReleaseResult<MemoryError> =
    Result<
        GeometryNativeJumpRotateHaltTripleCacheRelease,
        Box<
            ExecutionGeometryNativeJumpRotateHaltTripleReleaseFailure<
                MemoryError,
            >,
        >,
    >;

impl<MemoryError: Display> Display
    for GeometryNativeJumpRotateHaltTripleCacheAcquireFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::IdentityOccupied => {
                f.write_str("different v5 triple identity already resident")
            },
            Self::Leased { leases } => {
                write!(f, "v5 triple replacement blocked by {leases} lease(s)")
            },
            Self::Load(error) => {
                write!(f, "v5 triple resident load failed: {error}")
            },
            Self::Release(error) => {
                write!(f, "v5 triple replacement release failed: {error}")
            },
        }
    }
}

impl GeometryNativeJumpRotateHaltTripleCacheAcquisition {
    /// Returns whether this acquisition loaded or reused mappings.
    #[must_use]
    pub const fn disposition(
        &self,
    ) -> GeometryNativeJumpRotateHaltTripleCacheDisposition {
        self.disposition
    }

    /// Consumes the acquisition and returns its immutable external lease.
    #[must_use]
    pub fn into_lease(self) -> GeometryNativeJumpRotateHaltTripleLease {
        self.lease
    }

    /// Returns the immutable lease retained by this acquisition.
    #[must_use]
    pub const fn lease(&self) -> &GeometryNativeJumpRotateHaltTripleLease {
        &self.lease
    }
}

impl GeometryNativeJumpRotateHaltTripleLease {
    /// Executes through the resident exact triple without mapping operations.
    ///
    /// # Errors
    ///
    /// Returns indexed v5 runner/completion failure from the resident triple.
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

    /// Returns exact resident weight from the synchronized mapping reports.
    ///
    /// # Errors
    ///
    /// Returns overflow when mapped byte capacities cannot be summed.
    pub fn resident_weight(
        &self,
    ) -> Result<
        ExecutionGeometryNativeJumpRotateHaltResidentWeight,
        ExecutionGeometryNativeJumpRotateHaltResidentWeightError,
    > {
        self.resident.resident_weight()
    }

    /// Returns the exact admitted v5 sequence retained beside the mappings.
    #[must_use]
    pub fn sequence(&self) -> &ExecutionGeometryNativeJumpRotateHaltSequence {
        self.resident.sequence()
    }

    /// Reports whether two leases share the same resident triple allocation.
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

impl GeometryNativeJumpRotateHaltTripleLeaseCache {
    /// Loads or reuses the exact requested sequence as one immutable lease.
    ///
    /// A different sequence cannot evict or replace the current resident. This
    /// deliberately keeps this v5 cache boundary smaller than the legacy
    /// multi-entry cache and makes exact geometry identity visible.
    ///
    /// # Errors
    ///
    /// Returns exact occupied-identity or triple-loading failure.
    pub fn ensure<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        sequence: &ExecutionGeometryNativeJumpRotateHaltSequence,
    ) -> GeometryNativeJumpRotateHaltTripleCacheAcquireResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        if let Some(resident) = &self.resident {
            if resident.sequence() != sequence {
                return Err(Box::new(TripleCacheFailure::IdentityOccupied));
            }
            return Ok(GeometryNativeJumpRotateHaltTripleCacheAcquisition {
                disposition:
                    GeometryNativeJumpRotateHaltTripleCacheDisposition::Hit,
                lease: GeometryNativeJumpRotateHaltTripleLease {
                    resident: Arc::clone(resident),
                },
            });
        }
        let loaded = sequence
            .load_triple(adapter)
            .map_err(|error| Box::new(TripleCacheFailure::Load(error)))?;
        let replacement_resident = Arc::new(loaded);
        let lease = GeometryNativeJumpRotateHaltTripleLease {
            resident: Arc::clone(&replacement_resident),
        };
        self.resident = Some(replacement_resident);
        Ok(GeometryNativeJumpRotateHaltTripleCacheAcquisition {
            disposition:
                GeometryNativeJumpRotateHaltTripleCacheDisposition::Inserted,
            lease,
        })
    }

    /// Reports whether any exact triple currently owns the resident slot.
    #[must_use]
    pub const fn has_resident(&self) -> bool {
        self.resident.is_some()
    }

    /// Constructs one empty single-resident v5 triple lease cache.
    #[must_use]
    pub const fn new() -> Self {
        Self { resident: None }
    }

    /// Releases resident mappings only when no external leases remain.
    ///
    /// Live leases return
    /// [`GeometryNativeJumpRotateHaltTripleCacheRelease::Leased`]
    /// without calling the adapter. A cleanup failure empties the cache because
    /// retry ownership moves into the returned triple release failure.
    ///
    /// # Errors
    ///
    /// Returns exact triple cleanup retry ownership when any mapping fails to
    /// release.
    pub fn release_if_unleased<Adapter>(
        &mut self,
        adapter: &mut Adapter,
    ) -> GeometryNativeJumpRotateHaltTripleCacheReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let Some(resident) = self.resident.take() else {
            return Ok(GeometryNativeJumpRotateHaltTripleCacheRelease::Missing);
        };
        let leases = Arc::strong_count(&resident).saturating_sub(1);
        if leases > 0 {
            self.resident = Some(resident);
            return Ok(
                GeometryNativeJumpRotateHaltTripleCacheRelease::Leased {
                    leases,
                },
            );
        }
        match Arc::try_unwrap(resident) {
            Ok(loaded) => loaded.release(adapter).map(|()| {
                GeometryNativeJumpRotateHaltTripleCacheRelease::Released
            }),
            Err(retained) => {
                let remaining_leases =
                    Arc::strong_count(&retained).saturating_sub(1);
                self.resident = Some(retained);
                Ok(GeometryNativeJumpRotateHaltTripleCacheRelease::Leased {
                    leases: remaining_leases,
                })
            },
        }
    }

    /// Replaces a different resident only after every external lease is gone.
    ///
    /// Equal identity delegates to ordinary hit acquisition. Different identity
    /// with live leases rejects before adapter work. For an unleased different
    /// resident, old mappings release completely before the new triple is
    /// loaded; any release or load failure leaves the cache empty and
    /// transfers exact cleanup ownership through the returned failure.
    ///
    /// # Errors
    ///
    /// Returns lease blockage, previous-resident cleanup ownership, or new
    /// triple load failure without publishing partial replacement state.
    pub fn replace_if_unleased<Adapter>(
        &mut self,
        adapter: &mut Adapter,
        sequence: &ExecutionGeometryNativeJumpRotateHaltSequence,
    ) -> GeometryNativeJumpRotateHaltTripleCacheAcquireResult<Adapter::Error>
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
            return Err(Box::new(TripleCacheFailure::Leased {
                leases: current_leases,
            }));
        }
        match self.release_if_unleased(adapter) {
            Ok(
                GeometryNativeJumpRotateHaltTripleCacheRelease::Released
                | GeometryNativeJumpRotateHaltTripleCacheRelease::Missing,
            ) => {},
            Ok(GeometryNativeJumpRotateHaltTripleCacheRelease::Leased {
                leases: blocked_leases,
            }) => {
                return Err(Box::new(TripleCacheFailure::Leased {
                    leases: blocked_leases,
                }));
            },
            Err(error) => {
                return Err(Box::new(TripleCacheFailure::Release(error)));
            },
        }
        let loaded = sequence
            .load_triple(adapter)
            .map_err(|error| Box::new(TripleCacheFailure::Load(error)))?;
        let replacement_resident = Arc::new(loaded);
        let lease = GeometryNativeJumpRotateHaltTripleLease {
            resident: Arc::clone(&replacement_resident),
        };
        self.resident = Some(replacement_resident);
        Ok(GeometryNativeJumpRotateHaltTripleCacheAcquisition {
            disposition:
                GeometryNativeJumpRotateHaltTripleCacheDisposition::Replaced,
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
