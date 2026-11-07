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
//   - Source-proven bounded recurrence with conditional assignment and no else.
// - Must-Not:
//   - Claim guest runtime conditionals or use host-emulated output.
// - Allows:
//   - Inputs: unsigned local state and source-backed conditional update.
//   - Outputs: one final proven byte on the normative guest VM.
//   - Side effects: one final putchar call.
// - Split-When:
//   - General guest runtime branching replaces compile-time replay.
// - Merge-When:
//   - Typed C control-flow lowering subsumes this bounded proof.
// - Summary:
//   - Exercises taken and skipped no-else branches across loop iterations.

#include <stdio.h>

void emit(void) {
    unsigned a = 3U;
    unsigned b = 5U;
    unsigned i = 0U;
    do {
        unsigned next = ((a * b) << 2U) & 255U;
        if (next & 8U) {
            a = (next >> 3U) ^ 1U;
        }
        b = next;
        i = i + 1U;
    } while (i < 3U);
    putchar((int)(a ^ 71U));
}
