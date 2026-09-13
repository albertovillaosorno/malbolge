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
//   - Composition of fused retry-attempt policy with exact host planning.
// - Must-Not:
//   - Execute native mappings, run the interpreter, or hide hard planning
//     failures.
// - Allows:
//   - Inputs: affine retry suspension, attempt evidence, policy, runtime, host.
//   - Outputs: exact native route, normative route, or owned stable rejection.
//   - Side effects: verified fused artifact allocation during host planning.
// - Split-When:
//   - Cache-aware routing or execution lifecycle gains independent ownership.
// - Merge-When:
//   - Product orchestration owns route selection and execution atomically.
// - Summary:
//   - Routes fused retry ownership through bounded policy and host planning.
// - Description:
//   - Planner fallback uses configured policy without counting an attempt.
// - Usage:
//   - Call once per fused retry turn before executing either selected route.
// - Defaults:
//   - Exhausted attempts bypass planning; hard failures retain suspension.
//

//! Bounded host routing for one fused native-retry turn.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::RuntimeCapability;

use super::fused_sequence_handoff::DirectFusedNativeInterpreterHandoff;
use super::fused_sequence_retry::DirectFusedNativeRetry;
use super::fused_sequence_retry_planner::{
    DirectFusedNativeRetryPlanningError, DirectFusedNativeRetryPlanningOutcome,
    plan_direct_fused_native_retry,
};
use super::fused_sequence_retry_policy::{
    DirectFusedNativeRetryPolicy, DirectFusedNativeRetryPolicyError,
    DirectFusedNativeRetryPolicyOutcome,
};
use super::fused_sequence_scheduler::{
    DirectFusedNativeScheduleDecision, DirectFusedNativeScheduleSuspension,
};
use crate::execution_cache::{HostIsa, HostOperatingSystem};

/// Explicit host assumptions for one fused retry routing turn.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct DirectFusedNativeRetryHost {
    host_isa: HostIsa,
    host_os: HostOperatingSystem,
    runtime: &'static RuntimeCapability,
}

/// Complete owned request for one bounded fused retry routing turn.
#[derive(Debug, Eq, PartialEq)]
pub struct DirectFusedNativeRetryRoutingRequest {
    attempts: usize,
    host: DirectFusedNativeRetryHost,
    policy: DirectFusedNativeRetryPolicy,
    suspension: DirectFusedNativeScheduleSuspension,
}

#[derive(Clone, Copy)]
struct DirectFusedNativeRetryPlanningRequest {
    attempt: usize,
    attempts: usize,
    host: DirectFusedNativeRetryHost,
    policy: DirectFusedNativeRetryPolicy,
}

/// Exact route selected for one bounded fused retry turn.
#[derive(Debug, Eq, PartialEq)]
pub enum DirectFusedNativeRetryRoute {
    /// Execute the exact checkpoint through the configured normative route.
    Interpreter(Box<DirectFusedNativeRetryRoutingInterpreterRoute>),
    /// Execute one exact admitted fused native retry attempt.
    Native(Box<DirectFusedNativeRetryRoutingNativeRoute>),
}

/// Normative route selected by exhausted budget or planner fallback.
#[derive(Debug, Eq, PartialEq)]
pub struct DirectFusedNativeRetryRoutingInterpreterRoute {
    attempts: usize,
    decision: DirectFusedNativeScheduleDecision,
    handoff: DirectFusedNativeInterpreterHandoff,
}

/// Exact admitted fused native route with one-based attempt evidence.
#[derive(Debug, Eq, PartialEq)]
pub struct DirectFusedNativeRetryRoutingNativeRoute {
    attempt: usize,
    retry: DirectFusedNativeRetry,
}

/// Stable routing rejection across fused policy and planning boundaries.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectFusedNativeRetryRoutingError {
    /// Exact host planning rejected the fused retry suffix.
    Planning(DirectFusedNativeRetryPlanningError),
    /// Attempt policy rejected the supplied scheduler suspension.
    Policy(DirectFusedNativeRetryPolicyError),
}

/// Routing failure retaining the exact affine fused retry suspension.
#[derive(Debug, Eq, PartialEq)]
pub struct DirectFusedNativeRetryRoutingFailure {
    error: DirectFusedNativeRetryRoutingError,
    profile_diagnostic: Option<String>,
    suspension: DirectFusedNativeScheduleSuspension,
}

impl Display for DirectFusedNativeRetryRoutingError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Planning(error) => {
                write!(f, "fused retry routing planning: {error}")
            },
            Self::Policy(error) => {
                write!(f, "fused retry routing policy: {error}")
            },
        }
    }
}

impl Display for DirectFusedNativeRetryRoutingFailure {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        if let Some(diagnostic) = self.profile_diagnostic.as_deref() {
            f.write_str(diagnostic)
        } else {
            Display::fmt(&self.error, f)
        }
    }
}

impl DirectFusedNativeRetryHost {
    /// Constructs exact runtime and host assumptions for fused retry planning.
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

impl DirectFusedNativeRetryRoutingRequest {
    /// Constructs one complete affine fused retry routing request.
    #[must_use]
    pub const fn new(
        policy: DirectFusedNativeRetryPolicy,
        suspension: DirectFusedNativeScheduleSuspension,
        attempts: usize,
        host: DirectFusedNativeRetryHost,
    ) -> Self {
        Self {
            attempts,
            host,
            policy,
            suspension,
        }
    }
}

impl DirectFusedNativeRetryRoutingInterpreterRoute {
    /// Returns completed native attempts before this normative route.
    #[must_use]
    pub const fn attempts(&self) -> usize {
        self.attempts
    }

    /// Returns the exact configured scheduler decision.
    #[must_use]
    pub const fn decision(&self) -> DirectFusedNativeScheduleDecision {
        self.decision
    }

    /// Consumes this route into exact handoff and decision owners.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> (
        DirectFusedNativeInterpreterHandoff,
        DirectFusedNativeScheduleDecision,
    ) {
        (self.handoff, self.decision)
    }
}

impl DirectFusedNativeRetryRoutingNativeRoute {
    /// Returns the one-based native attempt number selected for this route.
    #[must_use]
    pub const fn attempt(&self) -> usize {
        self.attempt
    }

    /// Consumes this route and returns the exact admitted fused retry owner.
    #[must_use]
    pub fn into_retry(self) -> DirectFusedNativeRetry {
        self.retry
    }

    /// Returns the exact admitted fused retry owner.
    #[must_use]
    pub const fn retry(&self) -> &DirectFusedNativeRetry {
        &self.retry
    }
}

impl DirectFusedNativeRetryRoutingFailure {
    /// Returns the stable routing rejection.
    #[must_use]
    pub const fn error(&self) -> DirectFusedNativeRetryRoutingError {
        self.error
    }

    /// Consumes this failure and restores the exact retry suspension.
    #[must_use]
    pub fn into_suspension(self) -> DirectFusedNativeScheduleSuspension {
        self.suspension
    }

    /// Returns the retained canonical profile diagnostic, when applicable.
    #[must_use]
    pub fn profile_diagnostic(&self) -> Option<&str> {
        self.profile_diagnostic.as_deref()
    }
}

/// Routes one fused retry turn through attempt policy and exact host planning.
///
/// Exhausted policy routes bypass native planning. When budget remains,
/// planner fallback becomes the configured normative route without consuming
/// an attempt.
///
/// # Errors
///
/// Returns [`DirectFusedNativeRetryRoutingFailure`] while retaining the exact
/// suspension for every policy or hard planning rejection.
pub fn route_direct_fused_native_retry(
    request: DirectFusedNativeRetryRoutingRequest,
) -> Result<
    DirectFusedNativeRetryRoute,
    Box<DirectFusedNativeRetryRoutingFailure>,
> {
    let DirectFusedNativeRetryRoutingRequest {
        attempts,
        host,
        policy,
        suspension,
    } = request;
    let policy_route =
        policy.route(suspension, attempts).map_err(|failure| {
            let error =
                DirectFusedNativeRetryRoutingError::Policy(failure.error());
            routing_failure(error, None, (*failure).into_suspension())
        })?;
    match policy_route {
        DirectFusedNativeRetryPolicyOutcome::Interpreter(route) => {
            let completed_attempts = route.attempts();
            let (handoff, decision) = route.into_parts();
            Ok(DirectFusedNativeRetryRoute::Interpreter(Box::new(
                DirectFusedNativeRetryRoutingInterpreterRoute {
                    attempts: completed_attempts,
                    decision,
                    handoff,
                },
            )))
        },
        DirectFusedNativeRetryPolicyOutcome::NativeRetry(route) => {
            let planning_request = DirectFusedNativeRetryPlanningRequest {
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
    suspension: DirectFusedNativeScheduleSuspension,
    request: DirectFusedNativeRetryPlanningRequest,
) -> Result<
    DirectFusedNativeRetryRoute,
    Box<DirectFusedNativeRetryRoutingFailure>,
> {
    match plan_direct_fused_native_retry(
        suspension,
        request.host.runtime,
        request.host.host_os,
        request.host.host_isa,
    ) {
        Ok(DirectFusedNativeRetryPlanningOutcome::Native(retry)) => {
            Ok(DirectFusedNativeRetryRoute::Native(Box::new(
                DirectFusedNativeRetryRoutingNativeRoute {
                    attempt: request.attempt,
                    retry: *retry,
                },
            )))
        },
        Ok(DirectFusedNativeRetryPlanningOutcome::Interpreter(handoff)) => {
            Ok(DirectFusedNativeRetryRoute::Interpreter(Box::new(
                DirectFusedNativeRetryRoutingInterpreterRoute {
                    attempts: request.attempts,
                    decision: request.policy.fallback_decision(),
                    handoff: *handoff,
                },
            )))
        },
        Err(failure) => {
            let error =
                DirectFusedNativeRetryRoutingError::Planning(failure.error());
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
    error: DirectFusedNativeRetryRoutingError,
    profile_diagnostic: Option<String>,
    suspension: DirectFusedNativeScheduleSuspension,
) -> Box<DirectFusedNativeRetryRoutingFailure> {
    Box::new(DirectFusedNativeRetryRoutingFailure {
        error,
        profile_diagnostic,
        suspension,
    })
}
