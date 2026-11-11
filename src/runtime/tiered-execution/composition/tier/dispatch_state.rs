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
//   - Canonical versioned bytes for one revisioned active dispatch-policy
//     state.
// - Must-Not:
//   - Persist bytes, perform CAS, infer policy, coordinate processes, or assign
//     revision chronology beyond exact carried values.
// - Allows:
//   - Inputs: one validated active state or one untrusted fixed-width frame.
//   - Outputs: canonical bytes or one validated active-policy state.
//   - Side effects: owned process-local allocation only.
// - Split-When:
//   - Migration or cross-process optimistic publication gains authority.
// - Merge-When:
//   - Active-policy ownership directly owns durable framing and validation.
// - Summary:
//   - Encodes exact active revision plus canonical dispatch-policy bytes.
// - Description:
//   - Outer framing and nested policy framing both fail closed.
// - Usage:
//   - Transfer validated active state through caller-owned byte channels.
// - Defaults:
//   - Revision one is one fixed 52-byte little-endian frame.
//

//! Canonical byte transport for revisioned active synchronous dispatch policy.

use std::fmt::{Display, Formatter, Result as FormatResult};

use crate::continuation_dispatch_policy::NativeContinuationDispatchPolicy;
use crate::continuation_dispatch_policy_codec::{
    NativeContinuationDispatchPolicyCodecError,
    decode_native_continuation_dispatch_policy_snapshot,
    encode_native_continuation_dispatch_policy_snapshot,
};
use crate::continuation_dispatch_policy_owner::{
    NativeContinuationDispatchPolicyRevision,
    NativeContinuationDispatchPolicyState,
};

const CODEC_LEN: usize = 52;
const CODEC_MAGIC: [u8; 8] = *b"MBDPST01";
const CODEC_RESERVED: u16 = 0;
const CODEC_REVISION: u16 = 1;
const POLICY_LEN: usize = 32;

/// Why canonical active dispatch-policy state byte transport failed closed.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyStateCodecError {
    /// Input length differs from the fixed revision-one frame.
    Length {
        /// Exact required byte count.
        expected: usize,
        /// Supplied byte count.
        observed: usize,
    },
    /// Eight-byte state-format identity differs from revision-one framing.
    Magic,
    /// Nested canonical dispatch-policy framing or semantics failed.
    Policy(NativeContinuationDispatchPolicyCodecError),
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

impl Display for NativeContinuationDispatchPolicyStateCodecError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Length { expected, observed } => write!(
                f,
                "dispatch policy state length {observed}, expected {expected}",
            ),
            Self::Magic => {
                f.write_str("dispatch policy state codec magic mismatch")
            },
            Self::Policy(error) => Display::fmt(error, f),
            Self::Reserved { observed } => {
                write!(f, "dispatch policy state reserved value {observed}")
            },
            Self::Version { observed } => write!(
                f,
                "dispatch policy state revision {observed} is unsupported",
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
    ) -> Result<[u8; N], NativeContinuationDispatchPolicyStateCodecError> {
        let end = self.offset.checked_add(N).ok_or(
            NativeContinuationDispatchPolicyStateCodecError::Length {
                expected: CODEC_LEN,
                observed: self.bytes.len(),
            },
        )?;
        let source = self.bytes.get(self.offset..end).ok_or(
            NativeContinuationDispatchPolicyStateCodecError::Length {
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
    ) -> Result<u16, NativeContinuationDispatchPolicyStateCodecError> {
        Ok(u16::from_le_bytes(self.read_array()?))
    }

    fn read_u64(
        &mut self,
    ) -> Result<u64, NativeContinuationDispatchPolicyStateCodecError> {
        Ok(u64::from_le_bytes(self.read_array()?))
    }
}

/// Decodes one exact revision-one frame into validated active-policy state.
///
/// # Errors
///
/// Returns outer framing or nested policy rejection evidence.
pub fn decode_native_continuation_dispatch_policy_state(
    bytes: &[u8],
) -> Result<
    NativeContinuationDispatchPolicyState,
    NativeContinuationDispatchPolicyStateCodecError,
> {
    if bytes.len() != CODEC_LEN {
        return Err(NativeContinuationDispatchPolicyStateCodecError::Length {
            expected: CODEC_LEN,
            observed: bytes.len(),
        });
    }
    let mut reader = CodecReader::new(bytes);
    if reader.read_array::<8>()? != CODEC_MAGIC {
        return Err(NativeContinuationDispatchPolicyStateCodecError::Magic);
    }
    let revision = reader.read_u16()?;
    if revision != CODEC_REVISION {
        return Err(NativeContinuationDispatchPolicyStateCodecError::Version {
            observed: revision,
        });
    }
    let reserved = reader.read_u16()?;
    if reserved != CODEC_RESERVED {
        return Err(
            NativeContinuationDispatchPolicyStateCodecError::Reserved {
                observed: reserved,
            },
        );
    }
    let active_revision = NativeContinuationDispatchPolicyRevision::from_value(
        reader.read_u64()?,
    );
    let policy_bytes = reader.read_array::<POLICY_LEN>()?;
    let snapshot =
        decode_native_continuation_dispatch_policy_snapshot(&policy_bytes)
            .map_err(NativeContinuationDispatchPolicyStateCodecError::Policy)?;
    Ok(NativeContinuationDispatchPolicyState::new(
        NativeContinuationDispatchPolicy::from_snapshot(snapshot),
        active_revision,
    ))
}

/// Encodes one validated active-policy state into revision-one stable bytes.
///
/// # Errors
///
/// Returns nested policy representation failure before producing bytes.
pub fn encode_native_continuation_dispatch_policy_state(
    state: NativeContinuationDispatchPolicyState,
) -> Result<Vec<u8>, NativeContinuationDispatchPolicyStateCodecError> {
    let policy_bytes = encode_native_continuation_dispatch_policy_snapshot(
        state.policy().snapshot(),
    )
    .map_err(NativeContinuationDispatchPolicyStateCodecError::Policy)?;
    let mut bytes = Vec::with_capacity(CODEC_LEN);
    bytes.extend_from_slice(&CODEC_MAGIC);
    bytes.extend_from_slice(&CODEC_REVISION.to_le_bytes());
    bytes.extend_from_slice(&CODEC_RESERVED.to_le_bytes());
    bytes.extend_from_slice(&state.revision().value().to_le_bytes());
    bytes.extend_from_slice(&policy_bytes);
    Ok(bytes)
}
