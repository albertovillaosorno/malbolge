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
//   - Version-one monotonic-clock and sleep capability schemas.
// - Must-Not:
//   - Read a host clock, sleep a host thread, or expose a wall-clock epoch.
// - Allows:
//   - Inputs: generic frames, guest bytes, and semantic capability registries.
//   - Outputs: canonical nanosecond request/result values and admitted calls.
//   - Side effects: none.
// - Split-When:
//   - Calendar or deadline clocks require independently versioned semantics.
// - Merge-When:
//   - Built-in capability schemas become generated registry data.
// - Summary:
//   - Stable pointer-free monotonic time and sleep host-capability schemas.
// - Description:
//   - Reserves opaque IDs 0x0400 and 0x0401 with u64 nanosecond payloads.
// - Usage:
//   - Called after generic frame admission and before any host timing effect.
// - Defaults:
//   - Clock has no wall epoch; nonblocking sleep may return WOULD_BLOCK.
//

//! Version-one monotonic clock and sleep capability schemas.

use super::host_capability::{
    HOST_CALL_FLAG_NONBLOCKING, HOST_CAPABILITY_FLAG_AVAILABLE,
    HOST_CAPABILITY_FLAG_MAY_BLOCK, HostCapabilityDescriptor,
    HostCapabilityError, HostCapabilityFrame, HostCapabilityStatus,
    discover_host_capability,
};

/// Stable opaque capability ID for monotonic nanosecond observation.
pub const HOST_MONOTONIC_TIME_CAPABILITY_ID: u32 = 0x0000_0400;
/// Version-one operation number for monotonic time observation.
pub const HOST_MONOTONIC_TIME_V1_OPERATION: u16 = 0;
/// Exact byte length of one monotonic-time result.
pub const HOST_MONOTONIC_TIME_V1_RESULT_SIZE: usize = 8;
/// Stable semantic version for monotonic time observation.
pub const HOST_MONOTONIC_TIME_V1_VERSION: u16 = 1;
/// Stable opaque capability ID for relative-duration sleep.
pub const HOST_SLEEP_CAPABILITY_ID: u32 = 0x0000_0401;
/// Version-one operation number for relative-duration sleep.
pub const HOST_SLEEP_V1_OPERATION: u16 = 0;
/// Exact byte length of one sleep request.
pub const HOST_SLEEP_V1_REQUEST_SIZE: usize = 8;
/// Stable semantic version for relative-duration sleep.
pub const HOST_SLEEP_V1_VERSION: u16 = 1;

/// Builds the semantic descriptor for monotonic-time observation.
#[must_use]
pub const fn host_monotonic_time_v1_descriptor(
    available: bool,
) -> HostCapabilityDescriptor {
    HostCapabilityDescriptor {
        capability_id: HOST_MONOTONIC_TIME_CAPABILITY_ID,
        flags: if available {
            HOST_CAPABILITY_FLAG_AVAILABLE
        } else {
            0
        },
        maximum_version: HOST_MONOTONIC_TIME_V1_VERSION,
        minimum_version: HOST_MONOTONIC_TIME_V1_VERSION,
    }
}

/// Builds the semantic descriptor for relative-duration sleep.
#[must_use]
pub const fn host_sleep_v1_descriptor(
    available: bool,
) -> HostCapabilityDescriptor {
    HostCapabilityDescriptor {
        capability_id: HOST_SLEEP_CAPABILITY_ID,
        flags: if available {
            HOST_CAPABILITY_FLAG_AVAILABLE | HOST_CAPABILITY_FLAG_MAY_BLOCK
        } else {
            HOST_CAPABILITY_FLAG_MAY_BLOCK
        },
        maximum_version: HOST_SLEEP_V1_VERSION,
        minimum_version: HOST_SLEEP_V1_VERSION,
    }
}

/// Encodes one monotonic nanosecond observation result.
#[must_use]
pub const fn encode_host_monotonic_time_v1_result(
    nanoseconds: u64,
) -> [u8; HOST_MONOTONIC_TIME_V1_RESULT_SIZE] {
    nanoseconds.to_le_bytes()
}

/// Decodes one canonical monotonic nanosecond observation result.
///
/// # Errors
///
/// Returns [`HostCapabilityError::InvalidPayload`] for the wrong byte length.
pub fn decode_host_monotonic_time_v1_result(
    payload: &[u8],
) -> Result<u64, HostCapabilityError> {
    let bytes: [u8; HOST_MONOTONIC_TIME_V1_RESULT_SIZE] = payload
        .try_into()
        .map_err(|_error| HostCapabilityError::InvalidPayload)?;
    Ok(u64::from_le_bytes(bytes))
}

/// Encodes one relative sleep duration in nanoseconds.
#[must_use]
pub const fn encode_host_sleep_v1_request(
    nanoseconds: u64,
) -> [u8; HOST_SLEEP_V1_REQUEST_SIZE] {
    nanoseconds.to_le_bytes()
}

/// Decodes one canonical relative sleep duration in nanoseconds.
///
/// # Errors
///
/// Returns [`HostCapabilityError::InvalidPayload`] for the wrong byte length.
pub fn decode_host_sleep_v1_request(
    payload: &[u8],
) -> Result<u64, HostCapabilityError> {
    let bytes: [u8; HOST_SLEEP_V1_REQUEST_SIZE] = payload
        .try_into()
        .map_err(|_error| HostCapabilityError::InvalidPayload)?;
    Ok(u64::from_le_bytes(bytes))
}

/// Admits one monotonic-time observation call before reading a host clock.
///
/// # Errors
///
/// Returns generic frame/registry/range failures first, then schema failures
/// for identity, operation, behavior flags, or request/result shape.
pub fn validate_host_monotonic_time_v1_call(
    frame: HostCapabilityFrame,
    guest_memory_size: u64,
    registry: &[HostCapabilityDescriptor],
) -> Result<(), HostCapabilityError> {
    frame.validate_request(guest_memory_size, registry)?;
    let descriptor = discover_host_capability(
        registry,
        frame.capability_id,
        frame.capability_version,
    )?;
    let expected_result = u64::try_from(HOST_MONOTONIC_TIME_V1_RESULT_SIZE)
        .map_err(|_error| HostCapabilityError::InvalidPayload)?;
    if frame.capability_id != HOST_MONOTONIC_TIME_CAPABILITY_ID
        || frame.capability_version != HOST_MONOTONIC_TIME_V1_VERSION
        || frame.operation != HOST_MONOTONIC_TIME_V1_OPERATION
        || frame.flags != 0
        || frame.request_length != 0
        || frame.result_capacity != expected_result
    {
        return Err(HostCapabilityError::InvalidPayload);
    }
    if descriptor.flags != HOST_CAPABILITY_FLAG_AVAILABLE {
        return Err(HostCapabilityError::InvalidRegistry);
    }
    Ok(())
}

/// Admits and decodes one relative-duration sleep before a host wait.
///
/// A blocking request uses flags zero. A nonblocking request uses exactly
/// [`HOST_CALL_FLAG_NONBLOCKING`] and may later complete as `WOULD_BLOCK`.
///
/// # Errors
///
/// Returns generic frame/registry/range failures first, then schema failures
/// for identity, operation, behavior flags, result shape, or request bytes.
pub fn validate_host_sleep_v1_call(
    frame: HostCapabilityFrame,
    guest_memory: &[u8],
    registry: &[HostCapabilityDescriptor],
) -> Result<u64, HostCapabilityError> {
    let memory_size = u64::try_from(guest_memory.len())
        .map_err(|_error| HostCapabilityError::InvalidRange)?;
    frame.validate_request(memory_size, registry)?;
    let descriptor = discover_host_capability(
        registry,
        frame.capability_id,
        frame.capability_version,
    )?;
    let expected_request = u64::try_from(HOST_SLEEP_V1_REQUEST_SIZE)
        .map_err(|_error| HostCapabilityError::InvalidPayload)?;
    if frame.capability_id != HOST_SLEEP_CAPABILITY_ID
        || frame.capability_version != HOST_SLEEP_V1_VERSION
        || frame.operation != HOST_SLEEP_V1_OPERATION
        || frame.flags & !HOST_CALL_FLAG_NONBLOCKING != 0
        || frame.request_length != expected_request
        || frame.result_capacity != 0
    {
        return Err(HostCapabilityError::InvalidPayload);
    }
    let expected_flags =
        HOST_CAPABILITY_FLAG_AVAILABLE | HOST_CAPABILITY_FLAG_MAY_BLOCK;
    if descriptor.flags != expected_flags {
        return Err(HostCapabilityError::InvalidRegistry);
    }
    decode_host_sleep_v1_request(request_payload(frame, guest_memory)?)
}

/// Validates and decodes the staged monotonic-time result shape.
///
/// Generic response identity/status validation remains owned by the framing
/// layer. This schema check runs before publication and closes the successful
/// result width: `COMPLETE` is exactly one little-endian `u64`; host error and
/// cancellation carry no bytes.
///
/// # Errors
///
/// Returns [`HostCapabilityError::InvalidResponse`] for any status/result-byte
/// combination outside the version-one result schema.
pub fn validate_host_monotonic_time_v1_result(
    response: HostCapabilityFrame,
    staged_result: &[u8],
) -> Result<Option<u64>, HostCapabilityError> {
    if response.status == HostCapabilityStatus::Complete {
        let expected = u64::try_from(HOST_MONOTONIC_TIME_V1_RESULT_SIZE)
            .map_err(|_error| HostCapabilityError::InvalidResponse)?;
        if response.result_length != expected
            || staged_result.len() != HOST_MONOTONIC_TIME_V1_RESULT_SIZE
        {
            return Err(HostCapabilityError::InvalidResponse);
        }
        return decode_host_monotonic_time_v1_result(staged_result).map(Some);
    }
    if !matches!(
        response.status,
        HostCapabilityStatus::Cancelled | HostCapabilityStatus::HostError
    ) || response.result_length != 0
        || !staged_result.is_empty()
    {
        return Err(HostCapabilityError::InvalidResponse);
    }
    Ok(None)
}

fn request_payload(
    frame: HostCapabilityFrame,
    guest_memory: &[u8],
) -> Result<&[u8], HostCapabilityError> {
    let start = usize::try_from(frame.request_offset)
        .map_err(|_error| HostCapabilityError::InvalidRange)?;
    let length = usize::try_from(frame.request_length)
        .map_err(|_error| HostCapabilityError::InvalidRange)?;
    let end = start
        .checked_add(length)
        .ok_or(HostCapabilityError::InvalidRange)?;
    guest_memory
        .get(start..end)
        .ok_or(HostCapabilityError::InvalidRange)
}
