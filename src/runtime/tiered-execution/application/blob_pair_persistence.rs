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
//   - Explicit bounded persistence use cases for one opaque atomic blob pair.
// - Must-Not:
//   - Choose storage locations, interpret bytes, or emulate pair atomicity.
// - Allows:
//   - Inputs: two immutable blobs, independent positive bounds, and pair store.
//   - Outputs: missing/present pair bytes or exact publication evidence.
//   - Side effects: one delegated atomic pair load or replacement per call.
// - Split-When:
//   - Migration or N-object transactions gain application authority.
// - Merge-When:
//   - Another application service owns the exact bounded pair use case.
// - Summary:
//   - Coordinates independent byte bounds with atomic pair storage.
// - Description:
//   - Both bounds are checked before publication and after every adapter load.
// - Usage:
//   - Called by typed composition after both payloads are canonically encoded.
// - Defaults:
//   - Missing durable pair state is explicit and never invents empty bytes.
//

//! Explicit bounded persistence orchestration for one opaque atomic blob pair.

use std::num::NonZeroUsize;

use pair_store::{
    NativeContinuationBlobPairStore as PairStore,
    NativeContinuationConditionalBlobPairStore as ConditionalPairStore,
    NativeContinuationDurableBlobPairStore as DurablePairStore,
};

use crate::blob_pair_store as pair_store;

type PairConditionalPublication<Revision> =
    pair_store::NativeContinuationBlobPairConditionalPublication<Revision>;
type PairConditionalDurable<Revision, DurabilityError> =
    NativeContinuationBlobPairConditionalDurablePersistence<
        Revision,
        DurabilityError,
    >;

/// Immutable bounded request for one atomic pair publication.
#[derive(Clone, Copy, Debug)]
pub struct NativeContinuationBlobPairPersistenceRequest<'bytes> {
    first: &'bytes [u8],
    first_maximum_bytes: NonZeroUsize,
    second: &'bytes [u8],
    second_maximum_bytes: NonZeroUsize,
}

impl<'bytes> NativeContinuationBlobPairPersistenceRequest<'bytes> {
    /// Constructs one explicit bounded pair-publication request.
    #[must_use]
    pub const fn new(
        first: &'bytes [u8],
        second: &'bytes [u8],
        first_maximum_bytes: NonZeroUsize,
        second_maximum_bytes: NonZeroUsize,
    ) -> Self {
        Self {
            first,
            first_maximum_bytes,
            second,
            second_maximum_bytes,
        }
    }
}

/// Outcome after atomic pair publication plus durability confirmation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationBlobPairDurablePersistence<DurabilityError> {
    /// Pair publication and durability confirmation both completed.
    Durable {
        /// Exact committed byte counts for both pair members.
        write: NativeContinuationBlobPairPersistenceWrite,
    },
    /// Pair publication committed, then durability confirmation failed.
    Published {
        /// Exact post-publication durability failure.
        durability_error: DurabilityError,
        /// Exact committed byte counts for both pair members.
        write: NativeContinuationBlobPairPersistenceWrite,
    },
}

/// Why one bounded blob-pair persistence operation failed closed.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationBlobPairPersistenceError<StoreError> {
    /// One admitted or adapter-returned pair member exceeded its positive
    /// bound.
    ByteLimit {
        /// Which opaque pair member violated its bound.
        member: NativeContinuationBlobPairMember,
        /// Positive caller-configured byte limit.
        maximum_bytes: NonZeroUsize,
        /// Exact supplied or returned byte count.
        observed_bytes: usize,
    },
    /// The selected outbound pair store failed.
    Store(StoreError),
}

/// Identifies one member of the opaque pair without interpreting its bytes.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationBlobPairMember {
    /// First pair member.
    First,
    /// Second pair member.
    Second,
}

/// Result of one bounded atomic pair load.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationBlobPairPersistenceLoad {
    /// No atomic pair publication currently exists.
    Missing,
    /// One complete bounded pair was loaded atomically.
    Present {
        /// Exact first member bytes.
        first: Vec<u8>,
        /// Exact second member bytes.
        second: Vec<u8>,
    },
}

/// Exact publication evidence for one committed atomic pair replacement.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationBlobPairPersistenceWrite {
    first_bytes: usize,
    second_bytes: usize,
}

/// Bounded pair plus opaque publication revision returned to application code.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeContinuationBlobPairVersionedLoad<Revision> {
    /// Exact first member bytes.
    pub first: Vec<u8>,
    /// Opaque adapter-owned revision observed with both members.
    pub revision: Revision,
    /// Exact second member bytes.
    pub second: Vec<u8>,
}

/// Outcome of one bounded revision-conditional atomic pair publication.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationBlobPairConditionalPersistence<Revision> {
    /// Current publication differed from caller expectation.
    Conflict {
        /// Complete bounded current publication, or absence.
        current: Option<NativeContinuationBlobPairVersionedLoad<Revision>>,
    },
    /// Replacement committed under a fresh opaque revision.
    Published {
        /// Fresh adapter-owned revision assigned at commit.
        revision: Revision,
        /// Exact committed member byte counts.
        write: NativeContinuationBlobPairPersistenceWrite,
    },
}

/// Durable outcome of one revision-conditional pair publication.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationBlobPairConditionalDurablePersistence<
    Revision,
    DurabilityError,
> {
    /// Current publication differed from caller expectation.
    Conflict {
        /// Complete bounded current publication, or absence.
        current: Option<NativeContinuationBlobPairVersionedLoad<Revision>>,
    },
    /// Conditional publication and durability confirmation completed.
    Durable {
        /// Fresh adapter-owned revision assigned at commit.
        revision: Revision,
        /// Exact committed member byte counts.
        write: NativeContinuationBlobPairPersistenceWrite,
    },
    /// Conditional publication committed, then durability confirmation failed.
    Published {
        /// Exact post-publication durability failure.
        durability_error: DurabilityError,
        /// Fresh adapter-owned revision assigned at commit.
        revision: Revision,
        /// Exact committed member byte counts.
        write: NativeContinuationBlobPairPersistenceWrite,
    },
}

/// Result of one atomic pair persistence use case.
pub type NativeContinuationBlobPairPersistenceResult<Value, StoreError> =
    Result<Value, NativeContinuationBlobPairPersistenceError<StoreError>>;

/// Durable atomic pair result specialized to one outbound store type.
pub type NativeContinuationBlobPairDurableStoreResult<Store> = Result<
    NativeContinuationBlobPairDurablePersistence<
        <Store as DurablePairStore>::DurabilityError,
    >,
    NativeContinuationBlobPairPersistenceError<<Store as PairStore>::Error>,
>;

/// Conditional pair result specialized to one outbound store type.
pub type NativeContinuationBlobPairConditionalStoreResult<Store> = Result<
    NativeContinuationBlobPairConditionalPersistence<
        <Store as ConditionalPairStore>::Revision,
    >,
    NativeContinuationBlobPairPersistenceError<<Store as PairStore>::Error>,
>;

/// Durable conditional pair result specialized to one outbound store type.
pub type NativeContinuationBlobPairConditionalDurableStoreResult<Store> =
    Result<
        NativeContinuationBlobPairConditionalDurablePersistence<
            <Store as ConditionalPairStore>::Revision,
            <Store as DurablePairStore>::DurabilityError,
        >,
        NativeContinuationBlobPairPersistenceError<<Store as PairStore>::Error>,
    >;

/// Versioned pair load result specialized to one outbound store type.
pub type NativeContinuationBlobPairVersionedStoreLoadResult<Store> = Result<
    Option<
        NativeContinuationBlobPairVersionedLoad<
            <Store as ConditionalPairStore>::Revision,
        >,
    >,
    NativeContinuationBlobPairPersistenceError<<Store as PairStore>::Error>,
>;

impl<DurabilityError>
    NativeContinuationBlobPairDurablePersistence<DurabilityError>
{
    /// Returns post-publication durability failure when confirmation failed.
    #[must_use]
    pub const fn durability_error(&self) -> Option<&DurabilityError> {
        match self {
            Self::Durable { .. } => None,
            Self::Published { durability_error, .. } => Some(durability_error),
        }
    }

    /// Reports whether pair publication durability was explicitly confirmed.
    #[must_use]
    pub const fn is_durable(&self) -> bool {
        matches!(self, Self::Durable { .. })
    }

    /// Returns exact committed byte counts for both pair members.
    #[must_use]
    pub const fn write(&self) -> NativeContinuationBlobPairPersistenceWrite {
        match self {
            Self::Durable { write } | Self::Published { write, .. } => *write,
        }
    }
}

impl NativeContinuationBlobPairPersistenceWrite {
    /// Returns exact committed byte count for the first pair member.
    #[must_use]
    pub const fn first_bytes(self) -> usize {
        self.first_bytes
    }

    /// Returns exact committed byte count for the second pair member.
    #[must_use]
    pub const fn second_bytes(self) -> usize {
        self.second_bytes
    }
}

const fn admit_member<StoreError>(
    member: NativeContinuationBlobPairMember,
    observed_bytes: usize,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationBlobPairPersistenceResult<(), StoreError> {
    if observed_bytes <= maximum_bytes.get() {
        Ok(())
    } else {
        Err(NativeContinuationBlobPairPersistenceError::ByteLimit {
            member,
            maximum_bytes,
            observed_bytes,
        })
    }
}

/// Atomically persists both opaque pair members under independent byte bounds.
///
/// # Errors
///
/// Returns first/second byte-limit or pair-store failure before claiming
/// commit.
pub fn persist_blob_pair<Store>(
    store: &mut Store,
    request: NativeContinuationBlobPairPersistenceRequest<'_>,
) -> NativeContinuationBlobPairPersistenceResult<
    NativeContinuationBlobPairPersistenceWrite,
    Store::Error,
>
where
    Store: PairStore,
{
    admit_member(
        NativeContinuationBlobPairMember::First,
        request.first.len(),
        request.first_maximum_bytes,
    )?;
    admit_member(
        NativeContinuationBlobPairMember::Second,
        request.second.len(),
        request.second_maximum_bytes,
    )?;
    store
        .replace_pair(request.first, request.second)
        .map_err(NativeContinuationBlobPairPersistenceError::Store)?;
    Ok(NativeContinuationBlobPairPersistenceWrite {
        first_bytes: request.first.len(),
        second_bytes: request.second.len(),
    })
}

/// Conditionally persists both blobs against one opaque expected revision.
///
/// # Errors
///
/// Returns byte-limit or pair-store failure before a typed outcome is produced.
pub fn compare_and_swap_blob_pair<Store>(
    store: &mut Store,
    expected: Option<&Store::Revision>,
    request: NativeContinuationBlobPairPersistenceRequest<'_>,
) -> NativeContinuationBlobPairConditionalStoreResult<Store>
where
    Store: ConditionalPairStore,
{
    admit_member(
        NativeContinuationBlobPairMember::First,
        request.first.len(),
        request.first_maximum_bytes,
    )?;
    admit_member(
        NativeContinuationBlobPairMember::Second,
        request.second.len(),
        request.second_maximum_bytes,
    )?;
    let outcome = store
        .compare_and_swap_pair(
            pair_store::NativeContinuationBlobPairConditionalRequest {
                expected,
                first: request.first,
                first_maximum_bytes: request.first_maximum_bytes,
                second: request.second,
                second_maximum_bytes: request.second_maximum_bytes,
            },
        )
        .map_err(NativeContinuationBlobPairPersistenceError::Store)?;
    match outcome {
        PairConditionalPublication::Conflict { current } => {
            Ok(NativeContinuationBlobPairConditionalPersistence::Conflict {
                current: current
                    .map(|value| admit_versioned_pair(value, request))
                    .transpose()?,
            })
        },
        PairConditionalPublication::Published { revision } => Ok(
            NativeContinuationBlobPairConditionalPersistence::Published {
                revision,
                write: NativeContinuationBlobPairPersistenceWrite {
                    first_bytes: request.first.len(),
                    second_bytes: request.second.len(),
                },
            },
        ),
    }
}

/// Conditionally persists one pair and confirms durability only after commit.
///
/// # Errors
///
/// Returns only prepublication byte-limit/store failures. Conflict is
/// non-mutating evidence; durability failure after commit remains committed.
pub fn compare_and_swap_blob_pair_durably<Store>(
    store: &mut Store,
    expected: Option<&Store::Revision>,
    request: NativeContinuationBlobPairPersistenceRequest<'_>,
) -> NativeContinuationBlobPairConditionalDurableStoreResult<Store>
where
    Store: ConditionalPairStore + DurablePairStore,
{
    let (revision, write) =
        match compare_and_swap_blob_pair(store, expected, request)? {
            NativeContinuationBlobPairConditionalPersistence::Conflict {
                current,
            } => {
                return Ok(PairConditionalDurable::Conflict { current });
            },
            NativeContinuationBlobPairConditionalPersistence::Published {
                revision,
                write,
            } => (revision, write),
        };
    match store.confirm_pair_durability() {
        Ok(()) => Ok(PairConditionalDurable::Durable { revision, write }),
        Err(durability_error) => Ok(PairConditionalDurable::Published {
            durability_error,
            revision,
            write,
        }),
    }
}

/// Loads one complete bounded pair together with its opaque revision.
///
/// # Errors
///
/// Returns pair-store or post-load first/second byte-limit failure.
pub fn restore_blob_pair_versioned<Store>(
    store: &mut Store,
    first_maximum_bytes: NonZeroUsize,
    second_maximum_bytes: NonZeroUsize,
) -> NativeContinuationBlobPairVersionedStoreLoadResult<Store>
where
    Store: ConditionalPairStore,
{
    let value = store
        .load_pair_versioned(first_maximum_bytes, second_maximum_bytes)
        .map_err(NativeContinuationBlobPairPersistenceError::Store)?;
    value
        .map(|versioned| {
            admit_versioned_pair(
                versioned,
                NativeContinuationBlobPairPersistenceRequest::new(
                    &[],
                    &[],
                    first_maximum_bytes,
                    second_maximum_bytes,
                ),
            )
        })
        .transpose()
}

fn admit_versioned_pair<Revision, StoreError>(
    value: pair_store::NativeContinuationVersionedBlobPair<Revision>,
    request: NativeContinuationBlobPairPersistenceRequest<'_>,
) -> NativeContinuationBlobPairPersistenceResult<
    NativeContinuationBlobPairVersionedLoad<Revision>,
    StoreError,
> {
    admit_member(
        NativeContinuationBlobPairMember::First,
        value.pair.first.len(),
        request.first_maximum_bytes,
    )?;
    admit_member(
        NativeContinuationBlobPairMember::Second,
        value.pair.second.len(),
        request.second_maximum_bytes,
    )?;
    Ok(NativeContinuationBlobPairVersionedLoad {
        first: value.pair.first,
        revision: value.revision,
        second: value.pair.second,
    })
}

/// Atomically persists both blobs and then confirms pair durability.
///
/// # Errors
///
/// Returns only prepublication byte-limit or pair-store failure. Durability
/// failure after commit is returned as committed `Published` evidence.
pub fn persist_blob_pair_durably<Store>(
    store: &mut Store,
    request: NativeContinuationBlobPairPersistenceRequest<'_>,
) -> NativeContinuationBlobPairDurableStoreResult<Store>
where
    Store: DurablePairStore,
{
    let write = persist_blob_pair(store, request)?;
    match store.confirm_pair_durability() {
        Ok(()) => {
            Ok(NativeContinuationBlobPairDurablePersistence::Durable { write })
        },
        Err(durability_error) => {
            Ok(NativeContinuationBlobPairDurablePersistence::Published {
                durability_error,
                write,
            })
        },
    }
}

/// Atomically restores both opaque pair members under independent byte bounds.
///
/// # Errors
///
/// Returns pair-store or post-load first/second byte-limit failure.
pub fn restore_blob_pair<Store>(
    store: &mut Store,
    first_maximum_bytes: NonZeroUsize,
    second_maximum_bytes: NonZeroUsize,
) -> NativeContinuationBlobPairPersistenceResult<
    NativeContinuationBlobPairPersistenceLoad,
    Store::Error,
>
where
    Store: PairStore,
{
    let Some(pair) = store
        .load_pair(first_maximum_bytes, second_maximum_bytes)
        .map_err(NativeContinuationBlobPairPersistenceError::Store)?
    else {
        return Ok(NativeContinuationBlobPairPersistenceLoad::Missing);
    };
    admit_member(
        NativeContinuationBlobPairMember::First,
        pair.first.len(),
        first_maximum_bytes,
    )?;
    admit_member(
        NativeContinuationBlobPairMember::Second,
        pair.second.len(),
        second_maximum_bytes,
    )?;
    Ok(NativeContinuationBlobPairPersistenceLoad::Present {
        first: pair.first,
        second: pair.second,
    })
}
