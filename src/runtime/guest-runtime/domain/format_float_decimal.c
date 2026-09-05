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
//   - Deterministic binary64/binary128 decimal conversion and publication.
// - Must-Not:
//   - Use host floating arithmetic, formatting, locale, allocation, or va_list.
// - Allows:
//   - Inputs: resolved F64/F128 bits plus literal/omitted width and precision.
//   - Outputs: C scientific, fixed, or general decimal text and exact count.
//   - Side effects: bounded sink bytes only after complete geometry admission.
// - Split-When:
//   - Another floating format gains independent decimal arithmetic.
// - Merge-When:
//   - One decimal formatter owns scientific/fixed/general execution together.
// - Summary:
//   - Rounds exact binary decimal digits nearest ties to even for e/f/g.
// - Description:
//   - Large precision becomes virtual trailing zeroes after exact digits end.
// - Usage:
//   - Called after parser admission and atomic promoted-argument resolution.
// - Defaults:
//   - Omitted precision is six digits after the decimal point.
//

//! Exact-decimal binary64/binary128 formatting without host authority.

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
#define B128_EXPONENT UINT64_C(0x7fff000000000000)
#define B128_FRACTION_HIGH UINT64_C(0x0000ffffffffffff)
#define B128_EXPONENT_SHIFT UINT32_C(48)
#define B128_EXPONENT_ALL_ONES UINT32_C(0x7fff)
#define DEFAULT_PRECISION UINT32_C(6)

typedef struct DecimalWriter {
  MalbolgeGuestFormatSink *sink;
  uint32_t logical;
} DecimalWriter;

typedef struct DecimalExactView {
  const char *digits;
  uint32_t digit_count;
  int32_t decimal_shift;
} DecimalExactView;

typedef struct RoundedDecimal {
  char *digits;
  uint32_t digit_capacity;
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

static int resolved_decimal(
    const MalbolgeGuestResolvedFormatArgument *resolved) {
  uint32_t kind = MALBOLGE_GUEST_VARARG_NONE;

  if (resolved == NULL ||
      resolved->directive.width_kind == MALBOLGE_GUEST_FORMAT_FIELD_ARGUMENT ||
      resolved->directive.precision_kind ==
          MALBOLGE_GUEST_FORMAT_FIELD_ARGUMENT ||
      (resolved->directive.conversion !=
           MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_EXP &&
       resolved->directive.conversion !=
           MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_EXP_UPPER &&
       resolved->directive.conversion !=
           MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_FIXED &&
       resolved->directive.conversion !=
           MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_FIXED_UPPER &&
       resolved->directive.conversion !=
           MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_GENERAL &&
       resolved->directive.conversion !=
           MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_GENERAL_UPPER) ||
      malbolge_guest_format_argument_kind(&resolved->directive, &kind) !=
          MALBOLGE_GUEST_RUNTIME_VALID) {
    return 0;
  }
  if (kind == MALBOLGE_GUEST_VARARG_F64) {
    return resolved->argument_kind == MALBOLGE_GUEST_VARARG_F64 &&
           resolved->argument.high == UINT64_C(0);
  }
  return kind == MALBOLGE_GUEST_VARARG_F128 &&
         resolved->argument_kind == MALBOLGE_GUEST_VARARG_F128;
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

static uint32_t general_precision(
    const MalbolgeGuestFormatDirective *directive) {
  const uint32_t precision = effective_precision(directive);
  return precision == UINT32_C(0) ? UINT32_C(1) : precision;
}

static int exact_rounds_up(const DecimalExactView *exact,
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

static int round_exact(const DecimalExactView *exact, uint32_t target,
                       RoundedDecimal *rounded) {
  uint32_t index = UINT32_C(0);

  if (exact == NULL || rounded == NULL || rounded->digits == NULL ||
      target == UINT32_C(0) || exact->digit_count == UINT32_C(0)) {
    return 0;
  }
  rounded->exponent =
      (int32_t)(exact->digit_count - UINT32_C(1)) + exact->decimal_shift;
  rounded->stored_digits =
      target < exact->digit_count ? target : exact->digit_count;
  rounded->zero_digits = target > exact->digit_count
                             ? target - exact->digit_count
                             : UINT32_C(0);
  if (rounded->stored_digits > rounded->digit_capacity) {
    return 0;
  }
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

static int half_without_retained_rounds_up(
    const DecimalExactView *exact) {
  uint32_t index = UINT32_C(1);

  if (exact->digits[0] > '5') {
    return 1;
  }
  if (exact->digits[0] < '5') {
    return 0;
  }
  while (index < exact->digit_count) {
    if (exact->digits[index] != '0') {
      return 1;
    }
    ++index;
  }
  return 0;
}

static void trim_scaled_zeros(RoundedDecimal *scaled) {
  while (scaled->stored_digits > UINT32_C(1) &&
         scaled->digits[scaled->stored_digits - UINT32_C(1)] == '0') {
    --scaled->stored_digits;
    ++scaled->zero_digits;
  }
}

static int quantize_fixed(const DecimalExactView *exact,
                          uint32_t precision, RoundedDecimal *scaled) {
  int32_t decimal_power = INT32_C(0);
  uint32_t keep = UINT32_C(0);
  uint32_t index = UINT32_C(0);

  if (exact == NULL || scaled == NULL || scaled->digits == NULL ||
      precision > (uint32_t)INT32_MAX ||
      exact->decimal_shift > INT32_MAX - (int32_t)precision) {
    return 0;
  }
  decimal_power = exact->decimal_shift + (int32_t)precision;
  scaled->exponent = INT32_C(0);
  scaled->zero_digits = UINT32_C(0);
  if (decimal_power >= INT32_C(0)) {
    if (exact->digit_count > scaled->digit_capacity) {
      return 0;
    }
    scaled->stored_digits = exact->digit_count;
    scaled->zero_digits = (uint32_t)decimal_power;
    while (index < exact->digit_count) {
      scaled->digits[index] = exact->digits[index];
      ++index;
    }
    trim_scaled_zeros(scaled);
    return 1;
  }
  {
    const uint32_t cut = (uint32_t)(-decimal_power);
    if (cut > exact->digit_count) {
      scaled->digits[0] = '0';
      scaled->stored_digits = UINT32_C(1);
      return 1;
    }
    if (cut == exact->digit_count) {
      scaled->digits[0] = half_without_retained_rounds_up(exact) ? '1' : '0';
      scaled->stored_digits = UINT32_C(1);
      return 1;
    }
    keep = exact->digit_count - cut;
  }
  if (keep > scaled->digit_capacity) {
    return 0;
  }
  scaled->stored_digits = keep;
  while (index < keep) {
    scaled->digits[index] = exact->digits[index];
    ++index;
  }
  if (exact_rounds_up(exact, keep)) {
    index = keep;
    while (index != UINT32_C(0)) {
      --index;
      if (scaled->digits[index] != '9') {
        ++scaled->digits[index];
        trim_scaled_zeros(scaled);
        return 1;
      }
      scaled->digits[index] = '0';
    }
    scaled->digits[0] = '1';
    scaled->stored_digits = UINT32_C(1);
    scaled->zero_digits = keep;
    return 1;
  }
  trim_scaled_zeros(scaled);
  return 1;
}

static uint32_t scaled_length(const RoundedDecimal *scaled) {
  return scaled->stored_digits + scaled->zero_digits;
}

static int fixed_core_length(char sign, const RoundedDecimal *scaled,
                             uint32_t precision, int point, uint32_t *core) {
  const uint32_t digits = scaled_length(scaled);
  const uint32_t integer_digits =
      digits > precision ? digits - precision : UINT32_C(1);
  uint32_t total = sign == '\0' ? UINT32_C(0) : UINT32_C(1);

  if (!checked_add(total, integer_digits, &total) ||
      !checked_add(total, point != 0 ? UINT32_C(1) : UINT32_C(0), &total) ||
      !checked_add(total, precision, &total)) {
    return 0;
  }
  *core = total;
  return 1;
}

static void emit_scaled_range(DecimalWriter *writer,
                              const RoundedDecimal *scaled, uint32_t start,
                              uint32_t count) {
  uint32_t index = start;
  uint32_t end = start + count;

  while (index < end && index < scaled->stored_digits) {
    writer_character(writer, scaled->digits[index]);
    ++index;
  }
  if (index < end) {
    writer_repeat(writer, '0', end - index);
  }
}

static void emit_fixed(DecimalWriter *writer, const RoundedDecimal *scaled,
                       uint32_t precision, int point) {
  const uint32_t digits = scaled_length(scaled);
  uint32_t integer_digits = UINT32_C(0);

  if (digits > precision) {
    integer_digits = digits - precision;
    emit_scaled_range(writer, scaled, UINT32_C(0), integer_digits);
  } else {
    writer_character(writer, '0');
  }
  if (point != 0) {
    writer_character(writer, '.');
  }
  if (precision == UINT32_C(0)) {
    return;
  }
  if (digits < precision) {
    writer_repeat(writer, '0', precision - digits);
    emit_scaled_range(writer, scaled, UINT32_C(0), digits);
  } else {
    emit_scaled_range(writer, scaled, integer_digits, precision);
  }
}

static uint32_t general_significant_digits(
    const RoundedDecimal *rounded, uint32_t precision, int alternate) {
  uint32_t count = precision;

  if (alternate != 0) {
    return count;
  }
  if (count > rounded->stored_digits) {
    count = rounded->stored_digits;
  }
  while (count > UINT32_C(1) && rounded->digits[count - UINT32_C(1)] == '0') {
    --count;
  }
  return count;
}

static int general_scientific(int32_t exponent, uint32_t precision) {
  if (exponent < INT32_C(-4)) {
    return 1;
  }
  return precision <= (uint32_t)INT32_MAX && exponent >= (int32_t)precision;
}

static int general_fixed_geometry(char sign, int32_t exponent,
                                  uint32_t significant_digits, int alternate,
                                  uint32_t *fraction_digits, uint32_t *core) {
  uint32_t integer_digits = UINT32_C(1);
  uint32_t fraction = UINT32_C(0);
  uint32_t total = sign == '\0' ? UINT32_C(0) : UINT32_C(1);
  int point = alternate;

  if (exponent >= INT32_C(0)) {
    integer_digits = (uint32_t)exponent + UINT32_C(1);
    fraction = significant_digits > integer_digits
                   ? significant_digits - integer_digits
                   : UINT32_C(0);
  } else {
    const uint32_t leading_zeroes = (uint32_t)(-exponent - INT32_C(1));
    if (!checked_add(leading_zeroes, significant_digits, &fraction)) {
      return 0;
    }
  }
  if (fraction != UINT32_C(0)) {
    point = 1;
  }
  if (!checked_add(total, integer_digits, &total) ||
      !checked_add(total, point != 0 ? UINT32_C(1) : UINT32_C(0), &total) ||
      !checked_add(total, fraction, &total)) {
    return 0;
  }
  *fraction_digits = fraction;
  *core = total;
  return 1;
}

static void emit_general_fixed(DecimalWriter *writer,
                               const RoundedDecimal *rounded,
                               uint32_t significant_digits,
                               uint32_t fraction_digits, int point) {
  const int32_t exponent = rounded->exponent;

  if (exponent >= INT32_C(0)) {
    const uint32_t integer_digits = (uint32_t)exponent + UINT32_C(1);
    emit_scaled_range(writer, rounded, UINT32_C(0), integer_digits);
    if (point != 0) {
      writer_character(writer, '.');
    }
    if (fraction_digits != UINT32_C(0)) {
      emit_scaled_range(writer, rounded, integer_digits, fraction_digits);
    }
    return;
  }
  writer_character(writer, '0');
  if (point != 0) {
    writer_character(writer, '.');
  }
  writer_repeat(writer, '0', (uint32_t)(-exponent - INT32_C(1)));
  emit_scaled_range(writer, rounded, UINT32_C(0), significant_digits);
}

static MalbolgeGuestRuntimeStatus emit_special(
    MalbolgeGuestFormatSink *sink,
    const MalbolgeGuestResolvedFormatArgument *resolved, char sign,
    int uppercase, int nan) {
  DecimalWriter writer;
  const uint32_t core = sign == '\0' ? UINT32_C(3) : UINT32_C(4);
  const uint32_t width = field_width(&resolved->directive);
  const uint32_t total = width > core ? width : core;
  const uint32_t padding = total - core;
  const int left =
      (resolved->directive.flags & MALBOLGE_GUEST_FORMAT_LEFT) != UINT32_C(0);
  const char *text = nan == 0 ? (uppercase != 0 ? "INF" : "inf")
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

static MalbolgeGuestRuntimeStatus execute_finite_decimal(
    MalbolgeGuestFormatSink *sink,
    const MalbolgeGuestResolvedFormatArgument *resolved,
    const DecimalExactView *exact, RoundedDecimal *rounded, char sign,
    int uppercase) {
  DecimalWriter writer;
  uint32_t precision = effective_precision(&resolved->directive);
  uint32_t target = UINT32_C(0);
  uint32_t core = UINT32_C(0);
  uint32_t width = UINT32_C(0);
  uint32_t total = UINT32_C(0);
  uint32_t padding = UINT32_C(0);
  const int left =
      (resolved->directive.flags & MALBOLGE_GUEST_FORMAT_LEFT) != UINT32_C(0);
  int zero = 0;
  int point = 0;

  if (precision == UINT32_MAX) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  if (resolved->directive.conversion ==
          MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_GENERAL ||
      resolved->directive.conversion ==
          MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_GENERAL_UPPER) {
    uint32_t significant = UINT32_C(0);
    uint32_t fraction = UINT32_C(0);
    const int alternate =
        (resolved->directive.flags & MALBOLGE_GUEST_FORMAT_ALTERNATE) !=
        UINT32_C(0);
    int scientific = 0;

    precision = general_precision(&resolved->directive);
    if (precision == UINT32_MAX || !round_exact(exact, precision, rounded)) {
      return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
    }
    scientific = general_scientific(rounded->exponent, precision);
    significant = general_significant_digits(rounded, precision, alternate);
    if (scientific != 0) {
      fraction = significant - UINT32_C(1);
      point = alternate != 0 || fraction != UINT32_C(0);
      if (!finite_core_length(sign, fraction, point, rounded->exponent,
                              &core)) {
        return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
      }
    } else if (!general_fixed_geometry(sign, rounded->exponent, significant,
                                       alternate, &fraction, &core)) {
      return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
    } else {
      point = alternate != 0 || fraction != UINT32_C(0);
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
    if (scientific != 0) {
      emit_rounded(&writer, rounded, fraction, point, uppercase);
    } else {
      emit_general_fixed(&writer, rounded, significant, fraction, point);
    }
    if (left != 0) {
      writer_repeat(&writer, ' ', padding);
    }
    sink->required += total;
    return MALBOLGE_GUEST_RUNTIME_VALID;
  }
  if (resolved->directive.conversion ==
          MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_FIXED ||
      resolved->directive.conversion ==
          MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_FIXED_UPPER) {
    if (!quantize_fixed(exact, precision, rounded)) {
      return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
    }
    point = precision != UINT32_C(0) ||
            (resolved->directive.flags & MALBOLGE_GUEST_FORMAT_ALTERNATE) !=
                UINT32_C(0);
    if (!fixed_core_length(sign, rounded, precision, point, &core)) {
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
    emit_fixed(&writer, rounded, precision, point);
    if (left != 0) {
      writer_repeat(&writer, ' ', padding);
    }
    sink->required += total;
    return MALBOLGE_GUEST_RUNTIME_VALID;
  }
  target = precision + UINT32_C(1);
  if (!round_exact(exact, target, rounded)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  point = precision != UINT32_C(0) ||
          (resolved->directive.flags & MALBOLGE_GUEST_FORMAT_ALTERNATE) !=
              UINT32_C(0);
  if (!finite_core_length(sign, precision, point, rounded->exponent, &core)) {
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
  emit_rounded(&writer, rounded, precision, point, uppercase);
  if (left != 0) {
    writer_repeat(&writer, ' ', padding);
  }
  sink->required += total;
  return MALBOLGE_GUEST_RUNTIME_VALID;
}

MalbolgeGuestRuntimeStatus malbolge_guest_format_execute_decimal_float(
    MalbolgeGuestFormatSink *sink,
    const MalbolgeGuestResolvedFormatArgument *resolved) {
  const int uppercase =
      resolved != NULL &&
      (resolved->directive.conversion ==
           MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_EXP_UPPER ||
       resolved->directive.conversion ==
           MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_FIXED_UPPER ||
       resolved->directive.conversion ==
           MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_GENERAL_UPPER);

  if (sink == NULL || !resolved_decimal(resolved)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  if (resolved->argument_kind == MALBOLGE_GUEST_VARARG_F128) {
    MalbolgeGuestDecimalExact128 storage;
    char rounded_digits[11564];
    DecimalExactView exact;
    RoundedDecimal rounded = {rounded_digits,
                              MALBOLGE_GUEST_DECIMAL_BINARY128_DIGITS,
                              UINT32_C(0), UINT32_C(0), INT32_C(0)};
    const uint64_t high = resolved->argument.high;
    const uint32_t raw_exponent =
        (uint32_t)((high & B128_EXPONENT) >> B128_EXPONENT_SHIFT);
    const char sign = sign_character(high, resolved->directive.flags);

    if (raw_exponent == B128_EXPONENT_ALL_ONES) {
      const int nan = (high & B128_FRACTION_HIGH) != UINT64_C(0) ||
                      resolved->argument.low != UINT64_C(0);
      return emit_special(sink, resolved, sign, uppercase, nan);
    }
    if (malbolge_guest_decimal_from_binary128(resolved->argument.low, high,
                                               &storage) !=
        MALBOLGE_GUEST_RUNTIME_VALID) {
      return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
    }
    exact.digits = storage.digits;
    exact.digit_count = storage.digit_count;
    exact.decimal_shift = storage.decimal_shift;
    return execute_finite_decimal(sink, resolved, &exact, &rounded, sign,
                                  uppercase);
  }
  {
    MalbolgeGuestDecimalExact storage;
    char rounded_digits[768];
    DecimalExactView exact;
    RoundedDecimal rounded = {rounded_digits,
                              MALBOLGE_GUEST_DECIMAL_BINARY64_DIGITS,
                              UINT32_C(0), UINT32_C(0), INT32_C(0)};
    const uint64_t bits = resolved->argument.low;
    const uint32_t raw_exponent =
        (uint32_t)((bits & B64_EXPONENT) >> B64_EXPONENT_SHIFT);
    const char sign = sign_character(bits, resolved->directive.flags);

    if (raw_exponent == B64_EXPONENT_ALL_ONES) {
      const int nan = (bits & B64_FRACTION) != UINT64_C(0);
      return emit_special(sink, resolved, sign, uppercase, nan);
    }
    if (malbolge_guest_decimal_from_binary64(bits, &storage) !=
        MALBOLGE_GUEST_RUNTIME_VALID) {
      return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
    }
    exact.digits = storage.digits;
    exact.digit_count = storage.digit_count;
    exact.decimal_shift = storage.decimal_shift;
    return execute_finite_decimal(sink, resolved, &exact, &rounded, sign,
                                  uppercase);
  }
}
