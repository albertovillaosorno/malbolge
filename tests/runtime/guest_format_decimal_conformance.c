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
//   - Independent vectors for deterministic binary64 %e/%E execution.
// - Must-Not:
//   - Use host printf or native floating arithmetic as an expected-value
//     oracle.
// - Allows:
//   - Inputs: explicit binary64 bits and parser-produced directives.
//   - Outputs: zero only when scientific spelling/count/rejection matches.
//   - Side effects: test-local sinks and resolved argument records only.
// - Split-When:
//   - Fixed/general or binary128 decimal formatting gains separate vectors.
// - Merge-When:
//   - Complete decimal-format conformance owns all decimal styles together.
// - Summary:
//   - Locks scientific decimal rounding, exponent, flags, and atomic failures.
// - Description:
//   - Includes exact ties, subnormal/maximum edges, and virtual precision.
// - Usage:
//   - Built by guest-runtime C tests and direct strict local validation.
// - Defaults:
//   - Expected strings are explicit guest-contract vectors, not host output.
//

//! Binary64 scientific decimal formatting vectors over raw guest bits.

#include "guest_format_float.h"

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

static int build_resolved(const char *format, uint64_t bits,
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
  resolved->argument.low = bits;
  resolved->argument.high = UINT64_C(0);
  return 1;
}

static int expect_text(const char *format, uint64_t bits, const char *expected,
                       uint32_t required) {
  char output[96];
  MalbolgeGuestFormatSink sink;
  MalbolgeGuestResolvedFormatArgument resolved;

  return build_resolved(format, bits, &resolved) &&
         malbolge_guest_format_sink_init(&sink, output,
                                         (uint32_t)sizeof(output)) ==
             MALBOLGE_GUEST_RUNTIME_VALID &&
         malbolge_guest_format_execute_decimal_float(&sink, &resolved) ==
             MALBOLGE_GUEST_RUNTIME_VALID &&
         malbolge_guest_format_finish(&sink) == MALBOLGE_GUEST_RUNTIME_VALID &&
         sink.required == required && same_text(output, expected);
}

static int test_basic_and_edges(void) {
  if (!expect_text("%e", UINT64_C(0x3ff0000000000000), "1.000000e+00",
                   UINT32_C(12)) ||
      !expect_text("%.0e", UINT64_C(0x3ff0000000000000), "1e+00",
                   UINT32_C(5)) ||
      !expect_text("%#.0e", UINT64_C(0x3ff0000000000000), "1.e+00",
                   UINT32_C(6))) {
    return 1;
  }
  if (!expect_text("%e", UINT64_C(0x3fb999999999999a), "1.000000e-01",
                   UINT32_C(12)) ||
      !expect_text("%e", UINT64_C(1), "4.940656e-324", UINT32_C(13)) ||
      !expect_text("%E", UINT64_C(0x7fefffffffffffff), "1.797693E+308",
                   UINT32_C(13))) {
    return 2;
  }
  if (!expect_text("%e", UINT64_C(0x8000000000000000), "-0.000000e+00",
                   UINT32_C(13))) {
    return 3;
  }
  return 0;
}

static int test_rounding(void) {
  if (!expect_text("%.0e", UINT64_C(0x4004000000000000), "2e+00",
                   UINT32_C(5)) ||
      !expect_text("%.0e", UINT64_C(0x400c000000000000), "4e+00",
                   UINT32_C(5)) ||
      !expect_text("%.0e", UINT64_C(0x4021000000000000), "8e+00",
                   UINT32_C(5)) ||
      !expect_text("%.0e", UINT64_C(0x4023000000000000), "1e+01",
                   UINT32_C(5))) {
    return 1;
  }
  if (!expect_text("%.2e", UINT64_C(0x3ff3c083126e978d), "1.23e+00",
                   UINT32_C(8))) {
    return 2;
  }
  return 0;
}

static int test_flags_special_and_truncation(void) {
  if (!expect_text("%+015.2e", UINT64_C(0x3ff8000000000000),
                   "+0000001.50e+00", UINT32_C(15)) ||
      !expect_text("%-12.1e", UINT64_C(0x3ff8000000000000),
                   "1.5e+00     ", UINT32_C(12))) {
    return 1;
  }
  if (!expect_text("%020e", UINT64_C(0x7ff0000000000000),
                   "                 inf", UINT32_C(20)) ||
      !expect_text("%+E", UINT64_C(0x7ff8000000000001), "+NAN",
                   UINT32_C(4))) {
    return 2;
  }
  {
    char output[6];
    MalbolgeGuestFormatSink sink;
    MalbolgeGuestResolvedFormatArgument resolved;
    if (!build_resolved("%e", UINT64_C(0x3ff8000000000000), &resolved) ||
        malbolge_guest_format_sink_init(&sink, output,
                                        (uint32_t)sizeof(output)) !=
            MALBOLGE_GUEST_RUNTIME_VALID ||
        malbolge_guest_format_execute_decimal_float(&sink, &resolved) !=
            MALBOLGE_GUEST_RUNTIME_VALID ||
        malbolge_guest_format_finish(&sink) != MALBOLGE_GUEST_RUNTIME_VALID ||
        sink.required != UINT32_C(12) || !same_text(output, "1.500")) {
      return 3;
    }
  }
  return 0;
}

static int test_fixed(void) {
  if (!expect_text("%f", UINT64_C(0x3ff0000000000000), "1.000000",
                   UINT32_C(8)) ||
      !expect_text("%.0f", UINT64_C(0x4004000000000000), "2",
                   UINT32_C(1)) ||
      !expect_text("%.0f", UINT64_C(0x400c000000000000), "4",
                   UINT32_C(1)) ||
      !expect_text("%.0f", UINT64_C(0x4023000000000000), "10",
                   UINT32_C(2))) {
    return 1;
  }
  if (!expect_text("%.1f", UINT64_C(0x3ff4000000000000), "1.2",
                   UINT32_C(3)) ||
      !expect_text("%.1F", UINT64_C(0x3ffc000000000000), "1.8",
                   UINT32_C(3)) ||
      !expect_text("%f", UINT64_C(0x3fb999999999999a), "0.100000",
                   UINT32_C(8))) {
    return 2;
  }
  if (!expect_text("%f", UINT64_C(1), "0.000000", UINT32_C(8)) ||
      !expect_text("%f", UINT64_C(0x8000000000000000), "-0.000000",
                   UINT32_C(9)) ||
      !expect_text("%#.0F", UINT64_C(0x3ff0000000000000), "1.",
                   UINT32_C(2))) {
    return 3;
  }
  if (!expect_text("%+015.2f", UINT64_C(0x3ff8000000000000),
                   "+00000000001.50", UINT32_C(15)) ||
      !expect_text("%-12.2f", UINT64_C(0x3ff8000000000000),
                   "1.50        ", UINT32_C(12))) {
    return 4;
  }
  if (!expect_text("%020F", UINT64_C(0x7ff0000000000000),
                   "                 INF", UINT32_C(20))) {
    return 5;
  }
  return 0;
}

static int test_fail_closed(void) {
  char output[8] = "stable";
  MalbolgeGuestFormatSink sink;
  MalbolgeGuestResolvedFormatArgument resolved;

  if (malbolge_guest_format_sink_init(&sink, output,
                                      (uint32_t)sizeof(output)) !=
      MALBOLGE_GUEST_RUNTIME_VALID) {
    return 1;
  }
  sink.required = UINT32_C(2);
  output[0] = 's';
  output[1] = 't';
  output[2] = '\0';
  if (!build_resolved("%Le", UINT64_C(0), &resolved)) {
    return 2;
  }
  resolved.argument.high = UINT64_C(0x3fff000000000000);
  if (malbolge_guest_format_execute_decimal_float(&sink, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      sink.required != UINT32_C(2) || !same_text(output, "st")) {
    return 3;
  }
  if (!build_resolved("%g", UINT64_C(0x3ff0000000000000), &resolved) ||
      malbolge_guest_format_execute_decimal_float(&sink, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      sink.required != UINT32_C(2)) {
    return 4;
  }
  if (!build_resolved("%.4294967295e", UINT64_C(0x3ff0000000000000),
                      &resolved) ||
      malbolge_guest_format_execute_decimal_float(&sink, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      sink.required != UINT32_C(2)) {
    return 5;
  }
  if (!build_resolved("%*e", UINT64_C(0x3ff0000000000000), &resolved) ||
      malbolge_guest_format_execute_decimal_float(&sink, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      sink.required != UINT32_C(2)) {
    return 6;
  }
  return 0;
}

int main(void) {
  const int basic = test_basic_and_edges();
  const int rounding = test_rounding();
  const int flags = test_flags_special_and_truncation();
  const int fixed = test_fixed();
  const int failures = test_fail_closed();

  if (basic != 0) {
    return 10 + basic;
  }
  if (rounding != 0) {
    return 20 + rounding;
  }
  if (flags != 0) {
    return 30 + flags;
  }
  if (fixed != 0) {
    return 40 + fixed;
  }
  return failures == 0 ? 0 : 50 + failures;
}
