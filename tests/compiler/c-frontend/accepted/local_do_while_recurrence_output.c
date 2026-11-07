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
//   - Source-proven bounded do-while recurrence with mutable loop counter.
// - Must-Not:
//   - Claim guest runtime control flow or host-emulated output.
// - Allows:
//   - Inputs: automatic unsigned local state and checked pure loop condition.
//   - Outputs: one final source-derived byte on the normative guest VM.
//   - Side effects: final putchar only.
// - Split-When:
//   - Dynamic C control flow is lowered into guest instructions.
// - Merge-When:
//   - General typed control-flow IR subsumes bounded constant replay.
// - Summary:
//   - Replays a mandatory first loop body before checked exit.

#include <stdio.h>

void emit(void) {
    unsigned a = 3U;
    unsigned b = 5U;
    unsigned i = 0U;
    do {
        unsigned next = ((a * b) << 2U) & 255U;
        if ((next & 8U)) {
            a = (next >> 3U) ^ 1U;
        } else {
            a = next - 1U;
        }
        b = next;
        i = i + 1U;
    } while (i < 3U);
    putchar((int)(a ^ 62U));
}
