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
//   - Complete Fibonacci C with three nested while/do bodies.
// - Must-Not:
//   - Substitute host stdout for guest semantics or imply general C support.
// - Allows:
//   - Inputs: pinned C23 source with bounded unsigned-local Fibonacci state.
//   - Outputs: twelve bytes selected after bounded nested while loops.
//   - Side effects: C putchar effects only.
// - Split-When:
//   - Stateful C lowering is independently admitted into guest IR.
// - Merge-When:
//   - The seeded general C corpus covers this complete program.
// - Summary:
//   - A stateful while/while/do computes and masks the next value.
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
        while (phase < 2U) {
            unsigned stage = 0U;
            while (stage < 2U) {
                unsigned pass = 0U;
                do {
                    if (phase == 0U) {
                        next = a + b;
                    } else {
                        next &= 255U;
                    }
                    ++pass;
                } while (pass < 2U);
                ++stage;
            }
            ++phase;
        }
        if ((next & 1U) == 0U) {
            putchar((int)(next & 31U));
        } else {
            putchar((int)((next ^ 0x1AU) & 31U));
        }
        a = b;
        b = next;
    }
}
