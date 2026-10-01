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
//   - Canonical durable journaling of caller-supplied executable lease owners.
// - Must-Not:
//   - Generate owner identifiers, infer artifact identity, expire leases,
//     choose storage paths, own executable mappings, or schedule retries.
// - Allows:
//   - Inputs: one preconfigured blob store, exact owner IDs, positive owner and
//     byte bounds, and caller-selected expected/replacement registries.
//   - Outputs: bounded restore state or exact durable CAS evidence.
//   - Side effects: delegated bounded blob load or conditional publication.
// - Split-When:
//   - Artifact-key binding, lease expiry, or distributed recovery gains
//     independent authority.
// - Merge-When:
//   - One cache lifecycle owner subsumes durable lease reconciliation.
// - Summary:
//   - Coordinates exact cross-process lease ownership without temporal policy.
// - Description:
//   - Storage location identifies the leased subject; this journal records only
//     opaque owners and never grants executable authority.
// - Usage:
//   - Restore, mutate a registry locally, then publish with exact expected CAS.
// - Defaults:
//   - Missing durable state means no journal; an explicit empty registry is
//     valid and distinct from missing state.
//
//! Durable optimistic-concurrency journal for executable lease owners.

use std::num::NonZeroUsize;

use crate::blob_persistence::{
    NativeContinuationBlobConditionalDurablePersistence,
    NativeContinuationBlobPersistenceError,
    NativeContinuationBlobPersistenceLoad, compare_and_swap_blob_durably,
    restore_blob,
};
use crate::blob_store::{
    NativeContinuationBlobStore as BlobStore,
    NativeContinuationConditionalBlobStore as ConditionalBlobStore,
    NativeContinuationDurableBlobStore as DurableBlobStore,
};

const HEADER_BYTES: usize = 16;
const JOURNAL_MAGIC: [u8; 8] = *b"MBLSE001";
const OWNER_BYTES: usize = 16;

/// Opaque caller-supplied identity for one cooperating lease owner.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct NativeExecutableDurableLeaseOwnerId([u8; OWNER_BYTES]);

/// Exact sorted set of owners retaining one caller-selected durable subject.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeExecutableDurableLeaseRegistry {
    owners: Vec<NativeExecutableDurableLeaseOwnerId>,
}

/// Bounded decoder policy for one durable lease journal.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeExecutableDurableLeaseRegistryDecodeLimits {
    maximum_owners: NonZeroUsize,
}

/// Caller-bound inputs for one exact durable lease-journal CAS.
#[derive(Clone, Copy, Debug)]
pub struct NativeExecutableDurableLeaseJournalCasRequest<'registry> {
    decode_limits: NativeExecutableDurableLeaseRegistryDecodeLimits,
    expected: Option<&'registry NativeExecutableDurableLeaseRegistry>,
    maximum_bytes: NonZeroUsize,
    replacement: &'registry NativeExecutableDurableLeaseRegistry,
}

/// Why canonical durable lease bytes failed closed.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeExecutableDurableLeaseRegistryCodecError {
    /// Canonical journal magic did not identify the supported format.
    Magic,
    /// Registry cardinality cannot fit the canonical 32-bit count field.
    OwnerCountOverflow {
        /// Exact in-memory owner count.
        observed_owners: usize,
    },
    /// Canonical owner count exceeds the configured positive decoder bound.
    OwnerLimit {
        /// Positive configured owner-count bound.
        maximum_owners: NonZeroUsize,
        /// Exact owner count claimed by the journal.
        observed_owners: usize,
    },
    /// Owner IDs were duplicated or not in strict ascending canonical order.
    OwnerOrder,
    /// Reserved canonical header bytes were nonzero.
    Reserved,
    /// Canonical length did not match the owner count.
    Size {
        /// Exact observed byte count.
        observed_bytes: usize,
    },
}

/// Why one local owner insertion failed before durable publication.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeExecutableDurableLeaseRegistryCapacityError {
    maximum_owners: NonZeroUsize,
    observed_owners: usize,
}

/// Typed durable lease-journal load.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeExecutableDurableLeaseJournalLoad {
    /// No durable lease journal exists at the configured location.
    Missing,
    /// One canonical lease registry was restored.
    Present {
        /// Exact decoded lease registry.
        registry: NativeExecutableDurableLeaseRegistry,
    },
}

/// Typed outcome of one exact durable lease-registry CAS publication.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeExecutableDurableLeaseJournalCas<DurabilityError> {
    /// Expected journal differed; no publication occurred.
    Conflict {
        /// Exact typed current durable registry, or absence.
        current: Option<NativeExecutableDurableLeaseRegistry>,
    },
    /// Replacement committed and durability confirmation completed.
    Durable {
        /// Exact committed canonical byte count.
        bytes: usize,
    },
    /// Replacement committed, then durability confirmation failed.
    Published {
        /// Exact committed canonical byte count.
        bytes: usize,
        /// Exact post-publication durability failure.
        durability_error: DurabilityError,
    },
}

/// Why typed durable lease journal orchestration failed closed.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeExecutableDurableLeaseJournalError<StoreError> {
    /// Generic bounded blob persistence failed before typed decoding completed.
    Blob(NativeContinuationBlobPersistenceError<StoreError>),
    /// Canonical lease-journal bytes were invalid.
    Codec(NativeExecutableDurableLeaseRegistryCodecError),
}

/// Generic typed lease-journal result specialized to one blob store.
pub type NativeExecutableDurableLeaseJournalStoreResult<Store, Value> = Result<
    Value,
    NativeExecutableDurableLeaseJournalError<<Store as BlobStore>::Error>,
>;

/// Durable lease-journal CAS result specialized to one blob store.
pub type NativeExecutableDurableLeaseJournalCasStoreResult<Store> =
    NativeExecutableDurableLeaseJournalStoreResult<
        Store,
        NativeExecutableDurableLeaseJournalCas<
            <Store as DurableBlobStore>::DurabilityError,
        >,
    >;

impl NativeExecutableDurableLeaseOwnerId {
    /// Returns the exact opaque owner bytes.
    #[must_use]
    pub const fn bytes(self) -> [u8; OWNER_BYTES] {
        self.0
    }

    /// Constructs one opaque owner ID supplied by caller coordination.
    #[must_use]
    pub const fn new(bytes: [u8; OWNER_BYTES]) -> Self {
        Self(bytes)
    }
}

impl NativeExecutableDurableLeaseRegistry {
    /// Acquires one exact owner locally before caller-selected CAS publication.
    ///
    /// # Errors
    ///
    /// Returns capacity failure when insertion would exceed the positive owner
    /// bound. Existing membership is idempotent and does not consume capacity.
    pub fn acquire(
        &mut self,
        owner: NativeExecutableDurableLeaseOwnerId,
        maximum_owners: NonZeroUsize,
    ) -> Result<bool, NativeExecutableDurableLeaseRegistryCapacityError> {
        match self.owners.binary_search(&owner) {
            Ok(_index) => Ok(false),
            Err(index) => {
                let observed_owners = self.owners.len().saturating_add(1);
                if observed_owners > maximum_owners.get() {
                    return Err(
                        NativeExecutableDurableLeaseRegistryCapacityError {
                            maximum_owners,
                            observed_owners,
                        },
                    );
                }
                self.owners.insert(index, owner);
                Ok(true)
            },
        }
    }

    /// Reports whether one exact owner is currently retained.
    #[must_use]
    pub fn contains(&self, owner: NativeExecutableDurableLeaseOwnerId) -> bool {
        self.owners.binary_search(&owner).is_ok()
    }

    /// Reports whether this explicit registry retains no owners.
    #[must_use]
    pub const fn is_empty(&self) -> bool {
        self.owners.is_empty()
    }

    /// Returns exact retained owner count.
    #[must_use]
    pub const fn len(&self) -> usize {
        self.owners.len()
    }

    /// Constructs an explicit empty lease registry.
    #[must_use]
    pub const fn new() -> Self {
        Self { owners: Vec::new() }
    }

    /// Borrows owners in canonical strict ascending order.
    #[must_use]
    pub fn owners(&self) -> &[NativeExecutableDurableLeaseOwnerId] {
        &self.owners
    }

    /// Releases one exact owner locally before caller-selected CAS publication.
    pub fn release(
        &mut self,
        owner: NativeExecutableDurableLeaseOwnerId,
    ) -> bool {
        let Ok(index) = self.owners.binary_search(&owner) else {
            return false;
        };
        let _removed = self.owners.remove(index);
        true
    }
}

impl Default for NativeExecutableDurableLeaseRegistry {
    fn default() -> Self {
        Self::new()
    }
}

impl NativeExecutableDurableLeaseRegistryCapacityError {
    /// Returns the positive owner bound that rejected insertion.
    #[must_use]
    pub const fn maximum_owners(self) -> NonZeroUsize {
        self.maximum_owners
    }

    /// Returns exact owner count the rejected insertion would have produced.
    #[must_use]
    pub const fn observed_owners(self) -> usize {
        self.observed_owners
    }
}

impl NativeExecutableDurableLeaseRegistryDecodeLimits {
    /// Returns the positive maximum decoded owner count.
    #[must_use]
    pub const fn maximum_owners(self) -> NonZeroUsize {
        self.maximum_owners
    }

    /// Binds one positive maximum owner count to canonical decoding.
    #[must_use]
    pub const fn new(maximum_owners: NonZeroUsize) -> Self {
        Self { maximum_owners }
    }
}

impl<'registry> NativeExecutableDurableLeaseJournalCasRequest<'registry> {
    /// Binds expected/replacement registries and explicit decode/byte bounds.
    #[must_use]
    pub const fn new(
        expected: Option<&'registry NativeExecutableDurableLeaseRegistry>,
        replacement: &'registry NativeExecutableDurableLeaseRegistry,
        decode_limits: NativeExecutableDurableLeaseRegistryDecodeLimits,
        maximum_bytes: NonZeroUsize,
    ) -> Self {
        Self {
            decode_limits,
            expected,
            maximum_bytes,
            replacement,
        }
    }
}

/// Encodes one exact lease registry into canonical sorted fixed-width bytes.
///
/// # Errors
///
/// Returns owner-count overflow if cardinality cannot fit the canonical count.
pub fn encode_executable_durable_lease_registry(
    registry: &NativeExecutableDurableLeaseRegistry,
) -> Result<Vec<u8>, NativeExecutableDurableLeaseRegistryCodecError> {
    let owner_count =
        u32::try_from(registry.owners.len()).map_err(|_error| {
            NativeExecutableDurableLeaseRegistryCodecError::OwnerCountOverflow {
                observed_owners: registry.owners.len(),
            }
        })?;
    let capacity = HEADER_BYTES
        .checked_add(registry.owners.len().saturating_mul(OWNER_BYTES))
        .ok_or(NativeExecutableDurableLeaseRegistryCodecError::Size {
            observed_bytes: usize::MAX,
        })?;
    let mut bytes = Vec::with_capacity(capacity);
    bytes.extend_from_slice(&JOURNAL_MAGIC);
    bytes.extend_from_slice(&owner_count.to_le_bytes());
    bytes.extend_from_slice(&[0; 4]);
    for owner in &registry.owners {
        bytes.extend_from_slice(&owner.bytes());
    }
    Ok(bytes)
}

/// Decodes one canonical lease registry under an explicit owner bound.
///
/// # Errors
///
/// Rejects wrong magic/length, nonzero reserved bytes, owner-count overflow,
/// owner-count excess, duplicates, or noncanonical owner ordering.
pub fn decode_executable_durable_lease_registry(
    bytes: &[u8],
    limits: NativeExecutableDurableLeaseRegistryDecodeLimits,
) -> Result<
    NativeExecutableDurableLeaseRegistry,
    NativeExecutableDurableLeaseRegistryCodecError,
> {
    use NativeExecutableDurableLeaseRegistryCodecError as CodecError;

    if bytes.len() < HEADER_BYTES {
        return Err(CodecError::Size {
            observed_bytes: bytes.len(),
        });
    }
    if bytes.get(..8) != Some(JOURNAL_MAGIC.as_slice()) {
        return Err(CodecError::Magic);
    }
    if bytes.get(12..HEADER_BYTES) != Some([0; 4].as_slice()) {
        return Err(CodecError::Reserved);
    }
    let count_bytes: [u8; 4] = bytes
        .get(8..12)
        .ok_or(CodecError::Size {
            observed_bytes: bytes.len(),
        })?
        .try_into()
        .map_err(|_error| CodecError::Size {
            observed_bytes: bytes.len(),
        })?;
    let observed_owners = usize::try_from(u32::from_le_bytes(count_bytes))
        .map_err(|_error| CodecError::OwnerCountOverflow {
            observed_owners: usize::MAX,
        })?;
    if observed_owners > limits.maximum_owners.get() {
        return Err(CodecError::OwnerLimit {
            maximum_owners: limits.maximum_owners,
            observed_owners,
        });
    }
    let expected_bytes = observed_owners
        .checked_mul(OWNER_BYTES)
        .and_then(|owner_bytes| HEADER_BYTES.checked_add(owner_bytes))
        .ok_or(CodecError::Size {
            observed_bytes: bytes.len(),
        })?;
    if bytes.len() != expected_bytes {
        return Err(CodecError::Size {
            observed_bytes: bytes.len(),
        });
    }
    let owner_region = bytes.get(HEADER_BYTES..).ok_or(CodecError::Size {
        observed_bytes: bytes.len(),
    })?;
    let (owner_chunks, remainder) = owner_region.as_chunks::<OWNER_BYTES>();
    if !remainder.is_empty() {
        return Err(CodecError::Size {
            observed_bytes: bytes.len(),
        });
    }
    let mut owners = Vec::with_capacity(observed_owners);
    for chunk in owner_chunks {
        let owner = NativeExecutableDurableLeaseOwnerId::new(*chunk);
        if owners.last().is_some_and(|previous| previous >= &owner) {
            return Err(CodecError::OwnerOrder);
        }
        owners.push(owner);
    }
    Ok(NativeExecutableDurableLeaseRegistry { owners })
}

/// Conditionally persists one exact lease registry and confirms durability.
///
/// Storage location is the lease-subject identity. The journal itself contains
/// only exact owner IDs. Conflict is typed non-mutating evidence.
///
/// # Errors
///
/// Returns canonical encoding/decoding or bounded/store failure. Durability
/// failure after publication remains committed publication evidence.
pub fn compare_and_swap_executable_durable_lease_journal<Store>(
    store: &mut Store,
    request: NativeExecutableDurableLeaseJournalCasRequest<'_>,
) -> NativeExecutableDurableLeaseJournalCasStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    let expected_bytes = request
        .expected
        .map(encode_executable_durable_lease_registry)
        .transpose()
        .map_err(NativeExecutableDurableLeaseJournalError::Codec)?;
    let replacement_bytes =
        encode_executable_durable_lease_registry(request.replacement)
            .map_err(NativeExecutableDurableLeaseJournalError::Codec)?;
    let outcome = compare_and_swap_blob_durably(
        store,
        expected_bytes.as_deref(),
        &replacement_bytes,
        request.maximum_bytes,
    )
    .map_err(NativeExecutableDurableLeaseJournalError::Blob)?;
    match outcome {
        NativeContinuationBlobConditionalDurablePersistence::Conflict {
            current,
        } => Ok(NativeExecutableDurableLeaseJournalCas::Conflict {
            current: current
                .as_deref()
                .map(|bytes| {
                    decode_executable_durable_lease_registry(
                        bytes,
                        request.decode_limits,
                    )
                })
                .transpose()
                .map_err(NativeExecutableDurableLeaseJournalError::Codec)?,
        }),
        NativeContinuationBlobConditionalDurablePersistence::Durable {
            write,
        } => Ok(NativeExecutableDurableLeaseJournalCas::Durable {
            bytes: write.bytes(),
        }),
        NativeContinuationBlobConditionalDurablePersistence::Published {
            durability_error,
            write,
        } => Ok(NativeExecutableDurableLeaseJournalCas::Published {
            bytes: write.bytes(),
            durability_error,
        }),
    }
}

/// Restores one bounded exact durable lease journal.
///
/// # Errors
///
/// Returns bounded/store failure or malformed canonical journal evidence.
pub fn restore_executable_durable_lease_journal<Store>(
    store: &mut Store,
    decode_limits: NativeExecutableDurableLeaseRegistryDecodeLimits,
    maximum_bytes: NonZeroUsize,
) -> NativeExecutableDurableLeaseJournalStoreResult<
    Store,
    NativeExecutableDurableLeaseJournalLoad,
>
where
    Store: BlobStore,
{
    let load = restore_blob(store, maximum_bytes)
        .map_err(NativeExecutableDurableLeaseJournalError::Blob)?;
    let NativeContinuationBlobPersistenceLoad::Present { bytes } = load else {
        return Ok(NativeExecutableDurableLeaseJournalLoad::Missing);
    };
    let registry =
        decode_executable_durable_lease_registry(&bytes, decode_limits)
            .map_err(NativeExecutableDurableLeaseJournalError::Codec)?;
    Ok(NativeExecutableDurableLeaseJournalLoad::Present { registry })
}

#[cfg(test)]
mod tests {
    use std::fs::{create_dir_all, remove_dir_all};
    use std::io::ErrorKind;
    use std::{env, process};

    use super::*;
    use crate::file_blob_store::NativeContinuationFileBlobStore;

    type TestResult = Result<(), String>;

    fn decode_limits(
        maximum: usize,
    ) -> Result<NativeExecutableDurableLeaseRegistryDecodeLimits, String> {
        NonZeroUsize::new(maximum)
            .map(NativeExecutableDurableLeaseRegistryDecodeLimits::new)
            .ok_or_else(|| String::from("test owner limit missing"))
    }

    fn maximum_bytes() -> Result<NonZeroUsize, String> {
        NonZeroUsize::new(4096)
            .ok_or_else(|| String::from("test byte limit missing"))
    }

    const fn owner(value: u8) -> NativeExecutableDurableLeaseOwnerId {
        NativeExecutableDurableLeaseOwnerId::new([value; OWNER_BYTES])
    }

    #[test]
    fn canonical_codec_round_trip_is_sorted() -> TestResult {
        let mut registry = NativeExecutableDurableLeaseRegistry::new();
        let _first = registry
            .acquire(owner(9), NonZeroUsize::new(4).ok_or("owner bound")?)
            .map_err(|error| format!("{error:?}"))?;
        let _second = registry
            .acquire(owner(2), NonZeroUsize::new(4).ok_or("owner bound")?)
            .map_err(|error| format!("{error:?}"))?;
        let bytes = encode_executable_durable_lease_registry(&registry)
            .map_err(|error| format!("{error:?}"))?;
        let decoded =
            decode_executable_durable_lease_registry(&bytes, decode_limits(4)?)
                .map_err(|error| format!("{error:?}"))?;
        if decoded == registry
            && decoded.owners() == [owner(2), owner(9)].as_slice()
        {
            Ok(())
        } else {
            Err(String::from("lease registry canonical round trip drifted"))
        }
    }

    #[test]
    fn decoder_rejects_noncanonical_owner_order() -> TestResult {
        let mut registry = NativeExecutableDurableLeaseRegistry::new();
        let bound = NonZeroUsize::new(4).ok_or("owner bound")?;
        let _first = registry
            .acquire(owner(2), bound)
            .map_err(|error| format!("{error:?}"))?;
        let _second = registry
            .acquire(owner(9), bound)
            .map_err(|error| format!("{error:?}"))?;
        let mut bytes = encode_executable_durable_lease_registry(&registry)
            .map_err(|error| format!("{error:?}"))?;
        bytes[HEADER_BYTES..HEADER_BYTES + OWNER_BYTES]
            .copy_from_slice(&owner(9).bytes());
        bytes[HEADER_BYTES + OWNER_BYTES..].copy_from_slice(&owner(2).bytes());
        let result =
            decode_executable_durable_lease_registry(&bytes, decode_limits(4)?);
        if result
            == Err(NativeExecutableDurableLeaseRegistryCodecError::OwnerOrder)
        {
            Ok(())
        } else {
            Err(String::from("noncanonical lease owners were admitted"))
        }
    }

    #[test]
    fn file_journal_coordinates_acquire_release_and_conflict() -> TestResult {
        let directory = env::temp_dir()
            .join(format!("malbolge-durable-lease-journal-{}", process::id(),));
        match remove_dir_all(&directory) {
            Ok(()) => {},
            Err(error) if error.kind() == ErrorKind::NotFound => {},
            Err(error) => {
                return Err(format!("test cleanup failed: {error}"));
            },
        }
        create_dir_all(&directory)
            .map_err(|error| format!("test create failed: {error}"))?;
        let destination = directory.join("leases.bin");
        let mut first_store =
            NativeContinuationFileBlobStore::new(destination.clone());
        let mut second_store =
            NativeContinuationFileBlobStore::new(destination);
        let limits = decode_limits(8)?;
        let bytes = maximum_bytes()?;
        let empty = NativeExecutableDurableLeaseRegistry::new();
        let mut one = empty.clone();
        let _acquired = one
            .acquire(owner(1), limits.maximum_owners())
            .map_err(|error| format!("{error:?}"))?;
        let initialized = compare_and_swap_executable_durable_lease_journal(
            &mut first_store,
            NativeExecutableDurableLeaseJournalCasRequest::new(
                None, &one, limits, bytes,
            ),
        )
        .map_err(|error| format!("{error:?}"))?;
        let mut two = one.clone();
        let _acquired = two
            .acquire(owner(2), limits.maximum_owners())
            .map_err(|error| format!("{error:?}"))?;
        let expanded = compare_and_swap_executable_durable_lease_journal(
            &mut second_store,
            NativeExecutableDurableLeaseJournalCasRequest::new(
                Some(&one),
                &two,
                limits,
                bytes,
            ),
        )
        .map_err(|error| format!("{error:?}"))?;
        let stale = compare_and_swap_executable_durable_lease_journal(
            &mut first_store,
            NativeExecutableDurableLeaseJournalCasRequest::new(
                Some(&one),
                &empty,
                limits,
                bytes,
            ),
        )
        .map_err(|error| format!("{error:?}"))?;
        let restored = restore_executable_durable_lease_journal(
            &mut second_store,
            limits,
            bytes,
        )
        .map_err(|error| format!("{error:?}"))?;
        drop(first_store);
        drop(second_store);
        remove_dir_all(&directory)
            .map_err(|error| format!("test removal failed: {error}"))?;
        if initialized
            == (NativeExecutableDurableLeaseJournalCas::Durable { bytes: 32 })
            && expanded
                == (NativeExecutableDurableLeaseJournalCas::Durable {
                    bytes: 48,
                })
            && matches!(
                stale,
                NativeExecutableDurableLeaseJournalCas::Conflict {
                    current: Some(ref current),
                } if current == &two
            )
            && restored
                == (NativeExecutableDurableLeaseJournalLoad::Present {
                    registry: two,
                })
        {
            Ok(())
        } else {
            Err(String::from("durable lease journal coordination drifted"))
        }
    }

    #[test]
    fn missing_file_journal_is_explicit() -> TestResult {
        let directory = env::temp_dir()
            .join(format!("malbolge-durable-lease-missing-{}", process::id(),));
        match remove_dir_all(&directory) {
            Ok(()) => {},
            Err(error) if error.kind() == ErrorKind::NotFound => {},
            Err(error) => {
                return Err(format!("test cleanup failed: {error}"));
            },
        }
        create_dir_all(&directory)
            .map_err(|error| format!("test create failed: {error}"))?;
        let mut store =
            NativeContinuationFileBlobStore::new(directory.join("leases.bin"));
        let load = restore_executable_durable_lease_journal(
            &mut store,
            decode_limits(2)?,
            maximum_bytes()?,
        )
        .map_err(|error| format!("{error:?}"))?;
        drop(store);
        remove_dir_all(&directory)
            .map_err(|error| format!("test removal failed: {error}"))?;
        if load == NativeExecutableDurableLeaseJournalLoad::Missing {
            Ok(())
        } else {
            Err(String::from("missing lease journal invented owners"))
        }
    }

    #[test]
    fn owner_decode_limit_fails_closed() -> TestResult {
        let mut registry = NativeExecutableDurableLeaseRegistry::new();
        let bound = NonZeroUsize::new(2).ok_or("owner bound")?;
        let _first = registry
            .acquire(owner(1), bound)
            .map_err(|error| format!("{error:?}"))?;
        let _second = registry
            .acquire(owner(2), bound)
            .map_err(|error| format!("{error:?}"))?;
        let bytes = encode_executable_durable_lease_registry(&registry)
            .map_err(|error| format!("{error:?}"))?;
        let maximum_owners = NonZeroUsize::new(1).ok_or("decode bound")?;
        let result = decode_executable_durable_lease_registry(
            &bytes,
            NativeExecutableDurableLeaseRegistryDecodeLimits::new(
                maximum_owners,
            ),
        );
        if result
            == Err(NativeExecutableDurableLeaseRegistryCodecError::OwnerLimit {
                maximum_owners,
                observed_owners: 2,
            })
        {
            Ok(())
        } else {
            Err(String::from("lease journal owner bound was bypassed"))
        }
    }

    #[test]
    fn owner_capacity_fails_before_registry_mutation() -> TestResult {
        let mut registry = NativeExecutableDurableLeaseRegistry::new();
        let maximum = NonZeroUsize::new(1).ok_or("owner bound")?;
        let _acquired = registry
            .acquire(owner(1), maximum)
            .map_err(|error| format!("{error:?}"))?;
        let error = registry
            .acquire(owner(2), maximum)
            .expect_err("second owner must exceed bound");
        if error.maximum_owners() == maximum
            && error.observed_owners() == 2
            && registry.owners() == [owner(1)].as_slice()
        {
            Ok(())
        } else {
            Err(String::from("lease owner bound mutated registry"))
        }
    }

    #[test]
    fn release_to_explicit_empty_journal_is_durable() -> TestResult {
        let directory = env::temp_dir()
            .join(format!("malbolge-durable-lease-release-{}", process::id(),));
        match remove_dir_all(&directory) {
            Ok(()) => {},
            Err(error) if error.kind() == ErrorKind::NotFound => {},
            Err(error) => {
                return Err(format!("test cleanup failed: {error}"));
            },
        }
        create_dir_all(&directory)
            .map_err(|error| format!("test create failed: {error}"))?;
        let mut store =
            NativeContinuationFileBlobStore::new(directory.join("leases.bin"));
        let limits = decode_limits(2)?;
        let bytes = maximum_bytes()?;
        let mut held = NativeExecutableDurableLeaseRegistry::new();
        let _acquired = held
            .acquire(owner(7), limits.maximum_owners())
            .map_err(|error| format!("{error:?}"))?;
        let _initialized = compare_and_swap_executable_durable_lease_journal(
            &mut store,
            NativeExecutableDurableLeaseJournalCasRequest::new(
                None, &held, limits, bytes,
            ),
        )
        .map_err(|error| format!("{error:?}"))?;
        let mut released = held.clone();
        if !released.release(owner(7)) {
            return Err(String::from("test owner was not released"));
        }
        let publication = compare_and_swap_executable_durable_lease_journal(
            &mut store,
            NativeExecutableDurableLeaseJournalCasRequest::new(
                Some(&held),
                &released,
                limits,
                bytes,
            ),
        )
        .map_err(|error| format!("{error:?}"))?;
        let restored =
            restore_executable_durable_lease_journal(&mut store, limits, bytes)
                .map_err(|error| format!("{error:?}"))?;
        drop(store);
        remove_dir_all(&directory)
            .map_err(|error| format!("test removal failed: {error}"))?;
        if publication
            == (NativeExecutableDurableLeaseJournalCas::Durable { bytes: 16 })
            && restored
                == (NativeExecutableDurableLeaseJournalLoad::Present {
                    registry: released,
                })
        {
            Ok(())
        } else {
            Err(String::from("empty durable lease journal drifted"))
        }
    }
}
