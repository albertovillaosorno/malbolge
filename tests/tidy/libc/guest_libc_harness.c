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
//   - Executable no-CRT behavior checks for the available guest libc subset.
// - Must-Not:
//   - Link a host C runtime or test routines still marked unavailable.
// - Allows:
//   - Inputs: fixed in-process byte arrays and narrow strings.
//   - Outputs: zero on exact semantic agreement, otherwise a stable code.
//   - Side effects: writes only to local automatic arrays.
// - Split-When:
//   - Split when another libc family requires an independent executable probe.
// - Merge-When:
//   - Merge when another harness owns these exact guest-library semantics.
// - Summary:
//   - No-CRT executable evidence for available guest libc routines.
// - Description:
//   - Exercises all currently available malbolge-libc-v1 function symbols.
// - Usage:
//   - Compiled with the pinned Clang and linked with lld-link `/nodefaultlib`.
// - Defaults:
//   - Any semantic mismatch returns a distinct nonzero process status.
//

//! Executable guest-libc regression with no host C runtime dependency.

#include "math.h"
#include "string.h"

#include <stdint.h>

#if defined(_MSC_VER)
int _fltused = 0;
#endif

typedef union TestBinary64Bits {
  double value;
  uint64_t bits;
} TestBinary64Bits;

static double double_from_bits(uint64_t bits) {
  TestBinary64Bits representation = {.bits = bits};
  return representation.value;
}

static uint64_t double_bits(double value) {
  TestBinary64Bits representation = {.value = value};
  return representation.bits;
}

static int test_exact_math(void) {
  const uint64_t positive_zero = UINT64_C(0x0000000000000000);
  const uint64_t negative_zero = UINT64_C(0x8000000000000000);
  const uint64_t positive_half = UINT64_C(0x3fe0000000000000);
  const uint64_t negative_half = UINT64_C(0xbfe0000000000000);
  const uint64_t positive_one = UINT64_C(0x3ff0000000000000);
  const uint64_t negative_one = UINT64_C(0xbff0000000000000);
  const uint64_t positive_one_half = UINT64_C(0x3ff8000000000000);
  const uint64_t negative_one_half = UINT64_C(0xbff8000000000000);
  const uint64_t positive_two = UINT64_C(0x4000000000000000);
  const uint64_t negative_two = UINT64_C(0xc000000000000000);
  const uint64_t positive_infinity = UINT64_C(0x7ff0000000000000);
  const uint64_t negative_infinity = UINT64_C(0xfff0000000000000);
  const uint64_t positive_subnormal = UINT64_C(0x0000000000000001);
  const uint64_t negative_subnormal = UINT64_C(0x8000000000000001);
  const uint64_t quiet_nan = UINT64_C(0x7ff8123456789abc);
  const uint64_t signaling_nan = UINT64_C(0x7ff0000000000001);
  const uint64_t canonical_nan = UINT64_C(0x7ff8000000000000);

  if (double_bits(fabs(double_from_bits(negative_zero))) != positive_zero ||
      double_bits(fabs(double_from_bits(negative_one_half))) !=
          positive_one_half ||
      double_bits(fabs(double_from_bits(negative_infinity))) !=
          positive_infinity ||
      double_bits(fabs(double_from_bits(quiet_nan))) != canonical_nan ||
      double_bits(fabs(double_from_bits(signaling_nan))) != canonical_nan) {
    return 1;
  }
  if (double_bits(trunc(double_from_bits(positive_half))) != positive_zero ||
      double_bits(trunc(double_from_bits(negative_half))) != negative_zero ||
      double_bits(trunc(double_from_bits(positive_one_half))) != positive_one ||
      double_bits(trunc(double_from_bits(negative_one_half))) != negative_one ||
      double_bits(trunc(double_from_bits(positive_subnormal))) !=
          positive_zero ||
      double_bits(trunc(double_from_bits(negative_subnormal))) !=
          negative_zero ||
      double_bits(trunc(double_from_bits(negative_infinity))) !=
          negative_infinity ||
      double_bits(trunc(double_from_bits(quiet_nan))) != canonical_nan) {
    return 2;
  }
  if (double_bits(floor(double_from_bits(positive_half))) != positive_zero ||
      double_bits(floor(double_from_bits(negative_half))) != negative_one ||
      double_bits(floor(double_from_bits(positive_one_half))) != positive_one ||
      double_bits(floor(double_from_bits(negative_one_half))) != negative_two ||
      double_bits(floor(double_from_bits(positive_subnormal))) !=
          positive_zero ||
      double_bits(floor(double_from_bits(negative_subnormal))) !=
          negative_one ||
      double_bits(floor(double_from_bits(negative_zero))) != negative_zero ||
      double_bits(floor(double_from_bits(positive_infinity))) !=
          positive_infinity ||
      double_bits(floor(double_from_bits(signaling_nan))) != canonical_nan) {
    return 3;
  }
  if (double_bits(ceil(double_from_bits(positive_half))) != positive_one ||
      double_bits(ceil(double_from_bits(negative_half))) != negative_zero ||
      double_bits(ceil(double_from_bits(positive_one_half))) != positive_two ||
      double_bits(ceil(double_from_bits(negative_one_half))) != negative_one ||
      double_bits(ceil(double_from_bits(positive_subnormal))) != positive_one ||
      double_bits(ceil(double_from_bits(negative_subnormal))) !=
          negative_zero ||
      double_bits(ceil(double_from_bits(negative_zero))) != negative_zero ||
      double_bits(ceil(double_from_bits(negative_infinity))) !=
          negative_infinity ||
      double_bits(ceil(double_from_bits(quiet_nan))) != canonical_nan) {
    return 4;
  }
  return 0;
}

static int test_sqrt(void) {
  const uint64_t positive_zero = UINT64_C(0x0000000000000000);
  const uint64_t negative_zero = UINT64_C(0x8000000000000000);
  const uint64_t min_subnormal = UINT64_C(0x0000000000000001);
  const uint64_t min_subnormal_root = UINT64_C(0x1e60000000000000);
  const uint64_t positive_two = UINT64_C(0x4000000000000000);
  const uint64_t sqrt_two = UINT64_C(0x3ff6a09e667f3bcd);
  const uint64_t positive_four = UINT64_C(0x4010000000000000);
  const uint64_t positive_infinity = UINT64_C(0x7ff0000000000000);
  const uint64_t negative_one = UINT64_C(0xbff0000000000000);
  const uint64_t signaling_nan = UINT64_C(0x7ff0000000000001);
  const uint64_t canonical_nan = UINT64_C(0x7ff8000000000000);

  if (double_bits(sqrt(double_from_bits(positive_zero))) != positive_zero ||
      double_bits(sqrt(double_from_bits(negative_zero))) != negative_zero ||
      double_bits(sqrt(double_from_bits(min_subnormal))) !=
          min_subnormal_root ||
      double_bits(sqrt(double_from_bits(positive_two))) != sqrt_two ||
      double_bits(sqrt(double_from_bits(positive_four))) != positive_two ||
      double_bits(sqrt(double_from_bits(positive_infinity))) !=
          positive_infinity ||
      double_bits(sqrt(double_from_bits(negative_one))) != canonical_nan ||
      double_bits(sqrt(double_from_bits(signaling_nan))) != canonical_nan) {
    return 1;
  }
  return 0;
}

static int same_bytes(const unsigned char *left, const unsigned char *right,
                      size_t count) {
  return memcmp(left, right, count) == 0;
}

int probe_entry(void) {
  unsigned char source[6] = {1U, 2U, 3U, 4U, 5U, 6U};
  unsigned char copied[6] = {0U, 0U, 0U, 0U, 0U, 0U};
  unsigned char moved[7] = {1U, 2U, 3U, 4U, 5U, 6U, 7U};
  unsigned char expected_move[7] = {1U, 2U, 1U, 2U, 3U, 4U, 5U};
  char text[16] = "abc";
  char copy[8];
  char bounded[6] = {'x', 'x', 'x', 'x', 'x', 'x'};

  if (memcpy(copied, source, sizeof(source)) != copied ||
      !same_bytes(copied, source, sizeof(source))) {
    return 1;
  }
  if (memset(copied, 0xa5, 3U) != copied || copied[0] != 0xa5U ||
      copied[1] != 0xa5U || copied[2] != 0xa5U) {
    return 2;
  }
  if (memmove(moved + 2, moved, 5U) != moved + 2 ||
      !same_bytes(moved, expected_move, sizeof(moved))) {
    return 3;
  }
  if (strlen(text) != 3U || strcmp("abc", "abc") != 0 ||
      strcmp("abc", "abd") >= 0 || strcmp("abd", "abc") <= 0) {
    return 4;
  }
  if (strcpy(copy, "guest") != copy || strcmp(copy, "guest") != 0) {
    return 5;
  }
  if (strncpy(bounded, "ab", sizeof(bounded)) != bounded || bounded[0] != 'a' ||
      bounded[1] != 'b' || bounded[2] != '\0' || bounded[5] != '\0') {
    return 6;
  }
  if (strcat(text, "def") != text || strcmp(text, "abcdef") != 0) {
    return 7;
  }
  {
    const int math_result = test_exact_math();
    if (math_result != 0) {
      return 10 + math_result;
    }
  }
  {
    const int sqrt_result = test_sqrt();
    if (sqrt_result != 0) {
      return 20 + sqrt_result;
    }
  }
  return 0;
}
