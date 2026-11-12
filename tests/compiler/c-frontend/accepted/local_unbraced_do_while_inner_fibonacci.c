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
//   - Full C Fibonacci with unbraced while as the body of a do loop.
// - Must-Not:
//   - Treat compile-time source replay as dynamic guest C control.
// - Allows:
//   - Inputs: source-proven C23 unsigned local control and guest output.
//   - Outputs: twelve masked recurrence bytes in the normative VM.
//   - Side effects: selected putchar calls in the inner loop.
// - Split-When:
//   - General guest control-flow lowering supersedes bounded source replay.
// - Merge-When:
//   - An independent nested-loop compiler corpus covers this feature.
// - Summary:
//   - Inner break advances the enclosing post-test do loop after two bytes.

#include <stdio.h>

void emit(void) {
    unsigned a = 1U;
    unsigned b = 1U;
    unsigned phase = 0U;
    unsigned target = 2U;
    unsigned completed = 0U;
    do
        while (phase < target) {
            unsigned next = (a + b) & 255U;
            if ((next & 1U) == 0U) {
                putchar((int)(next & 31U));
            } else {
                putchar((int)((next ^ 0x1AU) & 31U));
            }
            a = b;
            b = next;
            ++phase;
            if ((phase & 1U) == 0U) {
                ++completed;
                target += 2U;
                break;
            }
        }
    while (completed < 6U);
}
