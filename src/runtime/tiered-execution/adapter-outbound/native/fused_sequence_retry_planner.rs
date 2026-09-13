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
//   - Exact host planning of one fused native-retry suspension.
// - Must-Not:
//   - Load mappings, mutate caches, invoke native code, or hide hard failures.
// - Allows:
//   - Inputs: native-retry suspension, runtime capability, and explicit host.
//   - Outputs: admitted fused retry, normative handoff, or owned hard failure.
//   - Side effects: process-local verified artifact allocation only.
// - Split-When:
//   - Cached planning or retry-attempt budgets gain policy.
// - Merge-When:
//   - Product orchestration owns planning, execution, and routing atomically.
// - Summary:
//   - Replans exact fused retry suffixes for one explicit host.
// - Description:
//   - Falls back only for target-format absence or an unfusable one-step
//     suffix.
// - Usage:
//   - Call after the fused scheduler yields exact `NativeRetry` ownership.
// - Defaults:
//   - Every other planning or verification rejection remains hard.
//

//! Exact host routing for one affine fused native-retry suspension.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::RuntimeCapability;

use super::direct::{
    DirectFusedSequenceObjectError, DirectSelectionError, DirectSequenceError,
    emit_fused_direct_sequence_coff, select_verified_direct_sequence,
    verify_fused_direct_sequence,
};
use super::fused_sequence::{
    DirectFusedSequenceAdmissionError, admit_fused_direct_sequence,
};
use super::fused_sequence_handoff::DirectFusedNativeInterpreterHandoff;
use super::fused_sequence_plan::{
    DirectFusedNativeSequencePlan, DirectFusedNativeSequencePlanError,
};
use super::fused_sequence_retry::{
    DirectFusedNativeRetry, DirectFusedNativeRetryAdmissionError,
};
use super::fused_sequence_scheduler::{
    DirectFusedNativeScheduleStopReason, DirectFusedNativeScheduleSuspension,
};
use crate::execution_cache::{HostIsa, HostOperatingSystem};

/// One exact route selected for a fused native-retry suspension.
#[derive(Debug, Eq, PartialEq)]
pub enum DirectFusedNativeRetryPlanningOutcome {
    /// This host/suffix lacks fused-native capability; continue normatively.
    Interpreter(Box<DirectFusedNativeInterpreterHandoff>),
    /// The explicit host admitted the exact suffix as one fused native retry.
    Native(Box<DirectFusedNativeRetry>),
}

/// Stable hard failure while planning one fused retry suffix.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectFusedNativeRetryPlanningError {
    /// Exact post-planning retry admission unexpectedly failed.
    Admission(DirectFusedNativeRetryAdmissionError),
    /// Fused-region semantic admission failed unexpectedly.
    FusedAdmission(DirectFusedSequenceAdmissionError),
    /// Fused object emission or semantic verification failed unexpectedly.
    FusedObject(DirectFusedSequenceObjectError),
    /// Verified fused-region topology could not be published.
    FusedPlan(DirectFusedNativeSequencePlanError),
    /// The suspension was not yielded for native retry.
    ScheduleReason {
        /// Exact observed scheduler reason.
        observed: DirectFusedNativeScheduleStopReason,
    },
    /// One exact source step failed direct planning or verification.
    Step {
        /// Stable direct-planning failure class.
        cause: DirectFusedNativeRetryStepPlanningError,
        /// Zero-based source-step position.
        index: usize,
    },
    /// Direct source-sequence topology failed before fused admission.
    Topology(DirectFusedNativeRetryTopologyError),
}

/// Stable source-step direct-planning failure class.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectFusedNativeRetryStepPlanningError {
    /// Crazy-operation direct planning failed.
    Crazy,
    /// Deoptimization direct planning failed.
    Deoptimization,
    /// Graphical halt-fetch direct planning failed.
    HaltFetch,
    /// Arbitrary-register halt direct planning failed.
    HaltRegisters,
    /// Initial-halt direct planning failed.
    InitialHalt,
    /// Input direct planning failed.
    Input,
    /// Jump-code direct planning failed.
    JumpCode,
    /// Jump-data direct planning failed.
    JumpData,
    /// No-operation direct planning failed.
    NoOperation,
    /// Non-graphical direct planning failed.
    NonGraphical,
    /// Output direct planning failed.
    Output,
    /// Runtime/profile requirement admission failed.
    Profile,
    /// Rotate direct planning failed.
    Rotate,
}

/// Stable direct source-sequence topology failure class.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectFusedNativeRetryTopologyError {
    /// One source step selected deoptimization rather than a native fast path.
    Deoptimization {
        /// Zero-based source step.
        index: usize,
    },
    /// The retained semantic suffix unexpectedly contained no work.
    Empty,
    /// Adjacent source-step observations are not exactly continuous.
    ObservationChain {
        /// Zero-based source step whose entry disagrees with the prior exit.
        index: usize,
    },
    /// Canonical profile identity changed inside the retained suffix.
    ProfileMismatch {
        /// Zero-based source step whose profile differs.
        index: usize,
    },
    /// One retained source program no longer has exact one-step shape.
    ProgramShape {
        /// Zero-based malformed source step.
        index: usize,
    },
    /// A terminated source step was followed by more retained work.
    TerminationBeforeEnd {
        /// Zero-based prematurely terminating source step.
        index: usize,
    },
}

/// Hard fused planning rejection retaining the exact affine suspension.
#[derive(Debug, Eq, PartialEq)]
pub struct DirectFusedNativeRetryPlanningFailure {
    error: DirectFusedNativeRetryPlanningError,
    profile_diagnostic: Option<String>,
    suspension: DirectFusedNativeScheduleSuspension,
}

enum DirectFusedRetryPlanningClassification {
    Hard {
        error: DirectFusedNativeRetryPlanningError,
        profile_diagnostic: Option<String>,
    },
    Interpreter,
}

impl Display for DirectFusedNativeRetryPlanningError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Admission(error) => {
                write!(f, "fused retry admission: {error}")
            },
            Self::FusedAdmission(error) => {
                write!(f, "fused retry region admission: {error}")
            },
            Self::FusedObject(error) => {
                write!(f, "fused retry object verification: {error}")
            },
            Self::FusedPlan(error) => write!(f, "fused retry plan: {error}"),
            Self::ScheduleReason { observed } => write!(
                f,
                "fused retry planning requires native-retry yield, got {}",
                stop_reason_id(*observed),
            ),
            Self::Step { cause, index } => {
                write!(f, "fused retry step {index}: {}", cause.stable_id())
            },
            Self::Topology(error) => Display::fmt(error, f),
        }
    }
}

impl Display for DirectFusedNativeRetryPlanningFailure {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        if let Some(diagnostic) = self.profile_diagnostic.as_deref() {
            f.write_str(diagnostic)
        } else {
            Display::fmt(&self.error, f)
        }
    }
}

impl Display for DirectFusedNativeRetryTopologyError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Deoptimization { index } => {
                write!(f, "fused retry source {index} selected deoptimization")
            },
            Self::Empty => f.write_str("fused retry source suffix is empty"),
            Self::ObservationChain { index } => {
                write!(f, "fused retry source chain broke at {index}")
            },
            Self::ProfileMismatch { index } => {
                write!(f, "fused retry source profile changed at {index}")
            },
            Self::ProgramShape { index } => {
                write!(f, "fused retry source shape changed at {index}")
            },
            Self::TerminationBeforeEnd { index } => {
                write!(f, "fused retry source terminated at {index}")
            },
        }
    }
}

impl DirectFusedNativeRetryPlanningFailure {
    /// Returns the stable hard planning rejection.
    #[must_use]
    pub const fn error(&self) -> DirectFusedNativeRetryPlanningError {
        self.error
    }

    /// Consumes this rejection and restores the exact scheduler suspension.
    #[must_use]
    pub fn into_suspension(self) -> DirectFusedNativeScheduleSuspension {
        self.suspension
    }

    /// Returns the canonical profile diagnostic retained from direct planning.
    #[must_use]
    pub fn profile_diagnostic(&self) -> Option<&str> {
        self.profile_diagnostic.as_deref()
    }
}

impl DirectFusedNativeRetryStepPlanningError {
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

/// Plans one exact fused native-retry suffix for an explicit host.
///
/// Missing target format and a one-step suffix that cannot retain a whole fused
/// identity become normative interpreter fallback. Every other rejection is a
/// hard failure retaining exact scheduler ownership.
///
/// # Errors
///
/// Returns [`DirectFusedNativeRetryPlanningFailure`] for non-retry scheduling
/// or hard direct/fused planning and verification failures.
pub fn plan_direct_fused_native_retry(
    suspension: DirectFusedNativeScheduleSuspension,
    runtime: &'static RuntimeCapability,
    host_os: HostOperatingSystem,
    host_isa: HostIsa,
) -> Result<
    DirectFusedNativeRetryPlanningOutcome,
    Box<DirectFusedNativeRetryPlanningFailure>,
> {
    if suspension.reason() != DirectFusedNativeScheduleStopReason::NativeRetry {
        return Err(planning_failure(
            DirectFusedNativeRetryPlanningError::ScheduleReason {
                observed: suspension.reason(),
            },
            None,
            suspension,
        ));
    }
    let direct_result = select_verified_direct_sequence(
        suspension.remaining_programs(),
        runtime,
        host_os,
        host_isa,
    );
    let direct_plan = match direct_result {
        Ok(plan) => plan,
        Err(error) => {
            let classification = classify_direct_failure(error);
            return route_direct_classification(suspension, classification);
        },
    };
    plan_fused_retry(suspension, &direct_plan)
}

fn plan_fused_retry(
    suspension: DirectFusedNativeScheduleSuspension,
    direct: &super::direct::VerifiedDirectSequencePlan,
) -> Result<
    DirectFusedNativeRetryPlanningOutcome,
    Box<DirectFusedNativeRetryPlanningFailure>,
> {
    let admission = match admit_fused_direct_sequence(direct) {
        Ok(admission) => admission,
        Err(DirectFusedSequenceAdmissionError::SequenceLength { steps: 1 }) => {
            return Ok(interpreter_route(suspension));
        },
        Err(error) => return hard_fused_admission(suspension, error),
    };
    let candidate = match emit_fused_direct_sequence_coff(&admission) {
        Ok(candidate) => candidate,
        Err(DirectFusedSequenceObjectError::TargetFormat) => {
            return Ok(interpreter_route(suspension));
        },
        Err(error) => return hard_fused_object(suspension, error),
    };
    let artifact = match verify_fused_direct_sequence(&candidate, &admission) {
        Ok(artifact) => artifact,
        Err(error) => return hard_fused_object(suspension, error),
    };
    let plan = match DirectFusedNativeSequencePlan::new(&[artifact]) {
        Ok(plan) => plan,
        Err(error) => {
            return Err(hard_failure(
                DirectFusedNativeRetryPlanningError::FusedPlan(error),
                None,
                suspension,
            ));
        },
    };
    match DirectFusedNativeRetry::new(suspension, plan) {
        Ok(retry) => Ok(DirectFusedNativeRetryPlanningOutcome::Native(
            Box::new(retry),
        )),
        Err(failure) => {
            let error = failure.error();
            let (restored_suspension, _) = (*failure).into_parts();
            Err(hard_failure(
                DirectFusedNativeRetryPlanningError::Admission(error),
                None,
                restored_suspension,
            ))
        },
    }
}

fn route_direct_classification(
    suspension: DirectFusedNativeScheduleSuspension,
    classification: DirectFusedRetryPlanningClassification,
) -> Result<
    DirectFusedNativeRetryPlanningOutcome,
    Box<DirectFusedNativeRetryPlanningFailure>,
> {
    match classification {
        DirectFusedRetryPlanningClassification::Interpreter => {
            Ok(interpreter_route(suspension))
        },
        DirectFusedRetryPlanningClassification::Hard {
            error,
            profile_diagnostic,
        } => Err(hard_failure(error, profile_diagnostic, suspension)),
    }
}

fn classify_direct_failure(
    sequence_error: DirectSequenceError<'_>,
) -> DirectFusedRetryPlanningClassification {
    use DirectFusedNativeRetryTopologyError as Topology;
    match sequence_error {
        DirectSequenceError::Deoptimization { index } => {
            hard_topology(Topology::Deoptimization { index })
        },
        DirectSequenceError::Empty => hard_topology(Topology::Empty),
        DirectSequenceError::ObservationChain { index } => {
            hard_topology(Topology::ObservationChain { index })
        },
        DirectSequenceError::ProfileMismatch { index } => {
            hard_topology(Topology::ProfileMismatch { index })
        },
        DirectSequenceError::ProgramShape { index } => {
            hard_topology(Topology::ProgramShape { index })
        },
        DirectSequenceError::TerminationBeforeEnd { index } => {
            hard_topology(Topology::TerminationBeforeEnd { index })
        },
        DirectSequenceError::Step { error, index } => {
            classify_direct_step(&error, index)
        },
    }
}

fn classify_direct_step(
    error: &DirectSelectionError<'_>,
    index: usize,
) -> DirectFusedRetryPlanningClassification {
    let Some(cause) = direct_step_cause(error) else {
        return DirectFusedRetryPlanningClassification::Interpreter;
    };
    let profile_diagnostic = match error {
        DirectSelectionError::Profile(profile) => Some(profile.to_string()),
        DirectSelectionError::Crazy(_)
        | DirectSelectionError::Deopt(_)
        | DirectSelectionError::HaltFetch(_)
        | DirectSelectionError::HaltRegisters(_)
        | DirectSelectionError::InitialHalt(_)
        | DirectSelectionError::Input(_)
        | DirectSelectionError::JumpCode(_)
        | DirectSelectionError::JumpData(_)
        | DirectSelectionError::NoOperation(_)
        | DirectSelectionError::NonGraphical(_)
        | DirectSelectionError::Output(_)
        | DirectSelectionError::ProfileRequirement
        | DirectSelectionError::Rotate(_)
        | DirectSelectionError::TargetFormat => None,
    };
    DirectFusedRetryPlanningClassification::Hard {
        error: DirectFusedNativeRetryPlanningError::Step { cause, index },
        profile_diagnostic,
    }
}

const fn direct_step_cause(
    error: &DirectSelectionError<'_>,
) -> Option<DirectFusedNativeRetryStepPlanningError> {
    use DirectFusedNativeRetryStepPlanningError as Cause;
    match error {
        DirectSelectionError::Crazy(_) => Some(Cause::Crazy),
        DirectSelectionError::Deopt(_) => Some(Cause::Deoptimization),
        DirectSelectionError::HaltFetch(_) => Some(Cause::HaltFetch),
        DirectSelectionError::HaltRegisters(_) => Some(Cause::HaltRegisters),
        DirectSelectionError::InitialHalt(_) => Some(Cause::InitialHalt),
        DirectSelectionError::Input(_) => Some(Cause::Input),
        DirectSelectionError::JumpCode(_) => Some(Cause::JumpCode),
        DirectSelectionError::JumpData(_) => Some(Cause::JumpData),
        DirectSelectionError::NoOperation(_) => Some(Cause::NoOperation),
        DirectSelectionError::NonGraphical(_) => Some(Cause::NonGraphical),
        DirectSelectionError::Output(_) => Some(Cause::Output),
        DirectSelectionError::Profile(_)
        | DirectSelectionError::ProfileRequirement => Some(Cause::Profile),
        DirectSelectionError::Rotate(_) => Some(Cause::Rotate),
        DirectSelectionError::TargetFormat => None,
    }
}

const fn hard_topology(
    error: DirectFusedNativeRetryTopologyError,
) -> DirectFusedRetryPlanningClassification {
    DirectFusedRetryPlanningClassification::Hard {
        error: DirectFusedNativeRetryPlanningError::Topology(error),
        profile_diagnostic: None,
    }
}

fn hard_fused_admission(
    suspension: DirectFusedNativeScheduleSuspension,
    error: DirectFusedSequenceAdmissionError,
) -> Result<
    DirectFusedNativeRetryPlanningOutcome,
    Box<DirectFusedNativeRetryPlanningFailure>,
> {
    Err(hard_failure(
        DirectFusedNativeRetryPlanningError::FusedAdmission(error),
        None,
        suspension,
    ))
}

fn hard_fused_object(
    suspension: DirectFusedNativeScheduleSuspension,
    error: DirectFusedSequenceObjectError,
) -> Result<
    DirectFusedNativeRetryPlanningOutcome,
    Box<DirectFusedNativeRetryPlanningFailure>,
> {
    Err(hard_failure(
        DirectFusedNativeRetryPlanningError::FusedObject(error),
        None,
        suspension,
    ))
}

fn hard_failure(
    error: DirectFusedNativeRetryPlanningError,
    profile_diagnostic: Option<String>,
    suspension: DirectFusedNativeScheduleSuspension,
) -> Box<DirectFusedNativeRetryPlanningFailure> {
    Box::new(DirectFusedNativeRetryPlanningFailure {
        error,
        profile_diagnostic,
        suspension,
    })
}

fn interpreter_route(
    suspension: DirectFusedNativeScheduleSuspension,
) -> DirectFusedNativeRetryPlanningOutcome {
    DirectFusedNativeRetryPlanningOutcome::Interpreter(Box::new(
        suspension.into_handoff(),
    ))
}

fn planning_failure(
    error: DirectFusedNativeRetryPlanningError,
    profile_diagnostic: Option<String>,
    suspension: DirectFusedNativeScheduleSuspension,
) -> Box<DirectFusedNativeRetryPlanningFailure> {
    hard_failure(error, profile_diagnostic, suspension)
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
