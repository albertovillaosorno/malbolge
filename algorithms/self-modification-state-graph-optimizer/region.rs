// File:
//   - region.rs
// Path:
//   - algorithms/self-modification-state-graph-optimizer/region.rs
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
//   - Exact-state guarded region certificates for future native shortcuts.
// - Must-Not:
//   - Treat digest equality as a guard or trust unverified certificate
//     contents.
// - Allows:
//   - Inputs: incremental exact states, bounded normative VM execution, traces.
//   - Outputs: untrusted certificates and verifier-produced exact regions.
//   - Side effects: verifier-local allocation and normative VM execution only.
// - Split-When:
//   - Split when broader dependency guards or native code artifacts gain
//     ownership.
// - Merge-When:
//   - Merge when a production tiered execution engine owns region verification.
// - Summary:
//   - Certifies bounded VM regions under exact entry-state guards.
// - Description:
//   - Re-executes normative VM traces before a shortcut can become trusted.
// - Usage:
//   - Foundation for guarded native/JIT region specialization and
//     deoptimization.
// - Defaults:
//   - Rejected VM transitions are never admitted as verified shortcuts.
//
// Related documents:
// - docs/technical/adr/verification-trust-boundary.md
// - math/algorithms/self-modification-state-graph-optimizer.tex
//
// Large file:
//   - false

//! Deterministically verified exact-state region certificates.

use malbolge::{
    ProfileMachine, ProfileMachineError, ProfileStepTrace, RunOutcome,
};

use crate::indexed_state::{IndexedMachineState, IndexedStateError};

/// Untrusted bounded-region claim requiring normative re-execution.
#[derive(Clone, Debug)]
pub struct ExactRegionCertificate {
    entry: IndexedMachineState,
    exit: IndexedMachineState,
    outcome: RunOutcome,
    step_budget: usize,
    traces: Vec<ProfileStepTrace>,
}

/// Explicit caller-supplied region claim with no verifier authority.
#[derive(Clone, Debug)]
pub struct UntrustedExactRegionClaim {
    /// Claimed exact entry state.
    pub entry: IndexedMachineState,
    /// Claimed exact exit state.
    pub exit: IndexedMachineState,
    /// Claimed bounded-run outcome.
    pub outcome: RunOutcome,
    /// Claimed semantic-step budget.
    pub step_budget: usize,
    /// Claimed normative trace sequence.
    pub traces: Vec<ProfileStepTrace>,
}

/// Verified exact-state region safe to reuse only under its exact entry guard.
#[derive(Clone, Debug)]
pub struct VerifiedExactRegion {
    entry: IndexedMachineState,
    exit: IndexedMachineState,
    outcome: RunOutcome,
    traces: Vec<ProfileStepTrace>,
}

/// Failure while recording or verifying one exact-state region.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExactRegionError {
    /// Normative execution rejected a requested transition.
    Machine(ProfileMachineError),
    /// Incremental state evolution or checkpoint reconstruction failed.
    State(IndexedStateError),
    /// Re-execution disagreed with one or more untrusted certificate fields.
    VerificationMismatch,
}

impl From<IndexedStateError> for ExactRegionError {
    fn from(error: IndexedStateError) -> Self {
        Self::State(error)
    }
}

impl From<ProfileMachineError> for ExactRegionError {
    fn from(error: ProfileMachineError) -> Self {
        Self::Machine(error)
    }
}

impl ExactRegionCertificate {
    /// Returns the exact incremental entry-state claim.
    #[must_use]
    pub const fn entry(&self) -> &IndexedMachineState {
        &self.entry
    }

    /// Returns the exact incremental exit-state claim.
    #[must_use]
    pub const fn exit(&self) -> &IndexedMachineState {
        &self.exit
    }

    /// Builds an explicitly untrusted certificate from caller-supplied fields.
    #[must_use]
    pub fn from_untrusted_parts(claim: UntrustedExactRegionClaim) -> Self {
        Self {
            entry: claim.entry,
            exit: claim.exit,
            outcome: claim.outcome,
            step_budget: claim.step_budget,
            traces: claim.traces,
        }
    }

    /// Returns the claimed bounded-run outcome.
    #[must_use]
    pub const fn outcome(&self) -> RunOutcome {
        self.outcome
    }

    /// Records one candidate region using the normative profile VM.
    ///
    /// Recording does not cross the verifier trust boundary; callers must still
    /// invoke [`Self::verify`] before treating the certificate as a shortcut.
    ///
    /// # Errors
    ///
    /// Returns [`ExactRegionError`] when checkpoint reconstruction, normative
    /// execution, or incremental trace application fails.
    pub fn record(
        entry: &IndexedMachineState,
        step_budget: usize,
    ) -> Result<Self, ExactRegionError> {
        let mut machine =
            ProfileMachine::from_snapshot(entry.materialize_checkpoint()?);
        let mut traces = Vec::new();
        let outcome = machine.run_traced(
            step_budget,
            &mut |trace: &ProfileStepTrace| {
                traces.push(*trace);
            },
        )?;
        let mut exit = entry.clone();
        for trace in &traces {
            exit = exit.apply_trace(trace)?;
        }
        Ok(Self {
            entry: entry.clone(),
            exit,
            outcome,
            step_budget,
            traces,
        })
    }

    /// Returns the requested semantic-step budget carried by this certificate.
    #[must_use]
    pub const fn step_budget(&self) -> usize {
        self.step_budget
    }

    /// Returns all exact normative trace claims in execution order.
    #[must_use]
    pub fn traces(&self) -> &[ProfileStepTrace] {
        &self.traces
    }

    /// Re-executes the normative VM and promotes this claim only on exact
    /// match.
    ///
    /// # Errors
    ///
    /// Returns [`ExactRegionError::VerificationMismatch`] when outcome, traces,
    /// or exact exit state differ from normative replay. Runtime/state failures
    /// are propagated as typed errors.
    pub fn verify(&self) -> Result<VerifiedExactRegion, ExactRegionError> {
        let replay = Self::record(&self.entry, self.step_budget)?;
        if replay.outcome != self.outcome
            || replay.traces != self.traces
            || !replay.exit.exact_state_eq(&self.exit)
        {
            return Err(ExactRegionError::VerificationMismatch);
        }
        Ok(VerifiedExactRegion {
            entry: self.entry.clone(),
            exit: self.exit.clone(),
            outcome: self.outcome,
            traces: self.traces.clone(),
        })
    }
}

impl VerifiedExactRegion {
    /// Returns whether a candidate satisfies the exact entry-state guard.
    #[must_use]
    pub fn accepts_entry(&self, candidate: &IndexedMachineState) -> bool {
        self.entry.exact_state_eq(candidate)
    }

    /// Returns the exact verified exit state produced by normative execution.
    #[must_use]
    pub const fn exit(&self) -> &IndexedMachineState {
        &self.exit
    }

    /// Returns the exact verified bounded-run outcome.
    #[must_use]
    pub const fn outcome(&self) -> RunOutcome {
        self.outcome
    }

    /// Returns the normative trace sequence a shortcut must preserve.
    #[must_use]
    pub fn traces(&self) -> &[ProfileStepTrace] {
        &self.traces
    }
}
