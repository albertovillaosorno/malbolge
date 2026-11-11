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
//   - Five output effects from source-proven stateful unsigned C arithmetic.
// - Must-Not:
//   - Claim host-folded C control flow runs inside the guest Malbolge VM.
// - Allows:
//   - Inputs: five loop iterations, branch, division and multiplication.
//   - Outputs: independently computed byte stream 35 08 dc 08 a3.
//   - Side effects: five ordered putchar effects only.
// - Split-When:
//   - Runtime guest C arithmetic and control flow subsume this projection.
// - Merge-When:
//   - General source-to-guest byte-stream verification covers the case.
// - Summary:
//   - A real C recurrence exercises previously rejected five-effect layout.

#include <stdio.h>

void emit(void) {
    unsigned a = 1U;
    unsigned b = 1U;
    for (unsigned i = 0U; i < 5U; ++i) {
        unsigned next = (a + b) & 255U;
        if ((next & 1U) == 0U) {
            putchar((int)((((next / 2U) * 241U) + 68U) & 255U));
        } else {
            putchar((int)((((next / 2U) * 212U) +
                           ((next / 8U) * 119U) + 52U) & 255U));
        }
        a = b;
        b = next;
    }
}
