// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Version-one capsule framing, fallback visibility, and runtime-boundary
//   - tests.
// - Must-Not:
//   - Claim scalable execution support or mutate the historical interpreter.
// - Allows:
//   - Inputs: public capsule/runtime APIs and checked-in compatibility fixture.
//   - Outputs: deterministic recognition, corruption, and fallback assertions.
//   - Side effects: test-process memory only.
// - Split-When:
//   - Split when another capsule version needs independent compatibility
//   - evidence.
// - Merge-When:
//   - Merge when capsule framing becomes ordinary profile-loading evidence.
// - Summary:
//   - Proves modern capsule recognition while historical tools see only the
//   - sentinel.
// - Description:
//   - Locks framing bytes, checksum failure, profile preflight, and fallback
//   - halt.
// - Usage:
//   - Composed by `tests/vm.rs` under the normal Cargo integration test target.
// - Defaults:
//   - Current-profile payloads parse but remain non-executable on classic
//   - runtime.
//

//! Historical-fallback capsule compatibility and runtime-boundary fixtures.

use std::ops::Range;
use std::str::from_utf8;

#[cfg(feature = "legacy-ben")]
use malbolge::ProfileMachine;
use malbolge::{
    CapsuleError, ExecutionErrorKind, ExecutionMachine, ExecutionMode,
    RunOutcome, Termination, build_capsule, current_profile, parse_capsule,
};

use super::{TestResult, check_equal, normalize_result};

const BITS_PER_BYTE: usize = 8;
const CHECKSUM_BYTES: usize = 8;
const CURRENT_CAPSULE_HEX: &str =
    include_str!("../compatibility/capsule/current-profile-capsule.hex");
const FALLBACK: &[u8] = b"(C<;_\"K";
const FNV1A64_OFFSET: u64 = 0xcbf2_9ce4_8422_2325;
const FNV1A64_PRIME: u64 = 0x0000_0100_0000_01b3;
const FRAME_HEADER_BYTES: usize = 18;
const PAYLOAD: &[u8] = b"ctO\n";
const SPACE: u8 = b' ';
const TAB: u8 = b'\t';
const UNKNOWN_PROFILE: &[u8] = b"malbolge-2026.x";

type IdentityRanges = (Range<usize>, Range<usize>);

fn capsule_fixture() -> TestResult<Vec<u8>> {
    let digits: Vec<u8> = CURRENT_CAPSULE_HEX
        .bytes()
        .filter(|byte| !byte.is_ascii_whitespace())
        .collect();
    let (pairs, remainder) = digits.as_chunks::<2>();
    if !remainder.is_empty() {
        return Err(String::from("capsule hex fixture has an odd digit count"));
    }
    let mut decoded = Vec::new();
    for pair in pairs {
        let text = from_utf8(pair)
            .map_err(|error| format!("capsule hex is not ASCII: {error}"))?;
        let byte = u8::from_str_radix(text, 16)
            .map_err(|error| format!("capsule hex byte is invalid: {error}"))?;
        decoded.push(byte);
    }
    Ok(decoded)
}

fn decoded_frame(source: &[u8]) -> TestResult<Vec<u8>> {
    let sideband = source
        .strip_prefix(FALLBACK)
        .ok_or_else(|| String::from("capsule fixture lacks fallback prefix"))?;
    let (chunks, remainder) = sideband.as_chunks::<BITS_PER_BYTE>();
    if !remainder.is_empty() {
        return Err(String::from("capsule sideband is not byte aligned"));
    }
    let mut frame = Vec::new();
    for chunk in chunks {
        let mut value = 0u8;
        for symbol in chunk.iter().copied() {
            value = value
                .checked_mul(2)
                .ok_or_else(|| String::from("capsule test decode overflow"))?;
            match symbol {
                SPACE => {},
                TAB => value = value.saturating_add(1),
                _ => {
                    return Err(String::from(
                        "capsule sideband symbol is invalid",
                    ));
                },
            }
        }
        frame.push(value);
    }
    Ok(frame)
}

fn encoded_capsule(frame: &[u8]) -> Vec<u8> {
    let mut source = Vec::from(FALLBACK);
    for byte in frame.iter().copied() {
        for shift in (0..BITS_PER_BYTE).rev() {
            source.push(if byte & (1u8 << shift) == 0 {
                SPACE
            } else {
                TAB
            });
        }
    }
    source
}

fn frame_identity_ranges(frame: &[u8]) -> TestResult<IdentityRanges> {
    let profile_len = frame_u16(frame, 10)?;
    let fingerprint_len = frame_u16(frame, 12)?;
    let profile_end = FRAME_HEADER_BYTES
        .checked_add(profile_len)
        .ok_or_else(|| String::from("capsule profile range overflow"))?;
    let fingerprint_end = profile_end
        .checked_add(fingerprint_len)
        .ok_or_else(|| String::from("capsule fingerprint range overflow"))?;
    if frame.get(FRAME_HEADER_BYTES..fingerprint_end).is_none() {
        return Err(String::from("capsule identity range is truncated"));
    }
    Ok((
        FRAME_HEADER_BYTES..profile_end,
        profile_end..fingerprint_end,
    ))
}

fn frame_u16(frame: &[u8], start: usize) -> TestResult<usize> {
    let end = start
        .checked_add(2)
        .ok_or_else(|| String::from("capsule field range overflow"))?;
    let bytes: [u8; 2] = frame
        .get(start..end)
        .ok_or_else(|| String::from("capsule field is truncated"))?
        .try_into()
        .map_err(|error| format!("capsule field width is invalid: {error}"))?;
    Ok(usize::from(u16::from_be_bytes(bytes)))
}

fn refresh_checksum(frame: &mut [u8]) -> TestResult {
    let checksum_start = frame
        .len()
        .checked_sub(CHECKSUM_BYTES)
        .ok_or_else(|| String::from("capsule frame lacks checksum"))?;
    let checksum =
        fnv1a64(frame.get(..checksum_start).ok_or_else(|| {
            String::from("capsule checksum input is invalid")
        })?);
    let target = frame
        .get_mut(checksum_start..)
        .ok_or_else(|| String::from("capsule checksum field is invalid"))?;
    target.copy_from_slice(&checksum.to_be_bytes());
    Ok(())
}

fn fnv1a64(bytes: &[u8]) -> u64 {
    let mut hash = FNV1A64_OFFSET;
    for byte in bytes.iter().copied() {
        hash ^= u64::from(byte);
        hash = hash.wrapping_mul(FNV1A64_PRIME);
    }
    hash
}

#[test]
fn builder_matches_checked_in_fixture() -> TestResult {
    let built = normalize_result(build_capsule(current_profile(), PAYLOAD))?;
    let fixture = capsule_fixture()?;
    check_equal(
        built.as_slice(),
        fixture.as_slice(),
        "version-one capsule fixture",
    )
}

#[test]
fn classic_facade_rejects_current_capsule_before_loader() -> TestResult {
    let parsed = normalize_result(parse_capsule(&capsule_fixture()?))?
        .ok_or_else(|| String::from("current fixture was not recognized"))?;
    let Err(error) = ExecutionMachine::from_source_for_profile(
        parsed.payload(),
        Vec::new(),
        ExecutionMode::Specification,
        parsed.profile(),
    ) else {
        return Err(String::from("unsupported current capsule executed"));
    };
    check_equal(
        &matches!(error.kind(), ExecutionErrorKind::Profile(_)),
        &true,
        "capsule profile rejection precedes payload loading",
    )
}

#[cfg(feature = "legacy-ben")]
#[test]
fn current_capsule_executes_on_profiled_runtime() -> TestResult {
    let fixture = capsule_fixture()?;
    let parsed = normalize_result(parse_capsule(&fixture))?
        .ok_or_else(|| String::from("current fixture was not recognized"))?;
    let mut machine = normalize_result(ProfileMachine::from_source(
        parsed.profile(),
        parsed.payload(),
        vec![0x41],
    ))?;
    let outcome = normalize_result(machine.run(8))?;
    check_equal(
        &outcome,
        &RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 3,
        },
        "profiled capsule halt",
    )?;
    check_equal(machine.output(), b"A".as_slice(), "profiled capsule output")
}

#[test]
fn fallback_emits_bang_and_halts_in_legacy_mode() -> TestResult {
    let mut machine = normalize_result(ExecutionMachine::from_source(
        b"(C<;_\"K",
        Vec::new(),
        ExecutionMode::LegacyBen,
    ))?;
    let outcome = normalize_result(machine.run(7))?;
    check_equal(
        &outcome,
        &RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 7,
        },
        "historical fallback halt",
    )?;
    check_equal(
        &machine.input_consumed(),
        &0usize,
        "historical fallback input",
    )?;
    check_equal(
        machine.output(),
        b"!".as_slice(),
        "historical fallback output",
    )
}

#[test]
fn historical_visible_surface_is_exact_fallback() -> TestResult {
    let fixture = capsule_fixture()?;
    let visible: Vec<u8> = fixture
        .iter()
        .copied()
        .filter(|byte| !matches!(*byte, b' ' | b'\t'))
        .collect();
    check_equal(visible.as_slice(), b"(C<;_\"K", "historical visible source")
}

#[test]
fn ordinary_classic_source_is_not_capsule() -> TestResult {
    check_equal(
        &normalize_result(parse_capsule(b"ctO\n"))?.is_none(),
        &true,
        "ordinary source recognition",
    )
}

#[test]
fn parsed_fixture_binds_current_profile_and_payload() -> TestResult {
    let parsed = normalize_result(parse_capsule(&capsule_fixture()?))?
        .ok_or_else(|| String::from("current fixture was not recognized"))?;
    check_equal(
        &parsed.profile().id(),
        &"malbolge-2026.2",
        "capsule profile",
    )?;
    check_equal(parsed.payload(), PAYLOAD, "capsule payload")
}

#[test]
fn tampered_payload_fails_checksum() -> TestResult {
    let mut tampered = capsule_fixture()?;
    let payload_symbol = tampered.len().saturating_sub(65);
    let symbol = tampered.get_mut(payload_symbol).ok_or_else(|| {
        String::from("fixture lacks payload checksum boundary")
    })?;
    *symbol = if *symbol == b' ' {
        b'\t'
    } else {
        b' '
    };
    let Err(error) = parse_capsule(&tampered) else {
        return Err(String::from("tampered capsule was accepted"));
    };
    check_equal(
        &matches!(error, CapsuleError::ChecksumMismatch { .. }),
        &true,
        "tampered payload checksum category",
    )
}

#[test]
fn trailing_whitespace_on_fallback_is_not_capsule() -> TestResult {
    check_equal(
        &normalize_result(parse_capsule(b"(C<;_\"K \t \t"))?.is_none(),
        &true,
        "ordinary trailing whitespace recognition",
    )
}

#[test]
fn fingerprint_mismatch_uses_shared_identity_diagnostic() -> TestResult {
    let mut frame = decoded_frame(&capsule_fixture()?)?;
    let (_, fingerprint_range) = frame_identity_ranges(&frame)?;
    let first = frame
        .get_mut(fingerprint_range.start)
        .ok_or_else(|| String::from("capsule fingerprint is empty"))?;
    *first = if *first == b'x' {
        b'y'
    } else {
        b'x'
    };
    let declared =
        from_utf8(frame.get(fingerprint_range).ok_or_else(|| {
            String::from("capsule fingerprint is unavailable")
        })?)
        .map_err(|error| format!("capsule fingerprint is not UTF-8: {error}"))?
        .to_owned();
    refresh_checksum(&mut frame)?;

    let Err(error) = parse_capsule(&encoded_capsule(&frame)) else {
        return Err(String::from(
            "mismatched capsule fingerprint was accepted",
        ));
    };
    let canonical_profile_id = current_profile().id();
    let canonical_fingerprint = current_profile().fingerprint();
    let expected_message = format!(
        concat!(
            "MALBOLGE-PROFILE-ID-001 profile={profile_id} ",
            "expected={declared} observed={observed}"
        ),
        profile_id = canonical_profile_id,
        declared = declared,
        observed = canonical_fingerprint,
    );
    check_equal(
        &format!("{error}"),
        &expected_message,
        "shared capsule profile identity diagnostic",
    )?;
    let CapsuleError::ProfileFingerprintMismatch {
        profile_id,
        expected,
        observed,
    } = error
    else {
        return Err(String::from("unexpected capsule mismatch error category"));
    };
    check_equal(&profile_id, &current_profile().id(), "mismatch profile")?;
    check_equal(expected.as_ref(), declared.as_str(), "declared fingerprint")?;
    check_equal(
        &observed,
        &current_profile().fingerprint(),
        "canonical fingerprint",
    )
}

#[test]
fn unknown_profile_remains_explicit_without_fallback() -> TestResult {
    let mut frame = decoded_frame(&capsule_fixture()?)?;
    let (profile_range, _) = frame_identity_ranges(&frame)?;
    let target = frame.get_mut(profile_range).ok_or_else(|| {
        String::from("capsule profile identity is unavailable")
    })?;
    if target.len() != UNKNOWN_PROFILE.len() {
        return Err(String::from("unknown profile fixture width changed"));
    }
    target.copy_from_slice(UNKNOWN_PROFILE);
    refresh_checksum(&mut frame)?;

    let Err(error) = parse_capsule(&encoded_capsule(&frame)) else {
        return Err(String::from("unknown capsule profile was accepted"));
    };
    check_equal(
        &format!("{error}"),
        &String::from("MALBOLGE-CAPSULE-004 unknown profile=malbolge-2026.x"),
        "unknown capsule profile diagnostic",
    )?;
    let CapsuleError::UnknownProfile { profile_id } = error else {
        return Err(String::from("unexpected unknown-profile error category"));
    };
    check_equal(
        profile_id.as_ref(),
        "malbolge-2026.x",
        "unknown capsule profile identity",
    )
}
