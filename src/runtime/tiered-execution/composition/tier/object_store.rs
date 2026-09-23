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
//   - Bounded persistence of one verified register-masked v6 AOT object.
// - Must-Not:
//   - Persist native keys as authority, choose storage paths, load executable
//     memory, or bypass semantic object verification on restore.
// - Allows:
//   - Inputs: one verified object for publication, or expected program/runtime/
//     host assumptions for bounded restoration.
//   - Outputs: ordinary blob publication evidence, missing state, or one
//     freshly reverified object-only artifact.
//   - Side effects: delegated through bounded opaque-blob persistence only.
// - Split-When:
//   - Multi-object transactions or executable residency gain ownership.
// - Merge-When:
//   - One general native artifact store subsumes exact v6 object persistence.
// - Summary:
//   - Stores canonical COFF bytes while rebuilding identity on every load.
// - Description:
//   - Restore derives the current exact key from caller authority and treats
//     all stored object bytes as untrusted compiler/emitter output.
// - Usage:
//   - Bind one exact expected program to one caller-configured blob location.
// - Defaults:
//   - Missing blobs are explicit; byte-limit, host, identity, or object drift
//     fails closed before any AOT artifact is returned.
//

//! Typed durable storage for one register-masked v6 AOT object.

use std::num::NonZeroUsize;

use malbolge::{RegisterMaskedRegionEffectProgram, RuntimeCapability};
use store_port::{
    NativeContinuationBlobStore as BlobStore,
    NativeContinuationDurableBlobStore as DurableBlobStore,
};

use crate::execution_native::{
    AheadOfExecutionRegisterMaskedObjectRestoreError, DirectHost,
    VerifiedAheadOfExecutionRegisterMaskedArtifact,
    restore_ahead_of_execution_register_masked_object,
};
use crate::{blob_persistence, blob_store as store_port};

/// Caller authority required to reverify one durable v6 object.
#[derive(Clone, Copy, Debug)]
pub struct RegisterMaskedAotObjectRestoreRequest<'requirement> {
    host: DirectHost,
    maximum_bytes: NonZeroUsize,
    program: &'requirement RegisterMaskedRegionEffectProgram,
    runtime: &'static RuntimeCapability,
}

impl<'requirement> RegisterMaskedAotObjectRestoreRequest<'requirement> {
    /// Binds expected IR/runtime/host identity and one positive blob byte
    /// bound.
    #[must_use]
    pub const fn new(
        program: &'requirement RegisterMaskedRegionEffectProgram,
        runtime: &'static RuntimeCapability,
        host: DirectHost,
        maximum_bytes: NonZeroUsize,
    ) -> Self {
        Self {
            host,
            maximum_bytes,
            program,
            runtime,
        }
    }
}

/// Result of one bounded durable object restoration.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum RegisterMaskedAotObjectPersistenceLoad {
    /// No object currently exists at the adapter-configured location.
    Missing,
    /// Stored COFF crossed current native verification for the expected IR.
    Restored {
        /// Exact opaque byte count returned by bounded blob loading.
        bytes: usize,
        /// Fresh object-only native authority rebuilt from current
        /// assumptions.
        artifact: Box<VerifiedAheadOfExecutionRegisterMaskedArtifact>,
    },
}

/// Why one durable object restore failed closed.
#[derive(Debug, Eq, PartialEq)]
pub enum RegisterMaskedAotObjectRestorePersistenceError<
    'requirement,
    StoreError,
> {
    /// Bounded opaque-blob orchestration or outbound storage failed.
    Blob(
        Box<
            blob_persistence::NativeContinuationBlobPersistenceError<
                StoreError,
            >,
        >,
    ),
    /// Stored object bytes failed current native admission or verification.
    Native(Box<AheadOfExecutionRegisterMaskedObjectRestoreError<'requirement>>),
}

/// Result of one typed durable object restoration.
pub type RegisterMaskedAotObjectRestoreResult<'requirement, Value, StoreError> =
    Result<
        Value,
        RegisterMaskedAotObjectRestorePersistenceError<
            'requirement,
            StoreError,
        >,
    >;

/// Persists exact verified COFF bytes under an explicit positive byte bound.
///
/// # Errors
///
/// Returns ordinary bounded blob persistence failure before publication.
pub fn persist_register_masked_aot_object<Store>(
    store: &mut Store,
    artifact: &VerifiedAheadOfExecutionRegisterMaskedArtifact,
    maximum_bytes: NonZeroUsize,
) -> blob_persistence::NativeContinuationBlobPersistenceResult<
    blob_persistence::NativeContinuationBlobPersistenceWrite,
    Store::Error,
>
where
    Store: BlobStore,
{
    blob_persistence::persist_blob(store, artifact.object(), maximum_bytes)
}

/// Persists exact verified COFF bytes and confirms store durability.
///
/// # Errors
///
/// Returns ordinary bounded blob persistence failure before publication.
pub fn persist_register_masked_aot_object_durably<Store>(
    store: &mut Store,
    artifact: &VerifiedAheadOfExecutionRegisterMaskedArtifact,
    maximum_bytes: NonZeroUsize,
) -> blob_persistence::NativeContinuationBlobDurableStoreResult<Store>
where
    Store: DurableBlobStore,
{
    blob_persistence::persist_blob_durably(
        store,
        artifact.object(),
        maximum_bytes,
    )
}

/// Restores bounded COFF and rebuilds object authority from current
/// assumptions.
///
/// # Errors
///
/// Returns byte-limit/store evidence or current native
/// admission/identity/object verification failure. Stored bytes never carry
/// their own key authority.
pub fn restore_register_masked_aot_object<'requirement, Store>(
    store: &mut Store,
    request: RegisterMaskedAotObjectRestoreRequest<'requirement>,
) -> RegisterMaskedAotObjectRestoreResult<
    'requirement,
    RegisterMaskedAotObjectPersistenceLoad,
    Store::Error,
>
where
    Store: BlobStore,
{
    let load = blob_persistence::restore_blob(store, request.maximum_bytes)
        .map_err(|error| {
            RegisterMaskedAotObjectRestorePersistenceError::Blob(Box::new(
                error,
            ))
        })?;
    let blob_persistence::NativeContinuationBlobPersistenceLoad::Present {
        bytes,
    } = load
    else {
        return Ok(RegisterMaskedAotObjectPersistenceLoad::Missing);
    };
    let length = bytes.len();
    let artifact = restore_ahead_of_execution_register_masked_object(
        request.program,
        request.runtime,
        request.host,
        bytes,
    )
    .map_err(|error| {
        RegisterMaskedAotObjectRestorePersistenceError::Native(Box::new(error))
    })?;
    Ok(RegisterMaskedAotObjectPersistenceLoad::Restored {
        bytes: length,
        artifact: Box::new(artifact),
    })
}
