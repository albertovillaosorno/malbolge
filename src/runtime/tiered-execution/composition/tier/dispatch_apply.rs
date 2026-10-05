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
//   - Process-local publication of one exact adaptive dispatch-policy
//     selection.
// - Must-Not:
//   - Assess telemetry, infer policy, persist state, coordinate processes, or
//     bypass revision-guarded owner publication.
// - Allows:
//   - Inputs: one adaptation, expected revision, and process-local owner.
//   - Outputs: deferred unchanged state, exact conflict, committed replacement,
//     or owner failure retaining adaptation evidence.
//   - Side effects: mutation of the supplied process-local owner only when a
//     ready adaptation matches the expected revision.
// - Split-When:
//   - Durable adaptive publication or multi-owner coordination gains authority.
// - Merge-When:
//   - Adaptive selection and process-local active ownership become atomic.
// - Summary:
//   - Applies sufficient adaptive evidence through the existing owner CAS.
// - Description:
//   - Deferral never mutates; ready evidence preserves exact owner outcomes.
// - Usage:
//   - Supply the revision observed before adaptation plus its exact result.
// - Defaults:
//   - Insufficient adaptation leaves the active policy unchanged.
//

//! Process-local publication of adaptive synchronous dispatch policy.

use crate::continuation_dispatch_policy_adaptation as adaptation;
use crate::continuation_dispatch_policy_owner::{
    NativeContinuationDispatchPolicyOwner,
    NativeContinuationDispatchPolicyOwnerError,
    NativeContinuationDispatchPolicyOwnerUpdate,
    NativeContinuationDispatchPolicyRevision,
    NativeContinuationDispatchPolicyState,
};

type DispatchAdaptation =
    adaptation::NativeContinuationDispatchPolicyAdaptation;

/// Exact failure retaining adaptive evidence and owner rejection evidence.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationDispatchPolicyAdaptationFailure {
    adaptation: DispatchAdaptation,
    error: NativeContinuationDispatchPolicyOwnerError,
}

/// Exact result of applying one adaptation to the process-local active owner.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyAdaptationPublication {
    /// Expected revision was stale; no active-policy mutation occurred.
    Conflict {
        /// Exact adaptation whose selected policy was rejected.
        adaptation: DispatchAdaptation,
        /// Exact active state observed at conflict detection.
        current: NativeContinuationDispatchPolicyState,
        /// Caller-supplied stale expected revision.
        expected: NativeContinuationDispatchPolicyRevision,
    },
    /// Adaptation deferred because telemetry evidence was insufficient.
    Deferred {
        /// Exact deferred adaptation evidence.
        adaptation: DispatchAdaptation,
        /// Exact unchanged active state.
        current: NativeContinuationDispatchPolicyState,
    },
    /// Ready adaptation replaced the process-local active policy.
    Published {
        /// Exact sufficient adaptation evidence that selected the policy.
        adaptation: DispatchAdaptation,
        /// Exact active state after publication.
        current: NativeContinuationDispatchPolicyState,
        /// Exact active state before publication.
        previous: NativeContinuationDispatchPolicyState,
    },
}

impl NativeContinuationDispatchPolicyAdaptationFailure {
    /// Returns the exact adaptation whose policy was not published.
    #[must_use]
    pub const fn adaptation(&self) -> DispatchAdaptation {
        self.adaptation
    }

    /// Returns exact process-local owner rejection evidence.
    #[must_use]
    pub const fn error(&self) -> NativeContinuationDispatchPolicyOwnerError {
        self.error
    }
}

/// Applies one exact adaptation through process-local revisioned ownership.
///
/// # Errors
///
/// Returns owner revision exhaustion while retaining the complete adaptation.
pub fn publish_native_continuation_dispatch_policy_adaptation(
    owner: &mut NativeContinuationDispatchPolicyOwner,
    expected: NativeContinuationDispatchPolicyRevision,
    adaptation: DispatchAdaptation,
) -> Result<
    NativeContinuationDispatchPolicyAdaptationPublication,
    Box<NativeContinuationDispatchPolicyAdaptationFailure>,
> {
    let Some(candidate) = adaptation.policy() else {
        return Ok(
            NativeContinuationDispatchPolicyAdaptationPublication::Deferred {
                adaptation,
                current: owner.state(),
            },
        );
    };
    let update =
        owner
            .compare_and_swap(expected, candidate)
            .map_err(|error| {
                Box::new(NativeContinuationDispatchPolicyAdaptationFailure {
                    adaptation,
                    error,
                })
            })?;
    Ok(match update {
        NativeContinuationDispatchPolicyOwnerUpdate::Conflict {
            current,
            expected: observed_expected,
            ..
        } => NativeContinuationDispatchPolicyAdaptationPublication::Conflict {
            adaptation,
            current,
            expected: observed_expected,
        },
        NativeContinuationDispatchPolicyOwnerUpdate::Published {
            current,
            previous,
        } => NativeContinuationDispatchPolicyAdaptationPublication::Published {
            adaptation,
            current,
            previous,
        },
    })
}
