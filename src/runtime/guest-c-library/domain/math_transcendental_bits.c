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
//   - Exact special-case reduction for future sin, cos, and atan2 kernels.
// - Must-Not:
//   - Approximate finite transcendental results or call host floating helpers.
// - Allows:
//   - Inputs: ABI-fixed raw binary64 words.
//   - Outputs: exact result bits or a kernel-required classification.
//   - Side effects: none.
// - Split-When:
//   - Range reduction or approximation gains an independently proved kernel.
// - Merge-When:
//   - Correctly-rounded transcendental routines consume this exact front end.
// - Summary:
//   - Classifies exact transcendental edge cases with integer bit operations.
// - Description:
//   - Resolves canonical NaNs, infinities, and exact signed-zero identities.
// - Usage:
//   - Internal only while public transcendental routines remain unavailable.
// - Defaults:
//   - Ordinary finite inputs remain unresolved and never receive an estimate.
//

//! Representation-only exact edge cases for future transcendental guest math.

#include "../contract/math_transcendental_bits.h"

#define BINARY64_SIGN UINT64_C(0x8000000000000000)
#define BINARY64_EXPONENT UINT64_C(0x7ff0000000000000)
#define BINARY64_FRACTION UINT64_C(0x000fffffffffffff)
#define BINARY64_CANONICAL_NAN UINT64_C(0x7ff8000000000000)
#define BINARY64_ONE UINT64_C(0x3ff0000000000000)

static int is_nan(uint64_t bits) {
  return (bits & BINARY64_EXPONENT) == BINARY64_EXPONENT &&
         (bits & BINARY64_FRACTION) != UINT64_C(0);
}

static int is_infinity(uint64_t bits) {
  return (bits & ~BINARY64_SIGN) == BINARY64_EXPONENT;
}

static int is_zero(uint64_t bits) {
  return (bits & ~BINARY64_SIGN) == UINT64_C(0);
}

static MalbolgeGuestMathSpecialResult resolved(uint64_t bits) {
  MalbolgeGuestMathSpecialResult result = {
      MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED, bits};
  return result;
}

static MalbolgeGuestMathSpecialResult kernel_required(void) {
  MalbolgeGuestMathSpecialResult result = {
      MALBOLGE_GUEST_MATH_SPECIAL_KERNEL_REQUIRED, UINT64_C(0)};
  return result;
}

MalbolgeGuestMathSpecialResult malbolge_guest_math_unary_special(
    MalbolgeGuestMathUnaryOperation operation, uint64_t bits) {
  if (operation != MALBOLGE_GUEST_MATH_SIN &&
      operation != MALBOLGE_GUEST_MATH_COS) {
    MalbolgeGuestMathSpecialResult invalid = {
        MALBOLGE_GUEST_MATH_SPECIAL_INVALID, UINT64_C(0)};
    return invalid;
  }
  if (is_nan(bits) || is_infinity(bits)) {
    return resolved(BINARY64_CANONICAL_NAN);
  }
  if (!is_zero(bits)) {
    return kernel_required();
  }
  if (operation == MALBOLGE_GUEST_MATH_SIN) {
    return resolved(bits);
  }
  return resolved(BINARY64_ONE);
}

MalbolgeGuestMathSpecialResult malbolge_guest_math_atan2_special(
    uint64_t y_bits, uint64_t x_bits) {
  if (is_nan(y_bits) || is_nan(x_bits)) {
    return resolved(BINARY64_CANONICAL_NAN);
  }
  if (is_zero(y_bits) && (x_bits & BINARY64_SIGN) == UINT64_C(0)) {
    return resolved(y_bits);
  }
  if (is_infinity(x_bits) && (x_bits & BINARY64_SIGN) == UINT64_C(0) &&
      !is_infinity(y_bits)) {
    return resolved(y_bits & BINARY64_SIGN);
  }
  return kernel_required();
}
