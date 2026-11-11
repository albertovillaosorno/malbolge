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
//   - Complete Fibonacci C for loop with nested stateful do-while computation.
// - Must-Not:
//   - Substitute host stdout for guest semantics or imply general C support.
// - Allows:
//   - Inputs: pinned C23 source with bounded unsigned-local Fibonacci state.
//   - Outputs: twelve bytes selected after an inner do-while loop.
//   - Side effects: C putchar effects only.
// - Split-When:
//   - Stateful C lowering is independently admitted into guest IR.
// - Merge-When:
//   - The seeded general C corpus covers this complete program.
// - Summary:
//   - The inner do-while computes and masks each next Fibonacci value.
// - Description:
//   - Normative guest byte parity is required, not a host-computed transcript.
// - Usage:
//   - Run the real C-to-Malbolge compiler against this tracked source.
// - Defaults:
//   - Guest output must match an independent unsigned-C oracle.
//

#include <stdio.h>

void emit(void) {
    unsigned a = 1U;
    unsigned b = 1U;
    for (unsigned i = 0U; i < 12U; ++i) {
        unsigned next = 0U;
        unsigned phase = 0U;
        do {
            if (phase == 0U) {
                next = a + b;
            } else {
                next &= 255U;
            }
            ++phase;
        } while (phase < 2U);
        if ((next & 1U) == 0U) {
            putchar((int)(next & 31U));
        } else {
            putchar((int)((next ^ 0x1AU) & 31U));
        }
        a = b;
        b = next;
    }
}
