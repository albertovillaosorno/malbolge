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
//   - Compound C loop with source-selected zero-prefixed guest output.
// - Must-Not:
//   - Replace guest output with host bytes or claim runtime C arithmetic.
// - Allows:
//   - Inputs: closed unsigned state, conditionals and four output effects.
//   - Outputs: exactly four independently checked real Malbolge bytes.
//   - Side effects: only the source-proven putchar calls.
// - Split-When:
//   - General byte-stream synthesis supersedes bounded projection.
// - Merge-When:
//   - Runtime C branch lowering proves this whole source independently.
// - Summary:
//   - An initial zero output precedes relocated guest arithmetic outputs.
// - Usage:
//   - Run tests.test_compound_c_pipeline.
// - Defaults:
//   - Unsupported expressions refuse output publication.
//
#include <stdio.h>

void emit(void) {
    unsigned a = 1U;
    unsigned b = 1U;
    for (unsigned i = 0U; i < 4U; ++i) {
        unsigned next = (a + b) & 255U;
        if ((next & 1U) == 0U) {
            putchar((int)((next == 2U) ? 0U : 63U));
        } else {
            putchar((int)((next == 3U) ? 84U : 178U));
        }
        a = b;
        b = next;
    }
}
