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
//   - Independent conformance vectors for guest-memory %s/%n execution.
// - Must-Not:
//   - Use host printf, native pointer identity, or unbounded string access.
// - Allows:
//   - Inputs: explicit guest object bytes, logical pointer encodings, and
//     directives.
//   - Outputs: zero only when bounded string/count semantics match the guest
//     ABI.
//   - Side effects: test-local sink and guest-object bytes only.
// - Split-When:
//   - Wide strings or floating conversion gains independent conformance.
// - Merge-When:
//   - Complete formatter vectors own this exact guest-memory boundary.
// - Summary:
//   - Locks logical pointer mapping, bounded %s, and canonical %n writes.
// - Description:
//   - Includes precision, alignment, range, count overflow, and atomic failure.
// - Usage:
//   - Built and executed by tests/test_guest_runtime_c.py.
// - Defaults:
//   - Public snprintf/vsnprintf availability remains unchanged.
//

//! Guest-memory printf conversion vectors over explicit logical object views.

#include "guest_format_memory.h"

#include <stddef.h>
#include <stdint.h>

#define OBJECT_BASE UINT32_C(0x101)

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

static int same_bytes(const uint8_t *left, const uint8_t *right,
                      uint32_t count) {
  uint32_t index = UINT32_C(0);
  while (index < count) {
    if (left[index] != right[index]) {
      return 0;
    }
    ++index;
  }
  return 1;
}

static int build_resolved(const char *format, uint32_t pointer,
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
  resolved->argument.low = pointer;
  resolved->argument.high = UINT64_C(0);
  return 1;
}

static int test_narrow_string(void) {
  uint8_t object[12] = {'x', 'x', 'h', 'e', 'l', 'l', 'o', '\0', 'z', 'z',
                        'z', '\0'};
  char output[16];
  MalbolgeGuestMemoryView view = {object, (uint32_t)sizeof(object),
                                  OBJECT_BASE};
  MalbolgeGuestResolvedFormatArgument resolved;
  MalbolgeGuestFormatSink sink;

  if (!build_resolved("%7.3s", OBJECT_BASE + UINT32_C(2), &resolved) ||
      malbolge_guest_format_sink_init(&sink, output,
                                      (uint32_t)sizeof(output)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_execute_memory(&sink, &view, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_finish(&sink) != MALBOLGE_GUEST_RUNTIME_VALID ||
      sink.required != UINT32_C(7) || !same_text(output, "    hel")) {
    return 1;
  }
  if (!build_resolved("%-6s", OBJECT_BASE + UINT32_C(8), &resolved) ||
      malbolge_guest_format_sink_init(&sink, output,
                                      (uint32_t)sizeof(output)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_execute_memory(&sink, &view, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_finish(&sink) != MALBOLGE_GUEST_RUNTIME_VALID ||
      !same_text(output, "zzz   ")) {
    return 2;
  }
  return 0;
}

static int test_precision_bounds(void) {
  uint8_t object[3] = {'a', 'b', 'c'};
  char output[8] = "seed";
  MalbolgeGuestMemoryView view = {object, (uint32_t)sizeof(object),
                                  OBJECT_BASE};
  MalbolgeGuestResolvedFormatArgument resolved;
  MalbolgeGuestFormatSink sink;

  if (!build_resolved("%.3s", OBJECT_BASE, &resolved) ||
      malbolge_guest_format_sink_init(&sink, output,
                                      (uint32_t)sizeof(output)) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_execute_memory(&sink, &view, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      malbolge_guest_format_finish(&sink) != MALBOLGE_GUEST_RUNTIME_VALID ||
      !same_text(output, "abc")) {
    return 1;
  }
  if (!build_resolved("%.4s", OBJECT_BASE, &resolved) ||
      malbolge_guest_format_sink_init(&sink, output,
                                      (uint32_t)sizeof(output)) !=
          MALBOLGE_GUEST_RUNTIME_VALID) {
    return 2;
  }
  sink.required = UINT32_C(2);
  output[0] = 's';
  output[1] = 'e';
  output[2] = '\0';
  if (malbolge_guest_format_execute_memory(&sink, &view, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      sink.required != UINT32_C(2) || !same_text(output, "se")) {
    return 3;
  }
  return 0;
}

static int test_count_storage(void) {
  uint8_t object[24] = {0};
  const uint8_t expected32[4] = {UINT8_C(42), UINT8_C(0), UINT8_C(0),
                                 UINT8_C(0)};
  const uint8_t expected64[8] = {UINT8_C(0xff), UINT8_C(0xff), UINT8_C(0xff),
                                 UINT8_C(0xff), UINT8_C(0),    UINT8_C(0),
                                 UINT8_C(0),    UINT8_C(0)};
  char output[1];
  MalbolgeGuestMemoryView view = {object, (uint32_t)sizeof(object),
                                  OBJECT_BASE};
  MalbolgeGuestResolvedFormatArgument resolved;
  MalbolgeGuestFormatSink sink;

  if (malbolge_guest_format_sink_init(
          &sink, output, (uint32_t)sizeof(output)) !=
      MALBOLGE_GUEST_RUNTIME_VALID) {
    return 1;
  }
  sink.required = UINT32_C(42);
  if (!build_resolved("%n", OBJECT_BASE + UINT32_C(4), &resolved) ||
      malbolge_guest_format_execute_memory(&sink, &view, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      sink.required != UINT32_C(42) ||
      !same_bytes(object + UINT32_C(4), expected32, UINT32_C(4))) {
    return 2;
  }
  sink.required = UINT32_C(0x80000000);
  if (!build_resolved("%n", OBJECT_BASE + UINT32_C(4), &resolved) ||
      malbolge_guest_format_execute_memory(&sink, &view, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      !same_bytes(object + UINT32_C(4), expected32, UINT32_C(4))) {
    return 3;
  }
  sink.required = UINT32_MAX;
  if (!build_resolved("%lln", OBJECT_BASE + UINT32_C(8), &resolved) ||
      malbolge_guest_format_execute_memory(&sink, &view, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      !same_bytes(object + UINT32_C(8), expected64, UINT32_C(8))) {
    return 4;
  }
  return 0;
}

static int test_count_width_and_atomic_failure(void) {
  uint8_t object[16] = {UINT8_C(0xa5), UINT8_C(0xa5), UINT8_C(0xa5),
                        UINT8_C(0xa5), UINT8_C(0xa5), UINT8_C(0xa5),
                        UINT8_C(0xa5), UINT8_C(0xa5), UINT8_C(0xa5),
                        UINT8_C(0xa5), UINT8_C(0xa5), UINT8_C(0xa5),
                        UINT8_C(0xa5), UINT8_C(0xa5), UINT8_C(0xa5),
                        UINT8_C(0xa5)};
  uint8_t original[16];
  char output[1];
  MalbolgeGuestMemoryView view = {object, (uint32_t)sizeof(object),
                                  OBJECT_BASE};
  MalbolgeGuestResolvedFormatArgument resolved;
  MalbolgeGuestFormatSink sink;
  uint32_t index = UINT32_C(0);

  while (index < (uint32_t)sizeof(object)) {
    original[index] = object[index];
    ++index;
  }
  if (malbolge_guest_format_sink_init(
          &sink, output, (uint32_t)sizeof(output)) !=
      MALBOLGE_GUEST_RUNTIME_VALID) {
    return 1;
  }
  sink.required = UINT32_C(127);
  if (!build_resolved("%hhn", OBJECT_BASE, &resolved) ||
      malbolge_guest_format_execute_memory(&sink, &view, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      object[0] != UINT8_C(127)) {
    return 2;
  }
  object[0] = original[0];
  sink.required = UINT32_C(128);
  if (malbolge_guest_format_execute_memory(&sink, &view, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      !same_bytes(object, original, (uint32_t)sizeof(object))) {
    return 3;
  }
  sink.required = UINT32_C(7);
  if (!build_resolved("%hn", OBJECT_BASE + UINT32_C(1), &resolved) ||
      malbolge_guest_format_execute_memory(&sink, &view, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      !same_bytes(object, original, (uint32_t)sizeof(object))) {
    return 4;
  }
  if (!build_resolved("%w16n", OBJECT_BASE + UINT32_C(2), &resolved) ||
      malbolge_guest_format_execute_memory(&sink, &view, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      object[2] != UINT8_C(7) || object[3] != UINT8_C(0)) {
    return 5;
  }
  return 0;
}

static int test_pointer_and_view_rejection(void) {
  uint8_t object[8] = {'o', 'k', '\0', 0, 0, 0, 0, 0};
  uint8_t original[8];
  char output[8] = "seed";
  MalbolgeGuestMemoryView view = {object, (uint32_t)sizeof(object),
                                  OBJECT_BASE};
  MalbolgeGuestResolvedFormatArgument resolved;
  MalbolgeGuestFormatSink sink;
  uint32_t index = UINT32_C(0);

  while (index < (uint32_t)sizeof(object)) {
    original[index] = object[index];
    ++index;
  }
  if (malbolge_guest_memory_view_validate(&view) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      !build_resolved("%s", UINT32_C(0), &resolved) ||
      malbolge_guest_format_sink_init(&sink, output,
                                      (uint32_t)sizeof(output)) !=
          MALBOLGE_GUEST_RUNTIME_VALID) {
    return 1;
  }
  if (malbolge_guest_format_execute_memory(&sink, &view, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      sink.required != UINT32_C(0) ||
      !same_bytes(object, original, (uint32_t)sizeof(object))) {
    return 2;
  }
  if (!build_resolved("%s", OBJECT_BASE + (uint32_t)sizeof(object),
                      &resolved) ||
      malbolge_guest_format_execute_memory(&sink, &view, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT) {
    return 3;
  }
  if (!build_resolved("%ls", OBJECT_BASE, &resolved) ||
      malbolge_guest_format_execute_memory(&sink, &view, &resolved) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT) {
    return 4;
  }
  view.encoded_base = UINT32_MAX;
  view.extent = UINT32_C(2);
  if (malbolge_guest_memory_view_validate(&view) !=
      MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT) {
    return 5;
  }
  view.extent = UINT32_C(1);
  if (malbolge_guest_memory_view_validate(&view) !=
      MALBOLGE_GUEST_RUNTIME_VALID) {
    return 6;
  }
  return 0;
}

int main(void) {
  const int string_result = test_narrow_string();
  const int precision_result = test_precision_bounds();
  const int count_result = test_count_storage();
  const int width_result = test_count_width_and_atomic_failure();
  const int rejection_result = test_pointer_and_view_rejection();

  if (string_result != 0) {
    return 10 + string_result;
  }
  if (precision_result != 0) {
    return 20 + precision_result;
  }
  if (count_result != 0) {
    return 30 + count_result;
  }
  if (width_result != 0) {
    return 40 + width_result;
  }
  return rejection_result == 0 ? 0 : 50 + rejection_result;
}
