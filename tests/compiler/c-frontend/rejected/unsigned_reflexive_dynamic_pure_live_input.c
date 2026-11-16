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
//   - Source-proven dead pure integer expressions in C branches.
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
//   - Prove dead integer arithmetic without executing it in the guest.
// - Description:
//   - Authenticates pure expressions only in a statically dead C output arm.
// - Usage:
//   - Pinned by the source-to-guest byte parity and mutation regressions.
// - Defaults:
//   - Never erase an executable guest C effect.
//

//! Source-bound four-byte C output branch fixture.

#include <stdio.h>

void emit(void) {
    for (unsigned i = 0U; i < 4U; ++i) {
        int current = getchar();
        if (current == current) {
            putchar(current);
            putchar(current);
        } else {
            putchar(0xA5);
        }
        if ((current & 1) != 0) {
            putchar((current + 1) * 2);
        } else {
            putchar(current);
        }
    }
}
