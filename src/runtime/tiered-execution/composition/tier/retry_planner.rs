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
//   - Exact host planning of one affine native-retry suspension.
// - Must-Not:
//   - Convert profile, IR, emission, or verification failures into fallback.
// - Allows:
//   - Inputs: native-retry suspension, runtime capability, and explicit host.
//   - Outputs: admitted native retry, normative handoff, or owned hard failure.
//   - Side effects: process-local verified direct artifact allocation only.
// - Split-When:
//   - Cache-aware planning or retry-attempt budgets gain policy.
// - Merge-When:
//   - Product orchestration owns planning, execution, and fallback atomically.
// - Summary:
//   - Plans exact retry suffixes and falls back only for missing target format.
// - Description:
//   - Retains suspension ownership across every hard planning rejection.
// - Usage:
//   - Call after the scheduler yields an exact `NativeRetry` suspension.
// - Defaults:
//   - Unsupported host format falls back; every other failure remains hard.
//

//! Exact host planning for one affine native continuation retry.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::RuntimeCapability;

use crate::continuation_scheduler::{
    NativeContinuationScheduleStopReason, NativeContinuationScheduleSuspension,
};
use crate::execution_cache::{HostIsa, HostOperatingSystem};
use crate::execution_native::{
    DirectSelectionError, DirectSequenceError, VerifiedDirectSequencePlan,
    select_verified_direct_sequence,
};
use crate::interpreter_handoff::NativeInterpreterHandoff;
use crate::native_retry::{
    NativeContinuationNativeRetry, NativeContinuationRetryAdmissionError,
};

/// One exact route selected for a native-retry suspension.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationRetryPlanningOutcome {
    /// Native target format is absent; continue normatively instead.
    Interpreter(Box<NativeInterpreterHandoff>),
    /// The host admitted the exact suffix as a verified native retry.
    Native(Box<NativeContinuationNativeRetry>),
}

/// Stable hard failure while planning one native retry suffix.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationRetryPlanningError {
    /// Exact post-planning retry admission unexpectedly failed.
    Admission(NativeContinuationRetryAdmissionError),
    /// One step selected the deoptimization stub.
    Deoptimization {
        /// Zero-based failing suffix position.
        index: usize,
    },
    /// The retained suffix unexpectedly contained no work.
    Empty,
    /// Adjacent observations were not exactly continuous.
    ObservationChain {
        /// Zero-based failing suffix position.
        index: usize,
    },
    /// Canonical profile identity changed inside the suffix.
    ProfileMismatch {
        /// Zero-based failing suffix position.
        index: usize,
    },
    /// One retained candidate was not one complete portable effect.
    ProgramShape {
        /// Zero-based failing suffix position.
        index: usize,
    },
    /// The suspension was not yielded for native retry.
    ScheduleReason {
        /// Exact observed scheduling reason.
        observed: NativeContinuationScheduleStopReason,
    },
    /// One exact step failed direct selection or verification.
    Step {
        /// Stable direct-selection failure class.
        cause: NativeContinuationRetryStepPlanningError,
        /// Zero-based failing suffix position.
        index: usize,
    },
    /// A terminating step was followed by another retained step.
    TerminationBeforeEnd {
        /// Zero-based terminating suffix position.
        index: usize,
    },
}

/// Stable owned class for one hard direct-step planning failure.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationRetryStepPlanningError {
    /// Crazy-operation direct selection or verification failed.
    Crazy,
    /// Deoptimization artifact selection or verification failed.
    Deoptimization,
    /// Graphical halt-fetch selection or verification failed.
    HaltFetch,
    /// Arbitrary-register halt selection or verification failed.
    HaltRegisters,
    /// Initial-halt selection or verification failed.
    InitialHalt,
    /// Input selection or verification failed.
    Input,
    /// Jump-code selection or verification failed.
    JumpCode,
    /// Jump-data selection or verification failed.
    JumpData,
    /// No-operation selection or verification failed.
    NoOperation,
    /// Non-graphical selection or verification failed.
    NonGraphical,
    /// Output selection or verification failed.
    Output,
    /// Runtime/profile requirement admission failed.
    Profile,
    /// Rotate selection or verification failed.
    Rotate,
}

/// Hard planning rejection retaining the exact affine suspension owner.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryPlanningFailure {
    error: NativeContinuationRetryPlanningError,
    suspension: NativeContinuationScheduleSuspension,
}

impl Display for NativeContinuationRetryPlanningError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Admission(error) => {
                write!(f, "retry admission failed: {error}")
            },
            Self::Deoptimization { index } => {
                write!(f, "retry step {index} selected deoptimization")
            },
            Self::Empty => {
                f.write_str("retry planning received an empty suffix")
            },
            Self::ObservationChain { index } => {
                write!(f, "retry observation chain broke at step {index}")
            },
            Self::ProfileMismatch { index } => {
                write!(f, "retry profile changed at step {index}")
            },
            Self::ProgramShape { index } => {
                write!(f, "retry step {index} is not one complete effect")
            },
            Self::ScheduleReason { observed } => write!(
                f,
                "retry planning requires native-retry yield, got {}",
                stop_reason_id(*observed),
            ),
            Self::Step { cause, index } => {
                write!(f, "retry step {index} failed: {}", cause.stable_id())
            },
            Self::TerminationBeforeEnd { index } => {
                write!(f, "retry step {index} terminated before suffix end")
            },
        }
    }
}

impl NativeContinuationRetryPlanningFailure {
    /// Returns the stable hard planning rejection.
    #[must_use]
    pub const fn error(&self) -> NativeContinuationRetryPlanningError {
        self.error
    }

    /// Consumes this rejection and restores the exact affine suspension.
    #[must_use]
    pub fn into_suspension(self) -> NativeContinuationScheduleSuspension {
        self.suspension
    }
}

impl NativeContinuationRetryStepPlanningError {
    const fn stable_id(self) -> &'static str {
        match self {
            Self::Crazy => "crazy",
            Self::Deoptimization => "deoptimization",
            Self::HaltFetch => "halt-fetch",
            Self::HaltRegisters => "halt-registers",
            Self::InitialHalt => "initial-halt",
            Self::Input => "input",
            Self::JumpCode => "jump-code",
            Self::JumpData => "jump-data",
            Self::NoOperation => "no-operation",
            Self::NonGraphical => "non-graphical",
            Self::Output => "output",
            Self::Profile => "profile",
            Self::Rotate => "rotate",
        }
    }
}

enum RetryPlanningClassification {
    Hard(NativeContinuationRetryPlanningError),
    Interpreter,
}

/// Plans one exact native-retry suffix for an explicit host.
///
/// Only direct `TargetFormat` absence becomes a normative interpreter handoff.
/// Every other planning or admission failure retains the suspension and fails
/// closed.
///
/// # Errors
///
/// Returns [`NativeContinuationRetryPlanningFailure`] for a non-native-retry
/// reason or any hard direct planning/admission failure.
pub fn plan_native_continuation_retry(
    suspension: NativeContinuationScheduleSuspension,
    runtime: &'static RuntimeCapability,
    host_os: HostOperatingSystem,
    host_isa: HostIsa,
) -> Result<
    NativeContinuationRetryPlanningOutcome,
    Box<NativeContinuationRetryPlanningFailure>,
> {
    if suspension.reason() != NativeContinuationScheduleStopReason::NativeRetry
    {
        return Err(planning_failure(
            NativeContinuationRetryPlanningError::ScheduleReason {
                observed: suspension.reason(),
            },
            suspension,
        ));
    }
    let planning = select_verified_direct_sequence(
        suspension.remaining_programs(),
        runtime,
        host_os,
        host_isa,
    );
    match planning {
        Ok(plan) => plan_admitted_retry(suspension, plan),
        Err(sequence_error) => match classify_sequence_error(sequence_error) {
            RetryPlanningClassification::Interpreter => {
                Ok(NativeContinuationRetryPlanningOutcome::Interpreter(
                    Box::new(suspension.into_handoff()),
                ))
            },
            RetryPlanningClassification::Hard(planning_error) => {
                Err(planning_failure(planning_error, suspension))
            },
        },
    }
}

const fn classify_selection_error(
    error: &DirectSelectionError<'_>,
) -> Option<NativeContinuationRetryStepPlanningError> {
    match error {
        DirectSelectionError::Crazy(_) => {
            Some(NativeContinuationRetryStepPlanningError::Crazy)
        },
        DirectSelectionError::Deopt(_) => {
            Some(NativeContinuationRetryStepPlanningError::Deoptimization)
        },
        DirectSelectionError::HaltFetch(_) => {
            Some(NativeContinuationRetryStepPlanningError::HaltFetch)
        },
        DirectSelectionError::HaltRegisters(_) => {
            Some(NativeContinuationRetryStepPlanningError::HaltRegisters)
        },
        DirectSelectionError::InitialHalt(_) => {
            Some(NativeContinuationRetryStepPlanningError::InitialHalt)
        },
        DirectSelectionError::Input(_) => {
            Some(NativeContinuationRetryStepPlanningError::Input)
        },
        DirectSelectionError::JumpCode(_) => {
            Some(NativeContinuationRetryStepPlanningError::JumpCode)
        },
        DirectSelectionError::JumpData(_) => {
            Some(NativeContinuationRetryStepPlanningError::JumpData)
        },
        DirectSelectionError::NoOperation(_) => {
            Some(NativeContinuationRetryStepPlanningError::NoOperation)
        },
        DirectSelectionError::NonGraphical(_) => {
            Some(NativeContinuationRetryStepPlanningError::NonGraphical)
        },
        DirectSelectionError::Output(_) => {
            Some(NativeContinuationRetryStepPlanningError::Output)
        },
        DirectSelectionError::Profile(_)
        | DirectSelectionError::ProfileRequirement => {
            Some(NativeContinuationRetryStepPlanningError::Profile)
        },
        DirectSelectionError::Rotate(_) => {
            Some(NativeContinuationRetryStepPlanningError::Rotate)
        },
        DirectSelectionError::TargetFormat => None,
    }
}

fn classify_sequence_error(
    error: DirectSequenceError<'_>,
) -> RetryPlanningClassification {
    match error {
        DirectSequenceError::Deoptimization { index } => {
            RetryPlanningClassification::Hard(
                NativeContinuationRetryPlanningError::Deoptimization { index },
            )
        },
        DirectSequenceError::Empty => RetryPlanningClassification::Hard(
            NativeContinuationRetryPlanningError::Empty,
        ),
        DirectSequenceError::ObservationChain { index } => {
            RetryPlanningClassification::Hard(
                NativeContinuationRetryPlanningError::ObservationChain {
                    index,
                },
            )
        },
        DirectSequenceError::ProfileMismatch { index } => {
            RetryPlanningClassification::Hard(
                NativeContinuationRetryPlanningError::ProfileMismatch { index },
            )
        },
        DirectSequenceError::ProgramShape { index } => {
            RetryPlanningClassification::Hard(
                NativeContinuationRetryPlanningError::ProgramShape { index },
            )
        },
        DirectSequenceError::Step {
            error: selection_error,
            index,
        } => classify_selection_error(&selection_error).map_or(
            RetryPlanningClassification::Interpreter,
            |cause| {
                RetryPlanningClassification::Hard(
                    NativeContinuationRetryPlanningError::Step { cause, index },
                )
            },
        ),
        DirectSequenceError::TerminationBeforeEnd { index } => {
            RetryPlanningClassification::Hard(
                NativeContinuationRetryPlanningError::TerminationBeforeEnd {
                    index,
                },
            )
        },
    }
}

fn plan_admitted_retry(
    suspension: NativeContinuationScheduleSuspension,
    plan: VerifiedDirectSequencePlan,
) -> Result<
    NativeContinuationRetryPlanningOutcome,
    Box<NativeContinuationRetryPlanningFailure>,
> {
    match NativeContinuationNativeRetry::new(suspension, plan) {
        Ok(retry) => Ok(NativeContinuationRetryPlanningOutcome::Native(
            Box::new(retry),
        )),
        Err(failure) => {
            let error = failure.error();
            let (recovered_suspension, _) = (*failure).into_parts();
            Err(planning_failure(
                NativeContinuationRetryPlanningError::Admission(error),
                recovered_suspension,
            ))
        },
    }
}

fn planning_failure(
    error: NativeContinuationRetryPlanningError,
    suspension: NativeContinuationScheduleSuspension,
) -> Box<NativeContinuationRetryPlanningFailure> {
    Box::new(NativeContinuationRetryPlanningFailure { error, suspension })
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
