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
//   - Explicit caller-driven scheduling of one fused interpreter handoff.
// - Must-Not:
//   - Replan native code, mutate caches, infer budgets, or duplicate
//     checkpoints.
// - Allows:
//   - Inputs: one affine fused handoff plus one explicit scheduling decision.
//   - Outputs: completion or one reasoned affine source-step suspension.
//   - Side effects: normative interpreter mutation only when requested.
// - Split-When:
//   - Native retry execution or asynchronous queue ownership gains policy.
// - Merge-When:
//   - One fused coordinator owns all fallback scheduling decisions.
// - Summary:
//   - Applies complete, positive-slice, or zero-step yield decisions.
// - Description:
//   - Preserves exact source-step progress and why scheduling paused.
// - Usage:
//   - Consume a handoff with `schedule_direct_fused_native_handoff()`.
// - Defaults:
//   - Yield decisions execute zero steps; native retry remains evidence only.
//

//! Caller-driven scheduling for fused interpreter fallback ownership.

use std::num::NonZeroUsize;

use malbolge::{ProfileMachineState, RegionEffectProgram};

use super::fused_sequence_continuation::DirectFusedNativeContinuation;
use super::fused_sequence_handoff::{
    DirectFusedNativeHandoffBudgetOutcome, DirectFusedNativeHandoffCompletion,
    DirectFusedNativeHandoffExecutionFailure,
    DirectFusedNativeHandoffSuspension, DirectFusedNativeInterpreterHandoff,
};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum DirectFusedNativeScheduleKind {
    CompleteInterpreter,
    Interpret,
    YieldCaller,
    YieldNativeRetry,
}

/// One explicit scheduling decision for an affine fused interpreter handoff.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct DirectFusedNativeScheduleDecision {
    kind: DirectFusedNativeScheduleKind,
    step_budget: usize,
}

/// Result of one explicit fused continuation scheduling turn.
#[derive(Debug, Eq, PartialEq)]
pub enum DirectFusedNativeScheduleOutcome {
    /// Normative interpretation completed and validated the fused plan.
    Completed(DirectFusedNativeHandoffCompletion),
    /// Exact source-step ownership remains after a reasoned scheduling pause.
    Suspended(DirectFusedNativeScheduleSuspension),
}

/// Why one fused scheduling turn preserved remaining source work.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectFusedNativeScheduleStopReason {
    /// A positive interpreter slice consumed its complete source-step budget.
    BudgetExhausted,
    /// The caller explicitly requested ownership back without execution.
    CallerYield,
    /// The caller requested source-step evidence for possible native
    /// replanning.
    NativeRetry,
}

/// One reasoned affine fused interpreter suspension.
#[derive(Debug, Eq, PartialEq)]
pub struct DirectFusedNativeScheduleSuspension {
    reason: DirectFusedNativeScheduleStopReason,
    suspension: DirectFusedNativeHandoffSuspension,
}

/// Explicit zero-step ownership target selected by the caller.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectFusedNativeYieldTarget {
    /// Return exact source-step ownership to the caller without tier
    /// preference.
    Caller,
    /// Return ownership for a possible future native replanning attempt.
    NativeRetry,
}

/// Result of one caller-driven fused continuation scheduling decision.
pub type DirectFusedNativeScheduleResult = Result<
    DirectFusedNativeScheduleOutcome,
    Box<DirectFusedNativeHandoffExecutionFailure>,
>;

impl DirectFusedNativeScheduleDecision {
    /// Selects complete normative interpretation of the remaining source
    /// suffix.
    #[must_use]
    pub const fn complete_interpreter() -> Self {
        Self {
            kind: DirectFusedNativeScheduleKind::CompleteInterpreter,
            step_budget: 0,
        }
    }

    /// Selects one positive normative interpreter source-step slice.
    #[must_use]
    pub const fn interpret(step_budget: NonZeroUsize) -> Self {
        Self {
            kind: DirectFusedNativeScheduleKind::Interpret,
            step_budget: step_budget.get(),
        }
    }

    /// Selects a zero-step ownership yield.
    #[must_use]
    pub const fn yield_to(target: DirectFusedNativeYieldTarget) -> Self {
        let kind = match target {
            DirectFusedNativeYieldTarget::Caller => {
                DirectFusedNativeScheduleKind::YieldCaller
            },
            DirectFusedNativeYieldTarget::NativeRetry => {
                DirectFusedNativeScheduleKind::YieldNativeRetry
            },
        };
        Self { kind, step_budget: 0 }
    }
}

impl DirectFusedNativeScheduleSuspension {
    /// Returns the original fused continuation authority.
    #[must_use]
    pub const fn continuation(&self) -> &DirectFusedNativeContinuation {
        self.suspension.continuation()
    }

    /// Returns cumulative normative interpreter progress.
    #[must_use]
    pub const fn interpreter_steps(&self) -> usize {
        self.suspension.interpreter_steps()
    }

    /// Converts this scheduler suspension into an executable fused handoff.
    #[must_use]
    pub fn into_handoff(self) -> DirectFusedNativeInterpreterHandoff {
        self.suspension.into_handoff()
    }

    /// Returns why this scheduling turn preserved remaining source work.
    #[must_use]
    pub const fn reason(&self) -> DirectFusedNativeScheduleStopReason {
        self.reason
    }

    /// Returns exact one-step source programs still requiring execution.
    #[must_use]
    pub fn remaining_programs(&self) -> &[RegionEffectProgram] {
        self.suspension.remaining_programs()
    }

    /// Returns the number of source semantic steps still requiring execution.
    #[must_use]
    pub const fn remaining_steps(&self) -> usize {
        self.suspension.remaining_steps()
    }

    /// Reschedules this exact affine source suffix under another decision.
    ///
    /// # Errors
    ///
    /// Returns fused handoff failure when requested interpreter work fails
    /// exact normative admission.
    pub fn resume(
        self,
        decision: DirectFusedNativeScheduleDecision,
    ) -> DirectFusedNativeScheduleResult {
        schedule_direct_fused_native_handoff(self.into_handoff(), decision)
    }

    /// Returns the next complete-plan source semantic-step index.
    #[must_use]
    pub const fn resume_step(&self) -> usize {
        self.suspension.resume_step()
    }

    /// Returns the exact normative checkpoint at this scheduling boundary.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        self.suspension.state()
    }
}

/// Applies one explicit scheduling decision to one affine fused handoff.
///
/// Yield decisions execute zero source semantic steps. `NativeRetry` is
/// evidence only: this boundary never replans, caches, loads, or invokes native
/// code.
///
/// # Errors
///
/// Returns fused handoff failure when requested normative interpreter work
/// fails exact admission.
pub fn schedule_direct_fused_native_handoff(
    handoff: DirectFusedNativeInterpreterHandoff,
    decision: DirectFusedNativeScheduleDecision,
) -> DirectFusedNativeScheduleResult {
    match decision.kind {
        DirectFusedNativeScheduleKind::CompleteInterpreter => handoff
            .execute()
            .map(DirectFusedNativeScheduleOutcome::Completed),
        DirectFusedNativeScheduleKind::Interpret => schedule_budget(
            handoff,
            decision.step_budget,
            DirectFusedNativeScheduleStopReason::BudgetExhausted,
        ),
        DirectFusedNativeScheduleKind::YieldCaller => schedule_budget(
            handoff,
            0,
            DirectFusedNativeScheduleStopReason::CallerYield,
        ),
        DirectFusedNativeScheduleKind::YieldNativeRetry => schedule_budget(
            handoff,
            0,
            DirectFusedNativeScheduleStopReason::NativeRetry,
        ),
    }
}

fn schedule_budget(
    handoff: DirectFusedNativeInterpreterHandoff,
    step_budget: usize,
    reason: DirectFusedNativeScheduleStopReason,
) -> DirectFusedNativeScheduleResult {
    handoff
        .execute_with_budget(step_budget)
        .map(|outcome| match outcome {
            DirectFusedNativeHandoffBudgetOutcome::Completed(completion) => {
                DirectFusedNativeScheduleOutcome::Completed(completion)
            },
            DirectFusedNativeHandoffBudgetOutcome::Suspended(suspension) => {
                DirectFusedNativeScheduleOutcome::Suspended(
                    DirectFusedNativeScheduleSuspension { reason, suspension },
                )
            },
        })
}
