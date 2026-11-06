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
//   - Four guest bytes from a complete stateful conditional C recurrence.
// - Must-Not:
//   - Substitute host output or assume runtime C integer arithmetic exists.
// - Allows:
//   - Inputs: four bounded C loop iterations, arithmetic and branches.
//   - Outputs: source-proven binary effects from the current Malbolge VM.
//   - Side effects: putchar calls only.
// - Split-When:
//   - The parametric guest-byte-stream compiler replaces closed folding.
// - Merge-When:
//   - General C-state runtime tests cover the same real guest behavior.
// - Summary:
//   - Exercises a fifth guest arithmetic write for four source output effects.

#include <stdio.h>

void emit(void) {
    unsigned a = 1U;
    unsigned b = 1U;
    for (unsigned i = 0U; i < 4U; ++i) {
        unsigned next = (a + b) & 255U;
        if ((next & 1U) == 0U) {
            putchar((int)(((next * 29U) + 251U) & 255U));
        } else {
            putchar((int)((((next / 2U) * 73U) + 119U) & 255U));
        }
        a = b;
        b = next;
    }
}
