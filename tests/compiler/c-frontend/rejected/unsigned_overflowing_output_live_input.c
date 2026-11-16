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
//   - Defined signed-integer arithmetic requirement for C output proof.
// - Must-Not:
//   - Treat overflowed i32 products as valid modular byte identities.
// - Allows:
//   - Inputs: four successful getchar values.
//   - Outputs: a C expression undefined for some successful input bytes.
//   - Side effects: a rejected candidate publishes no guest artifact.
// - Split-When:
//   - General defined-behavior diagnostics replace finite byte proofs.
// - Merge-When:
//   - Whole-C validation proves the same i32 overflow refusal.
// - Description:
//   - Multiplication overflows signed int for successful bytes >= 2.
// - Usage:
//   - Pinned C23 frontend and failed guest publication regression.
// - Defaults:
//   - Undefined signed arithmetic must never become guest byte output.
// - Summary:
//   - Refuse reachable signed overflow while proving modulo output.
//
//! Source-bound undefined signed output arithmetic rejection fixture.

#include <stdio.h>

void emit(void) {
    for (unsigned i = 0U; i < 4U; ++i) {
        int current = getchar();
        putchar(current * 2147483647);
    }
}
