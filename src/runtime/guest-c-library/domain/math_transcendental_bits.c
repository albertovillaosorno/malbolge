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
#define BINARY64_HIDDEN_BIT UINT64_C(0x0010000000000000)
#define BINARY64_EXPONENT_SHIFT UINT32_C(52)
#define BINARY64_EXPONENT_BIAS INT32_C(1023)
#define BINARY64_SUBNORMAL_EXPONENT INT32_C(-1074)
#define BINARY64_RATIO_MIN_EXPONENT_DELTA INT32_C(-2097)
#define ATAN_QUARTER_REDUCTION_NUMERATOR UINT64_C(169)
#define ATAN_QUARTER_REDUCTION_DENOMINATOR UINT64_C(408)
#define FIXED_192_LIMB_COUNT UINT32_C(7)
#define FIXED_192_FRACTION_BITS INT32_C(192)
#define EXACT_RATIO_COMPONENT_LIMIT UINT64_C(0x0100000000000000)
#define FIXED_PRODUCT_LIMBS UINT32_C(14)
#define ATAN_SERIES_TERMS UINT32_C(48)

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

static void copy_fixed_192(MalbolgeGuestMathFixed192 *output,
                           const uint32_t source[7]) {
  uint32_t index = UINT32_C(0);
  while (index < FIXED_192_LIMB_COUNT) {
    output->limbs[index] = source[index];
    ++index;
  }
}

static void zero_fixed_192(MalbolgeGuestMathFixed192 *value) {
  uint32_t index = UINT32_C(0);
  while (index < FIXED_192_LIMB_COUNT) {
    value->limbs[index] = UINT32_C(0);
    ++index;
  }
}

static void add_fixed_192(MalbolgeGuestMathFixed192 *value,
                          const MalbolgeGuestMathFixed192 *addend) {
  uint32_t index = UINT32_C(0);
  uint32_t carry = UINT32_C(0);

  while (index < FIXED_192_LIMB_COUNT) {
    const uint64_t sum = (uint64_t)value->limbs[index] +
                         (uint64_t)addend->limbs[index] + (uint64_t)carry;
    value->limbs[index] = (uint32_t)sum;
    carry = (uint32_t)(sum >> UINT32_C(32));
    ++index;
  }
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

static void increment_fixed_192(MalbolgeGuestMathFixed192 *value) {
  uint32_t index = UINT32_C(0);
  uint32_t carry = UINT32_C(1);
  while (index < FIXED_192_LIMB_COUNT && carry != UINT32_C(0)) {
    const uint32_t previous = value->limbs[index];
    value->limbs[index] = previous + UINT32_C(1);
    carry = value->limbs[index] == UINT32_C(0) ? UINT32_C(1) : UINT32_C(0);
    ++index;
  }
}

static void shift_fixed_192_bit(MalbolgeGuestMathFixed192 *value,
                                uint32_t bit) {
  uint32_t index = UINT32_C(0);
  uint32_t carry = bit;
  while (index < FIXED_192_LIMB_COUNT) {
    const uint32_t next = value->limbs[index] >> UINT32_C(31);
    value->limbs[index] = (value->limbs[index] << UINT32_C(1)) | carry;
    carry = next;
    ++index;
  }
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

static int fixed_192_is_zero(const MalbolgeGuestMathFixed192 *value) {
  uint32_t index = UINT32_C(0);
  while (index < FIXED_192_LIMB_COUNT) {
    if (value->limbs[index] != UINT32_C(0)) {
      return 0;
    }
    ++index;
  }
  return 1;
}

static int fixed_192_below_two_neg64(
    const MalbolgeGuestMathFixed192 *value) {
  return value->limbs[4] == UINT32_C(0) &&
         value->limbs[5] == UINT32_C(0) &&
         value->limbs[6] == UINT32_C(0);
}

static void decrement_fixed_192(MalbolgeGuestMathFixed192 *value) {
  uint32_t index = UINT32_C(0);
  uint32_t borrow = UINT32_C(1);
  while (index < FIXED_192_LIMB_COUNT && borrow != UINT32_C(0)) {
    const uint32_t previous = value->limbs[index];
    value->limbs[index] = previous - UINT32_C(1);
    borrow = previous == UINT32_C(0) ? UINT32_C(1) : UINT32_C(0);
    ++index;
  }
}

static int compare_fixed_192(const MalbolgeGuestMathFixed192 *left,
                             const MalbolgeGuestMathFixed192 *right) {
  uint32_t index = FIXED_192_LIMB_COUNT;
  while (index != UINT32_C(0)) {
    --index;
    if (left->limbs[index] < right->limbs[index]) {
      return -1;
    }
    if (left->limbs[index] > right->limbs[index]) {
      return 1;
    }
  }
  return 0;
}

static int subtract_fixed_192(MalbolgeGuestMathFixed192 *output,
                              const MalbolgeGuestMathFixed192 *left,
                              const MalbolgeGuestMathFixed192 *right) {
  MalbolgeGuestMathFixed192 staged;
  uint32_t index = UINT32_C(0);
  uint32_t borrow = UINT32_C(0);

  if (compare_fixed_192(left, right) < 0) {
    return 0;
  }
  while (index < FIXED_192_LIMB_COUNT) {
    const uint64_t subtrahend = (uint64_t)right->limbs[index] + borrow;
    const uint64_t minuend = left->limbs[index];
    staged.limbs[index] = (uint32_t)(minuend - subtrahend);
    borrow = minuend < subtrahend ? UINT32_C(1) : UINT32_C(0);
    ++index;
  }
  copy_fixed_192(output, staged.limbs);
  return 1;
}

static void multiply_fixed_floor(const MalbolgeGuestMathFixed192 *left,
                                 const MalbolgeGuestMathFixed192 *right,
                                 MalbolgeGuestMathFixed192 *output,
                                 uint32_t *discarded) {
  uint32_t product[14];
  uint32_t index = UINT32_C(0);
  uint32_t left_index = UINT32_C(0);

  while (index < FIXED_PRODUCT_LIMBS) {
    product[index] = UINT32_C(0);
    ++index;
  }
  while (left_index < FIXED_192_LIMB_COUNT) {
    uint32_t right_index = UINT32_C(0);
    uint64_t carry = UINT64_C(0);
    while (right_index < FIXED_192_LIMB_COUNT) {
      const uint32_t cell_index = left_index + right_index;
      const uint64_t cell = (uint64_t)left->limbs[left_index] *
                                (uint64_t)right->limbs[right_index] +
                            (uint64_t)product[cell_index] + carry;
      product[cell_index] = (uint32_t)cell;
      carry = cell >> UINT32_C(32);
      ++right_index;
    }
    index = left_index + FIXED_192_LIMB_COUNT;
    while (carry != UINT64_C(0) && index < FIXED_PRODUCT_LIMBS) {
      const uint64_t cell = (uint64_t)product[index] + carry;
      product[index] = (uint32_t)cell;
      carry = cell >> UINT32_C(32);
      ++index;
    }
    ++left_index;
  }
  *discarded = UINT32_C(0);
  index = UINT32_C(0);
  while (index < UINT32_C(6)) {
    if (product[index] != UINT32_C(0)) {
      *discarded = UINT32_C(1);
    }
    ++index;
  }
  index = UINT32_C(0);
  while (index < FIXED_192_LIMB_COUNT) {
    output->limbs[index] = product[index + UINT32_C(6)];
    ++index;
  }
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

static void multiply_fixed_small(MalbolgeGuestMathFixed192 *value,
                                 uint32_t factor) {
  uint32_t index = UINT32_C(0);
  uint64_t carry = UINT64_C(0);
  while (index < FIXED_192_LIMB_COUNT) {
    const uint64_t product =
        (uint64_t)value->limbs[index] * factor + carry;
    value->limbs[index] = (uint32_t)product;
    carry = product >> UINT32_C(32);
    ++index;
  }
}

static uint32_t divide_fixed_small_floor(
    const MalbolgeGuestMathFixed192 *input, uint32_t divisor,
    MalbolgeGuestMathFixed192 *output) {
  uint32_t limb_index = FIXED_192_LIMB_COUNT;
  uint32_t remainder = UINT32_C(0);
  zero_fixed_192(output);
  while (limb_index != UINT32_C(0)) {
    uint32_t bit_index = UINT32_C(32);
    --limb_index;
    while (bit_index != UINT32_C(0)) {
      uint32_t quotient_bit = UINT32_C(0);
      --bit_index;
      remainder = (remainder << UINT32_C(1)) |
                  ((input->limbs[limb_index] >> bit_index) & UINT32_C(1));
      if (remainder >= divisor) {
        remainder -= divisor;
        quotient_bit = UINT32_C(1);
      }
      output->limbs[limb_index] |= quotient_bit << bit_index;
    }
  }
  return remainder;
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
  MalbolgeGuestMathFixed192 truncation;
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
  zero_fixed_192(&truncation);
  truncation.limbs[2] = UINT32_C(1);
  add_fixed_192(&sum.upper, &truncation);
  copy_fixed_192(&output->lower, sum.lower.limbs);
  copy_fixed_192(&output->upper, sum.upper.limbs);
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

static int normal_ratio_rounding_margin_safe(
    const MalbolgeGuestMathAtan2KernelInput *input) {
  uint64_t numerator = input->numerator_significand;
  const uint64_t denominator = input->denominator_significand;
  uint64_t remainder = UINT64_C(0);
  int32_t exponent = input->exponent_delta;
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
  while (remaining != UINT32_C(0)) {
    --remaining;
    (void)ratio_fraction_bit(denominator, &remainder);
  }
  if ((remainder << UINT32_C(1)) < denominator) {
    return 1;
  }
  if (exponent == INT32_C(-27)) {
    return remainder * UINT64_C(768) >= denominator * UINT64_C(727);
  }
  return remainder * UINT64_C(3) >= denominator * UINT64_C(2);
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

static MalbolgeGuestMathSpecialResult small_ratio_atan2_special(
    uint64_t y_bits, uint64_t x_bits) {
  MalbolgeGuestMathAtan2KernelInput input;
  uint64_t ratio_bits = UINT64_C(0);
  uint64_t atan_bits = UINT64_C(0);
  uint32_t exact = UINT32_C(0);

  if ((x_bits & BINARY64_SIGN) != UINT64_C(0) ||
      !malbolge_guest_math_atan2_kernel_input(y_bits, x_bits, &input) ||
      input.swapped != UINT32_C(0) || !ratio_at_most_atan_identity(&input) ||
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
