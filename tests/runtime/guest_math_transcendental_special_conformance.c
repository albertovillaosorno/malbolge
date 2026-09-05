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
//   - Raw-bit vectors for exact transcendental preclassification.
// - Must-Not:
//   - Treat unresolved finite values as approximate transcendental evidence.
// - Allows:
//   - Inputs: fixed binary64 words and internal operation identities.
//   - Outputs: zero only when exact result-versus-kernel classification
//     matches.
//   - Side effects: none.
// - Split-When:
//   - Numerical transcendental kernels gain independent differential evidence.
// - Merge-When:
//   - Complete transcendental conformance owns these edge vectors directly.
// - Summary:
//   - Locks exact sin/cos/atan2 edge cases before numerical approximation.
// - Description:
//   - Covers zeros, infinities, NaNs, invalid operations, and kernel-required.
// - Usage:
//   - Compiled directly against the internal guest-libc classifier.
// - Defaults:
//   - Ordinary finite values must remain kernel-required.
//

//! Exact edge-case vectors for future correctly-rounded transcendental math.

#include "math_transcendental_bits.h"

#include <stdint.h>

static int expect(MalbolgeGuestMathSpecialResult result,
                  MalbolgeGuestMathSpecialStatus status, uint64_t bits) {
  return result.status == status && result.bits == bits;
}

int main(void) {
  if (!expect(malbolge_guest_math_unary_special(MALBOLGE_GUEST_MATH_SIN,
                                                 UINT64_C(0)),
              MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED, UINT64_C(0)) ||
      !expect(malbolge_guest_math_unary_special(
                  MALBOLGE_GUEST_MATH_SIN, UINT64_C(0x8000000000000000)),
              MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED,
              UINT64_C(0x8000000000000000)) ||
      !expect(malbolge_guest_math_unary_special(MALBOLGE_GUEST_MATH_COS,
                                                 UINT64_C(0)),
              MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED,
              UINT64_C(0x3ff0000000000000))) {
    return 1;
  }
  if (!expect(malbolge_guest_math_unary_special(
                  MALBOLGE_GUEST_MATH_SIN, UINT64_C(0x3e50000000000000)),
              MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED,
              UINT64_C(0x3e50000000000000)) ||
      !expect(malbolge_guest_math_unary_special(
                  MALBOLGE_GUEST_MATH_SIN, UINT64_C(0xbe50000000000000)),
              MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED,
              UINT64_C(0xbe50000000000000)) ||
      !expect(malbolge_guest_math_unary_special(
                  MALBOLGE_GUEST_MATH_COS, UINT64_C(0xbe40000000000000)),
              MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED,
              UINT64_C(0x3ff0000000000000)) ||
      !expect(malbolge_guest_math_unary_special(
                  MALBOLGE_GUEST_MATH_SIN, UINT64_C(0x3e50000000000001)),
              MALBOLGE_GUEST_MATH_SPECIAL_KERNEL_REQUIRED, UINT64_C(0)) ||
      !expect(malbolge_guest_math_unary_special(
                  MALBOLGE_GUEST_MATH_COS, UINT64_C(0x3e40000000000001)),
              MALBOLGE_GUEST_MATH_SPECIAL_KERNEL_REQUIRED, UINT64_C(0))) {
    return 2;
  }
  if (!expect(malbolge_guest_math_unary_special(
                  MALBOLGE_GUEST_MATH_SIN, UINT64_C(0x7ff0000000000000)),
              MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED,
              UINT64_C(0x7ff8000000000000)) ||
      !expect(malbolge_guest_math_unary_special(
                  MALBOLGE_GUEST_MATH_COS, UINT64_C(0xfff8000000000001)),
              MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED,
              UINT64_C(0x7ff8000000000000)) ||
      !expect(malbolge_guest_math_unary_special(
                  (MalbolgeGuestMathUnaryOperation)UINT32_C(99), UINT64_C(0)),
              MALBOLGE_GUEST_MATH_SPECIAL_INVALID, UINT64_C(0))) {
    return 3;
  }
  if (!expect(malbolge_guest_math_atan2_special(
                  UINT64_C(0), UINT64_C(0x3ff0000000000000)),
              MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED, UINT64_C(0)) ||
      !expect(malbolge_guest_math_atan2_special(
                  UINT64_C(0x8000000000000000),
                  UINT64_C(0xbff0000000000000)),
              MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED,
              UINT64_C(0xc00921fb54442d18)) ||
      !expect(malbolge_guest_math_atan2_special(
                  UINT64_C(0), UINT64_C(0x8000000000000000)),
              MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED,
              UINT64_C(0x400921fb54442d18))) {
    return 4;
  }
  if (!expect(malbolge_guest_math_atan2_special(
                  UINT64_C(0x3ff0000000000000), UINT64_C(0)),
              MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED,
              UINT64_C(0x3ff921fb54442d18)) ||
      !expect(malbolge_guest_math_atan2_special(
                  UINT64_C(0xbff0000000000000),
                  UINT64_C(0x8000000000000000)),
              MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED,
              UINT64_C(0xbff921fb54442d18))) {
    return 5;
  }
  if (!expect(malbolge_guest_math_atan2_special(
                  UINT64_C(0x7ff0000000000000),
                  UINT64_C(0x7ff0000000000000)),
              MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED,
              UINT64_C(0x3fe921fb54442d18)) ||
      !expect(malbolge_guest_math_atan2_special(
                  UINT64_C(0xfff0000000000000),
                  UINT64_C(0xfff0000000000000)),
              MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED,
              UINT64_C(0xc002d97c7f3321d2)) ||
      !expect(malbolge_guest_math_atan2_special(
                  UINT64_C(0x7ff0000000000000),
                  UINT64_C(0xbff0000000000000)),
              MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED,
              UINT64_C(0x3ff921fb54442d18))) {
    return 6;
  }
  if (!expect(malbolge_guest_math_atan2_special(
                  UINT64_C(0x3ff0000000000000),
                  UINT64_C(0x7ff0000000000000)),
              MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED, UINT64_C(0)) ||
      !expect(malbolge_guest_math_atan2_special(
                  UINT64_C(0xbff0000000000000),
                  UINT64_C(0xfff0000000000000)),
              MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED,
              UINT64_C(0xc00921fb54442d18)) ||
      !expect(malbolge_guest_math_atan2_special(
                  UINT64_C(0x3ff0000000000000),
                  UINT64_C(0x3ff0000000000000)),
              MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED,
              UINT64_C(0x3fe921fb54442d18)) ||
      !expect(malbolge_guest_math_atan2_special(
                  UINT64_C(0x3ff0000000000000),
                  UINT64_C(0x4000000000000000)),
              MALBOLGE_GUEST_MATH_SPECIAL_KERNEL_REQUIRED, UINT64_C(0))) {
    return 7;
  }
  if (!expect(malbolge_guest_math_atan2_special(
                  UINT64_C(0xbff0000000000000),
                  UINT64_C(0x3ff0000000000000)),
              MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED,
              UINT64_C(0xbfe921fb54442d18)) ||
      !expect(malbolge_guest_math_atan2_special(
                  UINT64_C(0x0000000000000001),
                  UINT64_C(0x8000000000000001)),
              MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED,
              UINT64_C(0x4002d97c7f3321d2)) ||
      !expect(malbolge_guest_math_atan2_special(
                  UINT64_C(0xffefffffffffffff),
                  UINT64_C(0xffefffffffffffff)),
              MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED,
              UINT64_C(0xc002d97c7f3321d2))) {
    return 8;
  }
  if (!expect(malbolge_guest_math_atan2_special(
                  UINT64_C(0x7ff8000000000001),
                  UINT64_C(0x3ff0000000000000)),
              MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED,
              UINT64_C(0x7ff8000000000000))) {
    return 9;
  }
  if (!expect(malbolge_guest_math_atan2_special(
                  UINT64_C(0x3e40000000000000),
                  UINT64_C(0x3ff0000000000000)),
              MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED,
              UINT64_C(0x3e40000000000000)) ||
      !expect(malbolge_guest_math_atan2_special(
                  UINT64_C(0xbe40000000000000),
                  UINT64_C(0x3ff0000000000000)),
              MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED,
              UINT64_C(0xbe40000000000000)) ||
      !expect(malbolge_guest_math_atan2_special(
                  UINT64_C(0x0000000000000001),
                  UINT64_C(0x3ff0000000000000)),
              MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED,
              UINT64_C(0x0000000000000001))) {
    return 10;
  }
  if (!expect(malbolge_guest_math_atan2_special(
                  UINT64_C(0x3e40000000000001),
                  UINT64_C(0x3ff0000000000000)),
              MALBOLGE_GUEST_MATH_SPECIAL_KERNEL_REQUIRED, UINT64_C(0)) ||
      !expect(malbolge_guest_math_atan2_special(
                  UINT64_C(0x3e40000000000000),
                  UINT64_C(0xbff0000000000000)),
              MALBOLGE_GUEST_MATH_SPECIAL_KERNEL_REQUIRED, UINT64_C(0))) {
    return 11;
  }
  if (!expect(malbolge_guest_math_atan2_special(
                  UINT64_C(0x9e102cdcf338d4ba),
                  UINT64_C(0x4008000000000000)),
              MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED,
              UINT64_C(0x9df5912699a11ba3)) ||
      !expect(malbolge_guest_math_atan2_special(
                  UINT64_C(0x801eabb56873d46a),
                  UINT64_C(0x4008000000000000)),
              MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED,
              UINT64_C(0x800a393c78269c23))) {
    return 12;
  }
  if (!expect(malbolge_guest_math_atan2_special(
                  UINT64_C(0x0000000000000003),
                  UINT64_C(0x4000000000000000)),
              MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED,
              UINT64_C(0x0000000000000001)) ||
      !expect(malbolge_guest_math_atan2_special(
                  UINT64_C(0x8000000000000003),
                  UINT64_C(0x4000000000000000)),
              MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED,
              UINT64_C(0x8000000000000001))) {
    return 13;
  }
  return 0;
}
