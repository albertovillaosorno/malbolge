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
// Compile callable entries with the actual Microsoft x64 native ABI.
#define MB_NATIVE_POSIX_WINDOWS_X64_BRIDGE
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

static struct mb_mock_reservation reservations[96];
static size_t reservation_count;
static size_t protect_count;
static size_t sync_count;
static const void *last_sync_address;
static size_t last_sync_len;
static size_t release_count;
static int recycle_next_release;
static void *recycled_allocation;
static void *recycled_base;
static size_t recycled_len;
static int fail_next_virtual_alloc;
static int fail_next_protect;
static int unexpected_old_protect;
static int fail_first_mapping_heap_alloc;
static int fail_next_heap_realloc;
static int fail_next_mapping_response;
static int fail_next_copy_response;
static int fail_next_sync_response;
static int fail_next_release_response;
static int fail_next_call_response;
static int fail_next_call_memory_alloc;
static int fail_next_call_output_alloc;
static size_t heap_free_count;
static size_t frame_body_allocations;
static size_t rejected_huge_frame_allocations;
static size_t fail_frame_body_allocation_number;
static int fail_next_invalid_call_response;
static int fail_next_release;
static int fail_next_sync;
static char mock_input_handle;
static char mock_output_handle;
static char mock_process_handle;
static char mock_heap_handle;
static const mb_u8 *mock_read_source;
static mb_u8 *mock_dynamic_wire;
static size_t mock_read_len;
static size_t mock_read_pos;
static size_t mock_read_chunk;
static mb_win_dword mock_last_read_request;
static int mock_fail_read;
static int mock_fail_read_with_count;
static int mock_read_overreport;
static size_t mock_read_overreport_after;
static size_t mock_fail_read_after;
static mb_win_dword mock_read_error = 5UL;
static mb_u8 mock_write_buffer[256];
static size_t mock_write_pos;
static size_t mock_write_chunk;
static mb_win_dword mock_last_write_request;
static int mock_fail_write;
static int mock_write_overreport;
static size_t mock_write_overreport_after;
static size_t mock_fail_write_after = (size_t)-1;

mb_win_handle GetCurrentProcess(void) { return &mock_process_handle; }
mb_win_dword GetLastError(void) { return mock_read_error; }
mb_win_handle GetProcessHeap(void) { return &mock_heap_handle; }
mb_win_handle GetStdHandle(mb_win_dword kind)
{
    if (kind == MB_WIN_STD_INPUT_HANDLE) {
        return &mock_input_handle;
    }
    if (kind == MB_WIN_STD_OUTPUT_HANDLE) {
        return &mock_output_handle;
    }
    return NULL;
}
void *HeapAlloc(mb_win_handle heap, mb_win_dword flags, size_t len)
{
    if (heap != &mock_heap_handle || flags != 0U) {
        return NULL;
    }
    if (len == (size_t)-1) {
        rejected_huge_frame_allocations += 1U;
        return NULL;
    }
    if (len == sizeof(struct mb_worker_mapping) * 4U
        && fail_first_mapping_heap_alloc != 0) {
        fail_first_mapping_heap_alloc = 0;
        return NULL;
    }
    if (len == 26U) {
        frame_body_allocations += 1U;
        if (frame_body_allocations == fail_frame_body_allocation_number) {
            return NULL;
        }
    }
    if (len == 4U && fail_next_call_memory_alloc != 0) {
        fail_next_call_memory_alloc = 0;
        return NULL;
    }
    if (len == 3U && fail_next_call_output_alloc != 0) {
        fail_next_call_output_alloc = 0;
        return NULL;
    }
    if (len == 74U && fail_next_invalid_call_response != 0) {
        fail_next_invalid_call_response = 0;
        return NULL;
    }
    if (len == 81U && fail_next_call_response != 0) {
        fail_next_call_response = 0;
        return NULL;
    }
    if (len == MB_NATIVE_PROCESS_MEMORY_MAPPING_RESPONSE_BYTES
        && fail_next_mapping_response != 0) {
        fail_next_mapping_response = 0;
        return NULL;
    }
    if (len == 32U && fail_next_copy_response != 0) {
        fail_next_copy_response = 0;
        return NULL;
    }
    if (len == MB_NATIVE_PROCESS_MEMORY_SYNC_RESPONSE_BYTES
        && fail_next_sync_response != 0) {
        fail_next_sync_response = 0;
        return NULL;
    }
    if (len == MB_NATIVE_PROCESS_MEMORY_RELEASE_RESPONSE_BYTES
        && fail_next_release_response != 0) {
        fail_next_release_response = 0;
        return NULL;
    }
    return malloc(len);
}
void *HeapReAlloc(mb_win_handle heap, mb_win_dword flags, void *ptr, size_t len)
{
    if (heap != &mock_heap_handle || flags != 0U) {
        return NULL;
    }
    if (fail_next_heap_realloc != 0) {
        fail_next_heap_realloc = 0;
        return NULL;
    }
    return realloc(ptr, len);
}
mb_win_bool HeapFree(mb_win_handle heap, mb_win_dword flags, void *ptr)
{
    if (heap != &mock_heap_handle || flags != 0U) {
        return 0;
    }
    free(ptr);
    heap_free_count += 1U;
    return 1;
}
mb_win_bool ReadFile(
    mb_win_handle handle, void *buffer, mb_win_dword len,
    mb_win_dword *read, void *overlapped)
{
    (void)overlapped;
    if (handle != &mock_input_handle) {
        *read = 0U;
        return 0;
    }
    mock_last_read_request = len;
    if (mock_read_overreport != 0
        && mock_read_pos >= mock_read_overreport_after) {
        mock_read_overreport = 0;
        *read = len + 1UL;
        return 1;
    }
    if (mock_fail_read != 0
        && mock_read_pos >= mock_fail_read_after) {
        mock_fail_read = 0;
        *read = mock_fail_read_with_count != 0 ? 1UL : 0UL;
        mock_fail_read_with_count = 0;
        return 0;
    }
    if (mock_dynamic_wire != NULL && mock_read_pos >= 34U) {
        const mb_u64 id = mb_native_process_read_u64(&mock_write_buffer[18]);
        const mb_u64 base = mb_native_process_read_u64(&mock_write_buffer[26]);
        for (size_t offset = 0U; offset < 4U; ++offset) {
            const size_t starts[4] = {42U, 98U, 140U, 181U};
            mb_native_process_write_u64(
                &mock_dynamic_wire[starts[offset] + 9U], id);
            mb_native_process_write_u64(
                &mock_dynamic_wire[starts[offset] + 17U], base);
        }
        mock_dynamic_wire = NULL;
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
    (void)overlapped;
    if (handle != &mock_output_handle) {
        *written = 0U;
        return 0;
    }
    mock_last_write_request = len;
    if (mock_write_overreport != 0
        && mock_write_pos >= mock_write_overreport_after) {
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
    if (fail_next_virtual_alloc != 0) {
        fail_next_virtual_alloc = 0;
        return NULL;
    }
    if (address != NULL || flags != (MB_WIN_MEM_RESERVE | MB_WIN_MEM_COMMIT)
        || protect != MB_WIN_PAGE_READWRITE
        || reservation_count >= 96U || len > 1048576U) {
        return NULL;
    }
    void *allocation = recycled_allocation;
    void *base = recycled_base;
    if (allocation != NULL) {
        if (len != recycled_len) {
            return NULL;
        }
        recycled_allocation = NULL;
        recycled_base = NULL;
        recycled_len = 0U;
    } else {
        const size_t total = len + 262144U;
        allocation = malloc(total);
        if (allocation == NULL) {
            return NULL;
        }
        const uintptr_t start = (uintptr_t)allocation;
        const uintptr_t aligned = (start + 131071U)
            & ~(uintptr_t)131071U;
        base = (void *)(aligned + 65536U);
    }
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
            if (recycle_next_release != 0) {
                recycle_next_release = 0;
                recycled_allocation = reservations[i].allocation;
                recycled_base = reservations[i].base;
                recycled_len = reservations[i].len;
            } else {
                free(reservations[i].allocation);
            }
            release_count += 1U;
            return 1;
        }
    }
    return 0;
}
mb_win_bool FlushInstructionCache(
    mb_win_handle process, const void *address, size_t len)
{
    if (process != &mock_process_handle) {
        return 0;
    }
    last_sync_address = address;
    last_sync_len = len;
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
static size_t empty_native_entry_invocations;
static size_t corrupted_shape_invocations;
static size_t exact_progress_invocations;
static size_t raw_status_invocations;
static size_t invalid_termination_invocations;
static int next_simulated_raw_status;
static size_t pointer_drift_invocations;
static size_t pointer_drift_field;

static int __attribute__((ms_abi)) mb_simulated_corrupt_shape_entry(
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

static int __attribute__((ms_abi)) mb_simulated_invalid_termination_entry(
    struct mb_native_region_state *state)
{
    invalid_termination_invocations += 1U;
    state->termination = 0xffU;
    return MB_NATIVE_APPLIED;
}

static int __attribute__((ms_abi)) mb_simulated_raw_status_entry(
    struct mb_native_region_state *state)
{
    raw_status_invocations += 1U;
    if (state->memory_words != 1U || state->memory[0] != 8U
        || state->input_len != 2U || state->input_consumed != 0U
        || state->output_capacity != 3U || state->output_len != 1U
        || state->output[0] != 0x10U || state->accumulator != 7U) {
        return MB_NATIVE_INVALID_ARGUMENT;
    }
    return next_simulated_raw_status;
}

static int __attribute__((ms_abi)) mb_simulated_exact_progress_entry(
    struct mb_native_region_state *state)
{
    exact_progress_invocations += 1U;
    if (state->input_len != 2U || state->input_consumed != 2U
        || state->output_capacity != 3U || state->output_len != 3U
        || state->input[0] != 0xa5U || state->input[1] != 0xb6U
        || state->output[0] != 0x10U || state->output[1] != 0U
        || state->output[2] != 0U || state->memory[0] != 8U) {
        return MB_NATIVE_INVALID_ARGUMENT;
    }
    return MB_NATIVE_GUARD_MISS;
}

static int __attribute__((ms_abi)) mb_simulated_empty_native_entry(
    struct mb_native_region_state *state)
{
    empty_native_entry_invocations += 1U;
    if (state->memory != NULL || state->input != NULL
        || state->output != NULL || state->memory_words != 0U
        || state->input_len != 0U || state->output_capacity != 0U
        || state->input_consumed != 0U || state->output_len != 0U) {
        return MB_NATIVE_INVALID_ARGUMENT;
    }
    state->accumulator += 1U;
    return MB_NATIVE_GUARD_MISS;
}

static int __attribute__((ms_abi)) mb_simulated_pointer_drift_entry(
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


static int __attribute__((ms_abi)) mb_simulated_native_entry(
    struct mb_native_region_state *state)
{
    native_entry_invocations += 1U;
    state->memory[0] += 2U;
    state->output[state->output_len] = state->input[state->input_consumed];
    state->input_consumed += 1U;
    state->output_len += 1U;
    state->accumulator += 1U;
    state->code_pointer = 0x123U;
    state->data_pointer = 0x456U;
    state->termination = MB_NATIVE_TERMINATION_HALT_INSTRUCTION;
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
        || mb_native_process_read_u32(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_CODE_POINTER_OFFSET])
            != (changed != 0 ? 0x123U : 0U)
        || mb_native_process_read_u32(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_DATA_POINTER_OFFSET])
            != (changed != 0 ? 0x456U : 0U)
        || response[MB_NATIVE_PROCESS_CALL_RESPONSE_TERMINATION_OFFSET]
            != (changed != 0 ? MB_NATIVE_TERMINATION_HALT_INSTRUCTION
                : request[MB_NATIVE_PROCESS_CALL_REQUEST_TERMINATION_OFFSET])) {
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

static int check_native_call_staging_failures(
    struct mb_worker_state *worker, const mb_u8 *request)
{
    const size_t calls_before = native_entry_invocations;
    const size_t frees_before = heap_free_count;
    const mb_u64 id = worker->mappings[0].id;
    const mb_u8 *const base = worker->mappings[0].base;
    mb_u8 *response = NULL;
    size_t len = 0U;
    fail_next_call_memory_alloc = 1;
    if (mb_worker_handle_call(worker, request, 86U, &response, &len)
        || response != NULL || len != 0U
        || heap_free_count != frees_before + 1U
        || native_entry_invocations != calls_before) {
        mb_worker_free(response);
        return 1;
    }
    fail_next_call_output_alloc = 1;
    if (mb_worker_handle_call(worker, request, 86U, &response, &len)
        || response != NULL || len != 0U
        || heap_free_count != frees_before + 2U
        || native_entry_invocations != calls_before) {
        mb_worker_free(response);
        return 2;
    }
    if (worker->count != 1U || worker->mappings[0].id != id
        || worker->mappings[0].base != base
        || worker->mappings[0].permission
            != MB_NATIVE_PROCESS_MEMORY_READ_EXECUTE) {
        return 3;
    }
    if (check_native_call_shape(worker, request, MB_NATIVE_APPLIED, 1)
        || native_entry_invocations != calls_before + 1U) {
        return 4;
    }
    return 0;
}

static int check_unreportable_native_call(
    struct mb_worker_state *worker, const mb_u8 *request)
{
    mb_u8 *response = NULL;
    size_t len = 0U;
    const size_t before = native_entry_invocations;
    const mb_u64 mapping_id = worker->mappings[0].id;
    const mb_u8 *const base = worker->mappings[0].base;
    fail_next_call_response = 1;
    if (mb_worker_handle_call(worker, request, 86U, &response, &len) != 0
        || response != NULL || len != 0U
        || native_entry_invocations != before + 1U
        || worker->count != 1U || worker->mappings[0].id != mapping_id
        || worker->mappings[0].base != base
        || worker->mappings[0].permission
            != MB_NATIVE_PROCESS_MEMORY_READ_EXECUTE) {
        mb_worker_free(response);
        return 1;
    }
    if (check_native_call_shape(worker, request, MB_NATIVE_APPLIED, 1)) {
        return 2;
    }
    return 0;
}

static int check_empty_native_call_shape(
    struct mb_worker_state *worker, mb_u64 mapping_id)
{
    mb_u8 frame[MB_NATIVE_PROCESS_CALL_REQUEST_FIXED_BYTES] = {0};
    mb_u8 *response = NULL;
    size_t len = 0U;
    memcpy(frame, MB_NATIVE_PROCESS_CALL_MAGIC, 8U);
    mb_native_process_write_u64(&frame[8], mapping_id);
    mb_native_process_write_u32(&frame[64], 9U);
    if (!mb_worker_handle_call(worker, frame, sizeof(frame),
            &response, &len)
        || len != MB_NATIVE_PROCESS_CALL_RESPONSE_FIXED_BYTES) {
        mb_worker_free(response);
        return 1;
    }
    const int valid = mb_native_process_read_u32(&response[69])
            == MB_NATIVE_GUARD_MISS
        && response[73] == 1U
        && mb_native_process_read_u32(&response[56]) == 10U
        && mb_native_process_read_u64(&response[16]) == 0U
        && mb_native_process_read_u64(&response[24]) == 0U
        && mb_native_process_read_u64(&response[32]) == 0U
        && empty_native_entry_invocations == 1U;
    mb_worker_free(response);
    if (!valid) {
        return 2;
    }
    mb_native_process_write_u64(&frame[48], 1U);
    if (!mb_worker_handle_call(worker, frame, sizeof(frame),
            &response, &len)
        || len != MB_NATIVE_PROCESS_CALL_RESPONSE_FIXED_BYTES
        || mb_native_process_read_u32(&response[69])
            != MB_NATIVE_INVALID_ARGUMENT
        || empty_native_entry_invocations != 1U) {
        mb_worker_free(response);
        return 3;
    }
    mb_worker_free(response);
    mb_native_process_write_u64(&frame[48], 0U);
    mb_native_process_write_u64(&frame[56], 1U);
    if (!mb_worker_handle_call(worker, frame, sizeof(frame),
            &response, &len)
        || len != MB_NATIVE_PROCESS_CALL_RESPONSE_FIXED_BYTES
        || mb_native_process_read_u32(&response[69])
            != MB_NATIVE_INVALID_ARGUMENT
        || empty_native_entry_invocations != 1U) {
        mb_worker_free(response);
        return 4;
    }
    mb_worker_free(response);
    return 0;
}

static int check_untrusted_termination(
    struct mb_worker_state *worker, const mb_u8 *request)
{
    mb_u8 *response = NULL;
    size_t len = 0U;
    const size_t before = invalid_termination_invocations;
    if (!mb_worker_handle_call(worker, request, 86U, &response, &len)
        || len != 81U) {
        mb_worker_free(response);
        return 1;
    }
    const int valid = mb_native_process_read_u32(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_STATUS_OFFSET])
            == MB_NATIVE_APPLIED
        && response[MB_NATIVE_PROCESS_CALL_RESPONSE_TERMINATION_OFFSET]
            == 0xffU
        && response[MB_NATIVE_PROCESS_CALL_RESPONSE_POINTER_FLAG_OFFSET]
            == 1U
        && mb_native_process_read_u32(&response[74]) == 8U
        && mb_native_process_read_u32(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_ACCUMULATOR_OFFSET])
            == 7U
        && mb_native_process_read_u64(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_INPUT_CONSUMED_OFFSET])
            == 0U
        && mb_native_process_read_u64(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_OUTPUT_LEN_OFFSET])
            == 1U
        && response[78] == 0x10U && response[79] == 0U
        && invalid_termination_invocations == before + 1U;
    mb_worker_free(response);
    return valid ? 0 : 2;
}

static int check_untrusted_raw_status(
    struct mb_worker_state *worker, const mb_u8 *request, int expected)
{
    mb_u8 *response = NULL;
    size_t len = 0U;
    const size_t before = raw_status_invocations;
    next_simulated_raw_status = expected;
    if (!mb_worker_handle_call(worker, request, 86U, &response, &len)
        || len != 81U) {
        mb_worker_free(response);
        return 1;
    }
    const int valid = mb_native_process_read_u32(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_STATUS_OFFSET])
            == (mb_u32)expected
        && response[MB_NATIVE_PROCESS_CALL_RESPONSE_POINTER_FLAG_OFFSET]
            == 1U
        && mb_native_process_read_u32(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_ACCUMULATOR_OFFSET])
            == 7U
        && mb_native_process_read_u32(&response[74]) == 8U
        && mb_native_process_read_u64(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_INPUT_CONSUMED_OFFSET])
            == 0U
        && mb_native_process_read_u64(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_OUTPUT_LEN_OFFSET])
            == 1U
        && response[78] == 0x10U && response[79] == 0U
        && raw_status_invocations == before + 1U;
    mb_worker_free(response);
    return valid ? 0 : 2;
}

static int check_exact_native_progress(
    struct mb_worker_state *worker, const mb_u8 *original)
{
    mb_u8 request[86] = {0};
    mb_worker_copy_bytes(request, original, sizeof(request));
    mb_native_process_write_u64(
        &request[MB_NATIVE_PROCESS_CALL_REQUEST_INPUT_CONSUMED_OFFSET], 2U);
    mb_native_process_write_u64(
        &request[MB_NATIVE_PROCESS_CALL_REQUEST_OUTPUT_LEN_OFFSET], 3U);
    mb_u8 *response = NULL;
    size_t len = 0U;
    const size_t before = exact_progress_invocations;
    if (!mb_worker_handle_call(worker, request, sizeof(request),
            &response, &len) || len != 81U) {
        mb_worker_free(response);
        return 1;
    }
    const int valid = mb_native_process_read_u32(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_STATUS_OFFSET])
            == MB_NATIVE_GUARD_MISS
        && response[MB_NATIVE_PROCESS_CALL_RESPONSE_POINTER_FLAG_OFFSET]
            == 1U
        && mb_native_process_read_u64(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_INPUT_CONSUMED_OFFSET])
            == 2U
        && mb_native_process_read_u64(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_OUTPUT_LEN_OFFSET])
            == 3U
        && mb_native_process_read_u32(&response[74]) == 8U
        && response[78] == 0x10U
        && response[79] == 0U && response[80] == 0U
        && exact_progress_invocations == before + 1U;
    mb_worker_free(response);
    return valid ? 0 : 2;
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
    const int staging_failure = check_native_call_staging_failures(
        worker, request);
    if (staging_failure != 0) {
        return 25 + staging_failure;
    }
    if (check_unreportable_native_call(worker, request) != 0) {
        return 15;
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
#if defined(__aarch64__)
    // Run with the ARM64 admission rule, but retain the host x64 C stub.
    for (mb_u64 misaligned = 1U; misaligned < 64U; ++misaligned) {
        if ((misaligned & 3U) == 0U) {
            continue;
        }
        mb_native_process_write_u64(&request[16], misaligned);
        if (check_native_call_shape(
                worker, request, MB_NATIVE_INVALID_ARGUMENT, 0)) {
            return 32;
        }
    }
#endif
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
    mb_native_entry_fn raw_entry = mb_simulated_raw_status_entry;
    mb_worker_copy_bytes(&native_address, &raw_entry, sizeof(raw_entry));
    worker->mappings[0].base = native_address;
    if (check_untrusted_raw_status(worker, request, MB_NATIVE_APPLIED)
        || check_untrusted_raw_status(worker, request, 127)) {
        return 18;
    }
    mb_native_entry_fn invalid_end = mb_simulated_invalid_termination_entry;
    mb_worker_copy_bytes(&native_address, &invalid_end, sizeof(invalid_end));
    worker->mappings[0].base = native_address;
    if (check_untrusted_termination(worker, request) != 0) {
        return 19;
    }
    mb_native_entry_fn exact_entry = mb_simulated_exact_progress_entry;
    mb_worker_copy_bytes(
        &native_address, &exact_entry, sizeof(exact_entry));
    worker->mappings[0].base = native_address;
    if (check_exact_native_progress(worker, request) != 0) {
        return 17;
    }
    mb_native_entry_fn empty_entry = mb_simulated_empty_native_entry;
    mb_worker_copy_bytes(&native_address, &empty_entry, sizeof(empty_entry));
    worker->mappings[0].base = native_address;
    if (check_empty_native_call_shape(worker, id) != 0) {
        return 16;
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
    return native_entry_invocations == 4U
        && pointer_drift_invocations == 3U
        && corrupted_shape_invocations == 1U
        && exact_progress_invocations == 1U
        && raw_status_invocations == 2U
        && invalid_termination_invocations == 1U ? 0 : 9;
}

static int check_win32_dword_transfer_chunks(void)
{
    static_assert(sizeof(mb_win_dword) == 4U,
        "mock DWORD size must agree with the Windows ABI");
    static_assert(sizeof(size_t) > sizeof(mb_win_dword),
        "host test requires a 64-bit size_t");
    mb_u8 byte = 0U;
    const size_t huge = (size_t)MB_WIN_DWORD_MAX + 1U;
    mock_fail_read = 1;
    mock_fail_read_after = 0U;
    mock_read_pos = 0U;
    mock_last_read_request = 0U;
    if (mb_worker_read_exact(&mock_input_handle, &byte, huge, 0) != -1
        || mock_last_read_request != MB_WIN_DWORD_MAX) {
        return 1;
    }
    mock_fail_write = 1;
    mock_fail_write_after = (size_t)-1;
    mock_last_write_request = 0U;
    if (mb_worker_write_exact(&mock_output_handle, &byte, huge) != 0
        || mock_last_write_request != MB_WIN_DWORD_MAX) {
        return 2;
    }
    if (mb_worker_read_exact(&mock_output_handle, &byte, 1U, 0) != -1
        || mb_worker_write_exact(&mock_input_handle, &byte, 1U) != 0
        || GetStdHandle(0U) != NULL) {
        return 3;
    }
    const size_t syncs_before = sync_count;
    if (HeapAlloc(&mock_input_handle, 0U, 16U) != NULL
        || HeapReAlloc(&mock_output_handle, 0U, NULL, 16U) != NULL
        || HeapFree(&mock_process_handle, 0U, NULL) != 0
        || FlushInstructionCache(&mock_heap_handle, &byte, 1U) != 0
        || sync_count != syncs_before) {
        return 4;
    }
    return 0;
}

static void mb_mock_read_reset(const mb_u8 *bytes, size_t len)
{
    mock_read_source = bytes;
    mock_read_len = len;
    mock_read_pos = 0U;
    mock_read_chunk = 2U;
    mock_fail_read = 0;
    mock_fail_read_with_count = 0;
    mock_read_overreport = 0;
    mock_read_overreport_after = 0U;
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
    mb_mock_read_reset(wire, 8U);
    mock_read_overreport = 1;
    mock_read_overreport_after = 2U;
    if (mb_worker_read_frame(&payload, &len) != -1
        || mock_read_pos != 2U) {
        return 17;
    }
    mb_native_process_write_u64(wire, 3U);
    mb_mock_read_reset(wire, sizeof(wire));
    mock_read_overreport = 1;
    mock_read_overreport_after = 8U;
    if (mb_worker_read_frame(&payload, &len) != -1
        || mock_read_pos != 8U) {
        return 18;
    }
    mock_write_pos = 0U;
    mock_write_overreport = 1;
    mock_write_overreport_after = 2U;
    if (mb_worker_write_frame(NULL, 0U) != 0
        || mock_write_pos != 2U) {
        return 19;
    }
    mock_write_pos = 0U;
    mock_write_overreport = 1;
    mock_write_overreport_after = 8U;
    if (mb_worker_write_frame((const mb_u8 *)"xyz", 3U) != 0
        || mock_write_pos != 8U) {
        return 20;
    }
    mock_write_overreport_after = 0U;
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
        mock_fail_read_with_count = 1;
        mock_read_error = error_code;
        if (mb_worker_read_frame(&payload, &len) != -1) {
            return 16;
        }
        mb_mock_read_reset(wire, 8U);
        mock_fail_read = 1;
        mock_fail_read_after = 2U;
        mock_read_error = error_code;
        if (mb_worker_read_frame(&payload, &len) != -1) {
            return 11;
        }
        mb_mock_read_reset(wire, sizeof(wire));
        mock_fail_read = 1;
        mock_fail_read_with_count = 1;
        mock_fail_read_after = 2U;
        mock_read_error = error_code;
        if (mb_worker_read_frame(&payload, &len) != -1
            || mock_read_pos != 2U) {
            return 21;
        }
        mb_mock_read_reset(wire, sizeof(wire));
        mock_fail_read = 1;
        mock_fail_read_with_count = 1;
        mock_fail_read_after = 8U;
        mock_read_error = error_code;
        if (mb_worker_read_frame(&payload, &len) != -1
            || mock_read_pos != 8U) {
            return 22;
        }
        mb_native_process_write_u64(wire, 3U);
        mb_mock_read_reset(wire, sizeof(wire));
        mock_fail_read = 1;
        mock_fail_read_after = 8U;
        mock_read_error = error_code;
        if (mb_worker_read_frame(&payload, &len) != -1
            || mock_read_pos != 8U) {
            return 23;
        }
        mb_mock_read_reset(wire, sizeof(wire));
        mock_read_chunk = 1U;
        mock_fail_read = 1;
        mock_fail_read_after = 9U;
        mock_read_error = error_code;
        if (mb_worker_read_frame(&payload, &len) != -1
            || mock_read_pos != 9U) {
            return 24;
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

static int check_unreportable_copy_sync_release(
    struct mb_worker_state *worker)
{
    mb_u8 request[48] = {0};
    mb_u8 *response = NULL;
    size_t response_len = 0U;
    const size_t before_sync = sync_count;
    const size_t before_release = release_count;
    memcpy(request, MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
    mb_native_process_write_u64(&request[9], 64U);
    mb_native_process_write_u64(&request[17], 131072U);
    request[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    if (!mb_worker_handle_allocate(worker, request, 26U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_MAPPING_RESPONSE_BYTES) {
        mb_worker_free(response);
        return 1;
    }
    const mb_u64 id = mb_native_process_read_u64(&response[10]);
    const mb_u64 base = mb_native_process_read_u64(&response[18]);
    mb_worker_free(response);
    mb_native_process_write_u64(&request[9], id);
    mb_native_process_write_u64(&request[17], base);
    mb_native_process_write_u64(&request[25], 64U);
    request[33] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    mb_native_process_write_u64(&request[34], 6U);
    memcpy(&request[42], "ABCDEF", 6U);
    response = NULL;
    response_len = 0U;
    fail_next_copy_response = 1;
    if (mb_worker_handle_copy(worker, request, 48U,
            &response, &response_len) != 0
        || response != NULL || response_len != 0U
        || worker->count != 1U
        || memcmp(worker->mappings[0].base, "ABCDEF", 6U) != 0) {
        mb_worker_free(response);
        return 2;
    }
    const int protected = mb_worker_handle_protect(
        worker, request, 34U, &response, &response_len);
    if (!protected) {
        mb_worker_free(response);
        return 21;
    }
    if (response_len != MB_NATIVE_PROCESS_MEMORY_MAPPING_RESPONSE_BYTES) {
        mb_worker_free(response);
        return 22;
    }
    if (worker->mappings[0].permission
        != MB_NATIVE_PROCESS_MEMORY_READ_EXECUTE) {
        mb_worker_free(response);
        return 23;
    }
    mb_worker_free(response);
    response = NULL;
    response_len = 0U;
    fail_next_sync_response = 1;
    if (mb_worker_handle_sync(worker, request, 33U,
            &response, &response_len) != 0
        || response != NULL || response_len != 0U
        || sync_count != before_sync + 1U || worker->count != 1U) {
        mb_worker_free(response);
        return 4;
    }
    if (!mb_worker_handle_sync(worker, request, 33U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_SYNC_RESPONSE_BYTES
        || sync_count != before_sync + 2U) {
        mb_worker_free(response);
        return 5;
    }
    mb_worker_free(response);
    response = NULL;
    response_len = 0U;
    fail_next_release_response = 1;
    if (mb_worker_handle_release(worker, request, 33U,
            &response, &response_len) != 0
        || response != NULL || response_len != 0U
        || worker->count != 0U || release_count != before_release + 1U) {
        mb_worker_free(response);
        return 6;
    }
    if (!mb_worker_handle_release(worker, request, 33U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_FAILURE_RESPONSE_BYTES
        || mb_native_process_read_u32(&response[10])
            != MB_WORKER_MAPPING_NOT_FOUND
        || worker->count != 0U || release_count != before_release + 1U) {
        mb_worker_free(response);
        return 7;
    }
    mb_worker_free(response);
    return 0;
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

static int check_mixed_live_mapping_ids(struct mb_worker_state *worker)
{
    mb_u8 request[43] = {0};
    mb_u8 *response = NULL;
    size_t response_len = 0U;
    mb_u64 ids[2] = {0};
    mb_u64 bases[2] = {0};
    const size_t protects_before = protect_count;
    const size_t syncs_before = sync_count;
    const size_t releases_before = release_count;
    memcpy(request, MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
    mb_native_process_write_u64(&request[9], 64U);
    mb_native_process_write_u64(&request[17], 131072U);
    request[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    for (size_t index = 0U; index < 2U; ++index) {
        if (!mb_worker_handle_allocate(worker, request, 26U,
                &response, &response_len)
            || response_len
                != MB_NATIVE_PROCESS_MEMORY_MAPPING_RESPONSE_BYTES) {
            mb_worker_free(response);
            return 1;
        }
        ids[index] = mb_native_process_read_u64(&response[10]);
        bases[index] = mb_native_process_read_u64(&response[18]);
        mb_worker_free(response);
        memset(worker->mappings[index].base,
            index == 0U ? 'A' : 'B', 64U);
    }
    if (ids[0] == ids[1] || bases[0] == bases[1]) {
        return 2;
    }
    mb_native_process_write_u64(&request[9], ids[1]);
    mb_native_process_write_u64(&request[17], bases[0]);
    mb_native_process_write_u64(&request[25], 64U);
    request[33] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    mb_native_process_write_u64(&request[34], 1U);
    request[42] = 'Z';
    for (size_t case_index = 0U; case_index < 3U; ++case_index) {
        size_t request_len = 33U;
        mb_u32 failure = MB_WORKER_MAPPING_NOT_FOUND;
        switch (case_index) {
        case 0U:
            request[8] = MB_NATIVE_PROCESS_MEMORY_COPY;
            request_len = 43U;
            break;
        case 1U:
            request[8] = MB_NATIVE_PROCESS_MEMORY_PROTECT;
            request_len = 34U;
            failure = MB_WORKER_INVALID_REQUEST;
            break;
        default:
            request[8] = MB_NATIVE_PROCESS_MEMORY_RELEASE;
            break;
        }
        if (check_invalid_memory_command(worker, request,
                request_len, failure) != 0
            || worker->count != 2U
            || protect_count != protects_before
            || sync_count != syncs_before
            || release_count != releases_before
            || worker->mappings[0].base[0] != 'A'
            || worker->mappings[1].base[0] != 'B') {
            return (int)(case_index + 3U);
        }
    }
    for (size_t index = 0U; index < 2U; ++index) {
        mb_native_process_write_u64(&request[9], ids[index]);
        mb_native_process_write_u64(&request[17], bases[index]);
        request[8] = MB_NATIVE_PROCESS_MEMORY_COPY;
        if (!mb_worker_handle_copy(worker, request, 43U,
                &response, &response_len)
            || response_len != 27U || response[26] != 'Z') {
            mb_worker_free(response);
            return 7;
        }
        mb_worker_free(response);
        request[8] = MB_NATIVE_PROCESS_MEMORY_PROTECT;
        if (!mb_worker_handle_protect(worker, request, 34U,
                &response, &response_len)
            || response_len
                != MB_NATIVE_PROCESS_MEMORY_MAPPING_RESPONSE_BYTES) {
            mb_worker_free(response);
            return 8;
        }
        mb_worker_free(response);
    }
    mb_native_process_write_u64(&request[9], ids[1]);
    mb_native_process_write_u64(&request[17], bases[0]);
    request[8] = MB_NATIVE_PROCESS_MEMORY_SYNCHRONIZE;
    if (check_invalid_memory_command(worker, request, 33U,
            MB_WORKER_MAPPING_NOT_FOUND) != 0
        || sync_count != syncs_before
        || worker->count != 2U) {
        return 9;
    }
    for (size_t index = 0U; index < 2U; ++index) {
        mb_native_process_write_u64(&request[9], ids[index]);
        mb_native_process_write_u64(&request[17], bases[index]);
        if (!mb_worker_handle_sync(worker, request, 33U,
                &response, &response_len)
            || response_len != MB_NATIVE_PROCESS_MEMORY_SYNC_RESPONSE_BYTES) {
            mb_worker_free(response);
            return 10;
        }
        mb_worker_free(response);
        request[8] = MB_NATIVE_PROCESS_MEMORY_RELEASE;
        if (!mb_worker_handle_release(worker, request, 33U,
                &response, &response_len)
            || response_len
                != MB_NATIVE_PROCESS_MEMORY_RELEASE_RESPONSE_BYTES) {
            mb_worker_free(response);
            return 11;
        }
        mb_worker_free(response);
        request[8] = MB_NATIVE_PROCESS_MEMORY_SYNCHRONIZE;
    }
    return worker->count == 0U
        && protect_count == protects_before + 2U
        && sync_count == syncs_before + 2U
        && release_count == releases_before + 2U ? 0 : 12;
}

static int check_empty_and_full_code_copies(struct mb_worker_state *worker)
{
    mb_u8 request[107] = {0};
    mb_u8 *response = NULL;
    size_t response_len = 0U;
    memcpy(request, MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
    mb_native_process_write_u64(&request[9], 64U);
    mb_native_process_write_u64(&request[17], 131072U);
    request[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    if (!mb_worker_handle_allocate(worker, request, 26U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_MAPPING_RESPONSE_BYTES) {
        mb_worker_free(response);
        return 1;
    }
    const mb_u64 id = mb_native_process_read_u64(&response[10]);
    const mb_u64 base = mb_native_process_read_u64(&response[18]);
    mb_worker_free(response);
    memset(worker->mappings[0].base, 'A', 64U);
    mb_native_process_write_u64(&request[9], id);
    mb_native_process_write_u64(&request[17], base);
    mb_native_process_write_u64(&request[25], 64U);
    request[8] = MB_NATIVE_PROCESS_MEMORY_COPY;
    request[33] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    mb_native_process_write_u64(&request[34], 0U);
    if (!mb_worker_handle_copy(worker, request, 42U,
            &response, &response_len)
        || response_len != 26U
        || mb_native_process_read_u64(&response[10]) != id
        || mb_native_process_read_u64(&response[18]) != base
        || worker->mappings[0].base[0] != 'A') {
        mb_worker_free(response);
        return 2;
    }
    mb_worker_free(response);
    memset(&request[42], 'B', 65U);
    mb_native_process_write_u64(&request[34], 65U);
    if (!mb_worker_handle_copy(worker, request, 107U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_FAILURE_RESPONSE_BYTES
        || response[9] != MB_NATIVE_PROCESS_MEMORY_FAILURE
        || worker->mappings[0].base[0] != 'A'
        || worker->mappings[0].permission
            != MB_NATIVE_PROCESS_MEMORY_READ_WRITE) {
        mb_worker_free(response);
        return 3;
    }
    mb_worker_free(response);
    mb_native_process_write_u64(&request[34], 64U);
    if (!mb_worker_handle_copy(worker, request, 106U,
            &response, &response_len)
        || response_len != 90U
        || memcmp(&response[26], &request[42], 64U) != 0
        || memcmp(worker->mappings[0].base, &request[42], 64U) != 0) {
        mb_worker_free(response);
        return 4;
    }
    mb_worker_free(response);
    if (!mb_worker_handle_protect(worker, request, 34U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_MAPPING_RESPONSE_BYTES) {
        mb_worker_free(response);
        return 5;
    }
    mb_worker_free(response);
    if (!mb_worker_handle_sync(worker, request, 33U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_SYNC_RESPONSE_BYTES) {
        mb_worker_free(response);
        return 6;
    }
    mb_worker_free(response);
    if (!mb_worker_handle_release(worker, request, 33U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_RELEASE_RESPONSE_BYTES
        || worker->count != 0U) {
        mb_worker_free(response);
        return 7;
    }
    mb_worker_free(response);
    return 0;
}

static size_t first_native_mapping_calls;
static size_t second_native_mapping_calls;

static int __attribute__((ms_abi)) mb_first_live_native_entry(
    struct mb_native_region_state *state)
{
    first_native_mapping_calls += 1U;
    state->accumulator += 1U;
    return MB_NATIVE_GUARD_MISS;
}

static int __attribute__((ms_abi)) mb_second_live_native_entry(
    struct mb_native_region_state *state)
{
    second_native_mapping_calls += 1U;
    state->accumulator += 2U;
    return MB_NATIVE_APPLIED;
}

static int check_live_native_dispatch(
    struct mb_worker_state *worker, mb_u64 id, int status,
    mb_u32 expected_accumulator)
{
    mb_u8 request[MB_NATIVE_PROCESS_CALL_REQUEST_FIXED_BYTES] = {0};
    mb_u8 *response = NULL;
    size_t response_len = 0U;
    memcpy(request, MB_NATIVE_PROCESS_CALL_MAGIC, 8U);
    mb_native_process_write_u64(&request[8], id);
    mb_native_process_write_u32(&request[64], 5U);
    if (!mb_worker_handle_call(worker, request, sizeof(request),
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_CALL_RESPONSE_FIXED_BYTES) {
        mb_worker_free(response);
        return 1;
    }
    const int valid = mb_native_process_read_u32(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_STATUS_OFFSET])
            == (mb_u32)status
        && mb_native_process_read_u32(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_ACCUMULATOR_OFFSET])
            == expected_accumulator
        && response[MB_NATIVE_PROCESS_CALL_RESPONSE_POINTER_FLAG_OFFSET]
            == 1U;
    mb_worker_free(response);
    return valid ? 0 : 2;
}

static int check_two_live_native_mappings(struct mb_worker_state *worker)
{
    mb_u8 allocation[34] = {0};
    mb_u8 *response = NULL;
    size_t response_len = 0U;
    mb_u64 ids[2] = {0};
    mb_u64 bases[2] = {0};
    mb_native_entry_fn entries[2] = {
        mb_first_live_native_entry, mb_second_live_native_entry,
    };
    const size_t releases_before = release_count;
    memcpy(allocation, MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
    mb_native_process_write_u64(&allocation[9], 64U);
    mb_native_process_write_u64(&allocation[17], 131072U);
    allocation[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    for (size_t index = 0U; index < 2U; ++index) {
        if (!mb_worker_handle_allocate(worker, allocation, 26U,
                &response, &response_len)
            || response_len
                != MB_NATIVE_PROCESS_MEMORY_MAPPING_RESPONSE_BYTES) {
            mb_worker_free(response);
            return 1;
        }
        ids[index] = mb_native_process_read_u64(&response[10]);
        bases[index] = mb_native_process_read_u64(&response[18]);
        mb_worker_free(response);
        mb_native_process_write_u64(&allocation[9], ids[index]);
        mb_native_process_write_u64(&allocation[17], bases[index]);
        mb_native_process_write_u64(&allocation[25], 64U);
        allocation[33] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
        if (!mb_worker_handle_protect(worker, allocation, 34U,
                &response, &response_len)
            || response_len
                != MB_NATIVE_PROCESS_MEMORY_MAPPING_RESPONSE_BYTES) {
            mb_worker_free(response);
            return 2;
        }
        mb_worker_free(response);
        mb_u8 *native_address = NULL;
        mb_worker_copy_bytes(&native_address, &entries[index],
            sizeof(entries[index]));
        worker->mappings[index].base = native_address;
        mb_native_process_write_u64(&allocation[9], 64U);
        mb_native_process_write_u64(&allocation[17], 131072U);
        allocation[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    }
    if (ids[0] == ids[1] || bases[0] == bases[1]
        || check_live_native_dispatch(worker, ids[0],
            MB_NATIVE_GUARD_MISS, 6U)
        || check_live_native_dispatch(worker, ids[1],
            MB_NATIVE_APPLIED, 7U)
        || check_live_native_dispatch(worker, ids[0],
            MB_NATIVE_GUARD_MISS, 6U)) {
        return 3;
    }
    worker->mappings[0].base = (mb_u8 *)(mb_uintptr)bases[0];
    mb_native_process_write_u64(&allocation[9], ids[0]);
    mb_native_process_write_u64(&allocation[17], bases[0]);
    mb_native_process_write_u64(&allocation[25], 64U);
    if (!mb_worker_handle_release(worker, allocation, 33U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_RELEASE_RESPONSE_BYTES
        || worker->count != 1U) {
        mb_worker_free(response);
        return 4;
    }
    mb_worker_free(response);
    if (check_live_native_dispatch(worker, ids[0],
            MB_NATIVE_INVALID_ARGUMENT, 5U)
        || check_live_native_dispatch(worker, ids[1],
            MB_NATIVE_APPLIED, 7U)) {
        return 5;
    }
    worker->mappings[0].base = (mb_u8 *)(mb_uintptr)bases[1];
    mb_native_process_write_u64(&allocation[9], ids[1]);
    mb_native_process_write_u64(&allocation[17], bases[1]);
    if (!mb_worker_handle_release(worker, allocation, 33U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_RELEASE_RESPONSE_BYTES) {
        mb_worker_free(response);
        return 6;
    }
    mb_worker_free(response);
    return worker->count == 0U
        && first_native_mapping_calls == 2U
        && second_native_mapping_calls == 2U
        && release_count == releases_before + 2U ? 0 : 7;
}

static int check_stale_id_with_recycled_base(
    struct mb_worker_state *worker)
{
    mb_u8 request[48] = {0};
    mb_u8 call[MB_NATIVE_PROCESS_CALL_REQUEST_FIXED_BYTES] = {0};
    mb_u8 *response = NULL;
    size_t len = 0U;
    const size_t releases_before = release_count;
    memcpy(request, MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
    mb_native_process_write_u64(&request[9], 64U);
    mb_native_process_write_u64(&request[17], 131072U);
    request[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    if (!mb_worker_handle_allocate(worker, request, 26U,
            &response, &len) || len != 35U) {
        mb_worker_free(response);
        return 1;
    }
    const mb_u64 stale_id = mb_native_process_read_u64(&response[10]);
    const mb_u64 base = mb_native_process_read_u64(&response[18]);
    mb_worker_free(response);
    mb_native_process_write_u64(&request[9], stale_id);
    mb_native_process_write_u64(&request[17], base);
    mb_native_process_write_u64(&request[25], 64U);
    recycle_next_release = 1;
    if (!mb_worker_handle_release(worker, request, 33U,
            &response, &len) || len != 10U) {
        mb_worker_free(response);
        return 2;
    }
    mb_worker_free(response);
    mb_native_process_write_u64(&request[9], 64U);
    mb_native_process_write_u64(&request[17], 131072U);
    request[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    if (!mb_worker_handle_allocate(worker, request, 26U,
            &response, &len) || len != 35U) {
        mb_worker_free(response);
        return 3;
    }
    const mb_u64 live_id = mb_native_process_read_u64(&response[10]);
    const mb_u64 live_base = mb_native_process_read_u64(&response[18]);
    mb_worker_free(response);
    if (live_id == stale_id || live_base != base
        || recycled_allocation != NULL || worker->count != 1U) {
        return 4;
    }
    mb_native_process_write_u64(&request[9], stale_id);
    mb_native_process_write_u64(&request[17], base);
    mb_native_process_write_u64(&request[25], 64U);
    request[33] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    mb_native_process_write_u64(&request[34], 6U);
    memcpy(&request[42], "ABCDEF", 6U);
    for (size_t index = 0U; index < 3U; ++index) {
        int handled = 0;
        if (index == 0U) {
            handled = mb_worker_handle_copy(
                worker, request, 48U, &response, &len);
        } else if (index == 1U) {
            handled = mb_worker_handle_protect(
                worker, request, 34U, &response, &len);
        } else {
            handled = mb_worker_handle_release(
                worker, request, 33U, &response, &len);
        }
        if (!handled || len != MB_NATIVE_PROCESS_MEMORY_FAILURE_RESPONSE_BYTES
            || response[9] != MB_NATIVE_PROCESS_MEMORY_FAILURE
            || worker->count != 1U) {
            mb_worker_free(response);
            return 5;
        }
        mb_worker_free(response);
    }
    memcpy(call, MB_NATIVE_PROCESS_CALL_MAGIC, 8U);
    mb_native_process_write_u64(&call[8], stale_id);
    if (!mb_worker_handle_call(worker, call, sizeof(call),
            &response, &len)
        || len != MB_NATIVE_PROCESS_CALL_RESPONSE_FIXED_BYTES
        || mb_native_process_read_u32(
            &response[MB_NATIVE_PROCESS_CALL_RESPONSE_STATUS_OFFSET])
            != MB_NATIVE_INVALID_ARGUMENT) {
        mb_worker_free(response);
        return 6;
    }
    mb_worker_free(response);
    mb_native_process_write_u64(&request[9], live_id);
    if (!mb_worker_handle_copy(worker, request, 48U,
            &response, &len) || len != 32U
        || memcmp(&response[26], "ABCDEF", 6U) != 0) {
        mb_worker_free(response);
        return 7;
    }
    mb_worker_free(response);
    if (!mb_worker_handle_release(worker, request, 33U,
            &response, &len) || len != 10U || worker->count != 0U
        || release_count != releases_before + 2U) {
        mb_worker_free(response);
        return 8;
    }
    mb_worker_free(response);
    return 0;
}

static int check_independent_worker_mapping_ids(void)
{
    struct mb_worker_state first = {.next_id = 1U};
    struct mb_worker_state second = {.next_id = 1U};
    mb_u8 request[48] = {0};
    mb_u8 *response = NULL;
    size_t len = 0U;
    memcpy(request, MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
    mb_native_process_write_u64(&request[9], 64U);
    mb_native_process_write_u64(&request[17], 131072U);
    request[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    if (!mb_worker_handle_allocate(&first, request, 26U,
            &response, &len) || len != 35U) {
        mb_worker_free(response);
        return 1;
    }
    const mb_u64 first_id = mb_native_process_read_u64(&response[10]);
    const mb_u64 first_base = mb_native_process_read_u64(&response[18]);
    mb_worker_free(response);
    if (!mb_worker_handle_allocate(&second, request, 26U,
            &response, &len) || len != 35U) {
        mb_worker_free(response);
        return 2;
    }
    const mb_u64 second_id = mb_native_process_read_u64(&response[10]);
    const mb_u64 second_base = mb_native_process_read_u64(&response[18]);
    mb_worker_free(response);
    if (first_id != 1U || second_id != 1U
        || first_base == second_base) {
        return 3;
    }
    mb_native_process_write_u64(&request[9], first_id);
    mb_native_process_write_u64(&request[17], first_base);
    mb_native_process_write_u64(&request[25], 64U);
    if (!mb_worker_handle_release(&first, request, 33U,
            &response, &len) || len != 10U || first.count != 0U) {
        mb_worker_free(response);
        return 4;
    }
    mb_worker_free(response);
    mb_native_process_write_u64(&request[17], second_base);
    request[33] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    mb_native_process_write_u64(&request[34], 6U);
    memcpy(&request[42], "UVWXYZ", 6U);
    if (!mb_worker_handle_copy(&second, request, 48U,
            &response, &len) || len != 32U
        || memcmp(&response[26], "UVWXYZ", 6U) != 0) {
        mb_worker_free(response);
        return 5;
    }
    mb_worker_free(response);
    if (!mb_worker_handle_protect(&second, request, 34U,
            &response, &len) || len != 35U
        || response[34] != MB_NATIVE_PROCESS_MEMORY_READ_EXECUTE) {
        mb_worker_free(response);
        return 6;
    }
    mb_worker_free(response);
    if (!mb_worker_handle_sync(&second, request, 33U,
            &response, &len) || len != 34U) {
        mb_worker_free(response);
        return 7;
    }
    mb_worker_free(response);
    if (!mb_worker_handle_release(&second, request, 33U,
            &response, &len) || len != 10U || second.count != 0U) {
        mb_worker_free(response);
        return 8;
    }
    mb_worker_free(response);
    mb_native_process_write_u64(&request[9], 64U);
    mb_native_process_write_u64(&request[17], 131072U);
    request[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    if (!mb_worker_handle_allocate(&first, request, 26U,
            &response, &len) || len != 35U
        || mb_native_process_read_u64(&response[10]) != 2U) {
        mb_worker_free(response);
        return 9;
    }
    mb_worker_free(response);
    mb_worker_release_all(&first);
    mb_worker_release_all(&second);
    return first.count == 0U && second.count == 0U ? 0 : 10;
}

static int check_mapping_id_exhaustion(struct mb_worker_state *worker)
{
    mb_u8 request[48] = {0};
    mb_u8 *response = NULL;
    size_t response_len = 0U;
    const size_t reservations_before = reservation_count;
    const size_t releases_before = release_count;
    const mb_u64 last_id = (mb_u64)-1;
    worker->next_id = last_id;
    memcpy(request, MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
    mb_native_process_write_u64(&request[9], 64U);
    mb_native_process_write_u64(&request[17], 131072U);
    request[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    if (!mb_worker_handle_allocate(
            worker, request, 26U, &response, &response_len)
        || response_len != 35U
        || mb_native_process_read_u64(&response[10]) != last_id
        || worker->next_id != 0U || worker->count != 1U) {
        mb_worker_free(response);
        return 1;
    }
    const mb_u64 address = mb_native_process_read_u64(&response[18]);
    mb_worker_free(response);
    if (!mb_worker_handle_allocate(
            worker, request, 26U, &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_FAILURE_RESPONSE_BYTES
        || mb_native_process_read_u32(&response[10])
            != MB_WORKER_ALLOCATION_FAILURE
        || worker->count != 1U || worker->next_id != 0U
        || reservation_count != reservations_before + 1U
        || release_count != releases_before) {
        mb_worker_free(response);
        return 2;
    }
    mb_worker_free(response);
    mb_native_process_write_u64(&request[9], last_id);
    mb_native_process_write_u64(&request[17], address);
    mb_native_process_write_u64(&request[25], 64U);
    request[33] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    mb_native_process_write_u64(&request[34], 6U);
    memcpy(&request[42], "ABCDEF", 6U);
    if (!mb_worker_handle_copy(
            worker, request, 48U, &response, &response_len)
        || response_len != 32U
        || memcmp(&response[26], "ABCDEF", 6U) != 0) {
        mb_worker_free(response);
        return 3;
    }
    mb_worker_free(response);
    if (!mb_worker_handle_release(
            worker, request, 33U, &response, &response_len)
        || response_len != 10U || worker->count != 0U
        || release_count != releases_before + 1U) {
        mb_worker_free(response);
        return 4;
    }
    mb_worker_free(response);
    mb_native_process_write_u64(&request[9], 64U);
    mb_native_process_write_u64(&request[17], 131072U);
    request[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    if (!mb_worker_handle_allocate(
            worker, request, 26U, &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_FAILURE_RESPONSE_BYTES
        || mb_native_process_read_u32(&response[10])
            != MB_WORKER_ALLOCATION_FAILURE
        || worker->next_id != 0U || worker->count != 0U
        || reservation_count != reservations_before + 1U
        || release_count != releases_before + 1U) {
        mb_worker_free(response);
        return 5;
    }
    mb_worker_free(response);
    return 0;
}

static int check_multi_frame_allocation_results(
    const mb_u8 *output, size_t output_len)
{
    if (output_len != 215U) {
        return 1;
    }
    for (size_t index = 0U; index < 5U; ++index) {
        const size_t offset = index * 43U;
        if (mb_native_process_read_u64(&output[offset]) != 35U
            || memcmp(&output[offset + 8U],
                MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U) != 0
            || output[offset + 16U] != MB_NATIVE_PROCESS_MEMORY_ALLOCATE
            || output[offset + 17U] != MB_NATIVE_PROCESS_MEMORY_SUCCESS
            || mb_native_process_read_u64(&output[offset + 18U])
                != (mb_u64)(index + 1U)) {
            return 2;
        }
    }
    return 0;
}

static int check_framed_memory_lifecycle_results(
    const mb_u8 *output, size_t output_len)
{
    const mb_u64 lengths[5] = {35U, 32U, 35U, 34U, 10U};
    const mb_u8 commands[5] = {
        MB_NATIVE_PROCESS_MEMORY_ALLOCATE,
        MB_NATIVE_PROCESS_MEMORY_COPY,
        MB_NATIVE_PROCESS_MEMORY_PROTECT,
        MB_NATIVE_PROCESS_MEMORY_SYNCHRONIZE,
        MB_NATIVE_PROCESS_MEMORY_RELEASE,
    };
    size_t cursor = 0U;
    for (size_t index = 0U; index < 5U; ++index) {
        if (mb_native_process_read_u64(&output[cursor]) != lengths[index]
            || memcmp(&output[cursor + 8U],
                MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U) != 0
            || output[cursor + 16U] != commands[index]
            || output[cursor + 17U] != MB_NATIVE_PROCESS_MEMORY_SUCCESS) {
            return 1;
        }
        cursor += (size_t)lengths[index] + 8U;
    }
    return cursor == output_len && output_len == 186U
        && memcmp(&output[77], "ABCDEF", 6U) == 0 ? 0 : 2;
}

static int check_process_loop_cleanup(int scenario)
{
    mb_u8 wire[240] = {0};
    mb_native_process_write_u64(wire, 26U);
    memcpy(&wire[8], MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
    mb_native_process_write_u64(&wire[17], 64U);
    mb_native_process_write_u64(&wire[25], 131072U);
    wire[33] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    size_t wire_len = 34U;
    if (scenario == 1) {
        mb_native_process_write_u64(&wire[34], 8U);
        memcpy(&wire[42], "wrongtag", 8U);
        wire_len = 50U;
    } else if (scenario == 2) {
        mb_native_process_write_u32(&wire[34], 8U);
        wire_len = 38U;
    } else if (scenario == 4) {
        // The second framed request has call magic but a short body.
        mb_native_process_write_u64(&wire[34], 16U);
        memcpy(&wire[42], MB_NATIVE_PROCESS_CALL_MAGIC, 8U);
        wire_len = 58U;
    } else if (scenario == 5 || scenario == 6) {
        // The call cannot enter mapping ID zero, even with full framing.
        mb_native_process_write_u64(&wire[34], 77U);
        memcpy(&wire[42], MB_NATIVE_PROCESS_CALL_MAGIC, 8U);
        wire_len = 119U;
    }
    if (scenario == 8 || scenario == 9
        || scenario == 11 || scenario == 12 || scenario == 13
        || scenario == 14 || scenario == 15) {
        for (size_t index = 1U; index < 5U; ++index) {
            mb_native_process_write_u64(&wire[wire_len], 26U);
            memcpy(&wire[wire_len + 8U], &wire[8], 26U);
            wire_len += 34U;
        }
        if (scenario == 9) {
            mb_native_process_write_u64(&wire[wire_len], 5U);
            memcpy(&wire[wire_len + 8U], MB_NATIVE_PROCESS_CALL_MAGIC, 5U);
            wire_len += 13U;
        } else if (scenario == 11) {
            // A complete length header but a truncated sixth request body.
            mb_native_process_write_u64(&wire[wire_len], 26U);
            memcpy(&wire[wire_len + 8U], MB_NATIVE_PROCESS_MEMORY_MAGIC, 4U);
            wire_len += 12U;
        } else if (scenario == 12 || scenario == 13
            || scenario == 14) {
            mb_native_process_write_u64(&wire[wire_len], 26U);
            memcpy(&wire[wire_len + 8U], &wire[8], 26U);
            wire_len += 34U;
        }
    }
    if (scenario == 15) {
        // Unreservable complete sixth header after five published mappings.
        mb_native_process_write_u64(&wire[wire_len], (mb_u64)-1);
        wire_len += 8U;
    }
    if (scenario == 10) {
        mb_native_process_write_u64(&wire[34], 48U);
        memcpy(&wire[42], MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
        wire[50] = MB_NATIVE_PROCESS_MEMORY_COPY;
        mb_native_process_write_u64(&wire[67], 64U);
        wire[75] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
        mb_native_process_write_u64(&wire[76], 6U);
        memcpy(&wire[84], "ABCDEF", 6U);
        mb_native_process_write_u64(&wire[90], 34U);
        memcpy(&wire[98], MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
        wire[106] = MB_NATIVE_PROCESS_MEMORY_PROTECT;
        mb_native_process_write_u64(&wire[123], 64U);
        wire[131] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
        mb_native_process_write_u64(&wire[132], 33U);
        memcpy(&wire[140], MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
        wire[148] = MB_NATIVE_PROCESS_MEMORY_SYNCHRONIZE;
        mb_native_process_write_u64(&wire[165], 64U);
        mb_native_process_write_u64(&wire[173], 33U);
        memcpy(&wire[181], MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
        wire[189] = MB_NATIVE_PROCESS_MEMORY_RELEASE;
        mb_native_process_write_u64(&wire[206], 64U);
        wire_len = 214U;
    }
    mb_mock_read_reset(wire, wire_len);
    mock_dynamic_wire = scenario == 10 ? wire : NULL;
    mock_write_pos = 0U;
    mock_write_chunk = 2U;
    mock_fail_write = 0;
    mock_write_overreport = 0;
    mock_fail_write_after = scenario == 3 ? 10U
        : scenario == 13 ? 225U : (size_t)-1;
    if (scenario == 12) {
        // A broken pipe after the first two bytes of the sixth length.
        mock_fail_read = 1;
        mock_fail_read_after = 172U;
        mock_read_error = 109U;
    }
    frame_body_allocations = 0U;
    fail_frame_body_allocation_number = scenario == 14 ? 6U : 0U;
    fail_next_invalid_call_response = scenario == 6 ? 1 : 0;
    fail_next_mapping_response = scenario == 7 ? 1 : 0;
    const size_t reservations_before = reservation_count;
    const size_t releases_before = release_count;
    const size_t protects_before = protect_count;
    const size_t syncs_before = sync_count;
    const int exit_code = mb_test_windows_worker_entry();
    const int expected_exit = scenario == 0 || scenario == 5
        || scenario == 8 || scenario == 10 ? 0
        : scenario == 2 || scenario == 11 || scenario == 12
            || scenario == 14 || scenario == 15 ? 2 : 3;
    const size_t expected_output = scenario == 7 ? 0U
        : scenario == 3 ? 10U : scenario == 5 ? 125U
        : scenario == 8 || scenario == 9 || scenario == 11
            || scenario == 12 || scenario == 14
            || scenario == 15 ? 215U
        : scenario == 13 ? 225U
        : scenario == 10 ? 186U : 43U;
    const size_t expected_reservations =
        scenario == 8 || scenario == 9 || scenario == 11
        || scenario == 12 || scenario == 14
        || scenario == 15 ? 5U
        : scenario == 13 ? 6U : 1U;
    const int valid = exit_code == expected_exit
        && mock_write_pos == expected_output
        && (scenario == 7
            || mb_native_process_read_u64(mock_write_buffer) == 35U)
        && reservation_count == reservations_before + expected_reservations
        && release_count == releases_before + expected_reservations
        && protect_count == protects_before + (scenario == 10 ? 1U : 0U)
        && sync_count == syncs_before + (scenario == 10 ? 1U : 0U)
        && fail_next_invalid_call_response == 0
        && fail_next_mapping_response == 0
        && (scenario != 5
            || (mb_native_process_read_u64(&mock_write_buffer[43]) == 74U
                && mb_native_process_read_u32(
                    &mock_write_buffer[
                        51U + MB_NATIVE_PROCESS_CALL_RESPONSE_STATUS_OFFSET])
                    == MB_NATIVE_INVALID_ARGUMENT));
    const int multi_valid = (scenario != 8 && scenario != 9
        && scenario != 11 && scenario != 12 && scenario != 13
        && scenario != 14 && scenario != 15)
        || check_multi_frame_allocation_results(
            mock_write_buffer, 215U) == 0;
    const int lifecycle_valid = scenario != 10
        || check_framed_memory_lifecycle_results(
            mock_write_buffer, mock_write_pos) == 0;
    mock_dynamic_wire = NULL;
    mock_fail_write_after = (size_t)-1;
    fail_frame_body_allocation_number = 0U;
    const int huge_valid = scenario != 15
        || rejected_huge_frame_allocations == 1U;
    return valid && multi_valid && lifecycle_valid && huge_valid ? 0 : 1;
}

static int check_overaligned_cross_page_code_copy(
    struct mb_worker_state *worker)
{
    enum { CODE_BYTES = 8198 };
    mb_u8 request[42U + CODE_BYTES] = {0};
    mb_u8 *response = NULL;
    size_t response_len = 0U;
    const size_t syncs_before = sync_count;
    const size_t releases_before = release_count;
    memcpy(request, MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
    mb_native_process_write_u64(&request[9], CODE_BYTES);
    mb_native_process_write_u64(&request[17], 131072U);
    request[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    if (!mb_worker_handle_allocate(worker, request, 26U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_MAPPING_RESPONSE_BYTES) {
        mb_worker_free(response);
        return 1;
    }
    const mb_u64 id = mb_native_process_read_u64(&response[10]);
    const mb_u64 base = mb_native_process_read_u64(&response[18]);
    mb_worker_free(response);
    if ((base & 131071U) != 0U || worker->count != 1U) {
        return 2;
    }
    mb_native_process_write_u64(&request[9], id);
    mb_native_process_write_u64(&request[17], base);
    mb_native_process_write_u64(&request[25], CODE_BYTES);
    request[33] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    mb_native_process_write_u64(&request[34], CODE_BYTES);
    for (size_t index = 0U; index < CODE_BYTES; ++index) {
        request[42U + index] = (mb_u8)(index & 0xffU);
    }
    if (!mb_worker_handle_copy(worker, request, sizeof(request),
            &response, &response_len)
        || response_len != 26U + CODE_BYTES
        || memcmp(&response[26], &request[42], CODE_BYTES) != 0) {
        mb_worker_free(response);
        return 3;
    }
    mb_worker_free(response);
    if (!mb_worker_handle_protect(worker, request, 34U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_MAPPING_RESPONSE_BYTES) {
        mb_worker_free(response);
        return 4;
    }
    mb_worker_free(response);
    if (!mb_worker_handle_sync(worker, request, 33U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_SYNC_RESPONSE_BYTES
        || sync_count != syncs_before + 1U
        || last_sync_address != worker->mappings[0].base
        || last_sync_len != CODE_BYTES) {
        mb_worker_free(response);
        return 5;
    }
    mb_worker_free(response);
    if (!mb_worker_handle_release(worker, request, 33U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_RELEASE_RESPONSE_BYTES
        || release_count != releases_before + 1U
        || worker->count != 0U) {
        mb_worker_free(response);
        return 6;
    }
    mb_worker_free(response);
    return 0;
}

static int check_virtual_alloc_failure_is_retryable(
    struct mb_worker_state *worker)
{
    mb_u8 request[33] = {0};
    mb_u8 *response = NULL;
    size_t response_len = 0U;
    const size_t reservations_before = reservation_count;
    const size_t releases_before = release_count;
    const mb_u64 id_before = worker->next_id;
    memcpy(request, MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
    mb_native_process_write_u64(&request[9], 64U);
    mb_native_process_write_u64(&request[17], 131072U);
    request[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    mock_read_error = 5UL;
    fail_next_virtual_alloc = 1;
    if (!mb_worker_handle_allocate(worker, request, 26U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_FAILURE_RESPONSE_BYTES
        || mb_native_process_read_u32(&response[10]) != 5U
        || fail_next_virtual_alloc != 0
        || worker->count != 0U || worker->next_id != id_before
        || reservation_count != reservations_before
        || release_count != releases_before) {
        mb_worker_free(response);
        return 1;
    }
    mb_worker_free(response);
    // Windows DWORD errors are unsigned; preserve their high-bit payload.
    mock_read_error = 0x80000001U;
    fail_next_virtual_alloc = 1;
    if (!mb_worker_handle_allocate(worker, request, 26U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_FAILURE_RESPONSE_BYTES
        || mb_native_process_read_u32(&response[10]) != 0x80000001U
        || fail_next_virtual_alloc != 0
        || worker->count != 0U || worker->next_id != id_before
        || reservation_count != reservations_before
        || release_count != releases_before) {
        mb_worker_free(response);
        return 5;
    }
    mb_worker_free(response);
    // Even missing GetLastError evidence must return a nonzero failure tag.
    mock_read_error = 0UL;
    fail_next_virtual_alloc = 1;
    if (!mb_worker_handle_allocate(worker, request, 26U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_FAILURE_RESPONSE_BYTES
        || mb_native_process_read_u32(&response[10])
            != MB_WORKER_PLATFORM_FAILURE
        || worker->count != 0U || worker->next_id != id_before
        || reservation_count != reservations_before
        || release_count != releases_before) {
        mb_worker_free(response);
        return 4;
    }
    mb_worker_free(response);
    mock_read_error = 5UL;
    if (!mb_worker_handle_allocate(worker, request, 26U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_MAPPING_RESPONSE_BYTES
        || mb_native_process_read_u64(&response[10]) != id_before
        || worker->next_id != id_before + 1U
        || worker->count != 1U) {
        mb_worker_free(response);
        return 2;
    }
    const mb_u64 id = mb_native_process_read_u64(&response[10]);
    const mb_u64 address = mb_native_process_read_u64(&response[18]);
    mb_worker_free(response);
    mb_native_process_write_u64(&request[9], id);
    mb_native_process_write_u64(&request[17], address);
    mb_native_process_write_u64(&request[25], 64U);
    if (!mb_worker_handle_release(worker, request, 33U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_RELEASE_RESPONSE_BYTES
        || worker->count != 0U || reservation_count != reservations_before + 1U
        || release_count != releases_before + 1U) {
        mb_worker_free(response);
        return 3;
    }
    mb_worker_free(response);
    return 0;
}

static int check_rejected_rx_sync_ranges(struct mb_worker_state *worker)
{
    mb_u8 request[42] = {0};
    mb_u8 *response = NULL;
    size_t response_len = 0U;
    memcpy(request, MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
    mb_native_process_write_u64(&request[9], 64U);
    mb_native_process_write_u64(&request[17], 131072U);
    request[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    if (!mb_worker_handle_allocate(worker, request, 26U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_MAPPING_RESPONSE_BYTES) {
        mb_worker_free(response);
        return 1;
    }
    const mb_u64 id = mb_native_process_read_u64(&response[10]);
    const mb_u64 base = mb_native_process_read_u64(&response[18]);
    mb_worker_free(response);
    mb_native_process_write_u64(&request[9], id);
    mb_native_process_write_u64(&request[17], base);
    mb_native_process_write_u64(&request[25], 64U);
    request[33] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    if (!mb_worker_handle_protect(worker, request, 34U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_MAPPING_RESPONSE_BYTES) {
        mb_worker_free(response);
        return 2;
    }
    mb_worker_free(response);
    const size_t syncs_before = sync_count;
    const size_t releases_before = release_count;
    for (size_t case_index = 0U; case_index < 9U; ++case_index) {
        mb_u8 forged[34];
        memcpy(forged, request, sizeof(forged));
        size_t length = 33U;
        switch (case_index) {
        case 0U:
            mb_native_process_write_u64(&forged[9], id + 1U);
            break;
        case 1U:
            mb_native_process_write_u64(&forged[17], base + 1U);
            break;
        case 2U:
            mb_native_process_write_u64(&forged[17], base - 1U);
            break;
        case 3U:
            mb_native_process_write_u64(&forged[25], 63U);
            break;
        case 4U:
            mb_native_process_write_u64(&forged[25], 65U);
            break;
        case 5U:
            mb_native_process_write_u64(&forged[25], 0U);
            break;
        case 6U:
            mb_native_process_write_u64(&forged[25], (mb_u64)-1);
            break;
        case 7U:
            length = 32U;
            break;
        default:
            length = 34U;
            break;
        }
        forged[MB_NATIVE_PROCESS_COMMAND_OFFSET]
            = MB_NATIVE_PROCESS_MEMORY_SYNCHRONIZE;
        if (!mb_worker_handle_memory(worker, forged, length,
                &response, &response_len)
            || response_len != MB_NATIVE_PROCESS_MEMORY_FAILURE_RESPONSE_BYTES
            || response == NULL
            || response[MB_NATIVE_PROCESS_OUTCOME_OFFSET]
                != MB_NATIVE_PROCESS_MEMORY_FAILURE
            || worker->count != 1U
            || worker->mappings[0].id != id
            || worker->mappings[0].permission
                != MB_NATIVE_PROCESS_MEMORY_READ_EXECUTE
            || sync_count != syncs_before
            || release_count != releases_before) {
            mb_worker_free(response);
            return (int)(case_index + 3U);
        }
        mb_worker_free(response);
    }
    // A sealed RX mapping may no longer be copied or protected again.
    const size_t protects_before = protect_count;
    request[MB_NATIVE_PROCESS_COMMAND_OFFSET]
        = MB_NATIVE_PROCESS_MEMORY_PROTECT;
    if (check_invalid_memory_command(worker, request, 34U,
            MB_WORKER_INVALID_REQUEST) != 0
        || protect_count != protects_before) {
        return 15;
    }
    request[MB_NATIVE_PROCESS_COMMAND_OFFSET]
        = MB_NATIVE_PROCESS_MEMORY_COPY;
    mb_native_process_write_u64(&request[34], 0U);
    if (check_invalid_memory_command(worker, request, 42U,
            MB_WORKER_MAPPING_NOT_FOUND) != 0
        || protect_count != protects_before
        || worker->mappings[0].permission
            != MB_NATIVE_PROCESS_MEMORY_READ_EXECUTE) {
        return 16;
    }
    request[MB_NATIVE_PROCESS_COMMAND_OFFSET]
        = MB_NATIVE_PROCESS_MEMORY_SYNCHRONIZE;
    if (!mb_worker_handle_memory(worker, request, 33U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_SYNC_RESPONSE_BYTES
        || sync_count != syncs_before + 1U) {
        mb_worker_free(response);
        return 13;
    }
    mb_worker_free(response);
    request[MB_NATIVE_PROCESS_COMMAND_OFFSET]
        = MB_NATIVE_PROCESS_MEMORY_RELEASE;
    if (!mb_worker_handle_memory(worker, request, 33U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_RELEASE_RESPONSE_BYTES
        || worker->count != 0U || release_count != releases_before + 1U) {
        mb_worker_free(response);
        return 14;
    }
    mb_worker_free(response);
    return 0;
}

static int check_mixed_geometry_survivors(
    struct mb_worker_state *worker,
    const mb_u64 ids[8],
    const mb_u64 bases[8],
    const size_t sizes[8],
    const int released[8])
{
    size_t live = 0U;
    for (size_t i = 0U; i < 8U; ++i) {
        const struct mb_worker_mapping *mapping =
            mb_worker_find_mapping(worker, ids[i]);
        if (released[i] != 0) {
            if (mapping != NULL) {
                return 1;
            }
            continue;
        }
        if (mapping == NULL
            || (mb_u64)(mb_uintptr)mapping->base != bases[i]
            || mapping->len != sizes[i]
            || mapping->permission != MB_NATIVE_PROCESS_MEMORY_READ_EXECUTE) {
            return 2;
        }
        live += 1U;
    }
    return worker->count == live ? 0 : 3;
}

static int check_mixed_geometry_forgery(
    struct mb_worker_state *worker,
    const mb_u64 ids[8],
    const mb_u64 bases[8],
    const size_t sizes[8])
{
    mb_u8 request[33] = {0};
    mb_u8 *response = NULL;
    size_t len = 0U;
    const size_t release_before = release_count;
    const size_t sync_before = sync_count;
    memcpy(request, MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
    for (size_t index = 0U; index < 8U; ++index) {
        const size_t other = (index + 1U) % 8U;
        for (size_t geometry = 0U; geometry < 3U; ++geometry) {
            const mb_u64 base = geometry == 1U
                ? bases[index] : bases[other];
            const mb_u64 size = geometry == 0U
                ? (mb_u64)sizes[index] : (mb_u64)sizes[other];
            mb_native_process_write_u64(&request[9], ids[index]);
            mb_native_process_write_u64(&request[17], base);
            mb_native_process_write_u64(&request[25], size);
            for (size_t command = 0U; command < 2U; ++command) {
                const int synced = command == 0U;
                request[8] = synced != 0
                    ? MB_NATIVE_PROCESS_MEMORY_SYNCHRONIZE
                    : MB_NATIVE_PROCESS_MEMORY_RELEASE;
                const int handled = synced != 0
                    ? mb_worker_handle_sync(
                        worker, request, sizeof(request), &response, &len)
                    : mb_worker_handle_release(
                        worker, request, sizeof(request), &response, &len);
                if (!handled || response == NULL
                    || len != MB_NATIVE_PROCESS_MEMORY_FAILURE_RESPONSE_BYTES
                    || response[9] != MB_NATIVE_PROCESS_MEMORY_FAILURE
                    || worker->count != 8U
                    || release_count != release_before
                    || sync_count != sync_before) {
                    mb_worker_free(response);
                    return 1;
                }
                mb_worker_free(response);
                response = NULL;
            }
        }
    }
    return 0;
}

static int check_mixed_geometry_stale_id(
    struct mb_worker_state *worker,
    mb_u64 stale_id,
    mb_u64 stale_base,
    size_t stale_size,
    const mb_u64 bases[8],
    const size_t sizes[8],
    const int released[8])
{
    mb_u8 request[33] = {0};
    mb_u8 *response = NULL;
    size_t len = 0U;
    const size_t count_before = worker->count;
    const size_t sync_before = sync_count;
    const size_t release_before = release_count;
    memcpy(request, MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
    mb_native_process_write_u64(&request[9], stale_id);
    for (size_t shape = 0U; shape <= 8U; ++shape) {
        if (shape < 8U && released[shape] != 0) {
            continue;
        }
        const mb_u64 base = shape == 8U ? stale_base : bases[shape];
        const mb_u64 size = shape == 8U
            ? (mb_u64)stale_size : (mb_u64)sizes[shape];
        mb_native_process_write_u64(&request[17], base);
        mb_native_process_write_u64(&request[25], size);
        for (size_t command = 0U; command < 2U; ++command) {
            const int sync = command == 0U;
            request[8] = sync != 0
                ? MB_NATIVE_PROCESS_MEMORY_SYNCHRONIZE
                : MB_NATIVE_PROCESS_MEMORY_RELEASE;
            const int handled = sync != 0
                ? mb_worker_handle_sync(
                    worker, request, sizeof(request), &response, &len)
                : mb_worker_handle_release(
                    worker, request, sizeof(request), &response, &len);
            if (!handled || response == NULL
                || len != MB_NATIVE_PROCESS_MEMORY_FAILURE_RESPONSE_BYTES
                || response[9] != MB_NATIVE_PROCESS_MEMORY_FAILURE
                || worker->count != count_before
                || release_count != release_before
                || sync_count != sync_before) {
                mb_worker_free(response);
                return 1;
            }
            mb_worker_free(response);
            response = NULL;
        }
    }
    return 0;
}

static int check_mixed_geometry_table(struct mb_worker_state *worker)
{
    const size_t sizes[8] = {
        64U, 256U, 4096U, 8198U, 127U, 1024U, 2048U, 16384U,
    };
    const size_t alignments[8] = {
        1U, 16U, 4096U, 65536U, 131072U, 262144U, 32U, 8192U,
    };
    const size_t order[8] = {2U, 7U, 0U, 5U, 3U, 1U, 6U, 4U};
    mb_u64 ids[8] = {0};
    mb_u64 bases[8] = {0};
    int released[8] = {0};
    mb_u8 request[48] = {0};
    mb_u8 *response = NULL;
    size_t len = 0U;
    const size_t original_releases = release_count;
    const size_t original_syncs = sync_count;
    const size_t original_protects = protect_count;
    memcpy(request, MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
    for (size_t i = 0U; i < 8U; ++i) {
        request[8] = MB_NATIVE_PROCESS_MEMORY_ALLOCATE;
        mb_native_process_write_u64(&request[9], (mb_u64)sizes[i]);
        mb_native_process_write_u64(&request[17], (mb_u64)alignments[i]);
        request[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
        if (!mb_worker_handle_allocate(worker, request, 26U,
                &response, &len)
            || len != MB_NATIVE_PROCESS_MEMORY_MAPPING_RESPONSE_BYTES) {
            mb_worker_free(response);
            return 1;
        }
        ids[i] = mb_native_process_read_u64(&response[10]);
        bases[i] = mb_native_process_read_u64(&response[18]);
        mb_worker_free(response);
        if (ids[i] == 0U
            || (bases[i] & (mb_u64)(alignments[i] - 1U)) != 0U) {
            return 2;
        }
        request[8] = MB_NATIVE_PROCESS_MEMORY_COPY;
        mb_native_process_write_u64(&request[9], ids[i]);
        mb_native_process_write_u64(&request[17], bases[i]);
        mb_native_process_write_u64(&request[25], (mb_u64)sizes[i]);
        request[33] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
        mb_native_process_write_u64(&request[34], 6U);
        memset(&request[42], (int)('A' + (int)i), 6U);
        if (!mb_worker_handle_copy(worker, request, 48U, &response, &len)
            || len != 32U || memcmp(&response[26], &request[42], 6U) != 0) {
            mb_worker_free(response);
            return 3;
        }
        mb_worker_free(response);
        request[8] = MB_NATIVE_PROCESS_MEMORY_PROTECT;
        if (!mb_worker_handle_protect(worker, request, 34U,
                &response, &len) || len != 35U) {
            mb_worker_free(response);
            return 4;
        }
        mb_worker_free(response);
        request[8] = MB_NATIVE_PROCESS_MEMORY_SYNCHRONIZE;
        if (!mb_worker_handle_sync(worker, request, 33U,
                &response, &len) || len != 34U) {
            mb_worker_free(response);
            return 5;
        }
        mb_worker_free(response);
    }
    if (check_mixed_geometry_survivors(
            worker, ids, bases, sizes, released) != 0) {
        return 6;
    }
    if (check_mixed_geometry_forgery(worker, ids, bases, sizes) != 0) {
        return 11;
    }
    for (size_t index = 0U; index < 8U; ++index) {
        const size_t i = order[index];
        request[8] = MB_NATIVE_PROCESS_MEMORY_RELEASE;
        mb_native_process_write_u64(&request[9], ids[i]);
        mb_native_process_write_u64(&request[17], bases[i]);
        mb_native_process_write_u64(&request[25], (mb_u64)sizes[i]);
        if (!mb_worker_handle_release(worker, request, 33U,
                &response, &len) || len != 10U) {
            mb_worker_free(response);
            return 7;
        }
        mb_worker_free(response);
        released[i] = 1;
        if (check_mixed_geometry_survivors(
                worker, ids, bases, sizes, released) != 0) {
            return 8;
        }
        if (check_mixed_geometry_stale_id(
                worker, ids[i], bases[i], sizes[i],
                bases, sizes, released) != 0) {
            return 12;
        }
        for (size_t live = 0U; live < 8U; ++live) {
            if (released[live] != 0) {
                continue;
            }
            request[8] = MB_NATIVE_PROCESS_MEMORY_SYNCHRONIZE;
            mb_native_process_write_u64(&request[9], ids[live]);
            mb_native_process_write_u64(&request[17], bases[live]);
            mb_native_process_write_u64(&request[25],
                (mb_u64)sizes[live]);
            if (!mb_worker_handle_sync(worker, request, 33U,
                    &response, &len) || len != 34U
                || mb_native_process_read_u64(&response[10]) != ids[live]
                || mb_native_process_read_u64(&response[18]) != bases[live]
                || mb_native_process_read_u64(&response[26])
                    != (mb_u64)sizes[live]
                || (mb_u64)(mb_uintptr)last_sync_address != bases[live]
                || last_sync_len != sizes[live]) {
                mb_worker_free(response);
                return 10;
            }
            mb_worker_free(response);
        }
    }
    return worker->count == 0U && release_count == original_releases + 8U
        && sync_count == original_syncs + 36U
        && protect_count == original_protects + 8U ? 0 : 9;
}

static int check_first_mapping_heap_failure(void)
{
    struct mb_worker_state worker = {.next_id = 1U};
    mb_u8 request[26] = {0};
    mb_u8 *response = NULL;
    size_t len = 0U;
    const size_t allocations_before = reservation_count;
    const size_t releases_before = release_count;
    memcpy(request, MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
    mb_native_process_write_u64(&request[9], 64U);
    mb_native_process_write_u64(&request[17], 131072U);
    request[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    fail_first_mapping_heap_alloc = 1;
    if (!mb_worker_handle_allocate(&worker, request, 26U,
            &response, &len)
        || len != MB_NATIVE_PROCESS_MEMORY_FAILURE_RESPONSE_BYTES
        || response == NULL
        || mb_native_process_read_u32(&response[10])
            != MB_WORKER_ALLOCATION_FAILURE
        || worker.count != 0U || worker.capacity != 0U
        || worker.next_id != 1U
        || reservation_count != allocations_before + 1U
        || release_count != releases_before + 1U) {
        mb_worker_free(response);
        mb_worker_release_all(&worker);
        return 1;
    }
    mb_worker_free(response);
    response = NULL;
    if (!mb_worker_handle_allocate(&worker, request, 26U,
            &response, &len)
        || len != MB_NATIVE_PROCESS_MEMORY_MAPPING_RESPONSE_BYTES
        || response == NULL
        || mb_native_process_read_u64(&response[10]) != 1U
        || worker.count != 1U || worker.next_id != 2U) {
        mb_worker_free(response);
        mb_worker_release_all(&worker);
        return 2;
    }
    mb_worker_free(response);
    mb_worker_release_all(&worker);
    return worker.count == 0U
        && reservation_count == allocations_before + 2U
        && release_count == releases_before + 2U ? 0 : 3;
}

int main(void)
{
#if defined(__aarch64__)
    if (mb_native_entry_offset_aligned(0U) == 0
        || mb_native_entry_offset_aligned(4U) == 0
        || mb_native_entry_offset_aligned(1U) != 0
        || mb_native_entry_offset_aligned(3U) != 0) {
        return 35;
    }
#else
    if (mb_native_entry_offset_aligned(1U) == 0
        || mb_native_entry_offset_aligned(3U) == 0) {
        return 35;
    }
#endif
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
        || protect_count != 9U || native_entry_invocations != 4U) {
        return 15;
    }
    const int frame_result = check_frame_io();
    if (frame_result != 0) {
        return 16 + frame_result;
    }
    if (check_win32_dword_transfer_chunks() != 0) {
        return 36;
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
    const int side_effects = check_unreportable_copy_sync_release(&worker);
    if (side_effects != 0) {
        return 80 + side_effects;
    }
    const int memory_failures = check_malformed_memory_commands(&worker);
    if (memory_failures != 0) {
        return 40 + memory_failures;
    }
    const int independent = check_independent_worker_mapping_ids();
    if (independent != 0) {
        return 75 + independent;
    }
    const int empty_copy = check_empty_and_full_code_copies(&worker);
    if (empty_copy != 0) {
        return 135 + empty_copy;
    }
    const int live_dispatch = check_two_live_native_mappings(&worker);
    if (live_dispatch != 0) {
        return 150 + live_dispatch;
    }
    const int mixed = check_mixed_live_mapping_ids(&worker);
    if (mixed != 0) {
        return 120 + mixed;
    }
    const int stale = check_stale_id_with_recycled_base(&worker);
    if (stale != 0) {
        return 57 + stale;
    }
    const int cross_page = check_overaligned_cross_page_code_copy(&worker);
    if (cross_page != 0) {
        return 110 + cross_page;
    }
    const int alloc_failure = check_virtual_alloc_failure_is_retryable(&worker);
    if (alloc_failure != 0) {
        return 100 + alloc_failure;
    }
    const int rejected_sync = check_rejected_rx_sync_ranges(&worker);
    if (rejected_sync != 0) {
        return 90 + rejected_sync;
    }
    const int mixed_geometry = check_mixed_geometry_table(&worker);
    if (mixed_geometry != 0) {
        return 175 + mixed_geometry;
    }
    const int exhausted = check_mapping_id_exhaustion(&worker);
    if (exhausted != 0) {
        return 60 + exhausted;
    }
    for (int scenario = 0; scenario < 16; ++scenario) {
        if (check_process_loop_cleanup(scenario) != 0) {
            return 70 + scenario;
        }
    }
    mb_worker_release_all(&worker);
    const int first_table = check_first_mapping_heap_failure();
    if (first_table != 0) {
        return 37 + first_table;
    }
    return 0;
}
