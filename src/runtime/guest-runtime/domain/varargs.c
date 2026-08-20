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
//   - Fail-closed decoding of canonical promoted guest variadic objects.
// - Must-Not:
//   - Inspect host va_list, host stack/register state, or native object layout.
// - Allows:
//   - Inputs: tracked guest bytes, zero-based linear address, and value kind.
//   - Outputs: raw little-endian value bits and advanced canonical cursor.
//   - Side effects: cursor/result mutation only after complete bounds
//     admission.
// - Split-When:
//   - Aggregate variadic values become an independently supported ABI family.
// - Merge-When:
//   - One formatter cursor directly owns this exact promoted-object decoding.
// - Summary:
//   - Applies guest natural alignment and decodes scalar variadic
//     representations.
// - Description:
//   - Covers i32/u32/i64/u64/f64/f128/object-pointer promoted storage shapes.
// - Usage:
//   - Future printf execution maps admitted directives to these promoted kinds.
// - Defaults:
//   - Address arithmetic and block extents are checked in the uint32 domain.
//

//! Guest variadic-block cursor with no native va_list representation
//! dependency.

#include "guest_varargs.h"

#include <stddef.h>
#include <stdint.h>

typedef struct VarargShape {
  uint32_t alignment;
  uint32_t size;
} VarargShape;

static int add_u32(uint32_t left, uint32_t right, uint32_t *result) {
  if (result == NULL || left > UINT32_MAX - right) {
    return 0;
  }
  *result = left + right;
  return 1;
}

static int kind_shape(uint32_t kind, VarargShape *shape) {
  if (shape == NULL) {
    return 0;
  }
  if (kind == MALBOLGE_GUEST_VARARG_I32 || kind == MALBOLGE_GUEST_VARARG_U32 ||
      kind == MALBOLGE_GUEST_VARARG_POINTER32) {
    shape->alignment = UINT32_C(4);
    shape->size = UINT32_C(4);
    return 1;
  }
  if (kind == MALBOLGE_GUEST_VARARG_I64 || kind == MALBOLGE_GUEST_VARARG_U64 ||
      kind == MALBOLGE_GUEST_VARARG_F64) {
    shape->alignment = UINT32_C(8);
    shape->size = UINT32_C(8);
    return 1;
  }
  if (kind == MALBOLGE_GUEST_VARARG_F128) {
    shape->alignment = UINT32_C(16);
    shape->size = UINT32_C(16);
    return 1;
  }
  return 0;
}

static int align_cursor(const MalbolgeGuestVarargCursor *cursor,
                        VarargShape shape, uint32_t *aligned_offset,
                        uint32_t *end_offset) {
  uint32_t absolute = UINT32_C(0);
  uint32_t biased = UINT32_C(0);
  uint32_t aligned_absolute = UINT32_C(0);
  uint32_t padding = UINT32_C(0);
  uint32_t end = UINT32_C(0);
  uint32_t logical_end = UINT32_C(0);

  if (!add_u32(cursor->linear_address, cursor->offset, &absolute) ||
      !add_u32(absolute, shape.alignment - UINT32_C(1), &biased)) {
    return 0;
  }
  aligned_absolute = biased & ~(shape.alignment - UINT32_C(1));
  padding = aligned_absolute - absolute;
  if (!add_u32(cursor->offset, padding, aligned_offset) ||
      !add_u32(*aligned_offset, shape.size, &end) || end > cursor->block_size ||
      !add_u32(cursor->linear_address, end, &logical_end)) {
    return 0;
  }
  *end_offset = end;
  return 1;
}

static uint64_t read_little_endian(const uint8_t *bytes, uint32_t size) {
  uint64_t value = UINT64_C(0);
  uint32_t index = UINT32_C(0);

  while (index < size) {
    value |= (uint64_t)bytes[index] << (index * UINT32_C(8));
    ++index;
  }
  return value;
}

MalbolgeGuestRuntimeStatus
malbolge_guest_varargs_validate(const MalbolgeGuestVarargCursor *cursor) {
  const uint32_t maximum_offset = UINT32_MAX - UINT32_C(1);

  if (cursor == NULL || cursor->offset > cursor->block_size ||
      (cursor->block == NULL && cursor->block_size != UINT32_C(0)) ||
      cursor->linear_address > maximum_offset ||
      (cursor->block_size != UINT32_C(0) &&
       cursor->block_size - UINT32_C(1) >
           maximum_offset - cursor->linear_address)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  return MALBOLGE_GUEST_RUNTIME_VALID;
}

MalbolgeGuestRuntimeStatus
malbolge_guest_varargs_init(MalbolgeGuestVarargCursor *cursor,
                            const uint8_t *block, uint32_t block_size,
                            uint32_t linear_address) {
  MalbolgeGuestVarargCursor staged;

  if (cursor == NULL) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  staged.block = block;
  staged.block_size = block_size;
  staged.linear_address = linear_address;
  staged.offset = UINT32_C(0);
  if (malbolge_guest_varargs_validate(&staged) !=
      MALBOLGE_GUEST_RUNTIME_VALID) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  cursor->block = staged.block;
  cursor->block_size = staged.block_size;
  cursor->linear_address = staged.linear_address;
  cursor->offset = staged.offset;
  return MALBOLGE_GUEST_RUNTIME_VALID;
}

MalbolgeGuestRuntimeStatus
malbolge_guest_varargs_read(MalbolgeGuestVarargCursor *cursor, uint32_t kind,
                            MalbolgeGuestVarargValue *result) {
  VarargShape shape;
  MalbolgeGuestVarargValue decoded;
  uint32_t aligned = UINT32_C(0);
  uint32_t end = UINT32_C(0);

  if (result == NULL ||
      malbolge_guest_varargs_validate(cursor) != MALBOLGE_GUEST_RUNTIME_VALID ||
      cursor->block == NULL || !kind_shape(kind, &shape) ||
      !align_cursor(cursor, shape, &aligned, &end)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  decoded.low = UINT64_C(0);
  decoded.high = UINT64_C(0);
  decoded.low =
      read_little_endian(cursor->block + aligned,
                         shape.size > UINT32_C(8) ? UINT32_C(8) : shape.size);
  if (shape.size == UINT32_C(16)) {
    decoded.high =
        read_little_endian(cursor->block + aligned + UINT32_C(8), UINT32_C(8));
  }
  result->low = decoded.low;
  result->high = decoded.high;
  cursor->offset = end;
  return MALBOLGE_GUEST_RUNTIME_VALID;
}
