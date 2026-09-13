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
//   - Storage-neutral bounded byte transport for one preconfigured telemetry
//     blob.
// - Must-Not:
//   - Name filesystems, choose paths, interpret telemetry bytes, or select
//     policy.
// - Allows:
//   - Inputs: one positive read limit or one immutable canonical byte slice.
//   - Outputs: absent/present owned bytes or adapter-local failure evidence.
//   - Side effects: delegated entirely to the selected outbound adapter.
// - Split-When:
//   - Multi-object transactions or compare-and-swap publication gain semantics.
// - Merge-When:
//   - One outbound storage contract owns the same bounded blob lifecycle.
// - Summary:
//   - Carries admitted telemetry bytes to replaceable durable storage.
// - Description:
//   - Adapters bind location and must make replacement all-or-nothing.
// - Usage:
//   - Consumed by cached-retry telemetry persistence application use cases.
// - Defaults:
//   - Missing blobs are not errors and reads must honor the supplied bound.
//

//! Outbound bounded blob-storage contract for cached-retry telemetry.

use std::num::NonZeroUsize;

/// Result of confirming durability after one committed blob replacement.
pub type NativeContinuationCachedRetryTelemetryBlobDurabilityResult<
    DurabilityError,
> = Result<(), DurabilityError>;

/// Bounded absent/present load result returned by one blob-store adapter.
pub type NativeContinuationCachedRetryTelemetryBlobLoadResult<StoreError> =
    Result<Option<Vec<u8>>, StoreError>;

/// Replaceable storage for one caller-preconfigured telemetry blob location.
pub trait NativeContinuationCachedRetryTelemetryBlobStore {
    /// Adapter-local storage failure retained by application orchestration.
    type Error;

    /// Loads at most `maximum_bytes` from the configured blob location.
    ///
    /// `Ok(None)` means no blob exists. Implementations must not return a value
    /// larger than `maximum_bytes`; application orchestration rechecks this
    /// invariant before decoding untrusted adapter output.
    ///
    /// # Errors
    ///
    /// Returns only adapter-local read or representation failures.
    fn load(
        &mut self,
        maximum_bytes: NonZeroUsize,
    ) -> NativeContinuationCachedRetryTelemetryBlobLoadResult<Self::Error>;

    /// Atomically replaces the configured blob with all supplied bytes.
    ///
    /// Failure must leave the previously published blob authoritative. This
    /// contract does not prescribe filesystem, database, or remote-store
    /// mechanics.
    ///
    /// # Errors
    ///
    /// Returns only adapter-local publication failures.
    fn replace(&mut self, bytes: &[u8]) -> Result<(), Self::Error>;
}
/// Optional post-publication durability confirmation for one blob store.
///
/// This capability is deliberately separate from `replace`: publication has
/// already committed before confirmation begins, so confirmation failure must
/// never be reported as if the prior blob remained authoritative.
pub trait NativeContinuationCachedRetryTelemetryDurableBlobStore:
    NativeContinuationCachedRetryTelemetryBlobStore
{
    /// Adapter-local durability-confirmation failure after publication.
    type DurabilityError;

    /// Confirms host durability for the most recently committed publication.
    ///
    /// # Errors
    ///
    /// Returns post-publication durability evidence. The new blob remains the
    /// process-visible publication even when confirmation fails.
    fn confirm_durability(
        &mut self,
    ) -> NativeContinuationCachedRetryTelemetryBlobDurabilityResult<
        Self::DurabilityError,
    >;
}
