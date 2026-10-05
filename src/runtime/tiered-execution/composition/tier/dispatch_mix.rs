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
//   - Pure latency-driven dispatch adaptation and conservative count-plus-
//     latency adaptation arbitration.
// - Must-Not:
//   - Assess telemetry, infer thresholds, assign signal precedence, publish
//     policy, execute dispatch, persist state, or mutate evidence.
// - Allows:
//   - Inputs: one validated latency assessment plus explicit policy table, or
//     one count adaptation plus one latency adaptation.
//   - Outputs: deferred/ready latency adaptation and deferred/agreed/conflict
//     arbitration evidence.
//   - Side effects: none.
// - Split-When:
//   - Additional evidence classes or caller-selected precedence gains
//     authority.
// - Merge-When:
//   - Product orchestration owns assessment through policy publication
//     atomically.
// - Summary:
//   - Adds latency policy selection and agreement-only multi-signal authority.
// - Description:
//   - Both ready signals must select one identical dispatch policy to
//     authorize.
// - Usage:
//   - Adapt independently assessed count and latency evidence, then arbitrate.
// - Defaults:
//   - No signal has implicit precedence and disagreement yields no policy.
//

//! Conservative count-plus-latency dispatch-policy adaptation arbitration.

use std::num::NonZeroUsize;

use crate::cached_cycle::{
    NativeContinuationCachedRetryLatencyAssessment,
    NativeContinuationCachedRetryLatencyAssessmentEvidence,
    NativeContinuationCachedRetryLatencyAssessmentViolations,
};
use crate::{
    continuation_dispatch_policy as dispatch_policy,
    continuation_dispatch_policy_adaptation as count_adaptation,
};

type CountAdaptation =
    count_adaptation::NativeContinuationDispatchPolicyAdaptation;
type DispatchPolicy = dispatch_policy::NativeContinuationDispatchPolicy;
type PolicySet =
    count_adaptation::NativeContinuationDispatchPolicyAdaptationSet;

/// Exact result of one latency-driven dispatch-policy adaptation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyLatencyAdaptation {
    /// Positive latency sample gate was not reached, so adaptation deferred.
    Deferred {
        /// Samples represented by the supplied assessment.
        observed_samples: usize,
        /// Positive caller-required sample count.
        required_samples: NonZeroUsize,
    },
    /// Ready latency met thresholds and selected the configured policy.
    Meets {
        /// Exact ready latency evidence that met configured thresholds.
        evidence: NativeContinuationCachedRetryLatencyAssessmentEvidence,
        /// Exact caller-configured dispatch policy.
        policy: DispatchPolicy,
    },
    /// Ready latency missed thresholds and selected the configured policy.
    Misses {
        /// Exact ready latency evidence that missed configured thresholds.
        evidence: NativeContinuationCachedRetryLatencyAssessmentEvidence,
        /// Exact caller-configured dispatch policy.
        policy: DispatchPolicy,
        /// Every simultaneously missed configured latency signal.
        violations: NativeContinuationCachedRetryLatencyAssessmentViolations,
    },
}

/// Exact conservative arbitration of count and latency dispatch adaptations.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyAdaptationArbitration {
    /// Both ready adaptations selected the identical dispatch policy.
    Agreed {
        /// Exact count adaptation participating in agreement.
        count: CountAdaptation,
        /// Exact latency adaptation participating in agreement.
        latency: NativeContinuationDispatchPolicyLatencyAdaptation,
        /// Exact policy independently selected by both evidence classes.
        policy: DispatchPolicy,
    },
    /// Both adaptations were ready but selected different dispatch policies.
    Conflict {
        /// Exact ready count adaptation.
        count: CountAdaptation,
        /// Policy selected by count evidence.
        count_policy: DispatchPolicy,
        /// Exact ready latency adaptation.
        latency: NativeContinuationDispatchPolicyLatencyAdaptation,
        /// Policy selected by latency evidence.
        latency_policy: DispatchPolicy,
    },
    /// At least one evidence class lacked sufficient evidence to select policy.
    Deferred {
        /// Exact count adaptation, ready or deferred.
        count: CountAdaptation,
        /// Exact latency adaptation, ready or deferred.
        latency: NativeContinuationDispatchPolicyLatencyAdaptation,
    },
}

impl NativeContinuationDispatchPolicyAdaptationArbitration {
    /// Returns policy authority only when both ready adaptations exactly agree.
    #[must_use]
    pub const fn policy(self) -> Option<DispatchPolicy> {
        match self {
            Self::Agreed { policy, .. } => Some(policy),
            Self::Conflict { .. } | Self::Deferred { .. } => None,
        }
    }
}

impl NativeContinuationDispatchPolicyLatencyAdaptation {
    /// Returns the exact selected dispatch policy once evidence is sufficient.
    #[must_use]
    pub const fn policy(self) -> Option<DispatchPolicy> {
        match self {
            Self::Deferred { .. } => None,
            Self::Meets { policy, .. } | Self::Misses { policy, .. } => {
                Some(policy)
            },
        }
    }
}

/// Maps one validated latency assessment to caller-configured dispatch policy.
#[must_use]
pub const fn adapt_native_continuation_dispatch_policy_from_latency(
    assessment: NativeContinuationCachedRetryLatencyAssessment,
    policies: PolicySet,
) -> NativeContinuationDispatchPolicyLatencyAdaptation {
    match assessment {
        NativeContinuationCachedRetryLatencyAssessment::Insufficient {
            observed_samples,
            required_samples,
        } => NativeContinuationDispatchPolicyLatencyAdaptation::Deferred {
            observed_samples,
            required_samples,
        },
        NativeContinuationCachedRetryLatencyAssessment::Meets { evidence } => {
            NativeContinuationDispatchPolicyLatencyAdaptation::Meets {
                evidence,
                policy: policies.meets(),
            }
        },
        NativeContinuationCachedRetryLatencyAssessment::Misses {
            evidence,
            violations,
        } => NativeContinuationDispatchPolicyLatencyAdaptation::Misses {
            evidence,
            policy: policies.misses(),
            violations,
        },
    }
}

/// Arbitrates independently adapted count and latency evidence without
/// precedence.
#[must_use]
pub fn arbitrate_native_continuation_dispatch_policy_adaptations(
    count: CountAdaptation,
    latency: NativeContinuationDispatchPolicyLatencyAdaptation,
) -> NativeContinuationDispatchPolicyAdaptationArbitration {
    match (count.policy(), latency.policy()) {
        (Some(count_policy), Some(latency_policy))
            if count_policy == latency_policy =>
        {
            NativeContinuationDispatchPolicyAdaptationArbitration::Agreed {
                count,
                latency,
                policy: count_policy,
            }
        },
        (Some(count_policy), Some(latency_policy)) => {
            NativeContinuationDispatchPolicyAdaptationArbitration::Conflict {
                count,
                count_policy,
                latency,
                latency_policy,
            }
        },
        (None, _) | (_, None) => {
            NativeContinuationDispatchPolicyAdaptationArbitration::Deferred {
                count,
                latency,
            }
        },
    }
}
