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
//   - Source-dependent unsigned-local arithmetic guest output regression.
// - Must-Not:
//   - Claim runtime arithmetic, aliases, general locals, or loop support.
// - Allows:
//   - Inputs: one automatic unsigned, ordered source-bound arithmetic writes.
//   - Outputs: the final computed byte through a real guest output effect.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General C arithmetic and storage lowering subsumes this bounded case.
// - Merge-When:
//   - Stateful compiler acceptance owns source-dependent arithmetic parity.
// - Summary:
//   - Addition, XOR, and subtraction depend on the prior local value.
// - Description:
//   - Prove each read and write before source-bound constant propagation.
// - Usage:
//   - Replayed through pinned Clang, typed IR, layout, and normative VM.
// - Defaults:
//   - Unsupported operations never publish a guest artifact.

#include <stdio.h>

void emit(void) {
    unsigned value = 60U;
    value = value + 8U;
    value = value ^ 3U;
    value = value - 6U;
    putchar(value);
}
