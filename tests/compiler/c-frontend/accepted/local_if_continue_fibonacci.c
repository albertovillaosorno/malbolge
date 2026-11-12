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
//   - Complete Fibonacci C with a conditional continue and lexical suffix.
// - Must-Not:
//   - Publish dead output effects or claim dynamic guest C loop lowering.
// - Allows:
//   - Inputs: source-proven unsigned state and one skipped output sibling.
//   - Outputs: twelve selected masked bytes in the normative guest VM.
//   - Side effects: bounded putchar only.
// - Split-When:
//   - A general control-flow IR supersedes compile-time source replay.
// - Merge-When:
//   - General C loop exits cover unreachable sibling source proof.
// - Summary:
//   - An if-selected continue skips the following lexical output.

#include <stdio.h>

void emit(void) {
    unsigned a = 1U;
    unsigned b = 1U;
    for (unsigned i = 0U; i < 12U; ++i) {
        unsigned next = (a + b) & 255U;
        a = b;
        b = next;
        if ((next & 1U) != 0U) {
            putchar((int)((next ^ 0x1AU) & 31U));
            continue;
        }
        putchar((int)(next & 31U));
    }
}
