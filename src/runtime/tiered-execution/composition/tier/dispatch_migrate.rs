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
//   - One-way durable migration from canonical plain dispatch-policy bytes to
//     canonical revision-zero active-policy state.
// - Must-Not:
//   - Invent policy, migrate unknown future formats, overwrite concurrent
//     publications, or assign revisions other than initial revision zero.
// - Allows:
//   - Inputs: one bounded conditional durable store and positive byte limit.
//   - Outputs: missing/already-active evidence, migrated state, conflict state,
//     committed durability failure, or typed prepublication failure.
//   - Side effects: one bounded load plus at most one delegated conditional
//     publication and durability confirmation.
// - Split-When:
//   - Another historical format or active-state frame revision needs migration.
// - Merge-When:
//   - One durable dispatch-policy lifecycle owner subsumes migration and CAS.
// - Summary:
//   - Upgrades legacy MBDPOL01 publication to revision-zero MBDPST01 state.
// - Description:
//   - Exact observed legacy bytes are the CAS expectation; races never clobber.
// - Usage:
//   - Invoke explicitly before requiring revisioned active-policy state.
// - Defaults:
//   - Missing and already-active publications are successful non-mutations.
//

//! One-way durable upgrade from plain dispatch policy to active policy state.

use std::num::NonZeroUsize;

use crate::blob_persistence::{
    NativeContinuationBlobConditionalDurablePersistence as BlobCasDurable,
    NativeContinuationBlobPersistenceError,
    NativeContinuationBlobPersistenceLoad as BlobLoad,
    compare_and_swap_blob_durably, restore_blob,
};
use crate::blob_store::{
    NativeContinuationBlobStore as BlobStore,
    NativeContinuationConditionalBlobStore as ConditionalBlobStore,
    NativeContinuationDurableBlobStore as DurableBlobStore,
};
use crate::continuation_dispatch_policy::NativeContinuationDispatchPolicy;
use crate::continuation_dispatch_policy_codec::{
    NativeContinuationDispatchPolicyCodecError,
    decode_native_continuation_dispatch_policy_snapshot,
};
use crate::continuation_dispatch_policy_owner::{
    NativeContinuationDispatchPolicyRevision,
    NativeContinuationDispatchPolicyState,
};
use crate::continuation_dispatch_policy_state_codec::{
    NativeContinuationDispatchPolicyStateCodecError,
    decode_native_continuation_dispatch_policy_state,
    encode_native_continuation_dispatch_policy_state,
};

const POLICY_MAGIC: &[u8; 8] = b"MBDPOL01";
const STATE_MAGIC: &[u8; 8] = b"MBDPST01";

/// Typed current durable representation observed during migration.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyMigrationCurrent {
    /// Canonical revisioned active-policy state already exists.
    Active(NativeContinuationDispatchPolicyState),
    /// Canonical legacy plain-policy publication exists.
    Legacy(NativeContinuationDispatchPolicy),
}

/// Typed outcome of one plain-policy to active-state migration attempt.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyMigration<DurabilityError> {
    /// Current durable publication is already canonical active state.
    AlreadyActive {
        /// Exact reconstructed active state.
        state: NativeContinuationDispatchPolicyState,
    },
    /// Observed legacy bytes changed before conditional publication.
    Conflict {
        /// Exact typed current publication, or `None` when concurrently
        /// removed.
        current: Option<NativeContinuationDispatchPolicyMigrationCurrent>,
        /// Legacy policy originally observed for migration.
        previous: NativeContinuationDispatchPolicy,
    },
    /// Revision-zero active state committed and durability was confirmed.
    Durable {
        /// Exact committed active-state byte count.
        bytes: usize,
        /// Exact revision-zero active state now published.
        current: NativeContinuationDispatchPolicyState,
        /// Legacy policy replaced by this migration.
        previous: NativeContinuationDispatchPolicy,
    },
    /// No durable dispatch policy exists.
    Missing,
    /// Revision-zero active state committed, then durability confirmation
    /// failed.
    Published {
        /// Exact committed active-state byte count.
        bytes: usize,
        /// Exact revision-zero active state now published.
        current: NativeContinuationDispatchPolicyState,
        /// Exact post-publication durability failure.
        durability_error: DurabilityError,
        /// Legacy policy replaced by this migration.
        previous: NativeContinuationDispatchPolicy,
    },
}

/// Why durable dispatch-policy migration failed before a typed outcome.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyMigrationError<StoreError> {
    /// Bounded blob load, conditional publication, or outbound store failed.
    Blob(NativeContinuationBlobPersistenceError<StoreError>),
    /// Bytes identified as legacy policy failed canonical decoding.
    PolicyCodec(NativeContinuationDispatchPolicyCodecError),
    /// Bytes identified as active state failed canonical decoding.
    StateCodec(NativeContinuationDispatchPolicyStateCodecError),
    /// Durable bytes do not identify either owned canonical format.
    UnknownFormat,
}

/// Migration result specialized to one conditional durable store.
pub type NativeContinuationDispatchPolicyMigrationStoreResult<Store> = Result<
    NativeContinuationDispatchPolicyMigration<
        <Store as DurableBlobStore>::DurabilityError,
    >,
    NativeContinuationDispatchPolicyMigrationError<<Store as BlobStore>::Error>,
>;

/// Migrates one canonical plain policy to revision-zero active state durably.
///
/// # Errors
///
/// Returns bounded storage, canonical decoding, or unknown-format evidence.
pub fn migrate_native_continuation_dispatch_policy_state_durably<Store>(
    store: &mut Store,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationDispatchPolicyMigrationStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    let load = restore_blob(store, maximum_bytes)
        .map_err(NativeContinuationDispatchPolicyMigrationError::Blob)?;
    let BlobLoad::Present { bytes } = load else {
        return Ok(NativeContinuationDispatchPolicyMigration::Missing);
    };
    match classify_publication(&bytes)? {
        NativeContinuationDispatchPolicyMigrationCurrent::Active(state) => {
            Ok(NativeContinuationDispatchPolicyMigration::AlreadyActive {
                state,
            })
        },
        NativeContinuationDispatchPolicyMigrationCurrent::Legacy(policy) => {
            migrate_legacy(store, maximum_bytes, &bytes, policy)
        },
    }
}

fn classify_publication<StoreError>(
    bytes: &[u8],
) -> Result<
    NativeContinuationDispatchPolicyMigrationCurrent,
    NativeContinuationDispatchPolicyMigrationError<StoreError>,
> {
    let Some(magic) = bytes.get(..8) else {
        return Err(
            NativeContinuationDispatchPolicyMigrationError::UnknownFormat,
        );
    };
    if magic == STATE_MAGIC {
        return decode_native_continuation_dispatch_policy_state(bytes)
            .map(NativeContinuationDispatchPolicyMigrationCurrent::Active)
            .map_err(
                NativeContinuationDispatchPolicyMigrationError::StateCodec,
            );
    }
    if magic == POLICY_MAGIC {
        return decode_native_continuation_dispatch_policy_snapshot(bytes)
            .map(NativeContinuationDispatchPolicy::from_snapshot)
            .map(NativeContinuationDispatchPolicyMigrationCurrent::Legacy)
            .map_err(
                NativeContinuationDispatchPolicyMigrationError::PolicyCodec,
            );
    }
    Err(NativeContinuationDispatchPolicyMigrationError::UnknownFormat)
}

fn migrate_legacy<Store>(
    store: &mut Store,
    maximum_bytes: NonZeroUsize,
    expected_bytes: &[u8],
    previous: NativeContinuationDispatchPolicy,
) -> NativeContinuationDispatchPolicyMigrationStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    let current = NativeContinuationDispatchPolicyState::new(
        previous,
        NativeContinuationDispatchPolicyRevision::initial(),
    );
    let replacement = encode_native_continuation_dispatch_policy_state(current)
        .map_err(NativeContinuationDispatchPolicyMigrationError::StateCodec)?;
    let outcome = compare_and_swap_blob_durably(
        store,
        Some(expected_bytes),
        &replacement,
        maximum_bytes,
    )
    .map_err(NativeContinuationDispatchPolicyMigrationError::Blob)?;
    match outcome {
        BlobCasDurable::Conflict { current: current_bytes } => {
            let observed = current_bytes
                .as_deref()
                .map(classify_publication)
                .transpose()?;
            Ok(NativeContinuationDispatchPolicyMigration::Conflict {
                current: observed,
                previous,
            })
        },
        BlobCasDurable::Durable { write } => {
            Ok(NativeContinuationDispatchPolicyMigration::Durable {
                bytes: write.bytes(),
                current,
                previous,
            })
        },
        BlobCasDurable::Published { durability_error, write } => {
            Ok(NativeContinuationDispatchPolicyMigration::Published {
                bytes: write.bytes(),
                current,
                durability_error,
                previous,
            })
        },
    }
}
