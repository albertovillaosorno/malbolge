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

//! Runtime target-profile capability and deterministic diagnostic fixtures.

use std::iter::repeat_n;

use malbolge::{
    ExecutionErrorKind, ExecutionMachine, ExecutionMode, ProfileKind,
    ProfileMachine, ProfileMachineError, ProfileRequirementErrorKind,
    RuntimeProfileRequirementError, TargetProfileRequirement, current_profile,
    historical_profile, preflight_portable_profile_requirement,
    preflight_profile, preflight_runtime_requirement,
    safe_rust_classic_capability, safe_rust_profiled_capability,
    target_profile,
};

use super::{TestResult, check_equal, normalize_result};

const CURRENT_FINGERPRINT: &str = concat!(
    "malbolge-profile-v1:sha256:",
    "1006b5fc06808f54aa5089cef0237539770c1d79a73c822e6e26e0e0ebfb0c76",
);
const CURRENT_ID: &str = "malbolge-2026";
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
    check_equal(&current.version(), &"2026", "current version")?;
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
    check_equal(&current.eof_word(), &4_782_968u32, "current EOF")?;
    check_equal(&current.input_instruction(), &b'/', "current input opcode")?;
    check_equal(
        &current.output_instruction(),
        &b'<',
        "current output opcode",
    )
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
            "MALBOLGE-PROFILE-001 profile=malbolge-2026 version=2026 ",
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
fn source_capacity_preflight_precedes_loader_errors() -> TestResult {
    let historical = historical_profile();
    let source = vec![b'!'; 59_050];

    let Err(classic_error) = ExecutionMachine::from_source_for_profile(
        &source,
        Vec::new(),
        ExecutionMode::Interpreter,
        historical,
    ) else {
        return Err(String::from("oversized classic source was accepted"));
    };
    let ExecutionErrorKind::Profile(classic_requirement) = classic_error.kind()
    else {
        return Err(format!(
            "classic source capacity lost profile precedence: {classic_error}"
        ));
    };
    check_equal(
        &classic_requirement.kind(),
        &ProfileRequirementErrorKind::ProfileCapacityExceeded,
        "classic source capacity category",
    )?;
    check_equal(
        &classic_requirement.required_memory_words(),
        &59_050,
        "classic source required memory",
    )?;

    let Err(profile_error) =
        ProfileMachine::from_source(historical, &source, Vec::new())
    else {
        return Err(String::from("oversized profiled source was accepted"));
    };
    let ProfileMachineError::Profile(profile_requirement) = profile_error
    else {
        return Err(format!(
            "profiled source capacity lost profile precedence: {profile_error}"
        ));
    };
    check_equal(
        &profile_requirement.kind(),
        &ProfileRequirementErrorKind::ProfileCapacityExceeded,
        "profiled source capacity category",
    )?;
    check_equal(
        &profile_requirement.required_memory_words(),
        &59_050,
        "profiled source required memory",
    )?;

    whitespace_padded_boundary_reaches_loader()
}

fn whitespace_padded_boundary_reaches_loader() -> TestResult {
    let mut whitespace_padded = vec![b' '; 128];
    whitespace_padded.extend(repeat_n(b'!', 59_049));
    let Err(loader_error) = ExecutionMachine::from_source_for_profile(
        &whitespace_padded,
        Vec::new(),
        ExecutionMode::Interpreter,
        historical_profile(),
    ) else {
        return Err(String::from("invalid boundary source was accepted"));
    };
    if matches!(loader_error.kind(), ExecutionErrorKind::Load(_)) {
        Ok(())
    } else {
        Err(format!(
            "canonical whitespace consumed profile capacity: {loader_error}"
        ))
    }
}

#[test]
fn portable_requirement_canonical_admission_is_exact() -> TestResult {
    let current = current_profile();
    let canonical = TargetProfileRequirement::from_descriptor(current);
    check_equal(
        &canonical.is_canonical_for(current.id()),
        &true,
        "canonical portable envelope",
    )?;
    check_equal(
        &canonical.is_canonical_for("malbolge-2026-alias"),
        &false,
        "unknown profile identity",
    )?;

    let mut feature_drift = canonical.clone();
    let _removed = feature_drift.features.pop();
    let mut memory_drift = canonical.clone();
    memory_drift.memory_words = memory_drift.memory_words.saturating_sub(1);
    let mut version_drift = canonical.clone();
    version_drift.version.push_str("-drift");
    let mut width_drift = canonical;
    width_drift.word_trits = width_drift.word_trits.saturating_sub(1);

    for (label, requirement) in [
        ("feature drift", feature_drift),
        ("memory drift", memory_drift),
        ("version drift", version_drift),
        ("word-width drift", width_drift),
    ] {
        check_equal(
            &requirement.is_canonical_for(current.id()),
            &false,
            label,
        )?;
    }
    Ok(())
}

#[test]
fn portable_requirement_matches_canonical_runtime_diagnostic() -> TestResult {
    let current = current_profile();
    let requirement = TargetProfileRequirement::from_descriptor(current);
    let Err(canonical) = preflight_profile(
        current,
        u64::from(current.memory_words()),
        safe_rust_classic_capability(),
    ) else {
        return Err(String::from("canonical current requirement was accepted"));
    };
    let Err(portable) = preflight_runtime_requirement(
        current.id(),
        &requirement,
        safe_rust_classic_capability(),
    ) else {
        return Err(String::from("portable current requirement was accepted"));
    };
    check_equal(
        &RuntimeProfileRequirementError::CODE,
        &canonical.code(),
        "portable diagnostic code",
    )?;
    check_equal(
        &portable.profile_id(),
        &current.id(),
        "portable profile identity",
    )?;
    check_equal(
        portable.requirement(),
        &requirement,
        "portable requirement access",
    )?;
    check_equal(
        &format!("{portable}"),
        &format!("{canonical}"),
        "portable/canonical diagnostic parity",
    )?;
    preflight_runtime_requirement(
        current.id(),
        &requirement,
        safe_rust_profiled_capability(),
    )
    .map_err(|error| format!("profiled runtime rejected envelope: {error}"))
}

#[test]
fn portable_requirement_rejects_unknown_feature_fail_closed() -> TestResult {
    let current = current_profile();
    let mut requirement = TargetProfileRequirement::from_descriptor(current);
    requirement
        .features
        .push(String::from("unknown-capability"));
    let Err(error) = preflight_runtime_requirement(
        current.id(),
        &requirement,
        safe_rust_profiled_capability(),
    ) else {
        return Err(String::from("unknown portable feature was accepted"));
    };
    let diagnostic = format!("{error}");
    if diagnostic.ends_with("missing=unknown-capability") {
        Ok(())
    } else {
        Err(format!("unknown feature diagnostic mismatch: {diagnostic}"))
    }
}

#[test]
fn portable_capacity_matches_historical_diagnostic() -> TestResult {
    let historical = historical_profile();
    let requirement = TargetProfileRequirement::from_descriptor(historical);
    let required_memory_words = u64::from(HISTORICAL_WORDS).saturating_add(1);
    let Err(canonical) = preflight_profile(
        historical,
        u64::from(HISTORICAL_WORDS.saturating_add(1)),
        safe_rust_classic_capability(),
    ) else {
        return Err(String::from("canonical historical overflow was accepted"));
    };
    let Err(portable) = preflight_portable_profile_requirement(
        historical.id(),
        &requirement,
        required_memory_words,
        safe_rust_classic_capability(),
    ) else {
        return Err(String::from("portable historical overflow was accepted"));
    };
    check_equal(
        &portable.kind(),
        &ProfileRequirementErrorKind::ProfileCapacityExceeded,
        "portable historical capacity kind",
    )?;
    check_equal(
        &portable.required_memory_words(),
        &required_memory_words,
        "portable requested memory",
    )?;
    check_equal(
        &format!("{portable}"),
        &format!("{canonical}"),
        "portable/canonical capacity diagnostic parity",
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
        u64::from(required_memory_words),
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
        u64::from(transition.memory_words()),
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
