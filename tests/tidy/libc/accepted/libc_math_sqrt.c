// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Positive source-preflight evidence for available canonical guest sqrt.
// - Must-Not:
//   - Reference unavailable transcendental routines or host rounding state.
// - Allows:
//   - Inputs: one binary64 value.
//   - Outputs: one canonical nearest-ties-even square-root result.
//   - Side effects: none.
// - Split-When:
//   - Another independently available inexact math family needs source
//   evidence.
// - Merge-When:
//   - Guest libc positive fixtures own all proved binary64 math together.
// - Summary:
//   - Admits sqrt through source preflight after integer-algorithm proof.
// - Description:
//   - Exercises the public routine without importing host libm or fenv state.
// - Usage:
//   - Consumed by guest-libc compile and manual-validator regressions.
// - Defaults:
//   - Sin, cos, and atan2 remain contracted-unavailable.
//

//! Positive source coverage for canonical binary64 guest square root.

#include <math.h>

double libc_math_sqrt_probe(double value) { return sqrt(value); }
