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
//   - Regression coverage for canonical cache-trigger cadence cursor bytes.
// - Must-Not:
//   - Persist bytes, perform CAS, activate policy, or infer lifecycle
//     semantics.
// - Allows:
//   - Inputs: validated cursor state and deliberately malformed fixed frames.
//   - Outputs: exact round-trip or stable decode rejection evidence.
//   - Side effects: test-local allocation only.
// - Split-When:
//   - Durable cursor publication gains independent codec fixtures.
// - Merge-When:
//   - Parent codec no longer requires private framing regression coverage.
// - Summary:
//   - Proves active/exhausted canonical bytes and malformed-state rejection.
// - Description:
//   - Revision-one framing preserves positive interval and optional next due.
// - Usage:
//   - Compiled only under Rust test configuration.
// - Defaults:
//   - No persistence or migration authority is implied by byte round-trip.
//

//! Regression coverage for cache-trigger cadence cursor framing.

use std::num::NonZeroU64;

use crate::executable_cache_limits_trigger_cadence as trigger;

type TriggerCadence = trigger::NativeExecutableCacheLimitsTriggerCadence;

type CodecError = super::NativeExecutableCacheLimitsTriggerCadenceCodecError;

fn nonzero(value: u64) -> Result<NonZeroU64, String> {
    NonZeroU64::new(value)
        .ok_or_else(|| String::from("test cursor value must be positive"))
}

fn replace(
    bytes: &mut [u8],
    offset: usize,
    replacement: &[u8],
) -> Result<(), String> {
    let end = offset
        .checked_add(replacement.len())
        .ok_or_else(|| String::from("test replacement offset overflow"))?;
    let destination = bytes
        .get_mut(offset..end)
        .ok_or_else(|| String::from("test replacement outside frame"))?;
    destination.copy_from_slice(replacement);
    Ok(())
}

#[test]
fn active_cursor_round_trips_canonical_bytes() -> Result<(), String> {
    let cadence = TriggerCadence::new(nonzero(5)?, nonzero(3)?);
    let bytes =
        super::encode_native_executable_cache_limits_trigger_cadence(cadence);
    let mut expected = Vec::new();
    expected.extend_from_slice(b"MBCTC001");
    expected.extend_from_slice(&1u16.to_le_bytes());
    expected.extend_from_slice(&0u16.to_le_bytes());
    expected.extend_from_slice(&0u32.to_le_bytes());
    expected.extend_from_slice(&3u64.to_le_bytes());
    expected.extend_from_slice(&5u64.to_le_bytes());
    let decoded =
        super::decode_native_executable_cache_limits_trigger_cadence(&bytes)
            .map_err(|error| error.to_string())?;
    if bytes == expected && decoded == cadence {
        Ok(())
    } else {
        Err(String::from("active cadence canonical bytes drifted"))
    }
}

#[test]
fn exhausted_cursor_round_trips_canonical_bytes() -> Result<(), String> {
    let cadence = TriggerCadence::exhausted(nonzero(7)?);
    let bytes =
        super::encode_native_executable_cache_limits_trigger_cadence(cadence);
    let mut expected = Vec::new();
    expected.extend_from_slice(b"MBCTC001");
    expected.extend_from_slice(&1u16.to_le_bytes());
    expected.extend_from_slice(&1u16.to_le_bytes());
    expected.extend_from_slice(&0u32.to_le_bytes());
    expected.extend_from_slice(&7u64.to_le_bytes());
    expected.extend_from_slice(&0u64.to_le_bytes());
    let decoded =
        super::decode_native_executable_cache_limits_trigger_cadence(&bytes)
            .map_err(|error| error.to_string())?;
    if bytes == expected && decoded == cadence {
        Ok(())
    } else {
        Err(String::from("exhausted cadence canonical bytes drifted"))
    }
}

#[test]
fn malformed_framing_fails_closed() -> Result<(), String> {
    let cadence = TriggerCadence::new(nonzero(5)?, nonzero(3)?);
    let canonical =
        super::encode_native_executable_cache_limits_trigger_cadence(cadence);
    let short = canonical
        .get(..canonical.len().saturating_sub(1))
        .ok_or_else(|| String::from("test short frame unavailable"))?;
    if super::decode_native_executable_cache_limits_trigger_cadence(short)
        != Err(CodecError::Length {
            expected: 32,
            observed: 31,
        })
    {
        return Err(String::from("cadence frame length was accepted"));
    }
    let mut magic = canonical.clone();
    replace(&mut magic, 0, b"XBCTC001")?;
    if super::decode_native_executable_cache_limits_trigger_cadence(&magic)
        != Err(CodecError::Magic)
    {
        return Err(String::from("cadence frame magic was accepted"));
    }
    let mut version = canonical.clone();
    replace(&mut version, 8, &2u16.to_le_bytes())?;
    if super::decode_native_executable_cache_limits_trigger_cadence(&version)
        != Err(CodecError::Version { observed: 2 })
    {
        return Err(String::from("cadence frame version was accepted"));
    }
    let mut flags = canonical.clone();
    replace(&mut flags, 10, &2u16.to_le_bytes())?;
    if super::decode_native_executable_cache_limits_trigger_cadence(&flags)
        != Err(CodecError::Flags { observed: 2 })
    {
        return Err(String::from("cadence frame flags were accepted"));
    }
    let mut reserved = canonical;
    replace(&mut reserved, 12, &1u32.to_le_bytes())?;
    if super::decode_native_executable_cache_limits_trigger_cadence(&reserved)
        != Err(CodecError::Reserved { observed: 1 })
    {
        return Err(String::from("cadence reserved bytes were accepted"));
    }
    Ok(())
}

#[test]
fn semantic_state_drift_fails_closed() -> Result<(), String> {
    let cadence = TriggerCadence::new(nonzero(5)?, nonzero(3)?);
    let canonical =
        super::encode_native_executable_cache_limits_trigger_cadence(cadence);
    let mut interval_zero = canonical.clone();
    replace(&mut interval_zero, 16, &0u64.to_le_bytes())?;
    if super::decode_native_executable_cache_limits_trigger_cadence(
        &interval_zero,
    ) != Err(CodecError::IntervalZero)
    {
        return Err(String::from("zero cadence interval was accepted"));
    }
    let mut due_zero = canonical.clone();
    replace(&mut due_zero, 24, &0u64.to_le_bytes())?;
    if super::decode_native_executable_cache_limits_trigger_cadence(&due_zero)
        != Err(CodecError::NextDueZero)
    {
        return Err(String::from("zero active due sequence was accepted"));
    }
    let mut exhausted_value = canonical;
    replace(&mut exhausted_value, 10, &1u16.to_le_bytes())?;
    if super::decode_native_executable_cache_limits_trigger_cadence(
        &exhausted_value,
    ) != Err(CodecError::ExhaustedValue { value: 5 })
    {
        return Err(String::from("exhausted cadence due value was accepted"));
    }
    Ok(())
}
