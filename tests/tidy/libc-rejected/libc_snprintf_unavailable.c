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
//   - Negative evidence for contracted but unavailable bounded formatting.
// - Must-Not:
//   - Treat the internal typed format kernel as complete public snprintf.
// - Allows:
//   - Inputs: one empty bounded-formatting call.
//   - Outputs: one source-located MALBOLGE-LIBC-001 diagnostic.
//   - Side effects: none because validation rejects before lowering.
// - Split-When:
//   - Another unavailable formatting API needs independent evidence.
// - Merge-When:
//   - Another fixture owns this exact snprintf rejection.
// - Summary:
//   - Contracted-unavailable snprintf fixture.
// - Description:
//   - Proves typed format-kernel progress does not imply source availability.
// - Usage:
//   - Consumed by guest-libc source preflight regression tests.
// - Defaults:
//   - Rejection occurs at the snprintf reference in this source file.
//

//! Public bounded formatting stays gated until the full C23 surface exists.

#include <stdio.h>

int libc_snprintf_probe(void)
{
    return snprintf((char *)0, 0U, "");
}
