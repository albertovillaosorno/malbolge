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
//   - Source-backed checked unsigned multiplication in a bounded C recurrence.
// - Must-Not:
//   - Claim runtime multiplication or loop execution inside Malbolge.
// - Allows:
//   - Inputs: unsigned locals, masked products, branching and three iterations.
//   - Outputs: one independent state-derived byte under the normative VM.
//   - Side effects: a single guest putchar after the recurrence.
// - Split-When:
//   - A general C state and arithmetic backend supersedes constant folding.
// - Merge-When:
//   - The complete compound C oracle becomes executable in the guest.
// - Summary:
//   - Prove products wider than a byte before masking and storing state.
// - Description:
//   - The selected branch changes a across odd/even product iterations.
// - Usage:
//   - Compile with pinned Clang and replay the emitted Malbolge in the VM.
// - Defaults:
//   - Unsupported effects, unknown operators or unchecked overflow reject.
//
#include <stdio.h>

void emit(void) {
    unsigned a = 3U;
    unsigned b = 5U;
    for (unsigned i = 0U; i < 3U; ++i) {
        unsigned next = (a * b) & 255U;
        if ((next & 1U) == 0U) {
            a = next ^ 1U;
        } else {
            a = next - 1U;
        }
        b = next;
    }
    putchar((int)(a ^ 86U));
}
