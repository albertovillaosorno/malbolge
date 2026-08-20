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
//   - Negative evidence for contracted but unavailable zeroed allocation.
// - Must-Not:
//   - Resolve allocation through host libc or bypass guest startup binding.
// - Allows:
//   - Inputs: one fixed zeroed-allocation request.
//   - Outputs: one source-located MALBOLGE-LIBC-001 diagnostic.
//   - Side effects: none because validation rejects before lowering.
// - Split-When:
//   - Another unavailable allocation API needs independent evidence.
// - Merge-When:
//   - Another fixture owns this exact calloc rejection.
// - Summary:
//   - Contracted-unavailable calloc fixture.
// - Description:
//   - Proves implemented wrapper source does not imply source availability.
// - Usage:
//   - Consumed by guest-libc source preflight regression tests.
// - Defaults:
//   - Rejection occurs at the calloc reference in this source file.
//

//! Guest zeroed allocation remains gated on startup integration.

#include <stdlib.h>

void *libc_calloc_probe(void)
{
    return calloc(4U, 4U);
}
