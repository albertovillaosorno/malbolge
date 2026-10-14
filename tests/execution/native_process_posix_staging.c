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
static size_t frees;
static size_t entries;

static void *mb_test_malloc(size_t len);
static void mb_test_free(void *ptr);

int mb_test_posix_worker_entry(void);

#define malloc mb_test_malloc
#define free mb_test_free
#define main mb_test_posix_worker_entry
#include "native_process_worker_posix.c"
#undef main
#undef malloc
#undef free

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
    return frees == 5U ? 0 : 4;
}

int main(void)
{
    return check_call_allocations();
}
