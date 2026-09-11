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
    ProfileRegisterSet, ProfileRegisters, ProfileStepTrace, RunOutcome,
    StepOutcome, Termination, current_profile,
    verify_minimum_jump_rotate_crazy_halt_profile_width,
    verify_minimum_straight_line_io_profile_width,
    verify_straight_line_io_profile_width,
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

type InputGuardRegion =
    Result<(IndexedMachineState, VerifiedExactRegion), String>;
type OutputPrefixRegion =
    Result<(ProfileMachineState, VerifiedExactRegion), String>;
type OneStepRegion = Result<(IndexedMachineState, VerifiedExactRegion), String>;
type ClosureCandidate = Result<(IndexedMachineState, u32, u32), String>;

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

fn one_step_register_dependencies(
    source: &[u8],
    input: Vec<u8>,
) -> Result<ProfileRegisterSet, String> {
    let machine = ProfileMachine::from_source(current_profile(), source, input)
        .map_err(|error| format!("register-live-in load failed: {error}"))?;
    let entry = IndexedMachineState::from_checkpoint(&machine.snapshot_state())
        .map_err(|error| format!("register-live-in entry failed: {error:?}"))?;
    let region = ExactRegionCertificate::record(&entry, 1)
        .and_then(|certificate| certificate.verify())
        .map_err(|error| {
            format!("register-live-in verify failed: {error:?}")
        })?;
    Ok(region.register_dependencies())
}

#[test]
fn register_live_ins_derive_only_from_normative_access_evidence()
-> Result<(), String> {
    let halt = one_step_register_dependencies(b"QP", Vec::new())?;
    let input = one_step_register_dependencies(b"uP", vec![0x41])?;
    let output = one_step_register_dependencies(b"cP", Vec::new())?;
    let c_only = ProfileRegisterSet {
        accumulator: false,
        code_pointer: true,
        data_pointer: false,
    };
    let cd = ProfileRegisterSet {
        accumulator: false,
        code_pointer: true,
        data_pointer: true,
    };
    let acd = ProfileRegisterSet {
        accumulator: true,
        code_pointer: true,
        data_pointer: true,
    };
    if halt != c_only || input != cd || output != acd {
        let details =
            format!("halt={halt:?} input={input:?} output={output:?}");
        return Err(format!("register live-ins drifted: {details}"));
    }
    Ok(())
}

fn one_step_region(source: &[u8], input: Vec<u8>) -> OneStepRegion {
    let machine = ProfileMachine::from_source(current_profile(), source, input)
        .map_err(|error| format!("register-rebase load failed: {error}"))?;
    let entry = IndexedMachineState::from_checkpoint(&machine.snapshot_state())
        .map_err(|error| format!("register-rebase entry failed: {error:?}"))?;
    let region = ExactRegionCertificate::record(&entry, 1)
        .and_then(|certificate| certificate.verify())
        .map_err(|error| format!("register-rebase verify failed: {error:?}"))?;
    Ok((entry, region))
}

fn changed_accumulator(
    entry: &IndexedMachineState,
) -> Result<IndexedMachineState, String> {
    let checkpoint = entry.materialize_checkpoint().map_err(|error| {
        format!("register-rebase checkpoint failed: {error:?}")
    })?;
    let before = checkpoint.registers();
    entry
        .with_validated_registers(ProfileRegisters {
            accumulator: changed_word(before.accumulator),
            code_pointer: before.code_pointer,
            data_pointer: before.data_pointer,
        })
        .map_err(|error| format!("register-rebase candidate failed: {error:?}"))
}

#[test]
fn dependency_guard_rebases_only_non_live_in_registers() -> Result<(), String> {
    let (input_entry, input_region) = one_step_region(b"uP", vec![0x41])?;
    let input_candidate = changed_accumulator(&input_entry)?;
    if input_region.register_dependencies().accumulator
        || !input_region
            .accepts_dependency_entry(&input_candidate)
            .map_err(|error| {
                format!("input register guard failed: {error:?}")
            })?
    {
        return Err(String::from("input region retained dead accumulator"));
    }
    let execution =
        input_region
            .execute_or_deopt(&input_candidate)
            .map_err(|error| {
                format!("input register shortcut failed: {error:?}")
            })?;
    let candidate_checkpoint =
        input_candidate.materialize_checkpoint().map_err(|error| {
            format!("input candidate materialize failed: {error:?}")
        })?;
    let mut direct = ProfileMachine::from_snapshot(candidate_checkpoint);
    let direct_outcome = direct
        .run(1)
        .map_err(|error| format!("input register direct failed: {error}"))?;
    let shortcut =
        execution
            .state()
            .materialize_checkpoint()
            .map_err(|error| {
                format!("input shortcut materialize failed: {error:?}")
            })?;
    if execution.tier() != RegionExecutionTier::VerifiedShortcut
        || execution.outcome() != direct_outcome
        || shortcut != direct.snapshot_state()
    {
        return Err(String::from("input register rebase diverged from VM"));
    }

    let (output_entry, output_region) = one_step_region(b"cP", Vec::new())?;
    let output_candidate = changed_accumulator(&output_entry)?;
    if !output_region.register_dependencies().accumulator
        || output_region
            .accepts_dependency_entry(&output_candidate)
            .map_err(|error| {
                format!("output register guard failed: {error:?}")
            })?
    {
        return Err(String::from("output region ignored live accumulator"));
    }
    Ok(())
}

fn all_irrelevant_dimensions_candidate(
    entry: &IndexedMachineState,
    region: &VerifiedExactRegion,
) -> ClosureCandidate {
    let checkpoint = entry
        .materialize_checkpoint()
        .map_err(|error| format!("closure checkpoint failed: {error:?}"))?;
    let address = irrelevant_address(region)?;
    let mut memory = checkpoint.memory().to_vec();
    let index = usize::try_from(address)
        .map_err(|_error| String::from("closure address conversion failed"))?;
    let slot = memory
        .get_mut(index)
        .ok_or_else(|| String::from("closure irrelevant address missing"))?;
    let changed_memory = changed_word(*slot);
    *slot = changed_memory;
    let registers = checkpoint.registers();
    let changed_accumulator = changed_word(registers.accumulator);
    let io = ProfileMachineIoState::new(
        vec![0xaa, 0xbb, 0x41, 0x99],
        2,
        vec![0x90, 0x91],
        None,
    )
    .map_err(|error| format!("closure IO failed: {error}"))?;
    let candidate = ProfileMachineState::new_with_geometry(
        checkpoint.geometry(),
        memory,
        ProfileRegisters {
            accumulator: changed_accumulator,
            code_pointer: registers.code_pointer,
            data_pointer: registers.data_pointer,
        },
        io,
    )
    .map_err(|error| format!("closure candidate checkpoint failed: {error}"))?;
    let indexed =
        IndexedMachineState::from_checkpoint(&candidate).map_err(|error| {
            format!("closure candidate index failed: {error:?}")
        })?;
    Ok((indexed, address, changed_memory))
}

#[test]
fn dependency_guard_composes_all_proved_future_irrelevance()
-> Result<(), String> {
    let (entry, region) = one_step_region(b"uP", vec![0x41, 0x33])?;
    if region.register_dependencies().accumulator {
        return Err(String::from("closure fixture unexpectedly reads entry A"));
    }
    let (candidate, address, changed_memory) =
        all_irrelevant_dimensions_candidate(&entry, &region)?;
    if entry.exact_state_eq(&candidate) {
        return Err(String::from("closure candidate remained exact-equal"));
    }
    if !region
        .accepts_dependency_entry(&candidate)
        .map_err(|error| {
            format!("closure dependency guard failed: {error:?}")
        })?
    {
        return Err(String::from("closure guard retained irrelevant history"));
    }
    validate_dependency_shortcut(&region, &candidate, address, changed_memory)
}

#[test]
fn dependency_guard_retains_live_termination_state() -> Result<(), String> {
    let (entry, region) = one_step_region(b"uP", vec![0x41])?;
    let checkpoint = entry
        .materialize_checkpoint()
        .map_err(|error| format!("termination checkpoint failed: {error:?}"))?;
    let io = ProfileMachineIoState::new(
        checkpoint.io().input().to_vec(),
        checkpoint.io().input_consumed(),
        checkpoint.io().output().to_vec(),
        Some(Termination::HaltInstruction),
    )
    .map_err(|error| format!("termination IO failed: {error}"))?;
    let terminated = ProfileMachineState::new_with_geometry(
        checkpoint.geometry(),
        checkpoint.memory().to_vec(),
        checkpoint.registers(),
        io,
    )
    .map_err(|error| format!("termination candidate failed: {error}"))?;
    let candidate = IndexedMachineState::from_checkpoint(&terminated)
        .map_err(|error| format!("termination index failed: {error:?}"))?;
    if region
        .accepts_dependency_entry(&candidate)
        .map_err(|error| format!("termination guard failed: {error:?}"))?
    {
        return Err(String::from("live region accepted terminated candidate"));
    }
    validate_region_execution_matches_direct(
        &region,
        &candidate,
        RegionExecutionTier::InterpreterFallback,
    )
}

#[test]
fn dependency_guard_preserves_opaque_geometry_authority() -> Result<(), String>
{
    let profile = current_profile();
    let source = b"uCar_L";
    let verified_geometry = verify_straight_line_io_profile_width(
        profile,
        source,
        profile.word_trits(),
    )
    .map_err(|error| format!("geometry authority verify failed: {error}"))?;
    let machine =
        ProfileMachine::from_verified_source(&verified_geometry, vec![
            0xa5, 0x3c,
        ])
        .map_err(|error| format!("geometry authority load failed: {error}"))?;
    let restricted = machine.snapshot_state();
    let entry =
        IndexedMachineState::from_checkpoint(&restricted).map_err(|error| {
            format!("geometry authority entry failed: {error:?}")
        })?;
    let region = ExactRegionCertificate::record(&entry, 1)
        .and_then(|certificate| certificate.verify())
        .map_err(|error| {
            format!("geometry authority region failed: {error:?}")
        })?;
    let canonical = ProfileMachineState::new(
        profile,
        restricted.memory().to_vec(),
        restricted.registers(),
        restricted.io().clone(),
    )
    .map_err(|error| format!("canonical geometry candidate failed: {error}"))?;
    if restricted.geometry().memory_words()
        != canonical.geometry().memory_words()
        || restricted.geometry().word_trits()
            != canonical.geometry().word_trits()
        || restricted.geometry() == canonical.geometry()
    {
        return Err(String::from(
            "geometry authority fixture did not isolate token",
        ));
    }
    let candidate =
        IndexedMachineState::from_checkpoint(&canonical).map_err(|error| {
            format!("canonical geometry index failed: {error:?}")
        })?;
    if region
        .accepts_dependency_entry(&candidate)
        .map_err(|error| {
            format!("geometry authority guard failed: {error:?}")
        })?
    {
        return Err(String::from("dependency guard crossed opaque geometry"));
    }
    Ok(())
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

fn validate_output_history_rebase(
    checkpoint: &ProfileMachineState,
    verified: &VerifiedExactRegion,
    prefix: Vec<u8>,
    expected_output: &[u8],
) -> Result<(), String> {
    let candidate_checkpoint = checkpoint_with_output(checkpoint, prefix)?;
    let candidate = IndexedMachineState::from_checkpoint(&candidate_checkpoint)
        .map_err(|error| {
            format!("output-rebase candidate failed: {error:?}")
        })?;
    if verified.accepts_entry(&candidate) {
        return Err(String::from("exact guard ignored output history"));
    }
    if !verified
        .accepts_dependency_entry(&candidate)
        .map_err(|error| format!("output-rebase guard failed: {error:?}"))?
    {
        return Err(String::from("dependency guard retained output history"));
    }
    let shortcut = verified
        .apply_dependency_shortcut(&candidate)
        .map_err(|error| format!("output-rebase shortcut failed: {error:?}"))?;
    let mut direct_machine =
        ProfileMachine::from_snapshot(candidate_checkpoint);
    let direct_outcome = direct_machine
        .run(verified.step_budget())
        .map_err(|error| format!("output-rebase direct run failed: {error}"))?;
    let shortcut_checkpoint =
        shortcut.materialize_checkpoint().map_err(|error| {
            format!("output-rebase shortcut materialize failed: {error:?}")
        })?;
    if direct_outcome != verified.outcome()
        || shortcut_checkpoint != direct_machine.snapshot_state()
        || shortcut_checkpoint.io().output() != expected_output
    {
        return Err(String::from(
            "rebased output shortcut diverged from normative VM",
        ));
    }
    Ok(())
}

#[test]
fn dependency_guard_rebases_output_history() -> Result<(), String> {
    let (checkpoint, verified) = output_prefix_region_fixture()?;
    validate_output_history_rebase(&checkpoint, &verified, vec![0x5a], &[
        0x5a, 0x3c,
    ])?;
    validate_output_history_rebase(&checkpoint, &verified, vec![0x5a, 0x5b], &[
        0x5a, 0x5b, 0x3c,
    ])
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
    let mut machine =
        ProfileMachine::from_verified_source(&geometry, vec![0x11, 0x7a, 0x33])
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

fn initial_input_guard_region(
    input: Vec<u8>,
    budget: usize,
) -> InputGuardRegion {
    let geometry = verify_minimum_straight_line_io_profile_width(
        current_profile(),
        INPUT_GUARD_SOURCE,
    )
    .map_err(|error| format!("bounded-input width verification: {error}"))?;
    let machine = ProfileMachine::from_verified_source(&geometry, input)
        .map_err(|error| format!("bounded-input load failed: {error}"))?;
    let entry = IndexedMachineState::from_checkpoint(&machine.snapshot_state())
        .map_err(|error| format!("bounded-input entry failed: {error:?}"))?;
    let region = ExactRegionCertificate::record(&entry, budget)
        .and_then(|certificate| certificate.verify())
        .map_err(|error| {
            format!("bounded-input region verify failed: {error:?}")
        })?;
    Ok((entry, region))
}

fn rebind_input_cursor(
    entry: &IndexedMachineState,
    input: Vec<u8>,
    input_cursor: usize,
) -> Result<IndexedMachineState, String> {
    let checkpoint = entry.materialize_checkpoint().map_err(|error| {
        format!("cursor-rebase checkpoint failed: {error:?}")
    })?;
    let io = ProfileMachineIoState::new(
        input,
        input_cursor,
        checkpoint.io().output().to_vec(),
        checkpoint.io().termination(),
    )
    .map_err(|error| format!("cursor-rebase IO failed: {error}"))?;
    let rebound = ProfileMachineState::new_with_geometry(
        checkpoint.geometry(),
        checkpoint.memory().to_vec(),
        checkpoint.registers(),
        io,
    )
    .map_err(|error| format!("cursor-rebase state failed: {error}"))?;
    IndexedMachineState::from_checkpoint(&rebound)
        .map_err(|error| format!("cursor-rebase index failed: {error:?}"))
}

fn validate_region_execution_matches_direct(
    region: &VerifiedExactRegion,
    candidate: &IndexedMachineState,
    expected_tier: RegionExecutionTier,
) -> Result<(), String> {
    let execution = region
        .execute_or_deopt(candidate)
        .map_err(|error| format!("input execution failed: {error:?}"))?;
    let mut direct = ProfileMachine::from_snapshot(
        candidate.materialize_checkpoint().map_err(|error| {
            format!("input candidate materialize failed: {error:?}")
        })?,
    );
    let direct_outcome = direct
        .run(region.step_budget())
        .map_err(|error| format!("input direct run failed: {error}"))?;
    let observed =
        execution
            .state()
            .materialize_checkpoint()
            .map_err(|error| {
                format!("input result materialize failed: {error:?}")
            })?;
    if execution.tier() != expected_tier
        || execution.outcome() != direct_outcome
        || observed != direct.snapshot_state()
    {
        return Err(String::from("input region diverged from normative VM"));
    }
    Ok(())
}

#[test]
fn dependency_guard_ignores_input_unobserved_by_region() -> Result<(), String> {
    let (entry, region) = consumed_input_guard_region()?;
    let changed_tail = entry
        .with_validated_input(vec![0x22, 0x99, 0x44])
        .map_err(|error| format!("input-tail candidate failed: {error:?}"))?;
    let absent_tail = entry
        .with_validated_input(vec![0x22, 0x99])
        .map_err(|error| format!("input-tail truncation failed: {error:?}"))?;
    for candidate in [&changed_tail, &absent_tail] {
        if entry.exact_non_memory_eq(candidate)
            || !region
                .accepts_dependency_entry(candidate)
                .map_err(|error| {
                    format!("input-tail dependency check failed: {error:?}")
                })?
        {
            return Err(String::from(
                "no-input region retained unobserved input bytes",
            ));
        }
        validate_region_execution_matches_direct(
            &region,
            candidate,
            RegionExecutionTier::VerifiedShortcut,
        )?;
    }
    Ok(())
}

#[test]
fn dependency_guard_requires_only_bounded_input_bytes() -> Result<(), String> {
    let (entry, region) =
        initial_input_guard_region(vec![0x11, 0x7a, 0x33], 2)?;
    let changed_tail = entry
        .with_validated_input(vec![0x11, 0x7a, 0x44])
        .map_err(|error| format!("bounded tail candidate failed: {error:?}"))?;
    let absent_tail =
        entry
            .with_validated_input(vec![0x11, 0x7a])
            .map_err(|error| {
                format!("bounded tail truncation failed: {error:?}")
            })?;
    for candidate in [&changed_tail, &absent_tail] {
        if !region
            .accepts_dependency_entry(candidate)
            .map_err(|error| format!("bounded input guard failed: {error:?}"))?
        {
            return Err(String::from(
                "bounded input guard retained unread tail",
            ));
        }
        validate_region_execution_matches_direct(
            &region,
            candidate,
            RegionExecutionTier::VerifiedShortcut,
        )?;
    }
    let changed_observed =
        entry.with_validated_input(vec![0x11, 0x55, 0x44]).map_err(
            |error| format!("observed input candidate failed: {error:?}"),
        )?;
    if region
        .accepts_dependency_entry(&changed_observed)
        .map_err(|error| format!("observed input guard failed: {error:?}"))?
    {
        return Err(String::from("bounded input guard ignored observed byte"));
    }
    Ok(())
}

#[test]
fn dependency_guard_rebases_input_cursor_from_candidate() -> Result<(), String>
{
    let (entry, region) =
        initial_input_guard_region(vec![0x11, 0x7a, 0x33], 2)?;
    let candidate =
        rebind_input_cursor(&entry, vec![0xee, 0xdd, 0x11, 0x7a, 0x44], 2)?;
    if !region
        .accepts_dependency_entry(&candidate)
        .map_err(|error| format!("cursor-rebase guard failed: {error:?}"))?
    {
        return Err(String::from(
            "cursor-rebase guard retained absolute cursor",
        ));
    }
    validate_region_execution_matches_direct(
        &region,
        &candidate,
        RegionExecutionTier::VerifiedShortcut,
    )?;
    let changed_observed =
        rebind_input_cursor(&entry, vec![0xee, 0xdd, 0x11, 0x55, 0x44], 2)?;
    if region
        .accepts_dependency_entry(&changed_observed)
        .map_err(|error| {
            format!("cursor-rebase observed guard failed: {error:?}")
        })?
    {
        return Err(String::from(
            "cursor rebase ignored relative observed byte",
        ));
    }
    Ok(())
}

#[test]
fn dependency_guard_rebases_eof_to_candidate_cursor() -> Result<(), String> {
    let (entry, region) = one_step_region(b"uP", Vec::new())?;
    let candidate_eof = rebind_input_cursor(&entry, vec![0xaa, 0xbb], 2)?;
    if !region
        .accepts_dependency_entry(&candidate_eof)
        .map_err(|error| format!("rebased EOF guard failed: {error:?}"))?
    {
        return Err(String::from("rebased EOF retained absolute cursor"));
    }
    validate_region_execution_matches_direct(
        &region,
        &candidate_eof,
        RegionExecutionTier::VerifiedShortcut,
    )?;
    let candidate_not_eof = rebind_input_cursor(&entry, vec![0xaa, 0xbb], 1)?;
    if region
        .accepts_dependency_entry(&candidate_not_eof)
        .map_err(|error| format!("rebased non-EOF guard failed: {error:?}"))?
    {
        return Err(String::from("rebased EOF accepted available byte"));
    }
    validate_region_execution_matches_direct(
        &region,
        &candidate_not_eof,
        RegionExecutionTier::InterpreterFallback,
    )
}

#[test]
fn dependency_guard_preserves_verified_eof_observation() -> Result<(), String> {
    let (entry, region) = one_step_region(b"uP", Vec::new())?;
    let byte_available = entry
        .with_validated_input(vec![0x41])
        .map_err(|error| format!("EOF candidate failed: {error:?}"))?;
    if region
        .accepts_dependency_entry(&byte_available)
        .map_err(|error| format!("EOF dependency guard failed: {error:?}"))?
    {
        return Err(String::from("EOF guard accepted available input byte"));
    }
    validate_region_execution_matches_direct(
        &region,
        &byte_available,
        RegionExecutionTier::InterpreterFallback,
    )
}
