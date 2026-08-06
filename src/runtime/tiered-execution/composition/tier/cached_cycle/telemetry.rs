// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Pure deterministic aggregation of cached native retry attempt evidence.
// - Must-Not:
//   - Select policy, mutate cache state, infer missing attempts, or hide
//     overflow.
// - Allows:
//   - Inputs: an ordered slice of completed cached retry attempts.
//   - Outputs: exact counters or the attempt whose accumulation overflowed.
//   - Side effects: none.
// - Split-When:
//   - Histograms, latency, or adaptive decisions gain independent ownership.
// - Merge-When:
//   - Cached-cycle policy consumes telemetry atomically during execution.
// - Summary:
//   - Summarizes cache reuse and semantic progress without changing policy.
// - Description:
//   - Counts hits, insertions, removals, retirements, and committed native
//     steps.
// - Usage:
//   - Summarize any completion, fallback, or retained prior-attempt slice.
// - Defaults:
//   - Arithmetic overflow fails closed with the exact one-based attempt number.
//

//! Pure telemetry summaries for cached native retry attempt evidence.

use std::fmt::{Display, Formatter, Result as FormatResult};

use super::{
    NativeContinuationCachedRetryAttempt,
    NativeContinuationCachedRetryCompletion,
    NativeContinuationCachedRetryInterpreterFailure,
    NativeContinuationCachedRetryInterpreterOutcome,
};

/// Exact cache and semantic counters for one ordered attempt slice.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryTelemetry {
    attempts: usize,
    completed_steps: usize,
    evicted_keys: usize,
    hits: usize,
    insertions: usize,
    retired_keys: usize,
}

/// Why exact cached-retry telemetry aggregation failed closed.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryTelemetryError {
    /// Committed native-step accumulation exceeded host indexing.
    CompletedSteps {
        /// One-based native attempt whose contribution overflowed.
        attempt: usize,
    },
    /// Evicted-key accumulation exceeded host indexing.
    EvictedKeys {
        /// One-based native attempt whose contribution overflowed.
        attempt: usize,
    },
    /// Retired-key accumulation exceeded host indexing.
    RetiredKeys {
        /// One-based native attempt whose contribution overflowed.
        attempt: usize,
    },
}

/// Common exact telemetry view for terminal cached-cycle owners.
pub trait NativeContinuationCachedRetryTelemetrySource {
    /// Returns ordered completed native attempts retained by this owner.
    #[must_use]
    fn cached_retry_attempts(&self) -> &[NativeContinuationCachedRetryAttempt];

    /// Aggregates this owner's completed native-attempt evidence exactly.
    ///
    /// # Errors
    ///
    /// Returns the exact attempt whose contribution overflowed.
    fn cached_retry_telemetry(
        &self,
    ) -> Result<
        NativeContinuationCachedRetryTelemetry,
        NativeContinuationCachedRetryTelemetryError,
    >;
}

impl Display for NativeContinuationCachedRetryTelemetryError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::CompletedSteps { attempt } => write!(
                f,
                "cached retry telemetry step overflow at attempt {attempt}",
            ),
            Self::EvictedKeys { attempt } => write!(
                f,
                "cached retry telemetry eviction overflow at attempt {attempt}",
            ),
            Self::RetiredKeys { attempt } => write!(
                f,
                "cached retry retirement overflow at attempt {attempt}",
            ),
        }
    }
}

impl NativeContinuationCachedRetryTelemetry {
    /// Returns attempts represented by this summary.
    #[must_use]
    pub const fn attempts(self) -> usize {
        self.attempts
    }

    /// Returns committed semantic native steps across represented attempts.
    #[must_use]
    pub const fn completed_steps(self) -> usize {
        self.completed_steps
    }

    pub(super) const fn empty() -> Self {
        Self {
            attempts: 0,
            completed_steps: 0,
            evicted_keys: 0,
            hits: 0,
            insertions: 0,
            retired_keys: 0,
        }
    }

    /// Returns active cache keys evicted by represented insertions.
    #[must_use]
    pub const fn evicted_keys(self) -> usize {
        self.evicted_keys
    }

    pub(super) const fn from_counts(counts: [usize; 6]) -> Self {
        let [
            attempts,
            completed_steps,
            evicted_keys,
            hits,
            insertions,
            retired_keys,
        ] = counts;
        Self {
            attempts,
            completed_steps,
            evicted_keys,
            hits,
            insertions,
            retired_keys,
        }
    }

    /// Returns exact active-cache hits.
    #[must_use]
    pub const fn hits(self) -> usize {
        self.hits
    }

    /// Returns exact cache insertions.
    #[must_use]
    pub const fn insertions(self) -> usize {
        self.insertions
    }

    /// Returns evicted keys left resident behind external leases.
    #[must_use]
    pub const fn retired_keys(self) -> usize {
        self.retired_keys
    }
}

impl NativeContinuationCachedRetryTelemetrySource
    for [NativeContinuationCachedRetryAttempt]
{
    fn cached_retry_attempts(&self) -> &[NativeContinuationCachedRetryAttempt] {
        self
    }

    fn cached_retry_telemetry(
        &self,
    ) -> Result<
        NativeContinuationCachedRetryTelemetry,
        NativeContinuationCachedRetryTelemetryError,
    > {
        summarize_cached_retry_attempts(self)
    }
}

impl NativeContinuationCachedRetryTelemetrySource
    for NativeContinuationCachedRetryCompletion
{
    fn cached_retry_attempts(&self) -> &[NativeContinuationCachedRetryAttempt] {
        self.native_attempts()
    }

    fn cached_retry_telemetry(
        &self,
    ) -> Result<
        NativeContinuationCachedRetryTelemetry,
        NativeContinuationCachedRetryTelemetryError,
    > {
        summarize_cached_retry_attempts(self.native_attempts())
    }
}

impl NativeContinuationCachedRetryTelemetrySource
    for NativeContinuationCachedRetryInterpreterFailure
{
    fn cached_retry_attempts(&self) -> &[NativeContinuationCachedRetryAttempt] {
        self.native_attempts()
    }

    fn cached_retry_telemetry(
        &self,
    ) -> Result<
        NativeContinuationCachedRetryTelemetry,
        NativeContinuationCachedRetryTelemetryError,
    > {
        summarize_cached_retry_attempts(self.native_attempts())
    }
}

impl NativeContinuationCachedRetryTelemetrySource
    for NativeContinuationCachedRetryInterpreterOutcome
{
    fn cached_retry_attempts(&self) -> &[NativeContinuationCachedRetryAttempt] {
        self.native_attempts()
    }

    fn cached_retry_telemetry(
        &self,
    ) -> Result<
        NativeContinuationCachedRetryTelemetry,
        NativeContinuationCachedRetryTelemetryError,
    > {
        summarize_cached_retry_attempts(self.native_attempts())
    }
}

/// Aggregates exact cached retry evidence without selecting a policy.
///
/// # Errors
///
/// Returns [`NativeContinuationCachedRetryTelemetryError`] with the exact
/// attempt whose step, eviction, or retirement contribution overflowed.
pub fn summarize_cached_retry_attempts(
    attempts: &[NativeContinuationCachedRetryAttempt],
) -> Result<
    NativeContinuationCachedRetryTelemetry,
    NativeContinuationCachedRetryTelemetryError,
> {
    let mut telemetry = NativeContinuationCachedRetryTelemetry {
        attempts: attempts.len(),
        ..NativeContinuationCachedRetryTelemetry::default()
    };
    for attempt in attempts {
        telemetry.completed_steps = telemetry
            .completed_steps
            .checked_add(attempt.completed_steps())
            .ok_or_else(|| {
                NativeContinuationCachedRetryTelemetryError::CompletedSteps {
                    attempt: attempt.attempt(),
                }
            })?;
        let disposition = attempt.disposition();
        if disposition.is_hit() {
            telemetry.hits = telemetry.hits.saturating_add(1);
        } else {
            telemetry.insertions = telemetry.insertions.saturating_add(1);
        }
        telemetry.evicted_keys = telemetry
            .evicted_keys
            .checked_add(disposition.evicted_keys().len())
            .ok_or_else(|| {
                NativeContinuationCachedRetryTelemetryError::EvictedKeys {
                    attempt: attempt.attempt(),
                }
            })?;
        telemetry.retired_keys = telemetry
            .retired_keys
            .checked_add(disposition.retired_keys().len())
            .ok_or_else(|| {
                NativeContinuationCachedRetryTelemetryError::RetiredKeys {
                    attempt: attempt.attempt(),
                }
            })?;
    }
    Ok(telemetry)
}
