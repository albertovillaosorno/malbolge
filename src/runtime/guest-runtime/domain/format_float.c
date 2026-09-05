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
//   - Bit-exact binary64 %a/%A conversion and bounded sink publication.
// - Must-Not:
//   - Execute host floating operations, call host printf, or consume va_list.
// - Allows:
//   - Inputs: resolved F64 bits, flags, width, and precision.
//   - Outputs: deterministic hexadecimal floating text and required byte count.
//   - Side effects: bounded sink writes only after total length is admissible.
// - Split-When:
//   - Decimal or binary128 formatting requires a separate conversion algorithm.
// - Merge-When:
//   - Full guest formatting directly owns these exact binary64 semantics.
// - Summary:
//   - Formats finite/special binary64 values using integer representation only.
// - Description:
//   - Normalizes nonzero finite values and rounds discarded bits ties-to-even.
// - Usage:
//   - Runs after format argument resolution publishes canonical F64 raw bits.
// - Defaults:
//   - Missing precision removes trailing exact hex zeros; # still forces point.
//

//! Binary64 hexadecimal printf conversion without host floating authority.

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

typedef struct HexFloatParts {
  char sign;
  char leading;
  char fraction[13];
  uint32_t fraction_digits;
  uint32_t zero_digits;
  char exponent[5];
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

static int resolved_f64(const MalbolgeGuestResolvedFormatArgument *resolved) {
  uint32_t kind = MALBOLGE_GUEST_VARARG_NONE;

  if (resolved == NULL || resolved->argument.high != UINT64_C(0) ||
      resolved->argument_kind != MALBOLGE_GUEST_VARARG_F64 ||
      resolved->directive.width_kind ==
          MALBOLGE_GUEST_FORMAT_FIELD_ARGUMENT ||
      resolved->directive.precision_kind ==
          MALBOLGE_GUEST_FORMAT_FIELD_ARGUMENT ||
      (resolved->directive.conversion !=
           MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_HEX &&
       resolved->directive.conversion !=
           MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_HEX_UPPER) ||
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

static uint32_t raw_exponent(uint64_t bits) {
  return (uint32_t)((bits & B64_EXPONENT) >> B64_EXPONENT_SHIFT);
}

static uint64_t normalize_significand(uint64_t bits, int32_t *exponent) {
  const uint32_t raw = raw_exponent(bits);
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

static uint64_t round_significand(uint64_t significand, uint32_t precision) {
  const uint32_t retained = precision * UINT32_C(4);
  const uint32_t discarded = B64_EXPONENT_SHIFT - retained;
  const uint64_t truncated = significand >> discarded;
  const uint64_t mask = (UINT64_C(1) << discarded) - UINT64_C(1);
  const uint64_t remainder = significand & mask;
  const uint64_t halfway = UINT64_C(1) << (discarded - UINT32_C(1));

  if (remainder > halfway ||
      (remainder == halfway && (truncated & UINT64_C(1)) != UINT64_C(0))) {
    return truncated + UINT64_C(1);
  }
  return truncated;
}

static char hex_digit(uint32_t value, int uppercase) {
  const char *alphabet = uppercase != 0 ? "0123456789ABCDEF"
                                        : "0123456789abcdef";
  return alphabet[value & UINT32_C(15)];
}

static void build_fraction(HexFloatParts *parts, uint64_t fraction,
                           uint32_t digits, int uppercase) {
  uint32_t index = UINT32_C(0);

  while (index < digits) {
    const uint32_t shift =
        (B64_HEX_FRACTION_DIGITS - index - UINT32_C(1)) * UINT32_C(4);
    parts->fraction[index] =
        hex_digit((uint32_t)(fraction >> shift), uppercase);
    ++index;
  }
  parts->fraction_digits = digits;
}

static void trim_default_fraction(HexFloatParts *parts) {
  while (parts->fraction_digits != UINT32_C(0) &&
         parts->fraction[parts->fraction_digits - UINT32_C(1)] == '0') {
    --parts->fraction_digits;
  }
}

static void exponent_text(HexFloatParts *parts, int32_t exponent) {
  uint32_t magnitude = UINT32_C(0);
  char reversed[4];
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

static void build_zero(HexFloatParts *parts, uint32_t precision_kind,
                       uint32_t precision) {
  parts->leading = '0';
  parts->fraction_digits = UINT32_C(0);
  parts->zero_digits = precision_kind == MALBOLGE_GUEST_FORMAT_FIELD_LITERAL
                           ? precision
                           : UINT32_C(0);
  exponent_text(parts, INT32_C(0));
}

static void build_finite(HexFloatParts *parts, uint64_t bits,
                         uint32_t precision_kind, uint32_t precision,
                         int uppercase) {
  uint64_t significand = UINT64_C(0);
  uint64_t fraction = UINT64_C(0);
  int32_t exponent = INT32_C(0);

  if ((bits & ~B64_SIGN) == UINT64_C(0)) {
    build_zero(parts, precision_kind, precision);
    return;
  }
  significand = normalize_significand(bits, &exponent);
  if (precision_kind != MALBOLGE_GUEST_FORMAT_FIELD_LITERAL) {
    parts->leading = '1';
    fraction = significand & B64_FRACTION;
    build_fraction(parts, fraction, B64_HEX_FRACTION_DIGITS, uppercase);
    trim_default_fraction(parts);
    parts->zero_digits = UINT32_C(0);
  } else if (precision >= B64_HEX_FRACTION_DIGITS) {
    parts->leading = '1';
    fraction = significand & B64_FRACTION;
    build_fraction(parts, fraction, B64_HEX_FRACTION_DIGITS, uppercase);
    parts->zero_digits = precision - B64_HEX_FRACTION_DIGITS;
  } else {
    const uint64_t rounded = round_significand(significand, precision);
    parts->leading = hex_digit(
        (uint32_t)(rounded >> (precision * UINT32_C(4))), uppercase);
    fraction = precision == UINT32_C(0)
                   ? UINT64_C(0)
                   : (rounded & ((UINT64_C(1) << (precision * UINT32_C(4))) -
                                 UINT64_C(1)))
                         << (B64_EXPONENT_SHIFT - precision * UINT32_C(4));
    build_fraction(parts, fraction, precision, uppercase);
    parts->zero_digits = UINT32_C(0);
  }
  exponent_text(parts, exponent);
}

static void build_parts(HexFloatParts *parts, uint64_t bits,
                        const MalbolgeGuestFormatDirective *directive) {
  const uint32_t exponent = raw_exponent(bits);
  const int uppercase = directive->conversion ==
                        MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_HEX_UPPER;

  parts->sign = sign_character(bits, directive->flags);
  parts->leading = '\0';
  parts->fraction_digits = UINT32_C(0);
  parts->zero_digits = UINT32_C(0);
  parts->exponent_digits = UINT32_C(0);
  parts->special = 0;
  parts->special_text = NULL;
  if (exponent == B64_EXPONENT_ALL_ONES) {
    parts->special = 1;
    parts->special_text = (bits & B64_FRACTION) == UINT64_C(0)
                              ? (uppercase != 0 ? "INF" : "inf")
                              : (uppercase != 0 ? "NAN" : "nan");
    return;
  }
  build_finite(parts, bits, directive->precision_kind, directive->precision,
               uppercase);
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
  uint32_t position = writer->sink->required + writer->logical;
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

  if (sink == NULL || !resolved_f64(resolved)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  build_parts(&parts, resolved->argument.low, &resolved->directive);
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
