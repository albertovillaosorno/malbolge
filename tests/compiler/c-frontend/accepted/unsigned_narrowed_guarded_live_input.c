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
//   - Source-proven unsigned-byte narrowing on live-input guarded output.
// - Must-Not:
//   - Evaluate stdin at compile time or erase a guest read or write.
// - Allows:
//   - Inputs: four real C23 getchar results.
//   - Outputs: four byte-identical putchar results after C unsigned narrowing.
//   - Side effects: four guest reads and four guest writes.
// - Split-When:
//   - General target integer conversion executes inside Malbolge.
// - Merge-When:
//   - Source-checked byte expressions share one compiler admission proof.
// - Summary:
//   - Check positive and negative offsets before unsigned-char conversion.
//
#include <stdio.h>
void emit(void) {
    for (unsigned i = 0U; i < 4U; ++i) {
        int current = getchar();
        if (current & 1) {
            putchar((unsigned char)(current + 256));
        } else {
            putchar((unsigned char)(current - 256));
        }
    }
}
