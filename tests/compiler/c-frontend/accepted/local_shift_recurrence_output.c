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
//   - Source-backed C unsigned shifts inside a bounded conditional recurrence.
// - Must-Not:
//   - Claim guest execution of shifts, loops, or runtime C state.
// - Allows:
//   - Inputs: byte locals, widened intermediates and both shift directions.
//   - Outputs: independently derived byte through the normative guest VM.
//   - Side effects: one final putchar after a complete C recurrence.
// - Split-When:
//   - Runtime C arithmetic replaces closed constant evaluation.
// - Merge-When:
//   - General source-proven C arithmetic subsumes this focused witness.
// - Summary:
//   - Prove checked shift counts and 32-bit unsigned semantics.
// - Description:
//   - Both conditional arms execute across three folded loop iterations.
// - Usage:
//   - Compile through pinned Clang and replay actual guest instructions.
// - Defaults:
//   - Shift counts outside unsigned's width must not publish guest artifacts.
//
#include <stdio.h>

void emit(void) {
    unsigned a = 3U;
    unsigned b = 5U;
    for (unsigned i = 0U; i < 3U; ++i) {
        unsigned next = ((a * b) << 2U) & 255U;
        if ((next & 8U) == 0U) {
            a = (next >> 3U) ^ 1U;
        } else {
            a = next - 1U;
        }
        b = next;
    }
    putchar((int)(a ^ 88U));
}
