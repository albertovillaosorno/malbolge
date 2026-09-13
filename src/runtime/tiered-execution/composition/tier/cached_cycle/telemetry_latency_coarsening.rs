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
//   - Exact coarsening of one cached-retry latency histogram schema.
// - Must-Not:
//   - Refine buckets, infer within-bucket distribution, read clocks, or mutate
//     the source histogram.
// - Allows:
//   - Inputs: one validated histogram and explicit coarser inclusive bounds.
//   - Outputs: exact coarsened histogram plus schema transition evidence.
//   - Side effects: owned process-local allocation only.
// - Split-When:
//   - Approximate refinement or distributed schema negotiation gains authority.
// - Merge-When:
//   - One aggregation lifecycle owns schema selection and merging atomically.
// - Summary:
//   - Removes existing interior bounds without changing latency evidence.
// - Description:
//   - Target bounds must be an ordered source subset with the same final bound.
// - Usage:
//   - Normalize finer histograms before exact same-schema aggregation.
// - Defaults:
//   - Same-schema coarsening is an exact identity transformation.
//

//! Exact schema coarsening for cached-retry latency histograms.

use super::{
    NativeContinuationCachedRetryLatencyHistogram,
    NativeContinuationCachedRetryLatencyHistogramError,
    NativeContinuationCachedRetryLatencyHistogramSnapshot,
    NativeContinuationCachedRetryLatencySnapshotCounts,
    NativeContinuationCachedRetryLatencySnapshotError,
    NativeContinuationCachedRetryLatencySnapshotRange,
};

/// Why exact latency histogram coarsening failed without source mutation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryLatencyCoarseningError {
    /// One requested target bound does not exist in the source schema.
    BoundMissing {
        /// Zero-based target bound index.
        index: usize,
        /// Requested target bound absent from the source schema.
        bound: u64,
    },
    /// Grouping source bucket counts exceeded the target count representation.
    BucketCountOverflow {
        /// Zero-based target bucket whose exact sum overflowed.
        bucket: usize,
    },
    /// Target final bound differs, which would change overflow-bin semantics.
    FinalBoundMismatch {
        /// Final inclusive source bound.
        source: u64,
        /// Requested final inclusive target bound.
        target: u64,
    },
    /// Reconstructed exact evidence unexpectedly failed snapshot validation.
    Snapshot(Box<NativeContinuationCachedRetryLatencySnapshotError>),
    /// Requested target bounds are empty or not strictly increasing.
    TargetBounds(NativeContinuationCachedRetryLatencyHistogramError),
}

/// Exact result of one latency histogram schema coarsening.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryLatencyCoarsening {
    histogram: NativeContinuationCachedRetryLatencyHistogram,
    source_bound_count: usize,
    target_bound_count: usize,
}

impl NativeContinuationCachedRetryLatencyCoarsening {
    /// Borrows the exact coarsened histogram.
    #[must_use]
    pub const fn histogram(
        &self,
    ) -> &NativeContinuationCachedRetryLatencyHistogram {
        &self.histogram
    }

    /// Consumes this transition into the exact coarsened histogram.
    #[must_use]
    pub fn into_histogram(
        self,
    ) -> NativeContinuationCachedRetryLatencyHistogram {
        self.histogram
    }

    /// Returns the number of interior bounds removed by this transition.
    #[must_use]
    pub const fn removed_bounds(&self) -> usize {
        self.source_bound_count
            .saturating_sub(self.target_bound_count)
    }

    /// Returns the source inclusive-bound count.
    #[must_use]
    pub const fn source_bound_count(&self) -> usize {
        self.source_bound_count
    }

    /// Returns the target inclusive-bound count.
    #[must_use]
    pub const fn target_bound_count(&self) -> usize {
        self.target_bound_count
    }
}

/// Coarsens one histogram exactly by removing only existing interior bounds.
///
/// # Errors
///
/// Rejects invalid target bounds, absent source boundaries, changed overflow
/// semantics, count overflow, or impossible reconstructed evidence.
pub fn coarsen_cached_retry_latency_histogram(
    source: &NativeContinuationCachedRetryLatencyHistogram,
    target_upper_bounds: Vec<u64>,
) -> Result<
    NativeContinuationCachedRetryLatencyCoarsening,
    NativeContinuationCachedRetryLatencyCoarseningError,
> {
    super::telemetry_latency::validate_latency_bounds(&target_upper_bounds)
        .map_err(
            NativeContinuationCachedRetryLatencyCoarseningError::TargetBounds,
        )?;
    let source_final = source.upper_bounds().last().copied().ok_or(
        NativeContinuationCachedRetryLatencyCoarseningError::TargetBounds(
            NativeContinuationCachedRetryLatencyHistogramError::BoundsEmpty,
        ),
    )?;
    let target_final = target_upper_bounds.last().copied().ok_or(
        NativeContinuationCachedRetryLatencyCoarseningError::TargetBounds(
            NativeContinuationCachedRetryLatencyHistogramError::BoundsEmpty,
        ),
    )?;
    if source_final != target_final {
        return Err(
            NativeContinuationCachedRetryLatencyCoarseningError::
                FinalBoundMismatch {
                    source: source_final,
                    target: target_final,
                },
        );
    }
    let buckets = coarsen_bucket_counts(source, &target_upper_bounds)?;
    let target_upper_bounds_len = target_upper_bounds.len();
    let snapshot = NativeContinuationCachedRetryLatencyHistogramSnapshot::new(
        target_upper_bounds,
        NativeContinuationCachedRetryLatencySnapshotCounts::new(
            buckets,
            source.above_maximum(),
            source.samples(),
        ),
        NativeContinuationCachedRetryLatencySnapshotRange::new(
            source.minimum_nanoseconds(),
            source.maximum_nanoseconds(),
            source.total_nanoseconds(),
        ),
    );
    let histogram =
        NativeContinuationCachedRetryLatencyHistogram::from_snapshot(snapshot)
            .map_err(|error| {
                NativeContinuationCachedRetryLatencyCoarseningError::Snapshot(
                    Box::new(error),
                )
            })?;
    Ok(NativeContinuationCachedRetryLatencyCoarsening {
        histogram,
        source_bound_count: source.upper_bounds().len(),
        target_bound_count: target_upper_bounds_len,
    })
}

fn coarsen_bucket_counts(
    source: &NativeContinuationCachedRetryLatencyHistogram,
    target_upper_bounds: &[u64],
) -> Result<Vec<usize>, NativeContinuationCachedRetryLatencyCoarseningError> {
    let mut buckets = Vec::with_capacity(target_upper_bounds.len());
    let mut source_index = 0;
    for (target_index, &target_bound) in target_upper_bounds.iter().enumerate()
    {
        let mut count = 0usize;
        loop {
            let Some(&source_bound) = source.upper_bounds().get(source_index)
            else {
                return Err(
                    NativeContinuationCachedRetryLatencyCoarseningError::
                        BoundMissing {
                            index: target_index,
                            bound: target_bound,
                        },
                );
            };
            if source_bound > target_bound {
                return Err(
                    NativeContinuationCachedRetryLatencyCoarseningError::
                        BoundMissing {
                            index: target_index,
                            bound: target_bound,
                        },
                );
            }
            let source_count = source
                .bucket_counts()
                .get(source_index)
                .copied()
                .unwrap_or(0);
            count = count.checked_add(source_count).ok_or(
                NativeContinuationCachedRetryLatencyCoarseningError::
                    BucketCountOverflow {
                        bucket: target_index,
                    },
            )?;
            source_index = source_index.checked_add(1).ok_or(
                NativeContinuationCachedRetryLatencyCoarseningError::
                    BucketCountOverflow {
                        bucket: target_index,
                    },
            )?;
            if source_bound == target_bound {
                buckets.push(count);
                break;
            }
        }
    }
    Ok(buckets)
}
