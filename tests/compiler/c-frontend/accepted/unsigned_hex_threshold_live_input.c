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
//   - C23 hexadecimal signed thresholds over successful live input bytes.
// - Must-Not:
//   - Predict guest bytes or erase effects from an unproven condition.
// - Allows:
//   - Inputs: four successful guest getchar bytes and a finite C loop.
//   - Outputs: eight ordered copies of the four live input bytes.
//   - Side effects: four guest reads and eight guest writes.
// - Split-When:
//   - Guest runtime comparisons implement general C value equality.
// - Merge-When:
//   - Total byte guards share one source-proven identity lattice.
// - Summary:
//   - Prove current < 0x100 for every successful real guest byte.
//
#include <stdio.h>

void emit(void) {
    for (unsigned i = 0U; i < 4U; ++i) {
        int current = getchar();
        if (current < 0x100) {
            putchar(current);
            putchar(current);
        } else {
            putchar(current);
        }
    }
}
