// File:
//   - r.rs
// Path:
//   - algorithms/self-modification-state-graph-optimizer/tests/r.rs
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
//   - Exact-region verifier, guard invalidation, and rejection fixtures.
// - Must-Not:
//   - Trust recorded certificates without re-execution or use digest-only
//     guards.
// - Allows:
//   - Inputs: current-profile exact states and bounded normative execution.
//   - Outputs: verifier acceptance/rejection evidence for future native
//     shortcuts.
//   - Side effects: test-process allocation and normative VM execution only.
// - Split-When:
//   - Split when broader dependency guards gain separate certification
//     evidence.
// - Merge-When:
//   - Merge when a tiered native engine owns equivalent verifier fixtures.
// - Summary:
//   - Proves exact-state region certificates fail closed around
//     mutations/errors.
// - Description:
//   - Verifies current execution, tamper detection, guard invalidation,
//     rejection.
// - Usage:
//   - Composed by `tests/state_graph_research.rs`.
// - Defaults:
//   - Only verifier-produced `VerifiedExactRegion` is admitted as trusted.
//
// Related documents:
// - algorithms/self-modification-state-graph-optimizer/region.rs
//
// Large file:
//   - false

//! Verification evidence for exact-state guarded future native regions.

use malbolge::{
    ProfileMachine, ProfileMachineError, ProfileMemoryDelta,
    ProfileMemoryWrite, RunOutcome, current_profile,
};

use crate::indexed_state::IndexedMachineState;
use crate::region_certificate::{
    ExactRegionCertificate, ExactRegionError, UntrustedExactRegionClaim,
    VerifiedExactRegion,
};

const CURRENT_SOURCE: &[u8] = b"(=%`qL";
const REGION_BUDGET: usize = 8;
const REJECTING_SOURCE: &[u8] = b"b'";

fn changed_word(value: u32) -> u32 {
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
        .run(REGION_BUDGET)
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
