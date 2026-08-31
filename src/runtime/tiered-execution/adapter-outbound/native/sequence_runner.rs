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
//   - Safe ordered execution and exact resume evidence for direct sequences.
// - Must-Not:
//   - Fuse objects, implement foreign calls, or roll back committed prior
//     steps.
// - Allows:
//   - Inputs: verified sequence plans, guest buffers, and explicit adapters.
//   - Outputs: complete application, guard-miss resume, or indexed failure.
//   - Side effects: those of admitted one-step calls and supplied adapters.
// - Split-When:
//   - Fused executable chains or interpreter resume transfer gain ownership.
// - Merge-When:
//   - Single-step and sequence execution share one transactional coordinator.
// - Summary:
//   - Executes verified one-step artifacts until completion or exact resume.
// - Description:
//   - Preserves committed prefixes and identifies the next semantic step.
// - Usage:
//   - Called after exact cached or uncached sequence planning.
// - Defaults:
//   - Current-step rejection restores that step; prior admitted steps remain.
//

//! Safe ordered execution for verified direct-native sequence plans.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{
    ExecutionGeometryRegionEffectProgram, ProfileMachineObservation,
    RegionEffectProgram,
};

use super::direct::{
    CachedVerifiedDirectSequencePlan,
    CachedVerifiedExecutionGeometryDirectSequencePlan,
    VerifiedDirectNativeArtifact, VerifiedDirectSequencePlan,
    VerifiedExecutionGeometryDirectSequencePlan,
    VerifiedExecutionGeometryNativeArtifact,
};
use super::executable_sequence::{
    ReadyExecutionGeometryNativeExecutableSequence,
    ReadyNativeExecutableSequence,
};
use super::invocation::{
    NativeRegionBuffers, NativeRegionInvocationOutcome,
    PreparedVerifiedDirectInvocation,
    PreparedVerifiedExecutionGeometryInvocation, VerifiedDirectInvocationError,
    VerifiedExecutionGeometryInvocationError,
};
use super::loader::{
    VerifiedDirectLoadError, VerifiedDirectLoadImage,
    VerifiedExecutionGeometryLoadImage,
};
use super::platform::NativeExecutableMemoryAdapter;
use super::runner::{
    ExecutionGeometryLoadedExecutionFailure, ExecutionGeometryNativeRunner,
    NativeExecutableExecutionFailure, NativeExecutableRunner,
    NativeLoadedExecutionFailure,
    execute_loaded_verified_execution_geometry_native,
    execute_loaded_verified_native, execute_verified_native,
};

/// Failure while admitting a preloaded v5 mapping chain against one plan.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryLoadedSequenceAdmissionError {
    /// The ready mapping count differs from the semantic step count.
    ExecutableCount {
        /// Exact number of mappings required by the plan.
        expected: usize,
        /// Number of mappings supplied by the loaded chain.
        observed: usize,
    },
    /// One ready mapping retains a different complete load image.
    ExecutableIdentity {
        /// Zero-based mismatching sequence position.
        index: usize,
    },
    /// One expected v5 artifact no longer yields a loader-ready image.
    Image {
        /// Zero-based image derivation position.
        index: usize,
        /// Exact loader-ready image failure.
        error: VerifiedDirectLoadError,
    },
}

#[derive(Debug, Eq, PartialEq)]
enum ExecutionGeometryLoadedSequenceFailureCause<RunnerError> {
    Admission(ExecutionGeometryLoadedSequenceAdmissionError),
    Execution(Box<ExecutionGeometryLoadedExecutionFailure<RunnerError>>),
    Preparation(Box<VerifiedExecutionGeometryInvocationError>),
}

/// Indexed failure while running one already-loaded verified-v5 sequence.
#[derive(Debug, Eq, PartialEq)]
pub struct ExecutionGeometryLoadedSequenceExecutionFailure<RunnerError> {
    cause: ExecutionGeometryLoadedSequenceFailureCause<RunnerError>,
    completed_steps: usize,
    observation: ProfileMachineObservation,
    resume_index: usize,
    step_index: usize,
}

/// Result of executing one already-loaded verified-v5 sequence.
pub type ExecutionGeometryLoadedSequenceExecutionResult<RunnerError> = Result<
    NativeSequenceExecutionOutcome,
    Box<ExecutionGeometryLoadedSequenceExecutionFailure<RunnerError>>,
>;

/// Admitted result of executing an ordered verified direct sequence.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeSequenceExecutionOutcome {
    /// Every sequence step applied exactly.
    Applied {
        /// Exact final observation after all committed steps.
        observation: ProfileMachineObservation,
        /// Number of committed sequence steps.
        steps: usize,
    },
    /// One semantic guard missed without applying the current step.
    GuardMiss {
        /// Zero-based step at which interpreter execution must resume.
        index: usize,
        /// Exact observation at the resume boundary.
        observation: ProfileMachineObservation,
    },
}

#[derive(Debug, Eq, PartialEq)]
enum NativeSequenceExecutionFailureCause<MemoryError, RunnerError> {
    Execution(Box<NativeExecutableExecutionFailure<MemoryError, RunnerError>>),
    Preparation(Box<VerifiedDirectInvocationError>),
}

/// Failure while admitting a preloaded executable chain against one plan.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeLoadedSequenceAdmissionError {
    /// The ready mapping count differs from the semantic step count.
    ExecutableCount {
        /// Exact number of mappings required by the plan.
        expected: usize,
        /// Number of mappings supplied by the loaded chain.
        observed: usize,
    },
    /// One ready mapping retains a different complete load image.
    ExecutableIdentity {
        /// Zero-based mismatching sequence position.
        index: usize,
    },
    /// One expected artifact no longer yields a loader-ready image.
    Image {
        /// Zero-based image derivation position.
        index: usize,
        /// Exact loader-ready image failure.
        error: VerifiedDirectLoadError,
    },
}

#[derive(Debug, Eq, PartialEq)]
enum NativeLoadedSequenceExecutionFailureCause<RunnerError> {
    Admission(NativeLoadedSequenceAdmissionError),
    Execution(Box<NativeLoadedExecutionFailure<RunnerError>>),
    Preparation(Box<VerifiedDirectInvocationError>),
}

/// Indexed failure while running one already loaded executable sequence.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeLoadedSequenceExecutionFailure<RunnerError> {
    cause: NativeLoadedSequenceExecutionFailureCause<RunnerError>,
    completed_steps: usize,
    observation: ProfileMachineObservation,
    resume_index: usize,
    step_index: usize,
}

/// Result of executing one already loaded verified direct sequence.
pub type NativeLoadedSequenceExecutionResult<RunnerError> = Result<
    NativeSequenceExecutionOutcome,
    Box<NativeLoadedSequenceExecutionFailure<RunnerError>>,
>;

/// Indexed sequence failure with exact committed-prefix and resume evidence.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeSequenceExecutionFailure<MemoryError, RunnerError> {
    cause: NativeSequenceExecutionFailureCause<MemoryError, RunnerError>,
    completed_steps: usize,
    observation: ProfileMachineObservation,
    resume_index: usize,
    step_index: usize,
}

/// Result of executing one cached or uncached verified direct sequence.
pub type NativeSequenceExecutionResult<MemoryError, RunnerError> = Result<
    NativeSequenceExecutionOutcome,
    Box<NativeSequenceExecutionFailure<MemoryError, RunnerError>>,
>;

type GeometrySequenceAdmissionError =
    ExecutionGeometryLoadedSequenceAdmissionError;
type ExecutionGeometryLoadedSequenceAdmissionResult =
    Result<(), (usize, ExecutionGeometryLoadedSequenceAdmissionError)>;
type ExecutionGeometryLoadedSequenceStepResult<Runner> = Result<
    NativeRegionInvocationOutcome,
    Box<
        ExecutionGeometryLoadedSequenceExecutionFailure<
            <Runner as ExecutionGeometryNativeRunner>::Error,
        >,
    >,
>;

type NativeLoadedSequenceAdmissionResult =
    Result<(), (usize, NativeLoadedSequenceAdmissionError)>;

type NativeLoadedSequenceStepResult<Runner> = Result<
    NativeRegionInvocationOutcome,
    Box<
        NativeLoadedSequenceExecutionFailure<
            <Runner as NativeExecutableRunner>::Error,
        >,
    >,
>;

type NativeSequenceAdapterResult<MemoryAdapter, Runner> =
    NativeSequenceExecutionResult<
        <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
        <Runner as NativeExecutableRunner>::Error,
    >;

struct ExecutionGeometrySequencePlanView<'plan> {
    artifacts: Vec<&'plan VerifiedExecutionGeometryNativeArtifact>,
    entry: ProfileMachineObservation,
    exit: ProfileMachineObservation,
    programs: &'plan [ExecutionGeometryRegionEffectProgram],
}

#[derive(Clone, Copy)]
struct ExecutionGeometryLoadedSequenceStep<'plan> {
    artifact: &'plan VerifiedExecutionGeometryNativeArtifact,
    entry: ProfileMachineObservation,
    executable: &'plan super::lifecycle::ReadyExecutionGeometryNativeExecutable,
    index: usize,
    program: &'plan ExecutionGeometryRegionEffectProgram,
}

struct NativeSequencePlanView<'plan> {
    artifacts: Vec<&'plan VerifiedDirectNativeArtifact>,
    entry: ProfileMachineObservation,
    exit: ProfileMachineObservation,
    programs: &'plan [RegionEffectProgram],
}

#[derive(Clone, Copy)]
struct NativeLoadedSequenceStep<'plan> {
    artifact: &'plan VerifiedDirectNativeArtifact,
    entry: ProfileMachineObservation,
    executable: &'plan super::lifecycle::ReadyNativeExecutable,
    index: usize,
    program: &'plan RegionEffectProgram,
}

impl Display for ExecutionGeometryLoadedSequenceAdmissionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::ExecutableCount { expected, observed } => write!(
                f,
                "v5 loaded mapping count {observed} differs from {expected}",
            ),
            Self::ExecutableIdentity { index } => {
                write!(f, "v5 loaded mapping identity differs at step {index}")
            },
            Self::Image { error, index } => {
                write!(f, "v5 load image failed at step {index}: {error}")
            },
        }
    }
}

impl<RunnerError> ExecutionGeometryLoadedSequenceExecutionFailure<RunnerError> {
    /// Returns whole-chain admission failure, when topology disagreed.
    #[must_use]
    pub const fn admission_error(
        &self,
    ) -> Option<ExecutionGeometryLoadedSequenceAdmissionError> {
        match &self.cause {
            ExecutionGeometryLoadedSequenceFailureCause::Admission(error) => {
                Some(*error)
            },
            ExecutionGeometryLoadedSequenceFailureCause::Execution(_)
            | ExecutionGeometryLoadedSequenceFailureCause::Preparation(_) => {
                None
            },
        }
    }

    /// Returns the number of already committed v5 steps.
    #[must_use]
    pub const fn completed_steps(&self) -> usize {
        self.completed_steps
    }

    /// Returns loaded-call failure for the current v5 step, when applicable.
    #[must_use]
    pub const fn execution_error(
        &self,
    ) -> Option<&ExecutionGeometryLoadedExecutionFailure<RunnerError>> {
        match &self.cause {
            ExecutionGeometryLoadedSequenceFailureCause::Execution(error) => {
                Some(error)
            },
            ExecutionGeometryLoadedSequenceFailureCause::Admission(_)
            | ExecutionGeometryLoadedSequenceFailureCause::Preparation(_) => {
                None
            },
        }
    }

    /// Returns the exact observation at the continuation boundary.
    #[must_use]
    pub const fn observation(&self) -> ProfileMachineObservation {
        self.observation
    }

    /// Returns v5 call preparation failure, when caller buffers disagreed.
    #[must_use]
    pub const fn preparation_error(
        &self,
    ) -> Option<&VerifiedExecutionGeometryInvocationError> {
        match &self.cause {
            ExecutionGeometryLoadedSequenceFailureCause::Preparation(error) => {
                Some(error)
            },
            ExecutionGeometryLoadedSequenceFailureCause::Admission(_)
            | ExecutionGeometryLoadedSequenceFailureCause::Execution(_) => None,
        }
    }

    /// Returns the next semantic step index for continuation.
    #[must_use]
    pub const fn resume_index(&self) -> usize {
        self.resume_index
    }

    /// Returns the zero-based v5 step whose transaction failed.
    #[must_use]
    pub const fn step_index(&self) -> usize {
        self.step_index
    }
}

impl<RunnerError: Display> Display
    for ExecutionGeometryLoadedSequenceExecutionFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "loaded v5 sequence step {} failed after {} committed steps: ",
            self.step_index, self.completed_steps,
        )?;
        match &self.cause {
            ExecutionGeometryLoadedSequenceFailureCause::Admission(error) => {
                write!(f, "admission: {error}")
            },
            ExecutionGeometryLoadedSequenceFailureCause::Execution(error) => {
                write!(f, "{error}")
            },
            ExecutionGeometryLoadedSequenceFailureCause::Preparation(error) => {
                write!(f, "preparation: {error}")
            },
        }
    }
}

impl NativeSequenceExecutionOutcome {
    /// Returns the number of steps committed before this outcome.
    #[must_use]
    pub const fn completed_steps(self) -> usize {
        match self {
            Self::Applied { steps, .. } => steps,
            Self::GuardMiss { index, .. } => index,
        }
    }

    /// Returns the exact observation at the continuation boundary.
    #[must_use]
    pub const fn observation(self) -> ProfileMachineObservation {
        match self {
            Self::Applied { observation, .. }
            | Self::GuardMiss { observation, .. } => observation,
        }
    }

    /// Returns the next semantic step index for interpreter continuation.
    #[must_use]
    pub const fn resume_index(self) -> usize {
        match self {
            Self::Applied { steps, .. } => steps,
            Self::GuardMiss { index, .. } => index,
        }
    }
}

impl Display for NativeLoadedSequenceAdmissionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::ExecutableCount { expected, observed } => write!(
                f,
                "loaded mapping count {observed} differs from {expected}",
            ),
            Self::ExecutableIdentity { index } => write!(
                f,
                "loaded sequence mapping identity differs at step {index}",
            ),
            Self::Image { error, index } => {
                write!(f, "loaded image failed at step {index}: {error}")
            },
        }
    }
}

impl<RunnerError> NativeLoadedSequenceExecutionFailure<RunnerError> {
    /// Returns chain admission failure, when topology or image identity
    /// drifted.
    #[must_use]
    pub const fn admission_error(
        &self,
    ) -> Option<NativeLoadedSequenceAdmissionError> {
        match self.cause {
            NativeLoadedSequenceExecutionFailureCause::Admission(error) => {
                Some(error)
            },
            NativeLoadedSequenceExecutionFailureCause::Execution(_)
            | NativeLoadedSequenceExecutionFailureCause::Preparation(_) => None,
        }
    }

    /// Returns the number of exact steps committed before failure.
    #[must_use]
    pub const fn completed_steps(&self) -> usize {
        self.completed_steps
    }

    /// Returns loaded one-step execution failure, when the runner path failed.
    #[must_use]
    pub const fn execution_failure(
        &self,
    ) -> Option<&NativeLoadedExecutionFailure<RunnerError>> {
        match &self.cause {
            NativeLoadedSequenceExecutionFailureCause::Admission(_)
            | NativeLoadedSequenceExecutionFailureCause::Preparation(_) => None,
            NativeLoadedSequenceExecutionFailureCause::Execution(error) => {
                Some(error)
            },
        }
    }

    /// Returns the exact observation at which execution may resume.
    #[must_use]
    pub const fn observation(&self) -> ProfileMachineObservation {
        self.observation
    }

    /// Returns call preparation failure, when current buffers disagreed.
    #[must_use]
    pub const fn preparation_error(
        &self,
    ) -> Option<&VerifiedDirectInvocationError> {
        match &self.cause {
            NativeLoadedSequenceExecutionFailureCause::Admission(_)
            | NativeLoadedSequenceExecutionFailureCause::Execution(_) => None,
            NativeLoadedSequenceExecutionFailureCause::Preparation(error) => {
                Some(error)
            },
        }
    }

    /// Returns the next semantic step index for interpreter continuation.
    #[must_use]
    pub const fn resume_index(&self) -> usize {
        self.resume_index
    }

    /// Returns the zero-based direct step whose transaction failed.
    #[must_use]
    pub const fn step_index(&self) -> usize {
        self.step_index
    }
}

impl<RunnerError: Display> Display
    for NativeLoadedSequenceExecutionFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "loaded native sequence step {} failed after {} committed steps: ",
            self.step_index, self.completed_steps
        )?;
        match &self.cause {
            NativeLoadedSequenceExecutionFailureCause::Admission(error) => {
                write!(f, "admission: {error}")
            },
            NativeLoadedSequenceExecutionFailureCause::Execution(error) => {
                write!(f, "{error}")
            },
            NativeLoadedSequenceExecutionFailureCause::Preparation(error) => {
                write!(f, "preparation: {error}")
            },
        }
    }
}

impl<MemoryError, RunnerError>
    NativeSequenceExecutionFailure<MemoryError, RunnerError>
{
    /// Returns the number of exact steps committed before failure.
    #[must_use]
    pub const fn completed_steps(&self) -> usize {
        self.completed_steps
    }

    /// Returns the failed one-step execution transaction, when available.
    #[must_use]
    pub const fn execution_failure(
        &self,
    ) -> Option<&NativeExecutableExecutionFailure<MemoryError, RunnerError>>
    {
        match &self.cause {
            NativeSequenceExecutionFailureCause::Execution(error) => {
                Some(error)
            },
            NativeSequenceExecutionFailureCause::Preparation(_) => None,
        }
    }

    /// Consumes this failure and returns the one-step transaction failure.
    #[must_use]
    pub fn into_execution_failure(
        self,
    ) -> Option<NativeExecutableExecutionFailure<MemoryError, RunnerError>>
    {
        match self.cause {
            NativeSequenceExecutionFailureCause::Execution(error) => {
                Some(*error)
            },
            NativeSequenceExecutionFailureCause::Preparation(_) => None,
        }
    }

    /// Returns the exact observation at which execution may resume.
    #[must_use]
    pub const fn observation(&self) -> ProfileMachineObservation {
        self.observation
    }

    /// Returns call preparation failure, when the current buffers disagreed.
    #[must_use]
    pub const fn preparation_error(
        &self,
    ) -> Option<&VerifiedDirectInvocationError> {
        match &self.cause {
            NativeSequenceExecutionFailureCause::Execution(_) => None,
            NativeSequenceExecutionFailureCause::Preparation(error) => {
                Some(error)
            },
        }
    }

    /// Returns the next semantic step index for interpreter continuation.
    #[must_use]
    pub const fn resume_index(&self) -> usize {
        self.resume_index
    }

    /// Returns the zero-based direct step whose transaction failed.
    #[must_use]
    pub const fn step_index(&self) -> usize {
        self.step_index
    }
}

impl<MemoryError: Display, RunnerError: Display> Display
    for NativeSequenceExecutionFailure<MemoryError, RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "native sequence step {} failed after {} committed steps: ",
            self.step_index, self.completed_steps
        )?;
        match &self.cause {
            NativeSequenceExecutionFailureCause::Execution(error) => {
                write!(f, "{error}")
            },
            NativeSequenceExecutionFailureCause::Preparation(error) => {
                write!(f, "preparation: {error}")
            },
        }
    }
}

/// Executes one cache-aware v5 plan against mappings loaded before first call.
///
/// Complete mapping count and exact load-image identity are admitted before any
/// caller buffer may change. Applied prefixes remain committed; guard miss
/// returns the exact current-step observation without applying that step.
///
/// # Errors
///
/// Returns [`ExecutionGeometryLoadedSequenceExecutionFailure`] for whole-chain
/// admission, current-step preparation, runner, or completion failure.
pub fn execute_loaded_cached_verified_execution_geometry_sequence<Runner>(
    runner: &mut Runner,
    plan: &CachedVerifiedExecutionGeometryDirectSequencePlan,
    sequence: &ReadyExecutionGeometryNativeExecutableSequence,
    buffers: NativeRegionBuffers<'_>,
) -> ExecutionGeometryLoadedSequenceExecutionResult<Runner::Error>
where
    Runner: ExecutionGeometryNativeRunner,
{
    let artifacts = plan
        .artifacts()
        .iter()
        .map(AsRef::as_ref)
        .collect::<Vec<_>>();
    execute_loaded_execution_geometry_sequence(
        runner,
        ExecutionGeometrySequencePlanView {
            artifacts,
            entry: plan.entry(),
            exit: plan.exit(),
            programs: plan.programs(),
        },
        sequence.executables(),
        buffers,
    )
}

/// Executes one verified v5 plan against mappings loaded before first call.
///
/// Complete mapping count and exact load-image identity are admitted before any
/// caller buffer may change. This function neither loads nor releases mappings.
///
/// # Errors
///
/// Returns [`ExecutionGeometryLoadedSequenceExecutionFailure`] for whole-chain
/// admission, current-step preparation, runner, or completion failure.
pub fn execute_loaded_verified_execution_geometry_sequence<Runner>(
    runner: &mut Runner,
    plan: &VerifiedExecutionGeometryDirectSequencePlan,
    sequence: &ReadyExecutionGeometryNativeExecutableSequence,
    buffers: NativeRegionBuffers<'_>,
) -> ExecutionGeometryLoadedSequenceExecutionResult<Runner::Error>
where
    Runner: ExecutionGeometryNativeRunner,
{
    execute_loaded_execution_geometry_sequence(
        runner,
        ExecutionGeometrySequencePlanView {
            artifacts: plan.artifacts().iter().collect(),
            entry: plan.entry(),
            exit: plan.exit(),
            programs: plan.programs(),
        },
        sequence.executables(),
        buffers,
    )
}

fn execute_loaded_execution_geometry_sequence<Runner>(
    runner: &mut Runner,
    plan: ExecutionGeometrySequencePlanView<'_>,
    executables: &[super::lifecycle::ReadyExecutionGeometryNativeExecutable],
    buffers: NativeRegionBuffers<'_>,
) -> ExecutionGeometryLoadedSequenceExecutionResult<Runner::Error>
where
    Runner: ExecutionGeometryNativeRunner,
{
    validate_loaded_execution_geometry_sequence(&plan, executables).map_err(
        |(index, error)| {
            Box::new(ExecutionGeometryLoadedSequenceExecutionFailure {
                cause: ExecutionGeometryLoadedSequenceFailureCause::Admission(
                    error,
                ),
                completed_steps: 0,
                observation: plan.entry,
                resume_index: 0,
                step_index: index,
            })
        },
    )?;
    let (memory, input, output) = buffers.into_parts();
    let step_count = plan.programs.len();
    for (index, ((artifact, program), executable)) in plan
        .artifacts
        .into_iter()
        .zip(plan.programs.iter())
        .zip(executables.iter())
        .enumerate()
    {
        let entry = program.entry_observation().unwrap_or(plan.exit);
        let outcome = execute_loaded_execution_geometry_sequence_step(
            runner,
            ExecutionGeometryLoadedSequenceStep {
                artifact,
                entry,
                executable,
                index,
                program,
            },
            NativeRegionBuffers::new(&mut *memory, input, &mut *output),
        )?;
        if outcome == NativeRegionInvocationOutcome::GuardMiss {
            return Ok(NativeSequenceExecutionOutcome::GuardMiss {
                index,
                observation: entry,
            });
        }
    }
    Ok(NativeSequenceExecutionOutcome::Applied {
        observation: plan.exit,
        steps: step_count,
    })
}

fn execute_loaded_execution_geometry_sequence_step<Runner>(
    runner: &mut Runner,
    step: ExecutionGeometryLoadedSequenceStep<'_>,
    buffers: NativeRegionBuffers<'_>,
) -> ExecutionGeometryLoadedSequenceStepResult<Runner>
where
    Runner: ExecutionGeometryNativeRunner,
{
    let prepared = PreparedVerifiedExecutionGeometryInvocation::new(
        step.artifact,
        step.program,
        buffers,
    )
    .map_err(|error| {
        Box::new(ExecutionGeometryLoadedSequenceExecutionFailure {
            cause: ExecutionGeometryLoadedSequenceFailureCause::Preparation(
                Box::new(error),
            ),
            completed_steps: step.index,
            observation: step.entry,
            resume_index: step.index,
            step_index: step.index,
        })
    })?;
    execute_loaded_verified_execution_geometry_native(
        runner,
        step.executable,
        prepared,
    )
    .map_err(|error| {
        Box::new(ExecutionGeometryLoadedSequenceExecutionFailure {
            cause: ExecutionGeometryLoadedSequenceFailureCause::Execution(
                error,
            ),
            completed_steps: step.index,
            observation: step.entry,
            resume_index: step.index,
            step_index: step.index,
        })
    })
}

fn validate_loaded_execution_geometry_sequence(
    plan: &ExecutionGeometrySequencePlanView<'_>,
    executables: &[super::lifecycle::ReadyExecutionGeometryNativeExecutable],
) -> ExecutionGeometryLoadedSequenceAdmissionResult {
    if executables.len() != plan.artifacts.len() {
        return Err((0, GeometrySequenceAdmissionError::ExecutableCount {
            expected: plan.artifacts.len(),
            observed: executables.len(),
        }));
    }
    for (index, (artifact, executable)) in
        plan.artifacts.iter().zip(executables).enumerate()
    {
        let image = VerifiedExecutionGeometryLoadImage::new(artifact).map_err(
            |error| {
                (index, GeometrySequenceAdmissionError::Image {
                    index,
                    error,
                })
            },
        )?;
        if executable.image() != &image {
            return Err((
                index,
                GeometrySequenceAdmissionError::ExecutableIdentity { index },
            ));
        }
    }
    Ok(())
}

/// Executes one cache-aware plan against mappings loaded before the first call.
///
/// The complete mapping topology and every load image are validated before
/// caller buffers may change. This function never releases the loaded chain.
///
/// # Errors
///
/// Returns [`NativeLoadedSequenceExecutionFailure`] for chain admission,
/// preparation, runner, or completion failure.
pub fn execute_loaded_cached_verified_native_sequence<Runner>(
    runner: &mut Runner,
    plan: &CachedVerifiedDirectSequencePlan,
    sequence: &ReadyNativeExecutableSequence,
    buffers: NativeRegionBuffers<'_>,
) -> NativeLoadedSequenceExecutionResult<Runner::Error>
where
    Runner: NativeExecutableRunner,
{
    let artifacts = plan
        .artifacts()
        .iter()
        .map(AsRef::as_ref)
        .collect::<Vec<_>>();
    execute_loaded_sequence(
        runner,
        NativeSequencePlanView {
            artifacts,
            entry: plan.entry(),
            exit: plan.exit(),
            programs: plan.programs(),
        },
        sequence,
        buffers,
    )
}

/// Executes one uncached plan against mappings loaded before the first call.
///
/// Applied prefixes remain committed and guard miss returns the exact current
/// step. The caller retains the complete loaded chain for reuse or release.
///
/// # Errors
///
/// Returns [`NativeLoadedSequenceExecutionFailure`] for chain admission,
/// preparation, runner, or completion failure.
pub fn execute_loaded_verified_native_sequence<Runner>(
    runner: &mut Runner,
    plan: &VerifiedDirectSequencePlan,
    sequence: &ReadyNativeExecutableSequence,
    buffers: NativeRegionBuffers<'_>,
) -> NativeLoadedSequenceExecutionResult<Runner::Error>
where
    Runner: NativeExecutableRunner,
{
    execute_loaded_sequence(
        runner,
        NativeSequencePlanView {
            artifacts: plan.artifacts().iter().collect(),
            entry: plan.entry(),
            exit: plan.exit(),
            programs: plan.programs(),
        },
        sequence,
        buffers,
    )
}

fn execute_loaded_sequence<Runner>(
    runner: &mut Runner,
    plan: NativeSequencePlanView<'_>,
    sequence: &ReadyNativeExecutableSequence,
    buffers: NativeRegionBuffers<'_>,
) -> NativeLoadedSequenceExecutionResult<Runner::Error>
where
    Runner: NativeExecutableRunner,
{
    validate_loaded_sequence(&plan, sequence).map_err(|(index, error)| {
        Box::new(NativeLoadedSequenceExecutionFailure {
            cause: NativeLoadedSequenceExecutionFailureCause::Admission(error),
            completed_steps: 0,
            observation: plan.entry,
            resume_index: 0,
            step_index: index,
        })
    })?;
    let (memory, input, output) = buffers.into_parts();
    let step_count = plan.programs.len();
    for (index, ((artifact, program), executable)) in plan
        .artifacts
        .into_iter()
        .zip(plan.programs.iter())
        .zip(sequence.executables().iter())
        .enumerate()
    {
        let entry = program
            .effects
            .first()
            .map_or(plan.exit, |effect| effect.before);
        let outcome = execute_loaded_sequence_step(
            runner,
            NativeLoadedSequenceStep {
                artifact,
                entry,
                executable,
                index,
                program,
            },
            NativeRegionBuffers::new(&mut *memory, input, &mut *output),
        )?;
        if outcome == NativeRegionInvocationOutcome::GuardMiss {
            return Ok(NativeSequenceExecutionOutcome::GuardMiss {
                index,
                observation: entry,
            });
        }
    }
    Ok(NativeSequenceExecutionOutcome::Applied {
        observation: plan.exit,
        steps: step_count,
    })
}

fn execute_loaded_sequence_step<Runner>(
    runner: &mut Runner,
    step: NativeLoadedSequenceStep<'_>,
    buffers: NativeRegionBuffers<'_>,
) -> NativeLoadedSequenceStepResult<Runner>
where
    Runner: NativeExecutableRunner,
{
    let prepared = PreparedVerifiedDirectInvocation::new(
        step.artifact,
        step.program,
        buffers,
    )
    .map_err(|error| {
        Box::new(NativeLoadedSequenceExecutionFailure {
            cause: NativeLoadedSequenceExecutionFailureCause::Preparation(
                Box::new(error),
            ),
            completed_steps: step.index,
            observation: step.entry,
            resume_index: step.index,
            step_index: step.index,
        })
    })?;
    execute_loaded_verified_native(runner, step.executable, prepared).map_err(
        |error| {
            Box::new(NativeLoadedSequenceExecutionFailure {
                cause: NativeLoadedSequenceExecutionFailureCause::Execution(
                    error,
                ),
                completed_steps: step.index,
                observation: step.entry,
                resume_index: step.index,
                step_index: step.index,
            })
        },
    )
}

fn validate_loaded_sequence(
    plan: &NativeSequencePlanView<'_>,
    sequence: &ReadyNativeExecutableSequence,
) -> NativeLoadedSequenceAdmissionResult {
    if sequence.len() != plan.artifacts.len() {
        return Err((0, NativeLoadedSequenceAdmissionError::ExecutableCount {
            expected: plan.artifacts.len(),
            observed: sequence.len(),
        }));
    }
    for (index, (artifact, executable)) in plan
        .artifacts
        .iter()
        .zip(sequence.executables())
        .enumerate()
    {
        let image =
            VerifiedDirectLoadImage::new(artifact).map_err(|error| {
                (index, NativeLoadedSequenceAdmissionError::Image {
                    index,
                    error,
                })
            })?;
        if executable.image() != &image {
            return Err((
                index,
                NativeLoadedSequenceAdmissionError::ExecutableIdentity {
                    index,
                },
            ));
        }
    }
    Ok(())
}

/// Executes one cache-aware verified direct sequence in semantic order.
///
/// # Errors
///
/// Returns [`NativeSequenceExecutionFailure`] with exact step and resume
/// evidence when preparation, loading, running, completion, or release fails.
pub fn execute_cached_verified_native_sequence<MemoryAdapter, Runner>(
    memory_adapter: &mut MemoryAdapter,
    runner: &mut Runner,
    plan: &CachedVerifiedDirectSequencePlan,
    buffers: NativeRegionBuffers<'_>,
) -> NativeSequenceAdapterResult<MemoryAdapter, Runner>
where
    MemoryAdapter: NativeExecutableMemoryAdapter,
    Runner: NativeExecutableRunner,
{
    let artifacts = plan
        .artifacts()
        .iter()
        .map(AsRef::as_ref)
        .collect::<Vec<_>>();
    execute_sequence(
        memory_adapter,
        runner,
        NativeSequencePlanView {
            artifacts,
            entry: plan.entry(),
            exit: plan.exit(),
            programs: plan.programs(),
        },
        buffers,
    )
}

/// Executes one uncached verified direct sequence in semantic order.
///
/// Prior admitted steps remain committed. A guard miss leaves the current step
/// untouched and returns its exact index and entry observation for interpreter
/// continuation.
///
/// # Errors
///
/// Returns [`NativeSequenceExecutionFailure`] with exact step and resume
/// evidence when preparation, loading, running, completion, or release fails.
pub fn execute_verified_native_sequence<MemoryAdapter, Runner>(
    memory_adapter: &mut MemoryAdapter,
    runner: &mut Runner,
    plan: &VerifiedDirectSequencePlan,
    buffers: NativeRegionBuffers<'_>,
) -> NativeSequenceAdapterResult<MemoryAdapter, Runner>
where
    MemoryAdapter: NativeExecutableMemoryAdapter,
    Runner: NativeExecutableRunner,
{
    execute_sequence(
        memory_adapter,
        runner,
        NativeSequencePlanView {
            artifacts: plan.artifacts().iter().collect(),
            entry: plan.entry(),
            exit: plan.exit(),
            programs: plan.programs(),
        },
        buffers,
    )
}

fn execute_sequence<MemoryAdapter, Runner>(
    memory_adapter: &mut MemoryAdapter,
    runner: &mut Runner,
    plan: NativeSequencePlanView<'_>,
    buffers: NativeRegionBuffers<'_>,
) -> NativeSequenceAdapterResult<MemoryAdapter, Runner>
where
    MemoryAdapter: NativeExecutableMemoryAdapter,
    Runner: NativeExecutableRunner,
{
    let (memory, input, output) = buffers.into_parts();
    let step_count = plan.programs.len();
    for (index, (artifact, program)) in plan
        .artifacts
        .into_iter()
        .zip(plan.programs.iter())
        .enumerate()
    {
        let entry = program
            .effects
            .first()
            .map_or(plan.exit, |effect| effect.before);
        let prepared = match PreparedVerifiedDirectInvocation::new(
            artifact,
            program,
            NativeRegionBuffers::new(&mut *memory, input, &mut *output),
        ) {
            Ok(prepared) => prepared,
            Err(error) => {
                return Err(Box::new(NativeSequenceExecutionFailure {
                    cause: NativeSequenceExecutionFailureCause::Preparation(
                        Box::new(error),
                    ),
                    completed_steps: index,
                    observation: entry,
                    resume_index: index,
                    step_index: index,
                }));
            },
        };
        match execute_verified_native(memory_adapter, runner, prepared) {
            Ok(NativeRegionInvocationOutcome::Applied(_)) => {},
            Ok(NativeRegionInvocationOutcome::GuardMiss) => {
                return Ok(NativeSequenceExecutionOutcome::GuardMiss {
                    index,
                    observation: entry,
                });
            },
            Err(error) => {
                return Err(Box::new(sequence_step_failure(
                    index, entry, *error,
                )));
            },
        }
    }
    Ok(NativeSequenceExecutionOutcome::Applied {
        observation: plan.exit,
        steps: step_count,
    })
}

fn sequence_step_failure<MemoryError, RunnerError>(
    step_index: usize,
    entry: ProfileMachineObservation,
    error: NativeExecutableExecutionFailure<MemoryError, RunnerError>,
) -> NativeSequenceExecutionFailure<MemoryError, RunnerError> {
    let (completed_steps, observation, resume_index) =
        match error.committed_outcome() {
            Some(NativeRegionInvocationOutcome::Applied(observation)) => (
                step_index.saturating_add(1),
                observation,
                step_index.saturating_add(1),
            ),
            Some(NativeRegionInvocationOutcome::GuardMiss) | None => {
                (step_index, entry, step_index)
            },
        };
    NativeSequenceExecutionFailure {
        cause: NativeSequenceExecutionFailureCause::Execution(Box::new(error)),
        completed_steps,
        observation,
        resume_index,
        step_index,
    }
}
