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
//   - Source-proven repeated byte effects within a stateful C loop.
// - Must-Not:
//   - Assume equal byte values imply identical source SSA definitions.
// - Allows:
//   - Inputs: three bounded Fibonacci-style recurrence iterations.
//   - Outputs: ordered binary byte stream `88>` from branch arithmetic.
//   - Side effects: C putchar calls only.
// - Split-When:
//   - General guest string output subsumes this source-backed experiment.
// - Merge-When:
//   - Parametric guest stream tests cover repeated output identities.
// - Summary:
//   - Three source-distinct writes with two equal observed output bytes.
// - Description:
//   - Guest repeats the first accumulator without a redundant arithmetic write.
// - Usage:
//   - Run the native C-to-guest pipeline and verify under the current VM.
// - Defaults:
//   - Refuse without publishing if typed or guest proof fails.
//
#include <stdio.h>

void emit(void) {
    unsigned a = 1U;
    unsigned b = 1U;
    for (unsigned i = 0U; i < 3U; ++i) {
        unsigned next = (a + b) & 255U;
        if ((next & 1U) == 0U) {
            putchar((int)(next ^ 58U));
        } else {
            putchar((int)(next ^ 59U));
        }
        a = b;
        b = next;
    }
}
