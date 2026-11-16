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
//   - Lexical identity across nested finite unsigned guest-byte loops.
// - Must-Not:
//   - Re-evaluate the original getchar or invent runtime C local storage.
// - Allows:
//   - Inputs: one successful getchar byte and loop-local identity copies.
//   - Outputs: four ordered writes of the one resident guest byte.
//   - Side effects: one real guest read and four writes.
// - Split-When:
//   - Executable guest locals support independent source value lifetimes.
// - Merge-When:
//   - Generic SSA alias propagation proves arbitrary nested lexical scopes.
// - Summary:
//   - Preserve source-checked aliases through two nested induction loops.
//
#include <stdio.h>

void emit(void) {
    int first = getchar();
    int alias = first;
    for (unsigned i = 0U; i < 2U; ++i) {
        int localcopy = alias;
        for (unsigned j = 0U; j < 2U; ++j) {
            if (i & 1U) {
                putchar(localcopy);
            } else {
                putchar(first);
            }
        }
    }
}
