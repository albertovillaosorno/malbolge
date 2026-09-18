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
//   - Transport-neutral framing for native executable-memory host commands.
// - Must-Not:
//   - Spawn processes, perform memory syscalls, invoke code, or admit reports.
// - Allows:
//   - Inputs: existing executable-memory requests/reports plus copied code
//     bytes.
//   - Outputs: exact MBNPM1 bytes or decoded untrusted platform evidence.
//   - Side effects: process-local owned allocation only.
// - Split-When:
//   - A new wire version requires incompatible command or evidence fields.
// - Merge-When:
//   - One concrete native process host becomes the sole protocol authority.
// - Summary:
//   - Frames executable-memory commands without granting lifecycle authority.
// - Description:
//   - Copy response bytes are bounded from the original copy request.
// - Usage:
//   - A persistent native host transports these commands before MBNPC1 calls.
// - Defaults:
//   - Invalid tags, identity, addresses, lengths, or trailing bytes fail
//     closed.
//

//! Transport-neutral MBNPM1 framing for native executable-memory operations.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::num::NonZeroUsize;

use super::lifecycle::{
    NativeExecutableMappingId, NativeExecutableMappingReport,
    NativeExecutableReleaseRequest, NativeInstructionSyncReport,
};
use super::loader::NativeExecutablePermission;
use super::platform::{
    NativeExecutableAllocationRequest, NativeExecutableCodeCopyReport,
    NativeInstructionSyncRequest,
};

/// Stable magic prefix for native process memory protocol version 1.
pub const NATIVE_PROCESS_MEMORY_WIRE_MAGIC: [u8; 8] = *b"MBNPM1\0\0";

const COMMAND_ALLOCATE: u8 = 0;
const COMMAND_COPY: u8 = 1;
const COMMAND_PROTECT: u8 = 2;
const COMMAND_RELEASE: u8 = 3;
const COMMAND_SYNCHRONIZE: u8 = 4;
const OUTCOME_FAILURE: u8 = 1;
const OUTCOME_SUCCESS: u8 = 0;

/// One owned executable-memory command suitable for process transport.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeProcessMemoryRequest {
    /// Allocates one writable mapping from an exact loader request.
    Allocate(NativeExecutableAllocationRequest),
    /// Copies exact admitted code into one writable mapping.
    Copy {
        /// Bytes to copy into the child-owned mapping.
        code: Box<[u8]>,
        /// Untrusted mapping report already admitted by the safe lifecycle.
        mapping: NativeExecutableMappingReport,
    },
    /// Transitions one exact mapping from writable to read-execute.
    Protect(NativeExecutableMappingReport),
    /// Releases one exact child-owned mapping.
    Release(NativeExecutableReleaseRequest),
    /// Synchronizes one exact executable instruction range.
    Synchronize(NativeInstructionSyncRequest),
}

/// One decoded child response carrying untrusted executable-memory evidence.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeProcessMemoryResponse {
    /// Writable mapping evidence from an allocation command.
    Allocate(NativeExecutableMappingReport),
    /// Exact copy evidence returned for the original request bytes.
    Copy(NativeExecutableCodeCopyReport),
    /// Child-defined platform failure code with no semantic authority.
    Failure(u32),
    /// Read-execute mapping evidence from a protection command.
    Protect(NativeExecutableMappingReport),
    /// Successful release acknowledgement.
    Release,
    /// Instruction synchronization evidence for one exact range.
    Synchronize(NativeInstructionSyncReport),
}

/// Failure while encoding or decoding the MBNPM1 memory contract.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeProcessMemoryWireError {
    /// A non-zero platform address decoded as zero or cannot fit `usize`.
    Address,
    /// The command tag is outside the MBNPM1 command domain.
    CommandTag(u8),
    /// A byte count cannot be represented by the current host.
    CounterOverflow,
    /// Bytes begin with a different protocol magic.
    Magic,
    /// A mapping identity decoded as zero.
    MappingIdentity,
    /// The outcome tag is outside the success/failure domain.
    OutcomeTag(u8),
    /// A page-permission tag is outside the supported W^X domain.
    PermissionTag(u8),
    /// The encoded payload ends before all required fields are available.
    ReadFailure,
    /// Response command differs from the original request command.
    ResponseCommand,
    /// Response variant cannot answer the supplied request command.
    ResponseShape,
    /// Bytes remain after the complete declared payload.
    TrailingBytes,
}

#[derive(Clone, Copy, Debug)]
struct WireReader<'bytes> {
    bytes: &'bytes [u8],
    offset: usize,
}

impl Display for NativeProcessMemoryWireError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Address => {
                f.write_str("native process memory address invalid")
            },
            Self::CommandTag(value) => {
                write!(
                    f,
                    "native process memory command tag {value} is invalid"
                )
            },
            Self::CounterOverflow => {
                f.write_str("native process memory counter overflowed")
            },
            Self::Magic => {
                f.write_str("native process memory wire magic mismatch")
            },
            Self::MappingIdentity => {
                f.write_str("native process memory mapping identity is zero")
            },
            Self::OutcomeTag(value) => {
                write!(
                    f,
                    "native process memory outcome tag {value} is invalid"
                )
            },
            Self::PermissionTag(value) => write!(
                f,
                "native process memory permission tag {value} is invalid"
            ),
            Self::ReadFailure => {
                f.write_str("native process memory payload is truncated")
            },
            Self::ResponseCommand => {
                f.write_str("native process memory response command drifted")
            },
            Self::ResponseShape => {
                f.write_str("native process memory response shape drifted")
            },
            Self::TrailingBytes => {
                f.write_str("native process memory payload has trailing bytes")
            },
        }
    }
}

impl<'bytes> WireReader<'bytes> {
    const fn finish(self) -> Result<(), NativeProcessMemoryWireError> {
        if self.offset == self.bytes.len() {
            Ok(())
        } else {
            Err(NativeProcessMemoryWireError::TrailingBytes)
        }
    }

    const fn new(bytes: &'bytes [u8]) -> Self {
        Self { bytes, offset: 0 }
    }

    fn take(
        &mut self,
        count: usize,
    ) -> Result<&'bytes [u8], NativeProcessMemoryWireError> {
        let end = self
            .offset
            .checked_add(count)
            .ok_or(NativeProcessMemoryWireError::ReadFailure)?;
        let value = self
            .bytes
            .get(self.offset..end)
            .ok_or(NativeProcessMemoryWireError::ReadFailure)?;
        self.offset = end;
        Ok(value)
    }

    fn u32(&mut self) -> Result<u32, NativeProcessMemoryWireError> {
        let bytes = self.take(size_of::<u32>())?;
        let array = <[u8; size_of::<u32>()]>::try_from(bytes)
            .map_err(|_error| NativeProcessMemoryWireError::ReadFailure)?;
        Ok(u32::from_le_bytes(array))
    }

    fn u64(&mut self) -> Result<u64, NativeProcessMemoryWireError> {
        let bytes = self.take(size_of::<u64>())?;
        let array = <[u8; size_of::<u64>()]>::try_from(bytes)
            .map_err(|_error| NativeProcessMemoryWireError::ReadFailure)?;
        Ok(u64::from_le_bytes(array))
    }

    fn u8(&mut self) -> Result<u8, NativeProcessMemoryWireError> {
        self.take(1)?
            .first()
            .copied()
            .ok_or(NativeProcessMemoryWireError::ReadFailure)
    }
}

impl NativeProcessMemoryRequest {
    const fn command_tag(&self) -> u8 {
        match self {
            Self::Allocate(_) => COMMAND_ALLOCATE,
            Self::Copy { .. } => COMMAND_COPY,
            Self::Protect(_) => COMMAND_PROTECT,
            Self::Release(_) => COMMAND_RELEASE,
            Self::Synchronize(_) => COMMAND_SYNCHRONIZE,
        }
    }
}

/// Decodes one complete MBNPM1 executable-memory request.
///
/// # Errors
///
/// Returns [`NativeProcessMemoryWireError`] for malformed framing, invalid
/// tags, zero identities/addresses, overflow, truncation, or trailing bytes.
pub fn decode_native_process_memory_request(
    bytes: &[u8],
) -> Result<NativeProcessMemoryRequest, NativeProcessMemoryWireError> {
    let mut reader = request_reader(bytes)?;
    let command = reader.u8()?;
    let request = match command {
        COMMAND_ALLOCATE => NativeProcessMemoryRequest::Allocate(
            NativeExecutableAllocationRequest::new(
                usize_from_u64(reader.u64()?)?,
                usize_from_u64(reader.u64()?)?,
                decode_permission(reader.u8()?)?,
            ),
        ),
        COMMAND_COPY => {
            let mapping = decode_mapping_report(&mut reader)?;
            let code_len = usize_from_u64(reader.u64()?)?;
            let code = reader.take(code_len)?.to_vec().into_boxed_slice();
            NativeProcessMemoryRequest::Copy { code, mapping }
        },
        COMMAND_PROTECT => NativeProcessMemoryRequest::Protect(
            decode_mapping_report(&mut reader)?,
        ),
        COMMAND_RELEASE => NativeProcessMemoryRequest::Release(
            NativeExecutableReleaseRequest::from_mapping(
                decode_release_mapping(&mut reader)?,
            ),
        ),
        COMMAND_SYNCHRONIZE => NativeProcessMemoryRequest::Synchronize(
            NativeInstructionSyncRequest::new(
                decode_mapping_id(&mut reader)?,
                decode_address(&mut reader)?,
                usize_from_u64(reader.u64()?)?,
            ),
        ),
        value => return Err(NativeProcessMemoryWireError::CommandTag(value)),
    };
    reader.finish()?;
    Ok(request)
}

/// Decodes one complete MBNPM1 response against its original request.
///
/// Copy response payload length derives only from the original request. The
/// child cannot increase Rust allocation by reporting a different copied-byte
/// count.
///
/// # Errors
///
/// Returns [`NativeProcessMemoryWireError`] for malformed framing, mismatched
/// command, invalid tags/identity/address, truncation, or trailing bytes.
pub fn decode_native_process_memory_response(
    bytes: &[u8],
    request: &NativeProcessMemoryRequest,
) -> Result<NativeProcessMemoryResponse, NativeProcessMemoryWireError> {
    let mut reader = response_reader(bytes)?;
    if reader.u8()? != request.command_tag() {
        return Err(NativeProcessMemoryWireError::ResponseCommand);
    }
    match reader.u8()? {
        OUTCOME_FAILURE => {
            let response = NativeProcessMemoryResponse::Failure(reader.u32()?);
            reader.finish()?;
            Ok(response)
        },
        OUTCOME_SUCCESS => {
            let response = decode_success_response(&mut reader, request)?;
            reader.finish()?;
            Ok(response)
        },
        value => Err(NativeProcessMemoryWireError::OutcomeTag(value)),
    }
}

/// Encodes one complete MBNPM1 executable-memory request.
///
/// # Errors
///
/// Returns [`NativeProcessMemoryWireError`] when host-sized values cannot be
/// represented by the stable 64-bit framing.
pub fn encode_native_process_memory_request(
    request: &NativeProcessMemoryRequest,
) -> Result<Vec<u8>, NativeProcessMemoryWireError> {
    let mut bytes =
        Vec::with_capacity(native_process_memory_request_byte_len(request)?);
    bytes.extend_from_slice(&NATIVE_PROCESS_MEMORY_WIRE_MAGIC);
    bytes.push(request.command_tag());
    match request {
        NativeProcessMemoryRequest::Allocate(allocation_request) => {
            push_usize(&mut bytes, allocation_request.byte_len())?;
            push_usize(&mut bytes, allocation_request.alignment())?;
            bytes.push(encode_permission(allocation_request.permissions()));
        },
        NativeProcessMemoryRequest::Copy { code, mapping } => {
            encode_mapping_report(&mut bytes, *mapping)?;
            push_usize(&mut bytes, code.len())?;
            bytes.extend_from_slice(code);
        },
        NativeProcessMemoryRequest::Protect(mapping) => {
            encode_mapping_report(&mut bytes, *mapping)?;
        },
        NativeProcessMemoryRequest::Release(release_request) => {
            push_u64(&mut bytes, release_request.mapping_id().get());
            push_address(&mut bytes, release_request.base_address())?;
            push_usize(&mut bytes, release_request.mapped_len())?;
        },
        NativeProcessMemoryRequest::Synchronize(sync_request) => {
            push_u64(&mut bytes, sync_request.mapping_id().get());
            push_address(&mut bytes, sync_request.start_address())?;
            push_usize(&mut bytes, sync_request.byte_len())?;
        },
    }
    Ok(bytes)
}

/// Encodes one MBNPM1 response against the exact original request.
///
/// # Errors
///
/// Returns [`NativeProcessMemoryWireError`] when response kind does not match
/// the request, copied-byte shape drifts, or host values cannot fit the wire.
pub fn encode_native_process_memory_response(
    request: &NativeProcessMemoryRequest,
    response: &NativeProcessMemoryResponse,
) -> Result<Vec<u8>, NativeProcessMemoryWireError> {
    let mut bytes =
        Vec::with_capacity(native_process_memory_response_byte_limit(request)?);
    bytes.extend_from_slice(&NATIVE_PROCESS_MEMORY_WIRE_MAGIC);
    bytes.push(request.command_tag());
    if let NativeProcessMemoryResponse::Failure(code) = response {
        bytes.push(OUTCOME_FAILURE);
        push_u32(&mut bytes, *code);
    } else {
        bytes.push(OUTCOME_SUCCESS);
        encode_success_response(&mut bytes, request, response)?;
    }
    Ok(bytes)
}

/// Returns the exact encoded request byte length.
///
/// # Errors
///
/// Returns [`NativeProcessMemoryWireError`] when copy payload arithmetic
/// overflows `usize`.
pub fn native_process_memory_request_byte_len(
    request: &NativeProcessMemoryRequest,
) -> Result<usize, NativeProcessMemoryWireError> {
    match request {
        NativeProcessMemoryRequest::Allocate(_) => Ok(26),
        NativeProcessMemoryRequest::Copy { code, .. } => 42usize
            .checked_add(code.len())
            .ok_or(NativeProcessMemoryWireError::CounterOverflow),
        NativeProcessMemoryRequest::Protect(_) => Ok(34),
        NativeProcessMemoryRequest::Release(_)
        | NativeProcessMemoryRequest::Synchronize(_) => Ok(33),
    }
}

/// Returns the largest valid response byte length for one exact request.
///
/// # Errors
///
/// Returns [`NativeProcessMemoryWireError`] when a copy-response byte count
/// overflows `usize`.
pub fn native_process_memory_response_byte_limit(
    request: &NativeProcessMemoryRequest,
) -> Result<usize, NativeProcessMemoryWireError> {
    let success = match request {
        NativeProcessMemoryRequest::Allocate(_)
        | NativeProcessMemoryRequest::Protect(_) => 35,
        NativeProcessMemoryRequest::Copy { code, .. } => 26usize
            .checked_add(code.len())
            .ok_or(NativeProcessMemoryWireError::CounterOverflow)?,
        NativeProcessMemoryRequest::Release(_) => 10,
        NativeProcessMemoryRequest::Synchronize(_) => 34,
    };
    Ok(success.max(14))
}

fn decode_address(
    reader: &mut WireReader<'_>,
) -> Result<NonZeroUsize, NativeProcessMemoryWireError> {
    let value = usize_from_u64(reader.u64()?)?;
    NonZeroUsize::new(value).ok_or(NativeProcessMemoryWireError::Address)
}

fn decode_mapping_id(
    reader: &mut WireReader<'_>,
) -> Result<NativeExecutableMappingId, NativeProcessMemoryWireError> {
    NativeExecutableMappingId::new(reader.u64()?)
        .ok_or(NativeProcessMemoryWireError::MappingIdentity)
}

fn decode_mapping_report(
    reader: &mut WireReader<'_>,
) -> Result<NativeExecutableMappingReport, NativeProcessMemoryWireError> {
    Ok(NativeExecutableMappingReport::new(
        decode_mapping_id(reader)?,
        decode_address(reader)?,
        usize_from_u64(reader.u64()?)?,
        decode_permission(reader.u8()?)?,
    ))
}

const fn decode_permission(
    value: u8,
) -> Result<NativeExecutablePermission, NativeProcessMemoryWireError> {
    match value {
        0 => Ok(NativeExecutablePermission::ReadExecute),
        1 => Ok(NativeExecutablePermission::ReadWrite),
        _ => Err(NativeProcessMemoryWireError::PermissionTag(value)),
    }
}

fn decode_release_mapping(
    reader: &mut WireReader<'_>,
) -> Result<NativeExecutableMappingReport, NativeProcessMemoryWireError> {
    Ok(NativeExecutableMappingReport::new(
        decode_mapping_id(reader)?,
        decode_address(reader)?,
        usize_from_u64(reader.u64()?)?,
        NativeExecutablePermission::ReadExecute,
    ))
}

fn decode_success_response(
    reader: &mut WireReader<'_>,
    request: &NativeProcessMemoryRequest,
) -> Result<NativeProcessMemoryResponse, NativeProcessMemoryWireError> {
    match request {
        NativeProcessMemoryRequest::Allocate(_) => {
            Ok(NativeProcessMemoryResponse::Allocate(
                decode_mapping_report(reader)?,
            ))
        },
        NativeProcessMemoryRequest::Copy { code, .. } => {
            let mapping_id = decode_mapping_id(reader)?;
            let start_address = decode_address(reader)?;
            let copied_code = reader.take(code.len())?.to_vec();
            Ok(NativeProcessMemoryResponse::Copy(
                NativeExecutableCodeCopyReport::new(
                    mapping_id,
                    start_address,
                    copied_code,
                ),
            ))
        },
        NativeProcessMemoryRequest::Protect(_) => {
            Ok(NativeProcessMemoryResponse::Protect(decode_mapping_report(
                reader,
            )?))
        },
        NativeProcessMemoryRequest::Release(_) => {
            Ok(NativeProcessMemoryResponse::Release)
        },
        NativeProcessMemoryRequest::Synchronize(_) => {
            Ok(NativeProcessMemoryResponse::Synchronize(
                NativeInstructionSyncReport::new(
                    decode_mapping_id(reader)?,
                    decode_address(reader)?,
                    usize_from_u64(reader.u64()?)?,
                ),
            ))
        },
    }
}

fn encode_mapping_report(
    bytes: &mut Vec<u8>,
    report: NativeExecutableMappingReport,
) -> Result<(), NativeProcessMemoryWireError> {
    push_u64(bytes, report.mapping_id().get());
    push_address(bytes, report.base_address())?;
    push_usize(bytes, report.mapped_len())?;
    bytes.push(encode_permission(report.permissions()));
    Ok(())
}

const fn encode_permission(permission: NativeExecutablePermission) -> u8 {
    match permission {
        NativeExecutablePermission::ReadExecute => 0,
        NativeExecutablePermission::ReadWrite => 1,
    }
}

fn encode_success_response(
    bytes: &mut Vec<u8>,
    request: &NativeProcessMemoryRequest,
    response: &NativeProcessMemoryResponse,
) -> Result<(), NativeProcessMemoryWireError> {
    match (request, response) {
        (
            NativeProcessMemoryRequest::Allocate(_),
            NativeProcessMemoryResponse::Allocate(report),
        )
        | (
            NativeProcessMemoryRequest::Protect(_),
            NativeProcessMemoryResponse::Protect(report),
        ) => encode_mapping_report(bytes, *report),
        (
            NativeProcessMemoryRequest::Copy { code, .. },
            NativeProcessMemoryResponse::Copy(report),
        ) => {
            if report.copied_code().len() != code.len() {
                return Err(NativeProcessMemoryWireError::ResponseShape);
            }
            push_u64(bytes, report.mapping_id().get());
            push_address(bytes, report.start_address())?;
            bytes.extend_from_slice(report.copied_code());
            Ok(())
        },
        (
            NativeProcessMemoryRequest::Release(_),
            NativeProcessMemoryResponse::Release,
        ) => Ok(()),
        (
            NativeProcessMemoryRequest::Synchronize(_),
            NativeProcessMemoryResponse::Synchronize(report),
        ) => {
            push_u64(bytes, report.mapping_id().get());
            push_address(bytes, report.start_address())?;
            push_usize(bytes, report.byte_len())?;
            Ok(())
        },
        _ => Err(NativeProcessMemoryWireError::ResponseShape),
    }
}

fn push_address(
    bytes: &mut Vec<u8>,
    address: NonZeroUsize,
) -> Result<(), NativeProcessMemoryWireError> {
    push_usize(bytes, address.get())
}

fn push_u32(bytes: &mut Vec<u8>, value: u32) {
    bytes.extend_from_slice(&value.to_le_bytes());
}

fn push_u64(bytes: &mut Vec<u8>, value: u64) {
    bytes.extend_from_slice(&value.to_le_bytes());
}

fn push_usize(
    bytes: &mut Vec<u8>,
    value: usize,
) -> Result<(), NativeProcessMemoryWireError> {
    let encoded = u64::try_from(value)
        .map_err(|_error| NativeProcessMemoryWireError::CounterOverflow)?;
    push_u64(bytes, encoded);
    Ok(())
}

fn request_reader(
    bytes: &[u8],
) -> Result<WireReader<'_>, NativeProcessMemoryWireError> {
    let mut reader = WireReader::new(bytes);
    if reader.take(NATIVE_PROCESS_MEMORY_WIRE_MAGIC.len())?
        != NATIVE_PROCESS_MEMORY_WIRE_MAGIC
    {
        return Err(NativeProcessMemoryWireError::Magic);
    }
    Ok(reader)
}

fn response_reader(
    bytes: &[u8],
) -> Result<WireReader<'_>, NativeProcessMemoryWireError> {
    request_reader(bytes)
}

fn usize_from_u64(value: u64) -> Result<usize, NativeProcessMemoryWireError> {
    usize::try_from(value)
        .map_err(|_error| NativeProcessMemoryWireError::CounterOverflow)
}
