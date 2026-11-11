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
//   - Root-tree regression coverage for executable cache-limit codec.
// - Must-Not:
//   - Define production semantics or replace the parent module's authority.
// - Allows:
//   - Inputs: the parent module's test-visible implementation surface.
//   - Outputs: deterministic regression evidence.
//   - Side effects: test-only in-memory or filesystem fixture effects.
// - Split-When:
//   - The regression surface requires an independent integration lifecycle.
// - Merge-When:
//   - The parent boundary no longer requires private regression access.
// - Summary:
//   - Proves executable cache-limit codec behavior from the root test tree.
// - Description:
//   - Loaded as a test-only child module to retain private-item access.
// - Usage:
//   - Selected by the parent module only when Rust test configuration is set.
// - Defaults:
//   - Production builds never compile this regression module.
//

//! Root-tree regression coverage for executable cache-limit codec.

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
    let bytes = super::encode_native_executable_sequence_cache_limits(limits)
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
    let bytes = super::encode_native_executable_sequence_cache_limits(limits)
        .map_err(|error| error.to_string())?;
    let flags = bytes
        .get(10..12)
        .ok_or_else(|| String::from("cache-limit flags missing"))?;
    let option_payload = bytes
        .get(24..40)
        .ok_or_else(|| String::from("cache-limit option payload missing"))?;
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
