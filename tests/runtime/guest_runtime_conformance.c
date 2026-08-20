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
//   - Independent C conformance vectors for guest heap and byte-stream v1.
// - Must-Not:
//   - Call host allocation/stdio or depend on host pointer serialization.
// - Allows:
//   - Inputs: guest-runtime C contract and implementation under strict Clang.
//   - Outputs: zero status only when deterministic semantic vectors all pass.
//   - Side effects: fixed test-process byte arenas only.
// - Split-When:
//   - Another guest runtime family needs independently versioned vectors.
// - Merge-When:
//   - One generated conformance suite owns these exact runtime semantics.
// - Summary:
//   - Locks deterministic allocator metadata and profile byte semantics.
// - Description:
//   - Uses aligned local arenas and inspects canonical metadata bytes directly.
// - Usage:
//   - Compiled by `tests/test_guest_runtime_c.py` with repository Clang.
// - Defaults:
//   - No host allocator or stream is linked by the runtime implementation.
//

//! Independent C vectors for guest-runtime heap and byte-I/O semantics.

#include "guest_runtime.h"

#include <stddef.h>
#include <stdint.h>

static int all_zero(const uint8_t *bytes, uint32_t count) {
  uint32_t index = 0U;

  while (index < count) {
    if (bytes[index] != UINT8_C(0)) {
      return 0;
    }
    ++index;
  }
  return 1;
}

static int bytes_equal(const uint8_t *left, const uint8_t *right,
                       uint32_t count) {
  uint32_t index = 0U;

  while (index < count) {
    if (left[index] != right[index]) {
      return 0;
    }
    ++index;
  }
  return 1;
}

static int test_frame_codec(void) {
  const MalbolgeGuestFrameHeader frame = {
      .previous_frame = UINT32_C(0x01020304),
      .continuation_id = UINT32_C(0x11223344),
      .function_id = UINT32_C(0x55667788),
      .frame_extent = UINT32_C(80),
      .argument_block = UINT32_C(0x00000101),
      .result_block = UINT32_C(0),
      .variadic_begin = UINT32_C(0x00000201),
      .flags = UINT32_C(0),
  };
  const uint8_t expected[MALBOLGE_GUEST_FRAME_HEADER_SIZE] = {
      0x04, 0x03, 0x02, 0x01, 0x44, 0x33, 0x22, 0x11, 0x88, 0x77, 0x66,
      0x55, 0x50, 0x00, 0x00, 0x00, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
      0x00, 0x00, 0x01, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  };
  uint8_t wire[MALBOLGE_GUEST_FRAME_HEADER_SIZE] = {0};
  MalbolgeGuestFrameHeader decoded = {0};
  MalbolgeGuestFrameHeader invalid = frame;

  if (malbolge_guest_frame_encode(&frame, wire, (uint32_t)sizeof(wire)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      !bytes_equal(wire, expected, (uint32_t)sizeof(wire))) {
    return 1;
  }
  if (malbolge_guest_frame_decode(wire, (uint32_t)sizeof(wire), &decoded) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      decoded.previous_frame != frame.previous_frame ||
      decoded.continuation_id != frame.continuation_id ||
      decoded.function_id != frame.function_id ||
      decoded.frame_extent != frame.frame_extent ||
      decoded.argument_block != frame.argument_block ||
      decoded.result_block != frame.result_block ||
      decoded.variadic_begin != frame.variadic_begin ||
      decoded.flags != frame.flags) {
    return 2;
  }
  invalid.argument_block = UINT32_C(0);
  wire[0] = UINT8_C(0xa5);
  if (malbolge_guest_frame_encode(&invalid, wire, (uint32_t)sizeof(wire)) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_FRAME ||
      wire[0] != UINT8_C(0xa5)) {
    return 3;
  }
  invalid = frame;
  invalid.frame_extent = UINT32_C(33);
  if (malbolge_guest_frame_validate(&invalid) !=
      MALBOLGE_GUEST_RUNTIME_INVALID_FRAME) {
    return 4;
  }
  decoded.function_id = UINT32_C(0xdeadbeef);
  wire[0] = expected[0];
  wire[28] = UINT8_C(1);
  if (malbolge_guest_frame_decode(wire, (uint32_t)sizeof(wire), &decoded) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_FRAME ||
      decoded.function_id != UINT32_C(0xdeadbeef)) {
    return 5;
  }
  return malbolge_guest_frame_decode(expected, UINT32_C(31), &decoded) ==
                 MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT
             ? 0
             : 6;
}

static int test_byte_stream(void) {
  int32_t value = INT32_C(99);

  if (malbolge_guest_decode_input_word(UINT32_C(0), &value) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      value != INT32_C(0)) {
    return 1;
  }
  if (malbolge_guest_decode_input_word(UINT32_C(255), &value) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      value != INT32_C(255)) {
    return 2;
  }
  if (malbolge_guest_decode_input_word(MALBOLGE_GUEST_PROFILE_EOF_WORD,
                                       &value) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      value != INT32_C(-1)) {
    return 3;
  }
  if (malbolge_guest_decode_input_word(UINT32_C(256), &value) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_INPUT_WORD ||
      malbolge_guest_decode_input_word(UINT32_C(0), NULL) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT) {
    return 4;
  }
  if (malbolge_guest_output_byte(INT32_C(-1)) != UINT8_C(255) ||
      malbolge_guest_output_byte(INT32_C(256)) != UINT8_C(0) ||
      malbolge_guest_output_byte(INT32_C(511)) != UINT8_C(255)) {
    return 5;
  }
  return 0;
}

static int test_allocation_identity(void) {
  alignas(16) uint8_t arena[256] = {0};
  MalbolgeGuestHeap heap = {0};
  void *pointer = NULL;
  const uint8_t expected_header[16] = {
      0x20, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00,
      0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  };
  uint32_t index = 0U;

  if (malbolge_guest_heap_init(&heap, arena, (uint32_t)sizeof(arena)) !=
      MALBOLGE_GUEST_RUNTIME_VALID) {
    return 1;
  }
  if (malbolge_guest_heap_allocate(&heap, UINT32_C(0), &pointer) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      pointer != NULL || heap.used != UINT32_C(0)) {
    return 2;
  }
  if (malbolge_guest_heap_allocate(&heap, UINT32_C(1), &pointer) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      pointer != (void *)(arena + 16) || heap.used != UINT32_C(32) ||
      (((uintptr_t)pointer) & (uintptr_t)15U) != (uintptr_t)0U) {
    return 3;
  }
  while (index < (uint32_t)sizeof(expected_header)) {
    if (arena[index] != expected_header[index]) {
      return 4;
    }
    ++index;
  }
  return 0;
}

static int test_reuse_split_coalesce(void) {
  alignas(16) uint8_t arena[256] = {0};
  MalbolgeGuestHeap heap = {0};
  void *first = NULL;
  void *middle = NULL;
  void *last = NULL;
  void *reuse = NULL;

  if (malbolge_guest_heap_init(&heap, arena, (uint32_t)sizeof(arena)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_heap_allocate(&heap, UINT32_C(1), &first) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_heap_allocate(&heap, UINT32_C(33), &middle) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_heap_allocate(&heap, UINT32_C(1), &last) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      heap.used != UINT32_C(128)) {
    return 1;
  }
  if (malbolge_guest_heap_release(&heap, middle) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_heap_allocate(&heap, UINT32_C(1), &reuse) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      reuse != middle || heap.used != UINT32_C(128)) {
    return 2;
  }
  if (arena[32] != UINT8_C(32) || arena[64] != UINT8_C(32)) {
    return 3;
  }
  if (malbolge_guest_heap_release(&heap, reuse) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_heap_release(&heap, first) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_heap_allocate(&heap, UINT32_C(33), &reuse) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      reuse != first) {
    return 4;
  }
  if (malbolge_guest_heap_release(&heap, last) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      heap.used != UINT32_C(64)) {
    return 5;
  }
  if (malbolge_guest_heap_release(&heap, reuse) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      heap.used != UINT32_C(0)) {
    return 6;
  }
  return 0;
}

static int test_calloc_and_failures(void) {
  alignas(16) uint8_t arena[96] = {0};
  MalbolgeGuestHeap heap = {0};
  void *pointer = NULL;

  if (malbolge_guest_heap_init(&heap, arena, (uint32_t)sizeof(arena)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_heap_allocate_zeroed(&heap, UINT32_C(4), UINT32_C(7),
                                          &pointer) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      pointer == NULL || !all_zero((const uint8_t *)pointer, UINT32_C(28))) {
    return 1;
  }
  ((uint8_t *)pointer)[0] = UINT8_C(0x5a);
  if (malbolge_guest_heap_allocate_zeroed(&heap, UINT32_MAX, UINT32_C(2),
                                          &pointer) !=
          MALBOLGE_GUEST_RUNTIME_OUT_OF_MEMORY ||
      pointer != NULL) {
    return 2;
  }
  if (malbolge_guest_heap_allocate(&heap, UINT32_C(49), &pointer) !=
          MALBOLGE_GUEST_RUNTIME_OUT_OF_MEMORY ||
      pointer != NULL) {
    return 3;
  }
  return 0;
}

static int test_resize(void) {
  alignas(16) uint8_t arena[160] = {0};
  MalbolgeGuestHeap heap = {0};
  void *first = NULL;
  void *middle = NULL;
  void *last = NULL;
  void *resized = NULL;
  uint8_t *bytes = NULL;
  uint32_t index = 0U;

  if (malbolge_guest_heap_init(&heap, arena, (uint32_t)sizeof(arena)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_heap_allocate(&heap, UINT32_C(8), &first) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_heap_allocate(&heap, UINT32_C(8), &middle) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_heap_allocate(&heap, UINT32_C(8), &last) !=
          MALBOLGE_GUEST_RUNTIME_VALID) {
    return 1;
  }
  bytes = (uint8_t *)first;
  while (index < UINT32_C(8)) {
    bytes[index] = (uint8_t)(index + UINT32_C(1));
    ++index;
  }
  if (malbolge_guest_heap_release(&heap, middle) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_heap_resize(&heap, first, UINT32_C(24), &resized) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      resized != first) {
    return 2;
  }
  bytes = (uint8_t *)resized;
  for (index = 0U; index < UINT32_C(8); ++index) {
    if (bytes[index] != (uint8_t)(index + UINT32_C(1))) {
      return 3;
    }
  }
  if (malbolge_guest_heap_resize(&heap, resized, UINT32_C(65), &first) !=
          MALBOLGE_GUEST_RUNTIME_OUT_OF_MEMORY ||
      first != NULL) {
    return 4;
  }
  if (((uint8_t *)resized)[0] != UINT8_C(1)) {
    return 5;
  }
  if (malbolge_guest_heap_release(&heap, last) !=
      MALBOLGE_GUEST_RUNTIME_VALID) {
    return 6;
  }
  if (malbolge_guest_heap_resize(&heap, resized, UINT32_C(8), &first) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      first != resized) {
    return 7;
  }
  return 0;
}

static int test_resize_tail_extent(void) {
  alignas(16) uint8_t arena[64] = {0};
  MalbolgeGuestHeap heap = {0};
  void *pointer = NULL;
  void *resized = NULL;

  if (malbolge_guest_heap_init(&heap, arena, (uint32_t)sizeof(arena)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_heap_allocate(&heap, UINT32_C(8), &pointer) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      heap.used != UINT32_C(32)) {
    return 1;
  }
  if (malbolge_guest_heap_resize(&heap, pointer, UINT32_C(40), &resized) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      resized != pointer || heap.used != UINT32_C(64)) {
    return 2;
  }
  if (malbolge_guest_heap_resize(&heap, resized, UINT32_C(8), &pointer) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      pointer != resized || heap.used != UINT32_C(32)) {
    return 3;
  }
  if (malbolge_guest_heap_release(&heap, pointer) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      heap.used != UINT32_C(0)) {
    return 4;
  }
  return 0;
}

static int test_resize_move(void) {
  alignas(16) uint8_t arena[192] = {0};
  MalbolgeGuestHeap heap = {0};
  void *first = NULL;
  void *blocker = NULL;
  void *moved = NULL;
  uint32_t index = 0U;

  if (malbolge_guest_heap_init(&heap, arena, (uint32_t)sizeof(arena)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_heap_allocate(&heap, UINT32_C(8), &first) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_heap_allocate(&heap, UINT32_C(65), &blocker) !=
          MALBOLGE_GUEST_RUNTIME_VALID) {
    return 1;
  }
  for (index = 0U; index < UINT32_C(8); ++index) {
    ((uint8_t *)first)[index] = (uint8_t)(UINT32_C(0xa0) + index);
  }
  if (malbolge_guest_heap_resize(&heap, first, UINT32_C(24), &moved) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      moved == NULL || moved == first) {
    return 2;
  }
  for (index = 0U; index < UINT32_C(8); ++index) {
    if (((uint8_t *)moved)[index] != (uint8_t)(UINT32_C(0xa0) + index)) {
      return 3;
    }
  }
  if (malbolge_guest_heap_release(&heap, first) !=
      MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT) {
    return 4;
  }
  if (malbolge_guest_heap_release(&heap, blocker) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_heap_release(&heap, moved) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      heap.used != UINT32_C(0)) {
    return 5;
  }
  return 0;
}

static int test_startup_binding(void) {
  alignas(16) uint8_t arena[96] = {0};
  void *pointer = (void *)(uintptr_t)1U;
  void *resized = NULL;

  if (malbolge_guest_runtime_allocate(UINT32_C(8), &pointer) !=
          MALBOLGE_GUEST_RUNTIME_NOT_INITIALIZED ||
      pointer != NULL ||
      malbolge_guest_runtime_release(NULL) !=
          MALBOLGE_GUEST_RUNTIME_NOT_INITIALIZED) {
    return 1;
  }
  if (malbolge_guest_runtime_bind_heap(arena + 1, UINT32_C(64)) !=
      MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT) {
    return 2;
  }
  if (malbolge_guest_runtime_bind_heap(arena, (uint32_t)sizeof(arena)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_runtime_bind_heap(arena, (uint32_t)sizeof(arena)) !=
          MALBOLGE_GUEST_RUNTIME_ALREADY_INITIALIZED) {
    return 3;
  }
  if (malbolge_guest_runtime_allocate_zeroed(
          UINT32_C(2), UINT32_C(8), &pointer) != MALBOLGE_GUEST_RUNTIME_VALID ||
      pointer == NULL || !all_zero((const uint8_t *)pointer, UINT32_C(16))) {
    return 4;
  }
  ((uint8_t *)pointer)[0] = UINT8_C(0x7b);
  if (malbolge_guest_runtime_resize(pointer, UINT32_C(24), &resized) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      resized != pointer || ((uint8_t *)resized)[0] != UINT8_C(0x7b)) {
    return 5;
  }
  if (malbolge_guest_runtime_release(resized) != MALBOLGE_GUEST_RUNTIME_VALID) {
    return 6;
  }
  return 0;
}

static uint32_t test_read_u32(const uint8_t *bytes) {
  return (uint32_t)bytes[0] | ((uint32_t)bytes[1] << 8U) |
         ((uint32_t)bytes[2] << 16U) | ((uint32_t)bytes[3] << 24U);
}

static int validate_heap_chain(const MalbolgeGuestHeap *heap) {
  uint32_t offset = 0U;
  uint32_t previous_free = UINT32_C(0);

  if (heap == NULL || heap->arena == NULL || heap->used > heap->capacity ||
      (heap->used & UINT32_C(15)) != UINT32_C(0)) {
    return 0;
  }
  while (offset < heap->used) {
    const uint8_t *header = heap->arena + offset;
    const uint32_t span = test_read_u32(header);
    const uint32_t requested = test_read_u32(header + UINT32_C(4));
    const uint32_t state = test_read_u32(header + UINT32_C(8));
    const uint32_t reserved = test_read_u32(header + UINT32_C(12));
    uint32_t end = 0U;

    if (span < UINT32_C(32) || (span & UINT32_C(15)) != UINT32_C(0) ||
        offset > UINT32_MAX - span) {
      return 0;
    }
    end = offset + span;
    if (end > heap->used || reserved != UINT32_C(0) ||
        (state != UINT32_C(0) && state != UINT32_C(1))) {
      return 0;
    }
    if (state == UINT32_C(0)) {
      if (requested != UINT32_C(0) || previous_free != UINT32_C(0) ||
          end == heap->used) {
        return 0;
      }
      previous_free = UINT32_C(1);
    } else {
      if (requested == UINT32_C(0) || requested > span - UINT32_C(16)) {
        return 0;
      }
      previous_free = UINT32_C(0);
    }
    offset = end;
  }
  return offset == heap->used;
}

typedef struct StressSlot {
  void *pointer;
  uint32_t size;
  uint8_t pattern;
} StressSlot;

static uint32_t stress_next(uint32_t *state) {
  *state = (*state * UINT32_C(1664525)) + UINT32_C(1013904223);
  return *state;
}

static int stress_verify_slot(const uint8_t *arena, uint32_t capacity,
                              const StressSlot *slot) {
  const uint8_t *bytes = (const uint8_t *)slot->pointer;
  uint32_t index = 0U;

  if (slot->pointer == NULL) {
    return slot->size == UINT32_C(0);
  }
  if ((((uintptr_t)slot->pointer) & (uintptr_t)15U) != (uintptr_t)0U ||
      bytes < arena || bytes >= arena + capacity ||
      slot->size > (uint32_t)(arena + capacity - bytes)) {
    return 0;
  }
  while (index < slot->size) {
    if (bytes[index] != slot->pattern) {
      return 0;
    }
    ++index;
  }
  return 1;
}

static void stress_fill_slot(StressSlot *slot) {
  uint8_t *bytes = (uint8_t *)slot->pointer;
  uint32_t index = 0U;

  while (index < slot->size) {
    bytes[index] = slot->pattern;
    ++index;
  }
}

static int test_allocator_stress(void) {
  alignas(16) uint8_t arena[1024] = {0};
  MalbolgeGuestHeap heap = {0};
  StressSlot slots[16] = {{0}};
  uint32_t random = UINT32_C(0x13579bdf);
  uint32_t step = 0U;
  uint32_t slot_index = 0U;

  if (malbolge_guest_heap_init(&heap, arena, (uint32_t)sizeof(arena)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      !validate_heap_chain(&heap)) {
    return 1;
  }
  while (step < UINT32_C(4000)) {
    StressSlot *slot = NULL;
    uint32_t choice = 0U;
    uint32_t size = 0U;
    void *result = NULL;
    MalbolgeGuestRuntimeStatus status = MALBOLGE_GUEST_RUNTIME_VALID;

    slot_index = stress_next(&random) & UINT32_C(15);
    slot = &slots[slot_index];
    if (!stress_verify_slot(arena, (uint32_t)sizeof(arena), slot)) {
      return 2;
    }
    choice = stress_next(&random) % UINT32_C(3);
    size = (stress_next(&random) % UINT32_C(97)) + UINT32_C(1);
    if (slot->pointer == NULL) {
      status = malbolge_guest_heap_allocate(&heap, size, &result);
      if (status == MALBOLGE_GUEST_RUNTIME_VALID) {
        if (result == NULL) {
          return 3;
        }
        slot->pointer = result;
        slot->size = size;
        slot->pattern = (uint8_t)(slot_index + UINT32_C(1));
        stress_fill_slot(slot);
      } else if (status != MALBOLGE_GUEST_RUNTIME_OUT_OF_MEMORY ||
                 result != NULL) {
        return 4;
      }
    } else if (choice == UINT32_C(0)) {
      if (malbolge_guest_heap_release(&heap, slot->pointer) !=
          MALBOLGE_GUEST_RUNTIME_VALID) {
        return 5;
      }
      slot->pointer = NULL;
      slot->size = UINT32_C(0);
      slot->pattern = UINT8_C(0);
    } else {
      const uint32_t old_size = slot->size;
      const uint8_t old_pattern = slot->pattern;

      status = malbolge_guest_heap_resize(&heap, slot->pointer, size, &result);
      if (status == MALBOLGE_GUEST_RUNTIME_VALID) {
        const uint32_t preserved = old_size < size ? old_size : size;
        uint32_t index = 0U;

        if (result == NULL) {
          return 6;
        }
        while (index < preserved) {
          if (((const uint8_t *)result)[index] != old_pattern) {
            return 7;
          }
          ++index;
        }
        slot->pointer = result;
        slot->size = size;
        stress_fill_slot(slot);
      } else if (status == MALBOLGE_GUEST_RUNTIME_OUT_OF_MEMORY) {
        if (result != NULL ||
            !stress_verify_slot(arena, (uint32_t)sizeof(arena), slot)) {
          return 8;
        }
      } else {
        return 9;
      }
    }
    if (!validate_heap_chain(&heap)) {
      return 12;
    }
    {
      uint32_t verify_index = 0U;
      while (verify_index < UINT32_C(16)) {
        if (!stress_verify_slot(arena, (uint32_t)sizeof(arena),
                                &slots[verify_index])) {
          return 11;
        }
        ++verify_index;
      }
    }
    ++step;
  }
  slot_index = UINT32_C(0);
  while (slot_index < UINT32_C(16)) {
    if (slots[slot_index].pointer != NULL &&
        malbolge_guest_heap_release(&heap, slots[slot_index].pointer) !=
            MALBOLGE_GUEST_RUNTIME_VALID) {
      return 10;
    }
    ++slot_index;
  }
  return heap.used == UINT32_C(0) && validate_heap_chain(&heap) ? 0 : 13;
}

static int test_late_corruption_preflight(void) {
  alignas(16) uint8_t arena[128] = {0};
  MalbolgeGuestHeap heap = {0};
  void *first = NULL;
  void *middle = NULL;
  void *last = NULL;
  void *result = (void *)(uintptr_t)1U;

  if (malbolge_guest_heap_init(&heap, arena, (uint32_t)sizeof(arena)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_heap_allocate(&heap, UINT32_C(8), &first) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_heap_allocate(&heap, UINT32_C(8), &middle) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_heap_allocate(&heap, UINT32_C(8), &last) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_heap_release(&heap, first) !=
          MALBOLGE_GUEST_RUNTIME_VALID) {
    return 1;
  }
  arena[UINT32_C(76)] = UINT8_C(1);
  if (malbolge_guest_heap_allocate(&heap, UINT32_C(8), &result) !=
          MALBOLGE_GUEST_RUNTIME_CORRUPT_STATE ||
      result != NULL || arena[UINT32_C(8)] != UINT8_C(0)) {
    return 2;
  }

  if (malbolge_guest_heap_init(&heap, arena, (uint32_t)sizeof(arena)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_heap_allocate(&heap, UINT32_C(8), &first) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_heap_allocate(&heap, UINT32_C(8), &middle) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_heap_allocate(&heap, UINT32_C(8), &last) !=
          MALBOLGE_GUEST_RUNTIME_VALID) {
    return 3;
  }
  arena[UINT32_C(76)] = UINT8_C(1);
  if (malbolge_guest_heap_release(&heap, first) !=
          MALBOLGE_GUEST_RUNTIME_CORRUPT_STATE ||
      arena[UINT32_C(8)] != UINT8_C(1)) {
    return 4;
  }

  if (malbolge_guest_heap_init(&heap, arena, (uint32_t)sizeof(arena)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_heap_allocate(&heap, UINT32_C(8), &first) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_heap_allocate(&heap, UINT32_C(8), &middle) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_heap_allocate(&heap, UINT32_C(8), &last) !=
          MALBOLGE_GUEST_RUNTIME_VALID) {
    return 5;
  }
  arena[UINT32_C(76)] = UINT8_C(1);
  result = (void *)(uintptr_t)1U;
  if (malbolge_guest_heap_resize(&heap, first, UINT32_C(1), &result) !=
          MALBOLGE_GUEST_RUNTIME_CORRUPT_STATE ||
      result != NULL || arena[UINT32_C(4)] != UINT8_C(8) ||
      arena[UINT32_C(8)] != UINT8_C(1)) {
    return 6;
  }
  return 0;
}

static int test_invalid_and_corrupt_state(void) {
  alignas(16) uint8_t arena[96] = {0};
  MalbolgeGuestHeap heap = {0};
  void *pointer = NULL;

  if (malbolge_guest_heap_init(&heap, arena + 1, UINT32_C(64)) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      malbolge_guest_heap_init(&heap, arena, UINT32_C(63)) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      malbolge_guest_heap_init(&heap, arena, (uint32_t)sizeof(arena)) !=
          MALBOLGE_GUEST_RUNTIME_VALID) {
    return 1;
  }
  if (malbolge_guest_heap_allocate(&heap, UINT32_C(8), &pointer) !=
      MALBOLGE_GUEST_RUNTIME_VALID) {
    return 2;
  }
  heap.arena = arena + 1;
  pointer = NULL;
  if (malbolge_guest_heap_allocate(&heap, UINT32_C(8), &pointer) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      pointer != NULL) {
    return 3;
  }
  heap.arena = arena;
  arena[12] = UINT8_C(1);
  if (malbolge_guest_heap_allocate(&heap, UINT32_C(8), &pointer) !=
          MALBOLGE_GUEST_RUNTIME_CORRUPT_STATE ||
      pointer != NULL) {
    return 4;
  }
  return 0;
}

int main(void) {
  const int frame = test_frame_codec();
  const int byte_stream = test_byte_stream();
  const int identity = test_allocation_identity();
  const int reuse = test_reuse_split_coalesce();
  const int calloc_result = test_calloc_and_failures();
  const int resize = test_resize();
  const int tail = test_resize_tail_extent();
  const int move = test_resize_move();
  const int startup = test_startup_binding();
  const int stress = test_allocator_stress();
  const int late_corrupt = test_late_corruption_preflight();
  const int corrupt = test_invalid_and_corrupt_state();

  if (frame != 0) {
    return 10 + frame;
  }
  if (byte_stream != 0) {
    return 20 + byte_stream;
  }
  if (identity != 0) {
    return 30 + identity;
  }
  if (reuse != 0) {
    return 40 + reuse;
  }
  if (calloc_result != 0) {
    return 50 + calloc_result;
  }
  if (resize != 0) {
    return 60 + resize;
  }
  if (tail != 0) {
    return 70 + tail;
  }
  if (move != 0) {
    return 80 + move;
  }
  if (startup != 0) {
    return 90 + startup;
  }
  if (stress != 0) {
    return 100 + stress;
  }
  if (late_corrupt != 0) {
    return 120 + late_corrupt;
  }
  return corrupt == 0 ? 0 : 140 + corrupt;
}
