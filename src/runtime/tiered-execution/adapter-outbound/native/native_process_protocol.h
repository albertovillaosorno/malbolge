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
//   - The C23 mirror of native process wire version-one constants and offsets.
// - Must-Not:
//   - Spawn processes, allocate executable memory, invoke code, or admit data.
// - Allows:
//   - Inputs: byte buffers exchanged through the persistent process session.
//   - Outputs: stable constants plus little-endian scalar helpers.
//   - Side effects: none.
// - Split-When:
//   - A new MBNPM or MBNPC wire version requires incompatible declarations.
// - Merge-When:
//   - Generated Rust/C protocol declarations become the sole wire authority.
// - Summary:
//   - Gives the future C worker one reviewed mirror of Rust process framing.
// - Description:
//   - Keeps child implementations from duplicating tags and byte offsets.
// - Usage:
//   - Included by strict C conformance tests and the future native worker.
// - Defaults:
//   - Helpers perform only bytewise little-endian access with no trust checks.

#ifndef MALBOLGE_NATIVE_PROCESS_PROTOCOL_H
#define MALBOLGE_NATIVE_PROCESS_PROTOCOL_H

#include <stddef.h>

#include "native_region_abi.h"

#define MB_NATIVE_PROCESS_MAGIC_BYTES 8U
#define MB_NATIVE_PROCESS_FRAME_LENGTH_BYTES 8U

#define MB_NATIVE_PROCESS_CALL_REQUEST_FIXED_BYTES 77U
#define MB_NATIVE_PROCESS_CALL_RESPONSE_FIXED_BYTES 74U

#define MB_NATIVE_PROCESS_MEMORY_ALLOCATE_REQUEST_BYTES 26U
#define MB_NATIVE_PROCESS_MEMORY_COPY_REQUEST_FIXED_BYTES 42U
#define MB_NATIVE_PROCESS_MEMORY_PROTECT_REQUEST_BYTES 34U
#define MB_NATIVE_PROCESS_MEMORY_RELEASE_REQUEST_BYTES 33U
#define MB_NATIVE_PROCESS_MEMORY_SYNC_REQUEST_BYTES 33U

#define MB_NATIVE_PROCESS_MEMORY_FAILURE_RESPONSE_BYTES 14U
#define MB_NATIVE_PROCESS_MEMORY_MAPPING_RESPONSE_BYTES 35U
#define MB_NATIVE_PROCESS_MEMORY_COPY_RESPONSE_FIXED_BYTES 26U
#define MB_NATIVE_PROCESS_MEMORY_RELEASE_RESPONSE_BYTES 10U
#define MB_NATIVE_PROCESS_MEMORY_SYNC_RESPONSE_BYTES 34U

#define MB_NATIVE_PROCESS_MAGIC_OFFSET 0U
#define MB_NATIVE_PROCESS_COMMAND_OFFSET 8U
#define MB_NATIVE_PROCESS_OUTCOME_OFFSET 9U

#define MB_NATIVE_PROCESS_CALL_REQUEST_MAPPING_ID_OFFSET 8U
#define MB_NATIVE_PROCESS_CALL_REQUEST_ENTRY_OFFSET 16U
#define MB_NATIVE_PROCESS_CALL_REQUEST_MEMORY_WORDS_OFFSET 24U
#define MB_NATIVE_PROCESS_CALL_REQUEST_INPUT_LEN_OFFSET 32U
#define MB_NATIVE_PROCESS_CALL_REQUEST_OUTPUT_CAPACITY_OFFSET 40U
#define MB_NATIVE_PROCESS_CALL_REQUEST_INPUT_CONSUMED_OFFSET 48U
#define MB_NATIVE_PROCESS_CALL_REQUEST_OUTPUT_LEN_OFFSET 56U
#define MB_NATIVE_PROCESS_CALL_REQUEST_ACCUMULATOR_OFFSET 64U
#define MB_NATIVE_PROCESS_CALL_REQUEST_CODE_POINTER_OFFSET 68U
#define MB_NATIVE_PROCESS_CALL_REQUEST_DATA_POINTER_OFFSET 72U
#define MB_NATIVE_PROCESS_CALL_REQUEST_TERMINATION_OFFSET 76U

#define MB_NATIVE_PROCESS_CALL_RESPONSE_MAPPING_ID_OFFSET 8U
#define MB_NATIVE_PROCESS_CALL_RESPONSE_MEMORY_WORDS_OFFSET 16U
#define MB_NATIVE_PROCESS_CALL_RESPONSE_INPUT_LEN_OFFSET 24U
#define MB_NATIVE_PROCESS_CALL_RESPONSE_OUTPUT_CAPACITY_OFFSET 32U
#define MB_NATIVE_PROCESS_CALL_RESPONSE_INPUT_CONSUMED_OFFSET 40U
#define MB_NATIVE_PROCESS_CALL_RESPONSE_OUTPUT_LEN_OFFSET 48U
#define MB_NATIVE_PROCESS_CALL_RESPONSE_ACCUMULATOR_OFFSET 56U
#define MB_NATIVE_PROCESS_CALL_RESPONSE_CODE_POINTER_OFFSET 60U
#define MB_NATIVE_PROCESS_CALL_RESPONSE_DATA_POINTER_OFFSET 64U
#define MB_NATIVE_PROCESS_CALL_RESPONSE_TERMINATION_OFFSET 68U
#define MB_NATIVE_PROCESS_CALL_RESPONSE_STATUS_OFFSET 69U
#define MB_NATIVE_PROCESS_CALL_RESPONSE_POINTER_FLAG_OFFSET 73U

enum mb_native_process_memory_command {
    MB_NATIVE_PROCESS_MEMORY_ALLOCATE = 0,
    MB_NATIVE_PROCESS_MEMORY_COPY = 1,
    MB_NATIVE_PROCESS_MEMORY_PROTECT = 2,
    MB_NATIVE_PROCESS_MEMORY_RELEASE = 3,
    MB_NATIVE_PROCESS_MEMORY_SYNCHRONIZE = 4
};

enum mb_native_process_memory_outcome {
    MB_NATIVE_PROCESS_MEMORY_SUCCESS = 0,
    MB_NATIVE_PROCESS_MEMORY_FAILURE = 1
};

enum mb_native_process_memory_permission {
    MB_NATIVE_PROCESS_MEMORY_READ_EXECUTE = 0,
    MB_NATIVE_PROCESS_MEMORY_READ_WRITE = 1
};

static const mb_u8
    MB_NATIVE_PROCESS_CALL_MAGIC[MB_NATIVE_PROCESS_MAGIC_BYTES] = {
    'M', 'B', 'N', 'P', 'C', '1', 0, 0
};

static const mb_u8
    MB_NATIVE_PROCESS_MEMORY_MAGIC[MB_NATIVE_PROCESS_MAGIC_BYTES] = {
    'M', 'B', 'N', 'P', 'M', '1', 0, 0
};

static inline mb_u32 mb_native_process_read_u32(const mb_u8 *bytes)
{
    return (mb_u32)bytes[0]
        | ((mb_u32)bytes[1] << 8U)
        | ((mb_u32)bytes[2] << 16U)
        | ((mb_u32)bytes[3] << 24U);
}

static inline mb_u64 mb_native_process_read_u64(const mb_u8 *bytes)
{
    mb_u64 value = 0U;
    for (size_t index = 0U; index < 8U; ++index) {
        value |= (mb_u64)bytes[index] << (index * 8U);
    }
    return value;
}

static inline void mb_native_process_write_u32(mb_u8 *bytes, mb_u32 value)
{
    for (size_t index = 0U; index < 4U; ++index) {
        bytes[index] = (mb_u8)(value >> (index * 8U));
    }
}

static inline void mb_native_process_write_u64(mb_u8 *bytes, mb_u64 value)
{
    for (size_t index = 0U; index < 8U; ++index) {
        bytes[index] = (mb_u8)(value >> (index * 8U));
    }
}

#endif
