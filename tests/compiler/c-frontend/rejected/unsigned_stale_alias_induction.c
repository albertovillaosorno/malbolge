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
//   - Reject C aliases after a new guest input clobbers resident state.
// - Must-Not:
//   - Reconstruct a stale C byte from the newest guest accumulator value.
// - Allows:
//   - Inputs: an old alias, then a different guest byte on each loop trip.
//   - Outputs: an explicit unsupported-lowering verdict.
//   - Side effects: none; compilation must not publish guest output.
// - Split-When:
//   - General guest runtime locals can store independent C byte values.
// - Merge-When:
//   - Executable guest-local SSA stores preserve original identity.
// - Summary:
//   - An old input cannot be recalled after repeated new guest reads.
//
#include <stdio.h>

void emit(void) {
    int first = getchar();
    int alias = first;
    for (unsigned i = 0U; i < 3U; ++i) {
        int recent = getchar();
        if (i & 1U) {
            putchar(first);
        } else {
            putchar(alias);
        }
    }
}
