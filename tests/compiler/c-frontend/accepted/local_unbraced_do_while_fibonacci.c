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
//   - Complete C Fibonacci with an unbraced do nested in while.
// - Must-Not:
//   - Claim runtime C loops or impersonate actual guest output.
// - Allows:
//   - Inputs: checked C23 state and directly nested while/do predicates.
//   - Outputs: twelve branch-selected masked recurrence bytes.
//   - Side effects: bounded C putchar calls.
// - Split-When:
//   - Genuine guest loop lowering independently supports this C family.
// - Merge-When:
//   - A generalized source-backed loop corpus covers this behavior.
// - Summary:
//   - The inner do decrements the outer bound during its two trips.
// - Description:
//   - Guest VM parity must match independent unsigned C state replay.
// - Usage:
//   - Compile through the pinned source C pipeline.
// - Defaults:
//   - No output artifact may be published on a failed source proof.
//

#include <stdio.h>
void emit(void) {
    unsigned a = 1U;
    unsigned b = 1U;
    unsigned remaining = 12U;
    unsigned phase = 0U;
    while (remaining > 0U)
        do {
            unsigned next = (a + b) & 255U;
            if ((next & 1U) == 0U) {
                putchar((int)(next & 31U));
            } else {
                putchar((int)((next ^ 0x1AU) & 31U));
            }
            a = b;
            b = next;
            remaining -= 1U;
            phase ^= 1U;
        } while (phase != 0U);
}
