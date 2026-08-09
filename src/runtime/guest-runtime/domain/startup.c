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
//   - One-time guest heap binding and allocation entry points.
// - Must-Not:
//   - Allocate host memory, infer heap bounds, or silently rebind.
// - Allows:
//   - Inputs: selected guest heap arena and allocation requests.
//   - Outputs: runtime status and pointers into the bound guest arena.
//   - Side effects: guest runtime state plus bound heap memory.
// - Split-When:
//   - Another runtime state family needs independent startup policy.
// - Merge-When:
//   - Compiler startup directly owns this heap-binding lifecycle.
// - Summary:
//   - Binds one deterministic guest heap before allocation wrappers.
// - Description:
//   - Prebind calls fail and successful binding is one-shot.
// - Usage:
//   - Compiler startup binds; guest allocation wrappers delegate.
// - Defaults:
//   - No ambient host heap or implicit prebind fallback exists.
//

//! One-time guest heap startup binding and allocation delegation.

#include "guest_runtime.h"

#include <stddef.h>

static MalbolgeGuestHeap runtime_heap;
static uint32_t runtime_heap_bound = UINT32_C(0);

MalbolgeGuestRuntimeStatus malbolge_guest_runtime_bind_heap(void *arena,
                                                            uint32_t capacity) {
  MalbolgeGuestRuntimeStatus status = MALBOLGE_GUEST_RUNTIME_VALID;

  if (runtime_heap_bound != UINT32_C(0)) {
    return MALBOLGE_GUEST_RUNTIME_ALREADY_INITIALIZED;
  }
  status = malbolge_guest_heap_init(&runtime_heap, arena, capacity);
  if (status != MALBOLGE_GUEST_RUNTIME_VALID) {
    return status;
  }
  runtime_heap_bound = UINT32_C(1);
  return MALBOLGE_GUEST_RUNTIME_VALID;
}

static int runtime_is_bound(void) { return runtime_heap_bound != UINT32_C(0); }

MalbolgeGuestRuntimeStatus malbolge_guest_runtime_allocate(uint32_t size,
                                                           void **result) {
  if (!runtime_is_bound()) {
    if (result != NULL) {
      *result = NULL;
    }
    return MALBOLGE_GUEST_RUNTIME_NOT_INITIALIZED;
  }
  return malbolge_guest_heap_allocate(&runtime_heap, size, result);
}

MalbolgeGuestRuntimeStatus
malbolge_guest_runtime_allocate_zeroed(uint32_t count, uint32_t size,
                                       void **result) {
  if (!runtime_is_bound()) {
    if (result != NULL) {
      *result = NULL;
    }
    return MALBOLGE_GUEST_RUNTIME_NOT_INITIALIZED;
  }
  return malbolge_guest_heap_allocate_zeroed(&runtime_heap, count, size,
                                             result);
}

MalbolgeGuestRuntimeStatus
malbolge_guest_runtime_resize(void *pointer, uint32_t size, void **result) {
  if (!runtime_is_bound()) {
    if (result != NULL) {
      *result = NULL;
    }
    return MALBOLGE_GUEST_RUNTIME_NOT_INITIALIZED;
  }
  return malbolge_guest_heap_resize(&runtime_heap, pointer, size, result);
}

MalbolgeGuestRuntimeStatus malbolge_guest_runtime_release(void *pointer) {
  if (!runtime_is_bound()) {
    return MALBOLGE_GUEST_RUNTIME_NOT_INITIALIZED;
  }
  return malbolge_guest_heap_release(&runtime_heap, pointer);
}
