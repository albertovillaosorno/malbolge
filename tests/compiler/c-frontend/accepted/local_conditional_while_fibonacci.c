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
//   - Full C Fibonacci with unbraced conditional while arms.
// - Must-Not:
//   - Replace guest C control or output with unverified host stdout.
// - Allows:
//   - Inputs: two source-proven bounded while arms and unsigned recurrence.
//   - Outputs: twelve masked Fibonacci bytes in the normative guest VM.
//   - Side effects: selected putchar only.
// - Split-When:
//   - General guest-side dynamic C control supersedes source replay.
// - Merge-When:
//   - General conditional loop conformance covers these two arms.
// - Summary:
//   - Each selected while produces a distinct, source-checked mask.
//
#include <stdio.h>
void emit(void) {
    unsigned a = 1U;
    unsigned b = 1U;
    for (unsigned i = 0U; i < 12U; ++i) {
        unsigned next = (a + b) & 255U;
        unsigned mask = 0U;
        unsigned steps = 0U;
        if ((next & 1U) != 0U)
            while (steps < 2U) {
                mask += 13U;
                steps += 1U;
            }
        else
            while (steps < 1U) {
                mask += 0U;
                steps += 1U;
            }
        putchar((int)((next ^ mask) & 31U));
        a = b;
        b = next;
    }
}
