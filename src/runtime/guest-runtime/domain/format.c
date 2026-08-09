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
//   - Exact integer/string conversion and bounded formatting sink semantics.
// - Must-Not:
//   - Parse printf syntax, inspect locale, allocate, or call host formatting.
// - Allows:
//   - Inputs: validated typed requests and caller-owned sink storage.
//   - Outputs: deterministic bytes and exact would-have-written count.
//   - Side effects: bounded writes to the declared sink destination only.
// - Split-When:
//   - Format parsing, varargs decoding, or floating conversion is implemented.
// - Merge-When:
//   - One complete formatter owns both syntax and typed conversion semantics.
// - Summary:
//   - Implements deterministic integer/string formatting primitives.
// - Description:
//   - Applies width, precision, sign, radix prefix, and truncation rules.
// - Usage:
//   - Future snprintf/vsnprintf parsing delegates typed conversions here.
// - Defaults:
//   - Nonzero sink capacity always reserves one byte for a final null.
//

//! Typed bounded formatting primitives with no host formatter dependency.

#include "guest_format.h"

#include <limits.h>
#include <stddef.h>
#include <stdint.h>

#define DIGIT_CAPACITY UINT32_C(64)
#define VALID_FLAGS                                                            \
  (MALBOLGE_GUEST_FORMAT_LEFT | MALBOLGE_GUEST_FORMAT_PLUS |                   \
   MALBOLGE_GUEST_FORMAT_SPACE | MALBOLGE_GUEST_FORMAT_ALTERNATE |             \
   MALBOLGE_GUEST_FORMAT_ZERO | MALBOLGE_GUEST_FORMAT_UPPERCASE)

typedef struct IntegerParts {
  char digits[64];
  uint32_t digits_length;
  char prefix[2];
  uint32_t prefix_length;
  char sign;
} IntegerParts;

static MalbolgeGuestRuntimeStatus
reserve_output(MalbolgeGuestFormatSink *sink, uint32_t count, uint32_t *start) {
  if (sink == NULL || start == NULL ||
      (sink->capacity != UINT32_C(0) && sink->destination == NULL) ||
      count > UINT32_MAX - sink->required) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  *start = sink->required;
  sink->required += count;
  return MALBOLGE_GUEST_RUNTIME_VALID;
}

static uint32_t writable_count(const MalbolgeGuestFormatSink *sink,
                               uint32_t start, uint32_t count) {
  uint32_t writable_limit = 0U;

  if (sink->capacity <= UINT32_C(1) || start >= sink->capacity - UINT32_C(1)) {
    return UINT32_C(0);
  }
  writable_limit = sink->capacity - UINT32_C(1) - start;
  return count < writable_limit ? count : writable_limit;
}

static MalbolgeGuestRuntimeStatus emit_repeat(MalbolgeGuestFormatSink *sink,
                                              char value, uint32_t count) {
  uint32_t start = 0U;
  uint32_t writable = 0U;
  uint32_t index = 0U;
  MalbolgeGuestRuntimeStatus status = reserve_output(sink, count, &start);

  if (status != MALBOLGE_GUEST_RUNTIME_VALID) {
    return status;
  }
  writable = writable_count(sink, start, count);
  while (index < writable) {
    sink->destination[start + index] = value;
    ++index;
  }
  return MALBOLGE_GUEST_RUNTIME_VALID;
}

static MalbolgeGuestRuntimeStatus
emit_bytes(MalbolgeGuestFormatSink *sink, const char *bytes, uint32_t count) {
  uint32_t start = 0U;
  uint32_t writable = 0U;
  uint32_t index = 0U;
  MalbolgeGuestRuntimeStatus status = MALBOLGE_GUEST_RUNTIME_VALID;

  if (bytes == NULL && count != UINT32_C(0)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  status = reserve_output(sink, count, &start);
  if (status != MALBOLGE_GUEST_RUNTIME_VALID) {
    return status;
  }
  writable = writable_count(sink, start, count);
  while (index < writable) {
    sink->destination[start + index] = bytes[index];
    ++index;
  }
  return MALBOLGE_GUEST_RUNTIME_VALID;
}

static int valid_integer_format(const MalbolgeGuestIntegerFormat *format,
                                int signed_conversion) {
  if (format == NULL || (format->flags & ~VALID_FLAGS) != UINT32_C(0)) {
    return 0;
  }
  if (format->base != UINT32_C(2) && format->base != UINT32_C(8) &&
      format->base != UINT32_C(10) && format->base != UINT32_C(16)) {
    return 0;
  }
  if (signed_conversion != 0) {
    return format->base == UINT32_C(10) &&
           (format->flags & (MALBOLGE_GUEST_FORMAT_ALTERNATE |
                             MALBOLGE_GUEST_FORMAT_UPPERCASE)) == UINT32_C(0);
  }
  if ((format->flags & (MALBOLGE_GUEST_FORMAT_PLUS |
                        MALBOLGE_GUEST_FORMAT_SPACE)) != UINT32_C(0)) {
    return 0;
  }
  if (format->base == UINT32_C(10) &&
      (format->flags & (MALBOLGE_GUEST_FORMAT_ALTERNATE |
                        MALBOLGE_GUEST_FORMAT_UPPERCASE)) != UINT32_C(0)) {
    return 0;
  }
  if (format->base == UINT32_C(8) &&
      (format->flags & MALBOLGE_GUEST_FORMAT_UPPERCASE) != UINT32_C(0)) {
    return 0;
  }
  return 1;
}

static void accumulate_word_digits(uint8_t digits[64], uint32_t *digit_count,
                                   uint32_t word, uint32_t base) {
  uint32_t bit = UINT32_C(32);

  while (bit != UINT32_C(0)) {
    uint32_t index = 0U;
    uint32_t carry = (word >> (bit - UINT32_C(1))) & UINT32_C(1);

    while (index < *digit_count) {
      const uint32_t doubled = ((uint32_t)digits[index] * UINT32_C(2)) + carry;
      digits[index] = (uint8_t)(doubled % base);
      carry = doubled / base;
      ++index;
    }
    if (carry != UINT32_C(0)) {
      digits[*digit_count] = (uint8_t)carry;
      ++(*digit_count);
    }
    --bit;
  }
}

static void build_digits(IntegerParts *parts, uint64_t value, uint32_t base,
                         int uppercase, uint32_t precision) {
  uint8_t numeric[64];
  uint32_t count = UINT32_C(1);
  uint32_t index = 0U;
  const uint32_t high = (uint32_t)(value >> UINT32_C(32));
  const uint32_t low = (uint32_t)value;
  const char *alphabet =
      uppercase != 0 ? "0123456789ABCDEF" : "0123456789abcdef";

  numeric[0] = UINT8_C(0);
  accumulate_word_digits(numeric, &count, high, base);
  accumulate_word_digits(numeric, &count, low, base);
  while (count > UINT32_C(1) && numeric[count - UINT32_C(1)] == UINT8_C(0)) {
    --count;
  }
  if (count == UINT32_C(1) && numeric[0] == UINT8_C(0) &&
      precision == UINT32_C(0)) {
    count = UINT32_C(0);
  }
  parts->digits_length = count;
  while (index < count) {
    parts->digits[index] = alphabet[numeric[count - index - UINT32_C(1)]];
    ++index;
  }
}

static void build_unsigned_prefix(IntegerParts *parts, uint64_t value,
                                  const MalbolgeGuestIntegerFormat *format) {
  if ((format->flags & MALBOLGE_GUEST_FORMAT_ALTERNATE) == UINT32_C(0)) {
    return;
  }
  if (format->base == UINT32_C(8)) {
    return;
  }
  if (value == UINT64_C(0) ||
      (format->base != UINT32_C(2) && format->base != UINT32_C(16))) {
    return;
  }
  parts->prefix[0] = '0';
  if (format->base == UINT32_C(2)) {
    parts->prefix[1] =
        (format->flags & MALBOLGE_GUEST_FORMAT_UPPERCASE) != UINT32_C(0) ? 'B'
                                                                         : 'b';
  } else {
    parts->prefix[1] =
        (format->flags & MALBOLGE_GUEST_FORMAT_UPPERCASE) != UINT32_C(0) ? 'X'
                                                                         : 'x';
  }
  parts->prefix_length = UINT32_C(2);
}

static uint32_t effective_precision(const MalbolgeGuestIntegerFormat *format) {
  return format->precision == MALBOLGE_GUEST_FORMAT_PRECISION_OMITTED
             ? UINT32_C(1)
             : format->precision;
}

static uint32_t precision_zeros(const IntegerParts *parts,
                                const MalbolgeGuestIntegerFormat *format) {
  const uint32_t precision = effective_precision(format);
  return precision > parts->digits_length ? precision - parts->digits_length
                                          : UINT32_C(0);
}

static int checked_add_u32(uint32_t left, uint32_t right, uint32_t *result) {
  if (result == NULL || right > UINT32_MAX - left) {
    return 0;
  }
  *result = left + right;
  return 1;
}

static uint32_t octal_precision_zero(const IntegerParts *parts,
                                     const MalbolgeGuestIntegerFormat *format,
                                     uint32_t current_zeros) {
  if (format->base != UINT32_C(8) ||
      (format->flags & MALBOLGE_GUEST_FORMAT_ALTERNATE) == UINT32_C(0) ||
      current_zeros != UINT32_C(0)) {
    return current_zeros;
  }
  if (parts->digits_length == UINT32_C(0) || parts->digits[0] != '0') {
    return UINT32_C(1);
  }
  return current_zeros;
}

static int integer_field_geometry(const IntegerParts *parts,
                                  const MalbolgeGuestIntegerFormat *format,
                                  uint32_t *zeros, uint32_t *padding,
                                  uint32_t *total) {
  uint32_t core = parts->sign == '\0' ? UINT32_C(0) : UINT32_C(1);
  uint32_t computed_zeros = precision_zeros(parts, format);

  if (zeros == NULL || padding == NULL || total == NULL) {
    return 0;
  }
  computed_zeros = octal_precision_zero(parts, format, computed_zeros);
  if (!checked_add_u32(core, parts->prefix_length, &core) ||
      !checked_add_u32(core, computed_zeros, &core) ||
      !checked_add_u32(core, parts->digits_length, &core)) {
    return 0;
  }
  *zeros = computed_zeros;
  *padding = format->width > core ? format->width - core : UINT32_C(0);
  *total = format->width > core ? format->width : core;
  return 1;
}

static MalbolgeGuestRuntimeStatus
emit_integer(MalbolgeGuestFormatSink *sink, const IntegerParts *parts,
             const MalbolgeGuestIntegerFormat *format) {
  uint32_t precision_padding = 0U;
  uint32_t field_padding = 0U;
  uint32_t total = 0U;
  const int left = (format->flags & MALBOLGE_GUEST_FORMAT_LEFT) != UINT32_C(0);
  const int precision_present =
      format->precision != MALBOLGE_GUEST_FORMAT_PRECISION_OMITTED;
  const int zero_pad =
      !left && !precision_present &&
      (format->flags & MALBOLGE_GUEST_FORMAT_ZERO) != UINT32_C(0);
  MalbolgeGuestRuntimeStatus status = MALBOLGE_GUEST_RUNTIME_VALID;

  if (sink == NULL ||
      !integer_field_geometry(parts, format, &precision_padding, &field_padding,
                              &total) ||
      total > UINT32_MAX - sink->required) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  if (!left && !zero_pad) {
    status = emit_repeat(sink, ' ', field_padding);
  }
  if (status == MALBOLGE_GUEST_RUNTIME_VALID && parts->sign != '\0') {
    status = emit_repeat(sink, parts->sign, UINT32_C(1));
  }
  if (status == MALBOLGE_GUEST_RUNTIME_VALID) {
    status = emit_bytes(sink, parts->prefix, parts->prefix_length);
  }
  if (status == MALBOLGE_GUEST_RUNTIME_VALID && zero_pad) {
    status = emit_repeat(sink, '0', field_padding);
  }
  if (status == MALBOLGE_GUEST_RUNTIME_VALID) {
    status = emit_repeat(sink, '0', precision_padding);
  }
  if (status == MALBOLGE_GUEST_RUNTIME_VALID) {
    status = emit_bytes(sink, parts->digits, parts->digits_length);
  }
  if (status == MALBOLGE_GUEST_RUNTIME_VALID && left) {
    status = emit_repeat(sink, ' ', field_padding);
  }
  return status;
}

MalbolgeGuestRuntimeStatus
malbolge_guest_format_sink_init(MalbolgeGuestFormatSink *sink,
                                char *destination, uint32_t capacity) {
  if (sink == NULL || (capacity != UINT32_C(0) && destination == NULL)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  sink->destination = destination;
  sink->capacity = capacity;
  sink->required = UINT32_C(0);
  if (capacity != UINT32_C(0)) {
    destination[0] = '\0';
  }
  return MALBOLGE_GUEST_RUNTIME_VALID;
}

MalbolgeGuestRuntimeStatus
malbolge_guest_format_finish(MalbolgeGuestFormatSink *sink) {
  uint32_t terminator = 0U;

  if (sink == NULL ||
      (sink->capacity != UINT32_C(0) && sink->destination == NULL)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  if (sink->capacity == UINT32_C(0)) {
    return MALBOLGE_GUEST_RUNTIME_VALID;
  }
  terminator = sink->required < sink->capacity ? sink->required
                                               : sink->capacity - UINT32_C(1);
  sink->destination[terminator] = '\0';
  return MALBOLGE_GUEST_RUNTIME_VALID;
}

MalbolgeGuestRuntimeStatus
malbolge_guest_format_unsigned(MalbolgeGuestFormatSink *sink, uint64_t value,
                               const MalbolgeGuestIntegerFormat *format) {
  IntegerParts parts;

  parts.digits_length = UINT32_C(0);
  parts.prefix_length = UINT32_C(0);
  parts.sign = '\0';

  if (!valid_integer_format(format, 0)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  build_digits(&parts, value, format->base,
               (format->flags & MALBOLGE_GUEST_FORMAT_UPPERCASE) != UINT32_C(0),
               effective_precision(format));
  build_unsigned_prefix(&parts, value, format);
  return emit_integer(sink, &parts, format);
}

MalbolgeGuestRuntimeStatus
malbolge_guest_format_signed_decimal(MalbolgeGuestFormatSink *sink,
                                     int64_t value,
                                     const MalbolgeGuestIntegerFormat *format) {
  IntegerParts parts;
  uint64_t magnitude = 0U;

  parts.digits_length = UINT32_C(0);
  parts.prefix_length = UINT32_C(0);
  parts.sign = '\0';

  if (!valid_integer_format(format, 1)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  if (value < INT64_C(0)) {
    parts.sign = '-';
    magnitude = (uint64_t)(-(value + INT64_C(1))) + UINT64_C(1);
  } else {
    magnitude = (uint64_t)value;
    if ((format->flags & MALBOLGE_GUEST_FORMAT_PLUS) != UINT32_C(0)) {
      parts.sign = '+';
    } else if ((format->flags & MALBOLGE_GUEST_FORMAT_SPACE) != UINT32_C(0)) {
      parts.sign = ' ';
    }
  }
  build_digits(&parts, magnitude, UINT32_C(10), 0, effective_precision(format));
  return emit_integer(sink, &parts, format);
}

static MalbolgeGuestRuntimeStatus
emit_padded_bytes(MalbolgeGuestFormatSink *sink, const char *value,
                  uint32_t length, uint32_t width, uint32_t flags) {
  const uint32_t padding = width > length ? width - length : UINT32_C(0);
  MalbolgeGuestRuntimeStatus status = MALBOLGE_GUEST_RUNTIME_VALID;

  const uint32_t total = width > length ? width : length;

  if (sink == NULL || total > UINT32_MAX - sink->required) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  if ((flags & MALBOLGE_GUEST_FORMAT_LEFT) == UINT32_C(0)) {
    status = emit_repeat(sink, ' ', padding);
  }
  if (status == MALBOLGE_GUEST_RUNTIME_VALID) {
    status = emit_bytes(sink, value, length);
  }
  if (status == MALBOLGE_GUEST_RUNTIME_VALID &&
      (flags & MALBOLGE_GUEST_FORMAT_LEFT) != UINT32_C(0)) {
    status = emit_repeat(sink, ' ', padding);
  }
  return status;
}

MalbolgeGuestRuntimeStatus
malbolge_guest_format_string(MalbolgeGuestFormatSink *sink, const char *value,
                             uint32_t width, uint32_t precision,
                             uint32_t flags) {
  uint32_t length = 0U;

  if (value == NULL || (flags & ~MALBOLGE_GUEST_FORMAT_LEFT) != UINT32_C(0)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  while (precision == MALBOLGE_GUEST_FORMAT_PRECISION_OMITTED ||
         length < precision) {
    if (length == UINT32_MAX) {
      return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
    }
    if (value[length] == '\0') {
      break;
    }
    ++length;
  }
  return emit_padded_bytes(sink, value, length, width, flags);
}

MalbolgeGuestRuntimeStatus
malbolge_guest_format_character(MalbolgeGuestFormatSink *sink, uint8_t value,
                                uint32_t width, uint32_t flags) {
  char character = (char)value;

  if ((flags & ~MALBOLGE_GUEST_FORMAT_LEFT) != UINT32_C(0)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  return emit_padded_bytes(sink, &character, UINT32_C(1), width, flags);
}
