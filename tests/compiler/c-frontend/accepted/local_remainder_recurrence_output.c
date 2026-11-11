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
//   - Source-proven unsigned remainder inside a stateful C loop and branch.
// - Must-Not:
//   - Claim guest runtime state, multiplication or remainder evaluation.
// - Allows:
//   - Inputs: bounded unsigned locals, masked products and three iterations.
//   - Outputs: one independently checked guest byte.
//   - Side effects: a final guest putchar after local-state projection.
// - Split-When:
//   - General C arithmetic and runtime branching supersede closed folding.
// - Merge-When:
//   - Complete runtime C input/output programs reach guest parity.
// - Summary:
//   - Prove a nonzero remainder through a conditional state recurrence.
// - Description:
//   - Divisor is a checked nonzero literal; the recurrence carries state.
// - Usage:
//   - Compile with pinned Clang and replay emitted Malbolge under the VM.
// - Defaults:
//   - Unsupported operations and invalid divisors fail closed.
//
#include <stdio.h>

void emit(void) {
    unsigned a = 3U;
    unsigned b = 5U;
    for (unsigned i = 0U; i < 3U; ++i) {
        unsigned next = (a * b) & 255U;
        if ((next & 1U) == 0U) {
            a = (next % 17U) ^ 1U;
        } else {
            a = next - 1U;
        }
        b = next;
    }
    putchar((int)(a ^ 67U));
}
