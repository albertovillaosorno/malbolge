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
//   - Safe-Rust conformance for relative mouse capture capability v1.
// - Must-Not:
//   - Perform native cursor capture or depend on one platform adapter.
// - Allows:
//   - Inputs: public capability codecs, frames, registries, and guest bytes.
//   - Outputs: deterministic schema and pre-effect admission assertions.
//   - Side effects: test-process memory only.
// - Split-When:
//   - Split when another relative-input operation requires separate fixtures.
// - Merge-When:
//   - Merge when built-in capability schema tests become generated vectors.
// - Summary:
//   - Verifies canonical relative mouse capture payload and call admission.
// - Description:
//   - Exercises boolean encoding, reserved bytes, discovery, and frame shape.
// - Usage:
//   - Composed by the Cargo VM integration-test target.
// - Defaults:
//   - Version one is a synchronous single-operation request with no result.
//

//! Relative mouse capture host-capability conformance.

use malbolge::{
    HOST_CAPABILITY_ABI_VERSION, HOST_RELATIVE_MOUSE_CAPTURE_CAPABILITY_ID,
    HOST_RELATIVE_MOUSE_CAPTURE_V1_OPERATION,
    HOST_RELATIVE_MOUSE_CAPTURE_V1_REQUEST_SIZE,
    HOST_RELATIVE_MOUSE_CAPTURE_V1_VERSION, HostCapabilityDescriptor,
    HostCapabilityError, HostCapabilityFrame, HostCapabilityStatus,
    HostRelativeMouseCaptureV1, decode_host_relative_mouse_capture_v1,
    encode_host_relative_mouse_capture_v1,
    host_relative_mouse_capture_v1_descriptor,
    validate_host_relative_mouse_capture_v1_call,
};

use super::{TestResult, check_equal};

const CAPTURE_VECTOR: [u8; HOST_RELATIVE_MOUSE_CAPTURE_V1_REQUEST_SIZE] =
    [1, 0, 0, 0, 0, 0, 0, 0];
const RELEASE_VECTOR: [u8; HOST_RELATIVE_MOUSE_CAPTURE_V1_REQUEST_SIZE] =
    [0, 0, 0, 0, 0, 0, 0, 0];

const fn call_frame(request_offset: u64) -> HostCapabilityFrame {
    HostCapabilityFrame {
        abi_version: HOST_CAPABILITY_ABI_VERSION,
        call_id: 17,
        capability_id: HOST_RELATIVE_MOUSE_CAPTURE_CAPABILITY_ID,
        capability_version: HOST_RELATIVE_MOUSE_CAPTURE_V1_VERSION,
        flags: 0,
        operation: HOST_RELATIVE_MOUSE_CAPTURE_V1_OPERATION,
        request_length: 8,
        request_offset,
        result_capacity: 0,
        result_length: 0,
        result_offset: request_offset,
        status: HostCapabilityStatus::Pending,
    }
}

#[test]
fn mouse_capture_payload_is_canonical() -> TestResult {
    check_equal(
        &HOST_RELATIVE_MOUSE_CAPTURE_V1_REQUEST_SIZE,
        &8,
        "capture request size",
    )?;
    let capture = HostRelativeMouseCaptureV1 { capture: true };
    let release = HostRelativeMouseCaptureV1 { capture: false };
    check_equal(
        &encode_host_relative_mouse_capture_v1(capture),
        &CAPTURE_VECTOR,
        "capture encoding",
    )?;
    check_equal(
        &encode_host_relative_mouse_capture_v1(release),
        &RELEASE_VECTOR,
        "release encoding",
    )?;
    check_equal(
        &decode_host_relative_mouse_capture_v1(&CAPTURE_VECTOR),
        &Ok(capture),
        "capture decoding",
    )?;
    check_equal(
        &decode_host_relative_mouse_capture_v1(&RELEASE_VECTOR),
        &Ok(release),
        "release decoding",
    )
}

#[test]
fn mouse_capture_payload_rejects_noncanonical_bytes() -> TestResult {
    check_equal(
        &decode_host_relative_mouse_capture_v1(&CAPTURE_VECTOR[..7]),
        &Err(HostCapabilityError::InvalidPayload),
        "short capture payload",
    )?;
    let mut malformed = CAPTURE_VECTOR;
    malformed[0] = 2;
    check_equal(
        &decode_host_relative_mouse_capture_v1(&malformed),
        &Err(HostCapabilityError::InvalidPayload),
        "noncanonical boolean",
    )?;
    malformed = CAPTURE_VECTOR;
    malformed[7] = 1;
    check_equal(
        &decode_host_relative_mouse_capture_v1(&malformed),
        &Err(HostCapabilityError::InvalidPayload),
        "nonzero reserved byte",
    )
}

#[test]
fn mouse_capture_descriptor_has_exact_semantics() -> TestResult {
    check_equal(
        &host_relative_mouse_capture_v1_descriptor(true),
        &HostCapabilityDescriptor {
            capability_id: HOST_RELATIVE_MOUSE_CAPTURE_CAPABILITY_ID,
            flags: 1,
            maximum_version: HOST_RELATIVE_MOUSE_CAPTURE_V1_VERSION,
            minimum_version: HOST_RELATIVE_MOUSE_CAPTURE_V1_VERSION,
        },
        "available descriptor",
    )?;
    check_equal(
        &host_relative_mouse_capture_v1_descriptor(false).flags,
        &0,
        "unavailable descriptor",
    )
}

#[test]
fn mouse_capture_call_admission_is_fail_closed() -> TestResult {
    let registry = [host_relative_mouse_capture_v1_descriptor(true)];
    let mut memory = [0u8; 32];
    memory[8..16].copy_from_slice(&CAPTURE_VECTOR);
    let frame = call_frame(8);
    check_equal(
        &validate_host_relative_mouse_capture_v1_call(
            frame, &memory, &registry,
        ),
        &Ok(HostRelativeMouseCaptureV1 { capture: true }),
        "valid capture call",
    )?;

    let unavailable = [host_relative_mouse_capture_v1_descriptor(false)];
    check_equal(
        &validate_host_relative_mouse_capture_v1_call(
            frame,
            &memory,
            &unavailable,
        ),
        &Err(HostCapabilityError::UnavailableCapability),
        "unavailable capture capability",
    )?;

    let mutations = [
        HostCapabilityFrame { operation: 1, ..frame },
        HostCapabilityFrame {
            result_capacity: 1,
            result_offset: 31,
            ..frame
        },
        HostCapabilityFrame {
            request_length: 7,
            ..frame
        },
    ];
    for mutated in mutations {
        check_equal(
            &validate_host_relative_mouse_capture_v1_call(
                mutated, &memory, &registry,
            ),
            &Err(HostCapabilityError::InvalidPayload),
            "capture frame semantic drift",
        )?;
    }
    Ok(())
}
