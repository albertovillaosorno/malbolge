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
//   - Process-local exact retention selection for opaque blob-pair revisions.
// - Must-Not:
//   - Infer chronology, capacity, expiry, eviction order, or cleanup
//     scheduling.
// - Allows:
//   - Inputs: explicit caller retain/release operations on opaque revisions.
//   - Outputs: one exact deduplicated preservation slice in caller insertion
//     order.
//   - Side effects: process-local ownership mutation only.
// - Split-When:
//   - Durable retention journals or asynchronous scheduling gain authority.
// - Merge-When:
//   - One application owner subsumes exact revision retention and reclamation.
// - Summary:
//   - Tracks only opaque revisions callers explicitly require to survive
//     cleanup.
// - Description:
//   - Equality controls membership; insertion order has no temporal semantics.
// - Usage:
//   - Borrow `revisions()` when constructing one explicit reclamation request.
// - Defaults:
//   - New retention starts empty and never selects a revision automatically.
//

//! Process-local exact preservation ownership for atomic-pair revisions.

/// Exact process-local set of opaque pair revisions selected for preservation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeContinuationBlobPairRetention<Revision> {
    revisions: Vec<Revision>,
}

impl<Revision> NativeContinuationBlobPairRetention<Revision> {
    /// Constructs an empty exact-retention owner.
    #[must_use]
    pub const fn new() -> Self {
        Self { revisions: Vec::new() }
    }

    /// Borrows revisions in caller insertion order without chronology
    /// semantics.
    #[must_use]
    pub fn revisions(&self) -> &[Revision] {
        &self.revisions
    }
}

impl<Revision: Eq> NativeContinuationBlobPairRetention<Revision> {
    /// Releases one exact retained revision, reporting whether it was present.
    pub fn release(&mut self, revision: &Revision) -> bool {
        let Some(index) = self
            .revisions
            .iter()
            .position(|current| current == revision)
        else {
            return false;
        };
        let _released = self.revisions.remove(index);
        true
    }

    /// Retains one exact revision once, reporting whether membership changed.
    pub fn retain(&mut self, revision: Revision) -> bool {
        if self.revisions.contains(&revision) {
            false
        } else {
            self.revisions.push(revision);
            true
        }
    }
}

impl<Revision> Default for NativeContinuationBlobPairRetention<Revision> {
    fn default() -> Self {
        Self::new()
    }
}
