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
//   - Atomic resolution of admitted printf directives against guest vararg
//   bytes.
// - Must-Not:
//   - Execute conversions, dereference guest pointers, or use host va_list
//   state.
// - Allows:
//   - Inputs: admitted directive plus canonical promoted-argument cursor.
//   - Outputs: resolved width/precision and one raw promoted conversion
//   argument.
//   - Side effects: cursor/result publication only after every required read
//   passes.
// - Split-When:
//   - Pointer-backed string/count access gains an independent memory-view
//   policy.
// - Merge-When:
//   - Full formatter execution owns this exact argument-resolution transaction.
// - Summary:
//   - Consumes dynamic fields and conversion arguments without partial
//   advancement.
// - Description:
//   - Applies C negative-width and negative-precision rules in uint32
//   arithmetic.
// - Usage:
//   - Runs after format directive admission and before typed conversion
//   execution.
// - Defaults:
//   - Percent conversion consumes no argument and publishes a NONE argument
//   kind.
//

//! Atomic guest format-argument resolution above the canonical vararg cursor.

#ifndef MALBOLGE_GUEST_FORMAT_ARGS_H
#define MALBOLGE_GUEST_FORMAT_ARGS_H

#include "guest_format_parse.h"
#include "guest_varargs.h"

#include <stdint.h>

typedef struct MalbolgeGuestResolvedFormatArgument {
  MalbolgeGuestFormatDirective directive;
  uint32_t argument_kind;
  MalbolgeGuestVarargValue argument;
} MalbolgeGuestResolvedFormatArgument;

MalbolgeGuestRuntimeStatus malbolge_guest_format_resolve_argument(
    MalbolgeGuestVarargCursor *cursor,
    const MalbolgeGuestFormatDirective *directive,
    MalbolgeGuestResolvedFormatArgument *result);

#endif
