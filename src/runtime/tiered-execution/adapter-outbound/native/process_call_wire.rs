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
//   - Transport-neutral binary framing for process-isolated native calls.
// - Must-Not:
//   - Spawn processes, map executable memory, invoke code, or admit semantics.
// - Allows:
//   - Inputs: pointer-free native call requests and responses.
//   - Outputs: exact MBNPC1 bytes or bounded decoded transfer evidence.
//   - Side effects: process-local owned allocation only.
// - Split-When:
//   - A new wire version needs incompatible fields or framing.
// - Merge-When:
//   - One concrete process transport becomes the sole protocol authority.
// - Summary:
//   - Frames pointer-free native call transfer without trusting response sizes.
// - Description:
//   - Response payload lengths derive from the original admitted request.
// - Usage:
//   - A process adapter encodes requests and bounds/decodes child responses.
// - Defaults:
//   - Invalid magic, identity, shape, flags, truncation, or trailing data
//     fails.
//

//! Transport-neutral MBNPC1 framing for process-isolated native calls.

use std::fmt::{Display, Formatter, Result as FormatResult};

use super::lifecycle::NativeExecutableMappingId;
use super::process_call::{
    NativeProcessCallRequest, NativeProcessCallResponse, NativeProcessCallState,
};

/// Stable magic prefix for native process call protocol version 1.
pub const NATIVE_PROCESS_CALL_WIRE_MAGIC: [u8; 8] = *b"MBNPC1\0\0";

/// Fixed bytes before the request memory/input/output payloads.
pub const NATIVE_PROCESS_CALL_REQUEST_FIXED_BYTES: usize = 69;
/// Fixed bytes before the response memory/output payloads.
pub const NATIVE_PROCESS_CALL_RESPONSE_FIXED_BYTES: usize = 74;

/// Failure while encoding or decoding the MBNPC1 transfer contract.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeProcessCallWireError {
    /// A declared capacity cannot be represented or its byte size overflowed.
    CounterOverflow,
    /// The request input payload differs from its scalar input capacity.
    InputLength,
    /// A mapping identity decoded as zero.
    MappingIdentity,
    /// The memory payload differs from the required guest-memory capacity.
    MemoryLength,
    /// The output payload differs from the required output capacity.
    OutputLength,
    /// The response pointer-integrity field is not canonical boolean encoding.
    PointerFlag(u8),
    /// The encoded payload ends before all required fields are available.
    ReadFailure,
    /// Request bytes begin with a different protocol magic.
    RequestMagic,
    /// Response bytes begin with a different protocol magic.
    ResponseMagic,
    /// Bytes remain after the complete declared payload.
    TrailingBytes,
}

#[derive(Clone, Copy, Debug)]
struct WireReader<'bytes> {
    bytes: &'bytes [u8],
    offset: usize,
}

impl Display for NativeProcessCallWireError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::CounterOverflow => {
                f.write_str("native process wire counter overflowed")
            },
            Self::InputLength => {
                f.write_str("native process wire input length drifted")
            },
            Self::MappingIdentity => {
                f.write_str("native process wire mapping identity is zero")
            },
            Self::MemoryLength => {
                f.write_str("native process wire memory length drifted")
            },
            Self::OutputLength => {
                f.write_str("native process wire output length drifted")
            },
            Self::PointerFlag(value) => write!(
                f,
                "native process wire pointer-integrity flag {value} is invalid"
            ),
            Self::ReadFailure => {
                f.write_str("native process wire payload is truncated")
            },
            Self::RequestMagic => {
                f.write_str("native process wire request magic mismatch")
            },
            Self::ResponseMagic => {
                f.write_str("native process wire response magic mismatch")
            },
            Self::TrailingBytes => {
                f.write_str("native process wire payload has trailing bytes")
            },
        }
    }
}

impl<'bytes> WireReader<'bytes> {
    const fn finish(self) -> Result<(), NativeProcessCallWireError> {
        if self.offset == self.bytes.len() {
            Ok(())
        } else {
            Err(NativeProcessCallWireError::TrailingBytes)
        }
    }

    fn i32(&mut self) -> Result<i32, NativeProcessCallWireError> {
        let bytes = self.take(size_of::<i32>())?;
        let array = <[u8; size_of::<i32>()]>::try_from(bytes)
            .map_err(|_error| NativeProcessCallWireError::ReadFailure)?;
        Ok(i32::from_le_bytes(array))
    }

    const fn new(bytes: &'bytes [u8]) -> Self {
        Self { bytes, offset: 0 }
    }

    fn take(
        &mut self,
        count: usize,
    ) -> Result<&'bytes [u8], NativeProcessCallWireError> {
        let end = self
            .offset
            .checked_add(count)
            .ok_or(NativeProcessCallWireError::ReadFailure)?;
        let value = self
            .bytes
            .get(self.offset..end)
            .ok_or(NativeProcessCallWireError::ReadFailure)?;
        self.offset = end;
        Ok(value)
    }

    fn u32(&mut self) -> Result<u32, NativeProcessCallWireError> {
        let bytes = self.take(size_of::<u32>())?;
        let array = <[u8; size_of::<u32>()]>::try_from(bytes)
            .map_err(|_error| NativeProcessCallWireError::ReadFailure)?;
        Ok(u32::from_le_bytes(array))
    }

    fn u64(&mut self) -> Result<u64, NativeProcessCallWireError> {
        let bytes = self.take(size_of::<u64>())?;
        let array = <[u8; size_of::<u64>()]>::try_from(bytes)
            .map_err(|_error| NativeProcessCallWireError::ReadFailure)?;
        Ok(u64::from_le_bytes(array))
    }

    fn u8(&mut self) -> Result<u8, NativeProcessCallWireError> {
        self.take(1)?
            .first()
            .copied()
            .ok_or(NativeProcessCallWireError::ReadFailure)
    }

    fn words(
        &mut self,
        count: usize,
    ) -> Result<Vec<u32>, NativeProcessCallWireError> {
        let mut words = Vec::with_capacity(count);
        for _word in 0..count {
            words.push(self.u32()?);
        }
        Ok(words)
    }
}

/// Decodes one complete MBNPC1 native call request.
///
/// # Errors
///
/// Returns [`NativeProcessCallWireError`] for malformed framing, zero mapping
/// identity, unrepresentable capacities, truncation, or trailing bytes.
pub fn decode_native_process_call_request(
    bytes: &[u8],
) -> Result<NativeProcessCallRequest, NativeProcessCallWireError> {
    let mut reader = WireReader::new(bytes);
    if reader.take(NATIVE_PROCESS_CALL_WIRE_MAGIC.len())?
        != NATIVE_PROCESS_CALL_WIRE_MAGIC
    {
        return Err(NativeProcessCallWireError::RequestMagic);
    }
    let mapping_id = decode_mapping_id(&mut reader)?;
    let state = decode_state(&mut reader)?;
    let memory_words = usize_from_u64(state.memory_words())?;
    let input_len = usize_from_u64(state.input_len())?;
    let output_capacity = usize_from_u64(state.output_capacity())?;
    let memory = reader.words(memory_words)?;
    let input = reader.take(input_len)?.to_vec();
    let output = reader.take(output_capacity)?.to_vec();
    reader.finish()?;
    Ok(NativeProcessCallRequest::new(
        mapping_id,
        state,
        (&memory, &input, &output),
    ))
}

/// Decodes one complete MBNPC1 response against the original request shape.
///
/// Memory and output payload sizes are derived only from `request`, never from
/// response-controlled state. This bounds allocation before the returned state
/// is structurally or semantically admitted by later layers.
///
/// # Errors
///
/// Returns [`NativeProcessCallWireError`] for malformed framing, zero mapping,
/// invalid pointer flag, unrepresentable request capacities, truncation, or
/// trailing bytes.
pub fn decode_native_process_call_response(
    bytes: &[u8],
    request: &NativeProcessCallRequest,
) -> Result<NativeProcessCallResponse, NativeProcessCallWireError> {
    let mut reader = WireReader::new(bytes);
    if reader.take(NATIVE_PROCESS_CALL_WIRE_MAGIC.len())?
        != NATIVE_PROCESS_CALL_WIRE_MAGIC
    {
        return Err(NativeProcessCallWireError::ResponseMagic);
    }
    let mapping_id = decode_mapping_id(&mut reader)?;
    let state = decode_state(&mut reader)?;
    let raw_status = reader.i32()?;
    let pointers_unchanged = decode_pointer_flag(reader.u8()?)?;
    let memory_words = request.memory().len();
    let output_capacity = request.output().len();
    let memory = reader.words(memory_words)?;
    let output = reader.take(output_capacity)?.to_vec();
    reader.finish()?;
    Ok(NativeProcessCallResponse::new(
        mapping_id,
        state,
        (memory, output),
        (raw_status, pointers_unchanged),
    ))
}

/// Encodes one complete MBNPC1 native call request.
///
/// # Errors
///
/// Returns [`NativeProcessCallWireError`] when state capacities disagree with
/// owned payload shape or the encoded byte count overflows `usize`.
pub fn encode_native_process_call_request(
    request: &NativeProcessCallRequest,
) -> Result<Vec<u8>, NativeProcessCallWireError> {
    validate_request_shape(request)?;
    let capacity = native_process_call_request_byte_len(request)?;
    let mut bytes = Vec::with_capacity(capacity);
    bytes.extend_from_slice(&NATIVE_PROCESS_CALL_WIRE_MAGIC);
    push_u64(&mut bytes, request.mapping_id().get());
    encode_state(&mut bytes, request.state());
    for word in request.memory() {
        push_u32(&mut bytes, *word);
    }
    bytes.extend_from_slice(request.input());
    bytes.extend_from_slice(request.output());
    Ok(bytes)
}

/// Encodes one MBNPC1 response using the original request as the payload bound.
///
/// # Errors
///
/// Returns [`NativeProcessCallWireError`] when returned memory/output shape
/// differs from the request or the encoded byte count overflows `usize`.
pub fn encode_native_process_call_response(
    request: &NativeProcessCallRequest,
    response: &NativeProcessCallResponse,
) -> Result<Vec<u8>, NativeProcessCallWireError> {
    validate_response_shape(request, response)?;
    let capacity = native_process_call_response_byte_limit(request)?;
    let mut bytes = Vec::with_capacity(capacity);
    bytes.extend_from_slice(&NATIVE_PROCESS_CALL_WIRE_MAGIC);
    push_u64(&mut bytes, response.mapping_id().get());
    encode_state(&mut bytes, response.state());
    push_i32(&mut bytes, response.raw_status());
    bytes.push(u8::from(response.pointers_unchanged()));
    for word in response.memory() {
        push_u32(&mut bytes, *word);
    }
    bytes.extend_from_slice(response.output());
    Ok(bytes)
}

/// Returns the exact encoded request length for one admitted transfer request.
///
/// # Errors
///
/// Returns [`NativeProcessCallWireError`] for shape disagreement or arithmetic
/// overflow.
pub fn native_process_call_request_byte_len(
    request: &NativeProcessCallRequest,
) -> Result<usize, NativeProcessCallWireError> {
    validate_request_shape(request)?;
    payload_byte_len(
        NATIVE_PROCESS_CALL_REQUEST_FIXED_BYTES,
        request.memory().len(),
        request.input().len(),
        request.output().len(),
    )
}

/// Returns the largest valid response size for one exact request.
///
/// # Errors
///
/// Returns [`NativeProcessCallWireError`] if the request payload size cannot be
/// represented by the host `usize` arithmetic used to bound reads.
pub fn native_process_call_response_byte_limit(
    request: &NativeProcessCallRequest,
) -> Result<usize, NativeProcessCallWireError> {
    payload_byte_len(
        NATIVE_PROCESS_CALL_RESPONSE_FIXED_BYTES,
        request.memory().len(),
        0,
        request.output().len(),
    )
}

fn decode_mapping_id(
    reader: &mut WireReader<'_>,
) -> Result<NativeExecutableMappingId, NativeProcessCallWireError> {
    NativeExecutableMappingId::new(reader.u64()?)
        .ok_or(NativeProcessCallWireError::MappingIdentity)
}

const fn decode_pointer_flag(
    value: u8,
) -> Result<bool, NativeProcessCallWireError> {
    match value {
        0 => Ok(false),
        1 => Ok(true),
        _ => Err(NativeProcessCallWireError::PointerFlag(value)),
    }
}

fn decode_state(
    reader: &mut WireReader<'_>,
) -> Result<NativeProcessCallState, NativeProcessCallWireError> {
    let capacities = [reader.u64()?, reader.u64()?, reader.u64()?];
    let progress = [reader.u64()?, reader.u64()?];
    let registers = [reader.u32()?, reader.u32()?, reader.u32()?];
    let termination_tag = reader.u8()?;
    Ok(NativeProcessCallState::from_raw(
        capacities,
        progress,
        registers,
        termination_tag,
    ))
}

fn encode_state(bytes: &mut Vec<u8>, state: NativeProcessCallState) {
    for value in [
        state.memory_words(),
        state.input_len(),
        state.output_capacity(),
        state.input_consumed(),
        state.output_len(),
    ] {
        push_u64(bytes, value);
    }
    for value in [
        state.accumulator(),
        state.code_pointer(),
        state.data_pointer(),
    ] {
        push_u32(bytes, value);
    }
    bytes.push(state.termination_tag());
}

fn payload_byte_len(
    fixed: usize,
    memory_words: usize,
    input_len: usize,
    output_len: usize,
) -> Result<usize, NativeProcessCallWireError> {
    let memory_bytes = memory_words
        .checked_mul(size_of::<u32>())
        .ok_or(NativeProcessCallWireError::CounterOverflow)?;
    fixed
        .checked_add(memory_bytes)
        .and_then(|value| value.checked_add(input_len))
        .and_then(|value| value.checked_add(output_len))
        .ok_or(NativeProcessCallWireError::CounterOverflow)
}

fn push_i32(bytes: &mut Vec<u8>, value: i32) {
    bytes.extend_from_slice(&value.to_le_bytes());
}

fn push_u32(bytes: &mut Vec<u8>, value: u32) {
    bytes.extend_from_slice(&value.to_le_bytes());
}

fn push_u64(bytes: &mut Vec<u8>, value: u64) {
    bytes.extend_from_slice(&value.to_le_bytes());
}

fn usize_from_u64(value: u64) -> Result<usize, NativeProcessCallWireError> {
    usize::try_from(value)
        .map_err(|_error| NativeProcessCallWireError::CounterOverflow)
}

fn validate_request_shape(
    request: &NativeProcessCallRequest,
) -> Result<(), NativeProcessCallWireError> {
    let state = request.state();
    let memory_words = usize_from_u64(state.memory_words())?;
    let input_len = usize_from_u64(state.input_len())?;
    let output_capacity = usize_from_u64(state.output_capacity())?;
    if memory_words != request.memory().len() {
        return Err(NativeProcessCallWireError::MemoryLength);
    }
    if input_len != request.input().len() {
        return Err(NativeProcessCallWireError::InputLength);
    }
    if output_capacity != request.output().len() {
        return Err(NativeProcessCallWireError::OutputLength);
    }
    Ok(())
}

const fn validate_response_shape(
    request: &NativeProcessCallRequest,
    response: &NativeProcessCallResponse,
) -> Result<(), NativeProcessCallWireError> {
    if response.memory().len() != request.memory().len() {
        return Err(NativeProcessCallWireError::MemoryLength);
    }
    if response.output().len() != request.output().len() {
        return Err(NativeProcessCallWireError::OutputLength);
    }
    Ok(())
}
