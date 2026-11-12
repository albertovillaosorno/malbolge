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
//   - Whole-C Fibonacci conditional arms containing unbraced do-while.
// - Must-Not:
//   - Impersonate normative guest stdout or admit unchecked C side effects.
// - Allows:
//   - Inputs: bounded unsigned loops and source-proven do-while arms.
//   - Outputs: twelve selected masked Fibonacci bytes on the real guest.
//   - Side effects: selected guest putchar only.
// - Split-When:
//   - Dynamic guest C control supersedes finite source-state replay.
// - Merge-When:
//   - General conditional loop lowering proves the same semantics.
// - Summary:
//   - Both arms run a post-test loop, but only the selected arm mutates mask.
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
            do {
                mask ^= 26U;
                steps += 1U;
            } while (steps < 1U);
        else
            do {
                mask |= 0U;
                steps += 1U;
            } while (steps < 1U);
        putchar((int)((next ^ mask) & 31U));
        a = b;
        b = next;
    }
}
