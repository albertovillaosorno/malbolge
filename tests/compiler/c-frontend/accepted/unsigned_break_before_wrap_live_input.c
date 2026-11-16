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
//   - Source-authenticated unsigned loop exit before a wrapping step.
// - Must-Not:
//   - Execute a decrement after a selected break or fold guest input.
// - Allows:
//   - Inputs: five successful guest bytes and a finite unsigned counter.
//   - Outputs: five live reads, with the third byte written twice.
//   - Side effects: five getchar and six putchar calls.
// - Split-When:
//   - General guest runtime C control flow replaces bounded induction.
// - Merge-When:
//   - Source-proven early exits and unsigned wrap checks share an engine.
// - Summary:
//   - A selected break prevents the final unsigned decrement from wrapping.
//
#include <stdio.h>
void emit(void) {
    for (unsigned i = 9U; i > 0U; i -= 2U) {
        int current = getchar();
        if (i == 5U) {
            putchar(current);
            putchar(current);
        } else {
            putchar(current);
        }
        if (i == 1U) {
            break;
        }
    }
}
