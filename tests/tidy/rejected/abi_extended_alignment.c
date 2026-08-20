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
//   - One deterministic guest-C ABI fixture for tools/tidy regression evidence.
// - Must-Not:
//   - Depend on native host ABI, operating-system APIs, or external state.
// - Allows:
//   - Inputs: compile-time C23 language and ABI evidence only.
//   - Outputs: deterministic accept/reject evidence for malbolge-c32-v1.
//   - Side effects: none.
// - Split-When:
//   - Split when the fixture covers an independent ABI diagnostic family.
// - Merge-When:
//   - Merge when another fixture exercises the exact same boundary condition.
// - Summary:
//   - Exercises one malbolge-c32-v1 ABI boundary.
// - Description:
//   - Compiled or inspected only by explicit guest-C compatibility tests.
// - Usage:
//   - Selected explicitly by the deterministic C ABI regression suite.
// - Defaults:
//   - No host ABI behavior is authoritative.
//

//! Rejects standard alignments beyond the ABI v1 maximum.

struct TooAligned {
    _Alignas(32) int value;
};
