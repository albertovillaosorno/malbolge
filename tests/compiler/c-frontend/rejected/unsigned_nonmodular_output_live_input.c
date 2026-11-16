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
//   - Nonidentity C23 output byte arithmetic rejection control.
// - Must-Not:
//   - Replace one changed output byte with an unmodified guest input byte.
// - Allows:
//   - Inputs: four successful getchar values.
//   - Outputs: C arithmetic changes the first written byte.
//   - Side effects: a rejected candidate publishes no guest artifact.
// - Split-When:
//   - Guest arithmetic output supports faithful transformed bytes.
// - Merge-When:
//   - Independent VM arithmetic oracles cover the same negative input.
// - Description:
//   - One pure C output changes every successful input byte.
// - Usage:
//   - Pinned C23 frontend and normative byte-stream regressions.
// - Defaults:
//   - A changed byte cannot be emitted as an unchanged guest byte.
// - Summary:
//   - Reject source arithmetic differing modulo 256.
//
//! Source-bound modulo-byte output proof fixture.

#include <stdio.h>

void emit(void) {
    for (unsigned i = 0U; i < 4U; ++i) {
        int current = getchar();
        putchar((current + 257) & 255);
        putchar(0 + current);
        putchar(current ^ 256);
    }
}
