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
//   - Source-proven multi-output C loop and independent normative VM replay.
// - Must-Not:
//   - Claim guest runtime arithmetic or replace actual Malbolge byte effects.
// - Allows:
//   - Inputs: bounded Fibonacci-style state and source-checked conditional I/O.
//   - Outputs: twelve C-selected zero bytes from the real Malbolge guest VM.
//   - Side effects: putchar inside each iteration, with no hidden host output.
// - Split-When:
//   - Dynamic guest loop state supersedes compiler-time evaluation.
// - Merge-When:
//   - General byte-stream lowering handles the original Fibonacci program.
// - Summary:
//   - Conditional per-iteration output from checked local expressions.
// - Description:
//   - Both arms emit zero by different C operations on current loop state.
// - Usage:
//   - Run pinned Clang, typed projection, layout and normative guest VM.
// - Defaults:
//   - Unsupported output effects must fail without an artifact.
//
#include <stdio.h>

void emit(void) {
    unsigned a = 1U;
    unsigned b = 1U;
    for (unsigned i = 0U; i < 12U; ++i) {
        unsigned next = (a + b) & 255U;
        if ((next & 1U) == 0U) {
            putchar((int)(next ^ next));
        } else {
            putchar((int)(next - next));
        }
        a = b;
        b = next;
    }
}
