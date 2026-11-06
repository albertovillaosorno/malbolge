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
//   - Multi-local source-dependent C constant propagation regression.
// - Must-Not:
//   - Imply general C storage, runtime arithmetic or control-flow lowering.
// - Allows:
//   - Inputs: three automatic unsigned locals with checked ordered writes.
//   - Outputs: a computed byte from normative Malbolge guest execution.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General symbolic C state lowering subsumes this semantic witness.
// - Merge-When:
//   - Full bounded C program acceptance validates the same source behavior.
// - Summary:
//   - Cross-local reads and arithmetic determine a guest-visible byte.
// - Description:
//   - A and B initialize result before subsequent writes and output.
// - Usage:
//   - Compiled with pinned Clang and run in the normative VM.
// - Defaults:
//   - Branches, loops and nonconstant reads remain unsupported.

#include <stdio.h>

void emit(void) {
    unsigned a = 60U;
    unsigned b = 8U;
    unsigned result = a + b;
    result = result ^ 3U;
    result = result - 6U;
    putchar(result);
}
