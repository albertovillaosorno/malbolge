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
//   - Pure-C version-one relative mouse capture capability schema.
// - Must-Not:
//   - Perform cursor capture or depend on one native window-system ABI.
// - Allows:
//   - Inputs: generic capability frames, registries, and guest bytes.
//   - Outputs: canonical request bytes and one validated capture decision.
//   - Side effects: writes only caller-provided output storage.
// - Split-When:
//   - Split when relative-input control gains another independent operation.
// - Merge-When:
//   - Merge when built-in capability schemas become generated registry data.
// - Summary:
//   - Pointer-free relative mouse capture capability v1 for pure C.
// - Description:
//   - Mirrors the safe-Rust schema without sharing implementation code.
// - Usage:
//   - Called before any platform-specific cursor effect.
// - Defaults:
//   - Noncanonical booleans, reserved bytes, and semantic drift fail closed.
//

#ifndef MALBOLGE_VM_C_MALBOLGE_HOST_CAPABILITY_MOUSE_H
#define MALBOLGE_VM_C_MALBOLGE_HOST_CAPABILITY_MOUSE_H

#include "malbolge_host_capability.h"

#include <stdbool.h>

#define MALBOLGE_HOST_RELATIVE_MOUSE_CAPTURE_CAPABILITY_ID \
    UINT32_C(0x00000601)
#define MALBOLGE_HOST_RELATIVE_MOUSE_CAPTURE_V1_OPERATION UINT16_C(0)
#define MALBOLGE_HOST_RELATIVE_MOUSE_CAPTURE_V1_VERSION UINT16_C(1)

enum {
    MALBOLGE_HOST_RELATIVE_MOUSE_CAPTURE_V1_REQUEST_SIZE = 8,
};

typedef struct MalbolgeHostRelativeMouseCaptureV1 {
    bool capture;
} MalbolgeHostRelativeMouseCaptureV1;

MalbolgeHostCapabilityDescriptor
malbolge_host_relative_mouse_capture_v1_descriptor(bool available);

MalbolgeHostCapabilityValidation
malbolge_host_relative_mouse_capture_v1_encode(
    const MalbolgeHostRelativeMouseCaptureV1 *request,
    uint8_t *destination,
    size_t destination_length);

MalbolgeHostCapabilityValidation
malbolge_host_relative_mouse_capture_v1_decode(
    const uint8_t *payload,
    size_t payload_length,
    MalbolgeHostRelativeMouseCaptureV1 *request);

MalbolgeHostCapabilityValidation
malbolge_host_relative_mouse_capture_v1_validate_call(
    const MalbolgeHostCapabilityFrame *frame,
    const uint8_t *guest_memory,
    size_t guest_memory_length,
    const MalbolgeHostCapabilityDescriptor *registry,
    size_t registry_length,
    MalbolgeHostRelativeMouseCaptureV1 *request);

#endif
