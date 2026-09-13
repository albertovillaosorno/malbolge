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
//   - Exact ordered fused-region leases bound to one admitted sequence plan.
// - Must-Not:
//   - Mutate cache policy, allocate/release mappings, or schedule continuation.
// - Allows:
//   - Inputs: admitted fused plan, caller-owned exact resident leases, runner,
//     and buffers.
//   - Outputs: admitted leased sequence, execution progress, or retained
//     leases.
//   - Side effects: native runner calls through already-resident leases only.
// - Split-When:
//   - Cache acquisition rollback or continuation policy gains separate rules.
// - Merge-When:
//   - One reviewed cache coordinator owns acquisition and leased execution.
// - Summary:
//   - Executes exact fused sequence leases without memory-adapter work.
// - Description:
//   - Admission failure returns every supplied lease without changing
//     residency.
// - Usage:
//   - Acquire region leases, bind them to a plan, execute, then return leases.
// - Defaults:
//   - Ordered lease keys must exactly equal ordered admitted artifact keys.
//

//! Exact lease-backed execution for admitted fused native sequences.

use std::fmt::{Display, Formatter, Result as FormatResult};

use super::fused_lease_cache::DirectFusedNativeLease;
use super::fused_sequence_execution::{
    DirectFusedNativeSequenceExecutionFailure,
    DirectFusedNativeSequenceExecutionOutcome,
    DirectFusedNativeSequenceExecutionResult,
};
use super::fused_sequence_plan::DirectFusedNativeSequencePlan;
use super::invocation::{NativeRegionBuffers, NativeRegionInvocationOutcome};
use super::runner::DirectFusedNativeRunner;

/// Exact lease topology disagreement for one admitted fused sequence.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectFusedNativeLeasedSequenceAdmissionError {
    /// Lease count differs from admitted fused-region count.
    LeaseCount {
        /// Exact admitted fused-region count.
        expected: usize,
        /// Supplied resident lease count.
        observed: usize,
    },
    /// One lease key differs from the admitted artifact at the same position.
    LeaseIdentity {
        /// Zero-based fused-region position whose key disagreed.
        index: usize,
    },
}

/// Failed leased-sequence admission retaining every caller-owned lease.
#[derive(Debug)]
pub struct DirectFusedNativeLeasedSequenceAdmissionFailure {
    error: DirectFusedNativeLeasedSequenceAdmissionError,
    leases: Vec<DirectFusedNativeLease>,
}

/// Exact admitted fused sequence plus immutable resident leases.
#[derive(Debug)]
pub struct DirectFusedNativeLeasedSequence {
    leases: Vec<DirectFusedNativeLease>,
    plan: DirectFusedNativeSequencePlan,
}

type AdmissionError = DirectFusedNativeLeasedSequenceAdmissionError;
type AdmissionFailure = DirectFusedNativeLeasedSequenceAdmissionFailure;

impl Display for DirectFusedNativeLeasedSequenceAdmissionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::LeaseCount { expected, observed } => {
                write!(f, "leased sequence expected {expected}, got {observed}")
            },
            Self::LeaseIdentity { index } => write!(
                f,
                "fused leased sequence identity differs at region {index}",
            ),
        }
    }
}

impl DirectFusedNativeLeasedSequenceAdmissionFailure {
    /// Returns the exact lease-topology rejection.
    #[must_use]
    pub const fn error(&self) -> DirectFusedNativeLeasedSequenceAdmissionError {
        self.error
    }

    /// Consumes the rejection and returns every supplied lease unchanged.
    #[must_use]
    pub fn into_leases(self) -> Vec<DirectFusedNativeLease> {
        self.leases
    }

    /// Returns all leases retained by this failed admission.
    #[must_use]
    pub fn leases(&self) -> &[DirectFusedNativeLease] {
        &self.leases
    }
}

impl DirectFusedNativeLeasedSequence {
    /// Executes retained fused leases in exact semantic order.
    ///
    /// Current-region failure rolls back that whole fused region through the
    /// resident-owner contract; prior committed regions remain committed.
    ///
    /// # Errors
    ///
    /// Returns indexed fused-region and source semantic-step failure evidence.
    pub fn execute<Runner>(
        &self,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> DirectFusedNativeSequenceExecutionResult<Runner::Error>
    where
        Runner: DirectFusedNativeRunner,
    {
        use DirectFusedNativeSequenceExecutionOutcome as Outcome;

        let (memory, input, output) = buffers.into_parts();
        let mut completed_steps = 0usize;
        let mut observation = self.plan.entry();
        for (region_index, (artifact, lease)) in
            self.plan.artifacts().iter().zip(&self.leases).enumerate()
        {
            let region_steps = artifact.admission().source_plan().len();
            let outcome = lease
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
                    completed_steps =
                        completed_steps.saturating_add(region_steps);
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
            regions: self.leases.len(),
            semantic_steps: completed_steps,
        })
    }

    /// Consumes this sequence and returns every exact region lease in order.
    #[must_use]
    pub fn into_leases(self) -> Vec<DirectFusedNativeLease> {
        self.leases
    }

    /// Returns whether this admitted leased sequence contains no regions.
    #[must_use]
    pub const fn is_empty(&self) -> bool {
        self.leases.is_empty()
    }

    /// Returns the number of retained fused-region leases.
    #[must_use]
    pub const fn len(&self) -> usize {
        self.leases.len()
    }

    /// Admits exact ordered leases against one already-admitted fused plan.
    ///
    /// # Errors
    ///
    /// Returns count or ordered-key rejection while retaining every supplied
    /// lease for the caller.
    pub fn new(
        plan: &DirectFusedNativeSequencePlan,
        leases: Vec<DirectFusedNativeLease>,
    ) -> Result<Self, Box<AdmissionFailure>> {
        if leases.len() != plan.len() {
            return Err(Box::new(AdmissionFailure {
                error: AdmissionError::LeaseCount {
                    expected: plan.len(),
                    observed: leases.len(),
                },
                leases,
            }));
        }
        for (index, (artifact, lease)) in
            plan.artifacts().iter().zip(&leases).enumerate()
        {
            if artifact.key() != lease.key() {
                return Err(Box::new(AdmissionFailure {
                    error: AdmissionError::LeaseIdentity { index },
                    leases,
                }));
            }
        }
        Ok(Self {
            leases,
            plan: plan.clone(),
        })
    }

    /// Returns the exact admitted fused plan bound to these leases.
    #[must_use]
    pub const fn plan(&self) -> &DirectFusedNativeSequencePlan {
        &self.plan
    }
}
