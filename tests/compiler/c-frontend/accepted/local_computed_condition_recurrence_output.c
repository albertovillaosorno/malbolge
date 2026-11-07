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
//   - Source-proven unsigned comparison of two computed C expressions.
// - Must-Not:
//   - Claim runtime guest arithmetic or admit unchecked condition effects.
// - Allows:
//   - Inputs: bounded stateful C recurrence and pure u32 comparison operands.
//   - Outputs: the final checked byte emitted by the normative guest VM.
//   - Side effects: one final putchar only.
// - Split-When:
//   - Dynamic guest control-flow compilation replaces closed C evaluation.
// - Merge-When:
//   - General typed-IR state propagation subsumes this bounded projection.
// - Summary:
//   - Both compared expressions depend on distinct locals and loop state.
// - Description:
//   - A three-iteration recurrence takes both branch arms.
// - Usage:
//   - Run the pinned C frontend and the normative guest VM.
// - Defaults:
//   - Unknown C operations fail without guest artifact publication.
//
#include <stdio.h>

void emit(void) {
    unsigned a = 3U;
    unsigned b = 5U;
    for (unsigned i = 0U; i < 3U; ++i) {
        unsigned next = ((a * b) << 2U) & 255U;
        if (((next & 31U) + (a & 7U)) >= ((b ^ 2U) + 3U)) {
            a = (next >> 3U) ^ 1U;
        } else {
            a = next - 1U;
        }
        b = next;
    }
    putchar((int)(a ^ 62U));
}
