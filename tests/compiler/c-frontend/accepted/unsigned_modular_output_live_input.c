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
//   - Proved C23 modular byte output from a resident guest input byte.
// - Must-Not:
//   - Predict stdin, compute byte arithmetic on the host, or erase effects.
// - Allows:
//   - Inputs: four successful source-C getchar results.
//   - Outputs: twenty source-authenticated modulo-256 byte identities.
//   - Side effects: four reads and twenty writes.
// - Split-When:
//   - General runtime C integer ALU emits guest arithmetic instructions.
// - Merge-When:
//   - The full guest-output arithmetic lowering subsumes this proof.
// - Description:
//   - Authenticated pure C output wraps modulo 256.
// - Usage:
//   - Pinned C23 frontend and normative byte-stream regressions.
// - Defaults:
//   - No arithmetic that changes the emitted byte is admitted.
// - Summary:
//   - Verify pure arithmetic under the putchar unsigned-char conversion.
//
//! Source-bound modulo-byte output proof fixture.

#include <stdio.h>

void emit(void) {
    for (unsigned i = 0U; i < 4U; ++i) {
        int current = getchar();
        putchar((current + 256) & 255);
        putchar(0 + current);
        putchar(current ^ 256);
        putchar(current - 256);
        putchar(current * 257);
    }
}
