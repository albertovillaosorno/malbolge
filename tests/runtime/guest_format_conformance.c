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
//   - Independent vectors for typed guest formatting-kernel semantics.
// - Must-Not:
//   - Use host printf-family output as expected-value authority.
// - Allows:
//   - Inputs: fixed values and explicit kernel formatting options.
//   - Outputs: zero only when bytes/counts/statuses match tracked vectors.
//   - Side effects: test-local destination buffers only.
// - Split-When:
//   - Full format-parser or floating-output conformance gains its own harness.
// - Merge-When:
//   - Runtime conformance owns these exact typed-format vectors directly.
// - Summary:
//   - Locks integer, string, padding, truncation, and overflow accounting.
// - Description:
//   - Expected bytes are independent literals, not host formatter results.
// - Usage:
//   - Built and executed by `tests/test_guest_runtime_c.py`.
// - Defaults:
//   - Public snprintf/vsnprintf availability remains unchanged.
//

//! Independent execution vectors for the typed formatting kernel.

#include "guest_format.h"

#include <stddef.h>
#include <stdint.h>

static int same_text(const char *left, const char *right) {
  uint32_t index = 0U;

  while (left[index] != '\0' && right[index] != '\0') {
    if (left[index] != right[index]) {
      return 0;
    }
    ++index;
  }
  return left[index] == right[index];
}

static int finish_matches(MalbolgeGuestFormatSink *sink, const char *expected,
                          uint32_t required) {
  return malbolge_guest_format_finish(sink) == MALBOLGE_GUEST_RUNTIME_VALID &&
         sink->required == required && same_text(sink->destination, expected);
}

static MalbolgeGuestIntegerFormat integer_format(uint32_t flags, uint32_t width,
                                                 uint32_t precision,
                                                 uint32_t base) {
  MalbolgeGuestIntegerFormat format = {flags, width, precision, base};
  return format;
}

static int test_signed_integer(void) {
  char output[64];
  MalbolgeGuestFormatSink sink;
  MalbolgeGuestIntegerFormat format =
      integer_format(UINT32_C(0), UINT32_C(6),
                     MALBOLGE_GUEST_FORMAT_PRECISION_OMITTED, UINT32_C(10));

  if (malbolge_guest_format_sink_init(&sink, output,
                                      (uint32_t)sizeof(output)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_signed_decimal(&sink, INT64_C(-42), &format) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      !finish_matches(&sink, "   -42", UINT32_C(6))) {
    return 1;
  }
  format.flags = MALBOLGE_GUEST_FORMAT_PLUS | MALBOLGE_GUEST_FORMAT_ZERO;
  if (malbolge_guest_format_sink_init(&sink, output,
                                      (uint32_t)sizeof(output)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_signed_decimal(&sink, INT64_C(42), &format) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      !finish_matches(&sink, "+00042", UINT32_C(6))) {
    return 2;
  }
  format.flags = MALBOLGE_GUEST_FORMAT_ZERO;
  format.precision = UINT32_C(3);
  if (malbolge_guest_format_sink_init(&sink, output,
                                      (uint32_t)sizeof(output)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_signed_decimal(&sink, INT64_C(42), &format) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      !finish_matches(&sink, "   042", UINT32_C(6))) {
    return 3;
  }
  format.flags = UINT32_C(0);
  format.width = UINT32_C(0);
  format.precision = MALBOLGE_GUEST_FORMAT_PRECISION_OMITTED;
  if (malbolge_guest_format_sink_init(&sink, output,
                                      (uint32_t)sizeof(output)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_signed_decimal(&sink, INT64_MIN, &format) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      !finish_matches(&sink, "-9223372036854775808", UINT32_C(20))) {
    return 4;
  }
  format.precision = UINT32_C(0);
  if (malbolge_guest_format_sink_init(&sink, output,
                                      (uint32_t)sizeof(output)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_signed_decimal(&sink, INT64_C(0), &format) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      !finish_matches(&sink, "", UINT32_C(0))) {
    return 5;
  }
  format.flags = MALBOLGE_GUEST_FORMAT_PLUS;
  if (malbolge_guest_format_sink_init(&sink, output,
                                      (uint32_t)sizeof(output)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_signed_decimal(&sink, INT64_C(0), &format) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      !finish_matches(&sink, "+", UINT32_C(1))) {
    return 6;
  }
  format.flags = MALBOLGE_GUEST_FORMAT_SPACE;
  if (malbolge_guest_format_sink_init(&sink, output,
                                      (uint32_t)sizeof(output)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_signed_decimal(&sink, INT64_C(0), &format) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      !finish_matches(&sink, " ", UINT32_C(1))) {
    return 7;
  }
  return 0;
}

static int test_unsigned_integer(void) {
  char output[64];
  MalbolgeGuestFormatSink sink;
  MalbolgeGuestIntegerFormat format = integer_format(
      MALBOLGE_GUEST_FORMAT_ALTERNATE | MALBOLGE_GUEST_FORMAT_UPPERCASE,
      UINT32_C(0), MALBOLGE_GUEST_FORMAT_PRECISION_OMITTED, UINT32_C(16));

  if (malbolge_guest_format_sink_init(&sink, output,
                                      (uint32_t)sizeof(output)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_unsigned(&sink, UINT64_C(42), &format) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      !finish_matches(&sink, "0X2A", UINT32_C(4))) {
    return 1;
  }
  format.flags = MALBOLGE_GUEST_FORMAT_ALTERNATE;
  format.base = UINT32_C(2);
  if (malbolge_guest_format_sink_init(&sink, output,
                                      (uint32_t)sizeof(output)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_unsigned(&sink, UINT64_C(5), &format) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      !finish_matches(&sink, "0b101", UINT32_C(5))) {
    return 2;
  }
  format.base = UINT32_C(8);
  format.precision = UINT32_C(3);
  if (malbolge_guest_format_sink_init(&sink, output,
                                      (uint32_t)sizeof(output)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_unsigned(&sink, UINT64_C(8), &format) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      !finish_matches(&sink, "010", UINT32_C(3))) {
    return 3;
  }
  format.precision = UINT32_C(0);
  if (malbolge_guest_format_sink_init(&sink, output,
                                      (uint32_t)sizeof(output)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_unsigned(&sink, UINT64_C(0), &format) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      !finish_matches(&sink, "0", UINT32_C(1))) {
    return 4;
  }
  format.flags = UINT32_C(0);
  format.base = UINT32_C(10);
  format.width = UINT32_C(0);
  format.precision = MALBOLGE_GUEST_FORMAT_PRECISION_OMITTED;
  if (malbolge_guest_format_sink_init(&sink, output,
                                      (uint32_t)sizeof(output)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_unsigned(&sink, UINT64_MAX, &format) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      !finish_matches(&sink, "18446744073709551615", UINT32_C(20))) {
    return 5;
  }
  format.flags = MALBOLGE_GUEST_FORMAT_LEFT;
  format.width = UINT32_C(6);
  if (malbolge_guest_format_sink_init(&sink, output,
                                      (uint32_t)sizeof(output)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_unsigned(&sink, UINT64_C(42), &format) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      !finish_matches(&sink, "42    ", UINT32_C(6))) {
    return 6;
  }
  return 0;
}

static int test_strings_and_truncation(void) {
  char output[8];
  MalbolgeGuestFormatSink sink;

  if (malbolge_guest_format_sink_init(&sink, output,
                                      (uint32_t)sizeof(output)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_string(&sink, "abcdef", UINT32_C(5), UINT32_C(3),
                                   UINT32_C(0)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      !finish_matches(&sink, "  abc", UINT32_C(5))) {
    return 1;
  }
  if (malbolge_guest_format_sink_init(&sink, output, UINT32_C(5)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_string(
          &sink, "abcdef", UINT32_C(0), MALBOLGE_GUEST_FORMAT_PRECISION_OMITTED,
          UINT32_C(0)) != MALBOLGE_GUEST_RUNTIME_VALID ||
      !finish_matches(&sink, "abcd", UINT32_C(6))) {
    return 2;
  }
  if (malbolge_guest_format_sink_init(&sink, output,
                                      (uint32_t)sizeof(output)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_character(&sink, UINT8_C('A'), UINT32_C(3),
                                      MALBOLGE_GUEST_FORMAT_LEFT) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      !finish_matches(&sink, "A  ", UINT32_C(3))) {
    return 3;
  }
  return 0;
}

static int test_invalid_and_large_counts(void) {
  char output[4] = {'x', 'x', 'x', '\0'};
  MalbolgeGuestFormatSink sink;
  MalbolgeGuestIntegerFormat format =
      integer_format(UINT32_C(0), UINT32_MAX,
                     MALBOLGE_GUEST_FORMAT_PRECISION_OMITTED, UINT32_C(10));

  if (malbolge_guest_format_sink_init(&sink, NULL, UINT32_C(1)) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      malbolge_guest_format_sink_init(&sink, NULL, UINT32_C(0)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_finish(&sink) != MALBOLGE_GUEST_RUNTIME_VALID) {
    return 1;
  }
  if (malbolge_guest_format_sink_init(&sink, output, UINT32_C(1)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_unsigned(&sink, UINT64_C(1), &format) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      sink.required != UINT32_MAX ||
      malbolge_guest_format_finish(&sink) != MALBOLGE_GUEST_RUNTIME_VALID ||
      output[0] != '\0') {
    return 2;
  }
  if (malbolge_guest_format_character(&sink, UINT8_C('x'), UINT32_C(1),
                                      UINT32_C(0)) !=
      MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT) {
    return 3;
  }
  format.width = UINT32_C(0);
  format.precision = (uint32_t)INT32_MAX;
  if (malbolge_guest_format_sink_init(&sink, output, UINT32_C(1)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_unsigned(&sink, UINT64_C(1), &format) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      sink.required != (uint32_t)INT32_MAX ||
      malbolge_guest_format_finish(&sink) != MALBOLGE_GUEST_RUNTIME_VALID ||
      output[0] != '\0') {
    return 4;
  }
  sink.destination = NULL;
  sink.capacity = UINT32_C(4);
  sink.required = UINT32_C(0);
  if (malbolge_guest_format_character(&sink, UINT8_C('x'), UINT32_C(1),
                                      UINT32_C(0)) !=
      MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT) {
    return 5;
  }
  format.width = UINT32_C(0);
  format.base = UINT32_C(3);
  if (malbolge_guest_format_sink_init(&sink, output,
                                      (uint32_t)sizeof(output)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_unsigned(&sink, UINT64_C(1), &format) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      sink.required != UINT32_C(0)) {
    return 6;
  }
  format.base = UINT32_C(10);
  format.flags = MALBOLGE_GUEST_FORMAT_ALTERNATE;
  if (malbolge_guest_format_unsigned(&sink, UINT64_C(1), &format) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      sink.required != UINT32_C(0)) {
    return 7;
  }
  return 0;
}

int main(void) {
  const int signed_result = test_signed_integer();
  const int unsigned_result = test_unsigned_integer();
  const int string_result = test_strings_and_truncation();
  const int invalid_result = test_invalid_and_large_counts();

  if (signed_result != 0) {
    return 10 + signed_result;
  }
  if (unsigned_result != 0) {
    return 20 + unsigned_result;
  }
  if (string_result != 0) {
    return 30 + string_result;
  }
  return invalid_result == 0 ? 0 : 40 + invalid_result;
}
