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
//   - Source-bound conditional effects inside nested Fibonacci switches.
// - Must-Not:
//   - Invent dynamic C runtime switches or host-side byte output.
// - Allows:
//   - Inputs: pinned C23 unsigned locals, switches and branch conditions.
//   - Outputs: twelve branch-selected masked Fibonacci bytes.
//   - Side effects: bounded C putchar effects, verified in the guest VM.
// - Split-When:
//   - General C runtime lowering subsumes bounded source replay.
// - Merge-When:
//   - An independent seeded C-to-guest control-flow corpus proves this.
// - Summary:
//   - Nested cases select state via inner conditionals before guest I/O.
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
                if ((next & 4U) != 0U) {
                    mask = 4U;
                } else {
                    mask = 0U;
                }
                mask ^= next & 4U;
                putchar((int)((next ^ mask) & 31U));
                break;
            default:
                if ((next & 4U) != 0U) {
                    mask = 36U;
                } else {
                    mask = 32U;
                }
                mask ^= next & 4U;
                putchar((int)((next ^ mask) & 31U));
                break;
            }
            break;
        default:
            switch (next & 2U) {
            case 0U:
                if ((next & 4U) != 0U) {
                    mask = 30U;
                } else {
                    mask = 26U;
                }
                mask ^= next & 4U;
                putchar((int)((next ^ mask) & 31U));
                break;
            default:
                if ((next & 4U) != 0U) {
                    mask = 62U;
                } else {
                    mask = 58U;
                }
                mask ^= next & 4U;
                putchar((int)((next ^ mask) & 31U));
                break;
            }
            break;
        }
        a = b;
        b = next;
    }
}
