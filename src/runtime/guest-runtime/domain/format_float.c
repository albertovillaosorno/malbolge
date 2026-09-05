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
//   - Bit-exact binary64/binary128 %a/%A conversion and bounded publication.
// - Must-Not:
//   - Execute host floating operations, call host printf, or consume va_list.
// - Allows:
//   - Inputs: resolved F64/F128 bits, flags, width, and precision.
//   - Outputs: deterministic hexadecimal floating text and required byte count.
//   - Side effects: bounded sink writes only after total length is admissible.
// - Split-When:
//   - Decimal floating formatting requires a separate conversion algorithm.
// - Merge-When:
//   - Full guest formatting directly owns these exact binary semantics.
// - Summary:
//   - Formats finite/special binary floats using integer representation only.
// - Description:
//   - Normalizes finite values and rounds discarded nibbles ties-to-even.
// - Usage:
//   - Runs after format argument resolution publishes canonical raw float bits.
// - Defaults:
//   - Missing precision removes trailing exact hex zeros; # still forces point.
//

//! Binary hexadecimal printf conversion without host floating authority.

#include "guest_format_float.h"

#include <limits.h>
#include <stddef.h>
#include <stdint.h>

#define B64_SIGN UINT64_C(0x8000000000000000)
#define B64_EXPONENT UINT64_C(0x7ff0000000000000)
#define B64_FRACTION UINT64_C(0x000fffffffffffff)
#define B64_HIDDEN UINT64_C(0x0010000000000000)
#define B64_EXPONENT_SHIFT UINT32_C(52)
#define B64_EXPONENT_BIAS INT32_C(1023)
#define B64_MIN_NORMAL_EXPONENT INT32_C(-1022)
#define B64_HEX_FRACTION_DIGITS UINT32_C(13)
#define B64_EXPONENT_ALL_ONES UINT32_C(0x7ff)

#define B128_SIGN UINT64_C(0x8000000000000000)
#define B128_EXPONENT UINT64_C(0x7fff000000000000)
#define B128_FRACTION_HIGH UINT64_C(0x0000ffffffffffff)
#define B128_HIDDEN_HIGH UINT64_C(0x0001000000000000)
#define B128_EXPONENT_SHIFT UINT32_C(48)
#define B128_EXPONENT_BIAS INT32_C(16383)
#define B128_MIN_NORMAL_EXPONENT INT32_C(-16382)
#define B128_HEX_FRACTION_DIGITS UINT32_C(28)
#define B128_EXPONENT_ALL_ONES UINT32_C(0x7fff)

#define MAX_HEX_FRACTION_DIGITS UINT32_C(28)

typedef struct HexFloatParts {
  char sign;
  char leading;
  char fraction[28];
  uint32_t fraction_digits;
  uint32_t zero_digits;
  char exponent[6];
  uint32_t exponent_digits;
  int special;
  const char *special_text;
} HexFloatParts;

typedef struct FloatWriter {
  MalbolgeGuestFormatSink *sink;
  uint32_t logical;
} FloatWriter;

static int checked_add(uint32_t left, uint32_t right, uint32_t *result) {
  if (result == NULL || right > UINT32_MAX - left) {
    return 0;
  }
  *result = left + right;
  return 1;
}

static int resolved_float(const MalbolgeGuestResolvedFormatArgument *resolved) {
  uint32_t kind = MALBOLGE_GUEST_VARARG_NONE;

  if (resolved == NULL ||
      resolved->directive.width_kind ==
          MALBOLGE_GUEST_FORMAT_FIELD_ARGUMENT ||
      resolved->directive.precision_kind ==
          MALBOLGE_GUEST_FORMAT_FIELD_ARGUMENT ||
      (resolved->directive.conversion !=
           MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_HEX &&
       resolved->directive.conversion !=
           MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_HEX_UPPER) ||
      malbolge_guest_format_argument_kind(&resolved->directive, &kind) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      kind != resolved->argument_kind) {
    return 0;
  }
  if (kind == MALBOLGE_GUEST_VARARG_F64) {
    return resolved->argument.high == UINT64_C(0);
  }
  return kind == MALBOLGE_GUEST_VARARG_F128;
}

static char sign_character(int negative, uint32_t flags) {
  if (negative != 0) {
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

static char hex_digit(uint32_t value, int uppercase) {
  const char *alphabet = uppercase != 0 ? "0123456789ABCDEF"
                                        : "0123456789abcdef";
  return alphabet[value & UINT32_C(15)];
}

static void exponent_text(HexFloatParts *parts, int32_t exponent) {
  uint32_t magnitude = UINT32_C(0);
  char reversed[5];
  uint32_t count = UINT32_C(0);
  uint32_t index = UINT32_C(0);

  parts->exponent[0] = exponent < INT32_C(0) ? '-' : '+';
  magnitude = exponent < INT32_C(0) ? (uint32_t)(-exponent)
                                    : (uint32_t)exponent;
  do {
    reversed[count] = (char)('0' + (char)(magnitude % UINT32_C(10)));
    magnitude /= UINT32_C(10);
    ++count;
  } while (magnitude != UINT32_C(0));
  while (index < count) {
    parts->exponent[index + UINT32_C(1)] =
        reversed[count - index - UINT32_C(1)];
    ++index;
  }
  parts->exponent_digits = count + UINT32_C(1);
}

static void trim_default_fraction(HexFloatParts *parts) {
  while (parts->fraction_digits != UINT32_C(0) &&
         parts->fraction[parts->fraction_digits - UINT32_C(1)] == '0') {
    --parts->fraction_digits;
  }
}

static int discarded_rounds_up(const uint8_t digits[28], uint32_t precision,
                               uint32_t exact_digits) {
  const uint8_t first = digits[precision];
  uint32_t index = precision + UINT32_C(1);
  uint8_t retained = UINT8_C(1);

  if (first > UINT8_C(8)) {
    return 1;
  }
  if (first < UINT8_C(8)) {
    return 0;
  }
  while (index < exact_digits) {
    if (digits[index] != UINT8_C(0)) {
      return 1;
    }
    ++index;
  }
  if (precision != UINT32_C(0)) {
    retained = digits[precision - UINT32_C(1)];
  }
  return (retained & UINT8_C(1)) != UINT8_C(0);
}

static uint32_t round_fraction(uint8_t digits[28], uint32_t precision,
                               uint32_t exact_digits) {
  uint32_t leading = UINT32_C(1);
  uint32_t index = precision;

  if (!discarded_rounds_up(digits, precision, exact_digits)) {
    return leading;
  }
  while (index != UINT32_C(0)) {
    --index;
    if (digits[index] != UINT8_C(15)) {
      ++digits[index];
      return leading;
    }
    digits[index] = UINT8_C(0);
  }
  ++leading;
  return leading;
}

static void build_fraction_parts(HexFloatParts *parts, uint8_t digits[28],
                                 uint32_t exact_digits,
                                 uint32_t precision_kind, uint32_t precision,
                                 int uppercase) {
  uint32_t output_digits = exact_digits;
  uint32_t leading = UINT32_C(1);
  uint32_t index = UINT32_C(0);

  parts->zero_digits = UINT32_C(0);
  if (precision_kind == MALBOLGE_GUEST_FORMAT_FIELD_LITERAL) {
    output_digits = precision < exact_digits ? precision : exact_digits;
    if (precision < exact_digits) {
      leading = round_fraction(digits, precision, exact_digits);
    } else {
      parts->zero_digits = precision - exact_digits;
    }
  }
  parts->leading = hex_digit(leading, uppercase);
  while (index < output_digits) {
    parts->fraction[index] = hex_digit((uint32_t)digits[index], uppercase);
    ++index;
  }
  parts->fraction_digits = output_digits;
  if (precision_kind != MALBOLGE_GUEST_FORMAT_FIELD_LITERAL) {
    trim_default_fraction(parts);
  }
}

static void build_zero(HexFloatParts *parts, uint32_t precision_kind,
                       uint32_t precision) {
  parts->leading = '0';
  parts->fraction_digits = UINT32_C(0);
  parts->zero_digits = precision_kind == MALBOLGE_GUEST_FORMAT_FIELD_LITERAL
                           ? precision
                           : UINT32_C(0);
  exponent_text(parts, INT32_C(0));
}

static void b64_fraction_digits(uint64_t significand, uint8_t digits[28]) {
  const uint64_t fraction = significand & B64_FRACTION;
  uint32_t index = UINT32_C(0);

  while (index < B64_HEX_FRACTION_DIGITS) {
    const uint32_t shift =
        (B64_HEX_FRACTION_DIGITS - index - UINT32_C(1)) * UINT32_C(4);
    digits[index] = (uint8_t)((fraction >> shift) & UINT64_C(15));
    ++index;
  }
}

static uint64_t b64_normalize(uint64_t bits, int32_t *exponent) {
  const uint32_t raw =
      (uint32_t)((bits & B64_EXPONENT) >> B64_EXPONENT_SHIFT);
  uint64_t significand = bits & B64_FRACTION;

  if (raw != UINT32_C(0)) {
    *exponent = (int32_t)raw - B64_EXPONENT_BIAS;
    return significand | B64_HIDDEN;
  }
  *exponent = B64_MIN_NORMAL_EXPONENT;
  while ((significand & B64_HIDDEN) == UINT64_C(0)) {
    significand <<= UINT32_C(1);
    --(*exponent);
  }
  return significand;
}

static void build_f64_finite(HexFloatParts *parts, uint64_t bits,
                             const MalbolgeGuestFormatDirective *directive,
                             int uppercase) {
  uint8_t digits[28] = {0};
  uint64_t significand = UINT64_C(0);
  int32_t exponent = INT32_C(0);

  if ((bits & ~B64_SIGN) == UINT64_C(0)) {
    build_zero(parts, directive->precision_kind, directive->precision);
    return;
  }
  significand = b64_normalize(bits, &exponent);
  b64_fraction_digits(significand, digits);
  build_fraction_parts(parts, digits, B64_HEX_FRACTION_DIGITS,
                       directive->precision_kind, directive->precision,
                       uppercase);
  exponent_text(parts, exponent);
}

static void b128_normalize(uint64_t *high, uint64_t *low, int32_t *exponent) {
  const uint32_t raw =
      (uint32_t)((*high & B128_EXPONENT) >> B128_EXPONENT_SHIFT);

  *high &= B128_FRACTION_HIGH;
  if (raw != UINT32_C(0)) {
    *exponent = (int32_t)raw - B128_EXPONENT_BIAS;
    *high |= B128_HIDDEN_HIGH;
    return;
  }
  *exponent = B128_MIN_NORMAL_EXPONENT;
  while ((*high & B128_HIDDEN_HIGH) == UINT64_C(0)) {
    *high = (*high << UINT32_C(1)) | (*low >> UINT32_C(63));
    *low <<= UINT32_C(1);
    --(*exponent);
  }
}

static void b128_fraction_digits(uint64_t high, uint64_t low,
                                 uint8_t digits[28]) {
  uint32_t index = UINT32_C(0);
  const uint64_t fraction_high = high & B128_FRACTION_HIGH;

  while (index < UINT32_C(12)) {
    const uint32_t shift = (UINT32_C(11) - index) * UINT32_C(4);
    digits[index] = (uint8_t)((fraction_high >> shift) & UINT64_C(15));
    ++index;
  }
  while (index < B128_HEX_FRACTION_DIGITS) {
    const uint32_t low_index = index - UINT32_C(12);
    const uint32_t shift = (UINT32_C(15) - low_index) * UINT32_C(4);
    digits[index] = (uint8_t)((low >> shift) & UINT64_C(15));
    ++index;
  }
}

static void build_f128_finite(HexFloatParts *parts, uint64_t high, uint64_t low,
                              const MalbolgeGuestFormatDirective *directive,
                              int uppercase) {
  uint8_t digits[28] = {0};
  int32_t exponent = INT32_C(0);

  if ((high & ~B128_SIGN) == UINT64_C(0) && low == UINT64_C(0)) {
    build_zero(parts, directive->precision_kind, directive->precision);
    return;
  }
  b128_normalize(&high, &low, &exponent);
  b128_fraction_digits(high, low, digits);
  build_fraction_parts(parts, digits, B128_HEX_FRACTION_DIGITS,
                       directive->precision_kind, directive->precision,
                       uppercase);
  exponent_text(parts, exponent);
}

static void initialize_parts(HexFloatParts *parts, int negative,
                             uint32_t flags) {
  parts->sign = sign_character(negative, flags);
  parts->leading = '\0';
  parts->fraction_digits = UINT32_C(0);
  parts->zero_digits = UINT32_C(0);
  parts->exponent_digits = UINT32_C(0);
  parts->special = 0;
  parts->special_text = NULL;
}

static void build_f64_parts(HexFloatParts *parts, uint64_t bits,
                            const MalbolgeGuestFormatDirective *directive,
                            int uppercase) {
  const uint32_t exponent =
      (uint32_t)((bits & B64_EXPONENT) >> B64_EXPONENT_SHIFT);

  initialize_parts(parts, (bits & B64_SIGN) != UINT64_C(0), directive->flags);
  if (exponent == B64_EXPONENT_ALL_ONES) {
    parts->special = 1;
    parts->special_text = (bits & B64_FRACTION) == UINT64_C(0)
                              ? (uppercase != 0 ? "INF" : "inf")
                              : (uppercase != 0 ? "NAN" : "nan");
    return;
  }
  build_f64_finite(parts, bits, directive, uppercase);
}

static void build_f128_parts(HexFloatParts *parts, uint64_t high, uint64_t low,
                             const MalbolgeGuestFormatDirective *directive,
                             int uppercase) {
  const uint32_t exponent =
      (uint32_t)((high & B128_EXPONENT) >> B128_EXPONENT_SHIFT);
  const int fraction =
      (high & B128_FRACTION_HIGH) != UINT64_C(0) || low != UINT64_C(0);

  initialize_parts(parts, (high & B128_SIGN) != UINT64_C(0), directive->flags);
  if (exponent == B128_EXPONENT_ALL_ONES) {
    parts->special = 1;
    parts->special_text = fraction == 0 ? (uppercase != 0 ? "INF" : "inf")
                                        : (uppercase != 0 ? "NAN" : "nan");
    return;
  }
  build_f128_finite(parts, high, low, directive, uppercase);
}

static void build_parts(HexFloatParts *parts,
                        const MalbolgeGuestResolvedFormatArgument *resolved) {
  const int uppercase = resolved->directive.conversion ==
                        MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_HEX_UPPER;

  if (resolved->argument_kind == MALBOLGE_GUEST_VARARG_F128) {
    build_f128_parts(parts, resolved->argument.high, resolved->argument.low,
                     &resolved->directive, uppercase);
  } else {
    build_f64_parts(parts, resolved->argument.low, &resolved->directive,
                    uppercase);
  }
}

static int core_length(const HexFloatParts *parts,
                       const MalbolgeGuestFormatDirective *directive,
                       uint32_t *length) {
  uint32_t total = parts->sign == '\0' ? UINT32_C(0) : UINT32_C(1);
  uint32_t fraction_total = UINT32_C(0);
  const int point =
      (directive->flags & MALBOLGE_GUEST_FORMAT_ALTERNATE) != UINT32_C(0) ||
      parts->fraction_digits != UINT32_C(0) ||
      parts->zero_digits != UINT32_C(0);

  if (parts->special != 0) {
    if (!checked_add(total, UINT32_C(3), &total)) {
      return 0;
    }
    *length = total;
    return 1;
  }
  if (!checked_add(parts->fraction_digits, parts->zero_digits,
                   &fraction_total) ||
      !checked_add(total, UINT32_C(3), &total) ||
      !checked_add(total, point != 0 ? UINT32_C(1) : UINT32_C(0), &total) ||
      !checked_add(total, fraction_total, &total) ||
      !checked_add(total, UINT32_C(1), &total) ||
      !checked_add(total, parts->exponent_digits, &total)) {
    return 0;
  }
  *length = total;
  return 1;
}

static uint32_t field_width(const MalbolgeGuestFormatDirective *directive) {
  return directive->width_kind == MALBOLGE_GUEST_FORMAT_FIELD_LITERAL
             ? directive->width
             : UINT32_C(0);
}

static int writer_init(FloatWriter *writer, MalbolgeGuestFormatSink *sink,
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

static void writer_character(FloatWriter *writer, char value) {
  const uint32_t position = writer->sink->required + writer->logical;

  if (writer->sink->capacity > UINT32_C(1) &&
      position < writer->sink->capacity - UINT32_C(1)) {
    writer->sink->destination[position] = value;
  }
  ++writer->logical;
}

static void writer_repeat(FloatWriter *writer, char value, uint32_t count) {
  uint32_t writable = count;
  const uint32_t position = writer->sink->required + writer->logical;
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

static void writer_bytes(FloatWriter *writer, const char *text,
                         uint32_t count) {
  uint32_t index = UINT32_C(0);
  while (index < count) {
    writer_character(writer, text[index]);
    ++index;
  }
}

static void emit_finite(FloatWriter *writer, const HexFloatParts *parts,
                        const MalbolgeGuestFormatDirective *directive,
                        uint32_t zero_padding) {
  const int uppercase = directive->conversion ==
                        MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_HEX_UPPER;
  const int point =
      (directive->flags & MALBOLGE_GUEST_FORMAT_ALTERNATE) != UINT32_C(0) ||
      parts->fraction_digits != UINT32_C(0) ||
      parts->zero_digits != UINT32_C(0);

  if (parts->sign != '\0') {
    writer_character(writer, parts->sign);
  }
  writer_character(writer, '0');
  writer_character(writer, uppercase != 0 ? 'X' : 'x');
  writer_repeat(writer, '0', zero_padding);
  writer_character(writer, parts->leading);
  if (point != 0) {
    writer_character(writer, '.');
  }
  writer_bytes(writer, parts->fraction, parts->fraction_digits);
  writer_repeat(writer, '0', parts->zero_digits);
  writer_character(writer, uppercase != 0 ? 'P' : 'p');
  writer_bytes(writer, parts->exponent, parts->exponent_digits);
}

static void emit_special(FloatWriter *writer, const HexFloatParts *parts) {
  if (parts->sign != '\0') {
    writer_character(writer, parts->sign);
  }
  writer_bytes(writer, parts->special_text, UINT32_C(3));
}

MalbolgeGuestRuntimeStatus malbolge_guest_format_execute_hex_float(
    MalbolgeGuestFormatSink *sink,
    const MalbolgeGuestResolvedFormatArgument *resolved) {
  HexFloatParts parts;
  FloatWriter writer;
  uint32_t core = UINT32_C(0);
  uint32_t width = UINT32_C(0);
  uint32_t padding = UINT32_C(0);
  uint32_t total = UINT32_C(0);
  uint32_t zero_padding = UINT32_C(0);
  const int left = resolved != NULL &&
                   (resolved->directive.flags & MALBOLGE_GUEST_FORMAT_LEFT) !=
                       UINT32_C(0);
  int zero = 0;

  if (sink == NULL || !resolved_float(resolved)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  build_parts(&parts, resolved);
  if (!core_length(&parts, &resolved->directive, &core)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  width = field_width(&resolved->directive);
  total = width > core ? width : core;
  padding = width > core ? width - core : UINT32_C(0);
  zero = parts.special == 0 && left == 0 &&
         (resolved->directive.flags & MALBOLGE_GUEST_FORMAT_ZERO) !=
             UINT32_C(0);
  zero_padding = zero != 0 ? padding : UINT32_C(0);
  if (!writer_init(&writer, sink, total)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  if (left == 0 && zero == 0) {
    writer_repeat(&writer, ' ', padding);
  }
  if (parts.special != 0) {
    emit_special(&writer, &parts);
  } else {
    emit_finite(&writer, &parts, &resolved->directive, zero_padding);
  }
  if (left != 0) {
    writer_repeat(&writer, ' ', padding);
  }
  sink->required += total;
  return MALBOLGE_GUEST_RUNTIME_VALID;
}
