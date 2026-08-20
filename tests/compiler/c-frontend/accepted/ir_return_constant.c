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
//   - One normalized C semantic fixture consumed by typed-IR lowering evidence.
// - Must-Not:
//   - Depend on host ABI, physical source paths, or unsupported C semantics.
// - Allows:
//   - Inputs: one C23 no-argument function returning an i32 integer constant.
//   - Outputs: deterministic normalized frontend semantics for lowering tests.
//   - Side effects: none.
// - Split-When:
//   - Another independent frontend-to-IR semantic family needs evidence.
// - Merge-When:
//   - Another fixture proves this exact normalized return-constant boundary.
// - Summary:
//   - Anchors the first real normalized-frontend-to-typed-IR lowering slice.
// - Description:
//   - The frontend golden is artifact authority; Rust consumes its semantics.
// - Usage:
//   - Normalized by the pinned Clang frontend with a portable source identity.
// - Defaults:
//   - Unsupported lowering shapes are tested separately and fail closed.
//

//! Normalized frontend fixture for the first typed-IR lowering slice.

int main(void) { return 7; }
