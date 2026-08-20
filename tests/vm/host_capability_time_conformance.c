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
//   - Independent C vectors for version-one timing host capabilities.
// - Must-Not:
//   - Call Rust, read native clocks, sleep threads, or perform host effects.
// - Allows:
//   - Inputs: pure-C timing codecs, generic framing, and fixed byte fixtures.
//   - Outputs: zero on conformance success, nonzero on first-class failure.
//   - Side effects: test-process memory only.
// - Split-When:
//   - Another timing family needs an independently versioned native harness.
// - Merge-When:
//   - Timing vectors become generated cross-language conformance data.
// - Summary:
//   - Verifies monotonic-time and relative-sleep schemas independently in C.
// - Description:
//   - Covers exact bytes, descriptors, admission, and WOULD_BLOCK behavior.
// - Usage:
//   - Compiled by `tests/test_host_capability_c_abi.py` with strict Clang.
// - Defaults:
//   - No tested path calls a real external host timing capability.
//

//! Independent pure-C timing host-capability conformance.

#include "malbolge_host_capability_time.h"

#include <string.h>

static const uint8_t CLOCK_VECTOR[] = {
    0x08, 0x07, 0x06, 0x05, 0x04, 0x03, 0x02, 0x01,
};
static const uint8_t SLEEP_VECTOR[] = {
    0x60, 0xe3, 0x16, 0x00, 0x00, 0x00, 0x00, 0x00,
};

static int expect_validation(MalbolgeHostCapabilityValidation actual,
                             MalbolgeHostCapabilityValidation expected)
{
    return actual == expected ? 0 : 1;
}

static int expect_true(bool condition)
{
    return condition ? 0 : 1;
}

static MalbolgeHostCapabilityFrame clock_request(void)
{
    const MalbolgeHostCapabilityFrame frame = {
        .abi_version = MALBOLGE_HOST_CAPABILITY_ABI_VERSION,
        .capability_id = MALBOLGE_HOST_MONOTONIC_TIME_CAPABILITY_ID,
        .capability_version = MALBOLGE_HOST_MONOTONIC_TIME_V1_VERSION,
        .operation = MALBOLGE_HOST_MONOTONIC_TIME_V1_OPERATION,
        .flags = 0U,
        .status = MALBOLGE_HOST_CAPABILITY_STATUS_PENDING,
        .request_offset = UINT64_C(8),
        .request_length = 0U,
        .result_offset = UINT64_C(24),
        .result_capacity = MALBOLGE_HOST_MONOTONIC_TIME_V1_RESULT_SIZE,
        .result_length = 0U,
        .call_id = UINT64_C(71),
    };
    return frame;
}

static MalbolgeHostCapabilityFrame sleep_request(uint32_t flags)
{
    const MalbolgeHostCapabilityFrame frame = {
        .abi_version = MALBOLGE_HOST_CAPABILITY_ABI_VERSION,
        .capability_id = MALBOLGE_HOST_SLEEP_CAPABILITY_ID,
        .capability_version = MALBOLGE_HOST_SLEEP_V1_VERSION,
        .operation = MALBOLGE_HOST_SLEEP_V1_OPERATION,
        .flags = flags,
        .status = MALBOLGE_HOST_CAPABILITY_STATUS_PENDING,
        .request_offset = UINT64_C(8),
        .request_length = MALBOLGE_HOST_SLEEP_V1_REQUEST_SIZE,
        .result_offset = UINT64_C(24),
        .result_capacity = 0U,
        .result_length = 0U,
        .call_id = UINT64_C(72),
    };
    return frame;
}

static int test_time_payloads(void)
{
    uint8_t payload[8] = {0};
    uint64_t decoded = 0U;
    int failures = 0;
    failures += expect_validation(
        malbolge_host_monotonic_time_v1_encode_result(
            UINT64_C(0x0102030405060708), payload, sizeof(payload)),
        MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_true(
        memcmp(payload, CLOCK_VECTOR, sizeof(CLOCK_VECTOR)) == 0);
    failures += expect_validation(
        malbolge_host_monotonic_time_v1_decode_result(
            CLOCK_VECTOR, sizeof(CLOCK_VECTOR), &decoded),
        MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_true(decoded == UINT64_C(0x0102030405060708));
    failures += expect_validation(
        malbolge_host_sleep_v1_encode_request(
            UINT64_C(1500000), payload, sizeof(payload)),
        MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_true(
        memcmp(payload, SLEEP_VECTOR, sizeof(SLEEP_VECTOR)) == 0);
    failures += expect_validation(
        malbolge_host_sleep_v1_decode_request(
            SLEEP_VECTOR, sizeof(SLEEP_VECTOR), &decoded),
        MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_true(decoded == UINT64_C(1500000));
    failures += expect_validation(
        malbolge_host_sleep_v1_decode_request(
            SLEEP_VECTOR, sizeof(SLEEP_VECTOR) - 1U, &decoded),
        MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD);
    return failures;
}

static int test_time_descriptors(void)
{
    const MalbolgeHostCapabilityDescriptor clock =
        malbolge_host_monotonic_time_v1_descriptor(true);
    const MalbolgeHostCapabilityDescriptor sleep =
        malbolge_host_sleep_v1_descriptor(true);
    const MalbolgeHostCapabilityDescriptor unavailable_sleep =
        malbolge_host_sleep_v1_descriptor(false);
    int failures = 0;
    failures += expect_true(
        clock.capability_id == MALBOLGE_HOST_MONOTONIC_TIME_CAPABILITY_ID);
    failures += expect_true(
        clock.flags == MALBOLGE_HOST_CAPABILITY_FLAG_AVAILABLE);
    failures += expect_true(
        sleep.capability_id == MALBOLGE_HOST_SLEEP_CAPABILITY_ID);
    failures += expect_true(
        sleep.flags == (MALBOLGE_HOST_CAPABILITY_FLAG_AVAILABLE |
                        MALBOLGE_HOST_CAPABILITY_FLAG_MAY_BLOCK));
    failures += expect_true(
        unavailable_sleep.flags == MALBOLGE_HOST_CAPABILITY_FLAG_MAY_BLOCK);
    return failures;
}

static int test_monotonic_call_and_result(void)
{
    MalbolgeHostCapabilityDescriptor registry[] = {
        malbolge_host_monotonic_time_v1_descriptor(true),
    };
    MalbolgeHostCapabilityFrame request = clock_request();
    MalbolgeHostCapabilityFrame response = request;
    uint64_t decoded = 0U;
    bool has_value = false;
    int failures = 0;
    failures += expect_validation(
        malbolge_host_monotonic_time_v1_validate_call(
            &request, UINT64_C(64), registry, 1U),
        MALBOLGE_HOST_CAPABILITY_VALID);
    response.status = MALBOLGE_HOST_CAPABILITY_STATUS_COMPLETE;
    response.result_length = MALBOLGE_HOST_MONOTONIC_TIME_V1_RESULT_SIZE;
    failures += expect_validation(
        malbolge_host_capability_validate_response(
            &request, &response, UINT64_C(64), registry, 1U),
        MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_validation(
        malbolge_host_monotonic_time_v1_validate_result(
            &response, CLOCK_VECTOR, sizeof(CLOCK_VECTOR),
            &decoded, &has_value),
        MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_true(has_value);
    failures += expect_true(decoded == UINT64_C(0x0102030405060708));
    response.result_length -= UINT64_C(1);
    failures += expect_validation(
        malbolge_host_monotonic_time_v1_validate_result(
            &response, CLOCK_VECTOR, sizeof(CLOCK_VECTOR) - 1U,
            &decoded, &has_value),
        MALBOLGE_HOST_CAPABILITY_INVALID_RESPONSE);
    request.flags = MALBOLGE_HOST_CALL_FLAG_NONBLOCKING;
    failures += expect_validation(
        malbolge_host_monotonic_time_v1_validate_call(
            &request, UINT64_C(64), registry, 1U),
        MALBOLGE_HOST_CAPABILITY_INVALID_STATUS);
    {
        union ClockResultAlias {
            uint8_t staged[8];
            uint64_t decoded;
        } overlap = {0};
        bool overlap_has_value = false;
        response.result_length = MALBOLGE_HOST_MONOTONIC_TIME_V1_RESULT_SIZE;
        memcpy(overlap.staged, CLOCK_VECTOR, sizeof(CLOCK_VECTOR));
        failures += expect_validation(
            malbolge_host_monotonic_time_v1_validate_result(
                &response, overlap.staged, sizeof(overlap.staged),
                &overlap.decoded, &overlap_has_value),
            MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT);
    }
    return failures;
}

static int test_sleep_call_and_would_block(void)
{
    MalbolgeHostCapabilityDescriptor registry[] = {
        malbolge_host_sleep_v1_descriptor(true),
    };
    MalbolgeHostCapabilityFrame blocking = sleep_request(0U);
    MalbolgeHostCapabilityFrame nonblocking =
        sleep_request(MALBOLGE_HOST_CALL_FLAG_NONBLOCKING);
    MalbolgeHostCapabilityFrame response = nonblocking;
    uint8_t memory[40] = {0};
    uint64_t duration = 0U;
    int failures = 0;
    memcpy(memory + 8U, SLEEP_VECTOR, sizeof(SLEEP_VECTOR));
    failures += expect_validation(
        malbolge_host_sleep_v1_validate_call(
            &blocking, memory, sizeof(memory), registry, 1U, &duration),
        MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_true(duration == UINT64_C(1500000));
    failures += expect_validation(
        malbolge_host_sleep_v1_validate_call(
            &nonblocking, memory, sizeof(memory), registry, 1U, &duration),
        MALBOLGE_HOST_CAPABILITY_VALID);
    response.status = MALBOLGE_HOST_CAPABILITY_STATUS_WOULD_BLOCK;
    failures += expect_validation(
        malbolge_host_capability_validate_response(
            &nonblocking, &response, (uint64_t)sizeof(memory), registry, 1U),
        MALBOLGE_HOST_CAPABILITY_VALID);
    response.flags = 0U;
    failures += expect_validation(
        malbolge_host_capability_validate_response(
            &blocking, &response, (uint64_t)sizeof(memory), registry, 1U),
        MALBOLGE_HOST_CAPABILITY_INVALID_RESPONSE);
    registry[0] = malbolge_host_sleep_v1_descriptor(false);
    failures += expect_validation(
        malbolge_host_sleep_v1_validate_call(
            &blocking, memory, sizeof(memory), registry, 1U, &duration),
        MALBOLGE_HOST_CAPABILITY_UNAVAILABLE);
    {
        union SleepOutputAlias {
            uint8_t memory[40];
            uint64_t decoded;
        } overlap = {0};
        registry[0] = malbolge_host_sleep_v1_descriptor(true);
        memcpy(overlap.memory + 8U, SLEEP_VECTOR, sizeof(SLEEP_VECTOR));
        failures += expect_validation(
            malbolge_host_sleep_v1_validate_call(
                &blocking, overlap.memory, sizeof(overlap.memory), registry,
                1U, &overlap.decoded),
            MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT);
    }
    return failures;
}

int main(void)
{
    int failures = 0;
    failures += test_monotonic_call_and_result();
    failures += test_sleep_call_and_would_block();
    failures += test_time_descriptors();
    failures += test_time_payloads();
    return failures;
}
