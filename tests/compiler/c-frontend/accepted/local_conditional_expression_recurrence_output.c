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
//   - Source-proven conditional selection inside an unsigned C recurrence.
// - Must-Not:
//   - Claim guest runtime C branching or unchecked conditional effects.
// - Allows:
//   - Inputs: a bounded loop and a pure three-operand conditional expression.
//   - Outputs: a source-derived byte executed by the normative guest VM.
//   - Side effects: one final putchar only.
// - Split-When:
//   - General guest control flow supersedes bounded compile-time selection.
// - Merge-When:
//   - General typed state propagation replaces closed C constant folding.
// - Summary:
//   - Both conditional alternatives depend on loop-carried local state.
// - Description:
//   - A three-iteration C recurrence selects both conditional alternatives.
// - Usage:
//   - Compile with pinned Clang and verify actual Malbolge VM output.
// - Defaults:
//   - Unsupported conditional operators or side effects fail closed.
//
#include <stdio.h>

void emit(void) {
    unsigned a = 3U;
    unsigned b = 5U;
    for (unsigned i = 0U; i < 3U; ++i) {
        unsigned next = ((a * b) << 2U) & 255U;
        a = ((next & 8U) != 0U) ? ((next >> 3U) ^ 1U) : (next - 1U);
        b = next;
    }
    putchar((int)(a ^ 62U));
}
