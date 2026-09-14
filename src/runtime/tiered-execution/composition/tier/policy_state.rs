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
//   - Canonical versioned bytes for one revisioned active retry-policy state.
// - Must-Not:
//   - Persist bytes, perform CAS, infer policy, or coordinate processes.
// - Allows:
//   - Inputs: one validated active state or one untrusted fixed-width frame.
//   - Outputs: canonical bytes or one validated active-policy state.
//   - Side effects: owned process-local allocation only.
// - Split-When:
//   - Migration or cross-process optimistic publication gains authority.
// - Merge-When:
//   - Active-policy ownership directly owns durable framing and validation.
// - Summary:
//   - Encodes exact active revision plus canonical retry-policy bytes.
// - Description:
//   - Outer framing and nested policy framing both fail closed.
// - Usage:
//   - Transfer validated active state through caller-owned byte channels.
// - Defaults:
//   - Revision one is one fixed 52-byte little-endian frame.
//

//! Canonical byte transport for revisioned active native retry-policy state.

use std::fmt::{Display, Formatter, Result as FormatResult};

use crate::retry_policy::NativeContinuationRetryPolicy;
use crate::retry_policy_codec::{
    NativeContinuationRetryPolicyCodecError,
    decode_native_continuation_retry_policy_snapshot,
    encode_native_continuation_retry_policy_snapshot,
};
use crate::retry_policy_owner::{
    NativeContinuationRetryPolicyRevision, NativeContinuationRetryPolicyState,
};

const CODEC_LEN: usize = 52;
const CODEC_MAGIC: [u8; 8] = *b"MBRPST01";
const CODEC_RESERVED: u16 = 0;
const CODEC_REVISION: u16 = 1;
const POLICY_LEN: usize = 32;

/// Why canonical active-policy state byte transport failed closed.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationRetryPolicyStateCodecError {
    /// Input length differs from the fixed revision-one frame.
    Length {
        /// Exact required byte count.
        expected: usize,
        /// Supplied byte count.
        observed: usize,
    },
    /// Eight-byte state-format identity differs from revision-one framing.
    Magic,
    /// Nested canonical retry-policy framing or semantics failed.
    Policy(NativeContinuationRetryPolicyCodecError),
    /// Reserved state-framing bits were nonzero.
    Reserved {
        /// Supplied reserved value.
        observed: u16,
    },
    /// State framing revision is unsupported.
    Version {
        /// Supplied state framing revision.
        observed: u16,
    },
}

struct CodecReader<'bytes> {
    bytes: &'bytes [u8],
    offset: usize,
}

impl Display for NativeContinuationRetryPolicyStateCodecError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Length { expected, observed } => write!(
                f,
                concat!("retry policy state codec length {}, ", "expected {}",),
                observed, expected,
            ),
            Self::Magic => {
                f.write_str("retry policy state codec magic mismatch")
            },
            Self::Policy(error) => Display::fmt(error, f),
            Self::Reserved { observed } => {
                write!(f, "retry policy state reserved value {observed}")
            },
            Self::Version { observed } => write!(
                f,
                "retry policy state revision {observed} is unsupported",
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
    ) -> Result<[u8; N], NativeContinuationRetryPolicyStateCodecError> {
        let end = self.offset.checked_add(N).ok_or(
            NativeContinuationRetryPolicyStateCodecError::Length {
                expected: CODEC_LEN,
                observed: self.bytes.len(),
            },
        )?;
        let source = self.bytes.get(self.offset..end).ok_or(
            NativeContinuationRetryPolicyStateCodecError::Length {
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
    ) -> Result<u16, NativeContinuationRetryPolicyStateCodecError> {
        Ok(u16::from_le_bytes(self.read_array()?))
    }

    fn read_u64(
        &mut self,
    ) -> Result<u64, NativeContinuationRetryPolicyStateCodecError> {
        Ok(u64::from_le_bytes(self.read_array()?))
    }
}

/// Decodes one exact revision-one frame into validated active-policy state.
///
/// # Errors
///
/// Returns outer framing or nested policy rejection evidence.
pub fn decode_native_continuation_retry_policy_state(
    bytes: &[u8],
) -> Result<
    NativeContinuationRetryPolicyState,
    NativeContinuationRetryPolicyStateCodecError,
> {
    if bytes.len() != CODEC_LEN {
        return Err(NativeContinuationRetryPolicyStateCodecError::Length {
            expected: CODEC_LEN,
            observed: bytes.len(),
        });
    }
    let mut reader = CodecReader::new(bytes);
    if reader.read_array::<8>()? != CODEC_MAGIC {
        return Err(NativeContinuationRetryPolicyStateCodecError::Magic);
    }
    let revision = reader.read_u16()?;
    if revision != CODEC_REVISION {
        return Err(NativeContinuationRetryPolicyStateCodecError::Version {
            observed: revision,
        });
    }
    let reserved = reader.read_u16()?;
    if reserved != CODEC_RESERVED {
        return Err(NativeContinuationRetryPolicyStateCodecError::Reserved {
            observed: reserved,
        });
    }
    let active_revision =
        NativeContinuationRetryPolicyRevision::from_value(reader.read_u64()?);
    let policy_bytes = reader.read_array::<POLICY_LEN>()?;
    let snapshot =
        decode_native_continuation_retry_policy_snapshot(&policy_bytes)
            .map_err(NativeContinuationRetryPolicyStateCodecError::Policy)?;
    Ok(NativeContinuationRetryPolicyState::new(
        NativeContinuationRetryPolicy::from_snapshot(snapshot),
        active_revision,
    ))
}

/// Encodes one validated active-policy state into revision-one stable bytes.
///
/// # Errors
///
/// Returns nested policy representation failure before producing bytes.
pub fn encode_native_continuation_retry_policy_state(
    state: NativeContinuationRetryPolicyState,
) -> Result<Vec<u8>, NativeContinuationRetryPolicyStateCodecError> {
    let policy_bytes = encode_native_continuation_retry_policy_snapshot(
        state.policy().snapshot(),
    )
    .map_err(NativeContinuationRetryPolicyStateCodecError::Policy)?;
    let mut bytes = Vec::with_capacity(CODEC_LEN);
    bytes.extend_from_slice(&CODEC_MAGIC);
    bytes.extend_from_slice(&CODEC_REVISION.to_le_bytes());
    bytes.extend_from_slice(&CODEC_RESERVED.to_le_bytes());
    bytes.extend_from_slice(&state.revision().value().to_le_bytes());
    bytes.extend_from_slice(&policy_bytes);
    Ok(bytes)
}
