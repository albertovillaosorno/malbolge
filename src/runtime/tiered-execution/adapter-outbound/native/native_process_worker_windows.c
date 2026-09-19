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
//   - Windows child-side MBNPM1 executable memory and MBNPC1 native invocation.
// - Must-Not:
//   - Admit lifecycle reports, verify guest semantics, or select native code.
// - Allows:
//   - Inputs: length-framed MBNPM1/MBNPC1 requests from one parent session.
//   - Outputs: untrusted protocol evidence consumed by safe Rust admission.
//   - Side effects: process-local VirtualAlloc/VirtualProtect/VirtualFree and
//     native entry calls.
// - Split-When:
//   - Another host API or process protocol needs independent policy.
// - Merge-When:
//   - One portable worker can own identical W^X and ABI behavior on all hosts.
// - Summary:
//   - Implements the concrete Windows W^X and foreign-call process boundary.
// - Description:
//   - Mapping ownership remains in this child; Rust remains admission
//     authority.
// - Usage:
//   - Spawn persistently through NativeProcessSession on Windows
//     x86-64/AArch64.
// - Defaults:
//   - Malformed framing exits; platform API failures return opaque codes.
//

//! Windows worker for process-isolated native executable memory and calls.

#if !defined(_WIN32)
#error "native Windows worker requires a Windows target"
#endif
#if !defined(__x86_64__) && !defined(__aarch64__)
#error "native Windows worker supports only x86-64 and AArch64"
#endif

#include "native_process_protocol.h"

typedef __UINTPTR_TYPE__ mb_uintptr;
typedef void *mb_win_handle;
typedef unsigned long mb_win_dword;
typedef int mb_win_bool;

#define MB_WIN_FALSE 0
#define MB_WIN_STD_INPUT_HANDLE ((mb_win_dword)-10)
#define MB_WIN_STD_OUTPUT_HANDLE ((mb_win_dword)-11)
#define MB_WIN_MEM_COMMIT 0x1000UL
#define MB_WIN_MEM_RESERVE 0x2000UL
#define MB_WIN_MEM_RELEASE 0x8000UL
#define MB_WIN_PAGE_READWRITE 0x04UL
#define MB_WIN_PAGE_EXECUTE_READ 0x20UL
#define MB_SIZE_MAX ((size_t)~(size_t)0)
#define MB_WIN_DWORD_MAX ((mb_win_dword)~(mb_win_dword)0)

__declspec(dllimport) mb_win_handle __stdcall GetCurrentProcess(void);
__declspec(dllimport) mb_win_dword __stdcall GetLastError(void);
__declspec(dllimport) mb_win_handle __stdcall GetProcessHeap(void);
__declspec(dllimport) mb_win_handle __stdcall GetStdHandle(mb_win_dword);
__declspec(dllimport) void *__stdcall HeapAlloc(
    mb_win_handle, mb_win_dword, size_t);
__declspec(dllimport) void *__stdcall HeapReAlloc(
    mb_win_handle, mb_win_dword, void *, size_t);
__declspec(dllimport) mb_win_bool __stdcall HeapFree(
    mb_win_handle, mb_win_dword, void *);
__declspec(dllimport) mb_win_bool __stdcall ReadFile(
    mb_win_handle, void *, mb_win_dword, mb_win_dword *, void *);
__declspec(dllimport) mb_win_bool __stdcall WriteFile(
    mb_win_handle, const void *, mb_win_dword, mb_win_dword *, void *);
__declspec(dllimport) void *__stdcall VirtualAlloc(
    void *, size_t, mb_win_dword, mb_win_dword);
__declspec(dllimport) mb_win_bool __stdcall VirtualProtect(
    void *, size_t, mb_win_dword, mb_win_dword *);
__declspec(dllimport) mb_win_bool __stdcall VirtualFree(
    void *, size_t, mb_win_dword);
__declspec(dllimport) mb_win_bool __stdcall FlushInstructionCache(
    mb_win_handle, const void *, size_t);

typedef int (*mb_native_entry_fn)(struct mb_native_region_state *);

static void *mb_worker_alloc(size_t len)
{
    return HeapAlloc(GetProcessHeap(), 0U, len);
}

static void *mb_worker_realloc(void *memory, size_t len)
{
    if (memory == NULL) {
        return mb_worker_alloc(len);
    }
    return HeapReAlloc(GetProcessHeap(), 0U, memory, len);
}

static void mb_worker_free(void *memory)
{
    if (memory != NULL) {
        (void)HeapFree(GetProcessHeap(), 0U, memory);
    }
}

static void *mb_worker_calloc(size_t count, size_t width)
{
    if (count != 0U && width > MB_SIZE_MAX / count) {
        return NULL;
    }
    const size_t len = count * width;
    mb_u8 *memory = mb_worker_alloc(len);
    if (memory == NULL) {
        return NULL;
    }
    for (size_t index = 0U; index < len; ++index) {
        memory[index] = 0U;
    }
    return memory;
}

static void mb_worker_copy_bytes(
    void *destination,
    const void *source,
    size_t len)
{
    mb_u8 *to = destination;
    const mb_u8 *from = source;
    for (size_t index = 0U; index < len; ++index) {
        to[index] = from[index];
    }
}

static void mb_worker_move_bytes(
    void *destination,
    const void *source,
    size_t len)
{
    mb_u8 *to = destination;
    const mb_u8 *from = source;
    if ((mb_uintptr)to < (mb_uintptr)from) {
        mb_worker_copy_bytes(to, from, len);
        return;
    }
    for (size_t index = len; index != 0U; --index) {
        to[index - 1U] = from[index - 1U];
    }
}

static int mb_worker_compare_bytes(
    const void *left,
    const void *right,
    size_t len)
{
    const mb_u8 *lhs = left;
    const mb_u8 *rhs = right;
    for (size_t index = 0U; index < len; ++index) {
        if (lhs[index] != rhs[index]) {
            return lhs[index] < rhs[index] ? -1 : 1;
        }
    }
    return 0;
}

struct mb_worker_mapping {
    mb_u64 id;
    mb_u8 *base;
    size_t len;
    enum mb_native_process_memory_permission permission;
};

struct mb_worker_state {
    struct mb_worker_mapping *mappings;
    size_t count;
    size_t capacity;
    mb_u64 next_id;
};

enum mb_worker_failure {
    MB_WORKER_INVALID_REQUEST = 1,
    MB_WORKER_MAPPING_NOT_FOUND = 2,
    MB_WORKER_PLATFORM_FAILURE = 3,
    MB_WORKER_ALLOCATION_FAILURE = 4,
    MB_WORKER_ALIGNMENT_FAILURE = 5
};

static int mb_worker_write_frame(const mb_u8 *payload, size_t len);
static int mb_worker_handle_memory(
    struct mb_worker_state *worker,
    const mb_u8 *request,
    size_t request_len,
    mb_u8 **response,
    size_t *response_len);
static int mb_worker_handle_call(
    struct mb_worker_state *worker,
    const mb_u8 *request,
    size_t request_len,
    mb_u8 **response,
    size_t *response_len);

static int mb_worker_size_from_u64(mb_u64 value, size_t *result)
{
    if (value > (mb_u64)MB_SIZE_MAX) {
        return 0;
    }
    *result = (size_t)value;
    return 1;
}

static int mb_worker_add_size(size_t left, size_t right, size_t *result)
{
    if (right > MB_SIZE_MAX - left) {
        return 0;
    }
    *result = left + right;
    return 1;
}

static int mb_worker_mul_size(size_t left, size_t right, size_t *result)
{
    if (left != 0U && right > MB_SIZE_MAX / left) {
        return 0;
    }
    *result = left * right;
    return 1;
}

static mb_u32 mb_worker_platform_code(void)
{
    const mb_win_dword value = GetLastError();
    return value != 0U
        ? (mb_u32)value
        : (mb_u32)MB_WORKER_PLATFORM_FAILURE;
}

static struct mb_worker_mapping *mb_worker_find_mapping(
    struct mb_worker_state *worker,
    mb_u64 id)
{
    for (size_t index = 0U; index < worker->count; ++index) {
        if (worker->mappings[index].id == id) {
            return &worker->mappings[index];
        }
    }
    return NULL;
}

static int mb_worker_reserve_mapping(struct mb_worker_state *worker)
{
    if (worker->count < worker->capacity) {
        return 1;
    }
    const size_t new_capacity = worker->capacity == 0U
        ? 4U
        : worker->capacity * 2U;
    if (new_capacity < worker->capacity
        || new_capacity > MB_SIZE_MAX / sizeof(*worker->mappings)) {
        return 0;
    }
    void *grown = mb_worker_realloc(
        worker->mappings,
        new_capacity * sizeof(*worker->mappings));
    if (grown == NULL) {
        return 0;
    }
    worker->mappings = grown;
    worker->capacity = new_capacity;
    return 1;
}

static void mb_worker_remove_mapping(
    struct mb_worker_state *worker,
    const struct mb_worker_mapping *mapping)
{
    const size_t index = (size_t)(mapping - worker->mappings);
    if (index + 1U < worker->count) {
        mb_worker_move_bytes(
            &worker->mappings[index],
            &worker->mappings[index + 1U],
            (worker->count - index - 1U) * sizeof(*worker->mappings));
    }
    worker->count -= 1U;
}

static void mb_worker_release_all(struct mb_worker_state *worker)
{
    for (size_t index = 0U; index < worker->count; ++index) {
        (void)VirtualFree(worker->mappings[index].base, 0U, MB_WIN_MEM_RELEASE);
    }
    mb_worker_free(worker->mappings);
    worker->mappings = NULL;
    worker->count = 0U;
    worker->capacity = 0U;
}

static int mb_worker_memory_failure(
    mb_u8 command,
    mb_u32 code,
    mb_u8 **response,
    size_t *response_len)
{
    mb_u8 *bytes = mb_worker_alloc(
        MB_NATIVE_PROCESS_MEMORY_FAILURE_RESPONSE_BYTES);
    if (bytes == NULL) {
        return 0;
    }
    mb_worker_copy_bytes(
        bytes,
        MB_NATIVE_PROCESS_MEMORY_MAGIC,
        MB_NATIVE_PROCESS_MAGIC_BYTES);
    bytes[MB_NATIVE_PROCESS_COMMAND_OFFSET] = command;
    bytes[MB_NATIVE_PROCESS_OUTCOME_OFFSET] = MB_NATIVE_PROCESS_MEMORY_FAILURE;
    mb_native_process_write_u32(&bytes[10], code);
    *response = bytes;
    *response_len = MB_NATIVE_PROCESS_MEMORY_FAILURE_RESPONSE_BYTES;
    return 1;
}

static mb_u8 *mb_worker_memory_success(
    mb_u8 command,
    size_t len)
{
    mb_u8 *bytes = mb_worker_calloc(len, 1U);
    if (bytes == NULL) {
        return NULL;
    }
    mb_worker_copy_bytes(
        bytes,
        MB_NATIVE_PROCESS_MEMORY_MAGIC,
        MB_NATIVE_PROCESS_MAGIC_BYTES);
    bytes[MB_NATIVE_PROCESS_COMMAND_OFFSET] = command;
    bytes[MB_NATIVE_PROCESS_OUTCOME_OFFSET] = MB_NATIVE_PROCESS_MEMORY_SUCCESS;
    return bytes;
}

static int mb_worker_handle_allocate(
    struct mb_worker_state *worker,
    const mb_u8 *request,
    size_t request_len,
    mb_u8 **response,
    size_t *response_len)
{
    if (request_len != MB_NATIVE_PROCESS_MEMORY_ALLOCATE_REQUEST_BYTES) {
        return mb_worker_memory_failure(
            MB_NATIVE_PROCESS_MEMORY_ALLOCATE,
            MB_WORKER_INVALID_REQUEST,
            response,
            response_len);
    }
    size_t byte_len = 0U;
    size_t alignment = 0U;
    if (!mb_worker_size_from_u64(
            mb_native_process_read_u64(&request[9]),
            &byte_len)
        || !mb_worker_size_from_u64(
            mb_native_process_read_u64(&request[17]), &alignment)
        || byte_len == 0U
        || alignment == 0U
        || request[25] != MB_NATIVE_PROCESS_MEMORY_READ_WRITE) {
        return mb_worker_memory_failure(
            MB_NATIVE_PROCESS_MEMORY_ALLOCATE,
            MB_WORKER_INVALID_REQUEST,
            response,
            response_len);
    }
    void *memory = VirtualAlloc(
        NULL,
        byte_len,
        MB_WIN_MEM_RESERVE | MB_WIN_MEM_COMMIT,
        MB_WIN_PAGE_READWRITE);
    if (memory == NULL) {
        return mb_worker_memory_failure(
            MB_NATIVE_PROCESS_MEMORY_ALLOCATE,
            mb_worker_platform_code(),
            response,
            response_len);
    }
    if (((mb_uintptr)memory % alignment) != 0U) {
        (void)VirtualFree(memory, 0U, MB_WIN_MEM_RELEASE);
        return mb_worker_memory_failure(
            MB_NATIVE_PROCESS_MEMORY_ALLOCATE,
            MB_WORKER_ALIGNMENT_FAILURE,
            response,
            response_len);
    }
    if (!mb_worker_reserve_mapping(worker)) {
        (void)VirtualFree(memory, 0U, MB_WIN_MEM_RELEASE);
        return mb_worker_memory_failure(
            MB_NATIVE_PROCESS_MEMORY_ALLOCATE,
            MB_WORKER_ALLOCATION_FAILURE,
            response,
            response_len);
    }
    if (worker->next_id == 0U) {
        (void)VirtualFree(memory, 0U, MB_WIN_MEM_RELEASE);
        return mb_worker_memory_failure(
            MB_NATIVE_PROCESS_MEMORY_ALLOCATE,
            MB_WORKER_ALLOCATION_FAILURE,
            response,
            response_len);
    }
    const mb_u64 id = worker->next_id;
    worker->next_id += 1U;
    struct mb_worker_mapping *const mapping =
        &worker->mappings[worker->count];
    mapping->id = id;
    mapping->base = memory;
    mapping->len = byte_len;
    mapping->permission = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    worker->count += 1U;

    mb_u8 *bytes = mb_worker_memory_success(
        MB_NATIVE_PROCESS_MEMORY_ALLOCATE,
        MB_NATIVE_PROCESS_MEMORY_MAPPING_RESPONSE_BYTES);
    if (bytes == NULL) {
        return 0;
    }
    mb_native_process_write_u64(&bytes[10], id);
    mb_native_process_write_u64(&bytes[18], (mb_u64)(mb_uintptr)memory);
    mb_native_process_write_u64(&bytes[26], (mb_u64)byte_len);
    bytes[34] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    *response = bytes;
    *response_len = MB_NATIVE_PROCESS_MEMORY_MAPPING_RESPONSE_BYTES;
    return 1;
}

static int mb_worker_request_mapping(
    struct mb_worker_state *worker,
    const mb_u8 *request,
    struct mb_worker_mapping **mapping)
{
    const mb_u64 id = mb_native_process_read_u64(&request[9]);
    struct mb_worker_mapping *found = mb_worker_find_mapping(worker, id);
    size_t reported_len = 0U;
    if (found == NULL
        || mb_native_process_read_u64(&request[17])
            != (mb_u64)(mb_uintptr)found->base
        || !mb_worker_size_from_u64(
            mb_native_process_read_u64(&request[25]),
            &reported_len)
        || reported_len != found->len) {
        return 0;
    }
    *mapping = found;
    return 1;
}

static int mb_worker_handle_copy(
    struct mb_worker_state *worker,
    const mb_u8 *request,
    size_t request_len,
    mb_u8 **response,
    size_t *response_len)
{
    if (request_len < MB_NATIVE_PROCESS_MEMORY_COPY_REQUEST_FIXED_BYTES) {
        return mb_worker_memory_failure(
            MB_NATIVE_PROCESS_MEMORY_COPY,
            MB_WORKER_INVALID_REQUEST,
            response,
            response_len);
    }
    struct mb_worker_mapping *mapping = NULL;
    size_t code_len = 0U;
    size_t expected_len = 0U;
    if (!mb_worker_request_mapping(worker, request, &mapping)
        || mapping->permission != MB_NATIVE_PROCESS_MEMORY_READ_WRITE
        || request[33] != MB_NATIVE_PROCESS_MEMORY_READ_WRITE
        || !mb_worker_size_from_u64(
            mb_native_process_read_u64(&request[34]),
            &code_len)
        || !mb_worker_add_size(
            MB_NATIVE_PROCESS_MEMORY_COPY_REQUEST_FIXED_BYTES,
            code_len,
            &expected_len)
        || expected_len != request_len
        || code_len > mapping->len) {
        return mb_worker_memory_failure(
            MB_NATIVE_PROCESS_MEMORY_COPY,
            MB_WORKER_MAPPING_NOT_FOUND,
            response,
            response_len);
    }
    mb_worker_copy_bytes(mapping->base, &request[42], code_len);
    size_t encoded_len = 0U;
    if (!mb_worker_add_size(26U, code_len, &encoded_len)) {
        return 0;
    }
    mb_u8 *bytes = mb_worker_memory_success(
        MB_NATIVE_PROCESS_MEMORY_COPY,
        encoded_len);
    if (bytes == NULL) {
        return 0;
    }
    mb_native_process_write_u64(&bytes[10], mapping->id);
    mb_native_process_write_u64(
        &bytes[18],
        (mb_u64)(mb_uintptr)mapping->base);
    mb_worker_copy_bytes(&bytes[26], mapping->base, code_len);
    *response = bytes;
    *response_len = encoded_len;
    return 1;
}

static int mb_worker_handle_protect(
    struct mb_worker_state *worker,
    const mb_u8 *request,
    size_t request_len,
    mb_u8 **response,
    size_t *response_len)
{
    struct mb_worker_mapping *mapping = NULL;
    if (request_len != MB_NATIVE_PROCESS_MEMORY_PROTECT_REQUEST_BYTES
        || !mb_worker_request_mapping(worker, request, &mapping)
        || mapping->permission != MB_NATIVE_PROCESS_MEMORY_READ_WRITE
        || request[33] != MB_NATIVE_PROCESS_MEMORY_READ_WRITE) {
        return mb_worker_memory_failure(
            MB_NATIVE_PROCESS_MEMORY_PROTECT,
            MB_WORKER_INVALID_REQUEST,
            response,
            response_len);
    }
    mb_win_dword old_protection = 0U;
    if (VirtualProtect(
            mapping->base,
            mapping->len,
            MB_WIN_PAGE_EXECUTE_READ,
            &old_protection) == MB_WIN_FALSE) {
        return mb_worker_memory_failure(
            MB_NATIVE_PROCESS_MEMORY_PROTECT,
            mb_worker_platform_code(),
            response,
            response_len);
    }
    if (old_protection != MB_WIN_PAGE_READWRITE) {
        return mb_worker_memory_failure(
            MB_NATIVE_PROCESS_MEMORY_PROTECT,
            MB_WORKER_PLATFORM_FAILURE,
            response,
            response_len);
    }
    mapping->permission = MB_NATIVE_PROCESS_MEMORY_READ_EXECUTE;
    mb_u8 *bytes = mb_worker_memory_success(
        MB_NATIVE_PROCESS_MEMORY_PROTECT,
        MB_NATIVE_PROCESS_MEMORY_MAPPING_RESPONSE_BYTES);
    if (bytes == NULL) {
        return 0;
    }
    mb_native_process_write_u64(&bytes[10], mapping->id);
    mb_native_process_write_u64(
        &bytes[18],
        (mb_u64)(mb_uintptr)mapping->base);
    mb_native_process_write_u64(&bytes[26], (mb_u64)mapping->len);
    bytes[34] = MB_NATIVE_PROCESS_MEMORY_READ_EXECUTE;
    *response = bytes;
    *response_len = MB_NATIVE_PROCESS_MEMORY_MAPPING_RESPONSE_BYTES;
    return 1;
}

static int mb_worker_handle_sync(
    struct mb_worker_state *worker,
    const mb_u8 *request,
    size_t request_len,
    mb_u8 **response,
    size_t *response_len)
{
    if (request_len != MB_NATIVE_PROCESS_MEMORY_SYNC_REQUEST_BYTES) {
        return mb_worker_memory_failure(
            MB_NATIVE_PROCESS_MEMORY_SYNCHRONIZE,
            MB_WORKER_INVALID_REQUEST,
            response,
            response_len);
    }
    const mb_u64 id = mb_native_process_read_u64(&request[9]);
    struct mb_worker_mapping *mapping = mb_worker_find_mapping(worker, id);
    size_t sync_len = 0U;
    const mb_u64 start = mb_native_process_read_u64(&request[17]);
    if (mapping == NULL
        || mapping->permission != MB_NATIVE_PROCESS_MEMORY_READ_EXECUTE
        || !mb_worker_size_from_u64(
            mb_native_process_read_u64(&request[25]),
            &sync_len)
        || start != (mb_u64)(mb_uintptr)mapping->base
        || sync_len != mapping->len) {
        return mb_worker_memory_failure(
            MB_NATIVE_PROCESS_MEMORY_SYNCHRONIZE,
            MB_WORKER_MAPPING_NOT_FOUND,
            response,
            response_len);
    }
    if (FlushInstructionCache(
            GetCurrentProcess(),
            mapping->base,
            sync_len) == MB_WIN_FALSE) {
        return mb_worker_memory_failure(
            MB_NATIVE_PROCESS_MEMORY_SYNCHRONIZE,
            mb_worker_platform_code(),
            response,
            response_len);
    }
    mb_u8 *bytes = mb_worker_memory_success(
        MB_NATIVE_PROCESS_MEMORY_SYNCHRONIZE,
        MB_NATIVE_PROCESS_MEMORY_SYNC_RESPONSE_BYTES);
    if (bytes == NULL) {
        return 0;
    }
    mb_native_process_write_u64(&bytes[10], mapping->id);
    mb_native_process_write_u64(&bytes[18], start);
    mb_native_process_write_u64(&bytes[26], (mb_u64)sync_len);
    *response = bytes;
    *response_len = MB_NATIVE_PROCESS_MEMORY_SYNC_RESPONSE_BYTES;
    return 1;
}

static int mb_worker_handle_release(
    struct mb_worker_state *worker,
    const mb_u8 *request,
    size_t request_len,
    mb_u8 **response,
    size_t *response_len)
{
    struct mb_worker_mapping *mapping = NULL;
    if (request_len != MB_NATIVE_PROCESS_MEMORY_RELEASE_REQUEST_BYTES
        || !mb_worker_request_mapping(worker, request, &mapping)) {
        return mb_worker_memory_failure(
            MB_NATIVE_PROCESS_MEMORY_RELEASE,
            MB_WORKER_MAPPING_NOT_FOUND,
            response,
            response_len);
    }
    if (VirtualFree(mapping->base, 0U, MB_WIN_MEM_RELEASE) == MB_WIN_FALSE) {
        return mb_worker_memory_failure(
            MB_NATIVE_PROCESS_MEMORY_RELEASE,
            mb_worker_platform_code(),
            response,
            response_len);
    }
    mb_worker_remove_mapping(worker, mapping);
    mb_u8 *bytes = mb_worker_memory_success(
        MB_NATIVE_PROCESS_MEMORY_RELEASE,
        MB_NATIVE_PROCESS_MEMORY_RELEASE_RESPONSE_BYTES);
    if (bytes == NULL) {
        return 0;
    }
    *response = bytes;
    *response_len = MB_NATIVE_PROCESS_MEMORY_RELEASE_RESPONSE_BYTES;
    return 1;
}

static int mb_worker_handle_memory(
    struct mb_worker_state *worker,
    const mb_u8 *request,
    size_t request_len,
    mb_u8 **response,
    size_t *response_len)
{
    if (request_len < 9U
        || mb_worker_compare_bytes(
            request,
            MB_NATIVE_PROCESS_MEMORY_MAGIC,
            MB_NATIVE_PROCESS_MAGIC_BYTES) != 0) {
        return 0;
    }
    switch (request[MB_NATIVE_PROCESS_COMMAND_OFFSET]) {
    case MB_NATIVE_PROCESS_MEMORY_ALLOCATE:
        return mb_worker_handle_allocate(
            worker, request, request_len, response, response_len);
    case MB_NATIVE_PROCESS_MEMORY_COPY:
        return mb_worker_handle_copy(
            worker, request, request_len, response, response_len);
    case MB_NATIVE_PROCESS_MEMORY_PROTECT:
        return mb_worker_handle_protect(
            worker, request, request_len, response, response_len);
    case MB_NATIVE_PROCESS_MEMORY_RELEASE:
        return mb_worker_handle_release(
            worker, request, request_len, response, response_len);
    case MB_NATIVE_PROCESS_MEMORY_SYNCHRONIZE:
        return mb_worker_handle_sync(
            worker, request, request_len, response, response_len);
    default:
        return mb_worker_memory_failure(
            request[MB_NATIVE_PROCESS_COMMAND_OFFSET],
            MB_WORKER_INVALID_REQUEST,
            response,
            response_len);
    }
}

static int mb_worker_decode_call_shape(
    const mb_u8 *request,
    size_t request_len,
    size_t *memory_words,
    size_t *input_len,
    size_t *output_capacity,
    size_t *memory_bytes,
    size_t *memory_end,
    size_t *input_end)
{
    if (request_len < MB_NATIVE_PROCESS_CALL_REQUEST_FIXED_BYTES
        || !mb_worker_size_from_u64(
            mb_native_process_read_u64(
                &request[MB_NATIVE_PROCESS_CALL_REQUEST_MEMORY_WORDS_OFFSET]),
            memory_words)
        || !mb_worker_size_from_u64(
            mb_native_process_read_u64(
                &request[MB_NATIVE_PROCESS_CALL_REQUEST_INPUT_LEN_OFFSET]),
            input_len)
        || !mb_worker_size_from_u64(
            mb_native_process_read_u64(
                &request[
                    MB_NATIVE_PROCESS_CALL_REQUEST_OUTPUT_CAPACITY_OFFSET]),
            output_capacity)
        || !mb_worker_mul_size(*memory_words, sizeof(mb_u32), memory_bytes)
        || !mb_worker_add_size(
            MB_NATIVE_PROCESS_CALL_REQUEST_FIXED_BYTES,
            *memory_bytes,
            memory_end)
        || !mb_worker_add_size(*memory_end, *input_len, input_end)) {
        return 0;
    }
    size_t expected = 0U;
    return mb_worker_add_size(*input_end, *output_capacity, &expected)
        && expected == request_len;
}

static int mb_worker_encode_call_response(
    mb_u64 mapping_id,
    const struct mb_native_region_state *state,
    int raw_status,
    int pointers_unchanged,
    const mb_u32 *memory,
    size_t memory_words,
    const mb_u8 *output,
    size_t output_capacity,
    mb_u8 **response,
    size_t *response_len)
{
    size_t memory_bytes = 0U;
    size_t total = 0U;
    if (!mb_worker_mul_size(memory_words, sizeof(mb_u32), &memory_bytes)
        || !mb_worker_add_size(
            MB_NATIVE_PROCESS_CALL_RESPONSE_FIXED_BYTES,
            memory_bytes,
            &total)
        || !mb_worker_add_size(total, output_capacity, &total)) {
        return 0;
    }
    mb_u8 *bytes = mb_worker_calloc(total, 1U);
    if (bytes == NULL) {
        return 0;
    }
    mb_worker_copy_bytes(
        bytes,
        MB_NATIVE_PROCESS_CALL_MAGIC,
        MB_NATIVE_PROCESS_MAGIC_BYTES);
    mb_native_process_write_u64(
        &bytes[MB_NATIVE_PROCESS_CALL_RESPONSE_MAPPING_ID_OFFSET],
        mapping_id);
    mb_native_process_write_u64(
        &bytes[MB_NATIVE_PROCESS_CALL_RESPONSE_MEMORY_WORDS_OFFSET],
        state->memory_words);
    mb_native_process_write_u64(
        &bytes[MB_NATIVE_PROCESS_CALL_RESPONSE_INPUT_LEN_OFFSET],
        state->input_len);
    mb_native_process_write_u64(
        &bytes[MB_NATIVE_PROCESS_CALL_RESPONSE_OUTPUT_CAPACITY_OFFSET],
        state->output_capacity);
    mb_native_process_write_u64(
        &bytes[MB_NATIVE_PROCESS_CALL_RESPONSE_INPUT_CONSUMED_OFFSET],
        state->input_consumed);
    mb_native_process_write_u64(
        &bytes[MB_NATIVE_PROCESS_CALL_RESPONSE_OUTPUT_LEN_OFFSET],
        state->output_len);
    mb_native_process_write_u32(
        &bytes[MB_NATIVE_PROCESS_CALL_RESPONSE_ACCUMULATOR_OFFSET],
        state->accumulator);
    mb_native_process_write_u32(
        &bytes[MB_NATIVE_PROCESS_CALL_RESPONSE_CODE_POINTER_OFFSET],
        state->code_pointer);
    mb_native_process_write_u32(
        &bytes[MB_NATIVE_PROCESS_CALL_RESPONSE_DATA_POINTER_OFFSET],
        state->data_pointer);
    bytes[MB_NATIVE_PROCESS_CALL_RESPONSE_TERMINATION_OFFSET]
        = state->termination;
    mb_native_process_write_u32(
        &bytes[MB_NATIVE_PROCESS_CALL_RESPONSE_STATUS_OFFSET],
        (mb_u32)raw_status);
    bytes[MB_NATIVE_PROCESS_CALL_RESPONSE_POINTER_FLAG_OFFSET]
        = pointers_unchanged ? 1U : 0U;
    size_t cursor = MB_NATIVE_PROCESS_CALL_RESPONSE_FIXED_BYTES;
    for (size_t index = 0U; index < memory_words; ++index) {
        mb_native_process_write_u32(&bytes[cursor], memory[index]);
        cursor += sizeof(mb_u32);
    }
    if (output_capacity != 0U) {
        mb_worker_copy_bytes(&bytes[cursor], output, output_capacity);
    }
    *response = bytes;
    *response_len = total;
    return 1;
}

static int mb_worker_handle_call(
    struct mb_worker_state *worker,
    const mb_u8 *request,
    size_t request_len,
    mb_u8 **response,
    size_t *response_len)
{
    if (request_len < MB_NATIVE_PROCESS_CALL_REQUEST_FIXED_BYTES
        || mb_worker_compare_bytes(
            request,
            MB_NATIVE_PROCESS_CALL_MAGIC,
            MB_NATIVE_PROCESS_MAGIC_BYTES) != 0) {
        return 0;
    }
    const mb_u64 mapping_id = mb_native_process_read_u64(
        &request[MB_NATIVE_PROCESS_CALL_REQUEST_MAPPING_ID_OFFSET]);
    struct mb_worker_mapping *mapping = mb_worker_find_mapping(
        worker,
        mapping_id);
    size_t entry_offset = 0U;
    size_t memory_words = 0U;
    size_t input_len = 0U;
    size_t output_capacity = 0U;
    size_t memory_bytes = 0U;
    size_t memory_end = 0U;
    size_t input_end = 0U;
    if (!mb_worker_size_from_u64(
            mb_native_process_read_u64(
                &request[MB_NATIVE_PROCESS_CALL_REQUEST_ENTRY_OFFSET]),
            &entry_offset)
        || !mb_worker_decode_call_shape(
            request,
            request_len,
            &memory_words,
            &input_len,
            &output_capacity,
            &memory_bytes,
            &memory_end,
            &input_end)) {
        return 0;
    }

    mb_u32 *memory = memory_words == 0U
        ? NULL
        : mb_worker_alloc(memory_bytes);
    mb_u8 *output = output_capacity == 0U
        ? NULL
        : mb_worker_alloc(output_capacity);
    if ((memory_words != 0U && memory == NULL)
        || (output_capacity != 0U && output == NULL)) {
        mb_worker_free(memory);
        mb_worker_free(output);
        return 0;
    }
    size_t cursor = MB_NATIVE_PROCESS_CALL_REQUEST_FIXED_BYTES;
    for (size_t index = 0U; index < memory_words; ++index) {
        memory[index] = mb_native_process_read_u32(&request[cursor]);
        cursor += sizeof(mb_u32);
    }
    const mb_u8 *input = input_len == 0U ? NULL : &request[memory_end];
    if (output_capacity != 0U) {
        mb_worker_copy_bytes(output, &request[input_end], output_capacity);
    }

    struct mb_native_region_state state;
    state.memory = memory;
    state.memory_words = mb_native_process_read_u64(
        &request[MB_NATIVE_PROCESS_CALL_REQUEST_MEMORY_WORDS_OFFSET]);
    state.input = input;
    state.input_len = mb_native_process_read_u64(
        &request[MB_NATIVE_PROCESS_CALL_REQUEST_INPUT_LEN_OFFSET]);
    state.input_consumed = mb_native_process_read_u64(
        &request[MB_NATIVE_PROCESS_CALL_REQUEST_INPUT_CONSUMED_OFFSET]);
    state.output = output;
    state.output_capacity = mb_native_process_read_u64(
        &request[MB_NATIVE_PROCESS_CALL_REQUEST_OUTPUT_CAPACITY_OFFSET]);
    state.output_len = mb_native_process_read_u64(
        &request[MB_NATIVE_PROCESS_CALL_REQUEST_OUTPUT_LEN_OFFSET]);
    state.accumulator = mb_native_process_read_u32(
        &request[MB_NATIVE_PROCESS_CALL_REQUEST_ACCUMULATOR_OFFSET]);
    state.code_pointer = mb_native_process_read_u32(
        &request[MB_NATIVE_PROCESS_CALL_REQUEST_CODE_POINTER_OFFSET]);
    state.data_pointer = mb_native_process_read_u32(
        &request[MB_NATIVE_PROCESS_CALL_REQUEST_DATA_POINTER_OFFSET]);
    state.termination =
        request[MB_NATIVE_PROCESS_CALL_REQUEST_TERMINATION_OFFSET];
    mb_u32 *const original_memory = memory;
    const mb_u8 *const original_input = input;
    mb_u8 *const original_output = output;
    int raw_status = MB_NATIVE_INVALID_ARGUMENT;
    if (mapping != NULL
        && mapping->permission == MB_NATIVE_PROCESS_MEMORY_READ_EXECUTE
        && entry_offset < mapping->len) {
        void *entry_address = &mapping->base[entry_offset];
        mb_native_entry_fn entry = NULL;
        static_assert(
            sizeof(entry) == sizeof(entry_address),
            "function and object pointers must have equal representation");
        mb_worker_copy_bytes(&entry, &entry_address, sizeof(entry));
        raw_status = entry(&state);
    }
    const int pointers_unchanged = state.memory == original_memory
        && state.input == original_input
        && state.output == original_output;
    const int encoded = mb_worker_encode_call_response(
        mapping_id,
        &state,
        raw_status,
        pointers_unchanged,
        original_memory,
        memory_words,
        original_output,
        output_capacity,
        response,
        response_len);
    mb_worker_free(original_memory);
    mb_worker_free(original_output);
    return encoded;
}

static int mb_worker_write_exact(
    mb_win_handle handle,
    const mb_u8 *bytes,
    size_t len)
{
    size_t written = 0U;
    while (written < len) {
        const size_t remaining = len - written;
        const mb_win_dword chunk = remaining > (size_t)MB_WIN_DWORD_MAX
            ? MB_WIN_DWORD_MAX
            : (mb_win_dword)remaining;
        mb_win_dword count = 0U;
        if (WriteFile(
                handle,
                &bytes[written],
                chunk,
                &count,
                NULL) == MB_WIN_FALSE
            || count == 0U
            || count > chunk) {
            return 0;
        }
        written += (size_t)count;
    }
    return 1;
}

static int mb_worker_read_exact(
    mb_win_handle handle,
    mb_u8 *bytes,
    size_t len,
    int clean_eof_allowed)
{
    size_t read = 0U;
    while (read < len) {
        const size_t remaining = len - read;
        const mb_win_dword chunk = remaining > (size_t)MB_WIN_DWORD_MAX
            ? MB_WIN_DWORD_MAX
            : (mb_win_dword)remaining;
        mb_win_dword count = 0U;
        if (ReadFile(
                handle,
                &bytes[read],
                chunk,
                &count,
                NULL) == MB_WIN_FALSE) {
            const mb_win_dword code = GetLastError();
            if (clean_eof_allowed != 0
                && read == 0U
                && (code == 38U || code == 109U)) {
                return 0;
            }
            return -1;
        }
        if (count == 0U || count > chunk) {
            return clean_eof_allowed != 0 && read == 0U ? 0 : -1;
        }
        read += (size_t)count;
    }
    return 1;
}

static int mb_worker_write_frame(const mb_u8 *payload, size_t len)
{
    mb_u8 header[MB_NATIVE_PROCESS_FRAME_LENGTH_BYTES];
    mb_native_process_write_u64(header, (mb_u64)len);
    const mb_win_handle output = GetStdHandle(MB_WIN_STD_OUTPUT_HANDLE);
    return mb_worker_write_exact(output, header, sizeof(header))
        && (len == 0U || mb_worker_write_exact(output, payload, len));
}

static int mb_worker_read_frame(mb_u8 **payload, size_t *len)
{
    mb_u8 header[MB_NATIVE_PROCESS_FRAME_LENGTH_BYTES];
    const mb_win_handle input = GetStdHandle(MB_WIN_STD_INPUT_HANDLE);
    const int header_read = mb_worker_read_exact(
        input,
        header,
        sizeof(header),
        1);
    if (header_read <= 0) {
        return header_read;
    }
    if (!mb_worker_size_from_u64(mb_native_process_read_u64(header), len)) {
        return -1;
    }
    mb_u8 *bytes = *len == 0U ? NULL : mb_worker_alloc(*len);
    if (*len != 0U && bytes == NULL) {
        return -1;
    }
    if (*len != 0U
        && mb_worker_read_exact(input, bytes, *len, 0) != 1) {
        mb_worker_free(bytes);
        return -1;
    }
    *payload = bytes;
    return 1;
}

int main(void)
{
    struct mb_worker_state worker = {
        .mappings = NULL,
        .count = 0U,
        .capacity = 0U,
        .next_id = 1U,
    };
    int exit_code = 0;
    for (;;) {
        mb_u8 *request = NULL;
        size_t request_len = 0U;
        const int read_result = mb_worker_read_frame(&request, &request_len);
        if (read_result == 0) {
            break;
        }
        if (read_result < 0) {
            exit_code = 2;
            break;
        }
        mb_u8 *response = NULL;
        size_t response_len = 0U;
        int handled = 0;
        if (request_len >= MB_NATIVE_PROCESS_MAGIC_BYTES
            && mb_worker_compare_bytes(
                request,
                MB_NATIVE_PROCESS_MEMORY_MAGIC,
                MB_NATIVE_PROCESS_MAGIC_BYTES) == 0) {
            handled = mb_worker_handle_memory(
                &worker,
                request,
                request_len,
                &response,
                &response_len);
        } else if (request_len >= MB_NATIVE_PROCESS_MAGIC_BYTES
            && mb_worker_compare_bytes(
                request,
                MB_NATIVE_PROCESS_CALL_MAGIC,
                MB_NATIVE_PROCESS_MAGIC_BYTES) == 0) {
            handled = mb_worker_handle_call(
                &worker,
                request,
                request_len,
                &response,
                &response_len);
        }
        mb_worker_free(request);
        if (!handled || response == NULL
            || !mb_worker_write_frame(response, response_len)) {
            mb_worker_free(response);
            exit_code = 3;
            break;
        }
        mb_worker_free(response);
    }
    mb_worker_release_all(&worker);
    return exit_code;
}
