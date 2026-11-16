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
//   - Unsigned induction selecting live guest input replay in a C branch.
// - Must-Not:
//   - Evaluate runtime getchar bytes or assume EOF produces a C byte.
// - Allows:
//   - Inputs: four successful binary getchar results.
//   - Outputs: five ordered guest writes, repeating the third input.
//   - Side effects: four getchar and five putchar calls.
// - Split-When:
//   - General guest-dependent C branches replace static induction.
// - Merge-When:
//   - Seeded runtime byte parity covers unsigned branch conditions.
// - Summary:
//   - Exact source-authenticated unsigned predicates select guest effects.

#include <stdio.h>

void emit(void) {
    for (unsigned i = 0U; i < 4U; ++i) {
        int current = getchar();
        if (i == 2U) {
            putchar(current);
            putchar(current);
        } else {
            putchar(current);
        }
    }
}
