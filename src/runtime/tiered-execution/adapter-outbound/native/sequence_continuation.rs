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
//   - Exact immutable interpreter-continuation evidence for native sequences.
// - Must-Not:
//   - Invoke the interpreter, retain executable mappings, or infer missing IR.
// - Allows:
//   - Inputs: admitted sequence outcomes/failures and their exact verified
//     plan.
//   - Outputs: validated plan identity, resume state, and remaining suffix.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - Concrete interpreter transfer or scheduler ownership gains policy.
// - Merge-When:
//   - Native execution and interpreter continuation share one coordinator.
// - Summary:
//   - Converts exact native resume evidence into a durable semantic handoff.
// - Description:
//   - Validates progress and observation before cloning remaining programs.
// - Usage:
//   - Build after guard miss or indexed failure, then pass to a future handoff.
// - Defaults:
//   - Completed plans produce no continuation; malformed evidence fails closed.
//

//! Exact semantic continuation objects for native-sequence fallback.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{ProfileMachineObservation, RegionEffectProgram, RunOutcome};

use super::direct::{
    CachedVerifiedDirectSequencePlan, VerifiedDirectSequencePlan,
};
use super::executable_cache::NativeExecutableSequenceKey;
use super::sequence_runner::{
    NativeLoadedSequenceExecutionFailure, NativeSequenceExecutionFailure,
    NativeSequenceExecutionOutcome,
};

/// Why native execution yielded remaining interpreter work.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeInterpreterContinuationReason {
    /// Native execution failed at a validated resumable boundary.
    ExecutionFailure,
    /// One native semantic guard missed without applying its current step.
    GuardMiss,
}

/// Immutable exact semantic suffix for future interpreter execution.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeInterpreterContinuation {
    expected_exit: ProfileMachineObservation,
    expected_outcome: RunOutcome,
    observation: ProfileMachineObservation,
    plan_key: NativeExecutableSequenceKey,
    reason: NativeInterpreterContinuationReason,
    remaining_key: NativeExecutableSequenceKey,
    remaining_programs: Vec<RegionEffectProgram>,
    resume_index: usize,
}

/// Malformed outcome/failure evidence rejected before creating a handoff.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeInterpreterContinuationError {
    /// A completed outcome reported a different final observation.
    AppliedObservation,
    /// A completed outcome reported a different committed-step count.
    AppliedSteps {
        /// Exact number of plan steps.
        expected: usize,
        /// Outcome-reported committed steps.
        observed: usize,
    },
    /// Failure progress disagreed with its resume or failing step.
    FailureProgress {
        /// Number of committed steps reported by the failure.
        completed: usize,
        /// Next semantic step reported by the failure.
        resume: usize,
        /// Transaction step reported by the failure.
        step: usize,
    },
    /// One supposedly verified remaining program was not one effect.
    ProgramShape {
        /// Zero-based malformed plan position.
        index: usize,
    },
    /// Resume index exceeded the complete plan length.
    ResumeIndex {
        /// Reported next semantic step.
        observed: usize,
        /// Exact number of plan steps.
        steps: usize,
    },
    /// Resume observation differed from the exact next program entry.
    ResumeObservation {
        /// Zero-based mismatching resume position.
        index: usize,
    },
}

/// Result of deriving optional interpreter work from admitted native evidence.
pub type NativeInterpreterContinuationResult = Result<
    Option<NativeInterpreterContinuation>,
    NativeInterpreterContinuationError,
>;

struct NativeContinuationPlanView<'plan> {
    expected_exit: ProfileMachineObservation,
    expected_outcome: RunOutcome,
    key: NativeExecutableSequenceKey,
    programs: &'plan [RegionEffectProgram],
}

#[derive(Clone, Copy)]
struct NativeContinuationFailureEvidence {
    completed_steps: usize,
    observation: ProfileMachineObservation,
    resume_index: usize,
    step_index: usize,
}

impl NativeInterpreterContinuation {
    /// Advances this semantic continuation by additional admitted tier steps.
    ///
    /// The returned continuation keeps complete-plan identity and outcome while
    /// rebasing its exact suffix to `additional_steps`. Completing the suffix
    /// returns `None` only when the supplied observation equals the verified
    /// final observation.
    ///
    /// # Errors
    ///
    /// Returns [`NativeInterpreterContinuationError`] when progress exceeds the
    /// remaining suffix, the new boundary observation drifts, or retained
    /// one-step program shape is invalid.
    pub fn advance(
        &self,
        additional_steps: usize,
        observation: ProfileMachineObservation,
        reason: NativeInterpreterContinuationReason,
    ) -> NativeInterpreterContinuationResult {
        let remaining_steps = self.remaining_steps();
        let total_steps = self.resume_index.saturating_add(remaining_steps);
        let Some(resume_index) =
            self.resume_index.checked_add(additional_steps)
        else {
            return Err(NativeInterpreterContinuationError::ResumeIndex {
                observed: usize::MAX,
                steps: total_steps,
            });
        };
        if additional_steps > remaining_steps {
            return Err(NativeInterpreterContinuationError::ResumeIndex {
                observed: resume_index,
                steps: total_steps,
            });
        }
        if additional_steps == remaining_steps {
            if observation == self.expected_exit {
                return Ok(None);
            }
            return Err(NativeInterpreterContinuationError::AppliedObservation);
        }
        validate_resume_observation(
            &self.remaining_programs,
            additional_steps,
            observation,
        )?;
        validate_remaining_programs(
            &self.remaining_programs,
            additional_steps,
        )?;
        let programs = self.remaining_programs.get(additional_steps..).ok_or(
            NativeInterpreterContinuationError::ResumeIndex {
                observed: resume_index,
                steps: total_steps,
            },
        )?;
        let remaining_key = self.remaining_key.suffix(additional_steps).ok_or(
            NativeInterpreterContinuationError::ResumeIndex {
                observed: resume_index,
                steps: total_steps,
            },
        )?;
        Ok(Some(Self {
            expected_exit: self.expected_exit,
            expected_outcome: self.expected_outcome,
            observation,
            plan_key: self.plan_key.clone(),
            reason,
            remaining_key,
            remaining_programs: programs.to_vec(),
            resume_index,
        }))
    }

    /// Returns the number of semantic steps committed before this handoff.
    #[must_use]
    pub const fn completed_steps(&self) -> usize {
        self.resume_index
    }

    /// Returns the exact final observation expected from the complete plan.
    #[must_use]
    pub const fn expected_exit(&self) -> ProfileMachineObservation {
        self.expected_exit
    }

    /// Returns the complete plan's verified regional outcome.
    #[must_use]
    pub const fn expected_outcome(&self) -> RunOutcome {
        self.expected_outcome
    }

    /// Derives optional interpreter work from one cached indexed failure.
    ///
    /// # Errors
    ///
    /// Returns [`NativeInterpreterContinuationError`] when failure progress or
    /// observation disagrees with the exact plan.
    pub fn from_cached_failure<MemoryError, RunnerError>(
        plan: &CachedVerifiedDirectSequencePlan,
        failure: &NativeSequenceExecutionFailure<MemoryError, RunnerError>,
    ) -> NativeInterpreterContinuationResult {
        continuation_from_failure(
            cached_plan_view(plan),
            NativeContinuationFailureEvidence {
                completed_steps: failure.completed_steps(),
                observation: failure.observation(),
                resume_index: failure.resume_index(),
                step_index: failure.step_index(),
            },
        )
    }

    /// Derives optional interpreter work from one cached loaded-chain failure.
    ///
    /// # Errors
    ///
    /// Returns [`NativeInterpreterContinuationError`] when failure progress or
    /// observation disagrees with the exact plan.
    pub fn from_cached_loaded_failure<RunnerError>(
        plan: &CachedVerifiedDirectSequencePlan,
        failure: &NativeLoadedSequenceExecutionFailure<RunnerError>,
    ) -> NativeInterpreterContinuationResult {
        continuation_from_failure(
            cached_plan_view(plan),
            NativeContinuationFailureEvidence {
                completed_steps: failure.completed_steps(),
                observation: failure.observation(),
                resume_index: failure.resume_index(),
                step_index: failure.step_index(),
            },
        )
    }

    /// Derives optional interpreter work from one cached native outcome.
    ///
    /// # Errors
    ///
    /// Returns [`NativeInterpreterContinuationError`] when public outcome
    /// fields disagree with the exact verified plan.
    pub fn from_cached_outcome(
        plan: &CachedVerifiedDirectSequencePlan,
        outcome: NativeSequenceExecutionOutcome,
    ) -> NativeInterpreterContinuationResult {
        continuation_from_outcome(cached_plan_view(plan), outcome)
    }

    /// Derives optional interpreter work from one uncached indexed failure.
    ///
    /// # Errors
    ///
    /// Returns [`NativeInterpreterContinuationError`] when failure progress or
    /// observation disagrees with the exact plan.
    pub fn from_failure<MemoryError, RunnerError>(
        plan: &VerifiedDirectSequencePlan,
        failure: &NativeSequenceExecutionFailure<MemoryError, RunnerError>,
    ) -> NativeInterpreterContinuationResult {
        continuation_from_failure(
            plan_view(plan),
            NativeContinuationFailureEvidence {
                completed_steps: failure.completed_steps(),
                observation: failure.observation(),
                resume_index: failure.resume_index(),
                step_index: failure.step_index(),
            },
        )
    }

    /// Derives optional interpreter work from one uncached loaded-chain
    /// failure.
    ///
    /// # Errors
    ///
    /// Returns [`NativeInterpreterContinuationError`] when failure progress or
    /// observation disagrees with the exact plan.
    pub fn from_loaded_failure<RunnerError>(
        plan: &VerifiedDirectSequencePlan,
        failure: &NativeLoadedSequenceExecutionFailure<RunnerError>,
    ) -> NativeInterpreterContinuationResult {
        continuation_from_failure(
            plan_view(plan),
            NativeContinuationFailureEvidence {
                completed_steps: failure.completed_steps(),
                observation: failure.observation(),
                resume_index: failure.resume_index(),
                step_index: failure.step_index(),
            },
        )
    }

    /// Derives optional interpreter work from one uncached native outcome.
    ///
    /// # Errors
    ///
    /// Returns [`NativeInterpreterContinuationError`] when public outcome
    /// fields disagree with the exact verified plan.
    pub fn from_outcome(
        plan: &VerifiedDirectSequencePlan,
        outcome: NativeSequenceExecutionOutcome,
    ) -> NativeInterpreterContinuationResult {
        continuation_from_outcome(plan_view(plan), outcome)
    }

    /// Returns the exact observation at which interpreter work begins.
    #[must_use]
    pub const fn observation(&self) -> ProfileMachineObservation {
        self.observation
    }

    /// Returns the exact complete ordered artifact identity.
    #[must_use]
    pub const fn plan_key(&self) -> &NativeExecutableSequenceKey {
        &self.plan_key
    }

    /// Returns why the semantic handoff was required.
    #[must_use]
    pub const fn reason(&self) -> NativeInterpreterContinuationReason {
        self.reason
    }

    /// Returns the exact ordered artifact identity still requiring execution.
    #[must_use]
    pub const fn remaining_key(&self) -> &NativeExecutableSequenceKey {
        &self.remaining_key
    }

    /// Returns exact one-step programs still requiring interpreter execution.
    #[must_use]
    pub fn remaining_programs(&self) -> &[RegionEffectProgram] {
        &self.remaining_programs
    }

    /// Returns the number of semantic steps still requiring execution.
    #[must_use]
    pub const fn remaining_steps(&self) -> usize {
        self.remaining_programs.len()
    }

    /// Returns the next zero-based semantic step for interpreter execution.
    #[must_use]
    pub const fn resume_index(&self) -> usize {
        self.resume_index
    }
}

impl Display for NativeInterpreterContinuationError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::AppliedObservation => {
                f.write_str("completed native outcome observation drifted")
            },
            Self::AppliedSteps { expected, observed } => write!(
                f,
                "completed outcome has {observed} of {expected} steps",
            ),
            Self::FailureProgress { completed, resume, step } => write!(
                f,
                "failure progress {completed}/{resume} at step {step}",
            ),
            Self::ProgramShape { index } => write!(
                f,
                "continuation program {index} is not exactly one effect",
            ),
            Self::ResumeIndex { observed, steps } => write!(
                f,
                "native resume index {observed} exceeds {steps} plan steps",
            ),
            Self::ResumeObservation { index } => write!(
                f,
                "native resume observation differs at plan step {index}",
            ),
        }
    }
}

fn cached_plan_view(
    plan: &CachedVerifiedDirectSequencePlan,
) -> NativeContinuationPlanView<'_> {
    NativeContinuationPlanView {
        expected_exit: plan.exit(),
        expected_outcome: plan.outcome(),
        key: NativeExecutableSequenceKey::from_cached_plan(plan),
        programs: plan.programs(),
    }
}

fn continuation_from_failure(
    plan: NativeContinuationPlanView<'_>,
    failure: NativeContinuationFailureEvidence,
) -> NativeInterpreterContinuationResult {
    if failure.completed_steps != failure.resume_index
        || !(failure.step_index == failure.resume_index
            || failure.step_index.saturating_add(1) == failure.resume_index)
    {
        return Err(NativeInterpreterContinuationError::FailureProgress {
            completed: failure.completed_steps,
            resume: failure.resume_index,
            step: failure.step_index,
        });
    }
    let steps = plan.programs.len();
    if failure.resume_index > steps {
        return Err(NativeInterpreterContinuationError::ResumeIndex {
            observed: failure.resume_index,
            steps,
        });
    }
    if failure.resume_index == steps {
        if failure.observation == plan.expected_exit {
            return Ok(None);
        }
        return Err(NativeInterpreterContinuationError::AppliedObservation);
    }
    build_continuation(
        plan,
        failure.resume_index,
        failure.observation,
        NativeInterpreterContinuationReason::ExecutionFailure,
    )
}

fn continuation_from_outcome(
    plan: NativeContinuationPlanView<'_>,
    outcome: NativeSequenceExecutionOutcome,
) -> NativeInterpreterContinuationResult {
    match outcome {
        NativeSequenceExecutionOutcome::Applied { observation, steps } => {
            let expected = plan.programs.len();
            if steps != expected {
                return Err(NativeInterpreterContinuationError::AppliedSteps {
                    expected,
                    observed: steps,
                });
            }
            if observation != plan.expected_exit {
                return Err(
                    NativeInterpreterContinuationError::AppliedObservation,
                );
            }
            Ok(None)
        },
        NativeSequenceExecutionOutcome::GuardMiss { index, observation } => {
            build_continuation(
                plan,
                index,
                observation,
                NativeInterpreterContinuationReason::GuardMiss,
            )
        },
    }
}

fn build_continuation(
    plan: NativeContinuationPlanView<'_>,
    resume_index: usize,
    observation: ProfileMachineObservation,
    reason: NativeInterpreterContinuationReason,
) -> NativeInterpreterContinuationResult {
    let steps = plan.programs.len();
    if resume_index >= steps {
        return Err(NativeInterpreterContinuationError::ResumeIndex {
            observed: resume_index,
            steps,
        });
    }
    validate_resume_observation(plan.programs, resume_index, observation)?;
    validate_remaining_programs(plan.programs, resume_index)?;
    let remaining_programs = plan.programs.get(resume_index..).ok_or(
        NativeInterpreterContinuationError::ResumeIndex {
            observed: resume_index,
            steps,
        },
    )?;
    let remaining_key = plan.key.suffix(resume_index).ok_or(
        NativeInterpreterContinuationError::ResumeIndex {
            observed: resume_index,
            steps,
        },
    )?;
    Ok(Some(NativeInterpreterContinuation {
        expected_exit: plan.expected_exit,
        expected_outcome: plan.expected_outcome,
        observation,
        plan_key: plan.key,
        reason,
        remaining_key,
        remaining_programs: remaining_programs.to_vec(),
        resume_index,
    }))
}

fn plan_view(
    plan: &VerifiedDirectSequencePlan,
) -> NativeContinuationPlanView<'_> {
    NativeContinuationPlanView {
        expected_exit: plan.exit(),
        expected_outcome: plan.outcome(),
        key: NativeExecutableSequenceKey::from_plan(plan),
        programs: plan.programs(),
    }
}

fn validate_remaining_programs(
    programs: &[RegionEffectProgram],
    resume_index: usize,
) -> Result<(), NativeInterpreterContinuationError> {
    for (index, program) in programs.iter().enumerate().skip(resume_index) {
        if program.effects.len() != 1 || program.step_budget != 1 {
            return Err(NativeInterpreterContinuationError::ProgramShape {
                index,
            });
        }
    }
    Ok(())
}

fn validate_resume_observation(
    programs: &[RegionEffectProgram],
    resume_index: usize,
    observation: ProfileMachineObservation,
) -> Result<(), NativeInterpreterContinuationError> {
    let Some(program) = programs.get(resume_index) else {
        return Err(NativeInterpreterContinuationError::ResumeIndex {
            observed: resume_index,
            steps: programs.len(),
        });
    };
    let [effect] = program.effects.as_slice() else {
        return Err(NativeInterpreterContinuationError::ProgramShape {
            index: resume_index,
        });
    };
    if effect.before == observation {
        Ok(())
    } else {
        Err(NativeInterpreterContinuationError::ResumeObservation {
            index: resume_index,
        })
    }
}
