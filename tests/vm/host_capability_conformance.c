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
//   - Independent C conformance vectors for the host-capability wire ABI.
// - Must-Not:
//   - Perform real host effects or depend on one platform transport.
// - Allows:
//   - Inputs: canonical frame bytes, registries, and guest memory extents.
//   - Outputs: process exit status indicating deterministic conformance.
//   - Side effects: test-process memory only.
// - Split-When:
//   - Split when capability-specific semantic fixtures gain separate ownership.
// - Merge-When:
//   - Merge when another harness owns the same canonical ABI vectors.
// - Summary:
//   - Exercises frame encoding, discovery, ranges, and response semantics.
// - Description:
//   - Rejects malformed ABI inputs before any transport-specific behavior.
// - Usage:
//   - Compile with the canonical C capability implementation and run directly.
// - Defaults:
//   - Version-one little-endian vectors are exact and platform independent.
//

//! Conformance harness for the version-one host-capability call ABI.

#include "malbolge_host_capability.h"

#include <stddef.h>
#include <stdint.h>
#include <string.h>

static const MalbolgeHostCapabilityDescriptor REGISTRY[] = {
    {UINT32_C(0x00000100), 1U, 1U,
     MALBOLGE_HOST_CAPABILITY_FLAG_AVAILABLE},
    {UINT32_C(0x00000200), 1U, 2U,
     MALBOLGE_HOST_CAPABILITY_FLAG_AVAILABLE |
         MALBOLGE_HOST_CAPABILITY_FLAG_MAY_BLOCK |
         MALBOLGE_HOST_CAPABILITY_FLAG_PARTIAL_PROGRESS},
    {UINT32_C(0x00000300), 1U, 1U, 0U},
};

static int expect_true(int condition)
{
    return condition != 0 ? 0 : 1;
}

static int expect_validation(MalbolgeHostCapabilityValidation actual,
                             MalbolgeHostCapabilityValidation expected)
{
    return expect_true(actual == expected);
}

static int bytes_are(uint8_t const *bytes, size_t length, uint8_t expected)
{
    size_t index = 0U;
    for (index = 0U; index < length; ++index) {
        if (bytes[index] != expected) {
            return 0;
        }
    }
    return 1;
}

static MalbolgeHostCapabilityFrame base_request(uint32_t capability_id)
{
    MalbolgeHostCapabilityFrame frame = {
        MALBOLGE_HOST_CAPABILITY_ABI_VERSION,
        capability_id,
        1U,
        7U,
        0U,
        MALBOLGE_HOST_CAPABILITY_STATUS_PENDING,
        UINT64_C(8),
        UINT64_C(8),
        UINT64_C(32),
        UINT64_C(16),
        0U,
        UINT64_C(99),
    };
    return frame;
}

static int frame_equal(const MalbolgeHostCapabilityFrame *left,
                       const MalbolgeHostCapabilityFrame *right)
{
    return left->abi_version == right->abi_version &&
           left->capability_id == right->capability_id &&
           left->capability_version == right->capability_version &&
           left->operation == right->operation &&
           left->flags == right->flags && left->status == right->status &&
           left->request_offset == right->request_offset &&
           left->request_length == right->request_length &&
           left->result_offset == right->result_offset &&
           left->result_capacity == right->result_capacity &&
           left->result_length == right->result_length &&
           left->call_id == right->call_id;
}

static int span_equal(const MalbolgeHostCapabilitySpan *left,
                      const MalbolgeHostCapabilitySpan *right)
{
    return left->offset == right->offset && left->length == right->length;
}

static int descriptor_equal(const MalbolgeHostCapabilityDescriptor *left,
                            const MalbolgeHostCapabilityDescriptor *right)
{
    return left->capability_id == right->capability_id &&
           left->minimum_version == right->minimum_version &&
           left->maximum_version == right->maximum_version &&
           left->flags == right->flags;
}

static int test_frame_codec(void)
{
    static const uint8_t EXPECTED[MALBOLGE_HOST_CAPABILITY_FRAME_WIRE_SIZE] = {
        0x4d, 0x42, 0x48, 0x43, 0x01, 0x00, 0x48, 0x00,
        0x04, 0x03, 0x02, 0x01, 0x06, 0x05, 0x08, 0x07,
        0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x18, 0x17, 0x16, 0x15, 0x14, 0x13, 0x12, 0x11,
        0x28, 0x27, 0x26, 0x25, 0x24, 0x23, 0x22, 0x21,
        0x38, 0x37, 0x36, 0x35, 0x34, 0x33, 0x32, 0x31,
        0x48, 0x47, 0x46, 0x45, 0x44, 0x43, 0x42, 0x41,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x58, 0x57, 0x56, 0x55, 0x54, 0x53, 0x52, 0x51,
    };
    MalbolgeHostCapabilityFrame frame = {
        MALBOLGE_HOST_CAPABILITY_ABI_VERSION,
        UINT32_C(0x01020304),
        UINT16_C(0x0506),
        UINT16_C(0x0708),
        MALBOLGE_HOST_CALL_FLAG_NONBLOCKING,
        MALBOLGE_HOST_CAPABILITY_STATUS_PENDING,
        UINT64_C(0x1112131415161718),
        UINT64_C(0x2122232425262728),
        UINT64_C(0x3132333435363738),
        UINT64_C(0x4142434445464748),
        0U,
        UINT64_C(0x5152535455565758),
    };
    union FrameAlias {
        MalbolgeHostCapabilityFrame frame;
        uint8_t bytes[MALBOLGE_HOST_CAPABILITY_FRAME_WIRE_SIZE];
    } alias = {0};
    MalbolgeHostCapabilityFrame decoded = {0};
    const MalbolgeHostCapabilityStatus statuses[] = {
        MALBOLGE_HOST_CAPABILITY_STATUS_PENDING,
        MALBOLGE_HOST_CAPABILITY_STATUS_COMPLETE,
        MALBOLGE_HOST_CAPABILITY_STATUS_PARTIAL,
        MALBOLGE_HOST_CAPABILITY_STATUS_WOULD_BLOCK,
        MALBOLGE_HOST_CAPABILITY_STATUS_HOST_ERROR,
        MALBOLGE_HOST_CAPABILITY_STATUS_CANCELLED,
    };
    MalbolgeHostCapabilityFrame invalid_frame;
    uint8_t wire[MALBOLGE_HOST_CAPABILITY_FRAME_WIRE_SIZE] = {0};
    size_t status_index = 0U;
    int failures = 0;

    failures += expect_validation(
        malbolge_host_capability_encode_frame(&frame, wire, sizeof(wire)),
        MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_true(memcmp(wire, EXPECTED, sizeof(wire)) == 0);
    failures += expect_validation(
        malbolge_host_capability_decode_frame(wire, sizeof(wire), &decoded),
        MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_true(frame_equal(&frame, &decoded));

    for (status_index = 0U;
         status_index < sizeof(statuses) / sizeof(statuses[0]);
         ++status_index) {
        memcpy(wire, EXPECTED, sizeof(wire));
        wire[20] = (uint8_t)status_index;
        failures += expect_validation(
            malbolge_host_capability_decode_frame(
                wire, sizeof(wire), &decoded),
            MALBOLGE_HOST_CAPABILITY_VALID);
        failures += expect_true(decoded.status == statuses[status_index]);
    }
    decoded = frame;
    memcpy(wire, EXPECTED, sizeof(wire));

    alias.frame = frame;
    failures += expect_validation(
        malbolge_host_capability_encode_frame(
            &alias.frame, alias.bytes,
            MALBOLGE_HOST_CAPABILITY_FRAME_WIRE_SIZE),
        MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_true(
        memcmp(alias.bytes, EXPECTED, sizeof(EXPECTED)) == 0);
    memcpy(alias.bytes, EXPECTED, sizeof(EXPECTED));
    failures += expect_validation(
        malbolge_host_capability_decode_frame(
            alias.bytes, MALBOLGE_HOST_CAPABILITY_FRAME_WIRE_SIZE,
            &alias.frame),
        MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_true(frame_equal(&frame, &alias.frame));

    invalid_frame = frame;
    invalid_frame.result_length = 1U;
    memset(wire, 0xa5, sizeof(wire));
    failures += expect_validation(
        malbolge_host_capability_encode_frame(
            &invalid_frame, wire, sizeof(wire)),
        MALBOLGE_HOST_CAPABILITY_INVALID_STATUS);
    failures += expect_true(bytes_are(wire, sizeof(wire), UINT8_C(0xa5)));
    memcpy(wire, EXPECTED, sizeof(wire));

    failures += expect_validation(
        malbolge_host_capability_encode_frame(NULL, wire, sizeof(wire)),
        MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT);
    failures += expect_validation(
        malbolge_host_capability_encode_frame(&frame, NULL, sizeof(wire)),
        MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT);
    failures += expect_validation(
        malbolge_host_capability_encode_frame(&frame, wire,
                                              sizeof(wire) - 1U),
        MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT);
    failures += expect_validation(
        malbolge_host_capability_decode_frame(NULL, sizeof(wire), &decoded),
        MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT);
    failures += expect_validation(
        malbolge_host_capability_decode_frame(wire, sizeof(wire), NULL),
        MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT);
    failures += expect_validation(
        malbolge_host_capability_decode_frame(wire, sizeof(wire) - 1U,
                                              &decoded),
        MALBOLGE_HOST_CAPABILITY_INVALID_WIRE_FRAME);

    wire[0] ^= UINT8_C(1);
    failures += expect_validation(
        malbolge_host_capability_decode_frame(wire, sizeof(wire), &decoded),
        MALBOLGE_HOST_CAPABILITY_INVALID_WIRE_FRAME);
    failures += expect_true(frame_equal(&frame, &decoded));
    wire[0] ^= UINT8_C(1);
    wire[6] = UINT8_C(71);
    failures += expect_validation(
        malbolge_host_capability_decode_frame(wire, sizeof(wire), &decoded),
        MALBOLGE_HOST_CAPABILITY_INVALID_WIRE_FRAME);
    failures += expect_true(frame_equal(&frame, &decoded));

    memcpy(wire, EXPECTED, sizeof(wire));
    wire[20] = UINT8_C(0xff);
    wire[21] = UINT8_C(0xff);
    wire[22] = UINT8_C(0xff);
    wire[23] = UINT8_C(0xff);
    failures += expect_validation(
        malbolge_host_capability_decode_frame(wire, sizeof(wire), &decoded),
        MALBOLGE_HOST_CAPABILITY_INVALID_STATUS);
    failures += expect_true(frame_equal(&frame, &decoded));

    memcpy(wire, EXPECTED, sizeof(wire));
    wire[4] = UINT8_C(2);
    failures += expect_validation(
        malbolge_host_capability_decode_frame(wire, sizeof(wire), &decoded),
        MALBOLGE_HOST_CAPABILITY_UNSUPPORTED_ABI_VERSION);
    failures += expect_true(frame_equal(&frame, &decoded));
    return failures;
}

static int test_payload_span(void)
{
    static const uint8_t EXPECTED[MALBOLGE_HOST_CAPABILITY_SPAN_WIRE_SIZE] = {
        0x18, 0x17, 0x16, 0x15, 0x14, 0x13, 0x12, 0x11,
        0x28, 0x27, 0x26, 0x25, 0x24, 0x23, 0x22, 0x21,
    };
    const MalbolgeHostCapabilitySpan span = {
        UINT64_C(0x1112131415161718),
        UINT64_C(0x2122232425262728),
    };
    union SpanAlias {
        MalbolgeHostCapabilitySpan span;
        uint8_t bytes[MALBOLGE_HOST_CAPABILITY_SPAN_WIRE_SIZE];
    } alias = {0};
    MalbolgeHostCapabilitySpan decoded = {
        UINT64_C(0xaaaaaaaaaaaaaaaa),
        UINT64_C(0xbbbbbbbbbbbbbbbb),
    };
    const MalbolgeHostCapabilitySpan sentinel = decoded;
    uint8_t wire[MALBOLGE_HOST_CAPABILITY_SPAN_WIRE_SIZE] = {0};
    int failures = 0;

    failures += expect_validation(
        malbolge_host_capability_encode_span(&span, wire, sizeof(wire)),
        MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_true(memcmp(wire, EXPECTED, sizeof(wire)) == 0);
    failures += expect_validation(
        malbolge_host_capability_decode_span(wire, sizeof(wire), &decoded),
        MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_true(span_equal(&span, &decoded));

    alias.span = span;
    failures += expect_validation(
        malbolge_host_capability_encode_span(
            &alias.span, alias.bytes, MALBOLGE_HOST_CAPABILITY_SPAN_WIRE_SIZE),
        MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_true(
        memcmp(alias.bytes, EXPECTED, sizeof(EXPECTED)) == 0);
    memcpy(alias.bytes, EXPECTED, sizeof(EXPECTED));
    failures += expect_validation(
        malbolge_host_capability_decode_span(
            alias.bytes, MALBOLGE_HOST_CAPABILITY_SPAN_WIRE_SIZE, &alias.span),
        MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_true(span_equal(&span, &alias.span));

    decoded = sentinel;
    failures += expect_validation(
        malbolge_host_capability_decode_span(
            wire, sizeof(wire) - 1U, &decoded),
        MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD);
    failures += expect_true(span_equal(&decoded, &sentinel));
    failures += expect_validation(
        malbolge_host_capability_encode_span(
            &span, wire, sizeof(wire) - 1U),
        MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT);

    failures += expect_validation(
        malbolge_host_capability_validate_span(
            &(MalbolgeHostCapabilitySpan){UINT64_C(16), UINT64_C(4)},
            UINT64_C(64), UINT64_C(16)),
        MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_validation(
        malbolge_host_capability_validate_span(
            &(MalbolgeHostCapabilitySpan){UINT64_C(64), 0U},
            UINT64_C(64), UINT64_C(16)),
        MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_validation(
        malbolge_host_capability_validate_span(
            &(MalbolgeHostCapabilitySpan){UINT64_C(15), UINT64_C(1)},
            UINT64_C(64), UINT64_C(16)),
        MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD);
    failures += expect_validation(
        malbolge_host_capability_validate_span(
            &(MalbolgeHostCapabilitySpan){UINT64_C(65), 0U},
            UINT64_C(64), UINT64_C(16)),
        MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD);
    failures += expect_validation(
        malbolge_host_capability_validate_span(
            &(MalbolgeHostCapabilitySpan){UINT64_MAX, UINT64_C(1)},
            UINT64_MAX, UINT64_C(16)),
        MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD);
    failures += expect_validation(
        malbolge_host_capability_validate_span(
            &(MalbolgeHostCapabilitySpan){UINT64_C(16), 0U},
            UINT64_C(8), UINT64_C(16)),
        MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT);
    return failures;
}

static int test_version_precedence(void)
{
    uint8_t future_frame[80] = {0};
    uint8_t future_descriptor[20] = {0};
    MalbolgeHostCapabilityFrame frame;
    MalbolgeHostCapabilityDescriptor descriptor;
    int failures = 0;

    failures += expect_validation(
        malbolge_host_capability_encode_frame(
            &(MalbolgeHostCapabilityFrame){
                MALBOLGE_HOST_CAPABILITY_ABI_VERSION,
                UINT32_C(0x00000100), 1U, 0U, 0U,
                MALBOLGE_HOST_CAPABILITY_STATUS_PENDING,
                0U, 0U, 0U, 0U, 0U, 0U,
            },
            future_frame, MALBOLGE_HOST_CAPABILITY_FRAME_WIRE_SIZE),
        MALBOLGE_HOST_CAPABILITY_VALID);
    future_frame[4] = UINT8_C(2);
    future_frame[20] = UINT8_C(0xff);
    future_frame[21] = UINT8_C(0xff);
    future_frame[22] = UINT8_C(0xff);
    future_frame[23] = UINT8_C(0xff);
    failures += expect_validation(
        malbolge_host_capability_decode_frame(
            future_frame, sizeof(future_frame), &frame),
        MALBOLGE_HOST_CAPABILITY_UNSUPPORTED_ABI_VERSION);

    failures += expect_validation(
        malbolge_host_capability_encode_descriptor(
            &REGISTRY[0], future_descriptor,
            MALBOLGE_HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE),
        MALBOLGE_HOST_CAPABILITY_VALID);
    future_descriptor[12] = UINT8_C(2);
    failures += expect_validation(
        malbolge_host_capability_decode_descriptor(
            future_descriptor, sizeof(future_descriptor), &descriptor),
        MALBOLGE_HOST_CAPABILITY_UNSUPPORTED_ABI_VERSION);
    return failures;
}

static int test_descriptor_codec(void)
{
    const MalbolgeHostCapabilityValidation unsupported_abi =
        MALBOLGE_HOST_CAPABILITY_UNSUPPORTED_ABI_VERSION;
    static const uint8_t EXPECTED[
        MALBOLGE_HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE] = {
        0x04, 0x03, 0x02, 0x01,
        0x01, 0x00, 0x03, 0x00,
        0x07, 0x00, 0x00, 0x00,
        0x01, 0x00, 0x10, 0x00,
    };
    const MalbolgeHostCapabilityDescriptor descriptor = {
        UINT32_C(0x01020304),
        1U,
        3U,
        MALBOLGE_HOST_CAPABILITY_FLAG_AVAILABLE |
            MALBOLGE_HOST_CAPABILITY_FLAG_MAY_BLOCK |
            MALBOLGE_HOST_CAPABILITY_FLAG_PARTIAL_PROGRESS,
    };
    union DescriptorAlias {
        MalbolgeHostCapabilityDescriptor descriptor;
        uint8_t bytes[MALBOLGE_HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE];
    } alias = {0};
    MalbolgeHostCapabilityDescriptor decoded = {0};
    MalbolgeHostCapabilityDescriptor invalid_descriptor;
    uint8_t wire[MALBOLGE_HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE] = {0};
    int failures = 0;

    failures += expect_validation(malbolge_host_capability_encode_descriptor(
                                      &descriptor, wire, sizeof(wire)),
                                  MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_true(memcmp(wire, EXPECTED, sizeof(wire)) == 0);
    failures += expect_validation(malbolge_host_capability_decode_descriptor(
                                      wire, sizeof(wire), &decoded),
                                  MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_true(descriptor_equal(&descriptor, &decoded));
    failures += expect_validation(malbolge_host_capability_decode_descriptor(
                                      wire, sizeof(wire) - 1U, &decoded),
                                  MALBOLGE_HOST_CAPABILITY_INVALID_WIRE_FRAME);
    failures += expect_true(descriptor_equal(&descriptor, &decoded));

    alias.descriptor = descriptor;
    failures += expect_validation(
        malbolge_host_capability_encode_descriptor(
            &alias.descriptor, alias.bytes,
            MALBOLGE_HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE),
        MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_true(
        memcmp(alias.bytes, EXPECTED, sizeof(EXPECTED)) == 0);
    memcpy(alias.bytes, EXPECTED, sizeof(EXPECTED));
    failures += expect_validation(
        malbolge_host_capability_decode_descriptor(
            alias.bytes, MALBOLGE_HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE,
            &alias.descriptor),
        MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_true(
        descriptor_equal(&descriptor, &alias.descriptor));

    invalid_descriptor = descriptor;
    invalid_descriptor.maximum_version = 0U;
    memset(wire, 0xa5, sizeof(wire));
    failures += expect_validation(
        malbolge_host_capability_encode_descriptor(
            &invalid_descriptor, wire, sizeof(wire)),
        MALBOLGE_HOST_CAPABILITY_INVALID_REGISTRY);
    failures += expect_true(bytes_are(wire, sizeof(wire), UINT8_C(0xa5)));
    memcpy(wire, EXPECTED, sizeof(wire));

    wire[12] = UINT8_C(2);
    failures += expect_validation(malbolge_host_capability_decode_descriptor(
                                      wire, sizeof(wire), &decoded),
                                  unsupported_abi);
    failures += expect_true(descriptor_equal(&descriptor, &decoded));

    memcpy(wire, EXPECTED, sizeof(wire));
    wire[14] = UINT8_C(15);
    failures += expect_validation(malbolge_host_capability_decode_descriptor(
                                      wire, sizeof(wire), &decoded),
                                  MALBOLGE_HOST_CAPABILITY_INVALID_WIRE_FRAME);
    failures += expect_true(descriptor_equal(&descriptor, &decoded));
    return failures;
}

static int test_registry_validation(void)
{
    MalbolgeHostCapabilityDescriptor out = {
        UINT32_C(0xaaaaaaaa),
        UINT16_C(0xaaaa),
        UINT16_C(0xaaaa),
        UINT32_C(0xaaaaaaaa),
    };
    MalbolgeHostCapabilityDescriptor invalid[2] = {REGISTRY[0], REGISTRY[1]};
    int failures = 0;

    failures += expect_validation(
        malbolge_host_capability_validate_registry(
            REGISTRY, sizeof(REGISTRY) / sizeof(REGISTRY[0])),
        MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_validation(
        malbolge_host_capability_validate_registry(NULL, 0U),
        MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_validation(
        malbolge_host_capability_validate_registry(NULL, 1U),
        MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT);

    invalid[0].capability_id = 0U;
    failures += expect_validation(
        malbolge_host_capability_validate_registry(invalid, 2U),
        MALBOLGE_HOST_CAPABILITY_INVALID_REGISTRY);
    invalid[0] = REGISTRY[0];
    invalid[0].minimum_version = 0U;
    failures += expect_validation(
        malbolge_host_capability_validate_registry(invalid, 2U),
        MALBOLGE_HOST_CAPABILITY_INVALID_REGISTRY);
    invalid[0] = REGISTRY[0];
    invalid[0].minimum_version = 2U;
    invalid[0].maximum_version = 1U;
    failures += expect_validation(
        malbolge_host_capability_validate_registry(invalid, 2U),
        MALBOLGE_HOST_CAPABILITY_INVALID_REGISTRY);
    invalid[0] = REGISTRY[0];
    invalid[0].flags |= UINT32_C(0x80000000);
    failures += expect_validation(
        malbolge_host_capability_validate_registry(invalid, 2U),
        MALBOLGE_HOST_CAPABILITY_INVALID_REGISTRY);
    invalid[0] = REGISTRY[0];
    invalid[1] = REGISTRY[0];
    failures += expect_validation(
        malbolge_host_capability_validate_registry(invalid, 2U),
        MALBOLGE_HOST_CAPABILITY_INVALID_REGISTRY);
    invalid[0] = REGISTRY[1];
    invalid[1] = REGISTRY[0];
    failures += expect_validation(
        malbolge_host_capability_validate_registry(invalid, 2U),
        MALBOLGE_HOST_CAPABILITY_INVALID_REGISTRY);

    failures += expect_validation(malbolge_host_capability_discover(
                                      REGISTRY, 3U, UINT32_C(0x00000200), 2U,
                                      &out),
                                  MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_true(descriptor_equal(&out, &REGISTRY[1]));
    failures += expect_validation(malbolge_host_capability_discover(
                                      REGISTRY, 3U, UINT32_C(0x00000200), 3U,
                                      &out),
                                  MALBOLGE_HOST_CAPABILITY_UNSUPPORTED_VERSION);
    failures += expect_true(descriptor_equal(&out, &REGISTRY[1]));
    failures += expect_validation(malbolge_host_capability_discover(
                                      REGISTRY, 3U, UINT32_C(0x00000280), 1U,
                                      &out),
                                  MALBOLGE_HOST_CAPABILITY_UNKNOWN);
    failures += expect_validation(malbolge_host_capability_discover(
                                      REGISTRY, 3U, UINT32_C(0x00000300), 1U,
                                      &out),
                                  MALBOLGE_HOST_CAPABILITY_UNAVAILABLE);
    failures += expect_validation(malbolge_host_capability_discover(
                                      REGISTRY, 3U, 0U, 1U, &out),
                                  MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT);
    failures += expect_validation(malbolge_host_capability_discover(
                                      REGISTRY, 3U, UINT32_C(0x00000100), 0U,
                                      &out),
                                  MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT);
    return failures;
}

static int test_wire_registry(void)
{
    uint8_t wire[sizeof(REGISTRY) / sizeof(REGISTRY[0]) *
                 MALBOLGE_HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE] = {0};
    uint8_t future_registry[36] = {0};
    MalbolgeHostCapabilityDescriptor out = {
        UINT32_C(0xaaaaaaaa),
        UINT16_C(0xaaaa),
        UINT16_C(0xaaaa),
        UINT32_C(0xaaaaaaaa),
    };
    MalbolgeHostCapabilityDescriptor sentinel = out;
    size_t index = 0U;
    int failures = 0;

    for (index = 0U; index < sizeof(REGISTRY) / sizeof(REGISTRY[0]); ++index) {
        failures += expect_validation(
            malbolge_host_capability_encode_descriptor(
                &REGISTRY[index],
                wire + index * MALBOLGE_HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE,
                MALBOLGE_HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE),
            MALBOLGE_HOST_CAPABILITY_VALID);
    }
    failures += expect_validation(
        malbolge_host_capability_validate_wire_registry(wire, sizeof(wire)),
        MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_validation(
        malbolge_host_capability_discover_wire(
            wire, sizeof(wire), UINT32_C(0x00000200), 2U, &out),
        MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_true(descriptor_equal(&out, &REGISTRY[1]));

    failures += expect_validation(
        malbolge_host_capability_validate_wire_registry(
            wire, sizeof(wire) - 1U),
        MALBOLGE_HOST_CAPABILITY_INVALID_WIRE_FRAME);

    memcpy(future_registry, wire,
           MALBOLGE_HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE);
    memcpy(future_registry + MALBOLGE_HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE,
           wire + MALBOLGE_HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE,
           MALBOLGE_HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE);
    future_registry[28] = UINT8_C(2);
    failures += expect_validation(
        malbolge_host_capability_validate_wire_registry(
            future_registry, sizeof(future_registry)),
        MALBOLGE_HOST_CAPABILITY_UNSUPPORTED_ABI_VERSION);
    out = sentinel;
    failures += expect_validation(
        malbolge_host_capability_discover_wire(
            future_registry, sizeof(future_registry),
            UINT32_C(0x00000100), 1U, &out),
        MALBOLGE_HOST_CAPABILITY_UNSUPPORTED_ABI_VERSION);
    failures += expect_true(descriptor_equal(&out, &sentinel));

    out = sentinel;
    memcpy(wire + MALBOLGE_HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE, wire,
           MALBOLGE_HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE);
    failures += expect_validation(
        malbolge_host_capability_discover_wire(
            wire, sizeof(wire), UINT32_C(0x00000100), 1U, &out),
        MALBOLGE_HOST_CAPABILITY_INVALID_REGISTRY);
    failures += expect_true(descriptor_equal(&out, &sentinel));
    return failures;
}

static int test_request_validation(void)
{
    MalbolgeHostCapabilityFrame frame = base_request(UINT32_C(0x00000100));
    int failures = 0;

    failures += expect_validation(malbolge_host_capability_validate_request(
                                      &frame, UINT64_C(64), REGISTRY, 3U),
                                  MALBOLGE_HOST_CAPABILITY_VALID);
    frame.flags = MALBOLGE_HOST_CALL_FLAG_NONBLOCKING;
    failures += expect_validation(malbolge_host_capability_validate_request(
                                      &frame, UINT64_C(64), REGISTRY, 3U),
                                  MALBOLGE_HOST_CAPABILITY_INVALID_STATUS);
    frame = base_request(UINT32_C(0x00000200));
    frame.flags = MALBOLGE_HOST_CALL_FLAG_NONBLOCKING;
    failures += expect_validation(malbolge_host_capability_validate_request(
                                      &frame, UINT64_C(64), REGISTRY, 3U),
                                  MALBOLGE_HOST_CAPABILITY_VALID);
    frame = base_request(UINT32_C(0x00000100));
    frame.result_offset = UINT64_C(16);
    failures += expect_validation(malbolge_host_capability_validate_request(
                                      &frame, UINT64_C(64), REGISTRY, 3U),
                                  MALBOLGE_HOST_CAPABILITY_VALID);
    frame.result_offset = UINT64_C(15);
    failures += expect_validation(malbolge_host_capability_validate_request(
                                      &frame, UINT64_C(64), REGISTRY, 3U),
                                  MALBOLGE_HOST_CAPABILITY_INVALID_RANGE);

    frame = base_request(UINT32_C(0x00000100));
    frame.request_offset = UINT64_C(64);
    frame.request_length = 0U;
    frame.result_offset = UINT64_C(64);
    frame.result_capacity = 0U;
    failures += expect_validation(malbolge_host_capability_validate_request(
                                      &frame, UINT64_C(64), REGISTRY, 3U),
                                  MALBOLGE_HOST_CAPABILITY_VALID);
    frame.request_offset = UINT64_C(65);
    failures += expect_validation(malbolge_host_capability_validate_request(
                                      &frame, UINT64_C(64), REGISTRY, 3U),
                                  MALBOLGE_HOST_CAPABILITY_INVALID_RANGE);

    frame = base_request(UINT32_C(0x00000100));
    frame.request_offset = UINT64_MAX;
    frame.request_length = 1U;
    failures += expect_validation(malbolge_host_capability_validate_request(
                                      &frame, UINT64_MAX, REGISTRY, 3U),
                                  MALBOLGE_HOST_CAPABILITY_INVALID_RANGE);
    frame = base_request(UINT32_C(0x00000100));
    frame.result_offset = UINT64_C(60);
    frame.result_capacity = UINT64_C(5);
    failures += expect_validation(malbolge_host_capability_validate_request(
                                      &frame, UINT64_C(64), REGISTRY, 3U),
                                  MALBOLGE_HOST_CAPABILITY_INVALID_RANGE);

    frame = base_request(UINT32_C(0x00000400));
    failures += expect_validation(malbolge_host_capability_validate_request(
                                      &frame, UINT64_C(64), REGISTRY, 3U),
                                  MALBOLGE_HOST_CAPABILITY_UNKNOWN);
    frame = base_request(UINT32_C(0x00000200));
    frame.capability_version = 3U;
    failures += expect_validation(malbolge_host_capability_validate_request(
                                      &frame, UINT64_C(64), REGISTRY, 3U),
                                  MALBOLGE_HOST_CAPABILITY_UNSUPPORTED_VERSION);
    frame = base_request(UINT32_C(0x00000300));
    failures += expect_validation(malbolge_host_capability_validate_request(
                                      &frame, UINT64_C(64), REGISTRY, 3U),
                                  MALBOLGE_HOST_CAPABILITY_UNAVAILABLE);
    return failures;
}

static int test_request_shape_failures(void)
{
    const MalbolgeHostCapabilityValidation unsupported_abi =
        MALBOLGE_HOST_CAPABILITY_UNSUPPORTED_ABI_VERSION;
    MalbolgeHostCapabilityFrame frame = base_request(UINT32_C(0x00000100));
    int failures = 0;

    frame.status = MALBOLGE_HOST_CAPABILITY_STATUS_COMPLETE;
    failures += expect_validation(malbolge_host_capability_validate_request(
                                      &frame, UINT64_C(64), REGISTRY, 3U),
                                  MALBOLGE_HOST_CAPABILITY_INVALID_STATUS);
    frame = base_request(UINT32_C(0x00000100));
    frame.result_length = 1U;
    failures += expect_validation(malbolge_host_capability_validate_request(
                                      &frame, UINT64_C(64), REGISTRY, 3U),
                                  MALBOLGE_HOST_CAPABILITY_INVALID_STATUS);
    frame = base_request(UINT32_C(0x00000100));
    frame.flags = UINT32_C(0x80000000);
    failures += expect_validation(malbolge_host_capability_validate_request(
                                      &frame, UINT64_C(64), REGISTRY, 3U),
                                  MALBOLGE_HOST_CAPABILITY_INVALID_WIRE_FRAME);
    frame = base_request(UINT32_C(0x00000100));
    frame.abi_version = 2U;
    failures += expect_validation(malbolge_host_capability_validate_request(
                                      &frame, UINT64_C(64), REGISTRY, 3U),
                                  unsupported_abi);
    frame = base_request(UINT32_C(0x00000100));
    frame.capability_version = 0U;
    failures += expect_validation(malbolge_host_capability_validate_request(
                                      &frame, UINT64_C(64), REGISTRY, 3U),
                                  MALBOLGE_HOST_CAPABILITY_INVALID_WIRE_FRAME);
    frame = base_request(0U);
    failures += expect_validation(malbolge_host_capability_validate_request(
                                      &frame, UINT64_C(64), REGISTRY, 3U),
                                  MALBOLGE_HOST_CAPABILITY_INVALID_WIRE_FRAME);
    frame = base_request(UINT32_C(0x00000100));
    frame.status = (MalbolgeHostCapabilityStatus)99;
    failures += expect_validation(malbolge_host_capability_validate_request(
                                      &frame, UINT64_C(64), REGISTRY, 3U),
                                  MALBOLGE_HOST_CAPABILITY_INVALID_STATUS);
    return failures;
}

static int expect_invalid_response_identity(
    const MalbolgeHostCapabilityFrame *request,
    const MalbolgeHostCapabilityFrame *response)
{
    return expect_validation(malbolge_host_capability_validate_response(
                                 request, response, UINT64_C(64), REGISTRY, 3U),
                             MALBOLGE_HOST_CAPABILITY_INVALID_RESPONSE);
}

static int test_response_identity(void)
{
    MalbolgeHostCapabilityFrame request =
        base_request(UINT32_C(0x00000100));
    MalbolgeHostCapabilityFrame response = request;
    int failures = 0;

    response.status = MALBOLGE_HOST_CAPABILITY_STATUS_COMPLETE;
    response.capability_id = UINT32_C(0x00000200);
    failures += expect_invalid_response_identity(&request, &response);
    response = request;
    response.status = MALBOLGE_HOST_CAPABILITY_STATUS_COMPLETE;
    response.capability_version = 2U;
    failures += expect_invalid_response_identity(&request, &response);
    response = request;
    response.status = MALBOLGE_HOST_CAPABILITY_STATUS_COMPLETE;
    response.operation = 8U;
    failures += expect_invalid_response_identity(&request, &response);
    response = request;
    response.status = MALBOLGE_HOST_CAPABILITY_STATUS_COMPLETE;
    response.flags = MALBOLGE_HOST_CALL_FLAG_NONBLOCKING;
    failures += expect_invalid_response_identity(&request, &response);
    response = request;
    response.status = MALBOLGE_HOST_CAPABILITY_STATUS_COMPLETE;
    response.request_offset = UINT64_C(9);
    failures += expect_invalid_response_identity(&request, &response);
    response = request;
    response.status = MALBOLGE_HOST_CAPABILITY_STATUS_COMPLETE;
    response.request_length = UINT64_C(7);
    failures += expect_invalid_response_identity(&request, &response);
    response = request;
    response.status = MALBOLGE_HOST_CAPABILITY_STATUS_COMPLETE;
    response.result_offset = UINT64_C(33);
    failures += expect_invalid_response_identity(&request, &response);
    response = request;
    response.status = MALBOLGE_HOST_CAPABILITY_STATUS_COMPLETE;
    response.result_capacity = UINT64_C(15);
    failures += expect_invalid_response_identity(&request, &response);
    response = request;
    response.status = MALBOLGE_HOST_CAPABILITY_STATUS_COMPLETE;
    response.call_id = UINT64_C(100);
    failures += expect_invalid_response_identity(&request, &response);
    return failures;
}

static int test_response_commit(void)
{
    MalbolgeHostCapabilityFrame request =
        base_request(UINT32_C(0x00000100));
    MalbolgeHostCapabilityFrame response = request;
    const uint8_t staged[] = {1U, 2U, 3U, 4U};
    uint8_t memory[64];
    uint8_t baseline[64];
    int failures = 0;

    memset(memory, 0xa5, sizeof(memory));
    response.status = MALBOLGE_HOST_CAPABILITY_STATUS_COMPLETE;
    response.result_length = sizeof(staged);
    failures += expect_validation(malbolge_host_capability_commit_response(
                                      &request, &response, REGISTRY, 3U,
                                      memory, sizeof(memory), staged,
                                      sizeof(staged)),
                                  MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_true(memcmp(memory + 32U, staged, sizeof(staged)) == 0);

    memset(memory, 0xa5, sizeof(memory));
    memcpy(baseline, memory, sizeof(memory));
    response.call_id = UINT64_C(100);
    failures += expect_validation(malbolge_host_capability_commit_response(
                                      &request, &response, REGISTRY, 3U,
                                      memory, sizeof(memory), staged,
                                      sizeof(staged)),
                                  MALBOLGE_HOST_CAPABILITY_INVALID_RESPONSE);
    failures += expect_true(memcmp(memory, baseline, sizeof(memory)) == 0);

    response = request;
    response.status = MALBOLGE_HOST_CAPABILITY_STATUS_COMPLETE;
    response.result_length = sizeof(staged);
    failures += expect_validation(malbolge_host_capability_commit_response(
                                      &request, &response, REGISTRY, 3U,
                                      memory, sizeof(memory), staged,
                                      sizeof(staged) - 1U),
                                  MALBOLGE_HOST_CAPABILITY_INVALID_RESPONSE);
    failures += expect_true(memcmp(memory, baseline, sizeof(memory)) == 0);

    memcpy(memory, staged, sizeof(staged));
    memcpy(baseline, memory, sizeof(memory));
    failures += expect_validation(malbolge_host_capability_commit_response(
                                      &request, &response, REGISTRY, 3U,
                                      memory, sizeof(memory), memory,
                                      sizeof(staged)),
                                  MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT);
    failures += expect_true(memcmp(memory, baseline, sizeof(memory)) == 0);
    return failures;
}

static int test_response_validation(void)
{
    MalbolgeHostCapabilityFrame request =
        base_request(UINT32_C(0x00000200));
    MalbolgeHostCapabilityFrame response = request;
    int failures = 0;

    response.status = MALBOLGE_HOST_CAPABILITY_STATUS_COMPLETE;
    response.result_length = UINT64_C(16);
    failures += expect_validation(malbolge_host_capability_validate_response(
                                      &request, &response, UINT64_C(64),
                                      REGISTRY, 3U),
                                  MALBOLGE_HOST_CAPABILITY_VALID);

    response = request;
    response.status = MALBOLGE_HOST_CAPABILITY_STATUS_PARTIAL;
    response.result_length = UINT64_C(8);
    failures += expect_validation(malbolge_host_capability_validate_response(
                                      &request, &response, UINT64_C(64),
                                      REGISTRY, 3U),
                                  MALBOLGE_HOST_CAPABILITY_VALID);
    response.result_length = 0U;
    failures += expect_validation(malbolge_host_capability_validate_response(
                                      &request, &response, UINT64_C(64),
                                      REGISTRY, 3U),
                                  MALBOLGE_HOST_CAPABILITY_INVALID_RESPONSE);

    request = base_request(UINT32_C(0x00000100));
    response = request;
    response.status = MALBOLGE_HOST_CAPABILITY_STATUS_PARTIAL;
    response.result_length = UINT64_C(1);
    failures += expect_validation(malbolge_host_capability_validate_response(
                                      &request, &response, UINT64_C(64),
                                      REGISTRY, 3U),
                                  MALBOLGE_HOST_CAPABILITY_INVALID_RESPONSE);

    request = base_request(UINT32_C(0x00000200));
    request.flags = MALBOLGE_HOST_CALL_FLAG_NONBLOCKING;
    response = request;
    response.status = MALBOLGE_HOST_CAPABILITY_STATUS_WOULD_BLOCK;
    failures += expect_validation(malbolge_host_capability_validate_response(
                                      &request, &response, UINT64_C(64),
                                      REGISTRY, 3U),
                                  MALBOLGE_HOST_CAPABILITY_VALID);
    request.flags = 0U;
    response = request;
    response.status = MALBOLGE_HOST_CAPABILITY_STATUS_WOULD_BLOCK;
    failures += expect_validation(malbolge_host_capability_validate_response(
                                      &request, &response, UINT64_C(64),
                                      REGISTRY, 3U),
                                  MALBOLGE_HOST_CAPABILITY_INVALID_RESPONSE);

    request = base_request(UINT32_C(0x00000100));
    request.flags = MALBOLGE_HOST_CALL_FLAG_NONBLOCKING;
    response = request;
    response.status = MALBOLGE_HOST_CAPABILITY_STATUS_WOULD_BLOCK;
    failures += expect_validation(malbolge_host_capability_validate_response(
                                      &request, &response, UINT64_C(64),
                                      REGISTRY, 3U),
                                  MALBOLGE_HOST_CAPABILITY_INVALID_STATUS);

    request = base_request(UINT32_C(0x00000100));
    response = request;
    response.status = MALBOLGE_HOST_CAPABILITY_STATUS_HOST_ERROR;
    failures += expect_validation(malbolge_host_capability_validate_response(
                                      &request, &response, UINT64_C(64),
                                      REGISTRY, 3U),
                                  MALBOLGE_HOST_CAPABILITY_VALID);
    response.result_length = 1U;
    failures += expect_validation(malbolge_host_capability_validate_response(
                                      &request, &response, UINT64_C(64),
                                      REGISTRY, 3U),
                                  MALBOLGE_HOST_CAPABILITY_INVALID_STATUS);

    response = request;
    response.status = MALBOLGE_HOST_CAPABILITY_STATUS_CANCELLED;
    failures += expect_validation(malbolge_host_capability_validate_response(
                                      &request, &response, UINT64_C(64),
                                      REGISTRY, 3U),
                                  MALBOLGE_HOST_CAPABILITY_VALID);
    response = request;
    response.status = MALBOLGE_HOST_CAPABILITY_STATUS_COMPLETE;
    response.call_id += UINT64_C(1);
    failures += expect_validation(malbolge_host_capability_validate_response(
                                      &request, &response, UINT64_C(64),
                                      REGISTRY, 3U),
                                  MALBOLGE_HOST_CAPABILITY_INVALID_RESPONSE);
    response = request;
    response.status = MALBOLGE_HOST_CAPABILITY_STATUS_PENDING;
    failures += expect_validation(malbolge_host_capability_validate_response(
                                      &request, &response, UINT64_C(64),
                                      REGISTRY, 3U),
                                  MALBOLGE_HOST_CAPABILITY_INVALID_RESPONSE);
    return failures;
}

int main(void)
{
    int failures = 0;
    failures += test_frame_codec();
    failures += test_payload_span();
    failures += test_version_precedence();
    failures += test_descriptor_codec();
    failures += test_registry_validation();
    failures += test_wire_registry();
    failures += test_request_validation();
    failures += test_request_shape_failures();
    failures += test_response_identity();
    failures += test_response_commit();
    failures += test_response_validation();
    return failures;
}
