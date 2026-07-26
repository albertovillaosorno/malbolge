// File:
//   - main.rs
// Path:
//   - interop/algorithms/quality/main.rs
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
//   - Deterministic modernization and lowerability rewrites for generated C.
// - Must-Not:
//   - Bypass tools/tidy or hide behavior changes behind lint suppressions.
// - Allows:
//   - Inputs: user-supplied C source, compile metadata, and explicit
//     interoperability adapters.
//   - Outputs: modern deterministic C accepted by the declared target profile.
//   - Side effects: generated artifacts only below the declared local out root.
// - Split-When:
//   - Split when one rewrite family becomes a reusable independently tested
//     pass.
// - Merge-When:
//   - Merge when another pass owns the same modernization and conformance
//     rules.
// - Summary:
//   - Normalize user-supplied interoperability C into verified lowerable
//     source.
// - Description:
//   - Converts repeated defects into deterministic AST-aware transformation
//     rules.
// - Usage:
//   - Runs before amalgamation and before end-to-end C-to-Malbolge compilation.
// - Defaults:
//   - Unsupported or unverified behavior-affecting rewrites fail closed.
//
// Related documents:
// - docs/technical/interoperability/doom-modernization.md
// - docs/todo/open/applications/doom-quality-and-modernization-pass.mdc
//
// Large file:
//   - false

//! Deterministic quality and modernization pass for interoperability C.
//!
//! This pass is the first DOOM interoperability stage. It transforms an
//! explicitly supplied multi-translation-unit source tree into deterministic,
//! modern C suitable for the declared guest profile. Source semantics, macro
//! state, linkage, ABI, and control flow require Clang/AST evidence; blanket
//! suppressions and hidden hand edits are not accepted transformations.
//!
//! The user-owned input tree is immutable. Generated output lives only under
//! this algorithm's ignored `out/` directory and must be reproducible from the
//! admitted input plus versioned transformation logic.
