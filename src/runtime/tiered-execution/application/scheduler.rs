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
//   - Explicit caller-driven scheduling of one interpreter continuation owner.
// - Must-Not:
//   - Replan native code, infer budgets, or duplicate checkpoint ownership.
// - Allows:
//   - Inputs: one affine handoff and one explicit scheduling decision.
//   - Outputs: completion or one reasoned affine suspension.
//   - Side effects: normative interpreter mutation only when requested.
// - Split-When:
//   - Native retry execution or asynchronous queue ownership gains policy.
// - Merge-When:
//   - One product coordinator owns all tier selection and interpreter slices.
// - Summary:
//   - Applies explicit complete, slice, or yield continuation decisions.
// - Description:
//   - Preserves exact suffix authority while exposing why scheduling paused.
// - Usage:
//   - Consume a handoff with `schedule_native_interpreter_handoff()`.
// - Defaults:
//   - Yield decisions execute zero steps and never attempt a native retry.
//

//! Caller-driven scheduling for exact interpreter continuation ownership.

use std::num::NonZeroUsize;

use malbolge::{ProfileMachineState, RegionEffectProgram};

use crate::execution_native::{
    NativeExecutableSequenceKey, NativeInterpreterContinuation,
};
use crate::interpreter_handoff::{
    NativeInterpreterHandoff, NativeInterpreterHandoffBudgetOutcome,
    NativeInterpreterHandoffCompletion,
    NativeInterpreterHandoffExecutionFailure,
    NativeInterpreterHandoffSuspension,
};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum NativeContinuationScheduleKind {
    CompleteInterpreter,
    Interpret,
    YieldCaller,
    YieldNativeRetry,
}

/// One explicit scheduling decision for an affine interpreter handoff.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationScheduleDecision {
    kind: NativeContinuationScheduleKind,
    step_budget: usize,
}

/// Result of one explicit continuation scheduling turn.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationScheduleOutcome {
    /// Normative interpretation completed and validated the original plan.
    Completed(NativeInterpreterHandoffCompletion),
    /// Exact suffix ownership remains after a reasoned scheduling pause.
    Suspended(NativeContinuationScheduleSuspension),
}

/// Why one scheduling turn returned an exact remaining suffix.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationScheduleStopReason {
    /// A positive interpreter slice consumed its complete step budget.
    BudgetExhausted,
    /// The caller explicitly requested ownership back without execution.
    CallerYield,
    /// The caller requested an exact suffix for possible native replanning.
    NativeRetry,
}

/// One reasoned affine suspension returned by the scheduler.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationScheduleSuspension {
    reason: NativeContinuationScheduleStopReason,
    suspension: NativeInterpreterHandoffSuspension,
}

/// Explicit zero-step ownership target selected by the caller.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationYieldTarget {
    /// Return exact ownership to the caller without tier preference.
    Caller,
    /// Return exact ownership for a possible future native retry attempt.
    NativeRetry,
}

/// Result of one caller-driven continuation scheduling decision.
pub type NativeContinuationScheduleResult = Result<
    NativeContinuationScheduleOutcome,
    Box<NativeInterpreterHandoffExecutionFailure>,
>;

impl NativeContinuationScheduleDecision {
    /// Selects complete normative interpretation of the remaining suffix.
    #[must_use]
    pub const fn complete_interpreter() -> Self {
        Self {
            kind: NativeContinuationScheduleKind::CompleteInterpreter,
            step_budget: 0,
        }
    }

    /// Selects one positive normative interpreter slice.
    #[must_use]
    pub const fn interpret(step_budget: NonZeroUsize) -> Self {
        Self {
            kind: NativeContinuationScheduleKind::Interpret,
            step_budget: step_budget.get(),
        }
    }

    /// Selects a zero-step ownership yield.
    #[must_use]
    pub const fn yield_to(target: NativeContinuationYieldTarget) -> Self {
        let kind = match target {
            NativeContinuationYieldTarget::Caller => {
                NativeContinuationScheduleKind::YieldCaller
            },
            NativeContinuationYieldTarget::NativeRetry => {
                NativeContinuationScheduleKind::YieldNativeRetry
            },
        };
        Self { kind, step_budget: 0 }
    }
}

impl NativeContinuationScheduleSuspension {
    /// Returns the original exact native continuation authority.
    #[must_use]
    pub const fn continuation(&self) -> &NativeInterpreterContinuation {
        self.suspension.continuation()
    }

    /// Returns cumulative interpreter progress after native execution.
    #[must_use]
    pub const fn interpreter_steps(&self) -> usize {
        self.suspension.interpreter_steps()
    }

    /// Converts this affine scheduler suspension into an executable handoff.
    #[must_use]
    pub fn into_handoff(self) -> NativeInterpreterHandoff {
        self.suspension.into_handoff()
    }

    /// Returns why this scheduling turn preserved the remaining suffix.
    #[must_use]
    pub const fn reason(&self) -> NativeContinuationScheduleStopReason {
        self.reason
    }

    /// Returns the exact artifact-key suffix still requiring execution.
    #[must_use]
    pub const fn remaining_key(&self) -> &NativeExecutableSequenceKey {
        self.suspension.remaining_key()
    }

    /// Returns exact one-step programs still requiring execution.
    #[must_use]
    pub fn remaining_programs(&self) -> &[RegionEffectProgram] {
        self.suspension.remaining_programs()
    }

    /// Returns the number of semantic steps still requiring execution.
    #[must_use]
    pub const fn remaining_steps(&self) -> usize {
        self.suspension.remaining_steps()
    }

    /// Reschedules this exact affine suffix under another explicit decision.
    ///
    /// # Errors
    ///
    /// Returns [`NativeInterpreterHandoffExecutionFailure`] when requested
    /// normative interpreter work fails exact admission.
    pub fn resume(
        self,
        decision: NativeContinuationScheduleDecision,
    ) -> NativeContinuationScheduleResult {
        schedule_native_interpreter_handoff(self.into_handoff(), decision)
    }

    /// Returns the next complete-plan semantic index.
    #[must_use]
    pub const fn resume_index(&self) -> usize {
        self.suspension.resume_index()
    }

    /// Returns the exact normative checkpoint at this scheduling boundary.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        self.suspension.state()
    }
}

/// Applies one explicit scheduling decision to one affine interpreter handoff.
///
/// Yield decisions execute zero semantic steps. `NativeRetry` is evidence only:
/// this boundary never replans or invokes native code.
///
/// # Errors
///
/// Returns [`NativeInterpreterHandoffExecutionFailure`] when requested
/// normative interpreter work fails exact admission.
pub fn schedule_native_interpreter_handoff(
    handoff: NativeInterpreterHandoff,
    decision: NativeContinuationScheduleDecision,
) -> NativeContinuationScheduleResult {
    match decision.kind {
        NativeContinuationScheduleKind::CompleteInterpreter => handoff
            .execute()
            .map(NativeContinuationScheduleOutcome::Completed),
        NativeContinuationScheduleKind::Interpret => schedule_budget(
            handoff,
            decision.step_budget,
            NativeContinuationScheduleStopReason::BudgetExhausted,
        ),
        NativeContinuationScheduleKind::YieldCaller => schedule_budget(
            handoff,
            0,
            NativeContinuationScheduleStopReason::CallerYield,
        ),
        NativeContinuationScheduleKind::YieldNativeRetry => schedule_budget(
            handoff,
            0,
            NativeContinuationScheduleStopReason::NativeRetry,
        ),
    }
}

fn schedule_budget(
    handoff: NativeInterpreterHandoff,
    step_budget: usize,
    reason: NativeContinuationScheduleStopReason,
) -> NativeContinuationScheduleResult {
    handoff
        .execute_with_budget(step_budget)
        .map(|outcome| match outcome {
            NativeInterpreterHandoffBudgetOutcome::Completed(completion) => {
                NativeContinuationScheduleOutcome::Completed(completion)
            },
            NativeInterpreterHandoffBudgetOutcome::Suspended(suspension) => {
                NativeContinuationScheduleOutcome::Suspended(
                    NativeContinuationScheduleSuspension { reason, suspension },
                )
            },
        })
}
