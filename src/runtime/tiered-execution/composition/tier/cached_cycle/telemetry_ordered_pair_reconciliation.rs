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
//   - One-shot reconciliation and durable CAS of ordered count plus latency.
// - Must-Not:
//   - Invent external order, retry conflict, sleep, or infer merge schemas.
// - Allows:
//   - Inputs: ordered count batch, latency delta, missing capacity, bounds,
//     store.
//   - Outputs: typed conflict, durable commit, committed sync failure, or
//     error.
//   - Side effects: one versioned load and at most one conditional publication.
// - Split-When:
//   - Conflict retry/backoff or distributed ordering service gains authority.
// - Merge-When:
//   - One distributed telemetry owner subsumes reconciliation and retry.
// - Summary:
//   - Reconciles caller-ordered count and exact latency deltas before one CAS.
// - Description:
//   - Current durable state remains authoritative and is never overwritten
//     blind.
// - Usage:
//   - Submit one external count order plus the latency evidence for that batch.
// - Defaults:
//   - Missing state uses caller capacity; conflict never retries automatically.
//

//! One-shot ordered count plus latency reconciliation with durable pair CAS.

use std::num::NonZeroUsize;

use pair_port::{
    NativeContinuationBlobPairStore as PairStore,
    NativeContinuationConditionalBlobPairStore as ConditionalPairStore,
    NativeContinuationDurableBlobPairStore as DurablePairStore,
};

use super::{
    NativeContinuationCachedRetryLatencyHistogram,
    NativeContinuationCachedRetryLatencyNormalizedMergeError,
    NativeContinuationCachedRetryTelemetry,
    NativeContinuationCachedRetryTelemetryBatchOrder,
    NativeContinuationCachedRetryTelemetryOrderedPairPersistenceError,
    NativeContinuationCachedRetryTelemetryOrderedWindow,
    NativeContinuationCachedRetryTelemetryOrderedWindowAppend,
    NativeContinuationCachedRetryTelemetryOrderedWindowError,
    NativeContinuationCachedRetryTelemetryWindow,
    encode_cached_retry_latency_snapshot as encode_latency,
    encode_cached_retry_telemetry_ordered_state as encode_ordered,
    merge_cached_retry_latency_histograms_exact,
    telemetry_ordered_pair_persistence as ordered_pair,
};
use crate::{
    blob_pair_persistence as pair_persistence, blob_pair_store as pair_port,
};

/// Immutable request for one ordered telemetry-pair reconciliation attempt.
#[derive(Clone, Copy, Debug)]
pub struct NativeContinuationCachedRetryOrderedPairReconciliationRequest<'state>
{
    count_maximum_bytes: NonZeroUsize,
    initial_capacity: NonZeroUsize,
    latency: &'state NativeContinuationCachedRetryLatencyHistogram,
    latency_maximum_bytes: NonZeroUsize,
    order: NativeContinuationCachedRetryTelemetryBatchOrder,
    telemetry: &'state [NativeContinuationCachedRetryTelemetry],
}

impl<'state>
    NativeContinuationCachedRetryOrderedPairReconciliationRequest<'state>
{
    /// Constructs one explicit ordered reconciliation request.
    #[must_use]
    pub const fn new(
        ordering: (
            NonZeroUsize,
            NativeContinuationCachedRetryTelemetryBatchOrder,
        ),
        telemetry: &'state [NativeContinuationCachedRetryTelemetry],
        latency: &'state NativeContinuationCachedRetryLatencyHistogram,
        maximum_bytes: (NonZeroUsize, NonZeroUsize),
    ) -> Self {
        let (initial_capacity, order) = ordering;
        let (count_maximum_bytes, latency_maximum_bytes) = maximum_bytes;
        Self {
            count_maximum_bytes,
            initial_capacity,
            latency,
            latency_maximum_bytes,
            order,
            telemetry,
        }
    }
}

/// Exact typed ordered telemetry pair observed at one opaque revision.
#[derive(Clone, Debug)]
pub struct NativeContinuationCachedRetryOrderedPairVersionedState<Revision> {
    histogram: Box<NativeContinuationCachedRetryLatencyHistogram>,
    ordered: Box<NativeContinuationCachedRetryTelemetryOrderedWindow>,
    revision: Revision,
}

/// Typed outcome of one ordered pair reconciliation attempt.
#[derive(Debug)]
pub enum NativeContinuationCachedRetryOrderedPairReconciliation<
    Revision,
    DurabilityError,
> {
    /// State changed after reconciliation and before conditional publication.
    Conflict {
        /// Complete current typed pair plus newer revision, or missing state.
        current: Option<
            Box<
                NativeContinuationCachedRetryOrderedPairVersionedState<
                    Revision,
                >,
            >,
        >,
        /// Revision reconciled by this attempt, or missing-state expectation.
        expected: Option<Revision>,
    },
    /// Reconciled pair committed and durability confirmation completed.
    Durable {
        /// Exact typed pair now published under its fresh revision.
        current: Box<
            NativeContinuationCachedRetryOrderedPairVersionedState<Revision>,
        >,
        /// Exact ordered count append evidence included in the commit.
        publication: NativeContinuationCachedRetryTelemetryOrderedWindowAppend,
    },
    /// Reconciled pair committed, then durability confirmation failed.
    Published {
        /// Exact typed pair now process-visible under its fresh revision.
        current: Box<
            NativeContinuationCachedRetryOrderedPairVersionedState<Revision>,
        >,
        /// Exact post-publication durability failure.
        durability_error: DurabilityError,
        /// Exact ordered count append evidence included in the commit.
        publication: NativeContinuationCachedRetryTelemetryOrderedWindowAppend,
    },
}

/// Why ordered pair reconciliation failed before a typed outcome.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryOrderedPairReconciliationError<StoreError>
{
    /// Exact latency normalization or merge failed.
    Latency(Box<NativeContinuationCachedRetryLatencyNormalizedMergeError>),
    /// Ordered count append rejected stale order or failed transactionally.
    Ordered(NativeContinuationCachedRetryTelemetryOrderedWindowError),
    /// Pair storage, bounds, codec, or reconstruction failed.
    Pair(
        NativeContinuationCachedRetryTelemetryOrderedPairPersistenceError<
            StoreError,
        >,
    ),
}

/// Ordered pair reconciliation result specialized to one durable store.
pub type NativeContinuationCachedRetryOrderedPairReconciliationStoreResult<
    Store,
> = Result<
    NativeContinuationCachedRetryOrderedPairReconciliation<
        <Store as ConditionalPairStore>::Revision,
        <Store as DurablePairStore>::DurabilityError,
    >,
    NativeContinuationCachedRetryOrderedPairReconciliationError<
        <Store as PairStore>::Error,
    >,
>;

type AppCas<Revision, DurabilityError> =
    pair_persistence::NativeContinuationBlobPairConditionalDurablePersistence<
        Revision,
        DurabilityError,
    >;
type PairError<StoreError> =
    NativeContinuationCachedRetryTelemetryOrderedPairPersistenceError<
        StoreError,
    >;
type ReconcileError<StoreError> =
    NativeContinuationCachedRetryOrderedPairReconciliationError<StoreError>;
type ReconcileRequest<'state> =
    NativeContinuationCachedRetryOrderedPairReconciliationRequest<'state>;
type ReconcileState<Revision> =
    NativeContinuationCachedRetryOrderedPairVersionedState<Revision>;
type ReconcileOutcome<Revision, DurabilityError> =
    NativeContinuationCachedRetryOrderedPairReconciliation<
        Revision,
        DurabilityError,
    >;
type DecodeResult<Revision, StoreError> =
    Result<ReconcileState<Revision>, ReconcileError<StoreError>>;
type MapResult<Revision, StoreError, DurabilityError> = Result<
    ReconcileOutcome<Revision, DurabilityError>,
    ReconcileError<StoreError>,
>;

struct ReconciledCandidate<Revision> {
    expected: Option<Revision>,
    histogram: NativeContinuationCachedRetryLatencyHistogram,
    ordered: NativeContinuationCachedRetryTelemetryOrderedWindow,
    publication: NativeContinuationCachedRetryTelemetryOrderedWindowAppend,
}

impl<Revision>
    NativeContinuationCachedRetryOrderedPairVersionedState<Revision>
{
    /// Borrows the exact reconciled latency histogram.
    #[must_use]
    pub const fn histogram(
        &self,
    ) -> &NativeContinuationCachedRetryLatencyHistogram {
        &self.histogram
    }

    /// Borrows the exact ordered count owner.
    #[must_use]
    pub const fn ordered(
        &self,
    ) -> &NativeContinuationCachedRetryTelemetryOrderedWindow {
        &self.ordered
    }

    /// Borrows the opaque publication revision.
    #[must_use]
    pub const fn revision(&self) -> &Revision {
        &self.revision
    }
}

/// Reconciles one caller-ordered count batch and latency delta, then CASes
/// once.
///
/// # Errors
///
/// Returns stale-order, transactional count, exact latency merge, codec,
/// byte-limit, or pair-store failure. Concurrent publication is typed conflict
/// evidence and is never retried automatically.
pub fn reconcile_cached_retry_telemetry_ordered_pair_durably<Store>(
    store: &mut Store,
    request: ReconcileRequest<'_>,
) -> NativeContinuationCachedRetryOrderedPairReconciliationStoreResult<Store>
where
    Store: ConditionalPairStore + DurablePairStore,
{
    let load = pair_persistence::restore_blob_pair_versioned(
        store,
        request.count_maximum_bytes,
        request.latency_maximum_bytes,
    )
    .map_err(|error| ReconcileError::Pair(PairError::Pair(error)))?;
    let (expected, mut ordered, current_histogram) = match load {
        None => (
            None,
            NativeContinuationCachedRetryTelemetryOrderedWindow::new(
                NativeContinuationCachedRetryTelemetryWindow::new(
                    request.initial_capacity,
                ),
            ),
            request.latency.clone(),
        ),
        Some(value) => {
            let decoded = decode_versioned(value)?;
            let revision = decoded.revision.clone();
            (Some(revision), *decoded.ordered, *decoded.histogram)
        },
    };
    let publication = ordered
        .append_ordered_batch(request.order, request.telemetry)
        .map_err(ReconcileError::Ordered)?;
    let reconciled_histogram = if expected.is_none() {
        current_histogram
    } else {
        merge_cached_retry_latency_histograms_exact(
            &current_histogram,
            request.latency,
        )
        .map_err(|error| ReconcileError::Latency(Box::new(error)))?
        .into_histogram()
    };
    let count = encode_ordered(&ordered).map_err(|error| {
        ReconcileError::Pair(PairError::OrderedCodec(Box::new(error)))
    })?;
    let latency =
        encode_latency(&reconciled_histogram.snapshot()).map_err(|error| {
            ReconcileError::Pair(PairError::LatencyCodec(Box::new(error)))
        })?;
    let outcome = pair_persistence::compare_and_swap_blob_pair_durably(
        store,
        expected.as_ref(),
        pair_persistence::NativeContinuationBlobPairPersistenceRequest::new(
            &count,
            &latency,
            request.count_maximum_bytes,
            request.latency_maximum_bytes,
        ),
    )
    .map_err(|error| ReconcileError::Pair(PairError::Pair(error)))?;
    map_outcome(outcome, ReconciledCandidate {
        expected,
        histogram: reconciled_histogram,
        ordered,
        publication,
    })
}

fn decode_versioned<Revision, StoreError>(
    value: pair_persistence::NativeContinuationBlobPairVersionedLoad<Revision>,
) -> DecodeResult<Revision, StoreError> {
    let decoded = ordered_pair::decode_cached_retry_telemetry_ordered_pair(
        &value.first,
        &value.second,
    )
    .map_err(ReconcileError::Pair)?;
    Ok(ReconcileState {
        histogram: Box::new(decoded.histogram),
        ordered: Box::new(decoded.ordered),
        revision: value.revision,
    })
}

fn map_outcome<Revision, StoreError, DurabilityError>(
    outcome: AppCas<Revision, DurabilityError>,
    candidate: ReconciledCandidate<Revision>,
) -> MapResult<Revision, StoreError, DurabilityError>
where
    Revision: Clone,
{
    match outcome {
        AppCas::Conflict { current: current_load } => {
            let current_state = current_load
                .map(decode_versioned)
                .transpose()?
                .map(Box::new);
            Ok(ReconcileOutcome::Conflict {
                current: current_state,
                expected: candidate.expected,
            })
        },
        AppCas::Durable { revision, .. } => Ok(ReconcileOutcome::Durable {
            current: Box::new(ReconcileState {
                histogram: Box::new(candidate.histogram),
                ordered: Box::new(candidate.ordered),
                revision,
            }),
            publication: candidate.publication,
        }),
        AppCas::Published {
            durability_error,
            revision,
            ..
        } => Ok(ReconcileOutcome::Published {
            current: Box::new(ReconcileState {
                histogram: Box::new(candidate.histogram),
                ordered: Box::new(candidate.ordered),
                revision,
            }),
            durability_error,
            publication: candidate.publication,
        }),
    }
}
