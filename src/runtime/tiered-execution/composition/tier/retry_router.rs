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
//   - Composition of retry-attempt policy with exact host retry planning.
// - Must-Not:
//   - Execute native mappings, run the interpreter, or hide hard planning
//     errors.
// - Allows:
//   - Inputs: affine retry suspension, attempt evidence, policy, runtime, host.
//   - Outputs: exact native route, normative route, or owned stable rejection.
//   - Side effects: verified direct artifact allocation during host planning.
// - Split-When:
//   - Cache-aware routing or execution lifecycle gains independent ownership.
// - Merge-When:
//   - Product orchestration owns route selection and execution atomically.
// - Summary:
//   - Routes retry ownership through bounded policy and exact host planning.
// - Description:
//   - Target-format fallback uses configured policy without counting an
//     attempt.
// - Usage:
//   - Call once per retry turn before executing either selected route.
// - Defaults:
//   - Exhausted attempts bypass host planning; hard failures retain suspension.
//

//! Bounded host routing for one native continuation retry turn.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::RuntimeCapability;

use crate::continuation_scheduler::{
    NativeContinuationScheduleDecision, NativeContinuationScheduleSuspension,
};
use crate::execution_cache::{HostIsa, HostOperatingSystem};
use crate::interpreter_handoff::NativeInterpreterHandoff;
use crate::native_retry::NativeContinuationNativeRetry;
use crate::retry_planner::{
    NativeContinuationRetryPlanningError,
    NativeContinuationRetryPlanningOutcome, plan_native_continuation_retry,
};
use crate::retry_policy::{
    NativeContinuationRetryPolicy, NativeContinuationRetryPolicyError,
    NativeContinuationRetryPolicyOutcome,
};

/// Explicit host assumptions for one retry routing turn.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryHost {
    host_isa: HostIsa,
    host_os: HostOperatingSystem,
    runtime: &'static RuntimeCapability,
}

/// Complete owned request for one bounded retry routing turn.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryRoutingRequest {
    attempts: usize,
    host: NativeContinuationRetryHost,
    policy: NativeContinuationRetryPolicy,
    suspension: NativeContinuationScheduleSuspension,
}

#[derive(Clone, Copy)]
struct NativeContinuationRetryPlanningRequest {
    attempt: usize,
    attempts: usize,
    host: NativeContinuationRetryHost,
    policy: NativeContinuationRetryPolicy,
}

/// Exact route selected for one bounded retry turn.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationRetryRoute {
    /// Execute the exact checkpoint through the configured normative route.
    Interpreter(Box<NativeContinuationRetryInterpreterRoute>),
    /// Execute one exact admitted native retry attempt.
    Native(Box<NativeContinuationRetryNativeRoute>),
}

/// Normative route selected by exhausted budget or unavailable target format.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryInterpreterRoute {
    attempts: usize,
    decision: NativeContinuationScheduleDecision,
    handoff: NativeInterpreterHandoff,
}

/// Exact admitted native route with one-based attempt evidence.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryNativeRoute {
    attempt: usize,
    retry: NativeContinuationNativeRetry,
}

/// Stable routing rejection across policy and planning boundaries.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationRetryRoutingError {
    /// Exact host planning rejected the retry suffix.
    Planning(NativeContinuationRetryPlanningError),
    /// Attempt policy rejected the supplied scheduler suspension.
    Policy(NativeContinuationRetryPolicyError),
}

/// Routing failure retaining the exact affine retry suspension.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryRoutingFailure {
    error: NativeContinuationRetryRoutingError,
    profile_diagnostic: Option<String>,
    suspension: NativeContinuationScheduleSuspension,
}

impl Display for NativeContinuationRetryRoutingError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Planning(error) => {
                write!(f, "retry routing planning: {error}")
            },
            Self::Policy(error) => write!(f, "retry routing policy: {error}"),
        }
    }
}

impl Display for NativeContinuationRetryRoutingFailure {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        if let Some(diagnostic) = self.profile_diagnostic.as_deref() {
            f.write_str(diagnostic)
        } else {
            Display::fmt(&self.error, f)
        }
    }
}

impl NativeContinuationRetryHost {
    /// Constructs exact runtime and host assumptions for retry planning.
    #[must_use]
    pub const fn new(
        runtime: &'static RuntimeCapability,
        host_os: HostOperatingSystem,
        host_isa: HostIsa,
    ) -> Self {
        Self {
            host_isa,
            host_os,
            runtime,
        }
    }
}

impl NativeContinuationRetryRoutingRequest {
    /// Constructs one complete affine retry routing request.
    #[must_use]
    pub const fn new(
        policy: NativeContinuationRetryPolicy,
        suspension: NativeContinuationScheduleSuspension,
        attempts: usize,
        host: NativeContinuationRetryHost,
    ) -> Self {
        Self {
            attempts,
            host,
            policy,
            suspension,
        }
    }
}

impl NativeContinuationRetryInterpreterRoute {
    /// Returns completed native attempts before this normative route.
    #[must_use]
    pub const fn attempts(&self) -> usize {
        self.attempts
    }

    /// Returns the exact configured scheduler decision.
    #[must_use]
    pub const fn decision(&self) -> NativeContinuationScheduleDecision {
        self.decision
    }

    /// Consumes this route into exact handoff and decision owners.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> (NativeInterpreterHandoff, NativeContinuationScheduleDecision) {
        (self.handoff, self.decision)
    }
}

impl NativeContinuationRetryNativeRoute {
    /// Returns the one-based native attempt number selected for this route.
    #[must_use]
    pub const fn attempt(&self) -> usize {
        self.attempt
    }

    /// Consumes this route and returns the exact admitted native retry owner.
    #[must_use]
    pub fn into_retry(self) -> NativeContinuationNativeRetry {
        self.retry
    }

    /// Returns the exact admitted native retry owner.
    #[must_use]
    pub const fn retry(&self) -> &NativeContinuationNativeRetry {
        &self.retry
    }
}

impl NativeContinuationRetryRoutingFailure {
    /// Returns the stable routing rejection.
    #[must_use]
    pub const fn error(&self) -> NativeContinuationRetryRoutingError {
        self.error
    }

    /// Returns the retained canonical profile diagnostic, when applicable.
    #[must_use]
    pub fn profile_diagnostic(&self) -> Option<&str> {
        self.profile_diagnostic.as_deref()
    }

    /// Consumes this failure and restores the exact retry suspension.
    #[must_use]
    pub fn into_suspension(self) -> NativeContinuationScheduleSuspension {
        self.suspension
    }
}

/// Routes one retry turn through attempt policy and exact host planning.
///
/// Exhausted policy routes bypass native planning. When budget remains, only
/// target-format absence becomes the configured normative fallback and does not
/// consume an attempt number.
///
/// # Errors
///
/// Returns [`NativeContinuationRetryRoutingFailure`] while retaining the exact
/// suspension for every policy or hard planning rejection.
pub fn route_native_continuation_retry(
    request: NativeContinuationRetryRoutingRequest,
) -> Result<
    NativeContinuationRetryRoute,
    Box<NativeContinuationRetryRoutingFailure>,
> {
    let NativeContinuationRetryRoutingRequest {
        attempts,
        host,
        policy,
        suspension,
    } = request;
    let policy_route =
        policy.route(suspension, attempts).map_err(|failure| {
            let error =
                NativeContinuationRetryRoutingError::Policy(failure.error());
            routing_failure(error, None, (*failure).into_suspension())
        })?;
    match policy_route {
        NativeContinuationRetryPolicyOutcome::Interpreter(route) => {
            let completed_attempts = route.attempts();
            let (handoff, decision) = route.into_parts();
            Ok(NativeContinuationRetryRoute::Interpreter(Box::new(
                NativeContinuationRetryInterpreterRoute {
                    attempts: completed_attempts,
                    decision,
                    handoff,
                },
            )))
        },
        NativeContinuationRetryPolicyOutcome::NativeRetry(route) => {
            let planning_request = NativeContinuationRetryPlanningRequest {
                attempt: route.next_attempt(),
                attempts,
                host,
                policy,
            };
            route_planned_retry(route.into_suspension(), planning_request)
        },
    }
}

fn route_planned_retry(
    suspension: NativeContinuationScheduleSuspension,
    request: NativeContinuationRetryPlanningRequest,
) -> Result<
    NativeContinuationRetryRoute,
    Box<NativeContinuationRetryRoutingFailure>,
> {
    match plan_native_continuation_retry(
        suspension,
        request.host.runtime,
        request.host.host_os,
        request.host.host_isa,
    ) {
        Ok(NativeContinuationRetryPlanningOutcome::Native(retry)) => {
            Ok(NativeContinuationRetryRoute::Native(Box::new(
                NativeContinuationRetryNativeRoute {
                    attempt: request.attempt,
                    retry: *retry,
                },
            )))
        },
        Ok(NativeContinuationRetryPlanningOutcome::Interpreter(handoff)) => {
            Ok(NativeContinuationRetryRoute::Interpreter(Box::new(
                NativeContinuationRetryInterpreterRoute {
                    attempts: request.attempts,
                    decision: request.policy.fallback_decision(),
                    handoff: *handoff,
                },
            )))
        },
        Err(failure) => {
            let error =
                NativeContinuationRetryRoutingError::Planning(failure.error());
            let profile_diagnostic =
                failure.profile_diagnostic().map(str::to_owned);
            Err(routing_failure(
                error,
                profile_diagnostic,
                (*failure).into_suspension(),
            ))
        },
    }
}

fn routing_failure(
    error: NativeContinuationRetryRoutingError,
    profile_diagnostic: Option<String>,
    suspension: NativeContinuationScheduleSuspension,
) -> Box<NativeContinuationRetryRoutingFailure> {
    Box::new(NativeContinuationRetryRoutingFailure {
        error,
        profile_diagnostic,
        suspension,
    })
}
