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
//   - Source-proven unsigned scalar induction truth controlling live bytes.
// - Must-Not:
//   - Predict a guest input byte or erase selected C output effects.
// - Allows:
//   - Inputs: four successful guest getchar bytes.
//   - Outputs: seven ordered guest writes, duplicating nonzero counter trips.
//   - Side effects: four getchar and seven putchar calls.
// - Split-When:
//   - General guest runtime C control replaces bounded source induction.
// - Merge-When:
//   - Source-checked integer truth guards share one induction grammar.
// - Summary:
//   - The unsigned counter, not the guest byte, chooses source branches.
//
#include <stdio.h>

void emit(void) {
    for (unsigned i = 0U; i < 4U; ++i) {
        int current = getchar();
        if (i) {
            putchar(current);
            putchar(current);
        } else {
            putchar(current);
        }
    }
}
