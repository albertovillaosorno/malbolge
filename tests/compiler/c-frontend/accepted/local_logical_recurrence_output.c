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
//   - Source-proven short-circuit Boolean selection in a bounded C recurrence.
// - Must-Not:
//   - Claim dynamic guest state or execute impure skipped branches on the host.
// - Allows:
//   - Inputs: checked unsigned comparisons under C logical AND and OR.
//   - Outputs: one independently checked actual guest byte.
//   - Side effects: final putchar only.
// - Split-When:
//   - General C control-flow lowering subsumes compile-time Boolean folding.
// - Merge-When:
//   - A general source-proven predicate evaluator replaces this bounded path.
// - Summary:
//   - Bind both operands of a pure logical condition to the Clang source AST.
// - Description:
//   - Check both branch shapes and output after three stateful loop iterations.
// - Usage:
//   - Compile with pinned Clang and replay the normative Malbolge VM.
// - Defaults:
//   - Unknown Boolean operations and side effects must refuse.
//
#include <stdio.h>

void emit(void) {
    unsigned a = 3U;
    unsigned b = 5U;
    for (unsigned i = 0U; i < 3U; ++i) {
        unsigned next = ((a * b) << 2U) & 255U;
        if (((next & 8U) < 8U) && ((b & 4U) != 0U)) {
            a = (next >> 3U) ^ 1U;
        } else {
            a = next - 1U;
        }
        b = next;
    }
    putchar((int)(a ^ 254U));
}
