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
//   - Nested path-sensitive proof of byte-preserving C arithmetic.
// - Must-Not:
//   - Predict the actual guest byte or erase input effects.
// - Allows:
//   - Inputs: four successful getchar values.
//   - Outputs: the original four bytes, including NUL and high-bit bytes.
//   - Side effects: four guest reads and four guest writes.
// - Split-When:
//   - Guest dynamic branches and arithmetic are independently executable.
// - Merge-When:
//   - The verified input-domain engine handles general nested conditions.
// - Summary:
//   - Carry the active C byte predicate through nested source branches.
//
#include <stdio.h>
void emit(void) {
    for (unsigned i = 0U; i < 4U; ++i) {
        int current = getchar();
        if ((current & 1) != 0) {
            if ((current & 2) != 0) {
                putchar(current - (current & 3) + 3);
            } else {
                putchar(current - (current & 3) + 1);
            }
        } else {
            putchar(current + (current & 1));
        }
    }
}
