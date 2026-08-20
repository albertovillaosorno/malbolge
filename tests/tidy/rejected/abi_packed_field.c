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
//   - Rejected guest-C evidence for field-local packed layout.
// - Must-Not:
//   - Define accepted ABI behavior or depend on a host compiler layout.
// - Allows:
//   - Inputs: pinned Clang parsing under the deterministic guest profile.
//   - Outputs: MALBOLGE-ABI-002 rejection evidence.
//   - Side effects: none.
// - Split-When:
//   - Split when another exclusion needs independent source evidence.
// - Merge-When:
//   - Merge when packed-field evidence is covered by an equivalent fixture.
// - Summary:
//   - Reject a packed field under malbolge-c32-v1.
// - Description:
//   - Exercises packed layout attached to a field rather than its record.
// - Usage:
//   - Consumed by native-analysis plugin regression tests.
// - Defaults:
//   - No host ABI behavior is authoritative.
//

//! Rejects field-local packed layout in ABI v1.

struct PackedField {
    char tag;
    int value __attribute__((packed));
};
