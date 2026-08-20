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
//   - Canonical cursor semantics for promoted malbolge-c32-v1 variadic objects.
// - Must-Not:
//   - Expose host va_list layout, infer registers, or consume native stack
//     state.
// - Allows:
//   - Inputs: one guest argument-byte block, decoded logical address, and kind.
//   - Outputs: raw canonical value bits plus an advanced fail-closed cursor.
//   - Side effects: caller-owned cursor/result publication after complete
//     reads.
// - Split-When:
//   - Public C va_list bridging needs an independently versioned compiler ABI.
// - Merge-When:
//   - Format execution directly owns the canonical promoted-argument cursor.
// - Summary:
//   - Decodes naturally aligned promoted variadic objects from guest bytes.
// - Description:
//   - Uses guest logical alignment and little-endian object representation
//     only.
// - Usage:
//   - Compiler/runtime bridges decode hidden-frame variadic_begin to its
//     zero-based logical byte address before initialization.
// - Defaults:
//   - Failed, overflowing, or out-of-range reads do not advance or publish.
//

//! Canonical guest variadic-argument cursor independent of host va_list.

#ifndef MALBOLGE_GUEST_VARARGS_H
#define MALBOLGE_GUEST_VARARGS_H

#include "guest_runtime.h"

#include <stdint.h>

#define MALBOLGE_GUEST_VARARG_NONE UINT32_C(0)
#define MALBOLGE_GUEST_VARARG_I32 UINT32_C(1)
#define MALBOLGE_GUEST_VARARG_U32 UINT32_C(2)
#define MALBOLGE_GUEST_VARARG_I64 UINT32_C(3)
#define MALBOLGE_GUEST_VARARG_U64 UINT32_C(4)
#define MALBOLGE_GUEST_VARARG_F64 UINT32_C(5)
#define MALBOLGE_GUEST_VARARG_F128 UINT32_C(6)
#define MALBOLGE_GUEST_VARARG_POINTER32 UINT32_C(7)

typedef struct MalbolgeGuestVarargValue {
  uint64_t low;
  uint64_t high;
} MalbolgeGuestVarargValue;

typedef struct MalbolgeGuestVarargCursor {
  const uint8_t *block;
  uint32_t block_size;
  uint32_t linear_address;
  uint32_t offset;
} MalbolgeGuestVarargCursor;

MalbolgeGuestRuntimeStatus
malbolge_guest_varargs_init(MalbolgeGuestVarargCursor *cursor,
                            const uint8_t *block, uint32_t block_size,
                            uint32_t linear_address);
MalbolgeGuestRuntimeStatus
malbolge_guest_varargs_validate(const MalbolgeGuestVarargCursor *cursor);
MalbolgeGuestRuntimeStatus
malbolge_guest_varargs_read(MalbolgeGuestVarargCursor *cursor, uint32_t kind,
                            MalbolgeGuestVarargValue *result);

#endif
