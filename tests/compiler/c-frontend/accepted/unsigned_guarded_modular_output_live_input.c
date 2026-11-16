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
//   - Branch-scoped byte-preserving C23 arithmetic on real guest input.
// - Must-Not:
//   - Predict input, erase a live effect, or treat both arms as unconditional.
// - Allows:
//   - Inputs: four successful signed getchar results.
//   - Outputs: four original bytes from individually guarded expressions.
//   - Side effects: four reads, four writes.
// - Split-When:
//   - General guest C arithmetic and control realize dynamic branches.
// - Merge-When:
//   - Path-sensitive source/Clang proof subsumes finite byte domains.
// - Summary:
//   - Authenticate output identities only over their active branch domains.
//
#include <stdio.h>

void emit(void) {
    for (unsigned i = 0U; i < 4U; ++i) {
        int current = getchar();
        if (current & 1) {
            putchar(current - (current & 1) + 1);
        } else {
            putchar(current + (current & 1));
        }
    }
}
