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
//   - Portable region artifact verification, execution, and tamper fixtures.
// - Must-Not:
//   - Treat generated artifacts as trusted or encode architecture machine code.
// - Allows:
//   - Inputs: verifier-produced current regions and untrusted artifact claims.
//   - Outputs: exact admission, shortcut, deopt, and tamper evidence.
//   - Side effects: test-process allocation and normative fallback execution.
// - Split-When:
//   - Split when architecture code artifacts gain independent backend tests.
// - Merge-When:
//   - Merge when production `execution/ir/` owns equivalent artifact evidence.
// - Summary:
//   - Proves portable effects require independent admission before execution.
// - Description:
//   - Covers artifact tampering, reduced-guard reuse, and deterministic deopt.
// - Usage:
//   - Composed by `tests/state_graph_research.rs`.
// - Defaults:
//   - Only `VerifiedRegionArtifact` may apply compact effects.
//

//! Verification fixtures for portable region effect artifacts.

use malbolge::{
    ProfileMachine, ProfileMemoryDelta, ProfileMemoryWrite,
    RegionEffectProgram, current_profile,
};

use crate::indexed_state::IndexedMachineState;
use crate::region_artifact::{
    RegionArtifactVerificationError, UntrustedRegionArtifact,
};
use crate::region_certificate::{
    ExactRegionCertificate, RegionExecutionTier, VerifiedExactRegion,
};

const CURRENT_SOURCE: &[u8] = b"(=%`qL";
const REGION_BUDGET: usize = 8;

type VerifiedFixture =
    Result<(IndexedMachineState, VerifiedExactRegion), String>;

const fn changed_word(value: u32) -> u32 {
    let incremented = value.saturating_add(1);
    if incremented == current_profile().word_modulus() {
        0
    } else {
        incremented
    }
}

fn irrelevant_address(region: &VerifiedExactRegion) -> Result<u32, String> {
    for address in 1_024..1_280u32 {
        let dependency = region
            .memory_dependencies()
            .iter()
            .any(|entry| entry.address == address);
        let written = region.traces().iter().any(|trace| {
            [trace.memory_delta.data, trace.memory_delta.encryption]
                .into_iter()
                .flatten()
                .any(|write| write.address == address)
        });
        if !dependency && !written {
            return Ok(address);
        }
    }
    Err(String::from("artifact fixture has no irrelevant address"))
}

fn verified_fixture() -> VerifiedFixture {
    let machine =
        ProfileMachine::from_source(current_profile(), CURRENT_SOURCE, vec![
            0x41,
        ])
        .map_err(|error| format!("artifact load failed: {error}"))?;
    let entry = IndexedMachineState::from_checkpoint(&machine.snapshot_state())
        .map_err(|error| format!("artifact entry failed: {error:?}"))?;
    let region = ExactRegionCertificate::record(&entry, REGION_BUDGET)
        .and_then(|certificate| certificate.verify())
        .map_err(|error| format!("artifact region verify failed: {error:?}"))?;
    Ok((entry, region))
}

#[test]
fn artifact_deoptimizes_advanced_state_identically_to_region()
-> Result<(), String> {
    let (entry, region) = verified_fixture()?;
    let artifact = UntrustedRegionArtifact::from_verified_region(&region)
        .verify_against(&region)
        .map_err(|error| format!("artifact admission failed: {error:?}"))?;
    let first_trace = region
        .traces()
        .first()
        .ok_or_else(|| String::from("artifact region has no trace"))?;
    let candidate = entry
        .apply_trace(first_trace)
        .map_err(|error| format!("artifact advance failed: {error:?}"))?;
    let artifact_result = artifact
        .execute_or_deopt(&candidate)
        .map_err(|error| format!("artifact deopt failed: {error:?}"))?;
    let region_result = region
        .execute_or_deopt(&candidate)
        .map_err(|error| format!("region deopt failed: {error:?}"))?;
    if artifact_result.tier() != RegionExecutionTier::InterpreterFallback {
        return Err(String::from("artifact guard miss did not deoptimize"));
    }
    if artifact_result.outcome() != region_result.outcome()
        || !artifact_result
            .state()
            .exact_state_eq(region_result.state())
    {
        return Err(String::from(
            "artifact deopt differs from region baseline",
        ));
    }
    Ok(())
}

#[test]
fn artifact_shortcut_matches_verified_region_on_reduced_guard()
-> Result<(), String> {
    let (entry, region) = verified_fixture()?;
    let artifact = UntrustedRegionArtifact::from_verified_region(&region)
        .verify_against(&region)
        .map_err(|error| format!("artifact admission failed: {error:?}"))?;
    let address = irrelevant_address(&region)?;
    let before = entry.memory_word(address).map_err(|error| {
        format!("artifact irrelevant read failed: {error:?}")
    })?;
    let candidate = entry
        .apply_memory_delta(ProfileMemoryDelta {
            data: Some(ProfileMemoryWrite {
                address,
                after: changed_word(before),
                before,
            }),
            encryption: None,
        })
        .map_err(|error| format!("artifact variant failed: {error:?}"))?;
    let artifact_result = artifact
        .execute_or_deopt(&candidate)
        .map_err(|error| format!("artifact shortcut failed: {error:?}"))?;
    let expected = region
        .apply_dependency_shortcut(&candidate)
        .map_err(|error| format!("region shortcut failed: {error:?}"))?;
    if artifact_result.tier() != RegionExecutionTier::VerifiedShortcut {
        return Err(String::from(
            "artifact reduced guard did not use shortcut",
        ));
    }
    if artifact_result.outcome() != region.outcome()
        || !artifact_result.state().exact_state_eq(&expected)
    {
        return Err(String::from(
            "artifact shortcut differs from verified region",
        ));
    }
    Ok(())
}

#[test]
fn artifact_verifier_rejects_effect_tampering() -> Result<(), String> {
    let (_entry, region) = verified_fixture()?;
    let source = UntrustedRegionArtifact::from_verified_region(&region);
    let mut program = source.program().clone();
    let _removed = program.effects.pop();
    let tampered = UntrustedRegionArtifact::from_untrusted_parts(program);
    match tampered.verify_against(&region) {
        Err(RegionArtifactVerificationError::VerificationMismatch) => Ok(()),
        other => Err(format!("tampered effects artifact result: {other:?}")),
    }
}

#[test]
fn artifact_verifier_rejects_profile_identity_tampering() -> Result<(), String>
{
    let (_entry, region) = verified_fixture()?;
    let source = UntrustedRegionArtifact::from_verified_region(&region);
    let mut program = source.program().clone();
    program.profile_id = String::from("malbolge-2026.2-alias");
    check_rejected(program, &region, "profile identity")
}

#[test]
fn artifact_verifier_rejects_profile_tampering() -> Result<(), String> {
    let (_entry, region) = verified_fixture()?;
    let source = UntrustedRegionArtifact::from_verified_region(&region);
    let mut program = source.program().clone();
    program.profile_fingerprint =
        String::from("malbolge-profile-v1:sha256:tampered");
    check_rejected(program, &region, "profile fingerprint")
}

#[test]
fn artifact_verifier_rejects_metadata_tampering() -> Result<(), String> {
    let (_entry, region) = verified_fixture()?;
    let source = UntrustedRegionArtifact::from_verified_region(&region);
    let original = source.program();

    let mut profile_features = original.clone();
    let _removed_feature = profile_features.profile_requirement.features.pop();
    check_rejected(profile_features, &region, "profile features")?;

    let mut profile_memory = original.clone();
    profile_memory.profile_requirement.memory_words = profile_memory
        .profile_requirement
        .memory_words
        .saturating_add(1);
    check_rejected(profile_memory, &region, "profile memory")?;

    let mut profile_version = original.clone();
    profile_version.profile_requirement.version.push('x');
    check_rejected(profile_version, &region, "profile version")?;

    let mut profile_word_trits = original.clone();
    profile_word_trits.profile_requirement.word_trits = profile_word_trits
        .profile_requirement
        .word_trits
        .saturating_add(1);
    check_rejected(profile_word_trits, &region, "profile word trits")?;

    let mut version = original.clone();
    version.format_version = version.format_version.saturating_add(1);
    check_rejected(version, &region, "format version")?;

    let mut dependencies = original.clone();
    let _removed_dependency = dependencies.memory_live_ins.pop();
    check_rejected(dependencies, &region, "memory live-ins")?;

    let mut budget = original.clone();
    budget.step_budget = budget.step_budget.saturating_add(1);
    check_rejected(budget, &region, "step budget")?;

    let mut outcome = original.clone();
    outcome.outcome = malbolge::RunOutcome::BudgetExhausted { steps: 0 };
    check_rejected(outcome, &region, "outcome")
}

fn check_rejected(
    program: RegionEffectProgram,
    region: &VerifiedExactRegion,
    field: &str,
) -> Result<(), String> {
    let artifact = UntrustedRegionArtifact::from_untrusted_parts(program);
    match artifact.verify_against(region) {
        Err(RegionArtifactVerificationError::VerificationMismatch) => Ok(()),
        other => Err(format!("tampered {field} artifact result: {other:?}")),
    }
}
