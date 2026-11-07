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
//   - Complete source-C recurrence with two branch-selected output triples.
// - Must-Not:
//   - Claim that host constant flow is guest runtime control flow.
// - Allows:
//   - Inputs: pinned C frontend, exact local writes and selected output calls.
//   - Outputs: six binary guest bytes including a leading zero.
//   - Side effects: source-proven putchar calls only.
// - Split-When:
//   - General source C state executes in the guest runtime.
// - Merge-When:
//   - General guest byte-stream lowering subsumes this bounded proof.
// - Summary:
//   - Two conditional iterations update three locals between output triples.

#include <stdio.h>
void emit(void) {
    unsigned a = 0U;
    unsigned b = 81U;
    unsigned c = 34U;
    unsigned i = 0U;
    while (i < 2U) {
        if ((i & 1U) == 0U) {
            putchar((int)a);
            putchar((int)b);
            putchar((int)c);
            a = 27U;
            b = 55U;
            c = 57U;
        } else {
            putchar((int)a);
            putchar((int)b);
            putchar((int)c);
        }
        i = i + 1U;
    }
}
