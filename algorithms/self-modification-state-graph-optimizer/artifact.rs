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
//   - deoptimization.
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
//   - them.
// - Description:
//   - Recomputes portable effects from verified traces and preserves region
//   - deopt.
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
//

//! Portable untrusted-to-verified region effect artifact boundary.

use malbolge::RunOutcome;

use crate::execution_ir::{
    EFFECT_IR_VERSION, EffectOp, MemoryLiveIn, RegionEffectProgram,
};
use crate::indexed_state::IndexedMachineState;
use crate::region_certificate::{
    ExactRegionError, RegionExecutionTier, VerifiedExactRegion,
};

/// Untrusted portable region artifact requiring verifier comparison.
#[derive(Clone, Debug)]
pub struct UntrustedRegionArtifact {
    program: RegionEffectProgram,
}

/// Verified portable effect artifact bound to one verifier-produced region.
#[derive(Clone, Debug)]
pub struct VerifiedRegionArtifact {
    program: RegionEffectProgram,
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
    /// Builds an explicitly untrusted artifact from caller-supplied IR.
    #[must_use]
    pub const fn from_untrusted_parts(program: RegionEffectProgram) -> Self {
        Self { program }
    }

    /// Builds a candidate artifact by projecting one already verified region.
    ///
    /// The returned artifact remains untrusted and must still pass
    /// [`Self::verify_against`] before execution.
    #[must_use]
    pub fn from_verified_region(region: &VerifiedExactRegion) -> Self {
        Self {
            program: RegionEffectProgram {
                effects: region
                    .traces()
                    .iter()
                    .map(EffectOp::from_trace)
                    .collect(),
                format_version: EFFECT_IR_VERSION,
                memory_live_ins: region
                    .memory_dependencies()
                    .iter()
                    .map(|dependency| MemoryLiveIn {
                        address: dependency.address,
                        value: dependency.value,
                    })
                    .collect(),
                outcome: region.outcome(),
                profile_fingerprint: String::from(
                    region.entry().profile_fingerprint(),
                ),
                profile_id: String::from(region.entry().profile_id()),
                step_budget: region.step_budget(),
            },
        }
    }

    /// Returns the untrusted product-owned IR for transport or mutation.
    #[must_use]
    pub const fn program(&self) -> &RegionEffectProgram {
        &self.program
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
        let expected = RegionEffectProgram {
            effects: region.traces().iter().map(EffectOp::from_trace).collect(),
            format_version: EFFECT_IR_VERSION,
            memory_live_ins: region
                .memory_dependencies()
                .iter()
                .map(|dependency| MemoryLiveIn {
                    address: dependency.address,
                    value: dependency.value,
                })
                .collect(),
            outcome: region.outcome(),
            profile_fingerprint: String::from(
                region.entry().profile_fingerprint(),
            ),
            profile_id: String::from(region.entry().profile_id()),
            step_budget: region.step_budget(),
        };
        if self.program != expected {
            return Err(RegionArtifactVerificationError::VerificationMismatch);
        }
        Ok(VerifiedRegionArtifact {
            program: expected,
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
        for effect in &self.program.effects {
            state = state.apply_verified_effect(effect)?;
        }
        Ok(RegionArtifactExecutionResult {
            outcome: self.region.outcome(),
            state,
            tier: RegionExecutionTier::VerifiedShortcut,
        })
    }
}
