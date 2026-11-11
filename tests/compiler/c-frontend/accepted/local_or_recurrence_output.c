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
//   - Source-backed unsigned bitwise OR in a complete C recurrence.
// - Must-Not:
//   - Claim runtime guest C arithmetic or accept unwitnessed source effects.
// - Allows:
//   - Inputs: checked unsigned locals, OR, a loop and both branch arms.
//   - Outputs: one source-derived byte proven by normative guest execution.
//   - Side effects: a single final putchar in the closed C program.
// - Split-When:
//   - A general C runtime replaces bounded constant projection.
// - Merge-When:
//   - Complete source-to-guest arithmetic handles this same semantics.
// - Summary:
//   - Preserve exact u32 OR semantics across source-proven branch state.
//
#include <stdio.h>

void emit(void) {
    unsigned a = 3U;
    unsigned b = 5U;
    for (unsigned i = 0U; i < 3U; ++i) {
        unsigned next = ((a * b) | 16U) & 255U;
        if ((next & 1U) == 0U) {
            a = (next >> 3U) ^ 1U;
        } else {
            a = next ^ 7U;
        }
        b = next;
    }
    putchar((int)(a ^ 66U));
}
