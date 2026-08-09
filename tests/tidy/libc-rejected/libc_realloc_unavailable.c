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
//   - Negative evidence for contracted but unavailable guest reallocation.
// - Must-Not:
//   - Resolve allocation through host libc or bypass guest startup binding.
// - Allows:
//   - Inputs: one pointer and fixed positive resize request.
//   - Outputs: one source-located MALBOLGE-LIBC-001 diagnostic.
//   - Side effects: none because validation rejects before lowering.
// - Split-When:
//   - Another unavailable allocation API needs independent evidence.
// - Merge-When:
//   - Another fixture owns this exact realloc rejection.
// - Summary:
//   - Contracted-unavailable realloc fixture.
// - Description:
//   - Proves implemented wrapper source does not imply source availability.
// - Usage:
//   - Consumed by guest-libc source preflight regression tests.
// - Defaults:
//   - Rejection occurs at the realloc reference in this source file.
//

//! Guest reallocation remains gated on startup integration.

#include <stdlib.h>

void *libc_realloc_probe(void *pointer)
{
    return realloc(pointer, 16U);
}
