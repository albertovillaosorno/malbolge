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
//   - POSIX native call staging allocation failure simulation.
// - Must-Not:
//   - Replace real process isolation or semantic verification.
// - Allows:
//   - Inputs: fixed MBNPC1 call and independent malloc failure injection.
//   - Outputs: zero on exact cleanup, frame, and retained-mapping behavior.
//   - Side effects: private heap allocations freed in this test process.
// - Split-When:
//   - Native POSIX fault injection moves to a shared test harness.
// - Merge-When:
//   - One host-side runtime simulator covers both worker implementations.
// - Summary:
//   - Simulates both guest call-buffer allocation failure paths.
// - Description:
//   - Links the real POSIX handler with controlled staging malloc failures.
// - Usage:
//   - Compile and run through pinned Clang and pytest on Linux x86-64.
// - Defaults:
//   - No subprocess isolation; all native entries are controlled C stubs.
//

//! Host fault injection against the real POSIX native-call handler.

#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

static int fail_next_memory;
static int fail_next_output;
static int fail_next_response;
static int fail_next_protect;
static int fail_next_release;
static size_t frees;
static size_t entries;

static void *mb_test_malloc(size_t len);
static void *mb_test_calloc(size_t count, size_t width);
static void mb_test_free(void *ptr);
static int mb_test_mprotect(void *address, size_t len, int permissions);
static int mb_test_munmap(void *address, size_t len);

int mb_test_posix_worker_entry(void);

#define malloc mb_test_malloc
#define calloc mb_test_calloc
#define free mb_test_free
#define mprotect mb_test_mprotect
#define munmap mb_test_munmap
#define main mb_test_posix_worker_entry
#include "native_process_worker_posix.c"
#undef main
#undef malloc
#undef calloc
#undef free
#undef mprotect
#undef munmap

static int mb_test_mprotect(void *address, size_t len, int permissions)
{
    if (fail_next_protect != 0) {
        fail_next_protect = 0;
        errno = EACCES;
        return -1;
    }
    return mprotect(address, len, permissions);
}

static int mb_test_munmap(void *address, size_t len)
{
    if (fail_next_release != 0) {
        fail_next_release = 0;
        errno = EINVAL;
        return -1;
    }
    return munmap(address, len);
}

static void *mb_test_malloc(size_t len)
{
    if (len == 4U && fail_next_memory != 0) {
        fail_next_memory = 0;
        return NULL;
    }
    if (len == 3U && fail_next_output != 0) {
        fail_next_output = 0;
        return NULL;
    }
    return malloc(len);
}

static void *mb_test_calloc(size_t count, size_t width)
{
    if (count == 81U && width == 1U && fail_next_response != 0) {
        fail_next_response = 0;
        return NULL;
    }
    return calloc(count, width);
}

static void mb_test_free(void *ptr)
{
    if (ptr != NULL) {
        frees += 1U;
        free(ptr);
    }
}

static int __attribute__((ms_abi)) mb_test_entry(
    struct mb_native_region_state *state)
{
    entries += 1U;
    state->memory[0] += 2U;
    state->output[1] = state->input[0];
    state->input_consumed = 1U;
    state->output_len = 2U;
    state->accumulator += 1U;
    return MB_NATIVE_APPLIED;
}

static int check_response_allocation_failure(
    struct mb_worker_state *worker, const mb_u8 *request)
{
    const size_t frees_before = frees;
    const size_t entries_before = entries;
    const mb_u8 *const base = worker->mappings[0].base;
    mb_u8 *response = NULL;
    size_t len = 0U;
    fail_next_response = 1;
    if (mb_worker_handle_call(worker, request, 86U, &response, &len)
        || response != NULL || len != 0U
        || frees != frees_before + 2U
        || entries != entries_before + 1U
        || worker->count != 1U || worker->mappings[0].base != base) {
        mb_test_free(response);
        return 1;
    }
    if (!mb_worker_handle_call(worker, request, 86U, &response, &len)
        || response == NULL || len != 81U
        || entries != entries_before + 2U
        || frees != frees_before + 4U
        || response[73] != 1U
        || mb_native_process_read_u32(&response[69]) != MB_NATIVE_APPLIED
        || mb_native_process_read_u32(&response[74]) != 10U
        || response[79] != 0xa5U) {
        mb_test_free(response);
        return 2;
    }
    mb_test_free(response);
    return frees == frees_before + 5U ? 0 : 3;
}

static int check_call_allocations(void)
{
    mb_native_entry_fn entry = mb_test_entry;
    mb_u8 *entry_bytes = NULL;
    static_assert(sizeof(entry) == sizeof(entry_bytes),
        "POSIX host entry pointer representation drifted");
    memcpy(&entry_bytes, &entry, sizeof(entry));
    struct mb_worker_mapping mapping = {
        .id = 1U,
        .base = entry_bytes,
        .len = 64U,
        .reservation = NULL,
        .reservation_len = 0U,
        .permission = MB_NATIVE_PROCESS_MEMORY_READ_EXECUTE,
    };
    struct mb_worker_state worker = {
        .mappings = &mapping,
        .count = 1U,
        .capacity = 1U,
        .next_id = 2U,
    };
    mb_u8 request[86] = {0};
    memcpy(request, MB_NATIVE_PROCESS_CALL_MAGIC, 8U);
    mb_native_process_write_u64(&request[8], mapping.id);
    mb_native_process_write_u64(&request[24], 1U);
    mb_native_process_write_u64(&request[32], 2U);
    mb_native_process_write_u64(&request[40], 3U);
    mb_native_process_write_u64(&request[56], 1U);
    mb_native_process_write_u32(&request[64], 7U);
    mb_native_process_write_u32(&request[77], 8U);
    request[81] = 0xa5U;
    request[82] = 0xb6U;
    request[83] = 0x10U;
    mb_u8 original[sizeof(request)];
    memcpy(original, request, sizeof(original));
    mb_u8 *response = NULL;
    size_t len = 0U;
    fail_next_memory = 1;
    if (mb_worker_handle_call(&worker, request, sizeof(request),
            &response, &len)
        || response != NULL || len != 0U || frees != 1U
        || entries != 0U) {
        mb_test_free(response);
        return 1;
    }
    fail_next_output = 1;
    if (mb_worker_handle_call(&worker, request, sizeof(request),
            &response, &len)
        || response != NULL || len != 0U || frees != 2U
        || entries != 0U) {
        mb_test_free(response);
        return 2;
    }
    if (!mb_worker_handle_call(&worker, request, sizeof(request),
            &response, &len)
        || len != 81U || response == NULL || entries != 1U
        || mb_native_process_read_u32(&response[69]) != MB_NATIVE_APPLIED
        || response[73] != 1U || response[79] != 0xa5U
        || mb_native_process_read_u32(&response[74]) != 10U
        || mb_native_process_read_u32(&response[56]) != 8U
        || mb_native_process_read_u64(&response[40]) != 1U
        || mb_native_process_read_u64(&response[48]) != 2U
        || memcmp(request, original, sizeof(request)) != 0
        || frees != 4U || worker.count != 1U
        || worker.mappings[0].base != entry_bytes) {
        mb_test_free(response);
        return 3;
    }
    mb_test_free(response);
    if (frees != 5U) {
        return 4;
    }
    const int response_failure = check_response_allocation_failure(
        &worker, request);
    if (response_failure != 0 || entries != 3U
        || memcmp(request, original, sizeof(request)) != 0) {
        return 5 + response_failure;
    }
    return 0;
}

static int check_lifecycle_fault_recovery(void)
{
    struct mb_worker_state worker = {.next_id = 1U};
    mb_u8 request[34] = {0};
    mb_u8 *response = NULL;
    size_t response_len = 0U;
    memcpy(request, MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
    mb_native_process_write_u64(&request[9], 64U);
    mb_native_process_write_u64(&request[17], 65536U);
    request[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    if (!mb_worker_handle_allocate(&worker, request, 26U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_MAPPING_RESPONSE_BYTES
        || worker.count != 1U) {
        mb_test_free(response);
        return 1;
    }
    const mb_u64 id = mb_native_process_read_u64(&response[10]);
    const mb_u64 base = mb_native_process_read_u64(&response[18]);
    mb_test_free(response);
    mb_native_process_write_u64(&request[9], id);
    mb_native_process_write_u64(&request[17], base);
    mb_native_process_write_u64(&request[25], 64U);
    request[33] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    fail_next_protect = 1;
    if (!mb_worker_handle_protect(&worker, request, 34U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_FAILURE_RESPONSE_BYTES
        || worker.mappings[0].permission
            != MB_NATIVE_PROCESS_MEMORY_READ_WRITE) {
        mb_test_free(response);
        return 2;
    }
    mb_test_free(response);
    if (!mb_worker_handle_protect(&worker, request, 34U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_MAPPING_RESPONSE_BYTES
        || response[34] != MB_NATIVE_PROCESS_MEMORY_READ_EXECUTE
        || worker.mappings[0].permission
            != MB_NATIVE_PROCESS_MEMORY_READ_EXECUTE) {
        mb_test_free(response);
        return 3;
    }
    mb_test_free(response);
    fail_next_release = 1;
    if (!mb_worker_handle_release(&worker, request, 33U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_FAILURE_RESPONSE_BYTES
        || worker.count != 1U
        || worker.mappings[0].base != (mb_u8 *)(uintptr_t)base) {
        mb_test_free(response);
        return 4;
    }
    mb_test_free(response);
    if (!mb_worker_handle_release(&worker, request, 33U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_RELEASE_RESPONSE_BYTES
        || worker.count != 0U) {
        mb_test_free(response);
        return 5;
    }
    mb_test_free(response);
    mb_worker_release_all(&worker);
    return 0;
}

int main(void)
{
    const int call_result = check_call_allocations();
    if (call_result != 0) {
        return call_result;
    }
    const int lifecycle_result = check_lifecycle_fault_recovery();
    return lifecycle_result == 0 ? 0 : 20 + lifecycle_result;
}
