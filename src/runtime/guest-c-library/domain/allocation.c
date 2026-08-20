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
//   - Guest libc allocation wrappers over the startup-bound guest heap.
// - Must-Not:
//   - Call host allocation, bind heap storage, or define C23 UB.
// - Allows:
//   - Inputs: guest allocation calls after runtime startup.
//   - Outputs: guest-arena pointers, null, and `free` side effects.
//   - Side effects: bound guest heap mutation through guest-runtime only.
// - Split-When:
//   - Another allocation ABI needs independent wrappers.
// - Merge-When:
//   - Guest runtime directly owns the public allocation entry points.
// - Summary:
//   - Public C allocation wrappers backed only by guest heap state.
// - Description:
//   - Runtime failures map to null; nonnull zero realloc remains C23 UB.
// - Usage:
//   - Linked after compiler startup binding is enabled.
// - Defaults:
//   - Libc authority keeps these unavailable until startup is proven.
//

//! Guest libc allocation wrappers over the deterministic startup-bound heap.

#include "guest_runtime.h"
#include "stdlib.h"

#include <stdint.h>

static int size_fits_guest(size_t size) { return size <= (size_t)UINT32_MAX; }

void *malloc(size_t size) {
  void *result = NULL;

  if (!size_fits_guest(size) ||
      malbolge_guest_runtime_allocate((uint32_t)size, &result) !=
          MALBOLGE_GUEST_RUNTIME_VALID) {
    return NULL;
  }
  return result;
}

void *calloc(size_t count, size_t size) {
  void *result = NULL;

  if (!size_fits_guest(count) || !size_fits_guest(size) ||
      malbolge_guest_runtime_allocate_zeroed((uint32_t)count, (uint32_t)size,
                                             &result) !=
          MALBOLGE_GUEST_RUNTIME_VALID) {
    return NULL;
  }
  return result;
}

void *realloc(void *pointer, size_t size) {
  void *result = NULL;

  if (!size_fits_guest(size) ||
      malbolge_guest_runtime_resize(pointer, (uint32_t)size, &result) !=
          MALBOLGE_GUEST_RUNTIME_VALID) {
    return NULL;
  }
  return result;
}

void free(void *pointer) { (void)malbolge_guest_runtime_release(pointer); }
