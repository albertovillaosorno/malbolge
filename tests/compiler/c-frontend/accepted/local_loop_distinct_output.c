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
//   - Source-proven branching loop with two different guest output bytes.
// - Must-Not:
//   - Delegate guest output to the host or assume runtime state lowering.
// - Allows:
//   - Inputs: checked bounded unsigned Fibonacci C state.
//   - Outputs: independent Q. byte oracle from real guest output instructions.
//   - Side effects: two selected putchar calls.
// - Split-When:
//   - General guest-state backend supersedes bounded compiler-time folding.
// - Merge-When:
//   - General output-stream lowering subsumes this verified loop.
// - Summary:
//   - Source-backed conditional arithmetic selecting different guest bytes.
// - Description:
//   - The two-iteration recurrence emits 2^83=81 and 3^45=46.
// - Usage:
//   - Replay pinned Clang to typed projection, layout and normative guest VM.
// - Defaults:
//   - Unwitnessed output sequences refuse without a guest artifact.
//
#include <stdio.h>

void emit(void) {
    unsigned a = 1U;
    unsigned b = 1U;
    for (unsigned i = 0U; i < 2U; ++i) {
        unsigned next = (a + b) & 255U;
        if ((next & 1U) == 0U) {
            putchar((int)(next ^ 83U));
        } else {
            putchar((int)(next ^ 45U));
        }
        a = b;
        b = next;
    }
}
