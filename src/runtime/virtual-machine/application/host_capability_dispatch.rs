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
//   - Validate-effect-commit orchestration for semantic host capabilities.
// - Must-Not:
//   - Let transports mutate guest memory or publish an unvalidated response.
// - Allows:
//   - Inputs: registry, request frame, guest memory, and outbound transport.
//   - Outputs: one validated response frame and atomic guest result
//     publication.
//   - Side effects: one transport invocation after complete request admission.
// - Split-When:
//   - Async or cancellable dispatch requires another lifecycle coordinator.
// - Merge-When:
//   - One coordinator owns synchronous capability effect ordering everywhere.
// - Summary:
//   - Validates before host effects and commits only a valid staged response.
// - Description:
//   - Gives interpreter and native tiers one identical semantic dispatch path.
// - Usage:
//   - Called by runners after decoding a version-one guest capability frame.
// - Defaults:
//   - Contract rejection happens before effects; response rejection is atomic.
//

//! Transport-independent validate-effect-commit host-capability dispatcher.

use crate::host_capability::{
    HostCapabilityDescriptor, HostCapabilityError, HostCapabilityFrame,
    HostCapabilityResponseBuffers, commit_host_capability_response,
    validate_host_capability_response,
};
use crate::host_capability_mouse::{
    HOST_RELATIVE_MOUSE_CAPTURE_CAPABILITY_ID,
    host_relative_mouse_capture_v1_descriptor,
    validate_host_relative_mouse_capture_v1_call,
};
use crate::host_capability_port::{
    HostCapabilityInvocation, HostCapabilityTransport,
    HostCapabilityTransportResponse,
};
use crate::host_capability_telemetry::{
    HOST_EXECUTION_TELEMETRY_CAPABILITY_ID,
    host_execution_telemetry_v1_descriptor,
    validate_host_execution_telemetry_v1_call,
};
use crate::host_capability_time::{
    HOST_MONOTONIC_TIME_CAPABILITY_ID, HOST_SLEEP_CAPABILITY_ID,
    host_monotonic_time_v1_descriptor, host_sleep_v1_descriptor,
    validate_host_monotonic_time_v1_call,
    validate_host_monotonic_time_v1_result, validate_host_sleep_v1_call,
};

/// Number of version-one built-in capability descriptor families.
pub const HOST_BUILTIN_CAPABILITY_COUNT: usize = 4;

/// Explicit availability state for one semantic host capability.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub enum HostCapabilityAvailability {
    /// The runner provides this capability with its declared semantics.
    Available,
    /// The runner does not provide this capability.
    #[default]
    Unavailable,
}

impl HostCapabilityAvailability {
    const fn is_available(self) -> bool {
        matches!(self, Self::Available)
    }
}

/// Runner-selected availability for each canonical built-in capability.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct HostBuiltinCapabilityAvailability {
    /// Monotonic nanosecond observation availability.
    pub monotonic_time: HostCapabilityAvailability,
    /// Guest-directed relative mouse capture availability.
    pub relative_mouse: HostCapabilityAvailability,
    /// Relative-duration sleep availability.
    pub sleep: HostCapabilityAvailability,
    /// Optional execution telemetry availability.
    pub telemetry: HostCapabilityAvailability,
}

/// Failure from semantic admission/commit or the selected host transport.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum HostCapabilityDispatchError<TransportError> {
    /// Guest ABI, registry, range, status, or response validation failed.
    Contract(HostCapabilityError),
    /// The selected host-effect transport failed after request admission.
    Transport(TransportError),
}

/// Result of one synchronous transport-neutral host-capability dispatch.
pub type HostCapabilityDispatchResult<TransportError> =
    Result<HostCapabilityFrame, HostCapabilityDispatchError<TransportError>>;

type HostCapabilityTransportInvocationResult<Transport> = Result<
    HostCapabilityTransportResponse,
    HostCapabilityDispatchError<<Transport as HostCapabilityTransport>::Error>,
>;

impl<TransportError> From<HostCapabilityError>
    for HostCapabilityDispatchError<TransportError>
{
    fn from(error: HostCapabilityError) -> Self {
        Self::Contract(error)
    }
}

fn request_bytes(
    request: HostCapabilityFrame,
    guest_memory: &[u8],
) -> Result<&[u8], HostCapabilityError> {
    let offset = usize::try_from(request.request_offset)
        .map_err(|_error| HostCapabilityError::InvalidRange)?;
    let length = usize::try_from(request.request_length)
        .map_err(|_error| HostCapabilityError::InvalidRange)?;
    let end = offset
        .checked_add(length)
        .ok_or(HostCapabilityError::InvalidRange)?;
    guest_memory
        .get(offset..end)
        .ok_or(HostCapabilityError::InvalidRange)
}

/// Returns the canonical sorted registry for currently implemented built-ins.
///
/// Availability is transport policy. Semantic identity, version ranges, and
/// descriptor order remain identical across interpreter, JIT, and AOT runners.
#[must_use]
pub const fn host_builtin_capability_registry(
    availability: HostBuiltinCapabilityAvailability,
) -> [HostCapabilityDescriptor; HOST_BUILTIN_CAPABILITY_COUNT] {
    [
        host_monotonic_time_v1_descriptor(
            availability.monotonic_time.is_available(),
        ),
        host_sleep_v1_descriptor(availability.sleep.is_available()),
        host_execution_telemetry_v1_descriptor(
            availability.telemetry.is_available(),
        ),
        host_relative_mouse_capture_v1_descriptor(
            availability.relative_mouse.is_available(),
        ),
    ]
}

fn invoke_transport<Transport>(
    request: HostCapabilityFrame,
    guest_memory: &[u8],
    transport: &mut Transport,
) -> HostCapabilityTransportInvocationResult<Transport>
where
    Transport: HostCapabilityTransport,
{
    let request_payload = request_bytes(request, guest_memory)?;
    transport
        .invoke(HostCapabilityInvocation {
            frame: request,
            request: request_payload,
        })
        .map_err(HostCapabilityDispatchError::Transport)
}

fn validate_builtin_request(
    request: HostCapabilityFrame,
    guest_memory: &[u8],
    registry: &[HostCapabilityDescriptor],
) -> Result<(), HostCapabilityError> {
    match request.capability_id {
        HOST_EXECUTION_TELEMETRY_CAPABILITY_ID => {
            let _telemetry = validate_host_execution_telemetry_v1_call(
                request,
                guest_memory,
                registry,
            )?;
            Ok(())
        },
        HOST_MONOTONIC_TIME_CAPABILITY_ID => {
            let memory_size = u64::try_from(guest_memory.len())
                .map_err(|_error| HostCapabilityError::InvalidRange)?;
            validate_host_monotonic_time_v1_call(request, memory_size, registry)
        },
        HOST_RELATIVE_MOUSE_CAPTURE_CAPABILITY_ID => {
            let _capture = validate_host_relative_mouse_capture_v1_call(
                request,
                guest_memory,
                registry,
            )?;
            Ok(())
        },
        HOST_SLEEP_CAPABILITY_ID => {
            let _duration =
                validate_host_sleep_v1_call(request, guest_memory, registry)?;
            Ok(())
        },
        _ => Err(HostCapabilityError::UnknownCapability),
    }
}

fn validate_builtin_response(
    request: HostCapabilityFrame,
    response: &HostCapabilityTransportResponse,
    guest_memory_size: u64,
    registry: &[HostCapabilityDescriptor],
) -> Result<(), HostCapabilityError> {
    validate_host_capability_response(
        request,
        response.frame,
        guest_memory_size,
        registry,
    )?;
    if request.capability_id == HOST_MONOTONIC_TIME_CAPABILITY_ID {
        let _time = validate_host_monotonic_time_v1_result(
            response.frame,
            &response.staged_result,
        )?;
        return Ok(());
    }
    let expected = usize::try_from(response.frame.result_length)
        .map_err(|_error| HostCapabilityError::InvalidResponse)?;
    if response.staged_result.len() != expected {
        return Err(HostCapabilityError::InvalidResponse);
    }
    Ok(())
}

/// Executes one canonical built-in capability with schema-aware admission.
///
/// The built-in path validates the selected capability request before the host
/// effect and validates capability-specific result shape before guest memory is
/// mutated. Unknown capability IDs fail closed instead of falling through to a
/// transport.
///
/// # Errors
///
/// Returns a schema/framing failure before effects, a transport-local failure,
/// or a response/schema failure before atomic guest-result publication.
pub fn dispatch_builtin_host_capability<Transport>(
    registry: &[HostCapabilityDescriptor],
    request: HostCapabilityFrame,
    guest_memory: &mut [u8],
    transport: &mut Transport,
) -> HostCapabilityDispatchResult<Transport::Error>
where
    Transport: HostCapabilityTransport,
{
    validate_builtin_request(request, guest_memory, registry)?;
    let guest_memory_size = u64::try_from(guest_memory.len())
        .map_err(|_error| HostCapabilityError::InvalidRange)?;
    let response = invoke_transport(request, guest_memory, transport)?;
    validate_builtin_response(request, &response, guest_memory_size, registry)?;
    commit_host_capability_response(
        request,
        response.frame,
        registry,
        HostCapabilityResponseBuffers {
            guest_memory,
            staged_result: &response.staged_result,
        },
    )?;
    Ok(response.frame)
}

/// Executes one synchronous capability call through a replaceable transport.
///
/// Request validation completes before `transport.invoke()` can observe the
/// call. The transport receives immutable request bytes and cannot mutate guest
/// memory. Its staged response is validated completely before result bytes are
/// published atomically to the guest result range.
///
/// # Errors
///
/// Returns a contract failure before effects for invalid requests, a transport
/// failure after admission, or a contract failure without guest mutation when
/// the staged response is invalid.
pub fn dispatch_host_capability<Transport>(
    registry: &[HostCapabilityDescriptor],
    request: HostCapabilityFrame,
    guest_memory: &mut [u8],
    transport: &mut Transport,
) -> HostCapabilityDispatchResult<Transport::Error>
where
    Transport: HostCapabilityTransport,
{
    let guest_memory_size = u64::try_from(guest_memory.len())
        .map_err(|_error| HostCapabilityError::InvalidRange)?;
    request.validate_request(guest_memory_size, registry)?;
    let response = invoke_transport(request, guest_memory, transport)?;
    commit_host_capability_response(
        request,
        response.frame,
        registry,
        HostCapabilityResponseBuffers {
            guest_memory,
            staged_result: &response.staged_result,
        },
    )?;
    Ok(response.frame)
}
