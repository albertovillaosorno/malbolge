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
//   - Atomic publication of verified multistep direct-native plans.
// - Must-Not:
//   - Infer omitted semantic reads, admit hidden deopt steps, or execute code.
// - Allows:
//   - Inputs: exact one-step portable programs and explicit host capability.
//   - Outputs: ordered verified direct artifacts with exact region boundaries.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - Cached transactions or executable chaining gain independent ownership.
// - Merge-When:
//   - One-step and multistep planning become the same reviewable authority.
// - Summary:
//   - Verifies and composes exact one-step artifacts without partial
//     publication.
// - Description:
//   - Checks profile and observation continuity before publishing all steps.
// - Usage:
//   - Called after VM trace evidence is projected to exact one-step IR.
// - Defaults:
//   - Empty, discontinuous, profile-mixed, or deoptimizing sequences fail
//     closed.
//

//! Verified multistep direct-native planning.

use super::plan::{PreparedDirectTarget, prepare_verified_direct_target};
use super::*;

/// Failure while composing exact one-step programs into one direct sequence.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum DirectSequenceError<'requirement> {
    /// One step would select the deoptimization stub rather than a fast path.
    Deoptimization {
        /// Zero-based failing sequence position.
        index: usize,
    },
    /// A direct sequence must contain at least one step.
    Empty,
    /// Adjacent before/after observations are not byte-exactly continuous.
    ObservationChain {
        /// Zero-based step whose entry disagrees with the prior exit.
        index: usize,
    },
    /// One step changed canonical profile identity or geometry.
    ProfileMismatch {
        /// Zero-based step whose canonical profile identity changed.
        index: usize,
    },
    /// One candidate is not represented by exactly one portable effect.
    ProgramShape {
        /// Zero-based structurally invalid step position.
        index: usize,
    },
    /// One exact step failed ordinary direct selection or verification.
    Step {
        /// Zero-based step whose ordinary direct selection failed.
        index: usize,
        /// Exact typed one-step selection or verification failure.
        error: Box<DirectSelectionError<'requirement>>,
    },
    /// A terminated observation was followed by another candidate step.
    TerminationBeforeEnd {
        /// Zero-based non-final step that terminated execution.
        index: usize,
    },
}

impl Display for DirectSequenceError<'_> {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Deoptimization { index } => {
                write!(
                    f,
                    "direct sequence step {index} selected deoptimization"
                )
            },
            Self::Empty => {
                f.write_str("direct sequence requires at least one step")
            },
            Self::ObservationChain { index } => write!(
                f,
                "direct sequence observation chain broke at step {index}",
            ),
            Self::ProgramShape { index } => {
                write!(f, "direct sequence step {index} is not one effect")
            },
            Self::ProfileMismatch { index } => {
                write!(f, "direct sequence profile changed at step {index}")
            },
            Self::Step { error, index } => {
                write!(f, "direct sequence step {index} failed: {error}")
            },
            Self::TerminationBeforeEnd { index } => write!(
                f,
                "direct sequence step {index} terminated before the final step",
            ),
        }
    }
}

/// Ordered direct artifacts whose exact one-step boundaries form one region.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedDirectSequencePlan {
    artifacts: Vec<VerifiedDirectNativeArtifact>,
    entry: ProfileMachineObservation,
    exit: ProfileMachineObservation,
    outcome: RunOutcome,
    programs: Vec<RegionEffectProgram>,
}

impl VerifiedDirectSequencePlan {
    /// Returns all verified one-step artifacts in execution order.
    #[must_use]
    pub fn artifacts(&self) -> &[VerifiedDirectNativeArtifact] {
        &self.artifacts
    }

    /// Returns the exact first-step entry observation.
    #[must_use]
    pub const fn entry(&self) -> ProfileMachineObservation {
        self.entry
    }

    /// Returns the exact final-step exit observation.
    #[must_use]
    pub const fn exit(&self) -> ProfileMachineObservation {
        self.exit
    }

    /// Returns whether the plan contains no direct artifacts.
    ///
    /// Verified plans are always non-empty; this method completes the standard
    /// collection-style inspection surface.
    #[must_use]
    pub const fn is_empty(&self) -> bool {
        self.artifacts.is_empty()
    }

    /// Returns the number of semantic steps represented by this plan.
    #[must_use]
    pub const fn len(&self) -> usize {
        self.artifacts.len()
    }

    /// Returns the exact regional outcome derived from the final observation.
    #[must_use]
    pub const fn outcome(&self) -> RunOutcome {
        self.outcome
    }

    /// Returns exact one-step programs paired with the ordered artifacts.
    #[must_use]
    pub fn programs(&self) -> &[RegionEffectProgram] {
        &self.programs
    }
}

/// Cache-aware ordered direct artifacts for one exact multistep region.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CachedVerifiedDirectSequencePlan {
    artifacts: Vec<Arc<VerifiedDirectNativeArtifact>>,
    cache_hits: usize,
    cache_insertions: usize,
    entry: ProfileMachineObservation,
    exit: ProfileMachineObservation,
    outcome: RunOutcome,
    programs: Vec<RegionEffectProgram>,
}

impl CachedVerifiedDirectSequencePlan {
    /// Returns all exact cached or newly verified artifacts in execution order.
    #[must_use]
    pub fn artifacts(&self) -> &[Arc<VerifiedDirectNativeArtifact>] {
        &self.artifacts
    }

    /// Returns the number of sequence positions resolved from the entry cache.
    #[must_use]
    pub const fn cache_hits(&self) -> usize {
        self.cache_hits
    }

    /// Returns the number of unique verified artifacts inserted atomically.
    #[must_use]
    pub const fn cache_insertions(&self) -> usize {
        self.cache_insertions
    }

    /// Returns the exact first-step entry observation.
    #[must_use]
    pub const fn entry(&self) -> ProfileMachineObservation {
        self.entry
    }

    /// Returns the exact final-step exit observation.
    #[must_use]
    pub const fn exit(&self) -> ProfileMachineObservation {
        self.exit
    }

    /// Returns whether the plan contains no direct artifacts.
    #[must_use]
    pub const fn is_empty(&self) -> bool {
        self.artifacts.is_empty()
    }

    /// Returns the number of semantic steps represented by this plan.
    #[must_use]
    pub const fn len(&self) -> usize {
        self.artifacts.len()
    }

    /// Returns the exact regional outcome derived from the final observation.
    #[must_use]
    pub const fn outcome(&self) -> RunOutcome {
        self.outcome
    }

    /// Returns exact one-step programs paired with the ordered artifacts.
    #[must_use]
    pub fn programs(&self) -> &[RegionEffectProgram] {
        &self.programs
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct DirectSequenceBoundary {
    entry: ProfileMachineObservation,
    exit: ProfileMachineObservation,
    outcome: RunOutcome,
}

#[derive(Clone, Debug)]
struct StagedDirectArtifact {
    artifact: Arc<VerifiedDirectNativeArtifact>,
    key: NativeArtifactKey,
}

/// Selects and verifies every exact one-step artifact before publishing a plan.
///
/// The caller must project complete VM trace evidence into one-step portable
/// programs first. Compact regional IR cannot be split here because it omits
/// intermediate semantic reads by design.
///
/// # Errors
///
/// Returns [`DirectSequenceError`] when the sequence is empty, discontinuous,
/// profile-mixed, structurally non-unit, selects deoptimization, or any step
/// fails normal direct selection and semantic admission.
pub fn select_verified_direct_sequence<'requirement>(
    programs: &'requirement [RegionEffectProgram],
    runtime: &'static RuntimeCapability,
    host_os: HostOperatingSystem,
    host_isa: HostIsa,
) -> Result<VerifiedDirectSequencePlan, DirectSequenceError<'requirement>> {
    let boundary = validate_sequence(programs)?;
    let mut artifacts = Vec::with_capacity(programs.len());
    for (index, program) in programs.iter().enumerate() {
        let prepared = prepare_sequence_target(
            program,
            runtime,
            DirectHost::new(host_os, host_isa),
            index,
        )?;
        artifacts.push(prepared.emit_verified(program).map_err(|error| {
            DirectSequenceError::Step {
                index,
                error: Box::new(error),
            }
        })?);
    }
    Ok(VerifiedDirectSequencePlan {
        artifacts,
        entry: boundary.entry,
        exit: boundary.exit,
        outcome: boundary.outcome,
        programs: programs.to_vec(),
    })
}

/// Selects one cache-aware exact direct sequence with atomic cache publication.
///
/// Exact entry-cache hits preserve their existing [`Arc`] identity. Every miss
/// is emitted and semantically verified into local staging; unique misses enter
/// the caller-owned cache only after all sequence positions succeed.
///
/// # Errors
///
/// Returns [`DirectSequenceError`] under the same fail-closed conditions as
/// [`select_verified_direct_sequence`]. Any failure leaves `cache` unchanged.
pub fn select_cached_verified_direct_sequence<'requirement>(
    programs: &'requirement [RegionEffectProgram],
    runtime: &'static RuntimeCapability,
    host: DirectHost,
    cache: &mut VerifiedDirectNativeCache,
) -> Result<CachedVerifiedDirectSequencePlan, DirectSequenceError<'requirement>>
{
    let boundary = validate_sequence(programs)?;
    let mut prepared = Vec::with_capacity(programs.len());
    for (index, program) in programs.iter().enumerate() {
        prepared.push(prepare_sequence_target(program, runtime, host, index)?);
    }

    let mut artifacts = Vec::with_capacity(programs.len());
    let mut cache_hits = 0usize;
    let mut staged = Vec::<StagedDirectArtifact>::new();
    for (index, (program, target)) in programs.iter().zip(prepared).enumerate()
    {
        if let Some(artifact) = cache.entries.get(target.key()) {
            cache_hits = cache_hits.saturating_add(1);
            artifacts.push(Arc::clone(artifact));
            continue;
        }
        if let Some(existing) = staged
            .iter()
            .find(|candidate| candidate.key == *target.key())
        {
            artifacts.push(Arc::clone(&existing.artifact));
            continue;
        }
        let key = target.key().clone();
        let artifact =
            Arc::new(target.emit_verified(program).map_err(|error| {
                DirectSequenceError::Step {
                    index,
                    error: Box::new(error),
                }
            })?);
        staged.push(StagedDirectArtifact {
            artifact: Arc::clone(&artifact),
            key,
        });
        artifacts.push(artifact);
    }

    let cache_insertions = staged.len();
    for item in staged {
        let _replaced = cache.entries.insert(item.key, item.artifact);
    }
    Ok(CachedVerifiedDirectSequencePlan {
        artifacts,
        cache_hits,
        cache_insertions,
        entry: boundary.entry,
        exit: boundary.exit,
        outcome: boundary.outcome,
        programs: programs.to_vec(),
    })
}

fn prepare_sequence_target<'requirement>(
    program: &'requirement RegionEffectProgram,
    runtime: &'static RuntimeCapability,
    host: DirectHost,
    index: usize,
) -> Result<PreparedDirectTarget, DirectSequenceError<'requirement>> {
    let prepared = prepare_verified_direct_target(
        program,
        runtime,
        host.operating_system,
        host.isa,
    )
    .map_err(|error| DirectSequenceError::Step {
        index,
        error: Box::new(error),
    })?;
    if prepared.is_deoptimization() {
        Err(DirectSequenceError::Deoptimization { index })
    } else {
        Ok(prepared)
    }
}

fn validate_sequence(
    programs: &[RegionEffectProgram],
) -> Result<DirectSequenceBoundary, DirectSequenceError<'_>> {
    let Some(first) = programs.first() else {
        return Err(DirectSequenceError::Empty);
    };
    let first_effect = one_effect(first, 0)?;
    let mut previous_after = None;
    for (index, program) in programs.iter().enumerate() {
        let effect = one_effect(program, index)?;
        if !same_sequence_profile(first, program) {
            return Err(DirectSequenceError::ProfileMismatch { index });
        }
        if previous_after.is_some_and(|after| after != effect.before) {
            return Err(DirectSequenceError::ObservationChain { index });
        }
        let is_final = index == programs.len().saturating_sub(1);
        if !is_final && effect.after.termination.is_some() {
            return Err(DirectSequenceError::TerminationBeforeEnd { index });
        }
        previous_after = Some(effect.after);
    }
    let exit = previous_after.ok_or(DirectSequenceError::Empty)?;
    let outcome = exit.termination.map_or(
        RunOutcome::BudgetExhausted { steps: programs.len() },
        |reason| RunOutcome::Terminated {
            reason,
            steps: programs.len(),
        },
    );
    Ok(DirectSequenceBoundary {
        entry: first_effect.before,
        exit,
        outcome,
    })
}

const fn one_effect(
    program: &RegionEffectProgram,
    index: usize,
) -> Result<EffectOp, DirectSequenceError<'_>> {
    let [effect] = program.effects.as_slice() else {
        return Err(DirectSequenceError::ProgramShape { index });
    };
    if program.step_budget != 1 {
        return Err(DirectSequenceError::ProgramShape { index });
    }
    Ok(*effect)
}

fn same_sequence_profile(
    first: &RegionEffectProgram,
    candidate: &RegionEffectProgram,
) -> bool {
    candidate.profile_id == first.profile_id
        && candidate.profile_fingerprint == first.profile_fingerprint
        && candidate.profile_requirement == first.profile_requirement
}
