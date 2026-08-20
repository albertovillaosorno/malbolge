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
//   - Canonical version-one host-capability wire codecs and admission checks.
// - Must-Not:
//   - Perform host effects or depend on one transport, OS, or native backend.
// - Allows:
//   - Inputs: fixed-width frames, guest memory extent, semantic registry.
//   - Outputs: canonical bytes and deterministic validation categories.
//   - Side effects: validates then publishes staged bytes to guest memory.
// - Split-When:
//   - Split when host dispatch or capability-specific schemas need ownership.
// - Merge-When:
//   - Merge when another module owns identical canonical frame semantics.
// - Summary:
//   - Implements transport-neutral host-capability framing and validation.
// - Description:
//   - Encodes little-endian wire data and validates before any host effect.
// - Usage:
//   - Called by execution tiers before dispatching external guest requests.
// - Defaults:
//   - Unknown semantics and malformed or overlapping ranges fail closed.
//

//! Canonical version-one host-capability frame and registry validation.

#include "malbolge_host_capability.h"

#include <stdbool.h>
#include <string.h>

static const uint32_t KNOWN_CALL_FLAGS = MALBOLGE_HOST_CALL_FLAG_NONBLOCKING;
static const uint32_t KNOWN_CAPABILITY_FLAGS =
    MALBOLGE_HOST_CAPABILITY_FLAG_AVAILABLE |
    MALBOLGE_HOST_CAPABILITY_FLAG_MAY_BLOCK |
    MALBOLGE_HOST_CAPABILITY_FLAG_PARTIAL_PROGRESS;

static uint16_t load_u16_le(const uint8_t *source)
{
    return (uint16_t)((uint16_t)source[0] |
                      (uint16_t)((uint16_t)source[1] << 8U));
}

static uint32_t load_u32_le(const uint8_t *source)
{
    return (uint32_t)source[0] | ((uint32_t)source[1] << 8U) |
           ((uint32_t)source[2] << 16U) | ((uint32_t)source[3] << 24U);
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

static void store_u16_le(uint8_t *destination, uint16_t value)
{
    destination[0] = (uint8_t)(value & UINT16_C(0x00ff));
    destination[1] = (uint8_t)(value >> 8U);
}

static void store_u32_le(uint8_t *destination, uint32_t value)
{
    destination[0] = (uint8_t)(value & UINT32_C(0x000000ff));
    destination[1] = (uint8_t)((value >> 8U) & UINT32_C(0x000000ff));
    destination[2] = (uint8_t)((value >> 16U) & UINT32_C(0x000000ff));
    destination[3] = (uint8_t)(value >> 24U);
}

static void store_u64_le(uint8_t *destination, uint64_t value)
{
    size_t index = 0U;
    for (index = 0U; index < 8U; ++index) {
        destination[index] =
            (uint8_t)((value >> (index * 8U)) & UINT64_C(0xff));
    }
}

static bool valid_status(MalbolgeHostCapabilityStatus status)
{
    return status == MALBOLGE_HOST_CAPABILITY_STATUS_PENDING ||
           status == MALBOLGE_HOST_CAPABILITY_STATUS_COMPLETE ||
           status == MALBOLGE_HOST_CAPABILITY_STATUS_PARTIAL ||
           status == MALBOLGE_HOST_CAPABILITY_STATUS_WOULD_BLOCK ||
           status == MALBOLGE_HOST_CAPABILITY_STATUS_HOST_ERROR ||
           status == MALBOLGE_HOST_CAPABILITY_STATUS_CANCELLED;
}

static MalbolgeHostCapabilityValidation validate_frame_shape(
    const MalbolgeHostCapabilityFrame *frame)
{
    if (frame == NULL) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT;
    }
    if (frame->abi_version != MALBOLGE_HOST_CAPABILITY_ABI_VERSION) {
        return MALBOLGE_HOST_CAPABILITY_UNSUPPORTED_ABI_VERSION;
    }
    if (frame->capability_id == 0U || frame->capability_version == 0U ||
        (frame->flags & ~KNOWN_CALL_FLAGS) != 0U) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_WIRE_FRAME;
    }
    if (!valid_status(frame->status)) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_STATUS;
    }
    if (frame->result_length > frame->result_capacity) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_STATUS;
    }
    if (frame->status == MALBOLGE_HOST_CAPABILITY_STATUS_PENDING &&
        frame->result_length != 0U) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_STATUS;
    }
    if ((frame->status == MALBOLGE_HOST_CAPABILITY_STATUS_WOULD_BLOCK ||
         frame->status == MALBOLGE_HOST_CAPABILITY_STATUS_HOST_ERROR ||
         frame->status == MALBOLGE_HOST_CAPABILITY_STATUS_CANCELLED) &&
        frame->result_length != 0U) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_STATUS;
    }
    return MALBOLGE_HOST_CAPABILITY_VALID;
}

static bool descriptor_valid(const MalbolgeHostCapabilityDescriptor *descriptor)
{
    return descriptor->capability_id != 0U &&
           descriptor->minimum_version != 0U &&
           descriptor->minimum_version <= descriptor->maximum_version &&
           (descriptor->flags & ~KNOWN_CAPABILITY_FLAGS) == 0U;
}

static bool range_valid(uint64_t offset,
                        uint64_t length,
                        uint64_t guest_memory_size)
{
    return offset <= guest_memory_size &&
           length <= guest_memory_size - offset;
}

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

static bool ranges_overlap(uint64_t left_offset,
                           uint64_t left_length,
                           uint64_t right_offset,
                           uint64_t right_length)
{
    uint64_t left_end;
    uint64_t right_end;
    if (left_length == 0U || right_length == 0U) {
        return false;
    }
    left_end = left_offset + left_length;
    right_end = right_offset + right_length;
    return left_offset < right_end && right_offset < left_end;
}

MalbolgeHostCapabilityValidation malbolge_host_capability_encode_frame(
    const MalbolgeHostCapabilityFrame *frame,
    uint8_t *destination,
    size_t destination_length)
{
    MalbolgeHostCapabilityFrame snapshot;
    MalbolgeHostCapabilityValidation validation;
    if (frame == NULL || destination == NULL ||
        destination_length != MALBOLGE_HOST_CAPABILITY_FRAME_WIRE_SIZE) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT;
    }
    snapshot = *frame;
    validation = validate_frame_shape(&snapshot);
    if (validation != MALBOLGE_HOST_CAPABILITY_VALID) {
        return validation;
    }
    store_u32_le(destination, MALBOLGE_HOST_CAPABILITY_FRAME_MAGIC);
    store_u16_le(destination + 4U, snapshot.abi_version);
    store_u16_le(destination + 6U,
                 (uint16_t)MALBOLGE_HOST_CAPABILITY_FRAME_WIRE_SIZE);
    store_u32_le(destination + 8U, snapshot.capability_id);
    store_u16_le(destination + 12U, snapshot.capability_version);
    store_u16_le(destination + 14U, snapshot.operation);
    store_u32_le(destination + 16U, snapshot.flags);
    store_u32_le(destination + 20U, (uint32_t)snapshot.status);
    store_u64_le(destination + 24U, snapshot.request_offset);
    store_u64_le(destination + 32U, snapshot.request_length);
    store_u64_le(destination + 40U, snapshot.result_offset);
    store_u64_le(destination + 48U, snapshot.result_capacity);
    store_u64_le(destination + 56U, snapshot.result_length);
    store_u64_le(destination + 64U, snapshot.call_id);
    return MALBOLGE_HOST_CAPABILITY_VALID;
}

MalbolgeHostCapabilityValidation malbolge_host_capability_decode_frame(
    const uint8_t *source,
    size_t source_length,
    MalbolgeHostCapabilityFrame *frame)
{
    MalbolgeHostCapabilityFrame decoded;
    MalbolgeHostCapabilityValidation validation;
    uint32_t status_value;
    if (source == NULL || frame == NULL) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT;
    }
    if (source_length < 8U ||
        load_u32_le(source) != MALBOLGE_HOST_CAPABILITY_FRAME_MAGIC) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_WIRE_FRAME;
    }
    decoded.abi_version = load_u16_le(source + 4U);
    if (decoded.abi_version != MALBOLGE_HOST_CAPABILITY_ABI_VERSION) {
        return MALBOLGE_HOST_CAPABILITY_UNSUPPORTED_ABI_VERSION;
    }
    if (source_length != MALBOLGE_HOST_CAPABILITY_FRAME_WIRE_SIZE ||
        load_u16_le(source + 6U) !=
            (uint16_t)MALBOLGE_HOST_CAPABILITY_FRAME_WIRE_SIZE) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_WIRE_FRAME;
    }
    decoded.capability_id = load_u32_le(source + 8U);
    decoded.capability_version = load_u16_le(source + 12U);
    decoded.operation = load_u16_le(source + 14U);
    decoded.flags = load_u32_le(source + 16U);
    status_value = load_u32_le(source + 20U);
    if (status_value >
        (uint32_t)MALBOLGE_HOST_CAPABILITY_STATUS_CANCELLED) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_STATUS;
    }
    decoded.status = (MalbolgeHostCapabilityStatus)status_value;
    decoded.request_offset = load_u64_le(source + 24U);
    decoded.request_length = load_u64_le(source + 32U);
    decoded.result_offset = load_u64_le(source + 40U);
    decoded.result_capacity = load_u64_le(source + 48U);
    decoded.result_length = load_u64_le(source + 56U);
    decoded.call_id = load_u64_le(source + 64U);
    validation = validate_frame_shape(&decoded);
    if (validation != MALBOLGE_HOST_CAPABILITY_VALID) {
        return validation;
    }
    *frame = decoded;
    return MALBOLGE_HOST_CAPABILITY_VALID;
}

MalbolgeHostCapabilityValidation malbolge_host_capability_encode_descriptor(
    const MalbolgeHostCapabilityDescriptor *descriptor,
    uint8_t *destination,
    size_t destination_length)
{
    MalbolgeHostCapabilityDescriptor snapshot;
    if (descriptor == NULL || destination == NULL ||
        destination_length != MALBOLGE_HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT;
    }
    snapshot = *descriptor;
    if (!descriptor_valid(&snapshot)) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_REGISTRY;
    }
    store_u32_le(destination, snapshot.capability_id);
    store_u16_le(destination + 4U, snapshot.minimum_version);
    store_u16_le(destination + 6U, snapshot.maximum_version);
    store_u32_le(destination + 8U, snapshot.flags);
    store_u16_le(destination + 12U, MALBOLGE_HOST_CAPABILITY_ABI_VERSION);
    store_u16_le(
        destination + 14U,
        (uint16_t)MALBOLGE_HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE);
    return MALBOLGE_HOST_CAPABILITY_VALID;
}

MalbolgeHostCapabilityValidation malbolge_host_capability_decode_descriptor(
    const uint8_t *source,
    size_t source_length,
    MalbolgeHostCapabilityDescriptor *descriptor)
{
    MalbolgeHostCapabilityDescriptor decoded;
    if (source == NULL || descriptor == NULL) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT;
    }
    if (source_length < 14U) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_WIRE_FRAME;
    }
    if (load_u16_le(source + 12U) !=
        MALBOLGE_HOST_CAPABILITY_ABI_VERSION) {
        return MALBOLGE_HOST_CAPABILITY_UNSUPPORTED_ABI_VERSION;
    }
    if (source_length != MALBOLGE_HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE ||
        load_u16_le(source + 14U) !=
            (uint16_t)MALBOLGE_HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_WIRE_FRAME;
    }
    decoded.capability_id = load_u32_le(source);
    decoded.minimum_version = load_u16_le(source + 4U);
    decoded.maximum_version = load_u16_le(source + 6U);
    decoded.flags = load_u32_le(source + 8U);
    if (!descriptor_valid(&decoded)) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_REGISTRY;
    }
    *descriptor = decoded;
    return MALBOLGE_HOST_CAPABILITY_VALID;
}

MalbolgeHostCapabilityValidation malbolge_host_capability_encode_span(
    const MalbolgeHostCapabilitySpan *span,
    uint8_t *destination,
    size_t destination_length)
{
    MalbolgeHostCapabilitySpan snapshot;
    if (span == NULL || destination == NULL ||
        destination_length != MALBOLGE_HOST_CAPABILITY_SPAN_WIRE_SIZE) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT;
    }
    snapshot = *span;
    store_u64_le(destination, snapshot.offset);
    store_u64_le(destination + 8U, snapshot.length);
    return MALBOLGE_HOST_CAPABILITY_VALID;
}

MalbolgeHostCapabilityValidation malbolge_host_capability_decode_span(
    const uint8_t *source,
    size_t source_length,
    MalbolgeHostCapabilitySpan *span)
{
    MalbolgeHostCapabilitySpan decoded;
    if (source == NULL || span == NULL) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT;
    }
    if (source_length != MALBOLGE_HOST_CAPABILITY_SPAN_WIRE_SIZE) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD;
    }
    decoded.offset = load_u64_le(source);
    decoded.length = load_u64_le(source + 8U);
    *span = decoded;
    return MALBOLGE_HOST_CAPABILITY_VALID;
}

MalbolgeHostCapabilityValidation malbolge_host_capability_validate_span(
    const MalbolgeHostCapabilitySpan *span,
    uint64_t record_length,
    uint64_t minimum_offset)
{
    if (span == NULL || minimum_offset > record_length) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT;
    }
    if (span->offset < minimum_offset ||
        !range_valid(span->offset, span->length, record_length)) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD;
    }
    return MALBOLGE_HOST_CAPABILITY_VALID;
}

MalbolgeHostCapabilityValidation malbolge_host_capability_validate_registry(
    const MalbolgeHostCapabilityDescriptor *registry,
    size_t registry_length)
{
    size_t index = 0U;
    if (registry_length != 0U && registry == NULL) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT;
    }
    for (index = 0U; index < registry_length; ++index) {
        if (!descriptor_valid(&registry[index])) {
            return MALBOLGE_HOST_CAPABILITY_INVALID_REGISTRY;
        }
        if (index != 0U &&
            registry[index - 1U].capability_id >=
                registry[index].capability_id) {
            return MALBOLGE_HOST_CAPABILITY_INVALID_REGISTRY;
        }
    }
    return MALBOLGE_HOST_CAPABILITY_VALID;
}

MalbolgeHostCapabilityValidation
malbolge_host_capability_validate_wire_registry(
    const uint8_t *registry,
    size_t registry_length)
{
    MalbolgeHostCapabilityDescriptor descriptor;
    uint32_t previous_id = 0U;
    size_t offset = 0U;
    if (registry_length != 0U && registry == NULL) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT;
    }
    for (offset = 0U; offset < registry_length;
         offset += MALBOLGE_HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE) {
        const size_t remaining = registry_length - offset;
        MalbolgeHostCapabilityValidation validation;
        if (remaining < 14U) {
            return MALBOLGE_HOST_CAPABILITY_INVALID_WIRE_FRAME;
        }
        if (load_u16_le(registry + offset + 12U) !=
            MALBOLGE_HOST_CAPABILITY_ABI_VERSION) {
            return MALBOLGE_HOST_CAPABILITY_UNSUPPORTED_ABI_VERSION;
        }
        if (remaining < MALBOLGE_HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE) {
            return MALBOLGE_HOST_CAPABILITY_INVALID_WIRE_FRAME;
        }
        validation = malbolge_host_capability_decode_descriptor(
            registry + offset,
            MALBOLGE_HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE,
            &descriptor);
        if (validation != MALBOLGE_HOST_CAPABILITY_VALID) {
            return validation;
        }
        if (previous_id >= descriptor.capability_id && offset != 0U) {
            return MALBOLGE_HOST_CAPABILITY_INVALID_REGISTRY;
        }
        previous_id = descriptor.capability_id;
    }
    return MALBOLGE_HOST_CAPABILITY_VALID;
}

MalbolgeHostCapabilityValidation malbolge_host_capability_discover(
    const MalbolgeHostCapabilityDescriptor *registry,
    size_t registry_length,
    uint32_t capability_id,
    uint16_t capability_version,
    MalbolgeHostCapabilityDescriptor *descriptor)
{
    MalbolgeHostCapabilityValidation validation;
    size_t index = 0U;
    if (capability_id == 0U || capability_version == 0U) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT;
    }
    validation =
        malbolge_host_capability_validate_registry(registry, registry_length);
    if (validation != MALBOLGE_HOST_CAPABILITY_VALID) {
        return validation;
    }
    for (index = 0U; index < registry_length; ++index) {
        const MalbolgeHostCapabilityDescriptor candidate = registry[index];
        if (candidate.capability_id < capability_id) {
            continue;
        }
        if (candidate.capability_id > capability_id) {
            return MALBOLGE_HOST_CAPABILITY_UNKNOWN;
        }
        if (capability_version < candidate.minimum_version ||
            capability_version > candidate.maximum_version) {
            return MALBOLGE_HOST_CAPABILITY_UNSUPPORTED_VERSION;
        }
        if ((candidate.flags & MALBOLGE_HOST_CAPABILITY_FLAG_AVAILABLE) == 0U) {
            return MALBOLGE_HOST_CAPABILITY_UNAVAILABLE;
        }
        if (descriptor != NULL) {
            *descriptor = candidate;
        }
        return MALBOLGE_HOST_CAPABILITY_VALID;
    }
    return MALBOLGE_HOST_CAPABILITY_UNKNOWN;
}

MalbolgeHostCapabilityValidation malbolge_host_capability_discover_wire(
    const uint8_t *registry,
    size_t registry_length,
    uint32_t capability_id,
    uint16_t capability_version,
    MalbolgeHostCapabilityDescriptor *descriptor)
{
    MalbolgeHostCapabilityDescriptor candidate;
    MalbolgeHostCapabilityValidation validation;
    size_t offset = 0U;
    if (capability_id == 0U || capability_version == 0U) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT;
    }
    validation = malbolge_host_capability_validate_wire_registry(
        registry, registry_length);
    if (validation != MALBOLGE_HOST_CAPABILITY_VALID) {
        return validation;
    }
    for (offset = 0U; offset < registry_length;
         offset += MALBOLGE_HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE) {
        validation = malbolge_host_capability_decode_descriptor(
            registry + offset,
            MALBOLGE_HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE,
            &candidate);
        if (validation != MALBOLGE_HOST_CAPABILITY_VALID) {
            return validation;
        }
        if (candidate.capability_id < capability_id) {
            continue;
        }
        if (candidate.capability_id > capability_id) {
            return MALBOLGE_HOST_CAPABILITY_UNKNOWN;
        }
        if (capability_version < candidate.minimum_version ||
            capability_version > candidate.maximum_version) {
            return MALBOLGE_HOST_CAPABILITY_UNSUPPORTED_VERSION;
        }
        if ((candidate.flags & MALBOLGE_HOST_CAPABILITY_FLAG_AVAILABLE) == 0U) {
            return MALBOLGE_HOST_CAPABILITY_UNAVAILABLE;
        }
        if (descriptor != NULL) {
            *descriptor = candidate;
        }
        return MALBOLGE_HOST_CAPABILITY_VALID;
    }
    return MALBOLGE_HOST_CAPABILITY_UNKNOWN;
}

MalbolgeHostCapabilityValidation malbolge_host_capability_validate_request(
    const MalbolgeHostCapabilityFrame *frame,
    uint64_t guest_memory_size,
    const MalbolgeHostCapabilityDescriptor *registry,
    size_t registry_length)
{
    MalbolgeHostCapabilityDescriptor descriptor;
    MalbolgeHostCapabilityValidation validation = validate_frame_shape(frame);
    if (validation != MALBOLGE_HOST_CAPABILITY_VALID) {
        return validation;
    }
    if (frame->status != MALBOLGE_HOST_CAPABILITY_STATUS_PENDING) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_STATUS;
    }
    validation = malbolge_host_capability_discover(
        registry, registry_length, frame->capability_id,
        frame->capability_version, &descriptor);
    if (validation != MALBOLGE_HOST_CAPABILITY_VALID) {
        return validation;
    }
    if ((frame->flags & MALBOLGE_HOST_CALL_FLAG_NONBLOCKING) != 0U &&
        (descriptor.flags & MALBOLGE_HOST_CAPABILITY_FLAG_MAY_BLOCK) == 0U) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_STATUS;
    }
    if (!range_valid(frame->request_offset, frame->request_length,
                     guest_memory_size) ||
        !range_valid(frame->result_offset, frame->result_capacity,
                     guest_memory_size)) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_RANGE;
    }
    if (ranges_overlap(frame->request_offset, frame->request_length,
                       frame->result_offset, frame->result_capacity)) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_RANGE;
    }
    return MALBOLGE_HOST_CAPABILITY_VALID;
}

static bool response_identity_matches(
    const MalbolgeHostCapabilityFrame *request,
    const MalbolgeHostCapabilityFrame *response)
{
    return response->abi_version == request->abi_version &&
           response->capability_id == request->capability_id &&
           response->capability_version == request->capability_version &&
           response->operation == request->operation &&
           response->flags == request->flags &&
           response->request_offset == request->request_offset &&
           response->request_length == request->request_length &&
           response->result_offset == request->result_offset &&
           response->result_capacity == request->result_capacity &&
           response->call_id == request->call_id;
}

MalbolgeHostCapabilityValidation malbolge_host_capability_validate_response(
    const MalbolgeHostCapabilityFrame *request,
    const MalbolgeHostCapabilityFrame *response,
    uint64_t guest_memory_size,
    const MalbolgeHostCapabilityDescriptor *registry,
    size_t registry_length)
{
    MalbolgeHostCapabilityDescriptor descriptor;
    MalbolgeHostCapabilityValidation validation;
    validation = malbolge_host_capability_validate_request(
        request, guest_memory_size, registry, registry_length);
    if (validation != MALBOLGE_HOST_CAPABILITY_VALID) {
        return validation;
    }
    validation = validate_frame_shape(response);
    if (validation != MALBOLGE_HOST_CAPABILITY_VALID) {
        return validation;
    }
    if (!response_identity_matches(request, response) ||
        response->status == MALBOLGE_HOST_CAPABILITY_STATUS_PENDING) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_RESPONSE;
    }
    validation = malbolge_host_capability_discover(
        registry, registry_length, request->capability_id,
        request->capability_version, &descriptor);
    if (validation != MALBOLGE_HOST_CAPABILITY_VALID) {
        return validation;
    }
    if (response->status == MALBOLGE_HOST_CAPABILITY_STATUS_PARTIAL &&
        ((descriptor.flags &
          MALBOLGE_HOST_CAPABILITY_FLAG_PARTIAL_PROGRESS) == 0U ||
         response->result_length == 0U)) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_RESPONSE;
    }
    if (response->status == MALBOLGE_HOST_CAPABILITY_STATUS_WOULD_BLOCK &&
        ((descriptor.flags & MALBOLGE_HOST_CAPABILITY_FLAG_MAY_BLOCK) == 0U ||
         (request->flags & MALBOLGE_HOST_CALL_FLAG_NONBLOCKING) == 0U)) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_RESPONSE;
    }
    return MALBOLGE_HOST_CAPABILITY_VALID;
}

MalbolgeHostCapabilityValidation malbolge_host_capability_commit_response(
    const MalbolgeHostCapabilityFrame *request,
    const MalbolgeHostCapabilityFrame *response,
    const MalbolgeHostCapabilityDescriptor *registry,
    size_t registry_length,
    uint8_t *guest_memory,
    size_t guest_memory_length,
    const uint8_t *staged_result,
    size_t staged_result_length)
{
    MalbolgeHostCapabilityValidation validation;
    size_t result_offset;
    if ((guest_memory_length != 0U && guest_memory == NULL) ||
        (staged_result_length != 0U && staged_result == NULL)) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT;
    }
    validation = malbolge_host_capability_validate_response(
        request, response, (uint64_t)guest_memory_length, registry,
        registry_length);
    if (validation != MALBOLGE_HOST_CAPABILITY_VALID) {
        return validation;
    }
    if (response->result_length != (uint64_t)staged_result_length) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_RESPONSE;
    }
    if (pointer_ranges_overlap(guest_memory, guest_memory_length,
                               staged_result, staged_result_length)) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT;
    }
    if (staged_result_length == 0U) {
        return MALBOLGE_HOST_CAPABILITY_VALID;
    }
    result_offset = (size_t)response->result_offset;
    memcpy(guest_memory + result_offset, staged_result, staged_result_length);
    return MALBOLGE_HOST_CAPABILITY_VALID;
}
