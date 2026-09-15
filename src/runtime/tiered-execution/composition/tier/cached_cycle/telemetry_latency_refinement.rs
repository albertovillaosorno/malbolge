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
//   - Exact latency-schema refinement from caller-supplied sample evidence.
// - Must-Not:
//   - Infer within-bucket distribution, read clocks, persist, or mutate source.
// - Allows:
//   - Inputs: one source histogram, finer bounds, and exact sample witness.
//   - Outputs: exact refined histogram or stable witness/schema rejection.
//   - Side effects: owned process-local allocation only.
// - Split-When:
//   - Approximate rebinning or compressed sample sketches gain authority.
// - Merge-When:
//   - One aggregation lifecycle retains exact samples with histogram state.
// - Summary:
//   - Refines only when supplied samples exactly reproduce coarse evidence.
// - Description:
//   - Candidate refinement must coarsen back to complete source equality.
// - Usage:
//   - Supply retained exact samples when a finer schema is required later.
// - Defaults:
//   - Histogram evidence without a sample witness cannot be refined.
//

//! Exact sample-witness refinement for cached-retry latency histograms.

use super::{
    NativeContinuationCachedRetryLatencyCoarseningError,
    NativeContinuationCachedRetryLatencyHistogram,
    NativeContinuationCachedRetryLatencyHistogramError,
    NativeContinuationCachedRetryLatencySample,
    coarsen_cached_retry_latency_histogram,
};

/// Why exact sample-witness latency refinement failed closed.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryLatencyRefinementError {
    /// Candidate finer schema could not coarsen exactly to the source schema.
    Coarsening(NativeContinuationCachedRetryLatencyCoarseningError),
    /// Recording one supplied exact sample failed before refinement
    /// publication.
    Sample {
        /// Zero-based witness sample index.
        index: usize,
        /// Exact histogram transition failure.
        error: NativeContinuationCachedRetryLatencyHistogramError,
    },
    /// Candidate finer bounds were empty or not strictly increasing.
    TargetBounds(NativeContinuationCachedRetryLatencyHistogramError),
    /// Supplied samples produced different complete source histogram evidence.
    WitnessMismatch {
        /// Exact source-schema histogram reconstructed from supplied samples.
        reconstructed: Box<NativeContinuationCachedRetryLatencyHistogram>,
    },
}

/// Exact result of one sample-witness latency histogram refinement.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryLatencyRefinement {
    histogram: NativeContinuationCachedRetryLatencyHistogram,
    source_bound_count: usize,
    witness_samples: usize,
}

impl NativeContinuationCachedRetryLatencyRefinement {
    /// Returns the number of finer interior bounds added by this refinement.
    #[must_use]
    pub fn added_bounds(&self) -> usize {
        self.histogram
            .upper_bounds()
            .len()
            .saturating_sub(self.source_bound_count)
    }

    /// Borrows the exact refined histogram.
    #[must_use]
    pub const fn histogram(
        &self,
    ) -> &NativeContinuationCachedRetryLatencyHistogram {
        &self.histogram
    }

    /// Consumes refinement evidence into the exact finer histogram.
    #[must_use]
    pub fn into_histogram(
        self,
    ) -> NativeContinuationCachedRetryLatencyHistogram {
        self.histogram
    }

    /// Returns the exact number of supplied witness samples.
    #[must_use]
    pub const fn witness_samples(&self) -> usize {
        self.witness_samples
    }
}

/// Refines one histogram only from complete caller-supplied sample evidence.
///
/// # Errors
///
/// Rejects invalid finer bounds, failed sample recording, schemas that cannot
/// coarsen to the source, or witnesses whose complete coarsened state differs
/// from the source histogram.
pub fn refine_cached_retry_latency_histogram(
    source: &NativeContinuationCachedRetryLatencyHistogram,
    target_upper_bounds: Vec<u64>,
    witness: &[NativeContinuationCachedRetryLatencySample],
) -> Result<
    NativeContinuationCachedRetryLatencyRefinement,
    NativeContinuationCachedRetryLatencyRefinementError,
> {
    let mut histogram = NativeContinuationCachedRetryLatencyHistogram::new(
        target_upper_bounds,
    )
    .map_err(
        NativeContinuationCachedRetryLatencyRefinementError::TargetBounds,
    )?;
    for (index, &sample) in witness.iter().enumerate() {
        let _record = histogram.record(sample).map_err(|error| {
            NativeContinuationCachedRetryLatencyRefinementError::Sample {
                index,
                error,
            }
        })?;
    }
    let reconstructed = coarsen_cached_retry_latency_histogram(
        &histogram,
        source.upper_bounds().to_vec(),
    )
    .map_err(NativeContinuationCachedRetryLatencyRefinementError::Coarsening)?
    .into_histogram();
    if reconstructed != *source {
        return Err(
            NativeContinuationCachedRetryLatencyRefinementError::
                WitnessMismatch {
                    reconstructed: Box::new(reconstructed),
                },
        );
    }
    Ok(NativeContinuationCachedRetryLatencyRefinement {
        histogram,
        source_bound_count: source.upper_bounds().len(),
        witness_samples: witness.len(),
    })
}
