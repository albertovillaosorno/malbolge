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
    NativeContinuationBlobConditionalDurableRemoval,
    NativeContinuationBlobPersistenceError,
    NativeContinuationBlobPersistenceLoad, compare_and_remove_blob_durably,
    compare_and_swap_blob_durably, restore_blob,
};
use crate::blob_store::{
    NativeContinuationBlobStore as BlobStore,
    NativeContinuationConditionalBlobStore as ConditionalBlobStore,
    NativeContinuationConditionalRemovableBlobStore as ConditionalRemoveStore,
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

/// Caller-owned inputs for one durable lease owner transition.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeExecutableDurableLeaseTransitionRequest {
    decode_limits: NativeExecutableDurableLeaseRegistryDecodeLimits,
    maximum_bytes: NonZeroUsize,
    owner: NativeExecutableDurableLeaseOwnerId,
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

/// Outcome of exact-empty durable lease-journal reclamation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeExecutableDurableLeaseJournalRemoval<DurabilityError> {
    /// Journal was missing, nonempty, or changed; no removal occurred.
    Conflict {
        /// Exact current durable registry, or missing state.
        current: Option<NativeExecutableDurableLeaseRegistry>,
    },
    /// Exact empty journal removal committed and durability was confirmed.
    Durable,
    /// Exact empty journal removal committed, then durability confirmation
    /// failed.
    Removed {
        /// Exact post-removal durability failure.
        durability_error: DurabilityError,
    },
}

/// Typed result of one bounded acquire or release transition.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeExecutableDurableLeaseTransition<DurabilityError> {
    /// Durable state changed after restore; no retry occurred.
    Conflict {
        /// Exact current durable registry, or missing state.
        current: Option<NativeExecutableDurableLeaseRegistry>,
    },
    /// Replacement committed and durability confirmation completed.
    Durable {
        /// Exact committed canonical byte count.
        bytes: usize,
        /// Exact registry committed by this transition.
        registry: NativeExecutableDurableLeaseRegistry,
    },
    /// Replacement committed, then durability confirmation failed.
    Published {
        /// Exact committed canonical byte count.
        bytes: usize,
        /// Exact post-publication durability failure.
        durability_error: DurabilityError,
        /// Exact registry committed by this transition.
        registry: NativeExecutableDurableLeaseRegistry,
    },
    /// Requested owner state already matched; storage was not mutated.
    Unchanged {
        /// Exact restored registry, or missing state.
        current: Option<NativeExecutableDurableLeaseRegistry>,
    },
}

/// Why one one-shot durable lease transition failed closed.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeExecutableDurableLeaseTransitionError<StoreError> {
    /// Local acquisition would exceed the caller's positive owner bound.
    Capacity(NativeExecutableDurableLeaseRegistryCapacityError),
    /// Durable restore/CAS or canonical decoding failed.
    Journal(NativeExecutableDurableLeaseJournalError<StoreError>),
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

/// One-shot lease transition result specialized to one blob store.
pub type NativeExecutableDurableLeaseTransitionStoreResult<Store> = Result<
    NativeExecutableDurableLeaseTransition<
        <Store as DurableBlobStore>::DurabilityError,
    >,
    NativeExecutableDurableLeaseTransitionError<<Store as BlobStore>::Error>,
>;

/// Empty-journal durable removal result specialized to one blob store.
pub type NativeExecutableDurableLeaseJournalRemovalStoreResult<Store> =
    NativeExecutableDurableLeaseJournalStoreResult<
        Store,
        NativeExecutableDurableLeaseJournalRemoval<
            <Store as DurableBlobStore>::DurabilityError,
        >,
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

impl NativeExecutableDurableLeaseTransitionRequest {
    /// Returns the exact owner-decoding limits bound to this transition.
    #[must_use]
    pub(crate) const fn decode_limits(
        self,
    ) -> NativeExecutableDurableLeaseRegistryDecodeLimits {
        self.decode_limits
    }

    /// Returns the positive journal-byte bound for this transition.
    #[must_use]
    pub(crate) const fn maximum_bytes(self) -> NonZeroUsize {
        self.maximum_bytes
    }

    /// Binds one caller-supplied owner to explicit decode and byte bounds.
    #[must_use]
    pub const fn new(
        owner: NativeExecutableDurableLeaseOwnerId,
        decode_limits: NativeExecutableDurableLeaseRegistryDecodeLimits,
        maximum_bytes: NonZeroUsize,
    ) -> Self {
        Self {
            decode_limits,
            maximum_bytes,
            owner,
        }
    }

    /// Returns the exact opaque owner selected by this transition.
    #[must_use]
    pub(crate) const fn owner(self) -> NativeExecutableDurableLeaseOwnerId {
        self.owner
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

const fn admit_registry_owner_limit(
    registry: &NativeExecutableDurableLeaseRegistry,
    limits: NativeExecutableDurableLeaseRegistryDecodeLimits,
) -> Result<(), NativeExecutableDurableLeaseRegistryCodecError> {
    if registry.len() <= limits.maximum_owners().get() {
        Ok(())
    } else {
        Err(NativeExecutableDurableLeaseRegistryCodecError::OwnerLimit {
            maximum_owners: limits.maximum_owners(),
            observed_owners: registry.len(),
        })
    }
}

fn transition_executable_durable_lease_once<Store, Mutate>(
    store: &mut Store,
    request: NativeExecutableDurableLeaseTransitionRequest,
    mutate: Mutate,
) -> NativeExecutableDurableLeaseTransitionStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
    Mutate: FnOnce(
        &mut NativeExecutableDurableLeaseRegistry,
        NativeExecutableDurableLeaseTransitionRequest,
    ) -> Result<
        bool,
        NativeExecutableDurableLeaseRegistryCapacityError,
    >,
{
    let load = restore_executable_durable_lease_journal(
        store,
        request.decode_limits,
        request.maximum_bytes,
    )
    .map_err(NativeExecutableDurableLeaseTransitionError::Journal)?;
    let expected = match load {
        NativeExecutableDurableLeaseJournalLoad::Missing => None,
        NativeExecutableDurableLeaseJournalLoad::Present { registry } => {
            Some(registry)
        },
    };
    let mut replacement = expected.clone().unwrap_or_default();
    let changed = mutate(&mut replacement, request)
        .map_err(NativeExecutableDurableLeaseTransitionError::Capacity)?;
    if !changed {
        return Ok(NativeExecutableDurableLeaseTransition::Unchanged {
            current: expected,
        });
    }
    let publication = compare_and_swap_executable_durable_lease_journal(
        store,
        NativeExecutableDurableLeaseJournalCasRequest::new(
            expected.as_ref(),
            &replacement,
            request.decode_limits,
            request.maximum_bytes,
        ),
    )
    .map_err(NativeExecutableDurableLeaseTransitionError::Journal)?;
    match publication {
        NativeExecutableDurableLeaseJournalCas::Conflict { current } => {
            Ok(NativeExecutableDurableLeaseTransition::Conflict { current })
        },
        NativeExecutableDurableLeaseJournalCas::Durable { bytes } => {
            Ok(NativeExecutableDurableLeaseTransition::Durable {
                bytes,
                registry: replacement,
            })
        },
        NativeExecutableDurableLeaseJournalCas::Published {
            bytes,
            durability_error,
        } => Ok(NativeExecutableDurableLeaseTransition::Published {
            bytes,
            durability_error,
            registry: replacement,
        }),
    }
}

/// Acquires one caller-supplied durable lease owner exactly once.
///
/// Missing state starts from an explicit empty registry. Existing membership is
/// idempotent and performs no publication. A concurrent journal change returns
/// typed conflict evidence and is never retried here.
///
/// # Errors
///
/// Returns bounded restore/CAS, codec, or owner-capacity failure.
pub fn acquire_executable_durable_lease_once<Store>(
    store: &mut Store,
    request: NativeExecutableDurableLeaseTransitionRequest,
) -> NativeExecutableDurableLeaseTransitionStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    transition_executable_durable_lease_once(
        store,
        request,
        |registry, transition| {
            registry.acquire(
                transition.owner,
                transition.decode_limits.maximum_owners(),
            )
        },
    )
}

/// Releases one caller-supplied durable lease owner exactly once.
///
/// Missing state and absent membership are idempotent no-ops. Last-owner
/// release commits an explicit empty registry rather than deleting the journal.
/// A concurrent journal change returns typed conflict evidence and is never
/// retried here.
///
/// # Errors
///
/// Returns bounded restore/CAS or canonical codec failure.
pub fn release_executable_durable_lease_once<Store>(
    store: &mut Store,
    request: NativeExecutableDurableLeaseTransitionRequest,
) -> NativeExecutableDurableLeaseTransitionStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    transition_executable_durable_lease_once(
        store,
        request,
        |registry, transition| Ok(registry.release(transition.owner)),
    )
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
    if let Some(expected) = request.expected {
        admit_registry_owner_limit(expected, request.decode_limits)
            .map_err(NativeExecutableDurableLeaseJournalError::Codec)?;
    }
    admit_registry_owner_limit(request.replacement, request.decode_limits)
        .map_err(NativeExecutableDurableLeaseJournalError::Codec)?;
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

/// Removes the journal only when its exact current registry is empty.
///
/// Missing or nonempty state is conflict evidence and is left untouched.
/// This operation performs no expiry, owner inference, retry, or artifact
/// eviction.
///
/// # Errors
///
/// Returns canonical decoding, byte-limit, coordination, removal, or durability
/// orchestration failure before typed outcome publication.
pub fn remove_empty_executable_durable_lease_journal_durably<Store>(
    store: &mut Store,
    decode_limits: NativeExecutableDurableLeaseRegistryDecodeLimits,
    maximum_bytes: NonZeroUsize,
) -> NativeExecutableDurableLeaseJournalRemovalStoreResult<Store>
where
    Store: ConditionalRemoveStore + DurableBlobStore,
{
    let empty = NativeExecutableDurableLeaseRegistry::new();
    let expected_bytes = encode_executable_durable_lease_registry(&empty)
        .map_err(NativeExecutableDurableLeaseJournalError::Codec)?;
    let outcome = compare_and_remove_blob_durably(
        store,
        Some(&expected_bytes),
        maximum_bytes,
    )
    .map_err(NativeExecutableDurableLeaseJournalError::Blob)?;
    match outcome {
        NativeContinuationBlobConditionalDurableRemoval::Conflict {
            current,
        } => Ok(NativeExecutableDurableLeaseJournalRemoval::Conflict {
            current: current
                .as_deref()
                .map(|bytes| {
                    decode_executable_durable_lease_registry(
                        bytes,
                        decode_limits,
                    )
                })
                .transpose()
                .map_err(NativeExecutableDurableLeaseJournalError::Codec)?,
        }),
        NativeContinuationBlobConditionalDurableRemoval::Durable => {
            Ok(NativeExecutableDurableLeaseJournalRemoval::Durable)
        },
        NativeContinuationBlobConditionalDurableRemoval::Missing => {
            Ok(NativeExecutableDurableLeaseJournalRemoval::Conflict {
                current: None,
            })
        },
        NativeContinuationBlobConditionalDurableRemoval::Removed {
            durability_error,
        } => Ok(NativeExecutableDurableLeaseJournalRemoval::Removed {
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
#[path = "../../../../../tests/tiered/durable_lease_journal.rs"]
mod tests;
