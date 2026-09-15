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
    NativeContinuationCachedRetryLatencyMergeError,
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

/// Why exact normalized latency merge failed without mutating either source.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryLatencyNormalizedMergeError {
    /// Greatest exact shared schema could not be derived.
    Common(NativeContinuationCachedRetryLatencyCommonCoarseningError),
    /// Left histogram could not be coarsened to the shared schema.
    Left(NativeContinuationCachedRetryLatencyCoarseningError),
    /// Coarsened histograms could not be merged transactionally.
    Merge(NativeContinuationCachedRetryLatencyMergeError),
    /// Right histogram could not be coarsened to the shared schema.
    Right(NativeContinuationCachedRetryLatencyCoarseningError),
}

/// Exact merged histogram plus normalization evidence for both sources.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryLatencyNormalizedMerge {
    histogram: NativeContinuationCachedRetryLatencyHistogram,
    left_removed_bounds: usize,
    right_removed_bounds: usize,
}

/// Why two histograms cannot share one exact coarsened schema.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryLatencyCommonCoarseningError {
    /// Final inclusive bounds differ, so overflow semantics are incompatible.
    FinalBoundMismatch {
        /// Final inclusive left-histogram bound.
        left: u64,
        /// Final inclusive right-histogram bound.
        right: u64,
    },
    /// Left histogram unexpectedly has no inclusive bounds.
    LeftBoundsEmpty,
    /// Right histogram unexpectedly has no inclusive bounds.
    RightBoundsEmpty,
}

/// Exact common schema derivation for two latency histograms.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryLatencyCommonCoarsening {
    left_bound_count: usize,
    right_bound_count: usize,
    upper_bounds: Vec<u64>,
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

impl NativeContinuationCachedRetryLatencyNormalizedMerge {
    /// Borrows the exact merged histogram on the shared schema.
    #[must_use]
    pub const fn histogram(
        &self,
    ) -> &NativeContinuationCachedRetryLatencyHistogram {
        &self.histogram
    }

    /// Consumes merge evidence into the exact merged histogram.
    #[must_use]
    pub fn into_histogram(
        self,
    ) -> NativeContinuationCachedRetryLatencyHistogram {
        self.histogram
    }

    /// Returns how many left-side bounds normalization removed.
    #[must_use]
    pub const fn left_removed_bounds(&self) -> usize {
        self.left_removed_bounds
    }

    /// Returns how many right-side bounds normalization removed.
    #[must_use]
    pub const fn right_removed_bounds(&self) -> usize {
        self.right_removed_bounds
    }
}

impl NativeContinuationCachedRetryLatencyCommonCoarsening {
    /// Returns how many left-side interior bounds normalization removes.
    #[must_use]
    pub const fn left_removed_bounds(&self) -> usize {
        self.left_bound_count
            .saturating_sub(self.upper_bounds.len())
    }

    /// Returns how many right-side interior bounds normalization removes.
    #[must_use]
    pub const fn right_removed_bounds(&self) -> usize {
        self.right_bound_count
            .saturating_sub(self.upper_bounds.len())
    }

    /// Returns the exact ordered bounds shared by both source schemas.
    #[must_use]
    pub fn upper_bounds(&self) -> &[u64] {
        &self.upper_bounds
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

/// Normalizes two compatible schemas and merges their evidence exactly.
///
/// # Errors
///
/// Returns exact shared-schema, coarsening, or transactional merge failure.
pub fn merge_cached_retry_latency_histograms_exact(
    left: &NativeContinuationCachedRetryLatencyHistogram,
    right: &NativeContinuationCachedRetryLatencyHistogram,
) -> Result<
    NativeContinuationCachedRetryLatencyNormalizedMerge,
    NativeContinuationCachedRetryLatencyNormalizedMergeError,
> {
    let common = derive_common_cached_retry_latency_coarsening(left, right)
        .map_err(
            NativeContinuationCachedRetryLatencyNormalizedMergeError::Common,
        )?;
    let left_removed_bounds = common.left_removed_bounds();
    let right_removed_bounds = common.right_removed_bounds();
    let mut merged = coarsen_cached_retry_latency_histogram(
        left,
        common.upper_bounds().to_vec(),
    )
    .map_err(NativeContinuationCachedRetryLatencyNormalizedMergeError::Left)?
    .into_histogram();
    let normalized_right = coarsen_cached_retry_latency_histogram(
        right,
        common.upper_bounds().to_vec(),
    )
    .map_err(NativeContinuationCachedRetryLatencyNormalizedMergeError::Right)?
    .into_histogram();
    let _record = merged.merge(&normalized_right).map_err(
        NativeContinuationCachedRetryLatencyNormalizedMergeError::Merge,
    )?;
    Ok(NativeContinuationCachedRetryLatencyNormalizedMerge {
        histogram: merged,
        left_removed_bounds,
        right_removed_bounds,
    })
}

/// Derives the greatest exact coarsened schema shared by two histograms.
///
/// # Errors
///
/// Rejects differing final bounds because one common overflow bin could not
/// preserve both source semantics exactly.
pub fn derive_common_cached_retry_latency_coarsening(
    left: &NativeContinuationCachedRetryLatencyHistogram,
    right: &NativeContinuationCachedRetryLatencyHistogram,
) -> Result<
    NativeContinuationCachedRetryLatencyCommonCoarsening,
    NativeContinuationCachedRetryLatencyCommonCoarseningError,
> {
    let left_final = left.upper_bounds().last().copied().ok_or(
        NativeContinuationCachedRetryLatencyCommonCoarseningError::
            LeftBoundsEmpty,
    )?;
    let right_final = right.upper_bounds().last().copied().ok_or(
        NativeContinuationCachedRetryLatencyCommonCoarseningError::
            RightBoundsEmpty,
    )?;
    if left_final != right_final {
        return Err(
            NativeContinuationCachedRetryLatencyCommonCoarseningError::
                FinalBoundMismatch {
                    left: left_final,
                    right: right_final,
                },
        );
    }
    let upper_bounds = left
        .upper_bounds()
        .iter()
        .copied()
        .filter(|bound| right.upper_bounds().binary_search(bound).is_ok())
        .collect::<Vec<_>>();
    Ok(NativeContinuationCachedRetryLatencyCommonCoarsening {
        left_bound_count: left.upper_bounds().len(),
        right_bound_count: right.upper_bounds().len(),
        upper_bounds,
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
