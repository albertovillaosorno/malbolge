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

#include <stddef.h>

#define BINARY64_SIGN UINT64_C(0x8000000000000000)
#define BINARY64_EXPONENT UINT64_C(0x7ff0000000000000)
#define BINARY64_FRACTION UINT64_C(0x000fffffffffffff)
#define BINARY64_CANONICAL_NAN UINT64_C(0x7ff8000000000000)
#define BINARY64_ONE UINT64_C(0x3ff0000000000000)
#define BINARY64_SMALL_ANGLE_MAX UINT64_C(0x3e40000000000000)
#define BINARY64_PI_OVER_FOUR UINT64_C(0x3fe921fb54442d18)
#define BINARY64_PI_OVER_TWO UINT64_C(0x3ff921fb54442d18)
#define BINARY64_PI UINT64_C(0x400921fb54442d18)
#define BINARY64_THREE_PI_OVER_FOUR UINT64_C(0x4002d97c7f3321d2)
#define BINARY64_HIDDEN_BIT UINT64_C(0x0010000000000000)
#define BINARY64_EXPONENT_SHIFT UINT32_C(52)
#define BINARY64_EXPONENT_BIAS INT32_C(1023)
#define BINARY64_SUBNORMAL_EXPONENT INT32_C(-1074)

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

static uint64_t with_sign(uint64_t magnitude, uint64_t source) {
  return magnitude | (source & BINARY64_SIGN);
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
  if ((bits & ~BINARY64_SIGN) <= BINARY64_SMALL_ANGLE_MAX) {
    if (operation == MALBOLGE_GUEST_MATH_SIN) {
      return resolved(bits);
    }
    return resolved(BINARY64_ONE);
  }
  return kernel_required();
}

typedef struct NormalizedMagnitude {
  uint64_t significand;
  int32_t exponent;
} NormalizedMagnitude;

static NormalizedMagnitude normalize_magnitude(uint64_t magnitude) {
  const uint32_t raw_exponent =
      (uint32_t)((magnitude & BINARY64_EXPONENT) >> BINARY64_EXPONENT_SHIFT);
  NormalizedMagnitude normalized;

  normalized.significand = magnitude & BINARY64_FRACTION;
  if (raw_exponent != UINT32_C(0)) {
    normalized.significand |= BINARY64_HIDDEN_BIT;
    normalized.exponent = (int32_t)raw_exponent - BINARY64_EXPONENT_BIAS -
                          (int32_t)BINARY64_EXPONENT_SHIFT;
    return normalized;
  }
  normalized.exponent = BINARY64_SUBNORMAL_EXPONENT;
  while ((normalized.significand & BINARY64_HIDDEN_BIT) == UINT64_C(0)) {
    normalized.significand <<= UINT32_C(1);
    --normalized.exponent;
  }
  return normalized;
}

MalbolgeGuestMathSpecialResult malbolge_guest_math_atan2_special(
    uint64_t y_bits, uint64_t x_bits) {
  const int y_infinite = is_infinity(y_bits);
  const int x_infinite = is_infinity(x_bits);

  if (is_nan(y_bits) || is_nan(x_bits)) {
    return resolved(BINARY64_CANONICAL_NAN);
  }
  if (is_zero(y_bits)) {
    if ((x_bits & BINARY64_SIGN) == UINT64_C(0)) {
      return resolved(y_bits);
    }
    return resolved(with_sign(BINARY64_PI, y_bits));
  }
  if (is_zero(x_bits)) {
    return resolved(with_sign(BINARY64_PI_OVER_TWO, y_bits));
  }
  if (y_infinite != 0) {
    if (x_infinite != 0) {
      const uint64_t magnitude =
          (x_bits & BINARY64_SIGN) == UINT64_C(0)
              ? BINARY64_PI_OVER_FOUR
              : BINARY64_THREE_PI_OVER_FOUR;
      return resolved(with_sign(magnitude, y_bits));
    }
    return resolved(with_sign(BINARY64_PI_OVER_TWO, y_bits));
  }
  if (x_infinite != 0) {
    if ((x_bits & BINARY64_SIGN) == UINT64_C(0)) {
      return resolved(y_bits & BINARY64_SIGN);
    }
    return resolved(with_sign(BINARY64_PI, y_bits));
  }
  return kernel_required();
}

int malbolge_guest_math_atan2_kernel_input(
    uint64_t y_bits, uint64_t x_bits,
    MalbolgeGuestMathAtan2KernelInput *output) {
  const uint64_t y_magnitude = y_bits & ~BINARY64_SIGN;
  const uint64_t x_magnitude = x_bits & ~BINARY64_SIGN;
  MalbolgeGuestMathAtan2KernelInput staged;
  NormalizedMagnitude numerator;
  NormalizedMagnitude denominator;

  if (output == NULL || y_magnitude == UINT64_C(0) ||
      x_magnitude == UINT64_C(0) || is_infinity(y_bits) ||
      is_infinity(x_bits) || is_nan(y_bits) || is_nan(x_bits)) {
    return 0;
  }
  staged.swapped = y_magnitude > x_magnitude ? UINT32_C(1) : UINT32_C(0);
  staged.y_negative =
      (y_bits & BINARY64_SIGN) != UINT64_C(0) ? UINT32_C(1) : UINT32_C(0);
  staged.x_negative =
      (x_bits & BINARY64_SIGN) != UINT64_C(0) ? UINT32_C(1) : UINT32_C(0);
  if (staged.swapped != UINT32_C(0)) {
    numerator = normalize_magnitude(x_magnitude);
    denominator = normalize_magnitude(y_magnitude);
  } else {
    numerator = normalize_magnitude(y_magnitude);
    denominator = normalize_magnitude(x_magnitude);
  }
  staged.numerator_significand = numerator.significand;
  staged.denominator_significand = denominator.significand;
  staged.exponent_delta = numerator.exponent - denominator.exponent;
  *output = staged;
  return 1;
}
