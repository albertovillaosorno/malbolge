// File:
//   - main.rs
// Path:
//   - interop/algorithms/amalgamate/main.rs
//
// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE
// Path-Rule:
//   - All paths in this header are repository-root relative.
//
// Boundary-Contract:
// - Owns:
//   - Deterministic multi-translation-unit C amalgamation for interoperability.
// - Must-Not:
//   - Treat textual concatenation as semantic C translation-unit merging.
// - Allows:
//   - Inputs: normalized quality-stage C, compile metadata, and pinned Clang
//     facts.
//   - Outputs: canonical generated single-file C with retained provenance.
//   - Side effects: generated artifacts only below the declared local out root.
// - Split-When:
//   - Split when one transformation family gains an independent verified API.
// - Merge-When:
//   - Merge when another interoperability pass owns identical source semantics.
// - Summary:
//   - Canonicalize a lawful external C tree into one deterministic C artifact.
// - Description:
//   - Uses semantic frontend evidence to preserve translation-unit behavior.
// - Usage:
//   - Runs before quality normalization and C-to-Malbolge lowerability checks.
// - Defaults:
//   - Ambiguous source semantics or missing compile metadata fails closed.
//
// Related documents:
// - docs/technical/interoperability/doom-amalgamation.md
// - docs/todo/open/applications/
//   user-supplied-doom-source-interoperability-generator.mdc
//
// Large file:
//   - false

//! Deterministic C-source amalgamation for normalized interoperability inputs.
//!
//! This pass runs only after the quality stage. It combines an accepted
//! multi-translation-unit C tree into one canonical translation artifact while
//! preserving preprocessing, linkage, declarations, ordering, provenance, and
//! observable native behavior. Plain textual concatenation is never sufficient.
//!
//! Generated output lives only under this algorithm's ignored `out/` directory
//! and must be byte-reproducible from the normalized input and versioned logic.
