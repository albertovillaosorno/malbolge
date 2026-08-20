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
//   - Negative evidence for contracted but unavailable guest deallocation.
// - Must-Not:
//   - Resolve deallocation through host libc or bypass guest startup binding.
// - Allows:
//   - Inputs: one pointer selected by guest allocation semantics.
//   - Outputs: one source-located MALBOLGE-LIBC-001 diagnostic.
//   - Side effects: none because validation rejects before lowering.
// - Split-When:
//   - Another unavailable allocation API needs independent evidence.
// - Merge-When:
//   - Another fixture owns this exact free rejection.
// - Summary:
//   - Contracted-unavailable free fixture.
// - Description:
//   - Proves implemented wrapper source does not imply source availability.
// - Usage:
//   - Consumed by guest-libc source preflight regression tests.
// - Defaults:
//   - Rejection occurs at the free reference in this source file.
//

//! Guest deallocation remains gated on startup integration.

#include <stdlib.h>

void *libc_free_probe(void *pointer)
{
    return free(pointer), pointer;
}
