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
//   - Ordered transactional composition of initial jump, rotate, and halt v5.
// - Must-Not:
//   - Skip checkpoint continuity, hide committed progress, or invent generic
//   - sequence/cache authority.
// - Allows:
//   - Inputs: exact verified v5 step evidence, checkpoint, adapter, and runner.
//   - Outputs: final checkpoint, indexed guard miss, or indexed failure.
//   - Side effects: supplied executable-memory and runner operations only.
// - Split-When:
//   - Generic explicit-geometry sequence planning has independent proof rules.
// - Merge-When:
//   - A generic sequence preserves identical checkpoint and failure evidence.
// - Summary:
//   - Executes the certified `(&O` jump/rotate/halt path natively.
// - Description:
//   - Chains normative replay authority across all three explicit-geometry
//     steps.
// - Usage:
//   - Construct from exact theorem-derived evidence, then execute
//     transactionally.
// - Defaults:
//   - Guard miss stops before suffix; failure reports last committed
//     checkpoint.
//

//! Three-step explicit-geometry native jump/rotate/halt composition.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{ExecutionGeometryRegionEffectProgram, ProfileMachineState};

use crate::execution_native::{
    ExecutionGeometryNativeRunner, NativeExecutableMemoryAdapter,
    NativeRegionBuffers, NativeRegionInvocationOutcome,
    ReadyExecutionGeometryNativeExecutable,
    VerifiedExecutionGeometryInitialJumpDataNativeObjectArtifact,
};
use crate::geometry_native_initial_jump_data::{
    ExecutionGeometryNativeInitialJumpDataAdmission,
    ExecutionGeometryNativeInitialJumpDataAdmissionError,
    ExecutionGeometryNativeInitialJumpDataBindingError,
    ExecutionGeometryNativeInitialJumpDataCompletion,
    ExecutionGeometryNativeInitialJumpDataExecutionError,
    ExecutionGeometryNativeInitialJumpDataPreparationError,
    ExecutionGeometryNativeInitialJumpDataTransactionFailure,
};
use crate::geometry_native_rotate_sequence::{
    BoundExecutionGeometryNativeRotateHaltSequence,
    ExecutionGeometryNativeRotateHaltAdmissionError,
    ExecutionGeometryNativeRotateHaltEvidence,
    ExecutionGeometryNativeRotateHaltExecutableBindingError,
    ExecutionGeometryNativeRotateHaltFailure,
    ExecutionGeometryNativeRotateHaltLoadedFailure,
    ExecutionGeometryNativeRotateHaltOutcome,
    ExecutionGeometryNativeRotateHaltSequence,
};

type FullAdapterResult<MemoryAdapter, Runner> =
    ExecutionGeometryNativeJumpRotateHaltAdapterResult<MemoryAdapter, Runner>;
type FullAdmissionError = ExecutionGeometryNativeJumpRotateHaltAdmissionError;
type FullBindingError =
    ExecutionGeometryNativeJumpRotateHaltExecutableBindingError;
type FullFailureCause<MemoryError, RunnerError> =
    ExecutionGeometryNativeJumpRotateHaltFailureCause<MemoryError, RunnerError>;
type FullLoadedStepResult<Completion, RunnerError> = Result<
    Completion,
    Box<ExecutionGeometryNativeJumpRotateHaltLoadedFailure<RunnerError>>,
>;

/// Failure while admitting the exact three-step certified v5 path.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeJumpRotateHaltAdmissionError {
    /// Initial aliasing jump could not bind to the entry checkpoint.
    InitialJump(ExecutionGeometryNativeInitialJumpDataAdmissionError),
    /// Rotate/halt suffix could not bind to the jump replay checkpoint.
    Suffix(ExecutionGeometryNativeRotateHaltAdmissionError),
}

/// Failure while prebinding all three synchronized executables.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeJumpRotateHaltExecutableBindingError {
    /// Ready initial-jump image differs from the admitted jump image.
    InitialJump,
    /// Rotate/halt pair differs from the admitted suffix images.
    Suffix(ExecutionGeometryNativeRotateHaltExecutableBindingError),
}

/// Failure cause while executing one prebound three-step sequence.
#[derive(Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeJumpRotateHaltLoadedFailureCause<RunnerError> {
    /// Initial jump unexpectedly failed exact binding.
    InitialJumpBinding(ExecutionGeometryNativeInitialJumpDataBindingError),
    /// Initial jump runner/completion failed.
    InitialJumpExecution(
        Box<ExecutionGeometryNativeInitialJumpDataExecutionError<RunnerError>>,
    ),
    /// Initial jump caller buffers differ from its admitted entry checkpoint.
    InitialJumpPreparation(
        ExecutionGeometryNativeInitialJumpDataPreparationError,
    ),
    /// Rotate/halt suffix failed after any committed jump progress.
    Suffix(Box<ExecutionGeometryNativeRotateHaltLoadedFailure<RunnerError>>),
}

/// Indexed prebound failure retaining the last committed opaque checkpoint.
#[derive(Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeJumpRotateHaltLoadedFailure<RunnerError> {
    cause: ExecutionGeometryNativeJumpRotateHaltLoadedFailureCause<RunnerError>,
    index: usize,
    state: ProfileMachineState,
}

/// Primary transaction failure from one stage of the three-step path.
#[derive(Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeJumpRotateHaltFailureCause<
    MemoryError,
    RunnerError,
> {
    /// Initial jump transaction failed.
    InitialJump(
        Box<
            ExecutionGeometryNativeInitialJumpDataTransactionFailure<
                MemoryError,
                RunnerError,
            >,
        >,
    ),
    /// Rotate/halt suffix transaction failed.
    Suffix(
        Box<ExecutionGeometryNativeRotateHaltFailure<MemoryError, RunnerError>>,
    ),
}

/// Indexed native failure retaining the last committed opaque checkpoint.
#[derive(Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeJumpRotateHaltFailure<
    MemoryError,
    RunnerError,
> {
    cause: ExecutionGeometryNativeJumpRotateHaltFailureCause<
        MemoryError,
        RunnerError,
    >,
    index: usize,
    state: ProfileMachineState,
}

/// Successful or safely suspended three-step v5 execution.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeJumpRotateHaltOutcome {
    /// Jump, rotate, and halt all applied exactly.
    Completed(ProfileMachineState),
    /// A semantic native guard missed before the indexed step could commit.
    GuardMiss {
        /// Zero-based step whose guard missed.
        index: usize,
        /// Last fully committed opaque-geometry checkpoint.
        state: ProfileMachineState,
    },
}

/// Exact verified evidence required by the certified three-step path.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeJumpRotateHaltEvidence {
    initial_jump_artifact:
        VerifiedExecutionGeometryInitialJumpDataNativeObjectArtifact,
    initial_jump_program: ExecutionGeometryRegionEffectProgram,
    suffix: ExecutionGeometryNativeRotateHaltEvidence,
}

/// Three independently admitted v5 steps sharing one checkpoint authority line.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeJumpRotateHaltSequence {
    initial_jump: ExecutionGeometryNativeInitialJumpDataAdmission,
    suffix: ExecutionGeometryNativeRotateHaltSequence,
}

/// Three exact synchronized executables prebound before caller mutation.
#[derive(Debug)]
pub struct BoundExecutionGeometryNativeJumpRotateHaltSequence<
    'sequence,
    'executable,
> {
    initial_jump: &'executable ReadyExecutionGeometryNativeExecutable,
    sequence: &'sequence ExecutionGeometryNativeJumpRotateHaltSequence,
    suffix:
        BoundExecutionGeometryNativeRotateHaltSequence<'sequence, 'executable>,
}

/// Result of executing one exact prebound geometry-native triple.
pub type ExecutionGeometryNativeJumpRotateHaltLoadedResult<RunnerError> =
    Result<
        ExecutionGeometryNativeJumpRotateHaltOutcome,
        Box<ExecutionGeometryNativeJumpRotateHaltLoadedFailure<RunnerError>>,
    >;

/// Result of one concrete adapter/runner three-step transaction.
pub type ExecutionGeometryNativeJumpRotateHaltAdapterResult<
    MemoryAdapter,
    Runner,
> = Result<
    ExecutionGeometryNativeJumpRotateHaltOutcome,
    Box<
        ExecutionGeometryNativeJumpRotateHaltFailure<
            <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
            <Runner as ExecutionGeometryNativeRunner>::Error,
        >,
    >,
>;

impl Display for ExecutionGeometryNativeJumpRotateHaltAdmissionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::InitialJump(error) => {
                write!(f, "v5 full path initial-jump admission: {error}")
            },
            Self::Suffix(error) => {
                write!(f, "v5 full path suffix admission: {error}")
            },
        }
    }
}

impl Display for ExecutionGeometryNativeJumpRotateHaltExecutableBindingError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::InitialJump => {
                f.write_str("v5 full path initial-jump executable differs")
            },
            Self::Suffix(error) => Display::fmt(error, f),
        }
    }
}

impl<MemoryError: Display, RunnerError: Display> Display
    for ExecutionGeometryNativeJumpRotateHaltFailure<MemoryError, RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match &self.cause {
            FullFailureCause::InitialJump(error) => write!(
                f,
                "v5 full path step {} jump failed: {error}",
                self.index
            ),
            FullFailureCause::Suffix(error) => {
                write!(
                    f,
                    "v5 full path step {} suffix failed: {error}",
                    self.index
                )
            },
        }
    }
}

impl<RunnerError: Display> Display
    for ExecutionGeometryNativeJumpRotateHaltLoadedFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        use ExecutionGeometryNativeJumpRotateHaltLoadedFailureCause as Cause;

        write!(f, "v5 prebound full path step {} failed: ", self.index)?;
        match &self.cause {
            Cause::InitialJumpBinding(error) => Display::fmt(error, f),
            Cause::InitialJumpExecution(error) => Display::fmt(error, f),
            Cause::InitialJumpPreparation(error) => Display::fmt(error, f),
            Cause::Suffix(error) => Display::fmt(error, f),
        }
    }
}

impl ExecutionGeometryNativeJumpRotateHaltEvidence {
    /// Groups exact initial-jump evidence with exact rotate/halt suffix
    /// evidence.
    #[must_use]
    pub const fn new(
        initial_jump_program: ExecutionGeometryRegionEffectProgram,
        initial_jump_artifact:
            VerifiedExecutionGeometryInitialJumpDataNativeObjectArtifact,
        suffix: ExecutionGeometryNativeRotateHaltEvidence,
    ) -> Self {
        Self {
            initial_jump_artifact,
            initial_jump_program,
            suffix,
        }
    }
}

impl<MemoryError, RunnerError>
    ExecutionGeometryNativeJumpRotateHaltFailure<MemoryError, RunnerError>
{
    /// Returns the exact stage failure.
    #[must_use]
    pub const fn cause(
        &self,
    ) -> &ExecutionGeometryNativeJumpRotateHaltFailureCause<
        MemoryError,
        RunnerError,
    > {
        &self.cause
    }

    /// Returns the zero-based failing step in jump/rotate/halt order.
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

impl<RunnerError>
    ExecutionGeometryNativeJumpRotateHaltLoadedFailure<RunnerError>
{
    /// Returns the exact prebound stage failure.
    #[must_use]
    pub const fn cause(
        &self,
    ) -> &ExecutionGeometryNativeJumpRotateHaltLoadedFailureCause<RunnerError>
    {
        &self.cause
    }

    /// Returns the zero-based failing step in jump/rotate/halt order.
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

impl ExecutionGeometryNativeJumpRotateHaltOutcome {
    /// Returns the completed or last committed opaque-geometry checkpoint.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        match self {
            Self::Completed(state) | Self::GuardMiss { state, .. } => state,
        }
    }
}

impl BoundExecutionGeometryNativeJumpRotateHaltSequence<'_, '_> {
    /// Executes the prebound triple without executable-memory adapter work.
    ///
    /// # Errors
    ///
    /// Returns indexed preparation, binding, runner, or suffix failure while
    /// retaining every earlier committed checkpoint.
    pub fn execute<Runner>(
        &self,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> ExecutionGeometryNativeJumpRotateHaltLoadedResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        use ExecutionGeometryNativeJumpRotateHaltLoadedFailureCause as Cause;

        let (memory, input, output) = buffers.into_parts();
        let jump = self.execute_initial_jump(
            runner,
            NativeRegionBuffers::new(&mut *memory, input, &mut *output),
        )?;
        if jump.outcome() == NativeRegionInvocationOutcome::GuardMiss {
            return Ok(
                ExecutionGeometryNativeJumpRotateHaltOutcome::GuardMiss {
                    index: 0,
                    state: jump.state().clone(),
                },
            );
        }
        let suffix = self
            .suffix
            .execute(
                runner,
                NativeRegionBuffers::new(&mut *memory, input, &mut *output),
            )
            .map_err(|cause| {
                let index = cause.index().saturating_add(1);
                let state = cause.state().clone();
                Box::new(ExecutionGeometryNativeJumpRotateHaltLoadedFailure {
                    cause: Cause::Suffix(cause),
                    index,
                    state,
                })
            })?;
        Ok(match suffix {
            ExecutionGeometryNativeRotateHaltOutcome::Completed(state) => {
                ExecutionGeometryNativeJumpRotateHaltOutcome::Completed(state)
            },
            ExecutionGeometryNativeRotateHaltOutcome::GuardMiss {
                index,
                state,
            } => ExecutionGeometryNativeJumpRotateHaltOutcome::GuardMiss {
                index: index.saturating_add(1),
                state,
            },
        })
    }

    fn execute_initial_jump<Runner>(
        &self,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> FullLoadedStepResult<
        ExecutionGeometryNativeInitialJumpDataCompletion,
        Runner::Error,
    >
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        use ExecutionGeometryNativeJumpRotateHaltLoadedFailureCause as Cause;

        let checkpoint = self.sequence.initial_jump.checkpoint();
        let prepared =
            self.sequence
                .initial_jump
                .prepare(buffers)
                .map_err(|error| {
                    Box::new(
                        ExecutionGeometryNativeJumpRotateHaltLoadedFailure {
                            cause: Cause::InitialJumpPreparation(error),
                            index: 0,
                            state: checkpoint.clone(),
                        },
                    )
                })?;
        let bound =
            prepared
                .bind_executable(self.initial_jump)
                .map_err(|error| {
                    Box::new(
                        ExecutionGeometryNativeJumpRotateHaltLoadedFailure {
                            cause: Cause::InitialJumpBinding(error),
                            index: 0,
                            state: checkpoint.clone(),
                        },
                    )
                })?;
        bound.execute(runner).map_err(|error| {
            Box::new(ExecutionGeometryNativeJumpRotateHaltLoadedFailure {
                cause: Cause::InitialJumpExecution(error),
                index: 0,
                state: checkpoint.clone(),
            })
        })
    }
}

impl ExecutionGeometryNativeJumpRotateHaltSequence {
    /// Prebinds all three ready executables before caller-state mutation.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeJumpRotateHaltExecutableBindingError`]
    /// when any synchronized image differs from its admitted step.
    pub fn bind_executables<'sequence, 'executable>(
        &'sequence self,
        initial_jump: &'executable ReadyExecutionGeometryNativeExecutable,
        rotate: &'executable ReadyExecutionGeometryNativeExecutable,
        halt: &'executable ReadyExecutionGeometryNativeExecutable,
    ) -> Result<
        BoundExecutionGeometryNativeJumpRotateHaltSequence<
            'sequence,
            'executable,
        >,
        ExecutionGeometryNativeJumpRotateHaltExecutableBindingError,
    > {
        if self.initial_jump.load_image() != initial_jump.image() {
            return Err(FullBindingError::InitialJump);
        }
        let suffix = self
            .suffix
            .bind_executables(rotate, halt)
            .map_err(FullBindingError::Suffix)?;
        Ok(BoundExecutionGeometryNativeJumpRotateHaltSequence {
            initial_jump,
            sequence: self,
            suffix,
        })
    }

    /// Executes the exact certified jump/rotate/halt path transactionally.
    ///
    /// Every step retains its own load/call/release ownership. Guard miss stops
    /// before later steps and a failure after committed progress reports the
    /// last normative checkpoint.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeJumpRotateHaltFailure`] with the exact
    /// three-step index, primary transaction failure, and committed state.
    pub fn execute_transactionally<MemoryAdapter, Runner>(
        &self,
        memory_adapter: &mut MemoryAdapter,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> FullAdapterResult<MemoryAdapter, Runner>
    where
        MemoryAdapter: NativeExecutableMemoryAdapter,
        Runner: ExecutionGeometryNativeRunner,
    {
        let (memory, input, output) = buffers.into_parts();
        let jump = self
            .initial_jump
            .execute_transactionally(
                memory_adapter,
                runner,
                NativeRegionBuffers::new(&mut *memory, input, &mut *output),
            )
            .map_err(|cause| {
                let state = jump_failure_state(&self.initial_jump, &cause);
                Box::new(ExecutionGeometryNativeJumpRotateHaltFailure {
                    cause: FullFailureCause::InitialJump(cause),
                    index: 0,
                    state,
                })
            })?;
        if jump.outcome() == NativeRegionInvocationOutcome::GuardMiss {
            return Ok(
                ExecutionGeometryNativeJumpRotateHaltOutcome::GuardMiss {
                    index: 0,
                    state: jump.state().clone(),
                },
            );
        }
        let suffix = self
            .suffix
            .execute_transactionally(
                memory_adapter,
                runner,
                NativeRegionBuffers::new(&mut *memory, input, &mut *output),
            )
            .map_err(|cause| {
                let index = cause.index().saturating_add(1);
                let state = cause.state().clone();
                Box::new(ExecutionGeometryNativeJumpRotateHaltFailure {
                    cause: FullFailureCause::Suffix(cause),
                    index,
                    state,
                })
            })?;
        Ok(match suffix {
            ExecutionGeometryNativeRotateHaltOutcome::Completed(state) => {
                ExecutionGeometryNativeJumpRotateHaltOutcome::Completed(state)
            },
            ExecutionGeometryNativeRotateHaltOutcome::GuardMiss {
                index,
                state,
            } => ExecutionGeometryNativeJumpRotateHaltOutcome::GuardMiss {
                index: index.saturating_add(1),
                state,
            },
        })
    }

    /// Returns the admitted aliasing initial jump step.
    #[must_use]
    pub const fn initial_jump(
        &self,
    ) -> &ExecutionGeometryNativeInitialJumpDataAdmission {
        &self.initial_jump
    }

    /// Admits all three certified steps before any executable memory can map.
    ///
    /// Initial jump is replayed first. Its opaque exit checkpoint becomes the
    /// sole entry authority for rotate admission, whose replayed exit in turn
    /// becomes the sole halt authority inside the suffix.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeJumpRotateHaltAdmissionError`] when any
    /// step cannot bind to its required normative checkpoint.
    pub fn new(
        evidence: ExecutionGeometryNativeJumpRotateHaltEvidence,
        checkpoint: ProfileMachineState,
    ) -> Result<Self, ExecutionGeometryNativeJumpRotateHaltAdmissionError> {
        let ExecutionGeometryNativeJumpRotateHaltEvidence {
            initial_jump_artifact,
            initial_jump_program,
            suffix,
        } = evidence;
        let initial_jump =
            ExecutionGeometryNativeInitialJumpDataAdmission::new(
                initial_jump_program,
                checkpoint,
                initial_jump_artifact,
            )
            .map_err(FullAdmissionError::InitialJump)?;
        let admitted_suffix = ExecutionGeometryNativeRotateHaltSequence::new(
            suffix,
            initial_jump.expected_state().clone(),
        )
        .map_err(FullAdmissionError::Suffix)?;
        Ok(Self {
            initial_jump,
            suffix: admitted_suffix,
        })
    }

    /// Returns the admitted rotate/halt suffix.
    #[must_use]
    pub const fn suffix(&self) -> &ExecutionGeometryNativeRotateHaltSequence {
        &self.suffix
    }
}

fn jump_failure_state<MemoryError, RunnerError>(
    admission: &ExecutionGeometryNativeInitialJumpDataAdmission,
    failure: &ExecutionGeometryNativeInitialJumpDataTransactionFailure<
        MemoryError,
        RunnerError,
    >,
) -> ProfileMachineState {
    match failure {
        ExecutionGeometryNativeInitialJumpDataTransactionFailure::Release {
            completion,
            ..
        } => completion.state().clone(),
        ExecutionGeometryNativeInitialJumpDataTransactionFailure::Binding {
            ..
        }
        | ExecutionGeometryNativeInitialJumpDataTransactionFailure::Execution {
            ..
        }
        | ExecutionGeometryNativeInitialJumpDataTransactionFailure::Load(_)
        | ExecutionGeometryNativeInitialJumpDataTransactionFailure::Preparation(
            _,
        ) => admission.checkpoint().clone(),
    }
}
