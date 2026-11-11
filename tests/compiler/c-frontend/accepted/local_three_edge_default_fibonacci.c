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
//   - Whole-program source-bound C control-flow compiler experiment.
// - Must-Not:
//   - Substitute host stdout for guest semantics or imply general C support.
// - Allows:
//   - Inputs: pinned C23 source with bounded unsigned-local Fibonacci state.
//   - Outputs: twelve source-dependent masked bytes selected by a branch.
//   - Side effects: C putchar effects only.
// - Split-When:
//   - Stateful C lowering is independently admitted into guest IR.
// - Merge-When:
//   - The seeded general C corpus covers this complete program.
// - Summary:
//   - Three nonempty case edges feed default with separately carried local state.
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
        unsigned next = (a + b) & 255U;
        unsigned selected = (next & 31U) ^ (((next & 2U) >> 1U) * 7U) ^ ((next & 1U) * 29U);
        unsigned carry = 7U ^ (((next & 2U) >> 1U) * 7U);
        switch (next & 3U) {
        case 0U:
            selected ^= 7U;
            carry ^= 7U;
        case 2U:
            carry ^= 7U;
        case 1U:
            selected ^= 0U;
        default:
            selected ^= carry;
            selected ^= 0U;
            break;
        }
        putchar((int)selected);
        a = b;
        b = next;
    }
}
