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
//   - Process-local active dispatch-policy ownership and revision CAS.
// - Must-Not:
//   - Persist policy, coordinate processes, infer policy, execute dispatch, or
//     interpret revisions as time, priority, storage generation, or quality.
// - Allows:
//   - Inputs: one initial policy or one expected revision plus candidate
//     policy.
//   - Outputs: exact current state, committed replacement, or conflict
//     evidence.
//   - Side effects: mutation of this explicit process-local owner only.
// - Split-When:
//   - Durable state framing, publication, process locking, or distributed
//     consensus gains authority.
// - Merge-When:
//   - One dispatch orchestrator owns policy selection and local publication.
// - Summary:
//   - Owns one active dispatch policy with optimistic-concurrency revisions.
// - Description:
//   - Matching revisions advance once; conflicts and exhaustion never mutate.
// - Usage:
//   - Keep one owner across dispatch cycles and update through exact CAS
//     evidence.
// - Defaults:
//   - New owners begin at revision zero with the caller-supplied policy.
//

//! Process-local optimistic ownership for one active synchronous dispatch
//! policy.

use crate::continuation_dispatch_policy::NativeContinuationDispatchPolicy;

/// Monotonic process-local revision of one active dispatch policy.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct NativeContinuationDispatchPolicyRevision(u64);

/// Exact immutable state currently held by one active-policy owner.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationDispatchPolicyState {
    policy: NativeContinuationDispatchPolicy,
    revision: NativeContinuationDispatchPolicyRevision,
}

/// Process-local owner of one active dispatch policy and its revision.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationDispatchPolicyOwner {
    state: NativeContinuationDispatchPolicyState,
}

/// Result of one compare-and-swap publication attempt.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyOwnerUpdate {
    /// Expected revision was stale; active state did not change.
    Conflict {
        /// Candidate policy that was not published.
        candidate: NativeContinuationDispatchPolicy,
        /// Exact active state observed at conflict detection.
        current: NativeContinuationDispatchPolicyState,
        /// Caller-supplied stale expected revision.
        expected: NativeContinuationDispatchPolicyRevision,
    },
    /// Expected revision matched and candidate became the active policy.
    Published {
        /// Exact active state after publication.
        current: NativeContinuationDispatchPolicyState,
        /// Exact active state before publication.
        previous: NativeContinuationDispatchPolicyState,
    },
}

/// Why an otherwise matching active-policy update failed closed.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyOwnerError {
    /// Current revision reached the maximum representable monotonic value.
    RevisionExhausted {
        /// Exact unchanged active state at exhaustion.
        current: NativeContinuationDispatchPolicyState,
        /// Candidate policy that was not published.
        candidate: NativeContinuationDispatchPolicy,
    },
}

impl NativeContinuationDispatchPolicyRevision {
    /// Reconstructs one exact revision value from validated evidence.
    #[must_use]
    pub const fn from_value(value: u64) -> Self {
        Self(value)
    }

    /// Returns the initial active-policy revision.
    #[must_use]
    pub const fn initial() -> Self {
        Self(0)
    }

    /// Returns the exact process-local revision value.
    #[must_use]
    pub const fn value(self) -> u64 {
        self.0
    }
}

impl NativeContinuationDispatchPolicyState {
    /// Constructs one exact state from validated policy and revision evidence.
    #[must_use]
    pub const fn new(
        policy: NativeContinuationDispatchPolicy,
        revision: NativeContinuationDispatchPolicyRevision,
    ) -> Self {
        Self { policy, revision }
    }

    /// Derives one exactly revision-advanced candidate state.
    ///
    /// # Errors
    ///
    /// Returns revision-exhaustion evidence without changing this state.
    pub(crate) const fn next(
        self,
        candidate: NativeContinuationDispatchPolicy,
    ) -> Result<Self, NativeContinuationDispatchPolicyOwnerError> {
        let Some(next_revision) = self.revision.0.checked_add(1) else {
            return Err(
                NativeContinuationDispatchPolicyOwnerError::RevisionExhausted {
                    candidate,
                    current: self,
                },
            );
        };
        Ok(Self {
            policy: candidate,
            revision: NativeContinuationDispatchPolicyRevision(next_revision),
        })
    }

    /// Returns the exact active dispatch policy.
    #[must_use]
    pub const fn policy(self) -> NativeContinuationDispatchPolicy {
        self.policy
    }

    /// Returns the exact active-policy revision.
    #[must_use]
    pub const fn revision(self) -> NativeContinuationDispatchPolicyRevision {
        self.revision
    }
}

impl NativeContinuationDispatchPolicyOwner {
    /// Attempts one revision-guarded active-policy replacement.
    ///
    /// # Errors
    ///
    /// Returns revision-exhaustion evidence without mutating the owner.
    pub fn compare_and_swap(
        &mut self,
        expected: NativeContinuationDispatchPolicyRevision,
        candidate: NativeContinuationDispatchPolicy,
    ) -> Result<
        NativeContinuationDispatchPolicyOwnerUpdate,
        NativeContinuationDispatchPolicyOwnerError,
    > {
        let previous = self.state;
        if expected != previous.revision {
            return Ok(NativeContinuationDispatchPolicyOwnerUpdate::Conflict {
                candidate,
                current: previous,
                expected,
            });
        }
        self.state = previous.next(candidate)?;
        Ok(NativeContinuationDispatchPolicyOwnerUpdate::Published {
            current: self.state,
            previous,
        })
    }

    /// Reconstructs one process-local owner from exact validated state.
    #[must_use]
    pub const fn from_state(
        state: NativeContinuationDispatchPolicyState,
    ) -> Self {
        Self { state }
    }

    /// Constructs one process-local owner at revision zero.
    #[must_use]
    pub const fn new(policy: NativeContinuationDispatchPolicy) -> Self {
        Self {
            state: NativeContinuationDispatchPolicyState {
                policy,
                revision: NativeContinuationDispatchPolicyRevision::initial(),
            },
        }
    }

    /// Returns exact immutable active-policy state.
    #[must_use]
    pub const fn state(&self) -> NativeContinuationDispatchPolicyState {
        self.state
    }
}
