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
//   - Real Clang automatic unsigned local initialization and read regression.
// - Must-Not:
//   - Claim variable updates, arithmetic, loops, or branches are lowered.
// - Allows:
//   - Inputs: one initialized unsigned local used in a putchar call.
//   - Outputs: the guest's witnessed byte 'A'.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General local state lowering subsumes this semantic regression.
// - Merge-When:
//   - The general C compiler matrix verifies variable use and update.
// - Summary:
//   - Separate local declaration and source-reference semantics from literals.
// - Description:
//   - Literal source-only emission cannot prove this source's data dependency.
// - Usage:
//   - Replayed with the pinned frontend and normative VM integration test.
// - Defaults:
//   - No guest artifact is published if any local metadata drifts.

#include <stdio.h>

void emit(void) {
    unsigned value = 65U;
    putchar(value);
}
