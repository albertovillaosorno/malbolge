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
//   - Typed one-shot durable CAS for canonical count plus latency telemetry.
// - Must-Not:
//   - Retry conflicts, merge/rebase telemetry, infer revisions, or choose
//     paths.
// - Allows:
//   - Inputs: candidate count/latency owners, expected revision, bounds, store.
//   - Outputs: versioned typed state, conflict, durable commit, or committed
//     durability failure.
//   - Side effects: one versioned load or at most one conditional pair publish.
// - Split-When:
//   - Conflict reconciliation, retry policy, or N-object transactions gain
//     authority.
// - Merge-When:
//   - One cached-cycle transaction owner subsumes pair CAS and reconciliation.
// - Summary:
//   - Conditionally publishes typed count and latency telemetry by opaque
//     revision.
// - Description:
//   - Conflict bytes are decoded back into exact typed owners before return.
// - Usage:
//   - Reuse a revision returned by versioned restore or prior successful CAS.
// - Defaults:
//   - Missing expectation matches only missing state; conflicts never retry.
//

//! Typed one-shot durable CAS for cached-retry count plus latency telemetry.

use std::num::NonZeroUsize;

use pair_port::{
    NativeContinuationBlobPairStore as PairStore,
    NativeContinuationConditionalBlobPairStore as ConditionalPairStore,
    NativeContinuationDurableBlobPairStore as DurablePairStore,
};

use super::telemetry_pair_persistence::decode_cached_retry_telemetry_pair;
use super::{
    NativeContinuationCachedRetryLatencyHistogram,
    NativeContinuationCachedRetryTelemetryPairPersistenceError,
    NativeContinuationCachedRetryTelemetryWindow,
    encode_cached_retry_latency_snapshot as encode_latency,
    encode_cached_retry_telemetry_snapshot as encode_count,
};
use crate::{
    blob_pair_persistence as pair_persistence, blob_pair_store as pair_port,
};

/// Immutable request for one typed revision-conditional pair publication.
#[derive(Clone, Copy, Debug)]
pub struct NativeContinuationCachedRetryTelemetryPairCasRequest<
    'state,
    Revision,
> {
    count_maximum_bytes: NonZeroUsize,
    expected: Option<&'state Revision>,
    histogram: &'state NativeContinuationCachedRetryLatencyHistogram,
    latency_maximum_bytes: NonZeroUsize,
    window: &'state NativeContinuationCachedRetryTelemetryWindow,
}

impl<'state, Revision>
    NativeContinuationCachedRetryTelemetryPairCasRequest<'state, Revision>
{
    /// Constructs one explicit typed one-shot pair CAS request.
    #[must_use]
    pub const fn new(
        expected: Option<&'state Revision>,
        window: &'state NativeContinuationCachedRetryTelemetryWindow,
        histogram: &'state NativeContinuationCachedRetryLatencyHistogram,
        maximum_bytes: (NonZeroUsize, NonZeroUsize),
    ) -> Self {
        let (count_maximum_bytes, latency_maximum_bytes) = maximum_bytes;
        Self {
            count_maximum_bytes,
            expected,
            histogram,
            latency_maximum_bytes,
            window,
        }
    }
}

/// Exact typed telemetry pair observed at one opaque publication revision.
#[derive(Clone, Debug)]
pub struct NativeContinuationCachedRetryTelemetryPairVersionedState<Revision> {
    count_bytes: usize,
    histogram: Box<NativeContinuationCachedRetryLatencyHistogram>,
    latency_bytes: usize,
    revision: Revision,
    window: Box<NativeContinuationCachedRetryTelemetryWindow>,
}

/// Typed result of one durable revision-conditional telemetry pair publication.
#[derive(Debug)]
pub enum NativeContinuationCachedRetryTelemetryPairCas<
    Revision,
    DurabilityError,
> {
    /// Current pair revision differed from the caller expectation.
    Conflict {
        /// Complete current typed pair plus revision, or missing state.
        current: Option<
            Box<
                NativeContinuationCachedRetryTelemetryPairVersionedState<
                    Revision,
                >,
            >,
        >,
        /// Caller-supplied opaque revision expectation, or missing-state
        /// expectation.
        expected: Option<Revision>,
    },
    /// Candidate pair committed and durability confirmation completed.
    Durable {
        /// Exact typed pair now published under the fresh revision.
        current: Box<
            NativeContinuationCachedRetryTelemetryPairVersionedState<Revision>,
        >,
    },
    /// Candidate pair committed, then durability confirmation failed.
    Published {
        /// Exact typed pair now process-visible under the fresh revision.
        current: Box<
            NativeContinuationCachedRetryTelemetryPairVersionedState<Revision>,
        >,
        /// Exact post-publication durability failure.
        durability_error: DurabilityError,
    },
}

/// Typed pair CAS result specialized to one conditional durable pair store.
pub type NativeContinuationCachedRetryTelemetryPairCasStoreResult<Store> =
    Result<
        NativeContinuationCachedRetryTelemetryPairCas<
            <Store as ConditionalPairStore>::Revision,
            <Store as DurablePairStore>::DurabilityError,
        >,
        NativeContinuationCachedRetryTelemetryPairPersistenceError<
            <Store as PairStore>::Error,
        >,
    >;

/// Typed versioned restore result specialized to one conditional pair store.
pub type NativeContinuationCachedRetryTelemetryPairVersionedLoadStoreResult<
    Store,
> = Result<
    Option<
        NativeContinuationCachedRetryTelemetryPairVersionedState<
            <Store as ConditionalPairStore>::Revision,
        >,
    >,
    NativeContinuationCachedRetryTelemetryPairPersistenceError<
        <Store as PairStore>::Error,
    >,
>;

type AppCasDurable<Revision, DurabilityError> =
    pair_persistence::NativeContinuationBlobPairConditionalDurablePersistence<
        Revision,
        DurabilityError,
    >;
type PairError<StoreError> =
    NativeContinuationCachedRetryTelemetryPairPersistenceError<StoreError>;
type PairState<Revision> =
    NativeContinuationCachedRetryTelemetryPairVersionedState<Revision>;
type PairStateResult<Revision, StoreError> =
    Result<PairState<Revision>, PairError<StoreError>>;
type PairCasMapResult<Revision, StoreError, DurabilityError> = Result<
    NativeContinuationCachedRetryTelemetryPairCas<Revision, DurabilityError>,
    PairError<StoreError>,
>;

impl<Revision>
    NativeContinuationCachedRetryTelemetryPairVersionedState<Revision>
{
    /// Returns exact canonical count member byte count.
    #[must_use]
    pub const fn count_bytes(&self) -> usize {
        self.count_bytes
    }

    /// Borrows the exact reconstructed latency histogram.
    #[must_use]
    pub const fn histogram(
        &self,
    ) -> &NativeContinuationCachedRetryLatencyHistogram {
        &self.histogram
    }

    /// Returns exact canonical latency member byte count.
    #[must_use]
    pub const fn latency_bytes(&self) -> usize {
        self.latency_bytes
    }

    /// Borrows the opaque publication revision.
    #[must_use]
    pub const fn revision(&self) -> &Revision {
        &self.revision
    }

    /// Borrows the exact reconstructed count window.
    #[must_use]
    pub const fn window(
        &self,
    ) -> &NativeContinuationCachedRetryTelemetryWindow {
        &self.window
    }
}

/// Conditionally publishes one typed count plus latency telemetry pair.
///
/// # Errors
///
/// Returns codec, reconstruction, byte-limit, or pair-store failure before a
/// typed outcome can be returned. Conflict is explicit and never retried.
pub fn compare_and_swap_cached_retry_telemetry_pair_durably<Store>(
    store: &mut Store,
    request: &NativeContinuationCachedRetryTelemetryPairCasRequest<
        '_,
        Store::Revision,
    >,
) -> NativeContinuationCachedRetryTelemetryPairCasStoreResult<Store>
where
    Store: ConditionalPairStore + DurablePairStore,
{
    let count = encode_count(&request.window.snapshot())
        .map_err(|error| PairError::CountCodec(Box::new(error)))?;
    let latency = encode_latency(&request.histogram.snapshot())
        .map_err(|error| PairError::LatencyCodec(Box::new(error)))?;
    let outcome = pair_persistence::compare_and_swap_blob_pair_durably(
        store,
        request.expected,
        pair_persistence::NativeContinuationBlobPairPersistenceRequest::new(
            &count,
            &latency,
            request.count_maximum_bytes,
            request.latency_maximum_bytes,
        ),
    )
    .map_err(PairError::Pair)?;
    map_cas_outcome(outcome, request, count.len(), latency.len())
}

/// Restores one complete typed pair plus the opaque revision observed with it.
///
/// # Errors
///
/// Returns pair-store, bound, codec, or reconstruction evidence. Missing state
/// remains `None` and invents neither telemetry owner nor revision.
pub fn restore_cached_retry_telemetry_pair_versioned<Store>(
    store: &mut Store,
    count_maximum_bytes: NonZeroUsize,
    latency_maximum_bytes: NonZeroUsize,
) -> NativeContinuationCachedRetryTelemetryPairVersionedLoadStoreResult<Store>
where
    Store: ConditionalPairStore,
{
    let load = pair_persistence::restore_blob_pair_versioned(
        store,
        count_maximum_bytes,
        latency_maximum_bytes,
    )
    .map_err(PairError::Pair)?;
    load.map(decode_versioned_pair).transpose()
}

fn candidate_state<Revision>(
    request: &NativeContinuationCachedRetryTelemetryPairCasRequest<
        '_,
        Revision,
    >,
    revision: Revision,
    count_bytes: usize,
    latency_bytes: usize,
) -> PairState<Revision>
where
    Revision: Clone,
{
    PairState {
        count_bytes,
        histogram: Box::new(request.histogram.clone()),
        latency_bytes,
        revision,
        window: Box::new(request.window.clone()),
    }
}

fn decode_versioned_pair<Revision, StoreError>(
    value: pair_persistence::NativeContinuationBlobPairVersionedLoad<Revision>,
) -> PairStateResult<Revision, StoreError> {
    let decoded =
        decode_cached_retry_telemetry_pair(&value.first, &value.second)?;
    Ok(PairState {
        count_bytes: decoded.count_bytes,
        histogram: Box::new(decoded.histogram),
        latency_bytes: decoded.latency_bytes,
        revision: value.revision,
        window: Box::new(decoded.window),
    })
}

fn map_cas_outcome<Revision, StoreError, DurabilityError>(
    outcome: AppCasDurable<Revision, DurabilityError>,
    request: &NativeContinuationCachedRetryTelemetryPairCasRequest<
        '_,
        Revision,
    >,
    count_bytes: usize,
    latency_bytes: usize,
) -> PairCasMapResult<Revision, StoreError, DurabilityError>
where
    Revision: Clone,
{
    match outcome {
        AppCasDurable::Conflict { current: current_load } => {
            let current_state = current_load
                .map(decode_versioned_pair)
                .transpose()?
                .map(Box::new);
            Ok(NativeContinuationCachedRetryTelemetryPairCas::Conflict {
                current: current_state,
                expected: request.expected.cloned(),
            })
        },
        AppCasDurable::Durable { revision, .. } => {
            Ok(NativeContinuationCachedRetryTelemetryPairCas::Durable {
                current: Box::new(candidate_state(
                    request,
                    revision,
                    count_bytes,
                    latency_bytes,
                )),
            })
        },
        AppCasDurable::Published {
            durability_error,
            revision,
            ..
        } => Ok(NativeContinuationCachedRetryTelemetryPairCas::Published {
            current: Box::new(candidate_state(
                request,
                revision,
                count_bytes,
                latency_bytes,
            )),
            durability_error,
        }),
    }
}
