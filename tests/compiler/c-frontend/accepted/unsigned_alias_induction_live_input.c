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
//   - Source-checked C identity aliases across a finite unsigned loop.
// - Must-Not:
//   - Read the guest input on the host or synthesize missing C locals.
// - Allows:
//   - Inputs: one live getchar byte with two equivalent C local names.
//   - Outputs: three ordered copies of that same guest byte.
//   - Side effects: one real guest read and three writes.
// - Split-When:
//   - General guest-state support replaces accumulator-local aliases.
// - Merge-When:
//   - A source-to-SSA alias proof supports equivalent bindings generically.
// - Summary:
//   - Prove mixed live byte aliases through source-time induction control.
//
#include <stdio.h>

void emit(void) {
    int first = getchar();
    int alias = first;
    for (unsigned i = 0U; i < 3U; ++i) {
        if (i & 1U) {
            putchar(alias);
        } else {
            putchar(first);
        }
    }
}
