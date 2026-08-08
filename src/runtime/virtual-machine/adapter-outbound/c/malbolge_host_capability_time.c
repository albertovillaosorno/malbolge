// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Pure-C codecs and admission for timing capability schemas v1.
// - Must-Not:
//   - Read native clocks, sleep threads, or expose platform timing handles.
// - Allows:
//   - Inputs: generic frames, registries, and canonical nanosecond bytes.
//   - Outputs: validated timing values and canonical request/result bytes.
//   - Side effects: writes only caller-provided output storage.
// - Split-When:
//   - Calendar/deadline clock semantics require separate implementation.
// - Merge-When:
//   - Built-in capability schemas become generated registry data.
// - Summary:
//   - Independent C monotonic-time and relative-sleep capability schemas.
// - Description:
//   - Mirrors Rust timing wire semantics without FFI or shared codec code.
// - Usage:
//   - Used before and after platform-specific timing effects.
// - Defaults:
//   - u64 nanoseconds are little-endian; sleep may block.
//

//! Independent pure-C timing host-capability schemas v1.

#include "malbolge_host_capability_time.h"

static bool pointer_ranges_overlap(const void *left,
                                   size_t left_length,
                                   const void *right,
                                   size_t right_length)
{
    uintptr_t left_start;
    uintptr_t right_start;
    if (left == NULL || right == NULL || left_length == 0U ||
        right_length == 0U) {
        return false;
    }
    left_start = (uintptr_t)left;
    right_start = (uintptr_t)right;
    if (left_length > UINTPTR_MAX - left_start ||
        right_length > UINTPTR_MAX - right_start) {
        return true;
    }
    return left_start < right_start + right_length &&
           right_start < left_start + left_length;
}

static uint64_t load_u64_le(const uint8_t *source)
{
    uint64_t value = 0U;
    size_t index = 0U;
    for (index = 0U; index < 8U; ++index) {
        value |= (uint64_t)source[index] << (index * 8U);
    }
    return value;
}

static void store_u64_le(uint8_t *destination, uint64_t value)
{
    size_t index = 0U;
    for (index = 0U; index < 8U; ++index) {
        destination[index] =
            (uint8_t)((value >> (index * 8U)) & UINT64_C(0xff));
    }
}

MalbolgeHostCapabilityDescriptor
malbolge_host_monotonic_time_v1_descriptor(bool available)
{
    const MalbolgeHostCapabilityDescriptor descriptor = {
        MALBOLGE_HOST_MONOTONIC_TIME_CAPABILITY_ID,
        MALBOLGE_HOST_MONOTONIC_TIME_V1_VERSION,
        MALBOLGE_HOST_MONOTONIC_TIME_V1_VERSION,
        available ? MALBOLGE_HOST_CAPABILITY_FLAG_AVAILABLE : 0U,
    };
    return descriptor;
}

MalbolgeHostCapabilityDescriptor
malbolge_host_sleep_v1_descriptor(bool available)
{
    const uint32_t availability =
        available ? MALBOLGE_HOST_CAPABILITY_FLAG_AVAILABLE : 0U;
    const MalbolgeHostCapabilityDescriptor descriptor = {
        MALBOLGE_HOST_SLEEP_CAPABILITY_ID,
        MALBOLGE_HOST_SLEEP_V1_VERSION,
        MALBOLGE_HOST_SLEEP_V1_VERSION,
        availability | MALBOLGE_HOST_CAPABILITY_FLAG_MAY_BLOCK,
    };
    return descriptor;
}

static MalbolgeHostCapabilityValidation encode_u64(
    uint64_t value,
    uint8_t *destination,
    size_t destination_length)
{
    if (destination == NULL || destination_length != 8U) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT;
    }
    store_u64_le(destination, value);
    return MALBOLGE_HOST_CAPABILITY_VALID;
}

static MalbolgeHostCapabilityValidation decode_u64(
    const uint8_t *payload,
    size_t payload_length,
    uint64_t *value)
{
    if (payload == NULL || value == NULL ||
        pointer_ranges_overlap(payload, payload_length, value,
                               sizeof(*value))) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT;
    }
    if (payload_length != 8U) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD;
    }
    *value = load_u64_le(payload);
    return MALBOLGE_HOST_CAPABILITY_VALID;
}

MalbolgeHostCapabilityValidation malbolge_host_monotonic_time_v1_encode_result(
    uint64_t nanoseconds,
    uint8_t *destination,
    size_t destination_length)
{
    return encode_u64(nanoseconds, destination, destination_length);
}

MalbolgeHostCapabilityValidation malbolge_host_monotonic_time_v1_decode_result(
    const uint8_t *payload,
    size_t payload_length,
    uint64_t *nanoseconds)
{
    return decode_u64(payload, payload_length, nanoseconds);
}

MalbolgeHostCapabilityValidation malbolge_host_sleep_v1_encode_request(
    uint64_t nanoseconds,
    uint8_t *destination,
    size_t destination_length)
{
    return encode_u64(nanoseconds, destination, destination_length);
}

MalbolgeHostCapabilityValidation malbolge_host_sleep_v1_decode_request(
    const uint8_t *payload,
    size_t payload_length,
    uint64_t *nanoseconds)
{
    return decode_u64(payload, payload_length, nanoseconds);
}

MalbolgeHostCapabilityValidation malbolge_host_monotonic_time_v1_validate_call(
    const MalbolgeHostCapabilityFrame *frame,
    uint64_t guest_memory_size,
    const MalbolgeHostCapabilityDescriptor *registry,
    size_t registry_length)
{
    MalbolgeHostCapabilityDescriptor descriptor;
    MalbolgeHostCapabilityValidation validation;
    if (frame == NULL) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT;
    }
    validation = malbolge_host_capability_validate_request(
        frame, guest_memory_size, registry, registry_length);
    if (validation != MALBOLGE_HOST_CAPABILITY_VALID) {
        return validation;
    }
    validation = malbolge_host_capability_discover(
        registry, registry_length, frame->capability_id,
        frame->capability_version, &descriptor);
    if (validation != MALBOLGE_HOST_CAPABILITY_VALID) {
        return validation;
    }
    if (frame->capability_id != MALBOLGE_HOST_MONOTONIC_TIME_CAPABILITY_ID ||
        frame->capability_version != MALBOLGE_HOST_MONOTONIC_TIME_V1_VERSION ||
        frame->operation != MALBOLGE_HOST_MONOTONIC_TIME_V1_OPERATION ||
        frame->flags != 0U || frame->request_length != 0U ||
        frame->result_capacity != MALBOLGE_HOST_MONOTONIC_TIME_V1_RESULT_SIZE) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD;
    }
    if (descriptor.flags != MALBOLGE_HOST_CAPABILITY_FLAG_AVAILABLE) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_REGISTRY;
    }
    return MALBOLGE_HOST_CAPABILITY_VALID;
}

MalbolgeHostCapabilityValidation malbolge_host_sleep_v1_validate_call(
    const MalbolgeHostCapabilityFrame *frame,
    const uint8_t *guest_memory,
    size_t guest_memory_length,
    const MalbolgeHostCapabilityDescriptor *registry,
    size_t registry_length,
    uint64_t *nanoseconds)
{
    MalbolgeHostCapabilityDescriptor descriptor;
    MalbolgeHostCapabilityValidation validation;
    const uint32_t expected_flags =
        MALBOLGE_HOST_CAPABILITY_FLAG_AVAILABLE |
        MALBOLGE_HOST_CAPABILITY_FLAG_MAY_BLOCK;
    size_t request_offset;
    if (frame == NULL || nanoseconds == NULL ||
        (guest_memory_length != 0U && guest_memory == NULL) ||
        pointer_ranges_overlap(guest_memory, guest_memory_length,
                               nanoseconds, sizeof(*nanoseconds)) ||
        pointer_ranges_overlap(frame, sizeof(*frame), nanoseconds,
                               sizeof(*nanoseconds))) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT;
    }
    validation = malbolge_host_capability_validate_request(
        frame, (uint64_t)guest_memory_length, registry, registry_length);
    if (validation != MALBOLGE_HOST_CAPABILITY_VALID) {
        return validation;
    }
    validation = malbolge_host_capability_discover(
        registry, registry_length, frame->capability_id,
        frame->capability_version, &descriptor);
    if (validation != MALBOLGE_HOST_CAPABILITY_VALID) {
        return validation;
    }
    if (frame->capability_id != MALBOLGE_HOST_SLEEP_CAPABILITY_ID ||
        frame->capability_version != MALBOLGE_HOST_SLEEP_V1_VERSION ||
        frame->operation != MALBOLGE_HOST_SLEEP_V1_OPERATION ||
        (frame->flags & ~MALBOLGE_HOST_CALL_FLAG_NONBLOCKING) != 0U ||
        frame->request_length != MALBOLGE_HOST_SLEEP_V1_REQUEST_SIZE ||
        frame->result_capacity != 0U) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD;
    }
    if (descriptor.flags != expected_flags) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_REGISTRY;
    }
    request_offset = (size_t)frame->request_offset;
    return malbolge_host_sleep_v1_decode_request(
        guest_memory + request_offset,
        MALBOLGE_HOST_SLEEP_V1_REQUEST_SIZE, nanoseconds);
}

MalbolgeHostCapabilityValidation
malbolge_host_monotonic_time_v1_validate_result(
    const MalbolgeHostCapabilityFrame *response,
    const uint8_t *staged_result,
    size_t staged_result_length,
    uint64_t *nanoseconds,
    bool *has_value)
{
    MalbolgeHostCapabilityValidation validation;
    if (response == NULL || nanoseconds == NULL || has_value == NULL ||
        (staged_result_length != 0U && staged_result == NULL) ||
        pointer_ranges_overlap(staged_result, staged_result_length,
                               nanoseconds, sizeof(*nanoseconds)) ||
        pointer_ranges_overlap(staged_result, staged_result_length,
                               has_value, sizeof(*has_value)) ||
        pointer_ranges_overlap(response, sizeof(*response), nanoseconds,
                               sizeof(*nanoseconds)) ||
        pointer_ranges_overlap(response, sizeof(*response), has_value,
                               sizeof(*has_value)) ||
        pointer_ranges_overlap(nanoseconds, sizeof(*nanoseconds), has_value,
                               sizeof(*has_value))) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT;
    }
    if (response->status == MALBOLGE_HOST_CAPABILITY_STATUS_COMPLETE) {
        if (response->result_length !=
                MALBOLGE_HOST_MONOTONIC_TIME_V1_RESULT_SIZE ||
            staged_result_length !=
                MALBOLGE_HOST_MONOTONIC_TIME_V1_RESULT_SIZE) {
            return MALBOLGE_HOST_CAPABILITY_INVALID_RESPONSE;
        }
        validation = malbolge_host_monotonic_time_v1_decode_result(
            staged_result, staged_result_length, nanoseconds);
        if (validation != MALBOLGE_HOST_CAPABILITY_VALID) {
            return validation;
        }
        *has_value = true;
        return MALBOLGE_HOST_CAPABILITY_VALID;
    }
    if ((response->status != MALBOLGE_HOST_CAPABILITY_STATUS_CANCELLED &&
         response->status != MALBOLGE_HOST_CAPABILITY_STATUS_HOST_ERROR) ||
        response->result_length != 0U || staged_result_length != 0U) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_RESPONSE;
    }
    *nanoseconds = 0U;
    *has_value = false;
    return MALBOLGE_HOST_CAPABILITY_VALID;
}
