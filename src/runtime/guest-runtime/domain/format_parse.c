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
//   - Deterministic tokenization of the version-one C23 printf grammar.
// - Must-Not:
//   - Consume va_list, execute conversions, or import locale/host formatting.
// - Allows:
//   - Inputs: one narrow format string plus an explicit uint32 byte offset.
//   - Outputs: one stable format token or INVALID_ARGUMENT without publication.
//   - Side effects: local parse state and final caller-owned token publication.
// - Split-When:
//   - Variadic argument extraction or floating execution gains its own policy.
// - Merge-When:
//   - Variadic formatting can own grammar without obscuring its ABI boundary.
// - Summary:
//   - Parses and semantically admits C23 conversion syntax as stable tokens.
// - Description:
//   - Enforces conversion/length/precision/flag rules and guest width support.
// - Usage:
//   - Called repeatedly by future snprintf/vsnprintf execution above typed
//     sinks.
// - Defaults:
//   - Width/precision/length-width arithmetic is checked in the uint32 domain.
//

//! C23 printf grammar tokenizer with no variadic or output dependency.

#include "guest_format_parse.h"

#include <stddef.h>
#include <stdint.h>

static void clear_directive(MalbolgeGuestFormatDirective *directive) {
  directive->flags = UINT32_C(0);
  directive->width_kind = MALBOLGE_GUEST_FORMAT_FIELD_OMITTED;
  directive->width = UINT32_C(0);
  directive->precision_kind = MALBOLGE_GUEST_FORMAT_FIELD_OMITTED;
  directive->precision = UINT32_C(0);
  directive->length = MALBOLGE_GUEST_FORMAT_LENGTH_NONE;
  directive->length_bits = UINT32_C(0);
  directive->conversion = UINT32_C(0);
}

static int advance(uint32_t *index) {
  if (index == NULL || *index == UINT32_MAX) {
    return 0;
  }
  ++(*index);
  return 1;
}

static int offset_within_format(const char *format, uint32_t offset) {
  uint32_t index = UINT32_C(0);

  while (index < offset) {
    if (format[index] == '\0' || !advance(&index)) {
      return 0;
    }
  }
  return 1;
}

static int decimal_digit(char value) { return value >= '0' && value <= '9'; }

static int append_decimal(uint32_t current, char digit, uint32_t *result) {
  const uint32_t value = (uint32_t)(digit - '0');

  if (result == NULL || current > (UINT32_MAX - value) / UINT32_C(10)) {
    return 0;
  }
  *result = current * UINT32_C(10) + value;
  return 1;
}

static int parse_decimal(const char *format, uint32_t *index,
                         uint32_t *result) {
  uint32_t value = UINT32_C(0);
  uint32_t cursor = *index;

  if (!decimal_digit(format[cursor])) {
    return 0;
  }
  while (decimal_digit(format[cursor])) {
    if (!append_decimal(value, format[cursor], &value) || !advance(&cursor)) {
      return -1;
    }
  }
  *index = cursor;
  *result = value;
  return 1;
}

static uint32_t flag_bit(char value) {
  switch (value) {
  case '-':
    return MALBOLGE_GUEST_FORMAT_LEFT;
  case '+':
    return MALBOLGE_GUEST_FORMAT_PLUS;
  case ' ':
    return MALBOLGE_GUEST_FORMAT_SPACE;
  case '#':
    return MALBOLGE_GUEST_FORMAT_ALTERNATE;
  case '0':
    return MALBOLGE_GUEST_FORMAT_ZERO;
  default:
    return UINT32_C(0);
  }
}

static int parse_flags(const char *format, uint32_t *index,
                       MalbolgeGuestFormatDirective *directive) {
  for (;;) {
    const uint32_t bit = flag_bit(format[*index]);

    if (bit == UINT32_C(0)) {
      return 1;
    }
    directive->flags |= bit;
    if (!advance(index)) {
      return 0;
    }
  }
}

static int parse_width(const char *format, uint32_t *index,
                       MalbolgeGuestFormatDirective *directive) {
  int parsed = 0;

  if (format[*index] == '*') {
    directive->width_kind = MALBOLGE_GUEST_FORMAT_FIELD_ARGUMENT;
    return advance(index);
  }
  parsed = parse_decimal(format, index, &directive->width);
  if (parsed < 0) {
    return 0;
  }
  if (parsed > 0) {
    directive->width_kind = MALBOLGE_GUEST_FORMAT_FIELD_LITERAL;
  }
  return 1;
}

static int parse_precision(const char *format, uint32_t *index,
                           MalbolgeGuestFormatDirective *directive) {
  int parsed = 0;

  if (format[*index] != '.') {
    return 1;
  }
  directive->precision_kind = MALBOLGE_GUEST_FORMAT_FIELD_LITERAL;
  if (!advance(index)) {
    return 0;
  }
  if (format[*index] == '*') {
    directive->precision_kind = MALBOLGE_GUEST_FORMAT_FIELD_ARGUMENT;
    return advance(index);
  }
  parsed = parse_decimal(format, index, &directive->precision);
  return parsed >= 0;
}

static int parse_specific_width(const char *format, uint32_t *index,
                                MalbolgeGuestFormatDirective *directive) {
  uint32_t cursor = *index;
  uint32_t width = UINT32_C(0);
  int parsed = 0;

  if (format[cursor] != 'w' || !advance(&cursor)) {
    return 0;
  }
  directive->length = MALBOLGE_GUEST_FORMAT_LENGTH_WIDTH;
  if (format[cursor] == 'f') {
    directive->length = MALBOLGE_GUEST_FORMAT_LENGTH_FAST_WIDTH;
    if (!advance(&cursor)) {
      return 0;
    }
  }
  if (format[cursor] == '0') {
    return 0;
  }
  parsed = parse_decimal(format, &cursor, &width);
  if (parsed <= 0 || width == UINT32_C(0)) {
    return 0;
  }
  directive->length_bits = width;
  *index = cursor;
  return 1;
}

static int parse_length(const char *format, uint32_t *index,
                        MalbolgeGuestFormatDirective *directive) {
  const char value = format[*index];

  if (value == 'w') {
    return parse_specific_width(format, index, directive);
  }
  if (value == 'h') {
    if (!advance(index)) {
      return 0;
    }
    if (format[*index] == 'h') {
      directive->length = MALBOLGE_GUEST_FORMAT_LENGTH_HH;
      return advance(index);
    }
    directive->length = MALBOLGE_GUEST_FORMAT_LENGTH_H;
    return 1;
  }
  if (value == 'l') {
    if (!advance(index)) {
      return 0;
    }
    if (format[*index] == 'l') {
      directive->length = MALBOLGE_GUEST_FORMAT_LENGTH_LL;
      return advance(index);
    }
    directive->length = MALBOLGE_GUEST_FORMAT_LENGTH_L;
    return 1;
  }
  if (value == 'j') {
    directive->length = MALBOLGE_GUEST_FORMAT_LENGTH_J;
    return advance(index);
  }
  if (value == 'z') {
    directive->length = MALBOLGE_GUEST_FORMAT_LENGTH_Z;
    return advance(index);
  }
  if (value == 't') {
    directive->length = MALBOLGE_GUEST_FORMAT_LENGTH_T;
    return advance(index);
  }
  if (value == 'L') {
    directive->length = MALBOLGE_GUEST_FORMAT_LENGTH_LONG_DOUBLE;
    return advance(index);
  }
  return 1;
}

static uint32_t conversion_tag(char value) {
  switch (value) {
  case '%':
    return MALBOLGE_GUEST_FORMAT_CONVERSION_PERCENT;
  case 'b':
    return MALBOLGE_GUEST_FORMAT_CONVERSION_BINARY;
  case 'B':
    return MALBOLGE_GUEST_FORMAT_CONVERSION_BINARY_UPPER;
  case 'd':
    return MALBOLGE_GUEST_FORMAT_CONVERSION_DECIMAL;
  case 'i':
    return MALBOLGE_GUEST_FORMAT_CONVERSION_INTEGER;
  case 'o':
    return MALBOLGE_GUEST_FORMAT_CONVERSION_OCTAL;
  case 'u':
    return MALBOLGE_GUEST_FORMAT_CONVERSION_UNSIGNED;
  case 'x':
    return MALBOLGE_GUEST_FORMAT_CONVERSION_HEX;
  case 'X':
    return MALBOLGE_GUEST_FORMAT_CONVERSION_HEX_UPPER;
  case 'a':
    return MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_HEX;
  case 'A':
    return MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_HEX_UPPER;
  case 'e':
    return MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_EXP;
  case 'E':
    return MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_EXP_UPPER;
  case 'f':
    return MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_FIXED;
  case 'F':
    return MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_FIXED_UPPER;
  case 'g':
    return MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_GENERAL;
  case 'G':
    return MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_GENERAL_UPPER;
  case 'c':
    return MALBOLGE_GUEST_FORMAT_CONVERSION_CHARACTER;
  case 's':
    return MALBOLGE_GUEST_FORMAT_CONVERSION_STRING;
  case 'p':
    return MALBOLGE_GUEST_FORMAT_CONVERSION_POINTER;
  case 'n':
    return MALBOLGE_GUEST_FORMAT_CONVERSION_COUNT;
  default:
    return UINT32_C(0);
  }
}

static int parse_conversion(const char *format, uint32_t *index,
                            MalbolgeGuestFormatDirective *directive) {
  directive->conversion = conversion_tag(format[*index]);
  return directive->conversion != UINT32_C(0) && advance(index);
}

static int parse_directive(const char *format, uint32_t start, uint32_t *end,
                           MalbolgeGuestFormatDirective *directive) {
  uint32_t index = start;

  clear_directive(directive);
  if (format[index] != '%' || !advance(&index) ||
      !parse_flags(format, &index, directive) ||
      !parse_width(format, &index, directive) ||
      !parse_precision(format, &index, directive) ||
      !parse_length(format, &index, directive) ||
      !parse_conversion(format, &index, directive)) {
    return 0;
  }
  *end = index;
  return 1;
}

static void publish_token(MalbolgeGuestFormatToken *destination,
                          const MalbolgeGuestFormatToken *source) {
  destination->kind = source->kind;
  destination->offset = source->offset;
  destination->length = source->length;
  destination->next_offset = source->next_offset;
  destination->directive.flags = source->directive.flags;
  destination->directive.width_kind = source->directive.width_kind;
  destination->directive.width = source->directive.width;
  destination->directive.precision_kind = source->directive.precision_kind;
  destination->directive.precision = source->directive.precision;
  destination->directive.length = source->directive.length;
  destination->directive.length_bits = source->directive.length_bits;
  destination->directive.conversion = source->directive.conversion;
}

static MalbolgeGuestRuntimeStatus
parse_literal(const char *format, uint32_t offset,
              MalbolgeGuestFormatToken *token) {
  MalbolgeGuestFormatToken parsed;
  uint32_t index = offset;

  clear_directive(&parsed.directive);
  parsed.kind = MALBOLGE_GUEST_FORMAT_TOKEN_LITERAL;
  parsed.offset = offset;
  while (format[index] != '\0' && format[index] != '%') {
    if (!advance(&index)) {
      return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
    }
  }
  parsed.length = index - offset;
  parsed.next_offset = index;
  publish_token(token, &parsed);
  return MALBOLGE_GUEST_RUNTIME_VALID;
}

MalbolgeGuestRuntimeStatus
malbolge_guest_format_parse_next(const char *format, uint32_t offset,
                                 MalbolgeGuestFormatToken *token) {
  MalbolgeGuestFormatToken parsed;
  uint32_t end = offset;

  if (format == NULL || token == NULL ||
      !offset_within_format(format, offset)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  if (format[offset] == '\0') {
    clear_directive(&parsed.directive);
    parsed.kind = MALBOLGE_GUEST_FORMAT_TOKEN_END;
    parsed.offset = offset;
    parsed.length = UINT32_C(0);
    parsed.next_offset = offset;
    publish_token(token, &parsed);
    return MALBOLGE_GUEST_RUNTIME_VALID;
  }
  if (format[offset] != '%') {
    return parse_literal(format, offset, token);
  }
  if (!parse_directive(format, offset, &end, &parsed.directive)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  parsed.kind = MALBOLGE_GUEST_FORMAT_TOKEN_CONVERSION;
  parsed.offset = offset;
  parsed.length = end - offset;
  parsed.next_offset = end;
  publish_token(token, &parsed);
  return MALBOLGE_GUEST_RUNTIME_VALID;
}

static int semantic_field_valid(uint32_t kind, uint32_t value) {
  if (kind == MALBOLGE_GUEST_FORMAT_FIELD_OMITTED) {
    return value == UINT32_C(0);
  }
  if (kind == MALBOLGE_GUEST_FORMAT_FIELD_LITERAL) {
    return 1;
  }
  if (kind == MALBOLGE_GUEST_FORMAT_FIELD_ARGUMENT) {
    return value == UINT32_C(0);
  }
  return 0;
}

static int semantic_specific_width_supported(uint32_t bits) {
  return bits == UINT32_C(8) || bits == UINT32_C(16) || bits == UINT32_C(32) ||
         bits == UINT32_C(64);
}

static int semantic_length_shape_valid(const MalbolgeGuestFormatDirective *d) {
  if (d->length == MALBOLGE_GUEST_FORMAT_LENGTH_WIDTH ||
      d->length == MALBOLGE_GUEST_FORMAT_LENGTH_FAST_WIDTH) {
    return semantic_specific_width_supported(d->length_bits);
  }
  return d->length <= MALBOLGE_GUEST_FORMAT_LENGTH_LONG_DOUBLE &&
         d->length_bits == UINT32_C(0);
}

static int semantic_integer_length(uint32_t length) {
  return length == MALBOLGE_GUEST_FORMAT_LENGTH_NONE ||
         length == MALBOLGE_GUEST_FORMAT_LENGTH_HH ||
         length == MALBOLGE_GUEST_FORMAT_LENGTH_H ||
         length == MALBOLGE_GUEST_FORMAT_LENGTH_L ||
         length == MALBOLGE_GUEST_FORMAT_LENGTH_LL ||
         length == MALBOLGE_GUEST_FORMAT_LENGTH_J ||
         length == MALBOLGE_GUEST_FORMAT_LENGTH_Z ||
         length == MALBOLGE_GUEST_FORMAT_LENGTH_T ||
         length == MALBOLGE_GUEST_FORMAT_LENGTH_WIDTH ||
         length == MALBOLGE_GUEST_FORMAT_LENGTH_FAST_WIDTH;
}

static int semantic_float_length(uint32_t length) {
  return length == MALBOLGE_GUEST_FORMAT_LENGTH_NONE ||
         length == MALBOLGE_GUEST_FORMAT_LENGTH_L ||
         length == MALBOLGE_GUEST_FORMAT_LENGTH_LONG_DOUBLE;
}

static int semantic_flags_subset(uint32_t flags, uint32_t allowed) {
  const uint32_t textual =
      MALBOLGE_GUEST_FORMAT_LEFT | MALBOLGE_GUEST_FORMAT_PLUS |
      MALBOLGE_GUEST_FORMAT_SPACE | MALBOLGE_GUEST_FORMAT_ALTERNATE |
      MALBOLGE_GUEST_FORMAT_ZERO;
  return (flags & ~textual) == UINT32_C(0) && (flags & ~allowed) == UINT32_C(0);
}

static int semantic_precision_omitted(const MalbolgeGuestFormatDirective *d) {
  return d->precision_kind == MALBOLGE_GUEST_FORMAT_FIELD_OMITTED;
}

static int semantic_width_omitted(const MalbolgeGuestFormatDirective *d) {
  return d->width_kind == MALBOLGE_GUEST_FORMAT_FIELD_OMITTED;
}

static int semantic_integer(const MalbolgeGuestFormatDirective *d,
                            uint32_t allowed_flags) {
  return semantic_integer_length(d->length) &&
         semantic_flags_subset(d->flags, allowed_flags);
}

static int semantic_float(const MalbolgeGuestFormatDirective *d) {
  const uint32_t flags =
      MALBOLGE_GUEST_FORMAT_LEFT | MALBOLGE_GUEST_FORMAT_PLUS |
      MALBOLGE_GUEST_FORMAT_SPACE | MALBOLGE_GUEST_FORMAT_ALTERNATE |
      MALBOLGE_GUEST_FORMAT_ZERO;
  return semantic_float_length(d->length) &&
         semantic_flags_subset(d->flags, flags);
}

static int semantic_conversion_valid(const MalbolgeGuestFormatDirective *d) {
  const uint32_t signed_flags =
      MALBOLGE_GUEST_FORMAT_LEFT | MALBOLGE_GUEST_FORMAT_PLUS |
      MALBOLGE_GUEST_FORMAT_SPACE | MALBOLGE_GUEST_FORMAT_ZERO;
  const uint32_t base_flags = MALBOLGE_GUEST_FORMAT_LEFT |
                              MALBOLGE_GUEST_FORMAT_ALTERNATE |
                              MALBOLGE_GUEST_FORMAT_ZERO;
  const uint32_t unsigned_flags =
      MALBOLGE_GUEST_FORMAT_LEFT | MALBOLGE_GUEST_FORMAT_ZERO;

  switch (d->conversion) {
  case MALBOLGE_GUEST_FORMAT_CONVERSION_PERCENT:
    return d->flags == UINT32_C(0) && semantic_width_omitted(d) &&
           semantic_precision_omitted(d) &&
           d->length == MALBOLGE_GUEST_FORMAT_LENGTH_NONE;
  case MALBOLGE_GUEST_FORMAT_CONVERSION_BINARY:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_BINARY_UPPER:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_OCTAL:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_HEX:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_HEX_UPPER:
    return semantic_integer(d, base_flags);
  case MALBOLGE_GUEST_FORMAT_CONVERSION_DECIMAL:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_INTEGER:
    return semantic_integer(d, signed_flags);
  case MALBOLGE_GUEST_FORMAT_CONVERSION_UNSIGNED:
    return semantic_integer(d, unsigned_flags);
  case MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_HEX:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_HEX_UPPER:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_EXP:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_EXP_UPPER:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_FIXED:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_FIXED_UPPER:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_GENERAL:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_GENERAL_UPPER:
    return semantic_float(d);
  case MALBOLGE_GUEST_FORMAT_CONVERSION_CHARACTER:
    return semantic_precision_omitted(d) &&
           (d->length == MALBOLGE_GUEST_FORMAT_LENGTH_NONE ||
            d->length == MALBOLGE_GUEST_FORMAT_LENGTH_L) &&
           semantic_flags_subset(d->flags, MALBOLGE_GUEST_FORMAT_LEFT);
  case MALBOLGE_GUEST_FORMAT_CONVERSION_STRING:
    return (d->length == MALBOLGE_GUEST_FORMAT_LENGTH_NONE ||
            d->length == MALBOLGE_GUEST_FORMAT_LENGTH_L) &&
           semantic_flags_subset(d->flags, MALBOLGE_GUEST_FORMAT_LEFT);
  case MALBOLGE_GUEST_FORMAT_CONVERSION_POINTER:
    return semantic_precision_omitted(d) &&
           d->length == MALBOLGE_GUEST_FORMAT_LENGTH_NONE &&
           semantic_flags_subset(d->flags, MALBOLGE_GUEST_FORMAT_LEFT);
  case MALBOLGE_GUEST_FORMAT_CONVERSION_COUNT:
    return d->flags == UINT32_C(0) && semantic_width_omitted(d) &&
           semantic_precision_omitted(d) && semantic_integer_length(d->length);
  default:
    return 0;
  }
}

MalbolgeGuestRuntimeStatus malbolge_guest_format_directive_validate(
    const MalbolgeGuestFormatDirective *directive) {
  if (directive == NULL ||
      !semantic_field_valid(directive->width_kind, directive->width) ||
      !semantic_field_valid(directive->precision_kind, directive->precision) ||
      !semantic_length_shape_valid(directive) ||
      !semantic_conversion_valid(directive)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  return MALBOLGE_GUEST_RUNTIME_VALID;
}

static int semantic_64_bit_integer(uint32_t length, uint32_t length_bits) {
  return length == MALBOLGE_GUEST_FORMAT_LENGTH_LL ||
         length == MALBOLGE_GUEST_FORMAT_LENGTH_J ||
         ((length == MALBOLGE_GUEST_FORMAT_LENGTH_WIDTH ||
           length == MALBOLGE_GUEST_FORMAT_LENGTH_FAST_WIDTH) &&
          length_bits == UINT32_C(64));
}

static int semantic_small_promoted_integer(uint32_t length,
                                           uint32_t length_bits) {
  return length == MALBOLGE_GUEST_FORMAT_LENGTH_HH ||
         length == MALBOLGE_GUEST_FORMAT_LENGTH_H ||
         ((length == MALBOLGE_GUEST_FORMAT_LENGTH_WIDTH ||
           length == MALBOLGE_GUEST_FORMAT_LENGTH_FAST_WIDTH) &&
          (length_bits == UINT32_C(8) || length_bits == UINT32_C(16)));
}

MalbolgeGuestRuntimeStatus malbolge_guest_format_argument_kind(
    const MalbolgeGuestFormatDirective *directive, uint32_t *kind) {
  if (kind == NULL || malbolge_guest_format_directive_validate(directive) !=
                          MALBOLGE_GUEST_RUNTIME_VALID) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  switch (directive->conversion) {
  case MALBOLGE_GUEST_FORMAT_CONVERSION_PERCENT:
    *kind = MALBOLGE_GUEST_VARARG_NONE;
    return MALBOLGE_GUEST_RUNTIME_VALID;
  case MALBOLGE_GUEST_FORMAT_CONVERSION_DECIMAL:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_INTEGER:
    *kind = semantic_64_bit_integer(directive->length, directive->length_bits)
                ? MALBOLGE_GUEST_VARARG_I64
                : MALBOLGE_GUEST_VARARG_I32;
    return MALBOLGE_GUEST_RUNTIME_VALID;
  case MALBOLGE_GUEST_FORMAT_CONVERSION_BINARY:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_BINARY_UPPER:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_OCTAL:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_UNSIGNED:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_HEX:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_HEX_UPPER:
    if (semantic_small_promoted_integer(directive->length,
                                        directive->length_bits)) {
      *kind = MALBOLGE_GUEST_VARARG_I32;
    } else {
      *kind = semantic_64_bit_integer(directive->length, directive->length_bits)
                  ? MALBOLGE_GUEST_VARARG_U64
                  : MALBOLGE_GUEST_VARARG_U32;
    }
    return MALBOLGE_GUEST_RUNTIME_VALID;
  case MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_HEX:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_HEX_UPPER:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_EXP:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_EXP_UPPER:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_FIXED:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_FIXED_UPPER:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_GENERAL:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_GENERAL_UPPER:
    *kind = directive->length == MALBOLGE_GUEST_FORMAT_LENGTH_LONG_DOUBLE
                ? MALBOLGE_GUEST_VARARG_F128
                : MALBOLGE_GUEST_VARARG_F64;
    return MALBOLGE_GUEST_RUNTIME_VALID;
  case MALBOLGE_GUEST_FORMAT_CONVERSION_CHARACTER:
    if (directive->length == MALBOLGE_GUEST_FORMAT_LENGTH_L) {
      return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
    }
    *kind = MALBOLGE_GUEST_VARARG_I32;
    return MALBOLGE_GUEST_RUNTIME_VALID;
  case MALBOLGE_GUEST_FORMAT_CONVERSION_STRING:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_POINTER:
  case MALBOLGE_GUEST_FORMAT_CONVERSION_COUNT:
    *kind = MALBOLGE_GUEST_VARARG_POINTER32;
    return MALBOLGE_GUEST_RUNTIME_VALID;
  default:
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
}
