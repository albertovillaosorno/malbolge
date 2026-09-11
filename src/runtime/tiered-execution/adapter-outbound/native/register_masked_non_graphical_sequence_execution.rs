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
//   - Indexed runner execution for already-loaded non-graphical v6 sequences.
// - Must-Not:
//   - Allocate, release, cache, or alter admitted sequence topology.
// - Allows:
//   - Inputs: loaded non-graphical owner, runner, rebased entry, caller
//     buffers.
//   - Outputs: exact applied/guard progress or indexed current-step failure.
//   - Side effects: native runner calls through retained executable mappings.
// - Split-When:
//   - Continuation policy or cache scheduling gains independent ownership.
// - Merge-When:
//   - One reviewed non-graphical coordinator safely owns load and execution.
// - Summary:
//   - Executes retained non-graphical mappings without adapter work.
// - Description:
//   - Current-step failure rolls back through the owner contract while earlier
//     committed steps remain committed.
// - Usage:
//   - Execute one already-loaded sequence, then release it through its owner.
// - Defaults:
//   - Guard miss resumes at the current semantic position without mutation.
//

//! Indexed execution for loaded non-graphical register-masked v6 sequences.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::ProfileMachineObservation;

use super::invocation::{NativeRegionBuffers, NativeRegionInvocationOutcome};
use super::runner::RegisterMaskedNonGraphicalNativeRunner;
use super::{
    register_masked_non_graphical_loaded_sequence as loaded_sequence,
    register_masked_resident as resident,
};

/// Admitted result of executing one loaded non-graphical v6 sequence.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RegisterMaskedNonGraphicalNativeSequenceOutcome {
    /// Every semantic sequence step applied exactly.
    Applied {
        /// Exact final runtime observation after all committed steps.
        observation: ProfileMachineObservation,
        /// Number of committed semantic steps.
        steps: usize,
    },
    /// One semantic guard missed without applying the current step.
    GuardMiss {
        /// Zero-based step at which interpreter execution may resume.
        index: usize,
        /// Exact runtime observation at the resume boundary.
        observation: ProfileMachineObservation,
    },
}

/// Indexed current-step failure with exact committed-prefix evidence.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedNonGraphicalNativeSequenceExecutionFailure<RunnerError>
{
    cause: Box<
        resident::RegisterMaskedNonGraphicalNativeOwnerExecutionFailure<
            RunnerError,
        >,
    >,
    completed_steps: usize,
    observation: ProfileMachineObservation,
    step_index: usize,
}

/// Result of executing one already-loaded non-graphical v6 sequence.
pub type RegisterMaskedNonGraphicalNativeSequenceExecutionResult<RunnerError> =
    Result<
        RegisterMaskedNonGraphicalNativeSequenceOutcome,
        Box<
            RegisterMaskedNonGraphicalNativeSequenceExecutionFailure<
                RunnerError,
            >,
        >,
    >;

impl<RunnerError>
    RegisterMaskedNonGraphicalNativeSequenceExecutionFailure<RunnerError>
{
    /// Returns the number of exact sequence steps committed before failure.
    #[must_use]
    pub const fn completed_steps(&self) -> usize {
        self.completed_steps
    }

    /// Returns the exact current-step owner execution failure.
    #[must_use]
    pub const fn execution_failure(
        &self,
    ) -> &resident::RegisterMaskedNonGraphicalNativeOwnerExecutionFailure<
        RunnerError,
    > {
        &self.cause
    }

    /// Returns the exact runtime observation at the failed step boundary.
    #[must_use]
    pub const fn observation(&self) -> ProfileMachineObservation {
        self.observation
    }

    /// Returns the next semantic step index for interpreter continuation.
    #[must_use]
    pub const fn resume_index(&self) -> usize {
        self.step_index
    }

    /// Returns the zero-based v6 step whose execution failed.
    #[must_use]
    pub const fn step_index(&self) -> usize {
        self.step_index
    }
}

impl<RunnerError> Display
    for RegisterMaskedNonGraphicalNativeSequenceExecutionFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "non-graphical v6 sequence step {} failed after {} steps: {}",
            self.step_index, self.completed_steps, self.cause,
        )
    }
}

impl RegisterMaskedNonGraphicalNativeSequenceOutcome {
    /// Returns the number of sequence steps committed before this outcome.
    #[must_use]
    pub const fn completed_steps(self) -> usize {
        match self {
            Self::Applied { steps, .. } => steps,
            Self::GuardMiss { index, .. } => index,
        }
    }

    /// Returns the exact runtime observation at the continuation boundary.
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

/// Executes retained mappings in semantic order without adapter work.
///
/// Complete topology and artifact identity were admitted before loading. Each
/// current-step failure restores that step through the reusable owner contract;
/// already committed prior steps remain committed. Guard miss returns the exact
/// current runtime observation and resume index.
///
/// # Errors
///
/// Returns indexed current-step and committed-prefix failure evidence.
pub fn execute_loaded_register_masked_non_graphical_native_sequence<Runner>(
    loaded: &loaded_sequence::LoadedRegisterMaskedNonGraphicalNativeSequence,
    runner: &mut Runner,
    entry: ProfileMachineObservation,
    buffers: NativeRegionBuffers<'_>,
) -> RegisterMaskedNonGraphicalNativeSequenceExecutionResult<Runner::Error>
where
    Runner: RegisterMaskedNonGraphicalNativeRunner,
{
    use RegisterMaskedNonGraphicalNativeSequenceOutcome as Outcome;

    let (memory, input, output) = buffers.into_parts();
    let mut observation = entry;
    for (index, owner) in loaded.owners().iter().enumerate() {
        let outcome = owner
            .execute(
                runner,
                observation,
                NativeRegionBuffers::new(&mut *memory, input, &mut *output),
            )
            .map_err(|cause| {
                Box::new(
                    RegisterMaskedNonGraphicalNativeSequenceExecutionFailure {
                        cause,
                        completed_steps: index,
                        observation,
                        step_index: index,
                    },
                )
            })?;
        match outcome {
            NativeRegionInvocationOutcome::Applied(next) => {
                observation = next;
            },
            NativeRegionInvocationOutcome::GuardMiss => {
                return Ok(Outcome::GuardMiss { index, observation });
            },
        }
    }
    Ok(Outcome::Applied {
        observation,
        steps: loaded.len(),
    })
}
