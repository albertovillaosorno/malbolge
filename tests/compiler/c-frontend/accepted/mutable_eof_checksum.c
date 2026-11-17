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
//   - One complete P2 mutable EOF checksum and binary stdin acceptance source.
// - Must-Not:
//   - Assume four successful reads, compile-time input, or host output.
// - Allows:
//   - Inputs: any finite stdin byte stream, including empty and NUL.
//   - Outputs: one checksum byte after EOF.
//   - Side effects: getchar/putchar and local C state.
// - Split-When:
//   - A distinct C language construct needs an independent acceptance source.
// - Merge-When:
//   - The P3 supported-C corpus covers arbitrary runtime streams.
// - Summary:
//   - Runtime state, data-dependent arithmetic, branching and EOF termination.
//
#include <stdio.h>

void emit(void) {
    unsigned checksum = 0U;
    int current = getchar();
    while (current != EOF) {
        if ((current & 1) != 0) {
            checksum ^= (unsigned)current;
        } else {
            checksum += (unsigned)current;
        }
        checksum = (checksum + 3U) & 255U;
        current = getchar();
    }
    putchar((int)checksum);
}
