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
//   - Exact-region verifier, guard invalidation, and rejection fixtures.
// - Must-Not:
//   - Trust recorded certificates without re-execution or use digest-only
//   - guards.
// - Allows:
//   - Inputs: current-profile exact states and bounded normative execution.
//   - Outputs: verifier acceptance/rejection evidence for future native
//   - shortcuts.
//   - Side effects: test-process allocation and normative VM execution only.
// - Split-When:
//   - Split when broader dependency guards gain separate certification
//   - evidence.
// - Merge-When:
//   - Merge when a tiered native engine owns equivalent verifier fixtures.
// - Summary:
//   - Proves exact-state region certificates fail closed around
//   - mutations/errors.
// - Description:
//   - Verifies current execution, tamper detection, guard invalidation,
//   - rejection.
// - Usage:
//   - Composed by `tests/state_graph_research.rs`.
// - Defaults:
//   - Only verifier-produced `VerifiedExactRegion` is admitted as trusted.
//

//! Verification evidence for exact-state guarded future native regions.

use malbolge::{
    ProfileMachine, ProfileMachineError, ProfileMachineIoState,
    ProfileMachineState, ProfileMemoryDelta, ProfileMemoryWrite,
    ProfileStepTrace, RunOutcome, StepOutcome, Termination, current_profile,
    verify_minimum_jump_rotate_crazy_halt_profile_width,
    verify_minimum_straight_line_io_profile_width,
};

use crate::indexed_state::IndexedMachineState;
use crate::region_certificate::{
    ExactRegionCertificate, ExactRegionError, RegionExecutionTier,
    UntrustedExactRegionClaim, VerifiedExactRegion,
};

const CURRENT_SOURCE: &[u8] = b"(=%`qL";
const REGION_BUDGET: usize = 8;
const REJECTING_SOURCE: &[u8] = b"b'";
const TRANSFORM_SOURCE: &[u8] = b"(&<;:9K";
const TRANSFORM_BUDGET: usize = 6;
const INPUT_GUARD_SOURCE: &[u8] = b"utO";
const INPUT_GUARD_SUFFIX: u8 = 0x33;

type InputGuardRegion =
    Result<(IndexedMachineState, VerifiedExactRegion), String>;
type OutputPrefixRegion =
    Result<(ProfileMachineState, VerifiedExactRegion), String>;

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
    Err(String::from("no irrelevant region-memory address found"))
}

fn validate_dependency_shortcut(
    verified: &VerifiedExactRegion,
    candidate: &IndexedMachineState,
    address: u32,
    expected_irrelevant: u32,
) -> Result<(), String> {
    let shortcut_exit = verified
        .apply_dependency_shortcut(candidate)
        .map_err(|error| format!("dependency shortcut failed: {error:?}"))?;
    let mut direct = ProfileMachine::from_snapshot(
        candidate.materialize_checkpoint().map_err(|error| {
            format!("dependency candidate materialize: {error:?}")
        })?,
    );
    let direct_outcome = direct
        .run(verified.step_budget())
        .map_err(|error| format!("dependency direct run failed: {error}"))?;
    if direct_outcome != verified.outcome() {
        return Err(String::from("dependency shortcut outcome changed"));
    }
    let shortcut_checkpoint =
        shortcut_exit.materialize_checkpoint().map_err(|error| {
            format!("dependency shortcut materialize: {error:?}")
        })?;
    if shortcut_checkpoint != direct.snapshot_state() {
        return Err(String::from(
            "dependency shortcut exit differs from direct VM",
        ));
    }
    let preserved = shortcut_exit
        .memory_word(address)
        .map_err(|error| format!("dependency preserved read: {error:?}"))?;
    if preserved != expected_irrelevant {
        return Err(String::from("dependency shortcut lost irrelevant memory"));
    }
    Ok(())
}

#[test]
fn current_region_reexecutes_to_exact_verified_exit() -> Result<(), String> {
    let mut direct =
        ProfileMachine::from_source(current_profile(), CURRENT_SOURCE, vec![
            0x41,
        ])
        .map_err(|error| format!("region direct load failed: {error}"))?;
    let entry = IndexedMachineState::from_checkpoint(&direct.snapshot_state())
        .map_err(|error| format!("region entry failed: {error:?}"))?;
    let certificate = ExactRegionCertificate::record(&entry, REGION_BUDGET)
        .map_err(|error| format!("region record failed: {error:?}"))?;
    let verified = certificate
        .verify()
        .map_err(|error| format!("region verify failed: {error:?}"))?;
    let direct_outcome = direct
        .run(REGION_BUDGET)
        .map_err(|error| format!("region direct run failed: {error}"))?;
    if verified.outcome() != direct_outcome {
        return Err(String::from(
            "verified region outcome differs from direct VM",
        ));
    }
    let exit = verified.exit().materialize_checkpoint().map_err(|error| {
        format!("region exit materialize failed: {error:?}")
    })?;
    if exit != direct.snapshot_state() {
        return Err(String::from(
            "verified region exit differs from direct VM",
        ));
    }
    if !verified.accepts_entry(&entry) {
        return Err(String::from("verified region rejected its exact entry"));
    }
    Ok(())
}

#[test]
fn exact_guard_rejects_mutated_entry_state() -> Result<(), String> {
    let machine =
        ProfileMachine::from_source(current_profile(), CURRENT_SOURCE, vec![
            0x41,
        ])
        .map_err(|error| format!("region guard load failed: {error}"))?;
    let entry = IndexedMachineState::from_checkpoint(&machine.snapshot_state())
        .map_err(|error| format!("region guard entry failed: {error:?}"))?;
    let certificate = ExactRegionCertificate::record(&entry, REGION_BUDGET)
        .map_err(|error| format!("region guard record failed: {error:?}"))?;
    let verified = certificate
        .verify()
        .map_err(|error| format!("region guard verify failed: {error:?}"))?;
    let first_trace =
        verified.traces().first().copied().ok_or_else(|| {
            String::from("verified region has no first trace")
        })?;
    let mutated = entry
        .apply_trace(&first_trace)
        .map_err(|error| format!("region guard mutation failed: {error:?}"))?;
    if verified.accepts_entry(&mutated) {
        Err(String::from("exact region guard accepted a mutated entry"))
    } else {
        Ok(())
    }
}

#[test]
fn tampered_certificate_fails_normative_reverification() -> Result<(), String> {
    let machine =
        ProfileMachine::from_source(current_profile(), CURRENT_SOURCE, vec![
            0x41,
        ])
        .map_err(|error| format!("region tamper load failed: {error}"))?;
    let entry = IndexedMachineState::from_checkpoint(&machine.snapshot_state())
        .map_err(|error| format!("region tamper entry failed: {error:?}"))?;
    let certificate = ExactRegionCertificate::record(&entry, REGION_BUDGET)
        .map_err(|error| format!("region tamper record failed: {error:?}"))?;
    let tampered = ExactRegionCertificate::from_untrusted_parts(
        UntrustedExactRegionClaim {
            entry: certificate.entry().clone(),
            exit: certificate.exit().clone(),
            outcome: RunOutcome::BudgetExhausted { steps: 0 },
            step_budget: certificate.step_budget(),
            traces: certificate.traces().to_vec(),
        },
    );
    match tampered.verify() {
        Err(ExactRegionError::VerificationMismatch) => Ok(()),
        other => Err(format!("tampered region certificate result: {other:?}")),
    }
}

#[test]
fn rejected_transition_never_records_verified_region() -> Result<(), String> {
    let machine =
        ProfileMachine::from_source(current_profile(), REJECTING_SOURCE, vec![
            0x44,
        ])
        .map_err(|error| format!("region reject load failed: {error}"))?;
    let entry = IndexedMachineState::from_checkpoint(&machine.snapshot_state())
        .map_err(|error| format!("region reject entry failed: {error:?}"))?;
    let result = ExactRegionCertificate::record(&entry, 1);
    match result {
        Err(ExactRegionError::Machine(
            ProfileMachineError::InvalidEncryptionTarget { .. },
        )) => Ok(()),
        other => {
            Err(format!("rejected transition certificate result: {other:?}"))
        },
    }
}

fn output_prefix_region_fixture() -> OutputPrefixRegion {
    let geometry = verify_minimum_straight_line_io_profile_width(
        current_profile(),
        b"uCar_L",
    )
    .map_err(|error| format!("output-prefix geometry failed: {error}"))?;
    let mut machine =
        ProfileMachine::from_verified_source(&geometry, vec![0xa5, 0x3c])
            .map_err(|error| format!("output-prefix load failed: {error}"))?;
    let prefix_outcome = machine
        .run(3)
        .map_err(|error| format!("output-prefix setup failed: {error}"))?;
    if prefix_outcome != (RunOutcome::BudgetExhausted { steps: 3 })
        || machine.output() != [0xa5]
        || machine.input_consumed() != 1
    {
        return Err(String::from("output-prefix setup drifted"));
    }
    let checkpoint = machine.snapshot_state();
    let entry = IndexedMachineState::from_checkpoint(&checkpoint)
        .map_err(|error| format!("output-prefix entry failed: {error:?}"))?;
    let verified = ExactRegionCertificate::record(&entry, 3)
        .and_then(|certificate| certificate.verify())
        .map_err(|error| format!("output-prefix verify failed: {error:?}"))?;
    Ok((checkpoint, verified))
}

fn checkpoint_with_output(
    checkpoint: &ProfileMachineState,
    output: Vec<u8>,
) -> Result<ProfileMachineState, String> {
    let io = ProfileMachineIoState::new(
        checkpoint.io().input().to_vec(),
        checkpoint.io().input_consumed(),
        output,
        checkpoint.io().termination(),
    )
    .map_err(|error| format!("output replacement IO failed: {error}"))?;
    ProfileMachineState::new_with_geometry(
        checkpoint.geometry(),
        checkpoint.memory().to_vec(),
        checkpoint.registers(),
        io,
    )
    .map_err(|error| format!("output replacement checkpoint failed: {error}"))
}

#[test]
fn dependency_guard_ignores_equal_length_output_prefix_contents()
-> Result<(), String> {
    let (checkpoint, verified) = output_prefix_region_fixture()?;
    let changed_checkpoint = checkpoint_with_output(&checkpoint, vec![0x5a])?;
    let candidate = IndexedMachineState::from_checkpoint(&changed_checkpoint)
        .map_err(|error| {
        format!("output-prefix candidate failed: {error:?}")
    })?;
    if verified.accepts_entry(&candidate) {
        return Err(String::from("exact guard ignored prior output bytes"));
    }
    if !verified
        .accepts_dependency_entry(&candidate)
        .map_err(|error| format!("output-prefix guard failed: {error:?}"))?
    {
        return Err(String::from(
            "dependency guard retained prior output bytes",
        ));
    }

    let shortcut = verified
        .apply_dependency_shortcut(&candidate)
        .map_err(|error| format!("output-prefix shortcut failed: {error:?}"))?;
    let mut direct = ProfileMachine::from_snapshot(changed_checkpoint);
    let direct_outcome = direct
        .run(verified.step_budget())
        .map_err(|error| format!("output-prefix direct run failed: {error}"))?;
    let shortcut_checkpoint =
        shortcut.materialize_checkpoint().map_err(|error| {
            format!("output-prefix shortcut materialize failed: {error:?}")
        })?;
    if direct_outcome != verified.outcome()
        || shortcut_checkpoint != direct.snapshot_state()
        || shortcut_checkpoint.io().output() != [0x5a, 0x3c]
    {
        return Err(String::from(
            "output-prefix shortcut diverged from candidate-owned history",
        ));
    }

    let longer_checkpoint =
        checkpoint_with_output(&checkpoint, vec![0x5a, 0x5b])?;
    let longer = IndexedMachineState::from_checkpoint(&longer_checkpoint)
        .map_err(|error| {
            format!("output-length candidate failed: {error:?}")
        })?;
    if verified
        .accepts_dependency_entry(&longer)
        .map_err(|error| format!("output-length guard failed: {error:?}"))?
    {
        return Err(String::from("dependency guard ignored output length"));
    }
    Ok(())
}

#[test]
fn dependency_guard_reuses_equal_independent_root() -> Result<(), String> {
    let machine =
        ProfileMachine::from_source(current_profile(), CURRENT_SOURCE, vec![
            0x41,
        ])
        .map_err(|error| format!("cross-root region load failed: {error}"))?;
    let checkpoint = machine.snapshot_state();
    let entry =
        IndexedMachineState::from_checkpoint(&checkpoint).map_err(|error| {
            format!("cross-root region entry failed: {error:?}")
        })?;
    let verified = ExactRegionCertificate::record(&entry, REGION_BUDGET)
        .and_then(|certificate| certificate.verify())
        .map_err(|error| {
            format!("cross-root region verify failed: {error:?}")
        })?;
    let candidate =
        IndexedMachineState::from_checkpoint(&checkpoint).map_err(|error| {
            format!("cross-root independent state failed: {error:?}")
        })?;
    let shortcut = verified
        .apply_dependency_shortcut(&candidate)
        .map_err(|error| format!("cross-root shortcut failed: {error:?}"))?;
    let mut direct = ProfileMachine::from_snapshot(checkpoint);
    let direct_outcome = direct
        .run(verified.step_budget())
        .map_err(|error| format!("cross-root direct run failed: {error}"))?;
    if direct_outcome != verified.outcome() {
        return Err(String::from("cross-root region outcome changed"));
    }
    let shortcut_checkpoint =
        shortcut.materialize_checkpoint().map_err(|error| {
            format!("cross-root shortcut materialize failed: {error:?}")
        })?;
    if shortcut_checkpoint != direct.snapshot_state() {
        return Err(String::from(
            "cross-root shortcut differs from normative VM",
        ));
    }
    Ok(())
}

#[test]
fn dependency_guard_reuses_irrelevant_independent_base_change()
-> Result<(), String> {
    let machine =
        ProfileMachine::from_source(current_profile(), CURRENT_SOURCE, vec![
            0x41,
        ])
        .map_err(|error| format!("base-change region load failed: {error}"))?;
    let checkpoint = machine.snapshot_state();
    let entry = IndexedMachineState::from_checkpoint(&checkpoint)
        .map_err(|error| format!("base-change entry failed: {error:?}"))?;
    let verified = ExactRegionCertificate::record(&entry, REGION_BUDGET)
        .and_then(|certificate| certificate.verify())
        .map_err(|error| format!("base-change verify failed: {error:?}"))?;
    let address = irrelevant_address(&verified)?;
    let index = usize::try_from(address)
        .map_err(|error| format!("base-change address failed: {error}"))?;
    let mut memory = checkpoint.memory().to_vec();
    let slot = memory
        .get_mut(index)
        .ok_or_else(|| String::from("base-change address missing"))?;
    let before = *slot;
    let after = changed_word(before);
    *slot = after;
    let variant = ProfileMachineState::new_with_geometry(
        checkpoint.geometry(),
        memory,
        checkpoint.registers(),
        checkpoint.io().clone(),
    )
    .map_err(|error| format!("base-change checkpoint failed: {error}"))?;
    let candidate = IndexedMachineState::from_checkpoint(&variant)
        .map_err(|error| format!("base-change candidate failed: {error:?}"))?;
    if verified.accepts_entry(&candidate) {
        return Err(String::from("exact guard accepted changed base root"));
    }
    if !verified
        .accepts_dependency_entry(&candidate)
        .map_err(|error| format!("base-change guard failed: {error:?}"))?
    {
        return Err(String::from("dependency guard rejected irrelevant base"));
    }
    validate_dependency_shortcut(&verified, &candidate, address, after)
}

#[test]
fn dependency_guard_reuses_region_across_irrelevant_memory()
-> Result<(), String> {
    let machine =
        ProfileMachine::from_source(current_profile(), CURRENT_SOURCE, vec![
            0x41,
        ])
        .map_err(|error| format!("dependency fixture load failed: {error}"))?;
    let entry = IndexedMachineState::from_checkpoint(&machine.snapshot_state())
        .map_err(|error| format!("dependency entry failed: {error:?}"))?;
    let verified = ExactRegionCertificate::record(&entry, REGION_BUDGET)
        .and_then(|certificate| certificate.verify())
        .map_err(|error| format!("dependency verify failed: {error:?}"))?;
    let address = irrelevant_address(&verified)?;
    let before = entry.memory_word(address).map_err(|error| {
        format!("dependency irrelevant read failed: {error:?}")
    })?;
    let after = changed_word(before);
    let candidate = entry
        .apply_memory_delta(ProfileMemoryDelta {
            data: Some(ProfileMemoryWrite { address, after, before }),
            encryption: None,
        })
        .map_err(|error| format!("dependency variant failed: {error:?}"))?;
    if verified.accepts_entry(&candidate) {
        return Err(String::from(
            "exact guard accepted irrelevant memory variant",
        ));
    }
    if !verified
        .accepts_dependency_entry(&candidate)
        .map_err(|error| format!("dependency guard failed: {error:?}"))?
    {
        return Err(String::from(
            "dependency guard rejected irrelevant memory",
        ));
    }
    validate_dependency_shortcut(&verified, &candidate, address, after)
}

#[test]
fn dependency_guard_rejects_live_in_memory_change() -> Result<(), String> {
    let machine =
        ProfileMachine::from_source(current_profile(), CURRENT_SOURCE, vec![
            0x41,
        ])
        .map_err(|error| format!("live-in fixture load failed: {error}"))?;
    let entry = IndexedMachineState::from_checkpoint(&machine.snapshot_state())
        .map_err(|error| format!("live-in entry failed: {error:?}"))?;
    let verified = ExactRegionCertificate::record(&entry, REGION_BUDGET)
        .and_then(|certificate| certificate.verify())
        .map_err(|error| format!("live-in verify failed: {error:?}"))?;
    let dependency = verified
        .memory_dependencies()
        .first()
        .copied()
        .ok_or_else(|| String::from("verified region has no live-in memory"))?;
    let candidate = entry
        .apply_memory_delta(ProfileMemoryDelta {
            data: Some(ProfileMemoryWrite {
                address: dependency.address,
                after: changed_word(dependency.value),
                before: dependency.value,
            }),
            encryption: None,
        })
        .map_err(|error| format!("live-in mutation failed: {error:?}"))?;
    if verified
        .accepts_dependency_entry(&candidate)
        .map_err(|error| format!("live-in guard error: {error:?}"))?
    {
        return Err(String::from("dependency guard accepted changed live-in"));
    }
    match verified.apply_dependency_shortcut(&candidate) {
        Err(ExactRegionError::DependencyGuardMismatch) => Ok(()),
        other => Err(format!("changed live-in shortcut result: {other:?}")),
    }
}

#[test]
fn tiered_region_uses_shortcut_for_irrelevant_memory_variant()
-> Result<(), String> {
    let machine =
        ProfileMachine::from_source(current_profile(), CURRENT_SOURCE, vec![
            0x41,
        ])
        .map_err(|error| format!("tier shortcut load failed: {error}"))?;
    let entry = IndexedMachineState::from_checkpoint(&machine.snapshot_state())
        .map_err(|error| format!("tier shortcut entry failed: {error:?}"))?;
    let verified = ExactRegionCertificate::record(&entry, REGION_BUDGET)
        .and_then(|certificate| certificate.verify())
        .map_err(|error| format!("tier shortcut verify failed: {error:?}"))?;
    let address = irrelevant_address(&verified)?;
    let before = entry
        .memory_word(address)
        .map_err(|error| format!("tier shortcut read failed: {error:?}"))?;
    let after = changed_word(before);
    let candidate = entry
        .apply_memory_delta(ProfileMemoryDelta {
            data: Some(ProfileMemoryWrite { address, after, before }),
            encryption: None,
        })
        .map_err(|error| format!("tier shortcut variant failed: {error:?}"))?;
    let execution = verified.execute_or_deopt(&candidate).map_err(|error| {
        format!("tier shortcut execution failed: {error:?}")
    })?;
    if execution.tier() != RegionExecutionTier::VerifiedShortcut {
        return Err(String::from("tier shortcut unexpectedly deoptimized"));
    }
    if execution.outcome() != verified.outcome() {
        return Err(String::from("tier shortcut outcome changed"));
    }
    validate_dependency_shortcut(&verified, &candidate, address, after)?;
    let expected = verified
        .apply_dependency_shortcut(&candidate)
        .map_err(|error| format!("tier shortcut baseline failed: {error:?}"))?;
    if !execution.state().exact_state_eq(&expected) {
        return Err(String::from("tier shortcut state differs from baseline"));
    }
    Ok(())
}

#[test]
fn tiered_region_deoptimizes_advanced_state_to_normative_vm()
-> Result<(), String> {
    let machine =
        ProfileMachine::from_source(current_profile(), CURRENT_SOURCE, vec![
            0x41,
        ])
        .map_err(|error| format!("tier deopt load failed: {error}"))?;
    let entry = IndexedMachineState::from_checkpoint(&machine.snapshot_state())
        .map_err(|error| format!("tier deopt entry failed: {error:?}"))?;
    let verified = ExactRegionCertificate::record(&entry, REGION_BUDGET)
        .and_then(|certificate| certificate.verify())
        .map_err(|error| format!("tier deopt verify failed: {error:?}"))?;
    let first_trace = verified
        .traces()
        .first()
        .ok_or_else(|| String::from("tier deopt region has no first trace"))?;
    let candidate = entry
        .apply_trace(first_trace)
        .map_err(|error| format!("tier deopt advance failed: {error:?}"))?;
    let execution = verified
        .execute_or_deopt(&candidate)
        .map_err(|error| format!("tier deopt execution failed: {error:?}"))?;
    if execution.tier() != RegionExecutionTier::InterpreterFallback {
        return Err(String::from("advanced state did not deoptimize"));
    }
    let mut direct = ProfileMachine::from_snapshot(
        candidate.materialize_checkpoint().map_err(|error| {
            format!("tier direct checkpoint failed: {error:?}")
        })?,
    );
    let mut traces = Vec::new();
    let outcome = direct
        .run_traced(verified.step_budget(), &mut |trace: &ProfileStepTrace| {
            traces.push(*trace);
        })
        .map_err(|error| format!("tier direct run failed: {error}"))?;
    let mut expected = candidate;
    for trace in &traces {
        expected = expected
            .apply_trace(trace)
            .map_err(|error| format!("tier direct trace failed: {error:?}"))?;
    }
    if execution.outcome() != outcome {
        return Err(String::from("deopt outcome differs from normative VM"));
    }
    if !execution.state().exact_state_eq(&expected) {
        return Err(String::from("deopt state differs from normative VM"));
    }
    Ok(())
}

#[test]
fn tiered_region_deopt_propagates_normative_rejection() -> Result<(), String> {
    let machine =
        ProfileMachine::from_source(current_profile(), CURRENT_SOURCE, vec![
            0x41,
        ])
        .map_err(|error| format!("tier reject load failed: {error}"))?;
    let entry = IndexedMachineState::from_checkpoint(&machine.snapshot_state())
        .map_err(|error| format!("tier reject entry failed: {error:?}"))?;
    let verified = ExactRegionCertificate::record(&entry, REGION_BUDGET)
        .and_then(|certificate| certificate.verify())
        .map_err(|error| format!("tier reject verify failed: {error:?}"))?;
    let dependency = verified
        .memory_dependencies()
        .first()
        .copied()
        .ok_or_else(|| String::from("tier reject has no live-in dependency"))?;
    let candidate = entry
        .apply_memory_delta(ProfileMemoryDelta {
            data: Some(ProfileMemoryWrite {
                address: dependency.address,
                after: changed_word(dependency.value),
                before: dependency.value,
            }),
            encryption: None,
        })
        .map_err(|error| format!("tier reject variant failed: {error:?}"))?;
    let mut direct = ProfileMachine::from_snapshot(
        candidate.materialize_checkpoint().map_err(|error| {
            format!("tier reject checkpoint failed: {error:?}")
        })?,
    );
    let expected = direct.run(verified.step_budget());
    let observed = verified.execute_or_deopt(&candidate);
    match (expected, observed) {
        (
            Err(expected_error),
            Err(ExactRegionError::Machine(observed_error)),
        ) if expected_error == observed_error => Ok(()),
        other => Err(format!("tier rejection mismatch: {other:?}")),
    }
}

#[test]
fn verified_region_hoists_rotate_and_crazy_results() -> Result<(), String> {
    let geometry = verify_minimum_jump_rotate_crazy_halt_profile_width(
        current_profile(),
        TRANSFORM_SOURCE,
    )
    .map_err(|error| format!("transform-hoist width verification: {error}"))?;
    let machine =
        ProfileMachine::from_verified_source(&geometry, Vec::new())
            .map_err(|error| format!("transform-hoist load failed: {error}"))?;
    let entry = IndexedMachineState::from_checkpoint(&machine.snapshot_state())
        .map_err(|error| format!("transform-hoist entry failed: {error:?}"))?;
    let region = ExactRegionCertificate::record(&entry, TRANSFORM_BUDGET)
        .and_then(|certificate| certificate.verify())
        .map_err(|error| format!("transform-hoist verify failed: {error:?}"))?;
    let decoded: Vec<u8> = region
        .traces()
        .iter()
        .filter_map(|trace| trace.decoded)
        .collect();
    if !decoded.contains(&b'*') || !decoded.contains(&b'p') {
        return Err(format!(
            "transform-hoist trace lacks rotate/crazy: {decoded:?}"
        ));
    }
    let address = irrelevant_address(&region)?;
    let before = entry.memory_word(address).map_err(|error| {
        format!("transform-hoist irrelevant read: {error:?}")
    })?;
    let after = changed_word(before);
    let candidate = entry
        .apply_memory_delta(ProfileMemoryDelta {
            data: Some(ProfileMemoryWrite { address, after, before }),
            encryption: None,
        })
        .map_err(|error| {
            format!("transform-hoist variant failed: {error:?}")
        })?;
    if !region
        .accepts_dependency_entry(&candidate)
        .map_err(|error| format!("transform-hoist guard failed: {error:?}"))?
    {
        return Err(String::from(
            "transform-hoist guard rejected irrelevant memory",
        ));
    }
    validate_dependency_shortcut(&region, &candidate, address, after)
}

fn consumed_input_guard_region() -> InputGuardRegion {
    let geometry = verify_minimum_straight_line_io_profile_width(
        current_profile(),
        INPUT_GUARD_SOURCE,
    )
    .map_err(|error| format!("input-guard width verification: {error}"))?;
    let mut machine = ProfileMachine::from_verified_source(&geometry, vec![
        0x11,
        0x7a,
        INPUT_GUARD_SUFFIX,
    ])
    .map_err(|error| format!("input-guard load failed: {error}"))?;
    for _step in 0..2usize {
        let outcome = machine
            .step()
            .map_err(|error| format!("input-guard prefix step: {error}"))?;
        if outcome != StepOutcome::Continued {
            return Err(format!(
                "input-guard stopped before region: {outcome:?}"
            ));
        }
    }
    let entry = IndexedMachineState::from_checkpoint(&machine.snapshot_state())
        .map_err(|error| format!("input-guard entry failed: {error:?}"))?;
    let region = ExactRegionCertificate::record(&entry, 1)
        .and_then(|certificate| certificate.verify())
        .map_err(|error| {
            format!("input-guard region verify failed: {error:?}")
        })?;
    Ok((entry, region))
}

#[test]
fn dependency_guard_drops_only_consumed_input_prefix() -> Result<(), String> {
    let (entry, region) = consumed_input_guard_region()?;
    let candidate = entry
        .with_validated_input(vec![0x22, 0x99, INPUT_GUARD_SUFFIX])
        .map_err(|error| format!("input-guard candidate failed: {error:?}"))?;
    if entry.exact_non_memory_eq(&candidate) {
        return Err(String::from(
            "exact guard ignored replaced consumed input",
        ));
    }
    if !region
        .accepts_dependency_entry(&candidate)
        .map_err(|error| format!("input-guard dependency check: {error:?}"))?
    {
        return Err(String::from("dependency guard retained consumed prefix"));
    }
    let execution = region
        .execute_or_deopt(&candidate)
        .map_err(|error| format!("input-guard shortcut failed: {error:?}"))?;
    let expected = RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        steps: 1,
    };
    if execution.tier() != RegionExecutionTier::VerifiedShortcut
        || execution.outcome() != expected
    {
        return Err(String::from("consumed-prefix candidate did not shortcut"));
    }
    let changed_suffix =
        entry.with_validated_input(vec![0x22, 0x99, 0x44]).map_err(
            |error| format!("input-guard suffix variant failed: {error:?}"),
        )?;
    if region
        .accepts_dependency_entry(&changed_suffix)
        .map_err(|error| format!("input-guard suffix check: {error:?}"))?
    {
        return Err(String::from(
            "dependency guard ignored remaining input suffix",
        ));
    }
    Ok(())
}
