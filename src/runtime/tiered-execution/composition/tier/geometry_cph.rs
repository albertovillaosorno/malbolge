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
//   - Transactional composition of the theorem-derived four-crazy prefix and
//     its immediately reached halt.
// - Must-Not:
//   - Generalize prefix length, skip checkpoint continuity, preload mappings,
//     or include the preceding jump/rotate steps.
// - Allows:
//   - Inputs: exact crazy-prefix/halt evidence, post-rotate checkpoint,
//     adapter, runner, and caller buffers.
//   - Outputs: final halt checkpoint, indexed guard miss, or indexed failure.
//   - Side effects: delegated per-step executable mapping, runner, and release.
// - Split-When:
//   - Reusable five-mapping ownership or the preceding jump/rotate composition
//     gains independent lifecycle policy.
// - Merge-When:
//   - A generic geometry-native sequence preserves the exact theorem evidence.
// - Summary:
//   - Executes the `p p p p v` suffix of certified `(&<;:9K`.
// - Description:
//   - Extends the fixed crazy prefix with halt admitted only from its final
//     normative checkpoint.
// - Usage:
//   - Admit exact evidence, then execute transactionally from post-rotate
//     state.
// - Defaults:
//   - Guard/failure index is global within this five-step suffix.
//

//! Five-step explicit-geometry crazy-prefix/halt composition.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{ExecutionGeometryRegionEffectProgram, ProfileMachineState};

use crate::execution_native::{
    ExecutionGeometryNativeRunner, NativeExecutableMemoryAdapter,
    NativeRegionBuffers, NativeRegionInvocationOutcome,
    VerifiedExecutionGeometryInitialHaltNativeObjectArtifact,
};
use crate::geometry_native_admission::{
    ExecutionGeometryNativeInitialHaltAdmission,
    ExecutionGeometryNativeInitialHaltAdmissionError,
    ExecutionGeometryNativeInitialHaltTransactionFailure,
};
use crate::geometry_native_crazy_prefix::{
    EXECUTION_GEOMETRY_NATIVE_CRAZY_PREFIX_STEPS,
    ExecutionGeometryNativeCrazyPrefix,
    ExecutionGeometryNativeCrazyPrefixAdmissionFailure,
    ExecutionGeometryNativeCrazyPrefixEvidence,
    ExecutionGeometryNativeCrazyPrefixFailure,
    ExecutionGeometryNativeCrazyPrefixOutcome,
};

/// Total theorem steps in the post-rotate `p p p p v` suffix.
pub const EXECUTION_GEOMETRY_NATIVE_CRAZY_PREFIX_HALT_STEPS: usize =
    EXECUTION_GEOMETRY_NATIVE_CRAZY_PREFIX_STEPS + 1;

type CrazyPrefixHaltAdmissionResult = Result<
    ExecutionGeometryNativeCrazyPrefixHaltSequence,
    Box<ExecutionGeometryNativeCrazyPrefixHaltAdmissionFailure>,
>;
type CrazyPrefixHaltFailureBox<MemoryError, RunnerError> = Box<
    ExecutionGeometryNativeCrazyPrefixHaltFailure<MemoryError, RunnerError>,
>;

type HaltTransactionFailure<MemoryError, RunnerError> =
    ExecutionGeometryNativeInitialHaltTransactionFailure<
        MemoryError,
        RunnerError,
    >;

/// Exact theorem evidence for four crazy steps followed immediately by halt.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeCrazyPrefixHaltEvidence {
    halt_artifact: VerifiedExecutionGeometryInitialHaltNativeObjectArtifact,
    halt_program: ExecutionGeometryRegionEffectProgram,
    prefix: ExecutionGeometryNativeCrazyPrefixEvidence,
}

/// Failure while admitting the exact five-step suffix before any mapping.
#[derive(Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeCrazyPrefixHaltAdmissionFailure {
    /// Halt rejected the exact normative final crazy checkpoint.
    Halt(ExecutionGeometryNativeInitialHaltAdmissionError),
    /// One crazy step rejected its exact chained checkpoint.
    Prefix(Box<ExecutionGeometryNativeCrazyPrefixAdmissionFailure>),
}

/// Primary execution failure retaining specialized cleanup ownership.
#[derive(Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeCrazyPrefixHaltFailureCause<
    MemoryError,
    RunnerError,
> {
    /// Final halt transaction failed.
    Halt(Box<HaltTransactionFailure<MemoryError, RunnerError>>),
    /// One of the four crazy transactions failed.
    Prefix(
        Box<
            ExecutionGeometryNativeCrazyPrefixFailure<MemoryError, RunnerError>,
        >,
    ),
}

/// Indexed failure retaining the last committed opaque-geometry checkpoint.
#[derive(Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeCrazyPrefixHaltFailure<
    MemoryError,
    RunnerError,
> {
    cause: ExecutionGeometryNativeCrazyPrefixHaltFailureCause<
        MemoryError,
        RunnerError,
    >,
    index: usize,
    state: ProfileMachineState,
}

/// Successful or safely suspended execution of the exact five-step suffix.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeCrazyPrefixHaltOutcome {
    /// All four crazy steps and the final halt applied exactly.
    Completed(ProfileMachineState),
    /// A semantic guard missed before the indexed step could commit.
    GuardMiss {
        /// Zero-based index in the `p p p p v` suffix.
        index: usize,
        /// Last fully committed opaque-geometry checkpoint.
        state: ProfileMachineState,
    },
}

/// Exact admitted `p p p p v` suffix sharing one checkpoint authority line.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeCrazyPrefixHaltSequence {
    halt: ExecutionGeometryNativeInitialHaltAdmission,
    prefix: ExecutionGeometryNativeCrazyPrefix,
}

/// Complete transaction result for concrete adapter ports.
pub type ExecutionGeometryNativeCrazyPrefixHaltAdapterResult<
    MemoryAdapter,
    Runner,
> = ExecutionGeometryNativeCrazyPrefixHaltResult<
    <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
    <Runner as ExecutionGeometryNativeRunner>::Error,
>;

/// Complete transaction result for the exact five-step suffix.
pub type ExecutionGeometryNativeCrazyPrefixHaltResult<
    MemoryError,
    RunnerError,
> = Result<
    ExecutionGeometryNativeCrazyPrefixHaltOutcome,
    Box<
        ExecutionGeometryNativeCrazyPrefixHaltFailure<MemoryError, RunnerError>,
    >,
>;

impl Display for ExecutionGeometryNativeCrazyPrefixHaltAdmissionFailure {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Halt(error) => {
                write!(f, "v5 crazy-prefix halt admission: {error}")
            },
            Self::Prefix(error) => Display::fmt(error, f),
        }
    }
}

impl<MemoryError: Display, RunnerError: Display> Display
    for ExecutionGeometryNativeCrazyPrefixHaltFailure<MemoryError, RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "v5 crazy-prefix/halt failed at {}: ", self.index)?;
        match &self.cause {
            ExecutionGeometryNativeCrazyPrefixHaltFailureCause::Halt(error) => {
                Display::fmt(error, f)
            },
            ExecutionGeometryNativeCrazyPrefixHaltFailureCause::Prefix(
                error,
            ) => Display::fmt(error, f),
        }
    }
}

impl ExecutionGeometryNativeCrazyPrefixHaltEvidence {
    /// Retains exact prefix evidence and its immediately reached halt evidence.
    #[must_use]
    pub const fn new(
        prefix: ExecutionGeometryNativeCrazyPrefixEvidence,
        halt_program: ExecutionGeometryRegionEffectProgram,
        halt_artifact: VerifiedExecutionGeometryInitialHaltNativeObjectArtifact,
    ) -> Self {
        Self {
            halt_artifact,
            halt_program,
            prefix,
        }
    }
}

impl<MemoryError, RunnerError>
    ExecutionGeometryNativeCrazyPrefixHaltFailure<MemoryError, RunnerError>
{
    /// Borrows the specialized per-stage failure and cleanup ownership.
    #[must_use]
    pub const fn cause(
        &self,
    ) -> &ExecutionGeometryNativeCrazyPrefixHaltFailureCause<
        MemoryError,
        RunnerError,
    > {
        &self.cause
    }

    /// Returns the zero-based global suffix index that failed.
    #[must_use]
    pub const fn index(&self) -> usize {
        self.index
    }

    /// Consumes the wrapper and returns specialized failure ownership.
    #[must_use]
    pub fn into_cause(
        self,
    ) -> ExecutionGeometryNativeCrazyPrefixHaltFailureCause<
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

impl ExecutionGeometryNativeCrazyPrefixHaltOutcome {
    /// Returns the final or last committed opaque-geometry checkpoint.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        match self {
            Self::Completed(state) | Self::GuardMiss { state, .. } => state,
        }
    }
}

impl ExecutionGeometryNativeCrazyPrefixHaltSequence {
    /// Executes the exact `p p p p v` suffix transactionally in theorem order.
    ///
    /// # Errors
    ///
    /// Returns exact global index, last committed state, and specialized
    /// cleanup ownership for the failing prefix or halt transaction.
    pub fn execute_transactionally<MemoryAdapter, Runner>(
        &self,
        memory_adapter: &mut MemoryAdapter,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> ExecutionGeometryNativeCrazyPrefixHaltAdapterResult<
        MemoryAdapter,
        Runner,
    >
    where
        MemoryAdapter: NativeExecutableMemoryAdapter,
        Runner: ExecutionGeometryNativeRunner,
    {
        use ExecutionGeometryNativeCrazyPrefixHaltOutcome as Outcome;

        let (memory, input, output) = buffers.into_parts();
        let prefix_outcome = self
            .prefix
            .execute_transactionally(
                memory_adapter,
                runner,
                NativeRegionBuffers::new(&mut *memory, input, &mut *output),
            )
            .map_err(map_prefix_failure)?;
        let prefix_state = prefix_outcome.state().clone();
        if let ExecutionGeometryNativeCrazyPrefixOutcome::GuardMiss {
            index,
            state,
        } = prefix_outcome
        {
            return Ok(Outcome::GuardMiss { index, state });
        }
        let halt_result = self.halt.execute_transactionally(
            memory_adapter,
            runner,
            NativeRegionBuffers::new(&mut *memory, input, &mut *output),
        );
        let completion = halt_result.map_err(|cause| {
            let state = halt_failure_state(&prefix_state, &cause);
            Box::new(ExecutionGeometryNativeCrazyPrefixHaltFailure {
                cause: ExecutionGeometryNativeCrazyPrefixHaltFailureCause::Halt(
                    cause,
                ),
                index: EXECUTION_GEOMETRY_NATIVE_CRAZY_PREFIX_STEPS,
                state,
            })
        })?;
        let state = completion.state().clone();
        if completion.outcome() == NativeRegionInvocationOutcome::GuardMiss {
            return Ok(Outcome::GuardMiss {
                index: EXECUTION_GEOMETRY_NATIVE_CRAZY_PREFIX_STEPS,
                state,
            });
        }
        Ok(Outcome::Completed(state))
    }

    /// Returns the halt admitted only from the prefix's normative final state.
    #[must_use]
    pub const fn halt(&self) -> &ExecutionGeometryNativeInitialHaltAdmission {
        &self.halt
    }

    /// Admits the exact four-crazy prefix, then binds halt to its final state.
    ///
    /// # Errors
    ///
    /// Returns specialized prefix/halt admission failure before mapping work.
    pub fn new(
        evidence: ExecutionGeometryNativeCrazyPrefixHaltEvidence,
        checkpoint: ProfileMachineState,
    ) -> CrazyPrefixHaltAdmissionResult {
        let prefix = ExecutionGeometryNativeCrazyPrefix::new(
            evidence.prefix,
            checkpoint,
        )
        .map_err(|error| {
            Box::new(
                ExecutionGeometryNativeCrazyPrefixHaltAdmissionFailure::Prefix(
                    error,
                ),
            )
        })?;
        let halt = ExecutionGeometryNativeInitialHaltAdmission::new(
            evidence.halt_program,
            prefix.final_state().clone(),
            evidence.halt_artifact,
        )
        .map_err(|error| {
            Box::new(
                ExecutionGeometryNativeCrazyPrefixHaltAdmissionFailure::Halt(
                    error,
                ),
            )
        })?;
        Ok(Self { halt, prefix })
    }

    /// Returns the exact four-crazy checkpoint chain preceding halt.
    #[must_use]
    pub const fn prefix(&self) -> &ExecutionGeometryNativeCrazyPrefix {
        &self.prefix
    }
}

fn halt_failure_state<MemoryError, RunnerError>(
    prior_state: &ProfileMachineState,
    failure: &HaltTransactionFailure<MemoryError, RunnerError>,
) -> ProfileMachineState {
    match failure {
        HaltTransactionFailure::Release { completion, .. } => {
            completion.state().clone()
        },
        HaltTransactionFailure::Binding { .. }
        | HaltTransactionFailure::Execution { .. }
        | HaltTransactionFailure::Load(_)
        | HaltTransactionFailure::Preparation(_) => prior_state.clone(),
    }
}

fn map_prefix_failure<MemoryError, RunnerError>(
    failure: Box<
        ExecutionGeometryNativeCrazyPrefixFailure<MemoryError, RunnerError>,
    >,
) -> CrazyPrefixHaltFailureBox<MemoryError, RunnerError> {
    let index = failure.index();
    let state = failure.state().clone();
    Box::new(ExecutionGeometryNativeCrazyPrefixHaltFailure {
        cause: ExecutionGeometryNativeCrazyPrefixHaltFailureCause::Prefix(
            failure,
        ),
        index,
        state,
    })
}
