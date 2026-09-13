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
//   - Exact admission of caller-replanned fused native retry regions.
// - Must-Not:
//   - Execute mappings, infer a fused plan, mutate caches, or move VM buffers.
// - Allows:
//   - Inputs: one fused `NativeRetry` suspension and one verified fused plan.
//   - Outputs: an admitted retry owner or ownership-preserving rejection.
//   - Side effects: process-local comparison only.
// - Split-When:
//   - Retry execution, cache acquisition, or fallback routing gains ownership.
// - Merge-When:
//   - One fused coordinator owns retry admission plus execution.
// - Summary:
//   - Binds an exact fused-region plan to one affine scheduler suspension.
// - Description:
//   - Rejects reason, source suffix, region identity, or entry drift first.
// - Usage:
//   - Admit after a fused scheduler yields `NativeRetry` evidence.
// - Defaults:
//   - Mid-region source-step progress has no fabricated fused-region identity.
//

//! Exact admission for caller-replanned fused native retries.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{ProfileMachineObservation, ProfileMachineState};

use super::fused_sequence_plan::DirectFusedNativeSequencePlan;
use super::fused_sequence_scheduler::{
    DirectFusedNativeScheduleStopReason, DirectFusedNativeScheduleSuspension,
};

/// Why one caller-replanned fused retry was rejected before native work.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectFusedNativeRetryAdmissionError {
    /// Replanned entry observation differs from the owned checkpoint.
    EntryObservation,
    /// Replanned ordered fused-region keys differ from remaining authority.
    PlanKeys,
    /// Replanned source programs differ from remaining semantic work.
    PlanPrograms,
    /// The suspension was not explicitly yielded for native retry.
    ScheduleReason {
        /// Exact scheduler reason supplied by the caller.
        observed: DirectFusedNativeScheduleStopReason,
    },
}

/// Rejected fused retry admission retaining every supplied affine owner.
#[derive(Debug, Eq, PartialEq)]
pub struct DirectFusedNativeRetryAdmissionFailure {
    error: DirectFusedNativeRetryAdmissionError,
    plan: DirectFusedNativeSequencePlan,
    suspension: DirectFusedNativeScheduleSuspension,
}

/// Exact verified fused retry plan bound to one affine checkpoint owner.
#[derive(Debug, Eq, PartialEq)]
pub struct DirectFusedNativeRetry {
    plan: DirectFusedNativeSequencePlan,
    suspension: DirectFusedNativeScheduleSuspension,
}

impl Display for DirectFusedNativeRetryAdmissionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::EntryObservation => {
                f.write_str("fused native retry entry differs from checkpoint")
            },
            Self::PlanKeys => {
                f.write_str("fused native retry region keys differ from suffix")
            },
            Self::PlanPrograms => f.write_str(
                "fused native retry source programs differ from suffix",
            ),
            Self::ScheduleReason { observed } => write!(
                f,
                "fused native retry requires native-retry yield, got {}",
                stop_reason_id(*observed),
            ),
        }
    }
}

impl DirectFusedNativeRetry {
    /// Consumes this admission and returns exact suspension plus verified plan.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> (
        DirectFusedNativeScheduleSuspension,
        DirectFusedNativeSequencePlan,
    ) {
        (self.suspension, self.plan)
    }

    /// Admits one verified fused plan against a native-retry suspension.
    ///
    /// # Errors
    ///
    /// Returns [`DirectFusedNativeRetryAdmissionFailure`] while retaining both
    /// supplied owners when reason, source suffix, region keys, or entry
    /// drifts.
    pub fn new(
        suspension: DirectFusedNativeScheduleSuspension,
        plan: DirectFusedNativeSequencePlan,
    ) -> Result<Self, Box<DirectFusedNativeRetryAdmissionFailure>> {
        match retry_admission_error(&suspension, &plan) {
            Some(error) => {
                Err(Box::new(DirectFusedNativeRetryAdmissionFailure {
                    error,
                    plan,
                    suspension,
                }))
            },
            None => Ok(Self { plan, suspension }),
        }
    }

    /// Returns the exact verified fused plan selected for this retry.
    #[must_use]
    pub const fn plan(&self) -> &DirectFusedNativeSequencePlan {
        &self.plan
    }

    /// Returns the exact normative checkpoint owned by this retry.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        self.suspension.state()
    }

    /// Returns the scheduler suspension consumed by this retry admission.
    #[must_use]
    pub const fn suspension(&self) -> &DirectFusedNativeScheduleSuspension {
        &self.suspension
    }
}

impl DirectFusedNativeRetryAdmissionFailure {
    /// Returns the exact retry-admission rejection.
    #[must_use]
    pub const fn error(&self) -> DirectFusedNativeRetryAdmissionError {
        self.error
    }

    /// Consumes this rejection and restores both supplied affine owners.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> (
        DirectFusedNativeScheduleSuspension,
        DirectFusedNativeSequencePlan,
    ) {
        (self.suspension, self.plan)
    }

    /// Returns the rejected verified fused plan.
    #[must_use]
    pub const fn plan(&self) -> &DirectFusedNativeSequencePlan {
        &self.plan
    }

    /// Returns the exact scheduler suspension retained after rejection.
    #[must_use]
    pub const fn suspension(&self) -> &DirectFusedNativeScheduleSuspension {
        &self.suspension
    }
}

fn retry_admission_error(
    suspension: &DirectFusedNativeScheduleSuspension,
    plan: &DirectFusedNativeSequencePlan,
) -> Option<DirectFusedNativeRetryAdmissionError> {
    if suspension.reason() != DirectFusedNativeScheduleStopReason::NativeRetry {
        return Some(DirectFusedNativeRetryAdmissionError::ScheduleReason {
            observed: suspension.reason(),
        });
    }
    if !plan_programs_match(plan, suspension.remaining_programs()) {
        return Some(DirectFusedNativeRetryAdmissionError::PlanPrograms);
    }
    if !plan_keys_match(plan, suspension) {
        return Some(DirectFusedNativeRetryAdmissionError::PlanKeys);
    }
    if plan.entry() != state_observation(suspension.state()) {
        return Some(DirectFusedNativeRetryAdmissionError::EntryObservation);
    }
    None
}

fn plan_keys_match(
    plan: &DirectFusedNativeSequencePlan,
    suspension: &DirectFusedNativeScheduleSuspension,
) -> bool {
    plan.artifacts()
        .iter()
        .map(super::direct::VerifiedDirectFusedSequenceObjectArtifact::key)
        .eq(suspension.continuation().remaining_region_keys())
}

fn plan_programs_match(
    plan: &DirectFusedNativeSequencePlan,
    remaining: &[malbolge::RegionEffectProgram],
) -> bool {
    plan.artifacts()
        .iter()
        .flat_map(|artifact| artifact.admission().source_plan().programs())
        .eq(remaining)
}

fn state_observation(state: &ProfileMachineState) -> ProfileMachineObservation {
    ProfileMachineObservation {
        input_consumed: state.io().input_consumed(),
        output_len: state.io().output().len(),
        registers: state.registers(),
        termination: state.io().termination(),
    }
}

const fn stop_reason_id(
    reason: DirectFusedNativeScheduleStopReason,
) -> &'static str {
    match reason {
        DirectFusedNativeScheduleStopReason::BudgetExhausted => {
            "budget-exhausted"
        },
        DirectFusedNativeScheduleStopReason::CallerYield => "caller-yield",
        DirectFusedNativeScheduleStopReason::NativeRetry => "native-retry",
    }
}
