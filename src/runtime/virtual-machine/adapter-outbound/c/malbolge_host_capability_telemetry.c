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
//   - Independent C codec and validator for execution telemetry capability v1.
// - Must-Not:
//   - Perform UI/logging effects or use locale/native C string representation.
// - Allows:
//   - Inputs: admitted generic frames, registries, and canonical guest bytes.
//   - Outputs: canonical payload bytes and validated borrowed telemetry views.
//   - Side effects: writes only caller-provided encoding/output storage.
// - Split-When:
//   - Split when another observation schema needs independent semantic rules.
// - Merge-When:
//   - Merge when built-in capability schemas become generated registry data.
// - Summary:
//   - Pure-C execution telemetry v1 with explicit UTF-8 and byte spans.
// - Description:
//   - Validates payload structure before any host observation can consume it.
// - Usage:
//   - Called by C-compatible runners after generic capability discovery.
// - Defaults:
//   - Empty/NUL/invalid UTF-8 and noncanonical spans fail closed.
//

//! Independent pure-C execution telemetry capability v1.

#include "malbolge_host_capability_telemetry.h"

#include <string.h>

static bool continuation(uint8_t byte)
{
    return byte >= UINT8_C(0x80) && byte <= UINT8_C(0xbf);
}

static bool valid_utf8_text(const uint8_t *text, size_t length)
{
    size_t index = 0U;
    if (text == NULL || length == 0U) {
        return false;
    }
    while (index < length) {
        const uint8_t first = text[index];
        const size_t remaining = length - index;
        if (first == 0U) {
            return false;
        }
        if (first <= UINT8_C(0x7f)) {
            ++index;
            continue;
        }
        if (first >= UINT8_C(0xc2) && first <= UINT8_C(0xdf)) {
            if (remaining < 2U || !continuation(text[index + 1U])) {
                return false;
            }
            index += 2U;
            continue;
        }
        if (first == UINT8_C(0xe0)) {
            if (remaining < 3U || text[index + 1U] < UINT8_C(0xa0) ||
                text[index + 1U] > UINT8_C(0xbf) ||
                !continuation(text[index + 2U])) {
                return false;
            }
            index += 3U;
            continue;
        }
        if ((first >= UINT8_C(0xe1) && first <= UINT8_C(0xec)) ||
            (first >= UINT8_C(0xee) && first <= UINT8_C(0xef))) {
            if (remaining < 3U || !continuation(text[index + 1U]) ||
                !continuation(text[index + 2U])) {
                return false;
            }
            index += 3U;
            continue;
        }
        if (first == UINT8_C(0xed)) {
            if (remaining < 3U || text[index + 1U] < UINT8_C(0x80) ||
                text[index + 1U] > UINT8_C(0x9f) ||
                !continuation(text[index + 2U])) {
                return false;
            }
            index += 3U;
            continue;
        }
        if (first == UINT8_C(0xf0)) {
            if (remaining < 4U || text[index + 1U] < UINT8_C(0x90) ||
                text[index + 1U] > UINT8_C(0xbf) ||
                !continuation(text[index + 2U]) ||
                !continuation(text[index + 3U])) {
                return false;
            }
            index += 4U;
            continue;
        }
        if (first >= UINT8_C(0xf1) && first <= UINT8_C(0xf3)) {
            if (remaining < 4U || !continuation(text[index + 1U]) ||
                !continuation(text[index + 2U]) ||
                !continuation(text[index + 3U])) {
                return false;
            }
            index += 4U;
            continue;
        }
        if (first == UINT8_C(0xf4)) {
            if (remaining < 4U || text[index + 1U] < UINT8_C(0x80) ||
                text[index + 1U] > UINT8_C(0x8f) ||
                !continuation(text[index + 2U]) ||
                !continuation(text[index + 3U])) {
                return false;
            }
            index += 4U;
            continue;
        }
        return false;
    }
    return true;
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

static void store_u64_le(uint8_t *destination, uint64_t value)
{
    size_t index = 0U;
    for (index = 0U; index < 8U; ++index) {
        destination[index] =
            (uint8_t)((value >> (index * 8U)) & UINT64_C(0xff));
    }
}

static bool checked_add_size(size_t left, size_t right, size_t *result)
{
    if (result == NULL || right > SIZE_MAX - left) {
        return false;
    }
    *result = left + right;
    return true;
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

static bool valid_input_text(const uint8_t *text, size_t length)
{
    return valid_utf8_text(text, length);
}

MalbolgeHostCapabilityDescriptor
malbolge_host_execution_telemetry_v1_descriptor(bool available)
{
    const MalbolgeHostCapabilityDescriptor descriptor = {
        MALBOLGE_HOST_EXECUTION_TELEMETRY_CAPABILITY_ID,
        MALBOLGE_HOST_EXECUTION_TELEMETRY_V1_VERSION,
        MALBOLGE_HOST_EXECUTION_TELEMETRY_V1_VERSION,
        available ? MALBOLGE_HOST_CAPABILITY_FLAG_AVAILABLE : 0U,
    };
    return descriptor;
}

static bool telemetry_inputs_valid(
    const MalbolgeHostExecutionTelemetryV1 *telemetry)
{
    return telemetry != NULL &&
           valid_input_text(telemetry->language, telemetry->language_length) &&
           valid_input_text(telemetry->source, telemetry->source_length) &&
           valid_input_text(telemetry->instruction,
                            telemetry->instruction_length);
}

static bool telemetry_size(
    const MalbolgeHostExecutionTelemetryV1 *telemetry,
    size_t *source_offset,
    size_t *instruction_offset,
    size_t *payload_length)
{
    size_t source = 0U;
    size_t instruction = 0U;
    size_t total = 0U;
    if (telemetry == NULL || source_offset == NULL ||
        instruction_offset == NULL || payload_length == NULL ||
        !checked_add_size(MALBOLGE_HOST_EXECUTION_TELEMETRY_V1_HEADER_SIZE,
                          telemetry->language_length, &source) ||
        !checked_add_size(source, telemetry->source_length, &instruction) ||
        !checked_add_size(instruction, telemetry->instruction_length, &total)) {
        return false;
    }
    *source_offset = source;
    *instruction_offset = instruction;
    *payload_length = total;
    return true;
}

MalbolgeHostCapabilityValidation malbolge_host_execution_telemetry_v1_encode(
    const MalbolgeHostExecutionTelemetryV1 *telemetry,
    uint8_t *destination,
    size_t destination_capacity,
    size_t *written)
{
    MalbolgeHostExecutionTelemetryV1 snapshot;
    size_t source_offset = 0U;
    size_t instruction_offset = 0U;
    size_t payload_length = 0U;
    if (telemetry == NULL || destination == NULL || written == NULL) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT;
    }
    snapshot = *telemetry;
    if (!telemetry_inputs_valid(&snapshot)) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD;
    }
    if (!telemetry_size(&snapshot, &source_offset, &instruction_offset,
                        &payload_length)) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD;
    }
    if (destination_capacity < payload_length ||
        pointer_ranges_overlap(destination, payload_length, telemetry,
                               sizeof(*telemetry)) ||
        pointer_ranges_overlap(destination, payload_length, written,
                               sizeof(*written)) ||
        pointer_ranges_overlap(destination, payload_length, snapshot.language,
                               snapshot.language_length) ||
        pointer_ranges_overlap(destination, payload_length, snapshot.source,
                               snapshot.source_length) ||
        pointer_ranges_overlap(destination, payload_length,
                               snapshot.instruction,
                               snapshot.instruction_length) ||
        pointer_ranges_overlap(written, sizeof(*written), telemetry,
                               sizeof(*telemetry)) ||
        pointer_ranges_overlap(written, sizeof(*written), snapshot.language,
                               snapshot.language_length) ||
        pointer_ranges_overlap(written, sizeof(*written), snapshot.source,
                               snapshot.source_length) ||
        pointer_ranges_overlap(written, sizeof(*written), snapshot.instruction,
                               snapshot.instruction_length)) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT;
    }
    memset(destination, 0, MALBOLGE_HOST_EXECUTION_TELEMETRY_V1_HEADER_SIZE);
    store_u64_le(destination + 8U, snapshot.location);
    store_u64_le(destination + 16U,
                 MALBOLGE_HOST_EXECUTION_TELEMETRY_V1_HEADER_SIZE);
    store_u64_le(destination + 24U, (uint64_t)snapshot.language_length);
    store_u64_le(destination + 32U, (uint64_t)source_offset);
    store_u64_le(destination + 40U, (uint64_t)snapshot.source_length);
    store_u64_le(destination + 48U, (uint64_t)instruction_offset);
    store_u64_le(destination + 56U, (uint64_t)snapshot.instruction_length);
    memcpy(destination + MALBOLGE_HOST_EXECUTION_TELEMETRY_V1_HEADER_SIZE,
           snapshot.language, snapshot.language_length);
    memcpy(destination + source_offset, snapshot.source,
           snapshot.source_length);
    memcpy(destination + instruction_offset, snapshot.instruction,
           snapshot.instruction_length);
    *written = payload_length;
    return MALBOLGE_HOST_CAPABILITY_VALID;
}

static MalbolgeHostCapabilityValidation decode_telemetry_spans(
    const uint8_t *payload,
    size_t payload_length,
    MalbolgeHostCapabilitySpan *language,
    MalbolgeHostCapabilitySpan *source,
    MalbolgeHostCapabilitySpan *instruction)
{
    MalbolgeHostCapabilityValidation validation;
    const uint64_t record_length = (uint64_t)payload_length;
    const uint64_t header_length =
        MALBOLGE_HOST_EXECUTION_TELEMETRY_V1_HEADER_SIZE;
    validation = malbolge_host_capability_decode_span(
        payload + 16U, MALBOLGE_HOST_CAPABILITY_SPAN_WIRE_SIZE, language);
    if (validation != MALBOLGE_HOST_CAPABILITY_VALID) {
        return validation;
    }
    validation = malbolge_host_capability_decode_span(
        payload + 32U, MALBOLGE_HOST_CAPABILITY_SPAN_WIRE_SIZE, source);
    if (validation != MALBOLGE_HOST_CAPABILITY_VALID) {
        return validation;
    }
    validation = malbolge_host_capability_decode_span(
        payload + 48U, MALBOLGE_HOST_CAPABILITY_SPAN_WIRE_SIZE, instruction);
    if (validation != MALBOLGE_HOST_CAPABILITY_VALID) {
        return validation;
    }
    validation = malbolge_host_capability_validate_span(
        language, record_length, header_length);
    if (validation != MALBOLGE_HOST_CAPABILITY_VALID) {
        return validation;
    }
    validation = malbolge_host_capability_validate_span(
        source, record_length, header_length);
    if (validation != MALBOLGE_HOST_CAPABILITY_VALID) {
        return validation;
    }
    return malbolge_host_capability_validate_span(
        instruction, record_length, header_length);
}

static bool telemetry_spans_are_canonical(
    size_t payload_length,
    const MalbolgeHostCapabilitySpan *language,
    const MalbolgeHostCapabilitySpan *source,
    const MalbolgeHostCapabilitySpan *instruction)
{
    const uint64_t language_end = language->offset + language->length;
    const uint64_t source_end = source->offset + source->length;
    const uint64_t instruction_end = instruction->offset + instruction->length;
    return language->length != 0U && source->length != 0U &&
           instruction->length != 0U &&
           language->offset ==
               MALBOLGE_HOST_EXECUTION_TELEMETRY_V1_HEADER_SIZE &&
           source->offset == language_end &&
           instruction->offset == source_end &&
           instruction_end == (uint64_t)payload_length;
}

MalbolgeHostCapabilityValidation malbolge_host_execution_telemetry_v1_decode(
    const uint8_t *payload,
    size_t payload_length,
    MalbolgeHostExecutionTelemetryV1 *telemetry)
{
    MalbolgeHostCapabilitySpan language;
    MalbolgeHostCapabilitySpan source;
    MalbolgeHostCapabilitySpan instruction;
    MalbolgeHostExecutionTelemetryV1 decoded;
    MalbolgeHostCapabilityValidation validation;
    size_t language_offset;
    size_t source_offset;
    size_t instruction_offset;
    if (payload == NULL || telemetry == NULL ||
        pointer_ranges_overlap(payload, payload_length, telemetry,
                               sizeof(*telemetry))) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT;
    }
    if (payload_length < MALBOLGE_HOST_EXECUTION_TELEMETRY_V1_HEADER_SIZE ||
        load_u32_le(payload) != 0U || load_u32_le(payload + 4U) != 0U) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD;
    }
    validation = decode_telemetry_spans(
        payload, payload_length, &language, &source, &instruction);
    if (validation != MALBOLGE_HOST_CAPABILITY_VALID) {
        return validation;
    }
    if (!telemetry_spans_are_canonical(payload_length, &language, &source,
                                       &instruction)) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD;
    }
    language_offset = (size_t)language.offset;
    source_offset = (size_t)source.offset;
    instruction_offset = (size_t)instruction.offset;
    decoded.language = payload + language_offset;
    decoded.language_length = (size_t)language.length;
    decoded.source = payload + source_offset;
    decoded.source_length = (size_t)source.length;
    decoded.location = load_u64_le(payload + 8U);
    decoded.instruction = payload + instruction_offset;
    decoded.instruction_length = (size_t)instruction.length;
    if (!telemetry_inputs_valid(&decoded)) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD;
    }
    *telemetry = decoded;
    return MALBOLGE_HOST_CAPABILITY_VALID;
}

MalbolgeHostCapabilityValidation
malbolge_host_execution_telemetry_v1_validate_call(
    const MalbolgeHostCapabilityFrame *frame,
    const uint8_t *guest_memory,
    size_t guest_memory_length,
    const MalbolgeHostCapabilityDescriptor *registry,
    size_t registry_length,
    MalbolgeHostExecutionTelemetryV1 *telemetry)
{
    MalbolgeHostCapabilityDescriptor descriptor;
    MalbolgeHostCapabilityValidation validation;
    size_t request_offset;
    size_t request_length;
    if (frame == NULL || telemetry == NULL ||
        (guest_memory_length != 0U && guest_memory == NULL) ||
        pointer_ranges_overlap(guest_memory, guest_memory_length, telemetry,
                               sizeof(*telemetry))) {
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
            MALBOLGE_HOST_EXECUTION_TELEMETRY_CAPABILITY_ID ||
        frame->capability_version !=
            MALBOLGE_HOST_EXECUTION_TELEMETRY_V1_VERSION ||
        frame->operation != MALBOLGE_HOST_EXECUTION_TELEMETRY_V1_OPERATION ||
        frame->flags != 0U ||
        frame->request_length <
            MALBOLGE_HOST_EXECUTION_TELEMETRY_V1_HEADER_SIZE ||
        frame->result_capacity != 0U) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD;
    }
    if (descriptor.flags != MALBOLGE_HOST_CAPABILITY_FLAG_AVAILABLE) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_REGISTRY;
    }
    request_offset = (size_t)frame->request_offset;
    request_length = (size_t)frame->request_length;
    return malbolge_host_execution_telemetry_v1_decode(
        guest_memory + request_offset, request_length, telemetry);
}
