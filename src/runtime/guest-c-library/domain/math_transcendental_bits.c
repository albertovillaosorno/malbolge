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
//   - Exact pre-kernel reduction for future sin, cos, and atan2 routines.
// - Must-Not:
//   - Approximate finite transcendental results or call host floating helpers.
// - Allows:
//   - Inputs: ABI-fixed raw binary64 words.
//   - Outputs: exact cases, normalized ratios, or exact rounded ratio bits.
//   - Side effects: none.
// - Split-When:
//   - Range reduction or approximation gains an independently proved kernel.
// - Merge-When:
//   - Correctly-rounded transcendental routines consume this exact front end.
// - Summary:
//   - Resolves proved transcendental cases with integer bit operations only.
// - Description:
//   - Adds proved small-ratio atan identities before exact kernel geometry.
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
#define BINARY64_SIN_SMALL_ANGLE_MAX UINT64_C(0x3e57000000000000)
#define BINARY64_COS_SMALL_ANGLE_MAX UINT64_C(0x3e46a00000000000)
#define BINARY64_ATAN_IDENTITY_MAX UINT64_C(0x3e4c000000000000)
#define BINARY64_PI_OVER_FOUR UINT64_C(0x3fe921fb54442d18)
#define BINARY64_PI_OVER_TWO UINT64_C(0x3ff921fb54442d18)
#define BINARY64_PI UINT64_C(0x400921fb54442d18)
#define BINARY64_THREE_PI_OVER_FOUR UINT64_C(0x4002d97c7f3321d2)
#define BINARY64_FOUR UINT64_C(0x4010000000000000)
#define BINARY64_HIDDEN_BIT UINT64_C(0x0010000000000000)
#define BINARY64_EXPONENT_SHIFT UINT32_C(52)
#define BINARY64_EXPONENT_BIAS INT32_C(1023)
#define BINARY64_SUBNORMAL_EXPONENT INT32_C(-1074)
#define BINARY64_RATIO_MIN_EXPONENT_DELTA INT32_C(-2097)
#define BINARY64_ATAN_UNCONDITIONAL_EXPONENT INT32_C(-54)
#define ATAN2_ADAPTIVE_NUMERATOR_BITS_MAX UINT32_C(108)
#define ATAN2_ADAPTIVE_DENOMINATOR_BITS_MAX UINT32_C(106)
#define ATAN2_LAMBERT_SCALE_EXPONENT_MAX INT32_C(56)
#define ATAN_QUARTER_REDUCTION_NUMERATOR UINT64_C(169)
#define ATAN_QUARTER_REDUCTION_DENOMINATOR UINT64_C(408)
#define FIXED_192_LIMB_COUNT UINT32_C(7)
#define FIXED_192_FRACTION_BITS INT32_C(192)
#define FIXED_224_LIMB_COUNT UINT32_C(8)
#define FIXED_224_FRACTION_BITS INT32_C(224)
#define FIXED_256_LIMB_COUNT UINT32_C(9)
#define FIXED_256_FRACTION_BITS INT32_C(256)
#define EXACT_RATIO_COMPONENT_LIMIT UINT64_C(0x0100000000000000)
#define FIXED_MAX_LIMB_COUNT UINT32_C(9)
#define FIXED_MAX_PRODUCT_LIMBS UINT32_C(18)
#define ATAN_SERIES_TERMS UINT32_C(60)
#define ATAN_224_SERIES_TERMS UINT32_C(85)
#define ATAN_256_SERIES_TERMS UINT32_C(98)

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

static int positive_binary64_components(uint64_t bits, uint64_t *significand,
                                        int32_t *power) {
  const uint64_t raw_exponent =
      (bits & BINARY64_EXPONENT) >> BINARY64_EXPONENT_SHIFT;
  const uint64_t fraction = bits & BINARY64_FRACTION;
  if (significand == NULL || power == NULL || (bits & BINARY64_SIGN) != 0 ||
      raw_exponent == UINT64_C(0x7ff)) {
    return 0;
  }
  if (raw_exponent == UINT64_C(0)) {
    *significand = fraction;
    *power = BINARY64_SUBNORMAL_EXPONENT;
    return 1;
  }
  *significand = BINARY64_HIDDEN_BIT | fraction;
  *power = (int32_t)raw_exponent - BINARY64_EXPONENT_BIAS - INT32_C(52);
  return 1;
}

static void normalize_dyadic(MalbolgeGuestMathDyadic *value) {
  while (value->denominator_shift != UINT32_C(0) &&
         (value->numerator & UINT64_C(1)) == UINT64_C(0)) {
    value->numerator >>= UINT32_C(1);
    --value->denominator_shift;
  }
}

static int positive_binary64_midpoint(uint64_t lower_bits, uint64_t upper_bits,
                                      MalbolgeGuestMathDyadic *output) {
  uint64_t lower_significand = UINT64_C(0);
  uint64_t upper_significand = UINT64_C(0);
  uint64_t lower_scaled = UINT64_C(0);
  uint64_t upper_scaled = UINT64_C(0);
  uint64_t sum = UINT64_C(0);
  int32_t lower_power = INT32_C(0);
  int32_t upper_power = INT32_C(0);
  int32_t common_power = INT32_C(0);
  int32_t midpoint_power = INT32_C(0);
  uint32_t lower_shift = UINT32_C(0);
  uint32_t upper_shift = UINT32_C(0);
  MalbolgeGuestMathDyadic staged;

  staged.numerator = UINT64_C(0);
  staged.denominator_shift = UINT32_C(0);
  staged.negative = UINT32_C(0);
  if (output == NULL || lower_bits > upper_bits ||
      !positive_binary64_components(lower_bits, &lower_significand,
                                    &lower_power) ||
      !positive_binary64_components(upper_bits, &upper_significand,
                                    &upper_power)) {
    return 0;
  }
  common_power = lower_power < upper_power ? lower_power : upper_power;
  lower_shift = (uint32_t)(lower_power - common_power);
  upper_shift = (uint32_t)(upper_power - common_power);
  if (lower_shift >= UINT32_C(64) || upper_shift >= UINT32_C(64) ||
      lower_significand > (UINT64_MAX >> lower_shift) ||
      upper_significand > (UINT64_MAX >> upper_shift)) {
    return 0;
  }
  lower_scaled = lower_significand << lower_shift;
  upper_scaled = upper_significand << upper_shift;
  if (lower_scaled > UINT64_MAX - upper_scaled) {
    return 0;
  }
  sum = lower_scaled + upper_scaled;
  midpoint_power = common_power - INT32_C(1);
  if (midpoint_power >= INT32_C(0)) {
    const uint32_t shift = (uint32_t)midpoint_power;
    if (shift >= UINT32_C(64) || sum > (UINT64_MAX >> shift)) {
      return 0;
    }
    staged.numerator = sum << shift;
  } else {
    staged.numerator = sum;
    staged.denominator_shift = (uint32_t)(-midpoint_power);
  }
  normalize_dyadic(&staged);
  *output = staged;
  return 1;
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
    MalbolgeGuestMathSpecialResult invalid;
    invalid.status = MALBOLGE_GUEST_MATH_SPECIAL_INVALID;
    invalid.bits = UINT64_C(0);
    return invalid;
  }
  if (is_nan(bits) || is_infinity(bits)) {
    return resolved(BINARY64_CANONICAL_NAN);
  }
  if (operation == MALBOLGE_GUEST_MATH_SIN &&
      (bits & ~BINARY64_SIGN) <= BINARY64_SIN_SMALL_ANGLE_MAX) {
    return resolved(bits);
  }
  if (operation == MALBOLGE_GUEST_MATH_COS &&
      (bits & ~BINARY64_SIGN) <= BINARY64_COS_SMALL_ANGLE_MAX) {
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

static MalbolgeGuestMathSpecialResult small_ratio_atan2_special(
    uint64_t y_bits, uint64_t x_bits);

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
  if ((y_bits & ~BINARY64_SIGN) == (x_bits & ~BINARY64_SIGN)) {
    const uint64_t magnitude =
        (x_bits & BINARY64_SIGN) == UINT64_C(0)
            ? BINARY64_PI_OVER_FOUR
            : BINARY64_THREE_PI_OVER_FOUR;
    return resolved(with_sign(magnitude, y_bits));
  }
  return small_ratio_atan2_special(y_bits, x_bits);
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

static int valid_ratio_input(const MalbolgeGuestMathAtan2KernelInput *input) {
  const uint64_t significand_limit = BINARY64_HIDDEN_BIT << UINT32_C(1);

  return input != NULL &&
         input->numerator_significand >= BINARY64_HIDDEN_BIT &&
         input->numerator_significand < significand_limit &&
         input->denominator_significand >= BINARY64_HIDDEN_BIT &&
         input->denominator_significand < significand_limit &&
         input->exponent_delta >= BINARY64_RATIO_MIN_EXPONENT_DELTA &&
         input->exponent_delta <= INT32_C(0) &&
         (input->exponent_delta != INT32_C(0) ||
          input->numerator_significand <= input->denominator_significand) &&
         input->swapped <= UINT32_C(1) && input->y_negative <= UINT32_C(1) &&
         input->x_negative <= UINT32_C(1);
}

static uint32_t u64_bit_length_local(uint64_t value) {
  uint32_t bits = UINT32_C(0);
  while (value != UINT64_C(0)) {
    ++bits;
    value >>= UINT32_C(1);
  }
  return bits;
}

static uint32_t u64_trailing_zero_count(uint64_t value) {
  uint32_t count = UINT32_C(0);
  while (value != UINT64_C(0) && (value & UINT64_C(1)) == UINT64_C(0)) {
    ++count;
    value >>= UINT32_C(1);
  }
  return count;
}

static uint64_t u64_binary_gcd(uint64_t left, uint64_t right) {
  uint32_t common_shift = UINT32_C(0);
  if (left == UINT64_C(0)) {
    return right;
  }
  if (right == UINT64_C(0)) {
    return left;
  }
  common_shift = u64_trailing_zero_count(left | right);
  left >>= u64_trailing_zero_count(left);
  do {
    right >>= u64_trailing_zero_count(right);
    if (left > right) {
      const uint64_t temporary = left;
      left = right;
      right = temporary;
    }
    right -= left;
  } while (right != UINT64_C(0));
  return left << common_shift;
}

static int u64_divide_exact(uint64_t dividend, uint64_t divisor,
                            uint64_t *quotient) {
  uint64_t staged = UINT64_C(0);
  uint64_t remainder = UINT64_C(0);
  uint32_t bit = UINT32_C(64);
  if (divisor == UINT64_C(0) || quotient == NULL) {
    return 0;
  }
  while (bit != UINT32_C(0)) {
    --bit;
    remainder = (remainder << UINT32_C(1)) |
                ((dividend >> bit) & UINT64_C(1));
    if (remainder >= divisor) {
      remainder -= divisor;
      staged |= UINT64_C(1) << bit;
    }
  }
  if (remainder != UINT64_C(0)) {
    return 0;
  }
  *quotient = staged;
  return 1;
}

int malbolge_guest_math_atan2_ratio_reduced_height(
    const MalbolgeGuestMathAtan2KernelInput *input,
    MalbolgeGuestMathRationalHeight *output) {
  MalbolgeGuestMathRationalHeight staged;
  uint64_t numerator = UINT64_C(0);
  uint64_t denominator = UINT64_C(0);
  uint64_t divisor = UINT64_C(0);
  int32_t exponent = INT32_C(0);
  uint32_t cancellation = UINT32_C(0);
  uint32_t shift = UINT32_C(0);

  if (output == NULL || !valid_ratio_input(input)) {
    return 0;
  }
  if (input->swapped != UINT32_C(0)) {
    numerator = input->denominator_significand;
    denominator = input->numerator_significand;
    exponent = -input->exponent_delta;
  } else {
    numerator = input->numerator_significand;
    denominator = input->denominator_significand;
    exponent = input->exponent_delta;
  }
  divisor = u64_binary_gcd(numerator, denominator);
  if (divisor == UINT64_C(0)) {
    return 0;
  }
  if (!u64_divide_exact(numerator, divisor, &numerator) ||
      !u64_divide_exact(denominator, divisor, &denominator)) {
    return 0;
  }
  if (exponent >= INT32_C(0)) {
    shift = (uint32_t)exponent;
    cancellation = u64_trailing_zero_count(denominator);
    if (cancellation > shift) {
      cancellation = shift;
    }
    denominator >>= cancellation;
    shift -= cancellation;
    staged.numerator_bits = u64_bit_length_local(numerator) + shift;
    staged.denominator_bits = u64_bit_length_local(denominator);
  } else {
    shift = (uint32_t)(-exponent);
    cancellation = u64_trailing_zero_count(numerator);
    if (cancellation > shift) {
      cancellation = shift;
    }
    numerator >>= cancellation;
    shift -= cancellation;
    staged.numerator_bits = u64_bit_length_local(numerator);
    staged.denominator_bits = u64_bit_length_local(denominator) + shift;
  }
  staged.height_bits = staged.numerator_bits > staged.denominator_bits
                           ? staged.numerator_bits
                           : staged.denominator_bits;
  output->numerator_bits = staged.numerator_bits;
  output->denominator_bits = staged.denominator_bits;
  output->height_bits = staged.height_bits;
  return 1;
}

static uint32_t ratio_fraction_bit(uint64_t denominator, uint64_t *remainder) {
  *remainder <<= UINT32_C(1);
  if (*remainder >= denominator) {
    *remainder -= denominator;
    return UINT32_C(1);
  }
  return UINT32_C(0);
}

static uint64_t rounded_normal_ratio(uint64_t denominator, uint64_t remainder,
                                     int32_t *exponent, uint32_t *exact) {
  uint64_t significand = BINARY64_HIDDEN_BIT;
  uint32_t remaining = BINARY64_EXPONENT_SHIFT;
  uint32_t guard = UINT32_C(0);

  while (remaining != UINT32_C(0)) {
    --remaining;
    significand |= (uint64_t)ratio_fraction_bit(denominator, &remainder)
                   << remaining;
  }
  *exact = remainder == UINT64_C(0) ? UINT32_C(1) : UINT32_C(0);
  guard = ratio_fraction_bit(denominator, &remainder);
  if (guard != UINT32_C(0) &&
      (remainder != UINT64_C(0) ||
       (significand & UINT64_C(1)) != UINT64_C(0))) {
    ++significand;
  }
  if (significand == (BINARY64_HIDDEN_BIT << UINT32_C(1))) {
    significand = BINARY64_HIDDEN_BIT;
    ++(*exponent);
  }
  return significand;
}

static uint64_t rounded_subnormal_ratio(uint64_t denominator,
                                        uint64_t remainder, int32_t exponent,
                                        uint32_t *exact) {
  const int32_t scale = exponent + INT32_C(1074);
  uint64_t units = UINT64_C(0);
  uint32_t remaining = UINT32_C(0);
  uint32_t guard = UINT32_C(0);

  if (scale <= INT32_C(-2)) {
    *exact = UINT32_C(0);
    return UINT64_C(0);
  }
  if (scale == INT32_C(-1)) {
    *exact = UINT32_C(0);
    return remainder == UINT64_C(0) ? UINT64_C(0) : UINT64_C(1);
  }
  units = UINT64_C(1) << (uint32_t)scale;
  remaining = (uint32_t)scale;
  while (remaining != UINT32_C(0)) {
    --remaining;
    units |= (uint64_t)ratio_fraction_bit(denominator, &remainder) << remaining;
  }
  *exact = remainder == UINT64_C(0) ? UINT32_C(1) : UINT32_C(0);
  guard = ratio_fraction_bit(denominator, &remainder);
  if (guard != UINT32_C(0) &&
      (remainder != UINT64_C(0) || (units & UINT64_C(1)) != UINT64_C(0))) {
    ++units;
  }
  return units;
}

static int ratio_nearest_binary64_internal(
    const MalbolgeGuestMathAtan2KernelInput *input, uint64_t *output_bits,
    uint32_t *exact) {
  uint64_t numerator = UINT64_C(0);
  uint64_t denominator = UINT64_C(0);
  uint64_t remainder = UINT64_C(0);
  uint64_t significand = UINT64_C(0);
  int32_t exponent = INT32_C(0);

  if (output_bits == NULL || exact == NULL || !valid_ratio_input(input)) {
    return 0;
  }
  numerator = input->numerator_significand;
  denominator = input->denominator_significand;
  exponent = input->exponent_delta;
  if (numerator >= denominator) {
    remainder = numerator - denominator;
  } else {
    numerator <<= UINT32_C(1);
    remainder = numerator - denominator;
    --exponent;
  }
  if (exponent < INT32_C(-1022)) {
    *output_bits =
        rounded_subnormal_ratio(denominator, remainder, exponent, exact);
    return 1;
  }
  significand =
      rounded_normal_ratio(denominator, remainder, &exponent, exact);
  *output_bits = ((uint64_t)(exponent + BINARY64_EXPONENT_BIAS)
                  << BINARY64_EXPONENT_SHIFT) |
                 (significand - BINARY64_HIDDEN_BIT);
  return 1;
}

int malbolge_guest_math_atan2_reconstruction(
    uint64_t y_bits, uint64_t x_bits,
    MalbolgeGuestMathAtan2Reconstruction *output) {
  MalbolgeGuestMathAtan2KernelInput ratio;
  MalbolgeGuestMathAtan2Base base;
  MalbolgeGuestMathAtan2RatioOperation ratio_operation;

  if (output == NULL ||
      !malbolge_guest_math_atan2_kernel_input(y_bits, x_bits, &ratio)) {
    return 0;
  }
  if (ratio.x_negative == UINT32_C(0)) {
    if (ratio.swapped == UINT32_C(0)) {
      base = MALBOLGE_GUEST_MATH_ATAN2_BASE_ZERO;
      ratio_operation = MALBOLGE_GUEST_MATH_ATAN2_RATIO_ADD;
    } else {
      base = MALBOLGE_GUEST_MATH_ATAN2_BASE_HALF_PI;
      ratio_operation = MALBOLGE_GUEST_MATH_ATAN2_RATIO_SUBTRACT;
    }
  } else if (ratio.swapped == UINT32_C(0)) {
    base = MALBOLGE_GUEST_MATH_ATAN2_BASE_PI;
    ratio_operation = MALBOLGE_GUEST_MATH_ATAN2_RATIO_SUBTRACT;
  } else {
    base = MALBOLGE_GUEST_MATH_ATAN2_BASE_HALF_PI;
    ratio_operation = MALBOLGE_GUEST_MATH_ATAN2_RATIO_ADD;
  }

  output->ratio.numerator_significand = ratio.numerator_significand;
  output->ratio.denominator_significand = ratio.denominator_significand;
  output->ratio.exponent_delta = ratio.exponent_delta;
  output->ratio.swapped = ratio.swapped;
  output->ratio.y_negative = ratio.y_negative;
  output->ratio.x_negative = ratio.x_negative;
  output->base = base;
  output->ratio_operation = ratio_operation;
  output->negative = ratio.y_negative;
  return 1;
}

static int ratio_at_least_atan_quarter_cut(
    const MalbolgeGuestMathAtan2KernelInput *input) {
  uint64_t scaled_denominator = input->denominator_significand;
  uint32_t shift = UINT32_C(0);

  if (input->exponent_delta == INT32_C(-1)) {
    shift = UINT32_C(1);
  } else if (input->exponent_delta == INT32_C(-2)) {
    shift = UINT32_C(2);
  } else if (input->exponent_delta != INT32_C(0)) {
    return 0;
  }
  scaled_denominator <<= shift;
  return input->numerator_significand * ATAN_QUARTER_REDUCTION_DENOMINATOR >=
         scaled_denominator * ATAN_QUARTER_REDUCTION_NUMERATOR;
}

int malbolge_guest_math_atan_kernel_reduction(
    const MalbolgeGuestMathAtan2KernelInput *input,
    MalbolgeGuestMathAtanKernelReduction *output) {
  MalbolgeGuestMathExactRatio residual;
  MalbolgeGuestMathAtanBase base;
  MalbolgeGuestMathAtan2RatioOperation ratio_operation;
  uint64_t scaled_denominator = UINT64_C(0);
  uint32_t shift = UINT32_C(0);

  if (output == NULL || !valid_ratio_input(input)) {
    return 0;
  }
  if (!ratio_at_least_atan_quarter_cut(input)) {
    residual.numerator = input->numerator_significand;
    residual.denominator = input->denominator_significand;
    residual.exponent_delta = input->exponent_delta;
    base = MALBOLGE_GUEST_MATH_ATAN_BASE_ZERO;
    ratio_operation = MALBOLGE_GUEST_MATH_ATAN2_RATIO_ADD;
  } else {
    if (input->exponent_delta == INT32_C(-1)) {
      shift = UINT32_C(1);
    } else if (input->exponent_delta == INT32_C(-2)) {
      shift = UINT32_C(2);
    } else if (input->exponent_delta != INT32_C(0)) {
      return 0;
    }
    scaled_denominator = input->denominator_significand << shift;
    residual.numerator = scaled_denominator - input->numerator_significand;
    residual.denominator = scaled_denominator + input->numerator_significand;
    residual.exponent_delta = INT32_C(0);
    base = MALBOLGE_GUEST_MATH_ATAN_BASE_QUARTER_PI;
    ratio_operation = MALBOLGE_GUEST_MATH_ATAN2_RATIO_SUBTRACT;
  }
  output->residual.numerator = residual.numerator;
  output->residual.denominator = residual.denominator;
  output->residual.exponent_delta = residual.exponent_delta;
  output->base = base;
  output->ratio_operation = ratio_operation;
  return 1;
}

static uint32_t reconstruction_base_quarters(MalbolgeGuestMathAtan2Base base) {
  if (base == MALBOLGE_GUEST_MATH_ATAN2_BASE_HALF_PI) {
    return UINT32_C(2);
  }
  if (base == MALBOLGE_GUEST_MATH_ATAN2_BASE_PI) {
    return UINT32_C(4);
  }
  return UINT32_C(0);
}

int malbolge_guest_math_atan2_kernel_plan(
    uint64_t y_bits, uint64_t x_bits,
    MalbolgeGuestMathAtan2KernelPlan *output) {
  MalbolgeGuestMathAtan2Reconstruction reconstruction;
  MalbolgeGuestMathAtanKernelReduction reduction;
  uint32_t quarters = UINT32_C(0);
  MalbolgeGuestMathAtan2RatioOperation operation;

  if (output == NULL ||
      !malbolge_guest_math_atan2_reconstruction(y_bits, x_bits,
                                                &reconstruction) ||
      !malbolge_guest_math_atan_kernel_reduction(&reconstruction.ratio,
                                                 &reduction)) {
    return 0;
  }
  quarters = reconstruction_base_quarters(reconstruction.base);
  operation = reconstruction.ratio_operation;
  if (reduction.base == MALBOLGE_GUEST_MATH_ATAN_BASE_QUARTER_PI) {
    if (operation == MALBOLGE_GUEST_MATH_ATAN2_RATIO_ADD) {
      ++quarters;
      operation = MALBOLGE_GUEST_MATH_ATAN2_RATIO_SUBTRACT;
    } else {
      --quarters;
      operation = MALBOLGE_GUEST_MATH_ATAN2_RATIO_ADD;
    }
  }

  output->residual.numerator = reduction.residual.numerator;
  output->residual.denominator = reduction.residual.denominator;
  output->residual.exponent_delta = reduction.residual.exponent_delta;
  output->quarter_pi_base = (MalbolgeGuestMathAtan2QuarterPiBase)quarters;
  output->ratio_operation = operation;
  output->negative = reconstruction.negative;
  return 1;
}

static const uint32_t QUARTER_PI_LOWER_192[7] = {
    UINT32_C(0x8a67cc74), UINT32_C(0x29024e08), UINT32_C(0x80dc1cd1),
    UINT32_C(0xc4c6628b), UINT32_C(0x2168c234), UINT32_C(0xc90fdaa2),
    UINT32_C(0)};
static const uint32_t QUARTER_PI_UPPER_192[7] = {
    UINT32_C(0x8a67cc75), UINT32_C(0x29024e08), UINT32_C(0x80dc1cd1),
    UINT32_C(0xc4c6628b), UINT32_C(0x2168c234), UINT32_C(0xc90fdaa2),
    UINT32_C(0)};

static void copy_fixed_limbs(uint32_t *output, const uint32_t *source,
                             uint32_t limb_count) {
  uint32_t index = UINT32_C(0);
  while (index < limb_count) {
    output[index] = source[index];
    ++index;
  }
}

static void zero_fixed_limbs(uint32_t *value, uint32_t limb_count) {
  uint32_t index = UINT32_C(0);
  while (index < limb_count) {
    value[index] = UINT32_C(0);
    ++index;
  }
}

static void add_fixed_limbs(uint32_t *value, const uint32_t *addend,
                            uint32_t limb_count) {
  uint32_t index = UINT32_C(0);
  uint32_t carry = UINT32_C(0);

  while (index < limb_count) {
    const uint64_t sum = (uint64_t)value[index] + (uint64_t)addend[index] +
                         (uint64_t)carry;
    value[index] = (uint32_t)sum;
    carry = (uint32_t)(sum >> UINT32_C(32));
    ++index;
  }
}

static void copy_fixed_192(MalbolgeGuestMathFixed192 *output,
                           const uint32_t source[7]) {
  copy_fixed_limbs(output->limbs, source, FIXED_192_LIMB_COUNT);
}

static void zero_fixed_192(MalbolgeGuestMathFixed192 *value) {
  zero_fixed_limbs(value->limbs, FIXED_192_LIMB_COUNT);
}

static void add_fixed_192(MalbolgeGuestMathFixed192 *value,
                          const MalbolgeGuestMathFixed192 *addend) {
  add_fixed_limbs(value->limbs, addend->limbs, FIXED_192_LIMB_COUNT);
}

int malbolge_guest_math_quarter_pi_interval(
    MalbolgeGuestMathFixed192Interval *output) {
  if (output == NULL) {
    return 0;
  }
  copy_fixed_192(&output->lower, QUARTER_PI_LOWER_192);
  copy_fixed_192(&output->upper, QUARTER_PI_UPPER_192);
  return 1;
}

int malbolge_guest_math_atan2_base_interval(
    MalbolgeGuestMathAtan2QuarterPiBase base,
    MalbolgeGuestMathFixed192Interval *output) {
  MalbolgeGuestMathFixed192Interval quarter;
  MalbolgeGuestMathFixed192Interval staged;
  uint32_t remaining = (uint32_t)base;

  if (output == NULL || remaining > UINT32_C(4) ||
      !malbolge_guest_math_quarter_pi_interval(&quarter)) {
    return 0;
  }
  zero_fixed_192(&staged.lower);
  zero_fixed_192(&staged.upper);
  while (remaining != UINT32_C(0)) {
    add_fixed_192(&staged.lower, &quarter.lower);
    add_fixed_192(&staged.upper, &quarter.upper);
    --remaining;
  }
  copy_fixed_192(&output->lower, staged.lower.limbs);
  copy_fixed_192(&output->upper, staged.upper.limbs);
  return 1;
}

static void increment_fixed_limbs(uint32_t *value, uint32_t limb_count) {
  uint32_t index = UINT32_C(0);
  uint32_t carry = UINT32_C(1);
  while (index < limb_count && carry != UINT32_C(0)) {
    const uint32_t previous = value[index];
    value[index] = previous + UINT32_C(1);
    carry = value[index] == UINT32_C(0) ? UINT32_C(1) : UINT32_C(0);
    ++index;
  }
}

static void shift_fixed_limbs_bit(uint32_t *value, uint32_t limb_count,
                                  uint32_t bit) {
  uint32_t index = UINT32_C(0);
  uint32_t carry = bit;
  while (index < limb_count) {
    const uint32_t next = value[index] >> UINT32_C(31);
    value[index] = (value[index] << UINT32_C(1)) | carry;
    carry = next;
    ++index;
  }
}

static void increment_fixed_192(MalbolgeGuestMathFixed192 *value) {
  increment_fixed_limbs(value->limbs, FIXED_192_LIMB_COUNT);
}

static void shift_fixed_192_bit(MalbolgeGuestMathFixed192 *value,
                                uint32_t bit) {
  shift_fixed_limbs_bit(value->limbs, FIXED_192_LIMB_COUNT, bit);
}

static uint32_t divide_stream_bit(uint64_t denominator, uint64_t *remainder,
                                  uint32_t bit) {
  *remainder = (*remainder << UINT32_C(1)) | (uint64_t)bit;
  if (*remainder >= denominator) {
    *remainder -= denominator;
    return UINT32_C(1);
  }
  return UINT32_C(0);
}

static int valid_fixed_residual(const MalbolgeGuestMathExactRatio *input) {
  if (input == NULL || input->denominator == UINT64_C(0) ||
      input->denominator >= EXACT_RATIO_COMPONENT_LIMIT ||
      input->numerator >= EXACT_RATIO_COMPONENT_LIMIT ||
      input->exponent_delta > INT32_C(0) ||
      input->exponent_delta < BINARY64_RATIO_MIN_EXPONENT_DELTA) {
    return 0;
  }
  if (input->numerator == UINT64_C(0)) {
    return 1;
  }
  if (input->exponent_delta == INT32_C(0)) {
    return input->numerator < input->denominator;
  }
  return input->numerator >= BINARY64_HIDDEN_BIT &&
         input->numerator < (BINARY64_HIDDEN_BIT << UINT32_C(1)) &&
         input->denominator >= BINARY64_HIDDEN_BIT &&
         input->denominator < (BINARY64_HIDDEN_BIT << UINT32_C(1));
}

int malbolge_guest_math_exact_ratio_interval(
    const MalbolgeGuestMathExactRatio *input,
    MalbolgeGuestMathFixed192Interval *output) {
  MalbolgeGuestMathFixed192 lower;
  MalbolgeGuestMathFixed192 upper;
  uint64_t remainder = UINT64_C(0);
  int32_t shift = INT32_C(0);
  uint32_t bit_index = UINT32_C(64);
  uint32_t trailing = UINT32_C(0);

  if (output == NULL || !valid_fixed_residual(input)) {
    return 0;
  }
  zero_fixed_192(&lower);
  zero_fixed_192(&upper);
  if (input->numerator == UINT64_C(0)) {
    copy_fixed_192(&output->lower, lower.limbs);
    copy_fixed_192(&output->upper, upper.limbs);
    return 1;
  }
  shift = input->exponent_delta + FIXED_192_FRACTION_BITS;
  if (shift < INT32_C(0)) {
    increment_fixed_192(&upper);
    copy_fixed_192(&output->lower, lower.limbs);
    copy_fixed_192(&output->upper, upper.limbs);
    return 1;
  }
  while (bit_index != UINT32_C(0)) {
    uint32_t quotient_bit = UINT32_C(0);
    --bit_index;
    quotient_bit = divide_stream_bit(
        input->denominator, &remainder,
        (uint32_t)((input->numerator >> bit_index) & UINT64_C(1)));
    shift_fixed_192_bit(&lower, quotient_bit);
  }
  trailing = (uint32_t)shift;
  while (trailing != UINT32_C(0)) {
    const uint32_t quotient_bit =
        divide_stream_bit(input->denominator, &remainder, UINT32_C(0));
    shift_fixed_192_bit(&lower, quotient_bit);
    --trailing;
  }
  copy_fixed_192(&upper, lower.limbs);
  if (remainder != UINT64_C(0)) {
    increment_fixed_192(&upper);
  }
  copy_fixed_192(&output->lower, lower.limbs);
  copy_fixed_192(&output->upper, upper.limbs);
  return 1;
}

static const uint32_t ATAN_CUT_UPPER_192[7] = {
    UINT32_C(0x0a0a0a0b), UINT32_C(0x0a0a0a0a), UINT32_C(0x0a0a0a0a),
    UINT32_C(0x0a0a0a0a), UINT32_C(0x0a0a0a0a), UINT32_C(0x6a0a0a0a),
    UINT32_C(0)};

static int fixed_limbs_is_zero(const uint32_t *value, uint32_t limb_count) {
  uint32_t index = UINT32_C(0);
  while (index < limb_count) {
    if (value[index] != UINT32_C(0)) {
      return 0;
    }
    ++index;
  }
  return 1;
}

static int fixed_192_is_zero(const MalbolgeGuestMathFixed192 *value) {
  return fixed_limbs_is_zero(value->limbs, FIXED_192_LIMB_COUNT);
}

static int fixed_192_below_two_neg64(
    const MalbolgeGuestMathFixed192 *value) {
  return value->limbs[4] == UINT32_C(0) &&
         value->limbs[5] == UINT32_C(0) &&
         value->limbs[6] == UINT32_C(0);
}

static void decrement_fixed_limbs(uint32_t *value, uint32_t limb_count) {
  uint32_t index = UINT32_C(0);
  uint32_t borrow = UINT32_C(1);
  while (index < limb_count && borrow != UINT32_C(0)) {
    const uint32_t previous = value[index];
    value[index] = previous - UINT32_C(1);
    borrow = previous == UINT32_C(0) ? UINT32_C(1) : UINT32_C(0);
    ++index;
  }
}

static int compare_fixed_limbs(const uint32_t *left, const uint32_t *right,
                               uint32_t limb_count) {
  uint32_t index = limb_count;
  while (index != UINT32_C(0)) {
    --index;
    if (left[index] < right[index]) {
      return -1;
    }
    if (left[index] > right[index]) {
      return 1;
    }
  }
  return 0;
}

static int subtract_fixed_limbs(uint32_t *output, const uint32_t *left,
                                const uint32_t *right, uint32_t limb_count) {
  uint32_t index = UINT32_C(0);
  uint32_t borrow = UINT32_C(0);

  if (compare_fixed_limbs(left, right, limb_count) < 0) {
    return 0;
  }
  while (index < limb_count) {
    const uint64_t subtrahend = (uint64_t)right[index] + borrow;
    const uint64_t minuend = left[index];
    output[index] = (uint32_t)(minuend - subtrahend);
    borrow = minuend < subtrahend ? UINT32_C(1) : UINT32_C(0);
    ++index;
  }
  return 1;
}

static int add_fixed_limbs_fits(const uint32_t *left, const uint32_t *right,
                                uint32_t limb_count) {
  uint32_t index = UINT32_C(0);
  uint64_t carry = UINT64_C(0);
  while (index < limb_count) {
    const uint64_t sum = (uint64_t)left[index] + (uint64_t)right[index] + carry;
    carry = sum >> UINT32_C(32);
    ++index;
  }
  return carry == UINT64_C(0);
}

static void add_fixed_limbs_unchecked(uint32_t *output, const uint32_t *left,
                                      const uint32_t *right,
                                      uint32_t limb_count) {
  uint32_t index = UINT32_C(0);
  uint64_t carry = UINT64_C(0);
  while (index < limb_count) {
    const uint64_t sum = (uint64_t)left[index] + (uint64_t)right[index] + carry;
    output[index] = (uint32_t)sum;
    carry = sum >> UINT32_C(32);
    ++index;
  }
}

static int add_fixed_limbs_checked(uint32_t *output, const uint32_t *left,
                                   const uint32_t *right,
                                   uint32_t limb_count) {
  if (output == NULL || left == NULL || right == NULL ||
      limb_count == UINT32_C(0) ||
      !add_fixed_limbs_fits(left, right, limb_count)) {
    return 0;
  }
  add_fixed_limbs_unchecked(output, left, right, limb_count);
  return 1;
}

int malbolge_guest_math_fixed_add(
    const uint32_t *left, const uint32_t *right, uint32_t limb_count,
    uint32_t *output) {
  return add_fixed_limbs_checked(output, left, right, limb_count);
}

int malbolge_guest_math_fixed_subtract(
    const uint32_t *left, const uint32_t *right, uint32_t limb_count,
    uint32_t *output) {
  if (output == NULL || left == NULL || right == NULL ||
      limb_count == UINT32_C(0)) {
    return 0;
  }
  return subtract_fixed_limbs(output, left, right, limb_count);
}

static int compare_signed_fixed_limbs(
    const uint32_t *left, uint32_t left_negative, const uint32_t *right,
    uint32_t right_negative, uint32_t limb_count) {
  const uint32_t left_is_zero =
      fixed_limbs_is_zero(left, limb_count) ? UINT32_C(1) : UINT32_C(0);
  const uint32_t right_is_zero =
      fixed_limbs_is_zero(right, limb_count) ? UINT32_C(1) : UINT32_C(0);
  const uint32_t left_sign =
      left_is_zero != UINT32_C(0) ? UINT32_C(0) : left_negative;
  const uint32_t right_sign =
      right_is_zero != UINT32_C(0) ? UINT32_C(0) : right_negative;
  const int magnitude = compare_fixed_limbs(left, right, limb_count);

  if (left_sign != right_sign) {
    return left_sign != UINT32_C(0) ? -1 : 1;
  }
  return left_sign != UINT32_C(0) ? -magnitude : magnitude;
}

int malbolge_guest_math_fixed_signed_add(
    const uint32_t *left, uint32_t left_negative, const uint32_t *right,
    uint32_t right_negative, uint32_t limb_count, uint32_t *output,
    uint32_t *output_negative) {
  int comparison = 0;
  uint32_t result_negative = UINT32_C(0);

  if (left == NULL || right == NULL || output == NULL ||
      output_negative == NULL || limb_count == UINT32_C(0) ||
      left_negative > UINT32_C(1) || right_negative > UINT32_C(1)) {
    return 0;
  }
  if (left_negative == right_negative) {
    if (!add_fixed_limbs_checked(output, left, right, limb_count)) {
      return 0;
    }
    result_negative = left_negative;
  } else {
    comparison = compare_fixed_limbs(left, right, limb_count);
    if (comparison == 0) {
      zero_fixed_limbs(output, limb_count);
      result_negative = UINT32_C(0);
    } else if (comparison > 0) {
      (void)subtract_fixed_limbs(output, left, right, limb_count);
      result_negative = left_negative;
    } else {
      (void)subtract_fixed_limbs(output, right, left, limb_count);
      result_negative = right_negative;
    }
  }
  if (fixed_limbs_is_zero(output, limb_count)) {
    result_negative = UINT32_C(0);
  }
  *output_negative = result_negative;
  return 1;
}

int malbolge_guest_math_fixed_signed_interval_add(
    const uint32_t *left_lower, uint32_t left_lower_negative,
    const uint32_t *left_upper, uint32_t left_upper_negative,
    const uint32_t *right_lower, uint32_t right_lower_negative,
    const uint32_t *right_upper, uint32_t right_upper_negative,
    uint32_t limb_count, uint32_t *output_lower,
    uint32_t *output_lower_negative, uint32_t *output_upper,
    uint32_t *output_upper_negative, uint32_t *scratch,
    uint32_t scratch_capacity) {
  uint32_t lower_negative = UINT32_C(0);
  uint32_t upper_negative = UINT32_C(0);
  uint32_t *lower = scratch;
  uint32_t *upper = NULL;

  if (left_lower == NULL || left_upper == NULL || right_lower == NULL ||
      right_upper == NULL || output_lower == NULL ||
      output_lower_negative == NULL || output_upper == NULL ||
      output_upper_negative == NULL || scratch == NULL ||
      limb_count == UINT32_C(0) || limb_count > UINT32_MAX / UINT32_C(2) ||
      left_lower_negative > UINT32_C(1) ||
      left_upper_negative > UINT32_C(1) ||
      right_lower_negative > UINT32_C(1) ||
      right_upper_negative > UINT32_C(1) ||
      scratch_capacity < limb_count * UINT32_C(2) ||
      compare_signed_fixed_limbs(left_lower, left_lower_negative, left_upper,
                                 left_upper_negative, limb_count) > 0 ||
      compare_signed_fixed_limbs(right_lower, right_lower_negative, right_upper,
                                 right_upper_negative, limb_count) > 0) {
    return 0;
  }
  upper = lower + limb_count;
  if (!malbolge_guest_math_fixed_signed_add(
          left_lower, left_lower_negative, right_lower, right_lower_negative,
          limb_count, lower, &lower_negative) ||
      !malbolge_guest_math_fixed_signed_add(
          left_upper, left_upper_negative, right_upper, right_upper_negative,
          limb_count, upper, &upper_negative) ||
      compare_signed_fixed_limbs(lower, lower_negative, upper, upper_negative,
                                 limb_count) > 0) {
    return 0;
  }
  copy_fixed_limbs(output_lower, lower, limb_count);
  copy_fixed_limbs(output_upper, upper, limb_count);
  *output_lower_negative = lower_negative;
  *output_upper_negative = upper_negative;
  return 1;
}

static int fixed_limbs_below_small_integer(
    const uint32_t *value, uint32_t limb_count, uint32_t fraction_limbs,
    uint32_t limit) {
  uint32_t index = fraction_limbs + UINT32_C(1);
  if (fraction_limbs >= limb_count) {
    return 0;
  }
  while (index < limb_count) {
    if (value[index] != UINT32_C(0)) {
      return 0;
    }
    ++index;
  }
  return value[fraction_limbs] < limit;
}

static int taylor_recurrence_factors(
    uint32_t term_index, uint32_t cosine, uint32_t *left_factor,
    uint32_t *right_factor) {
  uint64_t left = UINT64_C(0);
  uint64_t right = UINT64_C(0);
  if (term_index == UINT32_C(0) || cosine > UINT32_C(1) ||
      left_factor == NULL || right_factor == NULL) {
    return 0;
  }
  if (cosine != UINT32_C(0)) {
    left = (uint64_t)term_index * UINT64_C(2) - UINT64_C(1);
    right = (uint64_t)term_index * UINT64_C(2);
  } else {
    left = (uint64_t)term_index * UINT64_C(2);
    right = left + UINT64_C(1);
  }
  if (left > UINT32_MAX || right > UINT32_MAX) {
    return 0;
  }
  *left_factor = (uint32_t)left;
  *right_factor = (uint32_t)right;
  return 1;
}

static int fixed_taylor_recurrence_interval(
    const uint32_t *term_lower, const uint32_t *term_upper,
    const uint32_t *square_lower, const uint32_t *square_upper,
    uint32_t limb_count, uint32_t fraction_limbs, uint32_t left_factor,
    uint32_t right_factor, uint32_t *output_lower, uint32_t *output_upper,
    uint32_t *scratch, uint32_t scratch_capacity) {
  uint32_t *operation = scratch;
  uint32_t *product_lower = NULL;
  uint32_t *product_upper = NULL;

  if (scratch == NULL || limb_count == UINT32_C(0) ||
      limb_count > UINT32_MAX / UINT32_C(4) ||
      scratch_capacity < limb_count * UINT32_C(4)) {
    return 0;
  }
  product_lower = operation + limb_count * UINT32_C(2);
  product_upper = product_lower + limb_count;
  if (!malbolge_guest_math_fixed_interval_multiply(
          term_lower, term_upper, square_lower, square_upper, limb_count,
          fraction_limbs, product_lower, product_upper, operation,
          limb_count * UINT32_C(4)) ||
      !malbolge_guest_math_fixed_interval_divide_small(
          product_lower, product_upper, limb_count, left_factor, product_lower,
          product_upper, operation, limb_count * UINT32_C(2)) ||
      !malbolge_guest_math_fixed_interval_divide_small(
          product_lower, product_upper, limb_count, right_factor, output_lower,
          output_upper, operation, limb_count * UINT32_C(2))) {
    return 0;
  }
  return 1;
}

static int fixed_taylor_series_interval(
    const uint32_t *input_lower, const uint32_t *input_upper,
    uint32_t limb_count, uint32_t fraction_limbs, uint32_t terms,
    uint32_t cosine, uint32_t *output_lower, uint32_t *output_lower_negative,
    uint32_t *output_upper, uint32_t *output_upper_negative,
    uint32_t *scratch, uint32_t scratch_capacity) {
  uint32_t index = UINT32_C(0);
  uint32_t left_factor = UINT32_C(0);
  uint32_t right_factor = UINT32_C(0);
  uint32_t sum_lower_negative = UINT32_C(0);
  uint32_t sum_upper_negative = UINT32_C(0);
  uint32_t *square_lower = scratch;
  uint32_t *square_upper = NULL;
  uint32_t *term_lower = NULL;
  uint32_t *term_upper = NULL;
  uint32_t *sum_lower = NULL;
  uint32_t *sum_upper = NULL;
  uint32_t *operation = NULL;

  if (input_lower == NULL || input_upper == NULL || output_lower == NULL ||
      output_lower_negative == NULL || output_upper == NULL ||
      output_upper_negative == NULL || scratch == NULL ||
      limb_count == UINT32_C(0) || limb_count > UINT32_MAX / UINT32_C(10) ||
      fraction_limbs >= limb_count || terms < UINT32_C(2) ||
      cosine > UINT32_C(1) || scratch_capacity < limb_count * UINT32_C(10) ||
      compare_fixed_limbs(input_lower, input_upper, limb_count) > 0 ||
      !fixed_limbs_below_small_integer(input_upper, limb_count, fraction_limbs,
                                       UINT32_C(4))) {
    return 0;
  }
  square_upper = square_lower + limb_count;
  term_lower = square_upper + limb_count;
  term_upper = term_lower + limb_count;
  sum_lower = term_upper + limb_count;
  sum_upper = sum_lower + limb_count;
  operation = sum_upper + limb_count;

  if (!malbolge_guest_math_fixed_interval_multiply(
          input_lower, input_upper, input_lower, input_upper, limb_count,
          fraction_limbs, square_lower, square_upper, operation,
          limb_count * UINT32_C(4))) {
    return 0;
  }
  if (cosine != UINT32_C(0)) {
    zero_fixed_limbs(term_lower, limb_count);
    zero_fixed_limbs(term_upper, limb_count);
    term_lower[fraction_limbs] = UINT32_C(1);
    term_upper[fraction_limbs] = UINT32_C(1);
  } else {
    copy_fixed_limbs(term_lower, input_lower, limb_count);
    copy_fixed_limbs(term_upper, input_upper, limb_count);
  }
  copy_fixed_limbs(sum_lower, term_lower, limb_count);
  copy_fixed_limbs(sum_upper, term_upper, limb_count);

  index = UINT32_C(1);
  while (index < terms) {
    const uint32_t negative = index & UINT32_C(1);
    const uint32_t *add_lower = term_lower;
    const uint32_t *add_upper = term_upper;
    uint32_t add_lower_negative = negative;
    uint32_t add_upper_negative = negative;
    if (!taylor_recurrence_factors(index, cosine, &left_factor,
                                    &right_factor) ||
        !fixed_taylor_recurrence_interval(
            term_lower, term_upper, square_lower, square_upper, limb_count,
            fraction_limbs, left_factor, right_factor, term_lower, term_upper,
            operation, limb_count * UINT32_C(4))) {
      return 0;
    }
    if (negative != UINT32_C(0)) {
      add_lower = term_upper;
      add_upper = term_lower;
    }
    if (!malbolge_guest_math_fixed_signed_interval_add(
            sum_lower, sum_lower_negative, sum_upper, sum_upper_negative,
            add_lower, add_lower_negative, add_upper, add_upper_negative,
            limb_count, sum_lower, &sum_lower_negative, sum_upper,
            &sum_upper_negative, operation, limb_count * UINT32_C(2))) {
      return 0;
    }
    ++index;
  }

  if (!taylor_recurrence_factors(terms, cosine, &left_factor,
                                  &right_factor) ||
      !fixed_taylor_recurrence_interval(
          term_lower, term_upper, square_lower, square_upper, limb_count,
          fraction_limbs, left_factor, right_factor, term_lower, term_upper,
          operation, limb_count * UINT32_C(4))) {
    return 0;
  }
  zero_fixed_limbs(square_lower, limb_count);
  if ((terms & UINT32_C(1)) != UINT32_C(0)) {
    if (!malbolge_guest_math_fixed_signed_interval_add(
            sum_lower, sum_lower_negative, sum_upper, sum_upper_negative,
            term_upper, UINT32_C(1), square_lower, UINT32_C(0), limb_count,
            sum_lower, &sum_lower_negative, sum_upper, &sum_upper_negative,
            operation, limb_count * UINT32_C(2))) {
      return 0;
    }
  } else if (!malbolge_guest_math_fixed_signed_interval_add(
                 sum_lower, sum_lower_negative, sum_upper, sum_upper_negative,
                 square_lower, UINT32_C(0), term_upper, UINT32_C(0), limb_count,
                 sum_lower, &sum_lower_negative, sum_upper,
                 &sum_upper_negative, operation,
                 limb_count * UINT32_C(2))) {
    return 0;
  }
  copy_fixed_limbs(output_lower, sum_lower, limb_count);
  copy_fixed_limbs(output_upper, sum_upper, limb_count);
  *output_lower_negative = sum_lower_negative;
  *output_upper_negative = sum_upper_negative;
  return 1;
}

int malbolge_guest_math_fixed_sin_taylor_interval(
    const uint32_t *input_lower, const uint32_t *input_upper,
    uint32_t limb_count, uint32_t fraction_limbs, uint32_t terms,
    uint32_t *output_lower, uint32_t *output_lower_negative,
    uint32_t *output_upper, uint32_t *output_upper_negative,
    uint32_t *scratch, uint32_t scratch_capacity) {
  return fixed_taylor_series_interval(
      input_lower, input_upper, limb_count, fraction_limbs, terms,
      UINT32_C(0), output_lower, output_lower_negative, output_upper,
      output_upper_negative, scratch, scratch_capacity);
}

int malbolge_guest_math_fixed_cos_taylor_interval(
    const uint32_t *input_lower, const uint32_t *input_upper,
    uint32_t limb_count, uint32_t fraction_limbs, uint32_t terms,
    uint32_t *output_lower, uint32_t *output_lower_negative,
    uint32_t *output_upper, uint32_t *output_upper_negative,
    uint32_t *scratch, uint32_t scratch_capacity) {
  return fixed_taylor_series_interval(
      input_lower, input_upper, limb_count, fraction_limbs, terms,
      UINT32_C(1), output_lower, output_lower_negative, output_upper,
      output_upper_negative, scratch, scratch_capacity);
}

static int multiply_limbs_u64(
    const uint32_t *input, uint32_t input_limbs, uint64_t factor,
    uint32_t *output, uint32_t output_limbs) {
  const uint32_t factor_parts[2] = {(uint32_t)factor,
                                    (uint32_t)(factor >> UINT32_C(32))};
  uint32_t index = UINT32_C(0);
  uint32_t left_index = UINT32_C(0);

  if (input == NULL || output == NULL || input_limbs == UINT32_C(0) ||
      factor == UINT64_C(0) || output_limbs < input_limbs + UINT32_C(2)) {
    return 0;
  }
  zero_fixed_limbs(output, output_limbs);
  while (left_index < input_limbs) {
    uint32_t factor_index = UINT32_C(0);
    uint64_t carry = UINT64_C(0);
    while (factor_index < UINT32_C(2)) {
      const uint32_t cell_index = left_index + factor_index;
      const uint64_t cell =
          (uint64_t)input[left_index] * factor_parts[factor_index] +
          (uint64_t)output[cell_index] + carry;
      output[cell_index] = (uint32_t)cell;
      carry = cell >> UINT32_C(32);
      ++factor_index;
    }
    index = left_index + UINT32_C(2);
    while (carry != UINT64_C(0)) {
      const uint64_t cell = (uint64_t)output[index] + carry;
      output[index] = (uint32_t)cell;
      carry = cell >> UINT32_C(32);
      ++index;
    }
    ++left_index;
  }
  return 1;
}

static uint64_t fixed_limbs_bit_length_wide(const uint32_t *value,
                                            uint32_t limb_count) {
  uint32_t index = limb_count;
  while (index != UINT32_C(0)) {
    uint32_t limb = UINT32_C(0);
    uint32_t bits = UINT32_C(0);
    --index;
    limb = value[index];
    if (limb == UINT32_C(0)) {
      continue;
    }
    while (limb != UINT32_C(0)) {
      ++bits;
      limb >>= UINT32_C(1);
    }
    return (uint64_t)index * UINT64_C(32) + bits;
  }
  return UINT64_C(0);
}

static uint32_t shifted_fixed_limbs_bit(const uint32_t *value,
                                        uint32_t limb_count, uint32_t shift,
                                        uint64_t position) {
  uint64_t source = UINT64_C(0);
  if (position < shift) {
    return UINT32_C(0);
  }
  source = position - shift;
  if (source >= (uint64_t)limb_count * UINT64_C(32)) {
    return UINT32_C(0);
  }
  return (value[(uint32_t)(source >> UINT32_C(5))] >>
          (uint32_t)(source & UINT64_C(31))) &
         UINT32_C(1);
}

static int compare_shifted_fixed_limbs(
    const uint32_t *left, uint32_t left_limbs, uint32_t left_shift,
    const uint32_t *right, uint32_t right_limbs, uint32_t right_shift) {
  const uint64_t left_length =
      fixed_limbs_bit_length_wide(left, left_limbs) + left_shift;
  const uint64_t right_length =
      fixed_limbs_bit_length_wide(right, right_limbs) + right_shift;
  uint64_t position = left_length;

  if (left_length < right_length) {
    return -1;
  }
  if (left_length > right_length) {
    return 1;
  }
  while (position != UINT64_C(0)) {
    uint32_t left_bit = UINT32_C(0);
    uint32_t right_bit = UINT32_C(0);
    --position;
    left_bit = shifted_fixed_limbs_bit(left, left_limbs, left_shift, position);
    right_bit =
        shifted_fixed_limbs_bit(right, right_limbs, right_shift, position);
    if (left_bit < right_bit) {
      return -1;
    }
    if (left_bit > right_bit) {
      return 1;
    }
  }
  return 0;
}

static int positive_ratio_tangent_compare_internal(
    const MalbolgeGuestMathAtan2KernelInput *ratio,
    const uint32_t *sin_lower, const uint32_t *sin_upper,
    const uint32_t *cos_lower, const uint32_t *cos_upper,
    uint32_t limb_count, uint32_t require_positive_inputs,
    int32_t *comparison, uint32_t *scratch, uint32_t scratch_capacity) {
  uint64_t numerator = UINT64_C(0);
  uint64_t denominator = UINT64_C(0);
  int32_t exponent = INT32_C(0);
  uint32_t numerator_shift = UINT32_C(0);
  uint32_t denominator_shift = UINT32_C(0);
  uint32_t extended_limbs = UINT32_C(0);
  uint32_t *left = scratch;
  uint32_t *right = NULL;

  if (!valid_ratio_input(ratio) || sin_lower == NULL || sin_upper == NULL ||
      cos_lower == NULL || cos_upper == NULL || comparison == NULL ||
      scratch == NULL || limb_count == UINT32_C(0) ||
      require_positive_inputs > UINT32_C(1) ||
      (require_positive_inputs != UINT32_C(0) &&
       (ratio->y_negative != UINT32_C(0) ||
        ratio->x_negative != UINT32_C(0))) ||
      compare_fixed_limbs(sin_lower, sin_upper, limb_count) > 0 ||
      compare_fixed_limbs(cos_lower, cos_upper, limb_count) > 0 ||
      limb_count > (UINT32_MAX - UINT32_C(4)) / UINT32_C(2)) {
    return 0;
  }
  if (ratio->swapped != UINT32_C(0)) {
    numerator = ratio->denominator_significand;
    denominator = ratio->numerator_significand;
    exponent = -ratio->exponent_delta;
  } else {
    numerator = ratio->numerator_significand;
    denominator = ratio->denominator_significand;
    exponent = ratio->exponent_delta;
  }
  if (exponent < INT32_C(0)) {
    denominator_shift = (uint32_t)(-exponent);
  } else {
    numerator_shift = (uint32_t)exponent;
  }
  extended_limbs = limb_count + UINT32_C(2);
  if (scratch_capacity < extended_limbs * UINT32_C(2)) {
    return 0;
  }
  right = left + extended_limbs;
  *comparison = INT32_C(0);
  if (fixed_limbs_is_zero(sin_lower, limb_count) ||
      fixed_limbs_is_zero(cos_lower, limb_count)) {
    return 1;
  }
  if (!multiply_limbs_u64(cos_lower, limb_count, numerator, left,
                           extended_limbs) ||
      !multiply_limbs_u64(sin_upper, limb_count, denominator, right,
                           extended_limbs)) {
    return 0;
  }
  if (compare_shifted_fixed_limbs(left, extended_limbs, numerator_shift,
                                  right, extended_limbs,
                                  denominator_shift) > 0) {
    *comparison = INT32_C(1);
    return 1;
  }
  if (!multiply_limbs_u64(cos_upper, limb_count, numerator, left,
                           extended_limbs) ||
      !multiply_limbs_u64(sin_lower, limb_count, denominator, right,
                           extended_limbs)) {
    return 0;
  }
  if (compare_shifted_fixed_limbs(left, extended_limbs, numerator_shift,
                                  right, extended_limbs,
                                  denominator_shift) < 0) {
    *comparison = INT32_C(-1);
  }
  return 1;
}

int malbolge_guest_math_positive_ratio_tangent_compare(
    const MalbolgeGuestMathAtan2KernelInput *ratio,
    const uint32_t *sin_lower, const uint32_t *sin_upper,
    const uint32_t *cos_lower, const uint32_t *cos_upper,
    uint32_t limb_count, int32_t *comparison, uint32_t *scratch,
    uint32_t scratch_capacity) {
  return positive_ratio_tangent_compare_internal(
      ratio, sin_lower, sin_upper, cos_lower, cos_upper, limb_count,
      UINT32_C(1), comparison, scratch, scratch_capacity);
}

int malbolge_guest_math_positive_midpoint_compare(
    const MalbolgeGuestMathAtan2KernelInput *ratio,
    const MalbolgeGuestMathDyadic *midpoint, uint32_t fraction_limbs,
    uint32_t terms, int32_t *comparison, uint32_t *scratch,
    uint32_t scratch_capacity) {
  uint32_t fraction_bits = UINT32_C(0);
  uint32_t limb_count = UINT32_C(0);
  uint32_t sin_lower_negative = UINT32_C(0);
  uint32_t sin_upper_negative = UINT32_C(0);
  uint32_t cos_lower_negative = UINT32_C(0);
  uint32_t cos_upper_negative = UINT32_C(0);
  int32_t staged_comparison = INT32_C(0);
  uint32_t *input = scratch;
  uint32_t *sin_lower = NULL;
  uint32_t *sin_upper = NULL;
  uint32_t *cos_lower = NULL;
  uint32_t *cos_upper = NULL;
  uint32_t *operation = NULL;

  if (ratio == NULL || midpoint == NULL || comparison == NULL ||
      scratch == NULL ||
      midpoint->negative != UINT32_C(0) || midpoint->numerator == UINT64_C(0) ||
      fraction_limbs == UINT32_C(0) ||
      fraction_limbs > UINT32_MAX / UINT32_C(32) ||
      fraction_limbs == UINT32_MAX || !valid_ratio_input(ratio) ||
      ratio->y_negative != UINT32_C(0) || ratio->x_negative != UINT32_C(0)) {
    return 0;
  }
  fraction_bits = fraction_limbs * UINT32_C(32);
  limb_count = fraction_limbs + UINT32_C(1);
  if (limb_count > UINT32_MAX / UINT32_C(15) ||
      scratch_capacity < limb_count * UINT32_C(15)) {
    return 0;
  }
  if (fraction_bits < midpoint->denominator_shift) {
    *comparison = INT32_C(0);
    return 1;
  }
  sin_lower = input + limb_count;
  sin_upper = sin_lower + limb_count;
  cos_lower = sin_upper + limb_count;
  cos_upper = cos_lower + limb_count;
  operation = cos_upper + limb_count;
  zero_fixed_limbs(input, limb_count);
  if (!malbolge_guest_math_dyadic_write_fixed(midpoint, fraction_bits, input,
                                               limb_count) ||
      !malbolge_guest_math_fixed_sin_taylor_interval(
          input, input, limb_count, fraction_limbs, terms, sin_lower,
          &sin_lower_negative, sin_upper, &sin_upper_negative, operation,
          limb_count * UINT32_C(10)) ||
      !malbolge_guest_math_fixed_cos_taylor_interval(
          input, input, limb_count, fraction_limbs, terms, cos_lower,
          &cos_lower_negative, cos_upper, &cos_upper_negative, operation,
          limb_count * UINT32_C(10))) {
    return 0;
  }
  if (sin_lower_negative != UINT32_C(0) ||
      sin_upper_negative != UINT32_C(0) ||
      cos_lower_negative != UINT32_C(0) ||
      cos_upper_negative != UINT32_C(0)) {
    *comparison = INT32_C(0);
    return 1;
  }
  if (!malbolge_guest_math_positive_ratio_tangent_compare(
          ratio, sin_lower, sin_upper, cos_lower, cos_upper, limb_count,
          &staged_comparison, operation, limb_count * UINT32_C(10))) {
    return 0;
  }
  *comparison = staged_comparison;
  return 1;
}

static int signed_fixed_interval_proven_sign(
    const uint32_t *lower, uint32_t lower_negative, const uint32_t *upper,
    uint32_t upper_negative, uint32_t limb_count) {
  if (lower == NULL || upper == NULL || lower_negative > UINT32_C(1) ||
      upper_negative > UINT32_C(1) || limb_count == UINT32_C(0)) {
    return 0;
  }
  if (lower_negative == UINT32_C(0) &&
      !fixed_limbs_is_zero(lower, limb_count)) {
    return 1;
  }
  if (upper_negative != UINT32_C(0) &&
      !fixed_limbs_is_zero(upper, limb_count)) {
    return -1;
  }
  return 0;
}

static int signed_interval_magnitude_bounds(
    const uint32_t *lower, uint32_t lower_negative, const uint32_t *upper,
    uint32_t upper_negative, uint32_t limb_count,
    const uint32_t **magnitude_lower, const uint32_t **magnitude_upper);

int malbolge_guest_math_fixed_sincos_double_interval(
    const uint32_t *sin_lower, uint32_t sin_lower_negative,
    const uint32_t *sin_upper, uint32_t sin_upper_negative,
    const uint32_t *cos_lower, uint32_t cos_lower_negative,
    const uint32_t *cos_upper, uint32_t cos_upper_negative,
    uint32_t limb_count, uint32_t fraction_limbs, uint32_t *output_sin_lower,
    uint32_t *output_sin_lower_negative, uint32_t *output_sin_upper,
    uint32_t *output_sin_upper_negative, uint32_t *output_cos_lower,
    uint32_t *output_cos_lower_negative, uint32_t *output_cos_upper,
    uint32_t *output_cos_upper_negative, uint32_t *proven, uint32_t *scratch,
    uint32_t scratch_capacity) {
  const uint32_t *sin_magnitude_lower = NULL;
  const uint32_t *sin_magnitude_upper = NULL;
  const uint32_t *cos_magnitude_lower = NULL;
  const uint32_t *cos_magnitude_upper = NULL;
  int sin_sign = 0;
  int cos_sign = 0;
  uint32_t cos_lower_result_negative = UINT32_C(0);
  uint32_t cos_upper_result_negative = UINT32_C(0);
  uint32_t *sin_product_lower = scratch;
  uint32_t *sin_product_upper = NULL;
  uint32_t *cos_square_lower = NULL;
  uint32_t *cos_square_upper = NULL;
  uint32_t *sin_square_lower = NULL;
  uint32_t *sin_square_upper = NULL;
  uint32_t *cos_result_lower = NULL;
  uint32_t *cos_result_upper = NULL;
  uint32_t *operation = NULL;

  if (sin_lower == NULL || sin_upper == NULL || cos_lower == NULL ||
      cos_upper == NULL || output_sin_lower == NULL ||
      output_sin_lower_negative == NULL || output_sin_upper == NULL ||
      output_sin_upper_negative == NULL || output_cos_lower == NULL ||
      output_cos_lower_negative == NULL || output_cos_upper == NULL ||
      output_cos_upper_negative == NULL || proven == NULL || scratch == NULL ||
      limb_count == UINT32_C(0) || limb_count > UINT32_MAX / UINT32_C(12) ||
      fraction_limbs >= limb_count ||
      scratch_capacity < limb_count * UINT32_C(12) ||
      sin_lower_negative > UINT32_C(1) || sin_upper_negative > UINT32_C(1) ||
      cos_lower_negative > UINT32_C(1) || cos_upper_negative > UINT32_C(1) ||
      compare_signed_fixed_limbs(sin_lower, sin_lower_negative, sin_upper,
                                 sin_upper_negative, limb_count) > 0 ||
      compare_signed_fixed_limbs(cos_lower, cos_lower_negative, cos_upper,
                                 cos_upper_negative, limb_count) > 0) {
    return 0;
  }
  sin_sign = signed_interval_magnitude_bounds(
      sin_lower, sin_lower_negative, sin_upper, sin_upper_negative, limb_count,
      &sin_magnitude_lower, &sin_magnitude_upper);
  cos_sign = signed_interval_magnitude_bounds(
      cos_lower, cos_lower_negative, cos_upper, cos_upper_negative, limb_count,
      &cos_magnitude_lower, &cos_magnitude_upper);
  if (sin_sign == 0 || cos_sign == 0) {
    *proven = UINT32_C(0);
    return 1;
  }

  sin_product_upper = sin_product_lower + limb_count;
  cos_square_lower = sin_product_upper + limb_count;
  cos_square_upper = cos_square_lower + limb_count;
  sin_square_lower = cos_square_upper + limb_count;
  sin_square_upper = sin_square_lower + limb_count;
  cos_result_lower = sin_square_upper + limb_count;
  cos_result_upper = cos_result_lower + limb_count;
  operation = cos_result_upper + limb_count;

  if (!malbolge_guest_math_fixed_interval_multiply(
          sin_magnitude_lower, sin_magnitude_upper, cos_magnitude_lower,
          cos_magnitude_upper, limb_count, fraction_limbs, sin_product_lower,
          sin_product_upper, operation, limb_count * UINT32_C(4)) ||
      !malbolge_guest_math_fixed_add(sin_product_lower, sin_product_lower,
                                     limb_count, cos_square_lower) ||
      !malbolge_guest_math_fixed_add(sin_product_upper, sin_product_upper,
                                     limb_count, cos_square_upper)) {
    return 0;
  }
  copy_fixed_limbs(sin_product_lower, cos_square_lower, limb_count);
  copy_fixed_limbs(sin_product_upper, cos_square_upper, limb_count);

  if (!malbolge_guest_math_fixed_interval_multiply(
          cos_magnitude_lower, cos_magnitude_upper, cos_magnitude_lower,
          cos_magnitude_upper, limb_count, fraction_limbs, cos_square_lower,
          cos_square_upper, operation, limb_count * UINT32_C(4)) ||
      !malbolge_guest_math_fixed_interval_multiply(
          sin_magnitude_lower, sin_magnitude_upper, sin_magnitude_lower,
          sin_magnitude_upper, limb_count, fraction_limbs, sin_square_lower,
          sin_square_upper, operation, limb_count * UINT32_C(4)) ||
      !malbolge_guest_math_fixed_signed_add(
          cos_square_lower, UINT32_C(0), sin_square_upper, UINT32_C(1),
          limb_count, cos_result_lower, &cos_lower_result_negative) ||
      !malbolge_guest_math_fixed_signed_add(
          cos_square_upper, UINT32_C(0), sin_square_lower, UINT32_C(1),
          limb_count, cos_result_upper, &cos_upper_result_negative) ||
      compare_signed_fixed_limbs(cos_result_lower, cos_lower_result_negative,
                                 cos_result_upper, cos_upper_result_negative,
                                 limb_count) > 0) {
    return 0;
  }

  if (sin_sign == cos_sign) {
    copy_fixed_limbs(output_sin_lower, sin_product_lower, limb_count);
    copy_fixed_limbs(output_sin_upper, sin_product_upper, limb_count);
    *output_sin_lower_negative = UINT32_C(0);
    *output_sin_upper_negative = UINT32_C(0);
  } else {
    copy_fixed_limbs(output_sin_lower, sin_product_upper, limb_count);
    copy_fixed_limbs(output_sin_upper, sin_product_lower, limb_count);
    *output_sin_lower_negative = fixed_limbs_is_zero(
                                     sin_product_upper, limb_count)
                                     ? UINT32_C(0)
                                     : UINT32_C(1);
    *output_sin_upper_negative = fixed_limbs_is_zero(
                                     sin_product_lower, limb_count)
                                     ? UINT32_C(0)
                                     : UINT32_C(1);
  }
  copy_fixed_limbs(output_cos_lower, cos_result_lower, limb_count);
  copy_fixed_limbs(output_cos_upper, cos_result_upper, limb_count);
  *output_cos_lower_negative = cos_lower_result_negative;
  *output_cos_upper_negative = cos_upper_result_negative;
  *proven = UINT32_C(1);
  return 1;
}

static int atan2_branch_rank(uint32_t y_negative, uint32_t x_negative) {
  if (y_negative != UINT32_C(0)) {
    return x_negative != UINT32_C(0) ? 0 : 1;
  }
  return x_negative != UINT32_C(0) ? 3 : 2;
}

int malbolge_guest_math_fixed_sincos_double_transport(
    const uint32_t *sin_lower, uint32_t sin_lower_negative,
    const uint32_t *sin_upper, uint32_t sin_upper_negative,
    const uint32_t *cos_lower, uint32_t cos_lower_negative,
    const uint32_t *cos_upper, uint32_t cos_upper_negative,
    uint32_t limb_count, uint32_t fraction_limbs, uint32_t doublings,
    uint32_t *output_sin_lower, uint32_t *output_sin_lower_negative,
    uint32_t *output_sin_upper, uint32_t *output_sin_upper_negative,
    uint32_t *output_cos_lower, uint32_t *output_cos_lower_negative,
    uint32_t *output_cos_upper, uint32_t *output_cos_upper_negative,
    uint32_t *proven, uint32_t *scratch, uint32_t scratch_capacity) {
  uint32_t index = UINT32_C(0);
  uint32_t current_sin_lower_negative = sin_lower_negative;
  uint32_t current_sin_upper_negative = sin_upper_negative;
  uint32_t current_cos_lower_negative = cos_lower_negative;
  uint32_t current_cos_upper_negative = cos_upper_negative;
  uint32_t step_proven = UINT32_C(0);
  uint32_t *current_sin_lower = scratch;
  uint32_t *current_sin_upper = NULL;
  uint32_t *current_cos_lower = NULL;
  uint32_t *current_cos_upper = NULL;
  uint32_t *operation = NULL;

  if (sin_lower == NULL || sin_upper == NULL || cos_lower == NULL ||
      cos_upper == NULL || output_sin_lower == NULL ||
      output_sin_lower_negative == NULL || output_sin_upper == NULL ||
      output_sin_upper_negative == NULL || output_cos_lower == NULL ||
      output_cos_lower_negative == NULL || output_cos_upper == NULL ||
      output_cos_upper_negative == NULL || proven == NULL || scratch == NULL ||
      limb_count == UINT32_C(0) || limb_count > UINT32_MAX / UINT32_C(16) ||
      fraction_limbs >= limb_count || doublings > UINT32_C(56) ||
      scratch_capacity < limb_count * UINT32_C(16) ||
      sin_lower_negative > UINT32_C(1) || sin_upper_negative > UINT32_C(1) ||
      cos_lower_negative > UINT32_C(1) || cos_upper_negative > UINT32_C(1) ||
      compare_signed_fixed_limbs(sin_lower, sin_lower_negative, sin_upper,
                                 sin_upper_negative, limb_count) > 0 ||
      compare_signed_fixed_limbs(cos_lower, cos_lower_negative, cos_upper,
                                 cos_upper_negative, limb_count) > 0) {
    return 0;
  }
  current_sin_upper = current_sin_lower + limb_count;
  current_cos_lower = current_sin_upper + limb_count;
  current_cos_upper = current_cos_lower + limb_count;
  operation = current_cos_upper + limb_count;
  copy_fixed_limbs(current_sin_lower, sin_lower, limb_count);
  copy_fixed_limbs(current_sin_upper, sin_upper, limb_count);
  copy_fixed_limbs(current_cos_lower, cos_lower, limb_count);
  copy_fixed_limbs(current_cos_upper, cos_upper, limb_count);

  while (index < doublings) {
    if (!malbolge_guest_math_fixed_sincos_double_interval(
            current_sin_lower, current_sin_lower_negative, current_sin_upper,
            current_sin_upper_negative, current_cos_lower,
            current_cos_lower_negative, current_cos_upper,
            current_cos_upper_negative, limb_count, fraction_limbs,
            current_sin_lower, &current_sin_lower_negative, current_sin_upper,
            &current_sin_upper_negative, current_cos_lower,
            &current_cos_lower_negative, current_cos_upper,
            &current_cos_upper_negative, &step_proven, operation,
            limb_count * UINT32_C(12))) {
      return 0;
    }
    if (step_proven == UINT32_C(0)) {
      *proven = UINT32_C(0);
      return 1;
    }
    ++index;
  }

  copy_fixed_limbs(output_sin_lower, current_sin_lower, limb_count);
  copy_fixed_limbs(output_sin_upper, current_sin_upper, limb_count);
  copy_fixed_limbs(output_cos_lower, current_cos_lower, limb_count);
  copy_fixed_limbs(output_cos_upper, current_cos_upper, limb_count);
  *output_sin_lower_negative = current_sin_lower_negative;
  *output_sin_upper_negative = current_sin_upper_negative;
  *output_cos_lower_negative = current_cos_lower_negative;
  *output_cos_upper_negative = current_cos_upper_negative;
  *proven = UINT32_C(1);
  return 1;
}

int malbolge_guest_math_dyadic_normalized_sincos_interval(
    const MalbolgeGuestMathDyadic *midpoint, uint32_t fraction_limbs,
    uint32_t terms, uint32_t *output_sin_lower,
    uint32_t *output_sin_lower_negative, uint32_t *output_sin_upper,
    uint32_t *output_sin_upper_negative, uint32_t *output_cos_lower,
    uint32_t *output_cos_lower_negative, uint32_t *output_cos_upper,
    uint32_t *output_cos_upper_negative, uint32_t *proven, uint32_t *scratch,
    uint32_t scratch_capacity) {
  MalbolgeGuestMathLambertArgumentBounds bounds;
  MalbolgeGuestMathDyadic normalized;
  uint32_t fraction_bits = UINT32_C(0);
  uint32_t limb_count = UINT32_C(0);
  uint32_t sin_lower_negative = UINT32_C(0);
  uint32_t sin_upper_negative = UINT32_C(0);
  uint32_t cos_lower_negative = UINT32_C(0);
  uint32_t cos_upper_negative = UINT32_C(0);
  uint32_t transport_proven = UINT32_C(0);
  uint32_t output_sin_lower_staged_negative = UINT32_C(0);
  uint32_t output_sin_upper_staged_negative = UINT32_C(0);
  uint32_t *sin_lower = scratch;
  uint32_t *sin_upper = NULL;
  uint32_t *cos_lower = NULL;
  uint32_t *cos_upper = NULL;
  uint32_t *operation = NULL;
  uint32_t *input = NULL;
  uint32_t *taylor_scratch = NULL;

  if (midpoint == NULL || output_sin_lower == NULL ||
      output_sin_lower_negative == NULL || output_sin_upper == NULL ||
      output_sin_upper_negative == NULL || output_cos_lower == NULL ||
      output_cos_lower_negative == NULL || output_cos_upper == NULL ||
      output_cos_upper_negative == NULL || proven == NULL || scratch == NULL ||
      fraction_limbs == UINT32_C(0) ||
      fraction_limbs > UINT32_MAX / UINT32_C(32) ||
      fraction_limbs == UINT32_MAX || terms < UINT32_C(2) ||
      !malbolge_guest_math_dyadic_lambert_argument_bounds(midpoint, &bounds)) {
    return 0;
  }
  fraction_bits = fraction_limbs * UINT32_C(32);
  limb_count = fraction_limbs + UINT32_C(1);
  if (limb_count > UINT32_MAX / UINT32_C(20) ||
      scratch_capacity < limb_count * UINT32_C(20)) {
    return 0;
  }
  if (fraction_bits < bounds.normalized_denominator_shift) {
    *proven = UINT32_C(0);
    return 1;
  }
  normalized.numerator = midpoint->numerator;
  normalized.denominator_shift = bounds.normalized_denominator_shift;
  normalized.negative = UINT32_C(0);
  sin_upper = sin_lower + limb_count;
  cos_lower = sin_upper + limb_count;
  cos_upper = cos_lower + limb_count;
  operation = cos_upper + limb_count;
  input = operation;
  taylor_scratch = input + limb_count;
  zero_fixed_limbs(input, limb_count);
  if (!malbolge_guest_math_dyadic_write_fixed(&normalized, fraction_bits, input,
                                               limb_count) ||
      !malbolge_guest_math_fixed_sin_taylor_interval(
          input, input, limb_count, fraction_limbs, terms, sin_lower,
          &sin_lower_negative, sin_upper, &sin_upper_negative, taylor_scratch,
          limb_count * UINT32_C(10)) ||
      !malbolge_guest_math_fixed_cos_taylor_interval(
          input, input, limb_count, fraction_limbs, terms, cos_lower,
          &cos_lower_negative, cos_upper, &cos_upper_negative, taylor_scratch,
          limb_count * UINT32_C(10))) {
    return 0;
  }
  if (signed_fixed_interval_proven_sign(
          sin_lower, sin_lower_negative, sin_upper, sin_upper_negative,
          limb_count) <= 0 ||
      signed_fixed_interval_proven_sign(
          cos_lower, cos_lower_negative, cos_upper, cos_upper_negative,
          limb_count) <= 0) {
    *proven = UINT32_C(0);
    return 1;
  }
  if (!malbolge_guest_math_fixed_sincos_double_transport(
          sin_lower, sin_lower_negative, sin_upper, sin_upper_negative,
          cos_lower, cos_lower_negative, cos_upper, cos_upper_negative,
          limb_count, fraction_limbs, bounds.normalizing_halvings, sin_lower,
          &sin_lower_negative, sin_upper, &sin_upper_negative, cos_lower,
          &cos_lower_negative, cos_upper, &cos_upper_negative,
          &transport_proven, operation, limb_count * UINT32_C(16))) {
    return 0;
  }
  if (transport_proven == UINT32_C(0)) {
    *proven = UINT32_C(0);
    return 1;
  }

  if (midpoint->negative == UINT32_C(0)) {
    copy_fixed_limbs(output_sin_lower, sin_lower, limb_count);
    copy_fixed_limbs(output_sin_upper, sin_upper, limb_count);
    output_sin_lower_staged_negative = sin_lower_negative;
    output_sin_upper_staged_negative = sin_upper_negative;
  } else {
    copy_fixed_limbs(output_sin_lower, sin_upper, limb_count);
    copy_fixed_limbs(output_sin_upper, sin_lower, limb_count);
    output_sin_lower_staged_negative =
        fixed_limbs_is_zero(sin_upper, limb_count)
            ? UINT32_C(0)
            : (sin_upper_negative ^ UINT32_C(1));
    output_sin_upper_staged_negative =
        fixed_limbs_is_zero(sin_lower, limb_count)
            ? UINT32_C(0)
            : (sin_lower_negative ^ UINT32_C(1));
  }
  copy_fixed_limbs(output_cos_lower, cos_lower, limb_count);
  copy_fixed_limbs(output_cos_upper, cos_upper, limb_count);
  *output_sin_lower_negative = output_sin_lower_staged_negative;
  *output_sin_upper_negative = output_sin_upper_staged_negative;
  *output_cos_lower_negative = cos_lower_negative;
  *output_cos_upper_negative = cos_upper_negative;
  *proven = UINT32_C(1);
  return 1;
}

static int signed_interval_magnitude_bounds(
    const uint32_t *lower, uint32_t lower_negative, const uint32_t *upper,
    uint32_t upper_negative, uint32_t limb_count,
    const uint32_t **magnitude_lower,
    const uint32_t **magnitude_upper) {
  const int sign = signed_fixed_interval_proven_sign(
      lower, lower_negative, upper, upper_negative, limb_count);
  if (magnitude_lower == NULL || magnitude_upper == NULL || sign == 0) {
    return 0;
  }
  if (sign > 0) {
    *magnitude_lower = lower;
    *magnitude_upper = upper;
  } else {
    *magnitude_lower = upper;
    *magnitude_upper = lower;
  }
  return sign;
}

int malbolge_guest_math_midpoint_compare(
    const MalbolgeGuestMathAtan2KernelInput *ratio,
    const MalbolgeGuestMathDyadic *midpoint, uint32_t fraction_limbs,
    uint32_t terms, int32_t *comparison, uint32_t *scratch,
    uint32_t scratch_capacity) {
  uint32_t fraction_bits = UINT32_C(0);
  uint32_t limb_count = UINT32_C(0);
  uint32_t sin_lower_negative = UINT32_C(0);
  uint32_t sin_upper_negative = UINT32_C(0);
  uint32_t cos_lower_negative = UINT32_C(0);
  uint32_t cos_upper_negative = UINT32_C(0);
  int sin_magnitude_sign = 0;
  int sin_sign = 0;
  int cos_sign = 0;
  int boundary_rank = 0;
  int actual_rank = 0;
  int32_t magnitude_comparison = INT32_C(0);
  const uint32_t *sin_magnitude_lower = NULL;
  const uint32_t *sin_magnitude_upper = NULL;
  const uint32_t *cos_magnitude_lower = NULL;
  const uint32_t *cos_magnitude_upper = NULL;
  uint32_t *input = scratch;
  uint32_t *sin_lower = NULL;
  uint32_t *sin_upper = NULL;
  uint32_t *cos_lower = NULL;
  uint32_t *cos_upper = NULL;
  uint32_t *operation = NULL;

  if (ratio == NULL || midpoint == NULL || comparison == NULL ||
      scratch == NULL || midpoint->numerator == UINT64_C(0) ||
      midpoint->negative > UINT32_C(1) || fraction_limbs == UINT32_C(0) ||
      fraction_limbs > UINT32_MAX / UINT32_C(32) ||
      fraction_limbs == UINT32_MAX || !valid_ratio_input(ratio)) {
    return 0;
  }
  fraction_bits = fraction_limbs * UINT32_C(32);
  limb_count = fraction_limbs + UINT32_C(1);
  if (limb_count > UINT32_MAX / UINT32_C(15) ||
      scratch_capacity < limb_count * UINT32_C(15)) {
    return 0;
  }
  if (fraction_bits < midpoint->denominator_shift) {
    *comparison = INT32_C(0);
    return 1;
  }
  sin_lower = input + limb_count;
  sin_upper = sin_lower + limb_count;
  cos_lower = sin_upper + limb_count;
  cos_upper = cos_lower + limb_count;
  operation = cos_upper + limb_count;
  zero_fixed_limbs(input, limb_count);
  if (!malbolge_guest_math_dyadic_write_fixed(midpoint, fraction_bits, input,
                                               limb_count) ||
      !malbolge_guest_math_fixed_sin_taylor_interval(
          input, input, limb_count, fraction_limbs, terms, sin_lower,
          &sin_lower_negative, sin_upper, &sin_upper_negative, operation,
          limb_count * UINT32_C(10)) ||
      !malbolge_guest_math_fixed_cos_taylor_interval(
          input, input, limb_count, fraction_limbs, terms, cos_lower,
          &cos_lower_negative, cos_upper, &cos_upper_negative, operation,
          limb_count * UINT32_C(10))) {
    return 0;
  }
  sin_magnitude_sign = signed_interval_magnitude_bounds(
      sin_lower, sin_lower_negative, sin_upper, sin_upper_negative, limb_count,
      &sin_magnitude_lower, &sin_magnitude_upper);
  cos_sign = signed_interval_magnitude_bounds(
      cos_lower, cos_lower_negative, cos_upper, cos_upper_negative, limb_count,
      &cos_magnitude_lower, &cos_magnitude_upper);
  if (sin_magnitude_sign == 0 || cos_sign == 0) {
    *comparison = INT32_C(0);
    return 1;
  }
  sin_sign = midpoint->negative != UINT32_C(0) ? -sin_magnitude_sign
                                                : sin_magnitude_sign;
  boundary_rank =
      sin_sign < 0 ? (cos_sign < 0 ? 0 : 1) : (cos_sign < 0 ? 3 : 2);
  if (midpoint->negative == UINT32_C(0) && boundary_rank == 0) {
    boundary_rank = 4;
  } else if (midpoint->negative != UINT32_C(0) && boundary_rank == 3) {
    boundary_rank = -1;
  }
  actual_rank = atan2_branch_rank(ratio->y_negative, ratio->x_negative);
  if (actual_rank < boundary_rank) {
    *comparison = INT32_C(-1);
    return 1;
  }
  if (actual_rank > boundary_rank) {
    *comparison = INT32_C(1);
    return 1;
  }
  if (!positive_ratio_tangent_compare_internal(
          ratio, sin_magnitude_lower, sin_magnitude_upper,
          cos_magnitude_lower, cos_magnitude_upper, limb_count, UINT32_C(0),
          &magnitude_comparison, operation, limb_count * UINT32_C(10))) {
    return 0;
  }
  *comparison = sin_sign == cos_sign ? magnitude_comparison
                                     : -magnitude_comparison;
  return 1;
}

int malbolge_guest_math_atan2_refinement_attempt(
    uint64_t y_bits, uint64_t x_bits, uint64_t candidate_bits,
    uint32_t fraction_limbs, uint32_t terms, uint32_t *certified,
    uint32_t *scratch, uint32_t scratch_capacity) {
  MalbolgeGuestMathAtan2KernelInput ratio;
  MalbolgeGuestMathAtan2CellMidpoints cell;
  const MalbolgeGuestMathSpecialResult special =
      malbolge_guest_math_atan2_special(y_bits, x_bits);
  int32_t lower_comparison = INT32_C(0);
  int32_t upper_comparison = INT32_C(0);
  uint32_t staged_certified = UINT32_C(0);

  if (certified == NULL || scratch == NULL ||
      special.status != MALBOLGE_GUEST_MATH_SPECIAL_KERNEL_REQUIRED ||
      !malbolge_guest_math_atan2_kernel_input(y_bits, x_bits, &ratio) ||
      !malbolge_guest_math_atan2_cell_midpoints(candidate_bits, &cell) ||
      !malbolge_guest_math_midpoint_compare(
          &ratio, &cell.lower, fraction_limbs, terms, &lower_comparison,
          scratch,
          scratch_capacity) ||
      !malbolge_guest_math_midpoint_compare(
          &ratio, &cell.upper, fraction_limbs, terms, &upper_comparison,
          scratch,
          scratch_capacity)) {
    return 0;
  }
  if (lower_comparison > INT32_C(0) &&
      upper_comparison < INT32_C(0)) {
    staged_certified = UINT32_C(1);
  }
  *certified = staged_certified;
  return 1;
}

int malbolge_guest_math_atan2_refinement_plan(
    uint32_t stage, MalbolgeGuestMathAtan2RefinementPlan *output) {
  MalbolgeGuestMathAtan2RefinementPlan staged;
  uint32_t limb_count = UINT32_C(0);
  uint32_t left_factor = UINT32_C(0);
  uint32_t right_factor = UINT32_C(0);

  if (output == NULL || stage > (UINT32_MAX - UINT32_C(8)) / UINT32_C(4) ||
      stage > UINT32_MAX - UINT32_C(3)) {
    return 0;
  }
  staged.stage = stage;
  staged.fraction_limbs = stage + UINT32_C(2);
  staged.terms = stage * UINT32_C(4) + UINT32_C(8);
  limb_count = staged.fraction_limbs + UINT32_C(1);
  if (limb_count > UINT32_MAX / UINT32_C(15) ||
      !taylor_recurrence_factors(staged.terms, UINT32_C(0), &left_factor,
                                &right_factor) ||
      !taylor_recurrence_factors(staged.terms, UINT32_C(1), &left_factor,
                                &right_factor)) {
    return 0;
  }
  staged.required_scratch_limbs = limb_count * UINT32_C(15);
  *output = staged;
  return 1;
}

int malbolge_guest_math_atan2_refine_available(
    uint64_t y_bits, uint64_t x_bits, uint64_t candidate_bits,
    uint32_t start_stage, uint32_t *scratch, uint32_t scratch_capacity,
    MalbolgeGuestMathAtan2RefinementProgress *output) {
  MalbolgeGuestMathAtan2RefinementProgress staged;
  MalbolgeGuestMathAtan2KernelInput ratio;
  MalbolgeGuestMathAtan2CellMidpoints cell;
  const MalbolgeGuestMathSpecialResult special =
      malbolge_guest_math_atan2_special(y_bits, x_bits);
  uint32_t stage = start_stage;

  if (scratch == NULL || output == NULL ||
      special.status != MALBOLGE_GUEST_MATH_SPECIAL_KERNEL_REQUIRED ||
      !malbolge_guest_math_atan2_kernel_input(y_bits, x_bits, &ratio) ||
      !malbolge_guest_math_atan2_cell_midpoints(candidate_bits, &cell)) {
    return 0;
  }
  for (;;) {
    uint32_t certified = UINT32_C(0);
    if (!malbolge_guest_math_atan2_refinement_plan(stage, &staged.plan)) {
      return 0;
    }
    staged.certified = UINT32_C(0);
    if (scratch_capacity < staged.plan.required_scratch_limbs) {
      *output = staged;
      return 1;
    }
    if (!malbolge_guest_math_atan2_refinement_attempt(
            y_bits, x_bits, candidate_bits, staged.plan.fraction_limbs,
            staged.plan.terms, &certified, scratch, scratch_capacity)) {
      return 0;
    }
    if (certified != UINT32_C(0)) {
      staged.certified = UINT32_C(1);
      *output = staged;
      return 1;
    }
    if (stage == UINT32_MAX) {
      return 0;
    }
    ++stage;
  }
}

int malbolge_guest_math_fixed_interval_add(
    const uint32_t *left_lower, const uint32_t *left_upper,
    const uint32_t *right_lower, const uint32_t *right_upper,
    uint32_t limb_count, uint32_t *output_lower, uint32_t *output_upper) {
  if (left_lower == NULL || left_upper == NULL || right_lower == NULL ||
      right_upper == NULL || output_lower == NULL || output_upper == NULL ||
      limb_count == UINT32_C(0) ||
      compare_fixed_limbs(left_lower, left_upper, limb_count) > 0 ||
      compare_fixed_limbs(right_lower, right_upper, limb_count) > 0 ||
      !add_fixed_limbs_fits(left_lower, right_lower, limb_count) ||
      !add_fixed_limbs_fits(left_upper, right_upper, limb_count)) {
    return 0;
  }
  add_fixed_limbs_unchecked(output_lower, left_lower, right_lower, limb_count);
  add_fixed_limbs_unchecked(output_upper, left_upper, right_upper, limb_count);
  return 1;
}

int malbolge_guest_math_fixed_interval_subtract(
    const uint32_t *left_lower, const uint32_t *left_upper,
    const uint32_t *right_lower, const uint32_t *right_upper,
    uint32_t limb_count, uint32_t *output_lower, uint32_t *output_upper) {
  if (left_lower == NULL || left_upper == NULL || right_lower == NULL ||
      right_upper == NULL || output_lower == NULL || output_upper == NULL ||
      limb_count == UINT32_C(0) ||
      compare_fixed_limbs(left_lower, left_upper, limb_count) > 0 ||
      compare_fixed_limbs(right_lower, right_upper, limb_count) > 0 ||
      compare_fixed_limbs(left_lower, right_upper, limb_count) < 0 ||
      compare_fixed_limbs(left_upper, right_lower, limb_count) < 0) {
    return 0;
  }
  (void)subtract_fixed_limbs(output_lower, left_lower, right_upper, limb_count);
  (void)subtract_fixed_limbs(output_upper, left_upper, right_lower, limb_count);
  return 1;
}

static void decrement_fixed_192(MalbolgeGuestMathFixed192 *value) {
  decrement_fixed_limbs(value->limbs, FIXED_192_LIMB_COUNT);
}

static int compare_fixed_192(const MalbolgeGuestMathFixed192 *left,
                             const MalbolgeGuestMathFixed192 *right) {
  return compare_fixed_limbs(left->limbs, right->limbs,
                             FIXED_192_LIMB_COUNT);
}

static int subtract_fixed_192(MalbolgeGuestMathFixed192 *output,
                              const MalbolgeGuestMathFixed192 *left,
                              const MalbolgeGuestMathFixed192 *right) {
  return subtract_fixed_limbs(output->limbs, left->limbs, right->limbs,
                              FIXED_192_LIMB_COUNT);
}

static int multiply_fixed_limbs_with_scratch(
    const uint32_t *left, const uint32_t *right, uint32_t limb_count,
    uint32_t fraction_limbs, uint32_t *output, uint32_t *product,
    uint32_t product_capacity, uint32_t round_up, uint32_t *discarded) {
  uint32_t product_limbs = UINT32_C(0);
  uint32_t index = UINT32_C(0);
  uint32_t left_index = UINT32_C(0);

  if (left == NULL || right == NULL || output == NULL || product == NULL ||
      discarded == NULL || limb_count == UINT32_C(0) ||
      limb_count > UINT32_MAX / UINT32_C(2) || fraction_limbs > limb_count ||
      round_up > UINT32_C(1)) {
    return 0;
  }
  product_limbs = limb_count * UINT32_C(2);
  if (product_capacity < product_limbs) {
    return 0;
  }
  while (index < product_limbs) {
    product[index] = UINT32_C(0);
    ++index;
  }
  while (left_index < limb_count) {
    uint32_t right_index = UINT32_C(0);
    uint64_t carry = UINT64_C(0);
    while (right_index < limb_count) {
      const uint32_t cell_index = left_index + right_index;
      const uint64_t cell = (uint64_t)left[left_index] *
                                (uint64_t)right[right_index] +
                            (uint64_t)product[cell_index] + carry;
      product[cell_index] = (uint32_t)cell;
      carry = cell >> UINT32_C(32);
      ++right_index;
    }
    index = left_index + limb_count;
    while (carry != UINT64_C(0) && index < product_limbs) {
      const uint64_t cell = (uint64_t)product[index] + carry;
      product[index] = (uint32_t)cell;
      carry = cell >> UINT32_C(32);
      ++index;
    }
    ++left_index;
  }
  index = fraction_limbs + limb_count;
  while (index < product_limbs) {
    if (product[index] != UINT32_C(0)) {
      return 0;
    }
    ++index;
  }
  {
    uint32_t staged_discarded = UINT32_C(0);
    uint32_t all_maximum = UINT32_C(1);
    index = UINT32_C(0);
    while (index < fraction_limbs) {
      if (product[index] != UINT32_C(0)) {
        staged_discarded = UINT32_C(1);
      }
      ++index;
    }
    if (round_up != UINT32_C(0) && staged_discarded != UINT32_C(0)) {
      index = UINT32_C(0);
      while (index < limb_count) {
        if (product[index + fraction_limbs] != UINT32_MAX) {
          all_maximum = UINT32_C(0);
        }
        ++index;
      }
      if (all_maximum != UINT32_C(0)) {
        return 0;
      }
    }
    index = UINT32_C(0);
    while (index < limb_count) {
      output[index] = product[index + fraction_limbs];
      ++index;
    }
    if (round_up != UINT32_C(0) && staged_discarded != UINT32_C(0)) {
      increment_fixed_limbs(output, limb_count);
    }
    *discarded = staged_discarded;
  }
  return 1;
}

int malbolge_guest_math_fixed_multiply_floor(
    const uint32_t *left, const uint32_t *right, uint32_t limb_count,
    uint32_t fraction_limbs, uint32_t *output, uint32_t *scratch,
    uint32_t scratch_capacity, uint32_t *discarded) {
  return multiply_fixed_limbs_with_scratch(
      left, right, limb_count, fraction_limbs, output, scratch,
      scratch_capacity, UINT32_C(0), discarded);
}

int malbolge_guest_math_fixed_multiply_ceil(
    const uint32_t *left, const uint32_t *right, uint32_t limb_count,
    uint32_t fraction_limbs, uint32_t *output, uint32_t *scratch,
    uint32_t scratch_capacity, uint32_t *discarded) {
  return multiply_fixed_limbs_with_scratch(
      left, right, limb_count, fraction_limbs, output, scratch,
      scratch_capacity, UINT32_C(1), discarded);
}

int malbolge_guest_math_fixed_interval_multiply(
    const uint32_t *left_lower, const uint32_t *left_upper,
    const uint32_t *right_lower, const uint32_t *right_upper,
    uint32_t limb_count, uint32_t fraction_limbs, uint32_t *output_lower,
    uint32_t *output_upper, uint32_t *scratch, uint32_t scratch_capacity) {
  uint32_t product_limbs = UINT32_C(0);
  uint32_t discarded = UINT32_C(0);
  uint32_t *lower = NULL;
  uint32_t *upper = NULL;

  if (left_lower == NULL || left_upper == NULL || right_lower == NULL ||
      right_upper == NULL || output_lower == NULL || output_upper == NULL ||
      scratch == NULL || limb_count == UINT32_C(0) ||
      compare_fixed_limbs(left_lower, left_upper, limb_count) > 0 ||
      compare_fixed_limbs(right_lower, right_upper, limb_count) > 0 ||
      limb_count > UINT32_MAX / UINT32_C(4) || fraction_limbs > limb_count) {
    return 0;
  }
  product_limbs = limb_count * UINT32_C(2);
  if (scratch_capacity < limb_count * UINT32_C(4)) {
    return 0;
  }
  lower = scratch + product_limbs;
  upper = lower + limb_count;
  if (!multiply_fixed_limbs_with_scratch(
          left_lower, right_lower, limb_count, fraction_limbs, lower, scratch,
          product_limbs, UINT32_C(0), &discarded) ||
      !multiply_fixed_limbs_with_scratch(
          left_upper, right_upper, limb_count, fraction_limbs, upper, scratch,
          product_limbs, UINT32_C(1), &discarded)) {
    return 0;
  }
  copy_fixed_limbs(output_lower, lower, limb_count);
  copy_fixed_limbs(output_upper, upper, limb_count);
  return 1;
}

static void multiply_fixed_limbs_floor(
    const uint32_t *left, const uint32_t *right, uint32_t limb_count,
    uint32_t fraction_limbs, uint32_t *output, uint32_t *discarded) {
  uint32_t product[FIXED_MAX_PRODUCT_LIMBS];
  (void)multiply_fixed_limbs_with_scratch(
      left, right, limb_count, fraction_limbs, output, product,
      FIXED_MAX_PRODUCT_LIMBS, UINT32_C(0), discarded);
}

static void multiply_fixed_floor(const MalbolgeGuestMathFixed192 *left,
                                 const MalbolgeGuestMathFixed192 *right,
                                 MalbolgeGuestMathFixed192 *output,
                                 uint32_t *discarded) {
  multiply_fixed_limbs_floor(left->limbs, right->limbs,
                             FIXED_192_LIMB_COUNT, UINT32_C(6),
                             output->limbs, discarded);
}

static void multiply_interval_192(
    const MalbolgeGuestMathFixed192Interval *left,
    const MalbolgeGuestMathFixed192Interval *right,
    MalbolgeGuestMathFixed192Interval *output) {
  uint32_t discarded = UINT32_C(0);
  multiply_fixed_floor(&left->lower, &right->lower, &output->lower, &discarded);
  multiply_fixed_floor(&left->upper, &right->upper, &output->upper, &discarded);
  if (discarded != UINT32_C(0)) {
    increment_fixed_192(&output->upper);
  }
}

static void multiply_fixed_limbs_small(uint32_t *value,
                                       uint32_t limb_count,
                                       uint32_t factor) {
  uint32_t index = UINT32_C(0);
  uint64_t carry = UINT64_C(0);
  while (index < limb_count) {
    const uint64_t product = (uint64_t)value[index] * factor + carry;
    value[index] = (uint32_t)product;
    carry = product >> UINT32_C(32);
    ++index;
  }
}

static uint32_t divide_fixed_limbs_small_floor(
    const uint32_t *input, uint32_t limb_count, uint32_t divisor,
    uint32_t *output) {
  uint32_t limb_index = limb_count;
  uint64_t remainder = UINT64_C(0);
  while (limb_index != UINT32_C(0)) {
    uint32_t bit_index = UINT32_C(32);
    uint32_t quotient_limb = UINT32_C(0);
    const uint32_t input_limb = input[limb_index - UINT32_C(1)];
    --limb_index;
    while (bit_index != UINT32_C(0)) {
      uint32_t quotient_bit = UINT32_C(0);
      --bit_index;
      remainder = (remainder << UINT32_C(1)) |
                  (uint64_t)((input_limb >> bit_index) & UINT32_C(1));
      if (remainder >= (uint64_t)divisor) {
        remainder -= (uint64_t)divisor;
        quotient_bit = UINT32_C(1);
      }
      quotient_limb |= quotient_bit << bit_index;
    }
    output[limb_index] = quotient_limb;
  }
  return (uint32_t)remainder;
}

int malbolge_guest_math_fixed_divide_small_floor(
    const uint32_t *input, uint32_t limb_count, uint32_t divisor,
    uint32_t *output, uint32_t *remainder) {
  uint32_t staged_remainder = UINT32_C(0);
  if (input == NULL || output == NULL || remainder == NULL ||
      limb_count == UINT32_C(0) || divisor == UINT32_C(0)) {
    return 0;
  }
  staged_remainder =
      divide_fixed_limbs_small_floor(input, limb_count, divisor, output);
  *remainder = staged_remainder;
  return 1;
}

int malbolge_guest_math_fixed_divide_small_ceil(
    const uint32_t *input, uint32_t limb_count, uint32_t divisor,
    uint32_t *output, uint32_t *remainder) {
  uint32_t staged_remainder = UINT32_C(0);
  if (input == NULL || output == NULL || remainder == NULL ||
      limb_count == UINT32_C(0) || divisor == UINT32_C(0)) {
    return 0;
  }
  staged_remainder =
      divide_fixed_limbs_small_floor(input, limb_count, divisor, output);
  if (staged_remainder != UINT32_C(0)) {
    increment_fixed_limbs(output, limb_count);
  }
  *remainder = staged_remainder;
  return 1;
}

int malbolge_guest_math_fixed_interval_divide_small(
    const uint32_t *input_lower, const uint32_t *input_upper,
    uint32_t limb_count, uint32_t divisor, uint32_t *output_lower,
    uint32_t *output_upper, uint32_t *scratch, uint32_t scratch_capacity) {
  uint32_t lower_remainder = UINT32_C(0);
  uint32_t upper_remainder = UINT32_C(0);
  uint32_t *lower = scratch;
  uint32_t *upper = NULL;

  if (input_lower == NULL || input_upper == NULL || output_lower == NULL ||
      output_upper == NULL || scratch == NULL || limb_count == UINT32_C(0) ||
      compare_fixed_limbs(input_lower, input_upper, limb_count) > 0 ||
      limb_count > UINT32_MAX / UINT32_C(2) || divisor == UINT32_C(0) ||
      scratch_capacity < limb_count * UINT32_C(2)) {
    return 0;
  }
  upper = lower + limb_count;
  lower_remainder =
      divide_fixed_limbs_small_floor(input_lower, limb_count, divisor, lower);
  upper_remainder =
      divide_fixed_limbs_small_floor(input_upper, limb_count, divisor, upper);
  if (upper_remainder != UINT32_C(0)) {
    increment_fixed_limbs(upper, limb_count);
  }
  (void)lower_remainder;
  copy_fixed_limbs(output_lower, lower, limb_count);
  copy_fixed_limbs(output_upper, upper, limb_count);
  return 1;
}

int malbolge_guest_math_fixed_taylor_term_interval(
    const uint32_t *term_lower, const uint32_t *term_upper,
    const uint32_t *square_lower, const uint32_t *square_upper,
    uint32_t limb_count, uint32_t fraction_limbs, uint32_t divisor,
    uint32_t *output_lower, uint32_t *output_upper, uint32_t *scratch,
    uint32_t scratch_capacity) {
  uint32_t product_limbs = UINT32_C(0);
  uint32_t *lower = NULL;
  uint32_t *upper = NULL;

  if (term_lower == NULL || term_upper == NULL || square_lower == NULL ||
      square_upper == NULL || output_lower == NULL || output_upper == NULL ||
      scratch == NULL || limb_count == UINT32_C(0) ||
      limb_count > UINT32_MAX / UINT32_C(4) || fraction_limbs > limb_count ||
      divisor == UINT32_C(0) ||
      scratch_capacity < limb_count * UINT32_C(4)) {
    return 0;
  }
  product_limbs = limb_count * UINT32_C(2);
  lower = scratch + product_limbs;
  upper = lower + limb_count;
  if (!malbolge_guest_math_fixed_interval_multiply(
          term_lower, term_upper, square_lower, square_upper, limb_count,
          fraction_limbs, lower, upper, scratch, scratch_capacity) ||
      !malbolge_guest_math_fixed_interval_divide_small(
          lower, upper, limb_count, divisor, lower, upper, scratch,
          product_limbs)) {
    return 0;
  }
  copy_fixed_limbs(output_lower, lower, limb_count);
  copy_fixed_limbs(output_upper, upper, limb_count);
  return 1;
}

static void multiply_fixed_small(MalbolgeGuestMathFixed192 *value,
                                 uint32_t factor) {
  multiply_fixed_limbs_small(value->limbs, FIXED_192_LIMB_COUNT, factor);
}

static uint32_t divide_fixed_small_floor(
    const MalbolgeGuestMathFixed192 *input, uint32_t divisor,
    MalbolgeGuestMathFixed192 *output) {
  return divide_fixed_limbs_small_floor(input->limbs, FIXED_192_LIMB_COUNT,
                                        divisor, output->limbs);
}

static void divide_interval_small(MalbolgeGuestMathFixed192Interval *value,
                                  uint32_t divisor) {
  MalbolgeGuestMathFixed192 lower;
  MalbolgeGuestMathFixed192 upper;
  const uint32_t upper_remainder =
      divide_fixed_small_floor(&value->upper, divisor, &upper);
  (void)divide_fixed_small_floor(&value->lower, divisor, &lower);
  if (upper_remainder != UINT32_C(0)) {
    increment_fixed_192(&upper);
  }
  copy_fixed_192(&value->lower, lower.limbs);
  copy_fixed_192(&value->upper, upper.limbs);
}

static int subtract_interval_192(
    MalbolgeGuestMathFixed192Interval *value,
    const MalbolgeGuestMathFixed192Interval *term) {
  MalbolgeGuestMathFixed192 lower;
  MalbolgeGuestMathFixed192 upper;
  if (!subtract_fixed_192(&lower, &value->lower, &term->upper) ||
      !subtract_fixed_192(&upper, &value->upper, &term->lower)) {
    return 0;
  }
  copy_fixed_192(&value->lower, lower.limbs);
  copy_fixed_192(&value->upper, upper.limbs);
  return 1;
}

static void add_interval_192(MalbolgeGuestMathFixed192Interval *value,
                             const MalbolgeGuestMathFixed192Interval *term) {
  add_fixed_192(&value->lower, &term->lower);
  add_fixed_192(&value->upper, &term->upper);
}

int malbolge_guest_math_atan_residual_interval(
    const MalbolgeGuestMathExactRatio *input,
    MalbolgeGuestMathFixed192Interval *output) {
  MalbolgeGuestMathFixed192Interval x;
  MalbolgeGuestMathFixed192Interval square;
  MalbolgeGuestMathFixed192Interval term;
  MalbolgeGuestMathFixed192Interval sum;
  MalbolgeGuestMathFixed192 cutoff;
  MalbolgeGuestMathFixed192Interval truncation;
  uint32_t index = UINT32_C(1);

  if (output == NULL || !malbolge_guest_math_exact_ratio_interval(input, &x)) {
    return 0;
  }
  copy_fixed_192(&cutoff, ATAN_CUT_UPPER_192);
  if (compare_fixed_192(&x.upper, &cutoff) > 0) {
    return 0;
  }
  if (fixed_192_is_zero(&x.lower)) {
    copy_fixed_192(&output->lower, x.lower.limbs);
    copy_fixed_192(&output->upper, x.upper.limbs);
    return 1;
  }
  if (fixed_192_below_two_neg64(&x.upper)) {
    MalbolgeGuestMathFixed192 lower;
    copy_fixed_192(&lower, x.lower.limbs);
    decrement_fixed_192(&lower);
    copy_fixed_192(&output->lower, lower.limbs);
    copy_fixed_192(&output->upper, x.upper.limbs);
    return 1;
  }
  multiply_interval_192(&x, &x, &square);
  copy_fixed_192(&term.lower, x.lower.limbs);
  copy_fixed_192(&term.upper, x.upper.limbs);
  copy_fixed_192(&sum.lower, x.lower.limbs);
  copy_fixed_192(&sum.upper, x.upper.limbs);
  while (index < ATAN_SERIES_TERMS) {
    const uint32_t previous_denominator = (UINT32_C(2) * index) - UINT32_C(1);
    const uint32_t denominator = (UINT32_C(2) * index) + UINT32_C(1);
    MalbolgeGuestMathFixed192Interval next;
    multiply_interval_192(&term, &square, &next);
    multiply_fixed_small(&next.lower, previous_denominator);
    multiply_fixed_small(&next.upper, previous_denominator);
    divide_interval_small(&next, denominator);
    copy_fixed_192(&term.lower, next.lower.limbs);
    copy_fixed_192(&term.upper, next.upper.limbs);
    if ((index & UINT32_C(1)) != UINT32_C(0)) {
      if (!subtract_interval_192(&sum, &term)) {
        return 0;
      }
    } else {
      add_interval_192(&sum, &term);
    }
    ++index;
  }
  multiply_interval_192(&term, &square, &truncation);
  multiply_fixed_small(&truncation.lower,
                       (UINT32_C(2) * index) - UINT32_C(1));
  multiply_fixed_small(&truncation.upper,
                       (UINT32_C(2) * index) - UINT32_C(1));
  divide_interval_small(&truncation, (UINT32_C(2) * index) + UINT32_C(1));
  add_fixed_192(&sum.upper, &truncation.upper);
  copy_fixed_192(&output->lower, sum.lower.limbs);
  copy_fixed_192(&output->upper, sum.upper.limbs);
  return 1;
}

int malbolge_guest_math_atan2_interval(
    uint64_t y_bits, uint64_t x_bits, MalbolgeGuestMathAtan2Interval *output) {
  MalbolgeGuestMathAtan2KernelPlan plan;
  MalbolgeGuestMathFixed192Interval base;
  MalbolgeGuestMathFixed192Interval residual;
  MalbolgeGuestMathFixed192Interval staged;

  if (output == NULL ||
      !malbolge_guest_math_atan2_kernel_plan(y_bits, x_bits, &plan) ||
      !malbolge_guest_math_atan2_base_interval(plan.quarter_pi_base, &base) ||
      !malbolge_guest_math_atan_residual_interval(&plan.residual, &residual)) {
    return 0;
  }
  copy_fixed_192(&staged.lower, base.lower.limbs);
  copy_fixed_192(&staged.upper, base.upper.limbs);
  if (plan.ratio_operation == MALBOLGE_GUEST_MATH_ATAN2_RATIO_ADD) {
    add_interval_192(&staged, &residual);
  } else if (!subtract_interval_192(&staged, &residual)) {
    return 0;
  }
  copy_fixed_192(&output->magnitude.lower, staged.lower.limbs);
  copy_fixed_192(&output->magnitude.upper, staged.upper.limbs);
  output->negative = plan.negative;
  return 1;
}

static const uint32_t QUARTER_PI_LOWER_224[8] = {
    UINT32_C(0x020bbea6), UINT32_C(0x8a67cc74), UINT32_C(0x29024e08),
    UINT32_C(0x80dc1cd1), UINT32_C(0xc4c6628b), UINT32_C(0x2168c234),
    UINT32_C(0xc90fdaa2), UINT32_C(0)};
static const uint32_t QUARTER_PI_UPPER_224[8] = {
    UINT32_C(0x020bbea7), UINT32_C(0x8a67cc74), UINT32_C(0x29024e08),
    UINT32_C(0x80dc1cd1), UINT32_C(0xc4c6628b), UINT32_C(0x2168c234),
    UINT32_C(0xc90fdaa2), UINT32_C(0)};
static const uint32_t ATAN_CUT_UPPER_224[8] = {
    UINT32_C(0x0a0a0a0b), UINT32_C(0x0a0a0a0a), UINT32_C(0x0a0a0a0a),
    UINT32_C(0x0a0a0a0a), UINT32_C(0x0a0a0a0a), UINT32_C(0x0a0a0a0a),
    UINT32_C(0x6a0a0a0a), UINT32_C(0)};

static void copy_fixed_224(MalbolgeGuestMathFixed224 *output,
                           const uint32_t source[8]) {
  copy_fixed_limbs(output->limbs, source, FIXED_224_LIMB_COUNT);
}

static void zero_fixed_224(MalbolgeGuestMathFixed224 *value) {
  zero_fixed_limbs(value->limbs, FIXED_224_LIMB_COUNT);
}

static void increment_fixed_224(MalbolgeGuestMathFixed224 *value) {
  increment_fixed_limbs(value->limbs, FIXED_224_LIMB_COUNT);
}

static void decrement_fixed_224(MalbolgeGuestMathFixed224 *value) {
  decrement_fixed_limbs(value->limbs, FIXED_224_LIMB_COUNT);
}

static int compare_fixed_224(const MalbolgeGuestMathFixed224 *left,
                             const MalbolgeGuestMathFixed224 *right) {
  return compare_fixed_limbs(left->limbs, right->limbs,
                             FIXED_224_LIMB_COUNT);
}

static int subtract_fixed_224(MalbolgeGuestMathFixed224 *output,
                              const MalbolgeGuestMathFixed224 *left,
                              const MalbolgeGuestMathFixed224 *right) {
  return subtract_fixed_limbs(output->limbs, left->limbs, right->limbs,
                              FIXED_224_LIMB_COUNT);
}

static int fixed_224_is_zero(const MalbolgeGuestMathFixed224 *value) {
  return fixed_limbs_is_zero(value->limbs, FIXED_224_LIMB_COUNT);
}

static int fixed_224_below_two_neg64(
    const MalbolgeGuestMathFixed224 *value) {
  return value->limbs[5] == UINT32_C(0) &&
         value->limbs[6] == UINT32_C(0) &&
         value->limbs[7] == UINT32_C(0);
}

static int exact_ratio_interval_224(
    const MalbolgeGuestMathExactRatio *input,
    MalbolgeGuestMathFixed224Interval *output) {
  MalbolgeGuestMathFixed224 lower;
  MalbolgeGuestMathFixed224 upper;
  uint64_t remainder = UINT64_C(0);
  int32_t shift = INT32_C(0);
  uint32_t bit_index = UINT32_C(64);
  uint32_t trailing = UINT32_C(0);

  if (output == NULL || !valid_fixed_residual(input)) {
    return 0;
  }
  zero_fixed_224(&lower);
  zero_fixed_224(&upper);
  if (input->numerator == UINT64_C(0)) {
    copy_fixed_224(&output->lower, lower.limbs);
    copy_fixed_224(&output->upper, upper.limbs);
    return 1;
  }
  shift = input->exponent_delta + FIXED_224_FRACTION_BITS;
  if (shift < INT32_C(0)) {
    increment_fixed_224(&upper);
    copy_fixed_224(&output->lower, lower.limbs);
    copy_fixed_224(&output->upper, upper.limbs);
    return 1;
  }
  while (bit_index != UINT32_C(0)) {
    uint32_t quotient_bit = UINT32_C(0);
    --bit_index;
    quotient_bit = divide_stream_bit(
        input->denominator, &remainder,
        (uint32_t)((input->numerator >> bit_index) & UINT64_C(1)));
    shift_fixed_limbs_bit(lower.limbs, FIXED_224_LIMB_COUNT, quotient_bit);
  }
  trailing = (uint32_t)shift;
  while (trailing != UINT32_C(0)) {
    const uint32_t quotient_bit =
        divide_stream_bit(input->denominator, &remainder, UINT32_C(0));
    shift_fixed_limbs_bit(lower.limbs, FIXED_224_LIMB_COUNT, quotient_bit);
    --trailing;
  }
  copy_fixed_224(&upper, lower.limbs);
  if (remainder != UINT64_C(0)) {
    increment_fixed_224(&upper);
  }
  copy_fixed_224(&output->lower, lower.limbs);
  copy_fixed_224(&output->upper, upper.limbs);
  return 1;
}

static void multiply_interval_224(
    const MalbolgeGuestMathFixed224Interval *left,
    const MalbolgeGuestMathFixed224Interval *right,
    MalbolgeGuestMathFixed224Interval *output) {
  uint32_t discarded = UINT32_C(0);
  multiply_fixed_limbs_floor(left->lower.limbs, right->lower.limbs,
                             FIXED_224_LIMB_COUNT, UINT32_C(7),
                             output->lower.limbs, &discarded);
  multiply_fixed_limbs_floor(left->upper.limbs, right->upper.limbs,
                             FIXED_224_LIMB_COUNT, UINT32_C(7),
                             output->upper.limbs, &discarded);
  if (discarded != UINT32_C(0)) {
    increment_fixed_224(&output->upper);
  }
}

static void multiply_fixed_224_small(MalbolgeGuestMathFixed224 *value,
                                     uint32_t factor) {
  multiply_fixed_limbs_small(value->limbs, FIXED_224_LIMB_COUNT, factor);
}

static uint32_t divide_fixed_224_small_floor(
    const MalbolgeGuestMathFixed224 *input, uint32_t divisor,
    MalbolgeGuestMathFixed224 *output) {
  return divide_fixed_limbs_small_floor(input->limbs, FIXED_224_LIMB_COUNT,
                                        divisor, output->limbs);
}

static void divide_interval_224_small(MalbolgeGuestMathFixed224Interval *value,
                                      uint32_t divisor) {
  MalbolgeGuestMathFixed224 lower;
  MalbolgeGuestMathFixed224 upper;
  const uint32_t upper_remainder =
      divide_fixed_224_small_floor(&value->upper, divisor, &upper);
  (void)divide_fixed_224_small_floor(&value->lower, divisor, &lower);
  if (upper_remainder != UINT32_C(0)) {
    increment_fixed_224(&upper);
  }
  copy_fixed_224(&value->lower, lower.limbs);
  copy_fixed_224(&value->upper, upper.limbs);
}

static int subtract_interval_224(
    MalbolgeGuestMathFixed224Interval *value,
    const MalbolgeGuestMathFixed224Interval *term) {
  MalbolgeGuestMathFixed224 lower;
  MalbolgeGuestMathFixed224 upper;
  if (!subtract_fixed_224(&lower, &value->lower, &term->upper) ||
      !subtract_fixed_224(&upper, &value->upper, &term->lower)) {
    return 0;
  }
  copy_fixed_224(&value->lower, lower.limbs);
  copy_fixed_224(&value->upper, upper.limbs);
  return 1;
}

static void add_interval_224(MalbolgeGuestMathFixed224Interval *value,
                             const MalbolgeGuestMathFixed224Interval *term) {
  add_fixed_limbs(value->lower.limbs, term->lower.limbs,
                  FIXED_224_LIMB_COUNT);
  add_fixed_limbs(value->upper.limbs, term->upper.limbs,
                  FIXED_224_LIMB_COUNT);
}

static int atan_residual_interval_224(
    const MalbolgeGuestMathExactRatio *input,
    MalbolgeGuestMathFixed224Interval *output) {
  MalbolgeGuestMathFixed224Interval x;
  MalbolgeGuestMathFixed224Interval square;
  MalbolgeGuestMathFixed224Interval term;
  MalbolgeGuestMathFixed224Interval sum;
  MalbolgeGuestMathFixed224 cutoff;
  MalbolgeGuestMathFixed224Interval truncation;
  uint32_t index = UINT32_C(1);

  if (output == NULL || !exact_ratio_interval_224(input, &x)) {
    return 0;
  }
  copy_fixed_224(&cutoff, ATAN_CUT_UPPER_224);
  if (compare_fixed_224(&x.upper, &cutoff) > 0) {
    return 0;
  }
  if (fixed_224_is_zero(&x.lower)) {
    copy_fixed_224(&output->lower, x.lower.limbs);
    copy_fixed_224(&output->upper, x.upper.limbs);
    return 1;
  }
  if (fixed_224_below_two_neg64(&x.upper)) {
    MalbolgeGuestMathFixed224 lower;
    copy_fixed_224(&lower, x.lower.limbs);
    decrement_fixed_224(&lower);
    copy_fixed_224(&output->lower, lower.limbs);
    copy_fixed_224(&output->upper, x.upper.limbs);
    return 1;
  }
  multiply_interval_224(&x, &x, &square);
  copy_fixed_224(&term.lower, x.lower.limbs);
  copy_fixed_224(&term.upper, x.upper.limbs);
  copy_fixed_224(&sum.lower, x.lower.limbs);
  copy_fixed_224(&sum.upper, x.upper.limbs);
  while (index < ATAN_224_SERIES_TERMS) {
    const uint32_t previous_denominator = (UINT32_C(2) * index) - UINT32_C(1);
    const uint32_t denominator = (UINT32_C(2) * index) + UINT32_C(1);
    MalbolgeGuestMathFixed224Interval next;
    multiply_interval_224(&term, &square, &next);
    multiply_fixed_224_small(&next.lower, previous_denominator);
    multiply_fixed_224_small(&next.upper, previous_denominator);
    divide_interval_224_small(&next, denominator);
    copy_fixed_224(&term.lower, next.lower.limbs);
    copy_fixed_224(&term.upper, next.upper.limbs);
    if ((index & UINT32_C(1)) != UINT32_C(0)) {
      if (!subtract_interval_224(&sum, &term)) {
        return 0;
      }
    } else {
      add_interval_224(&sum, &term);
    }
    ++index;
  }
  multiply_interval_224(&term, &square, &truncation);
  multiply_fixed_224_small(&truncation.lower,
                           (UINT32_C(2) * index) - UINT32_C(1));
  multiply_fixed_224_small(&truncation.upper,
                           (UINT32_C(2) * index) - UINT32_C(1));
  divide_interval_224_small(&truncation,
                            (UINT32_C(2) * index) + UINT32_C(1));
  add_fixed_limbs(sum.upper.limbs, truncation.upper.limbs,
                  FIXED_224_LIMB_COUNT);
  copy_fixed_224(&output->lower, sum.lower.limbs);
  copy_fixed_224(&output->upper, sum.upper.limbs);
  return 1;
}

static int atan2_base_interval_224(
    MalbolgeGuestMathAtan2QuarterPiBase base,
    MalbolgeGuestMathFixed224Interval *output) {
  uint32_t remaining = (uint32_t)base;
  if (output == NULL || remaining > UINT32_C(4)) {
    return 0;
  }
  zero_fixed_224(&output->lower);
  zero_fixed_224(&output->upper);
  while (remaining != UINT32_C(0)) {
    add_fixed_limbs(output->lower.limbs, QUARTER_PI_LOWER_224,
                    FIXED_224_LIMB_COUNT);
    add_fixed_limbs(output->upper.limbs, QUARTER_PI_UPPER_224,
                    FIXED_224_LIMB_COUNT);
    --remaining;
  }
  return 1;
}

int malbolge_guest_math_atan2_interval224(
    uint64_t y_bits, uint64_t x_bits,
    MalbolgeGuestMathAtan2Interval224 *output) {
  MalbolgeGuestMathAtan2KernelPlan plan;
  MalbolgeGuestMathFixed224Interval base;
  MalbolgeGuestMathFixed224Interval residual;
  MalbolgeGuestMathFixed224Interval staged;

  if (output == NULL ||
      !malbolge_guest_math_atan2_kernel_plan(y_bits, x_bits, &plan) ||
      !atan2_base_interval_224(plan.quarter_pi_base, &base) ||
      !atan_residual_interval_224(&plan.residual, &residual)) {
    return 0;
  }
  copy_fixed_224(&staged.lower, base.lower.limbs);
  copy_fixed_224(&staged.upper, base.upper.limbs);
  if (plan.ratio_operation == MALBOLGE_GUEST_MATH_ATAN2_RATIO_ADD) {
    add_interval_224(&staged, &residual);
  } else if (!subtract_interval_224(&staged, &residual)) {
    return 0;
  }
  copy_fixed_224(&output->magnitude.lower, staged.lower.limbs);
  copy_fixed_224(&output->magnitude.upper, staged.upper.limbs);
  output->negative = plan.negative;
  return 1;
}

static const uint32_t QUARTER_PI_LOWER_256[9] = {
    UINT32_C(0x3b139b22), UINT32_C(0x020bbea6), UINT32_C(0x8a67cc74),
    UINT32_C(0x29024e08), UINT32_C(0x80dc1cd1), UINT32_C(0xc4c6628b),
    UINT32_C(0x2168c234), UINT32_C(0xc90fdaa2), UINT32_C(0)};
static const uint32_t QUARTER_PI_UPPER_256[9] = {
    UINT32_C(0x3b139b23), UINT32_C(0x020bbea6), UINT32_C(0x8a67cc74),
    UINT32_C(0x29024e08), UINT32_C(0x80dc1cd1), UINT32_C(0xc4c6628b),
    UINT32_C(0x2168c234), UINT32_C(0xc90fdaa2), UINT32_C(0)};
static const uint32_t ATAN_CUT_UPPER_256[9] = {
    UINT32_C(0x0a0a0a0b), UINT32_C(0x0a0a0a0a), UINT32_C(0x0a0a0a0a),
    UINT32_C(0x0a0a0a0a), UINT32_C(0x0a0a0a0a), UINT32_C(0x0a0a0a0a),
    UINT32_C(0x0a0a0a0a), UINT32_C(0x6a0a0a0a), UINT32_C(0)};

static void copy_fixed_256(MalbolgeGuestMathFixed256 *output,
                           const uint32_t source[9]) {
  copy_fixed_limbs(output->limbs, source, FIXED_256_LIMB_COUNT);
}

static void zero_fixed_256(MalbolgeGuestMathFixed256 *value) {
  zero_fixed_limbs(value->limbs, FIXED_256_LIMB_COUNT);
}

static void increment_fixed_256(MalbolgeGuestMathFixed256 *value) {
  increment_fixed_limbs(value->limbs, FIXED_256_LIMB_COUNT);
}

static void decrement_fixed_256(MalbolgeGuestMathFixed256 *value) {
  decrement_fixed_limbs(value->limbs, FIXED_256_LIMB_COUNT);
}

static int compare_fixed_256(const MalbolgeGuestMathFixed256 *left,
                             const MalbolgeGuestMathFixed256 *right) {
  return compare_fixed_limbs(left->limbs, right->limbs,
                             FIXED_256_LIMB_COUNT);
}

static int subtract_fixed_256(MalbolgeGuestMathFixed256 *output,
                              const MalbolgeGuestMathFixed256 *left,
                              const MalbolgeGuestMathFixed256 *right) {
  return subtract_fixed_limbs(output->limbs, left->limbs, right->limbs,
                              FIXED_256_LIMB_COUNT);
}

static int fixed_256_is_zero(const MalbolgeGuestMathFixed256 *value) {
  return fixed_limbs_is_zero(value->limbs, FIXED_256_LIMB_COUNT);
}

static int fixed_256_below_two_neg64(
    const MalbolgeGuestMathFixed256 *value) {
  return value->limbs[6] == UINT32_C(0) &&
         value->limbs[7] == UINT32_C(0) &&
         value->limbs[8] == UINT32_C(0);
}

static int exact_ratio_interval_256(
    const MalbolgeGuestMathExactRatio *input,
    MalbolgeGuestMathFixed256Interval *output) {
  MalbolgeGuestMathFixed256 lower;
  MalbolgeGuestMathFixed256 upper;
  uint64_t remainder = UINT64_C(0);
  int32_t shift = INT32_C(0);
  uint32_t bit_index = UINT32_C(64);
  uint32_t trailing = UINT32_C(0);

  if (output == NULL || !valid_fixed_residual(input)) {
    return 0;
  }
  zero_fixed_256(&lower);
  zero_fixed_256(&upper);
  if (input->numerator == UINT64_C(0)) {
    copy_fixed_256(&output->lower, lower.limbs);
    copy_fixed_256(&output->upper, upper.limbs);
    return 1;
  }
  shift = input->exponent_delta + FIXED_256_FRACTION_BITS;
  if (shift < INT32_C(0)) {
    increment_fixed_256(&upper);
    copy_fixed_256(&output->lower, lower.limbs);
    copy_fixed_256(&output->upper, upper.limbs);
    return 1;
  }
  while (bit_index != UINT32_C(0)) {
    uint32_t quotient_bit = UINT32_C(0);
    --bit_index;
    quotient_bit = divide_stream_bit(
        input->denominator, &remainder,
        (uint32_t)((input->numerator >> bit_index) & UINT64_C(1)));
    shift_fixed_limbs_bit(lower.limbs, FIXED_256_LIMB_COUNT, quotient_bit);
  }
  trailing = (uint32_t)shift;
  while (trailing != UINT32_C(0)) {
    const uint32_t quotient_bit =
        divide_stream_bit(input->denominator, &remainder, UINT32_C(0));
    shift_fixed_limbs_bit(lower.limbs, FIXED_256_LIMB_COUNT, quotient_bit);
    --trailing;
  }
  copy_fixed_256(&upper, lower.limbs);
  if (remainder != UINT64_C(0)) {
    increment_fixed_256(&upper);
  }
  copy_fixed_256(&output->lower, lower.limbs);
  copy_fixed_256(&output->upper, upper.limbs);
  return 1;
}

static void multiply_interval_256(
    const MalbolgeGuestMathFixed256Interval *left,
    const MalbolgeGuestMathFixed256Interval *right,
    MalbolgeGuestMathFixed256Interval *output) {
  uint32_t discarded = UINT32_C(0);
  multiply_fixed_limbs_floor(left->lower.limbs, right->lower.limbs,
                             FIXED_256_LIMB_COUNT, UINT32_C(8),
                             output->lower.limbs, &discarded);
  multiply_fixed_limbs_floor(left->upper.limbs, right->upper.limbs,
                             FIXED_256_LIMB_COUNT, UINT32_C(8),
                             output->upper.limbs, &discarded);
  if (discarded != UINT32_C(0)) {
    increment_fixed_256(&output->upper);
  }
}

static void multiply_fixed_256_small(MalbolgeGuestMathFixed256 *value,
                                     uint32_t factor) {
  multiply_fixed_limbs_small(value->limbs, FIXED_256_LIMB_COUNT, factor);
}

static uint32_t divide_fixed_256_small_floor(
    const MalbolgeGuestMathFixed256 *input, uint32_t divisor,
    MalbolgeGuestMathFixed256 *output) {
  return divide_fixed_limbs_small_floor(input->limbs, FIXED_256_LIMB_COUNT,
                                        divisor, output->limbs);
}

static void divide_interval_256_small(MalbolgeGuestMathFixed256Interval *value,
                                      uint32_t divisor) {
  MalbolgeGuestMathFixed256 lower;
  MalbolgeGuestMathFixed256 upper;
  const uint32_t upper_remainder =
      divide_fixed_256_small_floor(&value->upper, divisor, &upper);
  (void)divide_fixed_256_small_floor(&value->lower, divisor, &lower);
  if (upper_remainder != UINT32_C(0)) {
    increment_fixed_256(&upper);
  }
  copy_fixed_256(&value->lower, lower.limbs);
  copy_fixed_256(&value->upper, upper.limbs);
}

static int subtract_interval_256(
    MalbolgeGuestMathFixed256Interval *value,
    const MalbolgeGuestMathFixed256Interval *term) {
  MalbolgeGuestMathFixed256 lower;
  MalbolgeGuestMathFixed256 upper;
  if (!subtract_fixed_256(&lower, &value->lower, &term->upper) ||
      !subtract_fixed_256(&upper, &value->upper, &term->lower)) {
    return 0;
  }
  copy_fixed_256(&value->lower, lower.limbs);
  copy_fixed_256(&value->upper, upper.limbs);
  return 1;
}

static void add_interval_256(MalbolgeGuestMathFixed256Interval *value,
                             const MalbolgeGuestMathFixed256Interval *term) {
  add_fixed_limbs(value->lower.limbs, term->lower.limbs,
                  FIXED_256_LIMB_COUNT);
  add_fixed_limbs(value->upper.limbs, term->upper.limbs,
                  FIXED_256_LIMB_COUNT);
}

static int atan_residual_interval_256(
    const MalbolgeGuestMathExactRatio *input,
    MalbolgeGuestMathFixed256Interval *output) {
  MalbolgeGuestMathFixed256Interval x;
  MalbolgeGuestMathFixed256Interval square;
  MalbolgeGuestMathFixed256Interval term;
  MalbolgeGuestMathFixed256Interval sum;
  MalbolgeGuestMathFixed256 cutoff;
  MalbolgeGuestMathFixed256Interval truncation;
  uint32_t index = UINT32_C(1);

  if (output == NULL || !exact_ratio_interval_256(input, &x)) {
    return 0;
  }
  copy_fixed_256(&cutoff, ATAN_CUT_UPPER_256);
  if (compare_fixed_256(&x.upper, &cutoff) > 0) {
    return 0;
  }
  if (fixed_256_is_zero(&x.lower)) {
    copy_fixed_256(&output->lower, x.lower.limbs);
    copy_fixed_256(&output->upper, x.upper.limbs);
    return 1;
  }
  if (fixed_256_below_two_neg64(&x.upper)) {
    MalbolgeGuestMathFixed256 lower;
    copy_fixed_256(&lower, x.lower.limbs);
    decrement_fixed_256(&lower);
    copy_fixed_256(&output->lower, lower.limbs);
    copy_fixed_256(&output->upper, x.upper.limbs);
    return 1;
  }
  multiply_interval_256(&x, &x, &square);
  copy_fixed_256(&term.lower, x.lower.limbs);
  copy_fixed_256(&term.upper, x.upper.limbs);
  copy_fixed_256(&sum.lower, x.lower.limbs);
  copy_fixed_256(&sum.upper, x.upper.limbs);
  while (index < ATAN_256_SERIES_TERMS) {
    const uint32_t previous_denominator = (UINT32_C(2) * index) - UINT32_C(1);
    const uint32_t denominator = (UINT32_C(2) * index) + UINT32_C(1);
    MalbolgeGuestMathFixed256Interval next;
    multiply_interval_256(&term, &square, &next);
    multiply_fixed_256_small(&next.lower, previous_denominator);
    multiply_fixed_256_small(&next.upper, previous_denominator);
    divide_interval_256_small(&next, denominator);
    copy_fixed_256(&term.lower, next.lower.limbs);
    copy_fixed_256(&term.upper, next.upper.limbs);
    if ((index & UINT32_C(1)) != UINT32_C(0)) {
      if (!subtract_interval_256(&sum, &term)) {
        return 0;
      }
    } else {
      add_interval_256(&sum, &term);
    }
    ++index;
  }
  multiply_interval_256(&term, &square, &truncation);
  multiply_fixed_256_small(&truncation.lower,
                           (UINT32_C(2) * index) - UINT32_C(1));
  multiply_fixed_256_small(&truncation.upper,
                           (UINT32_C(2) * index) - UINT32_C(1));
  divide_interval_256_small(&truncation,
                            (UINT32_C(2) * index) + UINT32_C(1));
  add_fixed_limbs(sum.upper.limbs, truncation.upper.limbs,
                  FIXED_256_LIMB_COUNT);
  copy_fixed_256(&output->lower, sum.lower.limbs);
  copy_fixed_256(&output->upper, sum.upper.limbs);
  return 1;
}

static int atan2_base_interval_256(
    MalbolgeGuestMathAtan2QuarterPiBase base,
    MalbolgeGuestMathFixed256Interval *output) {
  uint32_t remaining = (uint32_t)base;
  if (output == NULL || remaining > UINT32_C(4)) {
    return 0;
  }
  zero_fixed_256(&output->lower);
  zero_fixed_256(&output->upper);
  while (remaining != UINT32_C(0)) {
    add_fixed_limbs(output->lower.limbs, QUARTER_PI_LOWER_256,
                    FIXED_256_LIMB_COUNT);
    add_fixed_limbs(output->upper.limbs, QUARTER_PI_UPPER_256,
                    FIXED_256_LIMB_COUNT);
    --remaining;
  }
  return 1;
}

int malbolge_guest_math_atan2_interval256(
    uint64_t y_bits, uint64_t x_bits,
    MalbolgeGuestMathAtan2Interval256 *output) {
  MalbolgeGuestMathAtan2KernelPlan plan;
  MalbolgeGuestMathFixed256Interval base;
  MalbolgeGuestMathFixed256Interval residual;
  MalbolgeGuestMathFixed256Interval staged;

  if (output == NULL ||
      !malbolge_guest_math_atan2_kernel_plan(y_bits, x_bits, &plan) ||
      !atan2_base_interval_256(plan.quarter_pi_base, &base) ||
      !atan_residual_interval_256(&plan.residual, &residual)) {
    return 0;
  }
  copy_fixed_256(&staged.lower, base.lower.limbs);
  copy_fixed_256(&staged.upper, base.upper.limbs);
  if (plan.ratio_operation == MALBOLGE_GUEST_MATH_ATAN2_RATIO_ADD) {
    add_interval_256(&staged, &residual);
  } else if (!subtract_interval_256(&staged, &residual)) {
    return 0;
  }
  copy_fixed_256(&output->magnitude.lower, staged.lower.limbs);
  copy_fixed_256(&output->magnitude.upper, staged.upper.limbs);
  output->negative = plan.negative;
  return 1;
}

static uint32_t fixed_limbs_bit(const uint32_t *value, uint32_t position) {
  return (value[position / UINT32_C(32)] >> (position % UINT32_C(32))) &
         UINT32_C(1);
}

static int32_t fixed_limbs_high_bit(const uint32_t *value,
                                    uint32_t limb_count) {
  uint32_t limb_index = limb_count;
  while (limb_index != UINT32_C(0)) {
    uint32_t bit_index = UINT32_C(32);
    --limb_index;
    if (value[limb_index] == UINT32_C(0)) {
      continue;
    }
    while (bit_index != UINT32_C(0)) {
      --bit_index;
      if (((value[limb_index] >> bit_index) & UINT32_C(1)) != UINT32_C(0)) {
        return (int32_t)((limb_index * UINT32_C(32)) + bit_index);
      }
    }
  }
  return INT32_C(-1);
}

static uint32_t fixed_limbs_any_below(const uint32_t *value, uint32_t limit) {
  const uint32_t full_limbs = limit / UINT32_C(32);
  const uint32_t partial_bits = limit % UINT32_C(32);
  uint32_t limb_index = UINT32_C(0);

  while (limb_index < full_limbs) {
    if (value[limb_index] != UINT32_C(0)) {
      return UINT32_C(1);
    }
    ++limb_index;
  }
  if (partial_bits != UINT32_C(0)) {
    const uint32_t mask = (UINT32_C(1) << partial_bits) - UINT32_C(1);
    if ((value[full_limbs] & mask) != UINT32_C(0)) {
      return UINT32_C(1);
    }
  }
  return UINT32_C(0);
}

static uint64_t fixed_limbs_nearest_binary64(const uint32_t *value,
                                             uint32_t limb_count,
                                             int32_t fraction_bits) {
  int32_t high = fixed_limbs_high_bit(value, limb_count);
  uint64_t significand = UINT64_C(0);
  uint32_t offset = UINT32_C(0);
  int32_t guard_position = INT32_C(-1);
  uint32_t guard = UINT32_C(0);
  uint32_t sticky = UINT32_C(0);
  uint64_t raw_exponent = UINT64_C(0);

  if (high < INT32_C(0)) {
    return UINT64_C(0);
  }
  while (offset < UINT32_C(53)) {
    significand <<= UINT32_C(1);
    if (high >= (int32_t)offset) {
      significand |= fixed_limbs_bit(value, (uint32_t)(high - (int32_t)offset));
    }
    ++offset;
  }
  guard_position = high - INT32_C(53);
  if (guard_position >= INT32_C(0)) {
    guard = fixed_limbs_bit(value, (uint32_t)guard_position);
    sticky = fixed_limbs_any_below(value, (uint32_t)guard_position);
  }
  if (guard != UINT32_C(0) &&
      (sticky != UINT32_C(0) || (significand & UINT64_C(1)) != UINT64_C(0))) {
    ++significand;
  }
  if (significand == (UINT64_C(1) << UINT32_C(53))) {
    significand >>= UINT32_C(1);
    ++high;
  }
  raw_exponent =
      (uint64_t)(high - fraction_bits + BINARY64_EXPONENT_BIAS);
  return (raw_exponent << BINARY64_EXPONENT_SHIFT) |
         (significand & BINARY64_FRACTION);
}

static int fixed_limbs_unique_binary64(
    const uint32_t *lower, const uint32_t *upper, uint32_t limb_count,
    int32_t fraction_bits, uint64_t *output_bits) {
  uint64_t lower_bits = UINT64_C(0);
  uint64_t upper_bits = UINT64_C(0);
  if (output_bits == NULL ||
      compare_fixed_limbs(lower, upper, limb_count) > 0) {
    return 0;
  }
  lower_bits = fixed_limbs_nearest_binary64(lower, limb_count, fraction_bits);
  upper_bits = fixed_limbs_nearest_binary64(upper, limb_count, fraction_bits);
  if (lower_bits != upper_bits) {
    return 0;
  }
  *output_bits = lower_bits;
  return 1;
}

int malbolge_guest_math_fixed192_unique_binary64(
    const MalbolgeGuestMathFixed192Interval *input, uint64_t *output_bits) {
  if (input == NULL) {
    return 0;
  }
  return fixed_limbs_unique_binary64(
      input->lower.limbs, input->upper.limbs, FIXED_192_LIMB_COUNT,
      FIXED_192_FRACTION_BITS, output_bits);
}

int malbolge_guest_math_fixed224_unique_binary64(
    const MalbolgeGuestMathFixed224Interval *input, uint64_t *output_bits) {
  if (input == NULL) {
    return 0;
  }
  return fixed_limbs_unique_binary64(
      input->lower.limbs, input->upper.limbs, FIXED_224_LIMB_COUNT,
      FIXED_224_FRACTION_BITS, output_bits);
}

int malbolge_guest_math_fixed256_unique_binary64(
    const MalbolgeGuestMathFixed256Interval *input, uint64_t *output_bits) {
  if (input == NULL) {
    return 0;
  }
  return fixed_limbs_unique_binary64(
      input->lower.limbs, input->upper.limbs, FIXED_256_LIMB_COUNT,
      FIXED_256_FRACTION_BITS, output_bits);
}

int malbolge_guest_math_fixed256_candidates(
    const MalbolgeGuestMathFixed256Interval *input,
    MalbolgeGuestMathAtan2Candidates *output) {
  MalbolgeGuestMathAtan2Candidates staged;
  uint64_t lower_bits = UINT64_C(0);
  uint64_t upper_bits = UINT64_C(0);

  if (input == NULL || output == NULL ||
      compare_fixed_limbs(input->lower.limbs, input->upper.limbs,
                          FIXED_256_LIMB_COUNT) > 0) {
    return 0;
  }
  lower_bits = fixed_limbs_nearest_binary64(
      input->lower.limbs, FIXED_256_LIMB_COUNT, FIXED_256_FRACTION_BITS);
  upper_bits = fixed_limbs_nearest_binary64(
      input->upper.limbs, FIXED_256_LIMB_COUNT, FIXED_256_FRACTION_BITS);
  if (upper_bits < lower_bits || upper_bits - lower_bits > UINT64_C(1)) {
    return 0;
  }
  staged.count = lower_bits == upper_bits ? UINT32_C(1) : UINT32_C(2);
  staged.bits[0] = lower_bits;
  staged.bits[1] = upper_bits;
  *output = staged;
  return 1;
}

int malbolge_guest_math_fixed256_candidate_range(
    const MalbolgeGuestMathFixed256Interval *input,
    MalbolgeGuestMathAtan2CandidateRange *output) {
  MalbolgeGuestMathAtan2CandidateRange staged;
  if (input == NULL || output == NULL ||
      compare_fixed_limbs(input->lower.limbs, input->upper.limbs,
                          FIXED_256_LIMB_COUNT) > 0) {
    return 0;
  }
  staged.lower_bits = fixed_limbs_nearest_binary64(
      input->lower.limbs, FIXED_256_LIMB_COUNT, FIXED_256_FRACTION_BITS);
  staged.upper_bits = fixed_limbs_nearest_binary64(
      input->upper.limbs, FIXED_256_LIMB_COUNT, FIXED_256_FRACTION_BITS);
  if (staged.upper_bits < staged.lower_bits ||
      staged.upper_bits >= BINARY64_FOUR) {
    return 0;
  }
  output->lower_bits = staged.lower_bits;
  output->upper_bits = staged.upper_bits;
  return 1;
}

int malbolge_guest_math_atan2_q256_candidates(
    uint64_t y_bits, uint64_t x_bits,
    MalbolgeGuestMathAtan2Candidates *output) {
  MalbolgeGuestMathAtan2Interval256 interval;
  MalbolgeGuestMathAtan2Candidates staged;
  uint64_t lower_magnitude = UINT64_C(0);
  uint64_t upper_magnitude = UINT64_C(0);
  uint64_t sign = UINT64_C(0);

  if (output == NULL ||
      malbolge_guest_math_atan2_special(y_bits, x_bits).status !=
          MALBOLGE_GUEST_MATH_SPECIAL_KERNEL_REQUIRED ||
      !malbolge_guest_math_atan2_interval256(y_bits, x_bits, &interval)) {
    return 0;
  }
  if (!malbolge_guest_math_fixed256_candidates(&interval.magnitude, &staged)) {
    return 0;
  }
  lower_magnitude = staged.bits[0];
  upper_magnitude = staged.bits[staged.count - UINT32_C(1)];
  sign = interval.negative != UINT32_C(0) ? BINARY64_SIGN : UINT64_C(0);
  if (sign == UINT64_C(0)) {
    staged.bits[0] = lower_magnitude;
    staged.bits[1] = upper_magnitude;
  } else {
    staged.bits[0] = upper_magnitude | sign;
    staged.bits[1] = lower_magnitude | sign;
  }
  *output = staged;
  return 1;
}

int malbolge_guest_math_atan2_q256_candidate_range(
    uint64_t y_bits, uint64_t x_bits,
    MalbolgeGuestMathAtan2CandidateRange *output) {
  MalbolgeGuestMathAtan2Interval256 interval;
  MalbolgeGuestMathAtan2CandidateRange magnitude_range;
  MalbolgeGuestMathAtan2CandidateRange staged;
  const uint64_t sign = (y_bits & BINARY64_SIGN);

  if (output == NULL ||
      malbolge_guest_math_atan2_special(y_bits, x_bits).status !=
          MALBOLGE_GUEST_MATH_SPECIAL_KERNEL_REQUIRED ||
      !malbolge_guest_math_atan2_interval256(y_bits, x_bits, &interval) ||
      !malbolge_guest_math_fixed256_candidate_range(&interval.magnitude,
                                                    &magnitude_range)) {
    return 0;
  }
  if (interval.negative == UINT32_C(0)) {
    staged.lower_bits = magnitude_range.lower_bits;
    staged.upper_bits = magnitude_range.upper_bits;
  } else {
    staged.lower_bits = magnitude_range.upper_bits | sign;
    staged.upper_bits = magnitude_range.lower_bits | sign;
  }
  output->lower_bits = staged.lower_bits;
  output->upper_bits = staged.upper_bits;
  return 1;
}

static int atan2_candidates_valid(
    const MalbolgeGuestMathAtan2Candidates *candidates) {
  if (candidates == NULL || candidates->count == UINT32_C(0) ||
      candidates->count > UINT32_C(2)) {
    return 0;
  }
  if (candidates->count == UINT32_C(1)) {
    return 1;
  }
  if ((candidates->bits[0] & BINARY64_SIGN) !=
      (candidates->bits[1] & BINARY64_SIGN)) {
    return 0;
  }
  if ((candidates->bits[0] & BINARY64_SIGN) == UINT64_C(0)) {
    return candidates->bits[1] == candidates->bits[0] + UINT64_C(1);
  }
  return candidates->bits[0] == candidates->bits[1] + UINT64_C(1);
}

int malbolge_guest_math_atan2_refine_candidates_available(
    uint64_t y_bits, uint64_t x_bits,
    const MalbolgeGuestMathAtan2Candidates *candidates, uint32_t start_stage,
    uint32_t *scratch, uint32_t scratch_capacity,
    MalbolgeGuestMathAtan2CandidateProgress *output) {
  MalbolgeGuestMathAtan2CandidateProgress staged;
  uint32_t stage = start_stage;

  if (scratch == NULL || output == NULL ||
      !atan2_candidates_valid(candidates) ||
      malbolge_guest_math_atan2_special(y_bits, x_bits).status !=
          MALBOLGE_GUEST_MATH_SPECIAL_KERNEL_REQUIRED) {
    return 0;
  }
  for (;;) {
    uint32_t candidate_index = UINT32_C(0);
    uint32_t certified_count = UINT32_C(0);
    uint64_t certified_bits = UINT64_C(0);
    if (!malbolge_guest_math_atan2_refinement_plan(stage, &staged.plan)) {
      return 0;
    }
    staged.certified = UINT32_C(0);
    staged.bits = UINT64_C(0);
    if (scratch_capacity < staged.plan.required_scratch_limbs) {
      *output = staged;
      return 1;
    }
    while (candidate_index < candidates->count) {
      uint32_t certified = UINT32_C(0);
      if (!malbolge_guest_math_atan2_refinement_attempt(
              y_bits, x_bits, candidates->bits[candidate_index],
              staged.plan.fraction_limbs, staged.plan.terms, &certified,
              scratch,
              scratch_capacity)) {
        return 0;
      }
      if (certified != UINT32_C(0)) {
        ++certified_count;
        certified_bits = candidates->bits[candidate_index];
      }
      ++candidate_index;
    }
    if (certified_count > UINT32_C(1)) {
      return 0;
    }
    if (certified_count == UINT32_C(1)) {
      staged.certified = UINT32_C(1);
      staged.bits = certified_bits;
      *output = staged;
      return 1;
    }
    if (stage == UINT32_MAX) {
      return 0;
    }
    ++stage;
  }
}

int malbolge_guest_math_atan2_q256_refine_available(
    uint64_t y_bits, uint64_t x_bits, uint32_t start_stage, uint32_t *scratch,
    uint32_t scratch_capacity,
    MalbolgeGuestMathAtan2CandidateProgress *output) {
  MalbolgeGuestMathAtan2Candidates candidates;
  if (!malbolge_guest_math_atan2_q256_candidates(y_bits, x_bits, &candidates)) {
    return 0;
  }
  return malbolge_guest_math_atan2_refine_candidates_available(
      y_bits, x_bits, &candidates, start_stage, scratch, scratch_capacity,
      output);
}

static uint64_t atan2_candidate_key(uint64_t bits) {
  return (bits & BINARY64_SIGN) != UINT64_C(0) ? ~bits : bits;
}

static uint64_t atan2_candidate_from_key(uint64_t key, uint32_t negative) {
  return negative != UINT32_C(0) ? ~key : key;
}

static int atan2_candidate_range_valid(
    const MalbolgeGuestMathAtan2CandidateRange *range, uint32_t *negative) {
  const uint64_t lower_magnitude = range == NULL
                                       ? BINARY64_FOUR
                                       : range->lower_bits & ~BINARY64_SIGN;
  const uint64_t upper_magnitude = range == NULL
                                       ? BINARY64_FOUR
                                       : range->upper_bits & ~BINARY64_SIGN;
  uint32_t staged_negative = UINT32_C(0);
  if (range == NULL || negative == NULL || lower_magnitude >= BINARY64_FOUR ||
      upper_magnitude >= BINARY64_FOUR ||
      (range->lower_bits & BINARY64_SIGN) !=
          (range->upper_bits & BINARY64_SIGN)) {
    return 0;
  }
  staged_negative = (range->lower_bits & BINARY64_SIGN) != UINT64_C(0)
                        ? UINT32_C(1)
                        : UINT32_C(0);
  if (atan2_candidate_key(range->lower_bits) >
      atan2_candidate_key(range->upper_bits)) {
    return 0;
  }
  *negative = staged_negative;
  return 1;
}

static int atan2_candidate_cell_relation(
    const MalbolgeGuestMathAtan2KernelInput *ratio, uint64_t candidate_bits,
    const MalbolgeGuestMathAtan2RefinementPlan *plan, uint32_t *relation,
    uint32_t *scratch, uint32_t scratch_capacity) {
  MalbolgeGuestMathAtan2CellMidpoints cell;
  int32_t lower_comparison = INT32_C(0);
  int32_t upper_comparison = INT32_C(0);
  uint32_t staged = UINT32_C(0);

  if (ratio == NULL || plan == NULL || relation == NULL || scratch == NULL ||
      !malbolge_guest_math_atan2_cell_midpoints(candidate_bits, &cell) ||
      !malbolge_guest_math_midpoint_compare(
          ratio, &cell.lower, plan->fraction_limbs, plan->terms,
          &lower_comparison, scratch, scratch_capacity) ||
      !malbolge_guest_math_midpoint_compare(
          ratio, &cell.upper, plan->fraction_limbs, plan->terms,
          &upper_comparison, scratch, scratch_capacity)) {
    return 0;
  }
  if (lower_comparison == INT32_C(0) || upper_comparison == INT32_C(0)) {
    staged = UINT32_C(0);
  } else if (lower_comparison > INT32_C(0) &&
             upper_comparison < INT32_C(0)) {
    staged = UINT32_C(2);
  } else if (lower_comparison < INT32_C(0) &&
             upper_comparison < INT32_C(0)) {
    staged = UINT32_C(1);
  } else if (lower_comparison > INT32_C(0) &&
             upper_comparison > INT32_C(0)) {
    staged = UINT32_C(3);
  } else {
    return 0;
  }
  *relation = staged;
  return 1;
}

static void publish_atan2_range_progress(
    MalbolgeGuestMathAtan2RangeProgress *output,
    const MalbolgeGuestMathAtan2RangeProgress *input) {
  output->certified = input->certified;
  output->bits = input->bits;
  output->remaining.lower_bits = input->remaining.lower_bits;
  output->remaining.upper_bits = input->remaining.upper_bits;
  output->plan.stage = input->plan.stage;
  output->plan.fraction_limbs = input->plan.fraction_limbs;
  output->plan.terms = input->plan.terms;
  output->plan.required_scratch_limbs = input->plan.required_scratch_limbs;
}

int malbolge_guest_math_atan2_refine_range_available(
    uint64_t y_bits, uint64_t x_bits,
    const MalbolgeGuestMathAtan2CandidateRange *range, uint32_t start_stage,
    uint32_t *scratch, uint32_t scratch_capacity,
    MalbolgeGuestMathAtan2RangeProgress *output) {
  MalbolgeGuestMathAtan2RangeProgress staged;
  MalbolgeGuestMathAtan2KernelInput ratio;
  uint32_t negative = UINT32_C(0);
  uint32_t stage = start_stage;
  uint64_t lower_key = UINT64_C(0);
  uint64_t upper_key = UINT64_C(0);

  if (scratch == NULL || output == NULL ||
      !atan2_candidate_range_valid(range, &negative) ||
      malbolge_guest_math_atan2_special(y_bits, x_bits).status !=
          MALBOLGE_GUEST_MATH_SPECIAL_KERNEL_REQUIRED ||
      !malbolge_guest_math_atan2_kernel_input(y_bits, x_bits, &ratio)) {
    return 0;
  }
  lower_key = atan2_candidate_key(range->lower_bits);
  upper_key = atan2_candidate_key(range->upper_bits);
  for (;;) {
    uint32_t unresolved = UINT32_C(0);
    if (!malbolge_guest_math_atan2_refinement_plan(stage, &staged.plan)) {
      return 0;
    }
    staged.certified = UINT32_C(0);
    staged.bits = UINT64_C(0);
    staged.remaining.lower_bits =
        atan2_candidate_from_key(lower_key, negative);
    staged.remaining.upper_bits =
        atan2_candidate_from_key(upper_key, negative);
    if (scratch_capacity < staged.plan.required_scratch_limbs) {
      publish_atan2_range_progress(output, &staged);
      return 1;
    }
    while (lower_key <= upper_key) {
      const uint64_t middle_key =
          lower_key + ((upper_key - lower_key) >> UINT32_C(1));
      const uint64_t candidate_bits =
          atan2_candidate_from_key(middle_key, negative);
      uint32_t relation = UINT32_C(0);
      if (!atan2_candidate_cell_relation(
              &ratio, candidate_bits, &staged.plan, &relation, scratch,
              scratch_capacity)) {
        return 0;
      }
      if (relation == UINT32_C(0)) {
        unresolved = UINT32_C(1);
        break;
      }
      if (relation == UINT32_C(2)) {
        staged.certified = UINT32_C(1);
        staged.bits = candidate_bits;
        staged.remaining.lower_bits = candidate_bits;
        staged.remaining.upper_bits = candidate_bits;
        publish_atan2_range_progress(output, &staged);
        return 1;
      }
      if (relation == UINT32_C(1)) {
        if (middle_key == UINT64_C(0)) {
          return 0;
        }
        upper_key = middle_key - UINT64_C(1);
      } else {
        if (middle_key == UINT64_MAX) {
          return 0;
        }
        lower_key = middle_key + UINT64_C(1);
      }
    }
    if (lower_key > upper_key) {
      return 0;
    }
    staged.remaining.lower_bits =
        atan2_candidate_from_key(lower_key, negative);
    staged.remaining.upper_bits =
        atan2_candidate_from_key(upper_key, negative);
    if (unresolved == UINT32_C(0) || stage == UINT32_MAX) {
      return 0;
    }
    ++stage;
  }
}

int malbolge_guest_math_atan2_q256_refine_range_available(
    uint64_t y_bits, uint64_t x_bits, uint32_t start_stage, uint32_t *scratch,
    uint32_t scratch_capacity, MalbolgeGuestMathAtan2RangeProgress *output) {
  MalbolgeGuestMathAtan2CandidateRange range;
  if (!malbolge_guest_math_atan2_q256_candidate_range(y_bits, x_bits, &range)) {
    return 0;
  }
  return malbolge_guest_math_atan2_refine_range_available(
      y_bits, x_bits, &range, start_stage, scratch, scratch_capacity, output);
}

static void clear_atan2_refinement_plan(
    MalbolgeGuestMathAtan2RefinementPlan *plan) {
  plan->stage = UINT32_C(0);
  plan->fraction_limbs = UINT32_C(0);
  plan->terms = UINT32_C(0);
  plan->required_scratch_limbs = UINT32_C(0);
}

static void publish_atan2_handoff_progress(
    MalbolgeGuestMathAtan2HandoffProgress *output, uint64_t y_bits,
    uint64_t x_bits, MalbolgeGuestMathAtan2HandoffStatus status, uint64_t bits,
    const MalbolgeGuestMathAtan2CandidateRange *remaining,
    const MalbolgeGuestMathAtan2RefinementPlan *plan) {
  output->status = status;
  output->y_bits = y_bits;
  output->x_bits = x_bits;
  output->bits = bits;
  if (remaining == NULL) {
    output->remaining.lower_bits = bits;
    output->remaining.upper_bits = bits;
  } else {
    output->remaining.lower_bits = remaining->lower_bits;
    output->remaining.upper_bits = remaining->upper_bits;
  }
  if (plan == NULL) {
    clear_atan2_refinement_plan(&output->plan);
  } else {
    output->plan.stage = plan->stage;
    output->plan.fraction_limbs = plan->fraction_limbs;
    output->plan.terms = plan->terms;
    output->plan.required_scratch_limbs = plan->required_scratch_limbs;
  }
}

static int signed_atan2_range_from_q256_interval(
    const MalbolgeGuestMathAtan2Interval256 *interval,
    MalbolgeGuestMathAtan2CandidateRange *output) {
  MalbolgeGuestMathAtan2CandidateRange magnitude_range;
  if (interval == NULL || output == NULL || interval->negative > UINT32_C(1) ||
      !malbolge_guest_math_fixed256_candidate_range(&interval->magnitude,
                                                    &magnitude_range)) {
    return 0;
  }
  if (interval->negative == UINT32_C(0)) {
    output->lower_bits = magnitude_range.lower_bits;
    output->upper_bits = magnitude_range.upper_bits;
  } else {
    output->lower_bits = magnitude_range.upper_bits | BINARY64_SIGN;
    output->upper_bits = magnitude_range.lower_bits | BINARY64_SIGN;
  }
  return 1;
}

int malbolge_guest_math_atan2_refine_q256_interval_available(
    uint64_t y_bits, uint64_t x_bits,
    const MalbolgeGuestMathAtan2Interval256 *interval, uint32_t start_stage,
    uint32_t *scratch, uint32_t scratch_capacity,
    MalbolgeGuestMathAtan2HandoffProgress *output) {
  MalbolgeGuestMathAtan2CandidateRange range;
  MalbolgeGuestMathAtan2RefinementPlan first_plan;
  MalbolgeGuestMathAtan2RangeProgress refined;
  const uint32_t expected_negative =
      (y_bits & BINARY64_SIGN) != UINT64_C(0) ? UINT32_C(1) : UINT32_C(0);

  if (output == NULL || interval == NULL ||
      interval->negative != expected_negative ||
      malbolge_guest_math_atan2_special(y_bits, x_bits).status !=
          MALBOLGE_GUEST_MATH_SPECIAL_KERNEL_REQUIRED ||
      !signed_atan2_range_from_q256_interval(interval, &range) ||
      !malbolge_guest_math_atan2_refinement_plan(start_stage, &first_plan)) {
    return 0;
  }
  if (scratch == NULL || scratch_capacity < first_plan.required_scratch_limbs) {
    publish_atan2_handoff_progress(
        output, y_bits, x_bits, MALBOLGE_GUEST_MATH_ATAN2_HANDOFF_RETRY,
        UINT64_C(0), &range, &first_plan);
    return 1;
  }
  if (!malbolge_guest_math_atan2_refine_range_available(
          y_bits, x_bits, &range, start_stage, scratch, scratch_capacity,
          &refined)) {
    return 0;
  }
  publish_atan2_handoff_progress(
      output, y_bits, x_bits,
      refined.certified != UINT32_C(0)
          ? MALBOLGE_GUEST_MATH_ATAN2_HANDOFF_REFINED_RESOLVED
          : MALBOLGE_GUEST_MATH_ATAN2_HANDOFF_RETRY,
      refined.bits, &refined.remaining, &refined.plan);
  return 1;
}

int malbolge_guest_math_atan2_handoff_available(
    uint64_t y_bits, uint64_t x_bits, uint32_t start_stage, uint32_t *scratch,
    uint32_t scratch_capacity, MalbolgeGuestMathAtan2HandoffProgress *output) {
  MalbolgeGuestMathAtan2Interval interval;
  MalbolgeGuestMathAtan2Interval224 wide_interval;
  MalbolgeGuestMathAtan2Interval256 wider_interval;
  MalbolgeGuestMathSpecialResult special;
  uint64_t magnitude_bits = UINT64_C(0);
  uint64_t signed_bits = UINT64_C(0);

  if (output == NULL) {
    return 0;
  }
  special = malbolge_guest_math_atan2_special(y_bits, x_bits);
  if (special.status == MALBOLGE_GUEST_MATH_SPECIAL_INVALID) {
    return 0;
  }
  if (special.status == MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED) {
    publish_atan2_handoff_progress(
        output, y_bits, x_bits, MALBOLGE_GUEST_MATH_ATAN2_HANDOFF_FAST_RESOLVED,
        special.bits, NULL, NULL);
    return 1;
  }
  if (!malbolge_guest_math_atan2_interval(y_bits, x_bits, &interval)) {
    return 0;
  }
  if (malbolge_guest_math_fixed192_unique_binary64(&interval.magnitude,
                                                    &magnitude_bits)) {
    signed_bits = magnitude_bits |
                  (interval.negative != UINT32_C(0) ? BINARY64_SIGN
                                                     : UINT64_C(0));
    publish_atan2_handoff_progress(
        output, y_bits, x_bits, MALBOLGE_GUEST_MATH_ATAN2_HANDOFF_FAST_RESOLVED,
        signed_bits, NULL, NULL);
    return 1;
  }
  if (!malbolge_guest_math_atan2_interval224(y_bits, x_bits, &wide_interval)) {
    return 0;
  }
  if (malbolge_guest_math_fixed224_unique_binary64(&wide_interval.magnitude,
                                                    &magnitude_bits)) {
    signed_bits = magnitude_bits |
                  (wide_interval.negative != UINT32_C(0) ? BINARY64_SIGN
                                                          : UINT64_C(0));
    publish_atan2_handoff_progress(
        output, y_bits, x_bits, MALBOLGE_GUEST_MATH_ATAN2_HANDOFF_FAST_RESOLVED,
        signed_bits, NULL, NULL);
    return 1;
  }
  if (!malbolge_guest_math_atan2_interval256(y_bits, x_bits,
                                             &wider_interval)) {
    return 0;
  }
  if (malbolge_guest_math_fixed256_unique_binary64(&wider_interval.magnitude,
                                                    &magnitude_bits)) {
    signed_bits = magnitude_bits |
                  (wider_interval.negative != UINT32_C(0) ? BINARY64_SIGN
                                                           : UINT64_C(0));
    publish_atan2_handoff_progress(
        output, y_bits, x_bits, MALBOLGE_GUEST_MATH_ATAN2_HANDOFF_FAST_RESOLVED,
        signed_bits, NULL, NULL);
    return 1;
  }
  return malbolge_guest_math_atan2_refine_q256_interval_available(
      y_bits, x_bits, &wider_interval, start_stage, scratch, scratch_capacity,
      output);
}

static int atan2_refinement_plan_matches(
    const MalbolgeGuestMathAtan2RefinementPlan *input) {
  MalbolgeGuestMathAtan2RefinementPlan expected;
  if (input == NULL ||
      !malbolge_guest_math_atan2_refinement_plan(input->stage, &expected)) {
    return 0;
  }
  return input->fraction_limbs == expected.fraction_limbs &&
         input->terms == expected.terms &&
         input->required_scratch_limbs == expected.required_scratch_limbs;
}

int malbolge_guest_math_atan2_refinement_scratch_requirement(
    const MalbolgeGuestMathAtan2RefinementPlan *plan,
    MalbolgeGuestMathAtan2ScratchRequirement *output) {
  MalbolgeGuestMathAtan2ScratchRequirement staged;
  if (output == NULL || !atan2_refinement_plan_matches(plan) ||
      plan->required_scratch_limbs > UINT32_MAX / UINT32_C(4)) {
    return 0;
  }
  staged.limbs = plan->required_scratch_limbs;
  staged.bytes = plan->required_scratch_limbs * UINT32_C(4);
  staged.alignment = UINT32_C(4);
  output->limbs = staged.limbs;
  output->bytes = staged.bytes;
  output->alignment = staged.alignment;
  return 1;
}

int malbolge_guest_math_atan2_resume_handoff_available(
    uint64_t y_bits, uint64_t x_bits,
    const MalbolgeGuestMathAtan2HandoffProgress *previous, uint32_t *scratch,
    uint32_t scratch_capacity, MalbolgeGuestMathAtan2HandoffProgress *output) {
  MalbolgeGuestMathAtan2RangeProgress refined;

  if (previous == NULL || output == NULL ||
      previous->status != MALBOLGE_GUEST_MATH_ATAN2_HANDOFF_RETRY ||
      previous->y_bits != y_bits || previous->x_bits != x_bits ||
      !atan2_refinement_plan_matches(&previous->plan)) {
    return 0;
  }
  if (scratch == NULL ||
      scratch_capacity < previous->plan.required_scratch_limbs) {
    publish_atan2_handoff_progress(
        output, y_bits, x_bits, MALBOLGE_GUEST_MATH_ATAN2_HANDOFF_RETRY,
        UINT64_C(0), &previous->remaining, &previous->plan);
    return 1;
  }
  if (!malbolge_guest_math_atan2_refine_range_available(
          y_bits, x_bits, &previous->remaining, previous->plan.stage, scratch,
          scratch_capacity, &refined)) {
    return 0;
  }
  publish_atan2_handoff_progress(
      output, y_bits, x_bits,
      refined.certified != UINT32_C(0)
          ? MALBOLGE_GUEST_MATH_ATAN2_HANDOFF_REFINED_RESOLVED
          : MALBOLGE_GUEST_MATH_ATAN2_HANDOFF_RETRY,
      refined.bits, &refined.remaining, &refined.plan);
  return 1;
}

static uint32_t u64_bit_length(uint64_t value) {
  uint32_t bits = UINT32_C(0);
  while (value != UINT64_C(0)) {
    ++bits;
    value >>= UINT32_C(1);
  }
  return bits;
}

int malbolge_guest_math_dyadic_fixed_limb_count(
    const MalbolgeGuestMathDyadic *input, uint32_t fraction_bits,
    uint32_t *required_limbs) {
  uint64_t bit_count = UINT64_C(0);
  uint64_t limbs = UINT64_C(0);
  uint32_t numerator_bits = UINT32_C(0);

  if (input == NULL || required_limbs == NULL ||
      fraction_bits < input->denominator_shift ||
      input->negative > UINT32_C(1)) {
    return 0;
  }
  if (input->numerator == UINT64_C(0)) {
    *required_limbs = UINT32_C(1);
    return 1;
  }
  numerator_bits = u64_bit_length(input->numerator);
  bit_count = (uint64_t)numerator_bits +
              (uint64_t)(fraction_bits - input->denominator_shift);
  limbs = (bit_count + UINT64_C(31)) >> UINT32_C(5);
  if (limbs == UINT64_C(0) || limbs > UINT32_MAX) {
    return 0;
  }
  *required_limbs = (uint32_t)limbs;
  return 1;
}

int malbolge_guest_math_dyadic_write_fixed(
    const MalbolgeGuestMathDyadic *input, uint32_t fraction_bits,
    uint32_t *limbs, uint32_t limb_capacity) {
  uint32_t required = UINT32_C(0);
  uint32_t whole_shift = UINT32_C(0);
  uint32_t bit_shift = UINT32_C(0);
  uint32_t index = UINT32_C(0);
  uint64_t low = UINT64_C(0);
  uint64_t high = UINT64_C(0);

  if (limbs == NULL ||
      !malbolge_guest_math_dyadic_fixed_limb_count(input, fraction_bits,
                                                   &required) ||
      limb_capacity < required) {
    return 0;
  }
  while (index < required) {
    limbs[index] = UINT32_C(0);
    ++index;
  }
  if (input->numerator == UINT64_C(0)) {
    return 1;
  }
  whole_shift = (fraction_bits - input->denominator_shift) >> UINT32_C(5);
  bit_shift = (fraction_bits - input->denominator_shift) & UINT32_C(31);
  low = input->numerator << bit_shift;
  high = bit_shift == UINT32_C(0)
             ? UINT64_C(0)
             : input->numerator >> (UINT32_C(64) - bit_shift);
  limbs[whole_shift] = (uint32_t)low;
  if (whole_shift + UINT32_C(1) < required) {
    limbs[whole_shift + UINT32_C(1)] = (uint32_t)(low >> UINT32_C(32));
  }
  if (whole_shift + UINT32_C(2) < required) {
    limbs[whole_shift + UINT32_C(2)] = (uint32_t)high;
  }
  return 1;
}

int malbolge_guest_math_atan2_cell_midpoints(
    uint64_t output_bits, MalbolgeGuestMathAtan2CellMidpoints *output) {
  const uint64_t magnitude = output_bits & ~BINARY64_SIGN;
  MalbolgeGuestMathDyadic lower_positive;
  MalbolgeGuestMathDyadic upper_positive;
  MalbolgeGuestMathAtan2CellMidpoints staged;

  if (output == NULL || magnitude >= BINARY64_FOUR) {
    return 0;
  }
  if (magnitude == UINT64_C(0)) {
    staged.lower.numerator = UINT64_C(1);
    staged.lower.denominator_shift = UINT32_C(1075);
    staged.lower.negative = UINT32_C(1);
    staged.upper.numerator = UINT64_C(1);
    staged.upper.denominator_shift = UINT32_C(1075);
    staged.upper.negative = UINT32_C(0);
    *output = staged;
    return 1;
  }
  if (!positive_binary64_midpoint(magnitude - UINT64_C(1), magnitude,
                                  &lower_positive) ||
      !positive_binary64_midpoint(magnitude, magnitude + UINT64_C(1),
                                  &upper_positive)) {
    return 0;
  }
  if ((output_bits & BINARY64_SIGN) == UINT64_C(0)) {
    staged.lower = lower_positive;
    staged.upper = upper_positive;
  } else {
    staged.lower = upper_positive;
    staged.lower.negative = UINT32_C(1);
    staged.upper = lower_positive;
    staged.upper.negative = UINT32_C(1);
  }
  *output = staged;
  return 1;
}

int malbolge_guest_math_dyadic_lambert_argument_bounds(
    const MalbolgeGuestMathDyadic *midpoint,
    MalbolgeGuestMathLambertArgumentBounds *output) {
  MalbolgeGuestMathLambertArgumentBounds staged;
  uint32_t numerator_bits = UINT32_C(0);

  if (midpoint == NULL || output == NULL ||
      midpoint->numerator == UINT64_C(0) ||
      midpoint->negative > UINT32_C(1) ||
      (midpoint->denominator_shift != UINT32_C(0) &&
       (midpoint->numerator & UINT64_C(1)) == UINT64_C(0))) {
    return 0;
  }
  numerator_bits = u64_bit_length_local(midpoint->numerator);
  if (numerator_bits > UINT32_C(54) ||
      midpoint->denominator_shift > UINT32_C(107)) {
    return 0;
  }
  staged.numerator_bits = numerator_bits;
  staged.denominator_shift = midpoint->denominator_shift;
  staged.square_over_denominator_pow2_exponent_upper =
      (int32_t)(UINT32_C(2) * numerator_bits) -
      (int32_t)midpoint->denominator_shift;
  staged.normalizing_halvings =
      staged.square_over_denominator_pow2_exponent_upper > INT32_C(0)
          ? (uint32_t)staged.square_over_denominator_pow2_exponent_upper
          : UINT32_C(0);
  if (staged.normalizing_halvings > UINT32_C(56) ||
      staged.denominator_shift > UINT32_MAX - staged.normalizing_halvings) {
    return 0;
  }
  staged.normalized_denominator_shift =
      staged.denominator_shift + staged.normalizing_halvings;
  staged.normalized_scale_pow2_exponent_upper =
      staged.square_over_denominator_pow2_exponent_upper -
      (int32_t)staged.normalizing_halvings;
  output->numerator_bits = staged.numerator_bits;
  output->denominator_shift = staged.denominator_shift;
  output->square_over_denominator_pow2_exponent_upper =
      staged.square_over_denominator_pow2_exponent_upper;
  output->normalizing_halvings = staged.normalizing_halvings;
  output->normalized_denominator_shift = staged.normalized_denominator_shift;
  output->normalized_scale_pow2_exponent_upper =
      staged.normalized_scale_pow2_exponent_upper;
  return 1;
}

int malbolge_guest_math_atan2_separation_parameters(
    uint64_t y_bits, uint64_t x_bits, uint64_t candidate_bits,
    MalbolgeGuestMathAtan2SeparationParameters *output) {
  MalbolgeGuestMathAtan2KernelInput ratio;
  MalbolgeGuestMathAtan2CellMidpoints cell;
  MalbolgeGuestMathAtan2SeparationParameters staged;

  if (output == NULL ||
      malbolge_guest_math_atan2_special(y_bits, x_bits).status !=
          MALBOLGE_GUEST_MATH_SPECIAL_KERNEL_REQUIRED ||
      (candidate_bits & BINARY64_SIGN) != (y_bits & BINARY64_SIGN) ||
      !malbolge_guest_math_atan2_kernel_input(y_bits, x_bits, &ratio) ||
      !malbolge_guest_math_atan2_cell_midpoints(candidate_bits, &cell) ||
      !malbolge_guest_math_atan2_ratio_reduced_height(&ratio,
                                                      &staged.ratio_height) ||
      staged.ratio_height.numerator_bits > ATAN2_ADAPTIVE_NUMERATOR_BITS_MAX ||
      staged.ratio_height.denominator_bits >
          ATAN2_ADAPTIVE_DENOMINATOR_BITS_MAX) {
    return 0;
  }
  staged.lower_midpoint_shift = cell.lower.denominator_shift;
  staged.upper_midpoint_shift = cell.upper.denominator_shift;
  staged.midpoint_shift_max =
      staged.lower_midpoint_shift > staged.upper_midpoint_shift
          ? staged.lower_midpoint_shift
          : staged.upper_midpoint_shift;
  if (!malbolge_guest_math_dyadic_lambert_argument_bounds(
          &cell.lower, &staged.lower_lambert) ||
      !malbolge_guest_math_dyadic_lambert_argument_bounds(
          &cell.upper, &staged.upper_lambert)) {
    return 0;
  }
  staged.lambert_scale_pow2_exponent_upper =
      staged.lower_lambert.square_over_denominator_pow2_exponent_upper >
              staged.upper_lambert.square_over_denominator_pow2_exponent_upper
          ? staged.lower_lambert.square_over_denominator_pow2_exponent_upper
          : staged.upper_lambert.square_over_denominator_pow2_exponent_upper;
  if (staged.lambert_scale_pow2_exponent_upper >
      ATAN2_LAMBERT_SCALE_EXPONENT_MAX) {
    return 0;
  }
  output->ratio_height.numerator_bits = staged.ratio_height.numerator_bits;
  output->ratio_height.denominator_bits = staged.ratio_height.denominator_bits;
  output->ratio_height.height_bits = staged.ratio_height.height_bits;
  output->lower_midpoint_shift = staged.lower_midpoint_shift;
  output->upper_midpoint_shift = staged.upper_midpoint_shift;
  output->midpoint_shift_max = staged.midpoint_shift_max;
  output->lower_lambert = staged.lower_lambert;
  output->upper_lambert = staged.upper_lambert;
  output->lambert_scale_pow2_exponent_upper =
      staged.lambert_scale_pow2_exponent_upper;
  return 1;
}

int malbolge_guest_math_dyadic_exponential_argument_bounds(
    const MalbolgeGuestMathDyadic *midpoint,
    MalbolgeGuestMathExponentialArgumentBounds *output) {
  MalbolgeGuestMathExponentialArgumentBounds staged;
  uint32_t numerator_bits = UINT32_C(0);
  uint32_t alpha_numerator_bits = UINT32_C(0);
  uint32_t alpha_denominator_exponent = UINT32_C(0);
  uint32_t numerator_height_exponent = UINT32_C(0);
  uint32_t denominator_height_exponent = UINT32_C(0);

  if (midpoint == NULL || output == NULL ||
      midpoint->numerator == UINT64_C(0) ||
      midpoint->negative > UINT32_C(1) ||
      (midpoint->denominator_shift != UINT32_C(0) &&
       (midpoint->numerator & UINT64_C(1)) == UINT64_C(0))) {
    return 0;
  }
  numerator_bits = u64_bit_length_local(midpoint->numerator);
  if (midpoint->denominator_shift == UINT32_C(0)) {
    if (numerator_bits == UINT32_MAX) {
      return 0;
    }
    alpha_numerator_bits = numerator_bits + UINT32_C(1);
  } else {
    alpha_numerator_bits = numerator_bits;
    alpha_denominator_exponent = midpoint->denominator_shift - UINT32_C(1);
  }
  if (alpha_numerator_bits > UINT32_MAX / UINT32_C(2) ||
      alpha_denominator_exponent > (UINT32_MAX - UINT32_C(1)) / UINT32_C(2)) {
    return 0;
  }
  numerator_height_exponent = alpha_numerator_bits * UINT32_C(2);
  denominator_height_exponent =
      alpha_denominator_exponent * UINT32_C(2) + UINT32_C(1);
  staged.alpha_height_pow2_exponent_upper =
      numerator_height_exponent > denominator_height_exponent
          ? numerator_height_exponent
          : denominator_height_exponent;
  staged.inverse_denominator_bits = alpha_numerator_bits;
  staged.inverse_house_pow2_exponent_upper = alpha_denominator_exponent;
  output->alpha_height_pow2_exponent_upper =
      staged.alpha_height_pow2_exponent_upper;
  output->inverse_denominator_bits = staged.inverse_denominator_bits;
  output->inverse_house_pow2_exponent_upper =
      staged.inverse_house_pow2_exponent_upper;
  return 1;
}

int malbolge_guest_math_atan2_exponential_bridge_bounds(
    uint64_t y_bits, uint64_t x_bits, uint64_t candidate_bits,
    MalbolgeGuestMathAtan2ExponentialBridgeBounds *output) {
  MalbolgeGuestMathAtan2SeparationParameters separation;
  MalbolgeGuestMathAtan2CellMidpoints cell;
  MalbolgeGuestMathAtan2ExponentialBridgeBounds staged;

  if (output == NULL ||
      !malbolge_guest_math_atan2_separation_parameters(
          y_bits, x_bits, candidate_bits, &separation) ||
      !malbolge_guest_math_atan2_cell_midpoints(candidate_bits, &cell) ||
      !malbolge_guest_math_dyadic_exponential_argument_bounds(
          &cell.lower, &staged.lower_midpoint) ||
      !malbolge_guest_math_dyadic_exponential_argument_bounds(
          &cell.upper, &staged.upper_midpoint) ||
      separation.ratio_height.height_bits == UINT32_MAX) {
    return 0;
  }
  staged.linear_polynomial_height_pow2_exponent_upper =
      separation.ratio_height.height_bits + UINT32_C(1);
  staged.rational_denominator_bits = separation.ratio_height.denominator_bits;
  staged.alpha_height_pow2_exponent_upper =
      staged.lower_midpoint.alpha_height_pow2_exponent_upper >
              staged.upper_midpoint.alpha_height_pow2_exponent_upper
          ? staged.lower_midpoint.alpha_height_pow2_exponent_upper
          : staged.upper_midpoint.alpha_height_pow2_exponent_upper;
  staged.inverse_denominator_bits_max =
      staged.lower_midpoint.inverse_denominator_bits >
              staged.upper_midpoint.inverse_denominator_bits
          ? staged.lower_midpoint.inverse_denominator_bits
          : staged.upper_midpoint.inverse_denominator_bits;
  staged.inverse_house_pow2_exponent_upper =
      staged.lower_midpoint.inverse_house_pow2_exponent_upper >
              staged.upper_midpoint.inverse_house_pow2_exponent_upper
          ? staged.lower_midpoint.inverse_house_pow2_exponent_upper
          : staged.upper_midpoint.inverse_house_pow2_exponent_upper;
  output->linear_polynomial_height_pow2_exponent_upper =
      staged.linear_polynomial_height_pow2_exponent_upper;
  output->rational_denominator_bits = staged.rational_denominator_bits;
  output->lower_midpoint = staged.lower_midpoint;
  output->upper_midpoint = staged.upper_midpoint;
  output->alpha_height_pow2_exponent_upper =
      staged.alpha_height_pow2_exponent_upper;
  output->inverse_denominator_bits_max = staged.inverse_denominator_bits_max;
  output->inverse_house_pow2_exponent_upper =
      staged.inverse_house_pow2_exponent_upper;
  return 1;
}

int malbolge_guest_math_atan2_unique_binary64(
    uint64_t y_bits, uint64_t x_bits, uint64_t *output_bits) {
  MalbolgeGuestMathAtan2Interval interval;
  MalbolgeGuestMathAtan2Interval224 wide_interval;
  MalbolgeGuestMathAtan2Interval256 wider_interval;
  MalbolgeGuestMathSpecialResult special;
  uint64_t magnitude_bits = UINT64_C(0);

  if (output_bits == NULL) {
    return 0;
  }
  special = malbolge_guest_math_atan2_special(y_bits, x_bits);
  if (special.status == MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED) {
    *output_bits = special.bits;
    return 1;
  }
  if (!malbolge_guest_math_atan2_interval(y_bits, x_bits, &interval)) {
    return 0;
  }
  if (malbolge_guest_math_fixed192_unique_binary64(&interval.magnitude,
                                                    &magnitude_bits)) {
    *output_bits = magnitude_bits |
                   (interval.negative != UINT32_C(0) ? BINARY64_SIGN
                                                      : UINT64_C(0));
    return 1;
  }
  if (!malbolge_guest_math_atan2_interval224(y_bits, x_bits, &wide_interval)) {
    return 0;
  }
  if (malbolge_guest_math_fixed224_unique_binary64(&wide_interval.magnitude,
                                                    &magnitude_bits)) {
    *output_bits = magnitude_bits |
                   (wide_interval.negative != UINT32_C(0) ? BINARY64_SIGN
                                                           : UINT64_C(0));
    return 1;
  }
  if (!malbolge_guest_math_atan2_interval256(y_bits, x_bits,
                                             &wider_interval) ||
      !malbolge_guest_math_fixed256_unique_binary64(&wider_interval.magnitude,
                                                    &magnitude_bits)) {
    return 0;
  }
  *output_bits = magnitude_bits |
                 (wider_interval.negative != UINT32_C(0) ? BINARY64_SIGN
                                                          : UINT64_C(0));
  return 1;
}

int malbolge_guest_math_ratio_nearest_binary64(
    const MalbolgeGuestMathAtan2KernelInput *input, uint64_t *output_bits) {
  uint32_t exact = UINT32_C(0);
  return ratio_nearest_binary64_internal(input, output_bits, &exact);
}

static int ratio_at_most_atan_identity(
    const MalbolgeGuestMathAtan2KernelInput *input) {
  if (input->exponent_delta < INT32_C(-27)) {
    return 1;
  }
  if (input->exponent_delta == INT32_C(-27)) {
    return input->numerator_significand * UINT64_C(4) <=
           input->denominator_significand * UINT64_C(7);
  }
  if (input->exponent_delta == INT32_C(-26)) {
    return input->numerator_significand * UINT64_C(8) <=
           input->denominator_significand * UINT64_C(7);
  }
  return 0;
}

static uint64_t ceil_shift_right_u64(uint64_t value, uint32_t shift) {
  uint64_t quotient = UINT64_C(0);
  uint64_t mask = UINT64_C(0);

  if (shift == UINT32_C(0)) {
    return value;
  }
  if (shift >= UINT32_C(64)) {
    return value == UINT64_C(0) ? UINT64_C(0) : UINT64_C(1);
  }
  quotient = value >> shift;
  mask = (UINT64_C(1) << shift) - UINT64_C(1);
  return quotient + ((value & mask) != UINT64_C(0) ? UINT64_C(1) : UINT64_C(0));
}

static int denominator_spacing_safe_without_division(
    uint64_t denominator, int32_t exponent) {
  uint64_t odd_denominator = denominator;
  uint64_t maximum_odd_denominator = UINT64_C(0);
  int32_t margin_shift = INT32_C(0);

  if (denominator == UINT64_C(0)) {
    return 0;
  }
  if (exponent <= BINARY64_ATAN_UNCONDITIONAL_EXPONENT) {
    return 1;
  }
  if (exponent >= INT32_C(-27)) {
    return 0;
  }
  while ((odd_denominator & UINT64_C(1)) == UINT64_C(0)) {
    odd_denominator >>= UINT32_C(1);
  }
  margin_shift = -(INT32_C(2) * exponent + INT32_C(55));
  maximum_odd_denominator =
      UINT64_C(3) << (uint32_t)(margin_shift - INT32_C(1));
  return odd_denominator <= maximum_odd_denominator;
}

static int normal_ratio_rounding_margin_safe(
    const MalbolgeGuestMathAtan2KernelInput *input) {
  uint64_t numerator = input->numerator_significand;
  const uint64_t denominator = input->denominator_significand;
  uint64_t remainder = UINT64_C(0);
  uint64_t doubled_remainder = UINT64_C(0);
  uint64_t gap = UINT64_C(0);
  uint64_t threshold = UINT64_C(0);
  int32_t exponent = input->exponent_delta;
  int32_t margin_shift = INT32_C(0);
  uint32_t remaining = BINARY64_EXPONENT_SHIFT;

  if (numerator >= denominator) {
    remainder = numerator - denominator;
  } else {
    numerator <<= UINT32_C(1);
    remainder = numerator - denominator;
    --exponent;
  }
  if (exponent < INT32_C(-1022) || exponent > INT32_C(-27)) {
    return 0;
  }
  if (denominator_spacing_safe_without_division(denominator, exponent)) {
    return 1;
  }
  while (remaining != UINT32_C(0)) {
    --remaining;
    (void)ratio_fraction_bit(denominator, &remainder);
  }
  doubled_remainder = remainder << UINT32_C(1);
  if (doubled_remainder < denominator) {
    return 1;
  }
  if (doubled_remainder == denominator) {
    /* Defensive only: valid 53-bit binary64 ratio geometry cannot reach an
       exact normal midpoint after 52 quotient bits. */
    return 0;
  }
  if (exponent == INT32_C(-27)) {
    return remainder * UINT64_C(768) >= denominator * UINT64_C(727);
  }
  gap = doubled_remainder - denominator;
  margin_shift = -(INT32_C(2) * exponent + INT32_C(55));
  threshold = ceil_shift_right_u64(
      denominator << UINT32_C(1), (uint32_t)margin_shift);
  return gap * UINT64_C(3) >= threshold;
}

static int subnormal_atan_result(
    const MalbolgeGuestMathAtan2KernelInput *input, uint64_t ratio_bits,
    uint64_t *atan_bits) {
  uint64_t numerator = input->numerator_significand;
  const uint64_t denominator = input->denominator_significand;
  uint64_t remainder = UINT64_C(0);
  uint64_t units = UINT64_C(0);
  int32_t exponent = input->exponent_delta;
  int32_t scale = INT32_C(0);
  uint32_t remaining = UINT32_C(0);

  if (numerator >= denominator) {
    remainder = numerator - denominator;
  } else {
    numerator <<= UINT32_C(1);
    remainder = numerator - denominator;
    --exponent;
  }
  if (exponent >= INT32_C(-1022)) {
    return 0;
  }
  scale = exponent + INT32_C(1074);
  if (scale <= INT32_C(-2)) {
    *atan_bits = UINT64_C(0);
    return 1;
  }
  if (scale == INT32_C(-1)) {
    *atan_bits = remainder == UINT64_C(0) ? UINT64_C(0) : UINT64_C(1);
    return 1;
  }
  units = UINT64_C(1) << (uint32_t)scale;
  remaining = (uint32_t)scale;
  while (remaining != UINT32_C(0)) {
    --remaining;
    units |= (uint64_t)ratio_fraction_bit(denominator, &remainder) << remaining;
  }
  *atan_bits = (remainder << UINT32_C(1)) == denominator ? units : ratio_bits;
  return 1;
}

static int ratio_at_most_power_of_two(
    const MalbolgeGuestMathAtan2KernelInput *input, int32_t exponent) {
  if (!valid_ratio_input(input)) {
    return 0;
  }
  if (input->exponent_delta < exponent) {
    return 1;
  }
  if (input->exponent_delta > exponent) {
    return 0;
  }
  return input->numerator_significand <= input->denominator_significand;
}

static MalbolgeGuestMathSpecialResult axis_ratio_atan2_special(
    uint64_t y_bits, uint64_t x_bits,
    const MalbolgeGuestMathAtan2KernelInput *input) {
  if (input->swapped == UINT32_C(0)) {
    if ((x_bits & BINARY64_SIGN) != UINT64_C(0) &&
        ratio_at_most_power_of_two(input, INT32_C(-52))) {
      return resolved(with_sign(BINARY64_PI, y_bits));
    }
    return kernel_required();
  }
  if ((x_bits & BINARY64_SIGN) == UINT64_C(0)) {
    if (ratio_at_most_power_of_two(input, INT32_C(-53))) {
      return resolved(with_sign(BINARY64_PI_OVER_TWO, y_bits));
    }
  } else if (ratio_at_most_power_of_two(input, INT32_C(-55))) {
    return resolved(with_sign(BINARY64_PI_OVER_TWO, y_bits));
  }
  return kernel_required();
}

static MalbolgeGuestMathSpecialResult small_ratio_atan2_special(
    uint64_t y_bits, uint64_t x_bits) {
  MalbolgeGuestMathAtan2KernelInput input;
  uint64_t ratio_bits = UINT64_C(0);
  uint64_t atan_bits = UINT64_C(0);
  uint32_t exact = UINT32_C(0);

  if (!malbolge_guest_math_atan2_kernel_input(y_bits, x_bits, &input)) {
    return kernel_required();
  }
  if ((x_bits & BINARY64_SIGN) != UINT64_C(0) ||
      input.swapped != UINT32_C(0)) {
    return axis_ratio_atan2_special(y_bits, x_bits, &input);
  }
  if (!ratio_at_most_atan_identity(&input) ||
      !ratio_nearest_binary64_internal(&input, &ratio_bits, &exact) ||
      ratio_bits > BINARY64_ATAN_IDENTITY_MAX) {
    return kernel_required();
  }
  if (subnormal_atan_result(&input, ratio_bits, &atan_bits)) {
    return resolved(with_sign(atan_bits, y_bits));
  }
  if (exact == UINT32_C(0) && !normal_ratio_rounding_margin_safe(&input)) {
    return kernel_required();
  }
  return resolved(with_sign(ratio_bits, y_bits));
}
