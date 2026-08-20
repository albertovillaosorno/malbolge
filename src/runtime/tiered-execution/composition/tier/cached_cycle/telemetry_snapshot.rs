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
//   - Immutable transfer snapshots for bounded cached-retry telemetry windows.
// - Must-Not:
//   - Serialize, persist, merge, infer missing observations, or select policy.
// - Allows:
//   - Inputs: explicit metadata, ordered observations, totals, and capacity.
//   - Outputs: validated exact window reconstruction or stable rejection.
//   - Side effects: owned process-local allocation only.
// - Split-When:
//   - A byte format, durable store, or cross-process merge gains ownership.
// - Merge-When:
//   - One durable telemetry store owns validation and materialization.
// - Summary:
//   - Transfers bounded telemetry windows through validated immutable
//     snapshots.
// - Description:
//   - Reconstruction verifies capacity, sequence, evictions, and exact totals.
// - Usage:
//   - Snapshot a live window or validate caller-reconstructed transfer
//     evidence.
// - Defaults:
//   - Empty snapshots require zero metadata and zero totals.
//

//! Validated transfer snapshots for cached-retry telemetry windows.

use std::num::NonZeroUsize;

use super::{
    NativeContinuationCachedRetryTelemetry,
    NativeContinuationCachedRetryTelemetryObservation,
    NativeContinuationCachedRetryTelemetryWindow,
    NativeContinuationCachedRetryTelemetryWindowError,
};

type SnapshotError = NativeContinuationCachedRetryTelemetrySnapshotError;

/// Sequence and eviction metadata retained by one immutable snapshot.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryTelemetrySnapshotMetadata {
    evictions: u64,
    last_sequence: u64,
}

/// Immutable transfer representation of one bounded telemetry window.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryTelemetryWindowSnapshot {
    capacity: NonZeroUsize,
    metadata: NativeContinuationCachedRetryTelemetrySnapshotMetadata,
    observations: Vec<NativeContinuationCachedRetryTelemetryObservation>,
    totals: NativeContinuationCachedRetryTelemetry,
}

/// Why an immutable telemetry snapshot failed exact reconstruction.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryTelemetrySnapshotError {
    /// Recomputing retained totals overflowed at one exact observation.
    Aggregate(NativeContinuationCachedRetryTelemetryWindowError),
    /// An empty observation set retained nonzero sequence or eviction metadata.
    EmptyMetadata {
        /// Retained cumulative eviction count.
        evictions: u64,
        /// Retained newest sequence.
        last_sequence: u64,
    },
    /// Cumulative evictions differ from sequence minus retained count.
    EvictionCount {
        /// Count implied by retained sequence evidence.
        expected: u64,
        /// Count supplied by snapshot metadata.
        observed: u64,
    },
    /// The first retained sequence differs from eviction count plus one.
    FirstSequence {
        /// Sequence implied by cumulative evictions.
        expected: u64,
        /// Sequence retained by the first observation.
        observed: u64,
    },
    /// The newest observation differs from snapshot metadata.
    LastSequence {
        /// Sequence retained by snapshot metadata.
        expected: u64,
        /// Sequence retained by the newest observation.
        observed: u64,
    },
    /// Retained observation count cannot be represented by snapshot metadata.
    ObservationCountOverflow,
    /// Retained observation count exceeds the positive window capacity.
    RetainedCount {
        /// Maximum count admitted by the snapshot capacity.
        expected: usize,
        /// Count supplied by the snapshot.
        observed: usize,
    },
    /// Two retained observations are not exactly contiguous.
    SequenceGap {
        /// Zero-based retained observation index.
        index: usize,
        /// Sequence implied by preceding snapshot evidence.
        expected: u64,
        /// Sequence supplied by the observation.
        observed: u64,
    },
    /// Supplied totals differ from exact retained observation aggregation.
    Totals,
}

pub(super) struct ValidatedCachedRetryTelemetrySnapshot {
    pub(super) capacity: NonZeroUsize,
    pub(super) evictions: u64,
    pub(super) last_sequence: u64,
    pub(super) observations:
        Vec<NativeContinuationCachedRetryTelemetryObservation>,
    pub(super) totals: NativeContinuationCachedRetryTelemetry,
}

impl NativeContinuationCachedRetryTelemetrySnapshotMetadata {
    /// Returns cumulative oldest-first FIFO evictions.
    #[must_use]
    pub const fn evictions(self) -> u64 {
        self.evictions
    }

    /// Returns the newest published sequence, or zero before any append.
    #[must_use]
    pub const fn last_sequence(self) -> u64 {
        self.last_sequence
    }

    /// Constructs explicit snapshot metadata.
    #[must_use]
    pub const fn new(evictions: u64, last_sequence: u64) -> Self {
        Self { evictions, last_sequence }
    }
}

impl NativeContinuationCachedRetryTelemetryWindowSnapshot {
    /// Returns the positive retained observation capacity.
    #[must_use]
    pub const fn capacity(&self) -> NonZeroUsize {
        self.capacity
    }

    /// Consumes this snapshot into all explicit transfer evidence.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> NativeContinuationCachedRetryTelemetryWindowSnapshotParts {
        (self.capacity, self.metadata, self.observations, self.totals)
    }

    /// Returns sequence and eviction metadata.
    #[must_use]
    pub const fn metadata(
        &self,
    ) -> NativeContinuationCachedRetryTelemetrySnapshotMetadata {
        self.metadata
    }

    /// Constructs explicit untrusted transfer evidence for later validation.
    #[must_use]
    pub const fn new(
        capacity: NonZeroUsize,
        metadata: NativeContinuationCachedRetryTelemetrySnapshotMetadata,
        observations: Vec<NativeContinuationCachedRetryTelemetryObservation>,
        totals: NativeContinuationCachedRetryTelemetry,
    ) -> Self {
        Self {
            capacity,
            metadata,
            observations,
            totals,
        }
    }

    /// Returns retained observations from oldest to newest.
    #[must_use]
    pub fn observations(
        &self,
    ) -> &[NativeContinuationCachedRetryTelemetryObservation] {
        &self.observations
    }

    /// Returns exact aggregate telemetry claimed by this snapshot.
    #[must_use]
    pub const fn totals(&self) -> NativeContinuationCachedRetryTelemetry {
        self.totals
    }
}

/// Capacity, metadata, observations, and totals retained by one snapshot.
pub type NativeContinuationCachedRetryTelemetryWindowSnapshotParts = (
    NonZeroUsize,
    NativeContinuationCachedRetryTelemetrySnapshotMetadata,
    Vec<NativeContinuationCachedRetryTelemetryObservation>,
    NativeContinuationCachedRetryTelemetry,
);

pub(super) fn snapshot_telemetry_window(
    window: &NativeContinuationCachedRetryTelemetryWindow,
) -> NativeContinuationCachedRetryTelemetryWindowSnapshot {
    NativeContinuationCachedRetryTelemetryWindowSnapshot {
        capacity: window.capacity(),
        metadata: NativeContinuationCachedRetryTelemetrySnapshotMetadata::new(
            window.evictions(),
            window.last_sequence().unwrap_or(0),
        ),
        observations: window.observations().copied().collect(),
        totals: window.totals(),
    }
}

pub(super) fn validate_telemetry_snapshot(
    snapshot: NativeContinuationCachedRetryTelemetryWindowSnapshot,
) -> Result<
    ValidatedCachedRetryTelemetrySnapshot,
    NativeContinuationCachedRetryTelemetrySnapshotError,
> {
    let NativeContinuationCachedRetryTelemetryWindowSnapshot {
        capacity,
        metadata,
        observations,
        totals,
    } = snapshot;
    if observations.is_empty() {
        return validate_empty_snapshot(capacity, metadata, totals);
    }
    validate_snapshot_metadata(capacity, metadata, observations.len())?;
    validate_observation_sequences(&observations, metadata)?;
    let recomputed = super::telemetry_window::aggregate_telemetry_observations(
        &observations,
    )
    .map_err(NativeContinuationCachedRetryTelemetrySnapshotError::Aggregate)?;
    if recomputed != totals {
        return Err(
            NativeContinuationCachedRetryTelemetrySnapshotError::Totals,
        );
    }
    Ok(ValidatedCachedRetryTelemetrySnapshot {
        capacity,
        evictions: metadata.evictions(),
        last_sequence: metadata.last_sequence(),
        observations,
        totals,
    })
}

fn validate_snapshot_metadata(
    capacity: NonZeroUsize,
    metadata: NativeContinuationCachedRetryTelemetrySnapshotMetadata,
    observed_retained: usize,
) -> Result<(), NativeContinuationCachedRetryTelemetrySnapshotError> {
    let retained = u64::try_from(observed_retained).map_err(|_error| {
        NativeContinuationCachedRetryTelemetrySnapshotError::
            ObservationCountOverflow
    })?;
    if observed_retained > capacity.get() {
        return Err(
            NativeContinuationCachedRetryTelemetrySnapshotError::RetainedCount {
                expected: capacity.get(),
                observed: observed_retained,
            },
        );
    }
    let expected_evictions = metadata
        .last_sequence()
        .checked_sub(retained)
        .ok_or_else(|| {
            NativeContinuationCachedRetryTelemetrySnapshotError::EvictionCount {
                expected: 0,
                observed: metadata.evictions(),
            }
        })?;
    if metadata.evictions() != expected_evictions {
        return Err(
            NativeContinuationCachedRetryTelemetrySnapshotError::EvictionCount {
                expected: expected_evictions,
                observed: metadata.evictions(),
            },
        );
    }
    Ok(())
}

fn validate_empty_snapshot(
    capacity: NonZeroUsize,
    metadata: NativeContinuationCachedRetryTelemetrySnapshotMetadata,
    totals: NativeContinuationCachedRetryTelemetry,
) -> Result<
    ValidatedCachedRetryTelemetrySnapshot,
    NativeContinuationCachedRetryTelemetrySnapshotError,
> {
    if metadata
        != NativeContinuationCachedRetryTelemetrySnapshotMetadata::default()
    {
        return Err(
            NativeContinuationCachedRetryTelemetrySnapshotError::EmptyMetadata {
                evictions: metadata.evictions(),
                last_sequence: metadata.last_sequence(),
            },
        );
    }
    if totals != NativeContinuationCachedRetryTelemetry::default() {
        return Err(
            NativeContinuationCachedRetryTelemetrySnapshotError::Totals,
        );
    }
    Ok(ValidatedCachedRetryTelemetrySnapshot {
        capacity,
        evictions: 0,
        last_sequence: 0,
        observations: Vec::new(),
        totals,
    })
}

fn validate_observation_sequences(
    observations: &[NativeContinuationCachedRetryTelemetryObservation],
    metadata: NativeContinuationCachedRetryTelemetrySnapshotMetadata,
) -> Result<(), NativeContinuationCachedRetryTelemetrySnapshotError> {
    let mut iter = observations.iter();
    let Some(first_observation) = iter.next() else {
        return Ok(());
    };
    let first = first_observation.sequence();
    let expected_first = metadata.evictions().checked_add(1).ok_or(
        NativeContinuationCachedRetryTelemetrySnapshotError::FirstSequence {
            expected: 0,
            observed: first,
        },
    )?;
    if first != expected_first {
        return Err(
            NativeContinuationCachedRetryTelemetrySnapshotError::FirstSequence {
                expected: expected_first,
                observed: first,
            },
        );
    }
    let mut previous = first;
    for (offset, observation) in iter.enumerate() {
        let index = offset.checked_add(1).ok_or(
            NativeContinuationCachedRetryTelemetrySnapshotError::
                ObservationCountOverflow,
        )?;
        let observed = observation.sequence();
        let expected =
            previous.checked_add(1).ok_or(SnapshotError::SequenceGap {
                index,
                expected: 0,
                observed,
            })?;
        if observed != expected {
            return Err(SnapshotError::SequenceGap {
                index,
                expected,
                observed,
            });
        }
        previous = observed;
    }
    if previous != metadata.last_sequence() {
        return Err(
            NativeContinuationCachedRetryTelemetrySnapshotError::LastSequence {
                expected: metadata.last_sequence(),
                observed: previous,
            },
        );
    }
    Ok(())
}
