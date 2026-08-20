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
//   - Bounded process-local retention of exact cached-retry telemetry.
// - Must-Not:
//   - Select retry policy, persist observations, infer latency, or hide
//     arithmetic failure.
// - Allows:
//   - Inputs: exact immutable telemetry summaries.
//   - Outputs: monotonic observations, FIFO eviction evidence, and exact
//     totals.
//   - Side effects: bounded process-local allocation only.
// - Split-When:
//   - Persistence, cross-process merge, or adaptive decisions gain ownership.
// - Merge-When:
//   - One caller-owned telemetry lifecycle subsumes retention and policy.
// - Summary:
//   - Retains a bounded FIFO of exact cached-retry telemetry summaries.
// - Description:
//   - Aggregate transitions are computed before publication and fail closed.
// - Usage:
//   - Append summaries, inspect retained evidence, or snapshot exact state.
// - Defaults:
//   - Sequence IDs start at one; full windows evict exactly one oldest item.
//

//! Bounded process-local cached-retry telemetry retention.

#[path = "telemetry_window/aggregation.rs"]
mod aggregation;
#[path = "telemetry_window/reconfiguration.rs"]
mod reconfiguration;

use std::collections::{VecDeque, vec_deque};
use std::fmt::{Display, Formatter, Result as FormatResult};
use std::num::NonZeroUsize;

use aggregation::{add_telemetry, subtract_telemetry};
pub use reconfiguration::{
    NativeContinuationCachedRetryTelemetryWindowReconfiguration,
    NativeContinuationCachedRetryTelemetryWindowReconfigurationResult,
};

use super::{
    NativeContinuationCachedRetryTelemetry,
    NativeContinuationCachedRetryTelemetrySnapshotError,
    NativeContinuationCachedRetryTelemetryWindowSnapshot,
};

/// One immutable retained telemetry summary with a monotonic sequence ID.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryTelemetryObservation {
    sequence: u64,
    telemetry: NativeContinuationCachedRetryTelemetry,
}

/// One successfully published append and optional FIFO eviction.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryTelemetryWindowAppend {
    evicted: Option<NativeContinuationCachedRetryTelemetryObservation>,
    evictions: u64,
    observation: NativeContinuationCachedRetryTelemetryObservation,
    totals: NativeContinuationCachedRetryTelemetry,
}

/// Counter whose exact bounded-window transition failed.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryTelemetryWindowCounter {
    /// Number of represented attempts.
    Attempts,
    /// Number of committed semantic native steps.
    CompletedSteps,
    /// Number of active keys evicted by insertions.
    EvictedKeys,
    /// Number of cache hits.
    Hits,
    /// Number of cache insertions.
    Insertions,
    /// Number of keys left resident behind external leases.
    RetiredKeys,
}

/// Why one bounded telemetry-window transition failed without mutation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryTelemetryWindowError {
    /// One aggregate counter overflowed while adding the candidate.
    AggregateOverflow {
        /// Candidate sequence whose contribution overflowed.
        sequence: u64,
        /// Exact counter that overflowed.
        counter: NativeContinuationCachedRetryTelemetryWindowCounter,
    },
    /// Stored totals could not subtract the exact FIFO victim.
    AggregateUnderflow {
        /// Candidate sequence whose transaction exposed the invariant failure.
        sequence: u64,
        /// Exact counter that underflowed.
        counter: NativeContinuationCachedRetryTelemetryWindowCounter,
    },
    /// The exact cumulative FIFO-eviction counter overflowed.
    EvictionCountOverflow {
        /// Candidate sequence that required one more eviction.
        sequence: u64,
    },
    /// Removed observation count cannot become cumulative eviction evidence.
    RemovalCountOverflow {
        /// Newest sequence retained by the failed reconfiguration.
        sequence: u64,
    },
    /// The monotonic observation sequence cannot advance beyond `u64::MAX`.
    SequenceExhausted,
}

/// Caller-owned bounded FIFO for exact cached-retry telemetry summaries.
#[derive(Debug)]
pub struct NativeContinuationCachedRetryTelemetryWindow {
    capacity: NonZeroUsize,
    evictions: u64,
    last_sequence: u64,
    observations: VecDeque<NativeContinuationCachedRetryTelemetryObservation>,
    totals: NativeContinuationCachedRetryTelemetry,
}

impl Display for NativeContinuationCachedRetryTelemetryWindowCounter {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Attempts => "attempts",
            Self::CompletedSteps => "completed steps",
            Self::EvictedKeys => "evicted keys",
            Self::Hits => "hits",
            Self::Insertions => "insertions",
            Self::RetiredKeys => "retired keys",
        })
    }
}

impl Display for NativeContinuationCachedRetryTelemetryWindowError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::RemovalCountOverflow { sequence } => write!(
                f,
                concat!(
                    "cached retry telemetry removal count overflow ",
                    "at sequence {}",
                ),
                sequence,
            ),
            Self::SequenceExhausted => {
                f.write_str("cached retry telemetry sequence exhausted")
            },
            Self::AggregateOverflow { sequence, counter } => write!(
                f,
                "cached retry telemetry {counter} overflow at sequence \
                 {sequence}",
            ),
            Self::AggregateUnderflow { sequence, counter } => write!(
                f,
                "cached retry telemetry {counter} underflow at sequence \
                 {sequence}",
            ),
            Self::EvictionCountOverflow { sequence } => write!(
                f,
                "cached retry telemetry eviction count overflow at sequence \
                 {sequence}",
            ),
        }
    }
}

impl NativeContinuationCachedRetryTelemetryObservation {
    /// Constructs explicit untrusted observation evidence.
    ///
    /// Sequence continuity and aggregate consistency are validated only when
    /// reconstructing a telemetry window from a complete snapshot.
    #[must_use]
    pub const fn new(
        sequence: u64,
        telemetry: NativeContinuationCachedRetryTelemetry,
    ) -> Self {
        Self { sequence, telemetry }
    }

    /// Returns the monotonic one-based observation sequence.
    #[must_use]
    pub const fn sequence(self) -> u64 {
        self.sequence
    }

    /// Returns the exact immutable telemetry summary.
    #[must_use]
    pub const fn telemetry(self) -> NativeContinuationCachedRetryTelemetry {
        self.telemetry
    }
}

impl NativeContinuationCachedRetryTelemetryWindowAppend {
    /// Returns the oldest observation removed by this append, when full.
    #[must_use]
    pub const fn evicted(
        self,
    ) -> Option<NativeContinuationCachedRetryTelemetryObservation> {
        self.evicted
    }

    /// Returns cumulative FIFO evictions after publication.
    #[must_use]
    pub const fn evictions(self) -> u64 {
        self.evictions
    }

    /// Returns the newly retained observation.
    #[must_use]
    pub const fn observation(
        self,
    ) -> NativeContinuationCachedRetryTelemetryObservation {
        self.observation
    }

    /// Returns exact aggregate telemetry after publication.
    #[must_use]
    pub const fn totals(self) -> NativeContinuationCachedRetryTelemetry {
        self.totals
    }
}

impl NativeContinuationCachedRetryTelemetryWindow {
    /// Appends one summary transactionally and evicts one oldest item when
    /// full.
    ///
    /// # Errors
    ///
    /// Returns exact sequence, aggregate, or eviction-counter failure without
    /// changing retained observations, totals, sequence, or eviction evidence.
    pub fn append(
        &mut self,
        telemetry: NativeContinuationCachedRetryTelemetry,
    ) -> Result<
        NativeContinuationCachedRetryTelemetryWindowAppend,
        NativeContinuationCachedRetryTelemetryWindowError,
    > {
        let sequence = self
            .last_sequence
            .checked_add(1)
            .ok_or(
                NativeContinuationCachedRetryTelemetryWindowError::
                    SequenceExhausted,
            )?;
        let evicted = if self.observations.len() == self.capacity.get() {
            self.observations.front().copied()
        } else {
            None
        };
        let without_evicted = match evicted {
            Some(observation) => subtract_telemetry(
                self.totals,
                observation.telemetry,
                sequence,
            )?,
            None => self.totals,
        };
        let totals = add_telemetry(without_evicted, telemetry, sequence)?;
        let evictions = match evicted {
            Some(_) => self.evictions.checked_add(1).ok_or(
                NativeContinuationCachedRetryTelemetryWindowError::
                    EvictionCountOverflow { sequence },
            )?,
            None => self.evictions,
        };
        if evicted.is_some() {
            let _removed = self.observations.pop_front();
        }
        let observation = NativeContinuationCachedRetryTelemetryObservation {
            sequence,
            telemetry,
        };
        self.observations.push_back(observation);
        self.evictions = evictions;
        self.last_sequence = sequence;
        self.totals = totals;
        Ok(NativeContinuationCachedRetryTelemetryWindowAppend {
            evicted,
            evictions,
            observation,
            totals,
        })
    }

    /// Returns the positive retained observation capacity.
    #[must_use]
    pub const fn capacity(&self) -> NonZeroUsize {
        self.capacity
    }

    /// Returns cumulative oldest-first FIFO evictions.
    #[must_use]
    pub const fn evictions(&self) -> u64 {
        self.evictions
    }

    #[cfg(test)]
    pub(crate) const fn force_counters_for_test(
        &mut self,
        evictions: u64,
        last_sequence: u64,
    ) {
        self.evictions = evictions;
        self.last_sequence = last_sequence;
    }

    /// Reconstructs one exact window from validated transfer evidence.
    ///
    /// # Errors
    ///
    /// Returns stable snapshot validation evidence without partial publication.
    pub fn from_snapshot(
        snapshot: NativeContinuationCachedRetryTelemetryWindowSnapshot,
    ) -> Result<Self, NativeContinuationCachedRetryTelemetrySnapshotError> {
        let validated =
            super::telemetry_snapshot::validate_telemetry_snapshot(snapshot)?;
        Ok(Self {
            capacity: validated.capacity,
            evictions: validated.evictions,
            last_sequence: validated.last_sequence,
            observations: validated.observations.into(),
            totals: validated.totals,
        })
    }

    /// Reports whether no observation is retained.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.observations.is_empty()
    }

    /// Returns the newest published sequence, or `None` while empty.
    #[must_use]
    pub const fn last_sequence(&self) -> Option<u64> {
        if self.last_sequence == 0 {
            None
        } else {
            Some(self.last_sequence)
        }
    }

    /// Returns the retained observation count.
    #[must_use]
    pub fn len(&self) -> usize {
        self.observations.len()
    }

    /// Constructs an empty bounded process-local telemetry FIFO.
    #[must_use]
    pub const fn new(capacity: NonZeroUsize) -> Self {
        Self {
            capacity,
            evictions: 0,
            last_sequence: 0,
            observations: VecDeque::new(),
            totals: NativeContinuationCachedRetryTelemetry::empty(),
        }
    }

    /// Iterates retained observations from oldest to newest.
    #[must_use]
    pub fn observations(
        &self,
    ) -> vec_deque::Iter<'_, NativeContinuationCachedRetryTelemetryObservation>
    {
        self.observations.iter()
    }

    /// Reconfigures retained capacity transactionally.
    ///
    /// Shrink removes the exact oldest prefix and charges each removal to the
    /// cumulative eviction count. Expansion and no-op publication remove none.
    ///
    /// # Errors
    ///
    /// Returns exact aggregate or count failure without changing the window.
    pub fn reconfigure_capacity(
        &mut self,
        capacity: NonZeroUsize,
    ) -> NativeContinuationCachedRetryTelemetryWindowReconfigurationResult {
        reconfiguration::reconfigure_telemetry_window(self, capacity)
    }

    /// Captures one immutable exact transfer snapshot.
    #[must_use]
    pub fn snapshot(
        &self,
    ) -> NativeContinuationCachedRetryTelemetryWindowSnapshot {
        super::telemetry_snapshot::snapshot_telemetry_window(self)
    }

    /// Returns exact aggregate telemetry for retained observations.
    #[must_use]
    pub const fn totals(&self) -> NativeContinuationCachedRetryTelemetry {
        self.totals
    }
}

pub(super) fn aggregate_telemetry_observations(
    observations: &[NativeContinuationCachedRetryTelemetryObservation],
) -> Result<
    NativeContinuationCachedRetryTelemetry,
    NativeContinuationCachedRetryTelemetryWindowError,
> {
    aggregation::aggregate_telemetry_observations(observations)
}
