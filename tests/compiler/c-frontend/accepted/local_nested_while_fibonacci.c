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
//   - Source-checked nested while loops in complete unsigned C Fibonacci.
// - Must-Not:
//   - Treat a host-computed oracle as guest execution or admit dynamic input.
// - Allows:
//   - Inputs: unsigned recurrence, two loops, conditional mask and putchar.
//   - Outputs: twelve genuine guest bytes after finite C replay.
//   - Side effects: selected guest output only.
// - Split-When:
//   - General dynamic guest control makes bounded loop replay unnecessary.
// - Merge-When:
//   - A general while loop lowerer proves the same source semantics.
// - Summary:
//   - A directly nested while body updates both controlling locals.
//
#include <stdio.h>
void emit(void) {
    unsigned a = 1U;
    unsigned b = 1U;
    for (unsigned i = 0U; i < 12U; ++i) {
        unsigned next = (a + b) & 255U;
        unsigned mask = 0U;
        unsigned outer = 0U;
        unsigned inner = 0U;
        while (outer < 1U)
            while (inner < 1U) {
                if ((next & 1U) != 0U) {
                    mask ^= 26U;
                } else {
                    mask |= 0U;
                }
                inner += 1U;
                outer += 1U;
            }
        putchar((int)((next ^ mask) & 31U));
        a = b;
        b = next;
    }
}
