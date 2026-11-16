// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Source-authenticated unbraced C input guards and byte identities.
// - Must-Not:
//   - Predict stdin or silently remove a branch with unequal byte effects.
// - Allows:
//   - Inputs: four successful signed getchar bytes.
//   - Outputs: the same four guest bytes, including NUL and high-bit inputs.
//   - Side effects: four actual guest reads and writes.
// - Split-When:
//   - Runtime C branching becomes independently executable in the guest.
// - Merge-When:
//   - Source statement forms share a general guard-domain proof.
// - Summary:
//   - Preserve the live byte on both unbraced guarded paths.
//
#include <stdio.h>
void emit(void) {
    for (unsigned i = 0U; i < 4U; ++i) {
        int current = getchar();
        if (current & 1) putchar(current | 1); else putchar(current & -2);
    }
}
