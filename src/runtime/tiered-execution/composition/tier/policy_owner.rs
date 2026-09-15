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
//   - Process-local active retry-policy ownership and monotonic revision CAS.
// - Must-Not:
//   - Persist policy, coordinate processes, infer recommendations, or execute.
// - Allows:
//   - Inputs: one initial policy or one expected revision plus candidate
//     policy.
//   - Outputs: exact current state, committed replacement, or conflict
//     evidence.
//   - Side effects: mutation of this explicit process-local owner only.
// - Split-When:
//   - Durable publication, process locking, or distributed consensus is added.
// - Merge-When:
//   - One cross-cycle orchestrator owns policy selection and local publication.
// - Summary:
//   - Owns one active policy with explicit optimistic-concurrency revisions.
// - Description:
//   - Matching revisions advance once; conflicts and exhaustion never mutate.
// - Usage:
//   - Keep one owner across cached cycles and update through exact CAS
//     evidence.
// - Defaults:
//   - New owners begin at revision zero with the caller-supplied policy.
//

//! Process-local optimistic ownership for one active native retry policy.

use crate::retry_policy::NativeContinuationRetryPolicy;

/// Monotonic process-local revision of one active retry policy.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct NativeContinuationRetryPolicyRevision(u64);

/// Exact immutable state currently held by one active-policy owner.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryPolicyState {
    policy: NativeContinuationRetryPolicy,
    revision: NativeContinuationRetryPolicyRevision,
}

/// Process-local owner of one active retry policy and its monotonic revision.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryPolicyOwner {
    state: NativeContinuationRetryPolicyState,
}

/// Result of one compare-and-swap publication attempt.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationRetryPolicyOwnerUpdate {
    /// Expected revision was stale; active state did not change.
    Conflict {
        /// Candidate policy that was not published.
        candidate: NativeContinuationRetryPolicy,
        /// Exact active state observed at conflict detection.
        current: NativeContinuationRetryPolicyState,
        /// Caller-supplied stale expected revision.
        expected: NativeContinuationRetryPolicyRevision,
    },
    /// Expected revision matched and candidate became the active policy.
    Published {
        /// Exact active state after publication.
        current: NativeContinuationRetryPolicyState,
        /// Exact active state before publication.
        previous: NativeContinuationRetryPolicyState,
    },
}

/// Why an otherwise matching active-policy update failed closed.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationRetryPolicyOwnerError {
    /// Current revision reached the maximum representable monotonic value.
    RevisionExhausted {
        /// Exact unchanged active state at exhaustion.
        current: NativeContinuationRetryPolicyState,
        /// Candidate policy that was not published.
        candidate: NativeContinuationRetryPolicy,
    },
}

impl NativeContinuationRetryPolicyRevision {
    /// Reconstructs one exact revision value from validated durable evidence.
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

impl NativeContinuationRetryPolicyState {
    /// Constructs one exact state from validated policy and revision evidence.
    #[must_use]
    pub const fn new(
        policy: NativeContinuationRetryPolicy,
        revision: NativeContinuationRetryPolicyRevision,
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
        candidate: NativeContinuationRetryPolicy,
    ) -> Result<Self, NativeContinuationRetryPolicyOwnerError> {
        let Some(next_revision) = self.revision.0.checked_add(1) else {
            return Err(
                NativeContinuationRetryPolicyOwnerError::RevisionExhausted {
                    candidate,
                    current: self,
                },
            );
        };
        Ok(Self {
            policy: candidate,
            revision: NativeContinuationRetryPolicyRevision(next_revision),
        })
    }

    /// Returns the exact active retry policy.
    #[must_use]
    pub const fn policy(self) -> NativeContinuationRetryPolicy {
        self.policy
    }

    /// Returns the exact active-policy revision.
    #[must_use]
    pub const fn revision(self) -> NativeContinuationRetryPolicyRevision {
        self.revision
    }
}

impl NativeContinuationRetryPolicyOwner {
    /// Attempts one revision-guarded active-policy replacement.
    ///
    /// # Errors
    ///
    /// Returns revision-exhaustion evidence without mutating the owner.
    pub fn compare_and_swap(
        &mut self,
        expected: NativeContinuationRetryPolicyRevision,
        candidate: NativeContinuationRetryPolicy,
    ) -> Result<
        NativeContinuationRetryPolicyOwnerUpdate,
        NativeContinuationRetryPolicyOwnerError,
    > {
        let previous = self.state;
        if expected != previous.revision {
            return Ok(NativeContinuationRetryPolicyOwnerUpdate::Conflict {
                candidate,
                current: previous,
                expected,
            });
        }
        self.state = previous.next(candidate)?;
        Ok(NativeContinuationRetryPolicyOwnerUpdate::Published {
            current: self.state,
            previous,
        })
    }

    /// Reconstructs one process-local owner from exact validated state.
    #[must_use]
    pub const fn from_state(state: NativeContinuationRetryPolicyState) -> Self {
        Self { state }
    }

    /// Constructs one process-local owner at revision zero.
    #[must_use]
    pub const fn new(policy: NativeContinuationRetryPolicy) -> Self {
        Self {
            state: NativeContinuationRetryPolicyState {
                policy,
                revision: NativeContinuationRetryPolicyRevision::initial(),
            },
        }
    }

    /// Returns exact immutable active-policy state.
    #[must_use]
    pub const fn state(&self) -> NativeContinuationRetryPolicyState {
        self.state
    }
}
