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
//   - Source-proven unsigned sum, byte masking, branch and guest-output probe.
// - Must-Not:
//   - Claim guest runtime arithmetic or loop execution from constant folding.
// - Allows:
//   - Inputs: bounded unsigned locals with an intermediate wider than a byte.
//   - Outputs: one source-derived byte in the normative guest VM.
//   - Side effects: guest putchar only.
// - Split-When:
//   - Dynamic C integer and control flow lowering replaces constant folding.
// - Merge-When:
//   - Complete Fibonacci guest parity exercises this precise source pattern.
// - Summary:
//   - Prove the masked sum that appears inside the full Fibonacci loop.
// - Description:
//   - Preserve C unsigned intermediate semantics through parentheses and mask.
// - Usage:
//   - Compile with pinned Clang and compare the normative VM to C arithmetic.
// - Defaults:
//   - Loop and nonconstant guest state remain unsupported.

#include <stdio.h>

void emit(void) {
    unsigned a = 233U;
    unsigned b = 144U;
    unsigned next = (a + b) & 255U;
    if ((next & 1U) == 0U) {
        next = next ^ 3U;
    } else {
        next = next ^ 56U;
    }
    putchar((int)next);
}
