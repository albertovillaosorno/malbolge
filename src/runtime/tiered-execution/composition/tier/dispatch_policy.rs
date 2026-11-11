// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - One immutable process-local synchronous dispatch policy consisting of an
//     explicit canonical scheduler decision and a positive maximum turn count.
// - Must-Not:
//   - Infer decisions from telemetry, mutate policy during execution, spawn
//     workers, persist policy, or override queue/worker ownership semantics.
// - Allows:
//   - Inputs: one canonical decision variant and one positive turn bound.
//   - Outputs: exact policy snapshots, scheduler decisions, and one bounded
//     synchronous dispatch cycle.
//   - Side effects: only those of the delegated dispatch cycle.
// - Split-When:
//   - Adaptive policy, persistence, background execution, or distributed
//     scheduling gains independent authority.
// - Merge-When:
//   - Product orchestration owns policy selection and dispatch execution
//     atomically.
// - Summary:
//   - Repeats one explicit immutable scheduler decision under a positive bound.
// - Description:
//   - Canonical variants map directly to scheduler constructors without
//     inspecting private scheduler representation or execution behavior.
// - Usage:
//   - Configure one fixed decision and positive turn bound, then execute it
//     against a bounded affine dispatch queue.
// - Defaults:
//   - No implicit default policy exists; every decision and bound is explicit.
//

//! Immutable bounded policy for synchronous affine continuation dispatch.

use std::iter::repeat_n;
use std::num::NonZeroUsize;

use crate::continuation_dispatch_cycle::{
    NativeContinuationDispatchWorkerCycle,
    execute_native_continuation_dispatch_decisions,
};
use crate::continuation_dispatch_queue::NativeContinuationDispatchQueue;
use crate::continuation_scheduler::{
    NativeContinuationScheduleDecision, NativeContinuationYieldTarget,
};
use crate::monotonic_clock::NativeContinuationMonotonicClock;

/// Canonical explicit scheduler decision owned by one dispatch policy.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyDecision {
    /// Complete the remaining suffix through normative interpretation.
    CompleteInterpreter,
    /// Execute one positive bounded interpreter slice per dispatched owner.
    Interpret {
        /// Positive interpreter step budget for every worker turn.
        step_budget: NonZeroUsize,
    },
    /// Yield every dispatched owner directly back to its caller.
    YieldCaller,
    /// Yield every dispatched owner for possible native retry planning.
    YieldNativeRetry,
}

/// Immutable bounded synchronous dispatch policy.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationDispatchPolicy {
    decision: NativeContinuationDispatchPolicyDecision,
    maximum_turns: NonZeroUsize,
}

/// Canonical immutable representation of one complete dispatch policy.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationDispatchPolicySnapshot {
    decision: NativeContinuationDispatchPolicyDecision,
    maximum_turns: NonZeroUsize,
}

impl NativeContinuationDispatchPolicyDecision {
    /// Converts canonical policy evidence into one scheduler decision.
    #[must_use]
    pub const fn schedule_decision(self) -> NativeContinuationScheduleDecision {
        match self {
            Self::CompleteInterpreter => {
                NativeContinuationScheduleDecision::complete_interpreter()
            },
            Self::Interpret { step_budget } => {
                NativeContinuationScheduleDecision::interpret(step_budget)
            },
            Self::YieldCaller => NativeContinuationScheduleDecision::yield_to(
                NativeContinuationYieldTarget::Caller,
            ),
            Self::YieldNativeRetry => {
                NativeContinuationScheduleDecision::yield_to(
                    NativeContinuationYieldTarget::NativeRetry,
                )
            },
        }
    }
}

impl NativeContinuationDispatchPolicy {
    /// Returns the canonical decision configured for every worker turn.
    #[must_use]
    pub const fn decision(self) -> NativeContinuationDispatchPolicyDecision {
        self.decision
    }

    /// Reconstructs one policy from exact canonical immutable evidence.
    #[must_use]
    pub const fn from_snapshot(
        snapshot: NativeContinuationDispatchPolicySnapshot,
    ) -> Self {
        Self {
            decision: snapshot.decision,
            maximum_turns: snapshot.maximum_turns,
        }
    }

    /// Returns the positive maximum worker turns in one policy execution.
    #[must_use]
    pub const fn maximum_turns(self) -> NonZeroUsize {
        self.maximum_turns
    }

    /// Constructs one explicit immutable synchronous dispatch policy.
    #[must_use]
    pub const fn new(
        maximum_turns: NonZeroUsize,
        decision: NativeContinuationDispatchPolicyDecision,
    ) -> Self {
        Self { decision, maximum_turns }
    }

    /// Captures exact policy evidence without scheduler introspection.
    #[must_use]
    pub const fn snapshot(self) -> NativeContinuationDispatchPolicySnapshot {
        NativeContinuationDispatchPolicySnapshot {
            decision: self.decision,
            maximum_turns: self.maximum_turns,
        }
    }
}

impl NativeContinuationDispatchPolicySnapshot {
    /// Returns the canonical configured scheduler decision.
    #[must_use]
    pub const fn decision(self) -> NativeContinuationDispatchPolicyDecision {
        self.decision
    }

    /// Returns the positive configured maximum worker-turn count.
    #[must_use]
    pub const fn maximum_turns(self) -> NonZeroUsize {
        self.maximum_turns
    }
}

/// Executes one immutable bounded synchronous dispatch policy.
#[must_use]
pub fn execute_native_continuation_dispatch_policy<Clock>(
    queue: &mut NativeContinuationDispatchQueue<Clock>,
    policy: NativeContinuationDispatchPolicy,
) -> NativeContinuationDispatchWorkerCycle<Clock::Error>
where
    Clock: NativeContinuationMonotonicClock,
{
    execute_native_continuation_dispatch_decisions(
        queue,
        repeat_n(
            policy.decision.schedule_decision(),
            policy.maximum_turns.get(),
        ),
    )
}
