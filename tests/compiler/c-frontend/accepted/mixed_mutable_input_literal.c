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
//   - One source-C unsigned local update after a signed getchar effect.
// - Must-Not:
//   - Substitute guest EOF for C int or silently erase an input read.
// - Allows:
//   - Inputs: finite binary stdin, including EOF before the first read.
//   - Outputs: one source-derived byte after an independent guest read.
//   - Side effects: one getchar, one local update and one putchar.
// - Split-When:
//   - General mutable storage and EOF-controlled guest loops are supported.
// - Merge-When:
//   - Complete mutable EOF checksum supersedes this closed boundary.
// - Summary:
//   - Exercise source-bound constant propagation alongside live guest I/O.
//
#include <stdio.h>

void emit(void) {
    unsigned checksum = 0U;
    int current = getchar();
    checksum += 11U;
    putchar((int)checksum);
}
