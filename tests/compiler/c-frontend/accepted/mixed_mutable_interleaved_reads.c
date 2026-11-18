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
//   - Source-ordered unsigned state updates around two signed input effects.
// - Must-Not:
//   - Drop an input read or interpret signed EOF as a successful byte.
// - Allows:
//   - Inputs: any finite binary stream, including empty and high-byte input.
//   - Outputs: source-proved constant checksum after both signed reads.
//   - Side effects: two getchar calls and one putchar.
// - Split-When:
//   - General input-dependent guest storage subsumes constant propagation.
// - Merge-When:
//   - Whole mutable EOF checksum guest execution replaces this witness.
// - Summary:
//   - Distinguish ordered source effects from a single adjacent-read prefix.
//
#include <stdio.h>

void emit(void) {
    unsigned checksum = 7U;
    int first = getchar();
    checksum += 5U;
    int second = getchar();
    checksum ^= 7U;
    putchar((int)checksum);
}
