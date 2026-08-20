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
//   - Pure guest mapping between profile I/O words and C byte-stream values.
// - Must-Not:
//   - Read host streams, inherit host EOF, locale, or text-mode translation.
// - Allows:
//   - Inputs: canonical malbolge-2026 input words and C output integers.
//   - Outputs: C getchar-style value or low-eight-bit output byte.
//   - Side effects: none.
// - Split-When:
//   - Stream buffering or formatting gains an independent semantic lifecycle.
// - Merge-When:
//   - Another runtime module owns these exact profile/C conversion rules.
// - Summary:
//   - Deterministic byte-I/O conversion independent of host stdio.
// - Description:
//   - Rejects impossible non-byte/non-EOF profile input words explicitly.
// - Usage:
//   - Used by guest stdio wrappers and ternary/runtime lowering.
// - Defaults:
//   - Profile EOF becomes -1; output is modulo 256.
//

//! Pure profile-word to C-byte stream semantic mapping.

#include "guest_runtime.h"

#include <stddef.h>

MalbolgeGuestRuntimeStatus malbolge_guest_decode_input_word(uint32_t word,
                                                            int32_t *result) {
  if (result == NULL) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  if (word <= UINT32_C(255)) {
    *result = (int32_t)word;
    return MALBOLGE_GUEST_RUNTIME_VALID;
  }
  if (word == MALBOLGE_GUEST_PROFILE_EOF_WORD) {
    *result = INT32_C(-1);
    return MALBOLGE_GUEST_RUNTIME_VALID;
  }
  return MALBOLGE_GUEST_RUNTIME_INVALID_INPUT_WORD;
}

uint8_t malbolge_guest_output_byte(int32_t value) {
  return (uint8_t)((uint32_t)value & UINT32_C(255));
}
