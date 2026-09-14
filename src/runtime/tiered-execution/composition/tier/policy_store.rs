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
//   - Binding canonical retry-policy bytes to bounded single-blob persistence.
// - Must-Not:
//   - Choose storage locations, infer recommendations, or publish global
//     policy.
// - Allows:
//   - Inputs: one immutable retry policy, positive byte limit, and blob store.
//   - Outputs: exact typed publication or reconstructed policy evidence.
//   - Side effects: delegated through bounded opaque-blob persistence only.
// - Split-When:
//   - Concurrent policy ownership, CAS, or migration gains authority.
// - Merge-When:
//   - Cross-cycle policy orchestration owns persistence and request
//     publication.
// - Summary:
//   - Persists validated retry-policy snapshots without creating global policy.
// - Description:
//   - Canonical codec validation surrounds the opaque blob application service.
// - Usage:
//   - Call explicitly for one preconfigured policy-document blob store.
// - Defaults:
//   - Missing durable policy is explicit and never invents a default policy.
//

//! Typed bounded persistence for immutable native retry policies.

use std::num::NonZeroUsize;

use store_port::{
    NativeContinuationBlobStore as BlobStore,
    NativeContinuationDurableBlobStore as DurableBlobStore,
};

use crate::retry_policy::NativeContinuationRetryPolicy;
use crate::retry_policy_codec::{
    NativeContinuationRetryPolicyCodecError,
    decode_native_continuation_retry_policy_snapshot,
    encode_native_continuation_retry_policy_snapshot,
};
use crate::{blob_persistence, blob_store as store_port};

/// Retry-policy publication plus explicit post-publication durability state.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationRetryPolicyDurablePersistence<DurabilityError> {
    /// Canonical publication and durability confirmation both completed.
    Durable {
        /// Exact typed publication evidence.
        write: NativeContinuationRetryPolicyPersistenceWrite,
    },
    /// Canonical publication committed, but durability confirmation failed.
    Published {
        /// Exact post-publication durability failure.
        durability_error: DurabilityError,
        /// Exact typed publication evidence.
        write: NativeContinuationRetryPolicyPersistenceWrite,
    },
}

/// Why one typed retry-policy persistence operation failed closed.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationRetryPolicyPersistenceError<StoreError> {
    /// Bounded opaque-blob orchestration or its outbound store failed.
    Blob(blob_persistence::NativeContinuationBlobPersistenceError<StoreError>),
    /// Canonical retry-policy framing or semantics failed.
    Codec(NativeContinuationRetryPolicyCodecError),
}

/// Result of one bounded retry-policy restoration.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationRetryPolicyPersistenceLoad {
    /// No durable policy currently exists at the adapter-configured location.
    Missing,
    /// Canonical bytes reconstructed one exact immutable retry policy.
    Restored {
        /// Exact canonical byte count returned by the adapter.
        bytes: usize,
        /// Reconstructed retry policy.
        policy: NativeContinuationRetryPolicy,
    },
}

/// Result of typed policy publication plus durability confirmation.
pub type NativeContinuationRetryPolicyDurablePersistenceResult<
    StoreError,
    DurabilityError,
> = Result<
    NativeContinuationRetryPolicyDurablePersistence<DurabilityError>,
    NativeContinuationRetryPolicyPersistenceError<StoreError>,
>;

/// Durable typed policy result specialized to one store type.
pub type NativeContinuationRetryPolicyDurableStoreResult<Store> =
    NativeContinuationRetryPolicyDurablePersistenceResult<
        <Store as BlobStore>::Error,
        <Store as DurableBlobStore>::DurabilityError,
    >;

/// Result of one typed retry-policy persistence operation.
pub type NativeContinuationRetryPolicyPersistenceResult<Value, StoreError> =
    Result<Value, NativeContinuationRetryPolicyPersistenceError<StoreError>>;

/// Publication evidence from one successful canonical policy replacement.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryPolicyPersistenceWrite {
    bytes: usize,
}

type BlobDurablePersistence<DurabilityError> =
    blob_persistence::NativeContinuationBlobDurablePersistence<DurabilityError>;
type BlobLoad = blob_persistence::NativeContinuationBlobPersistenceLoad;

impl<DurabilityError>
    NativeContinuationRetryPolicyDurablePersistence<DurabilityError>
{
    /// Returns the exact committed canonical byte count.
    #[must_use]
    pub const fn bytes(&self) -> usize {
        match self {
            Self::Durable { write } | Self::Published { write, .. } => {
                write.bytes()
            },
        }
    }

    /// Returns post-publication durability failure when confirmation failed.
    #[must_use]
    pub const fn durability_error(&self) -> Option<&DurabilityError> {
        match self {
            Self::Durable { .. } => None,
            Self::Published { durability_error, .. } => Some(durability_error),
        }
    }

    /// Reports whether storage explicitly confirmed publication durability.
    #[must_use]
    pub const fn is_durable(&self) -> bool {
        matches!(self, Self::Durable { .. })
    }
}

impl NativeContinuationRetryPolicyPersistenceWrite {
    /// Returns the exact canonical byte count passed to the outbound store.
    #[must_use]
    pub const fn bytes(self) -> usize {
        self.bytes
    }
}

fn map_durable_persistence<DurabilityError>(
    outcome: BlobDurablePersistence<DurabilityError>,
) -> NativeContinuationRetryPolicyDurablePersistence<DurabilityError> {
    match outcome {
        BlobDurablePersistence::Durable { write } => {
            NativeContinuationRetryPolicyDurablePersistence::Durable {
                write: NativeContinuationRetryPolicyPersistenceWrite {
                    bytes: write.bytes(),
                },
            }
        },
        BlobDurablePersistence::Published { durability_error, write } => {
            NativeContinuationRetryPolicyDurablePersistence::Published {
                durability_error,
                write: NativeContinuationRetryPolicyPersistenceWrite {
                    bytes: write.bytes(),
                },
            }
        },
    }
}

/// Persists one exact retry policy as canonical bounded bytes.
///
/// # Errors
///
/// Returns codec, byte-limit, or outbound-store failure before publication.
pub fn persist_native_continuation_retry_policy<Store>(
    store: &mut Store,
    policy: NativeContinuationRetryPolicy,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationRetryPolicyPersistenceResult<
    NativeContinuationRetryPolicyPersistenceWrite,
    Store::Error,
>
where
    Store: BlobStore,
{
    let bytes =
        encode_native_continuation_retry_policy_snapshot(policy.snapshot())
            .map_err(NativeContinuationRetryPolicyPersistenceError::Codec)?;
    let write = blob_persistence::persist_blob(store, &bytes, maximum_bytes)
        .map_err(NativeContinuationRetryPolicyPersistenceError::Blob)?;
    Ok(NativeContinuationRetryPolicyPersistenceWrite { bytes: write.bytes() })
}

/// Persists one exact retry policy and confirms store durability.
///
/// # Errors
///
/// Returns only codec, byte-limit, or store failure before publication.
pub fn persist_native_continuation_retry_policy_durably<Store>(
    store: &mut Store,
    policy: NativeContinuationRetryPolicy,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationRetryPolicyDurableStoreResult<Store>
where
    Store: DurableBlobStore,
{
    let bytes =
        encode_native_continuation_retry_policy_snapshot(policy.snapshot())
            .map_err(NativeContinuationRetryPolicyPersistenceError::Codec)?;
    let outcome =
        blob_persistence::persist_blob_durably(store, &bytes, maximum_bytes)
            .map_err(NativeContinuationRetryPolicyPersistenceError::Blob)?;
    Ok(map_durable_persistence(outcome))
}

/// Restores one exact retry policy from canonical bounded bytes.
///
/// # Errors
///
/// Returns store, byte-limit, or codec evidence without inventing missing
/// state.
pub fn restore_native_continuation_retry_policy<Store>(
    store: &mut Store,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationRetryPolicyPersistenceResult<
    NativeContinuationRetryPolicyPersistenceLoad,
    Store::Error,
>
where
    Store: BlobStore,
{
    let load = blob_persistence::restore_blob(store, maximum_bytes)
        .map_err(NativeContinuationRetryPolicyPersistenceError::Blob)?;
    let BlobLoad::Present { bytes } = load else {
        return Ok(NativeContinuationRetryPolicyPersistenceLoad::Missing);
    };
    let length = bytes.len();
    let snapshot = decode_native_continuation_retry_policy_snapshot(&bytes)
        .map_err(NativeContinuationRetryPolicyPersistenceError::Codec)?;
    Ok(NativeContinuationRetryPolicyPersistenceLoad::Restored {
        bytes: length,
        policy: NativeContinuationRetryPolicy::from_snapshot(snapshot),
    })
}
