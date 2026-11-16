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
//   - Source-proven enclosing induction in nested dual-counter guest I/O loops.
// - Must-Not:
//   - Replace guest input with host data or confuse scoped loop counters.
// - Allows:
//   - Inputs: six successful byte reads across three outer, two inner trips.
//   - Outputs: seven writes, duplicating the third byte only.
//   - Side effects: six getchar and seven putchar calls.
// - Split-When:
//   - General runtime C loops own nested induction and byte storage.
// - Merge-When:
//   - Full multi-counter expression evaluation subsumes this bounded proof.
// - Summary:
//   - An inner branch combines both authenticated induction counters.

#include <stdio.h>
void emit(void) {
    for (unsigned row = 1U; row <= 3U; row += 1U) {
        for (unsigned col = 1U; col <= 2U; col += 1U) {
            int current = getchar();
            if (row == 2U && col == 1U) {
                putchar(current);
                putchar(current);
            } else {
                putchar(current);
            }
        }
    }
}
