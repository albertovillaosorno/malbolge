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
//   - Two ordered output effects per nested C switch-selected arm.
// - Must-Not:
//   - Publish speculative outputs from unselected source switch cases.
// - Allows:
//   - Inputs: source-proven six-trip unsigned Fibonacci recurrence.
//   - Outputs: twelve independently calculated masked Fibonacci bytes.
//   - Side effects: real guest putchar effects under bounded selection.
// - Split-When:
//   - General dynamic guest C switching proves the same behavior.
// - Merge-When:
//   - A general verified C-to-Malbolge compiler subsumes source replay.
// - Summary:
//   - Each nested switch arm emits two source-ordered guest bytes.
//
#include <stdio.h>
void emit(void) {
    unsigned a = 1U;
    unsigned b = 1U;
    unsigned first = 0U;
    unsigned second = 0U;
    unsigned x = 0U;
    unsigned y = 0U;
    for (unsigned i = 0U; i < 6U; ++i) {
        first = (a + b) & 255U;
        x = (first & 1U) != 0U ? (first ^ 26U) & 31U : first & 31U;
        a = b;
        b = first;
        second = (a + b) & 255U;
        y = (second & 1U) != 0U ? (second ^ 26U) & 31U : second & 31U;
        a = b;
        b = second;
        switch (i & 1U) {
        case 0U:
            switch (second & 1U) {
            case 0U:
                putchar((int)(x ^ (i & 1U)));
                putchar((int)(y ^ (second & 1U)));
                break;
            default:
                putchar((int)(x ^ (i & 1U)));
                putchar((int)(y ^ ((second & 1U) ^ 1U)));
                break;
            }
            break;
        default:
            switch (second & 1U) {
            case 0U:
                putchar((int)(x ^ ((i & 1U) ^ 1U)));
                putchar((int)(y ^ (second & 1U)));
                break;
            default:
                putchar((int)(x ^ ((i & 1U) ^ 1U)));
                putchar((int)(y ^ ((second & 1U) ^ 1U)));
                break;
            }
            break;
        }
    }
}
