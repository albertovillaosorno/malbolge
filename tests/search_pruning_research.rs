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
//   - Cargo composition for search-pruning research tests.
// - Must-Not:
//   - Implement candidate equivalence or production search semantics.
// - Allows:
//   - Inputs: mirrored pruning implementation and adversarial fixtures.
//   - Outputs: one Cargo-discoverable research test target.
//   - Side effects: composition only.
// - Split-When:
//   - Split when independent pruning families gain separate test lifecycles.
// - Merge-When:
//   - Merge when production optimizer tests own these exact contracts.
// - Summary:
//   - Composes exact duplicate pruning research evidence.
// - Description:
//   - Keeps executable research under its stable mirror owner.
// - Usage:
//   - Auto-discovered by Cargo workspace tests.
// - Defaults:
//   - No production optimizer API is exported from this target.
//

//! Cargo composition root for search-pruning research.

use malbolge as _;

/// Exact duplicate implementation composed from the research mirror.
pub mod exact_duplicate {
    include!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/src/research/algorithms/domain/algorithms/search-pruning-and-state-",
        "canonicalization/exact_duplicate.rs",
    ));
}
mod exact_duplicate_tests {
    include!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/tests/function/algorithms/domain/search-pruning-and-state-",
        "canonicalization/exact_duplicate.rs",
    ));
}
