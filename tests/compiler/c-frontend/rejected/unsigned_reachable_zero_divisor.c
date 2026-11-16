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
//   - Source-proven short-circuit unsigned division with live guest bytes.
// - Must-Not:
//   - Evaluate an unselected divisor or conceal a reachable zero divisor.
// - Allows:
//   - Inputs: a bounded unsigned induction counter and successful byte I/O.
//   - Outputs: none when a reachable zero divisor would execute.
//   - Side effects: runtime getchar and putchar on the selected path.
// - Split-When:
//   - General runtime C control replaces compile-time induction proofs.
// - Merge-When:
//   - Signed and unsigned skipped arithmetic share pure-source checks.
// - Summary:
//   - Refuse a reachable divisor with zero under genuine C control.
//
#include <stdio.h>
void emit(void) {
    for (unsigned i = 1U; i < 3U; ++i) {
        int current = getchar();
        if (i == 2U || i / 0U == 1U) {
            putchar(current);
            break;
        }
        putchar(current);
    }
}
