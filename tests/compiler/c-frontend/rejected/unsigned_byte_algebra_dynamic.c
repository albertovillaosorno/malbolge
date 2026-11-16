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
//   - Input-dependent parity guard requiring guest control.
// - Must-Not:
//   - Predict a runtime byte or erase a read or side effect.
// - Allows:
//   - Inputs: four successful live guest getchar values.
//   - Outputs: eight or twelve copies, depending on successful guest bytes.
//   - Side effects: four reads and eight to twelve conditional writes.
// - Split-When:
//   - General byte-dependent guest branching becomes available.
// - Merge-When:
//   - Total byte predicates share the same source proof lattice.
// - Summary:
//   - Refuse static admission when live parity changes the output trace.
//
#include <stdio.h>

void emit(void) {
    for (unsigned i = 0U; i < 4U; ++i) {
        int current = getchar();
        if ((current & 1) == 0 && (current + 1 > current)) {
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
