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
//   - Correctly rounded canonical binary64 sine and cosine entry points.
// - Must-Not:
//   - Call host libm, allocate guest heap storage, or inspect host fenv state.
// - Allows:
//   - Inputs: malbolge-c32-v1 binary64 values.
//   - Outputs: correctly rounded sine/cosine or canonical NaN.
//   - Side effects: automatic fixed-size scratch only.
// - Split-When:
//   - Another transcendental routine gains an independent finite proof.
// - Merge-When:
//   - One proved public transcendental family owns this dispatch policy.
// - Summary:
//   - Dispatches special, sub-four Q512, and periodic Payne-Hanek kernels.
// - Description:
//   - Uses fixed stack scratch after finite binary64 TMD resource closure.
// - Usage:
//   - Linked as ordinary guest C for the admitted sin/cos libc surface.
// - Defaults:
//   - Unexpected internal inconclusiveness fails closed to canonical NaN.
//

//! Correctly rounded binary64 sine and cosine without host libm.

#include "math.h"

#include "../contract/math_transcendental_bits.h"

#include <stdint.h>

typedef union MalbolgeSincosBinary64Bits {
  double value;
  uint64_t bits;
} MalbolgeSincosBinary64Bits;

#define BINARY64_SIGN UINT64_C(0x8000000000000000)
#define BINARY64_FOUR UINT64_C(0x4010000000000000)
#define BINARY64_CANONICAL_NAN UINT64_C(0x7ff8000000000000)

static uint64_t sincos_to_bits(double value) {
  MalbolgeSincosBinary64Bits representation = {.value = value};
  return representation.bits;
}

static double sincos_from_bits(uint64_t bits) {
  MalbolgeSincosBinary64Bits representation = {.bits = bits};
  return representation.value;
}

static double sincos_public(MalbolgeGuestMathUnaryOperation operation,
                            double value) {
  const uint64_t bits = sincos_to_bits(value);
  const uint64_t magnitude = bits & ~BINARY64_SIGN;
  const MalbolgeGuestMathSpecialResult special =
      malbolge_guest_math_unary_special(operation, bits);
  uint32_t scratch[MALBOLGE_GUEST_MATH_SUBFOUR_Q512_SCRATCH_LIMBS];
  uint64_t result = UINT64_C(0);

  if (special.status == MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED) {
    return sincos_from_bits(special.bits);
  }
  if (special.status != MALBOLGE_GUEST_MATH_SPECIAL_KERNEL_REQUIRED) {
    return sincos_from_bits(BINARY64_CANONICAL_NAN);
  }
  if (magnitude < BINARY64_FOUR) {
    if (malbolge_guest_math_sincos_subfour_unique_binary64_q512(
            operation, bits, &result, scratch,
            MALBOLGE_GUEST_MATH_SUBFOUR_Q512_SCRATCH_LIMBS)) {
      return sincos_from_bits(result);
    }
  } else {
    if (malbolge_guest_math_sincos_range_unique_binary64(
            operation, bits, &result, scratch,
            MALBOLGE_GUEST_MATH_PERIODIC_Q256_SCRATCH_LIMBS) ||
        malbolge_guest_math_sincos_range_unique_binary64_q512(
            operation, bits, &result, scratch,
            MALBOLGE_GUEST_MATH_PERIODIC_Q512_SCRATCH_LIMBS)) {
      return sincos_from_bits(result);
    }
  }
  return sincos_from_bits(BINARY64_CANONICAL_NAN);
}

double sin(double value) {
  return sincos_public(MALBOLGE_GUEST_MATH_SIN, value);
}

double cos(double value) {
  return sincos_public(MALBOLGE_GUEST_MATH_COS, value);
}
