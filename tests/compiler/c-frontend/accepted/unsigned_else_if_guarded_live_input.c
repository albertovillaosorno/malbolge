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
//   - Path-sensitive identity across multiline unbraced else-if chains.
// - Must-Not:
//   - Guess an input byte or execute a host-side dynamic branch.
// - Allows:
//   - Inputs: four successful C23 getchar values.
//   - Outputs: the unchanged four input bytes on disjoint low-bit paths.
//   - Side effects: four real guest reads and four guest writes.
// - Split-When:
//   - Guest execution of general runtime C branches is supported.
// - Merge-When:
//   - All source statement forms share an authenticated C control flow.
// - Summary:
//   - Preserve each live byte through an indented else-if ladder.
//
#include <stdio.h>
void emit(void) {
    for (unsigned i = 0U; i < 4U; ++i) {
        int current = getchar();
        if (current & 1)
            putchar(current | 1);
        else if (current & 2)
            putchar(current | 2);
        else
            putchar(current & -4);
    }
}
