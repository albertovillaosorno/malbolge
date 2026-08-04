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
//   - Immutable validated snapshots of caller-supplied latency histograms.
// - Must-Not:
//   - Serialize, persist, read clocks, merge histograms, or select policy.
// - Allows:
//   - Inputs: explicit bounds, bucket counts, totals, samples, and extrema.
//   - Outputs: exact histogram reconstruction or stable rejection evidence.
//   - Side effects: owned process-local allocation only.
// - Split-When:
//   - Byte framing, durable storage, or cross-process merge gains authority.
// - Merge-When:
//   - One durable latency store owns validation and materialization.
// - Summary:
//   - Transfers complete histogram state through validated immutable evidence.
// - Description:
//   - Validation checks counts, occupied bucket ranges, extrema, and totals.
// - Usage:
//   - Snapshot a live histogram or validate caller-reconstructed evidence.
// - Defaults:
//   - Empty snapshots require zero totals and absent extrema.
//

//! Validated transfer snapshots for cached-retry latency histograms.

use super::{
    NativeContinuationCachedRetryLatencyHistogram,
    NativeContinuationCachedRetryLatencyHistogramError,
};

/// Counts retained by one immutable latency histogram snapshot.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryLatencySnapshotCounts {
    above_maximum: usize,
    buckets: Vec<usize>,
    samples: usize,
}

/// Total and extrema retained by one immutable latency histogram snapshot.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryLatencySnapshotRange {
    maximum: Option<u64>,
    minimum: Option<u64>,
    total: u128,
}

/// Immutable complete transfer evidence for one latency histogram.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryLatencyHistogramSnapshot {
    counts: NativeContinuationCachedRetryLatencySnapshotCounts,
    range: NativeContinuationCachedRetryLatencySnapshotRange,
    upper_bounds: Vec<u64>,
}

/// Why latency histogram snapshot reconstruction failed closed.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryLatencySnapshotError {
    /// Inclusive bounds or their order were invalid.
    Bounds(NativeContinuationCachedRetryLatencyHistogramError),
    /// Bucket count length differs from bound count.
    BucketCount {
        /// Exact count required by supplied bounds.
        expected: usize,
        /// Supplied bucket count length.
        observed: usize,
    },
    /// Count or range arithmetic overflowed at one exact bin.
    CalculationOverflow {
        /// Inclusive bucket index, or `None` for the overflow bin.
        bucket: Option<usize>,
    },
    /// Empty evidence retained a nonempty total or extrema.
    EmptyState,
    /// Nonempty evidence omitted at least one extremum.
    ExtremaMissing,
    /// Minimum exceeds maximum.
    ExtremaOrder {
        /// Supplied maximum latency.
        maximum: u64,
        /// Supplied minimum latency.
        minimum: u64,
    },
    /// One extremum lies outside its exact occupied bin.
    ExtremaRange {
        /// Inclusive bucket index, or `None` for the overflow bin.
        bucket: Option<usize>,
        /// Lowest value admitted by the occupied bin.
        lower: u64,
        /// Supplied extremum.
        observed: u64,
        /// Highest value admitted by the occupied bin.
        upper: u64,
    },
    /// Exact bucket counts do not sum to the supplied sample count.
    SampleCount {
        /// Sample count implied by bucket evidence.
        expected: usize,
        /// Supplied sample count.
        observed: usize,
    },
    /// Total nanoseconds lie outside the exact range admitted by all bins.
    TotalRange {
        /// Lowest possible total for supplied bucket evidence.
        minimum: u128,
        /// Highest possible total for supplied bucket evidence.
        maximum: u128,
        /// Supplied exact total.
        observed: u128,
    },
}

pub(super) struct ValidatedCachedRetryLatencySnapshot {
    pub(super) above_maximum: usize,
    pub(super) buckets: Vec<usize>,
    pub(super) maximum: Option<u64>,
    pub(super) minimum: Option<u64>,
    pub(super) samples: usize,
    pub(super) total: u128,
    pub(super) upper_bounds: Vec<u64>,
}

impl NativeContinuationCachedRetryLatencyHistogramSnapshot {
    /// Returns exact count evidence.
    #[must_use]
    pub const fn counts(
        &self,
    ) -> &NativeContinuationCachedRetryLatencySnapshotCounts {
        &self.counts
    }

    /// Consumes this snapshot into bounds, counts, and range evidence.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> (
        Vec<u64>,
        NativeContinuationCachedRetryLatencySnapshotCounts,
        NativeContinuationCachedRetryLatencySnapshotRange,
    ) {
        (self.upper_bounds, self.counts, self.range)
    }

    /// Constructs explicit untrusted histogram snapshot evidence.
    #[must_use]
    pub const fn new(
        upper_bounds: Vec<u64>,
        counts: NativeContinuationCachedRetryLatencySnapshotCounts,
        range: NativeContinuationCachedRetryLatencySnapshotRange,
    ) -> Self {
        Self {
            counts,
            range,
            upper_bounds,
        }
    }

    /// Returns exact total and extrema evidence.
    #[must_use]
    pub const fn range(
        &self,
    ) -> NativeContinuationCachedRetryLatencySnapshotRange {
        self.range
    }

    /// Returns strictly increasing inclusive bucket bounds.
    #[must_use]
    pub fn upper_bounds(&self) -> &[u64] {
        &self.upper_bounds
    }
}

impl NativeContinuationCachedRetryLatencySnapshotCounts {
    /// Returns samples above the final inclusive bound.
    #[must_use]
    pub const fn above_maximum(&self) -> usize {
        self.above_maximum
    }

    /// Returns exact counts corresponding to snapshot bounds.
    #[must_use]
    pub fn bucket_counts(&self) -> &[usize] {
        &self.buckets
    }

    /// Constructs explicit untrusted count evidence.
    #[must_use]
    pub const fn new(
        buckets: Vec<usize>,
        above_maximum: usize,
        samples: usize,
    ) -> Self {
        Self {
            above_maximum,
            buckets,
            samples,
        }
    }

    /// Returns the claimed total sample count.
    #[must_use]
    pub const fn samples(&self) -> usize {
        self.samples
    }
}

impl NativeContinuationCachedRetryLatencySnapshotRange {
    /// Returns the claimed largest sample.
    #[must_use]
    pub const fn maximum_nanoseconds(self) -> Option<u64> {
        self.maximum
    }

    /// Returns the claimed smallest sample.
    #[must_use]
    pub const fn minimum_nanoseconds(self) -> Option<u64> {
        self.minimum
    }

    /// Constructs explicit untrusted range evidence.
    #[must_use]
    pub const fn new(
        minimum: Option<u64>,
        maximum: Option<u64>,
        total: u128,
    ) -> Self {
        Self { maximum, minimum, total }
    }

    /// Returns the claimed exact nanosecond total.
    #[must_use]
    pub const fn total_nanoseconds(self) -> u128 {
        self.total
    }
}

#[derive(Clone, Copy)]
struct LatencyOccupiedRange {
    bucket: Option<usize>,
    lower: u64,
    upper: u64,
}

#[derive(Clone, Copy)]
struct LatencySnapshotCalculation {
    first: Option<LatencyOccupiedRange>,
    last: Option<LatencyOccupiedRange>,
    maximum_total: u128,
    minimum_total: u128,
    samples: usize,
}

pub(super) fn snapshot_latency_histogram(
    histogram: &NativeContinuationCachedRetryLatencyHistogram,
) -> NativeContinuationCachedRetryLatencyHistogramSnapshot {
    NativeContinuationCachedRetryLatencyHistogramSnapshot::new(
        histogram.upper_bounds().to_vec(),
        NativeContinuationCachedRetryLatencySnapshotCounts::new(
            histogram.bucket_counts().to_vec(),
            histogram.above_maximum(),
            histogram.samples(),
        ),
        NativeContinuationCachedRetryLatencySnapshotRange::new(
            histogram.minimum_nanoseconds(),
            histogram.maximum_nanoseconds(),
            histogram.total_nanoseconds(),
        ),
    )
}

pub(super) fn validate_latency_histogram_snapshot(
    snapshot: NativeContinuationCachedRetryLatencyHistogramSnapshot,
) -> Result<
    ValidatedCachedRetryLatencySnapshot,
    NativeContinuationCachedRetryLatencySnapshotError,
> {
    let NativeContinuationCachedRetryLatencyHistogramSnapshot {
        counts,
        range,
        upper_bounds,
    } = snapshot;
    super::telemetry_latency::validate_latency_bounds(&upper_bounds)
        .map_err(NativeContinuationCachedRetryLatencySnapshotError::Bounds)?;
    if counts.buckets.len() != upper_bounds.len() {
        return Err(
            NativeContinuationCachedRetryLatencySnapshotError::BucketCount {
                expected: upper_bounds.len(),
                observed: counts.buckets.len(),
            },
        );
    }
    let calculation = calculate_latency_snapshot_ranges(
        &upper_bounds,
        &counts.buckets,
        counts.above_maximum,
    )?;
    if calculation.samples != counts.samples {
        return Err(
            NativeContinuationCachedRetryLatencySnapshotError::SampleCount {
                expected: calculation.samples,
                observed: counts.samples,
            },
        );
    }
    validate_latency_snapshot_range(range, calculation)?;
    Ok(ValidatedCachedRetryLatencySnapshot {
        above_maximum: counts.above_maximum,
        buckets: counts.buckets,
        maximum: range.maximum,
        minimum: range.minimum,
        samples: counts.samples,
        total: range.total,
        upper_bounds,
    })
}

fn add_latency_bin(
    calculation: &mut LatencySnapshotCalculation,
    occupied: LatencyOccupiedRange,
    count: usize,
) -> Result<(), NativeContinuationCachedRetryLatencySnapshotError> {
    if count == 0 {
        return Ok(());
    }
    let count_u128 = u128::try_from(count).map_err(|_error| {
        NativeContinuationCachedRetryLatencySnapshotError::CalculationOverflow {
            bucket: occupied.bucket,
        }
    })?;
    let minimum = count_u128
        .checked_mul(u128::from(occupied.lower))
        .ok_or(
            NativeContinuationCachedRetryLatencySnapshotError::
                CalculationOverflow {
                    bucket: occupied.bucket,
                },
        )?;
    let maximum = count_u128
        .checked_mul(u128::from(occupied.upper))
        .ok_or(
            NativeContinuationCachedRetryLatencySnapshotError::
                CalculationOverflow {
                    bucket: occupied.bucket,
                },
        )?;
    calculation.minimum_total = calculation
        .minimum_total
        .checked_add(minimum)
        .ok_or(
            NativeContinuationCachedRetryLatencySnapshotError::
                CalculationOverflow {
                    bucket: occupied.bucket,
                },
        )?;
    calculation.maximum_total = calculation
        .maximum_total
        .checked_add(maximum)
        .ok_or(
            NativeContinuationCachedRetryLatencySnapshotError::
                CalculationOverflow {
                    bucket: occupied.bucket,
                },
        )?;
    calculation.samples = calculation.samples.checked_add(count).ok_or(
        NativeContinuationCachedRetryLatencySnapshotError::
            CalculationOverflow {
                bucket: occupied.bucket,
            },
    )?;
    if calculation.first.is_none() {
        calculation.first = Some(occupied);
    }
    calculation.last = Some(occupied);
    Ok(())
}

fn calculate_latency_snapshot_ranges(
    upper_bounds: &[u64],
    buckets: &[usize],
    above_maximum: usize,
) -> Result<
    LatencySnapshotCalculation,
    NativeContinuationCachedRetryLatencySnapshotError,
> {
    let mut calculation = LatencySnapshotCalculation {
        first: None,
        last: None,
        maximum_total: 0,
        minimum_total: 0,
        samples: 0,
    };
    let mut lower = 0;
    for (index, (&upper, &count)) in
        upper_bounds.iter().zip(buckets).enumerate()
    {
        add_latency_bin(
            &mut calculation,
            LatencyOccupiedRange {
                bucket: Some(index),
                lower,
                upper,
            },
            count,
        )?;
        lower = upper.saturating_add(1);
    }
    if above_maximum > 0 {
        let final_bound = upper_bounds.last().copied().ok_or(
            NativeContinuationCachedRetryLatencySnapshotError::Bounds(
                NativeContinuationCachedRetryLatencyHistogramError::BoundsEmpty,
            ),
        )?;
        let overflow_lower = final_bound.checked_add(1).ok_or(
            NativeContinuationCachedRetryLatencySnapshotError::
                CalculationOverflow { bucket: None },
        )?;
        add_latency_bin(
            &mut calculation,
            LatencyOccupiedRange {
                bucket: None,
                lower: overflow_lower,
                upper: u64::MAX,
            },
            above_maximum,
        )?;
    }
    Ok(calculation)
}

fn validate_extremum(
    occupied: LatencyOccupiedRange,
    observed: u64,
) -> Result<(), NativeContinuationCachedRetryLatencySnapshotError> {
    if (occupied.lower..=occupied.upper).contains(&observed) {
        Ok(())
    } else {
        Err(
            NativeContinuationCachedRetryLatencySnapshotError::ExtremaRange {
                bucket: occupied.bucket,
                lower: occupied.lower,
                observed,
                upper: occupied.upper,
            },
        )
    }
}

fn validate_latency_snapshot_range(
    range: NativeContinuationCachedRetryLatencySnapshotRange,
    calculation: LatencySnapshotCalculation,
) -> Result<(), NativeContinuationCachedRetryLatencySnapshotError> {
    if calculation.samples == 0 {
        if range.total == 0
            && range.minimum.is_none()
            && range.maximum.is_none()
        {
            return Ok(());
        }
        return Err(
            NativeContinuationCachedRetryLatencySnapshotError::EmptyState,
        );
    }
    let (Some(minimum), Some(maximum)) = (range.minimum, range.maximum) else {
        return Err(
            NativeContinuationCachedRetryLatencySnapshotError::ExtremaMissing,
        );
    };
    if minimum > maximum {
        return Err(
            NativeContinuationCachedRetryLatencySnapshotError::ExtremaOrder {
                maximum,
                minimum,
            },
        );
    }
    let first = calculation.first.ok_or(
        NativeContinuationCachedRetryLatencySnapshotError::ExtremaMissing,
    )?;
    let last = calculation.last.ok_or(
        NativeContinuationCachedRetryLatencySnapshotError::ExtremaMissing,
    )?;
    validate_extremum(first, minimum)?;
    validate_extremum(last, maximum)?;
    if !(calculation.minimum_total..=calculation.maximum_total)
        .contains(&range.total)
    {
        return Err(
            NativeContinuationCachedRetryLatencySnapshotError::TotalRange {
                minimum: calculation.minimum_total,
                maximum: calculation.maximum_total,
                observed: range.total,
            },
        );
    }
    Ok(())
}
