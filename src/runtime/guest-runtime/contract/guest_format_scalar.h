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
//   - Execution of resolved non-dereferencing, non-floating conversions.
// - Must-Not:
//   - Dereference guest pointers, execute %n, float-format, or inspect va_list.
// - Allows:
//   - Inputs: admitted/resolved scalar format argument and bounded format sink.
//   - Outputs: deterministic integer/character/pointer/percent bytes and count
//     updates.
//   - Side effects: bounded sink writes only through the typed formatting
//     kernel.
// - Split-When:
//   - Pointer-dereferencing or floating conversions gain independent execution
//     policy.
// - Merge-When:
//   - Full formatter execution can own all conversion families without
//     ambiguity.
// - Summary:
//   - Executes d/i/u/o/x/X/b/B/c/p/% after promotion-aware resolution.
// - Description:
//   - Narrows hh/h/w8/w16 by bits and sign-extends without host signed
//     overflow.
// - Usage:
//   - Called after atomic dynamic-field and promoted-argument resolution.
// - Defaults:
//   - Unsupported conversion families fail closed without intentional fallback.
//

//! Deterministic resolved scalar printf execution below public snprintf.

#ifndef MALBOLGE_GUEST_FORMAT_SCALAR_H
#define MALBOLGE_GUEST_FORMAT_SCALAR_H

#include "guest_format.h"
#include "guest_format_args.h"

MalbolgeGuestRuntimeStatus malbolge_guest_format_execute_scalar(
    MalbolgeGuestFormatSink *sink,
    const MalbolgeGuestResolvedFormatArgument *resolved);

#endif
