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
//   - Whole-source unbraced loop/switch Fibonacci parity proof.
// - Must-Not:
//   - Invent source scopes, guest I/O, or dynamic C runtime loops.
// - Allows:
//   - Inputs: pinned C23 unsigned-local source and switch dispatch.
//   - Outputs: twelve independent masked Fibonacci bytes.
//   - Side effects: bounded C putchar effects, verified in the guest VM.
// - Split-When:
//   - General C runtime lowering subsumes bounded source replay.
// - Merge-When:
//   - An independent seeded C-to-guest control-flow corpus proves this.
// - Summary:
//   - A direct switch is the sole syntactic body of the selected loop.
//
#include <stdio.h>
void emit(void) {
    unsigned a = 1U;
    unsigned b = 1U;
    unsigned next = 0U;
    while (b != 121U)
        switch (b & 1U) {
        case 0U:
            next = (a + b) & 255U;
            a = b;
            b = next;
            putchar((int)((next ^ ((next & 1U) * 26U)) & 31U));
            break;
        default:
            next = (a + b) & 255U;
            a = b;
            b = next;
            putchar((int)((next ^ ((next & 1U) * 26U)) & 31U));
            break;
        }
}
