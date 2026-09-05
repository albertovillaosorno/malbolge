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
//   - Deterministic binary64 %e/%E decimal conversion and bounded publication.
// - Must-Not:
//   - Use host floating arithmetic, formatting, locale, allocation, or va_list.
// - Allows:
//   - Inputs: resolved F64 bits plus literal/omitted width and precision.
//   - Outputs: C scientific decimal spelling with exact sink accounting.
//   - Side effects: bounded sink bytes only after complete geometry admission.
// - Split-When:
//   - Fixed/general or binary128 decimal spelling gains independent policy.
// - Merge-When:
//   - One decimal formatter owns scientific/fixed/general execution together.
// - Summary:
//   - Rounds exact binary64 decimal digits to C %e/%E nearest ties to even.
// - Description:
//   - Large precision becomes virtual trailing zeroes after exact digits end.
// - Usage:
//   - Called after parser admission and atomic promoted-argument resolution.
// - Defaults:
//   - Omitted precision is six digits after the decimal point.
//

//! Exact-decimal binary64 scientific formatting without host floating
//! authority.

#include "guest_decimal_exact.h"
#include "guest_format_float.h"

#include <limits.h>
#include <stddef.h>
#include <stdint.h>

#define B64_SIGN UINT64_C(0x8000000000000000)
#define B64_EXPONENT UINT64_C(0x7ff0000000000000)
#define B64_FRACTION UINT64_C(0x000fffffffffffff)
#define B64_EXPONENT_SHIFT UINT32_C(52)
#define B64_EXPONENT_ALL_ONES UINT32_C(0x7ff)
#define DEFAULT_PRECISION UINT32_C(6)

typedef struct DecimalWriter {
  MalbolgeGuestFormatSink *sink;
  uint32_t logical;
} DecimalWriter;

typedef struct RoundedDecimal {
  char digits[768];
  uint32_t stored_digits;
  uint32_t zero_digits;
  int32_t exponent;
} RoundedDecimal;

static int checked_add(uint32_t left, uint32_t right, uint32_t *result) {
  if (result == NULL || right > UINT32_MAX - left) {
    return 0;
  }
  *result = left + right;
  return 1;
}

static int resolved_scientific(
    const MalbolgeGuestResolvedFormatArgument *resolved) {
  uint32_t kind = MALBOLGE_GUEST_VARARG_NONE;

  if (resolved == NULL || resolved->argument.high != UINT64_C(0) ||
      resolved->argument_kind != MALBOLGE_GUEST_VARARG_F64 ||
      resolved->directive.width_kind == MALBOLGE_GUEST_FORMAT_FIELD_ARGUMENT ||
      resolved->directive.precision_kind ==
          MALBOLGE_GUEST_FORMAT_FIELD_ARGUMENT ||
      (resolved->directive.conversion !=
           MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_EXP &&
       resolved->directive.conversion !=
           MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_EXP_UPPER) ||
      malbolge_guest_format_argument_kind(&resolved->directive, &kind) !=
          MALBOLGE_GUEST_RUNTIME_VALID) {
    return 0;
  }
  return kind == MALBOLGE_GUEST_VARARG_F64;
}

static char sign_character(uint64_t bits, uint32_t flags) {
  if ((bits & B64_SIGN) != UINT64_C(0)) {
    return '-';
  }
  if ((flags & MALBOLGE_GUEST_FORMAT_PLUS) != UINT32_C(0)) {
    return '+';
  }
  if ((flags & MALBOLGE_GUEST_FORMAT_SPACE) != UINT32_C(0)) {
    return ' ';
  }
  return '\0';
}

static uint32_t effective_precision(
    const MalbolgeGuestFormatDirective *directive) {
  return directive->precision_kind == MALBOLGE_GUEST_FORMAT_FIELD_OMITTED
             ? DEFAULT_PRECISION
             : directive->precision;
}

static int exact_rounds_up(const MalbolgeGuestDecimalExact *exact,
                           uint32_t keep) {
  uint32_t index = keep + UINT32_C(1);
  const char first = exact->digits[keep];
  const char retained = exact->digits[keep - UINT32_C(1)];

  if (first > '5') {
    return 1;
  }
  if (first < '5') {
    return 0;
  }
  while (index < exact->digit_count) {
    if (exact->digits[index] != '0') {
      return 1;
    }
    ++index;
  }
  return ((uint32_t)(retained - '0') & UINT32_C(1)) != UINT32_C(0);
}

static int round_exact(const MalbolgeGuestDecimalExact *exact, uint32_t target,
                       RoundedDecimal *rounded) {
  uint32_t index = UINT32_C(0);

  if (exact == NULL || rounded == NULL || target == UINT32_C(0) ||
      exact->digit_count == UINT32_C(0)) {
    return 0;
  }
  rounded->exponent =
      (int32_t)(exact->digit_count - UINT32_C(1)) + exact->decimal_shift;
  rounded->stored_digits =
      target < exact->digit_count ? target : exact->digit_count;
  rounded->zero_digits = target > exact->digit_count
                             ? target - exact->digit_count
                             : UINT32_C(0);
  while (index < rounded->stored_digits) {
    rounded->digits[index] = exact->digits[index];
    ++index;
  }
  if (target >= exact->digit_count || !exact_rounds_up(exact, target)) {
    return 1;
  }
  index = target;
  while (index != UINT32_C(0)) {
    --index;
    if (rounded->digits[index] != '9') {
      ++rounded->digits[index];
      return 1;
    }
    rounded->digits[index] = '0';
  }
  rounded->digits[0] = '1';
  ++rounded->exponent;
  return 1;
}

static uint32_t exponent_digit_count(int32_t exponent) {
  uint32_t magnitude = exponent < INT32_C(0) ? (uint32_t)(-exponent)
                                             : (uint32_t)exponent;
  uint32_t digits = UINT32_C(1);

  while (magnitude >= UINT32_C(10)) {
    magnitude /= UINT32_C(10);
    ++digits;
  }
  return digits < UINT32_C(2) ? UINT32_C(2) : digits;
}

static uint32_t field_width(const MalbolgeGuestFormatDirective *directive) {
  return directive->width_kind == MALBOLGE_GUEST_FORMAT_FIELD_LITERAL
             ? directive->width
             : UINT32_C(0);
}

static int finite_core_length(char sign, uint32_t precision, int point,
                              int32_t exponent, uint32_t *core) {
  uint32_t total = sign == '\0' ? UINT32_C(0) : UINT32_C(1);

  if (!checked_add(total, UINT32_C(1), &total) ||
      !checked_add(total, point != 0 ? UINT32_C(1) : UINT32_C(0), &total) ||
      !checked_add(total, precision, &total) ||
      !checked_add(total, UINT32_C(2), &total) ||
      !checked_add(total, exponent_digit_count(exponent), &total)) {
    return 0;
  }
  *core = total;
  return 1;
}

static int writer_init(DecimalWriter *writer, MalbolgeGuestFormatSink *sink,
                       uint32_t total) {
  if (writer == NULL || sink == NULL ||
      (sink->capacity != UINT32_C(0) && sink->destination == NULL) ||
      total > UINT32_MAX - sink->required) {
    return 0;
  }
  writer->sink = sink;
  writer->logical = UINT32_C(0);
  return 1;
}

static void writer_character(DecimalWriter *writer, char value) {
  const uint32_t position = writer->sink->required + writer->logical;

  if (writer->sink->capacity > UINT32_C(1) &&
      position < writer->sink->capacity - UINT32_C(1)) {
    writer->sink->destination[position] = value;
  }
  ++writer->logical;
}

static void writer_repeat(DecimalWriter *writer, char value, uint32_t count) {
  const uint32_t position = writer->sink->required + writer->logical;
  uint32_t writable = count;
  uint32_t index = UINT32_C(0);

  if (writer->sink->capacity <= UINT32_C(1) ||
      position >= writer->sink->capacity - UINT32_C(1)) {
    writable = UINT32_C(0);
  } else if (writable > writer->sink->capacity - UINT32_C(1) - position) {
    writable = writer->sink->capacity - UINT32_C(1) - position;
  }
  while (index < writable) {
    writer->sink->destination[position + index] = value;
    ++index;
  }
  writer->logical += count;
}

static void emit_exponent(DecimalWriter *writer, int32_t exponent,
                          int uppercase) {
  char reversed[3];
  uint32_t magnitude = exponent < INT32_C(0) ? (uint32_t)(-exponent)
                                             : (uint32_t)exponent;
  uint32_t count = UINT32_C(0);
  uint32_t minimum = UINT32_C(2);

  writer_character(writer, uppercase != 0 ? 'E' : 'e');
  writer_character(writer, exponent < INT32_C(0) ? '-' : '+');
  do {
    reversed[count] = (char)('0' + (char)(magnitude % UINT32_C(10)));
    magnitude /= UINT32_C(10);
    ++count;
  } while (magnitude != UINT32_C(0));
  while (count < minimum) {
    reversed[count] = '0';
    ++count;
  }
  while (count != UINT32_C(0)) {
    --count;
    writer_character(writer, reversed[count]);
  }
}

static void emit_rounded(DecimalWriter *writer, const RoundedDecimal *rounded,
                         uint32_t precision, int point, int uppercase) {
  uint32_t stored_fraction = rounded->stored_digits > UINT32_C(1)
                                 ? rounded->stored_digits - UINT32_C(1)
                                 : UINT32_C(0);
  uint32_t index = UINT32_C(0);

  writer_character(writer, rounded->digits[0]);
  if (point != 0) {
    writer_character(writer, '.');
  }
  while (index < stored_fraction && index < precision) {
    writer_character(writer, rounded->digits[index + UINT32_C(1)]);
    ++index;
  }
  if (precision > index) {
    writer_repeat(writer, '0', precision - index);
  }
  emit_exponent(writer, rounded->exponent, uppercase);
}

static MalbolgeGuestRuntimeStatus emit_special(
    MalbolgeGuestFormatSink *sink,
    const MalbolgeGuestResolvedFormatArgument *resolved, char sign,
    int uppercase) {
  DecimalWriter writer;
  const uint32_t core = sign == '\0' ? UINT32_C(3) : UINT32_C(4);
  const uint32_t width = field_width(&resolved->directive);
  const uint32_t total = width > core ? width : core;
  const uint32_t padding = total - core;
  const int left =
      (resolved->directive.flags & MALBOLGE_GUEST_FORMAT_LEFT) != UINT32_C(0);
  const char *text = (resolved->argument.low & B64_FRACTION) == UINT64_C(0)
                         ? (uppercase != 0 ? "INF" : "inf")
                         : (uppercase != 0 ? "NAN" : "nan");

  if (!writer_init(&writer, sink, total)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  if (left == 0) {
    writer_repeat(&writer, ' ', padding);
  }
  if (sign != '\0') {
    writer_character(&writer, sign);
  }
  writer_character(&writer, text[0]);
  writer_character(&writer, text[1]);
  writer_character(&writer, text[2]);
  if (left != 0) {
    writer_repeat(&writer, ' ', padding);
  }
  sink->required += total;
  return MALBOLGE_GUEST_RUNTIME_VALID;
}

MalbolgeGuestRuntimeStatus malbolge_guest_format_execute_decimal_float(
    MalbolgeGuestFormatSink *sink,
    const MalbolgeGuestResolvedFormatArgument *resolved) {
  MalbolgeGuestDecimalExact exact;
  RoundedDecimal rounded;
  DecimalWriter writer;
  uint32_t precision = UINT32_C(0);
  uint32_t target = UINT32_C(0);
  uint32_t core = UINT32_C(0);
  uint32_t width = UINT32_C(0);
  uint32_t total = UINT32_C(0);
  uint32_t padding = UINT32_C(0);
  const uint64_t bits = resolved != NULL ? resolved->argument.low : UINT64_C(0);
  const uint32_t raw_exponent =
      (uint32_t)((bits & B64_EXPONENT) >> B64_EXPONENT_SHIFT);
  const char sign = resolved != NULL
                        ? sign_character(bits, resolved->directive.flags)
                        : '\0';
  const int uppercase =
      resolved != NULL && resolved->directive.conversion ==
                              MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_EXP_UPPER;
  const int left =
      resolved != NULL &&
      (resolved->directive.flags & MALBOLGE_GUEST_FORMAT_LEFT) != UINT32_C(0);
  int zero = 0;
  int point = 0;

  if (sink == NULL || !resolved_scientific(resolved)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  if (raw_exponent == B64_EXPONENT_ALL_ONES) {
    return emit_special(sink, resolved, sign, uppercase);
  }
  precision = effective_precision(&resolved->directive);
  if (precision == UINT32_MAX) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  target = precision + UINT32_C(1);
  if (malbolge_guest_decimal_from_binary64(bits, &exact) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      !round_exact(&exact, target, &rounded)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  point = precision != UINT32_C(0) ||
          (resolved->directive.flags & MALBOLGE_GUEST_FORMAT_ALTERNATE) !=
              UINT32_C(0);
  if (!finite_core_length(sign, precision, point, rounded.exponent, &core)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  width = field_width(&resolved->directive);
  total = width > core ? width : core;
  padding = total - core;
  zero =
      left == 0 &&
      (resolved->directive.flags & MALBOLGE_GUEST_FORMAT_ZERO) != UINT32_C(0);
  if (!writer_init(&writer, sink, total)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  if (left == 0 && zero == 0) {
    writer_repeat(&writer, ' ', padding);
  }
  if (sign != '\0') {
    writer_character(&writer, sign);
  }
  if (zero != 0) {
    writer_repeat(&writer, '0', padding);
  }
  emit_rounded(&writer, &rounded, precision, point, uppercase);
  if (left != 0) {
    writer_repeat(&writer, ' ', padding);
  }
  sink->required += total;
  return MALBOLGE_GUEST_RUNTIME_VALID;
}
