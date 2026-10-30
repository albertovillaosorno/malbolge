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
//   - Checks POSIX call staging, framing, and worker cleanup failures.
// - Description:
//   - Runs actual POSIX handlers and loop with injected malloc/stdio faults.
// - Usage:
//   - Compile and run through pinned Clang and pytest on Linux x86-64.
// - Defaults:
//   - No subprocess isolation; all native entries are controlled C stubs.
//

//! Host fault injection against native-call and POSIX frame handlers.

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
static size_t frame_payload_allocations;
static size_t oversized_frame_allocations;
static size_t fail_frame_payload_allocation_number;
static int fail_next_response;
static int fail_next_protect;
static int fail_next_release;
static int fail_next_map;
static int fail_next_table_growth;
static size_t fail_next_lifecycle_response;
static size_t mapped_reservations;
static size_t unmapped_reservations;
static size_t frees;
static size_t entries;
static const unsigned char *mock_frame_input;
static size_t mock_frame_input_len;
static size_t mock_frame_input_pos;
static int mock_frame_eof;
static int mock_frame_error;
static unsigned char mock_frame_output[64];
static size_t mock_frame_output_pos;
static int mock_frame_short_write;
static int mock_frame_flush_error;

static void *mb_test_malloc(size_t len);
static void *mb_test_realloc(void *ptr, size_t len);
static void *mb_test_mmap(
    void *address, size_t len, int protection,
    int flags, int descriptor, off_t offset);
static void *mb_test_calloc(size_t count, size_t width);
static void mb_test_free(void *ptr);
static int mb_test_mprotect(void *address, size_t len, int permissions);
static int mb_test_munmap(void *address, size_t len);
static size_t mb_test_fread(
    void *bytes, size_t width, size_t count, FILE *stream);
static size_t mb_test_fwrite(
    const void *bytes, size_t width, size_t count, FILE *stream);
static int mb_test_feof(FILE *stream);
static int mb_test_ferror(FILE *stream);
static int mb_test_fflush(FILE *stream);

int mb_test_posix_worker_entry(void);

#define malloc mb_test_malloc
#define realloc mb_test_realloc
#define mmap mb_test_mmap
#define calloc mb_test_calloc
#define free mb_test_free
#define mprotect mb_test_mprotect
#define munmap mb_test_munmap
#define fread mb_test_fread
#define fwrite mb_test_fwrite
#define feof mb_test_feof
#define ferror mb_test_ferror
#define fflush mb_test_fflush
#define main mb_test_posix_worker_entry
#include "native_process_worker_posix.c"
#undef main
#undef malloc
#undef realloc
#undef mmap
#undef calloc
#undef free
#undef mprotect
#undef munmap
#undef fread
#undef fwrite
#undef feof
#undef ferror
#undef fflush

static size_t mb_test_fread(
    void *bytes, size_t width, size_t count, FILE *stream)
{
    (void)stream;
    if (width != 1U) {
        return 0U;
    }
    const size_t available = mock_frame_input_len - mock_frame_input_pos;
    const size_t length = count < available ? count : available;
    if (length != 0U) {
        memcpy(bytes, &mock_frame_input[mock_frame_input_pos], length);
    }
    mock_frame_input_pos += length;
    return length;
}

static size_t mb_test_fwrite(
    const void *bytes, size_t width, size_t count, FILE *stream)
{
    (void)stream;
    if (width != 1U || count > sizeof(mock_frame_output)
        || mock_frame_output_pos > sizeof(mock_frame_output) - count) {
        return 0U;
    }
    const size_t actual = mock_frame_short_write != 0 && count != 0U
        ? count - 1U : count;
    memcpy(&mock_frame_output[mock_frame_output_pos], bytes, actual);
    mock_frame_output_pos += actual;
    return actual;
}

static int mb_test_feof(FILE *stream)
{
    (void)stream;
    return mock_frame_eof;
}

static int mb_test_ferror(FILE *stream)
{
    (void)stream;
    return mock_frame_error;
}

static int mb_test_fflush(FILE *stream)
{
    (void)stream;
    return mock_frame_flush_error != 0 ? EOF : 0;
}

static void mb_test_frame_reset(
    const unsigned char *bytes, size_t len, int eof, int error)
{
    mock_frame_input = bytes;
    mock_frame_input_len = len;
    mock_frame_input_pos = 0U;
    mock_frame_eof = eof;
    mock_frame_error = error;
}

static int mb_test_frame_io(void)
{
    unsigned char frame[11] = {0};
    mb_u8 *payload = NULL;
    size_t len = 0U;
    mb_native_process_write_u64(frame, 3U);
    memcpy(&frame[8], "xyz", 3U);
    mb_test_frame_reset(frame, sizeof(frame), 0, 0);
    if (mb_worker_read_frame(&payload, &len) != 1
        || len != 3U || memcmp(payload, "xyz", 3U) != 0
        || mock_frame_input_pos != sizeof(frame)) {
        free(payload);
        return 1;
    }
    free(payload);
    mb_test_frame_reset(frame, 0U, 1, 0);
    if (mb_worker_read_frame(&payload, &len) != 0) {
        return 2;
    }
    mb_test_frame_reset(frame, 0U, 1, 1);
    if (mb_test_ferror(stdin) != 1) {
        return 11;
    }
    if (mb_worker_read_frame(&payload, &len) != -1) {
        return 3;
    }
    mb_test_frame_reset(frame, 4U, 1, 0);
    if (mb_worker_read_frame(&payload, &len) != -1) {
        return 4;
    }
    mb_test_frame_reset(frame, 9U, 1, 0);
    if (mb_worker_read_frame(&payload, &len) != -1) {
        return 5;
    }
    mb_native_process_write_u64(frame, 0U);
    mb_test_frame_reset(frame, 8U, 0, 0);
    if (mb_worker_read_frame(&payload, &len) != 1
        || len != 0U || payload != NULL) {
        return 6;
    }
    mock_frame_output_pos = 0U;
    mock_frame_short_write = 0;
    mock_frame_flush_error = 0;
    if (!mb_worker_write_frame((const mb_u8 *)"xyz", 3U)
        || mock_frame_output_pos != sizeof(frame)) {
        return 7;
    }
    mb_native_process_write_u64(frame, 3U);
    memcpy(&frame[8], "xyz", 3U);
    if (memcmp(mock_frame_output, frame, sizeof(frame)) != 0) {
        return 8;
    }
    mock_frame_short_write = 1;
    if (mb_worker_write_frame(NULL, 0U) != 0) {
        return 9;
    }
    mock_frame_short_write = 0;
    mock_frame_flush_error = 1;
    if (mb_worker_write_frame(NULL, 0U) != 0) {
        return 10;
    }
    mock_frame_flush_error = 0;
    mock_frame_output_pos = 0U;
    if (!mb_worker_write_frame(NULL, 0U)
        || mock_frame_output_pos != 8U) {
        return 12;
    }
    mb_test_frame_reset(frame, 0U, 0, 1);
    if (mb_worker_read_frame(&payload, &len) != -1) {
        return 13;
    }
    // A syntactically valid but unrepresentable object must fail before
    // any attempt to allocate its attacker-controlled payload length.
    mb_native_process_write_u64(frame, (mb_u64)__PTRDIFF_MAX__ + 1U);
    mb_test_frame_reset(frame, 8U, 0, 0);
    if (mb_worker_read_frame(&payload, &len) != -1
        || mock_frame_input_pos != 8U
        || oversized_frame_allocations != 0U) {
        return 14;
    }
    return 0;
}

static void *mb_test_realloc(void *ptr, size_t len)
{
    if (fail_next_table_growth != 0) {
        fail_next_table_growth = 0;
        return NULL;
    }
    return realloc(ptr, len);
}

static void *mb_test_mmap(
    void *address, size_t len, int protection,
    int flags, int descriptor, off_t offset)
{
    if (fail_next_map != 0) {
        fail_next_map = 0;
        errno = ENOMEM;
        return MAP_FAILED;
    }
    void *mapped = mmap(address, len, protection, flags, descriptor, offset);
    if (mapped != MAP_FAILED) {
        mapped_reservations += 1U;
    }
    return mapped;
}

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
    const int result = munmap(address, len);
    if (result == 0) {
        unmapped_reservations += 1U;
    }
    return result;
}

static void *mb_test_malloc(size_t len)
{
    if (len > (size_t)__PTRDIFF_MAX__) {
        oversized_frame_allocations += 1U;
        return NULL;
    }
    if (len == 26U) {
        frame_payload_allocations += 1U;
        if (frame_payload_allocations
            == fail_frame_payload_allocation_number) {
            fail_frame_payload_allocation_number = 0U;
            return NULL;
        }
    }
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
    if (width == 1U && count == fail_next_lifecycle_response) {
        fail_next_lifecycle_response = 0U;
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
        // Direct-handler fixture supplies the native entry without a copy frame.
        .copied_len = 64U,
        .reservation = NULL,
        .reservation_len = 0U,
        .permission = MB_NATIVE_PROCESS_MEMORY_READ_EXECUTE,
        // Direct-handler fixture starts with an already-synchronized entry.
        .synchronized = 1,
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

static int check_allocation_and_table_failure(void)
{
    struct mb_worker_state worker = {.next_id = 1U};
    mb_u8 request[26] = {0};
    mb_u8 *response = NULL;
    size_t response_len = 0U;
    memcpy(request, MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
    mb_native_process_write_u64(&request[9], 64U);
    mb_native_process_write_u64(&request[17], 65536U);
    request[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    fail_next_map = 1;
    if (!mb_worker_handle_allocate(&worker, request, sizeof(request),
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_FAILURE_RESPONSE_BYTES
        || mb_native_process_read_u32(&response[10]) != (mb_u32)ENOMEM
        || worker.count != 0U || worker.next_id != 1U
        || mapped_reservations != unmapped_reservations) {
        mb_test_free(response);
        return 1;
    }
    mb_test_free(response);
    for (size_t i = 0U; i < 4U; ++i) {
        if (!mb_worker_handle_allocate(&worker, request, sizeof(request),
                &response, &response_len)
            || response_len != MB_NATIVE_PROCESS_MEMORY_MAPPING_RESPONSE_BYTES
            || mb_native_process_read_u64(&response[10]) != (mb_u64)(i + 1U)
            || (mb_native_process_read_u64(&response[18]) & 65535U) != 0U
            || worker.count != i + 1U) {
            mb_test_free(response);
            mb_worker_release_all(&worker);
            return 2;
        }
        mb_test_free(response);
    }
    const size_t mapped_before_growth = mapped_reservations;
    fail_next_table_growth = 1;
    if (!mb_worker_handle_allocate(&worker, request, sizeof(request),
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_FAILURE_RESPONSE_BYTES
        || mb_native_process_read_u32(&response[10])
            != MB_WORKER_ALLOCATION_FAILURE
        || worker.count != 4U || worker.capacity != 4U
        || worker.next_id != 5U
        || mapped_reservations != mapped_before_growth
        || mapped_reservations != unmapped_reservations + 4U) {
        mb_test_free(response);
        mb_worker_release_all(&worker);
        return 3;
    }
    mb_test_free(response);
    if (!mb_worker_handle_allocate(&worker, request, sizeof(request),
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_MAPPING_RESPONSE_BYTES
        || mb_native_process_read_u64(&response[10]) != 5U
        || worker.count != 5U || worker.next_id != 6U) {
        mb_test_free(response);
        mb_worker_release_all(&worker);
        return 4;
    }
    mb_test_free(response);
    mb_worker_release_all(&worker);
    return worker.count == 0U && worker.capacity == 0U
        && mapped_reservations == unmapped_reservations ? 0 : 5;
}

static int check_mapping_id_exhaustion(void)
{
    struct mb_worker_state worker = {.next_id = UINT64_MAX};
    mb_u8 request[34] = {0};
    mb_u8 *response = NULL;
    size_t response_len = 0U;
    const size_t mapped_before = mapped_reservations;
    const size_t unmapped_before = unmapped_reservations;
    memcpy(request, MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
    mb_native_process_write_u64(&request[9], 64U);
    mb_native_process_write_u64(&request[17], 65536U);
    request[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    // A failed mmap must not consume the final available mapping identity.
    fail_next_map = 1;
    if (!mb_worker_handle_allocate(&worker, request, 26U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_FAILURE_RESPONSE_BYTES
        || mb_native_process_read_u32(&response[10]) != (mb_u32)ENOMEM
        || worker.next_id != UINT64_MAX || worker.count != 0U
        || mapped_reservations != mapped_before) {
        mb_test_free(response);
        mb_worker_release_all(&worker);
        return 6;
    }
    mb_test_free(response);
    if (!mb_worker_handle_allocate(&worker, request, 26U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_MAPPING_RESPONSE_BYTES
        || mb_native_process_read_u64(&response[10]) != UINT64_MAX
        || worker.count != 1U || worker.next_id != 0U) {
        mb_test_free(response);
        mb_worker_release_all(&worker);
        return 1;
    }
    const mb_u64 address = mb_native_process_read_u64(&response[18]);
    mb_test_free(response);
    if (!mb_worker_handle_allocate(&worker, request, 26U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_FAILURE_RESPONSE_BYTES
        || mb_native_process_read_u32(&response[10])
            != MB_WORKER_ALLOCATION_FAILURE
        || worker.count != 1U || worker.next_id != 0U
        || mapped_reservations != mapped_before + 1U) {
        mb_test_free(response);
        mb_worker_release_all(&worker);
        return 2;
    }
    mb_test_free(response);
    mb_native_process_write_u64(&request[9], UINT64_MAX);
    mb_native_process_write_u64(&request[17], address);
    mb_native_process_write_u64(&request[25], 64U);
    fail_next_release = 1;
    if (!mb_worker_handle_release(&worker, request, 33U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_FAILURE_RESPONSE_BYTES
        || mb_native_process_read_u32(&response[10]) != (mb_u32)EINVAL
        || worker.count != 1U || worker.next_id != 0U
        || unmapped_reservations != unmapped_before) {
        mb_test_free(response);
        mb_worker_release_all(&worker);
        return 7;
    }
    mb_test_free(response);
    if (!mb_worker_handle_release(&worker, request, 33U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_RELEASE_RESPONSE_BYTES
        || worker.count != 0U || worker.next_id != 0U) {
        mb_test_free(response);
        mb_worker_release_all(&worker);
        return 3;
    }
    mb_test_free(response);
    mb_native_process_write_u64(&request[9], 64U);
    mb_native_process_write_u64(&request[17], 65536U);
    request[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    if (!mb_worker_handle_allocate(&worker, request, 26U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_FAILURE_RESPONSE_BYTES
        || mb_native_process_read_u32(&response[10])
            != MB_WORKER_ALLOCATION_FAILURE
        || worker.count != 0U || worker.next_id != 0U
        || mapped_reservations != mapped_before + 1U
        || unmapped_reservations != unmapped_before + 1U) {
        mb_test_free(response);
        mb_worker_release_all(&worker);
        return 4;
    }
    mb_test_free(response);
    mb_worker_release_all(&worker);
    return mapped_reservations == unmapped_reservations ? 0 : 5;
}

static int check_exhausted_id_response_failure(void)
{
    struct mb_worker_state worker = {.next_id = UINT64_MAX};
    mb_u8 request[26] = {0};
    mb_u8 *response = NULL;
    size_t response_len = 0U;
    const size_t mapped_before = mapped_reservations;
    const size_t unmapped_before = unmapped_reservations;
    memcpy(request, MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
    mb_native_process_write_u64(&request[9], 64U);
    mb_native_process_write_u64(&request[17], 65536U);
    request[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    fail_next_lifecycle_response = 35U;
    if (mb_worker_handle_allocate(&worker, request, sizeof(request),
            &response, &response_len)
        || response != NULL || response_len != 0U
        || worker.count != 1U || worker.next_id != 0U
        || worker.mappings[0].id != UINT64_MAX
        || mapped_reservations != mapped_before + 1U) {
        mb_test_free(response);
        mb_worker_release_all(&worker);
        return 1;
    }
    if (!mb_worker_handle_allocate(&worker, request, sizeof(request),
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_FAILURE_RESPONSE_BYTES
        || mb_native_process_read_u32(&response[10])
            != MB_WORKER_ALLOCATION_FAILURE
        || worker.count != 1U || worker.next_id != 0U
        || mapped_reservations != mapped_before + 1U) {
        mb_test_free(response);
        mb_worker_release_all(&worker);
        return 2;
    }
    mb_test_free(response);
    mb_worker_release_all(&worker);
    return worker.count == 0U && worker.next_id == 0U
        && unmapped_reservations == unmapped_before + 1U
        && mapped_reservations == unmapped_reservations ? 0 : 3;
}

static int check_lifecycle_response_failures(void)
{
    struct mb_worker_state worker = {.next_id = 1U};
    mb_u8 request[34] = {0};
    mb_u8 *response = NULL;
    size_t response_len = 0U;
    memcpy(request, MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
    mb_native_process_write_u64(&request[9], 64U);
    mb_native_process_write_u64(&request[17], 65536U);
    request[25] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    fail_next_lifecycle_response = 35U;
    if (mb_worker_handle_allocate(&worker, request, 26U,
            &response, &response_len)
        || response != NULL || response_len != 0U
        || worker.count != 1U || worker.next_id != 2U) {
        mb_test_free(response);
        return 1;
    }
    mb_worker_release_all(&worker);
    if (worker.count != 0U || worker.capacity != 0U) {
        return 2;
    }
    if (!mb_worker_handle_allocate(&worker, request, 26U,
            &response, &response_len)
        || response_len != MB_NATIVE_PROCESS_MEMORY_MAPPING_RESPONSE_BYTES
        || mb_native_process_read_u64(&response[10]) != 2U) {
        mb_test_free(response);
        mb_worker_release_all(&worker);
        return 3;
    }
    const mb_u64 id = mb_native_process_read_u64(&response[10]);
    const mb_u64 base = mb_native_process_read_u64(&response[18]);
    mb_test_free(response);
    mb_native_process_write_u64(&request[9], id);
    mb_native_process_write_u64(&request[17], base);
    mb_native_process_write_u64(&request[25], 64U);
    request[33] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    // A failed response allocation after actual code copy must not grant
    // executable entry authority to those unreported bytes.
    mb_u8 copy[48] = {0};
    memcpy(copy, request, 34U);
    copy[8] = MB_NATIVE_PROCESS_MEMORY_COPY;
    mb_native_process_write_u64(&copy[34], 6U);
    memcpy(&copy[42], "ABCDEF", 6U);
    fail_next_lifecycle_response = 32U;
    response = NULL;
    response_len = 0U;
    if (mb_worker_handle_copy(&worker, copy, sizeof(copy),
            &response, &response_len)
        || response != NULL || response_len != 0U
        || worker.mappings[0].copied_len != 0U
        || memcmp(worker.mappings[0].base, "ABCDEF", 6U) != 0) {
        mb_test_free(response);
        mb_worker_release_all(&worker);
        return 7;
    }
    // An unreported six-byte copy must not survive a shorter reviewed copy.
    mb_native_process_write_u64(&copy[34], 2U);
    memcpy(&copy[42], "XY", 2U);
    if (!mb_worker_handle_copy(&worker, copy, 44U,
            &response, &response_len)
        || response_len != 28U
        || worker.mappings[0].copied_len != 2U
        || memcmp(worker.mappings[0].base, "XY\0\0\0\0", 6U) != 0) {
        mb_test_free(response);
        mb_worker_release_all(&worker);
        return 8;
    }
    mb_test_free(response);
    response = NULL;
    response_len = 0U;
    // An admitted longer copy followed by an empty copy must zero all its
    // previous instructions; the next short replacement must remain usable.
    mb_native_process_write_u64(&copy[34], 6U);
    memcpy(&copy[42], "GHIJKL", 6U);
    if (!mb_worker_handle_copy(&worker, copy, 48U,
            &response, &response_len)
        || response_len != 32U
        || worker.mappings[0].copied_len != 6U
        || memcmp(worker.mappings[0].base, "GHIJKL", 6U) != 0) {
            mb_test_free(response);
            mb_worker_release_all(&worker);
            return 9;
    }
    mb_test_free(response);
    response = NULL;
    response_len = 0U;
    mb_native_process_write_u64(&copy[34], 0U);
    if (!mb_worker_handle_copy(&worker, copy, 42U,
            &response, &response_len)
        || response_len != 26U
        || worker.mappings[0].copied_len != 0U
        || memcmp(worker.mappings[0].base, "\0\0\0\0\0\0", 6U) != 0) {
            mb_test_free(response);
            mb_worker_release_all(&worker);
            return 9;
    }
    mb_test_free(response);
    response = NULL;
    response_len = 0U;
    mb_native_process_write_u64(&copy[34], 2U);
    memcpy(&copy[42], "XY", 2U);
    if (!mb_worker_handle_copy(&worker, copy, 44U,
            &response, &response_len)
        || response_len != 28U
        || worker.mappings[0].copied_len != 2U
        || memcmp(worker.mappings[0].base, "XY\0\0\0\0", 6U) != 0) {
            mb_test_free(response);
            mb_worker_release_all(&worker);
            return 9;
    }
    mb_test_free(response);
    fail_next_lifecycle_response = 35U;
    response = NULL;
    response_len = 0U;
    if (mb_worker_handle_protect(&worker, request, 34U,
            &response, &response_len)
        || response != NULL || response_len != 0U
        || worker.count != 1U
        || worker.mappings[0].permission
            != MB_NATIVE_PROCESS_MEMORY_READ_EXECUTE) {
        mb_test_free(response);
        mb_worker_release_all(&worker);
        return 4;
    }
    // The OS changed this mapping to RX, but no successful protection
    // report was returned: a forged raw sync must not grant call authority.
    const int synchronized_before = worker.mappings[0].synchronized;
    mb_u8 *unreported_sync = NULL;
    size_t unreported_sync_len = 0U;
    if (!mb_worker_handle_sync(&worker, request, 33U,
            &unreported_sync, &unreported_sync_len)
        || unreported_sync == NULL
        || unreported_sync_len
            != MB_NATIVE_PROCESS_MEMORY_FAILURE_RESPONSE_BYTES
        || unreported_sync[9] != MB_NATIVE_PROCESS_MEMORY_FAILURE
        || worker.mappings[0].synchronized != synchronized_before) {
        mb_test_free(unreported_sync);
        mb_worker_release_all(&worker);
        return 10;
    }
    mb_test_free(unreported_sync);
    fail_next_lifecycle_response = 10U;
    if (mb_worker_handle_release(&worker, request, 33U,
            &response, &response_len)
        || response != NULL || response_len != 0U
        || worker.count != 0U) {
        mb_test_free(response);
        mb_worker_release_all(&worker);
        return 5;
    }
    mb_worker_release_all(&worker);
    return mapped_reservations == unmapped_reservations ? 0 : 6;
}

static int mb_test_process_loop_cleanup(int scenario)
{
    unsigned char frames[80] = {0};
    mb_native_process_write_u64(frames, 26U);
    memcpy(&frames[8], MB_NATIVE_PROCESS_MEMORY_MAGIC, 8U);
    frames[16] = MB_NATIVE_PROCESS_MEMORY_ALLOCATE;
    mb_native_process_write_u64(&frames[17], 64U);
    mb_native_process_write_u64(&frames[25], 65536U);
    frames[33] = MB_NATIVE_PROCESS_MEMORY_READ_WRITE;
    size_t frame_len = 34U;
    if (scenario == 1) {
        mb_native_process_write_u64(&frames[34], 8U);
        memcpy(&frames[42], "BADPROTO", 8U);
        frame_len = 50U;
    } else if (scenario == 2) {
        mb_native_process_write_u64(&frames[34], 26U);
        frame_len = 38U;
    } else if (scenario == 3) {
        mb_native_process_write_u64(&frames[34], 26U);
        memcpy(&frames[42], MB_NATIVE_PROCESS_MEMORY_MAGIC, 4U);
        frame_len = 46U;
    }
    if (scenario == 8) {
        mb_native_process_write_u64(&frames[34], 26U);
        memcpy(&frames[42], &frames[8], 26U);
        frame_len = 68U;
    }
    mb_test_frame_reset(frames, frame_len, 1, scenario == 6 ? 1 : 0);
    mock_frame_output_pos = 0U;
    mock_frame_short_write = scenario == 4 ? 1 : 0;
    mock_frame_flush_error = scenario == 5 ? 1 : 0;
    fail_next_lifecycle_response = scenario == 7 ? 35U : 0U;
    frame_payload_allocations = 0U;
    fail_frame_payload_allocation_number = scenario == 8 ? 2U : 0U;
    const size_t mapped_before = mapped_reservations;
    const size_t unmapped_before = unmapped_reservations;
    const int exit_code = mb_test_posix_worker_entry();
    const int expected_exit = scenario == 0 ? 0
        : scenario == 1 || scenario == 4 || scenario == 5
            || scenario == 7 ? 3 : 2;
    const size_t expected_output = scenario == 4 ? 7U
        : scenario == 7 ? 0U : 43U;
    const size_t expected_mappings = 1U;
    const int valid = exit_code == expected_exit
        && mock_frame_output_pos == expected_output
        && (scenario == 4 || scenario == 7
            || mb_native_process_read_u64(mock_frame_output) == 35U)
        && mapped_reservations == mapped_before + expected_mappings
        && unmapped_reservations == unmapped_before + expected_mappings;
    fail_next_lifecycle_response = 0U;
    fail_frame_payload_allocation_number = 0U;
    if (!valid) {
        return 1;
    }
    return 0;
}

int main(void)
{
    const int call_result = check_call_allocations();
    if (call_result != 0) {
        return call_result;
    }
    const int lifecycle_result = check_lifecycle_fault_recovery();
    if (lifecycle_result != 0) {
        return 20 + lifecycle_result;
    }
    const int allocation_result = check_allocation_and_table_failure();
    if (allocation_result != 0) {
        return 40 + allocation_result;
    }
    const int exhaustion_result = check_mapping_id_exhaustion();
    if (exhaustion_result != 0) {
        return 55 + exhaustion_result;
    }
    const int exhausted_response = check_exhausted_id_response_failure();
    if (exhausted_response != 0) {
        return 65 + exhausted_response;
    }
    const int response_result = check_lifecycle_response_failures();
    if (response_result != 0) {
        return 60 + response_result;
    }
    const int frame_result = mb_test_frame_io();
    if (frame_result != 0) {
        return 80 + frame_result;
    }
    for (int scenario = 0; scenario < 9; ++scenario) {
        if (mb_test_process_loop_cleanup(scenario) != 0) {
            return 100 + scenario;
        }
    }
    return 0;
}
