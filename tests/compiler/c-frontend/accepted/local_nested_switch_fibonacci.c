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
//   - Whole-source two-level switch Fibonacci state-flow proof.
// - Must-Not:
//   - Invent nested byte I/O or dynamic C runtime switches.
// - Allows:
//   - Inputs: pinned C23 unsigned-local source and nested switch dispatch.
//   - Outputs: twelve independent masked Fibonacci bytes.
//   - Side effects: bounded C putchar effects, verified in the guest VM.
// - Split-When:
//   - General C runtime lowering subsumes bounded source replay.
// - Merge-When:
//   - An independent seeded C-to-guest control-flow corpus proves this.
// - Summary:
//   - Two nested switches select source-local state in a bounded loop.
//
#include <stdio.h>
void emit(void) {
    unsigned a = 1U;
    unsigned b = 1U;
    unsigned next = 0U;
    unsigned mask = 0U;
    for (unsigned i = 0U; i < 12U; ++i) {
        next = (a + b) & 255U;
        switch (next & 1U) {
        case 0U:
            switch (next & 2U) {
            case 0U:
                mask = 0U;
                break;
            default:
                mask = 32U;
                break;
            }
            break;
        default:
            switch (next & 2U) {
            case 0U:
                mask = 26U;
                break;
            default:
                mask = 58U;
                break;
            }
            break;
        }
        putchar((int)((next ^ mask) & 31U));
        a = b;
        b = next;
    }
}
