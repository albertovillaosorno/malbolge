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
//   - Source-proven middle-default C switch control-flow experiment.
// - Must-Not:
//   - Substitute host output or claim general runtime C switch support.
// - Allows:
//   - Inputs: bounded C23 Fibonacci locals and source-ordered C switch labels.
//   - Outputs: twelve masked source-selected bytes from actual guest output.
//   - Side effects: putchar only.
// - Split-When:
//   - General source-to-guest control flow supersedes this bounded proof.
// - Merge-When:
//   - General seeded C control-flow verification subsumes the experiment.
// - Summary:
//   - Default between two case labels is a distinct direct dispatch target.
// - Description:
//   - Check exact output under EOF and binary stdin in the normative VM.
// - Usage:
//   - Compile with the pinned C frontend and c2malbolge pipeline.
// - Defaults:
//   - Preserve the independently computed masked Fibonacci oracle.
//
#include <stdio.h>

void emit(void) {
    unsigned a = 1U;
    unsigned b = 1U;
    for (unsigned i = 0U; i < 12U; ++i) {
        unsigned next = (a + b) & 255U;
        unsigned selected = next & 31U;
        switch (next & 3U) {
        case 0U:
            selected ^= 0U;
            break;
        default:
            selected ^= 26U;
            break;
        case 2U:
            selected ^= 0U;
            break;
        case 1U:
            selected ^= 26U;
            break;
        }
        putchar((int)selected);
        a = b;
        b = next;
    }
}
