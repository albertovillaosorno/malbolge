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
//   - Exact raw-binary64 preclassification for transcendental guest math.
// - Must-Not:
//   - Approximate finite transcendental values or change libc availability.
// - Allows:
//   - Inputs: raw binary64 words and one admitted unary operation identity.
//   - Outputs: exact resolved bits or an explicit kernel-required result.
//   - Side effects: none.
// - Split-When:
//   - Range reduction or approximation kernels gain independent proof policy.
// - Merge-When:
//   - Complete correctly-rounded transcendental implementations own this step.
// - Summary:
//   - Resolves only exact transcendental edge cases before numerical kernels.
// - Description:
//   - Canonicalizes NaNs and handles exact zero/infinity outcomes by raw bits.
// - Usage:
//   - Internal guest-libc substrate; public sin/cos/atan2 remain gated.
// - Defaults:
//   - Every unresolved finite case reports kernel-required without an estimate.
//

//! Internal exact edge-case classifier for future transcendental kernels.

#ifndef MALBOLGE_GUEST_MATH_TRANSCENDENTAL_BITS_H
#define MALBOLGE_GUEST_MATH_TRANSCENDENTAL_BITS_H

#include <stdint.h>

typedef enum MalbolgeGuestMathUnaryOperation {
  MALBOLGE_GUEST_MATH_SIN = 1,
  MALBOLGE_GUEST_MATH_COS = 2,
} MalbolgeGuestMathUnaryOperation;

typedef enum MalbolgeGuestMathSpecialStatus {
  MALBOLGE_GUEST_MATH_SPECIAL_INVALID = 0,
  MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED = 1,
  MALBOLGE_GUEST_MATH_SPECIAL_KERNEL_REQUIRED = 2,
} MalbolgeGuestMathSpecialStatus;

typedef struct MalbolgeGuestMathSpecialResult {
  MalbolgeGuestMathSpecialStatus status;
  uint64_t bits;
} MalbolgeGuestMathSpecialResult;

MalbolgeGuestMathSpecialResult malbolge_guest_math_unary_special(
    MalbolgeGuestMathUnaryOperation operation, uint64_t bits);
MalbolgeGuestMathSpecialResult malbolge_guest_math_atan2_special(
    uint64_t y_bits, uint64_t x_bits);

#endif
