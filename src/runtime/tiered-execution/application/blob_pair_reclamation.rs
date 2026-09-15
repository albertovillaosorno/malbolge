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
//   - Explicit application orchestration for one atomic-pair reclamation pass.
// - Must-Not:
//   - Choose revisions, infer revision order, schedule cleanup, or name
//     storage.
// - Allows:
//   - Inputs: one caller-selected exact preserve set and reclaimable pair
//     store.
//   - Outputs: adapter-owned reclamation evidence or pre-cleanup failure.
//   - Side effects: exactly one delegated reclamation pass per call.
// - Split-When:
//   - Retention selection or asynchronous scheduling gains application policy.
// - Merge-When:
//   - Another application service owns the exact same reclamation use case.
// - Summary:
//   - Delegates one explicit pair reclamation with caller-selected
//     preservation.
// - Description:
//   - Opaque revisions are forwarded unchanged; no chronology is interpreted.
// - Usage:
//   - Called only after higher-level code selects revisions that must survive.
// - Defaults:
//   - Empty preserve set retains only state the adapter preserves
//     intrinsically.
//

//! Storage-neutral orchestration for explicit atomic-pair reclamation.

use crate::blob_pair_store::NativeContinuationReclaimableBlobPairStore as Store;

/// Immutable caller-selected exact preservation request for one cleanup pass.
#[derive(Clone, Copy, Debug)]
pub struct NativeContinuationBlobPairReclamationRequest<'revision, Revision> {
    preserved: &'revision [Revision],
}

impl<'revision, Revision>
    NativeContinuationBlobPairReclamationRequest<'revision, Revision>
{
    /// Constructs one exact revision-preservation request.
    #[must_use]
    pub const fn new(preserved: &'revision [Revision]) -> Self {
        Self { preserved }
    }

    /// Borrows the exact opaque revisions selected for preservation.
    #[must_use]
    pub const fn preserved(&self) -> &'revision [Revision] {
        self.preserved
    }
}

/// Result of one explicit reclamation pass specialized to one store.
pub type NativeContinuationBlobPairReclamationStoreResult<StoreType> = Result<
    <StoreType as Store>::Reclamation,
    <StoreType as Store>::ReclamationError,
>;

/// Runs one explicit reclamation pass with caller-selected exact preservation.
///
/// # Errors
///
/// Returns the adapter-owned pre-cleanup failure unchanged.
pub fn reclaim_blob_pair_generations<StoreType>(
    store: &mut StoreType,
    request: &NativeContinuationBlobPairReclamationRequest<
        '_,
        StoreType::Revision,
    >,
) -> NativeContinuationBlobPairReclamationStoreResult<StoreType>
where
    StoreType: Store,
{
    store.reclaim_pair_generations(request.preserved())
}
