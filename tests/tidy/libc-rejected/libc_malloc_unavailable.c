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
//   - Negative evidence for a contracted but unavailable guest heap routine.
// - Must-Not:
//   - Depend on a host allocator or conflate unavailability with prohibition.
// - Allows:
//   - Inputs: one fixed allocation size.
//   - Outputs: one source-located MALBOLGE-LIBC-001 diagnostic.
//   - Side effects: none because validation rejects the call before lowering.
// - Split-When:
//   - Split when another unavailable library family needs independent evidence.
// - Merge-When:
//   - Merge when another fixture owns this exact allocation rejection.
// - Summary:
//   - Contracted-unavailable malloc fixture.
// - Description:
//   - Proves allocation is future guest functionality, not a host shortcut.
// - Usage:
//   - Consumed by guest-libc source preflight regression tests.
// - Defaults:
//   - Rejection occurs at the malloc reference in this source file.
//

//! Contracted allocation remains unavailable until the guest runtime exists.

#include <stdlib.h>

void *libc_malloc_probe(void)
{
    return malloc(16U);
}
