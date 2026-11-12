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
//   - Complete C Fibonacci with a selected do break and unreachable output.
// - Must-Not:
//   - Publish unexecuted output or evaluate a skipped do predicate.
// - Allows:
//   - Inputs: pinned C23 source and checked branch/loop state.
//   - Outputs: twelve masked Fibonacci bytes on the normative guest VM.
//   - Side effects: selected putchar only.
// - Split-When:
//   - General guest runtime C control flow replaces bounded replay.
// - Merge-When:
//   - General loop exits cover lexical dead-source authentication.
// - Summary:
//   - A break skips the next putchar and the post-test predicate.

#include <stdio.h>

void emit(void) {
    unsigned a = 1U;
    unsigned b = 1U;
    for (unsigned i = 0U; i < 12U; ++i) {
        unsigned next = (a + b) & 255U;
        a = b;
        b = next;
        do {
            if ((next & 1U) != 0U) {
                putchar((int)((next ^ 0x1AU) & 31U));
                break;
            }
            putchar((int)(next & 31U));
        } while ((next & 1U) ? (1U / 0U) : 0U);
    }
}
