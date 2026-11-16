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
//   - Source-checked C unsigned bitwise induction predicates with live I/O.
// - Must-Not:
//   - Inspect or predict guest input values while choosing C branch effects.
// - Allows:
//   - Inputs: four successful guest getchar effects and finite u32 induction.
//   - Outputs: selected byte repeats from &, ^ and | induction predicates.
//   - Side effects: four actual guest reads and twelve ordered guest writes.
// - Split-When:
//   - General guest runtime C expressions replace static induction proof.
// - Merge-When:
//   - Induction arithmetic and bitwise C semantics share the same projector.
// - Summary:
//   - Real guest input is duplicated according to source-proven bit patterns.
//
#include <stdio.h>

void emit(void) {
    for (unsigned i = 0U; i < 4U; ++i) {
        int current = getchar();
        if (i & 1U) {
            putchar(current);
        }
        if (i ^ 2U) {
            putchar(current);
        }
        if (i | 0U) {
            putchar(current);
        }
        putchar(current);
    }
}
