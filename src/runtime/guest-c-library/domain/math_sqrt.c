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
//   - Canonical nearest-ties-even binary64 square-root semantics.
// - Must-Not:
//   - Call host libm, inspect host rounding state, or use floating arithmetic.
// - Allows:
//   - Inputs: malbolge-c32-v1 binary64 values.
//   - Outputs: correctly rounded binary64 square root or canonical NaN.
//   - Side effects: none.
// - Split-When:
//   - Another inexact math routine needs an independently proved algorithm.
// - Merge-When:
//   - One proved integer-representation math family owns this exact policy.
// - Summary:
//   - Computes deterministic binary64 sqrt with an integer restoring algorithm.
// - Description:
//   - Streams a conceptual 106-bit radicand through a 64-bit remainder.
// - Usage:
//   - Linked as ordinary guest C once sqrt is admitted by libc authority.
// - Defaults:
//   - Rounding is ABI-fixed nearest ties to even; every NaN is canonicalized.
//

//! Correctly rounded binary64 square root without host floating-point
//! authority.

#include "math.h"

#include <stdint.h>

typedef union MalbolgeSqrtBinary64Bits {
  double value;
  uint64_t bits;
} MalbolgeSqrtBinary64Bits;

#define BINARY64_SIGN UINT64_C(0x8000000000000000)
#define BINARY64_EXPONENT UINT64_C(0x7ff0000000000000)
#define BINARY64_FRACTION UINT64_C(0x000fffffffffffff)
#define BINARY64_HIDDEN_BIT UINT64_C(0x0010000000000000)
#define BINARY64_CANONICAL_NAN UINT64_C(0x7ff8000000000000)
#define BINARY64_EXPONENT_BIAS INT32_C(1023)
#define BINARY64_FRACTION_BITS UINT32_C(52)
#define BINARY64_EXPONENT_ALL_ONES UINT32_C(0x7ff)
#define BINARY64_MIN_NORMAL_EXPONENT INT32_C(-1022)
#define SQRT_RADICAND_PAIR_COUNT UINT32_C(53)

static uint64_t sqrt_to_bits(double value) {
  MalbolgeSqrtBinary64Bits representation = {.value = value};
  return representation.bits;
}

static double sqrt_from_bits(uint64_t bits) {
  MalbolgeSqrtBinary64Bits representation = {.bits = bits};
  return representation.value;
}

static uint32_t sqrt_exponent_bits(uint64_t bits) {
  return (uint32_t)((bits & BINARY64_EXPONENT) >> BINARY64_FRACTION_BITS);
}

static uint64_t normalize_significand(uint64_t bits, int32_t *exponent) {
  const uint32_t raw_exponent = sqrt_exponent_bits(bits);
  uint64_t significand = bits & BINARY64_FRACTION;

  if (raw_exponent != UINT32_C(0)) {
    *exponent = (int32_t)raw_exponent - BINARY64_EXPONENT_BIAS;
    return significand | BINARY64_HIDDEN_BIT;
  }
  *exponent = BINARY64_MIN_NORMAL_EXPONENT;
  while ((significand & BINARY64_HIDDEN_BIT) == UINT64_C(0)) {
    significand <<= UINT32_C(1);
    --(*exponent);
  }
  return significand;
}

static uint32_t radicand_pair(uint64_t significand, uint32_t pair_index) {
  const uint32_t bit = pair_index * UINT32_C(2);
  uint32_t pair = UINT32_C(0);

  if (bit >= BINARY64_FRACTION_BITS) {
    pair |= (uint32_t)((significand >> (bit - BINARY64_FRACTION_BITS)) &
                       UINT64_C(1));
  }
  if (bit + UINT32_C(1) >= BINARY64_FRACTION_BITS) {
    pair |= (uint32_t)(((significand >>
                         (bit + UINT32_C(1) - BINARY64_FRACTION_BITS)) &
                        UINT64_C(1))
                       << UINT32_C(1));
  }
  return pair;
}

static uint64_t scaled_integer_sqrt(uint64_t significand,
                                    uint64_t *final_remainder) {
  uint32_t pair_index = SQRT_RADICAND_PAIR_COUNT;
  uint64_t remainder = UINT64_C(0);
  uint64_t root = UINT64_C(0);

  while (pair_index != UINT32_C(0)) {
    uint64_t trial = UINT64_C(0);

    --pair_index;
    remainder = (remainder << UINT32_C(2)) |
                (uint64_t)radicand_pair(significand, pair_index);
    trial = (root << UINT32_C(2)) | UINT64_C(1);
    if (remainder >= trial) {
      remainder -= trial;
      root = (root << UINT32_C(1)) | UINT64_C(1);
    } else {
      root <<= UINT32_C(1);
    }
  }
  *final_remainder = remainder;
  return root;
}

static uint64_t encode_sqrt_result(uint64_t root, int32_t exponent) {
  int32_t result_exponent = exponent / INT32_C(2);

  if (root == (BINARY64_HIDDEN_BIT << UINT32_C(1))) {
    root >>= UINT32_C(1);
    ++result_exponent;
  }
  return ((uint64_t)(result_exponent + BINARY64_EXPONENT_BIAS)
          << BINARY64_FRACTION_BITS) |
         (root - BINARY64_HIDDEN_BIT);
}

double sqrt(double value) {
  const uint64_t bits = sqrt_to_bits(value);
  const uint64_t magnitude = bits & ~BINARY64_SIGN;
  const uint32_t raw_exponent = sqrt_exponent_bits(bits);
  uint64_t significand = UINT64_C(0);
  uint64_t remainder = UINT64_C(0);
  uint64_t root = UINT64_C(0);
  int32_t exponent = INT32_C(0);

  if (raw_exponent == BINARY64_EXPONENT_ALL_ONES) {
    if ((bits & BINARY64_FRACTION) != UINT64_C(0) ||
        (bits & BINARY64_SIGN) != UINT64_C(0)) {
      return sqrt_from_bits(BINARY64_CANONICAL_NAN);
    }
    return value;
  }
  if (magnitude == UINT64_C(0)) {
    return value;
  }
  if ((bits & BINARY64_SIGN) != UINT64_C(0)) {
    return sqrt_from_bits(BINARY64_CANONICAL_NAN);
  }

  significand = normalize_significand(bits, &exponent);
  if ((exponent % INT32_C(2)) != INT32_C(0)) {
    significand <<= UINT32_C(1);
    --exponent;
  }
  root = scaled_integer_sqrt(significand, &remainder);

  /* The exact midpoint between root and root+1 has a quarter-integer square.
     The streamed radicand is integral, so no halfway case can occur here. */
  if (remainder > root) {
    ++root;
  }
  return sqrt_from_bits(encode_sqrt_result(root, exponent));
}
