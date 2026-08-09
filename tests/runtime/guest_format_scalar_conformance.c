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
//   - Independent vectors for resolved scalar guest printf execution.
// - Must-Not:
//   - Use host printf, dereference guest pointers, or execute floating
//   conversion.
// - Allows:
//   - Inputs: parsed scalar directives plus explicit canonical promoted bits.
//   - Outputs: zero only when emitted bytes/counts and rejection atomicity
//   match.
//   - Side effects: test-local sinks and resolved argument records only.
// - Split-When:
//   - Pointer-backed or floating execution gains independent conformance.
// - Merge-When:
//   - Complete formatter conformance owns these exact scalar vectors directly.
// - Summary:
//   - Locks promotion-aware narrowing and integer/character/percent execution.
// - Description:
//   - Covers signed minima, dirty high bits, prefixes, precision, and padding.
// - Usage:
//   - Built and executed by tests/test_guest_runtime_c.py.
// - Defaults:
//   - Unsupported families reject without advancing the sink count.
//

//! Scalar conversion vectors over parsed and resolved guest format arguments.

#include "guest_format_scalar.h"

#include <stddef.h>
#include <stdint.h>

static int same_text(const char *left, const char *right) {
  uint32_t index = UINT32_C(0);
  while (left[index] != '\0' && right[index] != '\0') {
    if (left[index] != right[index]) {
      return 0;
    }
    ++index;
  }
  return left[index] == right[index];
}

static int build_resolved(const char *format, uint64_t low,
                          MalbolgeGuestResolvedFormatArgument *resolved) {
  MalbolgeGuestFormatToken token;
  uint32_t kind = MALBOLGE_GUEST_VARARG_NONE;
  if (malbolge_guest_format_parse_next(format, UINT32_C(0), &token) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_argument_kind(&token.directive, &kind) !=
          MALBOLGE_GUEST_RUNTIME_VALID) {
    return 0;
  }
  resolved->directive = token.directive;
  resolved->argument_kind = kind;
  resolved->argument.low = low;
  resolved->argument.high = UINT64_C(0);
  return 1;
}

static int expect_text(const char *format, uint64_t low, const char *expected,
                       uint32_t required) {
  char output[96];
  MalbolgeGuestFormatSink sink;
  MalbolgeGuestResolvedFormatArgument resolved;

  if (!build_resolved(format, low, &resolved) ||
      malbolge_guest_format_sink_init(&sink, output,
                                      (uint32_t)sizeof(output)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_execute_scalar(&sink, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_finish(&sink) != MALBOLGE_GUEST_RUNTIME_VALID ||
      sink.required != required || !same_text(output, expected)) {
    return 0;
  }
  return 1;
}

static int test_signed_narrowing(void) {
  if (!expect_text("%hhd", UINT64_C(0x000000ff), "-1", UINT32_C(2))) {
    return 1;
  }
  if (!expect_text("%hd", UINT64_C(0x00008001), "-32767", UINT32_C(6))) {
    return 2;
  }
  if (!expect_text("%w8d", UINT64_C(0x80), "-128", UINT32_C(4))) {
    return 3;
  }
  if (!expect_text("%lld", UINT64_C(0x8000000000000000), "-9223372036854775808",
                   UINT32_C(20))) {
    return 4;
  }
  return 0;
}

static int test_unsigned_narrowing(void) {
  if (!expect_text("%hhu", UINT64_C(0xffffffff), "255", UINT32_C(3))) {
    return 1;
  }
  if (!expect_text("%w16u", UINT64_C(0x12345), "9029", UINT32_C(4))) {
    return 2;
  }
  if (!expect_text("%#08x", UINT64_C(42), "0x00002a", UINT32_C(8))) {
    return 3;
  }
  if (!expect_text("%#B", UINT64_C(5), "0B101", UINT32_C(5))) {
    return 4;
  }
  if (!expect_text("%#.0o", UINT64_C(0), "0", UINT32_C(1))) {
    return 5;
  }
  return 0;
}

static int test_character_and_percent(void) {
  if (!expect_text("%-3c", UINT64_C(65), "A  ", UINT32_C(3))) {
    return 1;
  }
  if (!expect_text("%%", UINT64_C(0), "%", UINT32_C(1))) {
    return 2;
  }
  return 0;
}

static int reject_without_sink_change(const char *format, uint64_t low) {
  char output[8] = "seed";
  MalbolgeGuestFormatSink sink;
  MalbolgeGuestResolvedFormatArgument resolved;

  if (!build_resolved(format, low, &resolved) ||
      malbolge_guest_format_sink_init(&sink, output,
                                      (uint32_t)sizeof(output)) !=
          MALBOLGE_GUEST_RUNTIME_VALID) {
    return 0;
  }
  sink.required = UINT32_C(2);
  output[0] = 's';
  output[1] = 'e';
  output[2] = '\0';
  if (malbolge_guest_format_execute_scalar(&sink, &resolved) !=
      MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT) {
    return 0;
  }
  return sink.required == UINT32_C(2) && output[0] == 's' && output[1] == 'e' &&
         output[2] == '\0';
}

static int test_rejections(void) {
  MalbolgeGuestResolvedFormatArgument resolved;
  char output[8];
  MalbolgeGuestFormatSink sink;

  if (!reject_without_sink_change("%f", UINT64_C(0)) ||
      !reject_without_sink_change("%s", UINT64_C(4)) ||
      !reject_without_sink_change("%p", UINT64_C(4)) ||
      !reject_without_sink_change("%n", UINT64_C(4))) {
    return 1;
  }
  if (!build_resolved("%u", UINT64_C(7), &resolved) ||
      malbolge_guest_format_sink_init(&sink, output,
                                      (uint32_t)sizeof(output)) !=
          MALBOLGE_GUEST_RUNTIME_VALID) {
    return 2;
  }
  resolved.argument_kind = MALBOLGE_GUEST_VARARG_U64;
  if (malbolge_guest_format_execute_scalar(&sink, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      sink.required != UINT32_C(0)) {
    return 3;
  }
  if (!build_resolved("%*u", UINT64_C(7), &resolved) ||
      malbolge_guest_format_execute_scalar(&sink, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      sink.required != UINT32_C(0)) {
    return 4;
  }
  if (!build_resolved("%u", UINT64_C(7), &resolved)) {
    return 5;
  }
  resolved.argument.high = UINT64_C(1);
  if (malbolge_guest_format_execute_scalar(&sink, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      sink.required != UINT32_C(0)) {
    return 6;
  }
  resolved.argument.high = UINT64_C(0);
  resolved.argument.low = UINT64_C(0x100000000);
  if (malbolge_guest_format_execute_scalar(&sink, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      sink.required != UINT32_C(0)) {
    return 7;
  }
  if (malbolge_guest_format_execute_scalar(NULL, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      malbolge_guest_format_execute_scalar(&sink, NULL) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT) {
    return 8;
  }
  return 0;
}

int main(void) {
  const int signed_result = test_signed_narrowing();
  const int unsigned_result = test_unsigned_narrowing();
  const int character_result = test_character_and_percent();
  const int rejected = test_rejections();

  if (signed_result != 0) {
    return 10 + signed_result;
  }
  if (unsigned_result != 0) {
    return 20 + unsigned_result;
  }
  if (character_result != 0) {
    return 30 + character_result;
  }
  return rejected == 0 ? 0 : 40 + rejected;
}
