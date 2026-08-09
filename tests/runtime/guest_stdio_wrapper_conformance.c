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

static const uint32_t INPUT_WORDS[] = {
    UINT32_C(65), MALBOLGE_GUEST_PROFILE_EOF_WORD, UINT32_C(256)};
static uint32_t input_index = UINT32_C(0);
static uint8_t last_output = UINT8_C(0);
static uint32_t output_count = UINT32_C(0);

uint32_t malbolge_guest_intrinsic_input_word(void) {
  const uint32_t word = INPUT_WORDS[input_index];
  ++input_index;
  return word;
}

void malbolge_guest_intrinsic_output_byte(uint8_t value) {
  last_output = value;
  ++output_count;
}

int main(void) {
  if (malbolge_test_getchar() != 65 || malbolge_test_getchar() != EOF ||
      malbolge_test_getchar() != EOF) {
    return 1;
  }
  if (malbolge_test_putchar(-1) != 255 || last_output != UINT8_C(255) ||
      output_count != UINT32_C(1)) {
    return 2;
  }
  if (malbolge_test_putchar(256) != 0 || last_output != UINT8_C(0) ||
      output_count != UINT32_C(2)) {
    return 3;
  }
  return 0;
}
