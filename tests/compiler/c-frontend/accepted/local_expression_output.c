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
//   - C branch-selected expression-output guest parity regression.
// - Must-Not:
//   - Imply runtime C branching, guest arithmetic or general C storage.
// - Allows:
//   - Inputs: three locals, a checked if/else, and expression-based output.
//   - Outputs: the expression-derived byte from the normative guest VM.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General symbolic C control-flow lowering supersedes this witness.
// - Merge-When:
//   - Full C program acceptance validates this branch-selection behavior.
// - Summary:
//   - Local branch and putchar argument determine the output byte.
// - Description:
//   - Branch selects an update, then the call XORs the selected byte.
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
        result = result ^ 0U;
    } else {
        result = result ^ 1U;
    }
    putchar((int)(result ^ 3U));
}
