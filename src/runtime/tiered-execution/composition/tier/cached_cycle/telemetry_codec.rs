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
//   - Canonical versioned bytes for validated cached-retry telemetry snapshots.
// - Must-Not:
//   - Persist bytes, select storage, merge snapshots, or infer retry policy.
// - Allows:
//   - Inputs: one complete snapshot or one untrusted byte slice.
//   - Outputs: canonical little-endian bytes or one validated snapshot.
//   - Side effects: owned process-local allocation only.
// - Split-When:
//   - Compression, durable storage, or cross-process merge gains authority.
// - Merge-When:
//   - One durable telemetry store owns framing and snapshot validation.
// - Summary:
//   - Encodes and decodes exact telemetry snapshots with stable framing.
// - Description:
//   - Magic, revision, reserved bits, length, integers, and semantics fail
//     closed.
// - Usage:
//   - Transfer validated snapshot evidence through caller-owned byte channels.
// - Defaults:
//   - Revision one uses fixed-width little-endian unsigned integers.
//

//! Canonical byte transport for cached-retry telemetry snapshots.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::num::NonZeroUsize;

use super::{
    NativeContinuationCachedRetryTelemetry,
    NativeContinuationCachedRetryTelemetryObservation,
    NativeContinuationCachedRetryTelemetrySnapshotError,
    NativeContinuationCachedRetryTelemetrySnapshotMetadata,
    NativeContinuationCachedRetryTelemetryWindow,
    NativeContinuationCachedRetryTelemetryWindowSnapshot,
};

const CODEC_MAGIC: [u8; 8] = *b"MBTELM01";
const CODEC_REVISION: u16 = 1;
const CODEC_RESERVED: u16 = 0;
const COUNTER_COUNT: usize = 6;
const HEADER_LEN: usize = 92;
const OBSERVATION_LEN: usize = 56;

/// Integer field whose canonical representation could not be admitted.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryTelemetryCodecField {
    /// Aggregate or observation attempt count.
    Attempts,
    /// Positive retained observation capacity.
    Capacity,
    /// Aggregate or observation completed-step count.
    CompletedSteps,
    /// Aggregate or observation active-key eviction count.
    EvictedKeys,
    /// Aggregate or observation active-cache hit count.
    Hits,
    /// Aggregate or observation insertion count.
    Insertions,
    /// Number of retained observation records.
    ObservationCount,
    /// Aggregate or observation retired-key count.
    RetiredKeys,
}

/// Why canonical telemetry snapshot byte transport failed closed.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryTelemetryCodecError {
    /// Snapshot capacity was encoded as zero.
    CapacityZero,
    /// A host integer cannot fit the canonical unsigned representation.
    EncodingRange {
        /// Exact field that could not be encoded.
        field: NativeContinuationCachedRetryTelemetryCodecField,
        /// Zero-based observation index, or `None` for aggregate evidence.
        observation: Option<usize>,
    },
    /// Input length differs from exact framing evidence.
    Length {
        /// Exact required byte count.
        expected: usize,
        /// Supplied byte count.
        observed: usize,
    },
    /// Framing arithmetic overflowed before any allocation or publication.
    LengthOverflow,
    /// The eight-byte format identity differs from revision-one framing.
    Magic,
    /// One fixed-width integer cannot be represented by this host.
    Representation {
        /// Exact field that could not be represented.
        field: NativeContinuationCachedRetryTelemetryCodecField,
        /// Zero-based observation index, or `None` for aggregate evidence.
        observation: Option<usize>,
        /// Canonical unsigned value that exceeded the host representation.
        value: u64,
    },
    /// Reserved framing bits were nonzero.
    Reserved {
        /// Supplied reserved value.
        observed: u16,
    },
    /// Decoded snapshot evidence failed exact semantic validation.
    Snapshot(NativeContinuationCachedRetryTelemetrySnapshotError),
    /// The framing revision is not supported by this implementation.
    Version {
        /// Supplied framing revision.
        observed: u16,
    },
}

struct CodecReader<'bytes> {
    bytes: &'bytes [u8],
    offset: usize,
}

struct DecodedHeader {
    capacity: NonZeroUsize,
    evictions: u64,
    last_sequence: u64,
    observation_count: usize,
}

type DecodedHeaderResult<'bytes> = Result<
    (CodecReader<'bytes>, DecodedHeader),
    NativeContinuationCachedRetryTelemetryCodecError,
>;

impl Display for NativeContinuationCachedRetryTelemetryCodecError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::CapacityZero => {
                f.write_str("cached retry telemetry codec capacity is zero")
            },
            Self::EncodingRange { field, observation } => {
                format_encoding_range(f, *field, *observation)
            },
            Self::Length { expected, observed } => write!(
                f,
                "cached retry telemetry codec length {observed}, expected \
                 {expected}",
            ),
            Self::LengthOverflow => {
                f.write_str("cached retry telemetry codec length overflow")
            },
            Self::Magic => {
                f.write_str("cached retry telemetry codec magic mismatch")
            },
            Self::Representation {
                field,
                observation,
                value,
            } => format_representation(f, *field, *observation, *value),
            Self::Reserved { observed } => write!(
                f,
                "cached retry telemetry codec reserved value {observed}",
            ),
            Self::Snapshot(_error) => {
                f.write_str("cached retry telemetry codec snapshot rejected")
            },
            Self::Version { observed } => write!(
                f,
                concat!(
                    "cached retry telemetry codec revision ",
                    "{} is unsupported",
                ),
                observed,
            ),
        }
    }
}

impl Display for NativeContinuationCachedRetryTelemetryCodecField {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Attempts => "attempts",
            Self::Capacity => "capacity",
            Self::CompletedSteps => "completed steps",
            Self::EvictedKeys => "evicted keys",
            Self::Hits => "hits",
            Self::Insertions => "insertions",
            Self::ObservationCount => "observation count",
            Self::RetiredKeys => "retired keys",
        })
    }
}

impl<'bytes> CodecReader<'bytes> {
    const fn new(bytes: &'bytes [u8]) -> Self {
        Self { bytes, offset: 0 }
    }

    fn read_array<const N: usize>(
        &mut self,
    ) -> Result<[u8; N], NativeContinuationCachedRetryTelemetryCodecError> {
        let end = self.offset.checked_add(N).ok_or(
            NativeContinuationCachedRetryTelemetryCodecError::LengthOverflow,
        )?;
        let source = self.bytes.get(self.offset..end).ok_or(
            NativeContinuationCachedRetryTelemetryCodecError::Length {
                expected: end,
                observed: self.bytes.len(),
            },
        )?;
        let mut value = [0; N];
        value.copy_from_slice(source);
        self.offset = end;
        Ok(value)
    }

    fn read_u16(
        &mut self,
    ) -> Result<u16, NativeContinuationCachedRetryTelemetryCodecError> {
        Ok(u16::from_le_bytes(self.read_array()?))
    }

    fn read_u64(
        &mut self,
    ) -> Result<u64, NativeContinuationCachedRetryTelemetryCodecError> {
        Ok(u64::from_le_bytes(self.read_array()?))
    }
}

/// Decodes canonical bytes into one semantically validated snapshot.
///
/// # Errors
///
/// Returns stable framing, representation, or snapshot validation evidence.
pub fn decode_cached_retry_telemetry_snapshot(
    bytes: &[u8],
) -> Result<
    NativeContinuationCachedRetryTelemetryWindowSnapshot,
    NativeContinuationCachedRetryTelemetryCodecError,
> {
    let (mut reader, header) = decode_header(bytes)?;
    let totals = decode_telemetry(&mut reader, None)?;
    let observations =
        decode_observations(&mut reader, header.observation_count)?;
    let snapshot = NativeContinuationCachedRetryTelemetryWindowSnapshot::new(
        header.capacity,
        NativeContinuationCachedRetryTelemetrySnapshotMetadata::new(
            header.evictions,
            header.last_sequence,
        ),
        observations,
        totals,
    );
    let _validated =
        NativeContinuationCachedRetryTelemetryWindow::from_snapshot(
            snapshot.clone(),
        )
        .map_err(NativeContinuationCachedRetryTelemetryCodecError::Snapshot)?;
    Ok(snapshot)
}

/// Encodes one semantically valid snapshot into canonical revision-one bytes.
///
/// # Errors
///
/// Returns exact snapshot, representation, or framing arithmetic failure.
pub fn encode_cached_retry_telemetry_snapshot(
    snapshot: &NativeContinuationCachedRetryTelemetryWindowSnapshot,
) -> Result<Vec<u8>, NativeContinuationCachedRetryTelemetryCodecError> {
    let _validated =
        NativeContinuationCachedRetryTelemetryWindow::from_snapshot(
            snapshot.clone(),
        )
        .map_err(NativeContinuationCachedRetryTelemetryCodecError::Snapshot)?;
    let count = snapshot.observations().len();
    let length = encoded_len(count)?;
    let mut bytes = Vec::with_capacity(length);
    bytes.extend_from_slice(&CODEC_MAGIC);
    bytes.extend_from_slice(&CODEC_REVISION.to_le_bytes());
    bytes.extend_from_slice(&CODEC_RESERVED.to_le_bytes());
    write_usize(
        &mut bytes,
        snapshot.capacity().get(),
        NativeContinuationCachedRetryTelemetryCodecField::Capacity,
        None,
    )?;
    bytes.extend_from_slice(&snapshot.metadata().evictions().to_le_bytes());
    bytes.extend_from_slice(&snapshot.metadata().last_sequence().to_le_bytes());
    let count_u64 = u64::try_from(count).map_err(|_error| {
        NativeContinuationCachedRetryTelemetryCodecError::EncodingRange {
            field:
                NativeContinuationCachedRetryTelemetryCodecField::
                    ObservationCount,
            observation: None,
        }
    })?;
    bytes.extend_from_slice(&count_u64.to_le_bytes());
    encode_telemetry(&mut bytes, snapshot.totals(), None)?;
    for (index, observation) in snapshot.observations().iter().enumerate() {
        bytes.extend_from_slice(&observation.sequence().to_le_bytes());
        encode_telemetry(&mut bytes, observation.telemetry(), Some(index))?;
    }
    debug_assert_eq!(
        bytes.len(),
        length,
        "canonical telemetry codec length drifted",
    );
    Ok(bytes)
}

fn decode_capacity(
    value: u64,
) -> Result<NonZeroUsize, NativeContinuationCachedRetryTelemetryCodecError> {
    let capacity = decode_usize(
        value,
        NativeContinuationCachedRetryTelemetryCodecField::Capacity,
        None,
    )?;
    NonZeroUsize::new(capacity)
        .ok_or(NativeContinuationCachedRetryTelemetryCodecError::CapacityZero)
}

fn decode_header(bytes: &[u8]) -> DecodedHeaderResult<'_> {
    if bytes.len() < HEADER_LEN {
        return Err(NativeContinuationCachedRetryTelemetryCodecError::Length {
            expected: HEADER_LEN,
            observed: bytes.len(),
        });
    }
    let mut reader = CodecReader::new(bytes);
    if reader.read_array::<8>()? != CODEC_MAGIC {
        return Err(NativeContinuationCachedRetryTelemetryCodecError::Magic);
    }
    let revision = reader.read_u16()?;
    if revision != CODEC_REVISION {
        return Err(
            NativeContinuationCachedRetryTelemetryCodecError::Version {
                observed: revision,
            },
        );
    }
    let reserved = reader.read_u16()?;
    if reserved != CODEC_RESERVED {
        return Err(
            NativeContinuationCachedRetryTelemetryCodecError::Reserved {
                observed: reserved,
            },
        );
    }
    let capacity = decode_capacity(reader.read_u64()?)?;
    let evictions = reader.read_u64()?;
    let last_sequence = reader.read_u64()?;
    let observation_count = decode_usize(
        reader.read_u64()?,
        NativeContinuationCachedRetryTelemetryCodecField::ObservationCount,
        None,
    )?;
    let expected = encoded_len(observation_count)?;
    if bytes.len() != expected {
        return Err(NativeContinuationCachedRetryTelemetryCodecError::Length {
            expected,
            observed: bytes.len(),
        });
    }
    Ok((reader, DecodedHeader {
        capacity,
        evictions,
        last_sequence,
        observation_count,
    }))
}

fn decode_observations(
    reader: &mut CodecReader<'_>,
    count: usize,
) -> Result<
    Vec<NativeContinuationCachedRetryTelemetryObservation>,
    NativeContinuationCachedRetryTelemetryCodecError,
> {
    let mut observations = Vec::with_capacity(count);
    for index in 0..count {
        let sequence = reader.read_u64()?;
        let telemetry = decode_telemetry(reader, Some(index))?;
        observations.push(
            NativeContinuationCachedRetryTelemetryObservation::new(
                sequence, telemetry,
            ),
        );
    }
    Ok(observations)
}

fn decode_telemetry(
    reader: &mut CodecReader<'_>,
    observation: Option<usize>,
) -> Result<
    NativeContinuationCachedRetryTelemetry,
    NativeContinuationCachedRetryTelemetryCodecError,
> {
    let fields = [
        NativeContinuationCachedRetryTelemetryCodecField::Attempts,
        NativeContinuationCachedRetryTelemetryCodecField::CompletedSteps,
        NativeContinuationCachedRetryTelemetryCodecField::EvictedKeys,
        NativeContinuationCachedRetryTelemetryCodecField::Hits,
        NativeContinuationCachedRetryTelemetryCodecField::Insertions,
        NativeContinuationCachedRetryTelemetryCodecField::RetiredKeys,
    ];
    let mut counts = [0; COUNTER_COUNT];
    for (count, field) in counts.iter_mut().zip(fields) {
        *count = decode_usize(reader.read_u64()?, field, observation)?;
    }
    Ok(NativeContinuationCachedRetryTelemetry::from_counts(counts))
}

fn decode_usize(
    value: u64,
    field: NativeContinuationCachedRetryTelemetryCodecField,
    observation: Option<usize>,
) -> Result<usize, NativeContinuationCachedRetryTelemetryCodecError> {
    usize::try_from(value).map_err(|_error| {
        NativeContinuationCachedRetryTelemetryCodecError::Representation {
            field,
            observation,
            value,
        }
    })
}

fn encode_telemetry(
    bytes: &mut Vec<u8>,
    telemetry: NativeContinuationCachedRetryTelemetry,
    observation: Option<usize>,
) -> Result<(), NativeContinuationCachedRetryTelemetryCodecError> {
    let fields = [
        (
            telemetry.attempts(),
            NativeContinuationCachedRetryTelemetryCodecField::Attempts,
        ),
        (
            telemetry.completed_steps(),
            NativeContinuationCachedRetryTelemetryCodecField::CompletedSteps,
        ),
        (
            telemetry.evicted_keys(),
            NativeContinuationCachedRetryTelemetryCodecField::EvictedKeys,
        ),
        (
            telemetry.hits(),
            NativeContinuationCachedRetryTelemetryCodecField::Hits,
        ),
        (
            telemetry.insertions(),
            NativeContinuationCachedRetryTelemetryCodecField::Insertions,
        ),
        (
            telemetry.retired_keys(),
            NativeContinuationCachedRetryTelemetryCodecField::RetiredKeys,
        ),
    ];
    for (value, field) in fields {
        write_usize(bytes, value, field, observation)?;
    }
    Ok(())
}

fn encoded_len(
    observation_count: usize,
) -> Result<usize, NativeContinuationCachedRetryTelemetryCodecError> {
    observation_count
        .checked_mul(OBSERVATION_LEN)
        .and_then(|records| HEADER_LEN.checked_add(records))
        .ok_or(NativeContinuationCachedRetryTelemetryCodecError::LengthOverflow)
}

fn format_encoding_range(
    formatter: &mut Formatter<'_>,
    field: NativeContinuationCachedRetryTelemetryCodecField,
    observation: Option<usize>,
) -> FormatResult {
    match observation {
        Some(index) => write!(
            formatter,
            concat!(
                "cached retry telemetry codec {} cannot be encoded at ",
                "observation {}",
            ),
            field, index,
        ),
        None => write!(
            formatter,
            concat!(
                "cached retry telemetry codec aggregate {} cannot be ",
                "encoded",
            ),
            field,
        ),
    }
}

fn format_representation(
    formatter: &mut Formatter<'_>,
    field: NativeContinuationCachedRetryTelemetryCodecField,
    observation: Option<usize>,
    value: u64,
) -> FormatResult {
    match observation {
        Some(index) => write!(
            formatter,
            concat!(
                "cached retry telemetry codec {} value {} cannot be ",
                "represented at observation {}",
            ),
            field, value, index,
        ),
        None => write!(
            formatter,
            concat!(
                "cached retry telemetry codec aggregate {} value {} ",
                "cannot be represented",
            ),
            field, value,
        ),
    }
}

fn write_usize(
    bytes: &mut Vec<u8>,
    value: usize,
    field: NativeContinuationCachedRetryTelemetryCodecField,
    observation: Option<usize>,
) -> Result<(), NativeContinuationCachedRetryTelemetryCodecError> {
    let encoded = u64::try_from(value).map_err(|_error| {
        NativeContinuationCachedRetryTelemetryCodecError::EncodingRange {
            field,
            observation,
        }
    })?;
    bytes.extend_from_slice(&encoded.to_le_bytes());
    Ok(())
}
