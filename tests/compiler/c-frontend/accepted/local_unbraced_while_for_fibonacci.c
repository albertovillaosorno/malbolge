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
//   - Complete Fibonacci recurrence with an unbraced while inside for.
// - Must-Not:
//   - Claim runtime C loops or fake normative VM byte output.
// - Allows:
//   - Inputs: checked C23 unsigned locals and source-proven loop predicates.
//   - Outputs: twelve masked, branch-selected Fibonacci bytes.
//   - Side effects: bounded C putchar calls.
// - Split-When:
//   - Dynamic guest C loops supersede finite source-state replay.
// - Merge-When:
//   - A general source-backed compound C corpus subsumes this proof.
// - Summary:
//   - An unbraced while emits two bytes per enclosing for iteration.
// - Description:
//   - The inner phase advances toward the changing outer induction value.
// - Usage:
//   - Compile via pinned Clang, JSON adapter, layout and normative VM.
// - Defaults:
//   - Refuse any unproved effect without publishing a guest artifact.
//
#include <stdio.h>

void emit(void) {
    unsigned a = 1U;
    unsigned b = 1U;
    unsigned phase = 0U;
    for (unsigned i = 2U; i <= 12U; i += 2U)
        while (phase < i) {
            unsigned next = (a + b) & 255U;
            if ((next & 1U) == 0U) {
                putchar((int)(next & 31U));
            } else {
                putchar((int)((next ^ 0x1AU) & 31U));
            }
            a = b;
            b = next;
            ++phase;
        }
}
