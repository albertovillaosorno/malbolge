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
//   - Deterministic first-fit guest heap metadata and allocation semantics.
// - Must-Not:
//   - Call host allocation, serialize native pointers, or use ambient storage.
// - Allows:
//   - Inputs: one aligned caller-owned guest byte arena and 32-bit extents.
//   - Outputs: aligned arena pointers plus stable runtime status values.
//   - Side effects: metadata and allocated bytes inside the bound arena only.
// - Split-When:
//   - Another allocator policy requires independently versioned semantics.
// - Merge-When:
//   - Guest startup owns this exact arena allocator lifecycle.
// - Summary:
//   - Guest-owned first-fit allocator with split, coalesce, calloc, and resize.
// - Description:
//   - Stores canonical little-endian 16-byte headers in guest memory.
// - Usage:
//   - Bound once by guest startup and consumed by libc allocation wrappers.
// - Defaults:
//   - Allocation alignment is 16 bytes and zero-size allocation returns null.
//

//! Deterministic guest arena allocator with no host allocation dependency.

#include "guest_runtime.h"

#include <stddef.h>
#include <stdint.h>

#define BLOCK_FREE UINT32_C(0)
#define BLOCK_ALLOCATED UINT32_C(1)
#define MIN_BLOCK_SPAN UINT32_C(32)
#define OFFSET_REQUESTED UINT32_C(4)
#define OFFSET_RESERVED UINT32_C(12)
#define OFFSET_SPAN UINT32_C(0)
#define OFFSET_STATE UINT32_C(8)

typedef struct BlockInfo {
  uint32_t offset;
  uint32_t requested;
  uint32_t span;
  uint32_t state;
} BlockInfo;

static uint32_t read_u32(const uint8_t *bytes) {
  return (uint32_t)bytes[0] | ((uint32_t)bytes[1] << 8U) |
         ((uint32_t)bytes[2] << 16U) | ((uint32_t)bytes[3] << 24U);
}

static void write_u32(uint8_t *bytes, uint32_t value) {
  bytes[0] = (uint8_t)(value & UINT32_C(255));
  bytes[1] = (uint8_t)((value >> 8U) & UINT32_C(255));
  bytes[2] = (uint8_t)((value >> 16U) & UINT32_C(255));
  bytes[3] = (uint8_t)((value >> 24U) & UINT32_C(255));
}

static int add_u32(uint32_t left, uint32_t right, uint32_t *result) {
  if (result == NULL || left > UINT32_MAX - right) {
    return 0;
  }
  *result = left + right;
  return 1;
}

static int aligned_extent(uint32_t size, uint32_t *aligned) {
  uint32_t biased = 0U;

  if (aligned == NULL ||
      !add_u32(size, MALBOLGE_GUEST_HEAP_ALIGNMENT - UINT32_C(1), &biased)) {
    return 0;
  }
  *aligned = biased & ~(MALBOLGE_GUEST_HEAP_ALIGNMENT - UINT32_C(1));
  return 1;
}

static int heap_shape_valid(const MalbolgeGuestHeap *heap) {
  if (heap == NULL || heap->arena == NULL || heap->capacity < MIN_BLOCK_SPAN ||
      heap->used > heap->capacity) {
    return 0;
  }
  return (((uintptr_t)heap->arena) & ((uintptr_t)MALBOLGE_GUEST_HEAP_ALIGNMENT -
                                      (uintptr_t)1U)) == (uintptr_t)0U &&
         (heap->capacity & (MALBOLGE_GUEST_HEAP_ALIGNMENT - UINT32_C(1))) ==
             UINT32_C(0) &&
         (heap->used & (MALBOLGE_GUEST_HEAP_ALIGNMENT - UINT32_C(1))) ==
             UINT32_C(0);
}

static void write_block(uint8_t *header, uint32_t span, uint32_t requested,
                        uint32_t state) {
  write_u32(header + OFFSET_SPAN, span);
  write_u32(header + OFFSET_REQUESTED, requested);
  write_u32(header + OFFSET_STATE, state);
  write_u32(header + OFFSET_RESERVED, UINT32_C(0));
}

static int read_block(const MalbolgeGuestHeap *heap, uint32_t offset,
                      BlockInfo *block) {
  uint32_t end = 0U;
  uint32_t payload = 0U;
  const uint8_t *header = NULL;

  if (block == NULL || !heap_shape_valid(heap) || offset > heap->used ||
      heap->used - offset < MALBOLGE_GUEST_HEAP_HEADER_SIZE) {
    return 0;
  }
  header = heap->arena + offset;
  block->offset = offset;
  block->span = read_u32(header + OFFSET_SPAN);
  block->requested = read_u32(header + OFFSET_REQUESTED);
  block->state = read_u32(header + OFFSET_STATE);
  if (read_u32(header + OFFSET_RESERVED) != UINT32_C(0) ||
      block->span < MIN_BLOCK_SPAN ||
      (block->span & (MALBOLGE_GUEST_HEAP_ALIGNMENT - UINT32_C(1))) !=
          UINT32_C(0) ||
      !add_u32(offset, block->span, &end) || end > heap->used ||
      (block->state != BLOCK_FREE && block->state != BLOCK_ALLOCATED)) {
    return 0;
  }
  payload = block->span - MALBOLGE_GUEST_HEAP_HEADER_SIZE;
  if ((block->state == BLOCK_FREE && block->requested != UINT32_C(0)) ||
      (block->state == BLOCK_ALLOCATED &&
       (block->requested == UINT32_C(0) || block->requested > payload))) {
    return 0;
  }
  return 1;
}

static int heap_chain_valid(const MalbolgeGuestHeap *heap) {
  uint32_t offset = 0U;
  uint32_t previous_free = UINT32_C(0);
  BlockInfo block;

  if (!heap_shape_valid(heap)) {
    return 0;
  }
  while (offset < heap->used) {
    uint32_t end = 0U;

    if (!read_block(heap, offset, &block) ||
        !add_u32(offset, block.span, &end)) {
      return 0;
    }
    if (block.state == BLOCK_FREE) {
      if (previous_free != UINT32_C(0) || end == heap->used) {
        return 0;
      }
      previous_free = UINT32_C(1);
    } else {
      previous_free = UINT32_C(0);
    }
    offset = end;
  }
  return offset == heap->used;
}

static MalbolgeGuestRuntimeStatus required_span(uint32_t size, uint32_t *span) {
  uint32_t aligned = 0U;

  if (span == NULL || size == UINT32_C(0)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  if (!aligned_extent(size, &aligned) ||
      !add_u32(MALBOLGE_GUEST_HEAP_HEADER_SIZE, aligned, span)) {
    return MALBOLGE_GUEST_RUNTIME_OUT_OF_MEMORY;
  }
  return MALBOLGE_GUEST_RUNTIME_VALID;
}

static MalbolgeGuestRuntimeStatus
find_allocated_block(const MalbolgeGuestHeap *heap, const void *pointer,
                     BlockInfo *found) {
  uint32_t offset = 0U;
  BlockInfo block;

  if (!heap_shape_valid(heap) || pointer == NULL || found == NULL) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  while (offset < heap->used) {
    if (!read_block(heap, offset, &block)) {
      return MALBOLGE_GUEST_RUNTIME_CORRUPT_STATE;
    }
    if (heap->arena + offset + MALBOLGE_GUEST_HEAP_HEADER_SIZE == pointer) {
      if (block.state != BLOCK_ALLOCATED) {
        return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
      }
      *found = block;
      return MALBOLGE_GUEST_RUNTIME_VALID;
    }
    offset += block.span;
  }
  return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
}

static void split_or_claim(MalbolgeGuestHeap *heap, BlockInfo block,
                           uint32_t required, uint32_t requested) {
  const uint32_t remainder = block.span - required;

  if (remainder >= MIN_BLOCK_SPAN) {
    write_block(heap->arena + block.offset, required, requested,
                BLOCK_ALLOCATED);
    write_block(heap->arena + block.offset + required, remainder, UINT32_C(0),
                BLOCK_FREE);
    return;
  }
  write_block(heap->arena + block.offset, block.span, requested,
              BLOCK_ALLOCATED);
}

static MalbolgeGuestRuntimeStatus
coalesce_free_blocks(MalbolgeGuestHeap *heap) {
  uint32_t offset = 0U;
  BlockInfo current;
  BlockInfo next;

  while (offset < heap->used) {
    uint32_t next_offset = 0U;
    uint32_t merged = 0U;

    if (!read_block(heap, offset, &current)) {
      return MALBOLGE_GUEST_RUNTIME_CORRUPT_STATE;
    }
    if (!add_u32(offset, current.span, &next_offset)) {
      return MALBOLGE_GUEST_RUNTIME_CORRUPT_STATE;
    }
    if (current.state == BLOCK_FREE && next_offset < heap->used) {
      if (!read_block(heap, next_offset, &next)) {
        return MALBOLGE_GUEST_RUNTIME_CORRUPT_STATE;
      }
      if (next.state == BLOCK_FREE) {
        if (!add_u32(current.span, next.span, &merged)) {
          return MALBOLGE_GUEST_RUNTIME_CORRUPT_STATE;
        }
        write_block(heap->arena + offset, merged, UINT32_C(0), BLOCK_FREE);
        continue;
      }
    }
    offset = next_offset;
  }
  return MALBOLGE_GUEST_RUNTIME_VALID;
}

MalbolgeGuestRuntimeStatus malbolge_guest_heap_init(MalbolgeGuestHeap *heap,
                                                    void *arena,
                                                    uint32_t capacity) {
  uint32_t index = 0U;

  if (heap == NULL || arena == NULL || capacity < MIN_BLOCK_SPAN ||
      (capacity & (MALBOLGE_GUEST_HEAP_ALIGNMENT - UINT32_C(1))) !=
          UINT32_C(0) ||
      (((uintptr_t)arena) & ((uintptr_t)MALBOLGE_GUEST_HEAP_ALIGNMENT -
                             (uintptr_t)1U)) != (uintptr_t)0U) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  heap->arena = (uint8_t *)arena;
  heap->capacity = capacity;
  heap->used = UINT32_C(0);
  while (index < capacity) {
    heap->arena[index] = UINT8_C(0);
    ++index;
  }
  return MALBOLGE_GUEST_RUNTIME_VALID;
}

MalbolgeGuestRuntimeStatus malbolge_guest_heap_allocate(MalbolgeGuestHeap *heap,
                                                        uint32_t size,
                                                        void **result) {
  uint32_t offset = 0U;
  uint32_t required = 0U;
  uint32_t new_used = 0U;
  BlockInfo block;
  MalbolgeGuestRuntimeStatus status = MALBOLGE_GUEST_RUNTIME_VALID;

  if (result == NULL || !heap_shape_valid(heap)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  *result = NULL;
  if (!heap_chain_valid(heap)) {
    return MALBOLGE_GUEST_RUNTIME_CORRUPT_STATE;
  }
  if (size == UINT32_C(0)) {
    return MALBOLGE_GUEST_RUNTIME_VALID;
  }
  status = required_span(size, &required);
  if (status != MALBOLGE_GUEST_RUNTIME_VALID) {
    return status;
  }
  while (offset < heap->used) {
    if (!read_block(heap, offset, &block)) {
      return MALBOLGE_GUEST_RUNTIME_CORRUPT_STATE;
    }
    if (block.state == BLOCK_FREE && block.span >= required) {
      split_or_claim(heap, block, required, size);
      *result = heap->arena + offset + MALBOLGE_GUEST_HEAP_HEADER_SIZE;
      return MALBOLGE_GUEST_RUNTIME_VALID;
    }
    offset += block.span;
  }
  if (!add_u32(heap->used, required, &new_used) || new_used > heap->capacity) {
    return MALBOLGE_GUEST_RUNTIME_OUT_OF_MEMORY;
  }
  write_block(heap->arena + heap->used, required, size, BLOCK_ALLOCATED);
  *result = heap->arena + heap->used + MALBOLGE_GUEST_HEAP_HEADER_SIZE;
  heap->used = new_used;
  return MALBOLGE_GUEST_RUNTIME_VALID;
}

MalbolgeGuestRuntimeStatus
malbolge_guest_heap_allocate_zeroed(MalbolgeGuestHeap *heap, uint32_t count,
                                    uint32_t size, void **result) {
  uint32_t total = 0U;
  uint32_t index = 0U;
  uint8_t *bytes = NULL;
  MalbolgeGuestRuntimeStatus status = MALBOLGE_GUEST_RUNTIME_VALID;

  if (result == NULL) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  *result = NULL;
  if (count == UINT32_C(0) || size == UINT32_C(0)) {
    return malbolge_guest_heap_allocate(heap, UINT32_C(0), result);
  }
  if (count > UINT32_MAX / size) {
    return MALBOLGE_GUEST_RUNTIME_OUT_OF_MEMORY;
  }
  total = count * size;
  status = malbolge_guest_heap_allocate(heap, total, result);
  if (status != MALBOLGE_GUEST_RUNTIME_VALID || *result == NULL) {
    return status;
  }
  bytes = (uint8_t *)*result;
  while (index < total) {
    bytes[index] = UINT8_C(0);
    ++index;
  }
  return MALBOLGE_GUEST_RUNTIME_VALID;
}

static MalbolgeGuestRuntimeStatus trim_free_tail(MalbolgeGuestHeap *heap) {
  uint32_t offset = 0U;
  BlockInfo block;

  while (offset < heap->used) {
    uint32_t next = 0U;

    if (!read_block(heap, offset, &block)) {
      return MALBOLGE_GUEST_RUNTIME_CORRUPT_STATE;
    }
    if (!add_u32(offset, block.span, &next)) {
      return MALBOLGE_GUEST_RUNTIME_CORRUPT_STATE;
    }
    if (next == heap->used && block.state == BLOCK_FREE) {
      heap->used = offset;
      return MALBOLGE_GUEST_RUNTIME_VALID;
    }
    offset = next;
  }
  return MALBOLGE_GUEST_RUNTIME_VALID;
}

MalbolgeGuestRuntimeStatus malbolge_guest_heap_release(MalbolgeGuestHeap *heap,
                                                       void *pointer) {
  BlockInfo block;
  MalbolgeGuestRuntimeStatus status = MALBOLGE_GUEST_RUNTIME_VALID;

  if (!heap_shape_valid(heap)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  if (!heap_chain_valid(heap)) {
    return MALBOLGE_GUEST_RUNTIME_CORRUPT_STATE;
  }
  if (pointer == NULL) {
    return MALBOLGE_GUEST_RUNTIME_VALID;
  }
  status = find_allocated_block(heap, pointer, &block);
  if (status != MALBOLGE_GUEST_RUNTIME_VALID) {
    return status;
  }
  write_block(heap->arena + block.offset, block.span, UINT32_C(0), BLOCK_FREE);
  status = coalesce_free_blocks(heap);
  if (status != MALBOLGE_GUEST_RUNTIME_VALID) {
    return status;
  }
  return trim_free_tail(heap);
}

static MalbolgeGuestRuntimeStatus
resize_in_place(MalbolgeGuestHeap *heap, BlockInfo block, uint32_t size,
                uint32_t required, void **result) {
  uint32_t next_offset = 0U;
  uint32_t combined = 0U;
  BlockInfo next;

  if (required <= block.span) {
    MalbolgeGuestRuntimeStatus status = MALBOLGE_GUEST_RUNTIME_VALID;

    split_or_claim(heap, block, required, size);
    *result = heap->arena + block.offset + MALBOLGE_GUEST_HEAP_HEADER_SIZE;
    status = coalesce_free_blocks(heap);
    if (status != MALBOLGE_GUEST_RUNTIME_VALID) {
      return status;
    }
    return trim_free_tail(heap);
  }
  if (!add_u32(block.offset, block.span, &next_offset)) {
    return MALBOLGE_GUEST_RUNTIME_CORRUPT_STATE;
  }
  if (next_offset == heap->used) {
    uint32_t new_used = 0U;

    if (!add_u32(block.offset, required, &new_used) ||
        new_used > heap->capacity) {
      return MALBOLGE_GUEST_RUNTIME_OUT_OF_MEMORY;
    }
    write_block(heap->arena + block.offset, required, size, BLOCK_ALLOCATED);
    heap->used = new_used;
    *result = heap->arena + block.offset + MALBOLGE_GUEST_HEAP_HEADER_SIZE;
    return MALBOLGE_GUEST_RUNTIME_VALID;
  }
  if (next_offset > heap->used) {
    return MALBOLGE_GUEST_RUNTIME_CORRUPT_STATE;
  }
  if (!read_block(heap, next_offset, &next)) {
    return MALBOLGE_GUEST_RUNTIME_CORRUPT_STATE;
  }
  if (next.state != BLOCK_FREE || !add_u32(block.span, next.span, &combined) ||
      combined < required) {
    return MALBOLGE_GUEST_RUNTIME_OUT_OF_MEMORY;
  }
  block.span = combined;
  split_or_claim(heap, block, required, size);
  *result = heap->arena + block.offset + MALBOLGE_GUEST_HEAP_HEADER_SIZE;
  {
    MalbolgeGuestRuntimeStatus status = coalesce_free_blocks(heap);
    if (status != MALBOLGE_GUEST_RUNTIME_VALID) {
      return status;
    }
  }
  return trim_free_tail(heap);
}

static void copy_bytes(uint8_t *destination, const uint8_t *source,
                       uint32_t count) {
  uint32_t index = 0U;

  while (index < count) {
    destination[index] = source[index];
    ++index;
  }
}

MalbolgeGuestRuntimeStatus malbolge_guest_heap_resize(MalbolgeGuestHeap *heap,
                                                      void *pointer,
                                                      uint32_t size,
                                                      void **result) {
  uint32_t required = 0U;
  uint32_t copy_count = 0U;
  void *replacement = NULL;
  BlockInfo block;
  MalbolgeGuestRuntimeStatus status = MALBOLGE_GUEST_RUNTIME_VALID;

  if (result == NULL || !heap_shape_valid(heap)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  *result = NULL;
  if (!heap_chain_valid(heap)) {
    return MALBOLGE_GUEST_RUNTIME_CORRUPT_STATE;
  }
  if (pointer == NULL) {
    return malbolge_guest_heap_allocate(heap, size, result);
  }
  if (size == UINT32_C(0)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  status = find_allocated_block(heap, pointer, &block);
  if (status != MALBOLGE_GUEST_RUNTIME_VALID) {
    return status;
  }
  status = required_span(size, &required);
  if (status != MALBOLGE_GUEST_RUNTIME_VALID) {
    return status;
  }
  status = resize_in_place(heap, block, size, required, result);
  if (status == MALBOLGE_GUEST_RUNTIME_VALID) {
    return status;
  }
  if (status != MALBOLGE_GUEST_RUNTIME_OUT_OF_MEMORY) {
    return status;
  }
  status = malbolge_guest_heap_allocate(heap, size, &replacement);
  if (status != MALBOLGE_GUEST_RUNTIME_VALID) {
    return status;
  }
  if (replacement == NULL) {
    return MALBOLGE_GUEST_RUNTIME_OUT_OF_MEMORY;
  }
  copy_count = block.requested < size ? block.requested : size;
  copy_bytes((uint8_t *)replacement, (const uint8_t *)pointer, copy_count);
  status = malbolge_guest_heap_release(heap, pointer);
  if (status != MALBOLGE_GUEST_RUNTIME_VALID) {
    return status;
  }
  *result = replacement;
  return MALBOLGE_GUEST_RUNTIME_VALID;
}
