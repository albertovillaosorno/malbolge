// File:
//   - malbolge_host_capability.h
// Path:
//   - src/runtime/virtual-machine/adapter-outbound/c/malbolge_host_capability.h
//
// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
// Path-Rule:
//   - All paths in this header are repository-root relative.
//
// Boundary-Contract:
// - Owns:
//   - Canonical version-one host-capability frame and registry representation.
// - Must-Not:
//   - Expose host pointers, native handles, libc ABIs, or transport identity.
// - Allows:
//   - Inputs: fixed-width call frames, guest byte ranges, capability registry.
//   - Outputs: canonical wire bytes and deterministic admission diagnostics.
//   - Side effects: validated publication to caller-provided guest memory.
// - Split-When:
//   - Split when transport dispatch gains an independent runtime lifecycle.
// - Merge-When:
//   - Merge when another contract owns the same canonical capability wire ABI.
// - Summary:
//   - Transport-independent versioned host-capability call ABI primitives.
// - Description:
//   - Defines fixed little-endian frames, descriptors, and fail-closed checks.
// - Usage:
//   - Shared by interpreters, native tiers, runners, and conformance fixtures.
// - Defaults:
//   - Version one rejects unknown flags, malformed ranges, and version drift.
//
// Related documents:
// - docs/technical/runtime/execution/versioned-host-capability-call-abi.md
// - docs/technical/adr/verification-trust-boundary.md
//
// Large file:
//   - false

#ifndef MALBOLGE_VM_C_MALBOLGE_HOST_CAPABILITY_H
#define MALBOLGE_VM_C_MALBOLGE_HOST_CAPABILITY_H

#include <stddef.h>
#include <stdint.h>

enum {
    MALBOLGE_HOST_CAPABILITY_FRAME_WIRE_SIZE = 72,
    MALBOLGE_HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE = 16,
    MALBOLGE_HOST_CAPABILITY_SPAN_WIRE_SIZE = 16,
};

#define MALBOLGE_HOST_CAPABILITY_ABI_VERSION UINT16_C(1)
#define MALBOLGE_HOST_CAPABILITY_FRAME_MAGIC UINT32_C(0x4348424d)

#define MALBOLGE_HOST_CALL_FLAG_NONBLOCKING UINT32_C(0x00000001)

#define MALBOLGE_HOST_CAPABILITY_FLAG_AVAILABLE UINT32_C(0x00000001)
#define MALBOLGE_HOST_CAPABILITY_FLAG_MAY_BLOCK UINT32_C(0x00000002)
#define MALBOLGE_HOST_CAPABILITY_FLAG_PARTIAL_PROGRESS UINT32_C(0x00000004)

typedef enum MalbolgeHostCapabilityStatus {
    MALBOLGE_HOST_CAPABILITY_STATUS_PENDING = 0,
    MALBOLGE_HOST_CAPABILITY_STATUS_COMPLETE = 1,
    MALBOLGE_HOST_CAPABILITY_STATUS_PARTIAL = 2,
    MALBOLGE_HOST_CAPABILITY_STATUS_WOULD_BLOCK = 3,
    MALBOLGE_HOST_CAPABILITY_STATUS_HOST_ERROR = 4,
    MALBOLGE_HOST_CAPABILITY_STATUS_CANCELLED = 5,
} MalbolgeHostCapabilityStatus;

typedef enum MalbolgeHostCapabilityValidation {
    MALBOLGE_HOST_CAPABILITY_VALID = 0,
    MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT,
    MALBOLGE_HOST_CAPABILITY_INVALID_WIRE_FRAME,
    MALBOLGE_HOST_CAPABILITY_UNSUPPORTED_ABI_VERSION,
    MALBOLGE_HOST_CAPABILITY_INVALID_REGISTRY,
    MALBOLGE_HOST_CAPABILITY_UNKNOWN,
    MALBOLGE_HOST_CAPABILITY_UNSUPPORTED_VERSION,
    MALBOLGE_HOST_CAPABILITY_UNAVAILABLE,
    MALBOLGE_HOST_CAPABILITY_INVALID_RANGE,
    MALBOLGE_HOST_CAPABILITY_INVALID_STATUS,
    MALBOLGE_HOST_CAPABILITY_INVALID_RESPONSE,
    MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD,
} MalbolgeHostCapabilityValidation;

/* In-memory structure layout is not the wire ABI; use the codec functions. */
typedef struct MalbolgeHostCapabilityFrame {
    uint16_t abi_version;
    uint32_t capability_id;
    uint16_t capability_version;
    uint16_t operation;
    uint32_t flags;
    MalbolgeHostCapabilityStatus status;
    uint64_t request_offset;
    uint64_t request_length;
    uint64_t result_offset;
    uint64_t result_capacity;
    uint64_t result_length;
    uint64_t call_id;
} MalbolgeHostCapabilityFrame;

typedef struct MalbolgeHostCapabilityDescriptor {
    uint32_t capability_id;
    uint16_t minimum_version;
    uint16_t maximum_version;
    uint32_t flags;
} MalbolgeHostCapabilityDescriptor;

typedef struct MalbolgeHostCapabilitySpan {
    uint64_t offset;
    uint64_t length;
} MalbolgeHostCapabilitySpan;

MalbolgeHostCapabilityValidation malbolge_host_capability_encode_frame(
    const MalbolgeHostCapabilityFrame *frame,
    uint8_t *destination,
    size_t destination_length);

MalbolgeHostCapabilityValidation malbolge_host_capability_decode_frame(
    const uint8_t *source,
    size_t source_length,
    MalbolgeHostCapabilityFrame *frame);

MalbolgeHostCapabilityValidation malbolge_host_capability_encode_descriptor(
    const MalbolgeHostCapabilityDescriptor *descriptor,
    uint8_t *destination,
    size_t destination_length);

MalbolgeHostCapabilityValidation malbolge_host_capability_decode_descriptor(
    const uint8_t *source,
    size_t source_length,
    MalbolgeHostCapabilityDescriptor *descriptor);

MalbolgeHostCapabilityValidation malbolge_host_capability_encode_span(
    const MalbolgeHostCapabilitySpan *span,
    uint8_t *destination,
    size_t destination_length);

MalbolgeHostCapabilityValidation malbolge_host_capability_decode_span(
    const uint8_t *source,
    size_t source_length,
    MalbolgeHostCapabilitySpan *span);

MalbolgeHostCapabilityValidation malbolge_host_capability_validate_span(
    const MalbolgeHostCapabilitySpan *span,
    uint64_t record_length,
    uint64_t minimum_offset);

MalbolgeHostCapabilityValidation malbolge_host_capability_validate_registry(
    const MalbolgeHostCapabilityDescriptor *registry,
    size_t registry_length);

MalbolgeHostCapabilityValidation
malbolge_host_capability_validate_wire_registry(
    const uint8_t *registry,
    size_t registry_length);

MalbolgeHostCapabilityValidation malbolge_host_capability_discover(
    const MalbolgeHostCapabilityDescriptor *registry,
    size_t registry_length,
    uint32_t capability_id,
    uint16_t capability_version,
    MalbolgeHostCapabilityDescriptor *descriptor);

MalbolgeHostCapabilityValidation malbolge_host_capability_discover_wire(
    const uint8_t *registry,
    size_t registry_length,
    uint32_t capability_id,
    uint16_t capability_version,
    MalbolgeHostCapabilityDescriptor *descriptor);

MalbolgeHostCapabilityValidation malbolge_host_capability_validate_request(
    const MalbolgeHostCapabilityFrame *frame,
    uint64_t guest_memory_size,
    const MalbolgeHostCapabilityDescriptor *registry,
    size_t registry_length);

MalbolgeHostCapabilityValidation malbolge_host_capability_validate_response(
    const MalbolgeHostCapabilityFrame *request,
    const MalbolgeHostCapabilityFrame *response,
    uint64_t guest_memory_size,
    const MalbolgeHostCapabilityDescriptor *registry,
    size_t registry_length);

MalbolgeHostCapabilityValidation malbolge_host_capability_commit_response(
    const MalbolgeHostCapabilityFrame *request,
    const MalbolgeHostCapabilityFrame *response,
    const MalbolgeHostCapabilityDescriptor *registry,
    size_t registry_length,
    uint8_t *guest_memory,
    size_t guest_memory_length,
    const uint8_t *staged_result,
    size_t staged_result_length);

#endif
