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
//   - Stable token representation and semantic admission for C23 printf
//     grammar.
// - Must-Not:
//   - Consume variadic arguments, emit output bytes, or call host formatting.
// - Allows:
//   - Inputs: one null-terminated narrow format string and a byte offset.
//   - Outputs: one token plus deterministic directive-admission status.
//   - Side effects: caller-owned token publication only after complete parsing.
// - Split-When:
//   - Variadic decoding or conversion execution gains independent ownership.
// - Merge-When:
//   - Public formatting directly owns this exact grammar projection.
// - Summary:
//   - Tokenizes and admits C23 printf directives without coupling to va_list.
// - Description:
//   - Preserves dynamic fields, specific-width modifiers, and closed
//     specifiers.
// - Usage:
//   - Repeated from offset zero until an end token is returned.
// - Defaults:
//   - Decimal overflow, incomplete directives, and unknown specifiers fail
//     closed.
//

//! Deterministic C23 printf-format tokenizer below guest variadic decoding.

#ifndef MALBOLGE_GUEST_FORMAT_PARSE_H
#define MALBOLGE_GUEST_FORMAT_PARSE_H

#include "guest_format.h"
#include "guest_varargs.h"

#include <stdint.h>

#define MALBOLGE_GUEST_FORMAT_TOKEN_END UINT32_C(0)
#define MALBOLGE_GUEST_FORMAT_TOKEN_LITERAL UINT32_C(1)
#define MALBOLGE_GUEST_FORMAT_TOKEN_CONVERSION UINT32_C(2)

#define MALBOLGE_GUEST_FORMAT_FIELD_OMITTED UINT32_C(0)
#define MALBOLGE_GUEST_FORMAT_FIELD_LITERAL UINT32_C(1)
#define MALBOLGE_GUEST_FORMAT_FIELD_ARGUMENT UINT32_C(2)

#define MALBOLGE_GUEST_FORMAT_LENGTH_NONE UINT32_C(0)
#define MALBOLGE_GUEST_FORMAT_LENGTH_HH UINT32_C(1)
#define MALBOLGE_GUEST_FORMAT_LENGTH_H UINT32_C(2)
#define MALBOLGE_GUEST_FORMAT_LENGTH_L UINT32_C(3)
#define MALBOLGE_GUEST_FORMAT_LENGTH_LL UINT32_C(4)
#define MALBOLGE_GUEST_FORMAT_LENGTH_J UINT32_C(5)
#define MALBOLGE_GUEST_FORMAT_LENGTH_Z UINT32_C(6)
#define MALBOLGE_GUEST_FORMAT_LENGTH_T UINT32_C(7)
#define MALBOLGE_GUEST_FORMAT_LENGTH_LONG_DOUBLE UINT32_C(8)
#define MALBOLGE_GUEST_FORMAT_LENGTH_WIDTH UINT32_C(9)
#define MALBOLGE_GUEST_FORMAT_LENGTH_FAST_WIDTH UINT32_C(10)

#define MALBOLGE_GUEST_FORMAT_CONVERSION_PERCENT UINT32_C(1)
#define MALBOLGE_GUEST_FORMAT_CONVERSION_BINARY UINT32_C(2)
#define MALBOLGE_GUEST_FORMAT_CONVERSION_BINARY_UPPER UINT32_C(3)
#define MALBOLGE_GUEST_FORMAT_CONVERSION_DECIMAL UINT32_C(4)
#define MALBOLGE_GUEST_FORMAT_CONVERSION_INTEGER UINT32_C(5)
#define MALBOLGE_GUEST_FORMAT_CONVERSION_OCTAL UINT32_C(6)
#define MALBOLGE_GUEST_FORMAT_CONVERSION_UNSIGNED UINT32_C(7)
#define MALBOLGE_GUEST_FORMAT_CONVERSION_HEX UINT32_C(8)
#define MALBOLGE_GUEST_FORMAT_CONVERSION_HEX_UPPER UINT32_C(9)
#define MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_HEX UINT32_C(10)
#define MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_HEX_UPPER UINT32_C(11)
#define MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_EXP UINT32_C(12)
#define MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_EXP_UPPER UINT32_C(13)
#define MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_FIXED UINT32_C(14)
#define MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_FIXED_UPPER UINT32_C(15)
#define MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_GENERAL UINT32_C(16)
#define MALBOLGE_GUEST_FORMAT_CONVERSION_FLOAT_GENERAL_UPPER UINT32_C(17)
#define MALBOLGE_GUEST_FORMAT_CONVERSION_CHARACTER UINT32_C(18)
#define MALBOLGE_GUEST_FORMAT_CONVERSION_STRING UINT32_C(19)
#define MALBOLGE_GUEST_FORMAT_CONVERSION_POINTER UINT32_C(20)
#define MALBOLGE_GUEST_FORMAT_CONVERSION_COUNT UINT32_C(21)

typedef struct MalbolgeGuestFormatDirective {
  uint32_t flags;
  uint32_t width_kind;
  uint32_t width;
  uint32_t precision_kind;
  uint32_t precision;
  uint32_t length;
  uint32_t length_bits;
  uint32_t conversion;
} MalbolgeGuestFormatDirective;

typedef struct MalbolgeGuestFormatToken {
  uint32_t kind;
  uint32_t offset;
  uint32_t length;
  uint32_t next_offset;
  MalbolgeGuestFormatDirective directive;
} MalbolgeGuestFormatToken;

MalbolgeGuestRuntimeStatus
malbolge_guest_format_parse_next(const char *format, uint32_t offset,
                                 MalbolgeGuestFormatToken *token);
MalbolgeGuestRuntimeStatus malbolge_guest_format_directive_validate(
    const MalbolgeGuestFormatDirective *directive);
MalbolgeGuestRuntimeStatus malbolge_guest_format_argument_kind(
    const MalbolgeGuestFormatDirective *directive, uint32_t *kind);

#endif
