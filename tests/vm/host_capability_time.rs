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
//   - Safe-Rust conformance for monotonic-time and sleep capabilities v1.
// - Must-Not:
//   - Read a real clock, sleep a thread, or depend on a platform timer API.
// - Allows:
//   - Inputs: public capability codecs, frames, registries, and guest bytes.
//   - Outputs: deterministic schema, status, and admission assertions.
//   - Side effects: test-process memory only.
// - Split-When:
//   - Calendar/deadline capability semantics require separate fixtures.
// - Merge-When:
//   - Built-in capability schema tests become generated vectors.
// - Summary:
//   - Verifies canonical monotonic-clock and relative-sleep contracts.
// - Description:
//   - Exercises u64 encoding, exact result width, and nonblocking sleep rules.
// - Usage:
//   - Composed by the Cargo VM integration-test target.
// - Defaults:
//   - Clock has no wall epoch; sleep duration is an unsigned nanosecond count.
//

//! Monotonic-time and relative-sleep host-capability conformance.

use malbolge::{
    HOST_CALL_FLAG_NONBLOCKING, HOST_CAPABILITY_ABI_VERSION,
    HOST_CAPABILITY_FLAG_AVAILABLE, HOST_CAPABILITY_FLAG_MAY_BLOCK,
    HOST_MONOTONIC_TIME_CAPABILITY_ID, HOST_MONOTONIC_TIME_V1_OPERATION,
    HOST_MONOTONIC_TIME_V1_RESULT_SIZE, HOST_MONOTONIC_TIME_V1_VERSION,
    HOST_SLEEP_CAPABILITY_ID, HOST_SLEEP_V1_OPERATION,
    HOST_SLEEP_V1_REQUEST_SIZE, HOST_SLEEP_V1_VERSION,
    HostCapabilityDescriptor, HostCapabilityError, HostCapabilityFrame,
    HostCapabilityStatus, decode_host_monotonic_time_v1_result,
    decode_host_sleep_v1_request, encode_host_monotonic_time_v1_result,
    encode_host_sleep_v1_request, host_monotonic_time_v1_descriptor,
    host_sleep_v1_descriptor, validate_host_capability_response,
    validate_host_monotonic_time_v1_call,
    validate_host_monotonic_time_v1_result, validate_host_sleep_v1_call,
};

use super::{TestResult, check_equal};

const CLOCK_VALUE: u64 = 0x0102_0304_0506_0708;
const CLOCK_VECTOR: [u8; HOST_MONOTONIC_TIME_V1_RESULT_SIZE] =
    [8, 7, 6, 5, 4, 3, 2, 1];
const REQUEST_OFFSET: u64 = 8;
const RESULT_OFFSET: u64 = 24;
const SLEEP_DURATION: u64 = 1_500_000;
const SLEEP_VECTOR: [u8; HOST_SLEEP_V1_REQUEST_SIZE] =
    [0x60, 0xe3, 0x16, 0, 0, 0, 0, 0];

const fn clock_frame() -> HostCapabilityFrame {
    HostCapabilityFrame {
        abi_version: HOST_CAPABILITY_ABI_VERSION,
        call_id: 71,
        capability_id: HOST_MONOTONIC_TIME_CAPABILITY_ID,
        capability_version: HOST_MONOTONIC_TIME_V1_VERSION,
        flags: 0,
        operation: HOST_MONOTONIC_TIME_V1_OPERATION,
        request_length: 0,
        request_offset: REQUEST_OFFSET,
        result_capacity: 8,
        result_length: 0,
        result_offset: RESULT_OFFSET,
        status: HostCapabilityStatus::Pending,
    }
}

const fn sleep_frame(flags: u32) -> HostCapabilityFrame {
    HostCapabilityFrame {
        abi_version: HOST_CAPABILITY_ABI_VERSION,
        call_id: 72,
        capability_id: HOST_SLEEP_CAPABILITY_ID,
        capability_version: HOST_SLEEP_V1_VERSION,
        flags,
        operation: HOST_SLEEP_V1_OPERATION,
        request_length: 8,
        request_offset: REQUEST_OFFSET,
        result_capacity: 0,
        result_length: 0,
        result_offset: RESULT_OFFSET,
        status: HostCapabilityStatus::Pending,
    }
}

#[test]
fn time_payloads_are_canonical_little_endian_u64() -> TestResult {
    check_equal(
        &encode_host_monotonic_time_v1_result(CLOCK_VALUE),
        &CLOCK_VECTOR,
        "clock result encoding",
    )?;
    check_equal(
        &decode_host_monotonic_time_v1_result(&CLOCK_VECTOR),
        &Ok(CLOCK_VALUE),
        "clock result decoding",
    )?;
    check_equal(
        &encode_host_sleep_v1_request(SLEEP_DURATION),
        &SLEEP_VECTOR,
        "sleep request encoding",
    )?;
    check_equal(
        &decode_host_sleep_v1_request(&SLEEP_VECTOR),
        &Ok(SLEEP_DURATION),
        "sleep request decoding",
    )?;
    check_equal(
        &decode_host_monotonic_time_v1_result(&CLOCK_VECTOR[..7]),
        &Err(HostCapabilityError::InvalidPayload),
        "short clock result",
    )?;
    check_equal(
        &decode_host_sleep_v1_request(&SLEEP_VECTOR[..7]),
        &Err(HostCapabilityError::InvalidPayload),
        "short sleep request",
    )
}

#[test]
fn time_descriptors_have_exact_behavior_flags() -> TestResult {
    check_equal(
        &host_monotonic_time_v1_descriptor(true),
        &HostCapabilityDescriptor {
            capability_id: HOST_MONOTONIC_TIME_CAPABILITY_ID,
            flags: HOST_CAPABILITY_FLAG_AVAILABLE,
            maximum_version: HOST_MONOTONIC_TIME_V1_VERSION,
            minimum_version: HOST_MONOTONIC_TIME_V1_VERSION,
        },
        "monotonic descriptor",
    )?;
    check_equal(
        &host_sleep_v1_descriptor(true),
        &HostCapabilityDescriptor {
            capability_id: HOST_SLEEP_CAPABILITY_ID,
            flags: HOST_CAPABILITY_FLAG_AVAILABLE
                | HOST_CAPABILITY_FLAG_MAY_BLOCK,
            maximum_version: HOST_SLEEP_V1_VERSION,
            minimum_version: HOST_SLEEP_V1_VERSION,
        },
        "sleep descriptor",
    )?;
    check_equal(
        &host_sleep_v1_descriptor(false).flags,
        &HOST_CAPABILITY_FLAG_MAY_BLOCK,
        "unavailable sleep preserves behavior declaration",
    )
}

#[test]
fn monotonic_call_admission_fails_closed() -> TestResult {
    let registry = [host_monotonic_time_v1_descriptor(true)];
    let request = clock_frame();
    check_equal(
        &validate_host_monotonic_time_v1_call(request, 64, &registry),
        &Ok(()),
        "valid monotonic request",
    )?;
    let mutations = [
        (
            HostCapabilityFrame { operation: 1, ..request },
            HostCapabilityError::InvalidPayload,
        ),
        (
            HostCapabilityFrame {
                request_length: 1,
                ..request
            },
            HostCapabilityError::InvalidPayload,
        ),
        (
            HostCapabilityFrame {
                result_capacity: 7,
                ..request
            },
            HostCapabilityError::InvalidPayload,
        ),
        (
            HostCapabilityFrame {
                flags: HOST_CALL_FLAG_NONBLOCKING,
                ..request
            },
            HostCapabilityError::InvalidStatus,
        ),
    ];
    for (mutated, expected) in mutations {
        check_equal(
            &validate_host_monotonic_time_v1_call(mutated, 64, &registry),
            &Err(expected),
            "monotonic frame semantic drift",
        )?;
    }
    Ok(())
}

#[test]
fn monotonic_result_shape_is_exact() -> TestResult {
    let registry = [host_monotonic_time_v1_descriptor(true)];
    let request = clock_frame();
    let complete = HostCapabilityFrame {
        result_length: 8,
        status: HostCapabilityStatus::Complete,
        ..request
    };
    check_equal(
        &validate_host_capability_response(request, complete, 64, &registry),
        &Ok(()),
        "generic clock response",
    )?;
    check_equal(
        &validate_host_monotonic_time_v1_result(complete, &CLOCK_VECTOR),
        &Ok(Some(CLOCK_VALUE)),
        "complete clock result",
    )?;
    let short = HostCapabilityFrame {
        result_length: 7,
        ..complete
    };
    check_equal(
        &validate_host_monotonic_time_v1_result(short, &CLOCK_VECTOR[..7]),
        &Err(HostCapabilityError::InvalidResponse),
        "short successful clock result",
    )
}

#[test]
fn sleep_call_and_would_block_semantics_are_explicit() -> TestResult {
    let registry = [host_sleep_v1_descriptor(true)];
    let mut memory = [0u8; 40];
    memory[8..16].copy_from_slice(&SLEEP_VECTOR);

    let blocking = sleep_frame(0);
    check_equal(
        &validate_host_sleep_v1_call(blocking, &memory, &registry),
        &Ok(SLEEP_DURATION),
        "blocking sleep request",
    )?;
    let nonblocking = sleep_frame(HOST_CALL_FLAG_NONBLOCKING);
    check_equal(
        &validate_host_sleep_v1_call(nonblocking, &memory, &registry),
        &Ok(SLEEP_DURATION),
        "nonblocking sleep request",
    )?;

    let would_block = HostCapabilityFrame {
        status: HostCapabilityStatus::WouldBlock,
        ..nonblocking
    };
    check_equal(
        &validate_host_capability_response(
            nonblocking,
            would_block,
            40,
            &registry,
        ),
        &Ok(()),
        "nonblocking sleep would-block",
    )?;
    let invalid_blocking_response =
        HostCapabilityFrame { flags: 0, ..would_block };
    check_equal(
        &validate_host_capability_response(
            blocking,
            invalid_blocking_response,
            40,
            &registry,
        ),
        &Err(HostCapabilityError::InvalidResponse),
        "blocking sleep cannot would-block",
    )?;

    let unavailable = [host_sleep_v1_descriptor(false)];
    check_equal(
        &validate_host_sleep_v1_call(blocking, &memory, &unavailable),
        &Err(HostCapabilityError::UnavailableCapability),
        "unavailable sleep capability",
    )
}
