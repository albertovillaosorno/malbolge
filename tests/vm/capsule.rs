// File:
//   - capsule.rs
// Path:
//   - tests/vm/capsule.rs
//
// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE
// Path-Rule:
//   - All paths in this header are repository-root relative.
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
// Related documents:
// - docs/technical/compatibility/historical-interpreter-fallback-capsule.md
// - tests/compatibility/capsule/current-profile-capsule.hex
//
// Large file:
//   - false
//

//! Historical-fallback capsule compatibility and runtime-boundary fixtures.

use std::str::from_utf8;

#[cfg(feature = "legacy-ben")]
use malbolge::ProfileMachine;
use malbolge::{
    CapsuleError, ExecutionErrorKind, ExecutionMachine, ExecutionMode,
    RunOutcome, Termination, build_capsule, current_profile, parse_capsule,
};

use super::{TestResult, check_equal, normalize_result};

const CURRENT_CAPSULE_HEX: &str =
    include_str!("../compatibility/capsule/current-profile-capsule.hex");
const PAYLOAD: &[u8] = b"ctO\n";

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
