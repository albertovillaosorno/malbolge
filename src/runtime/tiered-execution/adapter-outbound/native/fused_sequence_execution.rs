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
//   - Ordered runner execution for already-loaded fused native sequences.
// - Must-Not:
//   - Allocate, release, cache, or alter admitted fused sequence topology.
// - Allows:
//   - Inputs: loaded fused owner, dedicated fused runner, and caller buffers.
//   - Outputs: exact region/semantic progress or indexed current-region
//     failure.
//   - Side effects: native runner calls through retained executable mappings.
// - Split-When:
//   - Fused continuation policy or cache scheduling gains independent
//     ownership.
// - Merge-When:
//   - One reviewed fused coordinator safely owns load and execution.
// - Summary:
//   - Executes retained fused mappings without memory-adapter work.
// - Description:
//   - Current-region failure rolls back that region while prior regions remain.
// - Usage:
//   - Execute one already-loaded fused sequence, then release it separately.
// - Defaults:
//   - Guard miss resumes before the complete current fused region.
//

//! Ordered execution for already-loaded fused native sequence plans.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::ProfileMachineObservation;

use super::invocation::{NativeRegionBuffers, NativeRegionInvocationOutcome};
use super::runner::DirectFusedNativeRunner;
use super::{
    fused_loaded_sequence as loaded_sequence, fused_resident as resident,
};

/// Admitted result of executing one loaded fused native sequence.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectFusedNativeSequenceExecutionOutcome {
    /// Every fused region applied exactly.
    Applied {
        /// Exact final runtime observation after all committed regions.
        observation: ProfileMachineObservation,
        /// Number of committed fused regions.
        regions: usize,
        /// Number of committed source semantic steps.
        semantic_steps: usize,
    },
    /// One fused-region guard missed without applying that region.
    GuardMiss {
        /// Zero-based fused region at which execution may resume.
        region_index: usize,
        /// Source semantic-step index at the region entry.
        resume_step: usize,
        /// Exact runtime observation at the region entry.
        observation: ProfileMachineObservation,
    },
}

/// Indexed fused-region failure with exact committed-prefix evidence.
#[derive(Debug, Eq, PartialEq)]
pub struct DirectFusedNativeSequenceExecutionFailure<RunnerError> {
    cause: Box<resident::DirectFusedNativeOwnerExecutionFailure<RunnerError>>,
    completed_regions: usize,
    completed_steps: usize,
    observation: ProfileMachineObservation,
    region_index: usize,
    resume_step: usize,
}

/// Result of executing one already-loaded fused native sequence.
pub type DirectFusedNativeSequenceExecutionResult<RunnerError> = Result<
    DirectFusedNativeSequenceExecutionOutcome,
    Box<DirectFusedNativeSequenceExecutionFailure<RunnerError>>,
>;

impl<RunnerError> DirectFusedNativeSequenceExecutionFailure<RunnerError> {
    /// Returns the number of fused regions committed before failure.
    #[must_use]
    pub const fn completed_regions(&self) -> usize {
        self.completed_regions
    }

    /// Returns the number of source semantic steps committed before failure.
    #[must_use]
    pub const fn completed_steps(&self) -> usize {
        self.completed_steps
    }

    /// Returns the exact current-region owner execution failure.
    #[must_use]
    pub const fn execution_failure(
        &self,
    ) -> &resident::DirectFusedNativeOwnerExecutionFailure<RunnerError> {
        &self.cause
    }

    pub(super) const fn new(
        cause: Box<
            resident::DirectFusedNativeOwnerExecutionFailure<RunnerError>,
        >,
        completed_regions: usize,
        completed_steps: usize,
        observation: ProfileMachineObservation,
    ) -> Self {
        Self {
            cause,
            completed_regions,
            completed_steps,
            observation,
            region_index: completed_regions,
            resume_step: completed_steps,
        }
    }

    /// Returns the exact runtime observation at the failed region entry.
    #[must_use]
    pub const fn observation(&self) -> ProfileMachineObservation {
        self.observation
    }

    /// Returns the zero-based fused region whose execution failed.
    #[must_use]
    pub const fn region_index(&self) -> usize {
        self.region_index
    }

    /// Returns the source semantic-step index for continuation.
    #[must_use]
    pub const fn resume_step(&self) -> usize {
        self.resume_step
    }
}

impl<RunnerError: Display> Display
    for DirectFusedNativeSequenceExecutionFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "fused sequence region {} failed after {} regions / {} steps: {}",
            self.region_index,
            self.completed_regions,
            self.completed_steps,
            self.cause,
        )
    }
}

impl DirectFusedNativeSequenceExecutionOutcome {
    /// Returns the number of fused regions committed before this outcome.
    #[must_use]
    pub const fn completed_regions(self) -> usize {
        match self {
            Self::Applied { regions, .. } => regions,
            Self::GuardMiss { region_index, .. } => region_index,
        }
    }

    /// Returns the number of source semantic steps committed before this
    /// outcome.
    #[must_use]
    pub const fn completed_steps(self) -> usize {
        match self {
            Self::Applied { semantic_steps, .. } => semantic_steps,
            Self::GuardMiss { resume_step, .. } => resume_step,
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

    /// Returns the fused-region continuation index.
    #[must_use]
    pub const fn resume_region(self) -> usize {
        match self {
            Self::Applied { regions, .. } => regions,
            Self::GuardMiss { region_index, .. } => region_index,
        }
    }

    /// Returns the source semantic-step continuation index.
    #[must_use]
    pub const fn resume_step(self) -> usize {
        match self {
            Self::Applied { semantic_steps, .. } => semantic_steps,
            Self::GuardMiss { resume_step, .. } => resume_step,
        }
    }
}

/// Executes retained fused mappings in semantic order without adapter work.
///
/// Complete topology and artifact identity were admitted before loading. Each
/// current-region runner/completion failure restores that complete fused region
/// through the reusable owner contract; already committed prior regions remain
/// committed. Guard miss returns the exact region-entry observation and source
/// semantic-step resume index.
///
/// # Errors
///
/// Returns indexed current-region failure with exact committed fused-region and
/// source semantic-step prefix evidence.
pub fn execute_loaded_direct_fused_native_sequence<Runner>(
    loaded: &loaded_sequence::LoadedDirectFusedNativeSequence,
    runner: &mut Runner,
    buffers: NativeRegionBuffers<'_>,
) -> DirectFusedNativeSequenceExecutionResult<Runner::Error>
where
    Runner: DirectFusedNativeRunner,
{
    use DirectFusedNativeSequenceExecutionOutcome as Outcome;

    let (memory, input, output) = buffers.into_parts();
    let mut completed_steps = 0usize;
    let mut observation = loaded.plan().entry();
    for (region_index, owner) in loaded.owners().iter().enumerate() {
        let region_steps = owner.artifact().admission().source_plan().len();
        let outcome = owner
            .execute(
                runner,
                NativeRegionBuffers::new(&mut *memory, input, &mut *output),
            )
            .map_err(|cause| {
                Box::new(DirectFusedNativeSequenceExecutionFailure::new(
                    cause,
                    region_index,
                    completed_steps,
                    observation,
                ))
            })?;
        match outcome {
            NativeRegionInvocationOutcome::Applied(next) => {
                observation = next;
                completed_steps = completed_steps.saturating_add(region_steps);
            },
            NativeRegionInvocationOutcome::GuardMiss => {
                return Ok(Outcome::GuardMiss {
                    region_index,
                    resume_step: completed_steps,
                    observation,
                });
            },
        }
    }
    Ok(Outcome::Applied {
        observation,
        regions: loaded.len(),
        semantic_steps: completed_steps,
    })
}
