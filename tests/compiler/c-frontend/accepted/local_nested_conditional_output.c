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
//   - Full C while recurrence with nested branch-local writes and output.
// - Must-Not:
//   - Model compile-time branch replay as dynamic Malbolge control flow.
// - Allows:
//   - Inputs: two source-proven unsigned recurrence trips and nested C arms.
//   - Outputs: independently computed Q. through actual guest putchar.
//   - Side effects: selected guest output calls only.
// - Split-When:
//   - General C control-flow lowering replaces bounded static replay.
// - Merge-When:
//   - The stateful C-to-guest compiler subsumes this bounded example.
// - Summary:
//   - Nested conditionals update distinct locals before emitting bytes.

#include <stdio.h>

void emit(void) {
    unsigned a = 1U;
    unsigned b = 1U;
    unsigned i = 0U;
    while (i < 2U) {
        unsigned next = (a + b) & 255U;
        if ((i & 1U) == 0U) {
            if ((next & 1U) == 0U) {
                a = next;
                putchar((int)(next ^ 83U));
            } else {
                a = (next + 1U) & 255U;
                putchar((int)(next ^ 84U));
            }
        } else {
            if ((next & 1U) != 0U) {
                b = (next + 1U) & 255U;
                putchar((int)(next ^ 45U));
            } else {
                b = next;
                putchar((int)(next ^ 44U));
            }
        }
        i = i + 1U;
    }
}
