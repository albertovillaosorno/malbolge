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
//   - Typed bounded persistence for dependency-reduced v6 graph provenance.
// - Must-Not:
//   - Choose storage paths, trust persisted verifier authority, bypass replay,
//     or grant executable-memory/invocation authority.
// - Allows:
//   - Inputs: one admitted graph claim, explicit byte/replay bounds, and a
//     caller-configured blob store.
//   - Outputs: exact publication evidence, missing state, or a freshly
//     replay-verified reduced graph.
//   - Side effects: delegated through bounded opaque-blob persistence only.
// - Split-When:
//   - Multi-blob object bundles, migration, or graph/object transactions gain
//     independent authority.
// - Merge-When:
//   - One general AOT artifact persistence owner subsumes reduced provenance.
// - Summary:
//   - Binds the reduced-graph codec to replaceable durable blob storage.
// - Description:
//   - Encoding happens before publication; restoration replays through the
//     codec only after bounded blob loading.
// - Usage:
//   - Call with an explicit blob store such as the filesystem blob adapter.
// - Defaults:
//   - Missing state is explicit; byte/replay limits and codec failures fail
//     closed without inventing graph authority.
//

//! Typed bounded persistence for dependency-reduced register-masked AOT graphs.

use std::num::NonZeroUsize;

use store_port::{
    NativeContinuationBlobStore as BlobStore,
    NativeContinuationDurableBlobStore as DurableBlobStore,
};

use crate::execution_native::{
    AheadOfExecutionRegisterMaskedReducedStateGraphCodecError,
    AheadOfExecutionRegisterMaskedReducedStateGraphDecodeLimits,
    UntrustedAheadOfExecutionRegisterMaskedReducedStateGraph,
    VerifiedAheadOfExecutionRegisterMaskedReducedStateGraph,
    decode_ahead_of_execution_register_masked_reduced_state_graph,
    encode_ahead_of_execution_register_masked_reduced_state_graph,
};
use crate::{blob_persistence, blob_store as store_port};

/// Publication plus explicit post-publication durability state.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum RegisterMaskedReducedGraphDurablePersistence<DurabilityError> {
    /// Canonical publication and durability confirmation both completed.
    Durable {
        /// Exact typed publication evidence.
        write: RegisterMaskedReducedGraphPersistenceWrite,
    },
    /// Canonical publication committed, but durability confirmation failed.
    Published {
        /// Exact post-publication durability failure.
        durability_error: DurabilityError,
        /// Exact typed publication evidence.
        write: RegisterMaskedReducedGraphPersistenceWrite,
    },
}

/// Why one typed reduced-graph persistence operation failed closed.
#[derive(Debug, Eq, PartialEq)]
pub enum RegisterMaskedReducedGraphPersistenceError<StoreError> {
    /// Bounded opaque-blob orchestration or its outbound store failed.
    Blob(blob_persistence::NativeContinuationBlobPersistenceError<StoreError>),
    /// Canonical provenance framing, replay, or graph admission failed.
    Codec(AheadOfExecutionRegisterMaskedReducedStateGraphCodecError),
}

/// Result of one bounded reduced-graph restoration.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum RegisterMaskedReducedGraphPersistenceLoad {
    /// No durable provenance exists at the adapter-configured location.
    Missing,
    /// Canonical bytes reconstructed one freshly verified reduced graph.
    Restored {
        /// Exact canonical byte count returned by the adapter.
        bytes: usize,
        /// Fresh graph authority rebuilt from durable provenance.
        graph: VerifiedAheadOfExecutionRegisterMaskedReducedStateGraph,
    },
}

/// Publication evidence from one successful canonical graph replacement.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RegisterMaskedReducedGraphPersistenceWrite {
    bytes: usize,
}

/// Result of publication plus optional durability confirmation.
pub type RegisterMaskedReducedGraphDurablePersistenceResult<
    StoreError,
    DurabilityError,
> = Result<
    RegisterMaskedReducedGraphDurablePersistence<DurabilityError>,
    RegisterMaskedReducedGraphPersistenceError<StoreError>,
>;

/// Durable typed graph result specialized to one store type.
pub type RegisterMaskedReducedGraphDurableStoreResult<Store> =
    RegisterMaskedReducedGraphDurablePersistenceResult<
        <Store as BlobStore>::Error,
        <Store as DurableBlobStore>::DurabilityError,
    >;

/// Result of one typed reduced-graph persistence operation.
pub type RegisterMaskedReducedGraphPersistenceResult<Value, StoreError> =
    Result<Value, RegisterMaskedReducedGraphPersistenceError<StoreError>>;

type BlobDurablePersistence<DurabilityError> =
    blob_persistence::NativeContinuationBlobDurablePersistence<DurabilityError>;
type BlobLoad = blob_persistence::NativeContinuationBlobPersistenceLoad;

impl<DurabilityError>
    RegisterMaskedReducedGraphDurablePersistence<DurabilityError>
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

impl RegisterMaskedReducedGraphPersistenceWrite {
    /// Returns the exact canonical byte count passed to the outbound store.
    #[must_use]
    pub const fn bytes(self) -> usize {
        self.bytes
    }
}

fn map_durable_persistence<DurabilityError>(
    outcome: BlobDurablePersistence<DurabilityError>,
) -> RegisterMaskedReducedGraphDurablePersistence<DurabilityError> {
    match outcome {
        BlobDurablePersistence::Durable { write } => {
            RegisterMaskedReducedGraphDurablePersistence::Durable {
                write: RegisterMaskedReducedGraphPersistenceWrite {
                    bytes: write.bytes(),
                },
            }
        },
        BlobDurablePersistence::Published { durability_error, write } => {
            RegisterMaskedReducedGraphDurablePersistence::Published {
                durability_error,
                write: RegisterMaskedReducedGraphPersistenceWrite {
                    bytes: write.bytes(),
                },
            }
        },
    }
}

/// Persists one admitted reduced graph as canonical bounded provenance bytes.
///
/// # Errors
///
/// Returns codec, byte-limit, or outbound-store failure before publication.
pub fn persist_register_masked_reduced_graph<Store>(
    store: &mut Store,
    claim: &UntrustedAheadOfExecutionRegisterMaskedReducedStateGraph,
    maximum_bytes: NonZeroUsize,
) -> RegisterMaskedReducedGraphPersistenceResult<
    RegisterMaskedReducedGraphPersistenceWrite,
    Store::Error,
>
where
    Store: BlobStore,
{
    let bytes =
        encode_ahead_of_execution_register_masked_reduced_state_graph(claim)
            .map_err(RegisterMaskedReducedGraphPersistenceError::Codec)?;
    let write = blob_persistence::persist_blob(store, &bytes, maximum_bytes)
        .map_err(RegisterMaskedReducedGraphPersistenceError::Blob)?;
    Ok(RegisterMaskedReducedGraphPersistenceWrite { bytes: write.bytes() })
}

/// Persists one admitted reduced graph and confirms store durability.
///
/// # Errors
///
/// Returns only codec, byte-limit, or store failure before publication.
pub fn persist_register_masked_reduced_graph_durably<Store>(
    store: &mut Store,
    claim: &UntrustedAheadOfExecutionRegisterMaskedReducedStateGraph,
    maximum_bytes: NonZeroUsize,
) -> RegisterMaskedReducedGraphDurableStoreResult<Store>
where
    Store: DurableBlobStore,
{
    let bytes =
        encode_ahead_of_execution_register_masked_reduced_state_graph(claim)
            .map_err(RegisterMaskedReducedGraphPersistenceError::Codec)?;
    let outcome =
        blob_persistence::persist_blob_durably(store, &bytes, maximum_bytes)
            .map_err(RegisterMaskedReducedGraphPersistenceError::Blob)?;
    Ok(map_durable_persistence(outcome))
}

/// Restores one bounded provenance blob and rebuilds reduced graph authority.
///
/// # Errors
///
/// Returns store, byte-limit, codec, replay-limit, or graph-admission evidence
/// without inventing missing state or trusting serialized verifier authority.
pub fn restore_register_masked_reduced_graph<Store>(
    store: &mut Store,
    maximum_bytes: NonZeroUsize,
    decode_limits: AheadOfExecutionRegisterMaskedReducedStateGraphDecodeLimits,
) -> RegisterMaskedReducedGraphPersistenceResult<
    RegisterMaskedReducedGraphPersistenceLoad,
    Store::Error,
>
where
    Store: BlobStore,
{
    let load = blob_persistence::restore_blob(store, maximum_bytes)
        .map_err(RegisterMaskedReducedGraphPersistenceError::Blob)?;
    let BlobLoad::Present { bytes } = load else {
        return Ok(RegisterMaskedReducedGraphPersistenceLoad::Missing);
    };
    let length = bytes.len();
    let graph = decode_ahead_of_execution_register_masked_reduced_state_graph(
        &bytes,
        decode_limits,
    )
    .map_err(RegisterMaskedReducedGraphPersistenceError::Codec)?;
    Ok(RegisterMaskedReducedGraphPersistenceLoad::Restored {
        bytes: length,
        graph,
    })
}
