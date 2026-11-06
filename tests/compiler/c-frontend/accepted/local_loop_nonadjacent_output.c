// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - LicenseRef-Proprietary
// Confidential:
//   - true
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Source-proven nonadjacent equal byte effects inside a real C loop.
// - Must-Not:
//   - Coalesce separate C call effects or substitute host stdout for guest I/O.
// - Allows:
//   - Inputs: three bounded Fibonacci state updates and index-based branches.
//   - Outputs: three guest bytes `Z%Z` from three proven call evaluations.
//   - Side effects: successful putchar calls only.
// - Split-When:
//   - General guest byte-stream lowering subsumes this pattern.
// - Merge-When:
//   - Seeded byte-stream tests cover independent repeated output identities.
// - Summary:
//   - First and third output bytes agree despite an intervening change.
// - Description:
//   - The guest must actually compute and emit all three output bytes.
// - Usage:
//   - Compile through pinned frontend and replay in the normative guest VM.
// - Defaults:
//   - Any unwitnessed or altered source effect refuses artifact publication.
//
#include <stdio.h>

void emit(void) {
    unsigned a = 1U;
    unsigned b = 1U;
    for (unsigned i = 0U; i < 3U; ++i) {
        unsigned next = (a + b) & 255U;
        if ((i & 1U) == 0U) {
            putchar((int)(((next - next) + 90U)));
        } else {
            putchar((int)(((next - next) + 37U)));
        }
        a = b;
        b = next;
    }
}
