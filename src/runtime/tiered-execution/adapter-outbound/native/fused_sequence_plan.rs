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
//   - Exact topology admission for ordered verified fused native regions.
// - Must-Not:
//   - Allocate mappings, invoke runners, own caches, or release executables.
// - Allows:
//   - Inputs: ordered semantically verified fused native object artifacts.
//   - Outputs: immutable region order, exact boundaries, and total outcome.
//   - Side effects: process-local allocation for owned plan evidence only.
// - Split-When:
//   - Loaded ownership, execution, or release gains independent authority.
// - Merge-When:
//   - Fused admission and multi-region topology become one reviewable boundary.
// - Summary:
//   - Admits exact fused-region sequence topology before executable ownership.
// - Description:
//   - Reconstructs each region admission and checks target/profile continuity.
// - Usage:
//   - Build before any future fused loaded-sequence operation.
// - Defaults:
//   - Current reviewed fused-template coverage provides one positive region.
//

//! Exact plan admission for ordered verified fused native regions.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{ProfileMachineObservation, RunOutcome};

use super::direct::VerifiedDirectFusedSequenceObjectArtifact;
use super::fused_sequence::{
    DirectFusedSequenceAdmissionError, admit_fused_direct_sequence,
};

/// Failure while admitting an ordered sequence of verified fused regions.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectFusedNativeSequencePlanError {
    /// One fused artifact's retained admission could not be reconstructed.
    Admission {
        /// Zero-based fused region whose admission failed.
        index: usize,
        /// Exact fused admission failure.
        error: DirectFusedSequenceAdmissionError,
    },
    /// One fused artifact differs from its reconstructed admission identity.
    ArtifactIdentity {
        /// Zero-based fused region whose identity differs.
        index: usize,
    },
    /// A fused region sequence must contain at least one verified artifact.
    Empty,
    /// Adjacent fused-region observations are not byte-exactly continuous.
    ObservationChain {
        /// Zero-based fused region whose entry disagrees with the prior exit.
        index: usize,
    },
    /// One fused region changed canonical profile identity or requirement.
    ProfileMismatch {
        /// Zero-based fused region whose profile differs.
        index: usize,
    },
    /// Total semantic source-step count overflowed host representation.
    StepCountOverflow,
    /// One fused region targets a different host/backend identity.
    TargetMismatch {
        /// Zero-based fused region whose target differs from the first region.
        index: usize,
    },
    /// A terminated fused region was followed by another region.
    TerminationBeforeEnd {
        /// Zero-based non-final fused region that terminated execution.
        index: usize,
    },
}

/// Ordered verified fused artifacts with exact regional boundaries.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DirectFusedNativeSequencePlan {
    artifacts: Vec<VerifiedDirectFusedSequenceObjectArtifact>,
    entry: ProfileMachineObservation,
    exit: ProfileMachineObservation,
    outcome: RunOutcome,
    semantic_steps: usize,
}

impl Display for DirectFusedNativeSequencePlanError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Admission { index, .. } => {
                write!(f, "fused native sequence admission failed at {index}")
            },
            Self::ArtifactIdentity { index } => write!(
                f,
                "fused native sequence artifact identity differs at {index}",
            ),
            Self::Empty => {
                f.write_str("fused native sequence requires a region")
            },
            Self::ObservationChain { index } => write!(
                f,
                "fused native sequence observation chain broke at {index}",
            ),
            Self::ProfileMismatch { index } => {
                write!(f, "fused native sequence profile changed at {index}")
            },
            Self::StepCountOverflow => f.write_str(
                "fused native sequence semantic step count overflowed",
            ),
            Self::TargetMismatch { index } => {
                write!(f, "fused native sequence target changed at {index}")
            },
            Self::TerminationBeforeEnd { index } => write!(
                f,
                "fused native region {index} terminated before sequence end",
            ),
        }
    }
}

impl DirectFusedNativeSequencePlan {
    /// Returns verified fused artifacts in semantic execution order.
    #[must_use]
    pub fn artifacts(&self) -> &[VerifiedDirectFusedSequenceObjectArtifact] {
        &self.artifacts
    }

    /// Returns the exact first fused-region entry observation.
    #[must_use]
    pub const fn entry(&self) -> ProfileMachineObservation {
        self.entry
    }

    /// Returns the exact final fused-region exit observation.
    #[must_use]
    pub const fn exit(&self) -> ProfileMachineObservation {
        self.exit
    }

    /// Returns whether this sequence contains no fused regions.
    #[must_use]
    pub const fn is_empty(&self) -> bool {
        self.artifacts.is_empty()
    }

    /// Returns the number of fused native regions retained by this plan.
    #[must_use]
    pub const fn len(&self) -> usize {
        self.artifacts.len()
    }

    /// Admits exact fused-region topology and reconstructed artifact identity.
    ///
    /// # Errors
    ///
    /// Returns [`DirectFusedNativeSequencePlanError`] for empty, mixed-target,
    /// mixed-profile, discontinuous, prematurely terminated, overflowed, or
    /// identity-drifted input.
    pub fn new(
        artifacts: &[VerifiedDirectFusedSequenceObjectArtifact],
    ) -> Result<Self, DirectFusedNativeSequencePlanError> {
        use DirectFusedNativeSequencePlanError as Error;

        let first = artifacts.first().ok_or(Error::Empty)?;
        let first_admission = reconstructed_admission(first, 0)?;
        let mut previous_exit = None;
        let mut semantic_steps = 0usize;
        for (index, artifact) in artifacts.iter().enumerate() {
            let admission = reconstructed_admission(artifact, index)?;
            if admission.key().target() != first_admission.key().target() {
                return Err(Error::TargetMismatch { index });
            }
            if !same_profile(first_admission.program(), admission.program()) {
                return Err(Error::ProfileMismatch { index });
            }
            let entry = admission.source_plan().entry();
            let exit = admission.source_plan().exit();
            if previous_exit.is_some_and(|previous| previous != entry) {
                return Err(Error::ObservationChain { index });
            }
            let is_final = index == artifacts.len().saturating_sub(1);
            if !is_final && exit.termination.is_some() {
                return Err(Error::TerminationBeforeEnd { index });
            }
            semantic_steps = semantic_steps
                .checked_add(admission.source_plan().len())
                .ok_or(Error::StepCountOverflow)?;
            previous_exit = Some(exit);
        }
        let entry = first_admission.source_plan().entry();
        let exit = previous_exit.ok_or(Error::Empty)?;
        let outcome = exit.termination.map_or(
            RunOutcome::BudgetExhausted { steps: semantic_steps },
            |reason| RunOutcome::Terminated {
                reason,
                steps: semantic_steps,
            },
        );
        Ok(Self {
            artifacts: artifacts.to_vec(),
            entry,
            exit,
            outcome,
            semantic_steps,
        })
    }

    /// Returns the exact complete semantic outcome across all fused regions.
    #[must_use]
    pub const fn outcome(&self) -> RunOutcome {
        self.outcome
    }

    /// Returns the total source-level semantic step count represented.
    #[must_use]
    pub const fn semantic_steps(&self) -> usize {
        self.semantic_steps
    }
}

fn reconstructed_admission(
    artifact: &VerifiedDirectFusedSequenceObjectArtifact,
    index: usize,
) -> Result<
    super::fused_sequence::DirectFusedSequenceAdmission,
    DirectFusedNativeSequencePlanError,
> {
    use DirectFusedNativeSequencePlanError as Error;

    let admission =
        admit_fused_direct_sequence(artifact.admission().source_plan())
            .map_err(|error| Error::Admission { index, error })?;
    if &admission != artifact.admission() || admission.key() != artifact.key() {
        return Err(Error::ArtifactIdentity { index });
    }
    Ok(admission)
}

fn same_profile(
    first: &malbolge::RegionEffectProgram,
    candidate: &malbolge::RegionEffectProgram,
) -> bool {
    candidate.profile_id == first.profile_id
        && candidate.profile_fingerprint == first.profile_fingerprint
        && candidate.profile_requirement == first.profile_requirement
}
