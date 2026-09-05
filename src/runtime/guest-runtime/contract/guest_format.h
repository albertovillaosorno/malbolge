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
//   - Typed locale-free formatting primitives below the public printf surface.
// - Must-Not:
//   - Parse format strings, consume va_list, float-format, or use host libc.
// - Allows:
//   - Inputs: fixed-width values and explicit formatting options.
//   - Outputs: snprintf-style bounded bytes plus would-have-written byte count.
//   - Side effects: caller-owned destination bytes only.
// - Split-When:
//   - Floating formatting or parsing gains independent runtime ownership.
// - Merge-When:
//   - The complete guest formatter owns these typed primitives directly.
// - Summary:
//   - Deterministic typed kernel for future bounded guest formatting.
// - Description:
//   - Separates exact conversion/padding from varargs and parsing.
// - Usage:
//   - Consumed by runtime tests and future snprintf/vsnprintf implementation.
// - Defaults:
//   - Capacity includes the reserved terminating null byte when nonzero.
//

//! Typed deterministic formatting kernel below public snprintf/vsnprintf.

#ifndef MALBOLGE_GUEST_FORMAT_H
#define MALBOLGE_GUEST_FORMAT_H

#include "guest_runtime.h"

#include <stdint.h>

#define MALBOLGE_GUEST_FORMAT_PRECISION_OMITTED UINT32_MAX
#define MALBOLGE_GUEST_FORMAT_LEFT UINT32_C(1)
#define MALBOLGE_GUEST_FORMAT_PLUS UINT32_C(2)
#define MALBOLGE_GUEST_FORMAT_SPACE UINT32_C(4)
#define MALBOLGE_GUEST_FORMAT_ALTERNATE UINT32_C(8)
#define MALBOLGE_GUEST_FORMAT_ZERO UINT32_C(16)
#define MALBOLGE_GUEST_FORMAT_UPPERCASE UINT32_C(32)

typedef struct MalbolgeGuestFormatSink {
  char *destination;
  uint32_t capacity;
  uint32_t required;
} MalbolgeGuestFormatSink;

typedef struct MalbolgeGuestIntegerFormat {
  uint32_t flags;
  uint32_t width;
  uint32_t precision;
  uint32_t base;
} MalbolgeGuestIntegerFormat;

MalbolgeGuestRuntimeStatus
malbolge_guest_format_sink_init(MalbolgeGuestFormatSink *sink,
                                char *destination, uint32_t capacity);
MalbolgeGuestRuntimeStatus
malbolge_guest_format_finish(MalbolgeGuestFormatSink *sink);
MalbolgeGuestRuntimeStatus
malbolge_guest_format_unsigned(MalbolgeGuestFormatSink *sink, uint64_t value,
                               const MalbolgeGuestIntegerFormat *format);
MalbolgeGuestRuntimeStatus
malbolge_guest_format_signed_decimal(MalbolgeGuestFormatSink *sink,
                                     int64_t value,
                                     const MalbolgeGuestIntegerFormat *format);
MalbolgeGuestRuntimeStatus
malbolge_guest_format_bytes(MalbolgeGuestFormatSink *sink, const char *value,
                            uint32_t length, uint32_t width, uint32_t flags);
MalbolgeGuestRuntimeStatus
malbolge_guest_format_string(MalbolgeGuestFormatSink *sink, const char *value,
                             uint32_t width, uint32_t precision,
                             uint32_t flags);
MalbolgeGuestRuntimeStatus
malbolge_guest_format_character(MalbolgeGuestFormatSink *sink, uint8_t value,
                                uint32_t width, uint32_t flags);

#endif
