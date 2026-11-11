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
//   - Canonical versioned bytes for one cache-trigger cadence cursor.
// - Must-Not:
//   - Persist bytes, perform CAS, infer scheduling, activate cache policy, or
//     assign durable ownership.
// - Allows:
//   - Inputs: one validated cadence cursor or one untrusted fixed-width frame.
//   - Outputs: canonical little-endian bytes or one validated cadence cursor.
//   - Side effects: owned process-local allocation only.
// - Split-When:
//   - Migration, durable publication, or multi-process cursor ownership gains
//     independent authority.
// - Merge-When:
//   - One durable cadence owner subsumes framing and state validation.
// - Summary:
//   - Transfers exact cadence interval and next-due/exhausted state.
// - Description:
//   - Positive interval is mandatory; exhausted state requires zero due bytes.
// - Usage:
//   - Transport cursor state separately from telemetry and cache-limit policy.
// - Defaults:
//   - Revision one is a fixed 32-byte little-endian frame.
//

//! Canonical byte transport for cache-policy trigger cadence cursors.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::num::NonZeroU64;

use crate::executable_cache_limits_trigger_cadence as trigger;

const CODEC_LEN: usize = 32;
const CODEC_MAGIC: [u8; 8] = *b"MBCTC001";
const CODEC_REVISION: u16 = 1;
const FLAG_EXHAUSTED: u16 = 1;
const KNOWN_FLAGS: u16 = FLAG_EXHAUSTED;
const RESERVED: u32 = 0;

type TriggerCadence = trigger::NativeExecutableCacheLimitsTriggerCadence;

/// Why cache-trigger cadence byte transport failed closed.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeExecutableCacheLimitsTriggerCadenceCodecError {
    /// Exhausted framing carried a nonzero next-due sequence.
    ExhaustedValue {
        /// Rejected next-due value.
        value: u64,
    },
    /// Unknown framing flag bits were present.
    Flags {
        /// Exact rejected flag bitset.
        observed: u16,
    },
    /// Positive cadence interval was encoded as zero.
    IntervalZero,
    /// Input length differs from the fixed revision-one frame.
    Length {
        /// Exact required byte count.
        expected: usize,
        /// Supplied byte count.
        observed: usize,
    },
    /// Eight-byte frame identity differs from revision-one cadence framing.
    Magic,
    /// Active cadence state encoded a zero next-due sequence.
    NextDueZero,
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

impl Display for NativeExecutableCacheLimitsTriggerCadenceCodecError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::ExhaustedValue { value } => write!(
                f,
                "exhausted cache trigger cadence carried due value {value}",
            ),
            Self::Flags { observed } => write!(
                f,
                "cache trigger cadence flags {observed:#06x} unsupported",
            ),
            Self::IntervalZero => {
                f.write_str("cache trigger cadence interval is zero")
            },
            Self::Length { expected, observed } => write!(
                f,
                "cache trigger cadence length {observed}, expected {expected}",
            ),
            Self::Magic => {
                f.write_str("cache trigger cadence codec magic mismatch")
            },
            Self::NextDueZero => {
                f.write_str("active cache trigger cadence due sequence is zero")
            },
            Self::Reserved { observed } => {
                write!(f, "cache trigger cadence reserved value {observed}")
            },
            Self::Version { observed } => write!(
                f,
                "cache trigger cadence revision {observed} unsupported",
            ),
        }
    }
}

impl<'bytes> CodecReader<'bytes> {
    const fn new(bytes: &'bytes [u8]) -> Self {
        Self { bytes, offset: 0 }
    }

    fn read_array<const N: usize>(
        &mut self,
    ) -> Result<[u8; N], NativeExecutableCacheLimitsTriggerCadenceCodecError>
    {
        let end = self.offset.checked_add(N).ok_or(
            NativeExecutableCacheLimitsTriggerCadenceCodecError::Length {
                expected: CODEC_LEN,
                observed: self.bytes.len(),
            },
        )?;
        let source = self.bytes.get(self.offset..end).ok_or(
            NativeExecutableCacheLimitsTriggerCadenceCodecError::Length {
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
    ) -> Result<u16, NativeExecutableCacheLimitsTriggerCadenceCodecError> {
        Ok(u16::from_le_bytes(self.read_array()?))
    }

    fn read_u32(
        &mut self,
    ) -> Result<u32, NativeExecutableCacheLimitsTriggerCadenceCodecError> {
        Ok(u32::from_le_bytes(self.read_array()?))
    }

    fn read_u64(
        &mut self,
    ) -> Result<u64, NativeExecutableCacheLimitsTriggerCadenceCodecError> {
        Ok(u64::from_le_bytes(self.read_array()?))
    }
}

/// Decodes one exact revision-one cadence cursor frame.
///
/// # Errors
///
/// Returns framing or positive-state semantic rejection evidence.
pub fn decode_native_executable_cache_limits_trigger_cadence(
    bytes: &[u8],
) -> Result<TriggerCadence, NativeExecutableCacheLimitsTriggerCadenceCodecError>
{
    if bytes.len() != CODEC_LEN {
        return Err(
            NativeExecutableCacheLimitsTriggerCadenceCodecError::Length {
                expected: CODEC_LEN,
                observed: bytes.len(),
            },
        );
    }
    let mut reader = CodecReader::new(bytes);
    if reader.read_array::<8>()? != CODEC_MAGIC {
        return Err(NativeExecutableCacheLimitsTriggerCadenceCodecError::Magic);
    }
    let revision = reader.read_u16()?;
    if revision != CODEC_REVISION {
        return Err(
            NativeExecutableCacheLimitsTriggerCadenceCodecError::Version {
                observed: revision,
            },
        );
    }
    let flags = reader.read_u16()?;
    if flags & !KNOWN_FLAGS != 0 {
        return Err(
            NativeExecutableCacheLimitsTriggerCadenceCodecError::Flags {
                observed: flags,
            },
        );
    }
    let reserved = reader.read_u32()?;
    if reserved != RESERVED {
        return Err(
            NativeExecutableCacheLimitsTriggerCadenceCodecError::Reserved {
                observed: reserved,
            },
        );
    }
    let interval = NonZeroU64::new(reader.read_u64()?).ok_or(
        NativeExecutableCacheLimitsTriggerCadenceCodecError::IntervalZero,
    )?;
    let due_value = reader.read_u64()?;
    if flags & FLAG_EXHAUSTED != 0 {
        if due_value != 0 {
            return Err(
                NativeExecutableCacheLimitsTriggerCadenceCodecError::
                    ExhaustedValue { value: due_value },
            );
        }
        return Ok(TriggerCadence::exhausted(interval));
    }
    let due_sequence = NonZeroU64::new(due_value).ok_or(
        NativeExecutableCacheLimitsTriggerCadenceCodecError::NextDueZero,
    )?;
    Ok(TriggerCadence::new(due_sequence, interval))
}

/// Encodes one validated cadence cursor into canonical revision-one bytes.
#[must_use]
pub fn encode_native_executable_cache_limits_trigger_cadence(
    cadence: TriggerCadence,
) -> Vec<u8> {
    let (flags, due_value) = cadence
        .next_due_sequence()
        .map_or((FLAG_EXHAUSTED, 0), |due_sequence| (0, due_sequence.get()));
    let mut bytes = Vec::with_capacity(CODEC_LEN);
    bytes.extend_from_slice(&CODEC_MAGIC);
    bytes.extend_from_slice(&CODEC_REVISION.to_le_bytes());
    bytes.extend_from_slice(&flags.to_le_bytes());
    bytes.extend_from_slice(&RESERVED.to_le_bytes());
    bytes.extend_from_slice(&cadence.interval().get().to_le_bytes());
    bytes.extend_from_slice(&due_value.to_le_bytes());
    bytes
}

#[cfg(test)]
#[path = "../../../../../tests/tiered/cache_trigger_codec.rs"]
mod tests;
