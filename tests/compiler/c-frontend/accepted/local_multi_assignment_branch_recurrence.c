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
//   - Complete C recurrence with two ordered writes per conditional arm.
// - Must-Not:
//   - Claim dynamic guest branches or ignore effects in an unselected arm.
// - Allows:
//   - Inputs: source-proven unsigned local state and bounded loop replay.
//   - Outputs: one source-derived byte on the normative guest VM.
//   - Side effects: one final putchar.
// - Split-When:
//   - General typed C control-flow lowering subsumes compile-time replay.
// - Merge-When:
//   - Full source-to-guest branching replaces bounded constant flow.
// - Summary:
//   - Both arms update multiple locals across three loop iterations.

#include <stdio.h>

void emit(void) {
    unsigned a = 3U;
    unsigned b = 5U;
    unsigned i = 0U;
    do {
        unsigned next = ((a * b) << 2U) & 255U;
        if (next & 8U) {
            a = (next >> 3U) ^ 1U;
            b = next ^ 2U;
        } else {
            a = next - 1U;
            b = next;
        }
        i = i + 1U;
    } while (i < 3U);
    putchar((int)(a ^ 254U));
}
