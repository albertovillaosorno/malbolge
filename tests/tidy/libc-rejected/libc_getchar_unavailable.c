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
//   - Negative evidence for contracted but unavailable guest byte input.
// - Must-Not:
//   - Resolve input through host stdio or claim target lowering already exists.
// - Allows:
//   - Inputs: one guest byte-input call.
//   - Outputs: one source-located MALBOLGE-LIBC-001 diagnostic.
//   - Side effects: none because validation rejects before lowering.
// - Split-When:
//   - Another unavailable byte-input API needs independent evidence.
// - Merge-When:
//   - Another fixture owns this exact getchar rejection.
// - Summary:
//   - Contracted-unavailable getchar fixture.
// - Description:
//   - Proves wrapper source does not imply target-intrinsic availability.
// - Usage:
//   - Consumed by guest-libc source preflight regression tests.
// - Defaults:
//   - Rejection occurs at the getchar reference in this source file.
//

//! Guest byte input remains unavailable until intrinsic lowering exists.

#include <stdio.h>

int libc_getchar_probe(void)
{
    return getchar();
}
