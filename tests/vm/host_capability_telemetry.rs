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
//   - Safe-Rust conformance for optional execution telemetry capability v1.
// - Must-Not:
//   - Update UI/logs or allow observation to influence guest execution.
// - Allows:
//   - Inputs: public telemetry codecs, frames, registries, and guest bytes.
//   - Outputs: exact vector, malformed payload, and admission assertions.
//   - Side effects: test-process memory only.
// - Split-When:
//   - Split when another observation schema requires independent fixtures.
// - Merge-When:
//   - Merge when built-in capability schema tests become generated vectors.
// - Summary:
//   - Verifies canonical UTF-8 execution telemetry and pre-effect admission.
// - Description:
//   - Covers exact spans, UTF-8, reserved fields, discovery, and frame shape.
// - Usage:
//   - Composed by the Cargo VM integration-test target.
// - Defaults:
//   - Telemetry is synchronous, result-free, optional observation only.
//

//! Execution telemetry host-capability conformance.

use malbolge::{
    HOST_CAPABILITY_ABI_VERSION, HOST_EXECUTION_TELEMETRY_CAPABILITY_ID,
    HOST_EXECUTION_TELEMETRY_V1_HEADER_SIZE,
    HOST_EXECUTION_TELEMETRY_V1_OPERATION, HOST_EXECUTION_TELEMETRY_V1_VERSION,
    HostCapabilityError, HostCapabilityFrame, HostCapabilityStatus,
    HostExecutionTelemetryV1, decode_host_execution_telemetry_v1,
    encode_host_execution_telemetry_v1, host_execution_telemetry_v1_descriptor,
    validate_host_execution_telemetry_v1_call,
};

use super::{TestResult, check_equal};

const TELEMETRY_VECTOR: [u8; 83] = [
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x35, 0x01, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x41, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x49, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0a, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x43, 0x64, 0x5f, 0x6d, 0x61, 0x69, 0x6e, 0x2e,
    0x63, 0x4d, 0x5f, 0x44, 0x72, 0x61, 0x77, 0x65, 0x72, 0x28, 0x29,
];
const TELEMETRY: HostExecutionTelemetryV1<'static> = HostExecutionTelemetryV1 {
    instruction: "M_Drawer()",
    language: "C",
    location: 309,
    source: "d_main.c",
};

const fn call_frame(
    request_offset: u64,
    request_length: u64,
) -> HostCapabilityFrame {
    HostCapabilityFrame {
        abi_version: HOST_CAPABILITY_ABI_VERSION,
        call_id: 23,
        capability_id: HOST_EXECUTION_TELEMETRY_CAPABILITY_ID,
        capability_version: HOST_EXECUTION_TELEMETRY_V1_VERSION,
        flags: 0,
        operation: HOST_EXECUTION_TELEMETRY_V1_OPERATION,
        request_length,
        request_offset,
        result_capacity: 0,
        result_length: 0,
        result_offset: request_offset,
        status: HostCapabilityStatus::Pending,
    }
}

fn set_byte(bytes: &mut [u8], index: usize, value: u8) -> TestResult {
    let byte = bytes
        .get_mut(index)
        .ok_or_else(|| format!("fixture byte {index} unavailable"))?;
    *byte = value;
    Ok(())
}

#[test]
fn telemetry_payload_matches_canonical_vector() -> TestResult {
    check_equal(
        &HOST_EXECUTION_TELEMETRY_V1_HEADER_SIZE,
        &64,
        "telemetry header size",
    )?;
    check_equal(
        &encode_host_execution_telemetry_v1(TELEMETRY),
        &Ok(TELEMETRY_VECTOR.to_vec()),
        "telemetry exact encoding",
    )?;
    check_equal(
        &decode_host_execution_telemetry_v1(&TELEMETRY_VECTOR),
        &Ok(TELEMETRY),
        "telemetry exact decoding",
    )
}

#[test]
fn telemetry_utf8_roundtrips_without_c_string_semantics() -> TestResult {
    let telemetry = HostExecutionTelemetryV1 {
        instruction: "[j] \u{3bb}",
        language: "MALBOLGE",
        location: 4_782_968,
        source: "\u{3b4}.malbolge",
    };
    let encoded = encode_host_execution_telemetry_v1(telemetry)
        .map_err(|error| format!("telemetry encode: {error}"))?;
    check_equal(
        &decode_host_execution_telemetry_v1(&encoded),
        &Ok(telemetry),
        "UTF-8 telemetry roundtrip",
    )
}

#[test]
fn telemetry_payload_rejects_noncanonical_shape() -> TestResult {
    check_equal(
        &decode_host_execution_telemetry_v1(
            TELEMETRY_VECTOR
                .get(..63)
                .ok_or_else(|| String::from("telemetry prefix unavailable"))?,
        ),
        &Err(HostCapabilityError::InvalidPayload),
        "short telemetry header",
    )?;
    let mut malformed = TELEMETRY_VECTOR;
    set_byte(&mut malformed, 0, 1)?;
    check_equal(
        &decode_host_execution_telemetry_v1(&malformed),
        &Err(HostCapabilityError::InvalidPayload),
        "unknown telemetry flags",
    )?;
    malformed = TELEMETRY_VECTOR;
    set_byte(&mut malformed, 4, 1)?;
    check_equal(
        &decode_host_execution_telemetry_v1(&malformed),
        &Err(HostCapabilityError::InvalidPayload),
        "nonzero telemetry reserved field",
    )?;
    malformed = TELEMETRY_VECTOR;
    set_byte(&mut malformed, 32, 0x42)?;
    check_equal(
        &decode_host_execution_telemetry_v1(&malformed),
        &Err(HostCapabilityError::InvalidPayload),
        "noncanonical span gap",
    )
}

#[test]
fn telemetry_payload_rejects_text_encoding_drift() -> TestResult {
    let mut malformed = TELEMETRY_VECTOR;
    set_byte(&mut malformed, 64, 0)?;
    check_equal(
        &decode_host_execution_telemetry_v1(&malformed),
        &Err(HostCapabilityError::InvalidPayload),
        "embedded NUL telemetry text",
    )?;
    malformed = TELEMETRY_VECTOR;
    set_byte(&mut malformed, 64, 0xff)?;
    check_equal(
        &decode_host_execution_telemetry_v1(&malformed),
        &Err(HostCapabilityError::InvalidPayload),
        "invalid UTF-8 telemetry text",
    )?;
    check_equal(
        &encode_host_execution_telemetry_v1(HostExecutionTelemetryV1 {
            language: "",
            ..TELEMETRY
        }),
        &Err(HostCapabilityError::InvalidPayload),
        "empty language",
    )?;
    check_equal(
        &encode_host_execution_telemetry_v1(HostExecutionTelemetryV1 {
            instruction: "bad\0text",
            ..TELEMETRY
        }),
        &Err(HostCapabilityError::InvalidPayload),
        "NUL instruction",
    )
}

#[test]
fn telemetry_descriptor_has_exact_semantics() -> TestResult {
    let available = host_execution_telemetry_v1_descriptor(true);
    check_equal(
        &available.capability_id,
        &HOST_EXECUTION_TELEMETRY_CAPABILITY_ID,
        "telemetry capability ID",
    )?;
    check_equal(&available.flags, &1, "telemetry available flag")?;
    check_equal(
        &available.minimum_version,
        &HOST_EXECUTION_TELEMETRY_V1_VERSION,
        "telemetry minimum version",
    )?;
    check_equal(
        &available.maximum_version,
        &HOST_EXECUTION_TELEMETRY_V1_VERSION,
        "telemetry maximum version",
    )?;
    check_equal(
        &host_execution_telemetry_v1_descriptor(false).flags,
        &0,
        "telemetry unavailable descriptor",
    )
}

#[test]
fn telemetry_call_admission_is_fail_closed() -> TestResult {
    let registry = [host_execution_telemetry_v1_descriptor(true)];
    let mut memory = vec![0u8; 8 + TELEMETRY_VECTOR.len() + 8];
    memory
        .get_mut(8..8 + TELEMETRY_VECTOR.len())
        .ok_or_else(|| String::from("telemetry memory slot unavailable"))?
        .copy_from_slice(&TELEMETRY_VECTOR);
    let request_length = u64::try_from(TELEMETRY_VECTOR.len())
        .map_err(|error| format!("telemetry vector length: {error}"))?;
    let frame = call_frame(8, request_length);
    check_equal(
        &validate_host_execution_telemetry_v1_call(frame, &memory, &registry),
        &Ok(TELEMETRY),
        "valid telemetry call",
    )?;

    let unavailable = [host_execution_telemetry_v1_descriptor(false)];
    check_equal(
        &validate_host_execution_telemetry_v1_call(
            frame,
            &memory,
            &unavailable,
        ),
        &Err(HostCapabilityError::UnavailableCapability),
        "unavailable telemetry capability",
    )?;

    Ok(())
}

#[test]
fn telemetry_call_rejects_schema_drift() -> TestResult {
    let registry = [host_execution_telemetry_v1_descriptor(true)];
    let mut memory = vec![0u8; 8 + TELEMETRY_VECTOR.len() + 8];
    memory
        .get_mut(8..8 + TELEMETRY_VECTOR.len())
        .ok_or_else(|| String::from("telemetry memory slot unavailable"))?
        .copy_from_slice(&TELEMETRY_VECTOR);
    let request_length = u64::try_from(TELEMETRY_VECTOR.len())
        .map_err(|error| format!("telemetry vector length: {error}"))?;
    let frame = call_frame(8, request_length);
    check_equal(
        &validate_host_execution_telemetry_v1_call(
            HostCapabilityFrame { operation: 1, ..frame },
            &memory,
            &registry,
        ),
        &Err(HostCapabilityError::InvalidPayload),
        "unknown telemetry operation",
    )?;
    let truncated_length = request_length
        .checked_sub(1)
        .ok_or_else(|| String::from("telemetry length underflow"))?;
    check_equal(
        &validate_host_execution_telemetry_v1_call(
            HostCapabilityFrame {
                request_length: truncated_length,
                ..frame
            },
            &memory,
            &registry,
        ),
        &Err(HostCapabilityError::InvalidPayload),
        "truncated telemetry request",
    )?;
    let memory_length = u64::try_from(memory.len())
        .map_err(|error| format!("telemetry memory length: {error}"))?;
    let last_byte = memory_length
        .checked_sub(1)
        .ok_or_else(|| String::from("telemetry memory unexpectedly empty"))?;
    check_equal(
        &validate_host_execution_telemetry_v1_call(
            HostCapabilityFrame {
                result_capacity: 1,
                result_offset: last_byte,
                ..frame
            },
            &memory,
            &registry,
        ),
        &Err(HostCapabilityError::InvalidPayload),
        "telemetry result storage is forbidden",
    )
}
