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
//   - Independent vectors for canonical guest variadic-block cursor semantics.
// - Must-Not:
//   - Use host va_list, native stack inspection, or host object representation.
// - Allows:
//   - Inputs: explicit little-endian promoted argument bytes and guest
//   addresses.
//   - Outputs: zero only when alignment, decoding, and failure atomicity match.
//   - Side effects: test-local blocks, cursors, and decoded-value structures
//   only.
// - Split-When:
//   - Public va_list bridging gains independent compiler integration evidence.
// - Merge-When:
//   - Runtime conformance owns equivalent canonical variadic-block vectors.
// - Summary:
//   - Locks promoted scalar decoding with guest natural alignment and bounds.
// - Description:
//   - Exercises 32/64/128-bit values, pointers, padding, overflow, and
//   failures.
// - Usage:
//   - Built and executed by tests/test_guest_runtime_c.py.
// - Defaults:
//   - Failed reads leave both cursor offset and result bits unchanged.
//

//! Independent guest variadic-cursor regression vectors.

#include "guest_varargs.h"

#include <stddef.h>
#include <stdint.h>

static void write_u64(uint8_t *bytes, uint64_t value, uint32_t size) {
  uint32_t index = UINT32_C(0);
  while (index < size) {
    bytes[index] = (uint8_t)(value >> (index * UINT32_C(8)));
    ++index;
  }
}

static int read_matches(MalbolgeGuestVarargCursor *cursor, uint32_t kind,
                        uint64_t low, uint64_t high, uint32_t expected_offset) {
  MalbolgeGuestVarargValue value = {UINT64_C(0), UINT64_C(0)};
  return malbolge_guest_varargs_read(cursor, kind, &value) ==
             MALBOLGE_GUEST_RUNTIME_VALID &&
         value.low == low && value.high == high &&
         cursor->offset == expected_offset;
}

static int test_promoted_sequence(void) {
  uint8_t block[48] = {0};
  MalbolgeGuestVarargCursor cursor;

  write_u64(block, UINT32_C(0xfffffff9), UINT32_C(4));
  write_u64(block + UINT32_C(8), UINT64_C(0x400921fb54442d18), UINT32_C(8));
  write_u64(block + UINT32_C(16), UINT32_C(0x10203040), UINT32_C(4));
  write_u64(block + UINT32_C(32), UINT64_C(0x0123456789abcdef), UINT32_C(8));
  write_u64(block + UINT32_C(40), UINT64_C(0xfedcba9876543210), UINT32_C(8));

  if (malbolge_guest_varargs_init(&cursor, block, (uint32_t)sizeof(block),
                                  UINT32_C(0x100)) !=
      MALBOLGE_GUEST_RUNTIME_VALID) {
    return 1;
  }
  if (!read_matches(&cursor, MALBOLGE_GUEST_VARARG_I32, UINT64_C(0xfffffff9),
                    UINT64_C(0), UINT32_C(4))) {
    return 2;
  }
  if (!read_matches(&cursor, MALBOLGE_GUEST_VARARG_F64,
                    UINT64_C(0x400921fb54442d18), UINT64_C(0), UINT32_C(16))) {
    return 3;
  }
  if (!read_matches(&cursor, MALBOLGE_GUEST_VARARG_POINTER32,
                    UINT64_C(0x10203040), UINT64_C(0), UINT32_C(20))) {
    return 4;
  }
  if (!read_matches(&cursor, MALBOLGE_GUEST_VARARG_F128,
                    UINT64_C(0x0123456789abcdef), UINT64_C(0xfedcba9876543210),
                    UINT32_C(48))) {
    return 5;
  }
  return 0;
}

static int test_absolute_alignment(void) {
  uint8_t block[8] = {0};
  MalbolgeGuestVarargCursor cursor;

  write_u64(block + UINT32_C(2), UINT32_C(0xa1b2c3d4), UINT32_C(4));
  if (malbolge_guest_varargs_init(&cursor, block, (uint32_t)sizeof(block),
                                  UINT32_C(0x102)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      !read_matches(&cursor, MALBOLGE_GUEST_VARARG_U32, UINT64_C(0xa1b2c3d4),
                    UINT64_C(0), UINT32_C(6))) {
    return 1;
  }
  return 0;
}

static int test_other_supported_kinds(void) {
  uint8_t block[16] = {0};
  static const uint32_t kinds[] = {
      MALBOLGE_GUEST_VARARG_U32,
      MALBOLGE_GUEST_VARARG_I64,
      MALBOLGE_GUEST_VARARG_U64,
  };
  uint32_t index = UINT32_C(0);

  while (index < (uint32_t)(sizeof(kinds) / sizeof(kinds[0]))) {
    MalbolgeGuestVarargCursor cursor;
    MalbolgeGuestVarargValue value;
    if (malbolge_guest_varargs_init(&cursor, block, (uint32_t)sizeof(block),
                                    UINT32_C(0x200)) !=
            MALBOLGE_GUEST_RUNTIME_VALID ||
        malbolge_guest_varargs_read(&cursor, kinds[index], &value) !=
            MALBOLGE_GUEST_RUNTIME_VALID) {
      return (int)(index + UINT32_C(1));
    }
    ++index;
  }
  return 0;
}

static int test_failure_atomicity(void) {
  uint8_t block[4] = {1, 2, 3, 4};
  MalbolgeGuestVarargCursor cursor;
  MalbolgeGuestVarargValue value = {UINT64_C(0x1111222233334444),
                                    UINT64_C(0x5555666677778888)};

  if (malbolge_guest_varargs_init(&cursor, block, (uint32_t)sizeof(block),
                                  UINT32_C(0x300)) !=
      MALBOLGE_GUEST_RUNTIME_VALID) {
    return 1;
  }
  if (malbolge_guest_varargs_read(&cursor, MALBOLGE_GUEST_VARARG_U64, &value) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      cursor.offset != UINT32_C(0) ||
      value.low != UINT64_C(0x1111222233334444) ||
      value.high != UINT64_C(0x5555666677778888)) {
    return 2;
  }
  if (malbolge_guest_varargs_read(&cursor, UINT32_C(99), &value) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      cursor.offset != UINT32_C(0)) {
    return 3;
  }
  if (malbolge_guest_varargs_read(NULL, MALBOLGE_GUEST_VARARG_I32, &value) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      malbolge_guest_varargs_read(&cursor, MALBOLGE_GUEST_VARARG_I32, NULL) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT) {
    return 4;
  }
  cursor.block = NULL;
  cursor.block_size = UINT32_C(4);
  cursor.offset = UINT32_C(0);
  if (malbolge_guest_varargs_validate(&cursor) !=
      MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT) {
    return 5;
  }
  cursor.block = block;
  cursor.offset = UINT32_C(5);
  if (malbolge_guest_varargs_validate(&cursor) !=
      MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT) {
    return 6;
  }
  cursor.offset = UINT32_C(4);
  if (malbolge_guest_varargs_validate(&cursor) !=
      MALBOLGE_GUEST_RUNTIME_VALID) {
    return 7;
  }
  return 0;
}

static int test_init_and_address_overflow(void) {
  uint8_t block[4] = {0};
  MalbolgeGuestVarargCursor cursor = {block, UINT32_C(4), UINT32_C(8),
                                      UINT32_C(3)};
  MalbolgeGuestVarargValue value = {UINT64_C(7), UINT64_C(9)};

  if (malbolge_guest_varargs_init(NULL, block, UINT32_C(4), UINT32_C(0)) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      malbolge_guest_varargs_init(&cursor, NULL, UINT32_C(4), UINT32_C(0)) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      cursor.offset != UINT32_C(3)) {
    return 1;
  }
  if (malbolge_guest_varargs_init(&cursor, NULL, UINT32_C(0), UINT32_C(0)) !=
      MALBOLGE_GUEST_RUNTIME_VALID) {
    return 2;
  }
  if (malbolge_guest_varargs_read(&cursor, MALBOLGE_GUEST_VARARG_I32, &value) !=
      MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT) {
    return 3;
  }
  cursor.block = NULL;
  cursor.block_size = UINT32_C(0);
  cursor.linear_address = UINT32_C(9);
  cursor.offset = UINT32_C(3);
  if (malbolge_guest_varargs_init(&cursor, block, UINT32_C(4),
                                  UINT32_C(0xfffffffc)) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      cursor.block != NULL || cursor.block_size != UINT32_C(0) ||
      cursor.linear_address != UINT32_C(9) || cursor.offset != UINT32_C(3) ||
      value.low != UINT64_C(7) || value.high != UINT64_C(9)) {
    return 4;
  }
  if (malbolge_guest_varargs_init(&cursor, block, UINT32_C(1),
                                  UINT32_C(0xfffffffe)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_varargs_validate(&cursor) !=
          MALBOLGE_GUEST_RUNTIME_VALID) {
    return 5;
  }
  if (malbolge_guest_varargs_init(&cursor, NULL, UINT32_C(0), UINT32_MAX) !=
      MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT) {
    return 6;
  }
  return 0;
}

int main(void) {
  const int sequence = test_promoted_sequence();
  const int alignment = test_absolute_alignment();
  const int kinds = test_other_supported_kinds();
  const int failures = test_failure_atomicity();
  const int overflow = test_init_and_address_overflow();

  if (sequence != 0) {
    return 10 + sequence;
  }
  if (alignment != 0) {
    return 20 + alignment;
  }
  if (kinds != 0) {
    return 30 + kinds;
  }
  if (failures != 0) {
    return 40 + failures;
  }
  return overflow == 0 ? 0 : 50 + overflow;
}
