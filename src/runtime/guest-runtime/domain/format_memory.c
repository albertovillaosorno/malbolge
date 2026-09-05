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
//   - Fail-closed guest-object dereference for resolved %s and %n conversions.
// - Must-Not:
//   - Treat encoded guest pointers as host addresses or call host formatting.
// - Allows:
//   - Inputs: one proven guest object, resolved directive, and bounded sink.
//   - Outputs: narrow-string text or canonical little-endian count bytes.
//   - Side effects: sink bytes for %s; guest-object bytes for successful %n.
// - Split-When:
//   - Wide-string conversion or another guest-memory family gains new policy.
// - Merge-When:
//   - Full formatter owns the same pointer proof and conversion transaction.
// - Summary:
//   - Maps logical offset-plus-one pointers into one caller-proven live object.
// - Description:
//   - Validates full access before publishing either output or count storage.
// - Usage:
//   - Runs only after format argument resolution has consumed promoted values.
// - Defaults:
//   - Narrow %s and integer %n are the only admitted memory conversions.
//

//! Bounded guest-memory execution for narrow strings and printf count stores.

#include "guest_format_memory.h"

#include <limits.h>
#include <stddef.h>
#include <stdint.h>

static int view_end(const MalbolgeGuestMemoryView *view, uint32_t *end) {
  const uint32_t base = view->encoded_base - UINT32_C(1);

  if (view->extent == UINT32_C(0) || base == UINT32_MAX ||
      view->extent - UINT32_C(1) > UINT32_MAX - UINT32_C(1) - base) {
    return 0;
  }
  *end = base + view->extent;
  return 1;
}

MalbolgeGuestRuntimeStatus malbolge_guest_memory_view_validate(
    const MalbolgeGuestMemoryView *view) {
  uint32_t end = UINT32_C(0);

  if (view == NULL || view->bytes == NULL ||
      view->encoded_base == UINT32_C(0) || !view_end(view, &end) ||
      end == UINT32_C(0)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  return MALBOLGE_GUEST_RUNTIME_VALID;
}

static int expected_pointer_argument(
    const MalbolgeGuestResolvedFormatArgument *resolved) {
  uint32_t kind = MALBOLGE_GUEST_VARARG_NONE;

  return resolved != NULL && resolved->argument.high == UINT64_C(0) &&
         resolved->argument.low <= UINT32_MAX &&
         resolved->directive.width_kind !=
             MALBOLGE_GUEST_FORMAT_FIELD_ARGUMENT &&
         resolved->directive.precision_kind !=
             MALBOLGE_GUEST_FORMAT_FIELD_ARGUMENT &&
         malbolge_guest_format_argument_kind(&resolved->directive, &kind) ==
             MALBOLGE_GUEST_RUNTIME_VALID &&
         kind == MALBOLGE_GUEST_VARARG_POINTER32 &&
         resolved->argument_kind == MALBOLGE_GUEST_VARARG_POINTER32;
}

static int pointer_offset(const MalbolgeGuestMemoryView *view,
                          uint32_t encoded_pointer, uint32_t width,
                          uint32_t alignment, uint32_t *offset) {
  const uint32_t base = view->encoded_base - UINT32_C(1);
  const uint32_t address = encoded_pointer - UINT32_C(1);
  uint32_t end = UINT32_C(0);

  if (encoded_pointer == UINT32_C(0) || offset == NULL || alignment == 0U ||
      malbolge_guest_memory_view_validate(view) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      !view_end(view, &end) || address < base || address >= end ||
      address % alignment != UINT32_C(0) || width > end - address) {
    return 0;
  }
  *offset = address - base;
  return 1;
}

static uint32_t resolved_width(const MalbolgeGuestFormatDirective *directive) {
  return directive->width_kind == MALBOLGE_GUEST_FORMAT_FIELD_LITERAL
             ? directive->width
             : UINT32_C(0);
}

static uint32_t
resolved_precision(const MalbolgeGuestFormatDirective *directive) {
  return directive->precision_kind == MALBOLGE_GUEST_FORMAT_FIELD_LITERAL
             ? directive->precision
             : MALBOLGE_GUEST_FORMAT_PRECISION_OMITTED;
}

static MalbolgeGuestRuntimeStatus
execute_string(MalbolgeGuestFormatSink *sink, MalbolgeGuestMemoryView *view,
               const MalbolgeGuestResolvedFormatArgument *resolved) {
  const uint32_t pointer = (uint32_t)resolved->argument.low;
  const uint32_t precision = resolved_precision(&resolved->directive);
  uint32_t offset = UINT32_C(0);
  uint32_t available = UINT32_C(0);
  uint32_t length = UINT32_C(0);

  if (sink == NULL ||
      resolved->directive.length != MALBOLGE_GUEST_FORMAT_LENGTH_NONE ||
      !pointer_offset(view, pointer, UINT32_C(1), UINT32_C(1), &offset)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  available = view->extent - offset;
  while (length < available &&
         (precision == MALBOLGE_GUEST_FORMAT_PRECISION_OMITTED ||
          length < precision) &&
         view->bytes[offset + length] != UINT8_C(0)) {
    ++length;
  }
  if ((precision == MALBOLGE_GUEST_FORMAT_PRECISION_OMITTED ||
       length < precision) &&
      (length == available || view->bytes[offset + length] != UINT8_C(0))) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  return malbolge_guest_format_bytes(
      sink, (const char *)(view->bytes + offset), length,
      resolved_width(&resolved->directive), resolved->directive.flags);
}

static int count_shape(const MalbolgeGuestFormatDirective *directive,
                       uint32_t *width) {
  if (directive->length == MALBOLGE_GUEST_FORMAT_LENGTH_HH) {
    *width = UINT32_C(1);
  } else if (directive->length == MALBOLGE_GUEST_FORMAT_LENGTH_H) {
    *width = UINT32_C(2);
  } else if (directive->length == MALBOLGE_GUEST_FORMAT_LENGTH_LL ||
             directive->length == MALBOLGE_GUEST_FORMAT_LENGTH_J ||
             ((directive->length == MALBOLGE_GUEST_FORMAT_LENGTH_WIDTH ||
               directive->length == MALBOLGE_GUEST_FORMAT_LENGTH_FAST_WIDTH) &&
              directive->length_bits == UINT32_C(64))) {
    *width = UINT32_C(8);
  } else if (directive->length == MALBOLGE_GUEST_FORMAT_LENGTH_NONE ||
             directive->length == MALBOLGE_GUEST_FORMAT_LENGTH_L ||
             directive->length == MALBOLGE_GUEST_FORMAT_LENGTH_Z ||
             directive->length == MALBOLGE_GUEST_FORMAT_LENGTH_T ||
             ((directive->length == MALBOLGE_GUEST_FORMAT_LENGTH_WIDTH ||
               directive->length == MALBOLGE_GUEST_FORMAT_LENGTH_FAST_WIDTH) &&
              directive->length_bits == UINT32_C(32))) {
    *width = UINT32_C(4);
  } else if ((directive->length == MALBOLGE_GUEST_FORMAT_LENGTH_WIDTH ||
              directive->length == MALBOLGE_GUEST_FORMAT_LENGTH_FAST_WIDTH) &&
             directive->length_bits == UINT32_C(8)) {
    *width = UINT32_C(1);
  } else if ((directive->length == MALBOLGE_GUEST_FORMAT_LENGTH_WIDTH ||
              directive->length == MALBOLGE_GUEST_FORMAT_LENGTH_FAST_WIDTH) &&
             directive->length_bits == UINT32_C(16)) {
    *width = UINT32_C(2);
  } else {
    return 0;
  }
  return 1;
}

static uint64_t signed_maximum(uint32_t width) {
  if (width == UINT32_C(8)) {
    return UINT64_C(0x7fffffffffffffff);
  }
  return (UINT64_C(1) << (width * UINT32_C(8) - UINT32_C(1))) - UINT64_C(1);
}

static MalbolgeGuestRuntimeStatus
execute_count(MalbolgeGuestFormatSink *sink, MalbolgeGuestMemoryView *view,
              const MalbolgeGuestResolvedFormatArgument *resolved) {
  const uint32_t pointer = (uint32_t)resolved->argument.low;
  uint32_t width = UINT32_C(0);
  uint32_t offset = UINT32_C(0);
  uint32_t index = UINT32_C(0);

  if (sink == NULL || !count_shape(&resolved->directive, &width) ||
      (uint64_t)sink->required > signed_maximum(width) ||
      !pointer_offset(view, pointer, width, width, &offset)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  while (index < width) {
    view->bytes[offset + index] = (uint8_t)(
        (uint64_t)sink->required >> (index * UINT32_C(8)));
    ++index;
  }
  return MALBOLGE_GUEST_RUNTIME_VALID;
}

MalbolgeGuestRuntimeStatus malbolge_guest_format_execute_memory(
    MalbolgeGuestFormatSink *sink, MalbolgeGuestMemoryView *view,
    const MalbolgeGuestResolvedFormatArgument *resolved) {
  if (sink == NULL || view == NULL || !expected_pointer_argument(resolved)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  if (resolved->directive.conversion ==
      MALBOLGE_GUEST_FORMAT_CONVERSION_STRING) {
    return execute_string(sink, view, resolved);
  }
  if (resolved->directive.conversion ==
      MALBOLGE_GUEST_FORMAT_CONVERSION_COUNT) {
    return execute_count(sink, view, resolved);
  }
  return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
}
