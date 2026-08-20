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
//   - Independent vectors for deterministic guest C23 format tokenization.
// - Must-Not:
//   - Consume va_list, call host printf parsing, or use host formatter output.
// - Allows:
//   - Inputs: fixed literal, directive, dynamic-field, and malformed formats.
//   - Outputs: zero only when stable token fields and rejection behavior match.
//   - Side effects: test-local token values only.
// - Split-When:
//   - Variadic decoding or conversion execution gains independent conformance.
// - Merge-When:
//   - Public formatting conformance owns these grammar vectors directly.
// - Summary:
//   - Locks literals, directives, lengths, fields, and fail-closed parsing.
// - Description:
//   - Includes binary conversions plus specific-width wN/wfN modifiers.
// - Usage:
//   - Built and executed by tests/test_guest_runtime_c.py.
// - Defaults:
//   - Invalid formats do not partially publish a replacement token.
//

//! Independent execution vectors for guest printf-format tokenization.

#include "guest_format_parse.h"

#include <stddef.h>
#include <stdint.h>

static int conversion(const char *format, uint32_t expected_length,
                      uint32_t expected_conversion,
                      uint32_t expected_length_tag,
                      uint32_t expected_length_bits) {
  MalbolgeGuestFormatToken token;
  return malbolge_guest_format_parse_next(format, UINT32_C(0), &token) ==
             MALBOLGE_GUEST_RUNTIME_VALID &&
         token.kind == MALBOLGE_GUEST_FORMAT_TOKEN_CONVERSION &&
         token.length == expected_length &&
         token.next_offset == expected_length &&
         token.directive.conversion == expected_conversion &&
         token.directive.length == expected_length_tag &&
         token.directive.length_bits == expected_length_bits;
}

static int test_stream(void) {
  const char format[] = "left %% right";
  MalbolgeGuestFormatToken token;

  if (malbolge_guest_format_parse_next(format, UINT32_C(0), &token) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      token.kind != MALBOLGE_GUEST_FORMAT_TOKEN_LITERAL ||
      token.length != UINT32_C(5) || token.next_offset != UINT32_C(5)) {
    return 1;
  }
  if (malbolge_guest_format_parse_next(format, token.next_offset, &token) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      token.kind != MALBOLGE_GUEST_FORMAT_TOKEN_CONVERSION ||
      token.directive.conversion != MALBOLGE_GUEST_FORMAT_CONVERSION_PERCENT ||
      token.length != UINT32_C(2) || token.next_offset != UINT32_C(7)) {
    return 2;
  }
  if (malbolge_guest_format_parse_next(format, token.next_offset, &token) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      token.kind != MALBOLGE_GUEST_FORMAT_TOKEN_LITERAL ||
      token.length != UINT32_C(6) || token.next_offset != UINT32_C(13)) {
    return 3;
  }
  if (malbolge_guest_format_parse_next(format, token.next_offset, &token) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      token.kind != MALBOLGE_GUEST_FORMAT_TOKEN_END ||
      token.next_offset != UINT32_C(13)) {
    return 4;
  }
  return 0;
}

static int test_fields(void) {
  MalbolgeGuestFormatToken token;

  if (malbolge_guest_format_parse_next("%+08.3lld", UINT32_C(0), &token) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      token.length != UINT32_C(9) ||
      token.directive.flags !=
          (MALBOLGE_GUEST_FORMAT_PLUS | MALBOLGE_GUEST_FORMAT_ZERO) ||
      token.directive.width_kind != MALBOLGE_GUEST_FORMAT_FIELD_LITERAL ||
      token.directive.width != UINT32_C(8) ||
      token.directive.precision_kind != MALBOLGE_GUEST_FORMAT_FIELD_LITERAL ||
      token.directive.precision != UINT32_C(3) ||
      token.directive.length != MALBOLGE_GUEST_FORMAT_LENGTH_LL ||
      token.directive.conversion != MALBOLGE_GUEST_FORMAT_CONVERSION_DECIMAL) {
    return 1;
  }
  if (malbolge_guest_format_parse_next("%#*.*w32b", UINT32_C(0), &token) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      token.directive.flags != MALBOLGE_GUEST_FORMAT_ALTERNATE ||
      token.directive.width_kind != MALBOLGE_GUEST_FORMAT_FIELD_ARGUMENT ||
      token.directive.precision_kind != MALBOLGE_GUEST_FORMAT_FIELD_ARGUMENT ||
      token.directive.length != MALBOLGE_GUEST_FORMAT_LENGTH_WIDTH ||
      token.directive.length_bits != UINT32_C(32) ||
      token.directive.conversion != MALBOLGE_GUEST_FORMAT_CONVERSION_BINARY) {
    return 2;
  }
  if (!conversion("%wf64X", UINT32_C(6),
                  MALBOLGE_GUEST_FORMAT_CONVERSION_HEX_UPPER,
                  MALBOLGE_GUEST_FORMAT_LENGTH_FAST_WIDTH, UINT32_C(64))) {
    return 3;
  }
  if (malbolge_guest_format_parse_next("%.s", UINT32_C(0), &token) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      token.directive.precision_kind != MALBOLGE_GUEST_FORMAT_FIELD_LITERAL ||
      token.directive.precision != UINT32_C(0) ||
      token.directive.conversion != MALBOLGE_GUEST_FORMAT_CONVERSION_STRING) {
    return 4;
  }
  return 0;
}

static int test_lengths(void) {
  static const char *const formats[] = {"%hhd", "%hd", "%ld", "%lld",
                                        "%jd",  "%zu", "%td", "%Lf"};
  static const uint32_t tags[] = {
      MALBOLGE_GUEST_FORMAT_LENGTH_HH, MALBOLGE_GUEST_FORMAT_LENGTH_H,
      MALBOLGE_GUEST_FORMAT_LENGTH_L,  MALBOLGE_GUEST_FORMAT_LENGTH_LL,
      MALBOLGE_GUEST_FORMAT_LENGTH_J,  MALBOLGE_GUEST_FORMAT_LENGTH_Z,
      MALBOLGE_GUEST_FORMAT_LENGTH_T,  MALBOLGE_GUEST_FORMAT_LENGTH_LONG_DOUBLE,
  };
  uint32_t index = UINT32_C(0);

  while (index < (uint32_t)(sizeof(formats) / sizeof(formats[0]))) {
    MalbolgeGuestFormatToken token;
    if (malbolge_guest_format_parse_next(formats[index], UINT32_C(0), &token) !=
            MALBOLGE_GUEST_RUNTIME_VALID ||
        token.directive.length != tags[index]) {
      return (int)(index + UINT32_C(1));
    }
    ++index;
  }
  return 0;
}

static int test_conversion_tags(void) {
  static const char *const formats[] = {"%b", "%B", "%a", "%A", "%e",
                                        "%E", "%f", "%F", "%g", "%G",
                                        "%c", "%s", "%p", "%n"};
  static const uint32_t tags[] = {
      MALBOLGE_GUEST_FORMAT_CONVERSION_BINARY,
      MALBOLGE_GUEST_FORMAT_CONVERSION_BINARY_UPPER,
      MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_HEX,
      MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_HEX_UPPER,
      MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_EXP,
      MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_EXP_UPPER,
      MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_FIXED,
      MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_FIXED_UPPER,
      MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_GENERAL,
      MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_GENERAL_UPPER,
      MALBOLGE_GUEST_FORMAT_CONVERSION_CHARACTER,
      MALBOLGE_GUEST_FORMAT_CONVERSION_STRING,
      MALBOLGE_GUEST_FORMAT_CONVERSION_POINTER,
      MALBOLGE_GUEST_FORMAT_CONVERSION_COUNT,
  };
  uint32_t index = UINT32_C(0);

  while (index < (uint32_t)(sizeof(formats) / sizeof(formats[0]))) {
    MalbolgeGuestFormatToken token;
    if (malbolge_guest_format_parse_next(formats[index], UINT32_C(0), &token) !=
            MALBOLGE_GUEST_RUNTIME_VALID ||
        token.directive.conversion != tags[index]) {
      return (int)(index + UINT32_C(1));
    }
    ++index;
  }
  return 0;
}

static int reject_offset_unchanged(const char *format, uint32_t offset) {
  MalbolgeGuestFormatToken token;

  token.kind = UINT32_C(91);
  token.offset = UINT32_C(92);
  token.length = UINT32_C(93);
  token.next_offset = UINT32_C(94);
  token.directive.flags = UINT32_C(95);
  if (malbolge_guest_format_parse_next(format, offset, &token) !=
      MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT) {
    return 0;
  }
  return token.kind == UINT32_C(91) && token.offset == UINT32_C(92) &&
         token.length == UINT32_C(93) && token.next_offset == UINT32_C(94) &&
         token.directive.flags == UINT32_C(95);
}

static int reject_unchanged(const char *format) {
  return reject_offset_unchanged(format, UINT32_C(0));
}

static int test_rejections(void) {
  static const char *const malformed[] = {
      "%",
      "%q",
      "%w0d",
      "%w01d",
      "%wd",
      "%wfd",
      "%42949672960d",
      "%.42949672960d",
      "%w42949672960d",
  };
  uint32_t index = UINT32_C(0);
  MalbolgeGuestFormatToken token;

  while (index < (uint32_t)(sizeof(malformed) / sizeof(malformed[0]))) {
    if (!reject_unchanged(malformed[index])) {
      return (int)(index + UINT32_C(1));
    }
    ++index;
  }
  if (malbolge_guest_format_parse_next(NULL, UINT32_C(0), &token) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      malbolge_guest_format_parse_next("%d", UINT32_C(0), NULL) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT) {
    return 20;
  }
  if (!reject_offset_unchanged("%d", UINT32_C(3))) {
    return 21;
  }
  return 0;
}

static int directive_status(const char *format,
                            MalbolgeGuestRuntimeStatus expected) {
  MalbolgeGuestFormatToken token;

  if (malbolge_guest_format_parse_next(format, UINT32_C(0), &token) !=
      MALBOLGE_GUEST_RUNTIME_VALID) {
    return 0;
  }
  return malbolge_guest_format_directive_validate(&token.directive) == expected;
}

static int test_semantic_admission(void) {
  static const char *const accepted[] = {
      "%+08.3lld", "%#*.*w32b", "%wf64X", "%.s",    "%hhd", "%jd",
      "%zu",       "%td",       "%Lf",    "%la",    "%lc",  "%ls",
      "%-10p",     "%hhn",      "%w8n",   "%wf32n", "%%",
  };
  static const char *const rejected[] = {
      "%Ld",  "%llf", "%hc", "%hs",  "%lp",  "%w32f", "%w24d",
      "%#d",  "%+u",  "%0s", "%.2c", "%.2p", "%.2n",  "%5%",
      "%10n", "%-n",  "%+p", "%0p",  "%#p",
  };
  uint32_t index = UINT32_C(0);
  MalbolgeGuestFormatDirective malformed = {
      UINT32_C(0), MALBOLGE_GUEST_FORMAT_FIELD_OMITTED,
      UINT32_C(0), MALBOLGE_GUEST_FORMAT_FIELD_OMITTED,
      UINT32_C(0), MALBOLGE_GUEST_FORMAT_LENGTH_NONE,
      UINT32_C(0), MALBOLGE_GUEST_FORMAT_CONVERSION_DECIMAL,
  };

  while (index < (uint32_t)(sizeof(accepted) / sizeof(accepted[0]))) {
    if (!directive_status(accepted[index], MALBOLGE_GUEST_RUNTIME_VALID)) {
      return (int)(index + UINT32_C(1));
    }
    ++index;
  }
  index = UINT32_C(0);
  while (index < (uint32_t)(sizeof(rejected) / sizeof(rejected[0]))) {
    if (!directive_status(rejected[index],
                          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT)) {
      return (int)(UINT32_C(40) + index);
    }
    ++index;
  }
  malformed.flags = MALBOLGE_GUEST_FORMAT_UPPERCASE;
  if (malbolge_guest_format_directive_validate(&malformed) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      malbolge_guest_format_directive_validate(NULL) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT) {
    return 80;
  }
  malformed.flags = UINT32_C(0);
  malformed.width_kind = UINT32_C(99);
  if (malbolge_guest_format_directive_validate(&malformed) !=
      MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT) {
    return 81;
  }
  return 0;
}

static int argument_kind(const char *format, uint32_t expected_kind) {
  MalbolgeGuestFormatToken token;
  uint32_t kind = UINT32_C(99);

  return malbolge_guest_format_parse_next(format, UINT32_C(0), &token) ==
             MALBOLGE_GUEST_RUNTIME_VALID &&
         malbolge_guest_format_argument_kind(&token.directive, &kind) ==
             MALBOLGE_GUEST_RUNTIME_VALID &&
         kind == expected_kind;
}

static int test_argument_kinds(void) {
  static const char *const formats[] = {
      "%d", "%lld", "%u", "%hhu", "%w16u", "%w32u", "%w64u", "%ju",
      "%f", "%Lf",  "%c", "%s",   "%p",    "%hhn",  "%%",
  };
  static const uint32_t kinds[] = {
      MALBOLGE_GUEST_VARARG_I32,       MALBOLGE_GUEST_VARARG_I64,
      MALBOLGE_GUEST_VARARG_U32,       MALBOLGE_GUEST_VARARG_I32,
      MALBOLGE_GUEST_VARARG_I32,       MALBOLGE_GUEST_VARARG_U32,
      MALBOLGE_GUEST_VARARG_U64,       MALBOLGE_GUEST_VARARG_U64,
      MALBOLGE_GUEST_VARARG_F64,       MALBOLGE_GUEST_VARARG_F128,
      MALBOLGE_GUEST_VARARG_I32,       MALBOLGE_GUEST_VARARG_POINTER32,
      MALBOLGE_GUEST_VARARG_POINTER32, MALBOLGE_GUEST_VARARG_POINTER32,
      MALBOLGE_GUEST_VARARG_NONE,
  };
  uint32_t index = UINT32_C(0);
  MalbolgeGuestFormatDirective invalid = {
      UINT32_C(0), MALBOLGE_GUEST_FORMAT_FIELD_OMITTED,
      UINT32_C(0), MALBOLGE_GUEST_FORMAT_FIELD_OMITTED,
      UINT32_C(0), MALBOLGE_GUEST_FORMAT_LENGTH_LONG_DOUBLE,
      UINT32_C(0), MALBOLGE_GUEST_FORMAT_CONVERSION_DECIMAL,
  };
  uint32_t kind = UINT32_C(77);

  while (index < (uint32_t)(sizeof(formats) / sizeof(formats[0]))) {
    if (!argument_kind(formats[index], kinds[index])) {
      return (int)(index + UINT32_C(1));
    }
    ++index;
  }
  {
    MalbolgeGuestFormatToken token;
    if (malbolge_guest_format_parse_next("%lc", UINT32_C(0), &token) !=
            MALBOLGE_GUEST_RUNTIME_VALID ||
        malbolge_guest_format_argument_kind(&token.directive, &kind) !=
            MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
        kind != UINT32_C(77)) {
      return 40;
    }
  }
  if (malbolge_guest_format_argument_kind(&invalid, &kind) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      kind != UINT32_C(77) ||
      malbolge_guest_format_argument_kind(NULL, &kind) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      malbolge_guest_format_argument_kind(&invalid, NULL) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT) {
    return 40;
  }
  return 0;
}

int main(void) {
  const int stream = test_stream();
  const int fields = test_fields();
  const int lengths = test_lengths();
  const int tags = test_conversion_tags();
  const int rejected = test_rejections();
  const int semantics = test_semantic_admission();
  const int argument_kinds = test_argument_kinds();

  if (stream != 0) {
    return 10 + stream;
  }
  if (fields != 0) {
    return 20 + fields;
  }
  if (lengths != 0) {
    return 40 + lengths;
  }
  if (tags != 0) {
    return 60 + tags;
  }
  if (rejected != 0) {
    return 80 + rejected;
  }
  if (semantics != 0) {
    return 120 + semantics;
  }
  return argument_kinds == 0 ? 0 : 220 + argument_kinds;
}
