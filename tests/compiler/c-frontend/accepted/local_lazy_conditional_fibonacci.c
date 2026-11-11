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
//   - Skipped C ternary division in a full source-proven recurrence.
// - Must-Not:
//   - Evaluate an unselected C operand or fake guest byte output.
// - Allows:
//   - Inputs: pinned C23 source with guarded unsigned division.
//   - Outputs: twelve masked Fibonacci bytes emitted by the normative guest VM.
//   - Side effects: C putchar effects only.
// - Split-When:
//   - General C expression lowering replaces bounded source replay.
// - Merge-When:
//   - The general C control-flow suite covers guarded ternaries.
// - Summary:
//   - A zero divisor occurs only in the skipped ternary arm.
// - Description:
//   - Skipped division must not cause a C evaluation failure.
// - Usage:
//   - Compile through pinned Clang and replay the actual Malbolge guest.
// - Defaults:
//   - Selected division by zero must still refuse publication.
//

#include <stdio.h>

void emit(void) {
    unsigned a = 1U;
    unsigned b = 1U;
    for (unsigned i = 0U; i < 12U; ++i) {
        unsigned next = (a + b) & 255U;
        unsigned selected = ((next & 1U) != 0U)
            ? (((next ^ 26U) & 31U) / (next & 1U))
            : (next & 31U);
        putchar((int)selected);
        a = b;
        b = next;
    }
}
