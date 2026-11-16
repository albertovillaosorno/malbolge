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
//   - Source-proven byte-domain switch with a terminating break per arm.
// - Must-Not:
//   - Predict stdin or erase a guest input or output.
// - Allows:
//   - Inputs: four real C23 getchar results.
//   - Outputs: four equivalent putchar results selected by low-bit cases.
//   - Side effects: four reads and four writes.
// - Split-When:
//   - General runtime C switch control flow is available.
// - Merge-When:
//   - Byte-domain conditional proofs share source authentication.
// - Summary:
//   - Preserve live input across a switch with one case and default.
//
#include <stdio.h>
void emit(void) {
    for (unsigned i = 0U; i < 4U; ++i) {
        int current = getchar();
        switch (current & 1) {
        case 0:
            putchar(current & -2);
            break;
        default:
            putchar(current | 1);
            break;
        }
    }
}
