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
//   - Pure-C validation and codec for relative mouse capture capability v1.
// - Must-Not:
//   - Perform a host cursor effect or expose native handles to guest code.
// - Allows:
//   - Inputs: admitted generic frames, registries, and guest request bytes.
//   - Outputs: canonical bytes and one validated boolean capture request.
//   - Side effects: writes only caller-provided output storage.
// - Split-When:
//   - Split when another relative-input operation requires distinct semantics.
// - Merge-When:
//   - Merge when built-in capability schemas become generated registry data.
// - Summary:
//   - Independent C implementation of relative mouse capture capability v1.
// - Description:
//   - Rejects noncanonical payloads before a platform adapter can observe them.
// - Usage:
//   - Used as a pre-effect boundary by C-compatible runners.
// - Defaults:
//   - Request is exactly eight bytes and carries no result payload.
//

//! Independent pure-C relative mouse capture capability v1.

#include "malbolge_host_capability_mouse.h"

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

MalbolgeHostCapabilityDescriptor
malbolge_host_relative_mouse_capture_v1_descriptor(bool available)
{
    const MalbolgeHostCapabilityDescriptor descriptor = {
        MALBOLGE_HOST_RELATIVE_MOUSE_CAPTURE_CAPABILITY_ID,
        MALBOLGE_HOST_RELATIVE_MOUSE_CAPTURE_V1_VERSION,
        MALBOLGE_HOST_RELATIVE_MOUSE_CAPTURE_V1_VERSION,
        available ? MALBOLGE_HOST_CAPABILITY_FLAG_AVAILABLE : 0U,
    };
    return descriptor;
}

MalbolgeHostCapabilityValidation
malbolge_host_relative_mouse_capture_v1_encode(
    const MalbolgeHostRelativeMouseCaptureV1 *request,
    uint8_t *destination,
    size_t destination_length)
{
    MalbolgeHostRelativeMouseCaptureV1 snapshot;
    size_t index = 0U;
    if (request == NULL || destination == NULL ||
        destination_length !=
            MALBOLGE_HOST_RELATIVE_MOUSE_CAPTURE_V1_REQUEST_SIZE) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT;
    }
    snapshot = *request;
    destination[0] = snapshot.capture ? UINT8_C(1) : UINT8_C(0);
    for (index = 1U; index < destination_length; ++index) {
        destination[index] = 0U;
    }
    return MALBOLGE_HOST_CAPABILITY_VALID;
}

MalbolgeHostCapabilityValidation
malbolge_host_relative_mouse_capture_v1_decode(
    const uint8_t *payload,
    size_t payload_length,
    MalbolgeHostRelativeMouseCaptureV1 *request)
{
    MalbolgeHostRelativeMouseCaptureV1 decoded;
    size_t index = 0U;
    if (payload == NULL || request == NULL ||
        pointer_ranges_overlap(payload, payload_length, request,
                               sizeof(*request))) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT;
    }
    if (payload_length !=
        MALBOLGE_HOST_RELATIVE_MOUSE_CAPTURE_V1_REQUEST_SIZE) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD;
    }
    if (payload[0] > UINT8_C(1)) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD;
    }
    for (index = 1U; index < payload_length; ++index) {
        if (payload[index] != 0U) {
            return MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD;
        }
    }
    decoded.capture = payload[0] != 0U;
    *request = decoded;
    return MALBOLGE_HOST_CAPABILITY_VALID;
}

MalbolgeHostCapabilityValidation
malbolge_host_relative_mouse_capture_v1_validate_call(
    const MalbolgeHostCapabilityFrame *frame,
    const uint8_t *guest_memory,
    size_t guest_memory_length,
    const MalbolgeHostCapabilityDescriptor *registry,
    size_t registry_length,
    MalbolgeHostRelativeMouseCaptureV1 *request)
{
    MalbolgeHostCapabilityDescriptor descriptor;
    MalbolgeHostCapabilityValidation validation;
    size_t request_offset;
    if (frame == NULL || request == NULL ||
        (guest_memory_length != 0U && guest_memory == NULL) ||
        pointer_ranges_overlap(guest_memory, guest_memory_length, request,
                               sizeof(*request))) {
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
    if (frame->capability_id !=
            MALBOLGE_HOST_RELATIVE_MOUSE_CAPTURE_CAPABILITY_ID ||
        frame->capability_version !=
            MALBOLGE_HOST_RELATIVE_MOUSE_CAPTURE_V1_VERSION ||
        frame->operation != MALBOLGE_HOST_RELATIVE_MOUSE_CAPTURE_V1_OPERATION ||
        frame->flags != 0U ||
        frame->request_length !=
            MALBOLGE_HOST_RELATIVE_MOUSE_CAPTURE_V1_REQUEST_SIZE ||
        frame->result_capacity != 0U) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD;
    }
    if (descriptor.flags != MALBOLGE_HOST_CAPABILITY_FLAG_AVAILABLE) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_REGISTRY;
    }
    request_offset = (size_t)frame->request_offset;
    return malbolge_host_relative_mouse_capture_v1_decode(
        guest_memory + request_offset,
        MALBOLGE_HOST_RELATIVE_MOUSE_CAPTURE_V1_REQUEST_SIZE, request);
}
