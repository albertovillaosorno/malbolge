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
//   - Safe-Rust conformance vectors for the host-capability wire ABI.
// - Must-Not:
//   - Call the independent C implementation or perform real host effects.
// - Allows:
//   - Inputs: canonical bytes, semantic registries, and guest memory extents.
//   - Outputs: deterministic equality evidence and rejected malformed vectors.
//   - Side effects: test-process memory only.
// - Split-When:
//   - Split when capability-specific semantic fixtures gain separate ownership.
// - Merge-When:
//   - Merge when another harness owns the same Rust ABI conformance vectors.
// - Summary:
//   - Replays the C-independent canonical capability vectors through Rust.
// - Description:
//   - Proves wire bytes and semantic validation agree without FFI coupling.
// - Usage:
//   - Run by the Cargo VM integration-test target.
// - Defaults:
//   - Version-one little-endian vectors are exact and platform independent.
//

//! Independent safe-Rust vectors for the host-capability ABI.

use malbolge::{
    HOST_CALL_FLAG_NONBLOCKING, HOST_CAPABILITY_ABI_VERSION,
    HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE, HOST_CAPABILITY_FLAG_AVAILABLE,
    HOST_CAPABILITY_FLAG_MAY_BLOCK, HOST_CAPABILITY_FLAG_PARTIAL_PROGRESS,
    HOST_CAPABILITY_FRAME_WIRE_SIZE, HOST_CAPABILITY_SPAN_WIRE_SIZE,
    HostCapabilityDescriptor, HostCapabilityError, HostCapabilityFrame,
    HostCapabilityResponseBuffers, HostCapabilitySpan, HostCapabilityStatus,
    commit_host_capability_response, discover_host_capability,
    discover_host_capability_wire, validate_host_capability_registry,
    validate_host_capability_response, validate_host_capability_wire_registry,
};

use super::{TestResult, check_equal};

const FRAME_VECTOR: [u8; HOST_CAPABILITY_FRAME_WIRE_SIZE] = [
    0x4d, 0x42, 0x48, 0x43, 0x01, 0x00, 0x48, 0x00, 0x04, 0x03, 0x02, 0x01,
    0x06, 0x05, 0x08, 0x07, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x18, 0x17, 0x16, 0x15, 0x14, 0x13, 0x12, 0x11, 0x28, 0x27, 0x26, 0x25,
    0x24, 0x23, 0x22, 0x21, 0x38, 0x37, 0x36, 0x35, 0x34, 0x33, 0x32, 0x31,
    0x48, 0x47, 0x46, 0x45, 0x44, 0x43, 0x42, 0x41, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x58, 0x57, 0x56, 0x55, 0x54, 0x53, 0x52, 0x51,
];
const DESCRIPTOR_VECTOR: [u8; HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE] = [
    0x04, 0x03, 0x02, 0x01, 0x01, 0x00, 0x03, 0x00, 0x07, 0x00, 0x00, 0x00,
    0x01, 0x00, 0x10, 0x00,
];
const SPAN_VECTOR: [u8; HOST_CAPABILITY_SPAN_WIRE_SIZE] = [
    0x18, 0x17, 0x16, 0x15, 0x14, 0x13, 0x12, 0x11, 0x28, 0x27, 0x26, 0x25,
    0x24, 0x23, 0x22, 0x21,
];
const REGISTRY_VECTOR: [u8; 3 * HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE] = [
    0x00, 0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0x00,
    0x01, 0x00, 0x10, 0x00, 0x00, 0x02, 0x00, 0x00, 0x01, 0x00, 0x02, 0x00,
    0x07, 0x00, 0x00, 0x00, 0x01, 0x00, 0x10, 0x00, 0x00, 0x03, 0x00, 0x00,
    0x01, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x10, 0x00,
];
const CAPABILITY_100: HostCapabilityDescriptor = HostCapabilityDescriptor {
    capability_id: 0x0000_0100,
    minimum_version: 1,
    maximum_version: 1,
    flags: HOST_CAPABILITY_FLAG_AVAILABLE,
};
const CAPABILITY_200: HostCapabilityDescriptor = HostCapabilityDescriptor {
    capability_id: 0x0000_0200,
    minimum_version: 1,
    maximum_version: 2,
    flags: HOST_CAPABILITY_FLAG_AVAILABLE
        | HOST_CAPABILITY_FLAG_MAY_BLOCK
        | HOST_CAPABILITY_FLAG_PARTIAL_PROGRESS,
};
const CAPABILITY_300: HostCapabilityDescriptor = HostCapabilityDescriptor {
    capability_id: 0x0000_0300,
    minimum_version: 1,
    maximum_version: 1,
    flags: 0,
};
const REGISTRY: [HostCapabilityDescriptor; 3] =
    [CAPABILITY_100, CAPABILITY_200, CAPABILITY_300];

const fn base_request(capability_id: u32) -> HostCapabilityFrame {
    HostCapabilityFrame {
        abi_version: HOST_CAPABILITY_ABI_VERSION,
        capability_id,
        capability_version: 1,
        operation: 7,
        flags: 0,
        status: HostCapabilityStatus::Pending,
        request_offset: 8,
        request_length: 8,
        result_offset: 32,
        result_capacity: 16,
        result_length: 0,
        call_id: 99,
    }
}

#[test]
fn canonical_frame_bytes_match_independent_c_vector() -> TestResult {
    let frame = HostCapabilityFrame {
        abi_version: HOST_CAPABILITY_ABI_VERSION,
        capability_id: 0x0102_0304,
        capability_version: 0x0506,
        operation: 0x0708,
        flags: HOST_CALL_FLAG_NONBLOCKING,
        status: HostCapabilityStatus::Pending,
        request_offset: 0x1112_1314_1516_1718,
        request_length: 0x2122_2324_2526_2728,
        result_offset: 0x3132_3334_3536_3738,
        result_capacity: 0x4142_4344_4546_4748,
        result_length: 0,
        call_id: 0x5152_5354_5556_5758,
    };
    check_equal(&frame.encode(), &Ok(FRAME_VECTOR), "frame encoding")?;
    check_equal(
        &HostCapabilityFrame::decode(&FRAME_VECTOR),
        &Ok(frame),
        "frame decoding",
    )
}

#[test]
fn frame_header_drift_fails_closed() -> TestResult {
    let mut malformed = FRAME_VECTOR;
    let first = malformed
        .first_mut()
        .ok_or_else(|| String::from("frame vector unexpectedly empty"))?;
    *first ^= 1;
    check_equal(
        &HostCapabilityFrame::decode(&malformed),
        &Err(HostCapabilityError::InvalidWireFrame),
        "frame magic rejection",
    )?;
    check_equal(
        &HostCapabilityFrame::decode(
            FRAME_VECTOR
                .get(..71)
                .ok_or_else(|| String::from("frame prefix unavailable"))?,
        ),
        &Err(HostCapabilityError::InvalidWireFrame),
        "frame length rejection",
    )?;

    malformed = FRAME_VECTOR;
    let size = malformed
        .get_mut(6)
        .ok_or_else(|| String::from("frame vector missing size byte"))?;
    *size = 71;
    check_equal(
        &HostCapabilityFrame::decode(&malformed),
        &Err(HostCapabilityError::InvalidWireFrame),
        "frame wire size rejection",
    )?;

    malformed = FRAME_VECTOR;
    let version = malformed
        .get_mut(4)
        .ok_or_else(|| String::from("frame vector missing ABI version byte"))?;
    *version = 2;
    check_equal(
        &HostCapabilityFrame::decode(&malformed),
        &Err(HostCapabilityError::UnsupportedAbiVersion),
        "frame ABI version rejection",
    )?;

    malformed = FRAME_VECTOR;
    let capability_id = malformed
        .get_mut(8..12)
        .ok_or_else(|| String::from("frame vector missing capability ID"))?;
    capability_id.copy_from_slice(&0u32.to_le_bytes());
    check_equal(
        &HostCapabilityFrame::decode(&malformed),
        &Err(HostCapabilityError::InvalidWireFrame),
        "reserved capability ID rejection",
    )
}

#[test]
fn future_abi_rejects_before_v1_payload_interpretation() -> TestResult {
    let mut future_frame = [0u8; 80];
    let frame_prefix = future_frame
        .get_mut(..FRAME_VECTOR.len())
        .ok_or_else(|| String::from("future frame prefix unavailable"))?;
    frame_prefix.copy_from_slice(&FRAME_VECTOR);
    let frame_version = future_frame
        .get_mut(4..6)
        .ok_or_else(|| String::from("future frame version unavailable"))?;
    frame_version.copy_from_slice(&2u16.to_le_bytes());
    let status = future_frame
        .get_mut(20..24)
        .ok_or_else(|| String::from("future frame status unavailable"))?;
    status.copy_from_slice(&u32::MAX.to_le_bytes());
    check_equal(
        &HostCapabilityFrame::decode(&future_frame),
        &Err(HostCapabilityError::UnsupportedAbiVersion),
        "future frame version precedence",
    )?;

    let mut future_descriptor = [0u8; 20];
    let descriptor_prefix = future_descriptor
        .get_mut(..DESCRIPTOR_VECTOR.len())
        .ok_or_else(|| String::from("future descriptor prefix unavailable"))?;
    descriptor_prefix.copy_from_slice(&DESCRIPTOR_VECTOR);
    let descriptor_version = future_descriptor
        .get_mut(12..14)
        .ok_or_else(|| String::from("future descriptor version unavailable"))?;
    descriptor_version.copy_from_slice(&2u16.to_le_bytes());
    check_equal(
        &HostCapabilityDescriptor::decode(&future_descriptor),
        &Err(HostCapabilityError::UnsupportedAbiVersion),
        "future descriptor version precedence",
    )
}

#[test]
fn status_wire_values_are_stable() -> TestResult {
    let cases = [
        (0u32, HostCapabilityStatus::Pending),
        (1u32, HostCapabilityStatus::Complete),
        (2u32, HostCapabilityStatus::Partial),
        (3u32, HostCapabilityStatus::WouldBlock),
        (4u32, HostCapabilityStatus::HostError),
        (5u32, HostCapabilityStatus::Cancelled),
    ];
    for (wire_value, expected) in cases {
        let mut wire = FRAME_VECTOR;
        let status_bytes = wire
            .get_mut(20..24)
            .ok_or_else(|| String::from("frame vector missing status field"))?;
        status_bytes.copy_from_slice(&wire_value.to_le_bytes());
        let decoded_status =
            HostCapabilityFrame::decode(&wire).map(|frame| frame.status);
        check_equal(&decoded_status, &Ok(expected), "wire status mapping")?;
    }

    let mut malformed = FRAME_VECTOR;
    let status_bytes = malformed
        .get_mut(20..24)
        .ok_or_else(|| String::from("frame vector missing status field"))?;
    status_bytes.copy_from_slice(&u32::MAX.to_le_bytes());
    check_equal(
        &HostCapabilityFrame::decode(&malformed),
        &Err(HostCapabilityError::InvalidStatus),
        "unknown wire status",
    )
}

#[test]
fn canonical_payload_span_matches_independent_c_vector() -> TestResult {
    let span = HostCapabilitySpan {
        length: 0x2122_2324_2526_2728,
        offset: 0x1112_1314_1516_1718,
    };
    check_equal(&span.encode(), &SPAN_VECTOR, "span encoding")?;
    check_equal(
        &HostCapabilitySpan::decode(&SPAN_VECTOR),
        &Ok(span),
        "span decoding",
    )?;
    check_equal(
        &HostCapabilitySpan::decode(
            SPAN_VECTOR
                .get(..15)
                .ok_or_else(|| String::from("span prefix unavailable"))?,
        ),
        &Err(HostCapabilityError::InvalidPayload),
        "span length rejection",
    )
}

#[test]
fn payload_span_bounds_are_relative_and_overflow_safe() -> TestResult {
    let mut record = [0u8; 64];
    for (index, byte) in record.iter_mut().enumerate() {
        *byte = u8::try_from(index)
            .map_err(|error| format!("record byte {index}: {error}"))?;
    }
    let span = HostCapabilitySpan { length: 4, offset: 16 };
    check_equal(&span.validate(64, 16), &Ok(()), "span bounds")?;
    check_equal(
        &span.bytes(&record, 16),
        &Ok(record
            .get(16..20)
            .ok_or_else(|| String::from("record fixture span unavailable"))?),
        "span bytes",
    )?;
    check_equal(
        &HostCapabilitySpan { length: 0, offset: 64 }.validate(64, 16),
        &Ok(()),
        "empty end span",
    )?;
    check_equal(
        &HostCapabilitySpan { length: 1, offset: 15 }.validate(64, 16),
        &Err(HostCapabilityError::InvalidPayload),
        "span enters fixed header",
    )?;
    check_equal(
        &HostCapabilitySpan { length: 0, offset: 65 }.validate(64, 16),
        &Err(HostCapabilityError::InvalidPayload),
        "empty span beyond record",
    )?;
    check_equal(
        &HostCapabilitySpan {
            length: 1,
            offset: u64::MAX,
        }
        .validate(u64::MAX, 16),
        &Err(HostCapabilityError::InvalidPayload),
        "overflowing span",
    )?;
    check_equal(
        &span.validate(8, 16),
        &Err(HostCapabilityError::InvalidArgument),
        "schema header exceeds record",
    )
}

#[test]
fn canonical_descriptor_bytes_match_independent_c_vector() -> TestResult {
    let descriptor = HostCapabilityDescriptor {
        capability_id: 0x0102_0304,
        minimum_version: 1,
        maximum_version: 3,
        flags: HOST_CAPABILITY_FLAG_AVAILABLE
            | HOST_CAPABILITY_FLAG_MAY_BLOCK
            | HOST_CAPABILITY_FLAG_PARTIAL_PROGRESS,
    };
    check_equal(
        &descriptor.encode(),
        &Ok(DESCRIPTOR_VECTOR),
        "descriptor encoding",
    )?;
    check_equal(
        &HostCapabilityDescriptor::decode(&DESCRIPTOR_VECTOR),
        &Ok(descriptor),
        "descriptor decoding",
    )?;

    let mut malformed = DESCRIPTOR_VECTOR;
    let version = malformed.get_mut(12).ok_or_else(|| {
        String::from("descriptor vector missing ABI version byte")
    })?;
    *version = 2;
    check_equal(
        &HostCapabilityDescriptor::decode(&malformed),
        &Err(HostCapabilityError::UnsupportedAbiVersion),
        "descriptor ABI version",
    )?;

    malformed = DESCRIPTOR_VECTOR;
    let size = malformed
        .get_mut(14)
        .ok_or_else(|| String::from("descriptor vector missing size byte"))?;
    *size = 15;
    check_equal(
        &HostCapabilityDescriptor::decode(&malformed),
        &Err(HostCapabilityError::InvalidWireFrame),
        "descriptor wire size",
    )
}

#[test]
fn registry_discovery_distinguishes_failure_classes() -> TestResult {
    check_equal(
        &validate_host_capability_registry(&REGISTRY),
        &Ok(()),
        "registry validation",
    )?;
    check_equal(
        &discover_host_capability(&REGISTRY, 0x0000_0200, 2),
        &Ok(CAPABILITY_200),
        "registry version discovery",
    )?;
    check_equal(
        &discover_host_capability(&REGISTRY, 0x0000_0200, 3),
        &Err(HostCapabilityError::UnsupportedCapabilityVersion),
        "unsupported capability version",
    )?;
    check_equal(
        &discover_host_capability(&REGISTRY, 0x0000_0280, 1),
        &Err(HostCapabilityError::UnknownCapability),
        "unknown capability",
    )?;
    check_equal(
        &discover_host_capability(&REGISTRY, 0x0000_0300, 1),
        &Err(HostCapabilityError::UnavailableCapability),
        "unavailable capability",
    )?;
    check_equal(
        &discover_host_capability(&REGISTRY, 0x0000_0100, 0),
        &Err(HostCapabilityError::InvalidArgument),
        "zero discovery version",
    )?;

    let duplicate = [CAPABILITY_100, CAPABILITY_100];
    check_equal(
        &validate_host_capability_registry(&duplicate),
        &Err(HostCapabilityError::InvalidRegistry),
        "duplicate capability identity",
    )?;
    let descending = [CAPABILITY_200, CAPABILITY_100];
    check_equal(
        &validate_host_capability_registry(&descending),
        &Err(HostCapabilityError::InvalidRegistry),
        "descending registry identity",
    )
}

#[test]
fn serialized_registry_is_directly_discoverable() -> TestResult {
    check_equal(
        &validate_host_capability_wire_registry(&REGISTRY_VECTOR),
        &Ok(()),
        "serialized registry validation",
    )?;
    check_equal(
        &discover_host_capability_wire(&REGISTRY_VECTOR, 0x0000_0200, 2),
        &Ok(CAPABILITY_200),
        "serialized registry discovery",
    )?;
    check_equal(
        &validate_host_capability_wire_registry(
            REGISTRY_VECTOR
                .get(..REGISTRY_VECTOR.len() - 1)
                .ok_or_else(|| String::from("registry prefix unavailable"))?,
        ),
        &Err(HostCapabilityError::InvalidWireFrame),
        "serialized registry trailing byte",
    )?;

    let mut duplicate = REGISTRY_VECTOR;
    let first = duplicate
        .get(..HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE)
        .ok_or_else(|| String::from("first registry descriptor unavailable"))?
        .to_vec();
    let second = duplicate
        .get_mut(
            HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE
                ..2 * HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE,
        )
        .ok_or_else(|| {
            String::from("second registry descriptor unavailable")
        })?;
    second.copy_from_slice(&first);
    check_equal(
        &validate_host_capability_wire_registry(&duplicate),
        &Err(HostCapabilityError::InvalidRegistry),
        "serialized duplicate identity",
    )
}

#[test]
fn serialized_registry_preserves_future_version_diagnostic() -> TestResult {
    let mut future_registry = [0u8; 36];
    let first = future_registry
        .get_mut(..HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE)
        .ok_or_else(|| {
            String::from("future registry first record unavailable")
        })?;
    first.copy_from_slice(
        REGISTRY_VECTOR
            .get(..HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE)
            .ok_or_else(|| String::from("registry first record unavailable"))?,
    );
    let future = future_registry
        .get_mut(HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE..32)
        .ok_or_else(|| String::from("future registry record unavailable"))?;
    future.copy_from_slice(&DESCRIPTOR_VECTOR);
    let future_version = future_registry
        .get_mut(28..30)
        .ok_or_else(|| String::from("future registry version unavailable"))?;
    future_version.copy_from_slice(&2u16.to_le_bytes());
    check_equal(
        &validate_host_capability_wire_registry(&future_registry),
        &Err(HostCapabilityError::UnsupportedAbiVersion),
        "future registry descriptor version",
    )?;
    check_equal(
        &discover_host_capability_wire(&future_registry, 0x0000_0100, 1),
        &Err(HostCapabilityError::UnsupportedAbiVersion),
        "discovery validates future later descriptor",
    )
}

#[test]
fn request_ranges_are_overflow_safe_and_nonoverlapping() -> TestResult {
    let mut request = base_request(0x0000_0100);
    check_equal(
        &request.validate_request(64, &REGISTRY),
        &Ok(()),
        "baseline request",
    )?;

    request.flags = HOST_CALL_FLAG_NONBLOCKING;
    check_equal(
        &request.validate_request(64, &REGISTRY),
        &Err(HostCapabilityError::InvalidStatus),
        "nonblocking flag requires may-block capability",
    )?;
    request = base_request(0x0000_0200);
    request.flags = HOST_CALL_FLAG_NONBLOCKING;
    check_equal(
        &request.validate_request(64, &REGISTRY),
        &Ok(()),
        "may-block capability accepts nonblocking flag",
    )?;
    request = base_request(0x0000_0100);

    request.result_offset = 16;
    check_equal(
        &request.validate_request(64, &REGISTRY),
        &Ok(()),
        "adjacent request and result ranges",
    )?;
    request.result_offset = 15;
    check_equal(
        &request.validate_request(64, &REGISTRY),
        &Err(HostCapabilityError::InvalidRange),
        "overlapping request and result ranges",
    )?;

    request = base_request(0x0000_0100);
    request.request_offset = 64;
    request.request_length = 0;
    request.result_offset = 64;
    request.result_capacity = 0;
    check_equal(
        &request.validate_request(64, &REGISTRY),
        &Ok(()),
        "zero-length end ranges",
    )?;
    request.request_offset = 65;
    check_equal(
        &request.validate_request(64, &REGISTRY),
        &Err(HostCapabilityError::InvalidRange),
        "range starts past guest end",
    )?;

    request = base_request(0x0000_0100);
    request.request_offset = u64::MAX;
    request.request_length = 1;
    check_equal(
        &request.validate_request(u64::MAX, &REGISTRY),
        &Err(HostCapabilityError::InvalidRange),
        "overflowing request range",
    )
}

#[test]
fn staged_response_publication_is_atomic() -> TestResult {
    let request = base_request(0x0000_0100);
    let response = HostCapabilityFrame {
        result_length: 4,
        status: HostCapabilityStatus::Complete,
        ..request
    };
    let staged = [1u8, 2, 3, 4];
    let mut memory = [0xa5u8; 64];
    check_equal(
        &commit_host_capability_response(
            request,
            response,
            &REGISTRY,
            HostCapabilityResponseBuffers {
                guest_memory: &mut memory,
                staged_result: &staged,
            },
        ),
        &Ok(()),
        "valid staged publication",
    )?;
    check_equal(
        &memory.get(32..36),
        &Some(staged.as_slice()),
        "published result bytes",
    )?;

    memory.fill(0xa5);
    let baseline = memory;
    let invalid = HostCapabilityFrame { call_id: 100, ..response };
    check_equal(
        &commit_host_capability_response(
            request,
            invalid,
            &REGISTRY,
            HostCapabilityResponseBuffers {
                guest_memory: &mut memory,
                staged_result: &staged,
            },
        ),
        &Err(HostCapabilityError::InvalidResponse),
        "invalid response publication",
    )?;
    check_equal(&memory, &baseline, "invalid response is atomic")?;
    check_equal(
        &commit_host_capability_response(
            request,
            response,
            &REGISTRY,
            HostCapabilityResponseBuffers {
                guest_memory: &mut memory,
                staged_result: staged
                    .get(..3)
                    .ok_or_else(|| String::from("staged prefix missing"))?,
            },
        ),
        &Err(HostCapabilityError::InvalidResponse),
        "staged length mismatch",
    )?;
    check_equal(&memory, &baseline, "length mismatch is atomic")
}

#[test]
fn response_identity_fields_are_immutable() -> TestResult {
    let request = base_request(0x0000_0100);
    let response = HostCapabilityFrame {
        status: HostCapabilityStatus::Complete,
        ..request
    };
    let mutations = [
        ("capability ID", HostCapabilityFrame {
            capability_id: 0x200,
            ..response
        }),
        ("capability version", HostCapabilityFrame {
            capability_version: 2,
            ..response
        }),
        ("operation", HostCapabilityFrame {
            operation: 8,
            ..response
        }),
        ("flags", HostCapabilityFrame {
            flags: HOST_CALL_FLAG_NONBLOCKING,
            ..response
        }),
        ("request offset", HostCapabilityFrame {
            request_offset: 9,
            ..response
        }),
        ("request length", HostCapabilityFrame {
            request_length: 7,
            ..response
        }),
        ("result offset", HostCapabilityFrame {
            result_offset: 33,
            ..response
        }),
        ("result capacity", HostCapabilityFrame {
            result_capacity: 15,
            ..response
        }),
        ("call ID", HostCapabilityFrame { call_id: 100, ..response }),
    ];
    for (field, mutated) in mutations {
        check_equal(
            &validate_host_capability_response(request, mutated, 64, &REGISTRY),
            &Err(HostCapabilityError::InvalidResponse),
            field,
        )?;
    }
    Ok(())
}

#[test]
fn response_status_obeys_declared_capability_behavior() -> TestResult {
    let mut request = base_request(0x0000_0200);
    let mut response = request;
    response.status = HostCapabilityStatus::Complete;
    response.result_length = 16;
    check_equal(
        &validate_host_capability_response(request, response, 64, &REGISTRY),
        &Ok(()),
        "complete response",
    )?;

    response = request;
    response.status = HostCapabilityStatus::Partial;
    response.result_length = 8;
    check_equal(
        &validate_host_capability_response(request, response, 64, &REGISTRY),
        &Ok(()),
        "declared partial response",
    )?;
    response.result_length = 0;
    check_equal(
        &validate_host_capability_response(request, response, 64, &REGISTRY),
        &Err(HostCapabilityError::InvalidResponse),
        "zero-progress partial response",
    )?;

    request.flags = HOST_CALL_FLAG_NONBLOCKING;
    response = request;
    response.status = HostCapabilityStatus::WouldBlock;
    check_equal(
        &validate_host_capability_response(request, response, 64, &REGISTRY),
        &Ok(()),
        "declared nonblocking would-block response",
    )?;
    request.flags = 0;
    response = request;
    response.status = HostCapabilityStatus::WouldBlock;
    check_equal(
        &validate_host_capability_response(request, response, 64, &REGISTRY),
        &Err(HostCapabilityError::InvalidResponse),
        "blocking request cannot return would-block",
    )?;

    request = base_request(0x0000_0100);
    request.flags = HOST_CALL_FLAG_NONBLOCKING;
    response = request;
    response.status = HostCapabilityStatus::WouldBlock;
    check_equal(
        &validate_host_capability_response(request, response, 64, &REGISTRY),
        &Err(HostCapabilityError::InvalidStatus),
        "invalid request fails before response behavior",
    )?;

    request = base_request(0x0000_0100);
    response = request;
    response.status = HostCapabilityStatus::Complete;
    response.call_id = response.call_id.saturating_add(1);
    check_equal(
        &validate_host_capability_response(request, response, 64, &REGISTRY),
        &Err(HostCapabilityError::InvalidResponse),
        "response identity mutation",
    )
}
