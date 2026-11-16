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
//   - Source-proven u32 subtraction wrapped before a guarded live output.
// - Must-Not:
//   - Apply signed comparisons to unsigned wrapped intermediate values.
// - Allows:
//   - Inputs: four successful guest bytes and a bounded unsigned counter.
//   - Outputs: a duplicated first byte selected by unsigned wrapping.
//   - Side effects: four getchar and five putchar calls.
// - Split-When:
//   - General guest runtime arithmetic replaces source-time predicates.
// - Merge-When:
//   - Source-checked unsigned induction handles wrapped arithmetic.
// - Summary:
//   - One minus two wraps to UINT_MAX and selects the extra first output.
//
#include <stdio.h>
void emit(void) {
    for (unsigned i = 1U; i <= 4U; ++i) {
        int current = getchar();
        if (i - 2U > 99U) {
            putchar(current);
            putchar(current);
        } else {
            putchar(current);
        }
    }
}
