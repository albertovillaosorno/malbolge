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
//   - Ordered transactional composition of the four theorem-derived v5 crazy
//     steps reached after jump and rotate.
// - Must-Not:
//   - Generalize crazy count, skip checkpoint replay, preload mappings, or hide
//     partial committed progress.
// - Allows:
//   - Inputs: four exact crazy programs/artifacts, entry checkpoint, adapter,
//     runner, and caller buffers.
//   - Outputs: final checkpoint, indexed guard miss, or indexed typed failure.
//   - Side effects: delegated per-step executable mapping, runner, and release.
// - Split-When:
//   - Reusable multi-mapping ownership or the final halt gains lifecycle
//     policy.
// - Merge-When:
//   - Generic geometry-native sequence planning preserves this exact theorem.
// - Summary:
//   - Executes the four-crazy `(&<;:9K` prefix from its post-rotate checkpoint.
// - Description:
//   - Chains each normative crazy exit into the next admission checkpoint.
// - Usage:
//   - Admit four exact theorem steps, then execute them transactionally in
//     order.
// - Defaults:
//   - Guard miss stops before the indexed step; failure reports committed
//     state.
//

//! Four-step explicit-geometry crazy-prefix composition.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{ExecutionGeometryRegionEffectProgram, ProfileMachineState};

use crate::execution_native::{
    ExecutionGeometryNativeRunner, NativeExecutableMemoryAdapter,
    NativeRegionBuffers, NativeRegionInvocationOutcome,
    VerifiedExecutionGeometryCrazyNativeObjectArtifact,
};
use crate::geometry_native_crazy::{
    ExecutionGeometryNativeCrazyAdmission,
    ExecutionGeometryNativeCrazyAdmissionError,
    ExecutionGeometryNativeCrazyCompletion,
    ExecutionGeometryNativeCrazyTransactionFailure,
};

/// Number of crazy steps certified by the `(&<;:9K` prefix theorem.
pub const EXECUTION_GEOMETRY_NATIVE_CRAZY_PREFIX_STEPS: usize = 4;

type CrazyPrefixAdapterStepResult<MemoryAdapter, Runner> =
    CrazyPrefixStepResult<
        <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
        <Runner as ExecutionGeometryNativeRunner>::Error,
    >;
type CrazyPrefixStepRequest<'request, MemoryAdapter, Runner> = (
    &'request ExecutionGeometryNativeCrazyAdmission,
    usize,
    &'request ProfileMachineState,
    &'request mut MemoryAdapter,
    &'request mut Runner,
);
type CrazyPrefixStepResult<MemoryError, RunnerError> = Result<
    ExecutionGeometryNativeCrazyCompletion,
    Box<ExecutionGeometryNativeCrazyPrefixFailure<MemoryError, RunnerError>>,
>;
type CrazyTransactionFailure<MemoryError, RunnerError> =
    ExecutionGeometryNativeCrazyTransactionFailure<MemoryError, RunnerError>;

/// One exact program/artifact pair for a theorem-derived crazy step.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeCrazyPrefixStepEvidence {
    artifact: VerifiedExecutionGeometryCrazyNativeObjectArtifact,
    program: ExecutionGeometryRegionEffectProgram,
}

/// Exact four-step crazy evidence retained before checkpoint admission.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeCrazyPrefixEvidence {
    steps: [ExecutionGeometryNativeCrazyPrefixStepEvidence;
        EXECUTION_GEOMETRY_NATIVE_CRAZY_PREFIX_STEPS],
}

/// Indexed failure while chaining four checkpoint-bound crazy admissions.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeCrazyPrefixAdmissionFailure {
    cause: ExecutionGeometryNativeCrazyAdmissionError,
    index: usize,
}

/// Indexed execution failure retaining the last committed opaque checkpoint.
#[derive(Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeCrazyPrefixFailure<MemoryError, RunnerError> {
    cause: Box<CrazyTransactionFailure<MemoryError, RunnerError>>,
    index: usize,
    state: ProfileMachineState,
}

/// Successful or safely suspended execution of the four-crazy prefix.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeCrazyPrefixOutcome {
    /// All four crazy steps applied and released exactly.
    Completed(ProfileMachineState),
    /// One semantic guard missed before the indexed crazy could commit.
    GuardMiss {
        /// Zero-based crazy step whose guard missed.
        index: usize,
        /// Last fully committed opaque-geometry checkpoint.
        state: ProfileMachineState,
    },
}

/// Four independently admitted crazy steps sharing one checkpoint authority
/// line.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeCrazyPrefix {
    steps: [ExecutionGeometryNativeCrazyAdmission;
        EXECUTION_GEOMETRY_NATIVE_CRAZY_PREFIX_STEPS],
}

/// Complete transaction result for the exact four-crazy prefix.
pub type ExecutionGeometryNativeCrazyPrefixAdapterResult<
    MemoryAdapter,
    Runner,
> = ExecutionGeometryNativeCrazyPrefixResult<
    <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
    <Runner as ExecutionGeometryNativeRunner>::Error,
>;

/// Complete transaction result for the exact four-crazy prefix.
pub type ExecutionGeometryNativeCrazyPrefixResult<MemoryError, RunnerError> =
    Result<
        ExecutionGeometryNativeCrazyPrefixOutcome,
        Box<
            ExecutionGeometryNativeCrazyPrefixFailure<MemoryError, RunnerError>,
        >,
    >;

impl Display for ExecutionGeometryNativeCrazyPrefixAdmissionFailure {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "v5 crazy prefix admission failed at {}: {}",
            self.index, self.cause
        )
    }
}

impl<MemoryError: Display, RunnerError: Display> Display
    for ExecutionGeometryNativeCrazyPrefixFailure<MemoryError, RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "v5 crazy prefix failed at {}: {}",
            self.index, self.cause
        )
    }
}

impl ExecutionGeometryNativeCrazyPrefixStepEvidence {
    /// Retains one exact crazy program and its verified geometry-bound
    /// artifact.
    #[must_use]
    pub const fn new(
        program: ExecutionGeometryRegionEffectProgram,
        artifact: VerifiedExecutionGeometryCrazyNativeObjectArtifact,
    ) -> Self {
        Self { artifact, program }
    }
}

impl ExecutionGeometryNativeCrazyPrefixEvidence {
    fn into_steps(
        self,
    ) -> [ExecutionGeometryNativeCrazyPrefixStepEvidence;
        EXECUTION_GEOMETRY_NATIVE_CRAZY_PREFIX_STEPS] {
        self.steps
    }

    /// Retains exactly four crazy step evidence values in theorem order.
    #[must_use]
    pub const fn new(
        steps: [ExecutionGeometryNativeCrazyPrefixStepEvidence;
            EXECUTION_GEOMETRY_NATIVE_CRAZY_PREFIX_STEPS],
    ) -> Self {
        Self { steps }
    }
}

impl ExecutionGeometryNativeCrazyPrefixAdmissionFailure {
    /// Returns the exact per-step crazy admission failure.
    #[must_use]
    pub const fn cause(&self) -> ExecutionGeometryNativeCrazyAdmissionError {
        self.cause
    }

    /// Returns the zero-based crazy step that failed admission.
    #[must_use]
    pub const fn index(&self) -> usize {
        self.index
    }
}

impl<MemoryError, RunnerError>
    ExecutionGeometryNativeCrazyPrefixFailure<MemoryError, RunnerError>
{
    /// Borrows the exact per-step transaction failure and cleanup ownership.
    #[must_use]
    pub const fn cause(
        &self,
    ) -> &CrazyTransactionFailure<MemoryError, RunnerError> {
        &self.cause
    }

    /// Returns the zero-based crazy step that failed.
    #[must_use]
    pub const fn index(&self) -> usize {
        self.index
    }

    /// Consumes the prefix failure and returns exact per-step ownership.
    #[must_use]
    pub fn into_cause(
        self,
    ) -> CrazyTransactionFailure<MemoryError, RunnerError> {
        *self.cause
    }

    /// Returns the last committed opaque-geometry checkpoint.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        &self.state
    }
}

impl ExecutionGeometryNativeCrazyPrefixOutcome {
    /// Returns the final or last committed opaque-geometry checkpoint.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        match self {
            Self::Completed(state) | Self::GuardMiss { state, .. } => state,
        }
    }
}

impl ExecutionGeometryNativeCrazyPrefix {
    fn admit_step(
        index: usize,
        evidence: ExecutionGeometryNativeCrazyPrefixStepEvidence,
        checkpoint: ProfileMachineState,
    ) -> Result<
        ExecutionGeometryNativeCrazyAdmission,
        Box<ExecutionGeometryNativeCrazyPrefixAdmissionFailure>,
    > {
        ExecutionGeometryNativeCrazyAdmission::new(
            evidence.program,
            checkpoint,
            evidence.artifact,
        )
        .map_err(|cause| {
            Box::new(ExecutionGeometryNativeCrazyPrefixAdmissionFailure {
                cause,
                index,
            })
        })
    }

    /// Returns the exact post-rotate checkpoint entering the crazy prefix.
    #[must_use]
    pub const fn entry_state(&self) -> &ProfileMachineState {
        let [first, ..] = &self.steps;
        first.checkpoint()
    }

    /// Executes all four crazy steps through per-step transactional ownership.
    ///
    /// Each step maps and releases independently. Applied completion advances
    /// checkpoint authority to the next admission. Guard miss stops
    /// immediately. A final-release failure after Applied reports the newly
    /// committed state while retaining that step's retryable executable
    /// cleanup ownership.
    ///
    /// # Errors
    ///
    /// Returns indexed exact per-step failure and the last committed
    /// checkpoint.
    pub fn execute_transactionally<MemoryAdapter, Runner>(
        &self,
        memory_adapter: &mut MemoryAdapter,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> ExecutionGeometryNativeCrazyPrefixAdapterResult<MemoryAdapter, Runner>
    where
        MemoryAdapter: NativeExecutableMemoryAdapter,
        Runner: ExecutionGeometryNativeRunner,
    {
        use ExecutionGeometryNativeCrazyPrefixOutcome as Outcome;

        let (memory, input, output) = buffers.into_parts();
        let mut state = self.entry_state().clone();
        for (index, step) in self.steps.iter().enumerate() {
            let request =
                (step, index, &state, &mut *memory_adapter, &mut *runner);
            let completion = execute_step_transactionally(
                request,
                NativeRegionBuffers::new(&mut *memory, input, &mut *output),
            )?;
            state = completion.state().clone();
            if completion.outcome() == NativeRegionInvocationOutcome::GuardMiss
            {
                return Ok(Outcome::GuardMiss { index, state });
            }
        }
        Ok(Outcome::Completed(state))
    }

    /// Returns the normative checkpoint after all four crazy steps.
    #[must_use]
    pub const fn final_state(&self) -> &ProfileMachineState {
        let [_, _, _, fourth] = &self.steps;
        fourth.expected_state()
    }

    /// Admits exactly four crazy steps by chaining normative replay
    /// checkpoints.
    ///
    /// # Errors
    ///
    /// Returns indexed exact crazy admission failure before any mapping work.
    pub fn new(
        evidence: ExecutionGeometryNativeCrazyPrefixEvidence,
        checkpoint: ProfileMachineState,
    ) -> Result<Self, Box<ExecutionGeometryNativeCrazyPrefixAdmissionFailure>>
    {
        let [
            first_evidence,
            second_evidence,
            third_evidence,
            fourth_evidence,
        ] = evidence.into_steps();
        let first = Self::admit_step(0, first_evidence, checkpoint)?;
        let second_checkpoint = first.expected_state().clone();
        let second = Self::admit_step(1, second_evidence, second_checkpoint)?;
        let third_checkpoint = second.expected_state().clone();
        let third = Self::admit_step(2, third_evidence, third_checkpoint)?;
        let fourth_checkpoint = third.expected_state().clone();
        let fourth = Self::admit_step(3, fourth_evidence, fourth_checkpoint)?;
        Ok(Self {
            steps: [first, second, third, fourth],
        })
    }

    /// Returns all four exact checkpoint-bound crazy admissions in order.
    #[must_use]
    pub const fn steps(
        &self,
    ) -> &[ExecutionGeometryNativeCrazyAdmission;
         EXECUTION_GEOMETRY_NATIVE_CRAZY_PREFIX_STEPS] {
        &self.steps
    }
}

fn execute_step_transactionally<MemoryAdapter, Runner>(
    request: CrazyPrefixStepRequest<'_, MemoryAdapter, Runner>,
    buffers: NativeRegionBuffers<'_>,
) -> CrazyPrefixAdapterStepResult<MemoryAdapter, Runner>
where
    MemoryAdapter: NativeExecutableMemoryAdapter,
    Runner: ExecutionGeometryNativeRunner,
{
    let (step, index, prior_state, memory_adapter, runner) = request;
    step.execute_transactionally(memory_adapter, runner, buffers)
        .map_err(|cause| {
            let state = transaction_failure_state(prior_state, &cause);
            Box::new(ExecutionGeometryNativeCrazyPrefixFailure {
                cause,
                index,
                state,
            })
        })
}

fn transaction_failure_state<MemoryError, RunnerError>(
    prior_state: &ProfileMachineState,
    failure: &CrazyTransactionFailure<MemoryError, RunnerError>,
) -> ProfileMachineState {
    match failure {
        CrazyTransactionFailure::Release { completion, .. } => {
            completion.state().clone()
        },
        CrazyTransactionFailure::Binding { .. }
        | CrazyTransactionFailure::Execution { .. }
        | CrazyTransactionFailure::Load(_)
        | CrazyTransactionFailure::Preparation(_) => prior_state.clone(),
    }
}
