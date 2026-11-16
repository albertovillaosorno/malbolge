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
//   - Guarded C23 output changing even successful guest input bytes.
// - Must-Not:
//   - Predict input, erase a live effect, or treat both arms as unconditional.
// - Allows:
//   - Inputs: four successful signed getchar results.
//   - Outputs: a changed even-byte output requiring unavailable guest arithmetic.
//   - Side effects: explicit refusal before any guest artifact.
// - Split-When:
//   - General guest C arithmetic and control realize dynamic branches.
// - Merge-When:
//   - Path-sensitive source/Clang proof subsumes finite byte domains.
// - Summary:
//   - Reject an output expression that changes its active branch byte.
//
#include <stdio.h>

void emit(void) {
    for (unsigned i = 0U; i < 4U; ++i) {
        int current = getchar();
        if (current & 1) {
            putchar(current - (current & 1) + 1);
        } else {
            putchar(current + (current & 1) + 1);
        }
    }
}
