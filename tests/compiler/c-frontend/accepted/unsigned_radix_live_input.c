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
//   - Source-proven C23 unsigned integer radix tokens with guest I/O.
// - Must-Not:
//   - Trust normalized decimal values without the original C tokens.
// - Allows:
//   - Inputs: five successful guest bytes and finite unsigned induction.
//   - Outputs: radix-bounded, source-selected repeated-byte branches.
//   - Side effects: five getchar and seven putchar calls.
// - Split-When:
//   - General guest runtime C arithmetic replaces static induction.
// - Merge-When:
//   - General source-C literal parsing supersedes bounded static proof.
// - Summary:
//   - Binary, octal and hex literals select a five-trip guest trace.
//
#include <stdio.h>
void emit(void) {
    for (unsigned i = 0b1U; i <= 0X5u; i += 01u) {
        int current = getchar();
        if (i % 0x2U == 0u) {
            putchar(current);
            putchar(current);
            continue;
        }
        if (i == 0x5U) {
            putchar(current);
            break;
        }
        putchar(current);
    }
}
