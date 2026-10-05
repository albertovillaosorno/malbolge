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
//   - Pure caller-selected precedence over one completed count-plus-latency
//     dispatch-policy arbitration.
// - Must-Not:
//   - Assess telemetry, adapt signals, alter arbitration evidence, publish
//     policy, persist precedence, or invent additional evidence classes.
// - Allows:
//   - Inputs: one exact arbitration and one explicit precedence mode.
//   - Outputs: agreed, deferred, selected, or withheld policy evidence.
//   - Side effects: none.
// - Split-When:
//   - Additional signals, weighted arbitration, or durable precedence state
//     gains authority.
// - Merge-When:
//   - Product orchestration owns precedence and publication atomically.
// - Summary:
//   - Resolves ready disagreement only when caller explicitly chooses a signal.
// - Description:
//   - Agreement is invariant; insufficient evidence always defers.
// - Usage:
//   - Arbitrate first, then apply one immutable caller-selected precedence
//     mode.
// - Defaults:
//   - Agreement-only precedence withholds ready disagreement.
//

//! Caller-selected precedence over exact mixed dispatch-policy evidence.

use crate::{
    continuation_dispatch_policy as dispatch_policy,
    continuation_dispatch_policy_mixed_evidence as mixed,
};

type Arbitration = mixed::NativeContinuationDispatchPolicyAdaptationArbitration;
type DispatchPolicy = dispatch_policy::NativeContinuationDispatchPolicy;

/// Explicit caller policy for resolving ready count/latency disagreement.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyPrecedence {
    /// Preserve agreement-only authority and withhold ready disagreement.
    #[default]
    AgreementOnly,
    /// Select the count-adaptation policy when both ready signals disagree.
    Count,
    /// Select the latency-adaptation policy when both ready signals disagree.
    Latency,
}

/// Exact result of applying one caller-selected precedence policy.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyPrecedenceSelection {
    /// Existing arbitration agreement already authorized this policy.
    Agreed {
        /// Exact arbitration evidence.
        arbitration: Arbitration,
        /// Exact agreed dispatch policy.
        policy: DispatchPolicy,
    },
    /// At least one signal lacked enough evidence; precedence was not applied.
    Deferred {
        /// Exact deferred arbitration evidence.
        arbitration: Arbitration,
    },
    /// Ready disagreement was resolved by explicit caller precedence.
    Selected {
        /// Exact conflicting arbitration evidence retained unchanged.
        arbitration: Arbitration,
        /// Exact selected dispatch policy.
        policy: DispatchPolicy,
        /// Explicit caller precedence that selected the policy.
        precedence: NativeContinuationDispatchPolicyPrecedence,
    },
    /// Agreement-only precedence withheld ready disagreement.
    Withheld {
        /// Exact conflicting arbitration evidence retained unchanged.
        arbitration: Arbitration,
    },
}

impl NativeContinuationDispatchPolicyPrecedenceSelection {
    /// Returns policy authority when agreement or explicit precedence selected
    /// it.
    #[must_use]
    pub const fn policy(self) -> Option<DispatchPolicy> {
        match self {
            Self::Agreed { policy, .. } | Self::Selected { policy, .. } => {
                Some(policy)
            },
            Self::Deferred { .. } | Self::Withheld { .. } => None,
        }
    }
}

/// Applies explicit caller precedence without changing arbitration evidence.
#[must_use]
pub const fn select_native_continuation_dispatch_policy_precedence(
    arbitration: &Arbitration,
    precedence: NativeContinuationDispatchPolicyPrecedence,
) -> NativeContinuationDispatchPolicyPrecedenceSelection {
    let evidence = *arbitration;
    match evidence {
        Arbitration::Agreed { policy, .. } => {
            NativeContinuationDispatchPolicyPrecedenceSelection::Agreed {
                arbitration: evidence,
                policy,
            }
        },
        Arbitration::Conflict {
            count_policy,
            latency_policy,
            ..
        } => match precedence {
            NativeContinuationDispatchPolicyPrecedence::AgreementOnly => {
                NativeContinuationDispatchPolicyPrecedenceSelection::Withheld {
                    arbitration: evidence,
                }
            },
            NativeContinuationDispatchPolicyPrecedence::Count => {
                NativeContinuationDispatchPolicyPrecedenceSelection::Selected {
                    arbitration: evidence,
                    policy: count_policy,
                    precedence,
                }
            },
            NativeContinuationDispatchPolicyPrecedence::Latency => {
                NativeContinuationDispatchPolicyPrecedenceSelection::Selected {
                    arbitration: evidence,
                    policy: latency_policy,
                    precedence,
                }
            },
        },
        Arbitration::Deferred { .. } => {
            NativeContinuationDispatchPolicyPrecedenceSelection::Deferred {
                arbitration: evidence,
            }
        },
    }
}
