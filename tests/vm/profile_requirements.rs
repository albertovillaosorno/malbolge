// File:
//   - profile_requirements.rs
// Path:
//   - tests/vm/profile_requirements.rs
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
//   - Runtime evidence for canonical profile and capacity preflight
//   - diagnostics.
// - Must-Not:
//   - Execute unsupported scalable profiles or treat profile fallback as valid.
// - Allows:
//   - Inputs: public canonical descriptors and safe Rust runtime capability.
//   - Outputs: exact acceptance/rejection and stable diagnostic assertions.
//   - Side effects: test-process memory only.
// - Split-When:
//   - Split when another runtime capability needs an independent fixture set.
// - Merge-When:
//   - Merge when profile requirements become ordinary execution-mode evidence.
// - Summary:
//   - Verifies fail-closed target-profile runtime preflight and diagnostics.
// - Description:
//   - Covers current, transition, historical ceiling, and no-fallback lookup.
// - Usage:
//   - Composed by `tests/vm.rs` under the normal Cargo integration test target.
// - Defaults:
//   - The safe Rust runtime advertises only the classic ten-trit capacity.
//
// Related documents:
// - malbolge.json
// - docs/technical/compatibility/required-profile-diagnostics.md
//
// Large file:
//   - false
//

//! Runtime target-profile capability and deterministic diagnostic fixtures.

use malbolge::{
    ExecutionErrorKind, ExecutionMachine, ExecutionMode, ProfileKind,
    ProfileRequirementErrorKind, current_profile, historical_profile,
    preflight_profile, safe_rust_classic_capability, target_profile,
};

use super::{TestResult, check_equal, normalize_result};

const CURRENT_FINGERPRINT: &str = concat!(
    "malbolge-profile-v1:sha256:",
    "e33e1488162dffdc8bad9102df8eed3f8aac294d057b4f7ad7a389906963fc50",
);
const CURRENT_ID: &str = "malbolge-2026.2";
const HISTORICAL_ID: &str = "malbolge-1998";
const HISTORICAL_WORDS: u32 = 59_049;
const IO_ROUNDTRIP: &[u8] =
    include_bytes!("../compatibility/specification/spec-io-roundtrip.malbolge");
const TRANSITION_ID: &str = "malbolge-2026.1";

#[test]
fn canonical_projection_exposes_current_geometry() -> TestResult {
    let current = current_profile();
    check_equal(
        &current.fingerprint(),
        &CURRENT_FINGERPRINT,
        "current profile fingerprint",
    )?;
    check_equal(&current.id(), &CURRENT_ID, "current profile id")?;
    check_equal(&current.version(), &"2026.2", "current version")?;
    check_equal(&current.kind(), &ProfileKind::Current, "current kind")?;
    check_equal(&current.word_trits(), &14u8, "current trit width")?;
    check_equal(
        &current.word_modulus(),
        &4_782_969u32,
        "current word modulus",
    )?;
    check_equal(
        &current.memory_words(),
        &4_782_969u32,
        "current memory capacity",
    )?;
    check_equal(&current.eof_word(), &4_782_968u32, "current EOF")
}

#[test]
fn current_profile_is_rejected_before_loader() -> TestResult {
    let current = current_profile();
    let Err(error) = ExecutionMachine::from_source_for_profile(
        b"",
        Vec::new(),
        ExecutionMode::Specification,
        current,
    ) else {
        return Err(String::from("unsupported current profile was executed"));
    };
    let ExecutionErrorKind::Profile(requirement) = error.kind() else {
        return Err(format!("profile preflight lost precedence: {error}"));
    };
    check_equal(
        &requirement.kind(),
        &ProfileRequirementErrorKind::RuntimeCapabilityMissing,
        "current profile requires unavailable runtime capacity",
    )?;
    check_equal(
        &requirement.code(),
        &"MALBOLGE-PROFILE-001",
        "runtime capability diagnostic code",
    )?;
    check_equal(
        &format!("{requirement}"),
        &String::from(concat!(
            "MALBOLGE-PROFILE-001 profile=malbolge-2026.2 version=2026.2 ",
            "required_features=byte-input,byte-output,crazy-operation,",
            "deterministic,post-instruction-encryption,rotate,",
            "self-modification,sequential-guest required_word_trits=14 ",
            "required_memory_words=4782969 runtime=safe-rust-classic ",
            "max_word_trits=10 max_memory_words=59049 ",
            "missing=word-trits,memory-words"
        )),
        "exact current-profile diagnostic",
    )
}

#[test]
fn default_execution_constructor_remains_historical() -> TestResult {
    let machine = normalize_result(ExecutionMachine::from_source(
        IO_ROUNDTRIP,
        vec![0x41],
        ExecutionMode::Specification,
    ))?;
    check_equal(
        &machine.profile().id(),
        &HISTORICAL_ID,
        "classic constructor keeps historical identity",
    )
}

#[test]
fn historical_capacity_excess_names_historical_ceiling() -> TestResult {
    let historical = historical_profile();
    let required_memory_words = HISTORICAL_WORDS.saturating_add(1);
    let Err(error) = preflight_profile(
        historical,
        required_memory_words,
        safe_rust_classic_capability(),
    ) else {
        return Err(String::from("historical capacity overflow was accepted"));
    };
    check_equal(
        &error.kind(),
        &ProfileRequirementErrorKind::ProfileCapacityExceeded,
        "historical ceiling category",
    )?;
    check_equal(
        &error.code(),
        &"MALBOLGE-PROFILE-002",
        "historical capacity diagnostic code",
    )?;
    check_equal(
        &format!("{error}"),
        &String::from(concat!(
            "MALBOLGE-PROFILE-002 profile=malbolge-1998 version=1998 ",
            "constraint=historical-profile-ceiling ",
            "required_memory_words=59050 ",
            "profile_memory_words=59049"
        )),
        "historical profile ceiling diagnostic",
    )
}

#[test]
fn transition_profile_runs_on_equivalent_classic_capacity() -> TestResult {
    let transition = target_profile(TRANSITION_ID)
        .ok_or_else(|| String::from("missing transition profile projection"))?;
    normalize_result(preflight_profile(
        transition,
        transition.memory_words(),
        safe_rust_classic_capability(),
    ))?;
    let machine = normalize_result(ExecutionMachine::from_source_for_profile(
        IO_ROUNDTRIP,
        vec![0x41],
        ExecutionMode::Specification,
        transition,
    ))?;
    check_equal(
        &machine.profile().id(),
        &TRANSITION_ID,
        "accepted machine retains exact transition identity",
    )
}

#[test]
fn unknown_profile_lookup_never_falls_back() -> TestResult {
    check_equal(
        &target_profile("malbolge-current-ish").is_none(),
        &true,
        "unknown profile identity is rejected",
    )
}
