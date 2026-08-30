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
    ExecutionGeometryNativeRunner, NativeExecutableMemoryAdapter,
    NativeRegionBuffers, NativeRegionInvocationOutcome,
    VerifiedExecutionGeometryInitialHaltNativeObjectArtifact,
    VerifiedExecutionGeometryNoOperationNativeObjectArtifact,
};
use crate::geometry_native_admission::{
    ExecutionGeometryNativeInitialHaltAdmission,
    ExecutionGeometryNativeInitialHaltAdmissionError,
    ExecutionGeometryNativeInitialHaltTransactionFailure,
};
use crate::geometry_native_no_operation::{
    ExecutionGeometryNativeNoOperationAdmission,
    ExecutionGeometryNativeNoOperationAdmissionError,
    ExecutionGeometryNativeNoOperationTransactionFailure,
};

type VerifiedNoOperationArtifact =
    VerifiedExecutionGeometryNoOperationNativeObjectArtifact;

/// Failure while admitting the exact two-step v5 native sequence.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeNoopHaltAdmissionError {
    /// Final halt could not bind to the normatively replayed no-op checkpoint.
    Halt(ExecutionGeometryNativeInitialHaltAdmissionError),
    /// First no-operation could not bind to the entry checkpoint.
    NoOperation(ExecutionGeometryNativeNoOperationAdmissionError),
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
