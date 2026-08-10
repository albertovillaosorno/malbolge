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
//   - Transactional guest printf argument resolution over canonical vararg
//     bytes.
// - Must-Not:
//   - Format output, dereference guest pointers, or inspect a native va_list.
// - Allows:
//   - Inputs: admitted format directive and canonical guest vararg cursor.
//   - Outputs: resolved directive, promoted kind, and raw promoted value bits.
//   - Side effects: original cursor/result mutation only on complete success.
// - Split-When:
//   - Conversion execution or guest-memory dereference needs separate
//     ownership.
// - Merge-When:
//   - One public formatter can own resolution without hiding ABI semantics.
// - Summary:
//   - Resolves dynamic fields then reads the conversion argument atomically.
// - Description:
//   - Negative width adds left flag; negative precision becomes omitted.
// - Usage:
//   - Bridges parser admission to typed formatter execution.
// - Defaults:
//   - Dynamic fields are promoted int32 arguments in source order.
//

//! Atomic directive argument resolution over guest promoted variadic storage.

#include "guest_format_args.h"

#include <stddef.h>
#include <stdint.h>

#define SIGN32 UINT32_C(0x80000000)

static void copy_cursor(MalbolgeGuestVarargCursor *destination,
                        const MalbolgeGuestVarargCursor *source) {
  destination->block = source->block;
  destination->block_size = source->block_size;
  destination->linear_address = source->linear_address;
  destination->offset = source->offset;
}

static void copy_directive(MalbolgeGuestFormatDirective *destination,
                           const MalbolgeGuestFormatDirective *source) {
  destination->flags = source->flags;
  destination->width_kind = source->width_kind;
  destination->width = source->width;
  destination->precision_kind = source->precision_kind;
  destination->precision = source->precision;
  destination->length = source->length;
  destination->length_bits = source->length_bits;
  destination->conversion = source->conversion;
}

static int read_dynamic_i32(MalbolgeGuestVarargCursor *cursor, uint32_t *bits) {
  MalbolgeGuestVarargValue value;

  if (malbolge_guest_varargs_read(cursor, MALBOLGE_GUEST_VARARG_I32, &value) !=
      MALBOLGE_GUEST_RUNTIME_VALID) {
    return 0;
  }
  *bits = (uint32_t)value.low;
  return 1;
}

static int resolve_width(MalbolgeGuestVarargCursor *cursor,
                         MalbolgeGuestFormatDirective *directive) {
  uint32_t bits = UINT32_C(0);

  if (directive->width_kind != MALBOLGE_GUEST_FORMAT_FIELD_ARGUMENT) {
    return 1;
  }
  if (!read_dynamic_i32(cursor, &bits)) {
    return 0;
  }
  directive->width_kind = MALBOLGE_GUEST_FORMAT_FIELD_LITERAL;
  if ((bits & SIGN32) != UINT32_C(0)) {
    directive->flags |= MALBOLGE_GUEST_FORMAT_LEFT;
    directive->width = UINT32_C(0) - bits;
  } else {
    directive->width = bits;
  }
  return 1;
}

static int resolve_precision(MalbolgeGuestVarargCursor *cursor,
                             MalbolgeGuestFormatDirective *directive) {
  uint32_t bits = UINT32_C(0);

  if (directive->precision_kind != MALBOLGE_GUEST_FORMAT_FIELD_ARGUMENT) {
    return 1;
  }
  if (!read_dynamic_i32(cursor, &bits)) {
    return 0;
  }
  if ((bits & SIGN32) != UINT32_C(0)) {
    directive->precision_kind = MALBOLGE_GUEST_FORMAT_FIELD_OMITTED;
    directive->precision = UINT32_C(0);
  } else {
    directive->precision_kind = MALBOLGE_GUEST_FORMAT_FIELD_LITERAL;
    directive->precision = bits;
  }
  return 1;
}

static void publish_result(MalbolgeGuestResolvedFormatArgument *destination,
                           const MalbolgeGuestResolvedFormatArgument *source) {
  copy_directive(&destination->directive, &source->directive);
  destination->argument_kind = source->argument_kind;
  destination->argument.low = source->argument.low;
  destination->argument.high = source->argument.high;
}

MalbolgeGuestRuntimeStatus malbolge_guest_format_resolve_argument(
    MalbolgeGuestVarargCursor *cursor,
    const MalbolgeGuestFormatDirective *directive,
    MalbolgeGuestResolvedFormatArgument *result) {
  MalbolgeGuestVarargCursor staged_cursor;
  MalbolgeGuestResolvedFormatArgument staged;

  if (directive == NULL || result == NULL ||
      malbolge_guest_varargs_validate(cursor) != MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_directive_validate(directive) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_argument_kind(directive, &staged.argument_kind) !=
          MALBOLGE_GUEST_RUNTIME_VALID) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  copy_cursor(&staged_cursor, cursor);
  copy_directive(&staged.directive, directive);
  staged.argument.low = UINT64_C(0);
  staged.argument.high = UINT64_C(0);
  if (!resolve_width(&staged_cursor, &staged.directive) ||
      !resolve_precision(&staged_cursor, &staged.directive)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  if (staged.argument_kind != MALBOLGE_GUEST_VARARG_NONE &&
      malbolge_guest_varargs_read(&staged_cursor, staged.argument_kind,
                                  &staged.argument) !=
          MALBOLGE_GUEST_RUNTIME_VALID) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  copy_cursor(cursor, &staged_cursor);
  publish_result(result, &staged);
  return MALBOLGE_GUEST_RUNTIME_VALID;
}
