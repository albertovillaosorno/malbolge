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
//   - Canonical pure-C registry assembly for version-one built-in capabilities.
// - Must-Not:
//   - Infer availability from host APIs or change semantic identity/order.
// - Allows:
//   - Inputs: explicit availability for each built-in capability family.
//   - Outputs: exactly four sorted version-one capability descriptors.
//   - Side effects: writes only caller-provided descriptor storage.
// - Split-When:
//   - A new ABI version requires independently versioned registry assembly.
// - Merge-When:
//   - A generated registry authority replaces both C and Rust constructors.
// - Summary:
//   - Builds the canonical four-family built-in registry in pure C.
// - Description:
//   - Mirrors Rust typed availability and canonical descriptor ordering.
// - Usage:
//   - Runners use this before discovery or semantic call admission.
// - Defaults:
//   - Availability is explicit; no capability is implicitly granted.
//

#ifndef MALBOLGE_VM_C_MALBOLGE_HOST_CAPABILITY_BUILTIN_H
#define MALBOLGE_VM_C_MALBOLGE_HOST_CAPABILITY_BUILTIN_H

#include "malbolge_host_capability_mouse.h"
#include "malbolge_host_capability_telemetry.h"
#include "malbolge_host_capability_time.h"

enum {
    MALBOLGE_HOST_BUILTIN_CAPABILITY_COUNT = 4,
};

typedef enum MalbolgeHostCapabilityAvailability {
    MALBOLGE_HOST_CAPABILITY_UNAVAILABLE_STATE = 0,
    MALBOLGE_HOST_CAPABILITY_AVAILABLE_STATE = 1,
} MalbolgeHostCapabilityAvailability;

typedef struct MalbolgeHostBuiltinCapabilityAvailability {
    MalbolgeHostCapabilityAvailability monotonic_time;
    MalbolgeHostCapabilityAvailability relative_mouse;
    MalbolgeHostCapabilityAvailability sleep;
    MalbolgeHostCapabilityAvailability telemetry;
} MalbolgeHostBuiltinCapabilityAvailability;

MalbolgeHostCapabilityValidation malbolge_host_builtin_capability_registry(
    MalbolgeHostBuiltinCapabilityAvailability availability,
    MalbolgeHostCapabilityDescriptor *registry,
    size_t registry_length);

#endif
