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
//   - Typed durable compare-and-swap publication of active retry-policy state.
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
//   - One cross-cycle policy orchestrator owns durable CAS and request binding.
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

//! Typed durable CAS for one revisioned active native retry policy.

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
use crate::retry_policy::NativeContinuationRetryPolicy;
use crate::retry_policy_owner::{
    NativeContinuationRetryPolicyOwnerError,
    NativeContinuationRetryPolicyRevision, NativeContinuationRetryPolicyState,
};
use crate::retry_policy_state_codec::{
    NativeContinuationRetryPolicyStateCodecError,
    decode_native_continuation_retry_policy_state,
    encode_native_continuation_retry_policy_state,
};

/// Typed outcome of one durable active-policy compare-and-swap publication.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationRetryPolicyStateCas<DurabilityError> {
    /// Durable bytes differed from expected active state.
    Conflict {
        /// Candidate policy that was not published.
        candidate: NativeContinuationRetryPolicy,
        /// Exact bounded current durable state, or `None` when missing.
        current: Option<NativeContinuationRetryPolicyState>,
        /// Caller-supplied expected state used for canonical comparison.
        expected: Option<NativeContinuationRetryPolicyState>,
    },
    /// Candidate state committed and durability confirmation completed.
    Durable {
        /// Exact canonical state byte count committed by the store.
        bytes: usize,
        /// Exact active state published by this operation.
        current: NativeContinuationRetryPolicyState,
        /// Exact prior state, or `None` for revision-zero initialization.
        previous: Option<NativeContinuationRetryPolicyState>,
    },
    /// Candidate state committed, then durability confirmation failed.
    Published {
        /// Exact canonical state byte count committed by the store.
        bytes: usize,
        /// Exact active state published by this operation.
        current: NativeContinuationRetryPolicyState,
        /// Exact post-publication durability failure.
        durability_error: DurabilityError,
        /// Exact prior state, or `None` for revision-zero initialization.
        previous: Option<NativeContinuationRetryPolicyState>,
    },
}

/// Why typed durable active-policy CAS failed before returning an outcome.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationRetryPolicyStateCasError<StoreError> {
    /// Bounded conditional blob orchestration or outbound store failed.
    Blob(NativeContinuationBlobPersistenceError<StoreError>),
    /// Canonical active-policy state framing or semantics failed.
    Codec(NativeContinuationRetryPolicyStateCodecError),
    /// Expected state could not advance exactly one revision.
    Owner(NativeContinuationRetryPolicyOwnerError),
}

/// Result of one typed durable active-policy CAS operation.
pub type NativeContinuationRetryPolicyStateCasResult<
    StoreError,
    DurabilityError,
> = Result<
    NativeContinuationRetryPolicyStateCas<DurabilityError>,
    NativeContinuationRetryPolicyStateCasError<StoreError>,
>;

/// Typed CAS result specialized to one conditional durable store.
pub type NativeContinuationRetryPolicyStateCasStoreResult<Store> =
    NativeContinuationRetryPolicyStateCasResult<
        <Store as BlobStore>::Error,
        <Store as DurableBlobStore>::DurabilityError,
    >;

/// Conditionally publishes one active retry policy under revision semantics.
///
/// # Errors
///
/// Returns revision exhaustion, codec rejection, byte-limit failure, or
/// outbound coordination/publication failure before a typed outcome can be
/// returned.
pub fn compare_and_swap_native_continuation_retry_policy_state_durably<Store>(
    store: &mut Store,
    expected: Option<NativeContinuationRetryPolicyState>,
    candidate: NativeContinuationRetryPolicy,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationRetryPolicyStateCasStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    let candidate_state = derive_candidate_state(expected, candidate)
        .map_err(NativeContinuationRetryPolicyStateCasError::Owner)?;
    let expected_bytes = expected
        .map(encode_native_continuation_retry_policy_state)
        .transpose()
        .map_err(NativeContinuationRetryPolicyStateCasError::Codec)?;
    let candidate_bytes =
        encode_native_continuation_retry_policy_state(candidate_state)
            .map_err(NativeContinuationRetryPolicyStateCasError::Codec)?;
    let outcome = compare_and_swap_blob_durably(
        store,
        expected_bytes.as_deref(),
        &candidate_bytes,
        maximum_bytes,
    )
    .map_err(NativeContinuationRetryPolicyStateCasError::Blob)?;
    match outcome {
        BlobCasDurable::Conflict { current: current_bytes } => {
            let current = current_bytes
                .as_deref()
                .map(decode_native_continuation_retry_policy_state)
                .transpose()
                .map_err(NativeContinuationRetryPolicyStateCasError::Codec)?;
            Ok(NativeContinuationRetryPolicyStateCas::Conflict {
                candidate,
                current,
                expected,
            })
        },
        BlobCasDurable::Durable { write } => {
            Ok(NativeContinuationRetryPolicyStateCas::Durable {
                bytes: write.bytes(),
                current: candidate_state,
                previous: expected,
            })
        },
        BlobCasDurable::Published { durability_error, write } => {
            Ok(NativeContinuationRetryPolicyStateCas::Published {
                bytes: write.bytes(),
                current: candidate_state,
                durability_error,
                previous: expected,
            })
        },
    }
}

fn derive_candidate_state(
    expected: Option<NativeContinuationRetryPolicyState>,
    candidate: NativeContinuationRetryPolicy,
) -> Result<
    NativeContinuationRetryPolicyState,
    NativeContinuationRetryPolicyOwnerError,
> {
    expected.map_or_else(
        || {
            Ok(NativeContinuationRetryPolicyState::new(
                candidate,
                NativeContinuationRetryPolicyRevision::initial(),
            ))
        },
        |previous| previous.next(candidate),
    )
}
