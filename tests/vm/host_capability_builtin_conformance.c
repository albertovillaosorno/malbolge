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
//   - Independent C vectors for built-in host-capability schemas.
// - Must-Not:
//   - Call Rust or perform a native cursor/UI/logging host effect.
// - Allows:
//   - Inputs: pure-C built-in schema codecs and fixed byte fixtures.
//   - Outputs: zero on conformance success, nonzero on first-class failure.
//   - Side effects: test-process memory only.
// - Split-When:
//   - Split when another capability family needs an independent native harness.
// - Merge-When:
//   - Merge when built-in schema vectors become generated cross-language data.
// - Summary:
//   - Verifies relative-mouse and telemetry schemas independently in pure C.
// - Description:
//   - Covers exact bytes, UTF-8, alias safety, discovery, and frame admission.
// - Usage:
//   - Compiled by `tests/test_host_capability_c_abi.py` with strict Clang.
// - Defaults:
//   - No tested path calls a real external host capability.
//

//! Conformance harness for built-in host-capability schemas.

#include "malbolge_host_capability_mouse.h"
#include "malbolge_host_capability_telemetry.h"

#include <string.h>

static const uint8_t CAPTURE_VECTOR[] = {1U, 0U, 0U, 0U, 0U, 0U, 0U, 0U};

static const uint8_t TELEMETRY_VECTOR[] = {
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x35, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x40, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x41, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x49, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x0a, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x43, 0x64, 0x5f, 0x6d, 0x61, 0x69, 0x6e, 0x2e,
    0x63, 0x4d, 0x5f, 0x44, 0x72, 0x61, 0x77, 0x65,
    0x72, 0x28, 0x29,
};

static const uint8_t LANGUAGE[] = {'C'};
static const uint8_t SOURCE[] = {'d', '_', 'm', 'a', 'i', 'n', '.', 'c'};
static const uint8_t INSTRUCTION[] = {
    'M', '_', 'D', 'r', 'a', 'w', 'e', 'r', '(', ')',
};

static int expect_validation(MalbolgeHostCapabilityValidation actual,
                             MalbolgeHostCapabilityValidation expected)
{
    return actual == expected ? 0 : 1;
}

static int expect_true(bool condition)
{
    return condition ? 0 : 1;
}

static MalbolgeHostCapabilityFrame request_frame(uint32_t capability_id,
                                                 uint16_t capability_version,
                                                 uint16_t operation,
                                                 uint64_t request_offset,
                                                 uint64_t request_length)
{
    const MalbolgeHostCapabilityFrame frame = {
        .abi_version = MALBOLGE_HOST_CAPABILITY_ABI_VERSION,
        .capability_id = capability_id,
        .capability_version = capability_version,
        .operation = operation,
        .flags = 0U,
        .status = MALBOLGE_HOST_CAPABILITY_STATUS_PENDING,
        .request_offset = request_offset,
        .request_length = request_length,
        .result_offset = request_offset,
        .result_capacity = 0U,
        .result_length = 0U,
        .call_id = UINT64_C(17),
    };
    return frame;
}

static int test_mouse_payload(void)
{
    MalbolgeHostRelativeMouseCaptureV1 request = {.capture = true};
    MalbolgeHostRelativeMouseCaptureV1 decoded = {.capture = false};
    uint8_t payload[MALBOLGE_HOST_RELATIVE_MOUSE_CAPTURE_V1_REQUEST_SIZE] = {0};
    int failures = 0;

    failures += expect_validation(
        malbolge_host_relative_mouse_capture_v1_encode(
            &request, payload, sizeof(payload)),
        MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_true(
        memcmp(payload, CAPTURE_VECTOR, sizeof(CAPTURE_VECTOR)) == 0);
    failures += expect_validation(
        malbolge_host_relative_mouse_capture_v1_decode(
            payload, sizeof(payload), &decoded),
        MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_true(decoded.capture);

    memcpy(payload, CAPTURE_VECTOR, sizeof(payload));
    request.capture = false;
    failures += expect_validation(
        malbolge_host_relative_mouse_capture_v1_encode(
            &request, payload, sizeof(payload) - 1U),
        MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT);
    failures += expect_true(
        memcmp(payload, CAPTURE_VECTOR, sizeof(CAPTURE_VECTOR)) == 0);

    payload[0] = UINT8_C(2);
    decoded.capture = true;
    failures += expect_validation(
        malbolge_host_relative_mouse_capture_v1_decode(
            payload, sizeof(payload), &decoded),
        MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD);
    failures += expect_true(decoded.capture);
    memcpy(payload, CAPTURE_VECTOR, sizeof(payload));
    payload[7] = UINT8_C(1);
    failures += expect_validation(
        malbolge_host_relative_mouse_capture_v1_decode(
            payload, sizeof(payload), &decoded),
        MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD);
    failures += expect_validation(
        malbolge_host_relative_mouse_capture_v1_decode(
            payload, sizeof(payload) - 1U, &decoded),
        MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD);

    {
        union MouseAlias {
            uint8_t bytes[MALBOLGE_HOST_RELATIVE_MOUSE_CAPTURE_V1_REQUEST_SIZE];
            MalbolgeHostRelativeMouseCaptureV1 request;
        } alias = {0};
        memcpy(alias.bytes, CAPTURE_VECTOR, sizeof(CAPTURE_VECTOR));
        failures += expect_validation(
            malbolge_host_relative_mouse_capture_v1_decode(
                alias.bytes, sizeof(alias.bytes), &alias.request),
            MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT);
    }
    return failures;
}

static int test_mouse_call(void)
{
    MalbolgeHostCapabilityDescriptor registry[] = {
        malbolge_host_execution_telemetry_v1_descriptor(true),
        malbolge_host_relative_mouse_capture_v1_descriptor(true),
    };
    MalbolgeHostCapabilityFrame frame = request_frame(
        MALBOLGE_HOST_RELATIVE_MOUSE_CAPTURE_CAPABILITY_ID,
        MALBOLGE_HOST_RELATIVE_MOUSE_CAPTURE_V1_VERSION,
        MALBOLGE_HOST_RELATIVE_MOUSE_CAPTURE_V1_OPERATION,
        UINT64_C(8), UINT64_C(8));
    MalbolgeHostRelativeMouseCaptureV1 request = {.capture = false};
    uint8_t memory[32] = {0};
    int failures = 0;

    memcpy(memory + 8U, CAPTURE_VECTOR, sizeof(CAPTURE_VECTOR));
    failures += expect_validation(
        malbolge_host_relative_mouse_capture_v1_validate_call(
            &frame, memory, sizeof(memory), registry, 2U, &request),
        MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_true(request.capture);

    frame.operation = UINT16_C(1);
    failures += expect_validation(
        malbolge_host_relative_mouse_capture_v1_validate_call(
            &frame, memory, sizeof(memory), registry, 2U, &request),
        MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD);
    frame.operation = MALBOLGE_HOST_RELATIVE_MOUSE_CAPTURE_V1_OPERATION;
    frame.result_offset = UINT64_C(31);
    frame.result_capacity = UINT64_C(1);
    failures += expect_validation(
        malbolge_host_relative_mouse_capture_v1_validate_call(
            &frame, memory, sizeof(memory), registry, 2U, &request),
        MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD);

    {
        union MouseCallAlias {
            uint8_t memory[32];
            MalbolgeHostRelativeMouseCaptureV1 request;
        } overlap = {0};
        memcpy(overlap.memory + 8U, CAPTURE_VECTOR, sizeof(CAPTURE_VECTOR));
        frame.result_offset = UINT64_C(8);
        frame.result_capacity = 0U;
        failures += expect_validation(
            malbolge_host_relative_mouse_capture_v1_validate_call(
                &frame, overlap.memory, sizeof(overlap.memory), registry, 2U,
                &overlap.request),
            MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT);
    }

    registry[1] = malbolge_host_relative_mouse_capture_v1_descriptor(false);
    frame.result_offset = UINT64_C(8);
    frame.result_capacity = 0U;
    failures += expect_validation(
        malbolge_host_relative_mouse_capture_v1_validate_call(
            &frame, memory, sizeof(memory), registry, 2U, &request),
        MALBOLGE_HOST_CAPABILITY_UNAVAILABLE);
    return failures;
}

static MalbolgeHostExecutionTelemetryV1 telemetry_fixture(void)
{
    const MalbolgeHostExecutionTelemetryV1 telemetry = {
        .language = LANGUAGE,
        .language_length = sizeof(LANGUAGE),
        .source = SOURCE,
        .source_length = sizeof(SOURCE),
        .location = UINT64_C(309),
        .instruction = INSTRUCTION,
        .instruction_length = sizeof(INSTRUCTION),
    };
    return telemetry;
}

static int telemetry_matches_fixture(
    const MalbolgeHostExecutionTelemetryV1 *telemetry)
{
    return telemetry != NULL && telemetry->location == UINT64_C(309) &&
           telemetry->language_length == sizeof(LANGUAGE) &&
           telemetry->source_length == sizeof(SOURCE) &&
           telemetry->instruction_length == sizeof(INSTRUCTION) &&
           memcmp(telemetry->language, LANGUAGE, sizeof(LANGUAGE)) == 0 &&
           memcmp(telemetry->source, SOURCE, sizeof(SOURCE)) == 0 &&
           memcmp(telemetry->instruction, INSTRUCTION,
                  sizeof(INSTRUCTION)) == 0;
}

static int test_telemetry_payload(void)
{
    const MalbolgeHostExecutionTelemetryV1 telemetry = telemetry_fixture();
    MalbolgeHostExecutionTelemetryV1 decoded = {0};
    uint8_t payload[sizeof(TELEMETRY_VECTOR)] = {0};
    size_t written = 0U;
    int failures = 0;

    failures += expect_validation(
        malbolge_host_execution_telemetry_v1_encode(
            &telemetry, payload, sizeof(payload), &written),
        MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_true(written == sizeof(TELEMETRY_VECTOR));
    failures += expect_true(
        memcmp(payload, TELEMETRY_VECTOR, sizeof(TELEMETRY_VECTOR)) == 0);
    failures += expect_validation(
        malbolge_host_execution_telemetry_v1_decode(
            payload, sizeof(payload), &decoded),
        MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_true(telemetry_matches_fixture(&decoded));

    memcpy(payload, TELEMETRY_VECTOR, sizeof(payload));
    decoded.location = UINT64_C(777);
    payload[0] = UINT8_C(1);
    failures += expect_validation(
        malbolge_host_execution_telemetry_v1_decode(
            payload, sizeof(payload), &decoded),
        MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD);
    failures += expect_true(decoded.location == UINT64_C(777));
    memcpy(payload, TELEMETRY_VECTOR, sizeof(payload));
    payload[4] = UINT8_C(1);
    failures += expect_validation(
        malbolge_host_execution_telemetry_v1_decode(
            payload, sizeof(payload), &decoded),
        MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD);
    memcpy(payload, TELEMETRY_VECTOR, sizeof(payload));
    payload[32] = UINT8_C(0x42);
    failures += expect_validation(
        malbolge_host_execution_telemetry_v1_decode(
            payload, sizeof(payload), &decoded),
        MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD);
    memcpy(payload, TELEMETRY_VECTOR, sizeof(payload));
    payload[64] = 0U;
    failures += expect_validation(
        malbolge_host_execution_telemetry_v1_decode(
            payload, sizeof(payload), &decoded),
        MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD);
    memcpy(payload, TELEMETRY_VECTOR, sizeof(payload));
    payload[64] = UINT8_C(0xff);
    failures += expect_validation(
        malbolge_host_execution_telemetry_v1_decode(
            payload, sizeof(payload), &decoded),
        MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD);
    return failures;
}

static int test_telemetry_utf8(void)
{
    static const uint8_t VALID_LANGUAGE[] = {UINT8_C(0xce), UINT8_C(0xbb)};
    static const uint8_t OVERLONG[] = {UINT8_C(0xc0), UINT8_C(0x80)};
    static const uint8_t SURROGATE[] = {
        UINT8_C(0xed), UINT8_C(0xa0), UINT8_C(0x80),
    };
    static const uint8_t TOO_HIGH[] = {
        UINT8_C(0xf4), UINT8_C(0x90), UINT8_C(0x80), UINT8_C(0x80),
    };
    static const uint8_t TRUNCATED[] = {UINT8_C(0xe2), UINT8_C(0x82)};
    static const uint8_t CONTINUATION[] = {UINT8_C(0x80)};
    const struct InvalidText {
        const uint8_t *bytes;
        size_t length;
    } invalid[] = {
        {OVERLONG, sizeof(OVERLONG)},
        {SURROGATE, sizeof(SURROGATE)},
        {TOO_HIGH, sizeof(TOO_HIGH)},
        {TRUNCATED, sizeof(TRUNCATED)},
        {CONTINUATION, sizeof(CONTINUATION)},
    };
    MalbolgeHostExecutionTelemetryV1 telemetry = telemetry_fixture();
    MalbolgeHostExecutionTelemetryV1 decoded = {0};
    uint8_t payload[96] = {0};
    size_t written = 0U;
    size_t index = 0U;
    int failures = 0;

    telemetry.language = VALID_LANGUAGE;
    telemetry.language_length = sizeof(VALID_LANGUAGE);
    failures += expect_validation(
        malbolge_host_execution_telemetry_v1_encode(
            &telemetry, payload, sizeof(payload), &written),
        MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_validation(
        malbolge_host_execution_telemetry_v1_decode(
            payload, written, &decoded),
        MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_true(decoded.language_length == sizeof(VALID_LANGUAGE));
    failures += expect_true(
        memcmp(decoded.language, VALID_LANGUAGE, sizeof(VALID_LANGUAGE)) == 0);

    for (index = 0U; index < sizeof(invalid) / sizeof(invalid[0]); ++index) {
        telemetry.language = invalid[index].bytes;
        telemetry.language_length = invalid[index].length;
        written = UINT64_C(99);
        failures += expect_validation(
            malbolge_host_execution_telemetry_v1_encode(
                &telemetry, payload, sizeof(payload), &written),
            MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD);
        failures += expect_true(written == 99U);
    }
    return failures;
}

static int test_telemetry_alias_and_capacity(void)
{
    MalbolgeHostExecutionTelemetryV1 telemetry = telemetry_fixture();
    uint8_t destination[sizeof(TELEMETRY_VECTOR)] = {0xa5};
    uint8_t baseline[sizeof(destination)];
    uint8_t alias[96] = {0};
    size_t written = UINT64_C(77);
    int failures = 0;

    memcpy(baseline, destination, sizeof(destination));
    failures += expect_validation(
        malbolge_host_execution_telemetry_v1_encode(
            &telemetry, destination, sizeof(destination) - 1U, &written),
        MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT);
    failures += expect_true(written == 77U);
    failures += expect_true(
        memcmp(destination, baseline, sizeof(destination)) == 0);

    alias[70] = 'C';
    telemetry.language = alias + 70U;
    telemetry.language_length = 1U;
    written = UINT64_C(88);
    failures += expect_validation(
        malbolge_host_execution_telemetry_v1_encode(
            &telemetry, alias, sizeof(alias), &written),
        MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT);
    failures += expect_true(written == 88U && alias[70] == 'C');

    {
        union TelemetryAlias {
            uint8_t bytes[sizeof(TELEMETRY_VECTOR)];
            MalbolgeHostExecutionTelemetryV1 telemetry;
        } overlap = {0};
        memcpy(overlap.bytes, TELEMETRY_VECTOR, sizeof(TELEMETRY_VECTOR));
        failures += expect_validation(
            malbolge_host_execution_telemetry_v1_decode(
                overlap.bytes, sizeof(overlap.bytes), &overlap.telemetry),
            MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT);
    }
    return failures;
}

static int test_telemetry_call(void)
{
    MalbolgeHostCapabilityDescriptor registry[] = {
        malbolge_host_execution_telemetry_v1_descriptor(true),
        malbolge_host_relative_mouse_capture_v1_descriptor(true),
    };
    MalbolgeHostCapabilityFrame frame = request_frame(
        MALBOLGE_HOST_EXECUTION_TELEMETRY_CAPABILITY_ID,
        MALBOLGE_HOST_EXECUTION_TELEMETRY_V1_VERSION,
        MALBOLGE_HOST_EXECUTION_TELEMETRY_V1_OPERATION,
        UINT64_C(8), (uint64_t)sizeof(TELEMETRY_VECTOR));
    MalbolgeHostExecutionTelemetryV1 telemetry = {0};
    uint8_t memory[128] = {0};
    int failures = 0;

    memcpy(memory + 8U, TELEMETRY_VECTOR, sizeof(TELEMETRY_VECTOR));
    failures += expect_validation(
        malbolge_host_execution_telemetry_v1_validate_call(
            &frame, memory, sizeof(memory), registry, 2U, &telemetry),
        MALBOLGE_HOST_CAPABILITY_VALID);
    failures += expect_true(telemetry_matches_fixture(&telemetry));

    frame.operation = UINT16_C(1);
    failures += expect_validation(
        malbolge_host_execution_telemetry_v1_validate_call(
            &frame, memory, sizeof(memory), registry, 2U, &telemetry),
        MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD);
    frame.operation = MALBOLGE_HOST_EXECUTION_TELEMETRY_V1_OPERATION;
    frame.request_length -= UINT64_C(1);
    failures += expect_validation(
        malbolge_host_execution_telemetry_v1_validate_call(
            &frame, memory, sizeof(memory), registry, 2U, &telemetry),
        MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD);
    frame.request_length = (uint64_t)sizeof(TELEMETRY_VECTOR);
    frame.result_offset = UINT64_C(127);
    frame.result_capacity = UINT64_C(1);
    failures += expect_validation(
        malbolge_host_execution_telemetry_v1_validate_call(
            &frame, memory, sizeof(memory), registry, 2U, &telemetry),
        MALBOLGE_HOST_CAPABILITY_INVALID_PAYLOAD);

    {
        union TelemetryCallAlias {
            uint8_t memory[128];
            MalbolgeHostExecutionTelemetryV1 telemetry;
        } overlap = {0};
        memcpy(overlap.memory + 8U, TELEMETRY_VECTOR,
               sizeof(TELEMETRY_VECTOR));
        frame.result_offset = UINT64_C(8);
        frame.result_capacity = 0U;
        failures += expect_validation(
            malbolge_host_execution_telemetry_v1_validate_call(
                &frame, overlap.memory, sizeof(overlap.memory), registry, 2U,
                &overlap.telemetry),
            MALBOLGE_HOST_CAPABILITY_INVALID_ARGUMENT);
    }

    registry[0] = malbolge_host_execution_telemetry_v1_descriptor(false);
    frame.result_offset = UINT64_C(8);
    frame.result_capacity = 0U;
    failures += expect_validation(
        malbolge_host_execution_telemetry_v1_validate_call(
            &frame, memory, sizeof(memory), registry, 2U, &telemetry),
        MALBOLGE_HOST_CAPABILITY_UNAVAILABLE);
    return failures;
}

int main(void)
{
    int failures = 0;
    failures += test_mouse_payload();
    failures += test_mouse_call();
    failures += test_telemetry_payload();
    failures += test_telemetry_utf8();
    failures += test_telemetry_alias_and_capacity();
    failures += test_telemetry_call();
    return failures;
}
