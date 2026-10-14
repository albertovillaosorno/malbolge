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
//   - Host simulation of Windows native-memory handlers with Win32 shims.
// - Must-Not:
//   - Claim Windows execution or replace target COFF ABI verification.
// - Allows:
//   - Inputs: tracked Windows worker and simulated allocation geometry.
//   - Outputs: zero for correct memory lifecycle, nonzero on a discrepancy.
//   - Side effects: private host heap reservation and release.
// - Split-When:
//   - Native Windows execution evidence becomes available.
// - Merge-When:
//   - One shared platform simulation replaces this narrow harness.
// - Summary:
//   - Tests Windows worker over-alignment under deterministic Win32 shims.
// - Description:
//   - Compiles real Windows handlers with controlled host memory APIs.
// - Usage:
//   - Compiled and run using pinned Clang through a Linux pytest fixture.
// - Defaults:
//   - No real Windows kernel semantics or native guest execution.
//

//! Host simulation of Windows allocation APIs, not Windows execution.
#define _WIN32 1
#define __declspec(value)
#define __stdcall
int mb_test_windows_worker_entry(void);
#define main mb_test_windows_worker_entry
#include "native_process_worker_windows.c"
#undef main

#include <stdint.h>
#include <stdlib.h>
#include <string.h>

struct mb_mock_reservation {
    void *allocation;
    void *base;
    size_t len;
    int released;
};

static struct mb_mock_reservation reservations[32];
static size_t reservation_count;
static size_t protect_count;
static size_t sync_count;
static size_t release_count;
static int fail_next_protect;
static int unexpected_old_protect;
static int fail_next_heap_realloc;
static int fail_next_mapping_response;
static int fail_next_release;
static int fail_next_sync;
static char mock_handle;
static const mb_u8 *mock_read_source;
static size_t mock_read_len;
static size_t mock_read_pos;
static size_t mock_read_chunk;
static int mock_fail_read;
static int mock_read_overreport;
static size_t mock_fail_read_after;
static mb_win_dword mock_read_error = 5UL;
static mb_u8 mock_write_buffer[256];
static size_t mock_write_pos;
static size_t mock_write_chunk;
static int mock_fail_write;
static int mock_write_overreport;
static size_t mock_fail_write_after = (size_t)-1;

mb_win_handle GetCurrentProcess(void) { return &mock_handle; }
mb_win_dword GetLastError(void) { return mock_read_error; }
mb_win_handle GetProcessHeap(void) { return &mock_handle; }
mb_win_handle GetStdHandle(mb_win_dword kind)
{
    (void)kind;
    return &mock_handle;
}
void *HeapAlloc(mb_win_handle heap, mb_win_dword flags, size_t len)
{
    (void)heap;
    (void)flags;
    if (len == MB_NATIVE_PROCESS_MEMORY_MAPPING_RESPONSE_BYTES
        && fail_next_mapping_response != 0) {
        fail_next_mapping_response = 0;
        return NULL;
    }
    return malloc(len);
}
void *HeapReAlloc(mb_win_handle heap, mb_win_dword flags, void *ptr, size_t len)
{
    (void)heap;
    (void)flags;
    if (fail_next_heap_realloc != 0) {
        fail_next_heap_realloc = 0;
        return NULL;
    }
    return realloc(ptr, len);
}
mb_win_bool HeapFree(mb_win_handle heap, mb_win_dword flags, void *ptr)
{
    (void)heap;
    (void)flags;
    free(ptr);
    return 1;
}
mb_win_bool ReadFile(
    mb_win_handle handle, void *buffer, mb_win_dword len,
    mb_win_dword *read, void *overlapped)
{
    (void)handle;
    (void)overlapped;
    if (mock_read_overreport != 0) {
        mock_read_overreport = 0;
        *read = len + 1UL;
        return 1;
    }
    if (mock_fail_read != 0
        && mock_read_pos >= mock_fail_read_after) {
        mock_fail_read = 0;
        *read = 0UL;
        return 0;
    }
    const size_t remaining = mock_read_len - mock_read_pos;
    size_t count = (size_t)len < remaining ? (size_t)len : remaining;
    if (count > mock_read_chunk) {
        count = mock_read_chunk;
    }
    if (count != 0U) {
        memcpy(buffer, &mock_read_source[mock_read_pos], count);
    }
    mock_read_pos += count;
    *read = (mb_win_dword)count;
    return 1;
}
mb_win_bool WriteFile(
    mb_win_handle handle, const void *buffer, mb_win_dword len,
    mb_win_dword *written, void *overlapped)
{
    (void)handle;
    (void)overlapped;
    if (mock_write_overreport != 0) {
        mock_write_overreport = 0;
        *written = len + 1UL;
        return 1;
    }
    if (mock_fail_write != 0
        || mock_write_pos >= mock_fail_write_after) {
        mock_fail_write = 0;
        *written = 0UL;
        return 0;
    }
    const size_t space = sizeof(mock_write_buffer) - mock_write_pos;
    size_t count = (size_t)len < space ? (size_t)len : space;
    if (count > mock_write_chunk) {
        count = mock_write_chunk;
    }
    if (count != 0U) {
        memcpy(&mock_write_buffer[mock_write_pos], buffer, count);
    }
    mock_write_pos += count;
    *written = (mb_win_dword)count;
    return 1;
}
void *VirtualAlloc(
    void *address, size_t len, mb_win_dword flags, mb_win_dword protect)
{
    if (address != NULL || flags != (MB_WIN_MEM_RESERVE | MB_WIN_MEM_COMMIT)
        || protect != MB_WIN_PAGE_READWRITE
        || reservation_count >= 32U || len > 1048576U) {
        return NULL;
    }
    const size_t total = len + 262144U;
    void *allocation = malloc(total);
    if (allocation == NULL) {
        return NULL;
    }
    const uintptr_t start = (uintptr_t)allocation;
    const uintptr_t aligned = (start + 131071U) & ~(uintptr_t)131071U;
    void *base = (void *)(aligned + 65536U);
    reservations[reservation_count] = (struct mb_mock_reservation){
        .allocation = allocation,
        .base = base,
        .len = len,
        .released = 0,
    };
    reservation_count += 1U;
    return base;
}
mb_win_bool VirtualProtect(
    void *address, size_t len, mb_win_dword permissions, mb_win_dword *old)
{
    if (permissions != MB_WIN_PAGE_EXECUTE_READ) {
        return 0;
    }
    if (fail_next_protect != 0) {
        fail_next_protect = 0;
        return 0;
    }
    for (size_t i = 0U; i < reservation_count; ++i) {
        const uintptr_t base = (uintptr_t)reservations[i].base;
        const uintptr_t location = (uintptr_t)address;
        if (!reservations[i].released && location >= base
            && location - base <= reservations[i].len
            && len <= reservations[i].len - (size_t)(location - base)) {
            *old = unexpected_old_protect != 0
                ? MB_WIN_PAGE_EXECUTE_READ
                : MB_WIN_PAGE_READWRITE;
            unexpected_old_protect = 0;
            protect_count += 1U;
            return 1;
        }
    }
    return 0;
}
mb_win_bool VirtualFree(void *address, size_t len, mb_win_dword flags)
{
    if (len != 0U || flags != MB_WIN_MEM_RELEASE) {
        return 0;
    }
    if (fail_next_release != 0) {
        fail_next_release = 0;
        return 0;
    }
    for (size_t i = 0U; i < reservation_count; ++i) {
        if (!reservations[i].released && address == reservations[i].base) {
            reservations[i].released = 1;
            free(reservations[i].allocation);
            release_count += 1U;
            return 1;
        }
    }
    return 0;
}
mb_win_bool FlushInstructionCache(
    mb_win_handle process, const void *address, size_t len)
{
    (void)process;
    (void)address;
    (void)len;
    if (fail_next_sync != 0) {
        fail_next_sync = 0;
        return 0;
    }
    sync_count += 1U;
    return 1;
}

static int check_mapping_lifecycle(struct mb_worker_state *worker)
{
    mb_u8 request[48] = {0};
    mb_u8 *response = NULL;
    size_t len = 0U;
    memcpy(request, MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
    mb_native_process_write_u64(&request[9], 64U);
    mb_native_process_write_u64(&request[17], 131072U);
    request[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    if (!mb_worker_handle_allocate(worker, request, 26U, &response, &len)
        || len != 35U || response[9] != MB_NATIVE_PROCESS_MEMORY_SUCCESS) {
        return 1;
    }
    const mb_u64 id = mb_native_process_read_u64(&response[10]);
    const mb_u64 address = mb_native_process_read_u64(&response[18]);
    const mb_u64 bytes = mb_native_process_read_u64(&response[26]);
    mb_worker_free(response);
    if (id == 0U || (address & 131071U) != 0U || bytes != 64U) {
        return 2;
    }
    mb_native_process_write_u64(&request[9], id);
    mb_native_process_write_u64(&request[17], address);
    mb_native_process_write_u64(&request[25], bytes);
    request[33] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    mb_native_process_write_u64(&request[34], 6U);
    memcpy(&request[42], "ABCDEF", 6U);
    if (!mb_worker_handle_copy(worker, request, 48U, &response, &len)
        || len != 32U || memcmp(&response[26], "ABCDEF", 6U) != 0) {
        return 3;
    }
    mb_worker_free(response);
    if (!mb_worker_handle_protect(worker, request, 34U, &response, &len)
        || len != 35U
        || response[34] != MB_NATIVE_PROCESS_MEMORY_READ_EXECUTE) {
        return 4;
    }
    mb_worker_free(response);
    if (!mb_worker_handle_sync(worker, request, 33U, &response, &len)
        || len != 34U) {
        return 5;
    }
    mb_worker_free(response);
    if (!mb_worker_handle_release(worker, request, 33U, &response, &len)
        || len != 10U || worker->count != 0U) {
        return 6;
    }
    mb_worker_free(response);
    return 0;
}

static int check_overflow_rejected(struct mb_worker_state *worker)
{
    mb_u8 request[26] = {0};
    mb_u8 *response = NULL;
    size_t len = 0U;
    const size_t count_before = reservation_count;
    memcpy(request, MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
    mb_native_process_write_u64(&request[9], (1ULL << 63) + 1ULL);
    mb_native_process_write_u64(&request[17], 1ULL << 63);
    request[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    if (!mb_worker_handle_allocate(worker, request, sizeof(request),
            &response, &len)
        || len != MB_NATIVE_PROCESS_MEMORY_FAILURE_RESPONSE_BYTES
        || response[9] != MB_NATIVE_PROCESS_MEMORY_FAILURE
        || mb_native_process_read_u32(&response[10])
            != MB_WORKER_ALLOCATION_FAILURE
        || reservation_count != count_before) {
        return 1;
    }
    mb_worker_free(response);
    return 0;
}

static int check_teardown_releases_backing(struct mb_worker_state *worker)
{
    mb_u8 request[26] = {0};
    mb_u8 *response = NULL;
    size_t len = 0U;
    memcpy(request, MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
    mb_native_process_write_u64(&request[9], 64U);
    mb_native_process_write_u64(&request[17], 131072U);
    request[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    if (!mb_worker_handle_allocate(worker, request, sizeof(request),
            &response, &len)
        || len != MB_NATIVE_PROCESS_MEMORY_MAPPING_RESPONSE_BYTES
        || worker->count != 1U) {
        return 1;
    }
    mb_worker_free(response);
    mb_worker_release_all(worker);
    return worker->count == 0U && release_count == 3U ? 0 : 2;
}

static int check_compaction_and_teardown(struct mb_worker_state *worker)
{
    mb_u64 ids[6] = {0};
    mb_u64 addresses[6] = {0};
    mb_u8 request[48] = {0};
    mb_u8 *response = NULL;
    size_t len = 0U;
    const size_t releases_before = release_count;
    const size_t protects_before = protect_count;
    const size_t syncs_before = sync_count;
    memcpy(request, MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
    request[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    for (size_t i = 0U; i < 6U; ++i) {
        mb_native_process_write_u64(&request[9], 64U);
        mb_native_process_write_u64(&request[17], 131072U);
        if (!mb_worker_handle_allocate(worker, request, 26U,
                &response, &len)
            || len != MB_NATIVE_PROCESS_MEMORY_MAPPING_RESPONSE_BYTES) {
            return 1;
        }
        ids[i] = mb_native_process_read_u64(&response[10]);
        addresses[i] = mb_native_process_read_u64(&response[18]);
        mb_worker_free(response);
        if ((addresses[i] & 131071U) != 0U
            || ids[i] == 0U || worker->count != i + 1U) {
            return 2;
        }
    }
    // Releasing the middle slot moves later mapping metadata in-place.
    mb_native_process_write_u64(&request[9], ids[2]);
    mb_native_process_write_u64(&request[17], addresses[2]);
    mb_native_process_write_u64(&request[25], 64U);
    if (!mb_worker_handle_release(worker, request, 33U, &response, &len)
        || worker->count != 5U) {
        return 3;
    }
    mb_worker_free(response);
    for (size_t i = 0U; i < 6U; ++i) {
        if (i == 2U) {
            continue;
        }
        mb_native_process_write_u64(&request[9], ids[i]);
        mb_native_process_write_u64(&request[17], addresses[i]);
        mb_native_process_write_u64(&request[25], 64U);
        request[33] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
        mb_native_process_write_u64(&request[34], 6U);
        memcpy(&request[42], "ABCDEF", 6U);
        if (!mb_worker_handle_copy(worker, request, 48U, &response, &len)
            || len != 32U
            || memcmp(&response[26], "ABCDEF", 6U) != 0) {
            return 4;
        }
        mb_worker_free(response);
        if (!mb_worker_handle_protect(worker, request, 34U,
                &response, &len)
            || len != 35U) {
            return 5;
        }
        mb_worker_free(response);
        if (!mb_worker_handle_sync(worker, request, 33U, &response, &len)
            || len != 34U) {
            return 6;
        }
        mb_worker_free(response);
    }
    // Process teardown must release the original bases for all survivors.
    mb_worker_release_all(worker);
    return worker->count == 0U && release_count == releases_before + 6U
        && protect_count == protects_before + 5U
        && sync_count == syncs_before + 5U ? 0 : 7;
}

static int check_protect_report_mismatch(struct mb_worker_state *worker)
{
    mb_u8 request[48] = {0};
    mb_u8 *response = NULL;
    size_t len = 0U;
    memcpy(request, MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
    mb_native_process_write_u64(&request[9], 64U);
    mb_native_process_write_u64(&request[17], 131072U);
    request[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    if (!mb_worker_handle_allocate(worker, request, 26U,
            &response, &len) || len != 35U) {
        return 1;
    }
    const mb_u64 id = mb_native_process_read_u64(&response[10]);
    const mb_u64 address = mb_native_process_read_u64(&response[18]);
    mb_worker_free(response);
    mb_native_process_write_u64(&request[9], id);
    mb_native_process_write_u64(&request[17], address);
    mb_native_process_write_u64(&request[25], 64U);
    request[33] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    unexpected_old_protect = 1;
    if (!mb_worker_handle_protect(worker, request, 34U,
            &response, &len)
        || len != MB_NATIVE_PROCESS_MEMORY_FAILURE_RESPONSE_BYTES
        || response[9] != MB_NATIVE_PROCESS_MEMORY_FAILURE
        || worker->mappings[0].permission
            != MB_NATIVE_PROCESS_MEMORY_READ_EXECUTE) {
        mb_worker_free(response);
        return 2;
    }
    mb_worker_free(response);
    mb_native_process_write_u64(&request[34], 6U);
    memcpy(&request[42], "ABCDEF", 6U);
    if (!mb_worker_handle_copy(worker, request, 48U, &response, &len)
        || len != MB_NATIVE_PROCESS_MEMORY_FAILURE_RESPONSE_BYTES
        || response[9] != MB_NATIVE_PROCESS_MEMORY_FAILURE) {
        mb_worker_free(response);
        return 3;
    }
    mb_worker_free(response);
    if (!mb_worker_handle_release(worker, request, 33U,
            &response, &len) || len != 10U || worker->count != 0U) {
        mb_worker_free(response);
        return 4;
    }
    mb_worker_free(response);
    return 0;
}

static int check_win32_failure_recovery(struct mb_worker_state *worker)
{
    mb_u8 request[48] = {0};
    mb_u8 *response = NULL;
    size_t len = 0U;
    const size_t releases_before = release_count;
    memcpy(request, MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
    mb_native_process_write_u64(&request[9], 64U);
    mb_native_process_write_u64(&request[17], 131072U);
    request[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    if (!mb_worker_handle_allocate(worker, request, 26U,
            &response, &len)
        || len != 35U || worker->count != 1U) {
        return 1;
    }
    const mb_u64 id = mb_native_process_read_u64(&response[10]);
    const mb_u64 address = mb_native_process_read_u64(&response[18]);
    mb_worker_free(response);
    mb_native_process_write_u64(&request[9], id);
    mb_native_process_write_u64(&request[17], address);
    mb_native_process_write_u64(&request[25], 64U);
    request[33] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    fail_next_protect = 1;
    if (!mb_worker_handle_protect(worker, request, 34U,
            &response, &len)
        || len != 14U || response[9] != MB_NATIVE_PROCESS_MEMORY_FAILURE
        || worker->mappings[0].permission
            != MB_NATIVE_PROCESS_MEMORY_READ_WRITE) {
        return 2;
    }
    mb_worker_free(response);
    mb_native_process_write_u64(&request[34], 6U);
    memcpy(&request[42], "ABCDEF", 6U);
    if (!mb_worker_handle_copy(worker, request, 48U, &response, &len)
        || len != 32U || memcmp(&response[26], "ABCDEF", 6U) != 0) {
        return 3;
    }
    mb_worker_free(response);
    if (!mb_worker_handle_protect(worker, request, 34U,
            &response, &len)
        || len != 35U
        || response[34] != MB_NATIVE_PROCESS_MEMORY_READ_EXECUTE) {
        return 4;
    }
    mb_worker_free(response);
    const size_t syncs_before = sync_count;
    fail_next_sync = 1;
    if (!mb_worker_handle_sync(worker, request, 33U,
            &response, &len)
        || len != MB_NATIVE_PROCESS_MEMORY_FAILURE_RESPONSE_BYTES
        || response[9] != MB_NATIVE_PROCESS_MEMORY_FAILURE
        || worker->mappings[0].permission
            != MB_NATIVE_PROCESS_MEMORY_READ_EXECUTE
        || sync_count != syncs_before) {
        return 7;
    }
    mb_worker_free(response);
    if (!mb_worker_handle_sync(worker, request, 33U,
            &response, &len)
        || len != MB_NATIVE_PROCESS_MEMORY_SYNC_RESPONSE_BYTES
        || sync_count != syncs_before + 1U) {
        return 8;
    }
    mb_worker_free(response);
    fail_next_release = 1;
    if (!mb_worker_handle_release(worker, request, 33U,
            &response, &len)
        || len != 14U || response[9] != MB_NATIVE_PROCESS_MEMORY_FAILURE
        || worker->count != 1U || release_count != releases_before) {
        return 5;
    }
    mb_worker_free(response);
    if (!mb_worker_handle_release(worker, request, 33U,
            &response, &len)
        || len != 10U || worker->count != 0U
        || release_count != releases_before + 1U) {
        return 6;
    }
    mb_worker_free(response);
    return 0;
}

static size_t native_entry_invocations;
static size_t corrupted_shape_invocations;
static size_t pointer_drift_invocations;
static size_t pointer_drift_field;

static int mb_simulated_corrupt_shape_entry(
    struct mb_native_region_state *state)
{
    corrupted_shape_invocations += 1U;
    state->memory[0] = 0x44U;
    state->output[1] = 0x33U;
    state->memory_words = (mb_u64)-1;
    state->input_len = (mb_u64)-1;
    state->input_consumed = (mb_u64)-1;
    state->output_capacity = (mb_u64)-1;
    state->output_len = (mb_u64)-1;
    return MB_NATIVE_GUARD_MISS;
}

static int mb_simulated_pointer_drift_entry(
    struct mb_native_region_state *state)
{
    pointer_drift_invocations += 1U;
    switch (pointer_drift_field) {
    case 0U:
        state->memory = NULL;
        break;
    case 1U:
        state->input = NULL;
        break;
    default:
        state->output = NULL;
        break;
    }
    return MB_NATIVE_GUARD_MISS;
}


static int mb_simulated_native_entry(struct mb_native_region_state *state)
{
    native_entry_invocations += 1U;
    state->memory[0] += 2U;
    state->output[state->output_len] = state->input[state->input_consumed];
    state->input_consumed += 1U;
    state->output_len += 1U;
    state->accumulator += 1U;
    return MB_NATIVE_APPLIED;
}

static int check_native_call_shape(
    struct mb_worker_state *worker,
    const mb_u8 *request,
    int expected_status,
    int changed)
{
    mb_u8 *response = NULL;
    size_t len = 0U;
    const size_t before = native_entry_invocations;
    if (!mb_worker_handle_call(worker, request, 86U, &response, &len)
        || len != 81U) {
        mb_worker_free(response);
        return 1;
    }
    int failure = 0;
    if (mb_native_process_read_u32(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_STATUS_OFFSET])
        != (mb_u32)expected_status) {
        failure = 2;
    } else if (mb_native_process_read_u64(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_MAPPING_ID_OFFSET])
        != mb_native_process_read_u64(&request[8])) {
        failure = 9;
    } else if (mb_native_process_read_u64(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_MEMORY_WORDS_OFFSET])
        != 1U
        || mb_native_process_read_u64(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_INPUT_LEN_OFFSET])
            != 2U
        || mb_native_process_read_u64(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_OUTPUT_CAPACITY_OFFSET])
            != 3U) {
        failure = 10;
    } else if (mb_native_process_read_u32(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_ACCUMULATOR_OFFSET])
        != (changed != 0 ? 8U : 7U)
        || response[MB_NATIVE_PROCESS_CALL_RESPONSE_TERMINATION_OFFSET]
            != request[MB_NATIVE_PROCESS_CALL_REQUEST_TERMINATION_OFFSET]) {
        failure = 11;
    } else if (response[MB_NATIVE_PROCESS_CALL_RESPONSE_POINTER_FLAG_OFFSET]
        != 1U) {
        failure = 3;
    } else if (mb_native_process_read_u64(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_INPUT_CONSUMED_OFFSET])
        != (changed != 0 ? 1U : mb_native_process_read_u64(&request[48]))) {
        failure = 4;
    } else if (mb_native_process_read_u64(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_OUTPUT_LEN_OFFSET])
        != (changed != 0 ? 2U : mb_native_process_read_u64(&request[56]))) {
        failure = 5;
    } else if (mb_native_process_read_u32(&response[74])
        != (changed != 0 ? 10U : 8U)) {
        failure = 6;
    } else if (response[78] != 0x10U
        || response[79] != (changed != 0 ? 0xa5U : 0U)) {
        failure = 7;
    } else if (native_entry_invocations
        != before + (changed != 0 ? 1U : 0U)) {
        failure = 8;
    }
    mb_worker_free(response);
    return failure;
}

static int check_native_pointer_drift_response(
    struct mb_worker_state *worker, const mb_u8 *request)
{
    mb_u8 *response = NULL;
    size_t len = 0U;
    const size_t before = pointer_drift_invocations;
    if (!mb_worker_handle_call(worker, request, 86U, &response, &len)
        || len != 81U) {
        mb_worker_free(response);
        return 1;
    }
    const int valid = mb_native_process_read_u32(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_STATUS_OFFSET])
            == MB_NATIVE_GUARD_MISS
        && response[MB_NATIVE_PROCESS_CALL_RESPONSE_POINTER_FLAG_OFFSET]
            == 0U
        && mb_native_process_read_u32(&response[74]) == 8U
        && response[78] == 0x10U && response[79] == 0U
        && mb_native_process_read_u64(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_INPUT_CONSUMED_OFFSET])
            == 0U
        && mb_native_process_read_u64(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_OUTPUT_LEN_OFFSET])
            == 1U
        && pointer_drift_invocations == before + 1U;
    mb_worker_free(response);
    return valid ? 0 : 2;
}

static int check_native_corrupted_shape_response(
    struct mb_worker_state *worker, const mb_u8 *request)
{
    mb_u8 *response = NULL;
    size_t len = 0U;
    const size_t before = corrupted_shape_invocations;
    if (!mb_worker_handle_call(worker, request, 86U, &response, &len)
        || len != 81U) {
        mb_worker_free(response);
        return 1;
    }
    const mb_u64 maximum = (mb_u64)-1;
    const int valid = mb_native_process_read_u32(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_STATUS_OFFSET])
            == MB_NATIVE_GUARD_MISS
        && response[MB_NATIVE_PROCESS_CALL_RESPONSE_POINTER_FLAG_OFFSET]
            == 1U
        && mb_native_process_read_u64(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_MEMORY_WORDS_OFFSET])
            == maximum
        && mb_native_process_read_u64(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_INPUT_LEN_OFFSET])
            == maximum
        && mb_native_process_read_u64(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_INPUT_CONSUMED_OFFSET])
            == maximum
        && mb_native_process_read_u64(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_OUTPUT_CAPACITY_OFFSET])
            == maximum
        && mb_native_process_read_u64(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_OUTPUT_LEN_OFFSET])
            == maximum
        && mb_native_process_read_u32(&response[74]) == 0x44U
        && response[78] == 0x10U && response[79] == 0x33U
        && response[80] == 0U
        && corrupted_shape_invocations == before + 1U;
    mb_worker_free(response);
    return valid ? 0 : 2;
}

static int check_invalid_call_framing(
    struct mb_worker_state *worker, const mb_u8 *valid)
{
    const size_t before = native_entry_invocations;
    for (size_t index = 0U; index < 10U; ++index) {
        mb_u8 frame[87] = {0};
        mb_worker_copy_bytes(frame, valid, 86U);
        size_t request_len = 86U;
        switch (index) {
        case 0U:
            request_len = 76U;
            break;
        case 1U:
            frame[0] ^= 0xffU;
            break;
        case 2U:
            mb_native_process_write_u64(&frame[24], (mb_u64)-1);
            break;
        case 3U:
            mb_native_process_write_u64(&frame[32], (mb_u64)-1);
            break;
        case 4U:
            mb_native_process_write_u64(&frame[40], (mb_u64)-1);
            break;
        case 5U:
            mb_native_process_write_u64(&frame[24], 0U);
            break;
        case 6U:
            mb_native_process_write_u64(&frame[32], 0U);
            break;
        case 7U:
            mb_native_process_write_u64(&frame[40], 0U);
            break;
        case 8U:
            request_len = 85U;
            break;
        default:
            request_len = 87U;
            break;
        }
        mb_u8 *response = NULL;
        size_t response_len = 0U;
        if (mb_worker_handle_call(
                worker, frame, request_len, &response, &response_len)
            || response != NULL || response_len != 0U
            || native_entry_invocations != before) {
            mb_worker_free(response);
            return (int)(index + 1U);
        }
    }
    return 0;
}

static int check_native_call_guarding(struct mb_worker_state *worker)
{
    mb_u8 allocation[33] = {0};
    mb_u8 request[86] = {0};
    mb_u8 *response = NULL;
    size_t len = 0U;
    memcpy(allocation, MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
    mb_native_process_write_u64(&allocation[9], 64U);
    mb_native_process_write_u64(&allocation[17], 131072U);
    allocation[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    if (!mb_worker_handle_allocate(worker, allocation, 26U,
            &response, &len) || len != 35U) {
        return 1;
    }
    const mb_u64 id = mb_native_process_read_u64(&response[10]);
    const mb_u64 address = mb_native_process_read_u64(&response[18]);
    mb_worker_free(response);
    mb_win_dword old_permissions = 0U;
    if (!VirtualProtect(worker->mappings[0].base, 64U,
            MB_WIN_PAGE_EXECUTE_READ, &old_permissions)) {
        return 2;
    }
    worker->mappings[0].permission = MB_NATIVE_PROCESS_MEMORY_READ_EXECUTE;
    // Run a host C entry through the Windows handler's pointer reconstruction.
    mb_native_entry_fn entry = mb_simulated_native_entry;
    mb_u8 *native_address = NULL;
    mb_worker_copy_bytes(&native_address, &entry, sizeof(entry));
    worker->mappings[0].base = native_address;
    memcpy(request, MB_NATIVE_PROCESS_CALL_MAGIC, 8U);
    mb_native_process_write_u64(&request[8], id);
    mb_native_process_write_u64(&request[24], 1U);
    mb_native_process_write_u64(&request[32], 2U);
    mb_native_process_write_u64(&request[40], 3U);
    mb_native_process_write_u64(&request[56], 1U);
    mb_native_process_write_u32(&request[64], 7U);
    mb_native_process_write_u32(&request[77], 8U);
    request[81] = 0xa5U;
    request[82] = 0xb6U;
    request[83] = 0x10U;
    mb_u8 unchanged_request[sizeof(request)];
    memcpy(unchanged_request, request, sizeof(request));
    const int call_result = check_native_call_shape(
        worker, request, MB_NATIVE_APPLIED, 1);
    if (call_result != 0 || memcmp(request, unchanged_request,
            sizeof(request)) != 0) {
        return 20 + call_result;
    }
    if (check_invalid_call_framing(worker, request) != 0) {
        return 14;
    }
    worker->mappings[0].permission = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    if (check_native_call_shape(
            worker, request, MB_NATIVE_INVALID_ARGUMENT, 0)) {
        return 10;
    }
    worker->mappings[0].permission = MB_NATIVE_PROCESS_MEMORY_READ_EXECUTE;
    mb_native_process_write_u64(&request[8], id + 1U);
    if (check_native_call_shape(
            worker, request, MB_NATIVE_INVALID_ARGUMENT, 0)) {
        return 11;
    }
    mb_native_process_write_u64(&request[8], id);
    mb_native_process_write_u64(&request[16], 64U);
    if (check_native_call_shape(
            worker, request, MB_NATIVE_INVALID_ARGUMENT, 0)) {
        return 4;
    }
    mb_native_process_write_u64(&request[16], 0U);
    mb_native_process_write_u64(&request[48], 3U);
    if (check_native_call_shape(
            worker, request, MB_NATIVE_INVALID_ARGUMENT, 0)) {
        return 5;
    }
    mb_native_process_write_u64(&request[48], 0U);
    mb_native_process_write_u64(&request[56], 4U);
    if (check_native_call_shape(
            worker, request, MB_NATIVE_INVALID_ARGUMENT, 0)) {
        return 6;
    }
    mb_native_process_write_u64(&request[56], 1U);
    request[76] = 0xffU;
    if (check_native_call_shape(
            worker, request, MB_NATIVE_INVALID_ARGUMENT, 0)) {
        return 7;
    }
    request[76] = MB_NATIVE_TERMINATION_RUNNING;
    mb_native_entry_fn drifting_entry = mb_simulated_pointer_drift_entry;
    mb_worker_copy_bytes(
        &native_address, &drifting_entry, sizeof(drifting_entry));
    worker->mappings[0].base = native_address;
    for (size_t field = 0U; field < 3U; ++field) {
        pointer_drift_field = field;
        if (check_native_pointer_drift_response(worker, request) != 0) {
            return 12;
        }
    }
    mb_native_entry_fn corrupt_entry = mb_simulated_corrupt_shape_entry;
    mb_worker_copy_bytes(
        &native_address, &corrupt_entry, sizeof(corrupt_entry));
    worker->mappings[0].base = native_address;
    if (check_native_corrupted_shape_response(worker, request) != 0) {
        return 13;
    }
    worker->mappings[0].base = (mb_u8 *)(mb_uintptr)address;
    mb_native_process_write_u64(&allocation[9], id);
    mb_native_process_write_u64(&allocation[17], address);
    mb_native_process_write_u64(&allocation[25], 64U);
    if (!mb_worker_handle_release(worker, allocation, 33U, &response, &len)
        || worker->count != 0U || len != 10U) {
        return 8;
    }
    mb_worker_free(response);
    return native_entry_invocations == 1U
        && pointer_drift_invocations == 3U
        && corrupted_shape_invocations == 1U ? 0 : 9;
}

static void mb_mock_read_reset(const mb_u8 *bytes, size_t len)
{
    mock_read_source = bytes;
    mock_read_len = len;
    mock_read_pos = 0U;
    mock_read_chunk = 2U;
    mock_fail_read = 0;
    mock_read_overreport = 0;
    mock_fail_read_after = 0U;
    mock_read_error = 5UL;
}

static int check_frame_io(void)
{
    mb_u8 wire[11] = {0};
    mb_u8 *payload = NULL;
    size_t len = 0U;
    mb_native_process_write_u64(wire, 3U);
    memcpy(&wire[8], "xyz", 3U);
    mb_mock_read_reset(wire, sizeof(wire));
    if (mb_worker_read_frame(&payload, &len) != 1
        || len != 3U || memcmp(payload, "xyz", 3U) != 0
        || mock_read_pos != sizeof(wire)) {
        mb_worker_free(payload);
        return 1;
    }
    mb_worker_free(payload);
    mock_write_pos = 0U;
    mock_write_chunk = 2U;
    mock_fail_write = 0;
    if (!mb_worker_write_frame((const mb_u8 *)"xyz", 3U)
        || mock_write_pos != sizeof(wire)
        || memcmp(mock_write_buffer, wire, sizeof(wire)) != 0) {
        return 2;
    }
    mb_mock_read_reset(wire, 0U);
    if (mb_worker_read_frame(&payload, &len) != 0) {
        return 3;
    }
    mb_mock_read_reset(wire, 4U);
    if (mb_worker_read_frame(&payload, &len) != -1) {
        return 4;
    }
    mb_mock_read_reset(wire, 9U);
    if (mb_worker_read_frame(&payload, &len) != -1) {
        return 5;
    }
    mb_native_process_write_u64(wire, 0U);
    mb_mock_read_reset(wire, 8U);
    if (mb_worker_read_frame(&payload, &len) != 1
        || len != 0U || payload != NULL) {
        return 6;
    }
    mock_write_pos = 0U;
    if (!mb_worker_write_frame(NULL, 0U)
        || mock_write_pos != 8U
        || memcmp(mock_write_buffer, wire, 8U) != 0) {
        return 7;
    }
    mock_fail_write = 1;
    if (mb_worker_write_frame(NULL, 0U) != 0) {
        return 8;
    }
    mock_write_pos = 0U;
    mock_fail_write_after = 10U;
    if (mb_worker_write_frame((const mb_u8 *)"xyz", 3U) != 0
        || mock_write_pos != 10U) {
        return 12;
    }
    mock_fail_write_after = (size_t)-1;
    mock_write_pos = 0U;
    mock_write_chunk = 0U;
    if (mb_worker_write_frame(NULL, 0U) != 0) {
        return 13;
    }
    mock_write_chunk = 2U;
    mock_write_overreport = 1;
    if (mb_worker_write_frame(NULL, 0U) != 0) {
        return 15;
    }
    mb_mock_read_reset(wire, 8U);
    mock_read_overreport = 1;
    if (mb_worker_read_frame(&payload, &len) != -1) {
        return 14;
    }
    mock_fail_read = 1;
    if (mb_worker_read_frame(&payload, &len) != -1) {
        return 9;
    }
    for (mb_win_dword error_code = 38U; error_code <= 109U;
            error_code += 71U) {
        mb_mock_read_reset(wire, 8U);
        mock_fail_read = 1;
        mock_read_error = error_code;
        if (mb_worker_read_frame(&payload, &len) != 0) {
            return 10;
        }
        mb_mock_read_reset(wire, 8U);
        mock_fail_read = 1;
        mock_fail_read_after = 2U;
        mock_read_error = error_code;
        if (mb_worker_read_frame(&payload, &len) != -1) {
            return 11;
        }
    }
    return 0;
}

static int check_mapping_table_growth_failure(
    struct mb_worker_state *worker)
{
    mb_u8 request[48] = {0};
    mb_u8 *response = NULL;
    size_t len = 0U;
    mb_u64 ids[4] = {0};
    mb_u64 addresses[4] = {0};
    const size_t reservations_before = reservation_count;
    const size_t releases_before = release_count;
    const mb_u64 id_before = worker->next_id;
    memcpy(request, MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
    mb_native_process_write_u64(&request[9], 64U);
    mb_native_process_write_u64(&request[17], 131072U);
    request[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    for (size_t i = 0U; i < 4U; ++i) {
        if (!mb_worker_handle_allocate(worker, request, 26U,
                &response, &len) || len != 35U) {
            return 1;
        }
        ids[i] = mb_native_process_read_u64(&response[10]);
        addresses[i] = mb_native_process_read_u64(&response[18]);
        mb_worker_free(response);
    }
    fail_next_heap_realloc = 1;
    if (!mb_worker_handle_allocate(worker, request, 26U,
            &response, &len)
        || len != MB_NATIVE_PROCESS_MEMORY_FAILURE_RESPONSE_BYTES
        || mb_native_process_read_u32(&response[10])
            != MB_WORKER_ALLOCATION_FAILURE
        || worker->count != 4U || worker->capacity != 4U
        || worker->next_id != id_before + 4U
        || reservation_count != reservations_before + 5U
        || release_count != releases_before + 1U) {
        mb_worker_free(response);
        return 2;
    }
    mb_worker_free(response);
    for (size_t i = 0U; i < 4U; ++i) {
        mb_native_process_write_u64(&request[9], ids[i]);
        mb_native_process_write_u64(&request[17], addresses[i]);
        mb_native_process_write_u64(&request[25], 64U);
        request[33] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
        mb_native_process_write_u64(&request[34], 6U);
        memcpy(&request[42], "ABCDEF", 6U);
        if (!mb_worker_handle_copy(worker, request, 48U,
                &response, &len) || len != 32U
            || memcmp(&response[26], "ABCDEF", 6U) != 0) {
            mb_worker_free(response);
            return 3;
        }
        mb_worker_free(response);
    }
    mb_native_process_write_u64(&request[9], 64U);
    mb_native_process_write_u64(&request[17], 131072U);
    request[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    if (!mb_worker_handle_allocate(worker, request, 26U,
            &response, &len)
        || len != 35U || worker->count != 5U
        || worker->capacity < 5U
        || mb_native_process_read_u64(&response[10])
            != id_before + 4U) {
        mb_worker_free(response);
        return 4;
    }
    mb_worker_free(response);
    mb_worker_release_all(worker);
    return worker->count == 0U
        && reservation_count == reservations_before + 6U
        && release_count == releases_before + 6U ? 0 : 5;
}

static int check_unreportable_mapping_cleanup(
    struct mb_worker_state *worker)
{
    mb_u8 request[34] = {0};
    mb_u8 *response = NULL;
    size_t len = 0U;
    const size_t releases_before = release_count;
    const size_t reservations_before = reservation_count;
    memcpy(request, MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
    mb_native_process_write_u64(&request[9], 64U);
    mb_native_process_write_u64(&request[17], 131072U);
    request[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    fail_next_mapping_response = 1;
    if (mb_worker_handle_allocate(worker, request, 26U,
            &response, &len) != 0
        || response != NULL || worker->count != 1U
        || worker->mappings[0].permission
            != MB_NATIVE_PROCESS_MEMORY_READ_WRITE) {
        return 1;
    }
    mb_worker_release_all(worker);
    if (release_count != releases_before + 1U
        || worker->count != 0U) {
        return 2;
    }
    if (!mb_worker_handle_allocate(worker, request, 26U,
            &response, &len) || len != 35U) {
        return 3;
    }
    const mb_u64 id = mb_native_process_read_u64(&response[10]);
    const mb_u64 address = mb_native_process_read_u64(&response[18]);
    mb_worker_free(response);
    mb_native_process_write_u64(&request[9], id);
    mb_native_process_write_u64(&request[17], address);
    mb_native_process_write_u64(&request[25], 64U);
    request[33] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    response = NULL;
    fail_next_mapping_response = 1;
    if (mb_worker_handle_protect(worker, request, 34U,
            &response, &len) != 0
        || response != NULL || worker->count != 1U
        || worker->mappings[0].permission
            != MB_NATIVE_PROCESS_MEMORY_READ_EXECUTE) {
        return 4;
    }
    mb_worker_release_all(worker);
    return worker->count == 0U
        && reservation_count == reservations_before + 2U
        && release_count == releases_before + 2U ? 0 : 5;
}

static int check_invalid_memory_command(
    struct mb_worker_state *worker,
    const mb_u8 *request,
    size_t request_len,
    mb_u32 expected_code)
{
    mb_u8 *response = NULL;
    size_t response_len = 0U;
    if (!mb_worker_handle_memory(
            worker, request, request_len, &response, &response_len)
        || response == NULL
        || response_len != MB_NATIVE_PROCESS_MEMORY_FAILURE_RESPONSE_BYTES
        || response[MB_NATIVE_PROCESS_COMMAND_OFFSET]
            != request[MB_NATIVE_PROCESS_COMMAND_OFFSET]
        || response[MB_NATIVE_PROCESS_OUTCOME_OFFSET]
            != MB_NATIVE_PROCESS_MEMORY_FAILURE
        || mb_native_process_read_u32(&response[10]) != expected_code) {
        mb_worker_free(response);
        return 1;
    }
    mb_worker_free(response);
    return 0;
}

static int check_malformed_memory_commands(struct mb_worker_state *worker)
{
    mb_u8 allocate[26] = {0};
    mb_u8 *response = NULL;
    size_t response_len = 0U;
    memcpy(allocate, MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
    mb_native_process_write_u64(&allocate[9], 64U);
    mb_native_process_write_u64(&allocate[17], 131072U);
    allocate[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    if (!mb_worker_handle_allocate(
            worker, allocate, 26U, &response, &response_len)
        || response == NULL || response_len != 35U) {
        mb_worker_free(response);
        return 1;
    }
    const mb_u64 mapping_id = mb_native_process_read_u64(&response[10]);
    const mb_u64 address = mb_native_process_read_u64(&response[18]);
    mb_worker_free(response);
    mb_u8 sentinel[64];
    memset(sentinel, 'X', sizeof(sentinel));
    mb_worker_copy_bytes(worker->mappings[0].base,
        sentinel, sizeof(sentinel));
    for (size_t index = 0U; index < 17U; ++index) {
        mb_u8 frame[48] = {0};
        size_t request_len = 43U;
        mb_u32 failure_code = MB_WORKER_MAPPING_NOT_FOUND;
        memcpy(frame, MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
        frame[8] = MB_NATIVE_PROCESS_MEMORY_COPY;
        mb_native_process_write_u64(&frame[9], mapping_id);
        mb_native_process_write_u64(&frame[17], address);
        mb_native_process_write_u64(&frame[25], 64U);
        frame[33] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
        mb_native_process_write_u64(&frame[34], 1U);
        frame[42] = 'Z';
        switch (index) {
        case 0U:
        case 1U:
        case 2U:
        case 3U:
            memcpy(frame, allocate, 26U);
            request_len = index == 0U ? 25U : 26U;
            failure_code = MB_WORKER_INVALID_REQUEST;
            if (index == 1U) {
                mb_native_process_write_u64(&frame[9], 0U);
            } else if (index == 2U) {
                mb_native_process_write_u64(&frame[17], 3U);
            } else if (index == 3U) {
                frame[25] = MB_NATIVE_PROCESS_MEMORY_READ_EXECUTE;
            }
            break;
        case 4U:
            request_len = 41U;
            failure_code = MB_WORKER_INVALID_REQUEST;
            break;
        case 5U:
            mb_native_process_write_u64(&frame[9], mapping_id + 1U);
            break;
        case 6U:
            mb_native_process_write_u64(&frame[17], address + 1U);
            break;
        case 7U:
            mb_native_process_write_u64(&frame[25], 63U);
            break;
        case 8U:
            mb_native_process_write_u64(&frame[34], 65U);
            break;
        case 9U:
            mb_native_process_write_u64(&frame[34], 0U);
            break;
        case 10U:
            frame[33] = MB_NATIVE_PROCESS_MEMORY_READ_EXECUTE;
            break;
        case 11U:
            frame[8] = MB_NATIVE_PROCESS_MEMORY_PROTECT;
            request_len = 34U;
            frame[33] = MB_NATIVE_PROCESS_MEMORY_READ_EXECUTE;
            failure_code = MB_WORKER_INVALID_REQUEST;
            break;
        case 12U:
            frame[8] = MB_NATIVE_PROCESS_MEMORY_RELEASE;
            request_len = 33U;
            mb_native_process_write_u64(&frame[9], mapping_id + 1U);
            break;
        case 13U:
            frame[8] = MB_NATIVE_PROCESS_MEMORY_SYNCHRONIZE;
            request_len = 33U;
            break;
        case 14U:
            frame[8] = 0xffU;
            request_len = 9U;
            failure_code = MB_WORKER_INVALID_REQUEST;
            break;
        case 15U:
            frame[8] = MB_NATIVE_PROCESS_MEMORY_PROTECT;
            request_len = 35U;
            failure_code = MB_WORKER_INVALID_REQUEST;
            break;
        default:
            frame[8] = MB_NATIVE_PROCESS_MEMORY_COPY;
            mb_native_process_write_u64(&frame[34], (mb_u64)-1);
            break;
        }
        if (check_invalid_memory_command(
                worker, frame, request_len, failure_code) != 0
            || worker->count != 1U
            || worker->mappings[0].permission
                != MB_NATIVE_PROCESS_MEMORY_READ_WRITE
            || memcmp(worker->mappings[0].base,
                sentinel, sizeof(sentinel)) != 0) {
            return (int)(index + 2U);
        }
    }
    mb_u8 release[33] = {0};
    memcpy(release, MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
    release[8] = MB_NATIVE_PROCESS_MEMORY_RELEASE;
    mb_native_process_write_u64(&release[9], mapping_id);
    mb_native_process_write_u64(&release[17], address);
    mb_native_process_write_u64(&release[25], 64U);
    if (!mb_worker_handle_release(worker, release, 33U,
            &response, &response_len)
        || response_len != 10U || worker->count != 0U) {
        mb_worker_free(response);
        return 20;
    }
    mb_worker_free(response);
    return check_mapping_lifecycle(worker) == 0 ? 0 : 21;
}

int main(void)
{
    struct mb_worker_state worker = {.next_id = 1U};
    const int first = check_mapping_lifecycle(&worker);
    if (first != 0) {
        return first;
    }
    const int second = check_mapping_lifecycle(&worker);
    if (second != 0) {
        return second;
    }
    if (check_overflow_rejected(&worker) != 0) {
        return 7;
    }
    if (check_teardown_releases_backing(&worker) != 0) {
        return 8;
    }
    if (reservation_count != 3U || release_count != 3U
        || protect_count != 2U || sync_count != 2U) {
        return 9;
    }
    if (check_compaction_and_teardown(&worker) != 0) {
        return 10;
    }
    if (reservation_count != 9U || release_count != 9U
        || protect_count != 7U || sync_count != 7U) {
        return 11;
    }
    if (check_win32_failure_recovery(&worker) != 0) {
        return 12;
    }
    if (reservation_count != 10U || release_count != 10U
        || protect_count != 8U || sync_count != 8U) {
        return 13;
    }
    const int call_failure = check_native_call_guarding(&worker);
    if (call_failure != 0) {
        return 14 + call_failure;
    }
    if (reservation_count != 11U || release_count != 11U
        || protect_count != 9U || native_entry_invocations != 1U) {
        return 15;
    }
    const int frame_result = check_frame_io();
    if (frame_result != 0) {
        return 16 + frame_result;
    }
    if (check_protect_report_mismatch(&worker) != 0) {
        return 33;
    }
    if (check_mapping_table_growth_failure(&worker) != 0) {
        return 34;
    }
    if (check_unreportable_mapping_cleanup(&worker) != 0) {
        return 35;
    }
    const int memory_failures = check_malformed_memory_commands(&worker);
    if (memory_failures != 0) {
        return 40 + memory_failures;
    }
    return 0;
}
