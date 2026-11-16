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
//   - Source-authenticated unsigned non-unit induction with live guest I/O.
// - Must-Not:
//   - Evaluate getchar in the compiler or guess unsigned wraparound.
// - Allows:
//   - Inputs: four successful guest bytes.
//   - Outputs: the four reads, repeating the third input once.
//   - Side effects: four getchar and five putchar calls.
// - Split-When:
//   - General runtime unsigned loop control replaces finite projection.
// - Merge-When:
//   - More non-unit induction forms share the same bounded proof.
// - Summary:
//   - Prove an exact unsigned compound stride and selected counter branch.

#include <stdio.h>

void emit(void) {
    for (unsigned i = 0U; i < 8U; i += 2U) {
        int current = getchar();
        if (i == 4U) {
            putchar(current);
            putchar(current);
        } else {
            putchar(current);
        }
    }
}
