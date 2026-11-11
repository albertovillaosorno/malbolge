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
//   - Pure caller-selected precedence over completed two-, three-, and
//     four-signal dispatch-policy arbitration.
// - Must-Not:
//   - Assess telemetry, adapt signals, alter arbitration evidence, publish
//     policy, persist precedence, or invent additional evidence classes.
// - Allows:
//   - Inputs: one exact two-, three-, or four-signal arbitration and one
//     explicit precedence mode.
//   - Outputs: agreed, deferred, selected, unavailable, or withheld evidence.
//   - Side effects: none.
// - Split-When:
//   - Signals beyond cache reuse, weighted arbitration, or durable precedence
//     policy gains authority.
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

//! Caller-selected precedence over exact dispatch-policy arbitration evidence.

use crate::{
    continuation_dispatch_policy as dispatch_policy,
    continuation_dispatch_policy_mixed_evidence as mixed,
};

type Arbitration = mixed::NativeContinuationDispatchPolicyAdaptationArbitration;
type DispatchPolicy = dispatch_policy::NativeContinuationDispatchPolicy;
type ThreeSignalArbitration =
    mixed::NativeContinuationDispatchPolicyThreeSignalArbitration;
type ProductivityAdaptation =
    mixed::NativeContinuationDispatchPolicyProductivityAdaptation;
type CacheReuseAdaptation =
    mixed::NativeContinuationDispatchPolicyCacheReuseAdaptation;
type FourSignalArbitration =
    mixed::NativeContinuationDispatchPolicyFourSignalArbitration;

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

/// Explicit caller policy for resolving ready four-signal disagreement.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyFourSignalPrecedence {
    /// Preserve agreement-only authority and withhold ready disagreement.
    #[default]
    AgreementOnly,
    /// Select the cache-reuse policy when available.
    CacheReuse,
    /// Select the count-adaptation policy when available.
    Count,
    /// Select the latency-adaptation policy when available.
    Latency,
    /// Select the semantic-productivity policy when available.
    Productivity,
}

/// Exact result of applying caller precedence to four-signal arbitration.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyFourSignalPrecedenceSelection {
    /// Existing four-signal agreement already authorized this policy.
    Agreed {
        /// Exact arbitration evidence.
        arbitration: FourSignalArbitration,
        /// Exact agreed dispatch policy.
        policy: DispatchPolicy,
    },
    /// Four-signal arbitration lacked enough evidence; precedence did not run.
    Deferred {
        /// Exact deferred arbitration evidence.
        arbitration: FourSignalArbitration,
    },
    /// Ready disagreement was resolved by explicit caller precedence.
    Selected {
        /// Exact conflicting arbitration evidence retained unchanged.
        arbitration: FourSignalArbitration,
        /// Exact selected dispatch policy.
        policy: DispatchPolicy,
        /// Explicit caller precedence that selected the policy.
        precedence: NativeContinuationDispatchPolicyFourSignalPrecedence,
    },
    /// Selected signal had no ready policy in otherwise conflicting evidence.
    Unavailable {
        /// Exact conflicting arbitration evidence retained unchanged.
        arbitration: FourSignalArbitration,
        /// Explicit precedence whose selected signal was unavailable.
        precedence: NativeContinuationDispatchPolicyFourSignalPrecedence,
    },
    /// Agreement-only precedence withheld ready disagreement.
    Withheld {
        /// Exact conflicting arbitration evidence retained unchanged.
        arbitration: FourSignalArbitration,
    },
}

/// Explicit caller policy for resolving ready three-signal disagreement.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyThreeSignalPrecedence {
    /// Preserve agreement-only authority and withhold ready disagreement.
    #[default]
    AgreementOnly,
    /// Select the count-adaptation policy when available.
    Count,
    /// Select the latency-adaptation policy when available.
    Latency,
    /// Select the semantic-productivity policy when available.
    Productivity,
}

/// Exact result of applying caller precedence to three-signal arbitration.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyThreeSignalPrecedenceSelection {
    /// Existing three-signal agreement already authorized this policy.
    Agreed {
        /// Exact arbitration evidence.
        arbitration: ThreeSignalArbitration,
        /// Exact agreed dispatch policy.
        policy: DispatchPolicy,
    },
    /// Three-signal arbitration lacked enough evidence; precedence did not run.
    Deferred {
        /// Exact deferred arbitration evidence.
        arbitration: ThreeSignalArbitration,
    },
    /// Ready disagreement was resolved by explicit caller precedence.
    Selected {
        /// Exact conflicting arbitration evidence retained unchanged.
        arbitration: ThreeSignalArbitration,
        /// Exact selected dispatch policy.
        policy: DispatchPolicy,
        /// Explicit caller precedence that selected the policy.
        precedence: NativeContinuationDispatchPolicyThreeSignalPrecedence,
    },
    /// Selected signal had no ready policy in otherwise conflicting evidence.
    Unavailable {
        /// Exact conflicting arbitration evidence retained unchanged.
        arbitration: ThreeSignalArbitration,
        /// Explicit precedence whose selected signal was unavailable.
        precedence: NativeContinuationDispatchPolicyThreeSignalPrecedence,
    },
    /// Agreement-only precedence withheld ready disagreement.
    Withheld {
        /// Exact conflicting arbitration evidence retained unchanged.
        arbitration: ThreeSignalArbitration,
    },
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

impl NativeContinuationDispatchPolicyFourSignalPrecedenceSelection {
    /// Returns policy authority only for agreement or explicit ready selection.
    #[must_use]
    pub const fn policy(self) -> Option<DispatchPolicy> {
        match self {
            Self::Agreed { policy, .. } | Self::Selected { policy, .. } => {
                Some(policy)
            },
            Self::Deferred { .. }
            | Self::Unavailable { .. }
            | Self::Withheld { .. } => None,
        }
    }
}

impl NativeContinuationDispatchPolicyThreeSignalPrecedenceSelection {
    /// Returns policy authority only for agreement or explicit ready selection.
    #[must_use]
    pub const fn policy(self) -> Option<DispatchPolicy> {
        match self {
            Self::Agreed { policy, .. } | Self::Selected { policy, .. } => {
                Some(policy)
            },
            Self::Deferred { .. }
            | Self::Unavailable { .. }
            | Self::Withheld { .. } => None,
        }
    }
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

const fn count_policy_from_mixed(
    arbitration: &Arbitration,
) -> Option<DispatchPolicy> {
    match *arbitration {
        Arbitration::Agreed { policy, .. } => Some(policy),
        Arbitration::Conflict { count_policy, .. } => Some(count_policy),
        Arbitration::Deferred { .. } => None,
    }
}

const fn latency_policy_from_mixed(
    arbitration: &Arbitration,
) -> Option<DispatchPolicy> {
    match *arbitration {
        Arbitration::Agreed { policy, .. } => Some(policy),
        Arbitration::Conflict { latency_policy, .. } => Some(latency_policy),
        Arbitration::Deferred { .. } => None,
    }
}

const fn select_three_signal_conflict_policy(
    mixed: &Arbitration,
    productivity: ProductivityAdaptation,
    precedence: NativeContinuationDispatchPolicyThreeSignalPrecedence,
) -> Option<DispatchPolicy> {
    use NativeContinuationDispatchPolicyThreeSignalPrecedence as Precedence;

    match precedence {
        Precedence::AgreementOnly => None,
        Precedence::Count => count_policy_from_mixed(mixed),
        Precedence::Latency => latency_policy_from_mixed(mixed),
        Precedence::Productivity => productivity.policy(),
    }
}

/// Applies explicit caller precedence to exact three-signal arbitration.
#[must_use]
pub const fn select_native_continuation_dispatch_policy_three_signal_precedence(
    arbitration: &ThreeSignalArbitration,
    precedence: NativeContinuationDispatchPolicyThreeSignalPrecedence,
) -> NativeContinuationDispatchPolicyThreeSignalPrecedenceSelection {
    type Selection =
        NativeContinuationDispatchPolicyThreeSignalPrecedenceSelection;

    let evidence = *arbitration;
    match evidence {
        ThreeSignalArbitration::Agreed { policy, .. } => Selection::Agreed {
            arbitration: evidence,
            policy,
        },
        ThreeSignalArbitration::Deferred { .. } => Selection::Deferred {
            arbitration: evidence,
        },
        ThreeSignalArbitration::Conflict {
            mixed,
            productivity,
        } => match precedence {
            NativeContinuationDispatchPolicyThreeSignalPrecedence::
                AgreementOnly => Selection::Withheld {
                    arbitration: evidence,
                },
            NativeContinuationDispatchPolicyThreeSignalPrecedence::Count
            | NativeContinuationDispatchPolicyThreeSignalPrecedence::Latency
            | NativeContinuationDispatchPolicyThreeSignalPrecedence::
                Productivity => match select_three_signal_conflict_policy(
                    &mixed,
                    productivity,
                    precedence,
                ) {
                Some(policy) => Selection::Selected {
                    arbitration: evidence,
                    policy,
                    precedence,
                },
                None => Selection::Unavailable {
                    arbitration: evidence,
                    precedence,
                },
            },
        },
    }
}
const fn count_policy_from_three_signal(
    arbitration: &ThreeSignalArbitration,
) -> Option<DispatchPolicy> {
    match *arbitration {
        ThreeSignalArbitration::Agreed { policy, .. } => Some(policy),
        ThreeSignalArbitration::Conflict { mixed, .. } => {
            count_policy_from_mixed(&mixed)
        },
        ThreeSignalArbitration::Deferred { .. } => None,
    }
}

const fn latency_policy_from_three_signal(
    arbitration: &ThreeSignalArbitration,
) -> Option<DispatchPolicy> {
    match *arbitration {
        ThreeSignalArbitration::Agreed { policy, .. } => Some(policy),
        ThreeSignalArbitration::Conflict { mixed, .. } => {
            latency_policy_from_mixed(&mixed)
        },
        ThreeSignalArbitration::Deferred { .. } => None,
    }
}

const fn productivity_policy_from_three_signal(
    arbitration: &ThreeSignalArbitration,
) -> Option<DispatchPolicy> {
    match *arbitration {
        ThreeSignalArbitration::Agreed { policy, .. } => Some(policy),
        ThreeSignalArbitration::Conflict { productivity, .. } => {
            productivity.policy()
        },
        ThreeSignalArbitration::Deferred { .. } => None,
    }
}

const fn select_four_signal_conflict_policy(
    three_signal: &ThreeSignalArbitration,
    cache_reuse: CacheReuseAdaptation,
    precedence: NativeContinuationDispatchPolicyFourSignalPrecedence,
) -> Option<DispatchPolicy> {
    use NativeContinuationDispatchPolicyFourSignalPrecedence as Precedence;

    match precedence {
        Precedence::AgreementOnly => None,
        Precedence::Count => count_policy_from_three_signal(three_signal),
        Precedence::Latency => latency_policy_from_three_signal(three_signal),
        Precedence::Productivity => {
            productivity_policy_from_three_signal(three_signal)
        },
        Precedence::CacheReuse => cache_reuse.policy(),
    }
}

/// Applies explicit caller precedence to exact four-signal arbitration.
#[must_use]
pub const fn select_native_continuation_dispatch_policy_four_signal_precedence(
    arbitration: &FourSignalArbitration,
    precedence: NativeContinuationDispatchPolicyFourSignalPrecedence,
) -> NativeContinuationDispatchPolicyFourSignalPrecedenceSelection {
    type Selection =
        NativeContinuationDispatchPolicyFourSignalPrecedenceSelection;

    use NativeContinuationDispatchPolicyFourSignalPrecedence as FourPrecedence;

    let evidence = *arbitration;
    match evidence {
        FourSignalArbitration::Agreed { policy, .. } => Selection::Agreed {
            arbitration: evidence,
            policy,
        },
        FourSignalArbitration::Deferred { .. } => {
            Selection::Deferred { arbitration: evidence }
        },
        FourSignalArbitration::Conflict {
            three_signal,
            cache_reuse,
        } => match precedence {
            FourPrecedence::AgreementOnly => {
                Selection::Withheld { arbitration: evidence }
            },
            FourPrecedence::Count
            | FourPrecedence::Latency
            | FourPrecedence::Productivity
            | FourPrecedence::CacheReuse => {
                match select_four_signal_conflict_policy(
                    &three_signal,
                    cache_reuse,
                    precedence,
                ) {
                    Some(policy) => Selection::Selected {
                        arbitration: evidence,
                        policy,
                        precedence,
                    },
                    None => Selection::Unavailable {
                        arbitration: evidence,
                        precedence,
                    },
                }
            },
        },
    }
}
