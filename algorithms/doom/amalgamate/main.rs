// File:
//   - main.rs
// Path:
//   - algorithms/doom/amalgamate/main.rs
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
//   - Generated source-bound materialization of canonical single-file DOOM C.
// - Must-Not:
//   - Consume unaccepted quality input, use plain concatenation as semantic
//     evidence, or require the local single-file oracle at materialization time.
// - Allows:
//   - Inputs: accepted normalized DOOM C plus configured semantic evidence.
//   - Outputs: one deterministic canonical doom_amalgamated.c under out/.
//   - Side effects: generated artifacts only below the declared local out root.
// - Split-When:
//   - Split reusable matching/reconstruction mechanics back into algorithms/diff.
// - Merge-When:
//   - Merge only with a stage that owns identical single-file C semantics.
// - Summary:
//   - Materializes one canonical DOOM C artifact from accepted normalized input.
// - Description:
//   - Future second DOOM consumer of the generic source-bound diff generator.
// - Usage:
//   - Runs after accepted quality output and before C-to-Malbolge lowering when a
//     single C translation artifact is desired.
// - Defaults:
//   - Semantic ambiguity, source-binding failure, or differential mismatch fails
//     closed.
//
// Related documents:
// - docs/technical/tooling/source-bound-diff-generator.md
// - docs/technical/interoperability/doom-amalgamation.md
// - docs/todo/open/applications/
//   user-supplied-doom-source-interoperability-generator.mdc
//
// Large file:
//   - false

//! Generated DOOM amalgamation transformation destination.
//!
//! This checked-in file is currently a scaffold. After quality acceptance, a thin
//! DOOM recipe will use algorithms/diff to generate source-bound materialization
//! logic from accepted normalized input and a local single-file oracle. Pinned
//! Clang evidence remains the semantic authority for amalgamation correctness.
