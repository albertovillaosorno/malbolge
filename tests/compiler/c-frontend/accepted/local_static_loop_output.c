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
//   - Source-proven, output-free bounded C for-loop constant-flow probe.
// - Must-Not:
//   - Claim guest runtime loops or replace actual VM output with host stdout.
// - Allows:
//   - Inputs: closed unsigned loop counter and Fibonacci-like state updates.
//   - Outputs: one source-derived byte verified by the normative guest VM.
//   - Side effects: guest putchar after the loop only.
// - Split-When:
//   - Runtime loop lowering replaces bounded constant propagation.
// - Merge-When:
//   - The complete Fibonacci C program reaches guest-output parity.
// - Summary:
//   - Loop-local declaration, condition, increment and state transfer proof.
// - Description:
//   - Eight iterations, including source-selected conditional assignments.
// - Usage:
//   - Compare pinned frontend AST and real guest VM against independent C.
// - Defaults:
//   - Loop effects, unbounded iteration and dynamic guest control reject.

#include <stdio.h>

void emit(void) {
    unsigned a = 1U;
    unsigned b = 1U;
    for (unsigned i = 0U; i < 8U; ++i) {
        unsigned next = (a + b) & 255U;
        if ((next & 1U) == 0U) {
            next = next ^ 0U;
        } else {
            next = next ^ 1U;
        }
        a = b;
        b = next;
    }
    putchar((int)(b ^ 107U));
}
