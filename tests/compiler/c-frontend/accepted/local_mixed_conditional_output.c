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
//   - Full bounded C recurrence with source-proven branch-local output effects.
// - Must-Not:
//   - Claim guest runtime branches or silently skip unselected C effects.
// - Allows:
//   - Inputs: two source-proven unsigned recurrence trips and both C arms.
//   - Outputs: independently derived Q. bytes through normative guest I/O.
//   - Side effects: selected putchar calls only.
// - Split-When:
//   - Runtime C control-flow lowering supersedes compile-time replay.
// - Merge-When:
//   - General guest C I/O lowering proves arbitrary branch effects.
// - Summary:
//   - Both arms mutate local state then emit a source-derived byte.

#include <stdio.h>

void emit(void) {
    unsigned a = 1U;
    unsigned b = 1U;
    unsigned i = 0U;
    while (i < 2U) {
        unsigned next = (a + b) & 255U;
        if ((i & 1U) == 0U) {
            a = next;
            putchar((int)(next ^ 83U));
        } else {
            b = (next + 1U) & 255U;
            putchar((int)(next ^ 45U));
        }
        i = i + 1U;
    }
}
