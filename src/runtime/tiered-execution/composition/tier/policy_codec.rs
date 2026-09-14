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
//   - Canonical versioned bytes for immutable native retry-policy snapshots.
// - Must-Not:
//   - Persist bytes, publish global policy, infer fallback, or execute a tier.
// - Allows:
//   - Inputs: one canonical policy snapshot or one untrusted fixed-width frame.
//   - Outputs: canonical little-endian bytes or one validated policy snapshot.
//   - Side effects: owned process-local allocation only.
// - Split-When:
//   - Migration, durable ownership, or concurrent publication gains authority.
// - Merge-When:
//   - Retry policy itself owns canonical byte framing and transfer validation.
// - Summary:
//   - Encodes and decodes exact retry-policy snapshots with stable framing.
// - Description:
//   - Magic, revision, reserved fields, fallback tag, and budgets fail closed.
// - Usage:
//   - Transfer policy snapshots through caller-owned byte channels.
// - Defaults:
//   - Revision one is a fixed 32-byte little-endian frame.
//

//! Canonical byte transport for immutable native retry-policy snapshots.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::num::NonZeroUsize;

use crate::retry_policy::{
    NativeContinuationRetryFallback, NativeContinuationRetryFallbackSnapshot,
    NativeContinuationRetryPolicy, NativeContinuationRetryPolicySnapshot,
};

const CODEC_LEN: usize = 32;
const CODEC_MAGIC: [u8; 8] = *b"MBRPOL01";
const CODEC_RESERVED: u16 = 0;
const CODEC_REVISION: u16 = 1;
const FALLBACK_COMPLETE: u16 = 0;
const FALLBACK_SLICED: u16 = 1;

/// Integer field whose canonical policy representation could not be admitted.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationRetryPolicyCodecField {
    /// Configured maximum native retry attempts.
    MaximumNativeAttempts,
    /// Positive sliced-fallback interpreter step budget.
    SliceStepBudget,
}

/// Why canonical retry-policy byte transport failed closed.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationRetryPolicyCodecError {
    /// Complete fallback carried a nonzero sliced-fallback payload.
    CompleteBudget {
        /// Rejected canonical sliced-fallback payload.
        observed: u64,
    },
    /// A host integer cannot fit the canonical unsigned representation.
    EncodingRange {
        /// Exact field that could not be encoded.
        field: NativeContinuationRetryPolicyCodecField,
    },
    /// Canonical fallback tag is not defined by this revision.
    FallbackKind {
        /// Rejected fallback tag.
        observed: u16,
    },
    /// Input length differs from the fixed revision-one frame.
    Length {
        /// Exact required byte count.
        expected: usize,
        /// Supplied byte count.
        observed: usize,
    },
    /// Eight-byte format identity differs from revision-one framing.
    Magic,
    /// One canonical integer cannot be represented by this host.
    Representation {
        /// Exact field that could not be represented.
        field: NativeContinuationRetryPolicyCodecField,
        /// Canonical value that exceeded host representation.
        value: u64,
    },
    /// Fallback-reserved framing bits were nonzero.
    ReservedFallback {
        /// Supplied reserved value.
        observed: u16,
    },
    /// Header-reserved framing bits were nonzero.
    ReservedHeader {
        /// Supplied reserved value.
        observed: u16,
    },
    /// Sliced fallback carried a zero step budget.
    SliceBudgetZero,
    /// Framing revision is unsupported.
    Version {
        /// Supplied framing revision.
        observed: u16,
    },
}

struct CodecReader<'bytes> {
    bytes: &'bytes [u8],
    offset: usize,
}

struct DecodedPolicyFrame {
    budget: u64,
    fallback_kind: u16,
    maximum: usize,
}

impl Display for NativeContinuationRetryPolicyCodecError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::CompleteBudget { observed } => write!(
                f,
                "complete retry fallback carried sliced budget {observed}",
            ),
            Self::EncodingRange { field } => {
                write!(f, "retry policy {field} exceeds canonical range")
            },
            Self::FallbackKind { observed } => {
                write!(f, "retry policy fallback tag {observed} is unsupported")
            },
            Self::Length { expected, observed } => write!(
                f,
                "retry policy codec length {observed}, expected {expected}",
            ),
            Self::Magic => f.write_str("retry policy codec magic mismatch"),
            Self::Representation { field, value } => write!(
                f,
                "retry policy {field} value {value} exceeds host range",
            ),
            Self::ReservedFallback { observed } => {
                write!(f, "retry policy fallback reserved value {observed}")
            },
            Self::ReservedHeader { observed } => {
                write!(f, "retry policy header reserved value {observed}")
            },
            Self::SliceBudgetZero => {
                f.write_str("retry policy sliced fallback budget is zero")
            },
            Self::Version { observed } => write!(
                f,
                "retry policy codec revision {observed} is unsupported",
            ),
        }
    }
}

impl Display for NativeContinuationRetryPolicyCodecField {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::MaximumNativeAttempts => "maximum native attempts",
            Self::SliceStepBudget => "slice step budget",
        })
    }
}

impl<'bytes> CodecReader<'bytes> {
    const fn new(bytes: &'bytes [u8]) -> Self {
        Self { bytes, offset: 0 }
    }

    fn read_array<const N: usize>(
        &mut self,
    ) -> Result<[u8; N], NativeContinuationRetryPolicyCodecError> {
        let end = self.offset.checked_add(N).ok_or(
            NativeContinuationRetryPolicyCodecError::Length {
                expected: CODEC_LEN,
                observed: self.bytes.len(),
            },
        )?;
        let source = self.bytes.get(self.offset..end).ok_or(
            NativeContinuationRetryPolicyCodecError::Length {
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
    ) -> Result<u16, NativeContinuationRetryPolicyCodecError> {
        Ok(u16::from_le_bytes(self.read_array()?))
    }

    fn read_u64(
        &mut self,
    ) -> Result<u64, NativeContinuationRetryPolicyCodecError> {
        Ok(u64::from_le_bytes(self.read_array()?))
    }
}

fn decode_fallback(
    fallback_kind: u16,
    budget: u64,
) -> Result<
    NativeContinuationRetryFallbackSnapshot,
    NativeContinuationRetryPolicyCodecError,
> {
    match fallback_kind {
        FALLBACK_COMPLETE => {
            if budget != 0 {
                return Err(
                    NativeContinuationRetryPolicyCodecError::CompleteBudget {
                        observed: budget,
                    },
                );
            }
            Ok(NativeContinuationRetryFallbackSnapshot::Complete)
        },
        FALLBACK_SLICED => {
            if budget == 0 {
                return Err(
                    NativeContinuationRetryPolicyCodecError::SliceBudgetZero,
                );
            }
            let decoded_budget = decode_usize(
                NativeContinuationRetryPolicyCodecField::SliceStepBudget,
                budget,
            )?;
            let step_budget = NonZeroUsize::new(decoded_budget).ok_or(
                NativeContinuationRetryPolicyCodecError::SliceBudgetZero,
            )?;
            Ok(NativeContinuationRetryFallbackSnapshot::Sliced { step_budget })
        },
        observed => {
            Err(NativeContinuationRetryPolicyCodecError::FallbackKind {
                observed,
            })
        },
    }
}

fn decode_frame(
    bytes: &[u8],
) -> Result<DecodedPolicyFrame, NativeContinuationRetryPolicyCodecError> {
    if bytes.len() != CODEC_LEN {
        return Err(NativeContinuationRetryPolicyCodecError::Length {
            expected: CODEC_LEN,
            observed: bytes.len(),
        });
    }
    let mut reader = CodecReader::new(bytes);
    if reader.read_array::<8>()? != CODEC_MAGIC {
        return Err(NativeContinuationRetryPolicyCodecError::Magic);
    }
    let revision = reader.read_u16()?;
    if revision != CODEC_REVISION {
        return Err(NativeContinuationRetryPolicyCodecError::Version {
            observed: revision,
        });
    }
    let header_reserved = reader.read_u16()?;
    if header_reserved != CODEC_RESERVED {
        return Err(NativeContinuationRetryPolicyCodecError::ReservedHeader {
            observed: header_reserved,
        });
    }
    let fallback_kind = reader.read_u16()?;
    let fallback_reserved = reader.read_u16()?;
    if fallback_reserved != CODEC_RESERVED {
        return Err(
            NativeContinuationRetryPolicyCodecError::ReservedFallback {
                observed: fallback_reserved,
            },
        );
    }
    let maximum = decode_usize(
        NativeContinuationRetryPolicyCodecField::MaximumNativeAttempts,
        reader.read_u64()?,
    )?;
    Ok(DecodedPolicyFrame {
        budget: reader.read_u64()?,
        fallback_kind,
        maximum,
    })
}

/// Decodes one exact revision-one frame into a canonical policy snapshot.
///
/// # Errors
///
/// Returns framing, representation, or fallback semantic rejection evidence.
pub fn decode_native_continuation_retry_policy_snapshot(
    bytes: &[u8],
) -> Result<
    NativeContinuationRetryPolicySnapshot,
    NativeContinuationRetryPolicyCodecError,
> {
    let frame = decode_frame(bytes)?;
    let fallback = decode_fallback(frame.fallback_kind, frame.budget)?;
    Ok(NativeContinuationRetryPolicy::new(
        frame.maximum,
        NativeContinuationRetryFallback::from_snapshot(fallback),
    )
    .snapshot())
}

/// Encodes one canonical policy snapshot into revision-one stable bytes.
///
/// # Errors
///
/// Returns exact host-to-canonical integer representation failure.
pub fn encode_native_continuation_retry_policy_snapshot(
    snapshot: NativeContinuationRetryPolicySnapshot,
) -> Result<Vec<u8>, NativeContinuationRetryPolicyCodecError> {
    let maximum = encode_usize(
        NativeContinuationRetryPolicyCodecField::MaximumNativeAttempts,
        snapshot.max_native_attempts(),
    )?;
    let (fallback_kind, budget) = match snapshot.fallback() {
        NativeContinuationRetryFallbackSnapshot::Complete => {
            (FALLBACK_COMPLETE, 0)
        },
        NativeContinuationRetryFallbackSnapshot::Sliced { step_budget } => (
            FALLBACK_SLICED,
            encode_usize(
                NativeContinuationRetryPolicyCodecField::SliceStepBudget,
                step_budget.get(),
            )?,
        ),
    };
    let mut bytes = Vec::with_capacity(CODEC_LEN);
    bytes.extend_from_slice(&CODEC_MAGIC);
    bytes.extend_from_slice(&CODEC_REVISION.to_le_bytes());
    bytes.extend_from_slice(&CODEC_RESERVED.to_le_bytes());
    bytes.extend_from_slice(&fallback_kind.to_le_bytes());
    bytes.extend_from_slice(&CODEC_RESERVED.to_le_bytes());
    bytes.extend_from_slice(&maximum.to_le_bytes());
    bytes.extend_from_slice(&budget.to_le_bytes());
    Ok(bytes)
}

fn decode_usize(
    field: NativeContinuationRetryPolicyCodecField,
    value: u64,
) -> Result<usize, NativeContinuationRetryPolicyCodecError> {
    usize::try_from(value).map_err(|_error| {
        NativeContinuationRetryPolicyCodecError::Representation { field, value }
    })
}

fn encode_usize(
    field: NativeContinuationRetryPolicyCodecField,
    value: usize,
) -> Result<u64, NativeContinuationRetryPolicyCodecError> {
    u64::try_from(value).map_err(|_error| {
        NativeContinuationRetryPolicyCodecError::EncodingRange { field }
    })
}
