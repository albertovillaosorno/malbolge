// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - LicenseRef-Proprietary
// Confidential:
//   - true
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Source-backed unsigned bitwise complement in a bounded recurrence.
// - Must-Not:
//   - Substitute host output for actual guest execution.
// - Allows:
//   - Inputs: local state, checked arithmetic, and a pure unary complement.
//   - Outputs: one computed byte through the normative Malbolge VM.
//   - Side effects: one final output effect.
// - Split-When:
//   - General dynamic guest arithmetic replaces constant folding.
// - Merge-When:
//   - A general typed C expression lowering proof subsumes this example.
// - Summary:
//   - Complement a loop-carried unsigned word before narrowing by masking.
// - Description:
//   - A bounded loop proves two conditional alternatives and unsigned width.
// - Usage:
//   - Compile with pinned Clang and run the actual Malbolge VM.
// - Defaults:
//   - No host output substitution or unsupported source side effects.

#include <stdio.h>

void emit(void) {
    unsigned a = 3U;
    unsigned b = 5U;
    for (unsigned i = 0U; i < 3U; ++i) {
        unsigned next = ((a * b) << 2U) & 255U;
        a = ((next & 8U) != 0U) ? ((~next) & 255U) : ((next >> 3U) ^ 1U);
        b = next;
    }
    putchar((int)(a ^ 88U));
}
