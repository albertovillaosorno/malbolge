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
//   - Typed cross-template ownership for reviewed explicit-geometry residents.
// - Must-Not:
//   - Merge template identities, invent generic execution semantics, or cache.
// - Allows:
//   - Inputs: exact admitted initial-jump, no-op/halt, rotate/halt, or
//     full-path plans.
//   - Outputs: typed loaded owner, exact resident weight, and cleanup
//     ownership.
//   - Side effects: delegated executable loading and release only.
// - Split-When:
//   - Cross-template eviction, leasing, or execution policy gains authority.
// - Merge-When:
//   - Every reviewed template shares identical resident lifecycle proofs.
// - Summary:
//   - Gives heterogeneous v5 residents one typed lifecycle boundary.
// - Description:
//   - Preserves variant-specific identity and cleanup while sharing weight.
// - Usage:
//   - Wrap one admitted plan, load it, inspect exact weight, then release it.
// - Defaults:
//   - Template variants never compare equal and execution remains specialized.
//

//! Typed ownership boundary for heterogeneous explicit-geometry residents.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::ProfileMachineState;

use crate::execution_native::{
    ExecutionGeometryNativeExecutableReleaseFailure,
    ExecutionGeometryNativeRunner, NativeExecutableLoadFailure,
    NativeExecutableMemoryAdapter, NativeRegionBuffers,
};
use crate::geometry_native_initial_jump_data::{
    ExecutionGeometryNativeInitialJumpDataAdmission,
    ExecutionGeometryNativeInitialJumpDataCompletion,
    ExecutionGeometryNativeInitialJumpDataOwnedFailure,
    LoadedExecutionGeometryNativeInitialJumpData,
};
use crate::geometry_native_jump_rotate_halt_sequence::{
    ExecutionGeometryNativeJumpRotateHaltOutcome,
    ExecutionGeometryNativeJumpRotateHaltOwnedFailure,
    ExecutionGeometryNativeJumpRotateHaltSequence,
    ExecutionGeometryNativeJumpRotateHaltTripleLoadFailure,
    ExecutionGeometryNativeJumpRotateHaltTripleReleaseFailure,
    LoadedExecutionGeometryNativeJumpRotateHaltSequence,
};
use crate::geometry_native_rotate_sequence::{
    ExecutionGeometryNativeRotateHaltLoadedFailure,
    ExecutionGeometryNativeRotateHaltOutcome,
    ExecutionGeometryNativeRotateHaltPairLoadFailure,
    ExecutionGeometryNativeRotateHaltPairReleaseFailure,
    ExecutionGeometryNativeRotateHaltSequence,
    LoadedExecutionGeometryNativeRotateHaltSequence,
};
use crate::geometry_native_sequence::{
    ExecutionGeometryNativeNoopHaltLoadedFailure,
    ExecutionGeometryNativeNoopHaltOutcome,
    ExecutionGeometryNativeNoopHaltPairLoadFailure,
    ExecutionGeometryNativeNoopHaltPairReleaseFailure,
    ExecutionGeometryNativeNoopHaltSequence,
    LoadedExecutionGeometryNativeNoopHaltSequence,
};

type FullLoadFailure<MemoryError> =
    ExecutionGeometryNativeJumpRotateHaltTripleLoadFailure<MemoryError>;
type FullReleaseFailure<MemoryError> =
    ExecutionGeometryNativeJumpRotateHaltTripleReleaseFailure<MemoryError>;
type InitialJumpLoadFailure<MemoryError> =
    NativeExecutableLoadFailure<MemoryError>;
type InitialJumpReleaseFailure<MemoryError> =
    ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>;
type NoopLoadFailure<MemoryError> =
    ExecutionGeometryNativeNoopHaltPairLoadFailure<MemoryError>;
type NoopReleaseFailure<MemoryError> =
    ExecutionGeometryNativeNoopHaltPairReleaseFailure<MemoryError>;
type RotateLoadFailure<MemoryError> =
    ExecutionGeometryNativeRotateHaltPairLoadFailure<MemoryError>;
type RotateReleaseFailure<MemoryError> =
    ExecutionGeometryNativeRotateHaltPairReleaseFailure<MemoryError>;

/// Exact reviewed template represented by one resident plan or loaded owner.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GeometryNativeResidentKind {
    /// Complete initial-jump, rotate, halt path.
    FullPath,
    /// One checkpoint-bound aliasing initial jump-data step.
    InitialJump,
    /// No-operation followed by halt.
    NoOperationPair,
    /// Rotate followed by halt.
    RotatePair,
}

/// Exact admitted identity for one heterogeneous explicit-geometry resident.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum GeometryNativeResidentPlan {
    /// Complete initial-jump, rotate, halt sequence.
    FullPath(Box<ExecutionGeometryNativeJumpRotateHaltSequence>),
    /// One exact checkpoint-bound initial jump-data admission.
    InitialJump(Box<ExecutionGeometryNativeInitialJumpDataAdmission>),
    /// No-operation followed by halt sequence.
    NoOperationPair(Box<ExecutionGeometryNativeNoopHaltSequence>),
    /// Rotate followed by halt sequence.
    RotatePair(Box<ExecutionGeometryNativeRotateHaltSequence>),
}

/// One loaded heterogeneous resident retaining its exact specialized owner.
#[derive(Debug)]
pub enum GeometryNativeLoadedResident {
    /// Complete initial-jump, rotate, halt owner.
    FullPath(Box<LoadedExecutionGeometryNativeJumpRotateHaltSequence>),
    /// One reusable checkpoint-bound initial jump-data owner.
    InitialJump(Box<LoadedExecutionGeometryNativeInitialJumpData>),
    /// No-operation followed by halt owner.
    NoOperationPair(Box<LoadedExecutionGeometryNativeNoopHaltSequence>),
    /// Rotate followed by halt owner.
    RotatePair(Box<LoadedExecutionGeometryNativeRotateHaltSequence>),
}

/// Successful or safely suspended execution through one typed resident.
#[derive(Debug, Eq, PartialEq)]
pub enum GeometryNativeResidentExecutionOutcome {
    /// Complete initial-jump, rotate, halt outcome.
    FullPath(Box<ExecutionGeometryNativeJumpRotateHaltOutcome>),
    /// One initial jump-data completion.
    InitialJump(Box<ExecutionGeometryNativeInitialJumpDataCompletion>),
    /// No-operation followed by halt outcome.
    NoOperationPair(Box<ExecutionGeometryNativeNoopHaltOutcome>),
    /// Rotate followed by halt outcome.
    RotatePair(Box<ExecutionGeometryNativeRotateHaltOutcome>),
}

/// Typed execution failure retaining the specialized resident failure.
#[derive(Debug, Eq, PartialEq)]
pub enum GeometryNativeResidentExecutionFailure<RunnerError> {
    /// Complete full-path execution failed.
    FullPath(
        Box<ExecutionGeometryNativeJumpRotateHaltOwnedFailure<RunnerError>>,
    ),
    /// Initial jump-data owner execution failed.
    InitialJump(
        Box<ExecutionGeometryNativeInitialJumpDataOwnedFailure<RunnerError>>,
    ),
    /// No-operation/halt pair execution failed.
    NoOperationPair(
        Box<ExecutionGeometryNativeNoopHaltLoadedFailure<RunnerError>>,
    ),
    /// Rotate/halt pair execution failed.
    RotatePair(
        Box<ExecutionGeometryNativeRotateHaltLoadedFailure<RunnerError>>,
    ),
}

/// Exact synchronized resources retained by one heterogeneous resident.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GeometryNativeResidentWeight {
    mapped_bytes: usize,
    mappings: usize,
}

/// Failure while deriving heterogeneous resident mapping weight.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GeometryNativeResidentWeightError {
    /// Summed synchronized mapped bytes exceeded host `usize`.
    MappedBytesOverflow,
    /// Summed live mapping count exceeded host `usize`.
    MappingsOverflow,
}

/// Failure while loading one typed heterogeneous resident.
#[derive(Debug, Eq, PartialEq)]
pub enum GeometryNativeResidentLoadFailure<MemoryError> {
    /// Complete full-path triple loading failed.
    FullPath(Box<FullLoadFailure<MemoryError>>),
    /// Initial jump-data executable loading failed.
    InitialJump(Box<InitialJumpLoadFailure<MemoryError>>),
    /// No-operation/halt pair loading failed.
    NoOperationPair(Box<NoopLoadFailure<MemoryError>>),
    /// Rotate/halt pair loading failed.
    RotatePair(Box<RotateLoadFailure<MemoryError>>),
}

/// Failed heterogeneous release retaining variant-specific retry ownership.
#[derive(Debug, Eq, PartialEq)]
pub enum GeometryNativeResidentReleaseFailure<MemoryError> {
    /// Complete full-path cleanup remains incomplete.
    FullPath(Box<FullReleaseFailure<MemoryError>>),
    /// Initial jump-data mapping cleanup remains incomplete.
    InitialJump(Box<InitialJumpReleaseFailure<MemoryError>>),
    /// No-operation/halt cleanup remains incomplete.
    NoOperationPair(Box<NoopReleaseFailure<MemoryError>>),
    /// Rotate/halt cleanup remains incomplete.
    RotatePair(Box<RotateReleaseFailure<MemoryError>>),
}

/// Result of executing one exact loaded heterogeneous v5 resident.
pub type GeometryNativeResidentExecutionResult<RunnerError> = Result<
    GeometryNativeResidentExecutionOutcome,
    Box<GeometryNativeResidentExecutionFailure<RunnerError>>,
>;

/// Result of loading one exact heterogeneous v5 resident.
pub type GeometryNativeResidentLoadResult<MemoryError> = Result<
    GeometryNativeLoadedResident,
    Box<GeometryNativeResidentLoadFailure<MemoryError>>,
>;

/// Result of releasing one exact heterogeneous v5 resident.
pub type GeometryNativeResidentReleaseResult<MemoryError> =
    Result<(), Box<GeometryNativeResidentReleaseFailure<MemoryError>>>;

impl<RunnerError: Display> Display
    for GeometryNativeResidentExecutionFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::FullPath(error) => Display::fmt(error, f),
            Self::InitialJump(error) => Display::fmt(error, f),
            Self::NoOperationPair(error) => Display::fmt(error, f),
            Self::RotatePair(error) => Display::fmt(error, f),
        }
    }
}

impl Display for GeometryNativeResidentWeightError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::MappedBytesOverflow => {
                f.write_str("heterogeneous v5 resident mapped-byte overflow")
            },
            Self::MappingsOverflow => {
                f.write_str("heterogeneous v5 resident mapping-count overflow")
            },
        }
    }
}

impl<MemoryError> GeometryNativeResidentLoadFailure<MemoryError> {
    /// Reports whether this primary load failure still owns rollback work.
    #[must_use]
    pub fn cleanup_pending(&self) -> bool {
        match self {
            Self::FullPath(error) => error.cleanup_pending(),
            Self::InitialJump(error) => error.cleanup_pending(),
            Self::NoOperationPair(error) => error.cleanup_pending(),
            Self::RotatePair(error) => error.cleanup_pending(),
        }
    }

    /// Retries retained rollback with the same adapter and preserves identity.
    #[must_use]
    pub fn retry_cleanup<Adapter>(self, adapter: &mut Adapter) -> Self
    where
        Adapter: NativeExecutableMemoryAdapter<Error = MemoryError>,
    {
        match self {
            Self::FullPath(error) => {
                Self::FullPath(Box::new((*error).retry_cleanup(adapter)))
            },
            Self::InitialJump(error) => {
                Self::InitialJump(Box::new((*error).retry_cleanup(adapter)))
            },
            Self::NoOperationPair(error) => {
                Self::NoOperationPair(Box::new((*error).retry_cleanup(adapter)))
            },
            Self::RotatePair(error) => {
                Self::RotatePair(Box::new((*error).retry_cleanup(adapter)))
            },
        }
    }
}

impl<MemoryError: Display> Display
    for GeometryNativeResidentLoadFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::FullPath(error) => Display::fmt(error, f),
            Self::InitialJump(error) => Display::fmt(error, f),
            Self::NoOperationPair(error) => Display::fmt(error, f),
            Self::RotatePair(error) => Display::fmt(error, f),
        }
    }
}

impl<MemoryError: Display> Display
    for GeometryNativeResidentReleaseFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::FullPath(error) => Display::fmt(error, f),
            Self::InitialJump(error) => Display::fmt(error, f),
            Self::NoOperationPair(error) => Display::fmt(error, f),
            Self::RotatePair(error) => Display::fmt(error, f),
        }
    }
}

impl GeometryNativeLoadedResident {
    /// Executes through the specialized loaded owner without adapter work.
    ///
    /// # Errors
    ///
    /// Returns the exact variant-specific execution failure without changing
    /// resident ownership or translating step semantics.
    pub fn execute<Runner>(
        &self,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> GeometryNativeResidentExecutionResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        match self {
            Self::FullPath(loaded) => loaded
                .execute(runner, buffers)
                .map(|outcome| {
                    GeometryNativeResidentExecutionOutcome::FullPath(Box::new(
                        outcome,
                    ))
                })
                .map_err(|error| {
                    Box::new(GeometryNativeResidentExecutionFailure::FullPath(
                        error,
                    ))
                }),
            Self::InitialJump(loaded) => loaded
                .execute(runner, buffers)
                .map(|outcome| {
                    GeometryNativeResidentExecutionOutcome::InitialJump(
                        Box::new(outcome),
                    )
                })
                .map_err(|error| {
                    Box::new(
                        GeometryNativeResidentExecutionFailure::InitialJump(
                            error,
                        ),
                    )
                }),
            Self::NoOperationPair(loaded) => loaded
                .execute(runner, buffers)
                .map(|outcome| {
                    GeometryNativeResidentExecutionOutcome::NoOperationPair(
                        Box::new(outcome),
                    )
                })
                .map_err(|error| {
                    Box::new(
                        GeometryNativeResidentExecutionFailure::NoOperationPair(
                            error,
                        ),
                    )
                }),
            Self::RotatePair(loaded) => loaded
                .execute(runner, buffers)
                .map(|outcome| {
                    GeometryNativeResidentExecutionOutcome::RotatePair(
                        Box::new(outcome),
                    )
                })
                .map_err(|error| {
                    Box::new(
                        GeometryNativeResidentExecutionFailure::RotatePair(
                            error,
                        ),
                    )
                }),
        }
    }

    /// Returns the exact reviewed template retained by this loaded owner.
    #[must_use]
    pub const fn kind(&self) -> GeometryNativeResidentKind {
        match self {
            Self::FullPath(_loaded) => GeometryNativeResidentKind::FullPath,
            Self::InitialJump(_loaded) => {
                GeometryNativeResidentKind::InitialJump
            },
            Self::NoOperationPair(_loaded) => {
                GeometryNativeResidentKind::NoOperationPair
            },
            Self::RotatePair(_loaded) => GeometryNativeResidentKind::RotatePair,
        }
    }

    /// Reports whether this owner matches the complete exact admitted plan.
    #[must_use]
    pub fn matches_plan(
        &self,
        requested_plan: &GeometryNativeResidentPlan,
    ) -> bool {
        match (self, requested_plan) {
            (
                Self::FullPath(loaded),
                GeometryNativeResidentPlan::FullPath(exact_plan),
            ) => loaded.sequence() == exact_plan.as_ref(),
            (
                Self::InitialJump(loaded),
                GeometryNativeResidentPlan::InitialJump(exact_plan),
            ) => loaded.admission() == exact_plan.as_ref(),
            (
                Self::NoOperationPair(loaded),
                GeometryNativeResidentPlan::NoOperationPair(exact_plan),
            ) => loaded.sequence() == exact_plan.as_ref(),
            (
                Self::RotatePair(loaded),
                GeometryNativeResidentPlan::RotatePair(exact_plan),
            ) => loaded.sequence() == exact_plan.as_ref(),
            _ => false,
        }
    }

    /// Reconstructs the exact admitted plan retained by this loaded owner.
    #[must_use]
    pub fn plan(&self) -> GeometryNativeResidentPlan {
        match self {
            Self::FullPath(loaded) => GeometryNativeResidentPlan::FullPath(
                Box::new(loaded.sequence().clone()),
            ),
            Self::InitialJump(loaded) => {
                GeometryNativeResidentPlan::InitialJump(Box::new(
                    loaded.admission().clone(),
                ))
            },
            Self::NoOperationPair(loaded) => {
                GeometryNativeResidentPlan::NoOperationPair(Box::new(
                    loaded.sequence().clone(),
                ))
            },
            Self::RotatePair(loaded) => GeometryNativeResidentPlan::RotatePair(
                Box::new(loaded.sequence().clone()),
            ),
        }
    }

    /// Releases the specialized owner and preserves typed cleanup retry
    /// evidence.
    ///
    /// # Errors
    ///
    /// Returns the exact variant-specific release ownership when any mapping
    /// remains live.
    pub fn release<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> GeometryNativeResidentReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        match self {
            Self::FullPath(loaded) => {
                loaded.release(adapter).map_err(|error| {
                    Box::new(GeometryNativeResidentReleaseFailure::FullPath(
                        error,
                    ))
                })
            },
            Self::InitialJump(loaded) => {
                loaded.release(adapter).map_err(|error| {
                    Box::new(GeometryNativeResidentReleaseFailure::InitialJump(
                        error,
                    ))
                })
            },
            Self::NoOperationPair(loaded) => {
                loaded.release(adapter).map_err(|error| {
                    Box::new(
                        GeometryNativeResidentReleaseFailure::NoOperationPair(
                            error,
                        ),
                    )
                })
            },
            Self::RotatePair(loaded) => {
                loaded.release(adapter).map_err(|error| {
                    Box::new(GeometryNativeResidentReleaseFailure::RotatePair(
                        error,
                    ))
                })
            },
        }
    }

    /// Returns exact synchronized mapping weight for this specialized owner.
    ///
    /// # Errors
    ///
    /// Returns mapped-byte overflow when the resident reports cannot be summed.
    pub fn resident_weight(
        &self,
    ) -> Result<GeometryNativeResidentWeight, GeometryNativeResidentWeightError>
    {
        let (mapped_bytes, mappings) = match self {
            Self::FullPath(loaded) => {
                let weight = loaded.resident_weight().map_err(|_error| {
                    GeometryNativeResidentWeightError::MappedBytesOverflow
                })?;
                (weight.mapped_bytes(), weight.mappings())
            },
            Self::InitialJump(loaded) => {
                let weight = loaded.resident_weight();
                (weight.mapped_bytes(), weight.mappings())
            },
            Self::NoOperationPair(loaded) => (
                sum_mapped_bytes([
                    loaded.no_operation().mapping().mapped_len(),
                    loaded.halt().mapping().mapped_len(),
                ])?,
                2,
            ),
            Self::RotatePair(loaded) => (
                sum_mapped_bytes([
                    loaded.rotate().mapping().mapped_len(),
                    loaded.halt().mapping().mapped_len(),
                ])?,
                2,
            ),
        };
        Ok(GeometryNativeResidentWeight { mapped_bytes, mappings })
    }
}

impl GeometryNativeResidentExecutionOutcome {
    /// Returns the reviewed template that produced this execution outcome.
    #[must_use]
    pub const fn kind(&self) -> GeometryNativeResidentKind {
        match self {
            Self::FullPath(_outcome) => GeometryNativeResidentKind::FullPath,
            Self::InitialJump(_outcome) => {
                GeometryNativeResidentKind::InitialJump
            },
            Self::NoOperationPair(_outcome) => {
                GeometryNativeResidentKind::NoOperationPair
            },
            Self::RotatePair(_outcome) => {
                GeometryNativeResidentKind::RotatePair
            },
        }
    }

    /// Returns the completed or last committed opaque-geometry checkpoint.
    #[must_use]
    pub fn state(&self) -> &ProfileMachineState {
        match self {
            Self::FullPath(outcome) => outcome.state(),
            Self::InitialJump(outcome) => outcome.state(),
            Self::NoOperationPair(outcome) => outcome.state(),
            Self::RotatePair(outcome) => outcome.state(),
        }
    }
}

impl GeometryNativeResidentPlan {
    /// Returns the reviewed template represented by this exact plan.
    #[must_use]
    pub const fn kind(&self) -> GeometryNativeResidentKind {
        match self {
            Self::FullPath(_plan) => GeometryNativeResidentKind::FullPath,
            Self::InitialJump(_plan) => GeometryNativeResidentKind::InitialJump,
            Self::NoOperationPair(_plan) => {
                GeometryNativeResidentKind::NoOperationPair
            },
            Self::RotatePair(_plan) => GeometryNativeResidentKind::RotatePair,
        }
    }

    /// Loads one exact specialized owner behind this heterogeneous plan.
    ///
    /// # Errors
    ///
    /// Returns the variant-specific load failure with any partial-load cleanup
    /// ownership retained by that template.
    pub fn load<Adapter>(
        &self,
        adapter: &mut Adapter,
    ) -> GeometryNativeResidentLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        match self {
            Self::FullPath(plan) => plan
                .load_triple(adapter)
                .map(|loaded| {
                    GeometryNativeLoadedResident::FullPath(Box::new(loaded))
                })
                .map_err(|error| {
                    Box::new(GeometryNativeResidentLoadFailure::FullPath(error))
                }),
            Self::InitialJump(plan) => plan
                .load_owned(adapter)
                .map(|loaded| {
                    GeometryNativeLoadedResident::InitialJump(Box::new(loaded))
                })
                .map_err(|error| {
                    Box::new(GeometryNativeResidentLoadFailure::InitialJump(
                        error,
                    ))
                }),
            Self::NoOperationPair(plan) => plan
                .load_pair(adapter)
                .map(|loaded| {
                    GeometryNativeLoadedResident::NoOperationPair(Box::new(
                        loaded,
                    ))
                })
                .map_err(|error| {
                    Box::new(
                        GeometryNativeResidentLoadFailure::NoOperationPair(
                            error,
                        ),
                    )
                }),
            Self::RotatePair(plan) => plan
                .load_pair(adapter)
                .map(|loaded| {
                    GeometryNativeLoadedResident::RotatePair(Box::new(loaded))
                })
                .map_err(|error| {
                    Box::new(GeometryNativeResidentLoadFailure::RotatePair(
                        error,
                    ))
                }),
        }
    }
}

impl<MemoryError> GeometryNativeResidentReleaseFailure<MemoryError> {
    /// Retries every mapping still owned by this exact template failure.
    ///
    /// # Errors
    ///
    /// Returns refreshed variant-specific cleanup ownership when retry remains
    /// incomplete.
    pub fn retry<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> GeometryNativeResidentReleaseResult<MemoryError>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = MemoryError>,
    {
        match self {
            Self::FullPath(error) => (*error)
                .retry(adapter)
                .map_err(|retry_error| Box::new(Self::FullPath(retry_error))),
            Self::InitialJump(error) => {
                (*error).retry(adapter).map_err(|retry_error| {
                    Box::new(Self::InitialJump(Box::new(retry_error)))
                })
            },
            Self::NoOperationPair(error) => {
                (*error).retry(adapter).map_err(|retry_error| {
                    Box::new(Self::NoOperationPair(retry_error))
                })
            },
            Self::RotatePair(error) => (*error)
                .retry(adapter)
                .map_err(|retry_error| Box::new(Self::RotatePair(retry_error))),
        }
    }
}

impl GeometryNativeResidentWeight {
    /// Returns exact synchronized mapped bytes retained by this resident.
    #[must_use]
    pub const fn mapped_bytes(self) -> usize {
        self.mapped_bytes
    }

    /// Returns exact live executable mappings retained by this resident.
    #[must_use]
    pub const fn mappings(self) -> usize {
        self.mappings
    }
}

fn sum_mapped_bytes<const N: usize>(
    mapped_lengths: [usize; N],
) -> Result<usize, GeometryNativeResidentWeightError> {
    mapped_lengths
        .into_iter()
        .try_fold(0usize, usize::checked_add)
        .ok_or(GeometryNativeResidentWeightError::MappedBytesOverflow)
}
