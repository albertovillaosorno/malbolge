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
//   - Ordered source-C unsigned arithmetic after genuine signed getchar.
// - Must-Not:
//   - Erase input effects, commute += and ^=, or fake guest computation.
// - Allows:
//   - Inputs: one C23 signed getchar and finite stdin including EOF.
//   - Outputs: source-computed independent byte after ordered mutations.
//   - Side effects: one getchar, two local updates and one putchar.
// - Split-When:
//   - General mutable source IR subsumes this finite constant-flow witness.
// - Merge-When:
//   - P2 EOF checksum subsumes ordered mutable guest storage.
// - Summary:
//   - Distinguish source-ordered update semantics from literal substitution.
//
#include <stdio.h>

void emit(void) {
    unsigned checksum = 7U;
    int current = getchar();
    checksum += 5U;
    checksum ^= 7U;
    putchar((int)checksum);
}
