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
//   - Unbraced C if/else comma writes in the twelve-step recurrence.
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
        unsigned selected = next & 31U;
        if ((next & 1U) == 0U)
            selected ^= 0U, a = b;
        else
            selected ^= 26U, a = b;
        putchar((int)selected);
        b = next;
    }
}
