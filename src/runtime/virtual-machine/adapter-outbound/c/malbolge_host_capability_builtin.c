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
//   - Canonical pure-C built-in capability registry construction.
// - Must-Not:
//   - Query host services, infer availability, or reorder semantic identities.
// - Allows:
//   - Inputs: explicit typed availability and caller descriptor storage.
//   - Outputs: one validated sorted four-family version-one registry.
//   - Side effects: caller-provided descriptor storage only.
// - Split-When:
//   - Another ABI version requires independent registry construction.
// - Merge-When:
//   - Generated registry data becomes the sole cross-language authority.
// - Summary:
//   - Constructs built-in descriptors in canonical semantic-ID order.
// - Description:
//   - Rejects invalid C enum representations instead of treating them as true.
// - Usage:
//   - Used by C runners and independent registry conformance vectors.
// - Defaults:
//   - No implicit availability or transport selection.
//

//! Pure-C version-one built-in capability registry construction.

#include "malbolge_host_capability_builtin.h"

static bool availability_valid(MalbolgeHostCapabilityAvailability availability)
{
    return availability == MALBOLGE_HOST_CAPABILITY_UNAVAILABLE_STATE ||
           availability == MALBOLGE_HOST_CAPABILITY_AVAILABLE_STATE;
}

static bool availability_value(MalbolgeHostCapabilityAvailability availability)
{
    return availability == MALBOLGE_HOST_CAPABILITY_AVAILABLE_STATE;
}

MalbolgeHostCapabilityValidation malbolge_host_builtin_capability_registry(
    MalbolgeHostBuiltinCapabilityAvailability availability,
    MalbolgeHostCapabilityDescriptor *registry,
    size_t registry_length)
{
    MalbolgeHostCapabilityDescriptor staged[
        MALBOLGE_HOST_BUILTIN_CAPABILITY_COUNT];
    MalbolgeHostCapabilityValidation validation;
    size_t index;
    if (registry == NULL ||
        registry_length != MALBOLGE_HOST_BUILTIN_CAPABILITY_COUNT ||
        !availability_valid(availability.monotonic_time) ||
        !availability_valid(availability.relative_mouse) ||
        !availability_valid(availability.sleep) ||
        !availability_valid(availability.telemetry)) {
        return MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT;
    }
    staged[0] = malbolge_host_monotonic_time_v1_descriptor(
        availability_value(availability.monotonic_time));
    staged[1] = malbolge_host_sleep_v1_descriptor(
        availability_value(availability.sleep));
    staged[2] = malbolge_host_execution_telemetry_v1_descriptor(
        availability_value(availability.telemetry));
    staged[3] = malbolge_host_relative_mouse_capture_v1_descriptor(
        availability_value(availability.relative_mouse));
    validation = malbolge_host_capability_validate_registry(
        staged, MALBOLGE_HOST_BUILTIN_CAPABILITY_COUNT);
    if (validation != MALBOLGE_HOST_CAPABILITY_VALID) {
        return validation;
    }
    for (index = 0U; index < MALBOLGE_HOST_BUILTIN_CAPABILITY_COUNT; ++index) {
        registry[index] = staged[index];
    }
    return MALBOLGE_HOST_CAPABILITY_VALID;
}
