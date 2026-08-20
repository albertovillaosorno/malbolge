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
//   - Exact declarations for contracted guest heap routines.
// - Must-Not:
//   - Claim those routines are executable before the guest allocator exists.
// - Allows:
//   - Inputs: C source requiring stable allocation signatures.
//   - Outputs: declarations only; source preflight owns availability rejection.
//   - Side effects: none.
// - Split-When:
//   - Split when another allocation family gains independent contract status.
// - Merge-When:
//   - Merge when another header owns these exact guest allocation signatures.
// - Summary:
//   - Declaration-only version-one guest allocation contract.
// - Description:
//   - Preserves exact C signatures while lane 8 owns executable heap semantics.
// - Usage:
//   - Included by guest source; calls fail preflight until runtime completion.
// - Defaults:
//   - No host allocation routine is a fallback.
//

//! Declaration-only heap surface for malbolge-libc-v1.

#ifndef MALBOLGE_GUEST_LIBC_STDLIB_H
#define MALBOLGE_GUEST_LIBC_STDLIB_H

#include <stddef.h>

void *malloc(size_t size);
void *calloc(size_t count, size_t size);
void *realloc(void *pointer, size_t size);
void free(void *pointer);

#endif
