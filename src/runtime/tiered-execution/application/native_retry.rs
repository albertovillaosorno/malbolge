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
//   - Exact admission of caller-replanned native continuation suffixes.
// - Must-Not:
//   - Execute mappings, infer a plan, or discard affine checkpoint ownership.
// - Allows:
//   - Inputs: one native-retry suspension and one verified direct plan.
//   - Outputs: an admitted retry owner or a retryable ownership-preserving
//     error.
//   - Side effects: process-local comparison only.
// - Split-When:
//   - Retry execution, cached planning, or fallback policy gains ownership.
// - Merge-When:
//   - One product coordinator owns both retry admission and execution.
// - Summary:
//   - Binds one exact replanned native suffix to its affine checkpoint owner.
// - Description:
//   - Rejects reason, programs, key, or entry drift before buffer movement.
// - Usage:
//   - Admit a scheduler `NativeRetry` suspension before native execution.
// - Defaults:
//   - Every rejection returns both supplied owners unchanged.
//

//! Exact admission for caller-replanned native continuation suffixes.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{ProfileMachineObservation, ProfileMachineState};

use crate::continuation_scheduler::{
    NativeContinuationScheduleStopReason, NativeContinuationScheduleSuspension,
};
use crate::execution_native::{
    NativeExecutableSequenceKey, VerifiedDirectSequencePlan,
};

/// Why one replanned native retry was rejected before buffer movement.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationRetryAdmissionError {
    /// Replanned entry observation differs from the owned checkpoint.
    EntryObservation,
    /// Replanned ordered artifact identity differs from the remaining suffix.
    PlanKey,
    /// Replanned one-step programs differ from the remaining semantic suffix.
    PlanPrograms,
    /// The suspension was not explicitly yielded for native retry.
    ScheduleReason {
        /// Exact scheduler reason supplied by the caller.
        observed: NativeContinuationScheduleStopReason,
    },
}

/// Rejected retry admission retaining every supplied affine owner.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryAdmissionFailure {
    error: NativeContinuationRetryAdmissionError,
    plan: VerifiedDirectSequencePlan,
    suspension: NativeContinuationScheduleSuspension,
}

/// Exact verified native retry plan bound to one affine checkpoint owner.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationNativeRetry {
    plan: VerifiedDirectSequencePlan,
    suspension: NativeContinuationScheduleSuspension,
}

impl Display for NativeContinuationRetryAdmissionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::EntryObservation => {
                f.write_str("native retry plan entry differs from checkpoint")
            },
            Self::PlanKey => {
                f.write_str("native retry plan key differs from suffix")
            },
            Self::PlanPrograms => {
                f.write_str("native retry programs differ from suffix")
            },
            Self::ScheduleReason { observed } => write!(
                f,
                "native retry requires native-retry yield, got {}",
                stop_reason_id(*observed),
            ),
        }
    }
}

impl NativeContinuationNativeRetry {
    /// Consumes this admission and returns exact suspension plus verified plan.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> (
        NativeContinuationScheduleSuspension,
        VerifiedDirectSequencePlan,
    ) {
        (self.suspension, self.plan)
    }

    /// Admits one verified plan against an exact native-retry suspension.
    ///
    /// # Errors
    ///
    /// Returns [`NativeContinuationRetryAdmissionFailure`] while retaining both
    /// supplied owners when reason, program suffix, key, or entry state drifts.
    pub fn new(
        suspension: NativeContinuationScheduleSuspension,
        plan: VerifiedDirectSequencePlan,
    ) -> Result<Self, Box<NativeContinuationRetryAdmissionFailure>> {
        let rejection = retry_admission_error(&suspension, &plan);
        match rejection {
            Some(error) => {
                Err(Box::new(NativeContinuationRetryAdmissionFailure {
                    error,
                    plan,
                    suspension,
                }))
            },
            None => Ok(Self { plan, suspension }),
        }
    }

    /// Returns the exact verified direct plan selected for this retry.
    #[must_use]
    pub const fn plan(&self) -> &VerifiedDirectSequencePlan {
        &self.plan
    }

    /// Returns the exact normative checkpoint owned by this retry.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        self.suspension.state()
    }

    /// Returns the scheduler suspension whose ownership this retry consumes.
    #[must_use]
    pub const fn suspension(&self) -> &NativeContinuationScheduleSuspension {
        &self.suspension
    }
}

impl NativeContinuationRetryAdmissionFailure {
    /// Returns the exact admission rejection.
    #[must_use]
    pub const fn error(&self) -> NativeContinuationRetryAdmissionError {
        self.error
    }

    /// Consumes this failure and restores every supplied affine owner.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> (
        NativeContinuationScheduleSuspension,
        VerifiedDirectSequencePlan,
    ) {
        (self.suspension, self.plan)
    }

    /// Returns the rejected verified direct plan.
    #[must_use]
    pub const fn plan(&self) -> &VerifiedDirectSequencePlan {
        &self.plan
    }

    /// Returns the exact scheduler suspension retained after rejection.
    #[must_use]
    pub const fn suspension(&self) -> &NativeContinuationScheduleSuspension {
        &self.suspension
    }
}

fn retry_admission_error(
    suspension: &NativeContinuationScheduleSuspension,
    plan: &VerifiedDirectSequencePlan,
) -> Option<NativeContinuationRetryAdmissionError> {
    if suspension.reason() != NativeContinuationScheduleStopReason::NativeRetry
    {
        return Some(NativeContinuationRetryAdmissionError::ScheduleReason {
            observed: suspension.reason(),
        });
    }
    if plan.programs() != suspension.remaining_programs() {
        return Some(NativeContinuationRetryAdmissionError::PlanPrograms);
    }
    if NativeExecutableSequenceKey::from_plan(plan)
        != *suspension.remaining_key()
    {
        return Some(NativeContinuationRetryAdmissionError::PlanKey);
    }
    if plan.entry() != state_observation(suspension.state()) {
        return Some(NativeContinuationRetryAdmissionError::EntryObservation);
    }
    None
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
    reason: NativeContinuationScheduleStopReason,
) -> &'static str {
    match reason {
        NativeContinuationScheduleStopReason::BudgetExhausted => {
            "budget-exhausted"
        },
        NativeContinuationScheduleStopReason::CallerYield => "caller-yield",
        NativeContinuationScheduleStopReason::NativeRetry => "native-retry",
    }
}
