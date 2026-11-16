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
//   - Multiple ordered byte-preserving effects per dynamic C branch.
// - Must-Not:
//   - Predict stdin, erase fresh guest I/O, or assume all-domain identity.
// - Allows:
//   - Inputs: four successful C23 getchar values.
//   - Outputs: two copies of each live input byte in source order.
//   - Side effects: four guest reads and eight guest writes.
// - Split-When:
//   - Runtime guest conditional execution replaces static source proof.
// - Merge-When:
//   - All ordered guest byte effects share one control-flow proof.
// - Summary:
//   - Keep both writes in each source-proven C guard arm.
//
#include <stdio.h>
void emit(void) {
    for (unsigned i = 0U; i < 4U; ++i) {
        int current = getchar();
        if (current & 1) {
            putchar(current | 1);
            putchar(current | 1);
        } else {
            putchar(current & -2);
            putchar(current & -2);
        }
    }
}
