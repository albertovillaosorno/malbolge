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
//   - Independent vectors for deterministic binary64 %a/%A execution.
// - Must-Not:
//   - Use host printf as an oracle or execute native floating arithmetic.
// - Allows:
//   - Inputs: explicit binary64 bit patterns and parsed format directives.
//   - Outputs: zero only when exact hex text/count/rejection semantics match.
//   - Side effects: test-local sink bytes and resolved argument records only.
// - Split-When:
//   - Decimal or binary128 formatting gains independent conformance vectors.
// - Merge-When:
//   - Complete formatter tests own this exact hexadecimal floating evidence.
// - Summary:
//   - Locks normalized finite values, special values, rounding, and padding.
// - Description:
//   - Includes subnormals, ties-to-even, huge precision, and atomic failures.
// - Usage:
//   - Built and executed by tests/test_guest_runtime_c.py.
// - Defaults:
//   - Expected strings are explicit guest-contract vectors, not host output.
//

//! Binary64 hexadecimal formatting vectors over raw canonical guest bits.

#include "guest_format_float.h"

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

static int build_resolved128(
    const char *format, uint64_t low, uint64_t high,
    MalbolgeGuestResolvedFormatArgument *resolved) {
  if (!build_resolved(format, low, resolved)) {
    return 0;
  }
  resolved->argument.high = high;
  return 1;
}

static int expect_text(const char *format, uint64_t bits, const char *expected,
                       uint32_t required) {
  char output[96];
  MalbolgeGuestFormatSink sink;
  MalbolgeGuestResolvedFormatArgument resolved;

  if (!build_resolved(format, bits, &resolved) ||
      malbolge_guest_format_sink_init(&sink, output,
                                      (uint32_t)sizeof(output)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_execute_hex_float(&sink, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_finish(&sink) != MALBOLGE_GUEST_RUNTIME_VALID ||
      sink.required != required || !same_text(output, expected)) {
    return 0;
  }
  return 1;
}

static int expect_text128(const char *format, uint64_t low, uint64_t high,
                          const char *expected, uint32_t required) {
  char output[128];
  MalbolgeGuestFormatSink sink;
  MalbolgeGuestResolvedFormatArgument resolved;

  if (!build_resolved128(format, low, high, &resolved) ||
      malbolge_guest_format_sink_init(&sink, output,
                                      (uint32_t)sizeof(output)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_execute_hex_float(&sink, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_finish(&sink) != MALBOLGE_GUEST_RUNTIME_VALID ||
      sink.required != required || !same_text(output, expected)) {
    return 0;
  }
  return 1;
}

static int test_exact_geometry(void) {
  if (!expect_text("%a", UINT64_C(0x3ff0000000000000), "0x1p+0",
                   UINT32_C(6))) {
    return 1;
  }
  if (!expect_text("%#a", UINT64_C(0x3ff0000000000000), "0x1.p+0",
                   UINT32_C(7))) {
    return 2;
  }
  if (!expect_text("%a", UINT64_C(0x3ff8000000000000), "0x1.8p+0",
                   UINT32_C(8))) {
    return 3;
  }
  if (!expect_text("%A", UINT64_C(0x7fefffffffffffff),
                   "0X1.FFFFFFFFFFFFFP+1023", UINT32_C(23))) {
    return 4;
  }
  if (!expect_text("%la", UINT64_C(0x400921fb54442d18),
                   "0x1.921fb54442d18p+1", UINT32_C(20))) {
    return 5;
  }
  return 0;
}

static int test_precision_rounding(void) {
  if (!expect_text("%.0a", UINT64_C(0x3ff8000000000000), "0x2p+0",
                   UINT32_C(6))) {
    return 1;
  }
  if (!expect_text("%.1a", UINT64_C(0x3ff8800000000000), "0x1.8p+0",
                   UINT32_C(8))) {
    return 2;
  }
  if (!expect_text("%.1a", UINT64_C(0x3ff9800000000000), "0x1.ap+0",
                   UINT32_C(8))) {
    return 3;
  }
  if (!expect_text("%.15a", UINT64_C(0x3ff8000000000000),
                   "0x1.800000000000000p+0", UINT32_C(22))) {
    return 4;
  }
  if (!expect_text("%.0a", UINT64_C(0x7fefffffffffffff), "0x2p+1023",
                   UINT32_C(9))) {
    return 5;
  }
  if (!expect_text("%#.0a", UINT64_C(0x3ff0000000000000), "0x1.p+0",
                   UINT32_C(7))) {
    return 6;
  }
  return 0;
}

static int test_subnormal_and_zero(void) {
  if (!expect_text("%a", UINT64_C(0x0000000000000001), "0x1p-1074",
                   UINT32_C(9))) {
    return 1;
  }
  if (!expect_text("%a", UINT64_C(0x000fffffffffffff),
                   "0x1.ffffffffffffep-1023", UINT32_C(23))) {
    return 2;
  }
  if (!expect_text("%a", UINT64_C(0x8000000000000000), "-0x0p+0",
                   UINT32_C(7))) {
    return 3;
  }
  if (!expect_text("%.3a", UINT64_C(0), "0x0.000p+0", UINT32_C(10))) {
    return 4;
  }
  return 0;
}

static int test_sign_width_and_special(void) {
  if (!expect_text("%+a", UINT64_C(0x3ff0000000000000), "+0x1p+0",
                   UINT32_C(7))) {
    return 1;
  }
  if (!expect_text("% a", UINT64_C(0x3ff0000000000000), " 0x1p+0",
                   UINT32_C(7))) {
    return 2;
  }
  if (!expect_text("%020a", UINT64_C(0x3ff8000000000000),
                   "0x0000000000001.8p+0", UINT32_C(20))) {
    return 3;
  }
  if (!expect_text("%-12a", UINT64_C(0x3ff8000000000000), "0x1.8p+0    ",
                   UINT32_C(12))) {
    return 4;
  }
  if (!expect_text("%A", UINT64_C(0x7ff0000000000000), "INF",
                   UINT32_C(3))) {
    return 5;
  }
  if (!expect_text("%+a", UINT64_C(0x7ff8000000000001), "+nan",
                   UINT32_C(4))) {
    return 6;
  }
  if (!expect_text("%020a", UINT64_C(0x7ff0000000000000),
                   "                 inf", UINT32_C(20))) {
    return 7;
  }
  if (!expect_text("%a", UINT64_C(0xfff8000000000001), "-nan",
                   UINT32_C(4))) {
    return 8;
  }
  return 0;
}

static int test_binary128(void) {
  if (!expect_text128("%La", UINT64_C(0), UINT64_C(0x3fff000000000000),
                      "0x1p+0", UINT32_C(6))) {
    return 1;
  }
  if (!expect_text128("%La", UINT64_C(0), UINT64_C(0x3fff800000000000),
                      "0x1.8p+0", UINT32_C(8))) {
    return 2;
  }
  if (!expect_text128("%LA", UINT64_MAX, UINT64_C(0x7ffeffffffffffff),
                      "0X1.FFFFFFFFFFFFFFFFFFFFFFFFFFFFP+16383",
                      UINT32_C(39))) {
    return 3;
  }
  if (!expect_text128("%La", UINT64_C(1), UINT64_C(0), "0x1p-16494",
                      UINT32_C(10))) {
    return 4;
  }
  if (!expect_text128("%La", UINT64_MAX, UINT64_C(0x0000ffffffffffff),
                      "0x1.fffffffffffffffffffffffffffep-16383",
                      UINT32_C(39))) {
    return 5;
  }
  if (!expect_text128("%La", UINT64_C(0), UINT64_C(0x8000000000000000),
                      "-0x0p+0", UINT32_C(7))) {
    return 6;
  }
  if (!expect_text128("%.1La", UINT64_C(0), UINT64_C(0x3fff880000000000),
                      "0x1.8p+0", UINT32_C(8)) ||
      !expect_text128("%.1La", UINT64_C(0), UINT64_C(0x3fff980000000000),
                      "0x1.ap+0", UINT32_C(8))) {
    return 7;
  }
  if (!expect_text128("%.0La", UINT64_MAX, UINT64_C(0x7ffeffffffffffff),
                      "0x2p+16383", UINT32_C(10))) {
    return 8;
  }
  if (!expect_text128("%#.0LA", UINT64_C(0), UINT64_C(0x3fff000000000000),
                      "0X1.P+0", UINT32_C(7))) {
    return 9;
  }
  if (!expect_text128("%.30La", UINT64_C(0), UINT64_C(0x3fff800000000000),
                      "0x1.800000000000000000000000000000p+0",
                      UINT32_C(37))) {
    return 10;
  }
  if (!expect_text128("%LA", UINT64_C(0), UINT64_C(0x7fff000000000000),
                      "INF", UINT32_C(3)) ||
      !expect_text128("%La", UINT64_C(1), UINT64_C(0x7fff800000000000),
                      "nan", UINT32_C(3))) {
    return 11;
  }
  return 0;
}

static int test_truncation_and_failures(void) {
  char output[6];
  MalbolgeGuestFormatSink sink;
  MalbolgeGuestResolvedFormatArgument resolved;

  if (!build_resolved("%a", UINT64_C(0x3ff8000000000000), &resolved) ||
      malbolge_guest_format_sink_init(&sink, output,
                                      (uint32_t)sizeof(output)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_execute_hex_float(&sink, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_finish(&sink) != MALBOLGE_GUEST_RUNTIME_VALID ||
      sink.required != UINT32_C(8) || !same_text(output, "0x1.8")) {
    return 1;
  }
  if (!build_resolved("%.4294967295a", UINT64_C(0x3ff0000000000000),
                      &resolved) ||
      malbolge_guest_format_sink_init(&sink, output,
                                      (uint32_t)sizeof(output)) !=
          MALBOLGE_GUEST_RUNTIME_VALID) {
    return 2;
  }
  sink.required = UINT32_C(2);
  output[0] = 's';
  output[1] = 'e';
  output[2] = '\0';
  if (malbolge_guest_format_execute_hex_float(&sink, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      sink.required != UINT32_C(2) || !same_text(output, "se")) {
    return 3;
  }
  if (!build_resolved("%Lf", UINT64_C(0), &resolved)) {
    return 4;
  }
  resolved.argument.high = UINT64_C(0x3fff000000000000);
  if (malbolge_guest_format_execute_hex_float(&sink, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      sink.required != UINT32_C(2)) {
    return 5;
  }
  if (!build_resolved("%f", UINT64_C(0x3ff0000000000000), &resolved) ||
      malbolge_guest_format_execute_hex_float(&sink, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      sink.required != UINT32_C(2)) {
    return 6;
  }
  if (!build_resolved("%*a", UINT64_C(0x3ff0000000000000), &resolved) ||
      malbolge_guest_format_execute_hex_float(&sink, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      sink.required != UINT32_C(2)) {
    return 7;
  }
  return 0;
}

int main(void) {
  const int exact = test_exact_geometry();
  const int rounding = test_precision_rounding();
  const int subnormal = test_subnormal_and_zero();
  const int flags = test_sign_width_and_special();
  const int binary128 = test_binary128();
  const int failures = test_truncation_and_failures();

  if (exact != 0) {
    return 10 + exact;
  }
  if (rounding != 0) {
    return 20 + rounding;
  }
  if (subnormal != 0) {
    return 30 + subnormal;
  }
  if (flags != 0) {
    return 40 + flags;
  }
  if (binary128 != 0) {
    return 50 + binary128;
  }
  return failures == 0 ? 0 : 70 + failures;
}
