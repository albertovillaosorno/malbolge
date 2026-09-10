// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Positive source-preflight evidence for available guest sine and cosine.
// - Must-Not:
//   - Reference unavailable atan2 or any host libm extension.
// - Allows:
//   - Inputs: one binary64 value.
//   - Outputs: the sum of canonical correctly rounded sine and cosine.
//   - Side effects: none.
// - Split-When:
//   - Another transcendental family gains independent availability.
// - Merge-When:
//   - Guest libc positive fixtures own all proved binary64 math together.
// - Summary:
//   - Admits sine and cosine after finite binary64 precision closure.
// - Description:
//   - Exercises both public symbols through the canonical math header.
// - Usage:
//   - Consumed by guest-libc compile and source-preflight regressions.
// - Defaults:
//   - Atan2 remains contracted-unavailable.
//

//! Positive source coverage for correctly rounded guest sine and cosine.

#include <math.h>

double libc_math_sincos_probe(double value) { return sin(value) + cos(value); }
