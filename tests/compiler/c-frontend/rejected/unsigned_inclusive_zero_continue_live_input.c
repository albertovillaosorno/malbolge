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
//   - Unsigned continue-at-zero wrap refusal.
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
//   - Continue at zero wraps the counter and cannot terminate.
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
            continue;
        }
    }
}
