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
//   - Pure-C version-one optional execution telemetry capability schema.
// - Must-Not:
//   - Perform UI/logging effects or treat host C strings as the wire ABI.
// - Allows:
//   - Inputs: generic capability frames, registries, and guest byte records.
//   - Outputs: canonical telemetry bytes and validated borrowed byte views.
//   - Side effects: writes only caller-provided encoding/output storage.
// - Split-When:
//   - Split when another observation family needs independent schema ownership.
// - Merge-When:
//   - Merge when built-in capability schemas become generated registry data.
// - Summary:
//   - Pointer-free execution telemetry capability v1 for pure C.
// - Description:
//   - Uses length-delimited canonical UTF-8 rather than host string semantics.
// - Usage:
//   - Called only after capability discovery and before any observation effect.
// - Defaults:
//   - Telemetry absence is optional; malformed admitted payloads fail closed.
//

#ifndef MALBOLGE_VM_C_MALBOLGE_HOST_CAPABILITY_TELEMETRY_H
#define MALBOLGE_VM_C_MALBOLGE_HOST_CAPABILITY_TELEMETRY_H

#include "malbolge_host_capability.h"

#include <stdbool.h>

#define MALBOLGE_HOST_EXECUTION_TELEMETRY_CAPABILITY_ID UINT32_C(0x00000600)
#define MALBOLGE_HOST_EXECUTION_TELEMETRY_V1_OPERATION UINT16_C(0)
#define MALBOLGE_HOST_EXECUTION_TELEMETRY_V1_VERSION UINT16_C(1)

enum {
    MALBOLGE_HOST_EXECUTION_TELEMETRY_V1_HEADER_SIZE = 64,
};

typedef struct MalbolgeHostExecutionTelemetryV1 {
    const uint8_t *language;
    size_t language_length;
    const uint8_t *source;
    size_t source_length;
    uint64_t location;
    const uint8_t *instruction;
    size_t instruction_length;
} MalbolgeHostExecutionTelemetryV1;

MalbolgeHostCapabilityDescriptor
malbolge_host_execution_telemetry_v1_descriptor(bool available);

MalbolgeHostCapabilityValidation malbolge_host_execution_telemetry_v1_encode(
    const MalbolgeHostExecutionTelemetryV1 *telemetry,
    uint8_t *destination,
    size_t destination_capacity,
    size_t *written);

MalbolgeHostCapabilityValidation malbolge_host_execution_telemetry_v1_decode(
    const uint8_t *payload,
    size_t payload_length,
    MalbolgeHostExecutionTelemetryV1 *telemetry);

MalbolgeHostCapabilityValidation
malbolge_host_execution_telemetry_v1_validate_call(
    const MalbolgeHostCapabilityFrame *frame,
    const uint8_t *guest_memory,
    size_t guest_memory_length,
    const MalbolgeHostCapabilityDescriptor *registry,
    size_t registry_length,
    MalbolgeHostExecutionTelemetryV1 *telemetry);

#endif
