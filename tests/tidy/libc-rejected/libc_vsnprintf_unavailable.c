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
//   - Negative evidence for contracted but unavailable variadic formatting.
// - Must-Not:
//   - Treat the internal typed format kernel as complete public vsnprintf.
// - Allows:
//   - Inputs: one guest va_list forwarded to bounded formatting.
//   - Outputs: one source-located MALBOLGE-LIBC-001 diagnostic.
//   - Side effects: none because validation rejects before lowering.
// - Split-When:
//   - Another unavailable formatting API needs independent evidence.
// - Merge-When:
//   - Another fixture owns this exact vsnprintf rejection.
// - Summary:
//   - Contracted-unavailable vsnprintf fixture.
// - Description:
//   - Proves typed format-kernel progress does not imply source availability.
// - Usage:
//   - Consumed by guest-libc source preflight regression tests.
// - Defaults:
//   - Rejection occurs at the vsnprintf reference in this source file.
//

//! Public vsnprintf still needs source va_list, guest memory, and floats.

#include <stdio.h>

int libc_vsnprintf_probe(va_list arguments)
{
    return vsnprintf((char *)0, 0U, "", arguments);
}
