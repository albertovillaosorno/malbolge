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
//   - Nested guest reads retain only the newest byte across two loops.
// - Must-Not:
//   - Synthesize repeated reads or silently reuse an older input.
// - Allows:
//   - Inputs: one unused original byte followed by four fresh guest reads.
//   - Outputs: four ordered writes of the four fresh input bytes.
//   - Side effects: five real guest reads and four writes.
// - Split-When:
//   - Runtime guest locals can retain the first value after new reads.
// - Merge-When:
//   - Nested source-to-SSA identities track newest and stale values.
// - Summary:
//   - Verify valid nested reads against the stale-alias negative control.
//
#include <stdio.h>

void emit(void) {
    int first = getchar();
    int alias = first;
    for (unsigned i = 0U; i < 2U; ++i) {
        for (unsigned j = 0U; j < 2U; ++j) {
            int recent = getchar();
            if (i & 1U) {
                putchar(recent);
            } else {
                putchar(recent);
            }
        }
    }
}
