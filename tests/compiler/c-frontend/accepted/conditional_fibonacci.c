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
//   - Whole-program source-bound C control-flow compiler experiment.
// - Must-Not:
//   - Substitute host stdout for guest semantics or imply general C support.
// - Allows:
//   - Inputs: pinned C23 source with bounded unsigned-local Fibonacci state.
//   - Outputs: twelve bytes selected by actual conditional arithmetic.
//   - Side effects: C putchar effects only.
// - Split-When:
//   - Stateful C lowering is independently admitted into guest IR.
// - Merge-When:
//   - The seeded general C corpus covers this complete program.
// - Summary:
//   - Complete 12-step Fibonacci, branch, and byte-output compiler target.
// - Description:
//   - Normative guest parity is the acceptance goal, not yet implemented.
// - Usage:
//   - Run the real C-to-Malbolge compiler against this tracked source.
// - Defaults:
//   - Unsupported local state must fail without a guest artifact.
//

#include <stdio.h>

void emit(void) {
    unsigned a = 1U;
    unsigned b = 1U;
    for (unsigned i = 0U; i < 12U; ++i) {
        unsigned next = (a + b) & 255U;
        if ((next & 1U) == 0U) {
            putchar((int)next);
        } else {
            putchar((int)(next ^ 0x5AU));
        }
        a = b;
        b = next;
    }
}
