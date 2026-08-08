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
//   - Pure-C monotonic-clock and relative-sleep capability schemas v1.
// - Must-Not:
//   - Read native clocks, sleep threads, or expose a host wall-clock epoch.
// - Allows:
//   - Inputs: generic frames, registries, and canonical u64 payload bytes.
//   - Outputs: validated nanosecond values and canonical request/result bytes.
//   - Side effects: writes only caller-provided output storage.
// - Split-When:
//   - Calendar or deadline clocks require independent schema ownership.
// - Merge-When:
//   - Built-in capability schemas become generated registry data.
// - Summary:
//   - Pointer-free monotonic time and relative sleep capability schemas v1.
// - Description:
//   - Mirrors safe Rust IDs 0x0400/0x0401 without sharing implementation code.
// - Usage:
//   - Called before any platform-specific timing effect.
// - Defaults:
//   - Values are little-endian u64 nanoseconds; sleep may block.
//

#ifndef MALBOLGE_VM_C_MALBOLGE_HOST_CAPABILITY_TIME_H
#define MALBOLGE_VM_C_MALBOLGE_HOST_CAPABILITY_TIME_H

#include "malbolge_host_capability.h"

#include <stdbool.h>

#define MALBOLGE_HOST_MONOTONIC_TIME_CAPABILITY_ID UINT32_C(0x00000400)
#define MALBOLGE_HOST_MONOTONIC_TIME_V1_OPERATION UINT16_C(0)
#define MALBOLGE_HOST_MONOTONIC_TIME_V1_VERSION UINT16_C(1)

#define MALBOLGE_HOST_SLEEP_CAPABILITY_ID UINT32_C(0x00000401)
#define MALBOLGE_HOST_SLEEP_V1_OPERATION UINT16_C(0)
#define MALBOLGE_HOST_SLEEP_V1_VERSION UINT16_C(1)

enum {
    MALBOLGE_HOST_MONOTONIC_TIME_V1_RESULT_SIZE = 8,
    MALBOLGE_HOST_SLEEP_V1_REQUEST_SIZE = 8,
};

MalbolgeHostCapabilityDescriptor
malbolge_host_monotonic_time_v1_descriptor(bool available);

MalbolgeHostCapabilityDescriptor
malbolge_host_sleep_v1_descriptor(bool available);

MalbolgeHostCapabilityValidation malbolge_host_monotonic_time_v1_encode_result(
    uint64_t nanoseconds,
    uint8_t *destination,
    size_t destination_length);

MalbolgeHostCapabilityValidation malbolge_host_monotonic_time_v1_decode_result(
    const uint8_t *payload,
    size_t payload_length,
    uint64_t *nanoseconds);

MalbolgeHostCapabilityValidation malbolge_host_sleep_v1_encode_request(
    uint64_t nanoseconds,
    uint8_t *destination,
    size_t destination_length);

MalbolgeHostCapabilityValidation malbolge_host_sleep_v1_decode_request(
    const uint8_t *payload,
    size_t payload_length,
    uint64_t *nanoseconds);

MalbolgeHostCapabilityValidation malbolge_host_monotonic_time_v1_validate_call(
    const MalbolgeHostCapabilityFrame *frame,
    uint64_t guest_memory_size,
    const MalbolgeHostCapabilityDescriptor *registry,
    size_t registry_length);

MalbolgeHostCapabilityValidation malbolge_host_sleep_v1_validate_call(
    const MalbolgeHostCapabilityFrame *frame,
    const uint8_t *guest_memory,
    size_t guest_memory_length,
    const MalbolgeHostCapabilityDescriptor *registry,
    size_t registry_length,
    uint64_t *nanoseconds);

MalbolgeHostCapabilityValidation
malbolge_host_monotonic_time_v1_validate_result(
    const MalbolgeHostCapabilityFrame *response,
    const uint8_t *staged_result,
    size_t staged_result_length,
    uint64_t *nanoseconds,
    bool *has_value);

#endif
