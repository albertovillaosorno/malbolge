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
//   - Transactional same-schema merges of cached-retry latency histograms.
// - Must-Not:
//   - Rebucket, read clocks, coordinate processes, persist, or select policy.
// - Allows:
//   - Inputs: two validated process-local histograms with explicit bounds.
//   - Outputs: exact merged state or stable mismatch/overflow evidence.
//   - Side effects: target mutation only after every transition is checked.
// - Split-When:
//   - Rebinning, distributed coordination, or durable merge gains authority.
// - Merge-When:
//   - One telemetry lifecycle owns collection and aggregation atomically.
// - Summary:
//   - Combines exact latency evidence without partial publication.
// - Description:
//   - Bounds must match exactly and every counter is checked before mutation.
// - Usage:
//   - Merge process-local workers that were configured with identical buckets.
// - Defaults:
//   - Empty source histograms are exact no-op merges.
//

//! Transactional same-schema latency histogram aggregation.

use super::NativeContinuationCachedRetryLatencyHistogram;

/// Why one exact latency histogram merge failed without mutation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryLatencyMergeError {
    /// Samples above the final bound could not be added.
    AboveMaximumOverflow,
    /// One corresponding inclusive bound differs.
    BoundMismatch {
        /// Zero-based differing bound index.
        index: usize,
        /// Target bound.
        target: u64,
        /// Source bound.
        source: u64,
    },
    /// Bound vector lengths differ.
    BoundsLength {
        /// Target bound count.
        target: usize,
        /// Source bound count.
        source: usize,
    },
    /// One corresponding bucket count could not be added.
    BucketCountOverflow {
        /// Zero-based inclusive bucket index.
        bucket: usize,
    },
    /// Exact sample count could not be added.
    SampleCountOverflow,
    /// Exact nanosecond total could not be added.
    TotalNanosecondsOverflow,
}

/// Exact publication evidence from one successful histogram merge.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryLatencyMergeRecord {
    above_maximum: usize,
    added_samples: usize,
    maximum: Option<u64>,
    minimum: Option<u64>,
    samples: usize,
    total: u128,
}

pub(super) struct CachedRetryLatencyMergeTransition {
    pub(super) above_maximum: usize,
    pub(super) buckets: Vec<usize>,
    pub(super) maximum: Option<u64>,
    pub(super) minimum: Option<u64>,
    pub(super) record: NativeContinuationCachedRetryLatencyMergeRecord,
    pub(super) samples: usize,
    pub(super) total: u128,
}

impl NativeContinuationCachedRetryLatencyMergeRecord {
    /// Returns merged samples above the final bound.
    #[must_use]
    pub const fn above_maximum(self) -> usize {
        self.above_maximum
    }

    /// Returns source samples added by this merge.
    #[must_use]
    pub const fn added_samples(self) -> usize {
        self.added_samples
    }

    /// Returns the merged largest sample.
    #[must_use]
    pub const fn maximum_nanoseconds(self) -> Option<u64> {
        self.maximum
    }

    /// Returns the merged smallest sample.
    #[must_use]
    pub const fn minimum_nanoseconds(self) -> Option<u64> {
        self.minimum
    }

    /// Returns merged exact sample count.
    #[must_use]
    pub const fn samples(self) -> usize {
        self.samples
    }

    /// Returns merged exact nanosecond total.
    #[must_use]
    pub const fn total_nanoseconds(self) -> u128 {
        self.total
    }
}

pub(super) fn prepare_cached_retry_latency_merge(
    target: &NativeContinuationCachedRetryLatencyHistogram,
    source: &NativeContinuationCachedRetryLatencyHistogram,
) -> Result<
    CachedRetryLatencyMergeTransition,
    NativeContinuationCachedRetryLatencyMergeError,
> {
    validate_merge_bounds(target.upper_bounds(), source.upper_bounds())?;
    let mut buckets = Vec::with_capacity(target.bucket_counts().len());
    for (index, (&target_count, &source_count)) in target
        .bucket_counts()
        .iter()
        .zip(source.bucket_counts())
        .enumerate()
    {
        let count = target_count.checked_add(source_count).ok_or(
            NativeContinuationCachedRetryLatencyMergeError::
                BucketCountOverflow { bucket: index },
        )?;
        buckets.push(count);
    }
    let above_maximum = target
        .above_maximum()
        .checked_add(source.above_maximum())
        .ok_or(
            NativeContinuationCachedRetryLatencyMergeError::
                AboveMaximumOverflow,
        )?;
    let samples = target.samples().checked_add(source.samples()).ok_or(
        NativeContinuationCachedRetryLatencyMergeError::SampleCountOverflow,
    )?;
    let total = target
        .total_nanoseconds()
        .checked_add(source.total_nanoseconds())
        .ok_or(
            NativeContinuationCachedRetryLatencyMergeError::
                TotalNanosecondsOverflow,
        )?;
    let minimum = merge_minimum(
        target.minimum_nanoseconds(),
        source.minimum_nanoseconds(),
    );
    let maximum = merge_maximum(
        target.maximum_nanoseconds(),
        source.maximum_nanoseconds(),
    );
    let record = NativeContinuationCachedRetryLatencyMergeRecord {
        above_maximum,
        added_samples: source.samples(),
        maximum,
        minimum,
        samples,
        total,
    };
    Ok(CachedRetryLatencyMergeTransition {
        above_maximum,
        buckets,
        maximum,
        minimum,
        record,
        samples,
        total,
    })
}

fn merge_maximum(left: Option<u64>, right: Option<u64>) -> Option<u64> {
    match (left, right) {
        (Some(left_value), Some(right_value)) => {
            Some(left_value.max(right_value))
        },
        (Some(value), None) | (None, Some(value)) => Some(value),
        (None, None) => None,
    }
}

fn merge_minimum(left: Option<u64>, right: Option<u64>) -> Option<u64> {
    match (left, right) {
        (Some(left_value), Some(right_value)) => {
            Some(left_value.min(right_value))
        },
        (Some(value), None) | (None, Some(value)) => Some(value),
        (None, None) => None,
    }
}

fn validate_merge_bounds(
    target: &[u64],
    source: &[u64],
) -> Result<(), NativeContinuationCachedRetryLatencyMergeError> {
    if target.len() != source.len() {
        return Err(
            NativeContinuationCachedRetryLatencyMergeError::BoundsLength {
                target: target.len(),
                source: source.len(),
            },
        );
    }
    for (index, (&target_bound, &source_bound)) in
        target.iter().zip(source).enumerate()
    {
        if target_bound != source_bound {
            return Err(
                NativeContinuationCachedRetryLatencyMergeError::BoundMismatch {
                    index,
                    target: target_bound,
                    source: source_bound,
                },
            );
        }
    }
    Ok(())
}
