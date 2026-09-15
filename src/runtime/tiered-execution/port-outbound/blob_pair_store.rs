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
//   - Storage-neutral atomic transport for one preconfigured opaque blob pair.
// - Must-Not:
//   - Name filesystems, choose locations, interpret bytes, or emulate a pair
//     transaction with sequential single-blob writes.
// - Allows:
//   - Inputs: two positive read limits or two immutable byte slices.
//   - Outputs: missing/present owned pair bytes or adapter-local failure.
//   - Side effects: delegated entirely to the selected outbound adapter.
// - Split-When:
//   - N-object transactions or distributed consensus gain semantics.
// - Merge-When:
//   - One outbound contract owns the exact same atomic pair lifecycle.
// - Summary:
//   - Carries two opaque blobs through one all-or-nothing publication boundary.
// - Description:
//   - Pair replacement either publishes both values or preserves the prior
//     pair.
// - Usage:
//   - Consumed by bounded pair-persistence application use cases.
// - Defaults:
//   - Missing pair state is not an error and partial pair state is
//     unrepresentable.
//

//! Outbound atomic blob-pair storage contract for tiered execution.

use std::num::NonZeroUsize;

/// Exact owned bytes from one atomically loaded blob pair.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeContinuationBlobPair {
    /// First opaque blob bytes.
    pub first: Vec<u8>,
    /// Second opaque blob bytes.
    pub second: Vec<u8>,
}

/// Bounded absent/present pair load result returned by one adapter.
pub type NativeContinuationBlobPairLoadResult<StoreError> =
    Result<Option<NativeContinuationBlobPair>, StoreError>;

/// Result of confirming durability after one committed pair replacement.
pub type NativeContinuationBlobPairDurabilityResult<DurabilityError> =
    Result<(), DurabilityError>;

/// Atomic storage for one caller-preconfigured pair of blob locations.
pub trait NativeContinuationBlobPairStore {
    /// Adapter-local pair storage failure retained by application
    /// orchestration.
    type Error;

    /// Atomically loads the current pair under independent positive byte
    /// bounds.
    ///
    /// `Ok(None)` means no pair publication exists. Implementations must never
    /// expose a state in which exactly one member of a committed pair exists.
    /// Application orchestration rechecks both returned byte lengths.
    ///
    /// # Errors
    ///
    /// Returns adapter-local read, representation, or transaction failures.
    fn load_pair(
        &mut self,
        first_maximum_bytes: NonZeroUsize,
        second_maximum_bytes: NonZeroUsize,
    ) -> NativeContinuationBlobPairLoadResult<Self::Error>;

    /// Atomically replaces both configured blobs with the supplied bytes.
    ///
    /// Failure must leave the complete previously published pair authoritative.
    /// Sequential publication of one member followed by the other does not
    /// satisfy this contract.
    ///
    /// # Errors
    ///
    /// Returns only adapter-local transaction/publication failures.
    fn replace_pair(
        &mut self,
        first: &[u8],
        second: &[u8],
    ) -> Result<(), Self::Error>;
}

/// One atomically observed blob pair plus its opaque publication revision.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeContinuationVersionedBlobPair<Revision> {
    /// Complete opaque pair observed at this revision.
    pub pair: NativeContinuationBlobPair,
    /// Adapter-owned opaque publication revision.
    pub revision: Revision,
}

/// Outcome of one revision-conditional atomic pair publication.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationBlobPairConditionalPublication<Revision> {
    /// Current publication revision differed from caller expectation.
    Conflict {
        /// Complete bounded current pair plus revision, or absence.
        current: Option<NativeContinuationVersionedBlobPair<Revision>>,
    },
    /// Replacement committed under a fresh opaque revision.
    Published {
        /// Exact opaque revision assigned to the committed replacement.
        revision: Revision,
    },
}

/// Immutable revision-conditional pair publication request.
#[derive(Clone, Copy, Debug)]
pub struct NativeContinuationBlobPairConditionalRequest<'request, Revision> {
    /// Opaque expected revision, or absence expectation.
    pub expected: Option<&'request Revision>,
    /// First replacement member bytes.
    pub first: &'request [u8],
    /// Positive first-member read/conflict bound.
    pub first_maximum_bytes: NonZeroUsize,
    /// Second replacement member bytes.
    pub second: &'request [u8],
    /// Positive second-member read/conflict bound.
    pub second_maximum_bytes: NonZeroUsize,
}

/// Conditional publication result specialized to one pair store.
pub type NativeContinuationConditionalBlobPairStoreResult<Store> = Result<
    NativeContinuationBlobPairConditionalPublication<
        <Store as NativeContinuationConditionalBlobPairStore>::Revision,
    >,
    <Store as NativeContinuationBlobPairStore>::Error,
>;

/// Versioned load result specialized to one pair store.
pub type NativeContinuationVersionedBlobPairStoreLoadResult<Store> = Result<
    Option<
        NativeContinuationVersionedBlobPair<
            <Store as NativeContinuationConditionalBlobPairStore>::Revision,
        >,
    >,
    <Store as NativeContinuationBlobPairStore>::Error,
>;

/// Optional revision-conditional publication for one atomic blob-pair store.
pub trait NativeContinuationConditionalBlobPairStore:
    NativeContinuationBlobPairStore + Sized
{
    /// Adapter-owned opaque publication revision.
    type Revision: Clone + Eq;

    /// Conditionally replaces both blobs when current revision matches
    /// expected.
    ///
    /// `None` matches only missing publication. Conflict returns the complete
    /// bounded current pair plus its opaque revision and performs no mutation.
    ///
    /// # Errors
    ///
    /// Returns adapter-local coordination, read, or publication failures.
    fn compare_and_swap_pair(
        &mut self,
        request: NativeContinuationBlobPairConditionalRequest<
            '_,
            Self::Revision,
        >,
    ) -> NativeContinuationConditionalBlobPairStoreResult<Self>;

    /// Loads one complete bounded pair and revision from one manifest commit.
    ///
    /// # Errors
    ///
    /// Returns adapter-local read, representation, or transaction failures.
    fn load_pair_versioned(
        &mut self,
        first_maximum_bytes: NonZeroUsize,
        second_maximum_bytes: NonZeroUsize,
    ) -> NativeContinuationVersionedBlobPairStoreLoadResult<Self>;
}

/// Optional post-publication durability confirmation for one blob-pair store.
///
/// Publication has already committed before confirmation begins, so durability
/// failure must never be reported as if the previous pair remained
/// authoritative.
pub trait NativeContinuationDurableBlobPairStore:
    NativeContinuationBlobPairStore
{
    /// Adapter-local durability failure after pair publication committed.
    type DurabilityError;

    /// Confirms durability for the most recently committed pair publication.
    ///
    /// # Errors
    ///
    /// Returns post-publication durability evidence. The new pair remains the
    /// process-visible publication even when confirmation fails.
    fn confirm_pair_durability(
        &mut self,
    ) -> NativeContinuationBlobPairDurabilityResult<Self::DurabilityError>;
}

/// Reclamation result specialized to one reclaimable pair store.
pub type NativeContinuationReclaimableBlobPairStoreResult<Store> = Result<
    <Store as NativeContinuationReclaimableBlobPairStore>::Reclamation,
    <Store as NativeContinuationReclaimableBlobPairStore>::ReclamationError,
>;

/// Optional explicit reclamation for superseded atomic-pair publications.
pub trait NativeContinuationReclaimableBlobPairStore:
    NativeContinuationConditionalBlobPairStore
{
    /// Adapter-owned successful or partial reclamation evidence.
    type Reclamation;
    /// Adapter-owned pre-reclamation failure evidence.
    type ReclamationError;

    /// Reclaims superseded pair publications while preserving exact revisions.
    ///
    /// The current publication must remain authoritative independently of the
    /// caller-provided preserve set. Implementations must compare opaque
    /// revisions only according to their own equality semantics; this contract
    /// defines no chronology, retention window, or scheduling policy.
    ///
    /// # Errors
    ///
    /// Returns adapter-local failure evidence from before cleanup could
    /// proceed.
    fn reclaim_pair_generations(
        &mut self,
        preserved: &[Self::Revision],
    ) -> NativeContinuationReclaimableBlobPairStoreResult<Self>;
}
