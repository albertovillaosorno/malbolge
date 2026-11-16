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
//   - Nested loop read invalidation for C aliases of an older guest byte.
// - Must-Not:
//   - Recover old accumulator state using source names without guest storage.
// - Allows:
//   - Inputs: an original byte and fresh reads in each inner loop trip.
//   - Outputs: explicit unsupported lowering and no published target.
//   - Side effects: none; unsupported compiler path must fail closed.
// - Split-When:
//   - General guest runtime local storage preserves independent bytes.
// - Merge-When:
//   - Generic guest SSA live ranges enforce local alias invalidation.
// - Summary:
//   - Reject nested guest reads that clobber still-referenced outer aliases.
//
#include <stdio.h>

void emit(void) {
    int first = getchar();
    int alias = first;
    for (unsigned i = 0U; i < 2U; ++i) {
        for (unsigned j = 0U; j < 2U; ++j) {
            int recent = getchar();
            if (i & 1U) {
                putchar(alias);
            } else {
                putchar(first);
            }
        }
    }
}
