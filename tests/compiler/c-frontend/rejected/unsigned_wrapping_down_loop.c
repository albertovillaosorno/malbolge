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
//   - Refuse source-time unsigned loop analysis that would wrap forever.
// - Must-Not:
//   - Assume unsigned i >= 0 becomes false when i underflows.
// - Allows:
//   - Inputs: bounded C23 source with a nonterminating unsigned loop.
//   - Outputs: explicit compiler refusal before guest publication.
//   - Side effects: no execution in tests.
// - Split-When:
//   - General C runtime semantics prove finite paths independently.
// - Merge-When:
//   - Safe unsigned loop induction is proven for all admitted operators.
// - Summary:
//   - Unsigned decrement at zero wraps instead of terminating.
//
#include <stdio.h>

void emit(void) {
    for (unsigned i = 3U; i >= 0U; --i) {
        putchar(getchar());
    }
}
