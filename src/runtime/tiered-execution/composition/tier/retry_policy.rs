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

//! Explicit bounded policy for native continuation retry attempts.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::num::NonZeroUsize;

use crate::continuation_scheduler::{
    NativeContinuationScheduleDecision, NativeContinuationScheduleStopReason,
    NativeContinuationScheduleSuspension,
};
use crate::interpreter_handoff::NativeInterpreterHandoff;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum NativeContinuationRetryFallbackKind {
    Complete,
    Slice,
}

/// Configured normative fallback after the native retry limit is reached.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryFallback {
    kind: NativeContinuationRetryFallbackKind,
    step_budget: usize,
}

/// Explicit immutable retry-attempt policy.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryPolicy {
    fallback: NativeContinuationRetryFallback,
    max_native_attempts: usize,
}

/// One route selected by the retry-attempt policy.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationRetryPolicyOutcome {
    /// Attempt limit reached; execute the exact handoff normatively.
    Interpreter(Box<NativeContinuationRetryInterpreterRoute>),
    /// Attempt budget remains; preserve the exact native-retry suspension.
    NativeRetry(Box<NativeContinuationRetryNativeRoute>),
}

/// Normative route selected after exhausting native attempts.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryInterpreterRoute {
    attempts: usize,
    decision: NativeContinuationScheduleDecision,
    handoff: NativeInterpreterHandoff,
}

/// Exact retry owner selected before exhausting native attempts.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryNativeRoute {
    attempts: usize,
    next_attempt: usize,
    suspension: NativeContinuationScheduleSuspension,
}

/// Why retry-attempt policy refused one suspension.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationRetryPolicyError {
    /// The suspension was not yielded for native retry.
    ScheduleReason {
        /// Exact observed scheduling reason.
        observed: NativeContinuationScheduleStopReason,
    },
}

/// Policy rejection retaining the exact affine suspension owner.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryPolicyFailure {
    error: NativeContinuationRetryPolicyError,
    suspension: NativeContinuationScheduleSuspension,
}

impl Display for NativeContinuationRetryPolicyError {
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

impl NativeContinuationRetryFallback {
    /// Selects complete normative interpretation after retry exhaustion.
    #[must_use]
    pub const fn complete() -> Self {
        Self {
            kind: NativeContinuationRetryFallbackKind::Complete,
            step_budget: 0,
        }
    }

    const fn decision(self) -> NativeContinuationScheduleDecision {
        match self.kind {
            NativeContinuationRetryFallbackKind::Complete => {
                NativeContinuationScheduleDecision::complete_interpreter()
            },
            NativeContinuationRetryFallbackKind::Slice => {
                let Some(step_budget) = NonZeroUsize::new(self.step_budget)
                else {
                    return NativeContinuationScheduleDecision::
                        complete_interpreter();
                };
                NativeContinuationScheduleDecision::interpret(step_budget)
            },
        }
    }

    /// Selects one positive normative slice after retry exhaustion.
    #[must_use]
    pub const fn sliced(step_budget: NonZeroUsize) -> Self {
        Self {
            kind: NativeContinuationRetryFallbackKind::Slice,
            step_budget: step_budget.get(),
        }
    }
}

impl NativeContinuationRetryInterpreterRoute {
    /// Returns native attempts completed before fallback.
    #[must_use]
    pub const fn attempts(&self) -> usize {
        self.attempts
    }

    /// Returns the exact scheduler decision configured for fallback.
    #[must_use]
    pub const fn decision(&self) -> NativeContinuationScheduleDecision {
        self.decision
    }

    /// Consumes this route into exact handoff and scheduler decision owners.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> (NativeInterpreterHandoff, NativeContinuationScheduleDecision) {
        (self.handoff, self.decision)
    }
}

impl NativeContinuationRetryNativeRoute {
    /// Returns native attempts completed before this route.
    #[must_use]
    pub const fn attempts(&self) -> usize {
        self.attempts
    }

    /// Consumes this route and restores the exact native-retry suspension.
    #[must_use]
    pub fn into_suspension(self) -> NativeContinuationScheduleSuspension {
        self.suspension
    }

    /// Returns the one-based attempt number selected next.
    #[must_use]
    pub const fn next_attempt(&self) -> usize {
        self.next_attempt
    }
}

impl NativeContinuationRetryPolicy {
    /// Returns the configured scheduler decision used for normative fallback.
    #[must_use]
    pub const fn fallback_decision(self) -> NativeContinuationScheduleDecision {
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
        fallback: NativeContinuationRetryFallback,
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
    /// Returns [`NativeContinuationRetryPolicyFailure`] while retaining the
    /// suspension when its scheduling reason is not `NativeRetry`.
    pub fn route(
        self,
        suspension: NativeContinuationScheduleSuspension,
        attempts: usize,
    ) -> Result<
        NativeContinuationRetryPolicyOutcome,
        Box<NativeContinuationRetryPolicyFailure>,
    > {
        if suspension.reason()
            != NativeContinuationScheduleStopReason::NativeRetry
        {
            return Err(Box::new(NativeContinuationRetryPolicyFailure {
                error: NativeContinuationRetryPolicyError::ScheduleReason {
                    observed: suspension.reason(),
                },
                suspension,
            }));
        }
        if attempts < self.max_native_attempts {
            return Ok(NativeContinuationRetryPolicyOutcome::NativeRetry(
                Box::new(NativeContinuationRetryNativeRoute {
                    attempts,
                    next_attempt: attempts.saturating_add(1),
                    suspension,
                }),
            ));
        }
        Ok(NativeContinuationRetryPolicyOutcome::Interpreter(Box::new(
            NativeContinuationRetryInterpreterRoute {
                attempts,
                decision: self.fallback.decision(),
                handoff: suspension.into_handoff(),
            },
        )))
    }
}

impl NativeContinuationRetryPolicyFailure {
    /// Returns the exact policy rejection.
    #[must_use]
    pub const fn error(&self) -> NativeContinuationRetryPolicyError {
        self.error
    }

    /// Consumes this failure and restores the exact suspension owner.
    #[must_use]
    pub fn into_suspension(self) -> NativeContinuationScheduleSuspension {
        self.suspension
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
