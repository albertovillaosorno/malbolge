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
//   - Canonical host-capability frame and registry serialization contract.
// - Must-Not:
//   - Perform host effects or expose native pointers, handles, or transports.
// - Allows:
//   - Inputs: fixed-width frames, semantic registries, guest byte extents.
//   - Outputs: canonical bytes and deterministic admission diagnostics.
//   - Side effects: validated publication to caller-provided guest memory.
// - Split-When:
//   - Split when capability-specific schemas require independent ownership.
// - Merge-When:
//   - Merge when another contract owns the identical serialized ABI.
// - Summary:
//   - Safe-Rust version-one host-capability wire contract.
// - Description:
//   - Mirrors semantic framing rules independently from the pure-C codec.
// - Usage:
//   - Used by interpreters, native tiers, runners, and differential tests.
// - Defaults:
//   - Unknown flags, malformed ranges, and version drift fail closed.
//

//! Canonical version-one host-capability frame and registry contract.

use std::fmt::{Display, Formatter, Result as FormatResult};

/// Version of the canonical host-capability frame format.
pub const HOST_CAPABILITY_ABI_VERSION: u16 = 1;
/// Fixed byte length of one canonical version-one call frame.
pub const HOST_CAPABILITY_FRAME_WIRE_SIZE: usize = 72;
/// Fixed byte length of one canonical capability descriptor.
pub const HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE: usize = 16;
/// Fixed byte length of one payload-relative byte span.
pub const HOST_CAPABILITY_SPAN_WIRE_SIZE: usize = 16;
/// Request flag asking a potentially blocking capability not to block.
pub const HOST_CALL_FLAG_NONBLOCKING: u32 = 0x0000_0001;
/// Descriptor flag indicating that the capability is currently available.
pub const HOST_CAPABILITY_FLAG_AVAILABLE: u32 = 0x0000_0001;
/// Descriptor flag indicating that an operation may block.
pub const HOST_CAPABILITY_FLAG_MAY_BLOCK: u32 = 0x0000_0002;
/// Descriptor flag allowing successful partial result progress.
pub const HOST_CAPABILITY_FLAG_PARTIAL_PROGRESS: u32 = 0x0000_0004;

const DESCRIPTOR_WIRE_SIZE_U16: u16 = 16;
const FRAME_MAGIC: u32 = 0x4348_424d;
const FRAME_WIRE_SIZE_U16: u16 = 72;
const KNOWN_CALL_FLAGS: u32 = HOST_CALL_FLAG_NONBLOCKING;
const KNOWN_CAPABILITY_FLAGS: u32 = HOST_CAPABILITY_FLAG_AVAILABLE
    | HOST_CAPABILITY_FLAG_MAY_BLOCK
    | HOST_CAPABILITY_FLAG_PARTIAL_PROGRESS;

/// Guest-visible completion state carried by one capability frame.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum HostCapabilityStatus {
    /// Operation was cancelled according to capability semantics.
    Cancelled,
    /// Operation completed and `result_length` bytes are valid.
    Complete,
    /// Host adapter reported an operation-specific failure.
    HostError,
    /// Operation made declared partial progress.
    Partial,
    /// Request is admitted but has not completed.
    Pending,
    /// Nonblocking request could not make progress without blocking.
    WouldBlock,
}

impl HostCapabilityStatus {
    const fn from_wire(value: u32) -> Result<Self, HostCapabilityError> {
        match value {
            0 => Ok(Self::Pending),
            1 => Ok(Self::Complete),
            2 => Ok(Self::Partial),
            3 => Ok(Self::WouldBlock),
            4 => Ok(Self::HostError),
            5 => Ok(Self::Cancelled),
            _ => Err(HostCapabilityError::InvalidStatus),
        }
    }

    const fn wire_value(self) -> u32 {
        match self {
            Self::Pending => 0,
            Self::Complete => 1,
            Self::Partial => 2,
            Self::WouldBlock => 3,
            Self::HostError => 4,
            Self::Cancelled => 5,
        }
    }
}

/// Deterministic host-capability admission or framing failure.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum HostCapabilityError {
    /// Caller supplied an invalid semantic identity.
    InvalidArgument,
    /// Capability-specific request/result bytes violate their declared schema.
    InvalidPayload,
    /// Guest request or result range is outside memory or overlaps its peer.
    InvalidRange,
    /// Capability registry ordering or descriptor metadata is invalid.
    InvalidRegistry,
    /// Response changed immutable request identity or violates behavior flags.
    InvalidResponse,
    /// Status/result-length combination is not valid for the frame state.
    InvalidStatus,
    /// Serialized frame or descriptor bytes are malformed.
    InvalidWireFrame,
    /// Capability/version is known but unavailable on this runner.
    UnavailableCapability,
    /// Capability identity is not present in the registry.
    UnknownCapability,
    /// Frame ABI version is not implemented.
    UnsupportedAbiVersion,
    /// Capability exists but does not implement the requested version.
    UnsupportedCapabilityVersion,
}

impl Display for HostCapabilityError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        let text = match self {
            Self::InvalidArgument => "invalid host-capability argument",
            Self::InvalidPayload => "invalid host-capability payload",
            Self::InvalidRange => "invalid host-capability guest range",
            Self::InvalidRegistry => "invalid host-capability registry",
            Self::InvalidResponse => "invalid host-capability response",
            Self::InvalidStatus => "invalid host-capability status",
            Self::InvalidWireFrame => "invalid host-capability wire frame",
            Self::UnavailableCapability => "host capability unavailable",
            Self::UnknownCapability => "unknown host capability",
            Self::UnsupportedAbiVersion => {
                "unsupported host-capability ABI version"
            },
            Self::UnsupportedCapabilityVersion => {
                "unsupported host-capability version"
            },
        };
        f.write_str(text)
    }
}

/// One semantic capability registry entry.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct HostCapabilityDescriptor {
    /// Stable semantic capability family identifier.
    pub capability_id: u32,
    /// Availability and blocking/progress behavior flags.
    pub flags: u32,
    /// Largest supported semantic version, inclusive.
    pub maximum_version: u16,
    /// Smallest supported semantic version, inclusive.
    pub minimum_version: u16,
}

impl HostCapabilityDescriptor {
    /// Decodes one canonical 16-byte little-endian descriptor.
    ///
    /// # Errors
    ///
    /// Returns [`HostCapabilityError::InvalidWireFrame`] for a wrong byte
    /// length or descriptor size,
    /// [`HostCapabilityError::UnsupportedAbiVersion`] for version drift,
    /// and [`HostCapabilityError::InvalidRegistry`] for invalid semantic
    /// fields.
    pub fn decode(source: &[u8]) -> Result<Self, HostCapabilityError> {
        if source.len() < 14 {
            return Err(HostCapabilityError::InvalidWireFrame);
        }
        if read_u16(source, 12)? != HOST_CAPABILITY_ABI_VERSION {
            return Err(HostCapabilityError::UnsupportedAbiVersion);
        }
        if source.len() != HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE
            || read_u16(source, 14)? != DESCRIPTOR_WIRE_SIZE_U16
        {
            return Err(HostCapabilityError::InvalidWireFrame);
        }
        let descriptor = Self {
            capability_id: read_u32(source, 0)?,
            flags: read_u32(source, 8)?,
            maximum_version: read_u16(source, 6)?,
            minimum_version: read_u16(source, 4)?,
        };
        descriptor.validate()?;
        Ok(descriptor)
    }

    /// Encodes one canonical 16-byte little-endian descriptor.
    ///
    /// # Errors
    ///
    /// Returns [`HostCapabilityError::InvalidRegistry`] if this descriptor is
    /// not a valid registry entry.
    pub fn encode(
        self,
    ) -> Result<[u8; HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE], HostCapabilityError>
    {
        self.validate()?;
        let mut wire = [0u8; HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE];
        write_bytes(&mut wire, 0, self.capability_id.to_le_bytes())?;
        write_bytes(&mut wire, 4, self.minimum_version.to_le_bytes())?;
        write_bytes(&mut wire, 6, self.maximum_version.to_le_bytes())?;
        write_bytes(&mut wire, 8, self.flags.to_le_bytes())?;
        write_bytes(&mut wire, 12, HOST_CAPABILITY_ABI_VERSION.to_le_bytes())?;
        write_bytes(&mut wire, 14, DESCRIPTOR_WIRE_SIZE_U16.to_le_bytes())?;
        Ok(wire)
    }

    const fn validate(self) -> Result<(), HostCapabilityError> {
        if self.capability_id == 0
            || self.minimum_version == 0
            || self.minimum_version > self.maximum_version
            || self.flags & !KNOWN_CAPABILITY_FLAGS != 0
        {
            Err(HostCapabilityError::InvalidRegistry)
        } else {
            Ok(())
        }
    }
}

/// Payload-relative byte span encoded as `{offset: u64, length: u64}`.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct HostCapabilitySpan {
    /// Number of bytes in the referenced payload subrange.
    pub length: u64,
    /// Byte offset relative to the start of the containing payload record.
    pub offset: u64,
}

impl HostCapabilitySpan {
    /// Resolves this span against one payload record after bounds validation.
    ///
    /// # Errors
    ///
    /// Returns [`HostCapabilityError::InvalidPayload`] if the span begins in a
    /// fixed header, extends outside the record, or cannot map to the host
    /// slice index domain.
    pub fn bytes(
        self,
        record: &[u8],
        minimum_offset: u64,
    ) -> Result<&[u8], HostCapabilityError> {
        let record_length = u64::try_from(record.len())
            .map_err(|_conversion_error| HostCapabilityError::InvalidPayload)?;
        self.validate(record_length, minimum_offset)?;
        let start = usize::try_from(self.offset)
            .map_err(|_conversion_error| HostCapabilityError::InvalidPayload)?;
        let length = usize::try_from(self.length)
            .map_err(|_conversion_error| HostCapabilityError::InvalidPayload)?;
        let end = start
            .checked_add(length)
            .ok_or(HostCapabilityError::InvalidPayload)?;
        record
            .get(start..end)
            .ok_or(HostCapabilityError::InvalidPayload)
    }

    /// Decodes one canonical 16-byte little-endian payload span.
    ///
    /// # Errors
    ///
    /// Returns [`HostCapabilityError::InvalidPayload`] for the wrong byte
    /// length.
    pub fn decode(source: &[u8]) -> Result<Self, HostCapabilityError> {
        if source.len() != HOST_CAPABILITY_SPAN_WIRE_SIZE {
            return Err(HostCapabilityError::InvalidPayload);
        }
        Ok(Self {
            length: read_u64(source, 8)?,
            offset: read_u64(source, 0)?,
        })
    }

    /// Encodes this span as exactly 16 little-endian bytes.
    #[must_use]
    pub fn encode(self) -> [u8; HOST_CAPABILITY_SPAN_WIRE_SIZE] {
        let mut wire = [0u8; HOST_CAPABILITY_SPAN_WIRE_SIZE];
        wire[..8].copy_from_slice(&self.offset.to_le_bytes());
        wire[8..].copy_from_slice(&self.length.to_le_bytes());
        wire
    }

    /// Validates this span against one containing payload record.
    ///
    /// # Errors
    ///
    /// Returns [`HostCapabilityError::InvalidArgument`] when the schema's
    /// fixed-header boundary exceeds the record itself, or
    /// [`HostCapabilityError::InvalidPayload`] when guest bytes reference the
    /// fixed header or extend beyond the record.
    pub fn validate(
        self,
        record_length: u64,
        minimum_offset: u64,
    ) -> Result<(), HostCapabilityError> {
        if minimum_offset > record_length {
            return Err(HostCapabilityError::InvalidArgument);
        }
        if self.offset < minimum_offset
            || !range_valid(self.offset, self.length, record_length)
        {
            return Err(HostCapabilityError::InvalidPayload);
        }
        Ok(())
    }
}

/// Buffers used to publish one already-staged capability result.
#[derive(Debug)]
pub struct HostCapabilityResponseBuffers<'buffers> {
    /// Guest byte-memory domain receiving validated result bytes.
    pub guest_memory: &'buffers mut [u8],
    /// Host-owned bytes staged before guest memory is mutated.
    pub staged_result: &'buffers [u8],
}

/// One decoded host-capability call frame.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct HostCapabilityFrame {
    /// Canonical frame format version.
    pub abi_version: u16,
    /// Guest-selected stable identity for retries and completion matching.
    pub call_id: u64,
    /// Stable semantic capability family identifier.
    pub capability_id: u32,
    /// Requested semantic capability version.
    pub capability_version: u16,
    /// Version-one call behavior flags.
    pub flags: u32,
    /// Capability-defined operation number.
    pub operation: u16,
    /// Number of request bytes available at `request_offset`.
    pub request_length: u64,
    /// Guest-memory byte offset of immutable request data.
    pub request_offset: u64,
    /// Number of result bytes available at `result_offset`.
    pub result_capacity: u64,
    /// Number of result bytes produced by the response.
    pub result_length: u64,
    /// Guest-memory byte offset of writable result storage.
    pub result_offset: u64,
    /// Request or response completion state.
    pub status: HostCapabilityStatus,
}

impl HostCapabilityFrame {
    /// Decodes one canonical 72-byte little-endian call frame.
    ///
    /// # Errors
    ///
    /// Returns a deterministic framing or status error for malformed bytes.
    pub fn decode(source: &[u8]) -> Result<Self, HostCapabilityError> {
        if source.len() < 8 || read_u32(source, 0)? != FRAME_MAGIC {
            return Err(HostCapabilityError::InvalidWireFrame);
        }
        let abi_version = read_u16(source, 4)?;
        if abi_version != HOST_CAPABILITY_ABI_VERSION {
            return Err(HostCapabilityError::UnsupportedAbiVersion);
        }
        if source.len() != HOST_CAPABILITY_FRAME_WIRE_SIZE
            || read_u16(source, 6)? != FRAME_WIRE_SIZE_U16
        {
            return Err(HostCapabilityError::InvalidWireFrame);
        }
        let frame = Self {
            abi_version,
            call_id: read_u64(source, 64)?,
            capability_id: read_u32(source, 8)?,
            capability_version: read_u16(source, 12)?,
            flags: read_u32(source, 16)?,
            operation: read_u16(source, 14)?,
            request_length: read_u64(source, 32)?,
            request_offset: read_u64(source, 24)?,
            result_capacity: read_u64(source, 48)?,
            result_length: read_u64(source, 56)?,
            result_offset: read_u64(source, 40)?,
            status: HostCapabilityStatus::from_wire(read_u32(source, 20)?)?,
        };
        frame.validate_shape()?;
        Ok(frame)
    }

    /// Encodes this frame as exactly 72 canonical little-endian bytes.
    ///
    /// # Errors
    ///
    /// Returns a deterministic framing or status error when this frame cannot
    /// be represented as a valid version-one request or response shape.
    pub fn encode(
        self,
    ) -> Result<[u8; HOST_CAPABILITY_FRAME_WIRE_SIZE], HostCapabilityError>
    {
        self.validate_shape()?;
        let mut wire = [0u8; HOST_CAPABILITY_FRAME_WIRE_SIZE];
        write_bytes(&mut wire, 0, FRAME_MAGIC.to_le_bytes())?;
        write_bytes(&mut wire, 4, self.abi_version.to_le_bytes())?;
        write_bytes(&mut wire, 6, FRAME_WIRE_SIZE_U16.to_le_bytes())?;
        write_bytes(&mut wire, 8, self.capability_id.to_le_bytes())?;
        write_bytes(&mut wire, 12, self.capability_version.to_le_bytes())?;
        write_bytes(&mut wire, 14, self.operation.to_le_bytes())?;
        write_bytes(&mut wire, 16, self.flags.to_le_bytes())?;
        write_bytes(&mut wire, 20, self.status.wire_value().to_le_bytes())?;
        write_bytes(&mut wire, 24, self.request_offset.to_le_bytes())?;
        write_bytes(&mut wire, 32, self.request_length.to_le_bytes())?;
        write_bytes(&mut wire, 40, self.result_offset.to_le_bytes())?;
        write_bytes(&mut wire, 48, self.result_capacity.to_le_bytes())?;
        write_bytes(&mut wire, 56, self.result_length.to_le_bytes())?;
        write_bytes(&mut wire, 64, self.call_id.to_le_bytes())?;
        Ok(wire)
    }

    /// Validates this as a pre-effect guest request.
    ///
    /// # Errors
    ///
    /// Returns a deterministic capability, version, status, or range error.
    pub fn validate_request(
        self,
        guest_memory_size: u64,
        registry: &[HostCapabilityDescriptor],
    ) -> Result<(), HostCapabilityError> {
        self.validate_shape()?;
        if self.status != HostCapabilityStatus::Pending {
            return Err(HostCapabilityError::InvalidStatus);
        }
        let descriptor = discover_host_capability(
            registry,
            self.capability_id,
            self.capability_version,
        )?;
        if self.flags & HOST_CALL_FLAG_NONBLOCKING != 0
            && descriptor.flags & HOST_CAPABILITY_FLAG_MAY_BLOCK == 0
        {
            return Err(HostCapabilityError::InvalidStatus);
        }
        if !range_valid(
            self.request_offset,
            self.request_length,
            guest_memory_size,
        ) || !range_valid(
            self.result_offset,
            self.result_capacity,
            guest_memory_size,
        ) {
            return Err(HostCapabilityError::InvalidRange);
        }
        if ranges_overlap(
            self.request_offset,
            self.request_length,
            self.result_offset,
            self.result_capacity,
        )? {
            return Err(HostCapabilityError::InvalidRange);
        }
        Ok(())
    }

    const fn validate_shape(self) -> Result<(), HostCapabilityError> {
        if self.abi_version != HOST_CAPABILITY_ABI_VERSION {
            return Err(HostCapabilityError::UnsupportedAbiVersion);
        }
        if self.capability_id == 0
            || self.capability_version == 0
            || self.flags & !KNOWN_CALL_FLAGS != 0
        {
            return Err(HostCapabilityError::InvalidWireFrame);
        }
        if self.result_length > self.result_capacity {
            return Err(HostCapabilityError::InvalidStatus);
        }
        let requires_empty_result = matches!(
            self.status,
            HostCapabilityStatus::Cancelled
                | HostCapabilityStatus::HostError
                | HostCapabilityStatus::Pending
                | HostCapabilityStatus::WouldBlock
        );
        if requires_empty_result && self.result_length != 0 {
            Err(HostCapabilityError::InvalidStatus)
        } else {
            Ok(())
        }
    }
}

/// Validates a response and atomically publishes its staged result bytes.
///
/// # Errors
///
/// Returns before mutating guest memory if the request/response pair is
/// invalid, the staged byte count differs from `result_length`, or the result
/// range cannot be represented in the caller's memory slice.
pub fn commit_host_capability_response(
    request: HostCapabilityFrame,
    response: HostCapabilityFrame,
    registry: &[HostCapabilityDescriptor],
    buffers: HostCapabilityResponseBuffers<'_>,
) -> Result<(), HostCapabilityError> {
    let HostCapabilityResponseBuffers {
        guest_memory,
        staged_result,
    } = buffers;
    let guest_memory_size = u64::try_from(guest_memory.len())
        .map_err(|_conversion_error| HostCapabilityError::InvalidRange)?;
    validate_host_capability_response(
        request,
        response,
        guest_memory_size,
        registry,
    )?;
    let result_length = usize::try_from(response.result_length)
        .map_err(|_conversion_error| HostCapabilityError::InvalidResponse)?;
    if staged_result.len() != result_length {
        return Err(HostCapabilityError::InvalidResponse);
    }
    let result_offset = usize::try_from(response.result_offset)
        .map_err(|_conversion_error| HostCapabilityError::InvalidRange)?;
    let result_end = result_offset
        .checked_add(result_length)
        .ok_or(HostCapabilityError::InvalidRange)?;
    let destination = guest_memory
        .get_mut(result_offset..result_end)
        .ok_or(HostCapabilityError::InvalidRange)?;
    destination.copy_from_slice(staged_result);
    Ok(())
}

/// Validates a registry as strictly ordered, unique semantic identities.
///
/// # Errors
///
/// Returns [`HostCapabilityError::InvalidRegistry`] when a descriptor is
/// malformed, duplicated, or out of order.
pub fn validate_host_capability_registry(
    registry: &[HostCapabilityDescriptor],
) -> Result<(), HostCapabilityError> {
    let mut previous_id = None;
    for descriptor in registry {
        descriptor.validate()?;
        if previous_id.is_some_and(|value| value >= descriptor.capability_id) {
            return Err(HostCapabilityError::InvalidRegistry);
        }
        previous_id = Some(descriptor.capability_id);
    }
    Ok(())
}

/// Validates canonical serialized capability descriptors as one registry.
///
/// # Errors
///
/// Returns a framing, version, or registry error when any record is malformed,
/// duplicated, or out of order.
pub fn validate_host_capability_wire_registry(
    registry: &[u8],
) -> Result<(), HostCapabilityError> {
    let mut previous_id = None;
    let mut remaining = registry;
    while !remaining.is_empty() {
        if remaining.len() < 14 {
            return Err(HostCapabilityError::InvalidWireFrame);
        }
        if read_u16(remaining, 12)? != HOST_CAPABILITY_ABI_VERSION {
            return Err(HostCapabilityError::UnsupportedAbiVersion);
        }
        let wire = remaining
            .get(..HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE)
            .ok_or(HostCapabilityError::InvalidWireFrame)?;
        let descriptor = HostCapabilityDescriptor::decode(wire)?;
        if previous_id.is_some_and(|value| value >= descriptor.capability_id) {
            return Err(HostCapabilityError::InvalidRegistry);
        }
        previous_id = Some(descriptor.capability_id);
        remaining = remaining
            .get(HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE..)
            .ok_or(HostCapabilityError::InvalidWireFrame)?;
    }
    Ok(())
}

/// Resolves one semantic capability/version from a validated registry.
///
/// # Errors
///
/// Returns stable unknown, unsupported-version, unavailable, or registry
/// diagnostics without exposing host implementation identity.
pub fn discover_host_capability(
    registry: &[HostCapabilityDescriptor],
    capability_id: u32,
    capability_version: u16,
) -> Result<HostCapabilityDescriptor, HostCapabilityError> {
    if capability_id == 0 || capability_version == 0 {
        return Err(HostCapabilityError::InvalidArgument);
    }
    validate_host_capability_registry(registry)?;
    for descriptor in registry {
        if descriptor.capability_id < capability_id {
            continue;
        }
        if descriptor.capability_id > capability_id {
            return Err(HostCapabilityError::UnknownCapability);
        }
        if capability_version < descriptor.minimum_version
            || capability_version > descriptor.maximum_version
        {
            return Err(HostCapabilityError::UnsupportedCapabilityVersion);
        }
        if descriptor.flags & HOST_CAPABILITY_FLAG_AVAILABLE == 0 {
            return Err(HostCapabilityError::UnavailableCapability);
        }
        return Ok(*descriptor);
    }
    Err(HostCapabilityError::UnknownCapability)
}

/// Resolves one capability/version directly from canonical registry bytes.
///
/// # Errors
///
/// Returns the same deterministic discovery errors as the decoded registry API,
/// plus framing/version failures from serialized descriptor validation.
pub fn discover_host_capability_wire(
    registry: &[u8],
    capability_id: u32,
    capability_version: u16,
) -> Result<HostCapabilityDescriptor, HostCapabilityError> {
    if capability_id == 0 || capability_version == 0 {
        return Err(HostCapabilityError::InvalidArgument);
    }
    validate_host_capability_wire_registry(registry)?;
    for wire in registry
        .as_chunks::<HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE>()
        .0
    {
        let descriptor = HostCapabilityDescriptor::decode(wire)?;
        if descriptor.capability_id < capability_id {
            continue;
        }
        if descriptor.capability_id > capability_id {
            return Err(HostCapabilityError::UnknownCapability);
        }
        if capability_version < descriptor.minimum_version
            || capability_version > descriptor.maximum_version
        {
            return Err(HostCapabilityError::UnsupportedCapabilityVersion);
        }
        if descriptor.flags & HOST_CAPABILITY_FLAG_AVAILABLE == 0 {
            return Err(HostCapabilityError::UnavailableCapability);
        }
        return Ok(descriptor);
    }
    Err(HostCapabilityError::UnknownCapability)
}

/// Validates one host response against an already admitted request.
///
/// # Errors
///
/// Returns a deterministic failure when request identity changed or response
/// status violates the capability's blocking or partial-progress declaration.
pub fn validate_host_capability_response(
    request: HostCapabilityFrame,
    response: HostCapabilityFrame,
    guest_memory_size: u64,
    registry: &[HostCapabilityDescriptor],
) -> Result<(), HostCapabilityError> {
    request.validate_request(guest_memory_size, registry)?;
    response.validate_shape()?;
    if !response_identity_matches(request, response)
        || response.status == HostCapabilityStatus::Pending
    {
        return Err(HostCapabilityError::InvalidResponse);
    }
    let descriptor = discover_host_capability(
        registry,
        request.capability_id,
        request.capability_version,
    )?;
    if response.status == HostCapabilityStatus::Partial
        && (descriptor.flags & HOST_CAPABILITY_FLAG_PARTIAL_PROGRESS == 0
            || response.result_length == 0)
    {
        return Err(HostCapabilityError::InvalidResponse);
    }
    if response.status == HostCapabilityStatus::WouldBlock
        && (descriptor.flags & HOST_CAPABILITY_FLAG_MAY_BLOCK == 0
            || request.flags & HOST_CALL_FLAG_NONBLOCKING == 0)
    {
        return Err(HostCapabilityError::InvalidResponse);
    }
    Ok(())
}

fn range_valid(offset: u64, length: u64, guest_memory_size: u64) -> bool {
    guest_memory_size
        .checked_sub(offset)
        .is_some_and(|remaining| length <= remaining)
}

fn ranges_overlap(
    left_offset: u64,
    left_length: u64,
    right_offset: u64,
    right_length: u64,
) -> Result<bool, HostCapabilityError> {
    if left_length == 0 || right_length == 0 {
        return Ok(false);
    }
    let left_end = left_offset
        .checked_add(left_length)
        .ok_or(HostCapabilityError::InvalidRange)?;
    let right_end = right_offset
        .checked_add(right_length)
        .ok_or(HostCapabilityError::InvalidRange)?;
    Ok(left_offset < right_end && right_offset < left_end)
}

const fn response_identity_matches(
    request: HostCapabilityFrame,
    response: HostCapabilityFrame,
) -> bool {
    response.abi_version == request.abi_version
        && response.capability_id == request.capability_id
        && response.capability_version == request.capability_version
        && response.operation == request.operation
        && response.flags == request.flags
        && response.request_offset == request.request_offset
        && response.request_length == request.request_length
        && response.result_offset == request.result_offset
        && response.result_capacity == request.result_capacity
        && response.call_id == request.call_id
}

fn read_u16(source: &[u8], offset: usize) -> Result<u16, HostCapabilityError> {
    Ok(u16::from_le_bytes(read_array(source, offset)?))
}

fn read_u32(source: &[u8], offset: usize) -> Result<u32, HostCapabilityError> {
    Ok(u32::from_le_bytes(read_array(source, offset)?))
}

fn read_u64(source: &[u8], offset: usize) -> Result<u64, HostCapabilityError> {
    Ok(u64::from_le_bytes(read_array(source, offset)?))
}

fn read_array<const LENGTH: usize>(
    source: &[u8],
    offset: usize,
) -> Result<[u8; LENGTH], HostCapabilityError> {
    let end = offset
        .checked_add(LENGTH)
        .ok_or(HostCapabilityError::InvalidWireFrame)?;
    let bytes = source
        .get(offset..end)
        .ok_or(HostCapabilityError::InvalidWireFrame)?;
    bytes
        .try_into()
        .map_err(|_conversion_error| HostCapabilityError::InvalidWireFrame)
}

fn write_bytes<const LENGTH: usize>(
    destination: &mut [u8],
    offset: usize,
    bytes: [u8; LENGTH],
) -> Result<(), HostCapabilityError> {
    let end = offset
        .checked_add(LENGTH)
        .ok_or(HostCapabilityError::InvalidWireFrame)?;
    let slot = destination
        .get_mut(offset..end)
        .ok_or(HostCapabilityError::InvalidWireFrame)?;
    slot.copy_from_slice(&bytes);
    Ok(())
}
