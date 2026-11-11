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
//   - Canonical revisioned bytes for immutable synchronous dispatch-policy
//     snapshots.
// - Must-Not:
//   - Persist bytes, infer scheduling policy, inspect private scheduler state,
//     or execute queued continuations.
// - Allows:
//   - Inputs: one canonical policy snapshot or one untrusted fixed-width frame.
//   - Outputs: canonical little-endian bytes or one validated policy snapshot.
//   - Side effects: owned process-local allocation only.
// - Split-When:
//   - Migration, durable ownership, or concurrent publication gains authority.
// - Merge-When:
//   - Dispatch policy itself owns canonical byte framing and transfer
//     validation.
// - Summary:
//   - Encodes and decodes exact bounded dispatch-policy snapshots.
// - Description:
//   - Magic, revision, reserved fields, decision tags, bounds, and decision
//     payload semantics fail closed.
// - Usage:
//   - Transfer policy snapshots through caller-owned byte channels.
// - Defaults:
//   - Revision one is a fixed 32-byte little-endian frame.
//

//! Canonical byte transport for immutable synchronous dispatch policies.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::num::NonZeroUsize;

use crate::continuation_dispatch_policy::{
    NativeContinuationDispatchPolicy, NativeContinuationDispatchPolicyDecision,
    NativeContinuationDispatchPolicySnapshot,
};

const CODEC_LEN: usize = 32;
const CODEC_MAGIC: [u8; 8] = *b"MBDPOL01";
const CODEC_RESERVED: u16 = 0;
const CODEC_REVISION: u16 = 1;
const DECISION_COMPLETE_INTERPRETER: u16 = 0;
const DECISION_INTERPRET: u16 = 1;
const DECISION_YIELD_CALLER: u16 = 2;
const DECISION_YIELD_NATIVE_RETRY: u16 = 3;

/// Integer field whose canonical dispatch-policy representation was rejected.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyCodecField {
    /// Positive maximum synchronous worker-turn count.
    MaximumTurns,
    /// Positive interpreter step budget for the `Interpret` decision.
    StepBudget,
}

/// Why canonical dispatch-policy byte transport failed closed.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyCodecError {
    /// Canonical decision tag is not defined by this revision.
    DecisionKind {
        /// Rejected decision tag.
        observed: u16,
    },
    /// A host integer cannot fit the canonical unsigned representation.
    EncodingRange {
        /// Exact field that could not be encoded.
        field: NativeContinuationDispatchPolicyCodecField,
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
    /// Canonical maximum-turn count was zero.
    MaximumTurnsZero,
    /// A non-interpret decision carried a nonzero step-budget payload.
    NonInterpretBudget {
        /// Rejected canonical step-budget payload.
        observed: u64,
    },
    /// One canonical integer cannot be represented by this host.
    Representation {
        /// Exact field that could not be represented.
        field: NativeContinuationDispatchPolicyCodecField,
        /// Canonical value that exceeded host representation.
        value: u64,
    },
    /// Decision-reserved framing bits were nonzero.
    ReservedDecision {
        /// Supplied reserved value.
        observed: u16,
    },
    /// Header-reserved framing bits were nonzero.
    ReservedHeader {
        /// Supplied reserved value.
        observed: u16,
    },
    /// `Interpret` carried a zero step budget.
    StepBudgetZero,
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
    decision_kind: u16,
    maximum_turns: usize,
}

impl Display for NativeContinuationDispatchPolicyCodecError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::DecisionKind { observed } => write!(
                f,
                "dispatch policy decision tag {observed} is unsupported",
            ),
            Self::EncodingRange { field } => {
                write!(f, "dispatch policy {field} exceeds canonical range")
            },
            Self::Length { expected, observed } => write!(
                f,
                "dispatch policy codec length {observed}, expected {expected}",
            ),
            Self::Magic => f.write_str("dispatch policy codec magic mismatch"),
            Self::MaximumTurnsZero => {
                f.write_str("dispatch policy maximum turns is zero")
            },
            Self::NonInterpretBudget { observed } => write!(
                f,
                "non-interpret dispatch decision carried budget {observed}",
            ),
            Self::Representation { field, value } => write!(
                f,
                "dispatch policy {field} value {value} exceeds host range",
            ),
            Self::ReservedDecision { observed } => {
                write!(f, "dispatch policy decision reserved value {observed}")
            },
            Self::ReservedHeader { observed } => {
                write!(f, "dispatch policy header reserved value {observed}")
            },
            Self::StepBudgetZero => {
                f.write_str("dispatch policy interpreter step budget is zero")
            },
            Self::Version { observed } => write!(
                f,
                "dispatch policy codec revision {observed} is unsupported",
            ),
        }
    }
}

impl Display for NativeContinuationDispatchPolicyCodecField {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::MaximumTurns => "maximum turns",
            Self::StepBudget => "step budget",
        })
    }
}

impl<'bytes> CodecReader<'bytes> {
    const fn new(bytes: &'bytes [u8]) -> Self {
        Self { bytes, offset: 0 }
    }

    fn read_array<const N: usize>(
        &mut self,
    ) -> Result<[u8; N], NativeContinuationDispatchPolicyCodecError> {
        let end = self.offset.checked_add(N).ok_or(
            NativeContinuationDispatchPolicyCodecError::Length {
                expected: CODEC_LEN,
                observed: self.bytes.len(),
            },
        )?;
        let source = self.bytes.get(self.offset..end).ok_or(
            NativeContinuationDispatchPolicyCodecError::Length {
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
    ) -> Result<u16, NativeContinuationDispatchPolicyCodecError> {
        Ok(u16::from_le_bytes(self.read_array()?))
    }

    fn read_u64(
        &mut self,
    ) -> Result<u64, NativeContinuationDispatchPolicyCodecError> {
        Ok(u64::from_le_bytes(self.read_array()?))
    }
}

fn decode_decision(
    decision_kind: u16,
    budget: u64,
) -> Result<
    NativeContinuationDispatchPolicyDecision,
    NativeContinuationDispatchPolicyCodecError,
> {
    match decision_kind {
        DECISION_COMPLETE_INTERPRETER => {
            require_zero_budget(budget)?;
            Ok(NativeContinuationDispatchPolicyDecision::CompleteInterpreter)
        },
        DECISION_INTERPRET => {
            if budget == 0 {
                return Err(
                    NativeContinuationDispatchPolicyCodecError::StepBudgetZero,
                );
            }
            let decoded_budget = decode_usize(
                NativeContinuationDispatchPolicyCodecField::StepBudget,
                budget,
            )?;
            let step_budget = NonZeroUsize::new(decoded_budget).ok_or(
                NativeContinuationDispatchPolicyCodecError::StepBudgetZero,
            )?;
            Ok(NativeContinuationDispatchPolicyDecision::Interpret {
                step_budget,
            })
        },
        DECISION_YIELD_CALLER => {
            require_zero_budget(budget)?;
            Ok(NativeContinuationDispatchPolicyDecision::YieldCaller)
        },
        DECISION_YIELD_NATIVE_RETRY => {
            require_zero_budget(budget)?;
            Ok(NativeContinuationDispatchPolicyDecision::YieldNativeRetry)
        },
        observed => {
            Err(NativeContinuationDispatchPolicyCodecError::DecisionKind {
                observed,
            })
        },
    }
}

fn decode_frame(
    bytes: &[u8],
) -> Result<DecodedPolicyFrame, NativeContinuationDispatchPolicyCodecError> {
    if bytes.len() != CODEC_LEN {
        return Err(NativeContinuationDispatchPolicyCodecError::Length {
            expected: CODEC_LEN,
            observed: bytes.len(),
        });
    }
    let mut reader = CodecReader::new(bytes);
    if reader.read_array::<8>()? != CODEC_MAGIC {
        return Err(NativeContinuationDispatchPolicyCodecError::Magic);
    }
    let revision = reader.read_u16()?;
    if revision != CODEC_REVISION {
        return Err(NativeContinuationDispatchPolicyCodecError::Version {
            observed: revision,
        });
    }
    let header_reserved = reader.read_u16()?;
    if header_reserved != CODEC_RESERVED {
        return Err(
            NativeContinuationDispatchPolicyCodecError::ReservedHeader {
                observed: header_reserved,
            },
        );
    }
    let decision_kind = reader.read_u16()?;
    let decision_reserved = reader.read_u16()?;
    if decision_reserved != CODEC_RESERVED {
        return Err(
            NativeContinuationDispatchPolicyCodecError::ReservedDecision {
                observed: decision_reserved,
            },
        );
    }
    let maximum_turns = decode_usize(
        NativeContinuationDispatchPolicyCodecField::MaximumTurns,
        reader.read_u64()?,
    )?;
    Ok(DecodedPolicyFrame {
        budget: reader.read_u64()?,
        decision_kind,
        maximum_turns,
    })
}

/// Decodes one exact revision-one frame into a canonical dispatch-policy
/// snapshot.
///
/// # Errors
///
/// Returns framing, representation, bound, or decision semantic rejection.
pub fn decode_native_continuation_dispatch_policy_snapshot(
    bytes: &[u8],
) -> Result<
    NativeContinuationDispatchPolicySnapshot,
    NativeContinuationDispatchPolicyCodecError,
> {
    let frame = decode_frame(bytes)?;
    let maximum_turns = NonZeroUsize::new(frame.maximum_turns)
        .ok_or(NativeContinuationDispatchPolicyCodecError::MaximumTurnsZero)?;
    let decision = decode_decision(frame.decision_kind, frame.budget)?;
    Ok(
        NativeContinuationDispatchPolicy::new(maximum_turns, decision)
            .snapshot(),
    )
}

/// Encodes one canonical dispatch-policy snapshot into revision-one stable
/// bytes.
///
/// # Errors
///
/// Returns exact host-to-canonical integer representation failure.
pub fn encode_native_continuation_dispatch_policy_snapshot(
    snapshot: NativeContinuationDispatchPolicySnapshot,
) -> Result<Vec<u8>, NativeContinuationDispatchPolicyCodecError> {
    let maximum_turns = encode_usize(
        NativeContinuationDispatchPolicyCodecField::MaximumTurns,
        snapshot.maximum_turns().get(),
    )?;
    let (decision_kind, budget) = match snapshot.decision() {
        NativeContinuationDispatchPolicyDecision::CompleteInterpreter => {
            (DECISION_COMPLETE_INTERPRETER, 0)
        },
        NativeContinuationDispatchPolicyDecision::Interpret { step_budget } => {
            (
                DECISION_INTERPRET,
                encode_usize(
                    NativeContinuationDispatchPolicyCodecField::StepBudget,
                    step_budget.get(),
                )?,
            )
        },
        NativeContinuationDispatchPolicyDecision::YieldCaller => {
            (DECISION_YIELD_CALLER, 0)
        },
        NativeContinuationDispatchPolicyDecision::YieldNativeRetry => {
            (DECISION_YIELD_NATIVE_RETRY, 0)
        },
    };
    let mut bytes = Vec::with_capacity(CODEC_LEN);
    bytes.extend_from_slice(&CODEC_MAGIC);
    bytes.extend_from_slice(&CODEC_REVISION.to_le_bytes());
    bytes.extend_from_slice(&CODEC_RESERVED.to_le_bytes());
    bytes.extend_from_slice(&decision_kind.to_le_bytes());
    bytes.extend_from_slice(&CODEC_RESERVED.to_le_bytes());
    bytes.extend_from_slice(&maximum_turns.to_le_bytes());
    bytes.extend_from_slice(&budget.to_le_bytes());
    Ok(bytes)
}

fn decode_usize(
    field: NativeContinuationDispatchPolicyCodecField,
    value: u64,
) -> Result<usize, NativeContinuationDispatchPolicyCodecError> {
    usize::try_from(value).map_err(|_error| {
        NativeContinuationDispatchPolicyCodecError::Representation {
            field,
            value,
        }
    })
}

fn encode_usize(
    field: NativeContinuationDispatchPolicyCodecField,
    value: usize,
) -> Result<u64, NativeContinuationDispatchPolicyCodecError> {
    u64::try_from(value).map_err(|_error| {
        NativeContinuationDispatchPolicyCodecError::EncodingRange { field }
    })
}

const fn require_zero_budget(
    budget: u64,
) -> Result<(), NativeContinuationDispatchPolicyCodecError> {
    if budget == 0 {
        Ok(())
    } else {
        Err(
            NativeContinuationDispatchPolicyCodecError::NonInterpretBudget {
                observed: budget,
            },
        )
    }
}
