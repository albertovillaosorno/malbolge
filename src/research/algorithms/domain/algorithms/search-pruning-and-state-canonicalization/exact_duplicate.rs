// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Exact duplicate pruning over pre-identity candidate byte sequences.
// - Must-Not:
//   - Merge candidates by hash, prefix, similarity, or heuristic state keys.
// - Allows:
//   - Inputs: ordered immutable candidate byte sequences.
//   - Outputs: stable first representatives and exact representative mapping.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - Split when a stronger proved equivalence rule gains independent evidence.
// - Merge-When:
//   - Merge when production search owns the same exact pre-identity rule.
// - Summary:
//   - Establishes the most conservative exact duplicate pruning baseline.
// - Description:
//   - Only full byte equality may assign two inputs to one representative.
// - Usage:
//   - Composed by `tests/search_pruning_research.rs`.
// - Defaults:
//   - No profile-specific or semantic equivalence beyond exact bytes is
//     claimed.
//

use std::collections::BTreeMap;
use std::collections::btree_map::Entry;

/// Exact partition produced by conservative duplicate pruning.
#[derive(Debug, Eq, PartialEq)]
pub struct ExactDuplicatePartition {
    /// First representative index selected for every input candidate.
    pub canonical_indices: Vec<usize>,
    /// Stable first occurrence retained for every exact byte class.
    pub representative_indices: Vec<usize>,
}

/// Return stable first representatives and representative index per input.
///
/// Equality is complete byte equality. Logical search identity is assigned
/// after this operation, so hashes, prefixes, similarity, and heuristic state
/// keys cannot merge candidates in this baseline.
#[must_use]
pub fn prune_exact_duplicates(candidates: &[&[u8]]) -> ExactDuplicatePartition {
    let mut canonical_indices = Vec::with_capacity(candidates.len());
    let mut first_indices = BTreeMap::<&[u8], usize>::new();
    let mut representative_indices = Vec::new();
    for (index, candidate) in candidates.iter().copied().enumerate() {
        let representative = match first_indices.entry(candidate) {
            Entry::Occupied(entry) => *entry.get(),
            Entry::Vacant(entry) => {
                representative_indices.push(index);
                *entry.insert(index)
            },
        };
        canonical_indices.push(representative);
    }
    ExactDuplicatePartition {
        canonical_indices,
        representative_indices,
    }
}
