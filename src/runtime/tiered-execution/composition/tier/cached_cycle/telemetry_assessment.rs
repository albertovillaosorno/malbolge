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
//   - Pure caller-configured assessment of exact cached-retry telemetry.
// - Must-Not:
//   - Change retry limits, infer latency, persist evidence, or select a tier.
// - Allows:
//   - Inputs: one exact telemetry summary and explicit count thresholds.
//   - Outputs: insufficient, meeting, or multi-signal miss evidence.
//   - Side effects: none.
// - Split-When:
//   - Automatic recommendations or adaptive policy gain authority.
// - Merge-When:
//   - Caller orchestration owns assessment and policy publication atomically.
// - Summary:
//   - Classifies exact telemetry against caller-owned count thresholds.
// - Description:
//   - Attempt count gates assessment; all remaining misses are retained.
// - Usage:
//   - Assess one cycle summary or one bounded-window aggregate.
// - Defaults:
//   - Inclusive minimums and maximums meet their thresholds exactly.
//

//! Caller-configured exact cached-retry telemetry assessment.

use std::num::NonZeroUsize;

use super::NativeContinuationCachedRetryTelemetry;

/// Exact result of one caller-configured telemetry assessment.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryTelemetryAssessment {
    /// The attempt gate was not reached, so no quality claim was made.
    Insufficient {
        /// Attempts represented by the supplied telemetry.
        observed_attempts: usize,
        /// Positive caller-required attempt count.
        required_attempts: NonZeroUsize,
    },
    /// Every configured minimum and maximum was met inclusively.
    Meets {
        /// Exact telemetry that met the thresholds.
        telemetry: NativeContinuationCachedRetryTelemetry,
    },
    /// The attempt gate was met and one or more exact signals missed.
    Misses {
        /// Exact telemetry that missed the thresholds.
        telemetry: NativeContinuationCachedRetryTelemetry,
        /// Every simultaneously missed configured signal.
        violations: NativeContinuationCachedRetryTelemetryAssessmentViolations,
    },
}

/// Inclusive maximum count thresholds for ready telemetry.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryTelemetryAssessmentMaximums {
    evicted_keys: usize,
    insertions: usize,
    retired_keys: usize,
}

/// Inclusive minimum count thresholds plus the positive evidence gate.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryTelemetryAssessmentMinimums {
    attempts: NonZeroUsize,
    completed_steps: usize,
    hits: usize,
}

/// One exact ready-telemetry signal with a configured threshold.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryTelemetryAssessmentSignal {
    /// Committed native steps.
    CompletedSteps,
    /// Active keys evicted by insertions.
    EvictedKeys,
    /// Active-cache hits.
    Hits,
    /// Cache insertions.
    Insertions,
    /// Evicted keys retained behind external leases.
    RetiredKeys,
}

/// Complete explicit threshold set for one pure telemetry assessment.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryTelemetryAssessmentThresholds {
    maximums: NativeContinuationCachedRetryTelemetryAssessmentMaximums,
    minimums: NativeContinuationCachedRetryTelemetryAssessmentMinimums,
}

/// Every ready-telemetry signal that missed its configured threshold.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryTelemetryAssessmentViolations {
    bits: u8,
}

impl NativeContinuationCachedRetryTelemetryAssessmentMaximums {
    /// Returns the inclusive maximum active-key eviction count.
    #[must_use]
    pub const fn evicted_keys(self) -> usize {
        self.evicted_keys
    }

    /// Returns the inclusive maximum insertion count.
    #[must_use]
    pub const fn insertions(self) -> usize {
        self.insertions
    }

    /// Constructs inclusive maximum count thresholds.
    #[must_use]
    pub const fn new(
        evicted_keys: usize,
        insertions: usize,
        retired_keys: usize,
    ) -> Self {
        Self {
            evicted_keys,
            insertions,
            retired_keys,
        }
    }

    /// Returns the inclusive maximum retired-key count.
    #[must_use]
    pub const fn retired_keys(self) -> usize {
        self.retired_keys
    }
}

impl NativeContinuationCachedRetryTelemetryAssessmentMinimums {
    /// Returns the positive attempt gate required before assessment.
    #[must_use]
    pub const fn attempts(self) -> NonZeroUsize {
        self.attempts
    }

    /// Returns the inclusive minimum committed native-step count.
    #[must_use]
    pub const fn completed_steps(self) -> usize {
        self.completed_steps
    }

    /// Returns the inclusive minimum cache-hit count.
    #[must_use]
    pub const fn hits(self) -> usize {
        self.hits
    }

    /// Constructs inclusive minimum count thresholds and evidence gate.
    #[must_use]
    pub const fn new(
        attempts: NonZeroUsize,
        completed_steps: usize,
        hits: usize,
    ) -> Self {
        Self {
            attempts,
            completed_steps,
            hits,
        }
    }
}

impl NativeContinuationCachedRetryTelemetryAssessmentThresholds {
    /// Returns inclusive maximum count thresholds.
    #[must_use]
    pub const fn maximums(
        self,
    ) -> NativeContinuationCachedRetryTelemetryAssessmentMaximums {
        self.maximums
    }

    /// Returns inclusive minimum count thresholds and evidence gate.
    #[must_use]
    pub const fn minimums(
        self,
    ) -> NativeContinuationCachedRetryTelemetryAssessmentMinimums {
        self.minimums
    }

    /// Constructs one complete caller-owned threshold set.
    #[must_use]
    pub const fn new(
        maximums: NativeContinuationCachedRetryTelemetryAssessmentMaximums,
        minimums: NativeContinuationCachedRetryTelemetryAssessmentMinimums,
    ) -> Self {
        Self { maximums, minimums }
    }
}

impl NativeContinuationCachedRetryTelemetryAssessmentSignal {
    const fn mask(self) -> u8 {
        match self {
            Self::CompletedSteps => 1,
            Self::EvictedKeys => 2,
            Self::Hits => 4,
            Self::Insertions => 8,
            Self::RetiredKeys => 16,
        }
    }
}

impl NativeContinuationCachedRetryTelemetryAssessmentViolations {
    /// Reports whether one exact signal missed its configured threshold.
    #[must_use]
    pub const fn contains(
        self,
        signal: NativeContinuationCachedRetryTelemetryAssessmentSignal,
    ) -> bool {
        self.bits & signal.mask() != 0
    }

    /// Reports whether every ready-telemetry threshold was met.
    #[must_use]
    pub const fn is_empty(self) -> bool {
        self.bits == 0
    }
}

/// Assesses one exact summary without selecting or changing retry policy.
#[must_use]
pub const fn assess_cached_retry_telemetry(
    telemetry: NativeContinuationCachedRetryTelemetry,
    thresholds: NativeContinuationCachedRetryTelemetryAssessmentThresholds,
) -> NativeContinuationCachedRetryTelemetryAssessment {
    let minimums = thresholds.minimums();
    if telemetry.attempts() < minimums.attempts().get() {
        return NativeContinuationCachedRetryTelemetryAssessment::Insufficient {
            observed_attempts: telemetry.attempts(),
            required_attempts: minimums.attempts(),
        };
    }
    let maximums = thresholds.maximums();
    let mut bits = 0;
    if telemetry.completed_steps() < minimums.completed_steps() {
        bits |= NativeContinuationCachedRetryTelemetryAssessmentSignal::
            CompletedSteps
            .mask();
    }
    if telemetry.evicted_keys() > maximums.evicted_keys() {
        bits |=
            NativeContinuationCachedRetryTelemetryAssessmentSignal::EvictedKeys
                .mask();
    }
    if telemetry.hits() < minimums.hits() {
        bits |=
            NativeContinuationCachedRetryTelemetryAssessmentSignal::Hits.mask();
    }
    if telemetry.insertions() > maximums.insertions() {
        bits |=
            NativeContinuationCachedRetryTelemetryAssessmentSignal::Insertions
                .mask();
    }
    if telemetry.retired_keys() > maximums.retired_keys() {
        bits |=
            NativeContinuationCachedRetryTelemetryAssessmentSignal::RetiredKeys
                .mask();
    }
    let violations =
        NativeContinuationCachedRetryTelemetryAssessmentViolations { bits };
    if violations.is_empty() {
        NativeContinuationCachedRetryTelemetryAssessment::Meets { telemetry }
    } else {
        NativeContinuationCachedRetryTelemetryAssessment::Misses {
            telemetry,
            violations,
        }
    }
}
