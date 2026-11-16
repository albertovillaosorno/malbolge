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
//   - Source-proven unsigned remainder guards on live-byte input loops.
// - Must-Not:
//   - Reinterpret unsigned C operations as signed or fold live input.
// - Allows:
//   - Inputs: five successful guest bytes and finite unsigned induction.
//   - Outputs: two statically selected repeated-byte branches.
//   - Side effects: five getchar and seven putchar calls.
// - Split-When:
//   - General guest runtime C arithmetic replaces static induction.
// - Merge-When:
//   - Checked signed and unsigned induction share typed C proof.
// - Summary:
//   - A remainder guard selects repeats and continue; break exits at five.
//
#include <stdio.h>
void emit(void) {
    for (unsigned i = 1U; i <= 5U; i += 1U) {
        int current = getchar();
        if (i % 2U == 0U) {
            putchar(current);
            putchar(current);
            continue;
        }
        if (i == 5U) {
            putchar(current);
            break;
        }
        putchar(current);
    }
}
