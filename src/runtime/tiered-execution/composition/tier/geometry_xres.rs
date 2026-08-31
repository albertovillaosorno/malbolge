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
//   - Inputs: exact reviewed single-step, prefix, pair, full-path, or
//     crazy-theorem plans.
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
use crate::geometry_native_admission::{
    ExecutionGeometryNativeInitialHaltAdmission,
    ExecutionGeometryNativeInitialHaltCompletion,
    ExecutionGeometryNativeInitialHaltOwnedFailure,
    LoadedExecutionGeometryNativeInitialHalt,
};
use crate::geometry_native_crazy::{
    ExecutionGeometryNativeCrazyAdmission,
    ExecutionGeometryNativeCrazyCompletion,
    ExecutionGeometryNativeCrazyOwnedFailure,
    LoadedExecutionGeometryNativeCrazy,
};
use crate::geometry_native_crazy_prefix::{
    ExecutionGeometryNativeCrazyPrefix,
    ExecutionGeometryNativeCrazyPrefixOutcome,
};
use crate::geometry_native_crazy_prefix_owner::{
    ExecutionGeometryNativeCrazyPrefixLoadFailure,
    ExecutionGeometryNativeCrazyPrefixOwnedFailure,
    ExecutionGeometryNativeCrazyPrefixReleaseFailure,
    ExecutionGeometryNativeCrazyPrefixResidentWeightError,
    LoadedExecutionGeometryNativeCrazyPrefix,
};
use crate::geometry_native_initial_jump_data::{
    ExecutionGeometryNativeInitialJumpDataAdmission,
    ExecutionGeometryNativeInitialJumpDataCompletion,
    ExecutionGeometryNativeInitialJumpDataOwnedFailure,
    LoadedExecutionGeometryNativeInitialJumpData,
};
use crate::geometry_native_input::{
    ExecutionGeometryNativeInputAdmission,
    ExecutionGeometryNativeInputCompletion,
    ExecutionGeometryNativeInputOwnedFailure,
    LoadedExecutionGeometryNativeInput,
};
use crate::geometry_native_jump_rotate_crazy_halt_owner::{
    ExecutionGeometryNativeJumpRotateCrazyHaltLoadFailure,
    ExecutionGeometryNativeJumpRotateCrazyHaltOwnedFailure,
    ExecutionGeometryNativeJumpRotateCrazyHaltReleaseFailure,
    ExecutionGeometryNativeJumpRotateCrazyHaltResidentWeightError,
    LoadedCrazyTheoremSequence,
};
use crate::geometry_native_jump_rotate_crazy_halt_sequence::{
    ExecutionGeometryNativeJumpRotateCrazyHaltOutcome,
    ExecutionGeometryNativeJumpRotateCrazyHaltSequence,
};
use crate::geometry_native_jump_rotate_halt_sequence::{
    ExecutionGeometryNativeJumpRotateHaltOutcome,
    ExecutionGeometryNativeJumpRotateHaltOwnedFailure,
    ExecutionGeometryNativeJumpRotateHaltResidentWeightError,
    ExecutionGeometryNativeJumpRotateHaltSequence,
    ExecutionGeometryNativeJumpRotateHaltTripleLoadFailure,
    ExecutionGeometryNativeJumpRotateHaltTripleReleaseFailure,
    LoadedExecutionGeometryNativeJumpRotateHaltSequence,
};
use crate::geometry_native_no_operation::{
    ExecutionGeometryNativeNoOperationAdmission,
    ExecutionGeometryNativeNoOperationCompletion,
    ExecutionGeometryNativeNoOperationOwnedFailure,
    LoadedExecutionGeometryNativeNoOperation,
};
use crate::geometry_native_output::{
    ExecutionGeometryNativeOutputAdmission,
    ExecutionGeometryNativeOutputCompletion,
    ExecutionGeometryNativeOutputOwnedFailure,
    LoadedExecutionGeometryNativeOutput,
};
use crate::geometry_native_rotate::{
    ExecutionGeometryNativeRotateAdmission,
    ExecutionGeometryNativeRotateCompletion,
    ExecutionGeometryNativeRotateOwnedFailure,
    LoadedExecutionGeometryNativeRotate,
};
use crate::geometry_native_rotate_sequence::{
    ExecutionGeometryNativeRotateHaltLoadedFailure,
    ExecutionGeometryNativeRotateHaltOutcome,
    ExecutionGeometryNativeRotateHaltPairLoadFailure,
    ExecutionGeometryNativeRotateHaltPairReleaseFailure,
    ExecutionGeometryNativeRotateHaltResidentWeightError,
    ExecutionGeometryNativeRotateHaltSequence,
    LoadedExecutionGeometryNativeRotateHaltSequence,
};
use crate::geometry_native_sequence::{
    ExecutionGeometryNativeNoopHaltLoadedFailure,
    ExecutionGeometryNativeNoopHaltOutcome,
    ExecutionGeometryNativeNoopHaltPairLoadFailure,
    ExecutionGeometryNativeNoopHaltPairReleaseFailure,
    ExecutionGeometryNativeNoopHaltResidentWeightError,
    ExecutionGeometryNativeNoopHaltSequence,
    LoadedExecutionGeometryNativeNoopHaltSequence,
};

type CrazyLoadFailure<MemoryError> = NativeExecutableLoadFailure<MemoryError>;
type CrazyPrefixLoadFailure<MemoryError> =
    ExecutionGeometryNativeCrazyPrefixLoadFailure<MemoryError>;
type CrazyPrefixReleaseFailure<MemoryError> =
    ExecutionGeometryNativeCrazyPrefixReleaseFailure<MemoryError>;
type CrazyPrefixWeightError =
    ExecutionGeometryNativeCrazyPrefixResidentWeightError;
type CrazyReleaseFailure<MemoryError> =
    ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>;
type CrazyTheoremLoadFailure<MemoryError> =
    ExecutionGeometryNativeJumpRotateCrazyHaltLoadFailure<MemoryError>;
type CrazyTheoremReleaseFailure<MemoryError> =
    ExecutionGeometryNativeJumpRotateCrazyHaltReleaseFailure<MemoryError>;
type CrazyTheoremWeightError =
    ExecutionGeometryNativeJumpRotateCrazyHaltResidentWeightError;
type FullLoadFailure<MemoryError> =
    ExecutionGeometryNativeJumpRotateHaltTripleLoadFailure<MemoryError>;
type FullReleaseFailure<MemoryError> =
    ExecutionGeometryNativeJumpRotateHaltTripleReleaseFailure<MemoryError>;
type FullWeightError = ExecutionGeometryNativeJumpRotateHaltResidentWeightError;
type InitialHaltLoadFailure<MemoryError> =
    NativeExecutableLoadFailure<MemoryError>;
type InitialHaltReleaseFailure<MemoryError> =
    ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>;
type InitialJumpLoadFailure<MemoryError> =
    NativeExecutableLoadFailure<MemoryError>;
type InitialJumpReleaseFailure<MemoryError> =
    ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>;
type InputLoadFailure<MemoryError> = NativeExecutableLoadFailure<MemoryError>;
type InputReleaseFailure<MemoryError> =
    ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>;
type NoOperationLoadFailure<MemoryError> =
    NativeExecutableLoadFailure<MemoryError>;
type NoOperationReleaseFailure<MemoryError> =
    ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>;
type NoopLoadFailure<MemoryError> =
    ExecutionGeometryNativeNoopHaltPairLoadFailure<MemoryError>;
type NoopReleaseFailure<MemoryError> =
    ExecutionGeometryNativeNoopHaltPairReleaseFailure<MemoryError>;
type NoopWeightError = ExecutionGeometryNativeNoopHaltResidentWeightError;
type OutputLoadFailure<MemoryError> = NativeExecutableLoadFailure<MemoryError>;
type OutputReleaseFailure<MemoryError> =
    ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>;
type RotateLoadFailure<MemoryError> =
    ExecutionGeometryNativeRotateHaltPairLoadFailure<MemoryError>;
type RotateReleaseFailure<MemoryError> =
    ExecutionGeometryNativeRotateHaltPairReleaseFailure<MemoryError>;
type RotateWeightError = ExecutionGeometryNativeRotateHaltResidentWeightError;
type RotateStepLoadFailure<MemoryError> =
    NativeExecutableLoadFailure<MemoryError>;
type RotateStepReleaseFailure<MemoryError> =
    ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>;

/// Exact reviewed template represented by one resident plan or loaded owner.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GeometryNativeResidentKind {
    /// One checkpoint-bound crazy step.
    Crazy,
    /// Exact four-crazy theorem prefix.
    CrazyPrefix,
    /// Complete initial-jump, rotate, four-crazy, halt theorem path.
    CrazyTheorem,
    /// Complete initial-jump, rotate, halt path.
    FullPath,
    /// One checkpoint-bound initial halt step.
    InitialHalt,
    /// One checkpoint-bound aliasing initial jump-data step.
    InitialJump,
    /// One checkpoint-bound byte or EOF input step.
    Input,
    /// One checkpoint-bound no-operation step.
    NoOperation,
    /// No-operation followed by halt.
    NoOperationPair,
    /// One checkpoint-bound output step.
    Output,
    /// One checkpoint-bound rotate step.
    Rotate,
    /// Rotate followed by halt.
    RotatePair,
}

/// Exact admitted identity for one heterogeneous explicit-geometry resident.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum GeometryNativeResidentPlan {
    /// One exact checkpoint-bound crazy admission.
    Crazy(Box<ExecutionGeometryNativeCrazyAdmission>),
    /// Exact four-crazy theorem prefix.
    CrazyPrefix(Box<ExecutionGeometryNativeCrazyPrefix>),
    /// Complete exact crazy-theorem sequence.
    CrazyTheorem(Box<ExecutionGeometryNativeJumpRotateCrazyHaltSequence>),
    /// Complete initial-jump, rotate, halt sequence.
    FullPath(Box<ExecutionGeometryNativeJumpRotateHaltSequence>),
    /// One exact checkpoint-bound initial-halt admission.
    InitialHalt(Box<ExecutionGeometryNativeInitialHaltAdmission>),
    /// One exact checkpoint-bound initial jump-data admission.
    InitialJump(Box<ExecutionGeometryNativeInitialJumpDataAdmission>),
    /// One exact checkpoint-bound input admission.
    Input(Box<ExecutionGeometryNativeInputAdmission>),
    /// One exact checkpoint-bound no-operation admission.
    NoOperation(Box<ExecutionGeometryNativeNoOperationAdmission>),
    /// No-operation followed by halt sequence.
    NoOperationPair(Box<ExecutionGeometryNativeNoopHaltSequence>),
    /// One exact checkpoint-bound output admission.
    Output(Box<ExecutionGeometryNativeOutputAdmission>),
    /// One exact checkpoint-bound rotate admission.
    Rotate(Box<ExecutionGeometryNativeRotateAdmission>),
    /// Rotate followed by halt sequence.
    RotatePair(Box<ExecutionGeometryNativeRotateHaltSequence>),
}

/// One loaded heterogeneous resident retaining its exact specialized owner.
#[derive(Debug)]
pub enum GeometryNativeLoadedResident {
    /// One reusable checkpoint-bound crazy owner.
    Crazy(Box<LoadedExecutionGeometryNativeCrazy>),
    /// Reusable four-mapping crazy-prefix owner.
    CrazyPrefix(Box<LoadedExecutionGeometryNativeCrazyPrefix>),
    /// Complete reusable seven-mapping crazy-theorem owner.
    CrazyTheorem(Box<LoadedCrazyTheoremSequence>),
    /// Complete initial-jump, rotate, halt owner.
    FullPath(Box<LoadedExecutionGeometryNativeJumpRotateHaltSequence>),
    /// One reusable checkpoint-bound initial-halt owner.
    InitialHalt(Box<LoadedExecutionGeometryNativeInitialHalt>),
    /// One reusable checkpoint-bound initial jump-data owner.
    InitialJump(Box<LoadedExecutionGeometryNativeInitialJumpData>),
    /// One reusable checkpoint-bound input owner.
    Input(Box<LoadedExecutionGeometryNativeInput>),
    /// One reusable checkpoint-bound no-operation owner.
    NoOperation(Box<LoadedExecutionGeometryNativeNoOperation>),
    /// No-operation followed by halt owner.
    NoOperationPair(Box<LoadedExecutionGeometryNativeNoopHaltSequence>),
    /// One reusable checkpoint-bound output owner.
    Output(Box<LoadedExecutionGeometryNativeOutput>),
    /// One reusable checkpoint-bound rotate owner.
    Rotate(Box<LoadedExecutionGeometryNativeRotate>),
    /// Rotate followed by halt owner.
    RotatePair(Box<LoadedExecutionGeometryNativeRotateHaltSequence>),
}

/// Successful or safely suspended execution through one typed resident.
#[derive(Debug, Eq, PartialEq)]
pub enum GeometryNativeResidentExecutionOutcome {
    /// One crazy completion.
    Crazy(Box<ExecutionGeometryNativeCrazyCompletion>),
    /// Exact four-crazy prefix outcome.
    CrazyPrefix(Box<ExecutionGeometryNativeCrazyPrefixOutcome>),
    /// Complete crazy-theorem outcome.
    CrazyTheorem(Box<ExecutionGeometryNativeJumpRotateCrazyHaltOutcome>),
    /// Complete initial-jump, rotate, halt outcome.
    FullPath(Box<ExecutionGeometryNativeJumpRotateHaltOutcome>),
    /// One initial-halt completion.
    InitialHalt(Box<ExecutionGeometryNativeInitialHaltCompletion>),
    /// One initial jump-data completion.
    InitialJump(Box<ExecutionGeometryNativeInitialJumpDataCompletion>),
    /// One input completion.
    Input(Box<ExecutionGeometryNativeInputCompletion>),
    /// One no-operation completion.
    NoOperation(Box<ExecutionGeometryNativeNoOperationCompletion>),
    /// No-operation followed by halt outcome.
    NoOperationPair(Box<ExecutionGeometryNativeNoopHaltOutcome>),
    /// One output completion.
    Output(Box<ExecutionGeometryNativeOutputCompletion>),
    /// One rotate completion.
    Rotate(Box<ExecutionGeometryNativeRotateCompletion>),
    /// Rotate followed by halt outcome.
    RotatePair(Box<ExecutionGeometryNativeRotateHaltOutcome>),
}

/// Typed execution failure retaining the specialized resident failure.
#[derive(Debug, Eq, PartialEq)]
pub enum GeometryNativeResidentExecutionFailure<RunnerError> {
    /// Crazy owner execution failed.
    Crazy(Box<ExecutionGeometryNativeCrazyOwnedFailure<RunnerError>>),
    /// Four-crazy prefix owner execution failed.
    CrazyPrefix(
        Box<ExecutionGeometryNativeCrazyPrefixOwnedFailure<RunnerError>>,
    ),
    /// Complete crazy-theorem owner execution failed.
    CrazyTheorem(
        Box<
            ExecutionGeometryNativeJumpRotateCrazyHaltOwnedFailure<RunnerError>,
        >,
    ),
    /// Complete full-path execution failed.
    FullPath(
        Box<ExecutionGeometryNativeJumpRotateHaltOwnedFailure<RunnerError>>,
    ),
    /// Initial-halt owner execution failed.
    InitialHalt(
        Box<ExecutionGeometryNativeInitialHaltOwnedFailure<RunnerError>>,
    ),
    /// Initial jump-data owner execution failed.
    InitialJump(
        Box<ExecutionGeometryNativeInitialJumpDataOwnedFailure<RunnerError>>,
    ),
    /// Input owner execution failed.
    Input(Box<ExecutionGeometryNativeInputOwnedFailure<RunnerError>>),
    /// No-operation owner execution failed.
    NoOperation(
        Box<ExecutionGeometryNativeNoOperationOwnedFailure<RunnerError>>,
    ),
    /// No-operation/halt pair execution failed.
    NoOperationPair(
        Box<ExecutionGeometryNativeNoopHaltLoadedFailure<RunnerError>>,
    ),
    /// Output owner execution failed.
    Output(Box<ExecutionGeometryNativeOutputOwnedFailure<RunnerError>>),
    /// Rotate owner execution failed.
    Rotate(Box<ExecutionGeometryNativeRotateOwnedFailure<RunnerError>>),
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
    /// Crazy executable loading failed.
    Crazy(Box<CrazyLoadFailure<MemoryError>>),
    /// Four-crazy prefix loading failed.
    CrazyPrefix(Box<CrazyPrefixLoadFailure<MemoryError>>),
    /// Complete crazy-theorem loading failed.
    CrazyTheorem(Box<CrazyTheoremLoadFailure<MemoryError>>),
    /// Complete full-path triple loading failed.
    FullPath(Box<FullLoadFailure<MemoryError>>),
    /// Initial-halt executable loading failed.
    InitialHalt(Box<InitialHaltLoadFailure<MemoryError>>),
    /// Initial jump-data executable loading failed.
    InitialJump(Box<InitialJumpLoadFailure<MemoryError>>),
    /// Input executable loading failed.
    Input(Box<InputLoadFailure<MemoryError>>),
    /// No-operation executable loading failed.
    NoOperation(Box<NoOperationLoadFailure<MemoryError>>),
    /// No-operation/halt pair loading failed.
    NoOperationPair(Box<NoopLoadFailure<MemoryError>>),
    /// Output executable loading failed.
    Output(Box<OutputLoadFailure<MemoryError>>),
    /// Rotate executable loading failed.
    Rotate(Box<RotateStepLoadFailure<MemoryError>>),
    /// Rotate/halt pair loading failed.
    RotatePair(Box<RotateLoadFailure<MemoryError>>),
}

/// Failed heterogeneous release retaining variant-specific retry ownership.
#[derive(Debug, Eq, PartialEq)]
pub enum GeometryNativeResidentReleaseFailure<MemoryError> {
    /// Crazy mapping cleanup remains incomplete.
    Crazy(Box<CrazyReleaseFailure<MemoryError>>),
    /// Four-crazy prefix cleanup remains incomplete.
    CrazyPrefix(Box<CrazyPrefixReleaseFailure<MemoryError>>),
    /// Complete crazy-theorem cleanup remains incomplete.
    CrazyTheorem(Box<CrazyTheoremReleaseFailure<MemoryError>>),
    /// Complete full-path cleanup remains incomplete.
    FullPath(Box<FullReleaseFailure<MemoryError>>),
    /// Initial-halt mapping cleanup remains incomplete.
    InitialHalt(Box<InitialHaltReleaseFailure<MemoryError>>),
    /// Initial jump-data mapping cleanup remains incomplete.
    InitialJump(Box<InitialJumpReleaseFailure<MemoryError>>),
    /// Input mapping cleanup remains incomplete.
    Input(Box<InputReleaseFailure<MemoryError>>),
    /// No-operation mapping cleanup remains incomplete.
    NoOperation(Box<NoOperationReleaseFailure<MemoryError>>),
    /// No-operation/halt cleanup remains incomplete.
    NoOperationPair(Box<NoopReleaseFailure<MemoryError>>),
    /// Output mapping cleanup remains incomplete.
    Output(Box<OutputReleaseFailure<MemoryError>>),
    /// Rotate mapping cleanup remains incomplete.
    Rotate(Box<RotateStepReleaseFailure<MemoryError>>),
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
            Self::Crazy(error) => Display::fmt(error, f),
            Self::CrazyPrefix(error) => Display::fmt(error, f),
            Self::CrazyTheorem(error) => Display::fmt(error, f),
            Self::FullPath(error) => Display::fmt(error, f),
            Self::InitialHalt(error) => Display::fmt(error, f),
            Self::InitialJump(error) => Display::fmt(error, f),
            Self::Input(error) => Display::fmt(error, f),
            Self::NoOperation(error) => Display::fmt(error, f),
            Self::NoOperationPair(error) => Display::fmt(error, f),
            Self::Output(error) => Display::fmt(error, f),
            Self::Rotate(error) => Display::fmt(error, f),
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
            Self::CrazyPrefix(error) => error.cleanup_pending(),
            Self::CrazyTheorem(error) => error.cleanup_pending(),
            Self::Crazy(error)
            | Self::InitialHalt(error)
            | Self::InitialJump(error)
            | Self::Input(error)
            | Self::NoOperation(error)
            | Self::Output(error)
            | Self::Rotate(error) => error.cleanup_pending(),
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
            Self::Crazy(error) => {
                Self::Crazy(Box::new((*error).retry_cleanup(adapter)))
            },
            Self::CrazyPrefix(error) => {
                Self::CrazyPrefix(Box::new((*error).retry_cleanup(adapter)))
            },
            Self::CrazyTheorem(error) => {
                Self::CrazyTheorem(Box::new((*error).retry_cleanup(adapter)))
            },
            Self::FullPath(error) => {
                Self::FullPath(Box::new((*error).retry_cleanup(adapter)))
            },
            Self::InitialHalt(error) => {
                Self::InitialHalt(Box::new((*error).retry_cleanup(adapter)))
            },
            Self::InitialJump(error) => {
                Self::InitialJump(Box::new((*error).retry_cleanup(adapter)))
            },
            Self::Input(error) => {
                Self::Input(Box::new((*error).retry_cleanup(adapter)))
            },
            Self::NoOperation(error) => {
                Self::NoOperation(Box::new((*error).retry_cleanup(adapter)))
            },
            Self::NoOperationPair(error) => {
                Self::NoOperationPair(Box::new((*error).retry_cleanup(adapter)))
            },
            Self::Output(error) => {
                Self::Output(Box::new((*error).retry_cleanup(adapter)))
            },
            Self::Rotate(error) => {
                Self::Rotate(Box::new((*error).retry_cleanup(adapter)))
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
            Self::CrazyPrefix(error) => Display::fmt(error, f),
            Self::CrazyTheorem(error) => Display::fmt(error, f),
            Self::Crazy(error)
            | Self::InitialHalt(error)
            | Self::InitialJump(error)
            | Self::Input(error)
            | Self::NoOperation(error)
            | Self::Output(error)
            | Self::Rotate(error) => Display::fmt(error, f),
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
            Self::CrazyPrefix(error) => Display::fmt(error, f),
            Self::CrazyTheorem(error) => Display::fmt(error, f),
            Self::Crazy(error)
            | Self::InitialHalt(error)
            | Self::InitialJump(error)
            | Self::Input(error)
            | Self::NoOperation(error)
            | Self::Output(error)
            | Self::Rotate(error) => Display::fmt(error, f),
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
            Self::Crazy(loaded) => Self::execute_crazy(loaded, runner, buffers),
            Self::CrazyPrefix(loaded) => {
                Self::execute_crazy_prefix(loaded, runner, buffers)
            },
            Self::CrazyTheorem(loaded) => {
                Self::execute_crazy_theorem(loaded, runner, buffers)
            },
            Self::FullPath(loaded) => {
                Self::execute_full_path(loaded, runner, buffers)
            },
            Self::InitialHalt(loaded) => {
                Self::execute_initial_halt(loaded, runner, buffers)
            },
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
            Self::Input(loaded) => Self::execute_input(loaded, runner, buffers),
            Self::NoOperation(loaded) => {
                Self::execute_no_operation(loaded, runner, buffers)
            },
            Self::NoOperationPair(loaded) => {
                Self::execute_no_operation_pair(loaded, runner, buffers)
            },
            Self::Output(loaded) => {
                Self::execute_output(loaded, runner, buffers)
            },
            Self::Rotate(loaded) => {
                Self::execute_rotate(loaded, runner, buffers)
            },
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

    fn execute_crazy<Runner>(
        loaded: &LoadedExecutionGeometryNativeCrazy,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> GeometryNativeResidentExecutionResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        loaded
            .execute(runner, buffers)
            .map(|outcome| {
                GeometryNativeResidentExecutionOutcome::Crazy(Box::new(outcome))
            })
            .map_err(|error| {
                Box::new(GeometryNativeResidentExecutionFailure::Crazy(error))
            })
    }

    fn execute_crazy_prefix<Runner>(
        loaded: &LoadedExecutionGeometryNativeCrazyPrefix,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> GeometryNativeResidentExecutionResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        loaded
            .execute(runner, buffers)
            .map(|outcome| {
                GeometryNativeResidentExecutionOutcome::CrazyPrefix(Box::new(
                    outcome,
                ))
            })
            .map_err(|error| {
                Box::new(GeometryNativeResidentExecutionFailure::CrazyPrefix(
                    error,
                ))
            })
    }

    fn execute_crazy_theorem<Runner>(
        loaded: &LoadedCrazyTheoremSequence,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> GeometryNativeResidentExecutionResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        loaded
            .execute(runner, buffers)
            .map(|outcome| {
                GeometryNativeResidentExecutionOutcome::CrazyTheorem(Box::new(
                    outcome,
                ))
            })
            .map_err(|error| {
                Box::new(GeometryNativeResidentExecutionFailure::CrazyTheorem(
                    error,
                ))
            })
    }

    fn execute_full_path<Runner>(
        loaded: &LoadedExecutionGeometryNativeJumpRotateHaltSequence,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> GeometryNativeResidentExecutionResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        loaded
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
            })
    }

    fn execute_initial_halt<Runner>(
        loaded: &LoadedExecutionGeometryNativeInitialHalt,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> GeometryNativeResidentExecutionResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        loaded
            .execute(runner, buffers)
            .map(|outcome| {
                GeometryNativeResidentExecutionOutcome::InitialHalt(Box::new(
                    outcome,
                ))
            })
            .map_err(|error| {
                Box::new(GeometryNativeResidentExecutionFailure::InitialHalt(
                    error,
                ))
            })
    }

    fn execute_input<Runner>(
        loaded: &LoadedExecutionGeometryNativeInput,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> GeometryNativeResidentExecutionResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        loaded
            .execute(runner, buffers)
            .map(|outcome| {
                GeometryNativeResidentExecutionOutcome::Input(Box::new(outcome))
            })
            .map_err(|error| {
                Box::new(GeometryNativeResidentExecutionFailure::Input(error))
            })
    }

    fn execute_no_operation<Runner>(
        loaded: &LoadedExecutionGeometryNativeNoOperation,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> GeometryNativeResidentExecutionResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        loaded
            .execute(runner, buffers)
            .map(|outcome| {
                GeometryNativeResidentExecutionOutcome::NoOperation(Box::new(
                    outcome,
                ))
            })
            .map_err(|error| {
                Box::new(GeometryNativeResidentExecutionFailure::NoOperation(
                    error,
                ))
            })
    }

    fn execute_no_operation_pair<Runner>(
        loaded: &LoadedExecutionGeometryNativeNoopHaltSequence,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> GeometryNativeResidentExecutionResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        loaded
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
            })
    }

    fn execute_output<Runner>(
        loaded: &LoadedExecutionGeometryNativeOutput,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> GeometryNativeResidentExecutionResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        loaded
            .execute(runner, buffers)
            .map(|outcome| {
                GeometryNativeResidentExecutionOutcome::Output(Box::new(
                    outcome,
                ))
            })
            .map_err(|error| {
                Box::new(GeometryNativeResidentExecutionFailure::Output(error))
            })
    }

    fn execute_rotate<Runner>(
        loaded: &LoadedExecutionGeometryNativeRotate,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> GeometryNativeResidentExecutionResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        loaded
            .execute(runner, buffers)
            .map(|outcome| {
                GeometryNativeResidentExecutionOutcome::Rotate(Box::new(
                    outcome,
                ))
            })
            .map_err(|error| {
                Box::new(GeometryNativeResidentExecutionFailure::Rotate(error))
            })
    }

    /// Returns the exact reviewed template retained by this loaded owner.
    #[must_use]
    pub const fn kind(&self) -> GeometryNativeResidentKind {
        match self {
            Self::Crazy(_loaded) => GeometryNativeResidentKind::Crazy,
            Self::CrazyPrefix(_loaded) => {
                GeometryNativeResidentKind::CrazyPrefix
            },
            Self::CrazyTheorem(_loaded) => {
                GeometryNativeResidentKind::CrazyTheorem
            },
            Self::FullPath(_loaded) => GeometryNativeResidentKind::FullPath,
            Self::InitialHalt(_loaded) => {
                GeometryNativeResidentKind::InitialHalt
            },
            Self::InitialJump(_loaded) => {
                GeometryNativeResidentKind::InitialJump
            },
            Self::Input(_loaded) => GeometryNativeResidentKind::Input,
            Self::NoOperation(_loaded) => {
                GeometryNativeResidentKind::NoOperation
            },
            Self::NoOperationPair(_loaded) => {
                GeometryNativeResidentKind::NoOperationPair
            },
            Self::Output(_loaded) => GeometryNativeResidentKind::Output,
            Self::Rotate(_loaded) => GeometryNativeResidentKind::Rotate,
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
                Self::Crazy(loaded),
                GeometryNativeResidentPlan::Crazy(exact_plan),
            ) => loaded.admission() == exact_plan.as_ref(),
            (
                Self::CrazyPrefix(loaded),
                GeometryNativeResidentPlan::CrazyPrefix(exact_plan),
            ) => loaded.prefix() == exact_plan.as_ref(),
            (
                Self::CrazyTheorem(loaded),
                GeometryNativeResidentPlan::CrazyTheorem(exact_plan),
            ) => loaded.sequence() == exact_plan.as_ref(),
            (
                Self::FullPath(loaded),
                GeometryNativeResidentPlan::FullPath(exact_plan),
            ) => loaded.sequence() == exact_plan.as_ref(),
            (
                Self::InitialHalt(loaded),
                GeometryNativeResidentPlan::InitialHalt(exact_plan),
            ) => loaded.admission() == exact_plan.as_ref(),
            (
                Self::InitialJump(loaded),
                GeometryNativeResidentPlan::InitialJump(exact_plan),
            ) => loaded.admission() == exact_plan.as_ref(),
            (
                Self::Input(loaded),
                GeometryNativeResidentPlan::Input(exact_plan),
            ) => loaded.admission() == exact_plan.as_ref(),
            (
                Self::NoOperation(loaded),
                GeometryNativeResidentPlan::NoOperation(exact_plan),
            ) => loaded.admission() == exact_plan.as_ref(),
            (
                Self::NoOperationPair(loaded),
                GeometryNativeResidentPlan::NoOperationPair(exact_plan),
            ) => loaded.sequence() == exact_plan.as_ref(),
            (
                Self::Output(loaded),
                GeometryNativeResidentPlan::Output(exact_plan),
            ) => loaded.admission() == exact_plan.as_ref(),
            (
                Self::Rotate(loaded),
                GeometryNativeResidentPlan::Rotate(exact_plan),
            ) => loaded.admission() == exact_plan.as_ref(),
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
            Self::Crazy(loaded) => GeometryNativeResidentPlan::Crazy(Box::new(
                loaded.admission().clone(),
            )),
            Self::CrazyPrefix(loaded) => {
                GeometryNativeResidentPlan::CrazyPrefix(Box::new(
                    loaded.prefix().clone(),
                ))
            },
            Self::CrazyTheorem(loaded) => {
                GeometryNativeResidentPlan::CrazyTheorem(Box::new(
                    loaded.sequence().clone(),
                ))
            },
            Self::FullPath(loaded) => GeometryNativeResidentPlan::FullPath(
                Box::new(loaded.sequence().clone()),
            ),
            Self::InitialHalt(loaded) => {
                GeometryNativeResidentPlan::InitialHalt(Box::new(
                    loaded.admission().clone(),
                ))
            },
            Self::InitialJump(loaded) => {
                GeometryNativeResidentPlan::InitialJump(Box::new(
                    loaded.admission().clone(),
                ))
            },
            Self::Input(loaded) => GeometryNativeResidentPlan::Input(Box::new(
                loaded.admission().clone(),
            )),
            Self::NoOperation(loaded) => {
                GeometryNativeResidentPlan::NoOperation(Box::new(
                    loaded.admission().clone(),
                ))
            },
            Self::NoOperationPair(loaded) => {
                GeometryNativeResidentPlan::NoOperationPair(Box::new(
                    loaded.sequence().clone(),
                ))
            },
            Self::Output(loaded) => GeometryNativeResidentPlan::Output(
                Box::new(loaded.admission().clone()),
            ),
            Self::Rotate(loaded) => GeometryNativeResidentPlan::Rotate(
                Box::new(loaded.admission().clone()),
            ),
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
            Self::Crazy(loaded) => loaded.release(adapter).map_err(|error| {
                Box::new(GeometryNativeResidentReleaseFailure::Crazy(error))
            }),
            Self::CrazyPrefix(loaded) => {
                Self::release_crazy_prefix(loaded, adapter)
            },
            Self::CrazyTheorem(loaded) => {
                Self::release_crazy_theorem(loaded, adapter)
            },
            Self::FullPath(loaded) => Self::release_full_path(loaded, adapter),
            Self::InitialHalt(loaded) => {
                loaded.release(adapter).map_err(|error| {
                    Box::new(GeometryNativeResidentReleaseFailure::InitialHalt(
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
            Self::Input(loaded) => loaded.release(adapter).map_err(|error| {
                Box::new(GeometryNativeResidentReleaseFailure::Input(error))
            }),
            Self::NoOperation(loaded) => {
                loaded.release(adapter).map_err(|error| {
                    Box::new(GeometryNativeResidentReleaseFailure::NoOperation(
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
            Self::Output(loaded) => loaded.release(adapter).map_err(|error| {
                Box::new(GeometryNativeResidentReleaseFailure::Output(error))
            }),
            Self::Rotate(loaded) => loaded.release(adapter).map_err(|error| {
                Box::new(GeometryNativeResidentReleaseFailure::Rotate(error))
            }),
            Self::RotatePair(loaded) => {
                loaded.release(adapter).map_err(|error| {
                    Box::new(GeometryNativeResidentReleaseFailure::RotatePair(
                        error,
                    ))
                })
            },
        }
    }

    fn release_crazy_prefix<Adapter>(
        loaded: Box<LoadedExecutionGeometryNativeCrazyPrefix>,
        adapter: &mut Adapter,
    ) -> GeometryNativeResidentReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        loaded.release(adapter).map_err(|error| {
            Box::new(GeometryNativeResidentReleaseFailure::CrazyPrefix(error))
        })
    }

    fn release_crazy_theorem<Adapter>(
        loaded: Box<LoadedCrazyTheoremSequence>,
        adapter: &mut Adapter,
    ) -> GeometryNativeResidentReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        loaded.release(adapter).map_err(|error| {
            Box::new(GeometryNativeResidentReleaseFailure::CrazyTheorem(error))
        })
    }

    fn release_full_path<Adapter>(
        loaded: Box<LoadedExecutionGeometryNativeJumpRotateHaltSequence>,
        adapter: &mut Adapter,
    ) -> GeometryNativeResidentReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        loaded.release(adapter).map_err(|error| {
            Box::new(GeometryNativeResidentReleaseFailure::FullPath(error))
        })
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
            Self::Crazy(loaded) => {
                let weight = loaded.resident_weight();
                (weight.mapped_bytes(), weight.mappings())
            },
            Self::CrazyPrefix(loaded) => {
                let weight = loaded
                    .resident_weight()
                    .map_err(map_crazy_prefix_weight_error)?;
                (weight.mapped_bytes(), weight.mappings())
            },
            Self::CrazyTheorem(loaded) => {
                let weight = loaded
                    .resident_weight()
                    .map_err(map_crazy_theorem_weight_error)?;
                (weight.mapped_bytes(), weight.mappings())
            },
            Self::FullPath(loaded) => {
                let weight =
                    loaded.resident_weight().map_err(map_full_weight_error)?;
                (weight.mapped_bytes(), weight.mappings())
            },
            Self::InitialHalt(loaded) => {
                let weight = loaded.resident_weight();
                (weight.mapped_bytes(), weight.mappings())
            },
            Self::InitialJump(loaded) => {
                let weight = loaded.resident_weight();
                (weight.mapped_bytes(), weight.mappings())
            },
            Self::Input(loaded) => {
                let weight = loaded.resident_weight();
                (weight.mapped_bytes(), weight.mappings())
            },
            Self::NoOperation(loaded) => {
                let weight = loaded.resident_weight();
                (weight.mapped_bytes(), weight.mappings())
            },
            Self::NoOperationPair(loaded) => {
                let weight =
                    loaded.resident_weight().map_err(map_noop_weight_error)?;
                (weight.mapped_bytes(), weight.mappings())
            },
            Self::Output(loaded) => {
                let weight = loaded.resident_weight();
                (weight.mapped_bytes(), weight.mappings())
            },
            Self::Rotate(loaded) => {
                let weight = loaded.resident_weight();
                (weight.mapped_bytes(), weight.mappings())
            },
            Self::RotatePair(loaded) => {
                let weight = loaded
                    .resident_weight()
                    .map_err(map_rotate_weight_error)?;
                (weight.mapped_bytes(), weight.mappings())
            },
        };
        Ok(GeometryNativeResidentWeight { mapped_bytes, mappings })
    }
}

impl GeometryNativeResidentExecutionOutcome {
    /// Returns the reviewed template that produced this execution outcome.
    #[must_use]
    pub const fn kind(&self) -> GeometryNativeResidentKind {
        match self {
            Self::Crazy(_outcome) => GeometryNativeResidentKind::Crazy,
            Self::CrazyPrefix(_outcome) => {
                GeometryNativeResidentKind::CrazyPrefix
            },
            Self::CrazyTheorem(_outcome) => {
                GeometryNativeResidentKind::CrazyTheorem
            },
            Self::FullPath(_outcome) => GeometryNativeResidentKind::FullPath,
            Self::InitialHalt(_outcome) => {
                GeometryNativeResidentKind::InitialHalt
            },
            Self::InitialJump(_outcome) => {
                GeometryNativeResidentKind::InitialJump
            },
            Self::Input(_outcome) => GeometryNativeResidentKind::Input,
            Self::NoOperation(_outcome) => {
                GeometryNativeResidentKind::NoOperation
            },
            Self::NoOperationPair(_outcome) => {
                GeometryNativeResidentKind::NoOperationPair
            },
            Self::Output(_outcome) => GeometryNativeResidentKind::Output,
            Self::Rotate(_outcome) => GeometryNativeResidentKind::Rotate,
            Self::RotatePair(_outcome) => {
                GeometryNativeResidentKind::RotatePair
            },
        }
    }

    /// Returns the completed or last committed opaque-geometry checkpoint.
    #[must_use]
    pub fn state(&self) -> &ProfileMachineState {
        match self {
            Self::Crazy(outcome) => outcome.state(),
            Self::CrazyPrefix(outcome) => outcome.state(),
            Self::CrazyTheorem(outcome) => outcome.state(),
            Self::FullPath(outcome) => outcome.state(),
            Self::InitialHalt(outcome) => outcome.state(),
            Self::InitialJump(outcome) => outcome.state(),
            Self::Input(outcome) => outcome.state(),
            Self::NoOperation(outcome) => outcome.state(),
            Self::NoOperationPair(outcome) => outcome.state(),
            Self::Output(outcome) => outcome.state(),
            Self::Rotate(outcome) => outcome.state(),
            Self::RotatePair(outcome) => outcome.state(),
        }
    }
}

impl GeometryNativeResidentPlan {
    /// Returns the reviewed template represented by this exact plan.
    #[must_use]
    pub const fn kind(&self) -> GeometryNativeResidentKind {
        match self {
            Self::Crazy(_plan) => GeometryNativeResidentKind::Crazy,
            Self::CrazyPrefix(_plan) => GeometryNativeResidentKind::CrazyPrefix,
            Self::CrazyTheorem(_plan) => {
                GeometryNativeResidentKind::CrazyTheorem
            },
            Self::FullPath(_plan) => GeometryNativeResidentKind::FullPath,
            Self::InitialHalt(_plan) => GeometryNativeResidentKind::InitialHalt,
            Self::InitialJump(_plan) => GeometryNativeResidentKind::InitialJump,
            Self::Input(_plan) => GeometryNativeResidentKind::Input,
            Self::NoOperation(_plan) => GeometryNativeResidentKind::NoOperation,
            Self::NoOperationPair(_plan) => {
                GeometryNativeResidentKind::NoOperationPair
            },
            Self::Output(_plan) => GeometryNativeResidentKind::Output,
            Self::Rotate(_plan) => GeometryNativeResidentKind::Rotate,
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
            Self::Crazy(plan) => Self::load_crazy(plan, adapter),
            Self::CrazyPrefix(plan) => Self::load_crazy_prefix(plan, adapter),
            Self::CrazyTheorem(plan) => Self::load_crazy_theorem(plan, adapter),
            Self::FullPath(plan) => Self::load_full_path(plan, adapter),
            Self::InitialHalt(plan) => plan
                .load_owned(adapter)
                .map(|loaded| {
                    GeometryNativeLoadedResident::InitialHalt(Box::new(loaded))
                })
                .map_err(|error| {
                    Box::new(GeometryNativeResidentLoadFailure::InitialHalt(
                        error,
                    ))
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
            Self::Input(plan) => Self::load_input(plan, adapter),
            Self::NoOperation(plan) => Self::load_no_operation(plan, adapter),
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
            Self::Output(plan) => Self::load_output(plan, adapter),
            Self::Rotate(plan) => Self::load_rotate(plan, adapter),
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

    fn load_crazy<Adapter>(
        plan: &ExecutionGeometryNativeCrazyAdmission,
        adapter: &mut Adapter,
    ) -> GeometryNativeResidentLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        plan.load_owned(adapter)
            .map(|loaded| GeometryNativeLoadedResident::Crazy(Box::new(loaded)))
            .map_err(|error| {
                Box::new(GeometryNativeResidentLoadFailure::Crazy(error))
            })
    }

    fn load_crazy_prefix<Adapter>(
        plan: &ExecutionGeometryNativeCrazyPrefix,
        adapter: &mut Adapter,
    ) -> GeometryNativeResidentLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        LoadedExecutionGeometryNativeCrazyPrefix::load(plan, adapter)
            .map(|loaded| {
                GeometryNativeLoadedResident::CrazyPrefix(Box::new(loaded))
            })
            .map_err(|error| {
                Box::new(GeometryNativeResidentLoadFailure::CrazyPrefix(error))
            })
    }

    fn load_crazy_theorem<Adapter>(
        plan: &ExecutionGeometryNativeJumpRotateCrazyHaltSequence,
        adapter: &mut Adapter,
    ) -> GeometryNativeResidentLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        LoadedCrazyTheoremSequence::load(plan, adapter)
            .map(|loaded| {
                GeometryNativeLoadedResident::CrazyTheorem(Box::new(loaded))
            })
            .map_err(|error| {
                Box::new(GeometryNativeResidentLoadFailure::CrazyTheorem(error))
            })
    }

    fn load_full_path<Adapter>(
        plan: &ExecutionGeometryNativeJumpRotateHaltSequence,
        adapter: &mut Adapter,
    ) -> GeometryNativeResidentLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        plan.load_triple(adapter)
            .map(|loaded| {
                GeometryNativeLoadedResident::FullPath(Box::new(loaded))
            })
            .map_err(|error| {
                Box::new(GeometryNativeResidentLoadFailure::FullPath(error))
            })
    }

    fn load_input<Adapter>(
        plan: &ExecutionGeometryNativeInputAdmission,
        adapter: &mut Adapter,
    ) -> GeometryNativeResidentLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        plan.load_owned(adapter)
            .map(|loaded| GeometryNativeLoadedResident::Input(Box::new(loaded)))
            .map_err(|error| {
                Box::new(GeometryNativeResidentLoadFailure::Input(error))
            })
    }

    fn load_no_operation<Adapter>(
        plan: &ExecutionGeometryNativeNoOperationAdmission,
        adapter: &mut Adapter,
    ) -> GeometryNativeResidentLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        plan.load_owned(adapter)
            .map(|loaded| {
                GeometryNativeLoadedResident::NoOperation(Box::new(loaded))
            })
            .map_err(|error| {
                Box::new(GeometryNativeResidentLoadFailure::NoOperation(error))
            })
    }

    fn load_output<Adapter>(
        plan: &ExecutionGeometryNativeOutputAdmission,
        adapter: &mut Adapter,
    ) -> GeometryNativeResidentLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        plan.load_owned(adapter)
            .map(|loaded| {
                GeometryNativeLoadedResident::Output(Box::new(loaded))
            })
            .map_err(|error| {
                Box::new(GeometryNativeResidentLoadFailure::Output(error))
            })
    }

    fn load_rotate<Adapter>(
        plan: &ExecutionGeometryNativeRotateAdmission,
        adapter: &mut Adapter,
    ) -> GeometryNativeResidentLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        plan.load_owned(adapter)
            .map(|loaded| {
                GeometryNativeLoadedResident::Rotate(Box::new(loaded))
            })
            .map_err(|error| {
                Box::new(GeometryNativeResidentLoadFailure::Rotate(error))
            })
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
            Self::Crazy(error) => {
                (*error).retry(adapter).map_err(|retry_error| {
                    Box::new(Self::Crazy(Box::new(retry_error)))
                })
            },
            Self::CrazyPrefix(error) => {
                (*error).retry(adapter).map_err(|retry_error| {
                    Box::new(Self::CrazyPrefix(retry_error))
                })
            },
            Self::CrazyTheorem(error) => {
                (*error).retry(adapter).map_err(|retry_error| {
                    Box::new(Self::CrazyTheorem(retry_error))
                })
            },
            Self::FullPath(error) => (*error)
                .retry(adapter)
                .map_err(|retry_error| Box::new(Self::FullPath(retry_error))),
            Self::InitialHalt(error) => {
                (*error).retry(adapter).map_err(|retry_error| {
                    Box::new(Self::InitialHalt(Box::new(retry_error)))
                })
            },
            Self::InitialJump(error) => {
                (*error).retry(adapter).map_err(|retry_error| {
                    Box::new(Self::InitialJump(Box::new(retry_error)))
                })
            },
            Self::Input(error) => {
                (*error).retry(adapter).map_err(|retry_error| {
                    Box::new(Self::Input(Box::new(retry_error)))
                })
            },
            Self::NoOperation(error) => {
                (*error).retry(adapter).map_err(|retry_error| {
                    Box::new(Self::NoOperation(Box::new(retry_error)))
                })
            },
            Self::NoOperationPair(error) => {
                (*error).retry(adapter).map_err(|retry_error| {
                    Box::new(Self::NoOperationPair(retry_error))
                })
            },
            Self::Output(error) => {
                (*error).retry(adapter).map_err(|retry_error| {
                    Box::new(Self::Output(Box::new(retry_error)))
                })
            },
            Self::Rotate(error) => {
                (*error).retry(adapter).map_err(|retry_error| {
                    Box::new(Self::Rotate(Box::new(retry_error)))
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

const fn map_crazy_prefix_weight_error(
    error: CrazyPrefixWeightError,
) -> GeometryNativeResidentWeightError {
    match error {
        CrazyPrefixWeightError::MappedBytesOverflow => {
            GeometryNativeResidentWeightError::MappedBytesOverflow
        },
        CrazyPrefixWeightError::MappingsOverflow => {
            GeometryNativeResidentWeightError::MappingsOverflow
        },
    }
}

const fn map_crazy_theorem_weight_error(
    error: CrazyTheoremWeightError,
) -> GeometryNativeResidentWeightError {
    match error {
        CrazyTheoremWeightError::MappedBytesOverflow => {
            GeometryNativeResidentWeightError::MappedBytesOverflow
        },
        CrazyTheoremWeightError::MappingsOverflow => {
            GeometryNativeResidentWeightError::MappingsOverflow
        },
    }
}

const fn map_full_weight_error(
    error: FullWeightError,
) -> GeometryNativeResidentWeightError {
    match error {
        FullWeightError::MappedBytesOverflow => {
            GeometryNativeResidentWeightError::MappedBytesOverflow
        },
        FullWeightError::MappingsOverflow => {
            GeometryNativeResidentWeightError::MappingsOverflow
        },
    }
}

const fn map_noop_weight_error(
    error: NoopWeightError,
) -> GeometryNativeResidentWeightError {
    match error {
        NoopWeightError::MappedBytesOverflow => {
            GeometryNativeResidentWeightError::MappedBytesOverflow
        },
        NoopWeightError::MappingsOverflow => {
            GeometryNativeResidentWeightError::MappingsOverflow
        },
    }
}

const fn map_rotate_weight_error(
    error: RotateWeightError,
) -> GeometryNativeResidentWeightError {
    match error {
        RotateWeightError::MappedBytesOverflow => {
            GeometryNativeResidentWeightError::MappedBytesOverflow
        },
        RotateWeightError::MappingsOverflow => {
            GeometryNativeResidentWeightError::MappingsOverflow
        },
    }
}
