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
//   - Negative finite-unroll proof for an unsigned wrapping non-unit step.
// - Must-Not:
//   - Treat wrapping from one to UINT_MAX as loop termination.
// - Allows:
//   - Inputs: genuine unsigned source-C loop.
//   - Outputs: a typed refusal before guest publication.
//   - Side effects: none.
// - Split-When:
//   - General unsigned termination analysis replaces bounded steps.
// - Merge-When:
//   - Non-unit induction tests share this counterexample.
// - Summary:
//   - A descending unsigned step of two never escapes a positive guard.

#include <stdio.h>

void emit(void) {
    for (unsigned i = 9U; i > 0U; i -= 2U) {
        putchar(getchar());
    }
}
