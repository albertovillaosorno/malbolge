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
//   - Exact immutable semantic continuation evidence at fused-region
//     boundaries.
// - Must-Not:
//   - Invoke interpreters/runners, retain leases, or infer partial fused
//     regions.
// - Allows:
//   - Inputs: admitted fused plan plus exact sequence outcome/failure evidence.
//   - Outputs: validated region/source-step resume state and semantic suffix.
//   - Side effects: process-local allocation for owned continuation evidence.
// - Split-When:
//   - Interpreter transfer, partial-region advance, or scheduler policy
//     appears.
// - Merge-When:
//   - One coordinator owns fused native execution and semantic fallback.
// - Summary:
//   - Converts fused native resume evidence into an exact semantic handoff.
// - Description:
//   - Continuations begin only at exact fused-region entry observations.
// - Usage:
//   - Build after fused GuardMiss or indexed execution failure.
// - Defaults:
//   - Completed execution produces no continuation; malformed evidence fails.
//

//! Semantic continuation evidence for fused native sequence fallback.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{
    ProfileExecutionGeometry, ProfileMachineObservation, RegionEffectProgram,
    RunOutcome, TargetProfileRequirement, target_profile,
};

use super::direct::VerifiedDirectFusedSequenceObjectArtifact;
use super::fused_sequence_execution::{
    DirectFusedNativeSequenceExecutionFailure,
    DirectFusedNativeSequenceExecutionOutcome,
};
use super::fused_sequence_plan::DirectFusedNativeSequencePlan;
use crate::execution_cache::NativeArtifactKey;

/// Why fused native execution yielded remaining semantic work.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectFusedNativeContinuationReason {
    /// Native execution failed at an exact fused-region entry boundary.
    ExecutionFailure,
    /// A fused region guard missed before applying that complete region.
    GuardMiss,
}

/// Immutable semantic suffix beginning at one exact fused-region entry.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DirectFusedNativeContinuation {
    complete_region_keys: Vec<NativeArtifactKey>,
    expected_exit: ProfileMachineObservation,
    expected_outcome: RunOutcome,
    geometry: ProfileExecutionGeometry,
    observation: ProfileMachineObservation,
    reason: DirectFusedNativeContinuationReason,
    remaining_programs: Vec<RegionEffectProgram>,
    remaining_region_keys: Vec<NativeArtifactKey>,
    resume_region: usize,
    resume_step: usize,
}

/// Malformed fused outcome/failure evidence rejected before semantic handoff.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectFusedNativeContinuationError {
    /// Retry plan no longer matches this continuation's exact semantic suffix.
    AdvancePlanIdentity,
    /// Completed outcome reported a different final observation.
    AppliedObservation,
    /// Completed outcome reported a different fused-region count.
    AppliedRegions {
        /// Exact admitted fused-region count.
        expected: usize,
        /// Outcome-reported committed regions.
        observed: usize,
    },
    /// Completed outcome reported a different source semantic-step count.
    AppliedSteps {
        /// Exact admitted source semantic-step count.
        expected: usize,
        /// Outcome-reported committed source steps.
        observed: usize,
    },
    /// Failure/retry progress differs from an exact fused-region boundary.
    FailureProgress,
    /// Retained profile identity no longer resolves canonically.
    ProfileIdentity,
    /// Absolute region or source-step progress overflowed host indexing.
    ProgressOverflow,
    /// Resume observation differs from the exact fused-region entry.
    ResumeObservation {
        /// Zero-based fused region at the rejected boundary.
        region: usize,
    },
    /// Resume fused-region index is outside the admitted plan.
    ResumeRegion {
        /// Reported fused-region continuation index.
        observed: usize,
        /// Exact admitted fused-region count.
        regions: usize,
    },
    /// Resume source semantic-step index differs from the region boundary.
    ResumeStep {
        /// Exact source-step offset of the fused-region boundary.
        expected: usize,
        /// Reported source semantic-step continuation index.
        observed: usize,
    },
}

/// Result of deriving optional remaining semantic work from fused execution.
pub type DirectFusedNativeContinuationResult = Result<
    Option<DirectFusedNativeContinuation>,
    DirectFusedNativeContinuationError,
>;

type DirectFusedAdvanceIndicesResult =
    Result<(usize, usize), DirectFusedNativeContinuationError>;

#[derive(Clone, Copy)]
struct DirectFusedContinuationResume {
    observation: ProfileMachineObservation,
    reason: DirectFusedNativeContinuationReason,
    region: usize,
    step: usize,
}

#[derive(Clone, Copy)]
pub(super) struct DirectFusedContinuationAdvance {
    pub(super) completed_regions: usize,
    pub(super) completed_steps: usize,
    pub(super) observation: ProfileMachineObservation,
    pub(super) reason: DirectFusedNativeContinuationReason,
}

impl DirectFusedNativeContinuation {
    /// Rebases this continuation across exact complete fused retry regions.
    ///
    /// This boundary never advances through a partial fused region. The retry
    /// plan must exactly equal the continuation's current region/program
    /// suffix.
    pub(super) fn advance_regions(
        &self,
        plan: &DirectFusedNativeSequencePlan,
        advance: DirectFusedContinuationAdvance,
    ) -> DirectFusedNativeContinuationResult {
        if !retry_plan_matches(self, plan) {
            return Err(
                DirectFusedNativeContinuationError::AdvancePlanIdentity,
            );
        }
        let (resume_region, resume_step) =
            validated_advance_indices(self, plan, advance)?;
        if advance.completed_regions == plan.len() {
            if advance.observation != self.expected_exit
                || resume_step != outcome_steps(self.expected_outcome)
            {
                return Err(
                    DirectFusedNativeContinuationError::AppliedObservation,
                );
            }
            return Ok(None);
        }
        let Some(next) = plan.artifacts().get(advance.completed_regions) else {
            return Err(DirectFusedNativeContinuationError::FailureProgress);
        };
        if advance.observation != next.admission().source_plan().entry() {
            return Err(
                DirectFusedNativeContinuationError::ResumeObservation {
                    region: resume_region,
                },
            );
        }
        let remaining_programs = self
            .remaining_programs
            .get(advance.completed_steps..)
            .ok_or(DirectFusedNativeContinuationError::FailureProgress)?
            .to_vec();
        let remaining_region_keys = self
            .remaining_region_keys
            .get(advance.completed_regions..)
            .ok_or(DirectFusedNativeContinuationError::FailureProgress)?
            .to_vec();
        Ok(Some(Self {
            complete_region_keys: self.complete_region_keys.clone(),
            expected_exit: self.expected_exit,
            expected_outcome: self.expected_outcome,
            geometry: self.geometry,
            observation: advance.observation,
            reason: advance.reason,
            remaining_programs,
            remaining_region_keys,
            resume_region,
            resume_step,
        }))
    }

    /// Returns exact complete fused-region artifact identity in plan order.
    #[must_use]
    pub fn complete_region_keys(&self) -> &[NativeArtifactKey] {
        &self.complete_region_keys
    }

    /// Returns the exact final observation expected from the complete plan.
    #[must_use]
    pub const fn expected_exit(&self) -> ProfileMachineObservation {
        self.expected_exit
    }

    /// Returns the complete plan's exact semantic outcome.
    #[must_use]
    pub const fn expected_outcome(&self) -> RunOutcome {
        self.expected_outcome
    }

    /// Derives semantic fallback from one indexed fused execution failure.
    ///
    /// # Errors
    ///
    /// Returns [`DirectFusedNativeContinuationError`] when failure progress or
    /// observation disagrees with the exact admitted fused plan.
    pub fn from_failure<RunnerError>(
        plan: &DirectFusedNativeSequencePlan,
        failure: &DirectFusedNativeSequenceExecutionFailure<RunnerError>,
    ) -> DirectFusedNativeContinuationResult {
        if failure.completed_regions() != failure.region_index()
            || failure.completed_steps() != failure.resume_step()
        {
            return Err(DirectFusedNativeContinuationError::FailureProgress);
        }
        build_continuation(plan, DirectFusedContinuationResume {
            observation: failure.observation(),
            reason: DirectFusedNativeContinuationReason::ExecutionFailure,
            region: failure.region_index(),
            step: failure.resume_step(),
        })
    }

    /// Derives semantic fallback from one admitted fused execution outcome.
    ///
    /// # Errors
    ///
    /// Returns [`DirectFusedNativeContinuationError`] when public outcome
    /// fields disagree with the exact admitted fused plan.
    pub fn from_outcome(
        plan: &DirectFusedNativeSequencePlan,
        outcome: DirectFusedNativeSequenceExecutionOutcome,
    ) -> DirectFusedNativeContinuationResult {
        match outcome {
            DirectFusedNativeSequenceExecutionOutcome::Applied {
                observation,
                regions,
                semantic_steps,
            } => {
                if regions != plan.len() {
                    return Err(
                        DirectFusedNativeContinuationError::AppliedRegions {
                            expected: plan.len(),
                            observed: regions,
                        },
                    );
                }
                if semantic_steps != plan.semantic_steps() {
                    return Err(
                        DirectFusedNativeContinuationError::AppliedSteps {
                            expected: plan.semantic_steps(),
                            observed: semantic_steps,
                        },
                    );
                }
                if observation != plan.exit() {
                    return Err(
                        DirectFusedNativeContinuationError::AppliedObservation,
                    );
                }
                Ok(None)
            },
            DirectFusedNativeSequenceExecutionOutcome::GuardMiss {
                region_index,
                resume_step,
                observation,
            } => build_continuation(plan, DirectFusedContinuationResume {
                observation,
                reason: DirectFusedNativeContinuationReason::GuardMiss,
                region: region_index,
                step: resume_step,
            }),
        }
    }

    /// Returns the exact canonical execution geometry retained for fallback.
    #[must_use]
    pub const fn geometry(&self) -> ProfileExecutionGeometry {
        self.geometry
    }

    /// Returns the exact observation where remaining semantic work begins.
    #[must_use]
    pub const fn observation(&self) -> ProfileMachineObservation {
        self.observation
    }

    /// Returns why semantic fallback is required.
    #[must_use]
    pub const fn reason(&self) -> DirectFusedNativeContinuationReason {
        self.reason
    }

    /// Returns verified one-step source programs still requiring execution.
    #[must_use]
    pub fn remaining_programs(&self) -> &[RegionEffectProgram] {
        &self.remaining_programs
    }

    /// Returns exact fused-region keys still beginning at this boundary.
    #[must_use]
    pub fn remaining_region_keys(&self) -> &[NativeArtifactKey] {
        &self.remaining_region_keys
    }

    /// Returns the number of remaining verified source semantic steps.
    #[must_use]
    pub const fn remaining_steps(&self) -> usize {
        self.remaining_programs.len()
    }

    /// Returns the next zero-based fused-region index.
    #[must_use]
    pub const fn resume_region(&self) -> usize {
        self.resume_region
    }

    /// Returns the next zero-based source semantic-step index.
    #[must_use]
    pub const fn resume_step(&self) -> usize {
        self.resume_step
    }
}

impl Display for DirectFusedNativeContinuationError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::AppliedObservation => {
                f.write_str("completed fused outcome observation drifted")
            },
            Self::AppliedRegions { expected, observed } => write!(
                f,
                "completed fused outcome has {observed} of {expected} regions",
            ),
            Self::AppliedSteps { expected, observed } => write!(
                f,
                "completed fused outcome has {observed} of {expected} steps",
            ),
            Self::AdvancePlanIdentity => {
                f.write_str("fused continuation retry plan identity drifted")
            },
            Self::FailureProgress => {
                f.write_str("fused execution failure progress drifted")
            },
            Self::ProfileIdentity => {
                f.write_str("fused continuation profile identity unavailable")
            },
            Self::ProgressOverflow => {
                f.write_str("fused continuation progress overflowed")
            },
            Self::ResumeObservation { region } => {
                write!(f, "fused resume observation differs at {region}")
            },
            Self::ResumeRegion { observed, regions } => write!(
                f,
                "fused resume region {observed} exceeds {regions} regions",
            ),
            Self::ResumeStep { expected, observed } => write!(
                f,
                "fused resume step {observed} differs from {expected}",
            ),
        }
    }
}

fn build_continuation(
    plan: &DirectFusedNativeSequencePlan,
    resume: DirectFusedContinuationResume,
) -> DirectFusedNativeContinuationResult {
    let Some(artifact) = plan.artifacts().get(resume.region) else {
        return Err(DirectFusedNativeContinuationError::ResumeRegion {
            observed: resume.region,
            regions: plan.len(),
        });
    };
    let expected_step = semantic_step_offset(plan, resume.region);
    if resume.step != expected_step {
        return Err(DirectFusedNativeContinuationError::ResumeStep {
            expected: expected_step,
            observed: resume.step,
        });
    }
    if resume.observation != artifact.admission().source_plan().entry() {
        return Err(DirectFusedNativeContinuationError::ResumeObservation {
            region: resume.region,
        });
    }
    let complete_region_keys = plan
        .artifacts()
        .iter()
        .map(|item| item.key().clone())
        .collect();
    let remaining_artifacts = plan.artifacts().get(resume.region..).ok_or(
        DirectFusedNativeContinuationError::ResumeRegion {
            observed: resume.region,
            regions: plan.len(),
        },
    )?;
    let remaining_region_keys = remaining_artifacts
        .iter()
        .map(|item| item.key().clone())
        .collect();
    let remaining_programs = remaining_artifacts
        .iter()
        .flat_map(|item| {
            item.admission().source_plan().programs().iter().cloned()
        })
        .collect();
    Ok(Some(DirectFusedNativeContinuation {
        complete_region_keys,
        expected_exit: plan.exit(),
        expected_outcome: plan.outcome(),
        geometry: canonical_geometry(plan)?,
        observation: resume.observation,
        reason: resume.reason,
        remaining_programs,
        remaining_region_keys,
        resume_region: resume.region,
        resume_step: resume.step,
    }))
}

fn canonical_geometry(
    plan: &DirectFusedNativeSequencePlan,
) -> Result<ProfileExecutionGeometry, DirectFusedNativeContinuationError> {
    let first = plan
        .artifacts()
        .first()
        .ok_or(DirectFusedNativeContinuationError::ProfileIdentity)?;
    let source = first.admission().source_plan();
    let program = source
        .programs()
        .first()
        .ok_or(DirectFusedNativeContinuationError::ProfileIdentity)?;
    let Some(profile) = target_profile(&program.profile_id) else {
        return Err(DirectFusedNativeContinuationError::ProfileIdentity);
    };
    if profile.fingerprint() != program.profile_fingerprint
        || TargetProfileRequirement::from_descriptor(profile)
            != program.profile_requirement
    {
        return Err(DirectFusedNativeContinuationError::ProfileIdentity);
    }
    Ok(ProfileExecutionGeometry::canonical(profile))
}

fn validated_advance_indices(
    continuation: &DirectFusedNativeContinuation,
    plan: &DirectFusedNativeSequencePlan,
    advance: DirectFusedContinuationAdvance,
) -> DirectFusedAdvanceIndicesResult {
    if advance.completed_regions > plan.len() {
        return Err(DirectFusedNativeContinuationError::FailureProgress);
    }
    let expected_steps = plan
        .artifacts()
        .iter()
        .take(advance.completed_regions)
        .map(|artifact| artifact.admission().source_plan().len())
        .sum::<usize>();
    if advance.completed_steps != expected_steps {
        return Err(DirectFusedNativeContinuationError::FailureProgress);
    }
    let resume_region = continuation
        .resume_region
        .checked_add(advance.completed_regions)
        .ok_or(DirectFusedNativeContinuationError::ProgressOverflow)?;
    let resume_step = continuation
        .resume_step
        .checked_add(advance.completed_steps)
        .ok_or(DirectFusedNativeContinuationError::ProgressOverflow)?;
    Ok((resume_region, resume_step))
}

const fn outcome_steps(outcome: RunOutcome) -> usize {
    match outcome {
        RunOutcome::BudgetExhausted { steps }
        | RunOutcome::Terminated { steps, .. } => steps,
    }
}

fn retry_plan_matches(
    continuation: &DirectFusedNativeContinuation,
    plan: &DirectFusedNativeSequencePlan,
) -> bool {
    let keys_match = plan
        .artifacts()
        .iter()
        .map(VerifiedDirectFusedSequenceObjectArtifact::key)
        .eq(continuation.remaining_region_keys.iter());
    let programs_match = plan
        .artifacts()
        .iter()
        .flat_map(|artifact| artifact.admission().source_plan().programs())
        .eq(continuation.remaining_programs.iter());
    keys_match && programs_match
}

fn semantic_step_offset(
    plan: &DirectFusedNativeSequencePlan,
    resume_region: usize,
) -> usize {
    plan.artifacts()
        .iter()
        .take(resume_region)
        .map(|artifact| artifact.admission().source_plan().len())
        .sum()
}
