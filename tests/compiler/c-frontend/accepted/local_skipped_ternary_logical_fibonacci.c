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
//   - Short-circuit C logical division in a full recurrence.
// - Must-Not:
//   - Evaluate a skipped logical operand or fake guest byte output.
// - Allows:
//   - Inputs: pinned C23 source with a short-circuited division.
//   - Outputs: twelve masked Fibonacci bytes emitted by the normative guest VM.
//   - Side effects: C putchar effects only.
// - Split-When:
//   - General C expression lowering replaces bounded source replay.
// - Merge-When:
//   - The general C control-flow suite covers guarded logic.
// - Summary:
//   - Division and remainder are undefined only in skipped arms.
// - Description:
//   - A skipped ternary must not evaluate either arithmetic arm.
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
        unsigned selected = next & 31U;
        if (((next & 1U) != 0U) && (((next & 2U) != 0U ? next / (next & 1U) : next % (next & 1U)) != 0U)) {
            selected = (next ^ 26U) & 31U;
        }
        putchar((int)selected);
        a = b;
        b = next;
    }
}
