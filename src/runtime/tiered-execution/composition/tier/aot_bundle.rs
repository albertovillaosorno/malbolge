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
//   - Atomic bounded persistence of complete register-masked v6 AOT bundles.
// - Must-Not:
//   - Persist native keys as authority, choose storage paths, publish partial
//     bundles, load executable memory, or trust object bytes during restore.
// - Allows:
//   - Inputs: caller-ordered expected v6 programs, a sealed verified AOT set,
//     current runtime/host assumptions, and one positive blob byte bound.
//   - Outputs: one atomic opaque bundle publication or one freshly reverified
//     exact-key AOT set.
//   - Side effects: delegated through bounded single-blob persistence only.
// - Split-When:
//   - Bundle migration, cross-blob transactions, or executable residency gains
//     independent policy.
// - Merge-When:
//   - One general AOT package owner subsumes object bundle persistence.
// - Summary:
//   - Commits a complete ordered COFF bundle through one atomic blob replace.
// - Description:
//   - Stored framing carries lengths only; restore rebuilds every key and
//     native authority from caller-supplied expected IR/runtime/host
//     assumptions.
// - Usage:
//   - Persist all reduced-graph node objects together before runtime dispatch.
// - Defaults:
//   - Empty, incomplete, malformed, reordered, oversized, or unverifiable
//     bundles fail closed without publishing or returning a partial AOT set.
//

//! Atomic durable bundles for register-masked v6 AOT objects.

use std::num::NonZeroUsize;
use std::sync::Arc;

use malbolge::{RegisterMaskedRegionEffectProgram, RuntimeCapability};
use store_port::{
    NativeContinuationBlobStore as BlobStore,
    NativeContinuationDurableBlobStore as DurableBlobStore,
};

use crate::execution_native::{
    AheadOfExecutionRegisterMaskedObjectRestoreError,
    AheadOfExecutionRegisterMaskedSelectionError,
    AheadOfExecutionRegisterMaskedTier, DirectHost,
    VerifiedAheadOfExecutionRegisterMaskedArtifact,
    VerifiedAheadOfExecutionRegisterMaskedSet,
    restore_ahead_of_execution_register_masked_object,
    select_ahead_of_execution_register_masked_tier,
};
use crate::{blob_persistence, blob_store as store_port};

const BUNDLE_HEADER_BYTES: usize = 10;
const BUNDLE_MAGIC: &[u8; 4] = b"MBAB";
const BUNDLE_VERSION: u16 = 1;
const OBJECT_LENGTH_BYTES: usize = 8;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum BundleAppendError {
    ByteLimit {
        maximum_bytes: NonZeroUsize,
        observed_bytes: usize,
    },
    SizeEncoding {
        index: usize,
    },
}

type DecodedObject<'bytes> = (&'bytes [u8], usize);

/// Why persisted bundle framing is not the exact expected ordered bundle.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RegisterMaskedAotBundleFramingError {
    /// Persisted object count differs from caller-owned expected program count.
    CountMismatch {
        /// Caller-owned expected program count.
        expected: usize,
        /// Persisted untrusted object count.
        observed: u32,
    },
    /// Caller-owned expected program count cannot be represented canonically.
    ExpectedCountEncoding,
    /// At least one expected program is required for a bundle.
    ExpectedEmpty,
    /// Bundle header is truncated before complete canonical framing exists.
    Header,
    /// Bundle magic is not the canonical register-masked AOT bundle marker.
    Magic,
    /// One object payload is truncated or its length cannot be represented.
    ObjectBytes {
        /// Zero-based expected object index.
        index: usize,
    },
    /// One object length prefix is truncated.
    ObjectLength {
        /// Zero-based expected object index.
        index: usize,
    },
    /// Bytes remain after the exact caller-owned expected object sequence.
    Trailing,
    /// Bundle schema version is not supported.
    Version {
        /// Persisted unsupported bundle version.
        observed: u16,
    },
}

/// Result of one bounded durable bundle restoration.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum RegisterMaskedAotBundlePersistenceLoad {
    /// No bundle currently exists at the adapter-configured location.
    Missing,
    /// Every stored object rebuilt current exact-key object-only authority.
    Restored {
        /// Exact opaque bundle byte count returned by bounded blob loading.
        bytes: usize,
        /// Exact number of ordered object payloads independently reverified.
        objects: usize,
        /// Fresh sealed AOT set rebuilt only after complete bundle
        /// verification.
        set: VerifiedAheadOfExecutionRegisterMaskedSet,
    },
}

/// Why a complete AOT bundle could not be prepared for publication.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum RegisterMaskedAotBundlePreparationError<'requirement> {
    /// Canonical framing would exceed the caller's positive byte bound.
    ByteLimit {
        /// Positive caller-configured bundle byte limit.
        maximum_bytes: NonZeroUsize,
        /// Exact size required through the object that crossed the bound.
        observed_bytes: usize,
    },
    /// Program count cannot be represented in canonical bundle framing.
    CountEncoding,
    /// At least one expected program is required for a bundle.
    Empty,
    /// The selected host has no direct object format for one expected program.
    Interpreter {
        /// Zero-based expected program index.
        index: usize,
    },
    /// Read-only AOT selection rejected one expected program or identity.
    Selection {
        /// Exact selection failure.
        error: Box<AheadOfExecutionRegisterMaskedSelectionError<'requirement>>,
        /// Zero-based expected program index.
        index: usize,
    },
    /// Framing arithmetic or object length representation overflowed.
    SizeEncoding {
        /// Zero-based expected program index.
        index: usize,
    },
    /// The sealed set does not contain one expected exact program artifact.
    Uncovered {
        /// Zero-based expected program index.
        index: usize,
    },
}

/// Why one persisted bundle failed to rebuild complete current native
/// authority.
#[derive(Debug, Eq, PartialEq)]
pub enum RegisterMaskedAotBundleRestorePersistenceError<
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
    /// Persisted bundle framing does not match caller-owned expectations.
    Framing(RegisterMaskedAotBundleFramingError),
    /// One stored object failed current native admission or verification.
    Native {
        /// Exact current native restore failure.
        error:
            Box<AheadOfExecutionRegisterMaskedObjectRestoreError<'requirement>>,
        /// Zero-based expected program/object index.
        index: usize,
    },
}

/// Why complete bundle publication failed before any replacement was claimed.
#[derive(Debug, Eq, PartialEq)]
pub enum RegisterMaskedAotBundleStoreError<'requirement, StoreError> {
    /// Bounded opaque-blob orchestration or outbound storage failed.
    Blob(
        Box<
            blob_persistence::NativeContinuationBlobPersistenceError<
                StoreError,
            >,
        >,
    ),
    /// Complete bundle preparation failed before publication.
    Preparation(Box<RegisterMaskedAotBundlePreparationError<'requirement>>),
}

/// Caller authority required to publish one complete ordered AOT bundle.
#[derive(Clone, Copy, Debug)]
pub struct RegisterMaskedAotBundlePersistRequest<'requirement> {
    maximum_bytes: NonZeroUsize,
    source: RegisterMaskedAotBundleSource<'requirement>,
}

/// Caller authority required to restore one complete ordered AOT bundle.
#[derive(Clone, Copy, Debug)]
pub struct RegisterMaskedAotBundleRestoreRequest<'requirement> {
    host: DirectHost,
    maximum_bytes: NonZeroUsize,
    programs: &'requirement [RegisterMaskedRegionEffectProgram],
    runtime: &'static RuntimeCapability,
}

/// Caller-owned exact native source for one ordered AOT bundle.
#[derive(Clone, Copy, Debug)]
pub struct RegisterMaskedAotBundleSource<'requirement> {
    aot: &'requirement VerifiedAheadOfExecutionRegisterMaskedSet,
    host: DirectHost,
    programs: &'requirement [RegisterMaskedRegionEffectProgram],
    runtime: &'static RuntimeCapability,
}

/// Durable bundle publication result specialized to one outbound store type.
pub type RegisterMaskedAotBundleDurableStoreResult<'requirement, Store> =
    RegisterMaskedAotBundleStoreResult<
        'requirement,
        blob_persistence::NativeContinuationBlobDurablePersistence<
            <Store as DurableBlobStore>::DurabilityError,
        >,
        <Store as BlobStore>::Error,
    >;

/// Result of one typed bundle restoration.
pub type RegisterMaskedAotBundleRestoreResult<'requirement, Value, StoreError> =
    Result<
        Value,
        RegisterMaskedAotBundleRestorePersistenceError<
            'requirement,
            StoreError,
        >,
    >;

/// Result of one typed bundle publication.
pub type RegisterMaskedAotBundleStoreResult<'requirement, Value, StoreError> =
    Result<Value, RegisterMaskedAotBundleStoreError<'requirement, StoreError>>;

impl<'requirement> RegisterMaskedAotBundlePersistRequest<'requirement> {
    /// Binds one exact native bundle source to a positive storage byte bound.
    #[must_use]
    pub const fn new(
        source: RegisterMaskedAotBundleSource<'requirement>,
        maximum_bytes: NonZeroUsize,
    ) -> Self {
        Self { maximum_bytes, source }
    }
}

impl<'requirement> RegisterMaskedAotBundleRestoreRequest<'requirement> {
    /// Binds exact expected programs/current native assumptions and byte bound.
    #[must_use]
    pub const fn new(
        programs: &'requirement [RegisterMaskedRegionEffectProgram],
        runtime: &'static RuntimeCapability,
        host: DirectHost,
        maximum_bytes: NonZeroUsize,
    ) -> Self {
        Self {
            host,
            maximum_bytes,
            programs,
            runtime,
        }
    }
}

impl<'requirement> RegisterMaskedAotBundleSource<'requirement> {
    /// Binds exact expected programs to one sealed AOT/native environment.
    #[must_use]
    pub const fn new(
        programs: &'requirement [RegisterMaskedRegionEffectProgram],
        aot: &'requirement VerifiedAheadOfExecutionRegisterMaskedSet,
        runtime: &'static RuntimeCapability,
        host: DirectHost,
    ) -> Self {
        Self {
            aot,
            host,
            programs,
            runtime,
        }
    }
}

/// Atomically persists one complete ordered AOT object bundle.
///
/// All expected artifacts are selected read-only and framed before the single
/// blob replacement. Therefore a missing/rejected later object cannot publish a
/// prefix from this call.
///
/// # Errors
///
/// Returns preparation, byte-bound, or outbound-store failure before claiming
/// complete bundle publication.
pub fn persist_register_masked_aot_bundle<'requirement, Store>(
    store: &mut Store,
    request: RegisterMaskedAotBundlePersistRequest<'requirement>,
) -> RegisterMaskedAotBundleStoreResult<
    'requirement,
    blob_persistence::NativeContinuationBlobPersistenceWrite,
    Store::Error,
>
where
    Store: BlobStore,
{
    let bytes = encode_bundle(request).map_err(|error| {
        RegisterMaskedAotBundleStoreError::Preparation(Box::new(error))
    })?;
    blob_persistence::persist_blob(store, &bytes, request.maximum_bytes)
        .map_err(|error| {
            RegisterMaskedAotBundleStoreError::Blob(Box::new(error))
        })
}

/// Atomically persists one complete ordered AOT bundle and confirms durability.
///
/// # Errors
///
/// Returns preparation, byte-bound, or store failure before publication. A
/// durability-confirmation failure remains committed `Published` evidence.
pub fn persist_register_masked_aot_bundle_durably<'requirement, Store>(
    store: &mut Store,
    request: RegisterMaskedAotBundlePersistRequest<'requirement>,
) -> RegisterMaskedAotBundleDurableStoreResult<'requirement, Store>
where
    Store: DurableBlobStore,
{
    let bytes = encode_bundle(request).map_err(|error| {
        RegisterMaskedAotBundleStoreError::Preparation(Box::new(error))
    })?;
    blob_persistence::persist_blob_durably(store, &bytes, request.maximum_bytes)
        .map_err(|error| {
            RegisterMaskedAotBundleStoreError::Blob(Box::new(error))
        })
}

/// Restores one atomic ordered bundle and publishes no partial verified set.
///
/// Persisted framing supplies only object boundaries. The expected ordered IR,
/// runtime capability, and host all come from the caller; every payload reruns
/// current structural and canonical-byte verification before the set is sealed.
///
/// # Errors
///
/// Returns store/byte-limit, framing, or indexed native verification failure.
pub fn restore_register_masked_aot_bundle<'requirement, Store>(
    store: &mut Store,
    request: RegisterMaskedAotBundleRestoreRequest<'requirement>,
) -> RegisterMaskedAotBundleRestoreResult<
    'requirement,
    RegisterMaskedAotBundlePersistenceLoad,
    Store::Error,
>
where
    Store: BlobStore,
{
    let _expected_count = admit_expected_program_count(request.programs)
        .map_err(RegisterMaskedAotBundleRestorePersistenceError::Framing)?;
    let load = blob_persistence::restore_blob(store, request.maximum_bytes)
        .map_err(|error| {
            RegisterMaskedAotBundleRestorePersistenceError::Blob(Box::new(
                error,
            ))
        })?;
    let blob_persistence::NativeContinuationBlobPersistenceLoad::Present {
        bytes,
    } = load
    else {
        return Ok(RegisterMaskedAotBundlePersistenceLoad::Missing);
    };
    decode_bundle(&bytes, request)
}

fn admit_expected_program_count(
    programs: &[RegisterMaskedRegionEffectProgram],
) -> Result<u32, RegisterMaskedAotBundleFramingError> {
    if programs.is_empty() {
        return Err(RegisterMaskedAotBundleFramingError::ExpectedEmpty);
    }
    u32::try_from(programs.len()).map_err(|_error| {
        RegisterMaskedAotBundleFramingError::ExpectedCountEncoding
    })
}

fn append_object(
    output: &mut Vec<u8>,
    object: &[u8],
    index: usize,
    maximum_bytes: NonZeroUsize,
) -> Result<(), BundleAppendError> {
    let object_length = u64::try_from(object.len())
        .map_err(|_error| BundleAppendError::SizeEncoding { index })?;
    let next_length = output
        .len()
        .checked_add(OBJECT_LENGTH_BYTES)
        .and_then(|length| length.checked_add(object.len()))
        .ok_or(BundleAppendError::SizeEncoding { index })?;
    if next_length > maximum_bytes.get() {
        return Err(BundleAppendError::ByteLimit {
            maximum_bytes,
            observed_bytes: next_length,
        });
    }
    output.extend_from_slice(&object_length.to_le_bytes());
    output.extend_from_slice(object);
    Ok(())
}

fn decode_bundle<'requirement, StoreError>(
    bytes: &[u8],
    request: RegisterMaskedAotBundleRestoreRequest<'requirement>,
) -> RegisterMaskedAotBundleRestoreResult<
    'requirement,
    RegisterMaskedAotBundlePersistenceLoad,
    StoreError,
> {
    decode_bundle_header(bytes, request.programs)
        .map_err(RegisterMaskedAotBundleRestorePersistenceError::Framing)?;
    let mut artifacts = Vec::with_capacity(request.programs.len());
    let mut offset = BUNDLE_HEADER_BYTES;
    for (index, program) in request.programs.iter().enumerate() {
        let (object, next_offset) = decode_object(bytes, offset, index)
            .map_err(RegisterMaskedAotBundleRestorePersistenceError::Framing)?;
        let artifact = restore_ahead_of_execution_register_masked_object(
            program,
            request.runtime,
            request.host,
            object.to_vec(),
        )
        .map_err(|error| {
            RegisterMaskedAotBundleRestorePersistenceError::Native {
                error: Box::new(error),
                index,
            }
        })?;
        artifacts.push(artifact);
        offset = next_offset;
    }
    if offset != bytes.len() {
        return Err(RegisterMaskedAotBundleRestorePersistenceError::Framing(
            RegisterMaskedAotBundleFramingError::Trailing,
        ));
    }
    Ok(RegisterMaskedAotBundlePersistenceLoad::Restored {
        bytes: bytes.len(),
        objects: request.programs.len(),
        set: VerifiedAheadOfExecutionRegisterMaskedSet::from_verified_artifacts(
            artifacts,
        ),
    })
}

fn decode_bundle_header(
    bytes: &[u8],
    programs: &[RegisterMaskedRegionEffectProgram],
) -> Result<(), RegisterMaskedAotBundleFramingError> {
    let header = bytes
        .get(..BUNDLE_HEADER_BYTES)
        .ok_or(RegisterMaskedAotBundleFramingError::Header)?;
    if header.get(..4) != Some(BUNDLE_MAGIC) {
        return Err(RegisterMaskedAotBundleFramingError::Magic);
    }
    let version_bytes: [u8; 2] = header
        .get(4..6)
        .and_then(|value| value.try_into().ok())
        .ok_or(RegisterMaskedAotBundleFramingError::Header)?;
    let version = u16::from_le_bytes(version_bytes);
    if version != BUNDLE_VERSION {
        return Err(RegisterMaskedAotBundleFramingError::Version {
            observed: version,
        });
    }
    let count_bytes: [u8; 4] = header
        .get(6..10)
        .and_then(|value| value.try_into().ok())
        .ok_or(RegisterMaskedAotBundleFramingError::Header)?;
    let observed = u32::from_le_bytes(count_bytes);
    let expected = admit_expected_program_count(programs)?;
    if observed == expected {
        Ok(())
    } else {
        Err(RegisterMaskedAotBundleFramingError::CountMismatch {
            expected: programs.len(),
            observed,
        })
    }
}

fn decode_object(
    bytes: &[u8],
    offset: usize,
    index: usize,
) -> Result<DecodedObject<'_>, RegisterMaskedAotBundleFramingError> {
    let length_end = offset
        .checked_add(OBJECT_LENGTH_BYTES)
        .ok_or(RegisterMaskedAotBundleFramingError::ObjectLength { index })?;
    let length_bytes = bytes
        .get(offset..length_end)
        .ok_or(RegisterMaskedAotBundleFramingError::ObjectLength { index })?;
    let length_array: [u8; 8] = length_bytes.try_into().map_err(|_error| {
        RegisterMaskedAotBundleFramingError::ObjectLength { index }
    })?;
    let encoded_length = u64::from_le_bytes(length_array);
    let object_length = usize::try_from(encoded_length).map_err(|_error| {
        RegisterMaskedAotBundleFramingError::ObjectBytes { index }
    })?;
    let object_end = length_end
        .checked_add(object_length)
        .ok_or(RegisterMaskedAotBundleFramingError::ObjectBytes { index })?;
    let object = bytes
        .get(length_end..object_end)
        .ok_or(RegisterMaskedAotBundleFramingError::ObjectBytes { index })?;
    Ok((object, object_end))
}

fn encode_bundle(
    request: RegisterMaskedAotBundlePersistRequest<'_>,
) -> Result<Vec<u8>, RegisterMaskedAotBundlePreparationError<'_>> {
    if request.source.programs.is_empty() {
        return Err(RegisterMaskedAotBundlePreparationError::Empty);
    }
    let count =
        u32::try_from(request.source.programs.len()).map_err(|_error| {
            RegisterMaskedAotBundlePreparationError::CountEncoding
        })?;
    if BUNDLE_HEADER_BYTES > request.maximum_bytes.get() {
        return Err(RegisterMaskedAotBundlePreparationError::ByteLimit {
            maximum_bytes: request.maximum_bytes,
            observed_bytes: BUNDLE_HEADER_BYTES,
        });
    }
    let mut output = Vec::new();
    output.extend_from_slice(BUNDLE_MAGIC);
    output.extend_from_slice(&BUNDLE_VERSION.to_le_bytes());
    output.extend_from_slice(&count.to_le_bytes());
    for (index, program) in request.source.programs.iter().enumerate() {
        let artifact = select_bundle_artifact(request, index, program)?;
        append_object(
            &mut output,
            artifact.object(),
            index,
            request.maximum_bytes,
        )
        .map_err(map_append_error)?;
    }
    Ok(output)
}

const fn map_append_error<'requirement>(
    error: BundleAppendError,
) -> RegisterMaskedAotBundlePreparationError<'requirement> {
    match error {
        BundleAppendError::ByteLimit {
            maximum_bytes,
            observed_bytes,
        } => RegisterMaskedAotBundlePreparationError::ByteLimit {
            maximum_bytes,
            observed_bytes,
        },
        BundleAppendError::SizeEncoding { index } => {
            RegisterMaskedAotBundlePreparationError::SizeEncoding { index }
        },
    }
}

fn select_bundle_artifact<'requirement>(
    request: RegisterMaskedAotBundlePersistRequest<'requirement>,
    index: usize,
    program: &'requirement RegisterMaskedRegionEffectProgram,
) -> Result<
    Arc<VerifiedAheadOfExecutionRegisterMaskedArtifact>,
    RegisterMaskedAotBundlePreparationError<'requirement>,
> {
    let selected = select_ahead_of_execution_register_masked_tier(
        program,
        request.source.runtime,
        request.source.host,
        request.source.aot,
    )
    .map_err(|error| {
        RegisterMaskedAotBundlePreparationError::Selection {
            error: Box::new(error),
            index,
        }
    })?;
    match selected {
        AheadOfExecutionRegisterMaskedTier::Direct(artifact) => Ok(artifact),
        AheadOfExecutionRegisterMaskedTier::Interpreter => {
            Err(RegisterMaskedAotBundlePreparationError::Interpreter { index })
        },
        AheadOfExecutionRegisterMaskedTier::Uncovered => {
            Err(RegisterMaskedAotBundlePreparationError::Uncovered { index })
        },
    }
}
