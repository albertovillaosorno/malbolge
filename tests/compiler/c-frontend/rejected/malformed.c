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
//   - One deterministic normalized C frontend integration fixture.
// - Must-Not:
//   - Depend on a native host ABI, physical source path, or external state.
// - Allows:
//   - Inputs: pinned C23 parser/type/constant/source-location semantics only.
//   - Outputs: accepted or rejected frontend normalization evidence.
//   - Side effects: none.
// - Split-When:
//   - Another independent frontend normalization condition needs evidence.
// - Merge-When:
//   - Another fixture exercises this exact semantic boundary.
// - Summary:
//   - Exercises one version-one normalized C frontend boundary.
// - Description:
//   - Consumed only by explicit frontend integration tests.
// - Usage:
//   - Selected by `tests/test_c_frontend.py` with a logical source identity.
// - Defaults:
//   - Clang internals and host paths are never artifact authority.
//

//! Deterministic normalized C frontend integration fixture.

int main( { return 0; }
