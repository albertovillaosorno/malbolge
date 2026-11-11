// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Strict C conformance evidence for MBNPM1 and MBNPC1 declarations.
// - Must-Not:
//   - Spawn a child, map executable memory, or invoke native code.
// - Allows:
//   - Inputs: tracked native process protocol and ABI headers.
//   - Outputs: zero when constants and little-endian helpers match v1 framing.
//   - Side effects: stack-only byte-buffer mutation.
// - Split-When:
//   - Another protocol version needs independent C conformance evidence.
// - Merge-When:
//   - A generated cross-language protocol test supersedes this mirror check.
// - Summary:
//   - Locks child-side C framing to the reviewed Rust version-one wire shape.
// - Description:
//   - Exercises exact fixed sizes, tags, magic bytes, and scalar byte order.
// - Usage:
//   - Compiled and run with repository-pinned Clang from pytest.
// - Defaults:
//   - Performs no platform operation beyond ordinary process execution.
//

//! C conformance harness for native process wire version one.

#include <string.h>

#include "native_process_protocol.h"

_Static_assert(MB_NATIVE_PROCESS_CALL_REQUEST_FIXED_BYTES == 77U,
    "MBNPC1 request prefix drifted");
_Static_assert(MB_NATIVE_PROCESS_CALL_RESPONSE_FIXED_BYTES == 74U,
    "MBNPC1 response prefix drifted");
_Static_assert(MB_NATIVE_PROCESS_MEMORY_ALLOCATE_REQUEST_BYTES == 26U,
    "MBNPM1 allocate request drifted");
_Static_assert(MB_NATIVE_PROCESS_MEMORY_COPY_REQUEST_FIXED_BYTES == 42U,
    "MBNPM1 copy request drifted");
_Static_assert(MB_NATIVE_PROCESS_MEMORY_PROTECT_REQUEST_BYTES == 34U,
    "MBNPM1 protect request drifted");
_Static_assert(MB_NATIVE_PROCESS_MEMORY_RELEASE_REQUEST_BYTES == 33U,
    "MBNPM1 release request drifted");
_Static_assert(MB_NATIVE_PROCESS_MEMORY_SYNC_REQUEST_BYTES == 33U,
    "MBNPM1 sync request drifted");
_Static_assert(MB_NATIVE_PROCESS_MEMORY_FAILURE_RESPONSE_BYTES == 14U,
    "MBNPM1 failure response drifted");
_Static_assert(MB_NATIVE_PROCESS_MEMORY_MAPPING_RESPONSE_BYTES == 35U,
    "MBNPM1 mapping response drifted");
_Static_assert(MB_NATIVE_PROCESS_MEMORY_COPY_RESPONSE_FIXED_BYTES == 26U,
    "MBNPM1 copy response drifted");
_Static_assert(MB_NATIVE_PROCESS_MEMORY_RELEASE_RESPONSE_BYTES == 10U,
    "MBNPM1 release response drifted");
_Static_assert(MB_NATIVE_PROCESS_MEMORY_SYNC_RESPONSE_BYTES == 34U,
    "MBNPM1 sync response drifted");
_Static_assert(MB_NATIVE_PROCESS_CALL_REQUEST_MAPPING_ID_OFFSET == 8U,
    "MBNPC1 request mapping offset drifted");
_Static_assert(MB_NATIVE_PROCESS_CALL_REQUEST_ENTRY_OFFSET == 16U,
    "MBNPC1 request entry offset drifted");
_Static_assert(MB_NATIVE_PROCESS_CALL_REQUEST_MEMORY_WORDS_OFFSET == 24U,
    "MBNPC1 request memory count offset drifted");
_Static_assert(MB_NATIVE_PROCESS_CALL_REQUEST_TERMINATION_OFFSET == 76U,
    "MBNPC1 request termination offset drifted");
_Static_assert(MB_NATIVE_PROCESS_CALL_RESPONSE_MAPPING_ID_OFFSET == 8U,
    "MBNPC1 response mapping offset drifted");
_Static_assert(MB_NATIVE_PROCESS_CALL_RESPONSE_MEMORY_WORDS_OFFSET == 16U,
    "MBNPC1 response memory count offset drifted");
_Static_assert(MB_NATIVE_PROCESS_CALL_RESPONSE_TERMINATION_OFFSET == 68U,
    "MBNPC1 response termination offset drifted");
_Static_assert(MB_NATIVE_PROCESS_CALL_RESPONSE_STATUS_OFFSET == 69U,
    "MBNPC1 response status offset drifted");
_Static_assert(MB_NATIVE_PROCESS_CALL_RESPONSE_POINTER_FLAG_OFFSET == 73U,
    "MBNPC1 response pointer flag offset drifted");

_Static_assert(sizeof(struct mb_native_region_state) == 80U,
    "native region state size drifted");
_Static_assert(offsetof(struct mb_native_region_state, memory) == 0U,
    "native region memory field offset drifted");
_Static_assert(offsetof(struct mb_native_region_state, memory_words) == 8U,
    "native region memory_words field offset drifted");
_Static_assert(offsetof(struct mb_native_region_state, input) == 16U,
    "native region input field offset drifted");
_Static_assert(offsetof(struct mb_native_region_state, input_len) == 24U,
    "native region input_len field offset drifted");
_Static_assert(offsetof(struct mb_native_region_state, input_consumed) == 32U,
    "native region input_consumed field offset drifted");
_Static_assert(offsetof(struct mb_native_region_state, output) == 40U,
    "native region output field offset drifted");
_Static_assert(offsetof(struct mb_native_region_state, output_capacity) == 48U,
    "native region output_capacity field offset drifted");
_Static_assert(offsetof(struct mb_native_region_state, output_len) == 56U,
    "native region output_len field offset drifted");
_Static_assert(offsetof(struct mb_native_region_state, accumulator) == 64U,
    "native region accumulator field offset drifted");
_Static_assert(offsetof(struct mb_native_region_state, code_pointer) == 68U,
    "native region code_pointer field offset drifted");
_Static_assert(offsetof(struct mb_native_region_state, data_pointer) == 72U,
    "native region data_pointer field offset drifted");
_Static_assert(offsetof(struct mb_native_region_state, termination) == 76U,
    "native region termination field offset drifted");

static int check_magic(void)
{
    static const mb_u8 expected_call[8] = {
        'M', 'B', 'N', 'P', 'C', '1', 0, 0
    };
    static const mb_u8 expected_memory[8] = {
        'M', 'B', 'N', 'P', 'M', '1', 0, 0
    };
    return memcmp(
        MB_NATIVE_PROCESS_CALL_MAGIC,
        expected_call,
        sizeof(expected_call)) == 0
        && memcmp(
            MB_NATIVE_PROCESS_MEMORY_MAGIC,
            expected_memory,
            sizeof(expected_memory)) == 0;
}

static int check_scalars(void)
{
    mb_u8 bytes[8] = {0};
    mb_native_process_write_u64(bytes, MB_U64(0x0123456789abcdef));
    if (mb_native_process_read_u64(bytes)
        != MB_U64(0x0123456789abcdef)) {
        return 0;
    }
    mb_native_process_write_u32(bytes, MB_U32(0x89abcdef));
    return mb_native_process_read_u32(bytes) == MB_U32(0x89abcdef);
}

static int check_tags(void)
{
    return MB_NATIVE_PROCESS_MEMORY_ALLOCATE == 0
        && MB_NATIVE_PROCESS_MEMORY_COPY == 1
        && MB_NATIVE_PROCESS_MEMORY_PROTECT == 2
        && MB_NATIVE_PROCESS_MEMORY_RELEASE == 3
        && MB_NATIVE_PROCESS_MEMORY_SYNCHRONIZE == 4
        && MB_NATIVE_PROCESS_MEMORY_SUCCESS == 0
        && MB_NATIVE_PROCESS_MEMORY_FAILURE == 1
        && MB_NATIVE_PROCESS_MEMORY_READ_EXECUTE == 0
        && MB_NATIVE_PROCESS_MEMORY_READ_WRITE == 1
        && MB_NATIVE_APPLIED == 0
        && MB_NATIVE_GUARD_MISS == 1
        && MB_NATIVE_INVALID_ARGUMENT == 2
        && MB_NATIVE_TERMINATION_RUNNING == 0
        && MB_NATIVE_TERMINATION_HALT_INSTRUCTION == 1
        && MB_NATIVE_TERMINATION_NON_GRAPHICAL_CELL == 2;
}

int main(void)
{
    return check_magic() && check_scalars() && check_tags() ? 0 : 1;
}
