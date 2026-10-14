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
static int fail_next_protect;
static int fail_next_release;
static int fail_next_sync;
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
    worker->mappings[0].base = (mb_u8 *)(mb_uintptr)address;
    mb_native_process_write_u64(&allocation[9], id);
    mb_native_process_write_u64(&allocation[17], address);
    mb_native_process_write_u64(&allocation[25], 64U);
    if (!mb_worker_handle_release(worker, allocation, 33U, &response, &len)
        || worker->count != 0U || len != 10U) {
        return 8;
    }
    mb_worker_free(response);
    return native_entry_invocations == 1U ? 0 : 9;
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
    return 0;
}
