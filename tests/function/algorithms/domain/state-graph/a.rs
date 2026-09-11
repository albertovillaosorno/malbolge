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
    EFFECT_IR_REGISTER_MASK_VERSION, IrEncodingError, ProfileMachine,
    ProfileMachineIoState, ProfileMachineState, ProfileMemoryDelta,
    ProfileMemoryWrite, ProfileRegisters, RegionEffectProgram,
    RegisterMaskedRegionEffectProgram, TraceInput, current_profile,
    verify_minimum_straight_line_io_profile_width,
};

use crate::indexed_state::IndexedMachineState;
use crate::region_artifact::{
    RegionArtifactVerificationError, UntrustedRegionArtifact,
    VerifiedRegionArtifact,
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

fn first_effect(
    program: &mut RegionEffectProgram,
) -> Result<&mut malbolge::EffectOp, String> {
    program
        .effects
        .first_mut()
        .ok_or_else(|| String::from("artifact fixture has no effects"))
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
fn artifact_shortcut_rebases_output_history() -> Result<(), String> {
    let geometry = verify_minimum_straight_line_io_profile_width(
        current_profile(),
        b"uCar_L",
    )
    .map_err(|error| format!("artifact output geometry failed: {error}"))?;
    let mut machine =
        ProfileMachine::from_verified_source(&geometry, vec![0xa5, 0x3c])
            .map_err(|error| format!("artifact output load failed: {error}"))?;
    let _prefix = machine
        .run(3)
        .map_err(|error| format!("artifact output setup failed: {error}"))?;
    let checkpoint = machine.snapshot_state();
    let entry = IndexedMachineState::from_checkpoint(&checkpoint)
        .map_err(|error| format!("artifact output entry failed: {error:?}"))?;
    let region = ExactRegionCertificate::record(&entry, 3)
        .and_then(|certificate| certificate.verify())
        .map_err(|error| format!("artifact output region failed: {error:?}"))?;
    let artifact = UntrustedRegionArtifact::from_verified_region(&region)
        .verify_against(&region)
        .map_err(|error| {
            format!("artifact output admission failed: {error:?}")
        })?;
    let io = ProfileMachineIoState::new(
        checkpoint.io().input().to_vec(),
        checkpoint.io().input_consumed(),
        vec![0x5a, 0x5b],
        checkpoint.io().termination(),
    )
    .map_err(|error| format!("artifact output IO failed: {error}"))?;
    let changed = ProfileMachineState::new_with_geometry(
        checkpoint.geometry(),
        checkpoint.memory().to_vec(),
        checkpoint.registers(),
        io,
    )
    .map_err(|error| format!("artifact output checkpoint failed: {error}"))?;
    let candidate =
        IndexedMachineState::from_checkpoint(&changed).map_err(|error| {
            format!("artifact output candidate failed: {error:?}")
        })?;
    let result = artifact.execute_or_deopt(&candidate).map_err(|error| {
        format!("artifact output execution failed: {error:?}")
    })?;
    let mut direct = ProfileMachine::from_snapshot(changed);
    let direct_outcome = direct
        .run(region.step_budget())
        .map_err(|error| format!("artifact output direct failed: {error}"))?;
    let actual = result.state().materialize_checkpoint().map_err(|error| {
        format!("artifact output materialize failed: {error:?}")
    })?;
    if result.tier() != RegionExecutionTier::VerifiedShortcut
        || result.outcome() != direct_outcome
        || actual != direct.snapshot_state()
        || actual.io().output() != [0x5a, 0x5b, 0x3c]
    {
        return Err(String::from(
            "artifact output rebasing differs from normative VM",
        ));
    }
    Ok(())
}

fn rebind_artifact_input_cursor(
    entry: &IndexedMachineState,
    input: Vec<u8>,
    input_cursor: usize,
) -> Result<IndexedMachineState, String> {
    let checkpoint = entry.materialize_checkpoint().map_err(|error| {
        format!("artifact cursor checkpoint failed: {error:?}")
    })?;
    let io = ProfileMachineIoState::new(
        input,
        input_cursor,
        checkpoint.io().output().to_vec(),
        checkpoint.io().termination(),
    )
    .map_err(|error| format!("artifact cursor IO failed: {error}"))?;
    let rebound = ProfileMachineState::new_with_geometry(
        checkpoint.geometry(),
        checkpoint.memory().to_vec(),
        checkpoint.registers(),
        io,
    )
    .map_err(|error| format!("artifact cursor state failed: {error}"))?;
    IndexedMachineState::from_checkpoint(&rebound)
        .map_err(|error| format!("artifact cursor index failed: {error:?}"))
}

fn validate_artifact_input_candidate(
    artifact: &VerifiedRegionArtifact,
    region: &VerifiedExactRegion,
    candidate: &IndexedMachineState,
    expected_tier: RegionExecutionTier,
) -> Result<(), String> {
    let result = artifact.execute_or_deopt(candidate).map_err(|error| {
        format!("artifact input execution failed: {error:?}")
    })?;
    let mut direct = ProfileMachine::from_snapshot(
        candidate.materialize_checkpoint().map_err(|error| {
            format!("artifact input checkpoint failed: {error:?}")
        })?,
    );
    let direct_outcome = direct
        .run(region.step_budget())
        .map_err(|error| format!("artifact input direct failed: {error}"))?;
    let actual = result
        .state()
        .materialize_checkpoint()
        .map_err(|error| format!("artifact input result failed: {error:?}"))?;
    if result.tier() != expected_tier
        || result.outcome() != direct_outcome
        || actual != direct.snapshot_state()
    {
        return Err(String::from("artifact input path diverged from VM"));
    }
    Ok(())
}

#[test]
fn artifact_v6_guards_only_bounded_input_observations() -> Result<(), String> {
    let geometry = verify_minimum_straight_line_io_profile_width(
        current_profile(),
        b"utO",
    )
    .map_err(|error| format!("artifact input geometry failed: {error}"))?;
    let machine =
        ProfileMachine::from_verified_source(&geometry, vec![0x11, 0x7a, 0x33])
            .map_err(|error| format!("artifact input load failed: {error}"))?;
    let entry = IndexedMachineState::from_checkpoint(&machine.snapshot_state())
        .map_err(|error| format!("artifact input entry failed: {error:?}"))?;
    let region = ExactRegionCertificate::record(&entry, 2)
        .and_then(|certificate| certificate.verify())
        .map_err(|error| format!("artifact input region failed: {error:?}"))?;
    let artifact = UntrustedRegionArtifact::from_verified_region(&region)
        .verify_against(&region)
        .map_err(|error| {
            format!("artifact input admission failed: {error:?}")
        })?;

    let changed_tail = entry
        .with_validated_input(vec![0x11, 0x7a, 0x44])
        .map_err(|error| format!("artifact input tail failed: {error:?}"))?;
    validate_artifact_input_candidate(
        &artifact,
        &region,
        &changed_tail,
        RegionExecutionTier::VerifiedShortcut,
    )?;

    let changed_observed =
        entry.with_validated_input(vec![0x11, 0x55, 0x44]).map_err(
            |error| format!("artifact observed input failed: {error:?}"),
        )?;
    validate_artifact_input_candidate(
        &artifact,
        &region,
        &changed_observed,
        RegionExecutionTier::InterpreterFallback,
    )
}

#[test]
fn artifact_v6_rebases_input_cursor_from_candidate() -> Result<(), String> {
    let geometry = verify_minimum_straight_line_io_profile_width(
        current_profile(),
        b"utO",
    )
    .map_err(|error| format!("artifact cursor geometry failed: {error}"))?;
    let machine =
        ProfileMachine::from_verified_source(&geometry, vec![0x11, 0x7a, 0x33])
            .map_err(|error| format!("artifact cursor load failed: {error}"))?;
    let entry = IndexedMachineState::from_checkpoint(&machine.snapshot_state())
        .map_err(|error| format!("artifact cursor entry failed: {error:?}"))?;
    let region = ExactRegionCertificate::record(&entry, 2)
        .and_then(|certificate| certificate.verify())
        .map_err(|error| format!("artifact cursor region failed: {error:?}"))?;
    let artifact = UntrustedRegionArtifact::from_verified_region(&region)
        .verify_against(&region)
        .map_err(|error| {
            format!("artifact cursor admission failed: {error:?}")
        })?;
    let candidate = rebind_artifact_input_cursor(
        &entry,
        vec![0xee, 0xdd, 0x11, 0x7a, 0x44],
        2,
    )?;
    validate_artifact_input_candidate(
        &artifact,
        &region,
        &candidate,
        RegionExecutionTier::VerifiedShortcut,
    )
}

fn check_v6_identity(source: &UntrustedRegionArtifact) -> Result<(), String> {
    let bytes = source
        .program()
        .canonical_bytes()
        .map_err(|error| format!("artifact v6 encoding failed: {error:?}"))?;
    if source.program().format_version() != EFFECT_IR_REGISTER_MASK_VERSION
        || bytes.get(..6) != Some(b"MBIR\x06\x00")
        || malbolge::is_canonical_effect_ir_version(
            EFFECT_IR_REGISTER_MASK_VERSION,
        )
    {
        return Err(String::from("artifact register-mask v6 identity drifted"));
    }
    Ok(())
}

fn check_v6_register_mask_tampering(
    source: &UntrustedRegionArtifact,
    region: &VerifiedExactRegion,
) -> Result<(), String> {
    let mut live_in_tamper = source.program().clone();
    live_in_tamper.register_live_ins.accumulator = true;
    check_rejected(live_in_tamper, region, "register live-ins")?;

    let mut write_tamper = source.program().clone();
    let writes = write_tamper.register_writes.first_mut().ok_or_else(|| {
        String::from("artifact v6 has no register-write mask")
    })?;
    writes.accumulator = false;
    check_rejected(write_tamper, region, "register writes")?;

    let mut count_tamper = source.program().clone();
    let _removed = count_tamper.register_writes.pop();
    if count_tamper.canonical_bytes()
        != Err(IrEncodingError::RegisterMaskCountMismatch)
    {
        return Err(String::from("artifact v6 encoded missing write mask"));
    }
    check_rejected(count_tamper, region, "register write count")
}

#[test]
fn artifact_v6_rebases_dead_register_and_rejects_mask_tampering()
-> Result<(), String> {
    let machine =
        ProfileMachine::from_source(current_profile(), b"uP", vec![0x41])
            .map_err(|error| {
                format!("artifact register load failed: {error}")
            })?;
    let checkpoint = machine.snapshot_state();
    let entry =
        IndexedMachineState::from_checkpoint(&checkpoint).map_err(|error| {
            format!("artifact register entry failed: {error:?}")
        })?;
    let region = ExactRegionCertificate::record(&entry, 1)
        .and_then(|certificate| certificate.verify())
        .map_err(|error| {
            format!("artifact register region failed: {error:?}")
        })?;
    let source = UntrustedRegionArtifact::from_verified_region(&region);
    check_v6_identity(&source)?;
    let artifact = source.verify_against(&region).map_err(|error| {
        format!("artifact register admission failed: {error:?}")
    })?;
    let registers = checkpoint.registers();
    let candidate = entry
        .with_validated_registers(ProfileRegisters {
            accumulator: changed_word(registers.accumulator),
            code_pointer: registers.code_pointer,
            data_pointer: registers.data_pointer,
        })
        .map_err(|error| {
            format!("artifact register candidate failed: {error:?}")
        })?;
    let result = artifact.execute_or_deopt(&candidate).map_err(|error| {
        format!("artifact register execution failed: {error:?}")
    })?;
    let mut direct = ProfileMachine::from_snapshot(
        candidate.materialize_checkpoint().map_err(|error| {
            format!("artifact register materialize: {error:?}")
        })?,
    );
    let direct_outcome = direct
        .run(1)
        .map_err(|error| format!("artifact register direct failed: {error}"))?;
    let actual = result.state().materialize_checkpoint().map_err(|error| {
        format!("artifact register result failed: {error:?}")
    })?;
    if result.tier() != RegionExecutionTier::VerifiedShortcut
        || result.outcome() != direct_outcome
        || actual != direct.snapshot_state()
    {
        return Err(String::from("artifact register rebase diverged from VM"));
    }

    check_v6_register_mask_tampering(&source, &region)
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
fn artifact_verifier_rejects_effect_field_tampering() -> Result<(), String> {
    let (_entry, region) = verified_fixture()?;
    let source = UntrustedRegionArtifact::from_verified_region(&region);
    let original = source.program();

    let mut before = original.clone();
    let before_effect = first_effect(&mut before)?;
    before_effect.before.registers.accumulator =
        changed_word(before_effect.before.registers.accumulator);
    check_rejected(before, &region, "effect before")?;

    let mut after = original.clone();
    let after_effect = first_effect(&mut after)?;
    after_effect.after.registers.accumulator =
        changed_word(after_effect.after.registers.accumulator);
    check_rejected(after, &region, "effect after")?;

    let mut input = original.clone();
    let input_effect = first_effect(&mut input)?;
    input_effect.input = match input_effect.input {
        Some(_) => None,
        None => Some(TraceInput::EndOfInput),
    };
    check_rejected(input, &region, "effect input")?;

    let mut output = original.clone();
    let output_effect = first_effect(&mut output)?;
    output_effect.output = match output_effect.output {
        Some(_) => None,
        None => Some(0),
    };
    check_rejected(output, &region, "effect output")?;

    let mut memory = original.clone();
    let memory_effect = first_effect(&mut memory)?;
    let write = ProfileMemoryWrite {
        address: 0,
        after: 1,
        before: 0,
    };
    memory_effect.memory_delta = match memory_effect.memory_delta.data {
        Some(_) => ProfileMemoryDelta {
            data: None,
            encryption: memory_effect.memory_delta.encryption,
        },
        None => ProfileMemoryDelta {
            data: Some(write),
            encryption: memory_effect.memory_delta.encryption,
        },
    };
    check_rejected(memory, &region, "effect memory delta")
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
    program: RegisterMaskedRegionEffectProgram,
    region: &VerifiedExactRegion,
    field: &str,
) -> Result<(), String> {
    let artifact = UntrustedRegionArtifact::from_untrusted_parts(program);
    match artifact.verify_against(region) {
        Err(RegionArtifactVerificationError::VerificationMismatch) => Ok(()),
        other => Err(format!("tampered {field} artifact result: {other:?}")),
    }
}
