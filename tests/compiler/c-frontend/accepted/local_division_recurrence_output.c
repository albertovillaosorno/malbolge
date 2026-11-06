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
//   - Source-proven unsigned quotient inside a stateful C loop and branch.
// - Must-Not:
//   - Claim guest execution of C division or recurrence state.
// - Allows:
//   - Inputs: bounded unsigned locals, products, three iterations and a divisor.
//   - Outputs: a source-derived byte checked against the normative guest VM.
//   - Side effects: one final guest putchar after the recurrence.
// - Split-When:
//   - General C arithmetic and runtime branching supersede closed folding.
// - Merge-When:
//   - Complete runtime C input/output programs reach guest parity.
// - Summary:
//   - Prove nonzero checked unsigned division in a conditional recurrence.
// - Description:
//   - Both branch outcomes update state and the quotient is not a byte write.
// - Usage:
//   - Compile with pinned Clang and replay emitted Malbolge under the VM.
// - Defaults:
//   - Zero divisors and unrecognized effects fail closed.
//
#include <stdio.h>

void emit(void) {
    unsigned a = 3U;
    unsigned b = 5U;
    for (unsigned i = 0U; i < 3U; ++i) {
        unsigned next = (a * b) & 255U;
        if ((next & 1U) == 0U) {
            a = (next / 17U) ^ 1U;
        } else {
            a = next - 1U;
        }
        b = next;
    }
    putchar((int)(a ^ 74U));
}
