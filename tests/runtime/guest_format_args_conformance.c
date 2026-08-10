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
//   - Independent vectors for atomic guest format-argument resolution.
// - Must-Not:
//   - Use host va_list, host printf, or dereference guest pointer arguments.
// - Allows:
//   - Inputs: parsed directives and explicit promoted guest argument bytes.
//   - Outputs: zero only when dynamic fields, kinds, values, and atomicity
//     match.
//   - Side effects: test-local bytes, cursor, and resolved-result structures
//     only.
// - Split-When:
//   - Floating or guest-memory conversion execution gains independent vectors.
// - Merge-When:
//   - Full formatting conformance owns this exact argument transaction.
// - Summary:
//   - Locks dynamic width/precision consumption and conversion-argument reads.
// - Description:
//   - Includes negative fields, INT_MIN width, promoted hhu, percent, and
//     rollback.
// - Usage:
//   - Built and executed by tests/test_guest_runtime_c.py.
// - Defaults:
//   - A late missing conversion argument rolls back earlier dynamic-field
//     reads.
//

//! Atomic format-argument resolution vectors over canonical guest varargs.

#include "guest_format_args.h"

#include <stddef.h>
#include <stdint.h>

static void write_u64(uint8_t *bytes, uint64_t value, uint32_t size) {
  uint32_t index = UINT32_C(0);
  while (index < size) {
    bytes[index] = (uint8_t)(value >> (index * UINT32_C(8)));
    ++index;
  }
}

static int parse(const char *format, MalbolgeGuestFormatDirective *directive) {
  MalbolgeGuestFormatToken token;
  if (malbolge_guest_format_parse_next(format, UINT32_C(0), &token) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      token.kind != MALBOLGE_GUEST_FORMAT_TOKEN_CONVERSION) {
    return 0;
  }
  directive->flags = token.directive.flags;
  directive->width_kind = token.directive.width_kind;
  directive->width = token.directive.width;
  directive->precision_kind = token.directive.precision_kind;
  directive->precision = token.directive.precision;
  directive->length = token.directive.length;
  directive->length_bits = token.directive.length_bits;
  directive->conversion = token.directive.conversion;
  return 1;
}

static int test_dynamic_fields(void) {
  uint8_t block[16] = {0};
  MalbolgeGuestVarargCursor cursor;
  MalbolgeGuestFormatDirective directive;
  MalbolgeGuestResolvedFormatArgument resolved;

  write_u64(block, UINT32_C(0xfffffffb), UINT32_C(4));
  write_u64(block + UINT32_C(4), UINT32_C(3), UINT32_C(4));
  write_u64(block + UINT32_C(8), UINT64_C(0x1122334455667788), UINT32_C(8));
  if (!parse("%+*.*lld", &directive) ||
      malbolge_guest_varargs_init(&cursor, block, (uint32_t)sizeof(block),
                                  UINT32_C(0x100)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_resolve_argument(&cursor, &directive, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_VALID) {
    return 1;
  }
  if (cursor.offset != UINT32_C(16) ||
      resolved.directive.width_kind != MALBOLGE_GUEST_FORMAT_FIELD_LITERAL ||
      resolved.directive.width != UINT32_C(5) ||
      (resolved.directive.flags & MALBOLGE_GUEST_FORMAT_LEFT) == UINT32_C(0) ||
      (resolved.directive.flags & MALBOLGE_GUEST_FORMAT_PLUS) == UINT32_C(0) ||
      resolved.directive.precision_kind !=
          MALBOLGE_GUEST_FORMAT_FIELD_LITERAL ||
      resolved.directive.precision != UINT32_C(3) ||
      resolved.argument_kind != MALBOLGE_GUEST_VARARG_I64 ||
      resolved.argument.low != UINT64_C(0x1122334455667788) ||
      resolved.argument.high != UINT64_C(0)) {
    return 2;
  }
  return 0;
}

static int test_negative_precision_and_int_min_width(void) {
  uint8_t precision_block[8] = {0};
  uint8_t width_block[8] = {0};
  MalbolgeGuestVarargCursor cursor;
  MalbolgeGuestFormatDirective directive;
  MalbolgeGuestResolvedFormatArgument resolved;

  write_u64(precision_block, UINT32_MAX, UINT32_C(4));
  write_u64(precision_block + UINT32_C(4), UINT32_C(17), UINT32_C(4));
  if (!parse("%.*u", &directive) ||
      malbolge_guest_varargs_init(
          &cursor, precision_block, (uint32_t)sizeof(precision_block),
          UINT32_C(0x200)) != MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_resolve_argument(&cursor, &directive, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      resolved.directive.precision_kind !=
          MALBOLGE_GUEST_FORMAT_FIELD_OMITTED ||
      resolved.directive.precision != UINT32_C(0) ||
      resolved.argument.low != UINT64_C(17) || cursor.offset != UINT32_C(8)) {
    return 1;
  }

  write_u64(width_block, UINT32_C(0x80000000), UINT32_C(4));
  write_u64(width_block + UINT32_C(4), UINT32_C(9), UINT32_C(4));
  if (!parse("%*u", &directive) ||
      malbolge_guest_varargs_init(
          &cursor, width_block, (uint32_t)sizeof(width_block),
          UINT32_C(0x300)) != MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_resolve_argument(&cursor, &directive, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      resolved.directive.width != UINT32_C(0x80000000) ||
      (resolved.directive.flags & MALBOLGE_GUEST_FORMAT_LEFT) == UINT32_C(0) ||
      resolved.argument.low != UINT64_C(9)) {
    return 2;
  }
  return 0;
}

static int test_promoted_small_unsigned_and_percent(void) {
  uint8_t block[4] = {0};
  MalbolgeGuestVarargCursor cursor;
  MalbolgeGuestFormatDirective directive;
  MalbolgeGuestResolvedFormatArgument resolved;

  write_u64(block, UINT32_C(255), UINT32_C(4));
  if (!parse("%hhu", &directive) ||
      malbolge_guest_varargs_init(&cursor, block, UINT32_C(4),
                                  UINT32_C(0x400)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_resolve_argument(&cursor, &directive, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      resolved.argument_kind != MALBOLGE_GUEST_VARARG_I32 ||
      resolved.argument.low != UINT64_C(255) || cursor.offset != UINT32_C(4)) {
    return 1;
  }
  if (!parse("%%", &directive) ||
      malbolge_guest_varargs_init(&cursor, NULL, UINT32_C(0), UINT32_C(0)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_resolve_argument(&cursor, &directive, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      resolved.argument_kind != MALBOLGE_GUEST_VARARG_NONE ||
      resolved.argument.low != UINT64_C(0) ||
      resolved.argument.high != UINT64_C(0) || cursor.offset != UINT32_C(0)) {
    return 2;
  }
  return 0;
}

static int test_late_failure_rolls_back(void) {
  uint8_t block[8] = {0};
  MalbolgeGuestVarargCursor cursor;
  MalbolgeGuestFormatDirective directive;
  MalbolgeGuestResolvedFormatArgument resolved;

  write_u64(block, UINT32_C(6), UINT32_C(4));
  write_u64(block + UINT32_C(4), UINT32_C(2), UINT32_C(4));
  resolved.argument_kind = UINT32_C(77);
  resolved.argument.low = UINT64_C(0x1111);
  resolved.argument.high = UINT64_C(0x2222);
  if (!parse("%*.*lld", &directive) ||
      malbolge_guest_varargs_init(&cursor, block, (uint32_t)sizeof(block),
                                  UINT32_C(0x500)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_resolve_argument(&cursor, &directive, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      cursor.offset != UINT32_C(0) || resolved.argument_kind != UINT32_C(77) ||
      resolved.argument.low != UINT64_C(0x1111) ||
      resolved.argument.high != UINT64_C(0x2222)) {
    return 1;
  }
  return 0;
}

static int test_invalid_inputs(void) {
  uint8_t block[4] = {0};
  MalbolgeGuestVarargCursor cursor;
  MalbolgeGuestFormatDirective directive;
  MalbolgeGuestResolvedFormatArgument resolved;

  if (!parse("%Ld", &directive) ||
      malbolge_guest_varargs_init(&cursor, block, UINT32_C(4),
                                  UINT32_C(0x600)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_resolve_argument(&cursor, &directive, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      cursor.offset != UINT32_C(0)) {
    return 1;
  }
  if (malbolge_guest_format_resolve_argument(NULL, &directive, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      malbolge_guest_format_resolve_argument(&cursor, NULL, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      malbolge_guest_format_resolve_argument(&cursor, &directive, NULL) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT) {
    return 2;
  }
  if (!parse("%%", &directive)) {
    return 3;
  }
  cursor.block = NULL;
  cursor.block_size = UINT32_C(4);
  cursor.linear_address = UINT32_C(0x700);
  cursor.offset = UINT32_C(0);
  resolved.argument_kind = UINT32_C(77);
  resolved.argument.low = UINT64_C(0x1111);
  resolved.argument.high = UINT64_C(0x2222);
  if (malbolge_guest_format_resolve_argument(&cursor, &directive, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      cursor.offset != UINT32_C(0) || resolved.argument_kind != UINT32_C(77) ||
      resolved.argument.low != UINT64_C(0x1111) ||
      resolved.argument.high != UINT64_C(0x2222)) {
    return 4;
  }
  return 0;
}

int main(void) {
  const int dynamic = test_dynamic_fields();
  const int negatives = test_negative_precision_and_int_min_width();
  const int promoted = test_promoted_small_unsigned_and_percent();
  const int rollback = test_late_failure_rolls_back();
  const int invalid = test_invalid_inputs();

  if (dynamic != 0) {
    return 10 + dynamic;
  }
  if (negatives != 0) {
    return 20 + negatives;
  }
  if (promoted != 0) {
    return 30 + promoted;
  }
  if (rollback != 0) {
    return 40 + rollback;
  }
  return invalid == 0 ? 0 : 50 + invalid;
}
