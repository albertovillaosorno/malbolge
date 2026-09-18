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
//   - The canonical C declarations for native region ABI revision 1.
// - Must-Not:
//   - Allocate executable memory, invoke machine code, or define guest
//   - semantics.
// - Allows:
//   - Inputs: C23 compilation and an optional POSIX x86-64 ABI-bridge define.
//   - Outputs: exact scalar, status, call-frame, and bridge-entry declarations.
//   - Side effects: none.
// - Split-When:
//   - Another native ABI revision requires incompatible declarations.
// - Merge-When:
//   - One generated ABI authority safely owns Rust and C layout declarations.
// - Summary:
//   - Shares one C call-frame contract across bootstrap code and host evidence.
// - Description:
//   - Keeps development harnesses from duplicating native layout authority.
// - Usage:
//   - Embedded by Rust bootstrap lowering or included by tracked C harnesses.
// - Defaults:
//   - The POSIX Windows-x64 bridge typedef is opt-in and never implied.

#ifndef MALBOLGE_NATIVE_REGION_ABI_H
#define MALBOLGE_NATIVE_REGION_ABI_H

typedef unsigned char mb_u8;
typedef unsigned int mb_u32;
typedef unsigned long long mb_u64;

#define MB_U8(value) ((mb_u8)(value))
#define MB_U32(value) ((mb_u32)(value##U))
#define MB_U64(value) ((mb_u64)(value##ULL))

static_assert(sizeof(mb_u8) == 1, "8-bit byte required");
static_assert(sizeof(mb_u32) == 4, "32-bit word required");
static_assert(sizeof(mb_u64) == 8, "64-bit ABI integer required");

enum mb_native_status {
    MB_NATIVE_APPLIED = 0,
    MB_NATIVE_GUARD_MISS = 1,
    MB_NATIVE_INVALID_ARGUMENT = 2
};

struct mb_native_region_state {
    mb_u32 *memory;
    mb_u64 memory_words;
    const mb_u8 *input;
    mb_u64 input_len;
    mb_u64 input_consumed;
    mb_u8 *output;
    mb_u64 output_capacity;
    mb_u64 output_len;
    mb_u32 accumulator;
    mb_u32 code_pointer;
    mb_u32 data_pointer;
    mb_u8 termination;
};

#if defined(MB_NATIVE_POSIX_WINDOWS_X64_BRIDGE)
typedef int (__attribute__((ms_abi)) *mb_native_entry_fn)(
    struct mb_native_region_state *);
#endif

#endif
