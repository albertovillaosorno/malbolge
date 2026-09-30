// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Canonical versioned bytes for executable-sequence cache limits.
// - Must-Not:
//   - Persist mappings, usage, FIFO identity, executable authority, or storage
//     locations.
// - Allows:
//   - Inputs: one immutable cache-limit value or one untrusted fixed frame.
//   - Outputs: canonical little-endian bytes or validated cache limits.
//   - Side effects: owned process-local allocation only.
// - Split-When:
//   - Durable cache manifests or migration gain independent authority.
// - Merge-When:
//   - Executable-cache policy owns canonical configuration transport directly.
// - Summary:
//   - Transfers caller-owned cache limits without serializing live residency.
// - Description:
//   - Entry capacity is always positive; optional mapping and byte limits are
//     represented by explicit flags and zero when absent.
// - Usage:
//   - Persist cache policy separately from verified artifacts and live
//     mappings.
// - Defaults:
//   - Revision one is a fixed 40-byte little-endian frame.
//

//! Canonical transport for executable-sequence cache configuration.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::num::NonZeroUsize;

use super::executable_cache_capacity::NativeExecutableSequenceCacheLimits;

const CODEC_LEN: usize = 40;
const CODEC_MAGIC: [u8; 8] = *b"MBXCL001";
const CODEC_REVISION: u16 = 1;
const FLAG_MAPPED_BYTES: u16 = 1 << 0;
const FLAG_MAPPINGS: u16 = 1 << 1;
const KNOWN_FLAGS: u16 = FLAG_MAPPED_BYTES | FLAG_MAPPINGS;
const RESERVED: u32 = 0;

/// Limit field whose canonical representation failed admission.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeExecutableSequenceCacheLimitsCodecField {
    /// Positive complete-entry limit.
    Entries,
    /// Optional positive admitted mapped-byte limit.
    MappedBytes,
    /// Optional positive live-mapping limit.
    Mappings,
}

/// Why executable-cache limit transport failed closed.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeExecutableSequenceCacheLimitsCodecError {
    /// One host integer exceeded canonical representation.
    EncodingRange {
        /// Exact field that could not be encoded.
        field: NativeExecutableSequenceCacheLimitsCodecField,
    },
    /// Required entry limit was zero.
    EntriesZero,
    /// Unknown option flag bits were present.
    Flags {
        /// Exact rejected flag bitset.
        observed: u16,
    },
    /// Input length differs from revision-one framing.
    Length {
        /// Required canonical byte count.
        expected: usize,
        /// Supplied byte count.
        observed: usize,
    },
    /// Magic does not identify executable-cache limit framing.
    Magic,
    /// Optional field carried bytes despite its absence flag.
    OptionalAbsentValue {
        /// Exact absent optional field carrying nonzero bytes.
        field: NativeExecutableSequenceCacheLimitsCodecField,
        /// Rejected canonical value.
        value: u64,
    },
    /// Optional field was zero despite its presence flag.
    OptionalZero {
        /// Exact optional field carrying the invalid zero.
        field: NativeExecutableSequenceCacheLimitsCodecField,
    },
    /// One canonical integer exceeded host representation.
    Representation {
        /// Exact field that could not be represented.
        field: NativeExecutableSequenceCacheLimitsCodecField,
        /// Canonical value that exceeded host representation.
        value: u64,
    },
    /// Reserved framing bits were nonzero.
    Reserved {
        /// Exact rejected reserved value.
        observed: u32,
    },
    /// Framing revision is unsupported.
    Version {
        /// Exact supplied revision.
        observed: u16,
    },
}

struct CodecReader<'bytes> {
    bytes: &'bytes [u8],
    offset: usize,
}

impl Display for NativeExecutableSequenceCacheLimitsCodecError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::EncodingRange { field } => {
                write!(f, "executable cache {field} exceeds canonical range")
            },
            Self::EntriesZero => {
                f.write_str("executable cache entry limit is zero")
            },
            Self::Flags { observed } => write!(
                f,
                concat!(
                    "executable cache limit codec flags ",
                    "{:#06x} unsupported",
                ),
                observed,
            ),
            Self::Length { expected, observed } => write!(
                f,
                concat!(
                    "executable cache limit codec length {}, ",
                    "expected {}",
                ),
                observed, expected,
            ),
            Self::Magic => {
                f.write_str("executable cache limit codec magic mismatch")
            },
            Self::OptionalAbsentValue { field, value } => write!(
                f,
                "executable cache absent {field} carried value {value}",
            ),
            Self::OptionalZero { field } => {
                write!(f, "executable cache optional {field} is zero")
            },
            Self::Representation { field, value } => write!(
                f,
                "executable cache {field} value {value} exceeds host range",
            ),
            Self::Reserved { observed } => write!(
                f,
                "executable cache limit codec reserved value {observed}",
            ),
            Self::Version { observed } => write!(
                f,
                "executable cache limit codec revision {observed} unsupported",
            ),
        }
    }
}

impl Display for NativeExecutableSequenceCacheLimitsCodecField {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Entries => "entry limit",
            Self::MappedBytes => "mapped-byte limit",
            Self::Mappings => "mapping limit",
        })
    }
}

impl<'bytes> CodecReader<'bytes> {
    const fn new(bytes: &'bytes [u8]) -> Self {
        Self { bytes, offset: 0 }
    }

    fn read_array<const N: usize>(
        &mut self,
    ) -> Result<[u8; N], NativeExecutableSequenceCacheLimitsCodecError> {
        let end = self.offset.checked_add(N).ok_or(
            NativeExecutableSequenceCacheLimitsCodecError::Length {
                expected: CODEC_LEN,
                observed: self.bytes.len(),
            },
        )?;
        let source = self.bytes.get(self.offset..end).ok_or(
            NativeExecutableSequenceCacheLimitsCodecError::Length {
                expected: CODEC_LEN,
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
    ) -> Result<u16, NativeExecutableSequenceCacheLimitsCodecError> {
        Ok(u16::from_le_bytes(self.read_array()?))
    }

    fn read_u32(
        &mut self,
    ) -> Result<u32, NativeExecutableSequenceCacheLimitsCodecError> {
        Ok(u32::from_le_bytes(self.read_array()?))
    }

    fn read_u64(
        &mut self,
    ) -> Result<u64, NativeExecutableSequenceCacheLimitsCodecError> {
        Ok(u64::from_le_bytes(self.read_array()?))
    }
}

fn decode_usize(
    field: NativeExecutableSequenceCacheLimitsCodecField,
    value: u64,
) -> Result<usize, NativeExecutableSequenceCacheLimitsCodecError> {
    usize::try_from(value).map_err(|_representation_error| {
        NativeExecutableSequenceCacheLimitsCodecError::Representation {
            field,
            value,
        }
    })
}

fn decode_optional(
    field: NativeExecutableSequenceCacheLimitsCodecField,
    present: bool,
    value: u64,
) -> Result<Option<NonZeroUsize>, NativeExecutableSequenceCacheLimitsCodecError>
{
    if !present {
        if value == 0 {
            return Ok(None);
        }
        return Err(
            NativeExecutableSequenceCacheLimitsCodecError::OptionalAbsentValue {
                field,
                value,
            },
        );
    }
    let decoded_value = decode_usize(field, value)?;
    NonZeroUsize::new(decoded_value).map(Some).ok_or(
        NativeExecutableSequenceCacheLimitsCodecError::OptionalZero { field },
    )
}

fn encode_usize(
    field: NativeExecutableSequenceCacheLimitsCodecField,
    value: NonZeroUsize,
) -> Result<u64, NativeExecutableSequenceCacheLimitsCodecError> {
    u64::try_from(value.get()).map_err(|_representation_error| {
        NativeExecutableSequenceCacheLimitsCodecError::EncodingRange { field }
    })
}

/// Decodes one exact revision-one executable-cache limit frame.
///
/// # Errors
///
/// Returns framing, representation, or positive-limit semantic rejection.
pub fn decode_native_executable_sequence_cache_limits(
    bytes: &[u8],
) -> Result<
    NativeExecutableSequenceCacheLimits,
    NativeExecutableSequenceCacheLimitsCodecError,
> {
    if bytes.len() != CODEC_LEN {
        return Err(NativeExecutableSequenceCacheLimitsCodecError::Length {
            expected: CODEC_LEN,
            observed: bytes.len(),
        });
    }
    let mut reader = CodecReader::new(bytes);
    if reader.read_array::<8>()? != CODEC_MAGIC {
        return Err(NativeExecutableSequenceCacheLimitsCodecError::Magic);
    }
    let revision = reader.read_u16()?;
    if revision != CODEC_REVISION {
        return Err(NativeExecutableSequenceCacheLimitsCodecError::Version {
            observed: revision,
        });
    }
    let flags = reader.read_u16()?;
    if flags & !KNOWN_FLAGS != 0 {
        return Err(NativeExecutableSequenceCacheLimitsCodecError::Flags {
            observed: flags,
        });
    }
    let reserved = reader.read_u32()?;
    if reserved != RESERVED {
        return Err(NativeExecutableSequenceCacheLimitsCodecError::Reserved {
            observed: reserved,
        });
    }
    let entries_value = decode_usize(
        NativeExecutableSequenceCacheLimitsCodecField::Entries,
        reader.read_u64()?,
    )?;
    let entry_limit = NonZeroUsize::new(entries_value)
        .ok_or(NativeExecutableSequenceCacheLimitsCodecError::EntriesZero)?;
    let mappings = decode_optional(
        NativeExecutableSequenceCacheLimitsCodecField::Mappings,
        flags & FLAG_MAPPINGS != 0,
        reader.read_u64()?,
    )?;
    let mapped_bytes = decode_optional(
        NativeExecutableSequenceCacheLimitsCodecField::MappedBytes,
        flags & FLAG_MAPPED_BYTES != 0,
        reader.read_u64()?,
    )?;

    let mut limits = NativeExecutableSequenceCacheLimits::new(entry_limit);
    if let Some(limit) = mappings {
        limits = limits.with_mapping_limit(limit);
    }
    if let Some(limit) = mapped_bytes {
        limits = limits.with_mapped_byte_limit(limit);
    }
    Ok(limits)
}

/// Encodes one cache-limit value into canonical revision-one bytes.
///
/// # Errors
///
/// Returns representation failure if a host integer cannot fit canonical u64.
pub fn encode_native_executable_sequence_cache_limits(
    limits: NativeExecutableSequenceCacheLimits,
) -> Result<Vec<u8>, NativeExecutableSequenceCacheLimitsCodecError> {
    let entries = encode_usize(
        NativeExecutableSequenceCacheLimitsCodecField::Entries,
        limits.entry_limit(),
    )?;
    let mappings = limits
        .mapping_limit()
        .map(|value| {
            encode_usize(
                NativeExecutableSequenceCacheLimitsCodecField::Mappings,
                value,
            )
        })
        .transpose()?;
    let mapped_bytes = limits
        .mapped_byte_limit()
        .map(|value| {
            encode_usize(
                NativeExecutableSequenceCacheLimitsCodecField::MappedBytes,
                value,
            )
        })
        .transpose()?;
    let flags = if mapped_bytes.is_some() {
        FLAG_MAPPED_BYTES
    } else {
        0
    } | if mappings.is_some() {
        FLAG_MAPPINGS
    } else {
        0
    };

    let mut bytes = Vec::with_capacity(CODEC_LEN);
    bytes.extend_from_slice(&CODEC_MAGIC);
    bytes.extend_from_slice(&CODEC_REVISION.to_le_bytes());
    bytes.extend_from_slice(&flags.to_le_bytes());
    bytes.extend_from_slice(&RESERVED.to_le_bytes());
    bytes.extend_from_slice(&entries.to_le_bytes());
    bytes.extend_from_slice(&mappings.unwrap_or_default().to_le_bytes());
    bytes.extend_from_slice(&mapped_bytes.unwrap_or_default().to_le_bytes());
    Ok(bytes)
}

#[cfg(test)]
mod tests {
    #[test]
    fn exact_limits_round_trip() -> Result<(), String> {
        use std::num::NonZeroUsize;

        use crate::execution_native::NativeExecutableSequenceCacheLimits;
        let Some(entries) = NonZeroUsize::new(3) else {
            return Err(String::from("entry test limit missing"));
        };
        let Some(mappings) = NonZeroUsize::new(5) else {
            return Err(String::from("mapping test limit missing"));
        };
        let Some(mapped_bytes) = NonZeroUsize::new(7_000) else {
            return Err(String::from("byte test limit missing"));
        };
        let limits = NativeExecutableSequenceCacheLimits::new(entries)
            .with_mapping_limit(mappings)
            .with_mapped_byte_limit(mapped_bytes);
        let bytes =
            super::encode_native_executable_sequence_cache_limits(limits)
                .map_err(|error| error.to_string())?;
        if bytes.len() == 40
            && super::decode_native_executable_sequence_cache_limits(&bytes)
                == Ok(limits)
        {
            Ok(())
        } else {
            Err(String::from("cache-limit round trip drifted"))
        }
    }

    #[test]
    fn absent_optional_limits_are_canonical() -> Result<(), String> {
        use std::num::NonZeroUsize;

        use crate::execution_native::NativeExecutableSequenceCacheLimits;
        let Some(entries) = NonZeroUsize::new(2) else {
            return Err(String::from("entry test limit missing"));
        };
        let limits = NativeExecutableSequenceCacheLimits::new(entries);
        let bytes =
            super::encode_native_executable_sequence_cache_limits(limits)
                .map_err(|error| error.to_string())?;
        let flags = bytes
            .get(10..12)
            .ok_or_else(|| String::from("cache-limit flags missing"))?;
        let option_payload = bytes.get(24..40).ok_or_else(|| {
            String::from("cache-limit option payload missing")
        })?;
        if flags == [0, 0]
            && option_payload == [0; 16]
            && super::decode_native_executable_sequence_cache_limits(&bytes)
                == Ok(limits)
        {
            Ok(())
        } else {
            Err(String::from("absent cache limits were not canonical"))
        }
    }

    #[test]
    fn malformed_header_fails_closed() -> Result<(), String> {
        use std::num::NonZeroUsize;

        use super::{
            NativeExecutableSequenceCacheLimitsCodecError as Error,
            decode_native_executable_sequence_cache_limits as decode,
        };
        use crate::execution_native::NativeExecutableSequenceCacheLimits;
        let Some(entries) = NonZeroUsize::new(2) else {
            return Err(String::from("entry test limit missing"));
        };
        let bytes = super::encode_native_executable_sequence_cache_limits(
            NativeExecutableSequenceCacheLimits::new(entries),
        )
        .map_err(|error| error.to_string())?;

        let mut magic = bytes.clone();
        let first = magic
            .get_mut(0)
            .ok_or_else(|| String::from("cache-limit magic missing"))?;
        *first ^= 0xff;

        let mut flags = bytes.clone();
        flags
            .get_mut(10..12)
            .ok_or_else(|| String::from("cache-limit flags missing"))?
            .copy_from_slice(&4u16.to_le_bytes());

        let truncated = bytes
            .get(..39)
            .ok_or_else(|| String::from("cache-limit truncation missing"))?;

        if decode(&magic) == Err(Error::Magic)
            && decode(&flags) == Err(Error::Flags { observed: 4 })
            && decode(truncated)
                == Err(Error::Length {
                    expected: 40,
                    observed: 39,
                })
        {
            Ok(())
        } else {
            Err(String::from("malformed cache-limit header was admitted"))
        }
    }
}
