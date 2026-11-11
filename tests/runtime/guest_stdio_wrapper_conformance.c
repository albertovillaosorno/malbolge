// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Execution vectors for guest getchar/putchar wrapper semantics.
// - Must-Not:
//   - Use host standard streams as intrinsic or result authority.
// - Allows:
//   - Inputs: deterministic intrinsic words and captured output bytes.
//   - Outputs: zero status only when wrappers match the guest ABI.
//   - Side effects: test-local intrinsic cursor and output state only.
// - Split-When:
//   - Formatting or buffered streams need independent conformance.
// - Merge-When:
//   - Another suite owns these exact byte-wrapper vectors.
// - Summary:
//   - Executes byte-I/O wrappers against deterministic intrinsic stubs.
// - Description:
//   - Proves byte, EOF, invalid input, output, and return semantics.
// - Usage:
//   - Built by runtime tests with the production wrapper source.
// - Defaults:
//   - Test intrinsic stubs cannot satisfy target lowering.
//

//! Native vectors for public guest C byte-I/O wrappers using test intrinsics.

#include "guest_intrinsics.h"
#include "guest_runtime.h"
#include "stdio.h"

#include <stdint.h>

int malbolge_test_getchar(void);
int malbolge_test_putchar(int value);

enum {
  ALL_BYTES = 256,
  EDGE_OUTPUTS = 5,
};

static uint32_t input_index = UINT32_C(0);
static uint8_t output_bytes[ALL_BYTES + EDGE_OUTPUTS];
static uint32_t output_count = UINT32_C(0);

uint32_t malbolge_guest_intrinsic_input_word(void) {
  uint32_t word = UINT32_MAX;
  if (input_index < UINT32_C(256)) {
    word = input_index;
  } else if (input_index == UINT32_C(256)) {
    word = MALBOLGE_GUEST_PROFILE_EOF_WORD;
  } else if (input_index == UINT32_C(257)) {
    word = UINT32_C(256);
  }
  ++input_index;
  return word;
}

void malbolge_guest_intrinsic_output_byte(uint8_t value) {
  if (output_count < sizeof(output_bytes)) {
    output_bytes[output_count] = value;
  }
  ++output_count;
}

int main(void) {
  static const int EDGE_VALUES[EDGE_OUTPUTS] = {
      -1, 256, -257, INT32_MIN, INT32_MAX};
  static const uint8_t EDGE_BYTES[EDGE_OUTPUTS] = {
      UINT8_C(255), UINT8_C(0), UINT8_C(255), UINT8_C(0), UINT8_C(255)};

  for (uint32_t index = 0U; index < UINT32_C(256); ++index) {
    if (malbolge_test_getchar() != (int)index) {
      return 1;
    }
  }
  if (malbolge_test_getchar() != EOF ||
      malbolge_test_getchar() != EOF ||
      malbolge_test_getchar() != EOF || input_index != UINT32_C(259)) {
    return 2;
  }

  for (uint32_t index = 0U; index < UINT32_C(256); ++index) {
    if (malbolge_test_putchar((int)index) != (int)index ||
        output_count != index + 1U ||
        output_bytes[index] != (uint8_t)index) {
      return 3;
    }
  }
  for (uint32_t index = 0U; index < EDGE_OUTPUTS; ++index) {
    if (malbolge_test_putchar(EDGE_VALUES[index]) != (int)EDGE_BYTES[index] ||
        output_count != UINT32_C(256) + index + 1U ||
        output_bytes[ALL_BYTES + index] != EDGE_BYTES[index]) {
      return 4;
    }
  }
  if (output_count != ALL_BYTES + EDGE_OUTPUTS) {
    return 5;
  }
  return 0;
}
