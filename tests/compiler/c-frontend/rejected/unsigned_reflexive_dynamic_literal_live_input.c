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
//   - Source-proven unreachable literal effects in two finite C branches.
// - Must-Not:
//   - Predict a runtime byte or erase a reachable side effect.
// - Allows:
//   - Inputs: four successful live guest getchar values.
//   - Outputs: twelve faithful copies in guest-effect order.
//   - Side effects: four reads and twelve writes.
// - Split-When:
//   - General byte-dependent guest branching becomes available.
// - Merge-When:
//   - Total byte predicates share the same source proof lattice.
// - Summary:
//   - Keep dead signed literals out of runtime guest output effects.
//
#include <stdio.h>

void emit(void) {
    for (unsigned i = 0U; i < 4U; ++i) {
        int current = getchar();
        if (current != 0) {
            putchar(current);
            putchar(current);
        } else {
            putchar(0xA5);
        }
        if ((current ^ current) != 0) {
            putchar(0);
        } else {
            putchar(current);
        }
    }
}
