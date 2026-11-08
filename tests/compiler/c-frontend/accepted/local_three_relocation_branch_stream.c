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
//   - Three source-distinct bytes from a stateful conditional C recurrence.
// - Must-Not:
//   - Confuse closed C constant folding with guest runtime state.
// - Allows:
//   - Inputs: three bounded C loop iterations and proven arithmetic/branch.
//   - Outputs: independently VM-verified 51 a2 fe with three real relocations.
//   - Side effects: three ordered putchar calls only.
// - Split-When:
//   - A general runtime guest state compiler subsumes closed C projection.
// - Merge-When:
//   - General source-to-guest stream verification covers this pattern.
// - Summary:
//   - Exercises the bounded three-j guest proposal through the real C path.

#include <stdio.h>

void emit(void) {
    unsigned a = 1U;
    unsigned b = 1U;
    for (unsigned i = 0U; i < 3U; ++i) {
        unsigned next = (a + b) & 255U;
        if ((next & 1U) == 0U) {
            putchar((int)(((next * 40U) + 1U) & 255U));
        } else {
            putchar((int)(((next * 46U) + 24U) & 255U));
        }
        a = b;
        b = next;
    }
}
