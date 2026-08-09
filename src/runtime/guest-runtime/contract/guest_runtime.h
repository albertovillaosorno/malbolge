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
//   - Version-one guest heap, frame, startup, and byte interfaces.
// - Must-Not:
//   - Expose host allocation, I/O handles, callbacks, or pointer widths.
// - Allows:
//   - Inputs: guest heap arena, frame values, and profile I/O words.
//   - Outputs: deterministic statuses, pointers, frames, and byte values.
//   - Side effects: bound guest-memory mutation only.
// - Split-When:
//   - Another runtime family needs independent ABI policy.
// - Merge-When:
//   - Another runtime contract owns these exact semantics.
// - Summary:
//   - Stable guest-owned runtime interfaces for version one.
// - Description:
//   - Fixed-width state follows malbolge-c32-v1 logical byte semantics.
// - Usage:
//   - Used by guest libc, startup, and downstream lowering.
// - Defaults:
//   - Invalid state fails closed and no host fallback exists.
//

//! Version-one guest runtime semantic contract without host-defined fallbacks.

#ifndef MALBOLGE_GUEST_RUNTIME_H
#define MALBOLGE_GUEST_RUNTIME_H

#include <stdint.h>

#define MALBOLGE_GUEST_FRAME_HEADER_SIZE UINT32_C(32)
#define MALBOLGE_GUEST_HEAP_ALIGNMENT UINT32_C(16)
#define MALBOLGE_GUEST_HEAP_HEADER_SIZE UINT32_C(16)
#define MALBOLGE_GUEST_PROFILE_EOF_WORD UINT32_C(4782968)

/** Stable status values for guest runtime core operations. */
typedef enum MalbolgeGuestRuntimeStatus {
  MALBOLGE_GUEST_RUNTIME_VALID = 0,
  MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT = 1,
  MALBOLGE_GUEST_RUNTIME_OUT_OF_MEMORY = 2,
  MALBOLGE_GUEST_RUNTIME_CORRUPT_STATE = 3,
  MALBOLGE_GUEST_RUNTIME_INVALID_INPUT_WORD = 4,
  MALBOLGE_GUEST_RUNTIME_INVALID_FRAME = 5,
  MALBOLGE_GUEST_RUNTIME_NOT_INITIALIZED = 6,
  MALBOLGE_GUEST_RUNTIME_ALREADY_INITIALIZED = 7
} MalbolgeGuestRuntimeStatus;

/** Canonical decoded malbolge-c32-v1 hidden call-frame header. */
typedef struct MalbolgeGuestFrameHeader {
  uint32_t previous_frame;
  uint32_t continuation_id;
  uint32_t function_id;
  uint32_t frame_extent;
  uint32_t argument_block;
  uint32_t result_block;
  uint32_t variadic_begin;
  uint32_t flags;
} MalbolgeGuestFrameHeader;

/** Caller-owned state for one deterministic guest heap arena. */
typedef struct MalbolgeGuestHeap {
  uint8_t *arena;
  uint32_t capacity;
  uint32_t used;
} MalbolgeGuestHeap;

MalbolgeGuestRuntimeStatus malbolge_guest_runtime_bind_heap(void *arena,
                                                            uint32_t capacity);
MalbolgeGuestRuntimeStatus malbolge_guest_runtime_allocate(uint32_t size,
                                                           void **result);
MalbolgeGuestRuntimeStatus
malbolge_guest_runtime_allocate_zeroed(uint32_t count, uint32_t size,
                                       void **result);
MalbolgeGuestRuntimeStatus
malbolge_guest_runtime_resize(void *pointer, uint32_t size, void **result);
MalbolgeGuestRuntimeStatus malbolge_guest_runtime_release(void *pointer);

MalbolgeGuestRuntimeStatus
malbolge_guest_frame_validate(const MalbolgeGuestFrameHeader *frame);
MalbolgeGuestRuntimeStatus
malbolge_guest_frame_encode(const MalbolgeGuestFrameHeader *frame,
                            uint8_t *wire, uint32_t wire_size);
MalbolgeGuestRuntimeStatus
malbolge_guest_frame_decode(const uint8_t *wire, uint32_t wire_size,
                            MalbolgeGuestFrameHeader *frame);

MalbolgeGuestRuntimeStatus malbolge_guest_heap_init(MalbolgeGuestHeap *heap,
                                                    void *arena,
                                                    uint32_t capacity);
MalbolgeGuestRuntimeStatus malbolge_guest_heap_allocate(MalbolgeGuestHeap *heap,
                                                        uint32_t size,
                                                        void **result);
MalbolgeGuestRuntimeStatus
malbolge_guest_heap_allocate_zeroed(MalbolgeGuestHeap *heap, uint32_t count,
                                    uint32_t size, void **result);
MalbolgeGuestRuntimeStatus malbolge_guest_heap_resize(MalbolgeGuestHeap *heap,
                                                      void *pointer,
                                                      uint32_t size,
                                                      void **result);
MalbolgeGuestRuntimeStatus malbolge_guest_heap_release(MalbolgeGuestHeap *heap,
                                                       void *pointer);

MalbolgeGuestRuntimeStatus malbolge_guest_decode_input_word(uint32_t word,
                                                            int32_t *result);
uint8_t malbolge_guest_output_byte(int32_t value);

#endif
