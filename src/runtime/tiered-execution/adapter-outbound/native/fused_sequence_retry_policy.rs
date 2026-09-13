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
//   - Explicit native-retry attempt limits and normative fallback choice.
// - Must-Not:
//   - Infer attempt counts, inspect wall time, or execute either tier.
// - Allows:
//   - Inputs: exact retry suspension, completed attempt count, fixed policy.
//   - Outputs: next retry owner, interpreter route, or owned reason failure.
//   - Side effects: none.
// - Split-When:
//   - Adaptive telemetry or persistence gains independent policy ownership.
// - Merge-When:
//   - Product orchestration owns retry planning and fallback execution
//     atomically.
// - Summary:
//   - Bounds native retries and selects explicit complete or sliced fallback.
// - Description:
//   - Preserves one affine checkpoint owner across every policy route.
// - Usage:
//   - Apply before host retry planning with caller-owned attempt evidence.
// - Defaults:
//   - Zero maximum attempts falls back immediately without native planning.
//

//! Explicit bounded policy for fused native retry attempts.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::num::NonZeroUsize;

use super::fused_sequence_handoff::DirectFusedNativeInterpreterHandoff;
use super::fused_sequence_scheduler::{
    DirectFusedNativeScheduleDecision, DirectFusedNativeScheduleStopReason,
    DirectFusedNativeScheduleSuspension,
};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum DirectFusedNativeRetryFallbackKind {
    Complete,
    Slice,
}

/// Configured normative fallback after the fused native retry limit is reached.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct DirectFusedNativeRetryFallback {
    kind: DirectFusedNativeRetryFallbackKind,
    step_budget: usize,
}

/// Explicit immutable retry-attempt policy.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct DirectFusedNativeRetryPolicy {
    fallback: DirectFusedNativeRetryFallback,
    max_native_attempts: usize,
}

/// One route selected by the retry-attempt policy.
#[derive(Debug, Eq, PartialEq)]
pub enum DirectFusedNativeRetryPolicyOutcome {
    /// Attempt limit reached; execute the exact handoff normatively.
    Interpreter(Box<DirectFusedNativeRetryInterpreterRoute>),
    /// Attempt budget remains; preserve the exact native-retry suspension.
    NativeRetry(Box<DirectFusedNativeRetryNativeRoute>),
}

/// Normative route selected after exhausting native attempts.
#[derive(Debug, Eq, PartialEq)]
pub struct DirectFusedNativeRetryInterpreterRoute {
    attempts: usize,
    decision: DirectFusedNativeScheduleDecision,
    handoff: DirectFusedNativeInterpreterHandoff,
}

/// Exact retry owner selected before exhausting native attempts.
#[derive(Debug, Eq, PartialEq)]
pub struct DirectFusedNativeRetryNativeRoute {
    attempts: usize,
    next_attempt: usize,
    suspension: DirectFusedNativeScheduleSuspension,
}

/// Why retry-attempt policy refused one suspension.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectFusedNativeRetryPolicyError {
    /// The suspension was not yielded for fused native retry.
    ScheduleReason {
        /// Exact observed scheduling reason.
        observed: DirectFusedNativeScheduleStopReason,
    },
}

/// Policy rejection retaining the exact affine suspension owner.
#[derive(Debug, Eq, PartialEq)]
pub struct DirectFusedNativeRetryPolicyFailure {
    error: DirectFusedNativeRetryPolicyError,
    suspension: DirectFusedNativeScheduleSuspension,
}

impl Display for DirectFusedNativeRetryPolicyError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::ScheduleReason { observed } => write!(
                f,
                "retry policy requires native-retry yield, got {}",
                stop_reason_id(*observed),
            ),
        }
    }
}

impl DirectFusedNativeRetryFallback {
    /// Selects complete normative interpretation after retry exhaustion.
    #[must_use]
    pub const fn complete() -> Self {
        Self {
            kind: DirectFusedNativeRetryFallbackKind::Complete,
            step_budget: 0,
        }
    }

    const fn decision(self) -> DirectFusedNativeScheduleDecision {
        match self.kind {
            DirectFusedNativeRetryFallbackKind::Complete => {
                DirectFusedNativeScheduleDecision::complete_interpreter()
            },
            DirectFusedNativeRetryFallbackKind::Slice => {
                let Some(step_budget) = NonZeroUsize::new(self.step_budget)
                else {
                    return DirectFusedNativeScheduleDecision::
                        complete_interpreter();
                };
                DirectFusedNativeScheduleDecision::interpret(step_budget)
            },
        }
    }

    /// Selects one positive normative slice after retry exhaustion.
    #[must_use]
    pub const fn sliced(step_budget: NonZeroUsize) -> Self {
        Self {
            kind: DirectFusedNativeRetryFallbackKind::Slice,
            step_budget: step_budget.get(),
        }
    }
}

impl DirectFusedNativeRetryInterpreterRoute {
    /// Returns native attempts completed before fallback.
    #[must_use]
    pub const fn attempts(&self) -> usize {
        self.attempts
    }

    /// Returns the exact scheduler decision configured for fallback.
    #[must_use]
    pub const fn decision(&self) -> DirectFusedNativeScheduleDecision {
        self.decision
    }

    /// Consumes this route into exact handoff and scheduler decision owners.
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

impl DirectFusedNativeRetryNativeRoute {
    /// Returns native attempts completed before this route.
    #[must_use]
    pub const fn attempts(&self) -> usize {
        self.attempts
    }

    /// Consumes this route and restores the exact native-retry suspension.
    #[must_use]
    pub fn into_suspension(self) -> DirectFusedNativeScheduleSuspension {
        self.suspension
    }

    /// Returns the one-based attempt number selected next.
    #[must_use]
    pub const fn next_attempt(&self) -> usize {
        self.next_attempt
    }
}

impl DirectFusedNativeRetryPolicy {
    /// Returns the configured scheduler decision used for normative fallback.
    #[must_use]
    pub const fn fallback_decision(self) -> DirectFusedNativeScheduleDecision {
        self.fallback.decision()
    }

    /// Returns the configured maximum native attempt count.
    #[must_use]
    pub const fn max_native_attempts(self) -> usize {
        self.max_native_attempts
    }

    /// Constructs one explicit immutable retry policy.
    #[must_use]
    pub const fn new(
        max_native_attempts: usize,
        fallback: DirectFusedNativeRetryFallback,
    ) -> Self {
        Self {
            fallback,
            max_native_attempts,
        }
    }

    /// Routes one exact suspension using caller-supplied completed attempts.
    ///
    /// # Errors
    ///
    /// Returns [`DirectFusedNativeRetryPolicyFailure`] while retaining the
    /// suspension when its scheduling reason is not `NativeRetry`.
    pub fn route(
        self,
        suspension: DirectFusedNativeScheduleSuspension,
        attempts: usize,
    ) -> Result<
        DirectFusedNativeRetryPolicyOutcome,
        Box<DirectFusedNativeRetryPolicyFailure>,
    > {
        if suspension.reason()
            != DirectFusedNativeScheduleStopReason::NativeRetry
        {
            return Err(Box::new(DirectFusedNativeRetryPolicyFailure {
                error: DirectFusedNativeRetryPolicyError::ScheduleReason {
                    observed: suspension.reason(),
                },
                suspension,
            }));
        }
        if attempts < self.max_native_attempts {
            return Ok(DirectFusedNativeRetryPolicyOutcome::NativeRetry(
                Box::new(DirectFusedNativeRetryNativeRoute {
                    attempts,
                    next_attempt: attempts.saturating_add(1),
                    suspension,
                }),
            ));
        }
        Ok(DirectFusedNativeRetryPolicyOutcome::Interpreter(Box::new(
            DirectFusedNativeRetryInterpreterRoute {
                attempts,
                decision: self.fallback.decision(),
                handoff: suspension.into_handoff(),
            },
        )))
    }
}

impl DirectFusedNativeRetryPolicyFailure {
    /// Returns the exact policy rejection.
    #[must_use]
    pub const fn error(&self) -> DirectFusedNativeRetryPolicyError {
        self.error
    }

    /// Consumes this failure and restores the exact suspension owner.
    #[must_use]
    pub fn into_suspension(self) -> DirectFusedNativeScheduleSuspension {
        self.suspension
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
