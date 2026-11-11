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
//   - Pure latency/productivity/cache-reuse adaptation plus conservative count,
//     latency, productivity, and reuse agreement-only arbitration.
// - Must-Not:
//   - Assess telemetry, infer thresholds, assign signal precedence, publish
//     policy, execute dispatch, persist state, or mutate evidence.
// - Allows:
//   - Inputs: validated latency or exact productivity/reuse evidence plus
//     explicit policy table and existing lower-order arbitration evidence.
//   - Outputs: deferred/ready adaptations and exact multi-signal
//     deferred/agreed/conflict evidence.
//   - Side effects: none.
// - Split-When:
//   - Evidence beyond cache reuse, weighted arbitration, or new signal-specific
//     precedence gains authority.
// - Merge-When:
//   - Product orchestration owns assessment through policy publication
//     atomically.
// - Summary:
//   - Adds normalized latency/productivity/reuse evidence and conservative
//     multi-signal authority.
// - Description:
//   - Every ready signal in an arbitration must select one identical policy.
// - Usage:
//   - Adapt count/latency first, then optionally require productivity and cache
//     reuse agreement.
// - Defaults:
//   - No signal has implicit precedence and disagreement yields no policy.
//

//! Conservative count/latency/productivity/reuse dispatch-policy arbitration.

use std::num::{NonZeroU64, NonZeroU128, NonZeroUsize};

use crate::cached_cycle::{
    NativeContinuationCachedRetryLatencyAssessment,
    NativeContinuationCachedRetryLatencyAssessmentEvidence,
    NativeContinuationCachedRetryLatencyAssessmentViolations,
    NativeContinuationCachedRetryTelemetry,
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

/// Caller-owned cache-reuse threshold for one telemetry cohort.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationDispatchPolicyCacheReuseThreshold {
    minimum_hits_denominator: NonZeroU64,
    minimum_hits_numerator: NonZeroU64,
    required_attempts: NonZeroUsize,
}

/// Why ready cache-reuse evidence selected the misses policy.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyCacheReuseMiss {
    /// Exact rational comparison overflowed `u128` and failed closed.
    ArithmeticOverflow,
    /// Active-cache hits per attempt missed the caller minimum.
    BelowMinimumHitsPerAttempt,
}

/// Exact cache-reuse dispatch-policy adaptation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyCacheReuseAdaptation {
    /// Positive attempt gate was not reached, so adaptation deferred.
    Deferred {
        /// Attempts represented by the supplied telemetry.
        observed_attempts: usize,
        /// Positive caller-required attempt count.
        required_attempts: NonZeroUsize,
    },
    /// Ready reuse met the exact caller ratio.
    Meets {
        /// Exact caller-configured dispatch policy.
        policy: DispatchPolicy,
        /// Exact telemetry whose reuse met the minimum.
        telemetry: NativeContinuationCachedRetryTelemetry,
    },
    /// Ready reuse failed to prove the exact caller ratio.
    Misses {
        /// Stable reason reuse did not authorize the meets policy.
        reason: NativeContinuationDispatchPolicyCacheReuseMiss,
        /// Exact caller-configured dispatch policy.
        policy: DispatchPolicy,
        /// Exact telemetry whose reuse failed closed.
        telemetry: NativeContinuationCachedRetryTelemetry,
    },
}

/// Caller-owned semantic-productivity threshold for one telemetry cohort.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationDispatchPolicyProductivityThreshold {
    minimum_steps_denominator: NonZeroU64,
    minimum_steps_numerator: NonZeroU64,
    required_attempts: NonZeroUsize,
}

/// Why ready semantic-productivity evidence selected the misses policy.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyProductivityMiss {
    /// Exact rational comparison overflowed `u128` and failed closed.
    ArithmeticOverflow,
    /// Committed semantic steps per attempt missed the caller minimum.
    BelowMinimumStepsPerAttempt,
}

/// Exact semantic-productivity dispatch-policy adaptation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyProductivityAdaptation {
    /// Positive attempt gate was not reached, so adaptation deferred.
    Deferred {
        /// Attempts represented by the supplied telemetry.
        observed_attempts: usize,
        /// Positive caller-required attempt count.
        required_attempts: NonZeroUsize,
    },
    /// Ready productivity met the exact caller ratio.
    Meets {
        /// Exact caller-configured dispatch policy.
        policy: DispatchPolicy,
        /// Exact telemetry whose productivity met the minimum.
        telemetry: NativeContinuationCachedRetryTelemetry,
    },
    /// Ready productivity failed to prove the exact caller ratio.
    Misses {
        /// Stable reason productivity did not authorize the meets policy.
        reason: NativeContinuationDispatchPolicyProductivityMiss,
        /// Exact caller-configured dispatch policy.
        policy: DispatchPolicy,
        /// Exact telemetry whose productivity failed closed.
        telemetry: NativeContinuationCachedRetryTelemetry,
    },
}

/// Agreement-only authority across count, latency, and productivity signals.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyThreeSignalArbitration {
    /// All three ready evidence classes selected the identical policy.
    Agreed {
        /// Existing exact count-plus-latency arbitration.
        mixed: NativeContinuationDispatchPolicyAdaptationArbitration,
        /// Exact productivity adaptation participating in agreement.
        productivity: NativeContinuationDispatchPolicyProductivityAdaptation,
        /// Exact policy selected independently by every ready signal.
        policy: DispatchPolicy,
    },
    /// Every signal was ready but at least two selected different policies.
    Conflict {
        /// Existing exact count-plus-latency arbitration.
        mixed: NativeContinuationDispatchPolicyAdaptationArbitration,
        /// Exact ready productivity adaptation.
        productivity: NativeContinuationDispatchPolicyProductivityAdaptation,
    },
    /// At least one evidence class lacked sufficient evidence.
    Deferred {
        /// Existing exact count-plus-latency arbitration.
        mixed: NativeContinuationDispatchPolicyAdaptationArbitration,
        /// Exact productivity adaptation, ready or deferred.
        productivity: NativeContinuationDispatchPolicyProductivityAdaptation,
    },
}

/// Agreement-only authority across count, latency, productivity, and reuse.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyFourSignalArbitration {
    /// All four ready evidence classes selected the identical policy.
    Agreed {
        /// Existing exact three-signal arbitration.
        three_signal: NativeContinuationDispatchPolicyThreeSignalArbitration,
        /// Exact cache-reuse adaptation participating in agreement.
        cache_reuse: NativeContinuationDispatchPolicyCacheReuseAdaptation,
        /// Exact policy selected independently by every ready signal.
        policy: DispatchPolicy,
    },
    /// Ready lower-order evidence or cache reuse disagreed.
    Conflict {
        /// Existing exact three-signal arbitration.
        three_signal: NativeContinuationDispatchPolicyThreeSignalArbitration,
        /// Exact cache-reuse adaptation, ready or deferred.
        cache_reuse: NativeContinuationDispatchPolicyCacheReuseAdaptation,
    },
    /// Lower-order evidence or cache reuse lacked sufficient evidence.
    Deferred {
        /// Existing exact three-signal arbitration.
        three_signal: NativeContinuationDispatchPolicyThreeSignalArbitration,
        /// Exact cache-reuse adaptation, ready or deferred.
        cache_reuse: NativeContinuationDispatchPolicyCacheReuseAdaptation,
    },
}

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

impl NativeContinuationDispatchPolicyCacheReuseAdaptation {
    /// Returns the exact selected policy once cache-reuse evidence is ready.
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

impl NativeContinuationDispatchPolicyCacheReuseThreshold {
    /// Returns the exact minimum hits-per-attempt denominator.
    #[must_use]
    pub const fn minimum_hits_denominator(self) -> NonZeroU64 {
        self.minimum_hits_denominator
    }

    /// Returns the exact minimum hits-per-attempt numerator.
    #[must_use]
    pub const fn minimum_hits_numerator(self) -> NonZeroU64 {
        self.minimum_hits_numerator
    }

    /// Constructs one exact positive cache-reuse threshold.
    #[must_use]
    pub const fn new(
        required_attempts: NonZeroUsize,
        minimum_hits_numerator: NonZeroU64,
        minimum_hits_denominator: NonZeroU64,
    ) -> Self {
        Self {
            minimum_hits_denominator,
            minimum_hits_numerator,
            required_attempts,
        }
    }

    /// Returns the positive attempt gate for cache-reuse assessment.
    #[must_use]
    pub const fn required_attempts(self) -> NonZeroUsize {
        self.required_attempts
    }
}

impl NativeContinuationDispatchPolicyFourSignalArbitration {
    /// Returns policy authority only when all four ready signals agree.
    #[must_use]
    pub const fn policy(self) -> Option<DispatchPolicy> {
        match self {
            Self::Agreed { policy, .. } => Some(policy),
            Self::Conflict { .. } | Self::Deferred { .. } => None,
        }
    }
}

impl NativeContinuationDispatchPolicyProductivityAdaptation {
    /// Returns the exact selected policy once productivity evidence is ready.
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

impl NativeContinuationDispatchPolicyProductivityThreshold {
    /// Returns the exact minimum steps-per-attempt denominator.
    #[must_use]
    pub const fn minimum_steps_denominator(self) -> NonZeroU64 {
        self.minimum_steps_denominator
    }

    /// Returns the exact minimum steps-per-attempt numerator.
    #[must_use]
    pub const fn minimum_steps_numerator(self) -> NonZeroU64 {
        self.minimum_steps_numerator
    }

    /// Constructs one exact positive semantic-productivity threshold.
    #[must_use]
    pub const fn new(
        required_attempts: NonZeroUsize,
        minimum_steps_numerator: NonZeroU64,
        minimum_steps_denominator: NonZeroU64,
    ) -> Self {
        Self {
            minimum_steps_denominator,
            minimum_steps_numerator,
            required_attempts,
        }
    }

    /// Returns the positive attempt gate for productivity assessment.
    #[must_use]
    pub const fn required_attempts(self) -> NonZeroUsize {
        self.required_attempts
    }
}

impl NativeContinuationDispatchPolicyThreeSignalArbitration {
    /// Returns policy authority only when all three ready signals agree.
    #[must_use]
    pub const fn policy(self) -> Option<DispatchPolicy> {
        match self {
            Self::Agreed { policy, .. } => Some(policy),
            Self::Conflict { .. } | Self::Deferred { .. } => None,
        }
    }
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

/// Maps exact cache reuse to caller-configured dispatch policy.
#[must_use]
pub fn adapt_native_continuation_dispatch_policy_from_cache_reuse(
    telemetry: NativeContinuationCachedRetryTelemetry,
    threshold: NativeContinuationDispatchPolicyCacheReuseThreshold,
    policies: PolicySet,
) -> NativeContinuationDispatchPolicyCacheReuseAdaptation {
    use NativeContinuationDispatchPolicyCacheReuseAdaptation as Adaptation;
    use NativeContinuationDispatchPolicyCacheReuseMiss as Miss;

    if telemetry.attempts() < threshold.required_attempts.get() {
        return Adaptation::Deferred {
            observed_attempts: telemetry.attempts(),
            required_attempts: threshold.required_attempts,
        };
    }
    let Ok(hits) = u128::try_from(telemetry.hits()) else {
        return Adaptation::Misses {
            reason: Miss::ArithmeticOverflow,
            policy: policies.misses(),
            telemetry,
        };
    };
    let Ok(attempts) = u128::try_from(telemetry.attempts()) else {
        return Adaptation::Misses {
            reason: Miss::ArithmeticOverflow,
            policy: policies.misses(),
            telemetry,
        };
    };
    let Some(weighted_hits) = hits.checked_mul(
        NonZeroU128::from(threshold.minimum_hits_denominator).get(),
    ) else {
        return Adaptation::Misses {
            reason: Miss::ArithmeticOverflow,
            policy: policies.misses(),
            telemetry,
        };
    };
    let Some(required_hits) = attempts
        .checked_mul(NonZeroU128::from(threshold.minimum_hits_numerator).get())
    else {
        return Adaptation::Misses {
            reason: Miss::ArithmeticOverflow,
            policy: policies.misses(),
            telemetry,
        };
    };
    if weighted_hits >= required_hits {
        Adaptation::Meets {
            policy: policies.meets(),
            telemetry,
        }
    } else {
        Adaptation::Misses {
            reason: Miss::BelowMinimumHitsPerAttempt,
            policy: policies.misses(),
            telemetry,
        }
    }
}

/// Maps exact semantic productivity to caller-configured dispatch policy.
#[must_use]
pub fn adapt_native_continuation_dispatch_policy_from_productivity(
    telemetry: NativeContinuationCachedRetryTelemetry,
    threshold: NativeContinuationDispatchPolicyProductivityThreshold,
    policies: PolicySet,
) -> NativeContinuationDispatchPolicyProductivityAdaptation {
    if telemetry.attempts() < threshold.required_attempts.get() {
        return NativeContinuationDispatchPolicyProductivityAdaptation::
            Deferred {
                observed_attempts: telemetry.attempts(),
                required_attempts: threshold.required_attempts,
            };
    }
    let Ok(steps) = u128::try_from(telemetry.completed_steps()) else {
        return NativeContinuationDispatchPolicyProductivityAdaptation::Misses {
            reason: NativeContinuationDispatchPolicyProductivityMiss::
                ArithmeticOverflow,
            policy: policies.misses(),
            telemetry,
        };
    };
    let Ok(attempts) = u128::try_from(telemetry.attempts()) else {
        return NativeContinuationDispatchPolicyProductivityAdaptation::Misses {
            reason: NativeContinuationDispatchPolicyProductivityMiss::
                ArithmeticOverflow,
            policy: policies.misses(),
            telemetry,
        };
    };
    let Some(weighted_steps) = steps.checked_mul(
        NonZeroU128::from(threshold.minimum_steps_denominator).get(),
    ) else {
        return NativeContinuationDispatchPolicyProductivityAdaptation::Misses {
            reason: NativeContinuationDispatchPolicyProductivityMiss::
                ArithmeticOverflow,
            policy: policies.misses(),
            telemetry,
        };
    };
    let Some(required_steps) = attempts.checked_mul(
        NonZeroU128::from(threshold.minimum_steps_numerator).get(),
    ) else {
        return NativeContinuationDispatchPolicyProductivityAdaptation::Misses {
            reason: NativeContinuationDispatchPolicyProductivityMiss::
                ArithmeticOverflow,
            policy: policies.misses(),
            telemetry,
        };
    };
    if weighted_steps >= required_steps {
        NativeContinuationDispatchPolicyProductivityAdaptation::Meets {
            policy: policies.meets(),
            telemetry,
        }
    } else {
        NativeContinuationDispatchPolicyProductivityAdaptation::Misses {
            reason: NativeContinuationDispatchPolicyProductivityMiss::
                BelowMinimumStepsPerAttempt,
            policy: policies.misses(),
            telemetry,
        }
    }
}

/// Extends count-plus-latency arbitration with productivity agreement only.
#[must_use]
pub fn arbitrate_native_continuation_dispatch_policy_three_signals(
    mixed: &NativeContinuationDispatchPolicyAdaptationArbitration,
    productivity: NativeContinuationDispatchPolicyProductivityAdaptation,
) -> NativeContinuationDispatchPolicyThreeSignalArbitration {
    use NativeContinuationDispatchPolicyAdaptationArbitration as Mixed;
    use NativeContinuationDispatchPolicyThreeSignalArbitration as ThreeSignal;

    let mixed_evidence = *mixed;
    match mixed_evidence {
        Mixed::Conflict { .. } => ThreeSignal::Conflict {
            mixed: mixed_evidence,
            productivity,
        },
        Mixed::Deferred { .. } => ThreeSignal::Deferred {
            mixed: mixed_evidence,
            productivity,
        },
        Mixed::Agreed { policy: mixed_policy, .. } => {
            match productivity.policy() {
                None => ThreeSignal::Deferred {
                    mixed: mixed_evidence,
                    productivity,
                },
                Some(productivity_policy)
                    if productivity_policy == mixed_policy =>
                {
                    ThreeSignal::Agreed {
                        mixed: mixed_evidence,
                        productivity,
                        policy: mixed_policy,
                    }
                },
                Some(_) => ThreeSignal::Conflict {
                    mixed: mixed_evidence,
                    productivity,
                },
            }
        },
    }
}

/// Extends three-signal arbitration with cache-reuse agreement only.
#[must_use]
pub fn arbitrate_native_continuation_dispatch_policy_four_signals(
    three_signal: &NativeContinuationDispatchPolicyThreeSignalArbitration,
    cache_reuse: NativeContinuationDispatchPolicyCacheReuseAdaptation,
) -> NativeContinuationDispatchPolicyFourSignalArbitration {
    use NativeContinuationDispatchPolicyFourSignalArbitration as FourSignal;
    use NativeContinuationDispatchPolicyThreeSignalArbitration as ThreeSignal;

    let three_signal_evidence = *three_signal;
    match three_signal_evidence {
        ThreeSignal::Conflict { .. } => FourSignal::Conflict {
            three_signal: three_signal_evidence,
            cache_reuse,
        },
        ThreeSignal::Deferred { .. } => FourSignal::Deferred {
            three_signal: three_signal_evidence,
            cache_reuse,
        },
        ThreeSignal::Agreed {
            policy: agreed_policy, ..
        } => match cache_reuse.policy() {
            None => FourSignal::Deferred {
                three_signal: three_signal_evidence,
                cache_reuse,
            },
            Some(reuse_policy) if reuse_policy == agreed_policy => {
                FourSignal::Agreed {
                    three_signal: three_signal_evidence,
                    cache_reuse,
                    policy: agreed_policy,
                }
            },
            Some(_) => FourSignal::Conflict {
                three_signal: three_signal_evidence,
                cache_reuse,
            },
        },
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
