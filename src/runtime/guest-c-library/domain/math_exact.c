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
//   - Exact binary64 fabs, floor, ceil, and trunc guest implementations.
// - Must-Not:
//   - Call host libm, inspect host rounding state, or preserve NaN payloads.
// - Allows:
//   - Inputs: malbolge-c32-v1 binary64 values.
//   - Outputs: exact binary64 results with canonical NaN publication.
//   - Side effects: none.
// - Split-When:
//   - Inexact or transcendental math requires an independent algorithm family.
// - Merge-When:
//   - One exact binary64 implementation owns these four routines together.
// - Summary:
//   - Implements exact rounding-independent binary64 math by representation.
// - Description:
//   - Uses ABI-fixed IEEE binary64 fields and no floating arithmetic fallback.
// - Usage:
//   - Linked as ordinary guest C for the available exact math subset.
// - Defaults:
//   - Every NaN input maps to the canonical quiet payload-zero NaN.
//

//! Exact binary64 guest math routines with canonical NaN handling.

#include "math.h"

#include <stdint.h>

typedef union MalbolgeBinary64Bits {
  double value;
  uint64_t bits;
} MalbolgeBinary64Bits;

#define BINARY64_SIGN UINT64_C(0x8000000000000000)
#define BINARY64_EXPONENT UINT64_C(0x7ff0000000000000)
#define BINARY64_FRACTION UINT64_C(0x000fffffffffffff)
#define BINARY64_CANONICAL_NAN UINT64_C(0x7ff8000000000000)
#define BINARY64_ONE UINT64_C(0x3ff0000000000000)
#define BINARY64_NEGATIVE_ONE UINT64_C(0xbff0000000000000)
#define BINARY64_EXPONENT_BIAS UINT32_C(1023)
#define BINARY64_FRACTION_BITS UINT32_C(52)

static uint64_t to_bits(double value) {
  MalbolgeBinary64Bits representation = {.value = value};
  return representation.bits;
}

static double from_bits(uint64_t bits) {
  MalbolgeBinary64Bits representation = {.bits = bits};
  return representation.value;
}

static int is_nan_bits(uint64_t bits) {
  return (bits & BINARY64_EXPONENT) == BINARY64_EXPONENT &&
         (bits & BINARY64_FRACTION) != UINT64_C(0);
}

static uint32_t exponent_bits(uint64_t bits) {
  return (uint32_t)((bits & BINARY64_EXPONENT) >> BINARY64_FRACTION_BITS);
}

static uint64_t fractional_integer_mask(uint32_t exponent) {
  const uint32_t unbiased = exponent - BINARY64_EXPONENT_BIAS;
  const uint32_t fractional_bits = BINARY64_FRACTION_BITS - unbiased;
  return (UINT64_C(1) << fractional_bits) - UINT64_C(1);
}

static uint64_t truncate_finite_bits(uint64_t bits, uint32_t exponent) {
  if (exponent < BINARY64_EXPONENT_BIAS) {
    return bits & BINARY64_SIGN;
  }
  if (exponent >= BINARY64_EXPONENT_BIAS + BINARY64_FRACTION_BITS) {
    return bits;
  }
  return bits & ~fractional_integer_mask(exponent);
}

double fabs(double value) {
  const uint64_t bits = to_bits(value);
  if (is_nan_bits(bits)) {
    return from_bits(BINARY64_CANONICAL_NAN);
  }
  return from_bits(bits & ~BINARY64_SIGN);
}

double trunc(double value) {
  const uint64_t bits = to_bits(value);
  const uint32_t exponent = exponent_bits(bits);
  if (is_nan_bits(bits)) {
    return from_bits(BINARY64_CANONICAL_NAN);
  }
  if (exponent == UINT32_C(0x7ff)) {
    return value;
  }
  return from_bits(truncate_finite_bits(bits, exponent));
}

double floor(double value) {
  const uint64_t bits = to_bits(value);
  const uint32_t exponent = exponent_bits(bits);
  const uint64_t magnitude = bits & ~BINARY64_SIGN;
  uint64_t truncated = 0U;
  uint64_t mask = 0U;

  if (is_nan_bits(bits)) {
    return from_bits(BINARY64_CANONICAL_NAN);
  }
  if (magnitude == UINT64_C(0) || exponent == UINT32_C(0x7ff)) {
    return value;
  }
  if (exponent < BINARY64_EXPONENT_BIAS) {
    return (bits & BINARY64_SIGN) == UINT64_C(0)
               ? from_bits(UINT64_C(0))
               : from_bits(BINARY64_NEGATIVE_ONE);
  }
  if (exponent >= BINARY64_EXPONENT_BIAS + BINARY64_FRACTION_BITS) {
    return value;
  }
  mask = fractional_integer_mask(exponent);
  if ((bits & mask) == UINT64_C(0)) {
    return value;
  }
  truncated = bits & ~mask;
  if ((bits & BINARY64_SIGN) != UINT64_C(0)) {
    truncated += mask + UINT64_C(1);
  }
  return from_bits(truncated);
}

double ceil(double value) {
  const uint64_t bits = to_bits(value);
  const uint32_t exponent = exponent_bits(bits);
  const uint64_t magnitude = bits & ~BINARY64_SIGN;
  uint64_t truncated = 0U;
  uint64_t mask = 0U;

  if (is_nan_bits(bits)) {
    return from_bits(BINARY64_CANONICAL_NAN);
  }
  if (magnitude == UINT64_C(0) || exponent == UINT32_C(0x7ff)) {
    return value;
  }
  if (exponent < BINARY64_EXPONENT_BIAS) {
    return (bits & BINARY64_SIGN) == UINT64_C(0) ? from_bits(BINARY64_ONE)
                                                 : from_bits(BINARY64_SIGN);
  }
  if (exponent >= BINARY64_EXPONENT_BIAS + BINARY64_FRACTION_BITS) {
    return value;
  }
  mask = fractional_integer_mask(exponent);
  if ((bits & mask) == UINT64_C(0)) {
    return value;
  }
  truncated = bits & ~mask;
  if ((bits & BINARY64_SIGN) == UINT64_C(0)) {
    truncated += mask + UINT64_C(1);
  }
  return from_bits(truncated);
}
