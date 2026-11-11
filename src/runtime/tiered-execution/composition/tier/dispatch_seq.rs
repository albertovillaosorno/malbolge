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
//   - One immutable non-empty ordered sequence of canonical synchronous
//     dispatch-policy decisions.
// - Must-Not:
//   - Infer or adapt decisions, persist policy, spawn workers, or change queue
//     ownership and worker failure semantics.
// - Allows:
//   - Inputs: one exact finite ordered canonical decision sequence.
//   - Outputs: exact sequence evidence and one bounded synchronous cycle.
//   - Side effects: only those of the delegated explicit-decision cycle.
// - Split-When:
//   - Adaptive choice, durable sequence transport, or background lifecycle
//     gains independent authority.
// - Merge-When:
//   - One product coordinator owns policy selection and execution atomically.
// - Summary:
//   - Replays one finite heterogeneous immutable dispatch decision sequence.
// - Description:
//   - Sequence order is policy evidence; no telemetry or runtime result changes
//     the next configured decision.
// - Usage:
//   - Construct from a non-empty decision vector and execute against one queue.
// - Defaults:
//   - Empty sequences are rejected; there is no implicit decision.
//

//! Immutable heterogeneous policy for bounded synchronous continuation
//! dispatch.

use std::num::NonZeroUsize;

use crate::continuation_dispatch_cycle::{
    NativeContinuationDispatchWorkerCycle,
    execute_native_continuation_dispatch_decisions,
};
use crate::continuation_dispatch_policy as dispatch_policy;
use crate::continuation_dispatch_queue::NativeContinuationDispatchQueue;
use crate::monotonic_clock::NativeContinuationMonotonicClock;

type PolicyDecision = dispatch_policy::NativeContinuationDispatchPolicyDecision;

/// Why one mixed dispatch-policy sequence could not be constructed.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicySequenceError {
    /// A policy sequence must own at least one explicit decision.
    Empty,
}

/// Immutable non-empty ordered mixed-decision synchronous dispatch policy.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeContinuationDispatchPolicySequence {
    decisions: Box<[PolicyDecision]>,
    length: NonZeroUsize,
}

impl NativeContinuationDispatchPolicySequence {
    /// Returns the exact canonical ordered policy decisions.
    #[must_use]
    pub fn decisions(&self) -> &[PolicyDecision] {
        &self.decisions
    }

    /// Returns the exact positive number of configured worker turns.
    #[must_use]
    pub const fn length(&self) -> NonZeroUsize {
        self.length
    }

    /// Constructs one immutable finite heterogeneous dispatch policy.
    ///
    /// # Errors
    ///
    /// Rejects an empty decision vector rather than inventing a default.
    pub fn new(
        decisions: Vec<
            dispatch_policy::NativeContinuationDispatchPolicyDecision,
        >,
    ) -> Result<Self, NativeContinuationDispatchPolicySequenceError> {
        let Some(length) = NonZeroUsize::new(decisions.len()) else {
            return Err(NativeContinuationDispatchPolicySequenceError::Empty);
        };
        Ok(Self {
            decisions: decisions.into_boxed_slice(),
            length,
        })
    }
}

/// Executes one immutable mixed-decision synchronous dispatch policy.
#[must_use]
pub fn execute_native_continuation_dispatch_policy_sequence<Clock>(
    queue: &mut NativeContinuationDispatchQueue<Clock>,
    policy: &NativeContinuationDispatchPolicySequence,
) -> NativeContinuationDispatchWorkerCycle<Clock::Error>
where
    Clock: NativeContinuationMonotonicClock,
{
    execute_native_continuation_dispatch_decisions(
        queue,
        policy
            .decisions()
            .iter()
            .copied()
            .map(PolicyDecision::schedule_decision),
    )
}
