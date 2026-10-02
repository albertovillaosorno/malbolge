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
//   - Binding canonical dispatch-policy bytes to bounded single-blob
//     persistence.
// - Must-Not:
//   - Choose storage locations, infer policy, perform compare-and-swap, or
//     create revision ownership.
// - Allows:
//   - Inputs: one immutable dispatch policy, positive byte limit, and blob
//     store.
//   - Outputs: exact typed publication or reconstructed policy evidence.
//   - Side effects: delegated through bounded opaque-blob persistence only.
// - Split-When:
//   - Concurrent policy ownership, CAS, or migration gains authority.
// - Merge-When:
//   - Cross-cycle dispatch orchestration owns persistence and policy execution
//     atomically.
// - Summary:
//   - Persists validated dispatch-policy snapshots without global ownership.
// - Description:
//   - Canonical codec validation surrounds the opaque blob application service.
// - Usage:
//   - Call explicitly for one preconfigured dispatch-policy blob store.
// - Defaults:
//   - Missing durable policy is explicit and never invents a default policy.
//

//! Typed bounded persistence for immutable synchronous dispatch policies.

use std::num::NonZeroUsize;

use store_port::{
    NativeContinuationBlobStore as BlobStore,
    NativeContinuationDurableBlobStore as DurableBlobStore,
};

use crate::continuation_dispatch_policy::NativeContinuationDispatchPolicy;
use crate::continuation_dispatch_policy_codec::{
    NativeContinuationDispatchPolicyCodecError,
    decode_native_continuation_dispatch_policy_snapshot,
    encode_native_continuation_dispatch_policy_snapshot,
};
use crate::{blob_persistence, blob_store as store_port};

/// Dispatch-policy publication plus explicit post-publication durability state.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyDurablePersistence<DurabilityError> {
    /// Canonical publication and durability confirmation both completed.
    Durable {
        /// Exact typed publication evidence.
        write: NativeContinuationDispatchPolicyPersistenceWrite,
    },
    /// Canonical publication committed, but durability confirmation failed.
    Published {
        /// Exact post-publication durability failure.
        durability_error: DurabilityError,
        /// Exact typed publication evidence.
        write: NativeContinuationDispatchPolicyPersistenceWrite,
    },
}

/// Why one typed dispatch-policy persistence operation failed closed.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyPersistenceError<StoreError> {
    /// Bounded opaque-blob orchestration or its outbound store failed.
    Blob(blob_persistence::NativeContinuationBlobPersistenceError<StoreError>),
    /// Canonical dispatch-policy framing or semantics failed.
    Codec(NativeContinuationDispatchPolicyCodecError),
}

/// Result of one bounded dispatch-policy restoration.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyPersistenceLoad {
    /// No durable policy currently exists at the adapter-configured location.
    Missing,
    /// Canonical bytes reconstructed one exact immutable dispatch policy.
    Restored {
        /// Exact canonical byte count returned by the adapter.
        bytes: usize,
        /// Reconstructed dispatch policy.
        policy: NativeContinuationDispatchPolicy,
    },
}

/// Result of typed policy publication plus durability confirmation.
pub type NativeContinuationDispatchPolicyDurablePersistenceResult<
    StoreError,
    DurabilityError,
> = Result<
    NativeContinuationDispatchPolicyDurablePersistence<DurabilityError>,
    NativeContinuationDispatchPolicyPersistenceError<StoreError>,
>;

/// Durable typed policy result specialized to one store type.
pub type NativeContinuationDispatchPolicyDurableStoreResult<Store> =
    NativeContinuationDispatchPolicyDurablePersistenceResult<
        <Store as BlobStore>::Error,
        <Store as DurableBlobStore>::DurabilityError,
    >;

/// Result of one typed dispatch-policy persistence operation.
pub type NativeContinuationDispatchPolicyPersistenceResult<Value, StoreError> =
    Result<Value, NativeContinuationDispatchPolicyPersistenceError<StoreError>>;

/// Publication evidence from one successful canonical policy replacement.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationDispatchPolicyPersistenceWrite {
    bytes: usize,
}

type BlobDurablePersistence<DurabilityError> =
    blob_persistence::NativeContinuationBlobDurablePersistence<DurabilityError>;
type BlobLoad = blob_persistence::NativeContinuationBlobPersistenceLoad;

impl<DurabilityError>
    NativeContinuationDispatchPolicyDurablePersistence<DurabilityError>
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

impl NativeContinuationDispatchPolicyPersistenceWrite {
    /// Returns the exact canonical byte count passed to the outbound store.
    #[must_use]
    pub const fn bytes(self) -> usize {
        self.bytes
    }
}

fn map_durable_persistence<DurabilityError>(
    outcome: BlobDurablePersistence<DurabilityError>,
) -> NativeContinuationDispatchPolicyDurablePersistence<DurabilityError> {
    match outcome {
        BlobDurablePersistence::Durable { write } => {
            NativeContinuationDispatchPolicyDurablePersistence::Durable {
                write: NativeContinuationDispatchPolicyPersistenceWrite {
                    bytes: write.bytes(),
                },
            }
        },
        BlobDurablePersistence::Published { durability_error, write } => {
            NativeContinuationDispatchPolicyDurablePersistence::Published {
                durability_error,
                write: NativeContinuationDispatchPolicyPersistenceWrite {
                    bytes: write.bytes(),
                },
            }
        },
    }
}

/// Persists one exact dispatch policy as canonical bounded bytes.
///
/// # Errors
///
/// Returns codec, byte-limit, or outbound-store failure before publication.
pub fn persist_native_continuation_dispatch_policy<Store>(
    store: &mut Store,
    policy: NativeContinuationDispatchPolicy,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationDispatchPolicyPersistenceResult<
    NativeContinuationDispatchPolicyPersistenceWrite,
    Store::Error,
>
where
    Store: BlobStore,
{
    let bytes =
        encode_native_continuation_dispatch_policy_snapshot(policy.snapshot())
            .map_err(NativeContinuationDispatchPolicyPersistenceError::Codec)?;
    let write = blob_persistence::persist_blob(store, &bytes, maximum_bytes)
        .map_err(NativeContinuationDispatchPolicyPersistenceError::Blob)?;
    Ok(NativeContinuationDispatchPolicyPersistenceWrite {
        bytes: write.bytes(),
    })
}

/// Persists one exact dispatch policy and confirms store durability.
///
/// # Errors
///
/// Returns only codec, byte-limit, or store failure before publication.
pub fn persist_native_continuation_dispatch_policy_durably<Store>(
    store: &mut Store,
    policy: NativeContinuationDispatchPolicy,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationDispatchPolicyDurableStoreResult<Store>
where
    Store: DurableBlobStore,
{
    let bytes =
        encode_native_continuation_dispatch_policy_snapshot(policy.snapshot())
            .map_err(NativeContinuationDispatchPolicyPersistenceError::Codec)?;
    let outcome =
        blob_persistence::persist_blob_durably(store, &bytes, maximum_bytes)
            .map_err(NativeContinuationDispatchPolicyPersistenceError::Blob)?;
    Ok(map_durable_persistence(outcome))
}

/// Restores one exact dispatch policy from canonical bounded bytes.
///
/// # Errors
///
/// Returns store, byte-limit, or codec evidence without inventing missing
/// state.
pub fn restore_native_continuation_dispatch_policy<Store>(
    store: &mut Store,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationDispatchPolicyPersistenceResult<
    NativeContinuationDispatchPolicyPersistenceLoad,
    Store::Error,
>
where
    Store: BlobStore,
{
    let load = blob_persistence::restore_blob(store, maximum_bytes)
        .map_err(NativeContinuationDispatchPolicyPersistenceError::Blob)?;
    let BlobLoad::Present { bytes } = load else {
        return Ok(NativeContinuationDispatchPolicyPersistenceLoad::Missing);
    };
    let length = bytes.len();
    let snapshot = decode_native_continuation_dispatch_policy_snapshot(&bytes)
        .map_err(NativeContinuationDispatchPolicyPersistenceError::Codec)?;
    Ok(NativeContinuationDispatchPolicyPersistenceLoad::Restored {
        bytes: length,
        policy: NativeContinuationDispatchPolicy::from_snapshot(snapshot),
    })
}
