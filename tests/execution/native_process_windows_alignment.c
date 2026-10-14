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

static struct mb_mock_reservation reservations[16];
static size_t reservation_count;
static size_t protect_count;
static size_t sync_count;
static size_t release_count;
static char mock_handle;

mb_win_handle GetCurrentProcess(void) { return &mock_handle; }
mb_win_dword GetLastError(void) { return 5UL; }
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
    return malloc(len);
}
void *HeapReAlloc(mb_win_handle heap, mb_win_dword flags, void *ptr, size_t len)
{
    (void)heap;
    (void)flags;
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
    (void)buffer;
    (void)len;
    (void)overlapped;
    *read = 0UL;
    return 0;
}
mb_win_bool WriteFile(
    mb_win_handle handle, const void *buffer, mb_win_dword len,
    mb_win_dword *written, void *overlapped)
{
    (void)handle;
    (void)buffer;
    (void)overlapped;
    *written = len;
    return 1;
}
void *VirtualAlloc(
    void *address, size_t len, mb_win_dword flags, mb_win_dword protect)
{
    if (address != NULL || flags != (MB_WIN_MEM_RESERVE | MB_WIN_MEM_COMMIT)
        || protect != MB_WIN_PAGE_READWRITE
        || reservation_count >= 16U || len > 1048576U) {
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
    for (size_t i = 0U; i < reservation_count; ++i) {
        const uintptr_t base = (uintptr_t)reservations[i].base;
        const uintptr_t location = (uintptr_t)address;
        if (!reservations[i].released && location >= base
            && location - base <= reservations[i].len
            && len <= reservations[i].len - (size_t)(location - base)) {
            *old = MB_WIN_PAGE_READWRITE;
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
    return 0;
}
