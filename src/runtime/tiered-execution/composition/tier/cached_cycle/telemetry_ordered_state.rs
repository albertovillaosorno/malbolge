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
//   - Canonical bytes for external order plus exact count-window state.
// - Must-Not:
//   - Persist, source order, merge windows, or reinterpret nested telemetry.
// - Allows:
//   - Inputs: one ordered-window owner or one untrusted byte slice.
//   - Outputs: canonical versioned bytes or reconstructed exact ordered owner.
//   - Side effects: owned process-local allocation only.
// - Split-When:
//   - Migration or another ordered-state revision gains semantics.
// - Merge-When:
//   - One durable ordered telemetry store owns framing and publication.
// - Summary:
//   - Frames optional external order around canonical count-window bytes.
// - Description:
//   - Order presence is explicit; nested count bytes retain their own
//     validator.
// - Usage:
//   - Transfer exact ordered count telemetry through caller-owned byte
//     channels.
// - Defaults:
//   - Absent order requires a canonical zero value in the outer frame.
//

//! Canonical framing for caller-ordered cached-retry count telemetry state.

use std::fmt::{Display, Formatter, Result as FormatResult};

use super::{
    NativeContinuationCachedRetryTelemetryBatchOrder,
    NativeContinuationCachedRetryTelemetryCodecError,
    NativeContinuationCachedRetryTelemetryOrderedWindow,
    NativeContinuationCachedRetryTelemetryWindow,
    decode_cached_retry_telemetry_snapshot,
    encode_cached_retry_telemetry_snapshot,
};

const ORDERED_STATE_MAGIC: [u8; 8] = *b"MBTORD01";
const ORDERED_STATE_REVISION: u16 = 1;
const ORDER_PRESENT: u16 = 1;
const HEADER_LEN: usize = 28;

type OrderedStateCodecError =
    NativeContinuationCachedRetryTelemetryOrderedStateCodecError;

type DecodedOrderedHeader<'bytes> = Result<
    (
        Option<NativeContinuationCachedRetryTelemetryBatchOrder>,
        &'bytes [u8],
    ),
    OrderedStateCodecError,
>;

/// Why ordered count-telemetry state framing failed closed.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryTelemetryOrderedStateCodecError {
    /// Absent-order framing carried a nonzero value and was not canonical.
    AbsentOrderValue {
        /// Nonzero value supplied while order presence was clear.
        observed: u64,
    },
    /// Unknown order-presence or reserved outer bits were set.
    Flags {
        /// Supplied outer flags value.
        observed: u16,
    },
    /// Input length differs from exact outer framing evidence.
    Length {
        /// Exact required byte count.
        expected: usize,
        /// Supplied byte count.
        observed: usize,
    },
    /// Outer framing length arithmetic overflowed.
    LengthOverflow,
    /// Eight-byte ordered-state identity differs from revision one.
    Magic,
    /// Nested count-window canonical framing or semantics failed.
    Telemetry(Box<NativeContinuationCachedRetryTelemetryCodecError>),
    /// Nested payload length cannot be represented by this host.
    TelemetryLengthRepresentation {
        /// Canonical unsigned nested byte count.
        observed: u64,
    },
    /// Outer framing revision is unsupported.
    Version {
        /// Supplied outer revision.
        observed: u16,
    },
}

impl Display for NativeContinuationCachedRetryTelemetryOrderedStateCodecError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::AbsentOrderValue { observed } => write!(
                f,
                "ordered telemetry absent order carried value {observed}",
            ),
            Self::Length { expected, observed } => write!(
                f,
                "ordered telemetry length {observed}, expected {expected}",
            ),
            Self::LengthOverflow => {
                f.write_str("ordered telemetry framing length overflow")
            },
            Self::Magic => {
                f.write_str("ordered telemetry codec magic mismatch")
            },
            Self::Telemetry(_error) => {
                f.write_str("ordered telemetry nested count state rejected")
            },
            Self::TelemetryLengthRepresentation { observed } => write!(
                f,
                concat!(
                    "ordered telemetry nested length {} ",
                    "is not representable",
                ),
                observed,
            ),
            Self::Flags { observed } => {
                write!(f, "ordered telemetry flags {observed} are unsupported")
            },
            Self::Version { observed } => write!(
                f,
                "ordered telemetry codec revision {observed} is unsupported",
            ),
        }
    }
}

/// Decodes canonical bytes into exact ordered count-telemetry ownership.
///
/// # Errors
///
/// Returns outer framing, representation, canonical-order, or nested count
/// telemetry rejection evidence.
pub fn decode_cached_retry_telemetry_ordered_state(
    bytes: &[u8],
) -> Result<
    NativeContinuationCachedRetryTelemetryOrderedWindow,
    OrderedStateCodecError,
> {
    let (order, payload) = decode_ordered_header(bytes)?;
    let snapshot = decode_cached_retry_telemetry_snapshot(payload)
        .map_err(|error| OrderedStateCodecError::Telemetry(Box::new(error)))?;
    let window =
        NativeContinuationCachedRetryTelemetryWindow::from_snapshot(snapshot)
            .map_err(|error| {
            OrderedStateCodecError::Telemetry(Box::new(
                NativeContinuationCachedRetryTelemetryCodecError::Snapshot(
                    error,
                ),
            ))
        })?;
    Ok(
        NativeContinuationCachedRetryTelemetryOrderedWindow::from_parts(
            window, order,
        ),
    )
}

fn decode_ordered_header(bytes: &[u8]) -> DecodedOrderedHeader<'_> {
    if bytes.len() < HEADER_LEN {
        return Err(OrderedStateCodecError::Length {
            expected: HEADER_LEN,
            observed: bytes.len(),
        });
    }
    if bytes.get(0..8) != Some(&ORDERED_STATE_MAGIC) {
        return Err(OrderedStateCodecError::Magic);
    }
    let revision = read_u16(bytes, 8)?;
    if revision != ORDERED_STATE_REVISION {
        return Err(OrderedStateCodecError::Version { observed: revision });
    }
    let flags = read_u16(bytes, 10)?;
    if flags & !ORDER_PRESENT != 0 {
        return Err(OrderedStateCodecError::Flags { observed: flags });
    }
    let order_value = read_u64(bytes, 12)?;
    let order = decode_order(flags, order_value)?;
    let payload_u64 = read_u64(bytes, 20)?;
    let payload_len = usize::try_from(payload_u64).map_err(|_error| {
        OrderedStateCodecError::TelemetryLengthRepresentation {
            observed: payload_u64,
        }
    })?;
    let expected = HEADER_LEN
        .checked_add(payload_len)
        .ok_or(OrderedStateCodecError::LengthOverflow)?;
    if bytes.len() != expected {
        return Err(OrderedStateCodecError::Length {
            expected,
            observed: bytes.len(),
        });
    }
    let payload =
        bytes
            .get(HEADER_LEN..)
            .ok_or(OrderedStateCodecError::Length {
                expected: HEADER_LEN,
                observed: bytes.len(),
            })?;
    Ok((order, payload))
}

const fn decode_order(
    flags: u16,
    value: u64,
) -> Result<
    Option<NativeContinuationCachedRetryTelemetryBatchOrder>,
    OrderedStateCodecError,
> {
    if flags & ORDER_PRESENT == ORDER_PRESENT {
        return Ok(Some(
            NativeContinuationCachedRetryTelemetryBatchOrder::from_value(value),
        ));
    }
    if value != 0 {
        return Err(OrderedStateCodecError::AbsentOrderValue {
            observed: value,
        });
    }
    Ok(None)
}

/// Encodes exact ordered count telemetry into canonical revision-one bytes.
///
/// # Errors
///
/// Returns nested count telemetry, representation, or framing arithmetic
/// failure.
pub fn encode_cached_retry_telemetry_ordered_state(
    ordered: &NativeContinuationCachedRetryTelemetryOrderedWindow,
) -> Result<Vec<u8>, OrderedStateCodecError> {
    let telemetry =
        encode_cached_retry_telemetry_snapshot(&ordered.window().snapshot())
            .map_err(|error| {
                OrderedStateCodecError::Telemetry(Box::new(error))
            })?;
    let payload_len = u64::try_from(telemetry.len())
        .map_err(|_error| OrderedStateCodecError::LengthOverflow)?;
    let length = HEADER_LEN
        .checked_add(telemetry.len())
        .ok_or(OrderedStateCodecError::LengthOverflow)?;
    let (flags, order_value) = ordered
        .last_order()
        .map_or((0, 0), |order| (ORDER_PRESENT, order.value()));
    let mut bytes = Vec::with_capacity(length);
    bytes.extend_from_slice(&ORDERED_STATE_MAGIC);
    bytes.extend_from_slice(&ORDERED_STATE_REVISION.to_le_bytes());
    bytes.extend_from_slice(&flags.to_le_bytes());
    bytes.extend_from_slice(&order_value.to_le_bytes());
    bytes.extend_from_slice(&payload_len.to_le_bytes());
    bytes.extend_from_slice(&telemetry);
    debug_assert_eq!(
        bytes.len(),
        length,
        "ordered telemetry encoded length drifted",
    );
    Ok(bytes)
}

fn read_u16(
    bytes: &[u8],
    offset: usize,
) -> Result<u16, OrderedStateCodecError> {
    let end = offset
        .checked_add(2)
        .ok_or(OrderedStateCodecError::LengthOverflow)?;
    let source =
        bytes
            .get(offset..end)
            .ok_or(OrderedStateCodecError::Length {
                expected: end,
                observed: bytes.len(),
            })?;
    let mut value = [0; 2];
    value.copy_from_slice(source);
    Ok(u16::from_le_bytes(value))
}

fn read_u64(
    bytes: &[u8],
    offset: usize,
) -> Result<u64, OrderedStateCodecError> {
    let end = offset
        .checked_add(8)
        .ok_or(OrderedStateCodecError::LengthOverflow)?;
    let source =
        bytes
            .get(offset..end)
            .ok_or(OrderedStateCodecError::Length {
                expected: end,
                observed: bytes.len(),
            })?;
    let mut value = [0; 8];
    value.copy_from_slice(source);
    Ok(u64::from_le_bytes(value))
}
