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
//   - Full Fibonacci C with selected do-break skipping undefined arithmetic.
// - Must-Not:
//   - Evaluate an unexecuted C predicate or spoof guest VM output.
// - Allows:
//   - Inputs: pinned C23 source with checked branch and do control.
//   - Outputs: twelve Fibonacci bytes on the normative Malbolge VM.
//   - Side effects: selected putchar calls after the bounded do loop.
// - Split-When:
//   - General dynamic C do-while lowering replaces source replay.
// - Merge-When:
//   - A semantic loop-control corpus proves the same skipped predicate.
// - Summary:
//   - Odd terms break before division by zero; even terms test false.
//

#include <stdio.h>

void emit(void) {
    unsigned a = 1U;
    unsigned b = 1U;
    for (unsigned i = 0U; i < 12U; ++i) {
        unsigned next = 0U;
        do {
            next = (a + b) & 255U;
            if (next & 1U) {
                break;
            }
        } while ((next & 1U) ? (1U / 0U) : 0U);
        if ((next & 1U) == 0U) {
            putchar((int)(next & 31U));
        } else {
            putchar((int)((next ^ 0x1AU) & 31U));
        }
        a = b;
        b = next;
    }
}
