// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - LicenseRef-Proprietary
// Confidential:
//   - true
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Source-verified two-branch C loop with nonzero-leading binary output.
// - Must-Not:
//   - Replace guest execution with host-computed output.
// - Allows:
//   - Inputs: pinned Clang source and complete typed SSA effects.
//   - Outputs: six actual guest bytes including an interior NUL.
//   - Side effects: six source-proven putchar effects only.
// - Split-When:
//   - General C control flow executes in the guest runtime.
// - Merge-When:
//   - Verified guest output synthesis subsumes this bounded regression.
// - Summary:
//   - Both conditional iterations emit three distinct call effects.

#include <stdio.h>
void emit(void) {
    unsigned a = 53U;
    unsigned b = 54U;
    unsigned c = 53U;
    unsigned i = 0U;
    while (i < 2U) {
        if ((i & 1U) == 0U) {
            putchar((int)a);
            putchar((int)b);
            putchar((int)c);
            a = 0U;
            b = 80U;
            c = 27U;
        } else {
            putchar((int)a);
            putchar((int)b);
            putchar((int)c);
        }
        i = i + 1U;
    }
}
