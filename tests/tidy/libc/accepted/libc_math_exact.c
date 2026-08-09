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
//   - Positive source-preflight evidence for exact available guest math.
// - Must-Not:
//   - Reference unavailable sqrt/trigonometric routines or host libm state.
// - Allows:
//   - Inputs: fixed binary64 values and exact math calls.
//   - Outputs: one deterministic arithmetic combination.
//   - Side effects: none.
// - Split-When:
//   - Another independently available math family needs source evidence.
// - Merge-When:
//   - Guest libc positive fixtures own exact math source coverage together.
// - Summary:
//   - Admits fabs, floor, ceil, and trunc through source preflight.
// - Description:
//   - Exercises every exact binary64 routine promoted to executable guest C.
// - Usage:
//   - Consumed by guest-libc compile and manual-validator regressions.
// - Defaults:
//   - Inexact and transcendental math remains contracted-unavailable.
//

//! Positive source coverage for exact binary64 guest math.

#include <math.h>

double libc_math_exact_probe(double value) {
  return fabs(value) + floor(value) + ceil(value) + trunc(value);
}
