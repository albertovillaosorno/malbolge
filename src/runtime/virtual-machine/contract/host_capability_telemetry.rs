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
//   - Version-one optional execution-activity telemetry capability schema.
// - Must-Not:
//   - Perform UI/logging effects or let telemetry alter guest VM semantics.
// - Allows:
//   - Inputs: generic frames, guest bytes, and semantic capability registries.
//   - Outputs: canonical UTF-8 telemetry payloads and validated borrowed views.
//   - Side effects: none.
// - Split-When:
//   - Split when another observation family needs independent schema ownership.
// - Merge-When:
//   - Merge when built-in capability schemas become generated registry data.
// - Summary:
//   - Stable pointer-free execution telemetry host-capability schema.
// - Description:
//   - Promotes historical opaque ID 0x0600 into a canonical version-one record.
// - Usage:
//   - Used only when telemetry discovery succeeds; absence remains semantically
//     inert.
// - Defaults:
//   - Noncanonical spans, empty/NUL text, UTF-8 errors, and flag drift fail
//     closed.
//

//! Version-one optional execution telemetry capability schema.

use std::str::from_utf8;

use super::host_capability::{
    HOST_CAPABILITY_FLAG_AVAILABLE, HostCapabilityDescriptor,
    HostCapabilityError, HostCapabilityFrame, HostCapabilitySpan,
    discover_host_capability,
};

/// Stable opaque capability ID for optional execution-activity telemetry.
pub const HOST_EXECUTION_TELEMETRY_CAPABILITY_ID: u32 = 0x0000_0600;
/// Fixed header size before canonical telemetry text bytes.
pub const HOST_EXECUTION_TELEMETRY_V1_HEADER_SIZE: usize = 64;
/// Version-one operation number in this single-operation capability family.
pub const HOST_EXECUTION_TELEMETRY_V1_OPERATION: u16 = 0;
/// Stable semantic version for execution telemetry.
pub const HOST_EXECUTION_TELEMETRY_V1_VERSION: u16 = 1;

const HEADER_SIZE_U64: u64 = 64;
const INSTRUCTION_SPAN_OFFSET: usize = 48;
const LANGUAGE_SPAN_OFFSET: usize = 16;
const LOCATION_OFFSET: usize = 8;
const SOURCE_SPAN_OFFSET: usize = 32;

/// Borrowed, validated execution-activity telemetry record.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct HostExecutionTelemetryV1<'payload> {
    /// Active instruction text at the reported location.
    pub instruction: &'payload str,
    /// Language identifier such as `C` or `MALBOLGE`.
    pub language: &'payload str,
    /// Language-defined source line, cell, or instruction address.
    pub location: u64,
    /// Stable source or artifact identity.
    pub source: &'payload str,
}

/// Builds the semantic registry descriptor for one runner.
#[must_use]
pub const fn host_execution_telemetry_v1_descriptor(
    available: bool,
) -> HostCapabilityDescriptor {
    HostCapabilityDescriptor {
        capability_id: HOST_EXECUTION_TELEMETRY_CAPABILITY_ID,
        flags: if available {
            HOST_CAPABILITY_FLAG_AVAILABLE
        } else {
            0
        },
        maximum_version: HOST_EXECUTION_TELEMETRY_V1_VERSION,
        minimum_version: HOST_EXECUTION_TELEMETRY_V1_VERSION,
    }
}

/// Decodes and validates one canonical execution-telemetry payload.
///
/// # Errors
///
/// Returns [`HostCapabilityError::InvalidPayload`] when the fixed header,
/// canonical text spans, UTF-8, or NUL exclusion rules are violated.
pub fn decode_host_execution_telemetry_v1(
    payload: &[u8],
) -> Result<HostExecutionTelemetryV1<'_>, HostCapabilityError> {
    if payload.len() < HOST_EXECUTION_TELEMETRY_V1_HEADER_SIZE
        || read_u32(payload, 0)? != 0
        || read_u32(payload, 4)? != 0
    {
        return Err(HostCapabilityError::InvalidPayload);
    }
    let language_span = decode_span(payload, LANGUAGE_SPAN_OFFSET)?;
    let source_span = decode_span(payload, SOURCE_SPAN_OFFSET)?;
    let instruction_span = decode_span(payload, INSTRUCTION_SPAN_OFFSET)?;
    validate_canonical_spans(
        payload,
        language_span,
        source_span,
        instruction_span,
    )?;
    let language = decode_text(language_span.bytes(payload, HEADER_SIZE_U64)?)?;
    let source = decode_text(source_span.bytes(payload, HEADER_SIZE_U64)?)?;
    let instruction =
        decode_text(instruction_span.bytes(payload, HEADER_SIZE_U64)?)?;
    Ok(HostExecutionTelemetryV1 {
        instruction,
        language,
        location: read_u64(payload, LOCATION_OFFSET)?,
        source,
    })
}

/// Encodes one execution-telemetry record canonically.
///
/// # Errors
///
/// Returns [`HostCapabilityError::InvalidPayload`] for empty/NUL-containing
/// text or if the combined payload length cannot be represented safely.
pub fn encode_host_execution_telemetry_v1(
    telemetry: HostExecutionTelemetryV1<'_>,
) -> Result<Vec<u8>, HostCapabilityError> {
    validate_text(telemetry.language)?;
    validate_text(telemetry.source)?;
    validate_text(telemetry.instruction)?;
    let language_length = telemetry.language.len();
    let source_length = telemetry.source.len();
    let instruction_length = telemetry.instruction.len();
    let source_offset = HOST_EXECUTION_TELEMETRY_V1_HEADER_SIZE
        .checked_add(language_length)
        .ok_or(HostCapabilityError::InvalidPayload)?;
    let instruction_offset = source_offset
        .checked_add(source_length)
        .ok_or(HostCapabilityError::InvalidPayload)?;
    let payload_length = instruction_offset
        .checked_add(instruction_length)
        .ok_or(HostCapabilityError::InvalidPayload)?;
    let language_span =
        host_span(HOST_EXECUTION_TELEMETRY_V1_HEADER_SIZE, language_length)?;
    let source_span = host_span(source_offset, source_length)?;
    let instruction_span = host_span(instruction_offset, instruction_length)?;
    let mut payload = vec![0u8; payload_length];
    write_u64(&mut payload, LOCATION_OFFSET, telemetry.location)?;
    write_span(&mut payload, LANGUAGE_SPAN_OFFSET, language_span)?;
    write_span(&mut payload, SOURCE_SPAN_OFFSET, source_span)?;
    write_span(&mut payload, INSTRUCTION_SPAN_OFFSET, instruction_span)?;
    copy_bytes(
        &mut payload,
        HOST_EXECUTION_TELEMETRY_V1_HEADER_SIZE,
        telemetry.language.as_bytes(),
    )?;
    copy_bytes(&mut payload, source_offset, telemetry.source.as_bytes())?;
    copy_bytes(
        &mut payload,
        instruction_offset,
        telemetry.instruction.as_bytes(),
    )?;
    Ok(payload)
}

/// Admits and decodes one execution-telemetry call before any host effect.
///
/// # Errors
///
/// Returns generic frame/registry/range failures first, then schema failures
/// for identity, operation, behavior flags, result shape, or request bytes.
pub fn validate_host_execution_telemetry_v1_call<'memory>(
    frame: HostCapabilityFrame,
    guest_memory: &'memory [u8],
    registry: &[HostCapabilityDescriptor],
) -> Result<HostExecutionTelemetryV1<'memory>, HostCapabilityError> {
    let memory_size = u64::try_from(guest_memory.len())
        .map_err(|_error| HostCapabilityError::InvalidRange)?;
    frame.validate_request(memory_size, registry)?;
    let descriptor = discover_host_capability(
        registry,
        frame.capability_id,
        frame.capability_version,
    )?;
    if frame.capability_id != HOST_EXECUTION_TELEMETRY_CAPABILITY_ID
        || frame.capability_version != HOST_EXECUTION_TELEMETRY_V1_VERSION
        || frame.operation != HOST_EXECUTION_TELEMETRY_V1_OPERATION
        || frame.flags != 0
        || frame.request_length < HEADER_SIZE_U64
        || frame.result_capacity != 0
    {
        return Err(HostCapabilityError::InvalidPayload);
    }
    if descriptor.flags != HOST_CAPABILITY_FLAG_AVAILABLE {
        return Err(HostCapabilityError::InvalidRegistry);
    }
    decode_host_execution_telemetry_v1(request_payload(frame, guest_memory)?)
}

fn copy_bytes(
    payload: &mut [u8],
    offset: usize,
    bytes: &[u8],
) -> Result<(), HostCapabilityError> {
    let end = offset
        .checked_add(bytes.len())
        .ok_or(HostCapabilityError::InvalidPayload)?;
    let slot = payload
        .get_mut(offset..end)
        .ok_or(HostCapabilityError::InvalidPayload)?;
    slot.copy_from_slice(bytes);
    Ok(())
}

fn decode_span(
    payload: &[u8],
    offset: usize,
) -> Result<HostCapabilitySpan, HostCapabilityError> {
    let end = offset
        .checked_add(16)
        .ok_or(HostCapabilityError::InvalidPayload)?;
    HostCapabilitySpan::decode(
        payload
            .get(offset..end)
            .ok_or(HostCapabilityError::InvalidPayload)?,
    )
}

fn decode_text(bytes: &[u8]) -> Result<&str, HostCapabilityError> {
    if bytes.is_empty() || bytes.contains(&0) {
        return Err(HostCapabilityError::InvalidPayload);
    }
    from_utf8(bytes).map_err(|_error| HostCapabilityError::InvalidPayload)
}

fn host_span(
    offset: usize,
    length: usize,
) -> Result<HostCapabilitySpan, HostCapabilityError> {
    Ok(HostCapabilitySpan {
        length: u64::try_from(length)
            .map_err(|_error| HostCapabilityError::InvalidPayload)?,
        offset: u64::try_from(offset)
            .map_err(|_error| HostCapabilityError::InvalidPayload)?,
    })
}

fn read_u32(payload: &[u8], offset: usize) -> Result<u32, HostCapabilityError> {
    let end = offset
        .checked_add(4)
        .ok_or(HostCapabilityError::InvalidPayload)?;
    let bytes: [u8; 4] = payload
        .get(offset..end)
        .ok_or(HostCapabilityError::InvalidPayload)?
        .try_into()
        .map_err(|_error| HostCapabilityError::InvalidPayload)?;
    Ok(u32::from_le_bytes(bytes))
}

fn read_u64(payload: &[u8], offset: usize) -> Result<u64, HostCapabilityError> {
    let end = offset
        .checked_add(8)
        .ok_or(HostCapabilityError::InvalidPayload)?;
    let bytes: [u8; 8] = payload
        .get(offset..end)
        .ok_or(HostCapabilityError::InvalidPayload)?
        .try_into()
        .map_err(|_error| HostCapabilityError::InvalidPayload)?;
    Ok(u64::from_le_bytes(bytes))
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

fn validate_canonical_spans(
    payload: &[u8],
    language: HostCapabilitySpan,
    source: HostCapabilitySpan,
    instruction: HostCapabilitySpan,
) -> Result<(), HostCapabilityError> {
    let payload_length = u64::try_from(payload.len())
        .map_err(|_error| HostCapabilityError::InvalidPayload)?;
    language.validate(payload_length, HEADER_SIZE_U64)?;
    source.validate(payload_length, HEADER_SIZE_U64)?;
    instruction.validate(payload_length, HEADER_SIZE_U64)?;
    if language.length == 0 || source.length == 0 || instruction.length == 0 {
        return Err(HostCapabilityError::InvalidPayload);
    }
    let language_end = language
        .offset
        .checked_add(language.length)
        .ok_or(HostCapabilityError::InvalidPayload)?;
    let source_end = source
        .offset
        .checked_add(source.length)
        .ok_or(HostCapabilityError::InvalidPayload)?;
    let instruction_end = instruction
        .offset
        .checked_add(instruction.length)
        .ok_or(HostCapabilityError::InvalidPayload)?;
    if language.offset != HEADER_SIZE_U64
        || source.offset != language_end
        || instruction.offset != source_end
        || instruction_end != payload_length
    {
        return Err(HostCapabilityError::InvalidPayload);
    }
    Ok(())
}

fn validate_text(text: &str) -> Result<(), HostCapabilityError> {
    if text.is_empty() || text.as_bytes().contains(&0) {
        Err(HostCapabilityError::InvalidPayload)
    } else {
        Ok(())
    }
}

fn write_span(
    payload: &mut [u8],
    offset: usize,
    span: HostCapabilitySpan,
) -> Result<(), HostCapabilityError> {
    let end = offset
        .checked_add(16)
        .ok_or(HostCapabilityError::InvalidPayload)?;
    let slot = payload
        .get_mut(offset..end)
        .ok_or(HostCapabilityError::InvalidPayload)?;
    slot.copy_from_slice(&span.encode());
    Ok(())
}

fn write_u64(
    payload: &mut [u8],
    offset: usize,
    value: u64,
) -> Result<(), HostCapabilityError> {
    let end = offset
        .checked_add(8)
        .ok_or(HostCapabilityError::InvalidPayload)?;
    let slot = payload
        .get_mut(offset..end)
        .ok_or(HostCapabilityError::InvalidPayload)?;
    slot.copy_from_slice(&value.to_le_bytes());
    Ok(())
}
