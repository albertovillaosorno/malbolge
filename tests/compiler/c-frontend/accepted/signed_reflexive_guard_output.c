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
//   - Complete signed-EOF-safe reflexive C branch and live guest input.
// - Must-Not:
//   - Predict stdin, discard getchar, or execute unproven control on the host.
// - Allows:
//   - Inputs: finite binary stdin including EOF on the first read.
//   - Outputs: one source-proven selected byte from a real guest execution.
//   - Side effects: one signed getchar and one putchar.
// - Split-When:
//   - General guest data-dependent branch execution replaces this proof.
// - Merge-When:
//   - Full mutable EOF checksum covers the same signed input boundary.
// - Summary:
//   - A self-subtraction Boolean guard is always true even for C EOF -1.
//
#include <stdio.h>

void emit(void) {
    int current = getchar();
    if ((current - current) == 0) {
        putchar(11);
    } else {
        putchar(5);
    }
}
