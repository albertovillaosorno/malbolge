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
//   - Transactional theorem composition of `j * p p p p v` under one explicit
//     geometry authority line.
// - Must-Not:
//   - Generalize step count, skip checkpoint continuity, preload mappings, or
//     translate specialized per-step failure ownership.
// - Allows:
//   - Inputs: exact jump, rotate, crazy-prefix/halt evidence, entry checkpoint,
//     adapter, runner, and caller buffers.
//   - Outputs: exact terminal checkpoint, indexed guard miss, or indexed
//     failure.
//   - Side effects: delegated per-step executable mapping, runner, and release.
// - Split-When:
//   - Preloaded seven-mapping ownership or generic sequence planning gains
//     independent lifecycle authority.
// - Merge-When:
//   - A generic geometry-native sequence preserves this exact theorem evidence.
// - Summary:
//   - Executes certified `(&<;:9K` as seven checkpoint-bound native steps.
// - Description:
//   - Chains jump and rotate replay into the fixed `p p p p v` suffix.
// - Usage:
//   - Admit exact theorem evidence, then execute transactionally from entry.
// - Defaults:
//   - Guard/failure index is global across all seven theorem steps.
//

//! Seven-step explicit-geometry jump/rotate/crazy/halt composition.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{ExecutionGeometryRegionEffectProgram, ProfileMachineState};

use crate::execution_native::{
    ExecutionGeometryNativeRunner, NativeExecutableMemoryAdapter,
    NativeRegionBuffers, NativeRegionInvocationOutcome,
    ReadyExecutionGeometryNativeExecutable,
    VerifiedExecutionGeometryInitialJumpDataNativeObjectArtifact,
    VerifiedExecutionGeometryRotateNativeObjectArtifact,
};
use crate::geometry_native_crazy_prefix_halt_sequence::{
    EXECUTION_GEOMETRY_NATIVE_CRAZY_PREFIX_HALT_STEPS,
    ExecutionGeometryNativeCrazyPrefixHaltAdmissionFailure,
    ExecutionGeometryNativeCrazyPrefixHaltEvidence,
    ExecutionGeometryNativeCrazyPrefixHaltFailure,
    ExecutionGeometryNativeCrazyPrefixHaltOutcome,
    ExecutionGeometryNativeCrazyPrefixHaltSequence,
};
use crate::geometry_native_initial_jump_data::{
    ExecutionGeometryNativeInitialJumpDataAdmission,
    ExecutionGeometryNativeInitialJumpDataAdmissionError,
    ExecutionGeometryNativeInitialJumpDataTransactionFailure,
};
use crate::geometry_native_rotate::{
    ExecutionGeometryNativeRotateAdmission,
    ExecutionGeometryNativeRotateAdmissionError,
    ExecutionGeometryNativeRotateTransactionFailure,
};

/// Total theorem steps in `j * p p p p v`.
pub const EXECUTION_GEOMETRY_NATIVE_JUMP_ROTATE_CRAZY_HALT_STEPS: usize =
    EXECUTION_GEOMETRY_NATIVE_CRAZY_PREFIX_HALT_STEPS + 2;

type FullAdmissionFailure =
    ExecutionGeometryNativeJumpRotateCrazyHaltAdmissionFailure;
type FullAdmissionResult = Result<
    ExecutionGeometryNativeJumpRotateCrazyHaltSequence,
    Box<ExecutionGeometryNativeJumpRotateCrazyHaltAdmissionFailure>,
>;
type FullBindingError =
    ExecutionGeometryNativeJumpRotateCrazyHaltExecutableBindingError;
type FullFailureBox<MemoryError, RunnerError> = Box<
    ExecutionGeometryNativeJumpRotateCrazyHaltFailure<MemoryError, RunnerError>,
>;
type JumpTransactionFailure<MemoryError, RunnerError> =
    ExecutionGeometryNativeInitialJumpDataTransactionFailure<
        MemoryError,
        RunnerError,
    >;
type RotateTransactionFailure<MemoryError, RunnerError> =
    ExecutionGeometryNativeRotateTransactionFailure<MemoryError, RunnerError>;

/// Exact theorem evidence for the leading jump and rotate steps.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeJumpRotateCrazyHaltPrefixEvidence {
    initial_jump_artifact:
        VerifiedExecutionGeometryInitialJumpDataNativeObjectArtifact,
    initial_jump_program: ExecutionGeometryRegionEffectProgram,
    rotate_artifact: VerifiedExecutionGeometryRotateNativeObjectArtifact,
    rotate_program: ExecutionGeometryRegionEffectProgram,
}

/// Exact theorem evidence for jump, rotate, then fixed crazy-prefix/halt
/// suffix.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeJumpRotateCrazyHaltEvidence {
    prefix: ExecutionGeometryNativeJumpRotateCrazyHaltPrefixEvidence,
    suffix: ExecutionGeometryNativeCrazyPrefixHaltEvidence,
}

/// Failure while admitting the exact seven-step theorem path before mapping.
#[derive(Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeJumpRotateCrazyHaltAdmissionFailure {
    /// Initial jump rejected the theorem entry checkpoint.
    InitialJump(ExecutionGeometryNativeInitialJumpDataAdmissionError),
    /// Rotate rejected the normatively replayed jump checkpoint.
    Rotate(ExecutionGeometryNativeRotateAdmissionError),
    /// Crazy-prefix/halt suffix rejected the normatively replayed rotate exit.
    Suffix(Box<ExecutionGeometryNativeCrazyPrefixHaltAdmissionFailure>),
}

/// Failure while prebinding all seven synchronized theorem executables.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeJumpRotateCrazyHaltExecutableBindingError {
    /// One crazy image differs at its fixed zero-based prefix index.
    Crazy {
        /// Zero-based crazy index within the four-step theorem prefix.
        index: usize,
    },
    /// Final halt image differs from the admitted halt image.
    Halt,
    /// Initial jump image differs from the admitted theorem entry step.
    InitialJump,
    /// Rotate image differs from the admitted replayed rotate step.
    Rotate,
}

/// Primary execution failure retaining exact specialized cleanup ownership.
#[derive(Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeJumpRotateCrazyHaltFailureCause<
    MemoryError,
    RunnerError,
> {
    /// Initial jump transaction failed.
    InitialJump(Box<JumpTransactionFailure<MemoryError, RunnerError>>),
    /// Rotate transaction failed after jump committed.
    Rotate(Box<RotateTransactionFailure<MemoryError, RunnerError>>),
    /// Fixed crazy-prefix/halt suffix failed after rotate committed.
    Suffix(
        Box<
            ExecutionGeometryNativeCrazyPrefixHaltFailure<
                MemoryError,
                RunnerError,
            >,
        >,
    ),
}

/// Indexed theorem failure retaining the last committed opaque checkpoint.
#[derive(Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeJumpRotateCrazyHaltFailure<
    MemoryError,
    RunnerError,
> {
    cause: ExecutionGeometryNativeJumpRotateCrazyHaltFailureCause<
        MemoryError,
        RunnerError,
    >,
    index: usize,
    state: ProfileMachineState,
}

/// Successful or safely suspended execution of exact `j * p p p p v`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeJumpRotateCrazyHaltOutcome {
    /// All seven theorem steps applied exactly.
    Completed(ProfileMachineState),
    /// A semantic guard missed before the indexed step could commit.
    GuardMiss {
        /// Zero-based index in `j * p p p p v`.
        index: usize,
        /// Last fully committed opaque-geometry checkpoint.
        state: ProfileMachineState,
    },
}

/// Seven synchronized ready executables supplied for exact prebinding.
#[derive(Clone, Copy, Debug)]
pub struct ExecutionGeometryNativeJumpRotateCrazyHaltExecutables<'executable> {
    crazy: [&'executable ReadyExecutionGeometryNativeExecutable; 4],
    halt: &'executable ReadyExecutionGeometryNativeExecutable,
    initial_jump: &'executable ReadyExecutionGeometryNativeExecutable,
    rotate: &'executable ReadyExecutionGeometryNativeExecutable,
}

/// Seven ready executables prebound to one exact theorem sequence.
#[derive(Debug)]
pub struct BoundExecutionGeometryNativeJumpRotateCrazyHaltSequence<
    'sequence,
    'executable,
> {
    executables:
        ExecutionGeometryNativeJumpRotateCrazyHaltExecutables<'executable>,
    sequence: &'sequence ExecutionGeometryNativeJumpRotateCrazyHaltSequence,
}

/// Exact seven-step theorem path admitted under one checkpoint authority line.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeJumpRotateCrazyHaltSequence {
    initial_jump: ExecutionGeometryNativeInitialJumpDataAdmission,
    rotate: ExecutionGeometryNativeRotateAdmission,
    suffix: ExecutionGeometryNativeCrazyPrefixHaltSequence,
}

/// Complete transaction result for concrete adapter ports.
pub type ExecutionGeometryNativeJumpRotateCrazyHaltAdapterResult<
    MemoryAdapter,
    Runner,
> = ExecutionGeometryNativeJumpRotateCrazyHaltResult<
    <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
    <Runner as ExecutionGeometryNativeRunner>::Error,
>;

/// Complete transaction result for the seven-step theorem path.
pub type ExecutionGeometryNativeJumpRotateCrazyHaltResult<
    MemoryError,
    RunnerError,
> = Result<
    ExecutionGeometryNativeJumpRotateCrazyHaltOutcome,
    FullFailureBox<MemoryError, RunnerError>,
>;

impl Display for ExecutionGeometryNativeJumpRotateCrazyHaltAdmissionFailure {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::InitialJump(error) => {
                write!(f, "v5 full crazy path jump admission: {error}")
            },
            Self::Rotate(error) => {
                write!(f, "v5 full crazy path rotate admission: {error}")
            },
            Self::Suffix(error) => Display::fmt(error, f),
        }
    }
}

impl Display
    for ExecutionGeometryNativeJumpRotateCrazyHaltExecutableBindingError
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Crazy { index } => {
                write!(
                    f,
                    "v5 full crazy path crazy executable differs at {index}"
                )
            },
            Self::Halt => {
                f.write_str("v5 full crazy path halt executable differs")
            },
            Self::InitialJump => f.write_str(
                "v5 full crazy path initial-jump executable differs",
            ),
            Self::Rotate => {
                f.write_str("v5 full crazy path rotate executable differs")
            },
        }
    }
}

impl<MemoryError: Display, RunnerError: Display> Display
    for ExecutionGeometryNativeJumpRotateCrazyHaltFailure<
        MemoryError,
        RunnerError,
    >
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "v5 full crazy path failed at {}: ", self.index)?;
        match &self.cause {
            ExecutionGeometryNativeJumpRotateCrazyHaltFailureCause::InitialJump(
                error,
            ) => Display::fmt(error, f),
            ExecutionGeometryNativeJumpRotateCrazyHaltFailureCause::Rotate(
                error,
            ) => Display::fmt(error, f),
            ExecutionGeometryNativeJumpRotateCrazyHaltFailureCause::Suffix(
                error,
            ) => Display::fmt(error, f),
        }
    }
}

impl ExecutionGeometryNativeJumpRotateCrazyHaltEvidence {
    /// Retains exact leading and suffix theorem evidence.
    #[must_use]
    pub const fn new(
        prefix: ExecutionGeometryNativeJumpRotateCrazyHaltPrefixEvidence,
        suffix: ExecutionGeometryNativeCrazyPrefixHaltEvidence,
    ) -> Self {
        Self { prefix, suffix }
    }
}

impl ExecutionGeometryNativeJumpRotateCrazyHaltPrefixEvidence {
    /// Retains exact initial-jump and rotate evidence in theorem order.
    #[must_use]
    pub const fn new(
        initial_jump_program: ExecutionGeometryRegionEffectProgram,
        initial_jump_artifact:
            VerifiedExecutionGeometryInitialJumpDataNativeObjectArtifact,
        rotate_program: ExecutionGeometryRegionEffectProgram,
        rotate_artifact: VerifiedExecutionGeometryRotateNativeObjectArtifact,
    ) -> Self {
        Self {
            initial_jump_artifact,
            initial_jump_program,
            rotate_artifact,
            rotate_program,
        }
    }
}

impl<'executable>
    ExecutionGeometryNativeJumpRotateCrazyHaltExecutables<'executable>
{
    /// Retains borrowed ready mappings in theorem execution order.
    #[must_use]
    pub const fn new(
        initial_jump: &'executable ReadyExecutionGeometryNativeExecutable,
        rotate: &'executable ReadyExecutionGeometryNativeExecutable,
        crazy: [&'executable ReadyExecutionGeometryNativeExecutable; 4],
        halt: &'executable ReadyExecutionGeometryNativeExecutable,
    ) -> Self {
        Self {
            crazy,
            halt,
            initial_jump,
            rotate,
        }
    }
}

impl<MemoryError, RunnerError>
    ExecutionGeometryNativeJumpRotateCrazyHaltFailure<MemoryError, RunnerError>
{
    /// Borrows the specialized stage failure and exact cleanup ownership.
    #[must_use]
    pub const fn cause(
        &self,
    ) -> &ExecutionGeometryNativeJumpRotateCrazyHaltFailureCause<
        MemoryError,
        RunnerError,
    > {
        &self.cause
    }

    /// Returns the zero-based theorem step that failed.
    #[must_use]
    pub const fn index(&self) -> usize {
        self.index
    }

    /// Consumes the wrapper and returns exact specialized failure ownership.
    #[must_use]
    pub fn into_cause(
        self,
    ) -> ExecutionGeometryNativeJumpRotateCrazyHaltFailureCause<
        MemoryError,
        RunnerError,
    > {
        self.cause
    }

    /// Returns the last committed opaque-geometry checkpoint.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        &self.state
    }
}

impl ExecutionGeometryNativeJumpRotateCrazyHaltOutcome {
    /// Returns the final or last committed opaque-geometry checkpoint.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        match self {
            Self::Completed(state) | Self::GuardMiss { state, .. } => state,
        }
    }
}

impl BoundExecutionGeometryNativeJumpRotateCrazyHaltSequence<'_, '_> {
    /// Returns the exact borrowed ready-set validated by this prebinding.
    #[must_use]
    pub const fn executables(
        &self,
    ) -> ExecutionGeometryNativeJumpRotateCrazyHaltExecutables<'_> {
        self.executables
    }

    /// Returns the exact theorem sequence validated by this prebinding.
    #[must_use]
    pub const fn sequence(
        &self,
    ) -> &ExecutionGeometryNativeJumpRotateCrazyHaltSequence {
        self.sequence
    }
}

impl ExecutionGeometryNativeJumpRotateCrazyHaltSequence {
    /// Prebinds all seven ready executables before any caller-state mutation.
    ///
    /// # Errors
    ///
    /// Returns exact stage/index identity for the first image mismatch.
    pub fn bind_executables<'sequence, 'executable>(
        &'sequence self,
        executables: ExecutionGeometryNativeJumpRotateCrazyHaltExecutables<
            'executable,
        >,
    ) -> Result<
        BoundExecutionGeometryNativeJumpRotateCrazyHaltSequence<
            'sequence,
            'executable,
        >,
        ExecutionGeometryNativeJumpRotateCrazyHaltExecutableBindingError,
    > {
        use FullBindingError as Error;

        if self.initial_jump.load_image() != executables.initial_jump.image() {
            return Err(Error::InitialJump);
        }
        if self.rotate.load_image() != executables.rotate.image() {
            return Err(Error::Rotate);
        }
        for (index, (admission, ready)) in self
            .suffix
            .prefix()
            .steps()
            .iter()
            .zip(executables.crazy.iter())
            .enumerate()
        {
            if admission.load_image() != ready.image() {
                return Err(Error::Crazy { index });
            }
        }
        if self.suffix.halt().load_image() != executables.halt.image() {
            return Err(Error::Halt);
        }
        Ok(BoundExecutionGeometryNativeJumpRotateCrazyHaltSequence {
            executables,
            sequence: self,
        })
    }

    fn execute_suffix<MemoryAdapter, Runner>(
        &self,
        memory_adapter: &mut MemoryAdapter,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> ExecutionGeometryNativeJumpRotateCrazyHaltAdapterResult<
        MemoryAdapter,
        Runner,
    >
    where
        MemoryAdapter: NativeExecutableMemoryAdapter,
        Runner: ExecutionGeometryNativeRunner,
    {
        use ExecutionGeometryNativeJumpRotateCrazyHaltOutcome as Outcome;

        let suffix_outcome = self
            .suffix
            .execute_transactionally(memory_adapter, runner, buffers)
            .map_err(map_suffix_failure)?;
        match suffix_outcome {
            ExecutionGeometryNativeCrazyPrefixHaltOutcome::Completed(state) => {
                Ok(Outcome::Completed(state))
            },
            ExecutionGeometryNativeCrazyPrefixHaltOutcome::GuardMiss {
                index,
                state,
            } => Ok(Outcome::GuardMiss {
                index: index.saturating_add(2),
                state,
            }),
        }
    }

    /// Executes exact `j * p p p p v` transactionally in theorem order.
    ///
    /// # Errors
    ///
    /// Returns global index, last committed state, and specialized cleanup
    /// ownership for the failing jump, rotate, or fixed suffix transaction.
    pub fn execute_transactionally<MemoryAdapter, Runner>(
        &self,
        memory_adapter: &mut MemoryAdapter,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> ExecutionGeometryNativeJumpRotateCrazyHaltAdapterResult<
        MemoryAdapter,
        Runner,
    >
    where
        MemoryAdapter: NativeExecutableMemoryAdapter,
        Runner: ExecutionGeometryNativeRunner,
    {
        use ExecutionGeometryNativeJumpRotateCrazyHaltFailureCause as Cause;
        use ExecutionGeometryNativeJumpRotateCrazyHaltOutcome as Outcome;

        let (memory, input, output) = buffers.into_parts();
        let entry = self.initial_jump.checkpoint().clone();
        let jump_result = self.initial_jump.execute_transactionally(
            memory_adapter,
            runner,
            NativeRegionBuffers::new(&mut *memory, input, &mut *output),
        );
        let jump_completion = jump_result.map_err(|cause| {
            let state = jump_failure_state(&entry, &cause);
            Box::new(ExecutionGeometryNativeJumpRotateCrazyHaltFailure {
                cause: Cause::InitialJump(cause),
                index: 0,
                state,
            })
        })?;
        let jump_state = jump_completion.state().clone();
        if jump_completion.outcome() == NativeRegionInvocationOutcome::GuardMiss
        {
            return Ok(Outcome::GuardMiss {
                index: 0,
                state: jump_state,
            });
        }

        let rotate_result = self.rotate.execute_transactionally(
            memory_adapter,
            runner,
            NativeRegionBuffers::new(&mut *memory, input, &mut *output),
        );
        let rotate_completion = rotate_result.map_err(|cause| {
            let state = rotate_failure_state(&jump_state, &cause);
            Box::new(ExecutionGeometryNativeJumpRotateCrazyHaltFailure {
                cause: Cause::Rotate(cause),
                index: 1,
                state,
            })
        })?;
        let rotate_state = rotate_completion.state().clone();
        if rotate_completion.outcome()
            == NativeRegionInvocationOutcome::GuardMiss
        {
            return Ok(Outcome::GuardMiss {
                index: 1,
                state: rotate_state,
            });
        }

        self.execute_suffix(
            memory_adapter,
            runner,
            NativeRegionBuffers::new(&mut *memory, input, &mut *output),
        )
    }

    /// Returns the exact theorem entry admission.
    #[must_use]
    pub const fn initial_jump(
        &self,
    ) -> &ExecutionGeometryNativeInitialJumpDataAdmission {
        &self.initial_jump
    }

    /// Admits jump, rotate, then fixed crazy-prefix/halt from replayed exits.
    ///
    /// # Errors
    ///
    /// Returns specialized admission failure before any executable mapping.
    pub fn new(
        evidence: ExecutionGeometryNativeJumpRotateCrazyHaltEvidence,
        checkpoint: ProfileMachineState,
    ) -> FullAdmissionResult {
        use FullAdmissionFailure as Failure;

        let prefix = evidence.prefix;
        let initial_jump =
            ExecutionGeometryNativeInitialJumpDataAdmission::new(
                prefix.initial_jump_program,
                checkpoint,
                prefix.initial_jump_artifact,
            )
            .map_err(|error| Box::new(Failure::InitialJump(error)))?;
        let rotate = ExecutionGeometryNativeRotateAdmission::new(
            prefix.rotate_program,
            initial_jump.expected_state().clone(),
            prefix.rotate_artifact,
        )
        .map_err(|error| Box::new(Failure::Rotate(error)))?;
        let suffix = ExecutionGeometryNativeCrazyPrefixHaltSequence::new(
            evidence.suffix,
            rotate.expected_state().clone(),
        )
        .map_err(|error| Box::new(Failure::Suffix(error)))?;
        Ok(Self {
            initial_jump,
            rotate,
            suffix,
        })
    }

    /// Returns the rotate admitted only from the initial jump's replayed exit.
    #[must_use]
    pub const fn rotate(&self) -> &ExecutionGeometryNativeRotateAdmission {
        &self.rotate
    }

    /// Returns the fixed `p p p p v` suffix admitted from rotate's replayed
    /// exit.
    #[must_use]
    pub const fn suffix(
        &self,
    ) -> &ExecutionGeometryNativeCrazyPrefixHaltSequence {
        &self.suffix
    }
}

fn jump_failure_state<MemoryError, RunnerError>(
    prior_state: &ProfileMachineState,
    failure: &JumpTransactionFailure<MemoryError, RunnerError>,
) -> ProfileMachineState {
    match failure {
        JumpTransactionFailure::Release { completion, .. } => {
            completion.state().clone()
        },
        JumpTransactionFailure::Binding { .. }
        | JumpTransactionFailure::Execution { .. }
        | JumpTransactionFailure::Load(_)
        | JumpTransactionFailure::Preparation(_) => prior_state.clone(),
    }
}

fn map_suffix_failure<MemoryError, RunnerError>(
    failure: Box<
        ExecutionGeometryNativeCrazyPrefixHaltFailure<MemoryError, RunnerError>,
    >,
) -> FullFailureBox<MemoryError, RunnerError> {
    let index = failure.index().saturating_add(2);
    let state = failure.state().clone();
    Box::new(ExecutionGeometryNativeJumpRotateCrazyHaltFailure {
        cause: ExecutionGeometryNativeJumpRotateCrazyHaltFailureCause::Suffix(
            failure,
        ),
        index,
        state,
    })
}

fn rotate_failure_state<MemoryError, RunnerError>(
    prior_state: &ProfileMachineState,
    failure: &RotateTransactionFailure<MemoryError, RunnerError>,
) -> ProfileMachineState {
    match failure {
        RotateTransactionFailure::Release { completion, .. } => {
            completion.state().clone()
        },
        RotateTransactionFailure::Binding { .. }
        | RotateTransactionFailure::Execution { .. }
        | RotateTransactionFailure::Load(_)
        | RotateTransactionFailure::Preparation(_) => prior_state.clone(),
    }
}
