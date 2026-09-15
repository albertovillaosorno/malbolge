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
