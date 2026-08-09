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
//   - Guest getchar/putchar wrappers over stable byte-I/O intrinsics.
// - Must-Not:
//   - Use host stdio, FILE state, locale, or text translation.
// - Allows:
//   - Inputs: profile input intrinsic and one C output integer.
//   - Outputs: C byte-or-EOF input and emitted unsigned-byte value.
//   - Side effects: one declared guest byte I/O intrinsic operation.
// - Split-When:
//   - Buffered streams or formatting gain independent ownership.
// - Merge-When:
//   - Guest runtime directly owns these byte-stream entry points.
// - Summary:
//   - Maps public C byte I/O to stable compiler intrinsic identities.
// - Description:
//   - Invalid intrinsic input maps to EOF; output returns emitted byte.
// - Usage:
//   - Linked once lane-9 lowering resolves the intrinsic symbols.
// - Defaults:
//   - Canonical libc keeps these unavailable until lowering is proven.
//

//! Guest C byte-stream wrappers over declaration-only target intrinsics.

#include "stdio.h"
#include "guest_intrinsics.h"
#include "guest_runtime.h"

#include <stdint.h>

int getchar(void) {
  int32_t decoded = INT32_C(-1);
  const uint32_t word = malbolge_guest_intrinsic_input_word();

  if (malbolge_guest_decode_input_word(word, &decoded) !=
      MALBOLGE_GUEST_RUNTIME_VALID) {
    return EOF;
  }
  return (int)decoded;
}

int putchar(int value) {
  const uint8_t byte = malbolge_guest_output_byte((int32_t)value);

  malbolge_guest_intrinsic_output_byte(byte);
  return (int)byte;
}
