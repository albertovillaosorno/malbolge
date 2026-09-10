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
//   - Executable public sine/cosine symbol conformance without host libm.
// - Must-Not:
//   - Compute expected values with host transcendental functions.
// - Allows:
//   - Inputs: fixed raw binary64 words spanning special/sub-four/periodic
//     paths.
//   - Outputs: zero on exact bit agreement, otherwise a stable status.
//   - Side effects: none.
// - Split-When:
//   - Another public transcendental needs an independent executable harness.
// - Merge-When:
//   - The no-CRT libc harness owns these same high-precision cases.
// - Summary:
//   - Checks public sin/cos bits through maximum finite binary64.
// - Description:
//   - Uses source-certified expected words rather than host libm.
// - Usage:
//   - Linked with math_sincos and transcendental substrate in tests.
// - Defaults:
//   - Canonical NaN and signed-zero behavior are part of the public contract.
//

//! Exact public sine/cosine result vectors without host libm.

#include "math.h"

#include <stdint.h>

typedef union TestSincosBits {
  double value;
  uint64_t bits;
} TestSincosBits;

static double from_bits(uint64_t bits) {
  TestSincosBits value = {.bits = bits};
  return value.value;
}

static uint64_t to_bits(double value) {
  TestSincosBits representation = {.value = value};
  return representation.bits;
}

int main(void) {
  const uint64_t one = UINT64_C(0x3ff0000000000000);
  const uint64_t max_finite = UINT64_C(0x7fefffffffffffff);
  if (to_bits(sin(from_bits(one))) != UINT64_C(0x3feaed548f090cee) ||
      to_bits(cos(from_bits(one))) != UINT64_C(0x3fe14a280fb5068c)) {
    return 1;
  }
  if (to_bits(sin(from_bits(max_finite))) != UINT64_C(0x3f7452fc98b34e97) ||
      to_bits(cos(from_bits(max_finite))) != UINT64_C(0xbfefffe62ecfab75)) {
    return 2;
  }
  if (to_bits(sin(from_bits(UINT64_C(0x8000000000000000)))) !=
          UINT64_C(0x8000000000000000) ||
      to_bits(cos(from_bits(UINT64_C(0x0000000000000000)))) !=
          UINT64_C(0x3ff0000000000000) ||
      to_bits(sin(from_bits(UINT64_C(0x7ff0000000000000)))) !=
          UINT64_C(0x7ff8000000000000)) {
    return 3;
  }
  return 0;
}
