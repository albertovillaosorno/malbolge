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
mod tests {
    use std::fs::{create_dir_all, remove_dir_all};
    use std::io::ErrorKind;
    use std::{env, process};

    use super::*;
    use crate::blob_store::{
        NativeContinuationBlobConditionalPublication,
        NativeContinuationBlobConditionalPublicationResult,
        NativeContinuationBlobConditionalRemoval,
        NativeContinuationBlobConditionalRemovalResult,
        NativeContinuationBlobRemoval, NativeContinuationBlobRemovalResult,
        NativeContinuationBlobStore, NativeContinuationConditionalBlobStore,
        NativeContinuationConditionalRemovableBlobStore,
        NativeContinuationDurableBlobStore,
        NativeContinuationRemovableBlobStore,
    };
    use crate::file_blob_store::NativeContinuationFileBlobStore;

    type TestResult = Result<(), String>;

    #[derive(Clone, Copy, Debug, Eq, PartialEq)]
    enum TestDurabilityError {
        Failed,
    }

    #[derive(Clone, Copy, Debug, Eq, PartialEq)]
    enum TestStoreError {
        Failed,
    }

    #[derive(Debug, Default)]
    struct TransitionStore {
        bytes: Option<Vec<u8>>,
        durability_calls: usize,
        fail_durability: bool,
        race_bytes: Option<Vec<u8>>,
    }

    impl NativeContinuationBlobStore for TransitionStore {
        type Error = TestStoreError;

        fn load(
            &mut self,
            _maximum_bytes: NonZeroUsize,
        ) -> Result<Option<Vec<u8>>, Self::Error> {
            Ok(self.bytes.clone())
        }

        fn replace(&mut self, bytes: &[u8]) -> Result<(), Self::Error> {
            self.bytes = Some(bytes.to_vec());
            Ok(())
        }
    }

    impl NativeContinuationConditionalBlobStore for TransitionStore {
        fn compare_and_swap(
            &mut self,
            expected: Option<&[u8]>,
            replacement: &[u8],
            _maximum_bytes: NonZeroUsize,
        ) -> NativeContinuationBlobConditionalPublicationResult<Self::Error>
        {
            if let Some(race_bytes) = self.race_bytes.take() {
                self.bytes = Some(race_bytes);
            }
            if self.bytes.as_deref() != expected {
                return Ok(
                    NativeContinuationBlobConditionalPublication::Conflict {
                        current: self.bytes.clone(),
                    },
                );
            }
            self.bytes = Some(replacement.to_vec());
            Ok(NativeContinuationBlobConditionalPublication::Published)
        }
    }

    impl NativeContinuationRemovableBlobStore for TransitionStore {
        fn remove(
            &mut self,
        ) -> NativeContinuationBlobRemovalResult<Self::Error> {
            if self.bytes.take().is_some() {
                Ok(NativeContinuationBlobRemoval::Removed)
            } else {
                Ok(NativeContinuationBlobRemoval::Missing)
            }
        }
    }

    impl NativeContinuationConditionalRemovableBlobStore for TransitionStore {
        fn compare_and_remove(
            &mut self,
            expected: Option<&[u8]>,
            _maximum_bytes: NonZeroUsize,
        ) -> NativeContinuationBlobConditionalRemovalResult<Self::Error>
        {
            if self.bytes.as_deref() != expected {
                return Ok(
                    NativeContinuationBlobConditionalRemoval::Conflict {
                        current: self.bytes.clone(),
                    },
                );
            }
            if self.bytes.take().is_some() {
                Ok(NativeContinuationBlobConditionalRemoval::Removed)
            } else {
                Ok(NativeContinuationBlobConditionalRemoval::Missing)
            }
        }
    }

    impl NativeContinuationDurableBlobStore for TransitionStore {
        type DurabilityError = TestDurabilityError;

        fn confirm_durability(&mut self) -> Result<(), Self::DurabilityError> {
            self.durability_calls = self.durability_calls.saturating_add(1);
            if self.fail_durability {
                Err(TestDurabilityError::Failed)
            } else {
                Ok(())
            }
        }
    }

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

    fn transition_request(
        owner: NativeExecutableDurableLeaseOwnerId,
        maximum_owners: usize,
    ) -> Result<NativeExecutableDurableLeaseTransitionRequest, String> {
        Ok(NativeExecutableDurableLeaseTransitionRequest::new(
            owner,
            decode_limits(maximum_owners)?,
            maximum_bytes()?,
        ))
    }

    #[test]
    fn acquire_capacity_failure_preserves_durable_registry() -> TestResult {
        let bound = NonZeroUsize::new(1).ok_or("owner bound")?;
        let mut current = NativeExecutableDurableLeaseRegistry::new();
        let _inserted = current
            .acquire(owner(1), bound)
            .map_err(|error| format!("{error:?}"))?;
        let current_bytes = encode_executable_durable_lease_registry(&current)
            .map_err(|error| format!("{error:?}"))?;
        let mut store = TransitionStore {
            bytes: Some(current_bytes.clone()),
            ..TransitionStore::default()
        };
        let result = acquire_executable_durable_lease_once(
            &mut store,
            transition_request(owner(2), 1)?,
        );
        if matches!(
            result,
            Err(NativeExecutableDurableLeaseTransitionError::Capacity(error))
                if error.maximum_owners() == bound
                    && error.observed_owners() == 2
        ) && store.bytes == Some(current_bytes)
            && store.durability_calls == 0
        {
            Ok(())
        } else {
            Err(String::from(
                "capacity failure changed durable lease registry",
            ))
        }
    }

    #[test]
    fn acquire_conflict_returns_current_without_retry() -> TestResult {
        let bound = NonZeroUsize::new(4).ok_or("owner bound")?;
        let mut first = NativeExecutableDurableLeaseRegistry::new();
        let _inserted = first
            .acquire(owner(1), bound)
            .map_err(|error| format!("{error:?}"))?;
        let mut raced = first.clone();
        let _inserted = raced
            .acquire(owner(2), bound)
            .map_err(|error| format!("{error:?}"))?;
        let first_bytes = encode_executable_durable_lease_registry(&first)
            .map_err(|error| format!("{error:?}"))?;
        let raced_bytes = encode_executable_durable_lease_registry(&raced)
            .map_err(|error| format!("{error:?}"))?;
        let mut store = TransitionStore {
            bytes: Some(first_bytes),
            race_bytes: Some(raced_bytes.clone()),
            ..TransitionStore::default()
        };
        let outcome = acquire_executable_durable_lease_once(
            &mut store,
            transition_request(owner(3), 4)?,
        )
        .map_err(|error| format!("{error:?}"))?;
        if outcome
            == (NativeExecutableDurableLeaseTransition::Conflict {
                current: Some(raced),
            })
            && store.bytes == Some(raced_bytes)
            && store.durability_calls == 0
        {
            Ok(())
        } else {
            Err(String::from("lease acquire conflict retried or drifted"))
        }
    }

    #[test]
    fn acquire_post_commit_durability_failure_keeps_registry() -> TestResult {
        let mut store = TransitionStore {
            fail_durability: true,
            ..TransitionStore::default()
        };
        let request = transition_request(owner(4), 4)?;
        let outcome =
            acquire_executable_durable_lease_once(&mut store, request)
                .map_err(|error| format!("{error:?}"))?;
        let bytes = store
            .bytes
            .as_deref()
            .ok_or_else(|| String::from("committed lease journal missing"))?;
        let restored =
            decode_executable_durable_lease_registry(bytes, decode_limits(4)?)
                .map_err(|error| format!("{error:?}"))?;
        if matches!(
            outcome,
            NativeExecutableDurableLeaseTransition::Published {
                bytes: 32,
                durability_error: TestDurabilityError::Failed,
                ref registry,
            } if registry == &restored && restored.contains(owner(4))
        ) && store.durability_calls == 1
        {
            Ok(())
        } else {
            Err(String::from(
                "post-commit durability failure lost lease registry",
            ))
        }
    }

    #[test]
    fn file_owner_transitions_are_idempotent() -> TestResult {
        let directory = env::temp_dir().join(format!(
            "malbolge-durable-lease-transition-{}",
            process::id(),
        ));
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
        let request = transition_request(owner(7), 4)?;
        let acquired =
            acquire_executable_durable_lease_once(&mut store, request)
                .map_err(|error| format!("{error:?}"))?;
        let duplicate =
            acquire_executable_durable_lease_once(&mut store, request)
                .map_err(|error| format!("{error:?}"))?;
        let released =
            release_executable_durable_lease_once(&mut store, request)
                .map_err(|error| format!("{error:?}"))?;
        let duplicate_release =
            release_executable_durable_lease_once(&mut store, request)
                .map_err(|error| format!("{error:?}"))?;
        let restored = restore_executable_durable_lease_journal(
            &mut store,
            request.decode_limits,
            request.maximum_bytes,
        )
        .map_err(|error| format!("{error:?}"))?;
        drop(store);
        remove_dir_all(&directory)
            .map_err(|error| format!("test removal failed: {error}"))?;
        let empty = NativeExecutableDurableLeaseRegistry::new();
        if matches!(
            acquired,
            NativeExecutableDurableLeaseTransition::Durable {
                ref registry,
                ..
            } if registry.contains(owner(7))
        ) && matches!(
            duplicate,
            NativeExecutableDurableLeaseTransition::Unchanged {
                current: Some(ref registry),
            } if registry.contains(owner(7))
        ) && matches!(
            released,
            NativeExecutableDurableLeaseTransition::Durable {
                ref registry,
                ..
            } if registry.is_empty()
        ) && duplicate_release
            == (NativeExecutableDurableLeaseTransition::Unchanged {
                current: Some(empty.clone()),
            })
            && restored
                == (NativeExecutableDurableLeaseJournalLoad::Present {
                    registry: empty,
                })
        {
            Ok(())
        } else {
            Err(String::from("one-shot lease transitions drifted"))
        }
    }

    #[test]
    fn empty_removal_durability_failure_retains_absence() -> TestResult {
        let empty = NativeExecutableDurableLeaseRegistry::new();
        let empty_bytes = encode_executable_durable_lease_registry(&empty)
            .map_err(|error| format!("{error:?}"))?;
        let mut store = TransitionStore {
            bytes: Some(empty_bytes),
            fail_durability: true,
            ..TransitionStore::default()
        };
        let removal = remove_empty_executable_durable_lease_journal_durably(
            &mut store,
            decode_limits(4)?,
            maximum_bytes()?,
        )
        .map_err(|error| format!("{error:?}"))?;
        if removal
            == (NativeExecutableDurableLeaseJournalRemoval::Removed {
                durability_error: TestDurabilityError::Failed,
            })
            && store.bytes.is_none()
            && store.durability_calls == 1
        {
            Ok(())
        } else {
            Err(String::from(
                "post-removal durability failure restored lease journal",
            ))
        }
    }

    #[test]
    fn empty_file_journal_can_be_removed_durably() -> TestResult {
        let directory = env::temp_dir().join(format!(
            "malbolge-durable-lease-empty-remove-{}",
            process::id(),
        ));
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
        let request = transition_request(owner(8), 4)?;
        let _acquired =
            acquire_executable_durable_lease_once(&mut store, request)
                .map_err(|error| format!("{error:?}"))?;
        let _released =
            release_executable_durable_lease_once(&mut store, request)
                .map_err(|error| format!("{error:?}"))?;
        let removed = remove_empty_executable_durable_lease_journal_durably(
            &mut store,
            request.decode_limits,
            request.maximum_bytes,
        )
        .map_err(|error| format!("{error:?}"))?;
        let restored = restore_executable_durable_lease_journal(
            &mut store,
            request.decode_limits,
            request.maximum_bytes,
        )
        .map_err(|error| format!("{error:?}"))?;
        drop(store);
        remove_dir_all(&directory)
            .map_err(|error| format!("test removal failed: {error}"))?;
        if removed == NativeExecutableDurableLeaseJournalRemoval::Durable
            && restored == NativeExecutableDurableLeaseJournalLoad::Missing
        {
            Ok(())
        } else {
            Err(String::from("empty lease journal removal drifted"))
        }
    }

    #[test]
    fn nonempty_file_journal_blocks_empty_removal() -> TestResult {
        let directory = env::temp_dir().join(format!(
            "malbolge-durable-lease-nonempty-remove-{}",
            process::id(),
        ));
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
        let request = transition_request(owner(8), 4)?;
        let acquired =
            acquire_executable_durable_lease_once(&mut store, request)
                .map_err(|error| format!("{error:?}"))?;
        let expected = match acquired {
            NativeExecutableDurableLeaseTransition::Durable {
                registry,
                ..
            }
            | NativeExecutableDurableLeaseTransition::Published {
                registry,
                ..
            } => registry,
            _ => {
                return Err(String::from(
                    "test lease acquisition did not commit",
                ));
            },
        };
        let removal = remove_empty_executable_durable_lease_journal_durably(
            &mut store,
            request.decode_limits,
            request.maximum_bytes,
        )
        .map_err(|error| format!("{error:?}"))?;
        let restored = restore_executable_durable_lease_journal(
            &mut store,
            request.decode_limits,
            request.maximum_bytes,
        )
        .map_err(|error| format!("{error:?}"))?;
        drop(store);
        remove_dir_all(&directory)
            .map_err(|error| format!("test removal failed: {error}"))?;
        if removal
            == (NativeExecutableDurableLeaseJournalRemoval::Conflict {
                current: Some(expected.clone()),
            })
            && restored
                == (NativeExecutableDurableLeaseJournalLoad::Present {
                    registry: expected,
                })
        {
            Ok(())
        } else {
            Err(String::from("nonempty lease journal was removed"))
        }
    }

    #[test]
    fn release_missing_journal_is_unchanged() -> TestResult {
        let mut store = TransitionStore::default();
        let outcome = release_executable_durable_lease_once(
            &mut store,
            transition_request(owner(9), 4)?,
        )
        .map_err(|error| format!("{error:?}"))?;
        if outcome
            == (NativeExecutableDurableLeaseTransition::Unchanged {
                current: None,
            })
            && store.bytes.is_none()
            && store.durability_calls == 0
        {
            Ok(())
        } else {
            Err(String::from("missing lease release mutated storage"))
        }
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
    fn replacement_owner_limit_fails_before_publication() -> TestResult {
        let directory = env::temp_dir()
            .join(format!("malbolge-durable-lease-bound-{}", process::id(),));
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
        let construction_bound = NonZeroUsize::new(2).ok_or("owner bound")?;
        let mut replacement = NativeExecutableDurableLeaseRegistry::new();
        let _first = replacement
            .acquire(owner(1), construction_bound)
            .map_err(|error| format!("{error:?}"))?;
        let _second = replacement
            .acquire(owner(2), construction_bound)
            .map_err(|error| format!("{error:?}"))?;
        let maximum_owners = NonZeroUsize::new(1).ok_or("CAS owner bound")?;
        let decode_limits =
            NativeExecutableDurableLeaseRegistryDecodeLimits::new(
                maximum_owners,
            );
        let result = compare_and_swap_executable_durable_lease_journal(
            &mut store,
            NativeExecutableDurableLeaseJournalCasRequest::new(
                None,
                &replacement,
                decode_limits,
                maximum_bytes()?,
            ),
        );
        let load = restore_executable_durable_lease_journal(
            &mut store,
            decode_limits,
            maximum_bytes()?,
        )
        .map_err(|error| format!("{error:?}"))?;
        drop(store);
        remove_dir_all(&directory)
            .map_err(|error| format!("test removal failed: {error}"))?;
        if result
            == Err(NativeExecutableDurableLeaseJournalError::Codec(
                NativeExecutableDurableLeaseRegistryCodecError::OwnerLimit {
                    maximum_owners,
                    observed_owners: 2,
                },
            ))
            && load == NativeExecutableDurableLeaseJournalLoad::Missing
        {
            Ok(())
        } else {
            Err(String::from(
                "over-limit durable lease replacement reached storage",
            ))
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
