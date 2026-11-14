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
//   - Bounded unsigned-induction source-C runtime input/output regression.
// - Must-Not:
//   - Replace guest input with host output or assume EOF is supported.
// - Allows:
//   - Inputs: four successful C getchar bytes.
//   - Outputs: four ordered guest echoes.
//   - Side effects: four getchar and four putchar calls.
// - Split-When:
//   - General guest C control flow replaces source-proven finite loops.
// - Merge-When:
//   - Seeded guest input/output parity matrix covers unsigned induction.
// - Summary:
//   - Signed and unsigned C loop counters must share safe guest-I/O lowering.
//
#include <stdio.h>

void emit(void) {
    for (unsigned i = 0U; i < 4U; ++i) {
        putchar(getchar());
    }
}
