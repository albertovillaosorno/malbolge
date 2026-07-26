// File:
//   - amalgamate.rs
// Path:
//   - interop/algorithms/amalgamate.rs
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
//   - Inputs: user-supplied C source, compile metadata, and pinned Clang facts.
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
// - docs/todo/open/applications/user-supplied-doom-source-interoperability-generator.mdc
//
// Large file:
//   - false
////! Deterministic C-source amalgamation for interoperability inputs.
//!
//! This module will turn a user-supplied multi-file C codebase into one
//! semantically equivalent translation artifact such as `doom.c`.
//!
//! The algorithm is deliberately AST/preprocessor driven. Plain concatenation
//! is not sufficient because separate translation units may contain colliding
//! internal-linkage symbols, different macro environments, conditional includes,
//! and file-local declarations whose meaning changes when files are merged.
//!
//! Planned pipeline:
//!
//! 1. Inventory the exact user-supplied source tree and compile configuration.
//! 2. Parse and preprocess every admitted translation unit with pinned Clang.
//! 3. Build a stable symbol/provenance table before any textual rewriting.
//! 4. Rename colliding internal-linkage identifiers deterministically.
//! 5. Materialize required declarations and definitions in dependency order.
//! 6. Preserve macro-expanded semantics without carrying host-specific includes.
//! 7. Emit one canonical `doom.c` with deterministic ordering and provenance.
//! 8. Compile both the original program and the amalgamated program and run
//!    differential behavior tests before the artifact is admitted downstream.
//!
//! Every transformation must be reproducible. A manual source edit discovered
//! during development becomes an explicit transformation rule or the pipeline
//! remains incomplete.
