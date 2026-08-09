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
//   - Negative evidence for contracted but unavailable deterministic libm.
// - Must-Not:
//   - Resolve through host libm or classify deterministic math as forbidden.
// - Allows:
//   - Inputs: one binary64 constant.
//   - Outputs: one source-located MALBOLGE-LIBC-001 diagnostic.
//   - Side effects: none because validation rejects the call before lowering.
// - Split-When:
//   - Split when another unavailable math family needs independent evidence.
// - Merge-When:
//   - Merge when another fixture owns this exact libm rejection.
// - Summary:
//   - Contracted-unavailable sin fixture.
// - Description:
//   - Proves exact future math signatures do not imply executable support.
// - Usage:
//   - Consumed by guest-libc source preflight regression tests.
// - Defaults:
//   - Rejection occurs at the sin reference in this source file.
//

//! Deterministic binary64 math is contracted now and implemented later.

#include <math.h>

double libc_math_probe(void)
{
    return sin(4.0);
}
