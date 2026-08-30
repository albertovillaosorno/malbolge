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
//   - Ordered native composition of one v5 rotate followed by halt.
// - Must-Not:
//   - Skip per-step checkpoint admission, hide partial progress, or weaken
//   - executable cleanup ownership.
// - Allows:
//   - Inputs: exact verified v5 step artifacts, checkpoint, adapter, and
//     runner.
//   - Outputs: final checkpoint, guard-miss suspension, or indexed failure.
//   - Side effects: supplied executable-memory and runner operations only.
// - Split-When:
//   - General v5 native sequence planning supports additional step kinds.
// - Merge-When:
//   - A generic geometry-native continuation preserves this exact evidence.
// - Summary:
//   - Composes the explicit-geometry rotate/halt native suffix.
// - Description:
//   - Preserves the last committed opaque checkpoint across step boundaries.
// - Usage:
//   - Construct from exact rotate/halt evidence, then execute transactionally.
// - Defaults:
//   - Guard miss stops before the suffix; failure reports last committed state.
//

//! Two-step explicit-geometry native rotate/halt suffix composition.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{ExecutionGeometryRegionEffectProgram, ProfileMachineState};

use crate::execution_native::{
    ExecutionGeometryNativeExecutableReleaseFailure,
    ExecutionGeometryNativeRunner, NativeExecutableLoadFailure,
    NativeExecutableMemoryAdapter, NativeRegionBuffers,
    NativeRegionInvocationOutcome, ReadyExecutionGeometryNativeExecutable,
    VerifiedExecutionGeometryInitialHaltNativeObjectArtifact,
    VerifiedExecutionGeometryRotateNativeObjectArtifact,
    load_execution_geometry_native_executable,
    release_execution_geometry_native_executable,
};
use crate::geometry_native_admission::{
    ExecutionGeometryNativeInitialHaltAdmission,
    ExecutionGeometryNativeInitialHaltAdmissionError,
    ExecutionGeometryNativeInitialHaltBindingError,
    ExecutionGeometryNativeInitialHaltCompletion,
    ExecutionGeometryNativeInitialHaltExecutionError,
    ExecutionGeometryNativeInitialHaltPreparationError,
    ExecutionGeometryNativeInitialHaltTransactionFailure,
};
use crate::geometry_native_rotate::{
    ExecutionGeometryNativeRotateAdmission,
    ExecutionGeometryNativeRotateAdmissionError,
    ExecutionGeometryNativeRotateBindingError,
    ExecutionGeometryNativeRotateCompletion,
    ExecutionGeometryNativeRotateExecutionError,
    ExecutionGeometryNativeRotatePreparationError,
    ExecutionGeometryNativeRotateTransactionFailure,
};

type VerifiedRotateArtifact =
    VerifiedExecutionGeometryRotateNativeObjectArtifact;
type RotateHaltBindingError =
    ExecutionGeometryNativeRotateHaltExecutableBindingError;
type RotateHaltFailureCause<MemoryError, RunnerError> =
    ExecutionGeometryNativeRotateHaltFailureCause<MemoryError, RunnerError>;
type RotateCompletion = ExecutionGeometryNativeRotateCompletion;

type LoadedStepResult<Completion, RunnerError> = Result<
    Completion,
    Box<ExecutionGeometryNativeRotateHaltLoadedFailure<RunnerError>>,
>;

/// Failure while admitting the exact two-step v5 native sequence.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeRotateHaltAdmissionError {
    /// Final halt could not bind to the normatively replayed rotate checkpoint.
    Halt(ExecutionGeometryNativeInitialHaltAdmissionError),
    /// First rotate could not bind to the entry checkpoint.
    Rotate(ExecutionGeometryNativeRotateAdmissionError),
}

/// Failure while prebinding both synchronized executables to the sequence.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeRotateHaltExecutableBindingError {
    /// Ready halt image differs from the admitted halt image.
    Halt,
    /// Ready rotate image differs from the admitted rotate image.
    Rotate,
}

/// Failure cause while executing a prebound two-step native sequence.
#[derive(Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeRotateHaltLoadedFailureCause<RunnerError> {
    /// Final halt executable unexpectedly failed exact binding.
    HaltBinding(ExecutionGeometryNativeInitialHaltBindingError),
    /// Final halt runner/completion failed.
    HaltExecution(
        Box<ExecutionGeometryNativeInitialHaltExecutionError<RunnerError>>,
    ),
    /// Final halt buffer preparation failed.
    HaltPreparation(ExecutionGeometryNativeInitialHaltPreparationError),
    /// First rotate executable unexpectedly failed exact binding.
    RotateBinding(ExecutionGeometryNativeRotateBindingError),
    /// First rotate runner/completion failed.
    RotateExecution(
        Box<ExecutionGeometryNativeRotateExecutionError<RunnerError>>,
    ),
    /// First rotate buffer preparation failed.
    RotatePreparation(ExecutionGeometryNativeRotatePreparationError),
}

/// Indexed failure from a prebound sequence retaining last committed state.
#[derive(Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeRotateHaltLoadedFailure<RunnerError> {
    cause: ExecutionGeometryNativeRotateHaltLoadedFailureCause<RunnerError>,
    index: usize,
    state: ProfileMachineState,
}

/// Failure while loading the exact reusable v5 rotate/halt pair.
#[derive(Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeRotateHaltPairLoadFailure<MemoryError> {
    /// Halt loading failed after the rotate was ready.
    Halt {
        /// Primary halt load failure.
        error: Box<NativeExecutableLoadFailure<MemoryError>>,
        /// Failed rollback retaining the ready rotate for retry.
        rotate_release_failure: Option<
            Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
        >,
    },
    /// Rotate loading failed before any ready executable existed.
    Rotate(Box<NativeExecutableLoadFailure<MemoryError>>),
}

/// Failed pair release retaining every mapping that still needs cleanup.
#[derive(Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeRotateHaltPairReleaseFailure<MemoryError> {
    halt_failure: Option<
        Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
    >,
    rotate_failure: Option<
        Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
    >,
}

/// Primary failure from one indexed step of the two-step native sequence.
#[derive(Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeRotateHaltFailureCause<MemoryError, RunnerError>
{
    /// Final halt transaction failed.
    Halt(
        Box<
            ExecutionGeometryNativeInitialHaltTransactionFailure<
                MemoryError,
                RunnerError,
            >,
        >,
    ),
    /// First rotate transaction failed.
    Rotate(
        Box<
            ExecutionGeometryNativeRotateTransactionFailure<
                MemoryError,
                RunnerError,
            >,
        >,
    ),
}

/// Indexed two-step native failure retaining the last committed checkpoint.
#[derive(Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeRotateHaltFailure<MemoryError, RunnerError> {
    cause:
        ExecutionGeometryNativeRotateHaltFailureCause<MemoryError, RunnerError>,
    index: usize,
    state: ProfileMachineState,
}

/// Successful or safely suspended two-step v5 native execution.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeRotateHaltOutcome {
    /// Both rotate and halt applied exactly.
    Completed(ProfileMachineState),
    /// A semantic native guard missed before the indexed step could commit.
    GuardMiss {
        /// Zero-based step whose guard missed.
        index: usize,
        /// Last fully committed opaque-geometry checkpoint.
        state: ProfileMachineState,
    },
}

/// Exact verified programs/artifacts required by the two-step sequence.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeRotateHaltEvidence {
    halt_artifact: VerifiedExecutionGeometryInitialHaltNativeObjectArtifact,
    halt_program: ExecutionGeometryRegionEffectProgram,
    rotate_artifact: VerifiedRotateArtifact,
    rotate_program: ExecutionGeometryRegionEffectProgram,
}

/// Two independently admitted v5 native steps sharing one opaque geometry line.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeRotateHaltSequence {
    halt: ExecutionGeometryNativeInitialHaltAdmission,
    rotate: ExecutionGeometryNativeRotateAdmission,
}

/// Two exact synchronized executables prebound before caller-state mutation.
#[derive(Debug)]
pub struct BoundExecutionGeometryNativeRotateHaltSequence<
    'sequence,
    'executable,
> {
    halt: &'executable ReadyExecutionGeometryNativeExecutable,
    rotate: &'executable ReadyExecutionGeometryNativeExecutable,
    sequence: &'sequence ExecutionGeometryNativeRotateHaltSequence,
}

/// Owned ready rotate/halt pair bound to one admitted sequence.
#[derive(Debug)]
pub struct LoadedExecutionGeometryNativeRotateHaltSequence {
    halt: ReadyExecutionGeometryNativeExecutable,
    rotate: ReadyExecutionGeometryNativeExecutable,
    sequence: ExecutionGeometryNativeRotateHaltSequence,
}

/// Result of executing one prebound geometry-native pair.
pub type ExecutionGeometryNativeRotateHaltLoadedResult<RunnerError> = Result<
    ExecutionGeometryNativeRotateHaltOutcome,
    Box<ExecutionGeometryNativeRotateHaltLoadedFailure<RunnerError>>,
>;

/// Result of loading both exact ready executables as one owned pair.
pub type GeometryNativeRotateHaltPairLoadResult<MemoryError> = Result<
    LoadedExecutionGeometryNativeRotateHaltSequence,
    Box<ExecutionGeometryNativeRotateHaltPairLoadFailure<MemoryError>>,
>;

/// Result of releasing every mapping owned by one loaded pair.
pub type GeometryNativeRotateHaltPairReleaseResult<MemoryError> = Result<
    (),
    Box<ExecutionGeometryNativeRotateHaltPairReleaseFailure<MemoryError>>,
>;

/// Result of one concrete adapter/runner two-step transaction.
pub type ExecutionGeometryNativeRotateHaltAdapterResult<MemoryAdapter, Runner> =
    Result<
        ExecutionGeometryNativeRotateHaltOutcome,
        Box<
            ExecutionGeometryNativeRotateHaltFailure<
                <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
                <Runner as ExecutionGeometryNativeRunner>::Error,
            >,
        >,
    >;

impl Display for ExecutionGeometryNativeRotateHaltAdmissionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Halt(error) => {
                write!(f, "v5 sequence halt admission: {error}")
            },
            Self::Rotate(error) => {
                write!(f, "v5 sequence rotate admission: {error}")
            },
        }
    }
}

impl Display for ExecutionGeometryNativeRotateHaltExecutableBindingError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Halt => "v5 sequence halt executable identity differs",
            Self::Rotate => "v5 sequence rotate executable identity differs",
        })
    }
}

impl<RunnerError: Display> Display
    for ExecutionGeometryNativeRotateHaltLoadedFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        use ExecutionGeometryNativeRotateHaltLoadedFailureCause as Cause;

        write!(f, "v5 loaded sequence step {} failed: ", self.index)?;
        match &self.cause {
            Cause::HaltBinding(error) => Display::fmt(error, f),
            Cause::HaltExecution(error) => Display::fmt(error, f),
            Cause::HaltPreparation(error) => Display::fmt(error, f),
            Cause::RotateBinding(error) => Display::fmt(error, f),
            Cause::RotateExecution(error) => Display::fmt(error, f),
            Cause::RotatePreparation(error) => Display::fmt(error, f),
        }
    }
}

impl<MemoryError: Display> Display
    for ExecutionGeometryNativeRotateHaltPairLoadFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Halt { error, .. } => {
                write!(f, "v5 pair halt load failed: {error}")
            },
            Self::Rotate(error) => {
                write!(f, "v5 pair rotate load failed: {error}")
            },
        }
    }
}

impl<MemoryError>
    ExecutionGeometryNativeRotateHaltPairLoadFailure<MemoryError>
{
    /// Reports whether any mapping rollback still requires adapter cleanup.
    #[must_use]
    pub fn cleanup_pending(&self) -> bool {
        match self {
            Self::Halt {
                error,
                rotate_release_failure,
            } => error.cleanup_pending() || rotate_release_failure.is_some(),
            Self::Rotate(error) => error.cleanup_pending(),
        }
    }

    /// Retries every retained rollback while preserving the primary load error.
    #[must_use]
    pub fn retry_cleanup<Adapter>(self, adapter: &mut Adapter) -> Self
    where
        Adapter: NativeExecutableMemoryAdapter<Error = MemoryError>,
    {
        match self {
            Self::Halt {
                error,
                rotate_release_failure,
            } => Self::Halt {
                error: Box::new((*error).retry_cleanup(adapter)),
                rotate_release_failure: retry_pair_release(
                    rotate_release_failure,
                    adapter,
                ),
            },
            Self::Rotate(error) => {
                Self::Rotate(Box::new((*error).retry_cleanup(adapter)))
            },
        }
    }
}

impl<MemoryError: Display> Display
    for ExecutionGeometryNativeRotateHaltPairReleaseFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        let halt = self.halt_failure.is_some();
        let rotate = self.rotate_failure.is_some();
        write!(
            f,
            "v5 pair release incomplete (halt={halt}, rotate={rotate})"
        )
    }
}

impl<MemoryError: Display, RunnerError: Display> Display
    for ExecutionGeometryNativeRotateHaltFailure<MemoryError, RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match &self.cause {
            ExecutionGeometryNativeRotateHaltFailureCause::Halt(error) => {
                write!(
                    f,
                    "v5 sequence step {} halt failed: {error}",
                    self.index
                )
            },
            ExecutionGeometryNativeRotateHaltFailureCause::Rotate(error) => {
                write!(
                    f,
                    "v5 sequence step {} rotate failed: {error}",
                    self.index,
                )
            },
        }
    }
}

impl<MemoryError, RunnerError>
    ExecutionGeometryNativeRotateHaltFailure<MemoryError, RunnerError>
{
    /// Returns the exact per-step transaction failure.
    #[must_use]
    pub const fn cause(
        &self,
    ) -> &RotateHaltFailureCause<MemoryError, RunnerError> {
        &self.cause
    }

    /// Returns the zero-based step that failed.
    #[must_use]
    pub const fn index(&self) -> usize {
        self.index
    }

    /// Returns the last fully committed opaque-geometry checkpoint.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        &self.state
    }
}

impl BoundExecutionGeometryNativeRotateHaltSequence<'_, '_> {
    /// Executes the prebound pair without executable-memory adapter operations.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeRotateHaltLoadedFailure`] at the exact
    /// failing step while retaining every earlier committed checkpoint.
    pub fn execute<Runner>(
        &self,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> ExecutionGeometryNativeRotateHaltLoadedResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        let (memory, input, output) = buffers.into_parts();
        let rotate = self.execute_rotate(
            runner,
            NativeRegionBuffers::new(&mut *memory, input, &mut *output),
        )?;
        if rotate.outcome() == NativeRegionInvocationOutcome::GuardMiss {
            return Ok(ExecutionGeometryNativeRotateHaltOutcome::GuardMiss {
                index: 0,
                state: rotate.state().clone(),
            });
        }
        let halt = self.execute_halt(
            runner,
            NativeRegionBuffers::new(&mut *memory, input, &mut *output),
        )?;
        if halt.outcome() == NativeRegionInvocationOutcome::GuardMiss {
            Ok(ExecutionGeometryNativeRotateHaltOutcome::GuardMiss {
                index: 1,
                state: halt.state().clone(),
            })
        } else {
            Ok(ExecutionGeometryNativeRotateHaltOutcome::Completed(
                halt.state().clone(),
            ))
        }
    }

    fn execute_halt<Runner>(
        &self,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> LoadedStepResult<
        ExecutionGeometryNativeInitialHaltCompletion,
        Runner::Error,
    >
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        use ExecutionGeometryNativeRotateHaltLoadedFailureCause as Cause;

        let prepared =
            self.sequence.halt.prepare(buffers).map_err(|error| {
                Box::new(ExecutionGeometryNativeRotateHaltLoadedFailure {
                    cause: Cause::HaltPreparation(error),
                    index: 1,
                    state: self.sequence.halt.checkpoint().clone(),
                })
            })?;
        let bound = prepared.bind_executable(self.halt).map_err(|error| {
            Box::new(ExecutionGeometryNativeRotateHaltLoadedFailure {
                cause: Cause::HaltBinding(error),
                index: 1,
                state: self.sequence.halt.checkpoint().clone(),
            })
        })?;
        bound.execute(runner).map_err(|error| {
            Box::new(ExecutionGeometryNativeRotateHaltLoadedFailure {
                cause: Cause::HaltExecution(error),
                index: 1,
                state: self.sequence.halt.checkpoint().clone(),
            })
        })
    }

    fn execute_rotate<Runner>(
        &self,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> LoadedStepResult<RotateCompletion, Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        use ExecutionGeometryNativeRotateHaltLoadedFailureCause as Cause;

        let prepared =
            self.sequence.rotate.prepare(buffers).map_err(|error| {
                Box::new(ExecutionGeometryNativeRotateHaltLoadedFailure {
                    cause: Cause::RotatePreparation(error),
                    index: 0,
                    state: self.sequence.rotate.checkpoint().clone(),
                })
            })?;
        let bound = prepared.bind_executable(self.rotate).map_err(|error| {
            Box::new(ExecutionGeometryNativeRotateHaltLoadedFailure {
                cause: Cause::RotateBinding(error),
                index: 0,
                state: self.sequence.rotate.checkpoint().clone(),
            })
        })?;
        bound.execute(runner).map_err(|error| {
            Box::new(ExecutionGeometryNativeRotateHaltLoadedFailure {
                cause: Cause::RotateExecution(error),
                index: 0,
                state: self.sequence.rotate.checkpoint().clone(),
            })
        })
    }
}

impl ExecutionGeometryNativeRotateHaltEvidence {
    /// Groups the exact two reviewed v5 programs and verified native artifacts.
    #[must_use]
    pub const fn new(
        rotate_program: ExecutionGeometryRegionEffectProgram,
        rotate_artifact: VerifiedRotateArtifact,
        halt_program: ExecutionGeometryRegionEffectProgram,
        halt_artifact: VerifiedExecutionGeometryInitialHaltNativeObjectArtifact,
    ) -> Self {
        Self {
            halt_artifact,
            halt_program,
            rotate_artifact,
            rotate_program,
        }
    }
}

impl<RunnerError> ExecutionGeometryNativeRotateHaltLoadedFailure<RunnerError> {
    /// Returns the exact prebound execution failure cause.
    #[must_use]
    pub const fn cause(
        &self,
    ) -> &ExecutionGeometryNativeRotateHaltLoadedFailureCause<RunnerError> {
        &self.cause
    }

    /// Returns the zero-based step that failed.
    #[must_use]
    pub const fn index(&self) -> usize {
        self.index
    }

    /// Returns the last fully committed opaque-geometry checkpoint.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        &self.state
    }
}

impl<MemoryError>
    ExecutionGeometryNativeRotateHaltPairReleaseFailure<MemoryError>
{
    /// Returns the retained halt cleanup failure, when halt release failed.
    #[must_use]
    pub fn halt_failure(
        &self,
    ) -> Option<&ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>
    {
        self.halt_failure.as_deref()
    }

    /// Retries every still-owned mapping and retains only repeated failures.
    ///
    /// # Errors
    ///
    /// Returns a refreshed pair cleanup failure when either release fails
    /// again.
    pub fn retry<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> GeometryNativeRotateHaltPairReleaseResult<MemoryError>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = MemoryError>,
    {
        let halt_failure = retry_pair_release(self.halt_failure, adapter);
        let rotate_failure = retry_pair_release(self.rotate_failure, adapter);
        pair_release_result(halt_failure, rotate_failure)
    }

    /// Returns the retained rotate cleanup failure, when release failed.
    #[must_use]
    pub fn rotate_failure(
        &self,
    ) -> Option<&ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>
    {
        self.rotate_failure.as_deref()
    }
}

impl LoadedExecutionGeometryNativeRotateHaltSequence {
    /// Executes through the owned synchronized pair without mapping operations.
    ///
    /// # Errors
    ///
    /// Returns exact indexed execution failure while retaining both mappings.
    pub fn execute<Runner>(
        &self,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> ExecutionGeometryNativeRotateHaltLoadedResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        let bound = BoundExecutionGeometryNativeRotateHaltSequence {
            halt: &self.halt,
            rotate: &self.rotate,
            sequence: &self.sequence,
        };
        bound.execute(runner, buffers)
    }

    /// Returns the owned synchronized halt executable.
    #[must_use]
    pub const fn halt(&self) -> &ReadyExecutionGeometryNativeExecutable {
        &self.halt
    }

    /// Releases both mappings, attempting both even when one release fails.
    ///
    /// # Errors
    ///
    /// Returns retry ownership for every mapping whose release failed.
    pub fn release<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> GeometryNativeRotateHaltPairReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let halt_failure =
            release_execution_geometry_native_executable(adapter, self.halt)
                .err()
                .map(Box::new);
        let rotate_failure =
            release_execution_geometry_native_executable(adapter, self.rotate)
                .err()
                .map(Box::new);
        pair_release_result(halt_failure, rotate_failure)
    }

    /// Returns the owned synchronized rotate executable.
    #[must_use]
    pub const fn rotate(&self) -> &ReadyExecutionGeometryNativeExecutable {
        &self.rotate
    }

    /// Returns the exact immutable admission owned beside the ready pair.
    #[must_use]
    pub const fn sequence(&self) -> &ExecutionGeometryNativeRotateHaltSequence {
        &self.sequence
    }
}

impl ExecutionGeometryNativeRotateHaltOutcome {
    /// Returns the completed or last committed opaque-geometry checkpoint.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        match self {
            Self::Completed(state) | Self::GuardMiss { state, .. } => state,
        }
    }
}

impl ExecutionGeometryNativeRotateHaltSequence {
    /// Prebinds both ready executables before any caller buffer can mutate.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeRotateHaltExecutableBindingError`] when
    /// either synchronized image differs from its admitted step.
    pub fn bind_executables<'sequence, 'executable>(
        &'sequence self,
        rotate: &'executable ReadyExecutionGeometryNativeExecutable,
        halt: &'executable ReadyExecutionGeometryNativeExecutable,
    ) -> Result<
        BoundExecutionGeometryNativeRotateHaltSequence<'sequence, 'executable>,
        ExecutionGeometryNativeRotateHaltExecutableBindingError,
    > {
        if self.rotate.load_image() != rotate.image() {
            use RotateHaltBindingError as Error;
            return Err(Error::Rotate);
        }
        if self.halt.load_image() != halt.image() {
            return Err(
                ExecutionGeometryNativeRotateHaltExecutableBindingError::Halt,
            );
        }
        Ok(BoundExecutionGeometryNativeRotateHaltSequence {
            halt,
            rotate,
            sequence: self,
        })
    }

    /// Executes rotate then halt with per-step load/call/release
    /// ownership.
    ///
    /// A guard miss stops before the suffix and returns the last committed
    /// checkpoint. A later failure retains progress from every earlier applied
    /// step. Each per-step transaction preserves its own cleanup retry
    /// evidence.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeRotateHaltFailure`] with exact step
    /// index, transaction cause, and last committed checkpoint.
    pub fn execute_transactionally<MemoryAdapter, Runner>(
        &self,
        memory_adapter: &mut MemoryAdapter,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> ExecutionGeometryNativeRotateHaltAdapterResult<MemoryAdapter, Runner>
    where
        MemoryAdapter: NativeExecutableMemoryAdapter,
        Runner: ExecutionGeometryNativeRunner,
    {
        let (memory, input, output) = buffers.into_parts();
        let rotate = self
            .rotate
            .execute_transactionally(
                memory_adapter,
                runner,
                NativeRegionBuffers::new(&mut *memory, input, &mut *output),
            )
            .map_err(|cause| {
                use ExecutionGeometryNativeRotateHaltFailureCause as Cause;
                let state = rotate_failure_state(&self.rotate, &cause);
                Box::new(ExecutionGeometryNativeRotateHaltFailure {
                    cause: Cause::Rotate(cause),
                    index: 0,
                    state,
                })
            })?;
        if rotate.outcome() == NativeRegionInvocationOutcome::GuardMiss {
            return Ok(ExecutionGeometryNativeRotateHaltOutcome::GuardMiss {
                index: 0,
                state: rotate.state().clone(),
            });
        }

        let halt = self
            .halt
            .execute_transactionally(
                memory_adapter,
                runner,
                NativeRegionBuffers::new(&mut *memory, input, &mut *output),
            )
            .map_err(|cause| {
                let state = halt_failure_state(&self.halt, &cause);
                Box::new(ExecutionGeometryNativeRotateHaltFailure {
                    cause: ExecutionGeometryNativeRotateHaltFailureCause::Halt(
                        cause,
                    ),
                    index: 1,
                    state,
                })
            })?;
        if halt.outcome() == NativeRegionInvocationOutcome::GuardMiss {
            Ok(ExecutionGeometryNativeRotateHaltOutcome::GuardMiss {
                index: 1,
                state: halt.state().clone(),
            })
        } else {
            Ok(ExecutionGeometryNativeRotateHaltOutcome::Completed(
                halt.state().clone(),
            ))
        }
    }

    /// Returns the admitted final halt step.
    #[must_use]
    pub const fn halt(&self) -> &ExecutionGeometryNativeInitialHaltAdmission {
        &self.halt
    }

    /// Loads both exact v5 executables and owns them as one reusable pair.
    ///
    /// Halt load failure immediately releases the already-ready rotate.
    /// Failed rollback retains that ready executable without replacing the
    /// primary halt load error.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeRotateHaltPairLoadFailure`] for either
    /// load phase and any retryable partial-load cleanup ownership.
    pub fn load_pair<Adapter>(
        &self,
        adapter: &mut Adapter,
    ) -> GeometryNativeRotateHaltPairLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let rotate = load_execution_geometry_native_executable(
            adapter,
            self.rotate.load_image(),
        )
        .map_err(|error| {
            Box::new(ExecutionGeometryNativeRotateHaltPairLoadFailure::Rotate(
                Box::new(error),
            ))
        })?;
        let halt = match load_execution_geometry_native_executable(
            adapter,
            self.halt.load_image(),
        ) {
            Ok(halt) => halt,
            Err(error) => {
                let rotate_release_failure =
                    release_execution_geometry_native_executable(
                        adapter, rotate,
                    )
                    .err()
                    .map(Box::new);
                return Err(Box::new(
                    ExecutionGeometryNativeRotateHaltPairLoadFailure::Halt {
                        error: Box::new(error),
                        rotate_release_failure,
                    },
                ));
            },
        };
        Ok(LoadedExecutionGeometryNativeRotateHaltSequence {
            halt,
            rotate,
            sequence: self.clone(),
        })
    }

    /// Admits a rotate and its exact following halt before native
    /// mapping.
    ///
    /// The rotate admission normatively replays the entry checkpoint. The
    /// resulting opaque checkpoint is then the sole authority accepted for halt
    /// admission, so profile/geometry/observation/live-in continuity is checked
    /// before either step can map executable memory.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeRotateHaltAdmissionError`] when either
    /// independently verified step cannot bind to its required checkpoint.
    pub fn new(
        evidence: ExecutionGeometryNativeRotateHaltEvidence,
        checkpoint: ProfileMachineState,
    ) -> Result<Self, ExecutionGeometryNativeRotateHaltAdmissionError> {
        let ExecutionGeometryNativeRotateHaltEvidence {
            halt_artifact,
            halt_program,
            rotate_artifact,
            rotate_program,
        } = evidence;
        let rotate = ExecutionGeometryNativeRotateAdmission::new(
            rotate_program,
            checkpoint,
            rotate_artifact,
        )
        .map_err(ExecutionGeometryNativeRotateHaltAdmissionError::Rotate)?;
        let halt = ExecutionGeometryNativeInitialHaltAdmission::new(
            halt_program,
            rotate.expected_state().clone(),
            halt_artifact,
        )
        .map_err(ExecutionGeometryNativeRotateHaltAdmissionError::Halt)?;
        Ok(Self { halt, rotate })
    }

    /// Returns the admitted first rotate step.
    #[must_use]
    pub const fn rotate(&self) -> &ExecutionGeometryNativeRotateAdmission {
        &self.rotate
    }
}

fn pair_release_result<MemoryError>(
    halt_failure: Option<
        Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
    >,
    rotate_failure: Option<
        Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
    >,
) -> GeometryNativeRotateHaltPairReleaseResult<MemoryError> {
    if halt_failure.is_none() && rotate_failure.is_none() {
        Ok(())
    } else {
        Err(Box::new(
            ExecutionGeometryNativeRotateHaltPairReleaseFailure {
                halt_failure,
                rotate_failure,
            },
        ))
    }
}

fn retry_pair_release<Adapter, MemoryError>(
    failure: Option<
        Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
    >,
    adapter: &mut Adapter,
) -> Option<Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>>
where
    Adapter: NativeExecutableMemoryAdapter<Error = MemoryError>,
{
    failure.and_then(|candidate| candidate.retry(adapter).err().map(Box::new))
}

fn halt_failure_state<MemoryError, RunnerError>(
    admission: &ExecutionGeometryNativeInitialHaltAdmission,
    failure: &ExecutionGeometryNativeInitialHaltTransactionFailure<
        MemoryError,
        RunnerError,
    >,
) -> ProfileMachineState {
    match failure {
        ExecutionGeometryNativeInitialHaltTransactionFailure::Release {
            completion,
            ..
        } => completion.state().clone(),
        ExecutionGeometryNativeInitialHaltTransactionFailure::Binding {
            ..
        }
        | ExecutionGeometryNativeInitialHaltTransactionFailure::Execution {
            ..
        }
        | ExecutionGeometryNativeInitialHaltTransactionFailure::Load(_)
        | ExecutionGeometryNativeInitialHaltTransactionFailure::Preparation(
            _,
        ) => admission.checkpoint().clone(),
    }
}

fn rotate_failure_state<MemoryError, RunnerError>(
    admission: &ExecutionGeometryNativeRotateAdmission,
    failure: &ExecutionGeometryNativeRotateTransactionFailure<
        MemoryError,
        RunnerError,
    >,
) -> ProfileMachineState {
    match failure {
        ExecutionGeometryNativeRotateTransactionFailure::Release {
            completion,
            ..
        } => completion.state().clone(),
        ExecutionGeometryNativeRotateTransactionFailure::Binding { .. }
        | ExecutionGeometryNativeRotateTransactionFailure::Execution {
            ..
        }
        | ExecutionGeometryNativeRotateTransactionFailure::Load(_)
        | ExecutionGeometryNativeRotateTransactionFailure::Preparation(_) => {
            admission.checkpoint().clone()
        },
    }
}
