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
//   - Negative evidence for contracted but unavailable guest byte output.
// - Must-Not:
//   - Resolve output through host stdio or claim target lowering exists.
// - Allows:
//   - Inputs: one fixed guest byte-output call.
//   - Outputs: one source-located MALBOLGE-LIBC-001 diagnostic.
//   - Side effects: none because validation rejects before lowering.
// - Split-When:
//   - Another unavailable byte-output API needs independent evidence.
// - Merge-When:
//   - Another fixture owns this exact putchar rejection.
// - Summary:
//   - Contracted-unavailable putchar fixture.
// - Description:
//   - Proves wrapper source does not imply target-intrinsic availability.
// - Usage:
//   - Consumed by guest-libc source preflight regression tests.
// - Defaults:
//   - Rejection occurs at the putchar reference in this source file.
//

//! Guest byte output remains unavailable until intrinsic lowering exists.

#include <stdio.h>

int libc_putchar_probe(void)
{
    return putchar(65);
}
