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
//   - Verify defined C unsigned wraparound in complete guest output streams.
// - Must-Not:
//   - Substitute host output for Malbolge VM execution.
// - Allows:
//   - Inputs: byte-bounded local state and intermediate wrapping u32 values.
//   - Outputs: four real guest bytes through source-backed putchar calls.
//   - Side effects: only those four calls.
// - Split-When:
//   - Dynamic C arithmetic replaces static constant-state projection.
// - Merge-When:
//   - A general C semantics oracle subsumes this finite source program.
// - Summary:
//   - Reconstruct Fibonacci state using modular subtraction, product and sum.

#include <stdio.h>

void emit(void) {
    unsigned a = 1U;
    unsigned b = 1U;
    for (unsigned i = 0U; i < 4U; ++i) {
        unsigned next = ((0U - (a + b)) * 255U) & 255U;
        unsigned restored = ((~next + 1U) + (next * 2U)) & 255U;
        if ((restored & 1U) == 0U) {
            putchar((int)(((restored * 29U) + 251U) & 255U));
        } else {
            putchar((int)((((restored / 2U) * 73U) + 119U) & 255U));
        }
        a = b;
        b = restored;
    }
}
