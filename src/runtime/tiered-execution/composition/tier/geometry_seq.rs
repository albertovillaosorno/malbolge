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
//   - Ordered native composition of one v5 no-operation followed by halt.
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
//   - Composes the first two-step state-changing v5 native path.
// - Description:
//   - Preserves the last committed opaque checkpoint across step boundaries.
// - Usage:
//   - Construct from DP-style no-op/halt evidence, then execute
//     transactionally.
// - Defaults:
//   - Guard miss stops before the suffix; failure reports last committed state.
//

//! Two-step explicit-geometry native no-operation/halt composition.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{ExecutionGeometryRegionEffectProgram, ProfileMachineState};

use crate::execution_native::{
    ExecutionGeometryNativeExecutableReleaseFailure,
    ExecutionGeometryNativeRunner, NativeExecutableLoadFailure,
    NativeExecutableMemoryAdapter, NativeRegionBuffers,
    NativeRegionInvocationOutcome, ReadyExecutionGeometryNativeExecutable,
    VerifiedExecutionGeometryInitialHaltNativeObjectArtifact,
    VerifiedExecutionGeometryNoOperationNativeObjectArtifact,
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
use crate::geometry_native_no_operation::{
    ExecutionGeometryNativeNoOperationAdmission,
    ExecutionGeometryNativeNoOperationAdmissionError,
    ExecutionGeometryNativeNoOperationBindingError,
    ExecutionGeometryNativeNoOperationCompletion,
    ExecutionGeometryNativeNoOperationExecutionError,
    ExecutionGeometryNativeNoOperationPreparationError,
    ExecutionGeometryNativeNoOperationTransactionFailure,
};

type VerifiedNoOperationArtifact =
    VerifiedExecutionGeometryNoOperationNativeObjectArtifact;

type LoadedStepResult<Completion, RunnerError> = Result<
    Completion,
    Box<ExecutionGeometryNativeNoopHaltLoadedFailure<RunnerError>>,
>;

/// Failure while admitting the exact two-step v5 native sequence.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeNoopHaltAdmissionError {
    /// Final halt could not bind to the normatively replayed no-op checkpoint.
    Halt(ExecutionGeometryNativeInitialHaltAdmissionError),
    /// First no-operation could not bind to the entry checkpoint.
    NoOperation(ExecutionGeometryNativeNoOperationAdmissionError),
}

/// Failure while prebinding both synchronized executables to the sequence.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeNoopHaltExecutableBindingError {
    /// Ready halt image differs from the admitted halt image.
    Halt,
    /// Ready no-operation image differs from the admitted no-operation image.
    NoOperation,
}

/// Failure cause while executing a prebound two-step native sequence.
#[derive(Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeNoopHaltLoadedFailureCause<RunnerError> {
    /// Final halt executable unexpectedly failed exact binding.
    HaltBinding(ExecutionGeometryNativeInitialHaltBindingError),
    /// Final halt runner/completion failed.
    HaltExecution(
        Box<ExecutionGeometryNativeInitialHaltExecutionError<RunnerError>>,
    ),
    /// Final halt buffer preparation failed.
    HaltPreparation(ExecutionGeometryNativeInitialHaltPreparationError),
    /// First no-operation executable unexpectedly failed exact binding.
    NoOperationBinding(ExecutionGeometryNativeNoOperationBindingError),
    /// First no-operation runner/completion failed.
    NoOperationExecution(
        Box<ExecutionGeometryNativeNoOperationExecutionError<RunnerError>>,
    ),
    /// First no-operation buffer preparation failed.
    NoOperationPreparation(ExecutionGeometryNativeNoOperationPreparationError),
}

/// Indexed failure from a prebound sequence retaining last committed state.
#[derive(Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeNoopHaltLoadedFailure<RunnerError> {
    cause: ExecutionGeometryNativeNoopHaltLoadedFailureCause<RunnerError>,
    index: usize,
    state: ProfileMachineState,
}

/// Failure while loading the exact reusable v5 no-operation/halt pair.
#[derive(Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeNoopHaltPairLoadFailure<MemoryError> {
    /// Halt loading failed after the no-operation was ready.
    Halt {
        /// Primary halt load failure.
        error: Box<NativeExecutableLoadFailure<MemoryError>>,
        /// Failed rollback retaining the ready no-operation for retry.
        no_operation_release_failure: Option<
            Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
        >,
    },
    /// No-operation loading failed before any ready executable existed.
    NoOperation(Box<NativeExecutableLoadFailure<MemoryError>>),
}

/// Failed pair release retaining every mapping that still needs cleanup.
#[derive(Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeNoopHaltPairReleaseFailure<MemoryError> {
    halt_failure: Option<
        Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
    >,
    no_operation_failure: Option<
        Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
    >,
}

/// Primary failure from one indexed step of the two-step native sequence.
#[derive(Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeNoopHaltFailureCause<MemoryError, RunnerError> {
    /// Final halt transaction failed.
    Halt(
        Box<
            ExecutionGeometryNativeInitialHaltTransactionFailure<
                MemoryError,
                RunnerError,
            >,
        >,
    ),
    /// First no-operation transaction failed.
    NoOperation(
        Box<
            ExecutionGeometryNativeNoOperationTransactionFailure<
                MemoryError,
                RunnerError,
            >,
        >,
    ),
}

/// Indexed two-step native failure retaining the last committed checkpoint.
#[derive(Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeNoopHaltFailure<MemoryError, RunnerError> {
    cause:
        ExecutionGeometryNativeNoopHaltFailureCause<MemoryError, RunnerError>,
    index: usize,
    state: ProfileMachineState,
}

/// Successful or safely suspended two-step v5 native execution.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeNoopHaltOutcome {
    /// Both no-operation and halt applied exactly.
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
pub struct ExecutionGeometryNativeNoopHaltEvidence {
    halt_artifact: VerifiedExecutionGeometryInitialHaltNativeObjectArtifact,
    halt_program: ExecutionGeometryRegionEffectProgram,
    no_operation_artifact: VerifiedNoOperationArtifact,
    no_operation_program: ExecutionGeometryRegionEffectProgram,
}

/// Two independently admitted v5 native steps sharing one opaque geometry line.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeNoopHaltSequence {
    halt: ExecutionGeometryNativeInitialHaltAdmission,
    no_operation: ExecutionGeometryNativeNoOperationAdmission,
}

/// Two exact synchronized executables prebound before caller-state mutation.
#[derive(Debug)]
pub struct BoundExecutionGeometryNativeNoopHaltSequence<'sequence, 'executable>
{
    halt: &'executable ReadyExecutionGeometryNativeExecutable,
    no_operation: &'executable ReadyExecutionGeometryNativeExecutable,
    sequence: &'sequence ExecutionGeometryNativeNoopHaltSequence,
}

/// Owned ready no-operation/halt pair bound to one admitted sequence.
#[derive(Debug)]
pub struct LoadedExecutionGeometryNativeNoopHaltSequence {
    halt: ReadyExecutionGeometryNativeExecutable,
    no_operation: ReadyExecutionGeometryNativeExecutable,
    sequence: ExecutionGeometryNativeNoopHaltSequence,
}

/// Result of executing one prebound geometry-native pair.
pub type ExecutionGeometryNativeNoopHaltLoadedResult<RunnerError> = Result<
    ExecutionGeometryNativeNoopHaltOutcome,
    Box<ExecutionGeometryNativeNoopHaltLoadedFailure<RunnerError>>,
>;

/// Result of loading both exact ready executables as one owned pair.
pub type GeometryNativeNoopHaltPairLoadResult<MemoryError> = Result<
    LoadedExecutionGeometryNativeNoopHaltSequence,
    Box<ExecutionGeometryNativeNoopHaltPairLoadFailure<MemoryError>>,
>;

/// Result of releasing every mapping owned by one loaded pair.
pub type GeometryNativeNoopHaltPairReleaseResult<MemoryError> = Result<
    (),
    Box<ExecutionGeometryNativeNoopHaltPairReleaseFailure<MemoryError>>,
>;

/// Result of one concrete adapter/runner two-step transaction.
pub type ExecutionGeometryNativeNoopHaltAdapterResult<MemoryAdapter, Runner> =
    Result<
        ExecutionGeometryNativeNoopHaltOutcome,
        Box<
            ExecutionGeometryNativeNoopHaltFailure<
                <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
                <Runner as ExecutionGeometryNativeRunner>::Error,
            >,
        >,
    >;

impl Display for ExecutionGeometryNativeNoopHaltAdmissionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Halt(error) => {
                write!(f, "v5 sequence halt admission: {error}")
            },
            Self::NoOperation(error) => {
                write!(f, "v5 sequence no-operation admission: {error}")
            },
        }
    }
}

impl Display for ExecutionGeometryNativeNoopHaltExecutableBindingError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Halt => "v5 sequence halt executable identity differs",
            Self::NoOperation => {
                "v5 sequence no-operation executable identity differs"
            },
        })
    }
}

impl<RunnerError: Display> Display
    for ExecutionGeometryNativeNoopHaltLoadedFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        use ExecutionGeometryNativeNoopHaltLoadedFailureCause as Cause;

        write!(f, "v5 loaded sequence step {} failed: ", self.index)?;
        match &self.cause {
            Cause::HaltBinding(error) => Display::fmt(error, f),
            Cause::HaltExecution(error) => Display::fmt(error, f),
            Cause::HaltPreparation(error) => Display::fmt(error, f),
            Cause::NoOperationBinding(error) => Display::fmt(error, f),
            Cause::NoOperationExecution(error) => Display::fmt(error, f),
            Cause::NoOperationPreparation(error) => Display::fmt(error, f),
        }
    }
}

impl<MemoryError: Display> Display
    for ExecutionGeometryNativeNoopHaltPairLoadFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Halt { error, .. } => {
                write!(f, "v5 pair halt load failed: {error}")
            },
            Self::NoOperation(error) => {
                write!(f, "v5 pair no-operation load failed: {error}")
            },
        }
    }
}

impl<MemoryError: Display> Display
    for ExecutionGeometryNativeNoopHaltPairReleaseFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        let halt = self.halt_failure.is_some();
        let no_operation = self.no_operation_failure.is_some();
        write!(
            f,
            "v5 pair release incomplete (halt={halt}, noop={no_operation})"
        )
    }
}

impl<MemoryError: Display, RunnerError: Display> Display
    for ExecutionGeometryNativeNoopHaltFailure<MemoryError, RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match &self.cause {
            ExecutionGeometryNativeNoopHaltFailureCause::Halt(error) => {
                write!(
                    f,
                    "v5 sequence step {} halt failed: {error}",
                    self.index
                )
            },
            ExecutionGeometryNativeNoopHaltFailureCause::NoOperation(error) => {
                write!(
                    f,
                    "v5 sequence step {} no-operation failed: {error}",
                    self.index,
                )
            },
        }
    }
}

impl<MemoryError, RunnerError>
    ExecutionGeometryNativeNoopHaltFailure<MemoryError, RunnerError>
{
    /// Returns the exact per-step transaction failure.
    #[must_use]
    pub const fn cause(
        &self,
    ) -> &ExecutionGeometryNativeNoopHaltFailureCause<MemoryError, RunnerError>
    {
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

impl BoundExecutionGeometryNativeNoopHaltSequence<'_, '_> {
    /// Executes the prebound pair without executable-memory adapter operations.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeNoopHaltLoadedFailure`] at the exact
    /// failing step while retaining every earlier committed checkpoint.
    pub fn execute<Runner>(
        &self,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> ExecutionGeometryNativeNoopHaltLoadedResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        let (memory, input, output) = buffers.into_parts();
        let no_operation = self.execute_no_operation(
            runner,
            NativeRegionBuffers::new(&mut *memory, input, &mut *output),
        )?;
        if no_operation.outcome() == NativeRegionInvocationOutcome::GuardMiss {
            return Ok(ExecutionGeometryNativeNoopHaltOutcome::GuardMiss {
                index: 0,
                state: no_operation.state().clone(),
            });
        }
        let halt = self.execute_halt(
            runner,
            NativeRegionBuffers::new(&mut *memory, input, &mut *output),
        )?;
        if halt.outcome() == NativeRegionInvocationOutcome::GuardMiss {
            Ok(ExecutionGeometryNativeNoopHaltOutcome::GuardMiss {
                index: 1,
                state: halt.state().clone(),
            })
        } else {
            Ok(ExecutionGeometryNativeNoopHaltOutcome::Completed(
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
        use ExecutionGeometryNativeNoopHaltLoadedFailureCause as Cause;

        let prepared =
            self.sequence.halt.prepare(buffers).map_err(|error| {
                Box::new(ExecutionGeometryNativeNoopHaltLoadedFailure {
                    cause: Cause::HaltPreparation(error),
                    index: 1,
                    state: self.sequence.halt.checkpoint().clone(),
                })
            })?;
        let bound = prepared.bind_executable(self.halt).map_err(|error| {
            Box::new(ExecutionGeometryNativeNoopHaltLoadedFailure {
                cause: Cause::HaltBinding(error),
                index: 1,
                state: self.sequence.halt.checkpoint().clone(),
            })
        })?;
        bound.execute(runner).map_err(|error| {
            Box::new(ExecutionGeometryNativeNoopHaltLoadedFailure {
                cause: Cause::HaltExecution(error),
                index: 1,
                state: self.sequence.halt.checkpoint().clone(),
            })
        })
    }

    fn execute_no_operation<Runner>(
        &self,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> LoadedStepResult<
        ExecutionGeometryNativeNoOperationCompletion,
        Runner::Error,
    >
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        use ExecutionGeometryNativeNoopHaltLoadedFailureCause as Cause;

        let prepared =
            self.sequence
                .no_operation
                .prepare(buffers)
                .map_err(|error| {
                    Box::new(ExecutionGeometryNativeNoopHaltLoadedFailure {
                        cause: Cause::NoOperationPreparation(error),
                        index: 0,
                        state: self.sequence.no_operation.checkpoint().clone(),
                    })
                })?;
        let bound =
            prepared
                .bind_executable(self.no_operation)
                .map_err(|error| {
                    Box::new(ExecutionGeometryNativeNoopHaltLoadedFailure {
                        cause: Cause::NoOperationBinding(error),
                        index: 0,
                        state: self.sequence.no_operation.checkpoint().clone(),
                    })
                })?;
        bound.execute(runner).map_err(|error| {
            Box::new(ExecutionGeometryNativeNoopHaltLoadedFailure {
                cause: Cause::NoOperationExecution(error),
                index: 0,
                state: self.sequence.no_operation.checkpoint().clone(),
            })
        })
    }
}

impl ExecutionGeometryNativeNoopHaltEvidence {
    /// Groups the exact two reviewed v5 programs and verified native artifacts.
    #[must_use]
    pub const fn new(
        no_operation_program: ExecutionGeometryRegionEffectProgram,
        no_operation_artifact: VerifiedNoOperationArtifact,
        halt_program: ExecutionGeometryRegionEffectProgram,
        halt_artifact: VerifiedExecutionGeometryInitialHaltNativeObjectArtifact,
    ) -> Self {
        Self {
            halt_artifact,
            halt_program,
            no_operation_artifact,
            no_operation_program,
        }
    }
}

impl<RunnerError> ExecutionGeometryNativeNoopHaltLoadedFailure<RunnerError> {
    /// Returns the exact prebound execution failure cause.
    #[must_use]
    pub const fn cause(
        &self,
    ) -> &ExecutionGeometryNativeNoopHaltLoadedFailureCause<RunnerError> {
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
    ExecutionGeometryNativeNoopHaltPairReleaseFailure<MemoryError>
{
    /// Returns the retained halt cleanup failure, when halt release failed.
    #[must_use]
    pub fn halt_failure(
        &self,
    ) -> Option<&ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>
    {
        self.halt_failure.as_deref()
    }

    /// Returns the retained no-operation cleanup failure, when release failed.
    #[must_use]
    pub fn no_operation_failure(
        &self,
    ) -> Option<&ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>
    {
        self.no_operation_failure.as_deref()
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
    ) -> GeometryNativeNoopHaltPairReleaseResult<MemoryError>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = MemoryError>,
    {
        let halt_failure = retry_pair_release(self.halt_failure, adapter);
        let no_operation_failure =
            retry_pair_release(self.no_operation_failure, adapter);
        pair_release_result(halt_failure, no_operation_failure)
    }
}

impl LoadedExecutionGeometryNativeNoopHaltSequence {
    /// Executes through the owned synchronized pair without mapping operations.
    ///
    /// # Errors
    ///
    /// Returns exact indexed execution failure while retaining both mappings.
    pub fn execute<Runner>(
        &self,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> ExecutionGeometryNativeNoopHaltLoadedResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        let bound = BoundExecutionGeometryNativeNoopHaltSequence {
            halt: &self.halt,
            no_operation: &self.no_operation,
            sequence: &self.sequence,
        };
        bound.execute(runner, buffers)
    }

    /// Returns the owned synchronized halt executable.
    #[must_use]
    pub const fn halt(&self) -> &ReadyExecutionGeometryNativeExecutable {
        &self.halt
    }

    /// Returns the owned synchronized no-operation executable.
    #[must_use]
    pub const fn no_operation(
        &self,
    ) -> &ReadyExecutionGeometryNativeExecutable {
        &self.no_operation
    }

    /// Releases both mappings, attempting both even when one release fails.
    ///
    /// # Errors
    ///
    /// Returns retry ownership for every mapping whose release failed.
    pub fn release<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> GeometryNativeNoopHaltPairReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let halt_failure =
            release_execution_geometry_native_executable(adapter, self.halt)
                .err()
                .map(Box::new);
        let no_operation_failure =
            release_execution_geometry_native_executable(
                adapter,
                self.no_operation,
            )
            .err()
            .map(Box::new);
        pair_release_result(halt_failure, no_operation_failure)
    }

    /// Returns the exact immutable admission owned beside the ready pair.
    #[must_use]
    pub const fn sequence(&self) -> &ExecutionGeometryNativeNoopHaltSequence {
        &self.sequence
    }
}

impl ExecutionGeometryNativeNoopHaltOutcome {
    /// Returns the completed or last committed opaque-geometry checkpoint.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        match self {
            Self::Completed(state) | Self::GuardMiss { state, .. } => state,
        }
    }
}

impl ExecutionGeometryNativeNoopHaltSequence {
    /// Prebinds both ready executables before any caller buffer can mutate.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeNoopHaltExecutableBindingError`] when
    /// either synchronized image differs from its admitted step.
    pub fn bind_executables<'sequence, 'executable>(
        &'sequence self,
        no_operation: &'executable ReadyExecutionGeometryNativeExecutable,
        halt: &'executable ReadyExecutionGeometryNativeExecutable,
    ) -> Result<
        BoundExecutionGeometryNativeNoopHaltSequence<'sequence, 'executable>,
        ExecutionGeometryNativeNoopHaltExecutableBindingError,
    > {
        if self.no_operation.load_image() != no_operation.image() {
            use ExecutionGeometryNativeNoopHaltExecutableBindingError as Error;
            return Err(Error::NoOperation);
        }
        if self.halt.load_image() != halt.image() {
            return Err(
                ExecutionGeometryNativeNoopHaltExecutableBindingError::Halt,
            );
        }
        Ok(BoundExecutionGeometryNativeNoopHaltSequence {
            halt,
            no_operation,
            sequence: self,
        })
    }

    /// Executes no-operation then halt with per-step load/call/release
    /// ownership.
    ///
    /// A guard miss stops before the suffix and returns the last committed
    /// checkpoint. A later failure retains progress from every earlier applied
    /// step. Each per-step transaction preserves its own cleanup retry
    /// evidence.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeNoopHaltFailure`] with exact step
    /// index, transaction cause, and last committed checkpoint.
    pub fn execute_transactionally<MemoryAdapter, Runner>(
        &self,
        memory_adapter: &mut MemoryAdapter,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> ExecutionGeometryNativeNoopHaltAdapterResult<MemoryAdapter, Runner>
    where
        MemoryAdapter: NativeExecutableMemoryAdapter,
        Runner: ExecutionGeometryNativeRunner,
    {
        let (memory, input, output) = buffers.into_parts();
        let no_operation = self
            .no_operation
            .execute_transactionally(
                memory_adapter,
                runner,
                NativeRegionBuffers::new(&mut *memory, input, &mut *output),
            )
            .map_err(|cause| {
                use ExecutionGeometryNativeNoopHaltFailureCause as Cause;
                let state =
                    no_operation_failure_state(&self.no_operation, &cause);
                Box::new(ExecutionGeometryNativeNoopHaltFailure {
                    cause: Cause::NoOperation(cause),
                    index: 0,
                    state,
                })
            })?;
        if no_operation.outcome() == NativeRegionInvocationOutcome::GuardMiss {
            return Ok(ExecutionGeometryNativeNoopHaltOutcome::GuardMiss {
                index: 0,
                state: no_operation.state().clone(),
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
                Box::new(ExecutionGeometryNativeNoopHaltFailure {
                    cause: ExecutionGeometryNativeNoopHaltFailureCause::Halt(
                        cause,
                    ),
                    index: 1,
                    state,
                })
            })?;
        if halt.outcome() == NativeRegionInvocationOutcome::GuardMiss {
            Ok(ExecutionGeometryNativeNoopHaltOutcome::GuardMiss {
                index: 1,
                state: halt.state().clone(),
            })
        } else {
            Ok(ExecutionGeometryNativeNoopHaltOutcome::Completed(
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
    /// Halt load failure immediately releases the already-ready no-operation.
    /// Failed rollback retains that ready executable without replacing the
    /// primary halt load error.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeNoopHaltPairLoadFailure`] for either
    /// load phase and any retryable partial-load cleanup ownership.
    pub fn load_pair<Adapter>(
        &self,
        adapter: &mut Adapter,
    ) -> GeometryNativeNoopHaltPairLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let no_operation = load_execution_geometry_native_executable(
            adapter,
            self.no_operation.load_image(),
        )
        .map_err(|error| {
            Box::new(
                ExecutionGeometryNativeNoopHaltPairLoadFailure::NoOperation(
                    Box::new(error),
                ),
            )
        })?;
        let halt = match load_execution_geometry_native_executable(
            adapter,
            self.halt.load_image(),
        ) {
            Ok(halt) => halt,
            Err(error) => {
                let no_operation_release_failure =
                    release_execution_geometry_native_executable(
                        adapter,
                        no_operation,
                    )
                    .err()
                    .map(Box::new);
                return Err(Box::new(
                    ExecutionGeometryNativeNoopHaltPairLoadFailure::Halt {
                        error: Box::new(error),
                        no_operation_release_failure,
                    },
                ));
            },
        };
        Ok(LoadedExecutionGeometryNativeNoopHaltSequence {
            halt,
            no_operation,
            sequence: self.clone(),
        })
    }

    /// Admits a no-operation and its exact following halt before native
    /// mapping.
    ///
    /// The no-operation admission normatively replays the entry checkpoint. The
    /// resulting opaque checkpoint is then the sole authority accepted for halt
    /// admission, so profile/geometry/observation/live-in continuity is checked
    /// before either step can map executable memory.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeNoopHaltAdmissionError`] when either
    /// independently verified step cannot bind to its required checkpoint.
    pub fn new(
        evidence: ExecutionGeometryNativeNoopHaltEvidence,
        checkpoint: ProfileMachineState,
    ) -> Result<Self, ExecutionGeometryNativeNoopHaltAdmissionError> {
        let ExecutionGeometryNativeNoopHaltEvidence {
            halt_artifact,
            halt_program,
            no_operation_artifact,
            no_operation_program,
        } = evidence;
        let no_operation = ExecutionGeometryNativeNoOperationAdmission::new(
            no_operation_program,
            checkpoint,
            no_operation_artifact,
        )
        .map_err(ExecutionGeometryNativeNoopHaltAdmissionError::NoOperation)?;
        let halt = ExecutionGeometryNativeInitialHaltAdmission::new(
            halt_program,
            no_operation.expected_state().clone(),
            halt_artifact,
        )
        .map_err(ExecutionGeometryNativeNoopHaltAdmissionError::Halt)?;
        Ok(Self { halt, no_operation })
    }

    /// Returns the admitted first no-operation step.
    #[must_use]
    pub const fn no_operation(
        &self,
    ) -> &ExecutionGeometryNativeNoOperationAdmission {
        &self.no_operation
    }
}

fn pair_release_result<MemoryError>(
    halt_failure: Option<
        Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
    >,
    no_operation_failure: Option<
        Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
    >,
) -> GeometryNativeNoopHaltPairReleaseResult<MemoryError> {
    if halt_failure.is_none() && no_operation_failure.is_none() {
        Ok(())
    } else {
        Err(Box::new(
            ExecutionGeometryNativeNoopHaltPairReleaseFailure {
                halt_failure,
                no_operation_failure,
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

fn no_operation_failure_state<MemoryError, RunnerError>(
    admission: &ExecutionGeometryNativeNoOperationAdmission,
    failure: &ExecutionGeometryNativeNoOperationTransactionFailure<
        MemoryError,
        RunnerError,
    >,
) -> ProfileMachineState {
    match failure {
        ExecutionGeometryNativeNoOperationTransactionFailure::Release {
            completion,
            ..
        } => completion.state().clone(),
        ExecutionGeometryNativeNoOperationTransactionFailure::Binding {
            ..
        }
        | ExecutionGeometryNativeNoOperationTransactionFailure::Execution {
            ..
        }
        | ExecutionGeometryNativeNoOperationTransactionFailure::Load(_)
        | ExecutionGeometryNativeNoOperationTransactionFailure::Preparation(
            _,
        ) => admission.checkpoint().clone(),
    }
}
