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
//   - Source-authenticated inclusive-zero unsigned loop exit.
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
//   - A break at zero makes an always-true unsigned guard finite.
//
#include <stdio.h>
void emit(void) {
    for (unsigned i = 4U; i >= 0U; i--) {
        int current = getchar();
        if (i == 2U) {
            putchar(current);
            putchar(current);
        } else {
            putchar(current);
        }
        if (i == 0U) {
            break;
        }
    }
}
