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
//   - Exact finite-binary64 to canonical decimal magnitude conversion.
// - Must-Not:
//   - Use floating arithmetic, allocation, host formatting, or 64-bit division.
// - Allows:
//   - Inputs: raw binary64 bits.
//   - Outputs: exact significant decimal digits and a base-ten shift.
//   - Side effects: result publication only after bounded conversion succeeds.
// - Split-When:
//   - Binary128 needs its separately sized exact-decimal scratch policy.
// - Merge-When:
//   - Decimal formatter owns the same bounded integer representation directly.
// - Summary:
//   - Rewrites m*2^e exactly as decimal integer digits times a power of ten.
// - Description:
//   - Negative binary powers become powers of five plus a negative decimal
//     shift.
// - Usage:
//   - Supplies exact source digits for decimal printf rounding and layout.
// - Defaults:
//   - Trailing decimal zeroes move into the shift without changing exact value.
//

//! Exact binary64 decimal decomposition with no host floating authority.

#include "guest_decimal_exact.h"

#include <stddef.h>
#include <stdint.h>

#define B64_SIGN UINT64_C(0x8000000000000000)
#define B64_EXPONENT UINT64_C(0x7ff0000000000000)
#define B64_FRACTION UINT64_C(0x000fffffffffffff)
#define B64_HIDDEN UINT64_C(0x0010000000000000)
#define B64_EXPONENT_SHIFT UINT32_C(52)
#define B64_EXPONENT_BIAS INT32_C(1023)
#define B64_SUBNORMAL_POWER INT32_C(-1074)
#define B64_EXPONENT_ALL_ONES UINT32_C(0x7ff)

#define BIG_BASE UINT32_C(10000)
#define BIG_LIMBS UINT32_C(192)
#define POW2_CHUNK UINT32_C(262144)
#define POW2_CHUNK_BITS UINT32_C(18)
#define POW5_CHUNK UINT32_C(3125)
#define POW5_CHUNK_BITS UINT32_C(5)

typedef struct DecimalBigNat {
  uint32_t limbs[192];
  uint32_t count;
} DecimalBigNat;

static void big_zero(DecimalBigNat *value) {
  uint32_t index = UINT32_C(0);

  value->count = UINT32_C(1);
  while (index < BIG_LIMBS) {
    value->limbs[index] = UINT32_C(0);
    ++index;
  }
}

static int big_multiply(DecimalBigNat *value, uint32_t factor) {
  uint32_t carry = UINT32_C(0);
  uint32_t index = UINT32_C(0);

  while (index < value->count) {
    const uint32_t product = value->limbs[index] * factor + carry;
    value->limbs[index] = product % BIG_BASE;
    carry = product / BIG_BASE;
    ++index;
  }
  while (carry != UINT32_C(0)) {
    if (value->count == BIG_LIMBS) {
      return 0;
    }
    value->limbs[value->count] = carry % BIG_BASE;
    carry /= BIG_BASE;
    ++value->count;
  }
  return 1;
}

static int big_add_bit(DecimalBigNat *value, uint32_t bit) {
  uint32_t carry = bit;
  uint32_t index = UINT32_C(0);

  while (carry != UINT32_C(0) && index < value->count) {
    const uint32_t sum = value->limbs[index] + carry;
    value->limbs[index] = sum >= BIG_BASE ? sum - BIG_BASE : sum;
    carry = sum >= BIG_BASE ? UINT32_C(1) : UINT32_C(0);
    ++index;
  }
  if (carry != UINT32_C(0)) {
    if (value->count == BIG_LIMBS) {
      return 0;
    }
    value->limbs[value->count] = carry;
    ++value->count;
  }
  return 1;
}

static int big_from_u64_bits(DecimalBigNat *value, uint64_t input) {
  uint32_t bit = UINT32_C(64);

  big_zero(value);
  while (bit != UINT32_C(0)) {
    --bit;
    if (!big_multiply(value, UINT32_C(2)) ||
        !big_add_bit(value, (uint32_t)((input >> bit) & UINT64_C(1)))) {
      return 0;
    }
  }
  return 1;
}

static int big_multiply_power(DecimalBigNat *value, uint32_t factor,
                              uint32_t chunk_power, uint32_t exponent) {
  while (exponent >= chunk_power) {
    if (!big_multiply(value, factor)) {
      return 0;
    }
    exponent -= chunk_power;
  }
  while (exponent != UINT32_C(0)) {
    const uint32_t small = factor == POW2_CHUNK ? UINT32_C(2) : UINT32_C(5);
    if (!big_multiply(value, small)) {
      return 0;
    }
    --exponent;
  }
  return 1;
}

static uint32_t top_decimal_digits(uint32_t value) {
  if (value >= UINT32_C(1000)) {
    return UINT32_C(4);
  }
  if (value >= UINT32_C(100)) {
    return UINT32_C(3);
  }
  if (value >= UINT32_C(10)) {
    return UINT32_C(2);
  }
  return UINT32_C(1);
}

static void emit_padded_limb(char *digits, uint32_t offset, uint32_t value) {
  digits[offset] = (char)('0' + (char)(value / UINT32_C(1000)));
  value %= UINT32_C(1000);
  digits[offset + UINT32_C(1)] =
      (char)('0' + (char)(value / UINT32_C(100)));
  value %= UINT32_C(100);
  digits[offset + UINT32_C(2)] =
      (char)('0' + (char)(value / UINT32_C(10)));
  digits[offset + UINT32_C(3)] = (char)('0' + (char)(value % UINT32_C(10)));
}

static uint32_t emit_top_limb(char *digits, uint32_t value) {
  const uint32_t count = top_decimal_digits(value);
  uint32_t divisor = UINT32_C(1);
  uint32_t index = UINT32_C(1);

  while (index < count) {
    divisor *= UINT32_C(10);
    ++index;
  }
  index = UINT32_C(0);
  while (divisor != UINT32_C(0)) {
    digits[index] = (char)('0' + (char)(value / divisor));
    value %= divisor;
    divisor /= UINT32_C(10);
    ++index;
  }
  return count;
}

static int big_to_decimal(const DecimalBigNat *value,
                          MalbolgeGuestDecimalExact *result,
                          int32_t initial_shift) {
  uint32_t limb = value->count;
  uint32_t output = UINT32_C(0);

  if (limb == UINT32_C(0)) {
    return 0;
  }
  --limb;
  output = emit_top_limb(result->digits, value->limbs[limb]);
  while (limb != UINT32_C(0)) {
    --limb;
    if (output > MALBOLGE_GUEST_DECIMAL_BINARY64_DIGITS - UINT32_C(4)) {
      return 0;
    }
    emit_padded_limb(result->digits, output, value->limbs[limb]);
    output += UINT32_C(4);
  }
  while (output > UINT32_C(1) && result->digits[output - UINT32_C(1)] == '0') {
    --output;
    ++initial_shift;
  }
  result->digit_count = output;
  result->decimal_shift = initial_shift;
  return 1;
}

MalbolgeGuestRuntimeStatus malbolge_guest_decimal_from_binary64(
    uint64_t bits, MalbolgeGuestDecimalExact *result) {
  const uint64_t magnitude = bits & ~B64_SIGN;
  const uint32_t raw_exponent =
      (uint32_t)((bits & B64_EXPONENT) >> B64_EXPONENT_SHIFT);
  uint64_t significand = bits & B64_FRACTION;
  DecimalBigNat value;
  int32_t binary_power = INT32_C(0);
  int32_t decimal_shift = INT32_C(0);

  if (result == NULL || raw_exponent == B64_EXPONENT_ALL_ONES) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  if (magnitude == UINT64_C(0)) {
    result->digits[0] = '0';
    result->digit_count = UINT32_C(1);
    result->decimal_shift = INT32_C(0);
    return MALBOLGE_GUEST_RUNTIME_VALID;
  }
  if (raw_exponent == UINT32_C(0)) {
    binary_power = B64_SUBNORMAL_POWER;
  } else {
    significand |= B64_HIDDEN;
    binary_power = (int32_t)raw_exponent - B64_EXPONENT_BIAS - INT32_C(52);
  }
  if (!big_from_u64_bits(&value, significand)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  if (binary_power >= INT32_C(0)) {
    if (!big_multiply_power(&value, POW2_CHUNK, POW2_CHUNK_BITS,
                            (uint32_t)binary_power)) {
      return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
    }
  } else {
    const uint32_t denominator_power = (uint32_t)(-binary_power);
    if (!big_multiply_power(&value, POW5_CHUNK, POW5_CHUNK_BITS,
                            denominator_power)) {
      return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
    }
    decimal_shift = binary_power;
  }
  if (!big_to_decimal(&value, result, decimal_shift)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  return MALBOLGE_GUEST_RUNTIME_VALID;
}
