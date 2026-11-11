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
//   - Pure dispatch-policy selection from one exact cached-retry telemetry
//     assessment and caller-supplied policy table.
// - Must-Not:
//   - Assess telemetry, infer thresholds or policy values, publish active
//     state, execute dispatch, persist policy, or mutate telemetry.
// - Allows:
//   - Inputs: one validated assessment plus explicit meets/misses policies.
//   - Outputs: deferred evidence or one exact selected dispatch policy.
//   - Side effects: none.
// - Split-When:
//   - Additional evidence classes, adaptive precedence, or automatic active
//     policy publication gains authority.
// - Merge-When:
//   - Product orchestration owns assessment, selection, and publication
//     atomically.
// - Summary:
//   - Maps exact cached-retry assessment to caller-configured dispatch policy.
// - Description:
//   - Insufficient evidence defers; ready evidence never invents policy values.
// - Usage:
//   - Assess cached-retry telemetry first, then request one dispatch selection.
// - Defaults:
//   - No dispatch policy is selected before the positive attempt gate is met.
//

//! Pure dispatch-policy selection from validated cached-retry telemetry
//! evidence.

use std::num::NonZeroUsize;

use crate::cached_cycle::{
    NativeContinuationCachedRetryTelemetry,
    NativeContinuationCachedRetryTelemetryAssessment,
    NativeContinuationCachedRetryTelemetryAssessmentViolations,
};
use crate::continuation_dispatch_policy::NativeContinuationDispatchPolicy;

/// Caller-owned dispatch policies eligible for one telemetry-based selection.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationDispatchPolicyAdaptationSet {
    meets: NativeContinuationDispatchPolicy,
    misses: NativeContinuationDispatchPolicy,
}

/// Exact result of one cached-retry-evidence dispatch-policy selection.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyAdaptation {
    /// The positive evidence gate was not reached, so selection deferred.
    Deferred {
        /// Attempts represented by the supplied assessment.
        observed_attempts: usize,
        /// Positive caller-required attempt count.
        required_attempts: NonZeroUsize,
    },
    /// Ready telemetry met every threshold and selected the configured policy.
    Meets {
        /// Exact dispatch policy selected by caller configuration.
        policy: NativeContinuationDispatchPolicy,
        /// Exact telemetry that met configured thresholds.
        telemetry: NativeContinuationCachedRetryTelemetry,
    },
    /// Ready telemetry missed thresholds and selected the configured policy.
    Misses {
        /// Exact dispatch policy selected by caller configuration.
        policy: NativeContinuationDispatchPolicy,
        /// Exact telemetry that missed configured thresholds.
        telemetry: NativeContinuationCachedRetryTelemetry,
        /// Every simultaneously missed configured signal.
        violations: NativeContinuationCachedRetryTelemetryAssessmentViolations,
    },
}

impl NativeContinuationDispatchPolicyAdaptation {
    /// Returns the exact selected dispatch policy once evidence is sufficient.
    #[must_use]
    pub const fn policy(self) -> Option<NativeContinuationDispatchPolicy> {
        match self {
            Self::Deferred { .. } => None,
            Self::Meets { policy, .. } | Self::Misses { policy, .. } => {
                Some(policy)
            },
        }
    }
}

impl NativeContinuationDispatchPolicyAdaptationSet {
    /// Returns the policy configured for threshold-meeting evidence.
    #[must_use]
    pub const fn meets(self) -> NativeContinuationDispatchPolicy {
        self.meets
    }

    /// Returns the policy configured for threshold-missing evidence.
    #[must_use]
    pub const fn misses(self) -> NativeContinuationDispatchPolicy {
        self.misses
    }

    /// Constructs one explicit adaptive selection table.
    #[must_use]
    pub const fn new(
        meets: NativeContinuationDispatchPolicy,
        misses: NativeContinuationDispatchPolicy,
    ) -> Self {
        Self { meets, misses }
    }
}

/// Selects one caller-supplied dispatch policy without publishing or executing.
#[must_use]
pub const fn adapt_native_continuation_dispatch_policy(
    assessment: NativeContinuationCachedRetryTelemetryAssessment,
    policies: NativeContinuationDispatchPolicyAdaptationSet,
) -> NativeContinuationDispatchPolicyAdaptation {
    match assessment {
        NativeContinuationCachedRetryTelemetryAssessment::Insufficient {
            observed_attempts,
            required_attempts,
        } => NativeContinuationDispatchPolicyAdaptation::Deferred {
            observed_attempts,
            required_attempts,
        },
        NativeContinuationCachedRetryTelemetryAssessment::Meets {
            telemetry,
        } => NativeContinuationDispatchPolicyAdaptation::Meets {
            policy: policies.meets(),
            telemetry,
        },
        NativeContinuationCachedRetryTelemetryAssessment::Misses {
            telemetry,
            violations,
        } => NativeContinuationDispatchPolicyAdaptation::Misses {
            policy: policies.misses(),
            telemetry,
            violations,
        },
    }
}
