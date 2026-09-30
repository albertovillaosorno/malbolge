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
//   - Process-local retry-policy owner alignment from committed durable binding
//     evidence.
// - Must-Not:
//   - Persist policy, infer recommendations, retry CAS, roll back newer local
//     state, or overwrite equal-revision divergence.
// - Allows:
//   - Inputs: one mutable process-local owner and immutable durable binding
//     evidence.
//   - Outputs: exact no-commit, unchanged, synchronized, local-ahead, or
//     divergence evidence.
//   - Side effects: owner replacement only when committed durable revision is
//     strictly newer than local state.
// - Split-When:
//   - Multi-owner coordination or distributed consensus gains authority.
// - Merge-When:
//   - Product orchestration owns durable binding and local policy lifecycle.
// - Summary:
//   - Advances local policy ownership only from newer committed durable state.
// - Description:
//   - Equal revision must retain identical policy; stale durable state never
//     rolls local ownership backward.
// - Usage:
//   - Apply immediately after durable policy binding and before later policy
//     production.
// - Defaults:
//   - Deferred/conflict binding leaves the local owner unchanged.
//
//! Process-local owner synchronization from durable cached-retry policy
//! binding.

use std::cmp::Ordering;

use super::NativeContinuationCachedRetryDurablePolicyBinding;
use crate::retry_policy_owner::{
    NativeContinuationRetryPolicyOwner, NativeContinuationRetryPolicyState,
};

type OwnerSynchronization =
    NativeContinuationCachedRetryPolicyOwnerSynchronization;

/// Result of aligning one process-local owner with durable binding evidence.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryPolicyOwnerSynchronization {
    /// Durable and local revisions match but carry different policy.
    Diverged {
        /// Exact committed durable state that was not adopted.
        committed: NativeContinuationRetryPolicyState,
        /// Exact unchanged process-local state.
        current: NativeContinuationRetryPolicyState,
    },
    /// Process-local ownership is newer than the committed durable state.
    LocalAhead {
        /// Exact committed durable state that was not allowed to roll back.
        committed: NativeContinuationRetryPolicyState,
        /// Exact unchanged newer process-local state.
        current: NativeContinuationRetryPolicyState,
    },
    /// Binding contained no committed state, so local ownership was untouched.
    NoCommit {
        /// Exact unchanged process-local state.
        current: NativeContinuationRetryPolicyState,
    },
    /// A newer committed durable revision replaced process-local ownership.
    Synchronized {
        /// Exact committed state now owned locally.
        current: NativeContinuationRetryPolicyState,
        /// Exact process-local state replaced by synchronization.
        previous: NativeContinuationRetryPolicyState,
    },
    /// Process-local ownership already equals committed durable state.
    Unchanged {
        /// Exact shared local and durable state.
        current: NativeContinuationRetryPolicyState,
    },
}

/// Aligns process-local policy ownership with committed durable binding state.
///
/// Durable state can only advance local ownership. Equal revisions must retain
/// byte-equivalent policy semantics, while stale durable revisions and
/// equal-revision divergence are retained as explicit non-mutating evidence.
#[must_use]
pub fn synchronize_cached_retry_policy_owner_from_durable_binding<
    Recommendation,
    DurabilityError,
>(
    owner: &mut NativeContinuationRetryPolicyOwner,
    binding: &NativeContinuationCachedRetryDurablePolicyBinding<
        Recommendation,
        DurabilityError,
    >,
) -> NativeContinuationCachedRetryPolicyOwnerSynchronization {
    let current = owner.state();
    let Some(committed) = binding.active_state() else {
        return OwnerSynchronization::NoCommit { current };
    };
    match committed.revision().cmp(&current.revision()) {
        Ordering::Greater => {
            *owner = NativeContinuationRetryPolicyOwner::from_state(committed);
            OwnerSynchronization::Synchronized {
                current: committed,
                previous: current,
            }
        },
        Ordering::Less => {
            OwnerSynchronization::LocalAhead { committed, current }
        },
        Ordering::Equal if committed == current => {
            OwnerSynchronization::Unchanged { current }
        },
        Ordering::Equal => {
            OwnerSynchronization::Diverged { committed, current }
        },
    }
}
