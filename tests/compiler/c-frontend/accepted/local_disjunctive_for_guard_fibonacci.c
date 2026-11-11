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
//   - Complete C loop with disjunctive guard after its induction bound.
// - Must-Not:
//   - Substitute host stdout for guest semantics or imply general C support.
// - Allows:
//   - Inputs: pinned C23 source with bounded unsigned-local Fibonacci state.
//   - Outputs: six source-dependent masked bytes selected by a branch.
//   - Side effects: C putchar effects only.
// - Split-When:
//   - Stateful C lowering is independently admitted into guest IR.
// - Merge-When:
//   - The seeded general C corpus covers this complete program.
// - Summary:
//   - Fibonacci continues past the first bound until the live OR guard ends.
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
    unsigned limit = 2U;
    unsigned stride = 1U;
    for (unsigned i = 0U; limit > i || b < 20U; i += stride) {
        unsigned next = (a + b) & 255U;
        if ((next & 1U) == 0U) {
            putchar((int)(next & 31U));
        } else {
            putchar((int)((next ^ 0x1AU) & 31U));
        }
        if (i == 2U) {
            stride = 2U;
        }
        a = b;
        b = next;
    }
}
