// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
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

use malbolge::ProfileMachineObservation;

use super::direct::{
    CachedVerifiedDirectSequencePlan, VerifiedDirectNativeArtifact,
    VerifiedDirectSequencePlan,
};
use super::invocation::{
    NativeRegionBuffers, NativeRegionInvocationOutcome,
    PreparedVerifiedDirectInvocation, VerifiedDirectInvocationError,
};
use super::platform::NativeExecutableMemoryAdapter;
use super::runner::{
    NativeExecutableExecutionFailure, NativeExecutableRunner,
    execute_verified_native,
};
use crate::execution_ir::RegionEffectProgram;

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

type NativeSequenceAdapterResult<MemoryAdapter, Runner> =
    NativeSequenceExecutionResult<
        <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
        <Runner as NativeExecutableRunner>::Error,
    >;

struct NativeSequencePlanView<'plan> {
    artifacts: Vec<&'plan VerifiedDirectNativeArtifact>,
    exit: ProfileMachineObservation,
    programs: &'plan [RegionEffectProgram],
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
