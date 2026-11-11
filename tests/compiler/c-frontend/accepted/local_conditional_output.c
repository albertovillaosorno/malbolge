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
//   - C conditional constant-flow source and guest parity regression.
// - Must-Not:
//   - Imply runtime C branching, guest arithmetic or general C storage.
// - Allows:
//   - Inputs: three unsigned locals with one checked source-proven if/else.
//   - Outputs: the branch-selected byte from the normative guest VM.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General symbolic C control-flow lowering supersedes this witness.
// - Merge-When:
//   - Full C program acceptance validates this branch-selection behavior.
// - Summary:
//   - Local condition selects one of two source-backed assignments.
// - Description:
//   - A and B initialize result; condition chooses one XOR assignment.
// - Usage:
//   - Compile with pinned Clang; verify guest output under normative VM.
// - Defaults:
//   - Loops, runtime-dependent conditions and guest branches are unsupported.

#include <stdio.h>

void emit(void) {
    unsigned a = 60U;
    unsigned b = 6U;
    unsigned result = a + b;
    if ((result & 1U) == 0U) {
        result = result ^ 3U;
    } else {
        result = result ^ 2U;
    }
    putchar(result);
}
