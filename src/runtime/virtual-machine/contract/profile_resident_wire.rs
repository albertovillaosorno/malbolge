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
//   - Transport-neutral binary framing for resident profile batch backends.
// - Must-Not:
//   - Name accelerator vendors or carry verifier authority across the wire.
// - Allows:
//   - Inputs: admitted resident geometry and immutable profile machine views.
//   - Outputs: exact request bytes and framed backend result snapshots.
//   - Side effects: none.
// - Split-When:
//   - Split when another wire version requires incompatible framing or fields.
// - Merge-When:
//   - Merge when another contract owns the exact resident profile batch schema.
// - Summary:
//   - Defines the MBPRN2 resident profile backend wire representation.
// - Description:
//   - Keeps external transport framing separate from VM semantic authority.
// - Usage:
//   - Used by optional profile backends after CPU-owned request admission.
// - Defaults:
//   - Malformed, mixed-geometry, truncated, or trailing data fails closed.
//

//! Transport-neutral resident profile batch wire representation.

use std::fmt::{Display, Formatter, Result as FormatResult};

/// Stable magic prefix for resident profile batch protocol version 2.
pub const PROFILE_RESIDENT_WIRE_MAGIC: [u8; 8] = *b"MBPRN2\0\0";

const RESPONSE_RESULTS: u32 = 0;
const RESPONSE_UNAVAILABLE: u32 = 1;

/// Failure to encode or decode the resident profile wire contract.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ProfileResidentWireError {
    /// A host-sized counter cannot be represented by the protocol u32 field.
    CounterOverflow,
    /// One request memory image does not match the declared resident geometry.
    MemoryLengthMismatch {
        /// Declared geometry word count.
        expected: u32,
        /// Actual request memory length.
        observed: usize,
    },
    /// One batch attempted to combine distinct resident wire geometries.
    MixedGeometry,
    /// The response payload ends before the declared fields are complete.
    ReadFailure,
    /// The response kind is not part of protocol version 2.
    ResponseKind(u32),
    /// The response begins with a different protocol magic.
    ResponseMagic,
    /// Bytes remain after the declared response payload.
    TrailingResponse,
}

impl Display for ProfileResidentWireError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::CounterOverflow => {
                f.write_str("resident profile wire counter exceeds u32")
            },
            Self::MemoryLengthMismatch { expected, observed } => write!(
                f,
                "resident profile wire memory length {observed} != {expected}"
            ),
            Self::MixedGeometry => f.write_str(
                "resident profile wire batch contains mixed geometry",
            ),
            Self::ReadFailure => {
                f.write_str("resident profile wire response is truncated")
            },
            Self::ResponseKind(kind) => write!(
                f,
                "resident profile wire response kind {kind} is unsupported"
            ),
            Self::ResponseMagic => {
                f.write_str("resident profile wire response magic mismatch")
            },
            Self::TrailingResponse => f.write_str(
                "resident profile wire response contains trailing bytes",
            ),
        }
    }
}

/// Numeric resident geometry serialized to an optional backend.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ProfileResidentWireGeometry {
    /// All-two-trit EOF word.
    pub eof_word: u32,
    /// Canonical input instruction byte.
    pub input_instruction: u8,
    /// Exact resident memory word count.
    pub memory_words: u32,
    /// Canonical output instruction byte.
    pub output_instruction: u8,
    /// Exact resident word modulus.
    pub word_modulus: u32,
    /// Exact ternary word width.
    pub word_trits: u8,
}

impl ProfileResidentWireGeometry {
    /// Returns the all-two-trit EOF word.
    #[must_use]
    pub const fn eof_word(self) -> u32 {
        self.eof_word
    }

    /// Returns the canonical input instruction byte.
    #[must_use]
    pub const fn input_instruction(self) -> u8 {
        self.input_instruction
    }

    /// Returns the exact resident memory word count.
    #[must_use]
    pub const fn memory_words(self) -> u32 {
        self.memory_words
    }

    /// Returns the canonical output instruction byte.
    #[must_use]
    pub const fn output_instruction(self) -> u8 {
        self.output_instruction
    }

    /// Returns the exact resident word modulus.
    #[must_use]
    pub const fn word_modulus(self) -> u32 {
        self.word_modulus
    }

    /// Returns the exact ternary word width.
    #[must_use]
    pub const fn word_trits(self) -> u8 {
        self.word_trits
    }
}

/// One immutable already-admitted profile request projected to wire fields.
#[derive(Clone, Copy, Debug)]
pub struct ProfileResidentWireRequest<'state> {
    /// Exact accumulator value.
    pub accumulator: u32,
    /// Exact code pointer value.
    pub code_pointer: u32,
    /// Exact data pointer value.
    pub data_pointer: u32,
    /// Numeric resident geometry shared by the batch.
    pub geometry: ProfileResidentWireGeometry,
    /// Immutable complete input stream.
    pub input: &'state [u8],
    /// Current input cursor.
    pub input_consumed: usize,
    /// Complete resident memory image.
    pub memory: &'state [u32],
    /// Existing output prefix.
    pub output: &'state [u8],
    /// Maximum additional semantic steps.
    pub step_budget: usize,
    /// Current stable termination code.
    pub termination: ProfileResidentWireTermination,
}

/// One decoded resident backend result snapshot.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ProfileResidentWireResult {
    /// Final accumulator.
    pub accumulator: u32,
    /// Final code pointer.
    pub code_pointer: u32,
    /// Final data pointer.
    pub data_pointer: u32,
    /// Backend execution error code.
    pub error: u32,
    /// Pointer associated with an execution error.
    pub error_pointer: u32,
    /// Value associated with an execution error.
    pub error_value: u32,
    /// Final input cursor.
    pub input_consumed: u32,
    /// Complete final resident memory.
    pub memory: Vec<u32>,
    /// Complete final output bytes.
    pub output: Vec<u8>,
    /// Backend run status code.
    pub status: u32,
    /// Number of semantic steps performed.
    pub steps: u32,
    /// Stable termination code.
    pub termination: u32,
}

/// Decoded top-level response from one resident profile backend attempt.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ProfileResidentWireResponse {
    /// Complete input-ordered backend result snapshots.
    Results(Vec<ProfileResidentWireResult>),
    /// The optional backend was unavailable and produced no results.
    Unavailable,
}

/// Stable wire codes for already-terminated request state.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ProfileResidentWireTermination {
    /// A halt instruction terminated execution.
    HaltInstruction,
    /// A non-graphical current cell terminated execution.
    NonGraphicalCell,
    /// The machine is live.
    None,
}

impl ProfileResidentWireTermination {
    const fn code(self) -> u32 {
        match self {
            Self::None => 0,
            Self::HaltInstruction => 1,
            Self::NonGraphicalCell => 2,
        }
    }
}

struct WireReader<'wire> {
    bytes: &'wire [u8],
    offset: usize,
}

impl<'wire> WireReader<'wire> {
    const fn finish(&self) -> Result<(), ProfileResidentWireError> {
        if self.offset == self.bytes.len() {
            Ok(())
        } else {
            Err(ProfileResidentWireError::TrailingResponse)
        }
    }

    const fn new(bytes: &'wire [u8]) -> Self {
        Self { bytes, offset: 0 }
    }

    fn take(
        &mut self,
        count: usize,
    ) -> Result<&'wire [u8], ProfileResidentWireError> {
        let end = self
            .offset
            .checked_add(count)
            .ok_or(ProfileResidentWireError::ReadFailure)?;
        let value = self
            .bytes
            .get(self.offset..end)
            .ok_or(ProfileResidentWireError::ReadFailure)?;
        self.offset = end;
        Ok(value)
    }

    fn u32(&mut self) -> Result<u32, ProfileResidentWireError> {
        let bytes = self.take(size_of::<u32>())?;
        let array = <[u8; size_of::<u32>()]>::try_from(bytes)
            .map_err(|_error| ProfileResidentWireError::ReadFailure)?;
        Ok(u32::from_le_bytes(array))
    }

    fn words(
        &mut self,
        count: usize,
    ) -> Result<Vec<u32>, ProfileResidentWireError> {
        let mut words = Vec::with_capacity(count);
        for _word in 0..count {
            words.push(self.u32()?);
        }
        Ok(words)
    }
}

/// Decodes one complete MBPRN2 response using the offered resident memory size.
///
/// # Errors
///
/// Returns [`ProfileResidentWireError`] for invalid magic/kind, truncation,
/// counter conversion failure, or trailing bytes.
pub fn decode_profile_resident_response(
    bytes: &[u8],
    memory_words: u32,
) -> Result<ProfileResidentWireResponse, ProfileResidentWireError> {
    let mut reader = WireReader::new(bytes);
    let magic = reader.take(PROFILE_RESIDENT_WIRE_MAGIC.len())?;
    if magic != PROFILE_RESIDENT_WIRE_MAGIC {
        return Err(ProfileResidentWireError::ResponseMagic);
    }
    let kind = reader.u32()?;
    let count = usize::try_from(reader.u32()?)
        .map_err(|_error| ProfileResidentWireError::CounterOverflow)?;
    if kind == RESPONSE_UNAVAILABLE {
        if count != 0 {
            return Err(ProfileResidentWireError::ResponseKind(kind));
        }
        reader.finish()?;
        return Ok(ProfileResidentWireResponse::Unavailable);
    }
    if kind != RESPONSE_RESULTS {
        return Err(ProfileResidentWireError::ResponseKind(kind));
    }
    let memory_len = usize::try_from(memory_words)
        .map_err(|_error| ProfileResidentWireError::CounterOverflow)?;
    let mut results = Vec::with_capacity(count);
    for _item in 0..count {
        results.push(decode_result(&mut reader, memory_len)?);
    }
    reader.finish()?;
    Ok(ProfileResidentWireResponse::Results(results))
}

/// Returns the largest valid MBPRN2 response for one admitted request batch.
///
/// The bound includes fixed response framing, complete resident memories, and
/// at most one newly emitted byte per semantic step.
///
/// # Errors
///
/// Returns [`ProfileResidentWireError`] for mixed geometry or counters whose
/// encoded/host representation would overflow.
pub fn profile_resident_response_byte_limit(
    requests: &[ProfileResidentWireRequest<'_>],
) -> Result<usize, ProfileResidentWireError> {
    let _count = usize_u32(requests.len())?;
    let prefix_scalars = 2usize
        .checked_mul(size_of::<u32>())
        .ok_or(ProfileResidentWireError::CounterOverflow)?;
    let prefix_bytes = PROFILE_RESIDENT_WIRE_MAGIC
        .len()
        .checked_add(prefix_scalars)
        .ok_or(ProfileResidentWireError::CounterOverflow)?;
    let geometry_option = homogeneous_geometry(requests)?;
    let Some(geometry) = geometry_option else {
        return Ok(prefix_bytes);
    };
    let memory_words = usize::try_from(geometry.memory_words())
        .map_err(|_error| ProfileResidentWireError::CounterOverflow)?;
    let memory_bytes = memory_words
        .checked_mul(size_of::<u32>())
        .ok_or(ProfileResidentWireError::CounterOverflow)?;
    let mut total = prefix_bytes;
    for request in requests {
        let output_capacity = request
            .output
            .len()
            .checked_add(request.step_budget)
            .ok_or(ProfileResidentWireError::CounterOverflow)?;
        let _output_capacity = usize_u32(output_capacity)?;
        let fixed = 11usize
            .checked_mul(size_of::<u32>())
            .ok_or(ProfileResidentWireError::CounterOverflow)?;
        let item = fixed
            .checked_add(memory_bytes)
            .and_then(|value| value.checked_add(output_capacity))
            .ok_or(ProfileResidentWireError::CounterOverflow)?;
        total = total
            .checked_add(item)
            .ok_or(ProfileResidentWireError::CounterOverflow)?;
    }
    Ok(total)
}

/// Encodes one homogeneous MBPRN2 request batch.
///
/// # Errors
///
/// Returns [`ProfileResidentWireError`] for mixed geometry, memory-shape drift,
/// or counters that cannot be represented by protocol u32 fields.
pub fn encode_profile_resident_batch(
    requests: &[ProfileResidentWireRequest<'_>],
) -> Result<Vec<u8>, ProfileResidentWireError> {
    let geometry_option = homogeneous_geometry(requests)?;
    let Some(geometry) = geometry_option else {
        return Ok(Vec::new());
    };
    let memory_len = usize::try_from(geometry.memory_words())
        .map_err(|_error| ProfileResidentWireError::CounterOverflow)?;
    let capacity = requests
        .len()
        .saturating_mul(memory_len.saturating_mul(size_of::<u32>()))
        .saturating_add(1024);
    let mut bytes = Vec::with_capacity(capacity);
    bytes.extend_from_slice(&PROFILE_RESIDENT_WIRE_MAGIC);
    for value in geometry_values(geometry)
        .into_iter()
        .chain([usize_u32(requests.len())?])
    {
        push_u32(&mut bytes, value);
    }
    for request in requests {
        encode_request(&mut bytes, request)?;
    }
    Ok(bytes)
}

fn decode_result(
    reader: &mut WireReader<'_>,
    memory_words: usize,
) -> Result<ProfileResidentWireResult, ProfileResidentWireError> {
    let status = reader.u32()?;
    let error = reader.u32()?;
    let accumulator = reader.u32()?;
    let code_pointer = reader.u32()?;
    let data_pointer = reader.u32()?;
    let input_consumed = reader.u32()?;
    let output_len = usize::try_from(reader.u32()?)
        .map_err(|_error| ProfileResidentWireError::CounterOverflow)?;
    let termination = reader.u32()?;
    let error_pointer = reader.u32()?;
    let error_value = reader.u32()?;
    let steps = reader.u32()?;
    let memory = reader.words(memory_words)?;
    let output = reader.take(output_len)?.to_vec();
    Ok(ProfileResidentWireResult {
        accumulator,
        code_pointer,
        data_pointer,
        error,
        error_pointer,
        error_value,
        input_consumed,
        memory,
        output,
        status,
        steps,
        termination,
    })
}

fn encode_request(
    bytes: &mut Vec<u8>,
    request: &ProfileResidentWireRequest<'_>,
) -> Result<(), ProfileResidentWireError> {
    let expected = request.geometry.memory_words();
    let expected_len = usize::try_from(expected)
        .map_err(|_error| ProfileResidentWireError::CounterOverflow)?;
    if request.memory.len() != expected_len {
        return Err(ProfileResidentWireError::MemoryLengthMismatch {
            expected,
            observed: request.memory.len(),
        });
    }
    for value in [
        request.accumulator,
        request.code_pointer,
        request.data_pointer,
        usize_u32(request.input.len())?,
        usize_u32(request.input_consumed)?,
        usize_u32(request.output.len())?,
        usize_u32(request.step_budget)?,
        request.termination.code(),
    ] {
        push_u32(bytes, value);
    }
    for value in request.memory {
        push_u32(bytes, *value);
    }
    bytes.extend_from_slice(request.input);
    bytes.extend_from_slice(request.output);
    Ok(())
}

fn geometry_values(geometry: ProfileResidentWireGeometry) -> [u32; 6] {
    [
        geometry.eof_word(),
        u32::from(geometry.input_instruction()),
        geometry.memory_words(),
        u32::from(geometry.output_instruction()),
        geometry.word_modulus(),
        u32::from(geometry.word_trits()),
    ]
}

fn homogeneous_geometry(
    requests: &[ProfileResidentWireRequest<'_>],
) -> Result<Option<ProfileResidentWireGeometry>, ProfileResidentWireError> {
    let Some(first) = requests.first() else {
        return Ok(None);
    };
    let geometry = first.geometry;
    if requests.iter().any(|request| request.geometry != geometry) {
        return Err(ProfileResidentWireError::MixedGeometry);
    }
    Ok(Some(geometry))
}

fn push_u32(bytes: &mut Vec<u8>, value: u32) {
    bytes.extend_from_slice(&value.to_le_bytes());
}

fn usize_u32(value: usize) -> Result<u32, ProfileResidentWireError> {
    u32::try_from(value)
        .map_err(|_error| ProfileResidentWireError::CounterOverflow)
}
