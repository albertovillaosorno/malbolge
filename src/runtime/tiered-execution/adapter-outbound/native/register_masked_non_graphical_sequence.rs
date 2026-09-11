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
//   - Exact non-graphical register-masked v6 sequence plan admission.
// - Must-Not:
//   - Allocate executable mappings, call native runners, own caches, or release
//     executable memory.
// - Allows:
//   - Inputs: ordered v6 one-step programs and verified non-graphical
//     artifacts.
//   - Outputs: immutable admitted topology and exact entry/exit observations.
//   - Side effects: process-local allocation for owned plan evidence only.
// - Split-When:
//   - Loaded ownership, execution, or release gains independent authority.
// - Merge-When:
//   - One reviewed terminal-kind sequence planner safely subsumes both paths.
// - Summary:
//   - Admits exact non-graphical v6 sequence topology before any mapping.
// - Description:
//   - Complete profile, observation, target, and artifact identity are checked
//     before the plan gains reusable admission authority.
// - Usage:
//   - Build an immutable plan before any future loaded-sequence operation.
// - Defaults:
//   - Current terminal-only coverage permits one executable semantic step.
//

//! Exact plan admission for non-graphical register-masked v6 sequences.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{
    EFFECT_IR_REGISTER_MASK_VERSION, ProfileMachineObservation,
    RegisterMaskedRegionEffectProgram,
};

use super::direct::VerifiedRegisterMaskedNonGraphicalNativeObjectArtifact;
use crate::execution_cache::{NativeArtifactKey, NativeIdentityError};

/// Failure while admitting one ordered non-graphical v6 sequence plan.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RegisterMaskedNonGraphicalNativeSequencePlanError {
    /// Verified-artifact count differs from semantic program count.
    ArtifactCount {
        /// Number of semantic programs supplied by the caller.
        programs: usize,
        /// Number of verified artifacts supplied by the caller.
        artifacts: usize,
    },
    /// One verified artifact differs from the exact v6 program at that step.
    ArtifactIdentity {
        /// Zero-based mismatching sequence position.
        index: usize,
    },
    /// A non-graphical sequence must contain at least one semantic step.
    Empty,
    /// Exact v6 native identity could not be reconstructed for one position.
    Identity {
        /// Zero-based sequence position whose identity failed.
        index: usize,
        /// Exact identity-construction failure.
        error: NativeIdentityError,
    },
    /// Adjacent trace observations are not byte-exactly continuous.
    ObservationChain {
        /// Zero-based step whose entry disagrees with the prior exit.
        index: usize,
    },
    /// One step changed canonical profile identity or requirement.
    ProfileMismatch {
        /// Zero-based step whose canonical profile identity changed.
        index: usize,
    },
    /// One candidate is not one complete register-masked v6 effect.
    ProgramShape {
        /// Zero-based structurally invalid step position.
        index: usize,
    },
    /// One verified artifact targets a different host/backend identity.
    TargetMismatch {
        /// Zero-based step whose target differs from the first step.
        index: usize,
    },
    /// A terminated observation was followed by another candidate step.
    TerminationBeforeEnd {
        /// Zero-based non-final step that terminated execution.
        index: usize,
    },
}

/// Ordered non-graphical v6 programs and exact verified artifacts.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RegisterMaskedNonGraphicalNativeSequencePlan {
    artifacts: Vec<VerifiedRegisterMaskedNonGraphicalNativeObjectArtifact>,
    entry: ProfileMachineObservation,
    exit: ProfileMachineObservation,
    programs: Vec<RegisterMaskedRegionEffectProgram>,
}

impl Display for RegisterMaskedNonGraphicalNativeSequencePlanError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::ArtifactCount { artifacts, programs } => write!(
                f,
                "non-graphical v6 sequence has {artifacts} artifacts for \
                 {programs} programs",
            ),
            Self::ArtifactIdentity { index } => write!(
                f,
                "non-graphical v6 sequence artifact identity differs at step \
                 {index}",
            ),
            Self::Empty => f.write_str(
                "non-graphical v6 sequence requires at least one step",
            ),
            Self::Identity { index, .. } => write!(
                f,
                "non-graphical v6 sequence identity failed at step {index}",
            ),
            Self::ObservationChain { index } => write!(
                f,
                "non-graphical v6 sequence observation chain broke at step \
                 {index}",
            ),
            Self::ProfileMismatch { index } => write!(
                f,
                "non-graphical v6 sequence profile changed at step {index}",
            ),
            Self::ProgramShape { index } => write!(
                f,
                "non-graphical v6 sequence step {index} is not one complete \
                 effect",
            ),
            Self::TargetMismatch { index } => write!(
                f,
                "non-graphical v6 sequence target changed at step {index}",
            ),
            Self::TerminationBeforeEnd { index } => write!(
                f,
                "non-graphical v6 step {index} terminated before sequence end",
            ),
        }
    }
}

impl RegisterMaskedNonGraphicalNativeSequencePlan {
    /// Returns exact verified artifacts in semantic execution order.
    #[must_use]
    pub fn artifacts(
        &self,
    ) -> &[VerifiedRegisterMaskedNonGraphicalNativeObjectArtifact] {
        &self.artifacts
    }

    /// Returns the exact trace entry observation retained by this plan.
    #[must_use]
    pub const fn entry(&self) -> ProfileMachineObservation {
        self.entry
    }

    /// Returns the exact trace exit observation retained by this plan.
    #[must_use]
    pub const fn exit(&self) -> ProfileMachineObservation {
        self.exit
    }

    /// Returns whether this sequence contains no semantic steps.
    #[must_use]
    pub const fn is_empty(&self) -> bool {
        self.programs.is_empty()
    }

    /// Returns the number of exact semantic steps retained by this plan.
    #[must_use]
    pub const fn len(&self) -> usize {
        self.programs.len()
    }

    /// Admits complete sequence topology and exact artifact identity.
    ///
    /// The entire semantic chain is checked without granting mapping or runner
    /// authority. Current non-graphical terminal coverage means an executable
    /// plan has one terminal step; a later position after termination fails.
    ///
    /// # Errors
    ///
    /// Returns [`RegisterMaskedNonGraphicalNativeSequencePlanError`] for empty,
    /// malformed, profile/target-mixed, discontinuous, prematurely terminated,
    /// or identity-mismatched input.
    pub fn new(
        programs: &[RegisterMaskedRegionEffectProgram],
        artifacts: &[VerifiedRegisterMaskedNonGraphicalNativeObjectArtifact],
    ) -> Result<Self, RegisterMaskedNonGraphicalNativeSequencePlanError> {
        use RegisterMaskedNonGraphicalNativeSequencePlanError as Error;

        if programs.is_empty() {
            return Err(Error::Empty);
        }
        if programs.len() != artifacts.len() {
            return Err(Error::ArtifactCount {
                programs: programs.len(),
                artifacts: artifacts.len(),
            });
        }
        validate_program_chain(programs)?;
        validate_artifact_chain(programs, artifacts)?;
        let entry = programs
            .first()
            .and_then(|program| program.program.effects.first())
            .map(|effect| effect.before)
            .ok_or(Error::ProgramShape { index: 0 })?;
        let exit_index = programs.len().saturating_sub(1);
        let exit = programs
            .last()
            .and_then(|program| program.program.effects.first())
            .map(|effect| effect.after)
            .ok_or(Error::ProgramShape { index: exit_index })?;
        Ok(Self {
            artifacts: artifacts.to_vec(),
            entry,
            exit,
            programs: programs.to_vec(),
        })
    }

    /// Returns exact register-masked programs in semantic execution order.
    #[must_use]
    pub fn programs(&self) -> &[RegisterMaskedRegionEffectProgram] {
        &self.programs
    }
}

fn validate_program_chain(
    programs: &[RegisterMaskedRegionEffectProgram],
) -> Result<(), RegisterMaskedNonGraphicalNativeSequencePlanError> {
    use RegisterMaskedNonGraphicalNativeSequencePlanError as Error;

    let first = programs.first().ok_or(Error::Empty)?;
    let mut previous_after = None;
    for (index, program) in programs.iter().enumerate() {
        let [effect] = program.program.effects.as_slice() else {
            return Err(Error::ProgramShape { index });
        };
        if program.format_version() != EFFECT_IR_REGISTER_MASK_VERSION
            || program.program.step_budget != 1
            || program.register_writes.len() != 1
        {
            return Err(Error::ProgramShape { index });
        }
        if !same_sequence_profile(first, program) {
            return Err(Error::ProfileMismatch { index });
        }
        if previous_after.is_some_and(|after| after != effect.before) {
            return Err(Error::ObservationChain { index });
        }
        let is_final = index == programs.len().saturating_sub(1);
        if !is_final && effect.after.termination.is_some() {
            return Err(Error::TerminationBeforeEnd { index });
        }
        previous_after = Some(effect.after);
    }
    Ok(())
}

fn validate_artifact_chain(
    programs: &[RegisterMaskedRegionEffectProgram],
    artifacts: &[VerifiedRegisterMaskedNonGraphicalNativeObjectArtifact],
) -> Result<(), RegisterMaskedNonGraphicalNativeSequencePlanError> {
    use RegisterMaskedNonGraphicalNativeSequencePlanError as Error;

    let first_target = artifacts.first().ok_or(Error::Empty)?.key().target();
    for (index, (program, artifact)) in
        programs.iter().zip(artifacts).enumerate()
    {
        if artifact.key().target() != first_target {
            return Err(Error::TargetMismatch { index });
        }
        let expected = NativeArtifactKey::new_register_masked(
            program,
            artifact.key().target().clone(),
        )
        .map_err(|error| Error::Identity { index, error })?;
        if artifact.key() != &expected {
            return Err(Error::ArtifactIdentity { index });
        }
    }
    Ok(())
}

fn same_sequence_profile(
    first: &RegisterMaskedRegionEffectProgram,
    candidate: &RegisterMaskedRegionEffectProgram,
) -> bool {
    candidate.program.profile_id == first.program.profile_id
        && candidate.program.profile_fingerprint
            == first.program.profile_fingerprint
        && candidate.program.profile_requirement
            == first.program.profile_requirement
}
