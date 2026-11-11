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
//   - Bounded zero-trip while followed by a stateful do-while recurrence.
// - Must-Not:
//   - Treat skipped C effects as emitted guest output or guest runtime control.
// - Allows:
//   - Inputs: proven unsigned local state and guarded source-backed C loops.
//   - Outputs: one final proven byte from the normative Malbolge guest VM.
//   - Side effects: one skipped putchar and one final executed putchar.
// - Split-When:
//   - Dynamic source control flow is lowered to actual guest instructions.
// - Merge-When:
//   - General C control-flow IR replaces bounded compile-time replay.
// - Summary:
//   - Skips a fully checked while body before running a three-step recurrence.

#include <stdio.h>

void emit(void) {
    unsigned a = 3U;
    unsigned b = 5U;
    unsigned i = 3U;
    while (i < 3U) {
        unsigned next = ((a * b) << 2U) & 255U;
        if (next & 8U) {
            a = (next >> 3U) ^ 1U;
        } else {
            a = next - 1U;
        }
        b = next;
        putchar((int)(next ^ 1U));
        i = i + 1U;
    }
    do {
        unsigned next = ((a * b) << 2U) & 255U;
        if (next & 8U) {
            a = (next >> 3U) ^ 1U;
        } else {
            a = next - 1U;
        }
        b = next;
        i = i + 1U;
    } while (i < 6U);
    putchar((int)(a ^ 62U));
}
