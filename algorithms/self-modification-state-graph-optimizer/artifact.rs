// File:
//   - artifact.rs
// Path:
//   - algorithms/self-modification-state-graph-optimizer/artifact.rs
//
// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE
// Path-Rule:
//   - All paths in this header are repository-root relative.
//
// Boundary-Contract:
// - Owns:
//   - Portable verifier-admitted effect artifacts for bounded regions.
// - Must-Not:
//   - Trust generated effects, encode host ISA bytes, or replace
//     deoptimization.
// - Allows:
//   - Inputs: verifier-produced regions and untrusted portable effect claims.
//   - Outputs: verified effect artifacts and guarded tier execution results.
//   - Side effects: process-local allocation and normative fallback execution.
// - Split-When:
//   - Split when stable serialization or architecture code artifacts are added.
// - Merge-When:
//   - Merge when `execution/ir/` owns the same verified effect contract.
// - Summary:
//   - Verifies compact region effects before any accelerated execution can use
//     them.
// - Description:
//   - Recomputes portable effects from verified traces and preserves region
//     deopt.
// - Usage:
//   - Research precursor for the portable tiered-execution IR boundary.
// - Defaults:
//   - Generated artifacts are untrusted until exact verifier comparison passes.
//
// Related documents:
// - docs/technical/adr/tiered-native-execution.md
// - docs/technical/adr/verification-trust-boundary.md
//
// Large file:
//   - false

//! Portable untrusted-to-verified region effect artifact boundary.

use malbolge::RunOutcome;

use crate::indexed_state::{IndexedMachineState, IndexedStateEffect};
use crate::region_certificate::{
    ExactRegionError, RegionExecutionTier, RegionMemoryDependency,
    VerifiedExactRegion,
};

const EFFECT_IR_VERSION: u16 = 1;

/// Explicit caller-supplied portable region claim with no verifier authority.
#[derive(Clone, Debug)]
pub struct UntrustedRegionArtifactClaim {
    /// Compact state effects claimed for the verified region.
    pub effects: Vec<IndexedStateEffect>,
    /// Portable effect-IR schema version.
    pub format_version: u16,
    /// Claimed verifier-derived live-in memory dependencies.
    pub memory_dependencies: Vec<RegionMemoryDependency>,
    /// Claimed bounded-run outcome.
    pub outcome: RunOutcome,
    /// Canonical target-profile fingerprint claimed by the artifact.
    pub profile_fingerprint: String,
    /// Claimed semantic-step budget.
    pub step_budget: usize,
}

/// Untrusted portable region artifact requiring verifier comparison.
#[derive(Clone, Debug)]
pub struct UntrustedRegionArtifact {
    claim: UntrustedRegionArtifactClaim,
}

/// Verified portable effect artifact bound to one verifier-produced region.
#[derive(Clone, Debug)]
pub struct VerifiedRegionArtifact {
    effects: Vec<IndexedStateEffect>,
    region: VerifiedExactRegion,
}

/// Result of one verified portable artifact execution request.
#[derive(Clone, Debug)]
pub struct RegionArtifactExecutionResult {
    outcome: RunOutcome,
    state: IndexedMachineState,
    tier: RegionExecutionTier,
}

/// Failure while admitting one untrusted portable region artifact.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RegionArtifactVerificationError {
    /// At least one artifact field differs from verifier-produced evidence.
    VerificationMismatch,
}

impl RegionArtifactExecutionResult {
    /// Returns the bounded outcome produced by artifact or interpreter
    /// fallback.
    #[must_use]
    pub const fn outcome(&self) -> RunOutcome {
        self.outcome
    }

    /// Returns the exact incremental exit state.
    #[must_use]
    pub const fn state(&self) -> &IndexedMachineState {
        &self.state
    }

    /// Returns the tier that executed this request.
    #[must_use]
    pub const fn tier(&self) -> RegionExecutionTier {
        self.tier
    }
}

impl UntrustedRegionArtifact {
    /// Returns the untrusted claim for mutation, transport, or inspection.
    #[must_use]
    pub const fn claim(&self) -> &UntrustedRegionArtifactClaim {
        &self.claim
    }

    /// Builds an explicitly untrusted artifact from caller-supplied fields.
    #[must_use]
    pub const fn from_untrusted_parts(
        claim: UntrustedRegionArtifactClaim,
    ) -> Self {
        Self { claim }
    }

    /// Builds a candidate artifact by projecting one already verified region.
    ///
    /// The returned artifact remains untrusted and must still pass
    /// [`Self::verify_against`] before execution.
    #[must_use]
    pub fn from_verified_region(region: &VerifiedExactRegion) -> Self {
        Self {
            claim: UntrustedRegionArtifactClaim {
                effects: region
                    .traces()
                    .iter()
                    .map(IndexedStateEffect::from_trace)
                    .collect(),
                format_version: EFFECT_IR_VERSION,
                memory_dependencies: region.memory_dependencies().to_vec(),
                outcome: region.outcome(),
                profile_fingerprint: String::from(
                    region.entry().profile_fingerprint(),
                ),
                step_budget: region.step_budget(),
            },
        }
    }

    /// Verifies every portable field against independent region evidence.
    ///
    /// # Errors
    ///
    /// Returns [`RegionArtifactVerificationError::VerificationMismatch`] when
    /// any profile, dependency, outcome, budget, version, or effect differs.
    pub fn verify_against(
        &self,
        region: &VerifiedExactRegion,
    ) -> Result<VerifiedRegionArtifact, RegionArtifactVerificationError> {
        let expected_effects = region
            .traces()
            .iter()
            .map(IndexedStateEffect::from_trace)
            .collect::<Vec<_>>();
        if self.claim.format_version != EFFECT_IR_VERSION
            || self.claim.profile_fingerprint
                != region.entry().profile_fingerprint()
            || self.claim.memory_dependencies != region.memory_dependencies()
            || self.claim.outcome != region.outcome()
            || self.claim.step_budget != region.step_budget()
            || self.claim.effects != expected_effects
        {
            return Err(RegionArtifactVerificationError::VerificationMismatch);
        }
        Ok(VerifiedRegionArtifact {
            effects: expected_effects,
            region: region.clone(),
        })
    }
}

impl VerifiedRegionArtifact {
    /// Executes compact verified effects or deoptimizes normatively on guard
    /// miss.
    ///
    /// # Errors
    ///
    /// Returns [`ExactRegionError`] when dependency inspection, compact effect
    /// application, checkpoint reconstruction, or normative fallback fails.
    pub fn execute_or_deopt(
        &self,
        candidate: &IndexedMachineState,
    ) -> Result<RegionArtifactExecutionResult, ExactRegionError> {
        if !self.region.accepts_dependency_entry(candidate)? {
            let fallback = self.region.execute_or_deopt(candidate)?;
            return Ok(RegionArtifactExecutionResult {
                outcome: fallback.outcome(),
                state: fallback.state().clone(),
                tier: fallback.tier(),
            });
        }
        let mut state = candidate.clone();
        for effect in &self.effects {
            state = state.apply_verified_effect(effect)?;
        }
        Ok(RegionArtifactExecutionResult {
            outcome: self.region.outcome(),
            state,
            tier: RegionExecutionTier::VerifiedShortcut,
        })
    }
}
