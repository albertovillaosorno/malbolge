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
//   - Transport-neutral host-capability dispatch and publication regressions.
// - Must-Not:
//   - Perform real host effects or claim production runner integration.
// - Allows:
//   - Inputs: canonical request frames, guest bytes, and recording transports.
//   - Outputs: effect-order, response, guest-memory, and failure evidence.
//   - Side effects: deterministic in-process recording only.
// - Split-When:
//   - Real runner adapters require independently owned integration fixtures.
// - Merge-When:
//   - Another VM test owns this exact dispatch coordinator behavior.
// - Summary:
//   - Proves one validate-effect-commit path is independent of transport label.
// - Description:
//   - Exercises interpreter-, JIT-, and AOT-labeled recording adapters equally.
// - Usage:
//   - Collected through the VM integration-test target.
// - Defaults:
//   - Invalid requests cause no effect; invalid responses mutate no guest
//     bytes.
//

//! Transport-independent validate-effect-commit host-capability evidence.

use malbolge::{
    HOST_CAPABILITY_ABI_VERSION, HOST_CAPABILITY_FLAG_AVAILABLE,
    HOST_EXECUTION_TELEMETRY_CAPABILITY_ID, HOST_MONOTONIC_TIME_CAPABILITY_ID,
    HOST_MONOTONIC_TIME_V1_OPERATION, HOST_MONOTONIC_TIME_V1_VERSION,
    HOST_RELATIVE_MOUSE_CAPTURE_CAPABILITY_ID, HOST_SLEEP_CAPABILITY_ID,
    HostBuiltinCapabilityAvailability, HostCapabilityAvailability,
    HostCapabilityDescriptor, HostCapabilityDispatchError, HostCapabilityFrame,
    HostCapabilityInvocation, HostCapabilityStatus, HostCapabilityTransport,
    HostCapabilityTransportResponse, dispatch_builtin_host_capability,
    dispatch_host_capability, host_builtin_capability_registry,
    validate_host_capability_registry,
};

use super::{TestResult, check_equal};

const CAPABILITY_ID: u32 = 0x0000_0700;
const BUILTIN_REGISTRY_VECTOR: [u8; 64] = [
    0x00, 0x04, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0x00,
    0x01, 0x00, 0x10, 0x00, 0x01, 0x04, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00,
    0x03, 0x00, 0x00, 0x00, 0x01, 0x00, 0x10, 0x00, 0x00, 0x06, 0x00, 0x00,
    0x01, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01, 0x00, 0x10, 0x00,
    0x01, 0x06, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0x00,
    0x01, 0x00, 0x10, 0x00,
];
const CLOCK_RESULT: [u8; 8] = [8, 7, 6, 5, 4, 3, 2, 1];
const REQUEST_OFFSET: u64 = 8;
const REQUEST_LENGTH: u64 = 4;
const REQUEST_START: usize = 8;
const REQUEST_END: usize = 12;
const RESULT_OFFSET: u64 = 32;
const RESULT_CAPACITY: u64 = 8;
const RESULT_START: usize = 32;
const RESULT_END: usize = 35;
const RESULT_LENGTH: u64 = 3;
const REQUEST_BYTES: [u8; 4] = [1, 2, 3, 4];
const RESULT_BYTES: [u8; 3] = [9, 8, 7];
const DESCRIPTOR: HostCapabilityDescriptor = HostCapabilityDescriptor {
    capability_id: CAPABILITY_ID,
    minimum_version: 1,
    maximum_version: 1,
    flags: HOST_CAPABILITY_FLAG_AVAILABLE,
};
const REGISTRY: [HostCapabilityDescriptor; 1] = [DESCRIPTOR];

#[derive(Clone, Debug, Eq, PartialEq)]
struct RecordedInvocation {
    frame: HostCapabilityFrame,
    request: Vec<u8>,
}

#[derive(Clone, Debug)]
struct RecordingTransport {
    calls: Vec<RecordedInvocation>,
    response: Result<HostCapabilityTransportResponse, &'static str>,
}

impl RecordingTransport {
    fn complete(request: HostCapabilityFrame) -> Self {
        let mut response = request;
        response.status = HostCapabilityStatus::Complete;
        response.result_length = RESULT_LENGTH;
        Self {
            calls: Vec::new(),
            response: Ok(HostCapabilityTransportResponse {
                frame: response,
                staged_result: RESULT_BYTES.to_vec(),
            }),
        }
    }
}

impl HostCapabilityTransport for RecordingTransport {
    type Error = &'static str;

    fn invoke(
        &mut self,
        invocation: HostCapabilityInvocation<'_>,
    ) -> Result<HostCapabilityTransportResponse, Self::Error> {
        self.calls.push(RecordedInvocation {
            frame: invocation.frame,
            request: invocation.request.to_vec(),
        });
        self.response.clone()
    }
}

trait TierTestTransport: HostCapabilityTransport<Error = String> {
    fn call_ids(&self) -> &[u64];
}

#[derive(Default)]
struct InterpreterTestTransport {
    call_ids: Vec<u64>,
}

impl HostCapabilityTransport for InterpreterTestTransport {
    type Error = String;

    fn invoke(
        &mut self,
        invocation: HostCapabilityInvocation<'_>,
    ) -> Result<HostCapabilityTransportResponse, Self::Error> {
        self.call_ids.push(invocation.frame.call_id);
        let mut frame = invocation.frame;
        frame.result_length = RESULT_LENGTH;
        frame.status = HostCapabilityStatus::Complete;
        Ok(HostCapabilityTransportResponse {
            frame,
            staged_result: RESULT_BYTES.to_vec(),
        })
    }
}

impl TierTestTransport for InterpreterTestTransport {
    fn call_ids(&self) -> &[u64] {
        &self.call_ids
    }
}

#[derive(Default)]
struct JitTestTransport {
    call_ids: Vec<u64>,
}

impl HostCapabilityTransport for JitTestTransport {
    type Error = String;

    fn invoke(
        &mut self,
        invocation: HostCapabilityInvocation<'_>,
    ) -> Result<HostCapabilityTransportResponse, Self::Error> {
        self.call_ids.push(invocation.frame.call_id);
        let wire = invocation
            .frame
            .encode()
            .map_err(|error| format!("JIT frame encode: {error:?}"))?;
        let mut frame = HostCapabilityFrame::decode(&wire)
            .map_err(|error| format!("JIT frame decode: {error:?}"))?;
        frame.result_length = RESULT_LENGTH;
        frame.status = HostCapabilityStatus::Complete;
        Ok(HostCapabilityTransportResponse {
            frame,
            staged_result: RESULT_BYTES.to_vec(),
        })
    }
}

impl TierTestTransport for JitTestTransport {
    fn call_ids(&self) -> &[u64] {
        &self.call_ids
    }
}

#[derive(Default)]
struct AotTestTransport {
    call_ids: Vec<u64>,
}

impl HostCapabilityTransport for AotTestTransport {
    type Error = String;

    fn invoke(
        &mut self,
        invocation: HostCapabilityInvocation<'_>,
    ) -> Result<HostCapabilityTransportResponse, Self::Error> {
        self.call_ids.push(invocation.frame.call_id);
        let request = invocation.frame;
        let frame = HostCapabilityFrame {
            abi_version: request.abi_version,
            call_id: request.call_id,
            capability_id: request.capability_id,
            capability_version: request.capability_version,
            flags: request.flags,
            operation: request.operation,
            request_length: request.request_length,
            request_offset: request.request_offset,
            result_capacity: request.result_capacity,
            result_length: RESULT_LENGTH,
            result_offset: request.result_offset,
            status: HostCapabilityStatus::Complete,
        };
        Ok(HostCapabilityTransportResponse {
            frame,
            staged_result: RESULT_BYTES.to_vec(),
        })
    }
}

impl TierTestTransport for AotTestTransport {
    fn call_ids(&self) -> &[u64] {
        &self.call_ids
    }
}

#[derive(Debug, Eq, PartialEq)]
struct TierSequenceObservation {
    call_ids: Vec<u64>,
    memory: Vec<u8>,
    responses: Vec<HostCapabilityFrame>,
}

const fn request_frame() -> HostCapabilityFrame {
    HostCapabilityFrame {
        abi_version: HOST_CAPABILITY_ABI_VERSION,
        call_id: 42,
        capability_id: CAPABILITY_ID,
        capability_version: 1,
        flags: 0,
        operation: 3,
        request_length: REQUEST_LENGTH,
        request_offset: REQUEST_OFFSET,
        result_capacity: RESULT_CAPACITY,
        result_length: 0,
        result_offset: RESULT_OFFSET,
        status: HostCapabilityStatus::Pending,
    }
}

fn guest_memory() -> TestResult<Vec<u8>> {
    let mut memory = vec![0xa5; 64];
    let destination = memory
        .get_mut(REQUEST_START..REQUEST_END)
        .ok_or_else(|| String::from("fixture request range unavailable"))?;
    destination.copy_from_slice(&REQUEST_BYTES);
    Ok(memory)
}

const fn clock_request_frame() -> HostCapabilityFrame {
    HostCapabilityFrame {
        abi_version: HOST_CAPABILITY_ABI_VERSION,
        call_id: 73,
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

const fn available_builtin_registry() -> [HostCapabilityDescriptor; 4] {
    host_builtin_capability_registry(HostBuiltinCapabilityAvailability {
        monotonic_time: HostCapabilityAvailability::Available,
        relative_mouse: HostCapabilityAvailability::Available,
        sleep: HostCapabilityAvailability::Available,
        telemetry: HostCapabilityAvailability::Available,
    })
}

fn run_tier_sequence<Transport>(
    transport: &mut Transport,
) -> TestResult<TierSequenceObservation>
where
    Transport: TierTestTransport,
{
    let mut memory = guest_memory()?;
    let requests = [
        HostCapabilityFrame {
            call_id: 100,
            ..request_frame()
        },
        HostCapabilityFrame {
            call_id: 101,
            ..request_frame()
        },
    ];
    let mut responses = Vec::new();
    for request in requests {
        let response = dispatch_host_capability(
            &REGISTRY,
            request,
            &mut memory,
            transport,
        )
        .map_err(|error| format!("tier dispatch: {error:?}"))?;
        responses.push(response);
    }
    Ok(TierSequenceObservation {
        call_ids: transport.call_ids().to_vec(),
        memory,
        responses,
    })
}

#[test]
fn invalid_request_rejects_before_transport_effect() -> TestResult {
    let mut request = request_frame();
    request.result_offset = 10;
    let mut memory = guest_memory()?;
    let baseline = memory.clone();
    let mut transport = RecordingTransport::complete(request);

    let result = dispatch_host_capability(
        &REGISTRY,
        request,
        &mut memory,
        &mut transport,
    );

    check_equal(
        &result,
        &Err(HostCapabilityDispatchError::Contract(
            malbolge::HostCapabilityError::InvalidRange,
        )),
        "overlapping request/result rejection",
    )?;
    check_equal(&transport.calls.len(), &0, "pre-effect transport count")?;
    check_equal(&memory, &baseline, "pre-effect guest memory")
}

#[test]
fn valid_dispatch_publishes_only_staged_result() -> TestResult {
    let request = request_frame();
    let mut memory = guest_memory()?;
    let mut expected = memory.clone();
    let result = expected
        .get_mut(RESULT_START..RESULT_END)
        .ok_or_else(|| String::from("fixture result range unavailable"))?;
    result.copy_from_slice(&RESULT_BYTES);
    let mut transport = RecordingTransport::complete(request);

    let response = dispatch_host_capability(
        &REGISTRY,
        request,
        &mut memory,
        &mut transport,
    );

    let expected_frame = transport
        .response
        .as_ref()
        .map_err(|error| format!("fixture response: {error}"))?
        .frame;
    check_equal(&response, &Ok(expected_frame), "validated response")?;
    check_equal(&memory, &expected, "atomic result publication")?;
    check_equal(&transport.calls.len(), &1, "transport invocation count")?;
    let call = transport
        .calls
        .first()
        .ok_or_else(|| String::from("recorded invocation missing"))?;
    check_equal(&call.frame, &request, "transport frame identity")?;
    check_equal(
        call.request.as_slice(),
        REQUEST_BYTES.as_slice(),
        "transport request bytes",
    )
}

#[test]
fn invalid_response_keeps_guest_memory_unchanged() -> TestResult {
    let request = request_frame();
    let mut memory = guest_memory()?;
    let baseline = memory.clone();
    let mut transport = RecordingTransport::complete(request);
    let response = transport
        .response
        .as_mut()
        .map_err(|error| format!("fixture response: {error}"))?;
    response.frame.call_id += 1;

    let result = dispatch_host_capability(
        &REGISTRY,
        request,
        &mut memory,
        &mut transport,
    );

    check_equal(
        &result,
        &Err(HostCapabilityDispatchError::Contract(
            malbolge::HostCapabilityError::InvalidResponse,
        )),
        "response identity rejection",
    )?;
    check_equal(&transport.calls.len(), &1, "post-effect transport count")?;
    check_equal(&memory, &baseline, "invalid response guest memory")
}

#[test]
fn transport_failure_is_distinct_and_atomic() -> TestResult {
    let request = request_frame();
    let mut memory = guest_memory()?;
    let baseline = memory.clone();
    let mut transport = RecordingTransport {
        calls: Vec::new(),
        response: Err("runner unavailable"),
    };

    let result = dispatch_host_capability(
        &REGISTRY,
        request,
        &mut memory,
        &mut transport,
    );

    check_equal(
        &result,
        &Err(HostCapabilityDispatchError::Transport("runner unavailable")),
        "transport failure",
    )?;
    check_equal(&transport.calls.len(), &1, "transport failure call count")?;
    check_equal(&memory, &baseline, "transport failure guest memory")
}

#[test]
fn distinct_tier_transports_preserve_semantics_and_effect_order() -> TestResult
{
    let mut interpreter = InterpreterTestTransport::default();
    let mut jit = JitTestTransport::default();
    let mut aot = AotTestTransport::default();

    let reference = run_tier_sequence(&mut interpreter)?;
    let jit_observation = run_tier_sequence(&mut jit)?;
    let aot_observation = run_tier_sequence(&mut aot)?;

    check_equal(&jit_observation, &reference, "JIT transport semantics")?;
    check_equal(&aot_observation, &reference, "AOT transport semantics")?;
    check_equal(
        reference.call_ids.as_slice(),
        &[100, 101],
        "tier effect ordering",
    )
}

#[test]
fn builtin_registry_has_stable_sorted_semantic_identity() -> TestResult {
    let available =
        host_builtin_capability_registry(HostBuiltinCapabilityAvailability {
            monotonic_time: HostCapabilityAvailability::Available,
            relative_mouse: HostCapabilityAvailability::Available,
            sleep: HostCapabilityAvailability::Available,
            telemetry: HostCapabilityAvailability::Available,
        });
    let selective =
        host_builtin_capability_registry(HostBuiltinCapabilityAvailability {
            monotonic_time: HostCapabilityAvailability::Unavailable,
            relative_mouse: HostCapabilityAvailability::Available,
            sleep: HostCapabilityAvailability::Available,
            telemetry: HostCapabilityAvailability::Unavailable,
        });

    validate_host_capability_registry(&available)
        .map_err(|error| format!("available registry: {error:?}"))?;
    validate_host_capability_registry(&selective)
        .map_err(|error| format!("selective registry: {error:?}"))?;
    let expected_ids = [
        HOST_MONOTONIC_TIME_CAPABILITY_ID,
        HOST_SLEEP_CAPABILITY_ID,
        HOST_EXECUTION_TELEMETRY_CAPABILITY_ID,
        HOST_RELATIVE_MOUSE_CAPTURE_CAPABILITY_ID,
    ];
    let observed_ids = available.map(|descriptor| descriptor.capability_id);
    check_equal(&observed_ids, &expected_ids, "built-in registry identity")?;
    let mut encoded = Vec::new();
    for descriptor in available {
        let wire = descriptor.encode().map_err(|error| {
            format!("built-in descriptor encode: {error:?}")
        })?;
        encoded.extend_from_slice(&wire);
    }
    check_equal(
        encoded.as_slice(),
        BUILTIN_REGISTRY_VECTOR.as_slice(),
        "built-in registry wire vector",
    )?;
    let selective_ids = selective.map(|descriptor| descriptor.capability_id);
    check_equal(
        &selective_ids,
        &expected_ids,
        "availability-independent identity",
    )?;
    check_equal(
        &(selective[0].flags & HOST_CAPABILITY_FLAG_AVAILABLE),
        &0,
        "disabled monotonic-time flag",
    )?;
    check_equal(
        &(selective[2].flags & HOST_CAPABILITY_FLAG_AVAILABLE),
        &0,
        "disabled telemetry flag",
    )
}

#[test]
fn builtin_dispatch_rejects_unknown_before_transport() -> TestResult {
    let request = request_frame();
    let mut memory = guest_memory()?;
    let baseline = memory.clone();
    let mut transport = RecordingTransport::complete(request);

    let result = dispatch_builtin_host_capability(
        &REGISTRY,
        request,
        &mut memory,
        &mut transport,
    );

    check_equal(
        &result,
        &Err(HostCapabilityDispatchError::Contract(
            malbolge::HostCapabilityError::UnknownCapability,
        )),
        "unknown built-in rejection",
    )?;
    check_equal(&transport.calls.len(), &0, "unknown transport count")?;
    check_equal(&memory, &baseline, "unknown guest memory")
}

#[test]
fn builtin_clock_rejects_short_result_before_publish() -> TestResult {
    let registry = available_builtin_registry();
    let request = clock_request_frame();
    let mut memory = guest_memory()?;
    let baseline = memory.clone();
    let mut response = request;
    response.status = HostCapabilityStatus::Complete;
    response.result_length = 7;
    let mut transport = RecordingTransport {
        calls: Vec::new(),
        response: Ok(HostCapabilityTransportResponse {
            frame: response,
            staged_result: CLOCK_RESULT[..7].to_vec(),
        }),
    };

    let result = dispatch_builtin_host_capability(
        &registry,
        request,
        &mut memory,
        &mut transport,
    );

    check_equal(
        &result,
        &Err(HostCapabilityDispatchError::Contract(
            malbolge::HostCapabilityError::InvalidResponse,
        )),
        "short clock result rejection",
    )?;
    check_equal(&transport.calls.len(), &1, "short clock transport count")?;
    check_equal(&memory, &baseline, "short clock guest memory")
}

#[test]
fn builtin_clock_commits_exact_result_atomically() -> TestResult {
    let registry = available_builtin_registry();
    let request = clock_request_frame();
    let mut memory = guest_memory()?;
    let mut expected = memory.clone();
    let destination = expected
        .get_mut(RESULT_START..RESULT_START + CLOCK_RESULT.len())
        .ok_or_else(|| String::from("clock result fixture unavailable"))?;
    destination.copy_from_slice(&CLOCK_RESULT);
    let mut response = request;
    response.status = HostCapabilityStatus::Complete;
    response.result_length = 8;
    let mut transport = RecordingTransport {
        calls: Vec::new(),
        response: Ok(HostCapabilityTransportResponse {
            frame: response,
            staged_result: CLOCK_RESULT.to_vec(),
        }),
    };

    let result = dispatch_builtin_host_capability(
        &registry,
        request,
        &mut memory,
        &mut transport,
    );

    check_equal(&result, &Ok(response), "clock dispatch response")?;
    check_equal(&transport.calls.len(), &1, "clock transport count")?;
    check_equal(&memory, &expected, "clock atomic publication")
}
