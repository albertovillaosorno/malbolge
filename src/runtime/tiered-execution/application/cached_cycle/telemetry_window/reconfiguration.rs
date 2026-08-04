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
//   - Transactional capacity changes for one cached-retry telemetry FIFO.
// - Must-Not:
//   - Select capacity policy, reset sequences, or discard removal evidence.
// - Allows:
//   - Inputs: one window owner and an explicit positive requested capacity.
//   - Outputs: published capacity, oldest-first removals, evictions, and
//     totals.
//   - Side effects: process-local removal of the exact oldest retained prefix.
// - Split-When:
//   - Capacity recommendation or asynchronous retention gains authority.
// - Merge-When:
//   - Retention and capacity publication become one indivisible use case.
// - Summary:
//   - Reconfigures bounded telemetry retention without partial publication.
// - Description:
//   - Expansion is immediate; shrink computes all exact evidence before change.
// - Usage:
//   - Called through `NativeContinuationCachedRetryTelemetryWindow`.
// - Defaults:
//   - Removed observations increment cumulative FIFO eviction evidence.
//

//! Transactional capacity changes for cached-retry telemetry retention.

use super::*;

/// Exact published result of one caller-requested capacity transition.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryTelemetryWindowReconfiguration {
    current_capacity: NonZeroUsize,
    evictions: u64,
    previous_capacity: NonZeroUsize,
    removed: Vec<NativeContinuationCachedRetryTelemetryObservation>,
    totals: NativeContinuationCachedRetryTelemetry,
}

/// Result of one transactional telemetry-window capacity publication.
pub type NativeContinuationCachedRetryTelemetryWindowReconfigurationResult =
    Result<
        NativeContinuationCachedRetryTelemetryWindowReconfiguration,
        NativeContinuationCachedRetryTelemetryWindowError,
    >;

impl NativeContinuationCachedRetryTelemetryWindowReconfiguration {
    /// Returns the published positive capacity.
    #[must_use]
    pub const fn current_capacity(&self) -> NonZeroUsize {
        self.current_capacity
    }

    /// Returns cumulative FIFO evictions after publication.
    #[must_use]
    pub const fn evictions(&self) -> u64 {
        self.evictions
    }

    /// Returns the capacity in force before publication.
    #[must_use]
    pub const fn previous_capacity(&self) -> NonZeroUsize {
        self.previous_capacity
    }

    /// Returns oldest-first observations removed by this transition.
    #[must_use]
    pub fn removed(
        &self,
    ) -> &[NativeContinuationCachedRetryTelemetryObservation] {
        &self.removed
    }

    /// Returns exact retained aggregate telemetry after publication.
    #[must_use]
    pub const fn totals(&self) -> NativeContinuationCachedRetryTelemetry {
        self.totals
    }
}

pub(super) fn reconfigure_telemetry_window(
    window: &mut NativeContinuationCachedRetryTelemetryWindow,
    capacity: NonZeroUsize,
) -> NativeContinuationCachedRetryTelemetryWindowReconfigurationResult {
    let previous_capacity = window.capacity;
    let removed_count =
        window.observations.len().saturating_sub(capacity.get());
    let mut totals = window.totals;
    for observation in window.observations.iter().take(removed_count) {
        totals = subtract_telemetry(
            totals,
            observation.telemetry(),
            observation.sequence(),
        )?;
    }
    let removed_u64 = u64::try_from(removed_count).map_err(|_error| {
        NativeContinuationCachedRetryTelemetryWindowError::
                RemovalCountOverflow {
                    sequence: window.last_sequence,
                }
    })?;
    let evictions = window.evictions.checked_add(removed_u64).ok_or(
            NativeContinuationCachedRetryTelemetryWindowError::
                EvictionCountOverflow {
                    sequence: window.last_sequence,
                },
        )?;
    let removed = window
        .observations
        .iter()
        .take(removed_count)
        .copied()
        .collect::<Vec<_>>();
    for _ in 0..removed_count {
        let _observation = window.observations.pop_front();
    }
    window.capacity = capacity;
    window.evictions = evictions;
    window.totals = totals;
    Ok(
        NativeContinuationCachedRetryTelemetryWindowReconfiguration {
            current_capacity: capacity,
            evictions,
            previous_capacity,
            removed,
            totals,
        },
    )
}
