// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Typed durable compare-and-swap publication of active dispatch-policy
//     state.
// - Must-Not:
//   - Infer policy, choose storage paths, skip revisions, or mutate requests.
// - Allows:
//   - Inputs: expected active state, candidate policy, bound, conditional
//     store.
//   - Outputs: exact conflict state, durable commit, committed sync failure, or
//     typed prepublication failure.
//   - Side effects: delegated conditional publication and durability check
//     only.
// - Split-When:
//   - Distributed consensus or multi-policy transactions gain authority.
// - Merge-When:
//   - One dispatch orchestrator owns durable CAS and request binding.
// - Summary:
//   - Publishes revisioned active policy through canonical conditional bytes.
// - Description:
//   - Missing expected state initializes revision zero; present state advances
//     through the existing owner transition exactly once.
// - Usage:
//   - Supply last observed state, or `None` for initialization, plus candidate.
// - Defaults:
//   - Missing/different durable state is conflict evidence, never overwrite.
//

//! Typed durable CAS for one revisioned active synchronous dispatch policy.

use std::num::NonZeroUsize;

use crate::blob_persistence::{
    NativeContinuationBlobConditionalDurablePersistence as BlobCasDurable,
    NativeContinuationBlobPersistenceError, compare_and_swap_blob_durably,
};
use crate::blob_store::{
    NativeContinuationBlobStore as BlobStore,
    NativeContinuationConditionalBlobStore as ConditionalBlobStore,
    NativeContinuationDurableBlobStore as DurableBlobStore,
};
use crate::continuation_dispatch_policy::NativeContinuationDispatchPolicy;
use crate::continuation_dispatch_policy_owner::{
    NativeContinuationDispatchPolicyOwnerError,
    NativeContinuationDispatchPolicyRevision,
    NativeContinuationDispatchPolicyState,
};
use crate::continuation_dispatch_policy_state_codec::{
    NativeContinuationDispatchPolicyStateCodecError,
    decode_native_continuation_dispatch_policy_state,
    encode_native_continuation_dispatch_policy_state,
};

/// Typed outcome of one durable active-policy compare-and-swap publication.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyStateCas<DurabilityError> {
    /// Durable bytes differed from expected active state.
    Conflict {
        /// Candidate policy that was not published.
        candidate: NativeContinuationDispatchPolicy,
        /// Exact bounded current durable state, or `None` when missing.
        current: Option<NativeContinuationDispatchPolicyState>,
        /// Caller-supplied expected state used for canonical comparison.
        expected: Option<NativeContinuationDispatchPolicyState>,
    },
    /// Candidate state committed and durability confirmation completed.
    Durable {
        /// Exact canonical state byte count committed by the store.
        bytes: usize,
        /// Exact active state published by this operation.
        current: NativeContinuationDispatchPolicyState,
        /// Exact prior state, or `None` for revision-zero initialization.
        previous: Option<NativeContinuationDispatchPolicyState>,
    },
    /// Candidate state committed, then durability confirmation failed.
    Published {
        /// Exact canonical state byte count committed by the store.
        bytes: usize,
        /// Exact active state published by this operation.
        current: NativeContinuationDispatchPolicyState,
        /// Exact post-publication durability failure.
        durability_error: DurabilityError,
        /// Exact prior state, or `None` for revision-zero initialization.
        previous: Option<NativeContinuationDispatchPolicyState>,
    },
}

/// Why typed durable active-policy CAS failed before returning an outcome.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyStateCasError<StoreError> {
    /// Bounded conditional blob orchestration or outbound store failed.
    Blob(NativeContinuationBlobPersistenceError<StoreError>),
    /// Canonical active-policy state framing or semantics failed.
    Codec(NativeContinuationDispatchPolicyStateCodecError),
    /// Expected state could not advance exactly one revision.
    Owner(NativeContinuationDispatchPolicyOwnerError),
}

/// Result of one typed durable active-policy CAS operation.
pub type NativeContinuationDispatchPolicyStateCasResult<
    StoreError,
    DurabilityError,
> = Result<
    NativeContinuationDispatchPolicyStateCas<DurabilityError>,
    NativeContinuationDispatchPolicyStateCasError<StoreError>,
>;

/// Typed CAS result specialized to one conditional durable store.
pub type NativeContinuationDispatchPolicyStateCasStoreResult<Store> =
    NativeContinuationDispatchPolicyStateCasResult<
        <Store as BlobStore>::Error,
        <Store as DurableBlobStore>::DurabilityError,
    >;

/// Conditionally publishes one active dispatch policy under revision semantics.
///
/// # Errors
///
/// Returns revision exhaustion, codec rejection, byte-limit failure, or
/// outbound coordination/publication failure before a typed outcome can be
/// returned.
pub fn compare_and_swap_native_continuation_dispatch_policy_state_durably<
    Store,
>(
    store: &mut Store,
    expected: Option<NativeContinuationDispatchPolicyState>,
    candidate: NativeContinuationDispatchPolicy,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationDispatchPolicyStateCasStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    let candidate_state = derive_candidate_state(expected, candidate)
        .map_err(NativeContinuationDispatchPolicyStateCasError::Owner)?;
    let expected_bytes = expected
        .map(encode_native_continuation_dispatch_policy_state)
        .transpose()
        .map_err(NativeContinuationDispatchPolicyStateCasError::Codec)?;
    let candidate_bytes =
        encode_native_continuation_dispatch_policy_state(candidate_state)
            .map_err(NativeContinuationDispatchPolicyStateCasError::Codec)?;
    let outcome = compare_and_swap_blob_durably(
        store,
        expected_bytes.as_deref(),
        &candidate_bytes,
        maximum_bytes,
    )
    .map_err(NativeContinuationDispatchPolicyStateCasError::Blob)?;
    match outcome {
        BlobCasDurable::Conflict { current: current_bytes } => {
            let current = current_bytes
                .as_deref()
                .map(decode_native_continuation_dispatch_policy_state)
                .transpose()
                .map_err(
                    NativeContinuationDispatchPolicyStateCasError::Codec,
                )?;
            Ok(NativeContinuationDispatchPolicyStateCas::Conflict {
                candidate,
                current,
                expected,
            })
        },
        BlobCasDurable::Durable { write } => {
            Ok(NativeContinuationDispatchPolicyStateCas::Durable {
                bytes: write.bytes(),
                current: candidate_state,
                previous: expected,
            })
        },
        BlobCasDurable::Published { durability_error, write } => {
            Ok(NativeContinuationDispatchPolicyStateCas::Published {
                bytes: write.bytes(),
                current: candidate_state,
                durability_error,
                previous: expected,
            })
        },
    }
}

fn derive_candidate_state(
    expected: Option<NativeContinuationDispatchPolicyState>,
    candidate: NativeContinuationDispatchPolicy,
) -> Result<
    NativeContinuationDispatchPolicyState,
    NativeContinuationDispatchPolicyOwnerError,
> {
    expected.map_or_else(
        || {
            Ok(NativeContinuationDispatchPolicyState::new(
                candidate,
                NativeContinuationDispatchPolicyRevision::initial(),
            ))
        },
        |previous| previous.next(candidate),
    )
}
