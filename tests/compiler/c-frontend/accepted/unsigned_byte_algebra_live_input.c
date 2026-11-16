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
//   - Source-bound total byte algebra over four live getchar results.
// - Must-Not:
//   - Predict a runtime byte or erase a read or side effect.
// - Allows:
//   - Inputs: four successful live guest getchar values.
//   - Outputs: twelve faithful copies in guest-effect order.
//   - Side effects: four reads and twelve writes.
// - Split-When:
//   - General byte-dependent guest branching becomes available.
// - Merge-When:
//   - Total byte predicates share the same source proof lattice.
// - Summary:
//   - Check algebraic identities across every successful input byte.
//
#include <stdio.h>

void emit(void) {
    for (unsigned i = 0U; i < 4U; ++i) {
        int current = getchar();
        if ((current ^ current) == 0 && (current + 1 > current)) {
            putchar(current);
            putchar(current);
        } else {
            putchar(current);
        }
        if ((current ^ current) != 0) {
            putchar(current);
        } else {
            putchar(current);
        }
    }
}
