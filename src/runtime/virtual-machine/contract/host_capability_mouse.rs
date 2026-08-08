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
//   - Version-one guest-directed relative mouse capture capability schema.
// - Must-Not:
//   - Perform mouse capture or bind the schema to one window-system API.
// - Allows:
//   - Inputs: generic frames, guest bytes, and semantic capability registries.
//   - Outputs: one validated boolean capture request.
//   - Side effects: none.
// - Split-When:
//   - Split when relative-input control gains another independent operation.
// - Merge-When:
//   - Merge when built-in capability schemas become generated registry data.
// - Summary:
//   - Stable pointer-free relative mouse capture host-capability schema.
// - Description:
//   - Reserves opaque capability ID 0x0601 and canonical v1 request bytes.
// - Usage:
//   - Called after generic frame admission and before any host cursor effect.
// - Defaults:
//   - Noncanonical booleans, reserved bytes, and behavior drift fail closed.
//

//! Version-one relative mouse capture capability schema.

use super::host_capability::{
    HOST_CAPABILITY_FLAG_AVAILABLE, HostCapabilityDescriptor,
    HostCapabilityError, HostCapabilityFrame, discover_host_capability,
};

/// Stable opaque capability ID for guest-directed relative mouse capture.
pub const HOST_RELATIVE_MOUSE_CAPTURE_CAPABILITY_ID: u32 = 0x0000_0601;
/// Version-one operation number in this single-operation capability family.
pub const HOST_RELATIVE_MOUSE_CAPTURE_V1_OPERATION: u16 = 0;
/// Exact byte length of one version-one capture request.
pub const HOST_RELATIVE_MOUSE_CAPTURE_V1_REQUEST_SIZE: usize = 8;
/// Stable semantic version for relative mouse capture.
pub const HOST_RELATIVE_MOUSE_CAPTURE_V1_VERSION: u16 = 1;

/// Guest request to enable or release relative mouse capture.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct HostRelativeMouseCaptureV1 {
    /// `true` requests relative capture; `false` requests release.
    pub capture: bool,
}

/// Builds the semantic registry descriptor for one runner.
#[must_use]
pub const fn host_relative_mouse_capture_v1_descriptor(
    available: bool,
) -> HostCapabilityDescriptor {
    HostCapabilityDescriptor {
        capability_id: HOST_RELATIVE_MOUSE_CAPTURE_CAPABILITY_ID,
        flags: if available {
            HOST_CAPABILITY_FLAG_AVAILABLE
        } else {
            0
        },
        maximum_version: HOST_RELATIVE_MOUSE_CAPTURE_V1_VERSION,
        minimum_version: HOST_RELATIVE_MOUSE_CAPTURE_V1_VERSION,
    }
}

/// Decodes one canonical relative-mouse-capture request payload.
///
/// # Errors
///
/// Returns [`HostCapabilityError::InvalidPayload`] for a noncanonical boolean,
/// a nonzero reserved byte, or the wrong payload length.
pub fn decode_host_relative_mouse_capture_v1(
    payload: &[u8],
) -> Result<HostRelativeMouseCaptureV1, HostCapabilityError> {
    if payload.len() != HOST_RELATIVE_MOUSE_CAPTURE_V1_REQUEST_SIZE
        || payload
            .get(1..)
            .is_none_or(|reserved| reserved.iter().any(|&byte| byte != 0))
    {
        return Err(HostCapabilityError::InvalidPayload);
    }
    let capture = match payload.first().copied() {
        Some(0) => false,
        Some(1) => true,
        _ => return Err(HostCapabilityError::InvalidPayload),
    };
    Ok(HostRelativeMouseCaptureV1 { capture })
}

/// Encodes one relative-mouse-capture request canonically.
#[must_use]
pub fn encode_host_relative_mouse_capture_v1(
    request: HostRelativeMouseCaptureV1,
) -> [u8; HOST_RELATIVE_MOUSE_CAPTURE_V1_REQUEST_SIZE] {
    let mut payload = [0u8; HOST_RELATIVE_MOUSE_CAPTURE_V1_REQUEST_SIZE];
    payload[0] = u8::from(request.capture);
    payload
}

/// Admits and decodes one relative-mouse-capture call before any host effect.
///
/// # Errors
///
/// Returns generic frame/registry/range failures first, then schema failures
/// for identity, operation, behavior flags, result shape, or request bytes.
pub fn validate_host_relative_mouse_capture_v1_call(
    frame: HostCapabilityFrame,
    guest_memory: &[u8],
    registry: &[HostCapabilityDescriptor],
) -> Result<HostRelativeMouseCaptureV1, HostCapabilityError> {
    let memory_size = u64::try_from(guest_memory.len())
        .map_err(|_error| HostCapabilityError::InvalidRange)?;
    frame.validate_request(memory_size, registry)?;
    let descriptor = discover_host_capability(
        registry,
        frame.capability_id,
        frame.capability_version,
    )?;
    let expected_length =
        u64::try_from(HOST_RELATIVE_MOUSE_CAPTURE_V1_REQUEST_SIZE)
            .map_err(|_error| HostCapabilityError::InvalidPayload)?;
    if frame.capability_id != HOST_RELATIVE_MOUSE_CAPTURE_CAPABILITY_ID
        || frame.capability_version != HOST_RELATIVE_MOUSE_CAPTURE_V1_VERSION
        || frame.operation != HOST_RELATIVE_MOUSE_CAPTURE_V1_OPERATION
        || frame.flags != 0
        || frame.request_length != expected_length
        || frame.result_capacity != 0
    {
        return Err(HostCapabilityError::InvalidPayload);
    }
    if descriptor.flags != HOST_CAPABILITY_FLAG_AVAILABLE {
        return Err(HostCapabilityError::InvalidRegistry);
    }
    decode_host_relative_mouse_capture_v1(request_payload(frame, guest_memory)?)
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
