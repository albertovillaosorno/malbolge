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
//   - Promotion-aware execution of resolved scalar printf conversions.
// - Must-Not:
//   - Dereference pointers, execute %n, format floating values, or call host
//   libc.
// - Allows:
//   - Inputs: validated resolved directive/value plus typed bounded sink.
//   - Outputs: integer, character, or percent bytes with exact sink accounting.
//   - Side effects: sink mutation delegated only to guest formatting
//   primitives.
// - Split-When:
//   - Another conversion family needs separate execution and proof obligations.
// - Merge-When:
//   - Complete formatting owns this exact scalar conversion policy directly.
// - Summary:
//   - Converts raw promoted bits to C-directed scalar widths then emits them.
// - Description:
//   - Signed narrowing uses explicit two's-complement magnitude, never host
//   casts.
// - Usage:
//   - Runs after malbolge_guest_format_resolve_argument succeeds.
// - Defaults:
//   - Pointer-backed and floating conversions return INVALID_ARGUMENT.
//

//! Scalar printf conversion execution over resolved canonical guest arguments.

#include "guest_format_scalar.h"

#include <limits.h>
#include <stddef.h>
#include <stdint.h>

static uint32_t integer_width(const MalbolgeGuestFormatDirective *directive) {
  if (directive->length == MALBOLGE_GUEST_FORMAT_LENGTH_HH) {
    return UINT32_C(8);
  }
  if (directive->length == MALBOLGE_GUEST_FORMAT_LENGTH_H) {
    return UINT32_C(16);
  }
  if (directive->length == MALBOLGE_GUEST_FORMAT_LENGTH_LL ||
      directive->length == MALBOLGE_GUEST_FORMAT_LENGTH_J) {
    return UINT32_C(64);
  }
  if (directive->length == MALBOLGE_GUEST_FORMAT_LENGTH_WIDTH ||
      directive->length == MALBOLGE_GUEST_FORMAT_LENGTH_FAST_WIDTH) {
    return directive->length_bits;
  }
  return UINT32_C(32);
}

static uint64_t low_mask(uint32_t width) {
  if (width == UINT32_C(64)) {
    return UINT64_MAX;
  }
  return (UINT64_C(1) << width) - UINT64_C(1);
}

static uint64_t narrow_unsigned(uint64_t bits, uint32_t width) {
  return bits & low_mask(width);
}

static int64_t narrow_signed(uint64_t bits, uint32_t width) {
  const uint64_t mask = low_mask(width);
  const uint64_t value = bits & mask;
  const uint64_t sign = UINT64_C(1) << (width - UINT32_C(1));
  uint64_t magnitude = UINT64_C(0);

  if ((value & sign) == UINT64_C(0)) {
    return (int64_t)value;
  }
  magnitude = ((~value) & mask) + UINT64_C(1);
  if (width == UINT32_C(64) && magnitude == (UINT64_C(1) << UINT32_C(63))) {
    return INT64_MIN;
  }
  return -(int64_t)magnitude;
}

static uint32_t scalar_width(const MalbolgeGuestFormatDirective *directive) {
  return directive->width_kind == MALBOLGE_GUEST_FORMAT_FIELD_LITERAL
             ? directive->width
             : UINT32_C(0);
}

static uint32_t
scalar_precision(const MalbolgeGuestFormatDirective *directive) {
  return directive->precision_kind == MALBOLGE_GUEST_FORMAT_FIELD_LITERAL
             ? directive->precision
             : MALBOLGE_GUEST_FORMAT_PRECISION_OMITTED;
}

static MalbolgeGuestIntegerFormat
integer_format(const MalbolgeGuestFormatDirective *directive, uint32_t base,
               int uppercase) {
  MalbolgeGuestIntegerFormat format;

  format.flags = directive->flags;
  if (uppercase != 0) {
    format.flags |= MALBOLGE_GUEST_FORMAT_UPPERCASE;
  }
  format.width = scalar_width(directive);
  format.precision = scalar_precision(directive);
  format.base = base;
  return format;
}

static int resolved_fields(const MalbolgeGuestFormatDirective *directive) {
  return directive->width_kind != MALBOLGE_GUEST_FORMAT_FIELD_ARGUMENT &&
         directive->precision_kind != MALBOLGE_GUEST_FORMAT_FIELD_ARGUMENT;
}

static int
canonical_argument(const MalbolgeGuestResolvedFormatArgument *resolved) {
  if (resolved->argument.high != UINT64_C(0)) {
    return 0;
  }
  if (resolved->argument_kind == MALBOLGE_GUEST_VARARG_NONE) {
    return resolved->argument.low == UINT64_C(0);
  }
  if (resolved->argument_kind == MALBOLGE_GUEST_VARARG_I32 ||
      resolved->argument_kind == MALBOLGE_GUEST_VARARG_U32) {
    return resolved->argument.low <= UINT32_MAX;
  }
  return resolved->argument_kind == MALBOLGE_GUEST_VARARG_I64 ||
         resolved->argument_kind == MALBOLGE_GUEST_VARARG_U64;
}

static int expected_kind(const MalbolgeGuestResolvedFormatArgument *resolved) {
  uint32_t kind = MALBOLGE_GUEST_VARARG_NONE;

  return resolved_fields(&resolved->directive) &&
         canonical_argument(resolved) &&
         malbolge_guest_format_argument_kind(&resolved->directive, &kind) ==
             MALBOLGE_GUEST_RUNTIME_VALID &&
         kind == resolved->argument_kind;
}

static MalbolgeGuestRuntimeStatus
execute_signed(MalbolgeGuestFormatSink *sink,
               const MalbolgeGuestResolvedFormatArgument *resolved) {
  const MalbolgeGuestIntegerFormat format =
      integer_format(&resolved->directive, UINT32_C(10), 0);
  const int64_t value = narrow_signed(resolved->argument.low,
                                      integer_width(&resolved->directive));
  return malbolge_guest_format_signed_decimal(sink, value, &format);
}

static MalbolgeGuestRuntimeStatus
execute_unsigned(MalbolgeGuestFormatSink *sink,
                 const MalbolgeGuestResolvedFormatArgument *resolved,
                 uint32_t base, int uppercase) {
  const MalbolgeGuestIntegerFormat format =
      integer_format(&resolved->directive, base, uppercase);
  const uint64_t value = narrow_unsigned(resolved->argument.low,
                                         integer_width(&resolved->directive));
  return malbolge_guest_format_unsigned(sink, value, &format);
}

MalbolgeGuestRuntimeStatus malbolge_guest_format_execute_scalar(
    MalbolgeGuestFormatSink *sink,
    const MalbolgeGuestResolvedFormatArgument *resolved) {
  if (sink == NULL || resolved == NULL || !expected_kind(resolved)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  switch (resolved->directive.conversion) {
  case MALBOLGE_GUEST_FORMAT_CONVERSION_PERCENT:
    return malbolge_guest_format_character(sink, (uint8_t)'%', UINT32_C(0),
                                           UINT32_C(0));
  case MALBOLGE_GUEST_FORMAT_CONVERSION_DECIMAL:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_INTEGER:
    return execute_signed(sink, resolved);
  case MALBOLGE_GUEST_FORMAT_CONVERSION_BINARY:
    return execute_unsigned(sink, resolved, UINT32_C(2), 0);
  case MALBOLGE_GUEST_FORMAT_CONVERSION_BINARY_UPPER:
    return execute_unsigned(sink, resolved, UINT32_C(2), 1);
  case MALBOLGE_GUEST_FORMAT_CONVERSION_OCTAL:
    return execute_unsigned(sink, resolved, UINT32_C(8), 0);
  case MALBOLGE_GUEST_FORMAT_CONVERSION_UNSIGNED:
    return execute_unsigned(sink, resolved, UINT32_C(10), 0);
  case MALBOLGE_GUEST_FORMAT_CONVERSION_HEX:
    return execute_unsigned(sink, resolved, UINT32_C(16), 0);
  case MALBOLGE_GUEST_FORMAT_CONVERSION_HEX_UPPER:
    return execute_unsigned(sink, resolved, UINT32_C(16), 1);
  case MALBOLGE_GUEST_FORMAT_CONVERSION_CHARACTER:
    return malbolge_guest_format_character(
        sink, (uint8_t)resolved->argument.low,
        scalar_width(&resolved->directive), resolved->directive.flags);
  case MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_HEX:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_HEX_UPPER:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_EXP:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_EXP_UPPER:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_FIXED:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_FIXED_UPPER:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_GENERAL:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_GENERAL_UPPER:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_STRING:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_POINTER:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_COUNT:
  default:
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
}
