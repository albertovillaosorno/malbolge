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
//   - Exact caller-supplied latency histograms for cached retry cycles.
// - Must-Not:
//   - Read clocks, infer missing samples, select policy, or persist evidence.
// - Allows:
//   - Inputs: explicit nanosecond samples and increasing inclusive bounds.
//   - Outputs: bucket counts, exact totals, extrema, and record evidence.
//   - Side effects: bounded process-local allocation and mutation only.
// - Split-When:
//   - Clock acquisition, durable retention, or policy publication gains
//     authority.
// - Merge-When:
//   - One telemetry lifecycle owns count and latency evidence atomically.
// - Summary:
//   - Records explicit latency samples without introducing a runtime clock.
// - Description:
//   - Every count and total transition is computed before publication.
// - Usage:
//   - Callers measure externally, then record one complete-cycle sample.
// - Defaults:
//   - Bounds are inclusive; samples above the final bound use the overflow bin.
//

//! Caller-supplied latency evidence for cached native retry cycles.

use std::fmt::{Display, Formatter, Result as FormatResult};

use super::{
    NativeContinuationCachedRetryLatencyHistogramSnapshot,
    NativeContinuationCachedRetryLatencyMergeError,
    NativeContinuationCachedRetryLatencyMergeRecord,
    NativeContinuationCachedRetryLatencySnapshotError,
};

/// Transactional histogram for explicit cached-retry latency samples.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryLatencyHistogram {
    above_maximum: usize,
    buckets: Vec<usize>,
    maximum_nanoseconds: Option<u64>,
    minimum_nanoseconds: Option<u64>,
    samples: usize,
    total_nanoseconds: u128,
    upper_bounds: Vec<u64>,
}

/// Why explicit latency histogram construction or recording failed closed.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryLatencyHistogramError {
    /// At least one inclusive bucket bound is required.
    BoundsEmpty,
    /// Inclusive bounds were not strictly increasing.
    BoundsNotIncreasing {
        /// Zero-based bound index containing the rejected value.
        index: usize,
        /// Immediately preceding bound.
        previous: u64,
        /// Rejected bound.
        observed: u64,
    },
    /// One exact bucket count could not advance.
    BucketCountOverflow {
        /// Inclusive bucket index, or `None` for the overflow bin.
        bucket: Option<usize>,
    },
    /// Exact sample count could not advance.
    SampleCountOverflow,
    /// Exact nanosecond total could not advance.
    TotalNanosecondsOverflow,
}

/// Exact evidence published by one successful histogram record.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryLatencyRecord {
    bucket: Option<usize>,
    maximum_nanoseconds: u64,
    minimum_nanoseconds: u64,
    samples: usize,
    total_nanoseconds: u128,
}

/// One explicit caller-measured latency sample in nanoseconds.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryLatencySample {
    nanoseconds: u64,
}

type LatencyTransitionResult = Result<
    LatencyTransition,
    NativeContinuationCachedRetryLatencyHistogramError,
>;

struct LatencyTransition {
    above_maximum: usize,
    bucket: Option<usize>,
    bucket_count: usize,
    maximum_nanoseconds: u64,
    minimum_nanoseconds: u64,
    samples: usize,
    total_nanoseconds: u128,
}

impl Display for NativeContinuationCachedRetryLatencyHistogramError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::BoundsEmpty => {
                f.write_str("cached retry latency histogram has no bounds")
            },
            Self::BoundsNotIncreasing {
                index,
                previous,
                observed,
            } => write!(
                f,
                concat!(
                    "cached retry latency bound {} is {}, not greater than ",
                    "{}",
                ),
                index, observed, previous,
            ),
            Self::BucketCountOverflow { bucket: Some(index) } => {
                write!(f, "cached retry latency bucket {index} count overflow")
            },
            Self::BucketCountOverflow { bucket: None } => {
                f.write_str("cached retry latency overflow-bin count overflow")
            },
            Self::SampleCountOverflow => {
                f.write_str("cached retry latency sample count overflow")
            },
            Self::TotalNanosecondsOverflow => {
                f.write_str("cached retry latency total nanoseconds overflow")
            },
        }
    }
}

impl NativeContinuationCachedRetryLatencyHistogram {
    /// Returns samples above the final inclusive bucket bound.
    #[must_use]
    pub const fn above_maximum(&self) -> usize {
        self.above_maximum
    }

    /// Returns exact counts corresponding to [`Self::upper_bounds`].
    #[must_use]
    pub fn bucket_counts(&self) -> &[usize] {
        &self.buckets
    }

    #[cfg(test)]
    pub(crate) const fn force_above_maximum_for_test(&mut self, count: usize) {
        self.above_maximum = count;
    }

    #[cfg(test)]
    pub(crate) fn force_bucket_for_test(
        &mut self,
        index: usize,
        count: usize,
    ) -> bool {
        let Some(bucket) = self.buckets.get_mut(index) else {
            return false;
        };
        *bucket = count;
        true
    }

    #[cfg(test)]
    pub(crate) const fn force_totals_for_test(
        &mut self,
        samples: usize,
        total_nanoseconds: u128,
    ) {
        self.samples = samples;
        self.total_nanoseconds = total_nanoseconds;
    }

    /// Reconstructs one histogram from complete untrusted snapshot evidence.
    ///
    /// # Errors
    ///
    /// Returns exact bound, count, extrema, or total rejection evidence.
    pub fn from_snapshot(
        snapshot: NativeContinuationCachedRetryLatencyHistogramSnapshot,
    ) -> Result<Self, NativeContinuationCachedRetryLatencySnapshotError> {
        let validated = super::telemetry_latency_snapshot::
            validate_latency_histogram_snapshot(snapshot)?;
        Ok(Self {
            above_maximum: validated.above_maximum,
            buckets: validated.buckets,
            maximum_nanoseconds: validated.maximum,
            minimum_nanoseconds: validated.minimum,
            samples: validated.samples,
            total_nanoseconds: validated.total,
            upper_bounds: validated.upper_bounds,
        })
    }

    /// Reports whether no latency sample has been recorded.
    #[must_use]
    pub const fn is_empty(&self) -> bool {
        self.samples == 0
    }

    /// Returns the largest recorded latency, or `None` while empty.
    #[must_use]
    pub const fn maximum_nanoseconds(&self) -> Option<u64> {
        self.maximum_nanoseconds
    }

    /// Merges one identical-schema histogram transactionally.
    ///
    /// # Errors
    ///
    /// Returns exact bound mismatch or overflow without changing this owner.
    pub fn merge(
        &mut self,
        source: &Self,
    ) -> Result<
        NativeContinuationCachedRetryLatencyMergeRecord,
        NativeContinuationCachedRetryLatencyMergeError,
    > {
        let transition =
            super::telemetry_latency_merge::prepare_cached_retry_latency_merge(
                self, source,
            )?;
        self.above_maximum = transition.above_maximum;
        self.buckets = transition.buckets;
        self.maximum_nanoseconds = transition.maximum;
        self.minimum_nanoseconds = transition.minimum;
        self.samples = transition.samples;
        self.total_nanoseconds = transition.total;
        Ok(transition.record)
    }

    /// Returns the smallest recorded latency, or `None` while empty.
    #[must_use]
    pub const fn minimum_nanoseconds(&self) -> Option<u64> {
        self.minimum_nanoseconds
    }

    /// Constructs an empty histogram from strictly increasing inclusive bounds.
    ///
    /// # Errors
    ///
    /// Returns exact empty or non-increasing bound evidence.
    pub fn new(
        upper_bounds: Vec<u64>,
    ) -> Result<Self, NativeContinuationCachedRetryLatencyHistogramError> {
        validate_latency_bounds(&upper_bounds)?;
        let buckets = vec![0; upper_bounds.len()];
        Ok(Self {
            above_maximum: 0,
            buckets,
            maximum_nanoseconds: None,
            minimum_nanoseconds: None,
            samples: 0,
            total_nanoseconds: 0,
            upper_bounds,
        })
    }

    /// Records one caller-supplied sample transactionally.
    ///
    /// # Errors
    ///
    /// Returns exact sample, total, or bucket overflow without mutation.
    pub fn record(
        &mut self,
        sample: NativeContinuationCachedRetryLatencySample,
    ) -> Result<
        NativeContinuationCachedRetryLatencyRecord,
        NativeContinuationCachedRetryLatencyHistogramError,
    > {
        let transition = prepare_latency_transition(self, sample)?;
        match transition.bucket {
            Some(index) => {
                let bucket = self.buckets.get_mut(index).ok_or(
                    NativeContinuationCachedRetryLatencyHistogramError::
                        BucketCountOverflow {
                            bucket: Some(index),
                        },
                )?;
                *bucket = transition.bucket_count;
            },
            None => self.above_maximum = transition.above_maximum,
        }
        self.maximum_nanoseconds = Some(transition.maximum_nanoseconds);
        self.minimum_nanoseconds = Some(transition.minimum_nanoseconds);
        self.samples = transition.samples;
        self.total_nanoseconds = transition.total_nanoseconds;
        Ok(NativeContinuationCachedRetryLatencyRecord {
            bucket: transition.bucket,
            maximum_nanoseconds: transition.maximum_nanoseconds,
            minimum_nanoseconds: transition.minimum_nanoseconds,
            samples: transition.samples,
            total_nanoseconds: transition.total_nanoseconds,
        })
    }

    /// Returns the exact number of recorded samples.
    #[must_use]
    pub const fn samples(&self) -> usize {
        self.samples
    }

    /// Returns one immutable complete transfer snapshot.
    #[must_use]
    pub fn snapshot(
        &self,
    ) -> NativeContinuationCachedRetryLatencyHistogramSnapshot {
        super::telemetry_latency_snapshot::snapshot_latency_histogram(self)
    }

    /// Returns the exact sum of recorded nanoseconds.
    #[must_use]
    pub const fn total_nanoseconds(&self) -> u128 {
        self.total_nanoseconds
    }

    /// Returns strictly increasing inclusive bucket bounds.
    #[must_use]
    pub fn upper_bounds(&self) -> &[u64] {
        &self.upper_bounds
    }
}

impl NativeContinuationCachedRetryLatencyRecord {
    /// Returns the inclusive bucket index, or `None` for the overflow bin.
    #[must_use]
    pub const fn bucket(self) -> Option<usize> {
        self.bucket
    }

    /// Returns the largest latency after this publication.
    #[must_use]
    pub const fn maximum_nanoseconds(self) -> u64 {
        self.maximum_nanoseconds
    }

    /// Returns the smallest latency after this publication.
    #[must_use]
    pub const fn minimum_nanoseconds(self) -> u64 {
        self.minimum_nanoseconds
    }

    /// Returns the exact sample count after this publication.
    #[must_use]
    pub const fn samples(self) -> usize {
        self.samples
    }

    /// Returns the exact nanosecond total after this publication.
    #[must_use]
    pub const fn total_nanoseconds(self) -> u128 {
        self.total_nanoseconds
    }
}

impl NativeContinuationCachedRetryLatencySample {
    /// Returns caller-supplied nanoseconds without reinterpretation.
    #[must_use]
    pub const fn nanoseconds(self) -> u64 {
        self.nanoseconds
    }

    /// Constructs one explicit caller-measured latency sample.
    #[must_use]
    pub const fn new(nanoseconds: u64) -> Self {
        Self { nanoseconds }
    }
}

fn prepare_latency_transition(
    histogram: &NativeContinuationCachedRetryLatencyHistogram,
    sample: NativeContinuationCachedRetryLatencySample,
) -> LatencyTransitionResult {
    let nanoseconds = sample.nanoseconds();
    let samples = histogram.samples.checked_add(1).ok_or(
        NativeContinuationCachedRetryLatencyHistogramError::SampleCountOverflow,
    )?;
    let total_nanoseconds = histogram
        .total_nanoseconds
        .checked_add(u128::from(nanoseconds))
        .ok_or(
            NativeContinuationCachedRetryLatencyHistogramError::
                TotalNanosecondsOverflow,
        )?;
    let index = histogram
        .upper_bounds
        .partition_point(|bound| *bound < nanoseconds);
    let bucket = (index < histogram.upper_bounds.len()).then_some(index);
    let (above_maximum, bucket_count) = if let Some(bucket_index) = bucket {
        let current = histogram.buckets.get(bucket_index).copied().ok_or(
            NativeContinuationCachedRetryLatencyHistogramError::
                BucketCountOverflow {
                    bucket: Some(bucket_index),
                },
        )?;
        let next = current.checked_add(1).ok_or(
            NativeContinuationCachedRetryLatencyHistogramError::
                BucketCountOverflow {
                    bucket: Some(bucket_index),
                },
        )?;
        (histogram.above_maximum, next)
    } else {
        let next = histogram.above_maximum.checked_add(1).ok_or(
            NativeContinuationCachedRetryLatencyHistogramError::
                BucketCountOverflow { bucket: None },
        )?;
        (next, next)
    };
    Ok(LatencyTransition {
        above_maximum,
        bucket,
        bucket_count,
        maximum_nanoseconds: histogram
            .maximum_nanoseconds
            .map_or(nanoseconds, |maximum| maximum.max(nanoseconds)),
        minimum_nanoseconds: histogram
            .minimum_nanoseconds
            .map_or(nanoseconds, |minimum| minimum.min(nanoseconds)),
        samples,
        total_nanoseconds,
    })
}

pub(super) fn validate_latency_bounds(
    upper_bounds: &[u64],
) -> Result<(), NativeContinuationCachedRetryLatencyHistogramError> {
    let mut bounds = upper_bounds.iter().copied();
    let Some(mut previous) = bounds.next() else {
        return Err(
            NativeContinuationCachedRetryLatencyHistogramError::BoundsEmpty,
        );
    };
    for (offset, observed) in bounds.enumerate() {
        if observed <= previous {
            return Err(
                NativeContinuationCachedRetryLatencyHistogramError::
                    BoundsNotIncreasing {
                        index: offset.saturating_add(1),
                        previous,
                        observed,
                    },
            );
        }
        previous = observed;
    }
    Ok(())
}
