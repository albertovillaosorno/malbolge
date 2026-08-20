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
//   - Execution vectors for guest libc allocation wrapper semantics.
// - Must-Not:
//   - Use host malloc-family behavior as guest allocation authority.
// - Allows:
//   - Inputs: test-renamed wrappers and guest startup heap binding.
//   - Outputs: zero status only when wrappers preserve runtime semantics.
//   - Side effects: one fixed test-local guest arena only.
// - Split-When:
//   - Another allocation surface needs independent wrapper policy.
// - Merge-When:
//   - Runtime tests directly own these wrapper vectors.
// - Summary:
//   - Executes malloc/calloc/realloc/free over the bound guest heap.
// - Description:
//   - Proves prebind null, zero-size, zeroing, resize, and release.
// - Usage:
//   - Built by runtime tests with test-renamed standard symbols.
// - Defaults:
//   - Production allocation names remain standard C names.
//

//! Native vectors for public guest allocation wrappers over guest runtime
//! state.

#include "guest_runtime.h"

#include <stddef.h>
#include <stdint.h>

void *malbolge_test_malloc(size_t size);
void *malbolge_test_calloc(size_t count, size_t size);
void *malbolge_test_realloc(void *pointer, size_t size);
void malbolge_test_free(void *pointer);

static int zero_bytes(const uint8_t *bytes, uint32_t count) {
  uint32_t index = 0U;

  while (index < count) {
    if (bytes[index] != UINT8_C(0)) {
      return 0;
    }
    ++index;
  }
  return 1;
}

int main(void) {
  alignas(16) uint8_t arena[256] = {0};
  void *first = NULL;
  void *zeroed = NULL;
  void *resized = NULL;

  if (malbolge_test_malloc((size_t)8U) != NULL ||
      malbolge_test_calloc((size_t)2U, (size_t)8U) != NULL ||
      malbolge_test_realloc(NULL, (size_t)8U) != NULL) {
    return 1;
  }
  malbolge_test_free(NULL);
  if (malbolge_guest_runtime_bind_heap(arena, (uint32_t)sizeof(arena)) !=
      MALBOLGE_GUEST_RUNTIME_VALID) {
    return 2;
  }
  if (malbolge_test_malloc((size_t)0U) != NULL ||
      malbolge_test_calloc((size_t)0U, (size_t)8U) != NULL) {
    return 3;
  }
  if (sizeof(size_t) > sizeof(uint32_t)) {
    const size_t too_large = (size_t)UINT32_MAX + (size_t)1U;

    if (malbolge_test_malloc(too_large) != NULL ||
        malbolge_test_calloc(too_large, (size_t)1U) != NULL ||
        malbolge_test_realloc(NULL, too_large) != NULL) {
      return 4;
    }
  }
  first = malbolge_test_malloc((size_t)8U);
  zeroed = malbolge_test_calloc((size_t)2U, (size_t)8U);
  if (first == NULL || zeroed == NULL ||
      !zero_bytes((const uint8_t *)zeroed, UINT32_C(16))) {
    return 5;
  }
  ((uint8_t *)first)[0] = UINT8_C(0x5a);
  resized = malbolge_test_realloc(first, (size_t)40U);
  if (resized == NULL || ((uint8_t *)resized)[0] != UINT8_C(0x5a)) {
    return 6;
  }
  malbolge_test_free(zeroed);
  malbolge_test_free(resized);
  return 0;
}
