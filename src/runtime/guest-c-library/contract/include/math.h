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
//   - Exact declarations for the deterministic guest binary64 math surface.
// - Must-Not:
//   - Resolve through host libm or claim unimplemented rounding behavior.
// - Allows:
//   - Inputs: guest binary64 values admitted by malbolge-c32-v1.
//   - Outputs: fixed routine declarations with per-routine availability.
//   - Side effects: none.
// - Split-When:
//   - Split when float or long-double math gains independent support status.
// - Merge-When:
//   - Merge when another header owns these exact guest binary64 signatures.
// - Summary:
//   - Version-one deterministic binary64 math contract.
// - Description:
//   - Proved exact/sqrt routines execute as guest C; transcendental work is
//     gated.
// - Usage:
//   - Included by guest source; unavailable calls still fail preflight.
// - Defaults:
//   - No host floating-point library is a fallback.
//

//! Version-one binary64 math surface for malbolge-libc-v1.

#ifndef MALBOLGE_GUEST_LIBC_MATH_H
#define MALBOLGE_GUEST_LIBC_MATH_H

double fabs(double value);
double sqrt(double value);
double floor(double value);
double ceil(double value);
double trunc(double value);
double sin(double value);
double cos(double value);
double atan2(double y, double x);

#endif
