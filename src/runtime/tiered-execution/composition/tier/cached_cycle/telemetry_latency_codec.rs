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
//   - Canonical versioned bytes for validated latency histogram snapshots.
// - Must-Not:
//   - Persist bytes, read clocks, rebin, coordinate processes, or select
//     policy.
// - Allows:
//   - Inputs: one complete snapshot or one untrusted byte slice.
//   - Outputs: canonical little-endian bytes or one validated snapshot.
//   - Side effects: owned process-local allocation only.
// - Split-When:
//   - Compression, durable storage, or distributed merge gains authority.
// - Merge-When:
//   - One durable telemetry store owns framing and histogram validation.
// - Summary:
//   - Encodes and decodes exact latency snapshots with stable framing.
// - Description:
//   - Framing, representation, extrema flags, and semantics fail closed.
// - Usage:
//   - Transfer validated latency evidence through caller-owned byte channels.
// - Defaults:
//   - Revision one uses fixed-width little-endian unsigned integers.
//

//! Canonical byte transport for cached-retry latency histogram snapshots.

use std::fmt::{Display, Formatter, Result as FormatResult};

use super::{
    NativeContinuationCachedRetryLatencyHistogram,
    NativeContinuationCachedRetryLatencyHistogramSnapshot,
    NativeContinuationCachedRetryLatencySnapshotCounts,
    NativeContinuationCachedRetryLatencySnapshotError,
    NativeContinuationCachedRetryLatencySnapshotRange,
};

const CODEC_MAGIC: [u8; 8] = *b"MBLATN01";
const CODEC_REVISION: u16 = 1;
const CODEC_RESERVED: u16 = 0;
const HEADER_LEN: usize = 72;
const BUCKET_LEN: usize = 16;

/// Integer field whose canonical latency representation could not be admitted.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryLatencyCodecField {
    /// Samples above the final inclusive bound.
    AboveMaximum,
    /// Number of bound/count pairs.
    BoundCount,
    /// One inclusive bucket count.
    BucketCount,
    /// Exact sample count.
    Samples,
}

/// Why canonical latency snapshot byte transport failed closed.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryLatencyCodecError {
    /// An absent extremum retained a nonzero canonical payload.
    AbsentExtremaValue {
        /// `true` identifies maximum; `false` identifies minimum.
        maximum: bool,
        /// Supplied payload for the absent extremum.
        observed: u64,
    },
    /// A host integer cannot fit the canonical unsigned representation.
    EncodingRange {
        /// Exact field that could not be encoded.
        field: NativeContinuationCachedRetryLatencyCodecField,
        /// Zero-based bucket index, or `None` for aggregate evidence.
        bucket: Option<usize>,
    },
    /// One extrema-presence byte was neither zero nor one.
    Flag {
        /// `true` identifies the maximum flag; `false` identifies minimum.
        maximum: bool,
        /// Supplied flag byte.
        observed: u8,
    },
    /// Input length differs from exact framing evidence.
    Length {
        /// Exact required byte count.
        expected: usize,
        /// Supplied byte count.
        observed: usize,
    },
    /// Framing arithmetic overflowed before allocation or publication.
    LengthOverflow,
    /// The eight-byte format identity differs from revision-one framing.
    Magic,
    /// One canonical integer cannot be represented by this host.
    Representation {
        /// Exact field that could not be represented.
        field: NativeContinuationCachedRetryLatencyCodecField,
        /// Zero-based bucket index, or `None` for aggregate evidence.
        bucket: Option<usize>,
        /// Canonical value that exceeded the host representation.
        value: u64,
    },
    /// Reserved framing bits were nonzero.
    Reserved {
        /// Supplied reserved value.
        observed: u16,
    },
    /// Decoded histogram evidence failed exact semantic validation.
    Snapshot(Box<NativeContinuationCachedRetryLatencySnapshotError>),
    /// Framing revision is unsupported.
    Version {
        /// Supplied revision.
        observed: u16,
    },
}

struct CodecReader<'bytes> {
    bytes: &'bytes [u8],
    offset: usize,
}

struct DecodedLatencyRange {
    maximum: Option<u64>,
    minimum: Option<u64>,
    total: u128,
}

struct DecodedLatencyHeader {
    above_maximum: usize,
    bound_count: usize,
    maximum: Option<u64>,
    minimum: Option<u64>,
    samples: usize,
    total: u128,
}

type DecodedLatencyHeaderResult<'bytes> = Result<
    (CodecReader<'bytes>, DecodedLatencyHeader),
    NativeContinuationCachedRetryLatencyCodecError,
>;

impl Display for NativeContinuationCachedRetryLatencyCodecError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::AbsentExtremaValue { maximum, observed } => write!(
                f,
                "cached retry latency absent {} value {observed}",
                if *maximum {
                    "maximum"
                } else {
                    "minimum"
                },
            ),
            Self::EncodingRange { field, bucket } => {
                format_encoding_range(f, *field, *bucket)
            },
            Self::Flag { maximum, observed } => write!(
                f,
                "cached retry latency {} flag value {observed}",
                if *maximum {
                    "maximum"
                } else {
                    "minimum"
                },
            ),
            Self::Length { expected, observed } => write!(
                f,
                "cached retry latency codec length {observed}, expected \
                 {expected}",
            ),
            Self::LengthOverflow => {
                f.write_str("cached retry latency codec length overflow")
            },
            Self::Magic => {
                f.write_str("cached retry latency codec magic mismatch")
            },
            Self::Representation { field, bucket, value } => {
                format_representation(f, *field, *bucket, *value)
            },
            Self::Reserved { observed } => write!(
                f,
                "cached retry latency codec reserved value {observed}",
            ),
            Self::Snapshot(_error) => {
                f.write_str("cached retry latency codec snapshot rejected")
            },
            Self::Version { observed } => write!(
                f,
                "cached retry latency codec revision {observed} is unsupported",
            ),
        }
    }
}

impl Display for NativeContinuationCachedRetryLatencyCodecField {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::AboveMaximum => "above maximum",
            Self::BoundCount => "bound count",
            Self::BucketCount => "bucket count",
            Self::Samples => "samples",
        })
    }
}

impl<'bytes> CodecReader<'bytes> {
    const fn new(bytes: &'bytes [u8]) -> Self {
        Self { bytes, offset: 0 }
    }

    fn read_array<const N: usize>(
        &mut self,
    ) -> Result<[u8; N], NativeContinuationCachedRetryLatencyCodecError> {
        let end = self.offset.checked_add(N).ok_or(
            NativeContinuationCachedRetryLatencyCodecError::LengthOverflow,
        )?;
        let source = self.bytes.get(self.offset..end).ok_or(
            NativeContinuationCachedRetryLatencyCodecError::Length {
                expected: end,
                observed: self.bytes.len(),
            },
        )?;
        let mut value = [0; N];
        value.copy_from_slice(source);
        self.offset = end;
        Ok(value)
    }

    fn read_u128(
        &mut self,
    ) -> Result<u128, NativeContinuationCachedRetryLatencyCodecError> {
        Ok(u128::from_le_bytes(self.read_array()?))
    }

    fn read_u16(
        &mut self,
    ) -> Result<u16, NativeContinuationCachedRetryLatencyCodecError> {
        Ok(u16::from_le_bytes(self.read_array()?))
    }

    fn read_u64(
        &mut self,
    ) -> Result<u64, NativeContinuationCachedRetryLatencyCodecError> {
        Ok(u64::from_le_bytes(self.read_array()?))
    }

    fn read_u8(
        &mut self,
    ) -> Result<u8, NativeContinuationCachedRetryLatencyCodecError> {
        Ok(self.read_array::<1>()?[0])
    }
}

/// Decodes canonical bytes into one semantically validated latency snapshot.
///
/// # Errors
///
/// Returns exact framing, representation, or snapshot validation evidence.
pub fn decode_cached_retry_latency_snapshot(
    bytes: &[u8],
) -> Result<
    NativeContinuationCachedRetryLatencyHistogramSnapshot,
    NativeContinuationCachedRetryLatencyCodecError,
> {
    let (mut reader, header) = decode_latency_header(bytes)?;
    let mut upper_bounds = Vec::with_capacity(header.bound_count);
    let mut buckets = Vec::with_capacity(header.bound_count);
    for index in 0..header.bound_count {
        upper_bounds.push(reader.read_u64()?);
        buckets.push(decode_usize(
            reader.read_u64()?,
            NativeContinuationCachedRetryLatencyCodecField::BucketCount,
            Some(index),
        )?);
    }
    let snapshot = NativeContinuationCachedRetryLatencyHistogramSnapshot::new(
        upper_bounds,
        NativeContinuationCachedRetryLatencySnapshotCounts::new(
            buckets,
            header.above_maximum,
            header.samples,
        ),
        NativeContinuationCachedRetryLatencySnapshotRange::new(
            header.minimum,
            header.maximum,
            header.total,
        ),
    );
    let _validated =
        NativeContinuationCachedRetryLatencyHistogram::from_snapshot(
            snapshot.clone(),
        )
        .map_err(|error| {
            NativeContinuationCachedRetryLatencyCodecError::Snapshot(Box::new(
                error,
            ))
        })?;
    Ok(snapshot)
}

/// Encodes one semantically valid latency snapshot into canonical bytes.
///
/// # Errors
///
/// Returns exact snapshot, representation, or framing arithmetic failure.
pub fn encode_cached_retry_latency_snapshot(
    snapshot: &NativeContinuationCachedRetryLatencyHistogramSnapshot,
) -> Result<Vec<u8>, NativeContinuationCachedRetryLatencyCodecError> {
    let _validated =
        NativeContinuationCachedRetryLatencyHistogram::from_snapshot(
            snapshot.clone(),
        )
        .map_err(|error| {
            NativeContinuationCachedRetryLatencyCodecError::Snapshot(Box::new(
                error,
            ))
        })?;
    let bound_count = snapshot.upper_bounds().len();
    let length = encoded_latency_len(bound_count)?;
    let mut bytes = Vec::with_capacity(length);
    bytes.extend_from_slice(&CODEC_MAGIC);
    bytes.extend_from_slice(&CODEC_REVISION.to_le_bytes());
    bytes.extend_from_slice(&CODEC_RESERVED.to_le_bytes());
    write_usize(
        &mut bytes,
        bound_count,
        NativeContinuationCachedRetryLatencyCodecField::BoundCount,
        None,
    )?;
    write_usize(
        &mut bytes,
        snapshot.counts().above_maximum(),
        NativeContinuationCachedRetryLatencyCodecField::AboveMaximum,
        None,
    )?;
    write_usize(
        &mut bytes,
        snapshot.counts().samples(),
        NativeContinuationCachedRetryLatencyCodecField::Samples,
        None,
    )?;
    encode_latency_range(&mut bytes, snapshot.range());
    encode_latency_buckets(&mut bytes, snapshot)?;
    debug_assert_eq!(
        bytes.len(),
        length,
        "canonical latency codec length drifted",
    );
    Ok(bytes)
}

const fn decode_extremum(
    maximum: bool,
    flag: u8,
    value: u64,
) -> Result<Option<u64>, NativeContinuationCachedRetryLatencyCodecError> {
    match flag {
        0 if value == 0 => Ok(None),
        0 => Err(
            NativeContinuationCachedRetryLatencyCodecError::AbsentExtremaValue {
                maximum,
                observed: value,
            },
        ),
        1 => Ok(Some(value)),
        observed => Err(NativeContinuationCachedRetryLatencyCodecError::Flag {
            maximum,
            observed,
        }),
    }
}

fn decode_latency_header(bytes: &[u8]) -> DecodedLatencyHeaderResult<'_> {
    if bytes.len() < HEADER_LEN {
        return Err(NativeContinuationCachedRetryLatencyCodecError::Length {
            expected: HEADER_LEN,
            observed: bytes.len(),
        });
    }
    let mut reader = CodecReader::new(bytes);
    if reader.read_array::<8>()? != CODEC_MAGIC {
        return Err(NativeContinuationCachedRetryLatencyCodecError::Magic);
    }
    let revision = reader.read_u16()?;
    if revision != CODEC_REVISION {
        return Err(NativeContinuationCachedRetryLatencyCodecError::Version {
            observed: revision,
        });
    }
    let reserved = reader.read_u16()?;
    if reserved != CODEC_RESERVED {
        return Err(NativeContinuationCachedRetryLatencyCodecError::Reserved {
            observed: reserved,
        });
    }
    let bound_count = decode_usize(
        reader.read_u64()?,
        NativeContinuationCachedRetryLatencyCodecField::BoundCount,
        None,
    )?;
    let expected = encoded_latency_len(bound_count)?;
    if bytes.len() != expected {
        return Err(NativeContinuationCachedRetryLatencyCodecError::Length {
            expected,
            observed: bytes.len(),
        });
    }
    let above_maximum = decode_usize(
        reader.read_u64()?,
        NativeContinuationCachedRetryLatencyCodecField::AboveMaximum,
        None,
    )?;
    let samples = decode_usize(
        reader.read_u64()?,
        NativeContinuationCachedRetryLatencyCodecField::Samples,
        None,
    )?;
    let range = decode_latency_range(&mut reader)?;
    Ok((reader, DecodedLatencyHeader {
        above_maximum,
        bound_count,
        maximum: range.maximum,
        minimum: range.minimum,
        samples,
        total: range.total,
    }))
}

fn decode_latency_range(
    reader: &mut CodecReader<'_>,
) -> Result<DecodedLatencyRange, NativeContinuationCachedRetryLatencyCodecError>
{
    let minimum_flag = reader.read_u8()?;
    let maximum_flag = reader.read_u8()?;
    let reserved = reader.read_u16()?;
    if reserved != CODEC_RESERVED {
        return Err(NativeContinuationCachedRetryLatencyCodecError::Reserved {
            observed: reserved,
        });
    }
    let minimum_value = reader.read_u64()?;
    let maximum_value = reader.read_u64()?;
    let total = reader.read_u128()?;
    Ok(DecodedLatencyRange {
        maximum: decode_extremum(true, maximum_flag, maximum_value)?,
        minimum: decode_extremum(false, minimum_flag, minimum_value)?,
        total,
    })
}

fn decode_usize(
    value: u64,
    field: NativeContinuationCachedRetryLatencyCodecField,
    bucket: Option<usize>,
) -> Result<usize, NativeContinuationCachedRetryLatencyCodecError> {
    usize::try_from(value).map_err(|_error| {
        NativeContinuationCachedRetryLatencyCodecError::Representation {
            field,
            bucket,
            value,
        }
    })
}

fn encode_latency_buckets(
    bytes: &mut Vec<u8>,
    snapshot: &NativeContinuationCachedRetryLatencyHistogramSnapshot,
) -> Result<(), NativeContinuationCachedRetryLatencyCodecError> {
    for (index, (&bound, &count)) in snapshot
        .upper_bounds()
        .iter()
        .zip(snapshot.counts().bucket_counts())
        .enumerate()
    {
        bytes.extend_from_slice(&bound.to_le_bytes());
        write_usize(
            bytes,
            count,
            NativeContinuationCachedRetryLatencyCodecField::BucketCount,
            Some(index),
        )?;
    }
    Ok(())
}

fn encode_latency_range(
    bytes: &mut Vec<u8>,
    range: NativeContinuationCachedRetryLatencySnapshotRange,
) {
    let minimum = range.minimum_nanoseconds();
    let maximum = range.maximum_nanoseconds();
    bytes.push(u8::from(minimum.is_some()));
    bytes.push(u8::from(maximum.is_some()));
    bytes.extend_from_slice(&CODEC_RESERVED.to_le_bytes());
    bytes.extend_from_slice(&minimum.unwrap_or(0).to_le_bytes());
    bytes.extend_from_slice(&maximum.unwrap_or(0).to_le_bytes());
    bytes.extend_from_slice(&range.total_nanoseconds().to_le_bytes());
}

fn encoded_latency_len(
    bound_count: usize,
) -> Result<usize, NativeContinuationCachedRetryLatencyCodecError> {
    bound_count
        .checked_mul(BUCKET_LEN)
        .and_then(|records| HEADER_LEN.checked_add(records))
        .ok_or(NativeContinuationCachedRetryLatencyCodecError::LengthOverflow)
}

fn format_encoding_range(
    formatter: &mut Formatter<'_>,
    field: NativeContinuationCachedRetryLatencyCodecField,
    bucket: Option<usize>,
) -> FormatResult {
    match bucket {
        Some(index) => write!(
            formatter,
            "cached retry latency cannot encode {field} at bucket {index}",
        ),
        None => write!(
            formatter,
            "cached retry latency cannot encode aggregate {field}",
        ),
    }
}

fn format_representation(
    formatter: &mut Formatter<'_>,
    field: NativeContinuationCachedRetryLatencyCodecField,
    bucket: Option<usize>,
    value: u64,
) -> FormatResult {
    match bucket {
        Some(index) => write!(
            formatter,
            concat!(
                "cached retry latency cannot represent {} value {} at ",
                "bucket {}",
            ),
            field, value, index,
        ),
        None => write!(
            formatter,
            concat!(
                "cached retry latency cannot represent aggregate {} value ",
                "{}",
            ),
            field, value,
        ),
    }
}

fn write_usize(
    bytes: &mut Vec<u8>,
    value: usize,
    field: NativeContinuationCachedRetryLatencyCodecField,
    bucket: Option<usize>,
) -> Result<(), NativeContinuationCachedRetryLatencyCodecError> {
    let encoded = u64::try_from(value).map_err(|_error| {
        NativeContinuationCachedRetryLatencyCodecError::EncodingRange {
            field,
            bucket,
        }
    })?;
    bytes.extend_from_slice(&encoded.to_le_bytes());
    Ok(())
}
