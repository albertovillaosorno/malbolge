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
//   - Deterministic execution of resolved binary floating printf conversions.
// - Must-Not:
//   - Use host floating arithmetic, host formatting, locale, or native va_list.
// - Allows:
//   - Inputs: canonical promoted floating bits and resolved format directives.
//   - Outputs: bounded hexadecimal floating text plus exact sink accounting.
//   - Side effects: caller-owned sink bytes after complete geometry admission.
// - Split-When:
//   - Decimal or binary128 formatting requires independent algorithm policy.
// - Merge-When:
//   - Complete formatter execution owns this exact floating conversion policy.
// - Summary:
//   - Executes C23 %a/%A for malbolge-c32-v1 binary64 without host FPU use.
// - Description:
//   - Uses normalized bit geometry and ABI-fixed nearest-ties-even rounding.
// - Usage:
//   - Called after parser admission and atomic promoted-argument resolution.
// - Defaults:
//   - Long-double and decimal floating conversions remain fail-closed.
//

//! Deterministic binary64 hexadecimal formatting below public snprintf.

#ifndef MALBOLGE_GUEST_FORMAT_FLOAT_H
#define MALBOLGE_GUEST_FORMAT_FLOAT_H

#include "guest_format_args.h"

MalbolgeGuestRuntimeStatus malbolge_guest_format_execute_hex_float(
    MalbolgeGuestFormatSink *sink,
    const MalbolgeGuestResolvedFormatArgument *resolved);

#endif
