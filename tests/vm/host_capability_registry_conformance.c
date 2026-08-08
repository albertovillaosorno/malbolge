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
//   - Independent pure-C byte vector for the canonical built-in registry.
// - Must-Not:
//   - Call Rust, infer identity from numeric adjacency, or perform host
//     effects.
// - Allows:
//   - Inputs: independent C descriptor constructors for four built-in families.
//   - Outputs: exact 64-byte registry equality or nonzero conformance failure.
//   - Side effects: test-process memory only.
// - Split-When:
//   - Another ABI version requires an independently versioned registry vector.
// - Merge-When:
//   - Registry generation becomes one shared machine-readable source authority.
// - Summary:
//   - Locks the complete version-one built-in descriptor sequence in pure C.
// - Description:
//   - Proves order, flags, semantic versions, ABI version, and record size.
// - Usage:
//   - Compiled by `tests/test_host_capability_c_abi.py` under strict Clang.
// - Defaults:
//   - All four built-in families are marked available in the canonical vector.
//

//! Independent C vector for the complete built-in capability registry.

#include "malbolge_host_capability_builtin.h"

#include <string.h>

static const uint8_t BUILTIN_REGISTRY_VECTOR[] = {
    0x00, 0x04, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00,
    0x01, 0x00, 0x00, 0x00, 0x01, 0x00, 0x10, 0x00,
    0x01, 0x04, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00,
    0x03, 0x00, 0x00, 0x00, 0x01, 0x00, 0x10, 0x00,
    0x00, 0x06, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00,
    0x01, 0x00, 0x00, 0x00, 0x01, 0x00, 0x10, 0x00,
    0x01, 0x06, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00,
    0x01, 0x00, 0x00, 0x00, 0x01, 0x00, 0x10, 0x00,
};


static int test_registry_rejects_invalid_availability(void)
{
    MalbolgeHostCapabilityDescriptor registry[
        MALBOLGE_HOST_BUILTIN_CAPABILITY_COUNT] = {0};
    MalbolgeHostBuiltinCapabilityAvailability availability = {
        .monotonic_time = MALBOLGE_HOST_CAPABILITY_AVAILABLE_STATE,
        .relative_mouse = MALBOLGE_HOST_CAPABILITY_AVAILABLE_STATE,
        .sleep = MALBOLGE_HOST_CAPABILITY_AVAILABLE_STATE,
        .telemetry = MALBOLGE_HOST_CAPABILITY_AVAILABLE_STATE,
    };
    availability.sleep = (MalbolgeHostCapabilityAvailability)2;
    if (malbolge_host_builtin_capability_registry(
            availability, registry, MALBOLGE_HOST_BUILTIN_CAPABILITY_COUNT) !=
        MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT) {
        return 1;
    }
    if (registry[0].capability_id != 0U) {
        return 2;
    }
    availability.sleep = MALBOLGE_HOST_CAPABILITY_AVAILABLE_STATE;
    if (malbolge_host_builtin_capability_registry(
            availability, registry,
            MALBOLGE_HOST_BUILTIN_CAPABILITY_COUNT - 1U) !=
        MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT) {
        return 3;
    }
    return registry[0].capability_id == 0U ? 0 : 4;
}

int main(void)
{
    const int invalid_failure = test_registry_rejects_invalid_availability();
    if (invalid_failure != 0) {
        return 10 + invalid_failure;
    }
    MalbolgeHostCapabilityDescriptor registry[
        MALBOLGE_HOST_BUILTIN_CAPABILITY_COUNT];
    const MalbolgeHostBuiltinCapabilityAvailability availability = {
        .monotonic_time = MALBOLGE_HOST_CAPABILITY_AVAILABLE_STATE,
        .relative_mouse = MALBOLGE_HOST_CAPABILITY_AVAILABLE_STATE,
        .sleep = MALBOLGE_HOST_CAPABILITY_AVAILABLE_STATE,
        .telemetry = MALBOLGE_HOST_CAPABILITY_AVAILABLE_STATE,
    };
    uint8_t encoded[sizeof(BUILTIN_REGISTRY_VECTOR)] = {0};
    size_t index = 0U;
    if (malbolge_host_builtin_capability_registry(
            availability, registry, MALBOLGE_HOST_BUILTIN_CAPABILITY_COUNT) !=
        MALBOLGE_HOST_CAPABILITY_VALID) {
        return 1;
    }
    for (index = 0U; index < MALBOLGE_HOST_BUILTIN_CAPABILITY_COUNT; ++index) {
        const size_t offset =
            index * MALBOLGE_HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE;
        if (malbolge_host_capability_encode_descriptor(
                &registry[index],
                encoded + offset,
                MALBOLGE_HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE) !=
            MALBOLGE_HOST_CAPABILITY_VALID) {
            return 2;
        }
    }
    return memcmp(encoded, BUILTIN_REGISTRY_VECTOR, sizeof(encoded)) == 0
               ? 0
               : 3;
}
