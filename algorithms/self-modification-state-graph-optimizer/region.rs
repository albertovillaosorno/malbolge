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

use std::collections::{BTreeMap, BTreeSet};

use malbolge::{
    ProfileMachine, ProfileMachineError, ProfileMemoryRead, ProfileStepTrace,
    RunOutcome,
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

/// One exact entry-memory value required by a verified region before writes.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RegionMemoryDependency {
    /// Profile-width entry address read before any region write dominates it.
    pub address: u32,
    /// Exact entry value required at that address.
    pub value: u32,
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
    memory_dependencies: Vec<RegionMemoryDependency>,
    outcome: RunOutcome,
    step_budget: usize,
    traces: Vec<ProfileStepTrace>,
}

/// Execution tier selected for one verified bounded region request.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RegionExecutionTier {
    /// The verified dependency guard failed and normative interpretation ran.
    InterpreterFallback,
    /// The verified dependency guard passed and trusted effects were applied.
    VerifiedShortcut,
}

/// Result of one guarded region execution request.
#[derive(Clone, Debug)]
pub struct RegionExecutionResult {
    outcome: RunOutcome,
    state: IndexedMachineState,
    tier: RegionExecutionTier,
}

/// Failure while recording or verifying one exact-state region.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExactRegionError {
    /// A candidate failed the verified reduced dependency guard.
    DependencyGuardMismatch,
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
        let memory_dependencies = derive_memory_dependencies(&replay.traces)?;
        Ok(VerifiedExactRegion {
            entry: self.entry.clone(),
            exit: self.exit.clone(),
            memory_dependencies,
            outcome: self.outcome,
            step_budget: self.step_budget,
            traces: self.traces.clone(),
        })
    }
}

impl RegionExecutionResult {
    /// Returns the bounded execution outcome produced by the selected tier.
    #[must_use]
    pub const fn outcome(&self) -> RunOutcome {
        self.outcome
    }

    /// Returns the exact incremental exit state produced by the selected tier.
    #[must_use]
    pub const fn state(&self) -> &IndexedMachineState {
        &self.state
    }

    /// Returns the tier that actually executed this request.
    #[must_use]
    pub const fn tier(&self) -> RegionExecutionTier {
        self.tier
    }
}

impl VerifiedExactRegion {
    /// Returns whether a candidate satisfies the reduced verified dependency
    /// guard.
    ///
    /// # Errors
    ///
    /// Returns [`ExactRegionError`] when indexed dependency reads fail.
    pub fn accepts_dependency_entry(
        &self,
        candidate: &IndexedMachineState,
    ) -> Result<bool, ExactRegionError> {
        if !self.entry.exact_non_memory_eq(candidate) {
            return Ok(false);
        }
        for dependency in &self.memory_dependencies {
            if candidate.memory_word(dependency.address)? != dependency.value {
                return Ok(false);
            }
        }
        Ok(true)
    }

    /// Returns whether a candidate satisfies the exact entry-state guard.
    #[must_use]
    pub fn accepts_entry(&self, candidate: &IndexedMachineState) -> bool {
        self.entry.exact_state_eq(candidate)
    }

    /// Applies verified region effects after the reduced dependency guard
    /// passes.
    ///
    /// Memory outside verified writes is preserved from the candidate state.
    ///
    /// # Errors
    ///
    /// Returns [`ExactRegionError::DependencyGuardMismatch`] when the candidate
    /// cannot safely reuse this region, or propagates indexed effect failures.
    pub fn apply_dependency_shortcut(
        &self,
        candidate: &IndexedMachineState,
    ) -> Result<IndexedMachineState, ExactRegionError> {
        if !self.accepts_dependency_entry(candidate)? {
            return Err(ExactRegionError::DependencyGuardMismatch);
        }
        let mut state = candidate.clone();
        for trace in &self.traces {
            state = state.apply_verified_trace_effect(trace)?;
        }
        Ok(state)
    }

    /// Executes the verified shortcut or deoptimizes to normative
    /// interpretation.
    ///
    /// A dependency-guard miss is not an error. The fallback replays the same
    /// bounded region from `candidate`, records normative traces, and applies
    /// those traces to the original incremental lineage.
    ///
    /// # Errors
    ///
    /// Returns [`ExactRegionError`] when dependency inspection, checkpoint
    /// reconstruction, normative execution, or incremental trace application
    /// fails.
    pub fn execute_or_deopt(
        &self,
        candidate: &IndexedMachineState,
    ) -> Result<RegionExecutionResult, ExactRegionError> {
        if self.accepts_dependency_entry(candidate)? {
            return Ok(RegionExecutionResult {
                outcome: self.outcome,
                state: self.apply_dependency_shortcut(candidate)?,
                tier: RegionExecutionTier::VerifiedShortcut,
            });
        }
        let mut machine =
            ProfileMachine::from_snapshot(candidate.materialize_checkpoint()?);
        let mut traces = Vec::new();
        let outcome = machine.run_traced(
            self.step_budget,
            &mut |trace: &ProfileStepTrace| {
                traces.push(*trace);
            },
        )?;
        let mut state = candidate.clone();
        for trace in &traces {
            state = state.apply_trace(trace)?;
        }
        Ok(RegionExecutionResult {
            outcome,
            state,
            tier: RegionExecutionTier::InterpreterFallback,
        })
    }

    /// Returns the exact verified exit state produced by normative execution.
    #[must_use]
    pub const fn exit(&self) -> &IndexedMachineState {
        &self.exit
    }

    /// Returns the verified entry-memory live-in dependency set.
    #[must_use]
    pub fn memory_dependencies(&self) -> &[RegionMemoryDependency] {
        &self.memory_dependencies
    }

    /// Returns the exact verified bounded-run outcome.
    #[must_use]
    pub const fn outcome(&self) -> RunOutcome {
        self.outcome
    }

    /// Returns the verifier-recorded semantic step budget for this region.
    #[must_use]
    pub const fn step_budget(&self) -> usize {
        self.step_budget
    }

    /// Returns the normative trace sequence a shortcut must preserve.
    #[must_use]
    pub fn traces(&self) -> &[ProfileStepTrace] {
        &self.traces
    }
}

fn add_live_in_read(
    dependencies: &mut BTreeMap<u32, u32>,
    written: &BTreeSet<u32>,
    read: ProfileMemoryRead,
) -> Result<(), ExactRegionError> {
    if written.contains(&read.address) {
        return Ok(());
    }
    if let Some(previous) = dependencies.get(&read.address) {
        if *previous != read.value {
            return Err(ExactRegionError::VerificationMismatch);
        }
        return Ok(());
    }
    let _previous = dependencies.insert(read.address, read.value);
    Ok(())
}

fn derive_memory_dependencies(
    traces: &[ProfileStepTrace],
) -> Result<Vec<RegionMemoryDependency>, ExactRegionError> {
    let mut dependencies = BTreeMap::<u32, u32>::new();
    let mut written = BTreeSet::<u32>::new();
    for trace in traces {
        for read in [
            trace.memory_reads.fetch,
            trace.memory_reads.data,
            trace.memory_reads.encryption,
        ]
        .into_iter()
        .flatten()
        {
            add_live_in_read(&mut dependencies, &written, read)?;
        }
        for write in [trace.memory_delta.data, trace.memory_delta.encryption]
            .into_iter()
            .flatten()
        {
            let _inserted = written.insert(write.address);
        }
    }
    Ok(dependencies
        .into_iter()
        .map(|(address, value)| RegionMemoryDependency { address, value })
        .collect())
}
